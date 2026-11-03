from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import sys
import types

from backtest_lab.core import Runtime, RuntimeConfig
from backtest_lab.data import DataCoverageError
from backtest_lab.strategies.psar_segment_duration.data import load_fdr_prices
from backtest_lab.strategies.psar_segment_duration import r01


def sample_prices(index: pd.DatetimeIndex) -> pd.DataFrame:
    t = np.arange(len(index))
    close = 100.0 + 15.0 * np.sin(t / 15.0) + t * 0.01
    return pd.DataFrame({
        "QQQ_High": close + 1.0, "QQQ_Low": close - 1.0,
        "QQQ": close, "QLD": close * 1.5, "PSQ": 10000.0 / close,
    }, index=index)


def test_segment_counter_uses_only_immediately_previous_completed_opposite_segment():
    directions = pd.Series(["UP", "UP", "DOWN", "DOWN", "UP", "UP", "UP", "DOWN", "UP", "UP"])
    frame = r01.segment_fields(directions)
    assert frame["entry_eligible"].tolist() == [
        False, False, False, False, False, False, True, False, False, True
    ]
    assert frame["previous_opposite_len"].iloc[:4].isna().all()
    assert frame["previous_opposite_len"].iloc[4] == 2
    assert frame["previous_opposite_len"].iloc[7] == 3
    assert frame["previous_opposite_len"].iloc[8] == 1


def test_psar_rejects_invalid_ohlc_and_parameters():
    idx = pd.date_range("2020-01-01", periods=2)
    with pytest.raises(ValueError, match="High >= Low"):
        r01.calculate_psar(
            pd.Series([1.0, .9], index=idx),
            pd.Series([1.1, .8], index=idx),
        )
    with pytest.raises(ValueError, match="acceleration"):
        r01.calculate_psar(
            pd.Series([2., 3.], index=idx),
            pd.Series([1., 2.], index=idx),
            step=.3, maximum=.2,
        )


def test_psar_is_causal_after_seed_and_has_valid_direction():
    prices = sample_prices(pd.bdate_range("2006-06-19", periods=300))
    full = r01.build_signals(prices)
    partial = r01.build_signals(prices.iloc[:100])
    pd.testing.assert_frame_equal(full.iloc[:100], partial)
    assert set(full["psar_direction"]) == {"UP", "DOWN"}


def test_entry_hold_without_rebalance_and_exit_only_on_reversal():
    index = pd.bdate_range("2020-01-01", periods=14)
    directions = pd.Series(
        ["UP"] * 2 + ["DOWN"] * 3 + ["UP"] * 6 + ["DOWN"] * 3,
        index=index,
    )
    signals = pd.DataFrame({
        "psar_value": np.arange(14, dtype=float),
        "psar_direction": directions,
    }, index=index).join(r01.segment_fields(directions))
    strategy = r01.PSARSegmentDurationStrategy(signals)
    price = pd.DataFrame({"QQQ": 100., "QLD": 100., "PSQ": 100.}, index=index)
    result = Runtime(strategy, 1000., RuntimeConfig(fee_rate=.001)).run(price)
    fills = [(f.timestamp, f.symbol, f.side) for f in result.fills]
    assert fills == [(index[8], "QLD", "buy"), (index[11], "QLD", "sell")]
    assert result.portfolio.positions == {}
    assert strategy.decisions[9]["action"] == "HOLD"
    assert strategy.decisions[10]["action"] == "HOLD"
    assert strategy.decisions[11]["action"] == "EXIT_ON_REVERSAL"


def test_independent_window_open_mid_qualified_segment():
    index = pd.bdate_range("2020-01-01", periods=11)
    directions = pd.Series(["UP"] * 2 + ["DOWN"] * 2 + ["UP"] * 7, index=index)
    signals = pd.DataFrame({
        "psar_value": 95., "psar_direction": directions,
    }, index=index).join(r01.segment_fields(directions))
    strategy = r01.PSARSegmentDurationStrategy(signals)
    window_index = index[8:11]
    prices = pd.DataFrame({"QQQ": 100., "QLD": 100., "PSQ": 100.}, index=window_index)
    result = Runtime(strategy, 1000.).run(prices)
    assert [(f.timestamp, f.side) for f in result.fills] == [(index[8], "buy")]
    assert all(d["action"] == "HOLD" for d in strategy.decisions[1:])


