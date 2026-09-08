from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import pandas as pd

from backtest_lab.analysis import (
    WindowSpec,
    average_monthly_turnover,
    evaluate_windows,
    ffn_stats_table,
    start_end_matrix,
    stat_value,
)
from backtest_lab.core import BacktestResult, Order, Runtime, RuntimeConfig, StrategyContext
from backtest_lab.strategies.us_market_cap_leaders.r01 import (
    QuarterlyMarketCapLeaderStrategy,
    load_rankings,
    required_symbols,
)

TOP1_NAME = "TOP1"
TOP2_NAME = "TOP2"
SPY_NAME = "SPY Buy & Hold"
QQQ_NAME = "QQQ Buy & Hold"

MATRIX_FILE_LABELS = {
    TOP1_NAME: "top1",
    TOP2_NAME: "top2",
    SPY_NAME: "spy",
    QQQ_NAME: "qqq",
}


@dataclass
class BuyAndHoldStrategy:
    symbol: str
    _bought: bool = False

    def on_step(self, context: StrategyContext) -> list[Order]:
        if self._bought:
            return []
        self._bought = True
        total_value = context.portfolio.value(context.prices)
        quantity = total_value / float(context.prices[self.symbol])
        return [Order(symbol=self.symbol, side="buy", quantity=quantity)]


@dataclass(frozen=True)
class BaselineOutputs:
    ffn_stats: pd.DataFrame
    performance_summary: pd.DataFrame
    equity_curves: pd.DataFrame
    yearly_performance: pd.DataFrame
    quarterly_rankings: pd.DataFrame
    quarterly_selections: pd.DataFrame
    fills: pd.DataFrame

    def write_csv(self, output_dir: str | Path) -> dict[str, Path]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        outputs: dict[str, Path] = {}

        self.ffn_stats.to_csv(path / "ffn_stats.csv", index=True, index_label="metric")
        outputs["ffn_stats"] = path / "ffn_stats.csv"
        self.equity_curves.to_csv(path / "equity_curves.csv", index=True, index_label="timestamp")
        outputs["equity_curves"] = path / "equity_curves.csv"

        for name, frame in {
            "performance_summary": self.performance_summary,
            "yearly_performance": self.yearly_performance,
            "quarterly_rankings": self.quarterly_rankings,
            "quarterly_selections": self.quarterly_selections,
            "fills": self.fills,
        }.items():
            frame.to_csv(path / f"{name}.csv", index=False)
            outputs[name] = path / f"{name}.csv"
        return outputs


@dataclass(frozen=True)
class WindowSensitivityOutputs:
    quarterly_rankings: pd.DataFrame
    window_performance: pd.DataFrame
    rolling_summary: pd.DataFrame
    cagr_matrices: Mapping[str, pd.DataFrame] = field(default_factory=dict)

    def write_csv(self, output_dir: str | Path) -> dict[str, Path]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        outputs: dict[str, Path] = {}
        for name, frame in {
            "quarterly_rankings": self.quarterly_rankings,
            "window_performance": self.window_performance,
            "rolling_summary": self.rolling_summary,
        }.items():
            frame.to_csv(path / f"{name}.csv", index=False)
            outputs[name] = path / f"{name}.csv"

        for strategy_name, matrix in self.cagr_matrices.items():
            label = MATRIX_FILE_LABELS[strategy_name]
            filename = f"start_end_cagr_{label}_pct.csv"
            matrix.to_csv(path / filename, index=True, index_label="start_date")
            outputs[f"start_end_cagr_{label}_pct"] = path / filename
        return outputs


def _validate_prices(prices: pd.DataFrame, rankings: pd.DataFrame) -> None:
    missing = [symbol for symbol in required_symbols(rankings) if symbol not in prices.columns]
    if missing:
        raise ValueError(f"prices missing required columns: {missing}")


def _run_four(
    prices: pd.DataFrame,
    start: pd.Timestamp,
    config: RuntimeConfig,
    rankings: pd.DataFrame,
) -> tuple[dict[str, BacktestResult], list[QuarterlyMarketCapLeaderStrategy]]:
    top1 = QuarterlyMarketCapLeaderStrategy(top_n=1, rankings=rankings)
    top2 = QuarterlyMarketCapLeaderStrategy(top_n=2, rankings=rankings)
    strategies: list[tuple[str, object]] = [
        (TOP1_NAME, top1),
        (TOP2_NAME, top2),
        (SPY_NAME, BuyAndHoldStrategy("SPY")),
        (QQQ_NAME, BuyAndHoldStrategy("QQQ")),
    ]
    results: dict[str, BacktestResult] = {}
    for name, strategy in strategies:
        results[name] = Runtime(strategy, initial_cash=1_000_000.0, config=config).run(prices, start=start)
    return results, [top1, top2]


