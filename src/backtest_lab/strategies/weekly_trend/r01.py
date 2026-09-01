from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

from backtest_lab.analysis import average_monthly_turnover
from backtest_lab.core import BacktestResult, Order, Runtime, RuntimeConfig, StrategyContext

STRATEGY_ID = "weekly_trend"
REVISION = "r01"

UNIVERSE = ("SPY", "QQQ", "DIA", "EWJ", "EWY", "MCHI", "DAX", "EWW", "EIDO", "INDY", "EPHE")


def _is_first_trading_day_of_week(context: StrategyContext) -> bool:
    if len(context.history) < 2:
        return False
    previous = pd.Timestamp(context.history.index[-2]).to_period("W-FRI")
    current = pd.Timestamp(context.timestamp).to_period("W-FRI")
    return previous != current


def completed_weekly_closes(history: pd.DataFrame, symbols: tuple[str, ...]) -> pd.DataFrame:
    frame = history.loc[:, list(symbols)]
    if frame.empty:
        return frame.copy()
    periods = frame.index.to_period("W-FRI")
    return frame.groupby(periods, sort=True).tail(1)


def two_week_direction(
    weekly_closes: pd.DataFrame,
    symbol: str,
    move_threshold: float = 0.0,
) -> tuple[bool, bool, float, float]:
    series = weekly_closes[symbol].dropna()
    if len(series) < 3:
        raise ValueError("At least three completed weekly closes are required.")
    recent = series.iloc[-3:]
    first_return = float(recent.iloc[1] / recent.iloc[0] - 1.0)
    second_return = float(recent.iloc[2] / recent.iloc[1] - 1.0)
    rising = first_return > move_threshold and second_return > move_threshold
    falling = first_return < -move_threshold and second_return < -move_threshold
    return rising, falling, first_return, second_return


def _target_weight_orders(
    context: StrategyContext,
    target_weights: Mapping[str, float],
    tolerance: float = 1e-9,
) -> list[Order]:
    total_value = context.portfolio.value(context.prices)
    orders: list[Order] = []
    symbols = sorted(set(context.portfolio.positions) | set(target_weights))
    for symbol in symbols:
        target_quantity = (total_value * target_weights.get(symbol, 0.0)) / context.prices[symbol]
        difference = target_quantity - context.portfolio.quantity(symbol)
        if abs(difference) <= tolerance:
            continue
        orders.append(Order(symbol, "buy" if difference > 0 else "sell", abs(difference)))
    return orders


@dataclass
class WeeklyTrendStrategy:
    symbols: tuple[str, ...] = UNIVERSE
    move_threshold: float = 0.0
    decisions: list[dict[str, object]] = field(default_factory=list)
    _active: set[str] = field(default_factory=set)
    _executed_weeks: set[pd.Period] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.symbols:
            raise ValueError("symbols must not be empty.")
        if self.move_threshold < 0:
            raise ValueError("move_threshold must be non-negative.")

    @property
    def slot_weight(self) -> float:
        return 1.0 / len(self.symbols)

    def on_step(self, context: StrategyContext) -> list[Order]:
        execution_week = pd.Timestamp(context.timestamp).to_period("W-FRI")
        if execution_week in self._executed_weeks or not _is_first_trading_day_of_week(context):
            return []

        signal_history = context.history.iloc[:-1]
        weekly = completed_weekly_closes(signal_history, self.symbols)
        if len(weekly) < 3:
            self._executed_weeks.add(execution_week)
            return []

        signal_date = pd.Timestamp(weekly.index[-1])
        changed = False
        rows: list[dict[str, object]] = []

        for symbol in self.symbols:
            rising, falling, return_1, return_2 = two_week_direction(
                weekly,
                symbol,
                move_threshold=self.move_threshold,
            )
            active_before = symbol in self._active
            action = "hold" if active_before else "out"

            if not active_before and rising:
                self._active.add(symbol)
                action = "enter"
                changed = True
            elif active_before and falling:
                self._active.remove(symbol)
                action = "exit"
                changed = True

            active_after = symbol in self._active
            rows.append(
                {
                    "signal_date": signal_date,
                    "execution_date": pd.Timestamp(context.timestamp),
                    "symbol": symbol,
                    "weekly_return_1": return_1,
                    "weekly_return_2": return_2,
                    "rise_2w": rising,
                    "fall_2w": falling,
                    "action": action,
                    "active_before": active_before,
                    "active_after": active_after,
                    "target_weight": self.slot_weight if active_after else 0.0,
                    "move_threshold": self.move_threshold,
                }
            )

        self.decisions.extend(rows)
        self._executed_weeks.add(execution_week)

        if not changed:
            return []

        targets = {symbol: self.slot_weight for symbol in self._active}
        return _target_weight_orders(context, targets)


@dataclass
class BuyHoldWeightsStrategy:
    target_weights: dict[str, float]
    _bought: bool = False

    def on_step(self, context: StrategyContext) -> list[Order]:
        if self._bought:
            return []
        self._bought = True
        return _target_weight_orders(context, self.target_weights)


