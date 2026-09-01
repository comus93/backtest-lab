from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import pandas as pd

from backtest_lab.analysis import average_monthly_turnover
from backtest_lab.core import BacktestResult, Order, Runtime, RuntimeConfig, StrategyContext

STRATEGY_ID = "tripod_nasdaq_leverage"
REVISION = "r01"

TRADABLES = ("QQQ", "QLD", "TQQQ")
SIGNAL_COLUMNS = ("NDX", "VIX")
REQUIRED_COLUMNS = (*TRADABLES, *SIGNAL_COLUMNS)
WARMUP_OBSERVATIONS = 252

TREND_UP_RATIO = 0.01
TREND_DOWN_RATIO = -0.05
VIX_UP_RISK = 28.0
VIX_DOWN_RISK = 18.0
DRAWDOWN_RISK = -0.09

REGIME_UP_LOW_RISK = "UP_LOW_RISK_3X"
REGIME_UP_RISK = "UP_RISK_1_5X"
REGIME_DOWN_LOW_VOL = "DOWN_LOW_VOL_1_5X"
REGIME_DOWN_HIGH_VOL = "DOWN_HIGH_VOL_CASH"
REGIME_UNKNOWN = "INITIAL_UNKNOWN_CASH"


def _target_key(weights: Mapping[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted((str(symbol), float(weight)) for symbol, weight in weights.items() if weight > 0.0))


def _target_weight_orders(
    context: StrategyContext,
    target_weights: Mapping[str, float],
    tolerance: float = 1e-9,
) -> list[Order]:
    total_value = context.portfolio.value(context.prices)
    orders: list[Order] = []
    symbols = sorted(set(context.portfolio.positions) | set(target_weights))
    for symbol in symbols:
        target_quantity = (total_value * float(target_weights.get(symbol, 0.0))) / float(context.prices[symbol])
        difference = target_quantity - context.portfolio.quantity(symbol)
        if abs(difference) <= tolerance:
            continue
        orders.append(Order(symbol=symbol, side="buy" if difference > 0 else "sell", quantity=abs(difference)))
    return orders


def _signal_snapshot(history: pd.DataFrame, signal_date: pd.Timestamp) -> dict[str, float]:
    available = history.loc[:signal_date]
    if len(available) < WARMUP_OBSERVATIONS:
        raise ValueError("Tripod signal requires at least 252 observations.")
    if any(column not in available.columns for column in SIGNAL_COLUMNS):
        raise ValueError(f"Signal history must include columns {SIGNAL_COLUMNS}.")

    ndx = available["NDX"].astype(float)
    vix = available["VIX"].astype(float)
    ndx_close = float(ndx.iloc[-1])
    sma250 = float(ndx.iloc[-250:].mean())
    high252 = float(ndx.iloc[-252:].max())
    vix_close = float(vix.iloc[-1])
    vix10 = float(vix.iloc[-10:].mean())
    trend_ratio = ndx_close / sma250 - 1.0
    dd52 = ndx_close / high252 - 1.0
    return {
        "ndx_close": ndx_close,
        "sma250": sma250,
        "trend_ratio": trend_ratio,
        "vix_close": vix_close,
        "vix10": vix10,
        "high252": high252,
        "dd52": dd52,
    }


def _update_trend(previous: str, trend_ratio: float) -> str:
    if trend_ratio >= TREND_UP_RATIO:
        return "UP"
    if trend_ratio <= TREND_DOWN_RATIO:
        return "DOWN"
    return previous


def _target_for_state(trend: str, vix10: float, dd52: float) -> tuple[dict[str, float], str, float]:
    if trend == "UP":
        if vix10 < VIX_UP_RISK and dd52 >= DRAWDOWN_RISK:
            return {"TQQQ": 1.0}, REGIME_UP_LOW_RISK, 3.0
        return {"QQQ": 0.5, "QLD": 0.5}, REGIME_UP_RISK, 1.5

    if trend == "DOWN":
        if vix10 < VIX_DOWN_RISK:
            return {"QQQ": 0.5, "QLD": 0.5}, REGIME_DOWN_LOW_VOL, 1.5
        return {}, REGIME_DOWN_HIGH_VOL, 0.0

    return {}, REGIME_UNKNOWN, 0.0


@dataclass
class TripodStrategy:
    trend: str = "UNKNOWN"
    decisions: list[dict[str, object]] = field(default_factory=list)
    _started: bool = False
    _last_target: tuple[tuple[str, float], ...] = field(default_factory=tuple)

    def on_step(self, context: StrategyContext) -> list[Order]:
        # The first active Runtime step establishes the backtest start. Its close
        # becomes the first eligible signal and can only execute on the next step.
        if not self._started:
            self._started = True
            return []

        signal_history = context.history.iloc[:-1]
        if len(signal_history) < WARMUP_OBSERVATIONS:
            return []
        signal_date = pd.Timestamp(signal_history.index[-1])
        signal = _signal_snapshot(signal_history, signal_date)
        self.trend = _update_trend(self.trend, signal["trend_ratio"])
        target, regime, nominal_exposure = _target_for_state(self.trend, signal["vix10"], signal["dd52"])
        target_key = _target_key(target)
        target_changed = target_key != self._last_target

        self.decisions.append(
            {
                "signal_date": signal_date,
                "execution_date": pd.Timestamp(context.timestamp),
                **signal,
                "trend": self.trend,
                "regime": regime,
                "target_qqq": float(target.get("QQQ", 0.0)),
                "target_qld": float(target.get("QLD", 0.0)),
                "target_tqqq": float(target.get("TQQQ", 0.0)),
                "target_cash": 1.0 - sum(target.values()),
                "nominal_exposure": nominal_exposure,
                "target_changed": target_changed,
            }
        )

        if not target_changed:
            return []
        self._last_target = target_key
        return _target_weight_orders(context, target)


@dataclass
class BuyAndHoldStrategy:
    symbol: str
    _bought: bool = False

    def on_step(self, context: StrategyContext) -> list[Order]:
        if self._bought:
            return []
        self._bought = True
        return _target_weight_orders(context, {self.symbol: 1.0})


@dataclass(frozen=True)
class PilotOutputs:
    ffn_stats: pd.DataFrame
    performance_summary: pd.DataFrame
    equity_curves: pd.DataFrame
    daily_signals: pd.DataFrame
    regime_summary: pd.DataFrame
    yearly_performance: pd.DataFrame
    exposure: pd.DataFrame

    def write_csv(self, output_dir: str | Path) -> dict[str, Path]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}

        ffn_path = path / "ffn_stats.csv"
        self.ffn_stats.to_csv(ffn_path, index=True, index_label="metric")
        paths["ffn_stats"] = ffn_path

        equity_path = path / "equity_curves.csv"
        self.equity_curves.to_csv(equity_path, index=True, index_label="timestamp")
        paths["equity_curves"] = equity_path

        for name, table in {
            "performance_summary": self.performance_summary,
            "daily_signals": self.daily_signals,
            "regime_summary": self.regime_summary,
            "yearly_performance": self.yearly_performance,
            "exposure": self.exposure,
        }.items():
            file_path = path / f"{name}.csv"
            table.to_csv(file_path, index=False)
            paths[name] = file_path
        return paths


