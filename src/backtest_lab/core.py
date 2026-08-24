from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

import pandas as pd


class BacktestError(Exception):
    pass


class InsufficientCashError(BacktestError):
    pass


class InsufficientPositionError(BacktestError):
    pass


@dataclass(frozen=True)
class Order:
    symbol: str
    side: str
    quantity: float

    def __post_init__(self) -> None:
        side = self.side.lower()
        if side not in {"buy", "sell"}:
            raise ValueError("Order side must be 'buy' or 'sell'.")
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive.")
        object.__setattr__(self, "side", side)


@dataclass(frozen=True)
class Fill:
    timestamp: pd.Timestamp
    symbol: str
    side: str
    quantity: float
    reference_price: float
    fill_price: float
    fee: float


@dataclass
class Portfolio:
    cash: float
    positions: dict[str, float] = field(default_factory=dict)

    def quantity(self, symbol: str) -> float:
        return self.positions.get(symbol, 0.0)

    def apply_fill(self, fill: Fill) -> None:
        notional = fill.fill_price * fill.quantity
        if fill.side == "buy":
            self.cash -= notional + fill.fee
            self.positions[fill.symbol] = self.quantity(fill.symbol) + fill.quantity
        elif fill.side == "sell":
            current = self.quantity(fill.symbol)
            if fill.quantity > current + 1e-9:
                raise InsufficientPositionError(
                    f"Cannot sell {fill.quantity} of {fill.symbol}; only {current} held."
                )
            self.cash += notional - fill.fee
            next_quantity = current - fill.quantity
            if abs(next_quantity) < 1e-9:
                self.positions.pop(fill.symbol, None)
            else:
                self.positions[fill.symbol] = next_quantity
        else:
            raise ValueError(f"Unsupported fill side: {fill.side}")

    def apply_cash_flow(self, amount: float) -> None:
        self.cash += amount

    def value(self, prices: Mapping[str, float]) -> float:
        missing = [symbol for symbol in self.positions if symbol not in prices]
        if missing:
            raise KeyError(f"Missing prices for positions: {missing}")
        return self.cash + sum(quantity * prices[symbol] for symbol, quantity in self.positions.items())

    def snapshot(self) -> "PortfolioSnapshot":
        return PortfolioSnapshot(cash=self.cash, positions=dict(self.positions))


@dataclass(frozen=True)
class PortfolioSnapshot:
    cash: float
    positions: dict[str, float]

    def quantity(self, symbol: str) -> float:
        return self.positions.get(symbol, 0.0)

    def value(self, prices: Mapping[str, float]) -> float:
        return self.cash + sum(quantity * prices[symbol] for symbol, quantity in self.positions.items())


@dataclass(frozen=True)
class StrategyContext:
    timestamp: pd.Timestamp
    prices: Mapping[str, float]
    history: pd.DataFrame
    portfolio: PortfolioSnapshot


class Strategy(Protocol):
    def on_step(self, context: StrategyContext) -> list[Order]:
        ...


@dataclass(frozen=True)
class RuntimeConfig:
    fee_rate: float = 0.0
    slippage_bps: float = 0.0
    initial_performance: float = 100.0
    constrain_buys_to_cash: bool = True

    def __post_init__(self) -> None:
        if self.fee_rate < 0:
            raise ValueError("fee_rate must be non-negative.")
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps must be non-negative.")
        if self.initial_performance <= 0:
            raise ValueError("initial_performance must be positive.")


@dataclass(frozen=True)
class BacktestResult:
    portfolio: Portfolio
    fills: list[Fill]
    performance: pd.Series
    equity: pd.Series

    def ffn_stats(self):
        import ffn  # noqa: F401

        return self.performance.calc_stats()