def _summary_row(
    name: str,
    result: BacktestResult,
    stats: pd.Series,
    start: pd.Timestamp,
) -> dict[str, object]:
    active = result.performance.loc[result.performance.index >= start]
    return {
        "strategy": name,
        "start_date": start.date(),
        "end_date": active.index[-1].date(),
        "total_return": stat_value(stats, "total_return"),
        "cagr": stat_value(stats, "cagr"),
        "volatility": stat_value(stats, "daily_vol"),
        "sharpe": stat_value(stats, "daily_sharpe"),
        "sortino": stat_value(stats, "daily_sortino"),
        "max_drawdown": stat_value(stats, "max_drawdown"),
        "calmar": stat_value(stats, "calmar"),
        "avg_monthly_turnover": average_monthly_turnover(result),
    }


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


def _fills(results: Mapping[str, BacktestResult]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name, result in results.items():
        for fill in result.fills:
            rows.append(
                {
                    "strategy": name,
                    "timestamp": fill.timestamp,
                    "symbol": fill.symbol,
                    "side": fill.side,
                    "quantity": fill.quantity,
                    "reference_price": fill.reference_price,
                    "fill_price": fill.fill_price,
                    "fee": fill.fee,
                }
            )
    return pd.DataFrame(
        rows,
        columns=["strategy", "timestamp", "symbol", "side", "quantity", "reference_price", "fill_price", "fee"],
    )


def run_baseline(
    prices: pd.DataFrame,
    start: pd.Timestamp | str,
    config: RuntimeConfig | None = None,
    rankings: pd.DataFrame | None = None,
) -> BaselineOutputs:
    rankings = load_rankings() if rankings is None else rankings.copy()
    rankings["ranking_date"] = pd.to_datetime(rankings["ranking_date"])
    _validate_prices(prices, rankings)
    start_timestamp = pd.Timestamp(start)
    config = config or RuntimeConfig(fee_rate=0.00015)

    results, leader_strategies = _run_four(prices, start_timestamp, config, rankings)
    ffn_table, stats_by_name = ffn_stats_table(results)
    performance_summary = pd.DataFrame(
        [_summary_row(name, result, stats_by_name[name], start_timestamp) for name, result in results.items()]
    )
    curves = pd.concat([result.performance.rename(name) for name, result in results.items()], axis=1)
    selections = pd.DataFrame([decision for strategy in leader_strategies for decision in strategy.decisions])

    return BaselineOutputs(
        ffn_stats=ffn_table,
        performance_summary=performance_summary,
        equity_curves=curves,
        yearly_performance=_yearly_performance(results, start_timestamp),
        quarterly_rankings=rankings.copy(),
        quarterly_selections=selections,
        fills=_fills(results),
    )


def _first_price_after(prices: pd.DataFrame, timestamp: pd.Timestamp) -> pd.Timestamp | None:
    index = pd.DatetimeIndex(prices.index)
    eligible = index[index > timestamp]
    return pd.Timestamp(eligible[0]) if not eligible.empty else None


def _last_price_on_or_before(prices: pd.DataFrame, timestamp: pd.Timestamp) -> pd.Timestamp | None:
    index = pd.DatetimeIndex(prices.index)
    eligible = index[index <= timestamp]
    return pd.Timestamp(eligible[-1]) if not eligible.empty else None


def _add_benchmark_deltas(window_performance: pd.DataFrame) -> pd.DataFrame:
    result = window_performance.copy()
    keys = ["start_date", "end_date"]

    for benchmark_name, suffix in ((SPY_NAME, "spy"), (QQQ_NAME, "qqq")):
        benchmark = result.loc[
            result["strategy"] == benchmark_name,
            [*keys, "cagr", "sharpe", "max_drawdown"],
        ].rename(
            columns={
                "cagr": f"_benchmark_cagr_{suffix}",
                "sharpe": f"_benchmark_sharpe_{suffix}",
                "max_drawdown": f"_benchmark_mdd_{suffix}",
            }
        )
        result = result.merge(benchmark, on=keys, how="left", validate="many_to_one")
        result[f"excess_cagr_vs_{suffix}"] = result["cagr"] - result[f"_benchmark_cagr_{suffix}"]
        result[f"sharpe_delta_vs_{suffix}"] = result["sharpe"] - result[f"_benchmark_sharpe_{suffix}"]
        result[f"mdd_improvement_vs_{suffix}"] = (
            result["max_drawdown"] - result[f"_benchmark_mdd_{suffix}"]
        )
        result = result.drop(
            columns=[
                f"_benchmark_cagr_{suffix}",
                f"_benchmark_sharpe_{suffix}",
                f"_benchmark_mdd_{suffix}",
            ]
        )

    return result


def _rolling_summary(window_performance: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    fixed = window_performance.dropna(subset=["fixed_horizon_years"]).copy()
    for horizon in (3, 5, 10):
        horizon_frame = fixed.loc[fixed["fixed_horizon_years"] == horizon]
        for strategy in (TOP1_NAME, TOP2_NAME):
            strategy_frame = horizon_frame.loc[horizon_frame["strategy"] == strategy]
            if strategy_frame.empty:
                continue
            for benchmark, suffix in ((SPY_NAME, "spy"), (QQQ_NAME, "qqq")):
                excess = strategy_frame[f"excess_cagr_vs_{suffix}"].astype(float)
                sharpe_delta = strategy_frame[f"sharpe_delta_vs_{suffix}"].astype(float)
                mdd_delta = strategy_frame[f"mdd_improvement_vs_{suffix}"].astype(float)
                rows.append(
                    {
                        "window_years": horizon,
                        "strategy": strategy,
                        "benchmark": benchmark,
                        "windows": len(strategy_frame),
                        "median_excess_cagr": float(excess.median()),
                        "p25_excess_cagr": float(excess.quantile(0.25)),
                        "p75_excess_cagr": float(excess.quantile(0.75)),
                        "worst_excess_cagr": float(excess.min()),
                        "best_excess_cagr": float(excess.max()),
                        "cagr_win_rate": float((excess > 0).mean()),
                        "median_sharpe_delta": float(sharpe_delta.median()),
                        "sharpe_win_rate": float((sharpe_delta > 0).mean()),
                        "median_mdd_improvement": float(mdd_delta.median()),
                        "mdd_win_rate": float((mdd_delta > 0).mean()),
                    }
                )
    return pd.DataFrame(rows)


def _build_window_specs(prices: pd.DataFrame, rankings: pd.DataFrame) -> list[WindowSpec]:
    specs: list[WindowSpec] = []
    for start_index, start_row in rankings.iterrows():
        if start_index + 12 >= len(rankings):
            break

        start_ranking_date = pd.Timestamp(start_row["ranking_date"])
        active_start = _first_price_after(prices, start_ranking_date)
        if active_start is None:
            continue

        end_indices = {start_index + 12}
        if start_index + 20 < len(rankings):
            end_indices.update(range(start_index + 20, len(rankings)))
        if start_index + 40 < len(rankings):
            end_indices.add(start_index + 40)

        for end_index in sorted(end_indices):
            end_ranking_date = pd.Timestamp(rankings.iloc[end_index]["ranking_date"])
            end_date = _last_price_on_or_before(prices, end_ranking_date)
            if end_date is None or end_date < active_start:
                continue

            quarter_span = end_index - start_index
            specs.append(
                WindowSpec(
                    start_date=active_start,
                    end_date=end_date,
                    metadata={
                        "start_ranking_date": start_ranking_date.date(),
                        "end_ranking_date": end_ranking_date.date(),
                        "quarter_span": quarter_span,
                        "fixed_horizon_years": {12: 3, 20: 5, 40: 10}.get(quarter_span),
                        "matrix_eligible": quarter_span >= 20,
                    },
                )
            )
    return specs


def run_window_sensitivity(
    prices: pd.DataFrame,
    start: pd.Timestamp | str,
    config: RuntimeConfig | None = None,
    rankings: pd.DataFrame | None = None,
) -> WindowSensitivityOutputs:
    rankings = load_rankings() if rankings is None else rankings.copy()
    rankings["ranking_date"] = pd.to_datetime(rankings["ranking_date"])
    rankings = rankings.sort_values("ranking_date").reset_index(drop=True)
    _validate_prices(prices, rankings)
    config = config or RuntimeConfig(fee_rate=0.00015)

    specs = _build_window_specs(prices, rankings)

    def run_from_start(active_start: pd.Timestamp) -> Mapping[str, BacktestResult]:
        results, _ = _run_four(prices, active_start, config, rankings)
        return results

    window_performance = evaluate_windows(specs, run_from_start)
    window_performance = _add_benchmark_deltas(window_performance)

    cagr_matrices = {
        name: start_end_matrix(
            window_performance,
            strategy=name,
            metric="cagr",
            eligible_column="matrix_eligible",
            scale=100.0,
        )
        for name in (TOP1_NAME, TOP2_NAME, SPY_NAME, QQQ_NAME)
    }

    return WindowSensitivityOutputs(
        quarterly_rankings=rankings.copy(),
        window_performance=window_performance,
        rolling_summary=_rolling_summary(window_performance),
        cagr_matrices=cagr_matrices,
    )