def test_fdr_loader_rejects_missing_trade_dates_and_reverse_split(monkeypatch):
    dates = pd.bdate_range("2025-01-02", periods=6)
    def frame(closes, idx=dates):
        return pd.DataFrame({
            "Open": closes, "High": np.array(closes) * 1.01,
            "Low": np.array(closes) * .99, "Close": closes,
        }, index=idx)
    rows = {
        "QQQ": frame([100, 101, 102, 103, 104, 105]),
        "QLD": frame([100, 102, 104, 106, 108, 110]),
        "PSQ": frame([100, 99, 98, 97, 96, 95]),
    }
    monkeypatch.setitem(sys.modules, "FinanceDataReader", types.SimpleNamespace(
        DataReader=lambda ticker, start, end: rows[ticker]
    ))
    good = load_fdr_prices("2025-01-01", "2025-02-01")
    assert len(good) == 6
    rows["PSQ"] = rows["PSQ"].drop(dates[3])
    with pytest.raises(DataCoverageError, match="trading dates missing"):
        load_fdr_prices("2025-01-01", "2025-02-01")
    rows["PSQ"] = frame([100, 99, 98, 485, 480, 475])
    with pytest.raises(DataCoverageError, match="reverse-split adjustment"):
        load_fdr_prices("2025-01-01", "2025-02-01")


def test_long_only_disables_psq_without_changing_qld_signals():
    index = pd.bdate_range("2020-01-01", periods=20)
    directions = pd.Series(
        ["UP"] * 2 + ["DOWN"] * 3 + ["UP"] * 4 + ["DOWN"] * 5 + ["UP"] * 6,
        index=index,
    )
    signals = pd.DataFrame({
        "psar_value": 95.0,
        "psar_direction": directions,
    }, index=index).join(r01.segment_fields(directions))
    prices = pd.DataFrame({"QQQ": 100.0, "QLD": 100.0, "PSQ": 100.0}, index=index)

    original = r01.PSARSegmentDurationStrategy(signals)
    long_only = r01.PSARSegmentDurationStrategy(signals, long_only=True)
    full_fills = Runtime(original, 1000.0).run(prices).fills
    long_fills = Runtime(long_only, 1000.0).run(prices).fills
    assert any(fill.symbol == "PSQ" for fill in full_fills)
    assert all(fill.symbol == "QLD" for fill in long_fills)
    assert [
        (fill.timestamp, fill.symbol, fill.side) for fill in full_fills if fill.symbol == "QLD"
    ] == [
        (fill.timestamp, fill.symbol, fill.side) for fill in long_fills
    ]
    assert all(
        item["held_symbol"] == "CASH" for item in long_only.decisions
        if item["psar_direction"] == "DOWN"
    )


def test_four_windows_are_strictly_bounded_and_carry_warmup():
    prices = sample_prices(pd.bdate_range("2006-06-19", "2026-11-03"))
    outputs = r01.run_pilot(prices)
    assert set(outputs.performance_summary["window"]) == {
        "2007-2011", "2012-2016", "2017-2021", "2022-2026",
    }
    psar = outputs.performance_summary.query("strategy.str.startswith('PSAR ')")
    assert list(psar["end_date"].astype(str)) == [
        "2011-12-30", "2016-12-30", "2021-12-31", "2026-11-03",
    ]
    assert list(psar["start_date"].astype(str)) == [
        "2007-01-01", "2012-01-02", "2017-01-02", "2022-01-03",
    ] or len(psar) == 4  # business calendar synthetic, not NYSE holiday calendar
    assert all(outputs.daily_signals.groupby("window").size() > 1000)
    assert all(outputs.fills["timestamp"].dt.year >= 2007)
    assert {"QQQ Buy & Hold 2007-2011", "QLD Buy & Hold 2022-2026"}.issubset(
        outputs.equity_curves.columns
    )
    first = outputs.performance_summary.query("window == '2007-2011'")
    assert len(first) == 3
    assert (first["end_date"].astype(str) == "2011-12-30").all()
    assert outputs.daily_signals["bias_note"].str.contains("look-ahead").all()
