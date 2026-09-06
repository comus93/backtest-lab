from __future__ import annotations

import pandas as pd

from backtest_lab.core import PortfolioSnapshot, RuntimeConfig, StrategyContext
from backtest_lab.strategies.sp500_top2_market_cap.r01 import (
    AnnualTop2MarketCapStrategy,
    TOP2_BY_YEAR,
    run_pilot,
)


def make_context(date: str, positions: dict[str, float] | None = None) -> StrategyContext:
    timestamp = pd.Timestamp(date)
    prices = {"AAPL": 100.0, "GOOGL": 100.0, "MSFT": 100.0, "NVDA": 100.0, "SPY": 100.0}
    history = pd.DataFrame([prices], index=[timestamp])
    return StrategyContext(
        timestamp=timestamp,
        prices=prices,
        history=history,
        portfolio=PortfolioSnapshot(cash=1_000_000.0, positions=positions or {}),
    )


def make_prices() -> pd.DataFrame:
    index = pd.bdate_range("2016-01-04", "2025-12-31")
    base = pd.Series(range(len(index)), index=index, dtype=float)
    return pd.DataFrame(
        {
            "AAPL": 25.0 + base * 0.06,
            "GOOGL": 35.0 + base * 0.05,
            "MSFT": 45.0 + base * 0.07,
            "NVDA": 5.0 + base * 0.08,
            "SPY": 180.0 + base * 0.04,
        },
        index=index,
    )


def test_fixed_selections_cover_ten_years() -> None:
    assert list(TOP2_BY_YEAR) == list(range(2016, 2026))
    assert TOP2_BY_YEAR[2016] == ("AAPL", "GOOGL")
    assert TOP2_BY_YEAR[2019] == ("MSFT", "AAPL")
    assert TOP2_BY_YEAR[2025] == ("AAPL", "NVDA")


def test_first_2016_step_targets_apple_and_alphabet() -> None:
    strategy = AnnualTop2MarketCapStrategy()
    orders = strategy.on_step(make_context("2016-01-04"))
    assert {(order.symbol, order.side) for order in orders} == {("AAPL", "buy"), ("GOOGL", "buy")}
    assert len(strategy.decisions) == 1
    assert strategy.decisions[0]["ranking_basis_year"] == 2015


def test_second_step_same_year_does_not_rebalance() -> None:
    strategy = AnnualTop2MarketCapStrategy()
    strategy.on_step(make_context("2016-01-04"))
    assert strategy.on_step(make_context("2016-01-05")) == []


def test_2019_switches_to_microsoft_and_apple() -> None:
    strategy = AnnualTop2MarketCapStrategy()
    orders = strategy.on_step(make_context("2019-01-02"))
    assert {order.symbol for order in orders} == {"AAPL", "MSFT"}


def test_2025_switches_to_apple_and_nvidia() -> None:
    strategy = AnnualTop2MarketCapStrategy()
    orders = strategy.on_step(make_context("2025-01-02"))
    assert {order.symbol for order in orders} == {"AAPL", "NVDA"}


def test_run_pilot_contains_strategy_and_spy_outputs() -> None:
    prices = make_prices()
    outputs = run_pilot(prices, start=prices.index[0], config=RuntimeConfig(fee_rate=0.0))

    assert set(outputs.performance_summary["strategy"]) == {
        "S&P 500 Top-2 Market Cap",
        "SPY Buy & Hold",
    }
    assert set(outputs.ffn_stats.columns) == {
        "S&P 500 Top-2 Market Cap",
        "SPY Buy & Hold",
    }
    assert len(outputs.annual_selections) == 10
    assert set(outputs.yearly_performance["year"]) == set(range(2016, 2026))
