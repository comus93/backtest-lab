"""Daily close 3-Line Break directional/trading tests.

A no-new-line session inherits the previous confirmed direction, and a new
opposite line needs to break three *line* extremes, not last three daily bars.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtest_lab.core import Runtime, RuntimeConfig
from backtest_lab.strategies.multi_asset_weekly_sma.line_break import daily_line_break_signals
from backtest_lab.strategies.multi_asset_weekly_sma.r01 import (
    AssetInput, SMARegimeStrategy, run_asset, STRATEGY_ORDER
)


def test_confirmed_lines_not_last_three_calendar_days_and_hold_direction():
    dates = pd.bdate_range("2020-01-01", periods=10)
    close = pd.Series([100, 101, 102, 103, 102.5, 100.5, 99, 98, 99.5, 103.1],
                      index=dates, dtype=float)
    result = daily_line_break_signals(close)
    assert result.direction.tolist() == [0, 1, 1, 1, 1, 1, -1, -1, -1, 1]
    assert result.line_formed.tolist() == [
        False, True, True, True, False, False, True, True, False, True
    ]
    assert result.reversal.tolist() == [
        False, False, False, False, False, False, True, False, False, True
    ]
    assert result.loc[dates[6], "prior_line_low"] == 100
    assert result.loc[dates[6], "line_open"] == 102
    assert result.loc[dates[6], "line_close"] == 99
    assert result.loc[dates[9], "prior_line_high"] == 103
    assert result.loc[dates[9], "line_open"] == 99
    assert result.loc[dates[9], "line_close"] == 103.1
    # 102.5, 100.5 and 99.5 are no-new-line sessions.
    assert (result.loc[[dates[4], dates[5], dates[8]], "line_formed"] == False).all()


def test_nonrepainting_daily_input_and_three_line_parameter():
    dates = pd.bdate_range("2020-01-01", periods=21).delete([5, 9]) # no synthetic weekends/holidays
    close = pd.Series([100, 101, 102, 103, 102.5, 100.5, 99, 98, 99.5, 103.1,
                       104, 105, 103, 101, 106, 107, 108, 104, 109],
                      index=dates, dtype=float)
    past = daily_line_break_signals(close.iloc[:15])
    whole = daily_line_break_signals(close)
    pd.testing.assert_frame_equal(past, whole.iloc[:15])
    assert whole.index.equals(dates)
    assert whole.index.is_unique
    with pytest.raises(ValueError, match="integer >= 2"):
        daily_line_break_signals(close, 1)
    with pytest.raises(ValueError, match="integer >= 2"):
        daily_line_break_signals(close, 3.0)
    with pytest.raises(ValueError, match="finite and positive"):
        daily_line_break_signals(close * 0)
    with pytest.raises(ValueError, match="unique dates"):
        daily_line_break_signals(pd.concat([close, close.iloc[-1:]]))


def test_confirmed_line_reversal_fills_next_day_not_today():
    dates = pd.bdate_range("2020-01-01", periods=11)
    close = pd.Series([100, 101, 102, 103, 102.5, 100.5, 99, 98, 99.5, 103.1, 105],
                      index=dates, dtype=float)
    signals = daily_line_break_signals(close)
    inverse = pd.Series(np.linspace(200, 180, len(dates)), index=dates)
    mode = SMARegimeStrategy(signals, "GLD", "GLL")
    out = Runtime(mode, 100_000, RuntimeConfig()).run(
        pd.DataFrame({"GLD": close, "GLL": inverse})
    )
    assert [(x.timestamp, x.symbol, x.side) for x in out.fills[:5]] == [
        (dates[2], "GLD", "buy"), (dates[7], "GLD", "sell"),
        (dates[7], "GLL", "buy"), (dates[10], "GLL", "sell"),
        (dates[10], "GLD", "buy"),
    ]
    assert all(x["signal_date"] < x["execution_date"] for x in mode.decisions)
    assert sum(x["changed_position"] for x in mode.decisions) == 3
    assert sum(x["line_break_reversal"] for x in mode.decisions) == 2


def test_line_break_only_for_real_inverse_and_ffn_monthly_reconcile(tmp_path):
    dates = pd.bdate_range("2015-01-01", periods=600)
    # Contains both rising and falling trends, plus sideways noise.
    price = pd.Series(100 + 20*np.sin(np.arange(len(dates)) / 16)
                      + np.arange(len(dates)) * .035, index=dates)
    inverse = pd.Series(150 + 25*np.sin(np.arange(len(dates)) / 15 + 2),
                        index=dates)
    pair = AssetInput("gold", "금", price, price, "GLD", inverse, "GLL")
    result = run_asset(pair, start="2016-01-01", end="2018-01-01")
    assert list(result.performance_summary.strategy) == list(STRATEGY_ORDER)
    assert result.ffn_stats.columns.tolist() == list(STRATEGY_ORDER)
    assert result.curves.columns.tolist() == list(STRATEGY_ORDER)
    assert result.monthly_performance.strategy.drop_duplicates().tolist() == list(STRATEGY_ORDER)
    assert result.yearly_performance.strategy.drop_duplicates().tolist() == list(STRATEGY_ORDER)
    assert (result.line_break_signals.index < dates[-1]).any()
    assert result.line_break_signals.reversal.any()
    fills = result.fills.loc[result.fills.strategy=="LineBreak Long/Inverse"]
    assert set(fills.symbol) == {"GLD", "GLL"}
    assert not fills.empty
    decisions = result.signals[result.signals.strategy=="LineBreak Long/Inverse"]
    assert not decisions.empty
    assert (pd.to_datetime(decisions.signal_date) < pd.to_datetime(decisions.execution_date)).all()
    summary = result.performance_summary.set_index("strategy")
    for strategy in STRATEGY_ORDER:
        y=result.yearly_performance.loc[result.yearly_performance.strategy==strategy]
        m=result.monthly_performance.loc[result.monthly_performance.strategy==strategy]
        assert (1+y["return"]).prod()-1 == pytest.approx(summary.loc[strategy, "total_return"])
        assert (1+m["return"]).prod()-1 == pytest.approx(summary.loc[strategy, "total_return"])

    no_inv=run_asset(AssetInput("copper","구리",price,price,"CPER"),
                     start="2016-01-01",end="2018-01-01")
    assert no_inv.performance_summary.strategy.tolist()==["Long/Cash","Buy & Hold"]
    assert "LineBreak Long/Inverse" not in no_inv.monthly_performance.strategy.to_list()
