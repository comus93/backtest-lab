from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from backtest_lab.analysis import average_monthly_turnover
from backtest_lab.core import BacktestResult, Order, Runtime, RuntimeConfig, StrategyContext
from backtest_lab.strategies.market_momentum.r01 import (
    _is_first_trading_day_of_month,
    _target_weight_orders,
    monthly_momentum,
    rank_symbols,
)

STRATEGY_ID = "market_momentum"
REVISION = "r02"

UNIVERSE = ("SPY", "QQQ", "DIA", "EWJ", "EWY", "MCHI", "DAX", "EWW", "EIDO", "INDY", "EPHE")
HORIZONS = (3, 6, 12)
COMPARISON_ASSETS = ("SPY", "QQQ", "SLV", "GDX", "AIA", "XLF", "XLE")


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


@dataclass
class SpyBuyHoldStrategy:
    symbol: str = "SPY"
    _bought: bool = False

    def on_step(self, context: StrategyContext) -> list[Order]:
        if self._bought:
            return []
        self._bought = True
        return _target_weight_orders(context, {self.symbol: 1.0})


@dataclass(frozen=True)
class PilotOutputs:
    performance_summary: pd.DataFrame
    equity_curves: pd.DataFrame
    monthly_decisions: pd.DataFrame
    yearly_asset_correlation: pd.DataFrame
    overall_asset_correlation: pd.DataFrame
    downside_asset_correlation: pd.DataFrame
    yearly_constituent_correlation: pd.DataFrame
    yearly_constituents: pd.DataFrame
    yearly_strategy_context: pd.DataFrame

    def write_csv(self, output_dir: str | Path) -> dict[str, Path]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        tables = {
            "performance_summary": self.performance_summary,
            "equity_curves": self.equity_curves,
            "monthly_decisions": self.monthly_decisions,
            "yearly_asset_correlation": self.yearly_asset_correlation,
            "overall_asset_correlation": self.overall_asset_correlation,
            "downside_asset_correlation": self.downside_asset_correlation,
            "yearly_constituent_correlation": self.yearly_constituent_correlation,
            "yearly_constituents": self.yearly_constituents,
            "yearly_strategy_context": self.yearly_strategy_context,
        }
        paths: dict[str, Path] = {}
        for name, table in tables.items():
            file_path = path / f"{name}.csv"
            table.to_csv(file_path, index=name == "equity_curves", index_label="timestamp")
            paths[name] = file_path
        return paths


def _resampled_returns(levels: pd.Series, frequency: str) -> pd.Series:
    rule = {"weekly": "W-FRI", "monthly": "ME"}[frequency]
    return levels.resample(rule).last().pct_change().dropna()


def _correlation(left: pd.Series, right: pd.Series) -> tuple[float, int]:
    aligned = pd.concat([left.rename("left"), right.rename("right")], axis=1, join="inner").dropna()
    return (float(aligned["left"].corr(aligned["right"])), len(aligned)) if len(aligned) >= 2 else (float("nan"), len(aligned))


def _performance_summary(results: Mapping[str, BacktestResult]) -> pd.DataFrame:
    rows = []
    for name, result in results.items():
        performance = result.performance
        returns = performance.pct_change().dropna()
        total_return = performance.iloc[-1] / performance.iloc[0] - 1.0
        years = max((performance.index[-1] - performance.index[0]).days / 365.25, 1 / 365.25)
        volatility = float(returns.std(ddof=0) * np.sqrt(252)) if not returns.empty else 0.0
        sharpe = float(returns.mean() / returns.std(ddof=0) * np.sqrt(252)) if returns.std(ddof=0) else 0.0
        drawdown = performance / performance.cummax() - 1.0
        rows.append({
            "strategy": name,
            "start_date": performance.index[1].date(),
            "end_date": performance.index[-1].date(),
            "total_return": total_return,
            "cagr": (1.0 + total_return) ** (1.0 / years) - 1.0,
            "volatility": volatility,
            "sharpe": sharpe,
            "max_drawdown": float(drawdown.min()),
            "avg_monthly_turnover": average_monthly_turnover(result),
        })
    return pd.DataFrame(rows)


