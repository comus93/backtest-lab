"""Synthetic, deterministic tests for independent weekly SMA research."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_lab.core import RuntimeConfig
from backtest_lab.strategies.multi_asset_weekly_sma.r01 import (
    AssetInput, SMARegimeStrategy, START, SUMMARY_COLUMNS, run_asset,
    weekly_sma_signals, write_asset_results,
)


def sample(days=450):
    idx = pd.bdate_range("2015-11-02", periods=days)
    reference = pd.Series(np.linspace(100.0, 150.0, len(idx)), index=idx)
    domestic = pd.Series(np.linspace(1000.0, 1500.0, len(idx)), index=idx)
    inverse = pd.Series(np.linspace(150.0, 100.0, len(idx)), index=idx)
    return idx, reference, domestic, inverse


def test_21_completed_weeks_before_first_signal():
    _, ref, _, _ = sample()
    signals = weekly_sma_signals(ref)
    assert len(signals) > 21
    assert (signals["direction"].iloc[:20] == 0).all()
    assert signals["sma21"].iloc[:20].isna().all()
    assert signals["sma21"].iloc[20:].notna().all()
    assert (signals["direction"].iloc[20:] == 1).all()


def test_no_execution_day_lookahead():
    _, ref, domestic, _ = sample()
    signal = weekly_sma_signals(ref)
    dates = domestic.index
    strategy = SMARegimeStrategy(signal, "KR_LONG")
    # Run via the actual Runtime, whose context contains current + historical ETF prices.
    from backtest_lab.core import Runtime
    result = Runtime(strategy, 10000.0, RuntimeConfig()).run(domestic.rename("KR_LONG").to_frame())
    assert result.fills
    for decision in strategy.decisions:
        assert decision["signal_date"] < decision["execution_date"]
    # Changing a Monday domestic execution price cannot change Friday signal.
    edited = domestic.copy()
    mondays = dates[dates.weekday == 0]
    edited.loc[mondays] *= 1.2
    other = SMARegimeStrategy(signal, "KR_LONG")
    Runtime(other, 10000.0, RuntimeConfig()).run(edited.rename("KR_LONG").to_frame())
    assert [(r["signal_date"], r["direction"]) for r in strategy.decisions] == [
        (r["signal_date"], r["direction"]) for r in other.decisions
    ]


def test_long_cash_and_inverse_separate_real_prices(tmp_path):
    _, ref, domestic, inverse = sample()
    item = AssetInput("gold", "금", ref, domestic, "KR_LONG", inverse, "KR_INV")
    result = run_asset(item, start="2016-01-01", end="2018-01-01",
                       config=RuntimeConfig(fee_rate=0.00015))
    assert list(result.performance_summary.columns) == list(SUMMARY_COLUMNS)
    assert set(result.performance_summary["strategy"]) == {
        "Long/Cash", "Buy & Hold", "Long/Inverse"
    }
    assert result.fills["symbol"].isin(["KR_LONG", "KR_INV"]).all()
    assert not result.signals.empty
    paths = write_asset_results([result], tmp_path)
    assert paths["performance_summary.csv"].exists()
    assert paths["gold/performance_summary.csv"].exists()
    summary = pd.read_csv(paths["performance_summary.csv"])
    assert list(summary.columns) == list(SUMMARY_COLUMNS)
    assert len(summary) == 1
    assert summary.iloc[0]["strategy"] == "금"


def test_missing_inverse_still_tests_asset():
    _, ref, domestic, _ = sample()
    result = run_asset(AssetInput("silver", "은", ref, domestic, "KR_LONG"),
                       start="2016-01-01", end="2018-01-01")
    assert set(result.performance_summary["strategy"]) == {"Long/Cash", "Buy & Hold"}


def test_short_window_fails_instead_of_inventing_returns():
    _, ref, domestic, _ = sample()
    with pytest.raises(ValueError, match="insufficient domestic"):
        run_asset(AssetInput("a", "A", ref, domestic, "LONG"),
                  start="2019-01-01", end="2020-01-01")
