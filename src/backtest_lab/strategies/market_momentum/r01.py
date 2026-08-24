from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from backtest_lab.analysis import average_monthly_turnover
from backtest_lab.core import Order, Runtime, RuntimeConfig, StrategyContext

STRATEGY_ID = "market_momentum"
REVISION = "r01"

UNIVERSE = (
    "SPY", "QQQ", "DIA", "EWJ", "EWY", "VNAM", "MCHI", "KTEC", "KSTR", "DAX", "EWW", "EIDO", "INDY", "EPHE"
)
HORIZONS = (3, 6, 9, 12)


def monthly_momentum(
    history: pd.DataFrame,
    signal_date: pd.Timestamp,
    horizon_months: int,
    symbols: Iterable[str],
) -> pd.Series:
    """Return calendar-month momentum using only rows through signal_date."""
    symbols = list(symbols)
    available = history.loc[:signal_date, symbols]
    monthly_prices = available.resample("ME").last()
    signal_period = pd.Timestamp(signal_date).to_period("M")
    signal_rows = monthly_prices[monthly_prices.index.to_period("M") == signal_period]
    base_rows = monthly_prices[monthly_prices.index.to_period("M") == signal_period - horizon_months]
    if signal_rows.empty or base_rows.empty:
        raise ValueError(f"Insufficient {horizon_months}M history for signal date {signal_date.date()}.")
    return signal_rows.iloc[-1] / base_rows.iloc[-1] - 1.0


def rank_symbols(momentum: pd.Series) -> list[str]:
    return sorted(momentum.index.tolist(), key=lambda symbol: (-float(momentum[symbol]), symbol))


def _target_weight_orders(
    context: StrategyContext,
    target_weights: Mapping[str, float],
    tolerance: float = 1e-9,
) -> list[Order]:
    total_value = context.portfolio.value(context.prices)
    orders: list[Order] = []
    for symbol in sorted(set(context.portfolio.positions) | set(target_weights)):
        target_quantity = (total_value * target_weights.get(symbol, 0.0)) / context.prices[symbol]
        difference = target_quantity - context.portfolio.quantity(symbol)
        if abs(difference) > tolerance:
            orders.append(Order(symbol, "buy" if difference > 0 else "sell", abs(difference)))
    return orders


def _is_first_trading_day_of_month(context: StrategyContext) -> bool:
    if len(context.history) < 2:
        return False
    return context.history.index[-2].to_period("M") != context.timestamp.to_period("M")


@dataclass
class StaticEqualWeightStrategy:
    symbols: tuple[str, ...] = UNIVERSE
    _initialized: bool = False

    def on_step(self, context: StrategyContext) -> list[Order]:
        if not self._initialized:
            self._initialized = True
        elif not _is_first_trading_day_of_month(context):
            return []
        return _target_weight_orders(context, {symbol: 1.0 / len(self.symbols) for symbol in self.symbols})


@dataclass
class SpyBuyHoldStrategy:
    symbol: str = "SPY"
    _bought: bool = False

    def on_step(self, context: StrategyContext) -> list[Order]:
        if self._bought:
            return []
        self._bought = True
        return _target_weight_orders(context, {self.symbol: 1.0})


@dataclass
class MarketMomentumStrategy:
    horizon_months: int
    symbols: tuple[str, ...] = UNIVERSE
    decisions: list[dict[str, object]] = field(default_factory=list)
    _executed_months: set[pd.Period] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.horizon_months not in HORIZONS:
            raise ValueError(f"horizon_months must be one of {HORIZONS}.")

    def on_step(self, context: StrategyContext) -> list[Order]:
        execution_month = context.timestamp.to_period("M")
        if execution_month in self._executed_months or not _is_first_trading_day_of_month(context):
            return []

        signal_history = context.history.iloc[:-1]
        signal_date = pd.Timestamp(signal_history.index[-1])
        try:
            momentum = monthly_momentum(signal_history, signal_date, self.horizon_months, self.symbols)
        except ValueError:
            return []

        ranking = rank_symbols(momentum)
        selected = set(ranking[:3])
        for rank, symbol in enumerate(ranking, start=1):
            self.decisions.append(
                {
                    "horizon": self.horizon_months,
                    "signal_date": signal_date,
                    "execution_date": pd.Timestamp(context.timestamp),
                    "symbol": symbol,
                    "momentum": float(momentum[symbol]),
                    "rank": rank,
                    "selected": symbol in selected,
                    "target_weight": 1.0 / 3.0 if symbol in selected else 0.0,
                }
            )
        self._executed_months.add(execution_month)
        return _target_weight_orders(context, {symbol: 1.0 / 3.0 for symbol in ranking[:3]})


