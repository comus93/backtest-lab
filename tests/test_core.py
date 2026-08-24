import pandas as pd
import pytest

from backtest_lab.core import BacktestError, Order, Runtime, RuntimeConfig
from backtest_lab.strategies import MonthlyTargetWeightStrategy


class BuyOnceStrategy:
    def __init__(self, symbol: str, quantity: float) -> None:
        self.symbol = symbol
        self.quantity = quantity
        self.called = False

    def on_step(self, context):
        if self.called:
            return []
        self.called = True
        return [Order(self.symbol, "buy", self.quantity)]


class FlowOnlyStrategy:
    def on_step(self, context):
        return []


class RoundTripStrategy:
    def __init__(self) -> None:
        self.step = 0

    def on_step(self, context):
        self.step += 1
        if self.step == 1:
            return [Order("AAA", "buy", 3), Order("AAA", "buy", 2)]
        if self.step == 2:
            return [Order("AAA", "sell", 1.5)]
        return []


class HistoryRecordingStrategy:
    def __init__(self) -> None:
        self.contexts = []

    def on_step(self, context):
        self.contexts.append(context)
        return []


def test_external_cash_flow_does_not_raise_performance() -> None:
    prices = pd.DataFrame({"AAA": [100.0, 100.0]}, index=pd.to_datetime(["2024-01-01", "2024-01-02"]))
    result = Runtime(FlowOnlyStrategy(), initial_cash=1_000).run(
        prices,
        external_cash_flows={pd.Timestamp("2024-01-02"): 500},
    )
    assert result.equity.iloc[-1] == pytest.approx(1_500)
    assert result.performance.iloc[-1] == pytest.approx(100)


def test_price_increase_raises_performance() -> None:
    prices = pd.DataFrame({"AAA": [100.0, 110.0]}, index=pd.to_datetime(["2024-01-01", "2024-01-02"]))
    result = Runtime(BuyOnceStrategy("AAA", 10), initial_cash=1_000).run(prices)
    assert result.performance.iloc[-1] == pytest.approx(110)


def test_fee_lowers_performance_and_first_step_cost_is_included() -> None:
    prices = pd.DataFrame({"AAA": [100.0, 100.0]}, index=pd.to_datetime(["2024-01-01", "2024-01-02"]))
    no_fee = Runtime(BuyOnceStrategy("AAA", 10), initial_cash=1_000).run(prices)
    with_fee = Runtime(
        BuyOnceStrategy("AAA", 10),
        initial_cash=1_000,
        config=RuntimeConfig(fee_rate=0.01),
    ).run(prices)
    assert no_fee.performance.iloc[0] == 100
    assert no_fee.performance.iloc[1] == 100
    assert with_fee.performance.iloc[1] < no_fee.performance.iloc[1]
    assert with_fee.performance.iloc[-1] == pytest.approx(99.00990099009901)


def test_slippage_changes_fill_price_and_cash() -> None:
    prices = pd.DataFrame({"AAA": [100.0]}, index=pd.to_datetime(["2024-01-01"]))
    result = Runtime(
        BuyOnceStrategy("AAA", 5),
        initial_cash=1_000,
        config=RuntimeConfig(slippage_bps=100),
    ).run(prices)
    assert result.fills[0].reference_price == pytest.approx(100)
    assert result.fills[0].fill_price == pytest.approx(101)
    assert result.portfolio.cash == pytest.approx(495)
    assert result.performance.iloc[-1] == pytest.approx(99.5)


def test_repeated_symbol_trades_keep_aggregate_quantity_and_fills_match() -> None:
    prices = pd.DataFrame({"AAA": [100.0, 100.0, 100.0]}, index=pd.date_range("2024-01-01", periods=3))
    result = Runtime(RoundTripStrategy(), initial_cash=1_000).run(prices)
    assert len(result.fills) == 3
    assert result.portfolio.quantity("AAA") == pytest.approx(3.5)
    position_value = result.portfolio.quantity("AAA") * 100
    assert result.portfolio.cash + position_value == pytest.approx(result.equity.iloc[-1])


def test_monthly_strategy_rebalances_once_per_month() -> None:
    prices = pd.DataFrame(
        {"AAA": [100.0, 120.0, 121.0], "BBB": [100.0, 80.0, 79.0]},
        index=pd.to_datetime(["2024-01-31", "2024-02-01", "2024-02-02"]),
    )
    strategy = MonthlyTargetWeightStrategy({"AAA": 0.7, "BBB": 0.3})
    result = Runtime(strategy, initial_cash=1_000).run(prices)
    assert len(result.fills) == 4
    assert result.fills[0].symbol == "AAA"
    assert result.fills[1].symbol == "BBB"
    assert result.fills[2].side == "sell"
    assert result.fills[3].side == "buy"


def test_intraday_index_uses_same_runtime_structure() -> None:
    prices = pd.DataFrame(
        {"AAA": [100.0, 101.0]},
        index=pd.to_datetime(["2024-01-01 09:00", "2024-01-01 09:05"]),
    )
    result = Runtime(BuyOnceStrategy("AAA", 1), initial_cash=1_000).run(prices)
    assert result.performance.index[0] == pd.Timestamp("2024-01-01 08:55")
    assert result.performance.iloc[-1] > 100


def test_runtime_can_only_run_once() -> None:
    prices = pd.DataFrame({"AAA": [100.0]}, index=pd.to_datetime(["2024-01-01"]))
    runtime = Runtime(FlowOnlyStrategy(), initial_cash=1_000)
    runtime.run(prices)

    with pytest.raises(BacktestError, match="only be run once"):
        runtime.run(prices)


def test_strategy_history_excludes_future_prices() -> None:
    prices = pd.DataFrame(
        {"AAA": [100.0, 101.0, 102.0]},
        index=pd.date_range("2024-01-01", periods=3),
    )
    strategy = HistoryRecordingStrategy()

    Runtime(strategy, initial_cash=1_000).run(prices)

    assert [len(context.history) for context in strategy.contexts] == [1, 2, 3]
    assert all(context.history.index.max() <= context.timestamp for context in strategy.contexts)


def test_warmup_rows_are_history_only_and_performance_starts_at_active_step() -> None:
    prices = pd.DataFrame(
        {"AAA": [100.0, 101.0, 102.0, 103.0]},
        index=pd.date_range("2024-01-01", periods=4),
    )
    strategy = HistoryRecordingStrategy()

    result = Runtime(strategy, initial_cash=1_000).run(prices, start="2024-01-03")

    assert [context.timestamp for context in strategy.contexts] == [
        pd.Timestamp("2024-01-03"),
        pd.Timestamp("2024-01-04"),
    ]
    assert [len(context.history) for context in strategy.contexts] == [3, 4]
    assert result.equity.index.tolist() == [pd.Timestamp("2024-01-03"), pd.Timestamp("2024-01-04")]
    assert result.performance.index[0] == pd.Timestamp("2024-01-02")
    assert result.performance.iloc[0] == pytest.approx(100)
