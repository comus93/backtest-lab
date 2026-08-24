import pandas as pd
import pytest

from backtest_lab.analysis import average_monthly_turnover, monthly_turnover_series
from backtest_lab.core import Order, Runtime


class BuyAndHold:
    def __init__(self, symbol="AAA", quantity=10.0):
        self.symbol = symbol
        self.quantity = quantity
        self.step = 0

    def on_step(self, context):
        if self.step == 0:
            self.step += 1
            return [Order(self.symbol, "buy", self.quantity)]
        self.step += 1
        return []


class TransferAfterInitialBuild:
    def __init__(self, second_step_prices=False):
        self.step = 0
        self.second_step_prices = second_step_prices

    def on_step(self, context):
        self.step += 1
        if self.step == 1:
            return [Order("AAA", "buy", 10)]
        if self.step == 2:
            return [Order("AAA", "sell", 1), Order("BBB", "buy", 1)]
        return []


def prices(index, aaa, bbb=None):
    return pd.DataFrame(
        {"AAA": aaa, "BBB": bbb or [100.0] * len(index)},
        index=pd.to_datetime(index),
    )


def test_buy_and_hold_initial_build_is_excluded_from_turnover() -> None:
    result = Runtime(BuyAndHold(), initial_cash=1_000).run(
        prices(["2024-01-01", "2024-02-01", "2024-03-01"], [100.0, 100.0, 100.0])
    )

    assert average_monthly_turnover(result) == pytest.approx(0.0)


def test_zero_trade_months_are_included_in_average() -> None:
    result = Runtime(TransferAfterInitialBuild(), initial_cash=1_000).run(
        prices(["2024-01-01", "2024-02-01", "2024-03-01"], [100.0, 100.0, 100.0])
    )
    series = monthly_turnover_series(result)

    assert list(series.index.astype(str)) == ["2024-01", "2024-02", "2024-03"]
    assert series.loc["2024-01"] == pytest.approx(0.0)
    assert series.loc["2024-02"] == pytest.approx(0.1)
    assert series.loc["2024-03"] == pytest.approx(0.0)
    assert average_monthly_turnover(result) == pytest.approx(0.1 / 3)


def test_equal_nav_ten_percent_transfer_is_ten_percent_turnover() -> None:
    result = Runtime(TransferAfterInitialBuild(), initial_cash=1_000).run(
        prices(["2024-01-01", "2024-02-01"], [100.0, 100.0])
    )

    assert monthly_turnover_series(result).loc["2024-02"] == pytest.approx(0.1)


def test_monthly_average_nav_is_used_instead_of_initial_cash() -> None:
    result = Runtime(TransferAfterInitialBuild(), initial_cash=1_000).run(
        prices(["2024-01-01", "2024-02-01"], [100.0, 200.0], [100.0, 200.0])
    )

    assert result.equity.loc["2024-02-01"] == pytest.approx(2_000.0)
    assert monthly_turnover_series(result).loc["2024-02"] == pytest.approx(0.1)


def test_external_cash_flow_does_not_create_turnover() -> None:
    result = Runtime(BuyAndHold(), initial_cash=1_000).run(
        prices(["2024-01-01", "2024-02-01"], [100.0, 100.0]),
        external_cash_flows={pd.Timestamp("2024-02-01"): 500.0},
    )

    assert average_monthly_turnover(result) == pytest.approx(0.0)