@dataclass(frozen=True)
class PilotOutputs:
    performance_summary: pd.DataFrame
    equity_curves: pd.DataFrame
    weekly_decisions: pd.DataFrame
    exposure: pd.DataFrame

    def write_csv(self, output_dir: str | Path) -> dict[str, Path]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        tables = {
            "performance_summary": self.performance_summary,
            "equity_curves": self.equity_curves,
            "weekly_decisions": self.weekly_decisions,
            "exposure": self.exposure,
        }
        result: dict[str, Path] = {}
        for name, table in tables.items():
            file_path = path / f"{name}.csv"
            use_index = name in {"equity_curves", "exposure"}
            table.to_csv(file_path, index=use_index, index_label="timestamp" if use_index else None)
            result[name] = file_path
        return result


def _performance_summary(results: Mapping[str, BacktestResult]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name, result in results.items():
        performance = result.performance
        returns = performance.pct_change().dropna()
        total_return = float(performance.iloc[-1] / performance.iloc[0] - 1.0)
        years = max((performance.index[-1] - performance.index[0]).days / 365.25, 1 / 365.25)
        volatility = float(returns.std(ddof=0) * np.sqrt(252)) if not returns.empty else 0.0
        std = float(returns.std(ddof=0)) if not returns.empty else 0.0
        sharpe = float(returns.mean() / std * np.sqrt(252)) if std else 0.0
        drawdown = performance / performance.cummax() - 1.0
        rows.append(
            {
                "strategy": name,
                "start_date": performance.index[1].date(),
                "end_date": performance.index[-1].date(),
                "total_return": total_return,
                "cagr": (1.0 + total_return) ** (1.0 / years) - 1.0,
                "volatility": volatility,
                "sharpe": sharpe,
                "max_drawdown": float(drawdown.min()),
                "avg_monthly_turnover": average_monthly_turnover(result),
            }
        )
    return pd.DataFrame(rows)


def _exposure_frame(
    prices: pd.DataFrame,
    result: BacktestResult,
    start: pd.Timestamp,
) -> pd.DataFrame:
    active_prices = prices.loc[prices.index >= start]
    fills_by_timestamp: dict[pd.Timestamp, list] = {}
    for fill in result.fills:
        fills_by_timestamp.setdefault(pd.Timestamp(fill.timestamp), []).append(fill)

    positions: dict[str, float] = {}
    rows: list[dict[str, object]] = []
    for timestamp, row in active_prices.iterrows():
        timestamp = pd.Timestamp(timestamp)
        for fill in fills_by_timestamp.get(timestamp, []):
            current = positions.get(fill.symbol, 0.0)
            next_quantity = current + fill.quantity if fill.side == "buy" else current - fill.quantity
            if abs(next_quantity) <= 1e-9:
                positions.pop(fill.symbol, None)
            else:
                positions[fill.symbol] = next_quantity

        invested_value = sum(quantity * float(row[symbol]) for symbol, quantity in positions.items())
        equity = float(result.equity.loc[timestamp])
        invested_weight = invested_value / equity if equity else 0.0
        rows.append(
            {
                "timestamp": timestamp,
                "invested_weight": invested_weight,
                "cash_weight": 1.0 - invested_weight,
                "active_positions": len(positions),
            }
        )

    if not rows:
        return pd.DataFrame(columns=["invested_weight", "cash_weight", "active_positions"])
    return pd.DataFrame(rows).set_index("timestamp")


def run_pilot(
    prices: pd.DataFrame,
    start: pd.Timestamp | str,
    config: RuntimeConfig | None = None,
    symbols: tuple[str, ...] = UNIVERSE,
    move_threshold: float = 0.0,
) -> PilotOutputs:
    if "SPY" not in prices.columns:
        raise ValueError("prices must contain SPY for the benchmark.")
    start_timestamp = pd.Timestamp(start)
    config = config or RuntimeConfig(fee_rate=0.00015)

    trend = WeeklyTrendStrategy(symbols=symbols, move_threshold=move_threshold)
    equal_weight = BuyHoldWeightsStrategy({symbol: 1.0 / len(symbols) for symbol in symbols})
    spy = BuyHoldWeightsStrategy({"SPY": 1.0})

    strategies = [
        ("Weekly Trend 1/N", trend),
        ("Universe Equal Weight Buy & Hold", equal_weight),
        ("SPY Buy & Hold", spy),
    ]
    results: dict[str, BacktestResult] = {}
    for name, strategy in strategies:
        results[name] = Runtime(strategy, initial_cash=1_000_000.0, config=config).run(prices, start=start_timestamp)

    curves = pd.concat([result.performance.rename(name) for name, result in results.items()], axis=1)
    decisions = pd.DataFrame(trend.decisions)
    exposure = _exposure_frame(prices, results["Weekly Trend 1/N"], start_timestamp)
    summary = _performance_summary(results)
    if not exposure.empty:
        avg_exposure = float(exposure["invested_weight"].mean())
        summary.loc[summary["strategy"] == "Weekly Trend 1/N", "avg_exposure"] = avg_exposure
        summary.loc[summary["strategy"] == "Universe Equal Weight Buy & Hold", "avg_exposure"] = 1.0
        summary.loc[summary["strategy"] == "SPY Buy & Hold", "avg_exposure"] = 1.0
    else:
        summary["avg_exposure"] = np.nan

    return PilotOutputs(summary, curves, decisions, exposure)
