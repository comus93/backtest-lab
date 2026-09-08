from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import pandas as pd

from backtest_lab.analysis import average_monthly_turnover
from backtest_lab.core import BacktestResult, Runtime, RuntimeConfig, StrategyContext, Order
from backtest_lab.strategies.us_market_cap_leaders.r01 import (
    QuarterlyMarketCapLeaderStrategy,
    load_rankings,
    required_symbols,
)

TOP1_NAME = "TOP1"
TOP2_NAME = "TOP2"
SPY_NAME = "SPY Buy & Hold"
QQQ_NAME = "QQQ Buy & Hold"


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


def _raw_stats(series: pd.Series) -> pd.Series:
    import ffn  # noqa: F401

    stats_object = series.calc_stats()
    raw = getattr(stats_object, "stats", None)
    if raw is None:
        raise ValueError("FFN calc_stats() result does not expose .stats.")
    return pd.Series(raw)


def _stat(stats: pd.Series, key: str) -> float:
    if key not in stats.index:
        return float("nan")
    try:
        return float(stats.loc[key])
    except (TypeError, ValueError):
        return float("nan")


def _ffn_stats(results: Mapping[str, BacktestResult]) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    columns = {name: _raw_stats(result.performance) for name, result in results.items()}
    return pd.concat(columns, axis=1), columns


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
        "total_return": _stat(stats, "total_return"),
        "cagr": _stat(stats, "cagr"),
        "volatility": _stat(stats, "daily_vol"),
        "sharpe": _stat(stats, "daily_sharpe"),
        "sortino": _stat(stats, "daily_sortino"),
        "max_drawdown": _stat(stats, "max_drawdown"),
        "calmar": _stat(stats, "calmar"),
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
    ffn_table, stats_by_name = _ffn_stats(results)
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


def _window_metrics(series: pd.Series, end_date: pd.Timestamp) -> dict[str, float]:
    sliced = series.loc[series.index <= end_date]
    if len(sliced) < 2:
        raise ValueError("window must contain at least two performance observations.")
    stats = _raw_stats(sliced)
    return {
        "total_return": _stat(stats, "total_return"),
        "cagr": _stat(stats, "cagr"),
        "volatility": _stat(stats, "daily_vol"),
        "sharpe": _stat(stats, "daily_sharpe"),
        "sortino": _stat(stats, "daily_sortino"),
        "max_drawdown": _stat(stats, "max_drawdown"),
        "calmar": _stat(stats, "calmar"),
    }


def _window_rows(
    results: Mapping[str, BacktestResult],
    start_ranking_date: pd.Timestamp,
    start_date: pd.Timestamp,
    end_ranking_date: pd.Timestamp,
    end_date: pd.Timestamp,
    quarter_span: int,
) -> list[dict[str, object]]:
    metrics = {name: _window_metrics(result.performance, end_date) for name, result in results.items()}
    fixed_horizon = {12: 3, 20: 5, 40: 10}.get(quarter_span)
    rows: list[dict[str, object]] = []
    for name, values in metrics.items():
        row: dict[str, object] = {
            "start_ranking_date": start_ranking_date.date(),
            "start_date": start_date.date(),
            "end_ranking_date": end_ranking_date.date(),
            "end_date": end_date.date(),
            "quarter_span": quarter_span,
            "fixed_horizon_years": fixed_horizon,
            "matrix_eligible": quarter_span >= 20,
            "strategy": name,
            **values,
        }
        spy = metrics[SPY_NAME]
        qqq = metrics[QQQ_NAME]
        row.update(
            {
                "excess_cagr_vs_spy": values["cagr"] - spy["cagr"],
                "excess_cagr_vs_qqq": values["cagr"] - qqq["cagr"],
                "sharpe_delta_vs_spy": values["sharpe"] - spy["sharpe"],
                "sharpe_delta_vs_qqq": values["sharpe"] - qqq["sharpe"],
                "mdd_improvement_vs_spy": values["max_drawdown"] - spy["max_drawdown"],
                "mdd_improvement_vs_qqq": values["max_drawdown"] - qqq["max_drawdown"],
            }
        )
        rows.append(row)
    return rows


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

    rows: list[dict[str, object]] = []
    for start_index, start_row in rankings.iterrows():
        if start_index + 12 >= len(rankings):
            break
        start_ranking_date = pd.Timestamp(start_row["ranking_date"])
        active_start = _first_price_after(prices, start_ranking_date)
        if active_start is None:
            continue
        results, _ = _run_four(prices, active_start, config, rankings)

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
            rows.extend(
                _window_rows(
                    results,
                    start_ranking_date=start_ranking_date,
                    start_date=active_start,
                    end_ranking_date=end_ranking_date,
                    end_date=end_date,
                    quarter_span=end_index - start_index,
                )
            )

    window_performance = pd.DataFrame(rows)
    return WindowSensitivityOutputs(
        quarterly_rankings=rankings.copy(),
        window_performance=window_performance,
        rolling_summary=_rolling_summary(window_performance),
    )
