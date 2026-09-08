from __future__ import annotations

import numpy as np
import pandas as pd

from backtest_lab.core import Runtime, RuntimeConfig
from backtest_lab.strategies.us_market_cap_leaders.evaluation import (
    QQQ_NAME,
    SPY_NAME,
    TOP1_NAME,
    TOP2_NAME,
    run_baseline,
    run_window_sensitivity,
)
from backtest_lab.strategies.us_market_cap_leaders.r01 import QuarterlyMarketCapLeaderStrategy


def make_rankings(dates: list[str], pairs: list[tuple[str, str]]) -> pd.DataFrame:
    rows = []
    for i, (date, pair) in enumerate(zip(dates, pairs, strict=True)):
        rows.append(
            {
                "ranking_date": pd.Timestamp(date),
                "rank1_company": pair[0],
                "rank1_ticker": pair[0],
                "rank1_market_cap_b": 1000.0 + i,
                "rank2_company": pair[1],
                "rank2_ticker": pair[1],
                "rank2_market_cap_b": 900.0 + i,
                "source_group": "test",
                "confidence": "high",
            }
        )
    return pd.DataFrame(rows)


def test_top1_uses_ranking_only_after_ranking_date() -> None:
    rankings = make_rankings(
        ["2020-03-31", "2020-06-30"],
        [("AAA", "BBB"), ("BBB", "AAA")],
    )
    prices = pd.DataFrame(
        {
            "AAA": [10.0, 10.0, 10.0, 10.0],
            "BBB": [20.0, 20.0, 20.0, 20.0],
        },
        index=pd.to_datetime(["2020-03-31", "2020-04-01", "2020-06-30", "2020-07-01"]),
    )
    strategy = QuarterlyMarketCapLeaderStrategy(top_n=1, rankings=rankings)
    result = Runtime(strategy, initial_cash=1000.0, config=RuntimeConfig()).run(prices, start="2020-03-31")

    assert [fill.timestamp for fill in result.fills] == [pd.Timestamp("2020-04-01"), pd.Timestamp("2020-07-01"), pd.Timestamp("2020-07-01")]
    assert result.fills[0].symbol == "AAA"
    assert result.fills[-1].symbol == "BBB"
    assert strategy.decisions[0]["ranking_date"] == pd.Timestamp("2020-03-31")
    assert strategy.decisions[0]["execution_date"] == pd.Timestamp("2020-04-01")


def test_top2_rebalances_to_equal_weights_each_quarter() -> None:
    rankings = make_rankings(
        ["2020-03-31", "2020-06-30"],
        [("AAA", "BBB"), ("AAA", "BBB")],
    )
    prices = pd.DataFrame(
        {
            "AAA": [10.0, 10.0, 15.0, 15.0],
            "BBB": [20.0, 20.0, 20.0, 20.0],
        },
        index=pd.to_datetime(["2020-03-31", "2020-04-01", "2020-06-30", "2020-07-01"]),
    )
    strategy = QuarterlyMarketCapLeaderStrategy(top_n=2, rankings=rankings)
    result = Runtime(strategy, initial_cash=1000.0, config=RuntimeConfig()).run(prices, start="2020-03-31")

    assert len(strategy.decisions) == 2
    final_prices = {"AAA": 15.0, "BBB": 20.0}
    total = result.portfolio.value(final_prices)
    aaa_value = result.portfolio.quantity("AAA") * final_prices["AAA"]
    bbb_value = result.portfolio.quantity("BBB") * final_prices["BBB"]
    assert abs(aaa_value / total - 0.5) < 1e-9
    assert abs(bbb_value / total - 0.5) < 1e-9


def test_baseline_compares_top1_top2_spy_and_qqq() -> None:
    rankings = make_rankings(["2020-03-31"], [("AAA", "BBB")])
    index = pd.date_range("2020-03-31", "2020-06-30", freq="B")
    prices = pd.DataFrame(
        {
            "AAA": np.linspace(100.0, 120.0, len(index)),
            "BBB": np.linspace(100.0, 110.0, len(index)),
            "SPY": np.linspace(100.0, 108.0, len(index)),
            "QQQ": np.linspace(100.0, 112.0, len(index)),
        },
        index=index,
    )
    outputs = run_baseline(prices, start="2020-04-01", config=RuntimeConfig(), rankings=rankings)

    assert set(outputs.performance_summary["strategy"]) == {TOP1_NAME, TOP2_NAME, SPY_NAME, QQQ_NAME}
    assert set(outputs.ffn_stats.columns) == {TOP1_NAME, TOP2_NAME, SPY_NAME, QQQ_NAME}
    assert set(outputs.quarterly_selections["strategy"]) == {TOP1_NAME, TOP2_NAME}


def test_window_sensitivity_generates_fixed_and_matrix_windows() -> None:
    ranking_dates = (
        pd.period_range("2010Q1", periods=22, freq="Q")
        .to_timestamp(how="end")
        .normalize()
        .strftime("%Y-%m-%d")
        .tolist()
    )
    pairs = [("AAA", "BBB") if i % 2 == 0 else ("BBB", "AAA") for i in range(len(ranking_dates))]
    rankings = make_rankings(ranking_dates, pairs)
    index = pd.date_range("2010-03-31", "2015-07-02", freq="B")
    base = np.arange(len(index), dtype=float)
    prices = pd.DataFrame(
        {
            "AAA": 100.0 + base * 0.04,
            "BBB": 100.0 + base * 0.03,
            "SPY": 100.0 + base * 0.02,
            "QQQ": 100.0 + base * 0.025,
        },
        index=index,
    )

    outputs = run_window_sensitivity(prices, start="2010-04-01", config=RuntimeConfig(), rankings=rankings)

    assert not outputs.window_performance.empty
    assert {3.0, 5.0}.issubset(set(outputs.window_performance["fixed_horizon_years"].dropna().astype(float)))
    assert outputs.window_performance["matrix_eligible"].any()
    assert set(outputs.rolling_summary["strategy"]) == {TOP1_NAME, TOP2_NAME}
    assert set(outputs.rolling_summary["benchmark"]) == {SPY_NAME, QQQ_NAME}