def _asset_correlation_rows(
    strategy_returns: Mapping[int, pd.Series],
    asset_prices: pd.DataFrame,
    frequency: str,
    yearly: bool,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    asset_returns = {asset: _resampled_returns(asset_prices[asset], frequency) for asset in COMPARISON_ASSETS}
    years = sorted({int(timestamp.year) for series in strategy_returns.values() for timestamp in series.index})
    for horizon, returns in strategy_returns.items():
        for asset, values in asset_returns.items():
            if yearly:
                for year in years:
                    correlation, n_obs = _correlation(returns[returns.index.year == year], values[values.index.year == year])
                    rows.append({"year": year, "horizon": horizon, "asset": asset, "correlation": correlation, "n_obs": n_obs})
            else:
                correlation, n_obs = _correlation(returns, values)
                rows.append({"frequency": frequency, "horizon": horizon, "asset": asset, "correlation": correlation, "n_obs": n_obs})
    return pd.DataFrame(rows)


def _downside_asset_correlation_rows(
    strategy_returns: Mapping[int, pd.Series],
    asset_prices: pd.DataFrame,
    reference_assets: Iterable[str] = COMPARISON_ASSETS,
) -> pd.DataFrame:
    """Correlate strategy returns with each reference asset's down weeks."""
    rows: list[dict[str, object]] = []
    asset_returns = {asset: _resampled_returns(asset_prices[asset], "weekly") for asset in reference_assets}
    for reference_asset, reference_returns in asset_returns.items():
        for horizon, strategy in strategy_returns.items():
            aligned = pd.concat(
                [reference_returns.rename("reference"), strategy.rename("strategy")], axis=1, join="inner"
            ).dropna()
            down = aligned.loc[aligned["reference"] < 0.0]
            correlation = float(down["reference"].corr(down["strategy"])) if len(down) >= 2 else float("nan")
            rows.append(
                {
                    "reference_asset": reference_asset,
                    "horizon": horizon,
                    "correlation": correlation,
                    "n_obs": len(down),
                    "reference_avg_return": float(down["reference"].mean()) if not down.empty else float("nan"),
                    "strategy_avg_return": float(down["strategy"].mean()) if not down.empty else float("nan"),
                }
            )
    return pd.DataFrame(
        rows,
        columns=["reference_asset", "horizon", "correlation", "n_obs", "reference_avg_return", "strategy_avg_return"],
    )


def _yearly_selection_counts(decisions: pd.DataFrame) -> pd.DataFrame:
    columns = ["year", "horizon", "symbol", "selected_months"]
    if decisions.empty:
        return pd.DataFrame(columns=columns)
    selected = decisions.loc[decisions["selected"]].copy()
    selected["year"] = pd.to_datetime(selected["signal_date"]).dt.year
    counts = (
        selected.groupby(["year", "horizon", "symbol"])["signal_date"]
        .nunique()
        .rename("selected_months")
        .reset_index()
    )
    return counts.loc[:, columns].sort_values(["year", "horizon", "selected_months", "symbol"], ascending=[True, True, False, True], ignore_index=True)


def _constituent_outputs(prices: pd.DataFrame, decisions: pd.DataFrame, start: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    constituent_columns = ["year", "horizon", "symbol", "selected_months"]
    matrix_columns = ["year", "symbol_a", "symbol_b", "correlation", "n_obs"]
    all_constituents = _yearly_selection_counts(decisions)
    selected = decisions[(decisions["horizon"] == 12) & decisions["selected"]].copy()
    if selected.empty:
        return pd.DataFrame(columns=matrix_columns), all_constituents.reindex(columns=constituent_columns)
    selected["year"] = pd.to_datetime(selected["signal_date"]).dt.year
    matrix_rows: list[dict[str, object]] = []
    active_prices = prices.loc[prices.index >= start]
    for year, group in selected.groupby("year"):
        counts = group.groupby("symbol")["signal_date"].nunique().sort_index()
        symbols = list(counts.index)
        returns = {symbol: _resampled_returns(active_prices[symbol][active_prices.index.year == year], "weekly") for symbol in symbols}
        for symbol_a in symbols:
            for symbol_b in symbols:
                correlation, n_obs = _correlation(returns[symbol_a], returns[symbol_b])
                matrix_rows.append({"year": int(year), "symbol_a": symbol_a, "symbol_b": symbol_b, "correlation": correlation, "n_obs": n_obs})
    return pd.DataFrame(matrix_rows, columns=matrix_columns), all_constituents.reindex(columns=constituent_columns)


def _max_drawdown(levels: pd.Series) -> float:
    if levels.empty:
        return float("nan")
    normalized = levels / levels.iloc[0]
    return float((normalized / normalized.cummax() - 1.0).min())


def _yearly_strategy_context(
    results: Mapping[str, BacktestResult],
    comparison_prices: pd.DataFrame,
    decisions: pd.DataFrame,
    start: pd.Timestamp,
) -> pd.DataFrame:
    columns = [
        "year", "horizon", "benchmark", "correlation", "n_obs", "benchmark_return", "strategy_return",
        "excess_return", "benchmark_mdd", "strategy_mdd", "selected_symbols",
    ]
    selection_counts = _yearly_selection_counts(decisions)
    rows: list[dict[str, object]] = []
    for horizon in HORIZONS:
        strategy_levels = results[f"Momentum {horizon}M"].performance
        strategy_levels = strategy_levels.loc[strategy_levels.index >= start]
        strategy_weekly = _resampled_returns(strategy_levels, "weekly")
        for benchmark in ("SPY", "QQQ"):
            benchmark_levels = comparison_prices[benchmark].loc[lambda series: series.index >= start]
            benchmark_weekly = _resampled_returns(benchmark_levels, "weekly")
            years = sorted(set(strategy_levels.index.year) & set(benchmark_levels.index.year))
            for year in years:
                strategy_year = strategy_levels[strategy_levels.index.year == year]
                benchmark_year = benchmark_levels[benchmark_levels.index.year == year]
                correlation, n_obs = _correlation(
                    strategy_weekly[strategy_weekly.index.year == year],
                    benchmark_weekly[benchmark_weekly.index.year == year],
                )
                selected = selection_counts[(selection_counts["year"] == year) & (selection_counts["horizon"] == horizon)]
                selected_symbols = ";".join(
                    f"{row.symbol}({row.selected_months})" for row in selected.itertuples(index=False)
                )
                benchmark_return = float(benchmark_year.iloc[-1] / benchmark_year.iloc[0] - 1.0)
                strategy_return = float(strategy_year.iloc[-1] / strategy_year.iloc[0] - 1.0)
                rows.append(
                    {
                        "year": int(year),
                        "horizon": horizon,
                        "benchmark": benchmark,
                        "correlation": correlation,
                        "n_obs": n_obs,
                        "benchmark_return": benchmark_return,
                        "strategy_return": strategy_return,
                        "excess_return": strategy_return - benchmark_return,
                        "benchmark_mdd": _max_drawdown(benchmark_year),
                        "strategy_mdd": _max_drawdown(strategy_year),
                        "selected_symbols": selected_symbols,
                    }
                )
    return pd.DataFrame(rows, columns=columns)


def run_pilot(
    prices: pd.DataFrame,
    comparison_prices: pd.DataFrame,
    start: pd.Timestamp | str,
    config: RuntimeConfig | None = None,
    symbols: tuple[str, ...] = UNIVERSE,
) -> PilotOutputs:
    missing_assets = [asset for asset in COMPARISON_ASSETS if asset not in comparison_prices.columns]
    if missing_assets:
        raise ValueError(f"comparison_prices missing assets: {missing_assets}")
    start_timestamp = pd.Timestamp(start)
    config = config or RuntimeConfig(fee_rate=0.00015)
    strategies: list[tuple[str, object]] = [(f"Momentum {horizon}M", MarketMomentumStrategy(horizon, symbols)) for horizon in HORIZONS]
    strategies.append(("SPY Buy & Hold", SpyBuyHoldStrategy()))
    results: dict[str, BacktestResult] = {}
    decision_frames: list[pd.DataFrame] = []
    for name, strategy in strategies:
        result = Runtime(strategy, initial_cash=1_000_000.0, config=config).run(prices, start=start_timestamp)
        results[name] = result
        if isinstance(strategy, MarketMomentumStrategy):
            decision_frames.append(pd.DataFrame(strategy.decisions))
    decisions = pd.concat(decision_frames, ignore_index=True) if decision_frames else pd.DataFrame()
    curves = pd.concat([result.performance.rename(name) for name, result in results.items()], axis=1)
    strategy_returns = {
        horizon: _resampled_returns(results[f"Momentum {horizon}M"].performance.loc[lambda series: series.index >= start_timestamp], "weekly")
        for horizon in HORIZONS
    }
    active_assets = comparison_prices.loc[comparison_prices.index >= start_timestamp]
    yearly_asset = _asset_correlation_rows(strategy_returns, active_assets, "weekly", yearly=True)
    overall_asset = pd.concat([
        _asset_correlation_rows(strategy_returns, active_assets, "weekly", yearly=False),
        _asset_correlation_rows(
            {horizon: _resampled_returns(results[f"Momentum {horizon}M"].performance.loc[lambda series: series.index >= start_timestamp], "monthly") for horizon in HORIZONS},
            active_assets,
            "monthly",
            yearly=False,
        ),
    ], ignore_index=True)
    downside_asset = _downside_asset_correlation_rows(strategy_returns, active_assets)
    matrix, constituents = _constituent_outputs(prices, decisions, start_timestamp)
    context = _yearly_strategy_context(results, active_assets, decisions, start_timestamp)
    return PilotOutputs(
        _performance_summary(results), curves, decisions, yearly_asset, overall_asset, downside_asset, matrix, constituents, context
    )