@dataclass(frozen=True)
class PilotOutputs:
    performance_summary: pd.DataFrame
    equity_curves: pd.DataFrame
    monthly_decisions: pd.DataFrame
    momentum_signal_analysis: pd.DataFrame

    def write_csv(self, output_dir: str | Path) -> dict[str, Path]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        tables = {
            "performance_summary": self.performance_summary,
            "equity_curves": self.equity_curves,
            "monthly_decisions": self.monthly_decisions,
            "momentum_signal_analysis": self.momentum_signal_analysis,
        }
        paths: dict[str, Path] = {}
        for name, table in tables.items():
            file_path = path / f"{name}.csv"
            table.to_csv(file_path, index=name == "equity_curves", index_label="timestamp")
            paths[name] = file_path
        return paths


def run_pilot(
    prices: pd.DataFrame,
    start: pd.Timestamp | str,
    config: RuntimeConfig | None = None,
    symbols: tuple[str, ...] = UNIVERSE,
) -> PilotOutputs:
    config = config or RuntimeConfig(fee_rate=0.00015)
    strategy_specs = [("Static Equal Weight", StaticEqualWeightStrategy(symbols))]
    strategy_specs += [(f"Momentum {horizon}M", MarketMomentumStrategy(horizon, symbols)) for horizon in HORIZONS]
    strategy_specs += [("SPY Buy & Hold", SpyBuyHoldStrategy())]

    results = {}
    decision_frames = []
    for name, strategy in strategy_specs:
        result = Runtime(strategy, initial_cash=1_000_000.0, config=config).run(prices, start=start)
        results[name] = result
        if isinstance(strategy, MarketMomentumStrategy):
            decision_frames.append(pd.DataFrame(strategy.decisions))

    decisions = pd.concat(decision_frames, ignore_index=True) if decision_frames else pd.DataFrame()
    curves = pd.concat([result.performance.rename(name) for name, result in results.items()], axis=1)
    summary = _performance_summary(results)
    analysis = _momentum_signal_analysis(prices, decisions)
    return PilotOutputs(summary, curves, decisions, analysis)


def find_active_start(prices: pd.DataFrame, symbols: tuple[str, ...] = UNIVERSE) -> pd.Timestamp:
    """Find the first trading day after a month-end with 12M common history."""
    for position in range(1, len(prices.index)):
        timestamp = pd.Timestamp(prices.index[position])
        signal_date = pd.Timestamp(prices.index[position - 1])
        if timestamp.to_period("M") == signal_date.to_period("M"):
            continue
        try:
            monthly_momentum(prices.loc[:signal_date], signal_date, 12, symbols)
        except ValueError:
            continue
        return timestamp
    raise ValueError("No active start has 12 months of common month-end history.")


def _performance_summary(results: Mapping[str, object]) -> pd.DataFrame:
    rows = []
    for name, result in results.items():
        performance = result.performance
        returns = performance.pct_change().dropna()
        total_return = performance.iloc[-1] / performance.iloc[0] - 1.0
        years = max((performance.index[-1] - performance.index[0]).days / 365.25, 1 / 365.25)
        volatility = float(returns.std(ddof=0) * np.sqrt(252)) if not returns.empty else 0.0
        sharpe = float(returns.mean() / returns.std(ddof=0) * np.sqrt(252)) if returns.std(ddof=0) else 0.0
        drawdown = performance / performance.cummax() - 1.0
        monthly_turnover = average_monthly_turnover(result)
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
                "avg_monthly_turnover": monthly_turnover,
            }
        )
    return pd.DataFrame(rows)


def _momentum_signal_analysis(prices: pd.DataFrame, decisions: pd.DataFrame) -> pd.DataFrame:
    columns = ["horizon", "top3_next_1m_return", "bottom3_next_1m_return", "top3_minus_bottom3", "spread_win_rate", "observation_months"]
    if decisions.empty:
        return pd.DataFrame(columns=columns)
    monthly = prices.resample("ME").last()
    observations = []
    for (horizon, signal_date), group in decisions.groupby(["horizon", "signal_date"]):
        periods = monthly.index.to_period("M")
        position = periods.get_loc(pd.Timestamp(signal_date).to_period("M"))
        if position + 1 >= len(monthly):
            continue
        next_returns = monthly.iloc[position + 1] / monthly.iloc[position] - 1.0
        top = group[group["rank"] <= 3]["symbol"].map(next_returns).mean()
        bottom = group[group["rank"] > len(group) - 3]["symbol"].map(next_returns).mean()
        observations.append({"horizon": horizon, "top": top, "bottom": bottom, "spread": top - bottom})
    if not observations:
        return pd.DataFrame(columns=columns)
    observed = pd.DataFrame(observations)
    return observed.groupby("horizon", as_index=False).agg(
        top3_next_1m_return=("top", "mean"),
        bottom3_next_1m_return=("bottom", "mean"),
        top3_minus_bottom3=("spread", "mean"),
        spread_win_rate=("spread", lambda values: float((values > 0).mean())),
        observation_months=("spread", "size"),
    )