class Runtime:
    def __init__(
        self,
        strategy: Strategy,
        initial_cash: float,
        config: RuntimeConfig | None = None,
    ) -> None:
        if initial_cash <= 0:
            raise ValueError("initial_cash must be positive.")
        self.strategy = strategy
        self.portfolio = Portfolio(cash=float(initial_cash))
        self.config = config or RuntimeConfig()
        self._initial_cash = float(initial_cash)
        self._has_run = False

    def run(
        self,
        prices: pd.DataFrame,
        external_cash_flows: Mapping[pd.Timestamp, float] | None = None,
        start: pd.Timestamp | str | None = None,
    ) -> BacktestResult:
        if self._has_run:
            raise BacktestError("A Runtime instance can only be run once.")
        self._has_run = True
        prices = self._normalize_prices(prices)
        active_prices = self._active_prices(prices, start)
        cash_flows = self._normalize_cash_flows(external_cash_flows)
        fills: list[Fill] = []
        equity_values: list[float] = []
        equity_index: list[pd.Timestamp] = []
        performance_values: list[float] = [self.config.initial_performance]
        performance_index: list[pd.Timestamp] = [self._pre_start_timestamp(active_prices.index)]

        previous_value = self._initial_cash
        previous_performance = self.config.initial_performance

        for timestamp, row in active_prices.iterrows():
            price_map = {str(symbol): float(price) for symbol, price in row.items()}
            context = StrategyContext(
                timestamp=pd.Timestamp(timestamp),
                prices=price_map,
                history=prices.loc[:timestamp].copy(),
                portfolio=self.portfolio.snapshot(),
            )
            orders = self.strategy.on_step(context)
            for order in self._sell_orders_first(orders):
                fill = self._execute_order(pd.Timestamp(timestamp), order, price_map)
                if fill is not None:
                    self.portfolio.apply_fill(fill)
                    fills.append(fill)

            flow = cash_flows.get(pd.Timestamp(timestamp), 0.0)
            if flow:
                self.portfolio.apply_cash_flow(flow)

            current_value = self.portfolio.value(price_map)
            denominator = previous_value + flow
            if denominator == 0:
                raise BacktestError("Cannot calculate return with zero previous value after cash flow.")
            period_return = current_value / denominator - 1.0
            previous_performance = previous_performance * (1.0 + period_return)

            equity_index.append(pd.Timestamp(timestamp))
            equity_values.append(current_value)
            performance_index.append(pd.Timestamp(timestamp))
            performance_values.append(previous_performance)
            previous_value = current_value

        performance = pd.Series(performance_values, index=pd.DatetimeIndex(performance_index), name="performance")
        equity = pd.Series(equity_values, index=pd.DatetimeIndex(equity_index), name="equity")
        return BacktestResult(
            portfolio=self.portfolio,
            fills=fills,
            performance=performance,
            equity=equity,
        )

    def _execute_order(
        self,
        timestamp: pd.Timestamp,
        order: Order,
        prices: Mapping[str, float],
    ) -> Fill | None:
        if order.symbol not in prices:
            raise KeyError(f"Missing reference price for {order.symbol}")
        reference_price = prices[order.symbol]
        if reference_price <= 0:
            raise ValueError(f"Reference price must be positive for {order.symbol}.")

        slip = self.config.slippage_bps / 10_000.0
        if order.side == "buy":
            fill_price = reference_price * (1.0 + slip)
            quantity = self._cash_constrained_quantity(order.quantity, fill_price)
        else:
            fill_price = reference_price * (1.0 - slip)
            held = self.portfolio.quantity(order.symbol)
            if order.quantity > held + 1e-9:
                raise InsufficientPositionError(
                    f"Cannot sell {order.quantity} of {order.symbol}; only {held} held."
                )
            quantity = order.quantity

        if quantity <= 1e-12:
            return None
        fee = abs(fill_price * quantity) * self.config.fee_rate
        return Fill(
            timestamp=timestamp,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            reference_price=reference_price,
            fill_price=fill_price,
            fee=fee,
        )

    def _cash_constrained_quantity(self, requested_quantity: float, fill_price: float) -> float:
        if not self.config.constrain_buys_to_cash:
            total_cost = fill_price * requested_quantity * (1.0 + self.config.fee_rate)
            if total_cost > self.portfolio.cash + 1e-9:
                raise InsufficientCashError(f"Buy cost {total_cost} exceeds cash {self.portfolio.cash}.")
            return requested_quantity
        max_quantity = self.portfolio.cash / (fill_price * (1.0 + self.config.fee_rate))
        return min(requested_quantity, max_quantity)

    @staticmethod
    def _normalize_prices(prices: pd.DataFrame) -> pd.DataFrame:
        if prices.empty:
            raise ValueError("prices must not be empty.")
        normalized = prices.copy()
        normalized.index = pd.to_datetime(normalized.index)
        normalized = normalized.sort_index()
        if normalized.index.has_duplicates:
            raise ValueError("prices index must not contain duplicates.")
        if normalized.isna().any().any():
            raise ValueError("prices must not contain missing values.")
        return normalized

    @staticmethod
    def _active_prices(prices: pd.DataFrame, start: pd.Timestamp | str | None) -> pd.DataFrame:
        if start is None:
            return prices
        active_prices = prices.loc[prices.index >= pd.Timestamp(start)]
        if active_prices.empty:
            raise ValueError("start must be on or before the last price timestamp.")
        return active_prices

    @staticmethod
    def _normalize_cash_flows(
        external_cash_flows: Mapping[pd.Timestamp, float] | None,
    ) -> dict[pd.Timestamp, float]:
        if not external_cash_flows:
            return {}
        return {pd.Timestamp(timestamp): float(amount) for timestamp, amount in external_cash_flows.items()}

    @staticmethod
    def _pre_start_timestamp(index: pd.DatetimeIndex) -> pd.Timestamp:
        first = pd.Timestamp(index[0])
        if len(index) >= 2:
            delta = pd.Timestamp(index[1]) - first
            if delta > pd.Timedelta(0):
                return first - delta
        return first - pd.Timedelta(nanoseconds=1)

    @staticmethod
    def _sell_orders_first(orders: list[Order]) -> list[Order]:
        return sorted(orders, key=lambda order: 0 if order.side == "sell" else 1)