def find_active_start(prices: pd.DataFrame, warmup_observations: int = WARMUP_OBSERVATIONS) -> pd.Timestamp:
    if len(prices) <= warmup_observations:
        raise ValueError(f"Need more than {warmup_observations} complete observations for warm-up and active data.")
    return pd.Timestamp(prices.index[warmup_observations])


def _ffn_stats(results: Mapping[str, BacktestResult]) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    columns: dict[str, pd.Series] = {}
    for name, result in results.items():
        stats_object = result.ffn_stats()
        raw = getattr(stats_object, "stats", None)
        if raw is None:
            raise ValueError("FFN calc_stats() result does not expose .stats.")
        columns[name] = pd.Series(raw)
    return pd.concat(columns, axis=1), columns


def _stat(series: pd.Series, key: str) -> float:
    if key not in series.index:
        return float("nan")
    value = series.loc[key]
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _performance_summary(
    results: Mapping[str, BacktestResult],
    stats_by_name: Mapping[str, pd.Series],
    start: pd.Timestamp,
    avg_exposure: Mapping[str, float],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name, result in results.items():
        stats = stats_by_name[name]
        active = result.performance.loc[result.performance.index >= start]
        rows.append(
            {
                "strategy": name,
                "start_date": start.date(),
                "end_date": active.index[-1].date(),
                "total_return": _stat(stats, "total_return"),
                "cagr": _stat(stats, "cagr"),
                "volatility": _stat(stats, "daily_vol"),
                "sharpe": _stat(stats, "daily_sharpe"),
                "max_drawdown": _stat(stats, "max_drawdown"),
                "calmar": _stat(stats, "calmar"),
                "avg_monthly_turnover": average_monthly_turnover(result),
                "avg_nominal_exposure": float(avg_exposure[name]),
            }
        )
    return pd.DataFrame(rows)


def _regime_summary(decisions: pd.DataFrame) -> pd.DataFrame:
    columns = ["regime", "days", "share_of_active_days", "nominal_exposure"]
    if decisions.empty:
        return pd.DataFrame(columns=columns)
    total = len(decisions)
    grouped = decisions.groupby("regime", sort=True).agg(
        days=("signal_date", "size"),
        nominal_exposure=("nominal_exposure", "first"),
    ).reset_index()
    grouped["share_of_active_days"] = grouped["days"] / total
    return grouped.loc[:, columns]


def _yearly_performance(results: Mapping[str, BacktestResult], start: pd.Timestamp) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name, result in results.items():
        active = result.performance.loc[result.performance.index >= start]
        for year, levels in active.groupby(active.index.year):
            if levels.empty:
                continue
            normalized = levels / levels.iloc[0]
            rows.append(
                {
                    "year": int(year),
                    "strategy": name,
                    "return": float(levels.iloc[-1] / levels.iloc[0] - 1.0),
                    "max_drawdown": float((normalized / normalized.cummax() - 1.0).min()),
                }
            )
    return pd.DataFrame(rows, columns=["year", "strategy", "return", "max_drawdown"])


def _exposure(decisions: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "timestamp", "trend", "regime", "qqq_weight", "qld_weight", "tqqq_weight", "cash_weight", "nominal_exposure"
    ]
    if decisions.empty:
        return pd.DataFrame(columns=columns)
    frame = decisions.loc[
        :, ["execution_date", "trend", "regime", "target_qqq", "target_qld", "target_tqqq", "target_cash", "nominal_exposure"]
    ].copy()
    frame.columns = columns
    return frame


def run_pilot(
    prices: pd.DataFrame,
    start: pd.Timestamp | str,
    config: RuntimeConfig | None = None,
) -> PilotOutputs:
    missing = [column for column in REQUIRED_COLUMNS if column not in prices.columns]
    if missing:
        raise ValueError(f"prices missing required columns: {missing}")

    start_timestamp = pd.Timestamp(start)
    config = config or RuntimeConfig(fee_rate=0.00015)
    tripod = TripodStrategy()
    strategies: list[tuple[str, object]] = [
        ("Tripod Strategy", tripod),
        ("QQQ Buy & Hold", BuyAndHoldStrategy("QQQ")),
        ("QLD Buy & Hold", BuyAndHoldStrategy("QLD")),
        ("TQQQ Buy & Hold", BuyAndHoldStrategy("TQQQ")),
    ]

    results: dict[str, BacktestResult] = {}
    for name, strategy in strategies:
        results[name] = Runtime(strategy, initial_cash=1_000_000.0, config=config).run(prices, start=start_timestamp)

    decisions = pd.DataFrame(tripod.decisions)
    curves = pd.concat([result.performance.rename(name) for name, result in results.items()], axis=1)
    ffn_table, stats_by_name = _ffn_stats(results)
    tripod_avg_exposure = float(decisions["nominal_exposure"].mean()) if not decisions.empty else 0.0
    avg_exposure = {
        "Tripod Strategy": tripod_avg_exposure,
        "QQQ Buy & Hold": 1.0,
        "QLD Buy & Hold": 2.0,
        "TQQQ Buy & Hold": 3.0,
    }

    return PilotOutputs(
        ffn_stats=ffn_table,
        performance_summary=_performance_summary(results, stats_by_name, start_timestamp, avg_exposure),
        equity_curves=curves,
        daily_signals=decisions,
        regime_summary=_regime_summary(decisions),
        yearly_performance=_yearly_performance(results, start_timestamp),
        exposure=_exposure(decisions),
    )
