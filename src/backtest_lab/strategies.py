from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backtest_lab.core import Order, StrategyContext


@dataclass
class MonthlyTargetWeightStrategy:
    target_weights: dict[str, float]
    tolerance: float = 1e-6
    _last_rebalance_month: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        total = sum(self.target_weights.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError("target weights must sum to 1.0.")
        if any(weight < 0 for weight in self.target_weights.values()):
            raise ValueError("target weights must be non-negative.")

    def on_step(self, context: StrategyContext) -> list[Order]:
        timestamp = pd.Timestamp(context.timestamp)
        month = (timestamp.year, timestamp.month)
        if self._last_rebalance_month == month:
            return []
        self._last_rebalance_month = month

        total_value = context.portfolio.value(context.prices)
        orders: list[Order] = []
        for symbol, weight in self.target_weights.items():
            price = context.prices[symbol]
            target_quantity = (total_value * weight) / price
            current_quantity = context.portfolio.quantity(symbol)
            difference = target_quantity - current_quantity
            if abs(difference) <= self.tolerance:
                continue
            side = "buy" if difference > 0 else "sell"
            orders.append(Order(symbol=symbol, side=side, quantity=abs(difference)))
        return orders
