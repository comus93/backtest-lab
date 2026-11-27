"""Synthetic, deterministic tests for independent weekly SMA research."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_lab.core import RuntimeConfig
from backtest_lab.strategies.multi_asset_weekly_sma.r01 import (
    AssetInput, SMARegimeStrategy, START, SUMMARY_COLUMNS, run_asset,
    daily_sma_signals, write_asset_results,
)


def sample(days=450):
    idx = pd.bdate_range("2015-11-02", periods=days)
    reference = pd.Series(np.linspace(100.0, 150.0, len(idx)), index=idx)
    domestic = pd.Series(np.linspace(1000.0, 1500.0, len(idx)), index=idx)
    inverse = pd.Series(np.linspace(150.0, 100.0, len(idx)), index=idx)
    return idx, reference, domestic, inverse


def test_105_completed_daily_closes_before_first_signal():
    _, ref, _, _ = sample()
    signals = daily_sma_signals(ref)
    assert len(signals) == len(ref)
    assert (signals["direction"].iloc[:104] == 0).all()
    assert signals["sma105"].iloc[:104].isna().all()
    assert signals["sma105"].iloc[104:].notna().all()
    assert (signals["direction"].iloc[104:] == 1).all()
    assert signals["sma105"].iloc[104] == pytest.approx(ref.iloc[:105].mean())
    assert signals["sma105"].iloc[105] == pytest.approx(ref.iloc[1:106].mean())


def test_intrawweek_cross_detected_daily_and_filled_next_session():
    from backtest_lab.core import Runtime
    dates = pd.bdate_range("2020-01-02", periods=115)
    values = np.full(115, 100.0)
    values[105:108] = [110.0, 90.0, 115.0]
    reference = pd.Series(values, index=dates)
    signals = daily_sma_signals(reference)
    assert signals["direction"].iloc[105:108].tolist() == [1, -1, 1]
    strategy = SMARegimeStrategy(signals, "GLD")
    actual = Runtime(strategy, 10000, RuntimeConfig()).run(
        reference.rename("GLD").to_frame()
    )
    # Three consecutive daily crosses (including midweek) cause three fills.
    early = actual.fills
    assert [(x.timestamp, x.side) for x in early[:3]] == [
        (dates[106], "buy"), (dates[107], "sell"), (dates[108], "buy")
    ]
    assert all(x["signal_date"] < x["execution_date"] for x in strategy.decisions)


def test_sma_uses_trade_count_not_calendar_days():
    dates = pd.bdate_range("2020-01-01", periods=130)
    dates = dates.delete([25, 26, 44, 67])  # holidays without synthetic prices
    prices = pd.Series(np.arange(100, 100 + len(dates)), index=dates, dtype=float)
    signals = daily_sma_signals(prices)
    assert signals["sma105"].first_valid_index() == dates[104]
    assert signals["sma105"].iloc[104] == pytest.approx(prices.iloc[:105].mean())
    with pytest.raises(ValueError, match="days must"):
        daily_sma_signals(prices, days=1)


def test_no_execution_day_lookahead():
    _, ref, domestic, _ = sample()
    signal = daily_sma_signals(ref)
    dates = domestic.index
    strategy = SMARegimeStrategy(signal, "KR_LONG")
    # Run via the actual Runtime, whose context contains current + historical ETF prices.
    from backtest_lab.core import Runtime
    result = Runtime(strategy, 10000.0, RuntimeConfig()).run(domestic.rename("KR_LONG").to_frame())
    assert result.fills
    for decision in strategy.decisions:
        assert decision["signal_date"] < decision["execution_date"]
    # Changing the execution price does not alter the separate prior-day reference signal.
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
        "Long/Cash", "Inverse/Cash", "Long/Inverse", "LineBreak Long/Cash", "LineBreak Long/Inverse", "Buy & Hold"
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
    assert set(result.performance_summary["strategy"]) == {"Long/Cash", "LineBreak Long/Cash", "Buy & Hold"}


def test_short_window_fails_instead_of_inventing_returns():
    _, ref, domestic, _ = sample()
    with pytest.raises(ValueError, match="insufficient domestic"):
        run_asset(AssetInput("a", "A", ref, domestic, "LONG"),
                  start="2019-01-01", end="2020-01-01")


def test_monthly_returns_and_benchmark_last():
    """Months reproduce annual FFN returns and the full-period total."""
    _, reference, domestic, inverse = sample()
    result = run_asset(AssetInput("gold", "금", reference, domestic, "GLD",
                                  inverse, "GLL"),
                       start="2016-01-01", end="2018-01-01")
    expected = ["Long/Cash", "Inverse/Cash", "Long/Inverse", "LineBreak Long/Cash", "LineBreak Long/Inverse", "Buy & Hold"]
    assert result.performance_summary["strategy"].tolist() == expected
    assert result.curves.columns.tolist() == expected
    assert result.ffn_stats.columns.tolist() == expected
    assert result.yearly_performance["strategy"].drop_duplicates().tolist() == expected
    assert result.monthly_performance["strategy"].drop_duplicates().tolist() == expected
    assert result.monthly_performance.columns.tolist() == ["strategy", "month", "return"]
    for strategy in expected:
        months = result.monthly_performance.loc[result.monthly_performance["strategy"] == strategy]
        assert months["month"].is_unique
        assert months["month"].is_monotonic_increasing
        total = result.performance_summary.set_index("strategy").loc[strategy, "total_return"]
        assert float((1 + months["return"]).prod() - 1) == pytest.approx(total)
        years = result.yearly_performance.loc[result.yearly_performance["strategy"] == strategy]
        for _, year in years.iterrows():
            selected = months.loc[months["month"].str[:4] == str(int(year["year"]))]
            assert float((1 + selected["return"]).prod() - 1) == pytest.approx(year["return"])


def test_no_inverse_benchmark_still_last():
    _, ref, domestic, _ = sample()
    result = run_asset(AssetInput("silver", "은", ref, domestic, "SLV"),
                       start="2016-01-01", end="2018-01-01")
    assert result.performance_summary["strategy"].tolist() == ["Long/Cash", "LineBreak Long/Cash", "Buy & Hold"]
    assert result.monthly_performance["strategy"].drop_duplicates().tolist() == [
        "Long/Cash", "LineBreak Long/Cash", "Buy & Hold"
    ]


def test_inverse_cash_only_owns_actual_inverse_on_bearish_days():
    from backtest_lab.core import Runtime
    dates = pd.bdate_range("2019-01-01", periods=130)
    values = np.full(len(dates), 100.0)
    values[105:111] = [110.0, 90.0, 95.0, 112.0, 108.0, 90.0]
    reference = pd.Series(values, index=dates)
    inverse = pd.Series(200.0 - 0.5*np.arange(len(dates)), index=dates)
    signals = daily_sma_signals(reference)
    assert signals.direction.iloc[105:111].tolist() == [1, -1, -1, 1, 1, -1]
    strategy = SMARegimeStrategy(signals, "GLD", "GLL", inverse_only=True)
    prices = pd.DataFrame({"GLD": reference, "GLL": inverse})
    result = Runtime(strategy, 10000, RuntimeConfig()).run(prices)
    assert result.fills
    assert all(fill.symbol == "GLL" for fill in result.fills)
    assert [(fill.timestamp, fill.side) for fill in result.fills[:3]] == [
        (dates[107], "buy"), (dates[109], "sell"), (dates[111], "buy")
    ]
    assert all(r["held_etf"] == "CASH" for r in strategy.decisions if r["direction"] >= 0)
    assert all(r["held_etf"] == "GLL" for r in strategy.decisions if r["direction"] < 0)
    assert all(r["signal_date"] < r["execution_date"] for r in strategy.decisions)


def test_inverse_only_monthly_and_yearly_reconcile():
    _, ref, long, inverse = sample()
    ref.iloc[150:190] *= .75  # controlled bearish window for inverse-only trades
    result = run_asset(AssetInput("gold", "금", ref, long, "GLD", inverse, "GLL"),
                       start="2016-01-01", end="2018-01-01")
    assert result.performance_summary.strategy.tolist() == [
        "Long/Cash", "Inverse/Cash", "Long/Inverse", "LineBreak Long/Cash", "LineBreak Long/Inverse", "Buy & Hold"
    ]
    only = result.fills.loc[result.fills.strategy == "Inverse/Cash"]
    assert not only.empty
    assert set(only.symbol) == {"GLL"}
    expected = result.performance_summary.set_index("strategy").loc["Inverse/Cash","total_return"]
    months = result.monthly_performance.loc[result.monthly_performance.strategy == "Inverse/Cash"]
    years = result.yearly_performance.loc[result.yearly_performance.strategy == "Inverse/Cash"]
    assert (1+months["return"]).prod()-1 == pytest.approx(expected)
    assert (1+years["return"]).prod()-1 == pytest.approx(expected)


def test_inverse_cash_requires_real_inverse_symbol():
    _, ref, _, _ = sample()
    with pytest.raises(ValueError, match="requires an actual inverse ETF"):
        SMARegimeStrategy(daily_sma_signals(ref), "GLD", inverse_only=True)
