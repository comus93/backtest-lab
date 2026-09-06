from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import pandas as pd

from backtest_lab.analysis import average_monthly_turnover
from backtest_lab.core import BacktestResult, Order, Runtime, RuntimeConfig, StrategyContext

STRATEGY_ID = "sp500_top2_market_cap"
REVISION = "r01"

START = "2016-01-01"
END_EXCLUSIVE = "2026-01-01"
REQUIRED_COLUMNS = ("AAPL", "GOOGL", "MSFT", "NVDA", "SPY")

TOP2_BY_YEAR: dict[int, tuple[str, str]] = {
    2016: ("AAPL", "GOOGL"),
    2017: ("AAPL", "GOOGL"),
    2018: ("AAPL", "GOOGL"),
    2019: ("MSFT", "AAPL"),
    2020: ("AAPL", "MSFT"),
    2021: ("AAPL", "MSFT"),
    2022: ("AAPL", "MSFT"),
    2023: ("AAPL", "MSFT"),
    2024: ("AAPL", "MSFT"),
    2025: ("AAPL", "NVDA"),
}

COMPANY_NAMES = {
    "AAPL": "Apple",
    "GOOGL": "Alphabet",
    "MSFT": "Microsoft",
    "NVDA": "Nvidia",
}


def _target_weight_orders(
    context: StrategyContext,
    target_weights: Mapping[str, float],
    tolerance: float = 1e-9,
) -> list[Order]:
    total_value = context.portfolio.value(context.prices)
    symbols = sorted(set(context.portfolio.positions) | set(target_weights))
    orders: list[Order] = []
    for symbol in symbols:
        target_quantity = (total_value * float(target_weights.get(symbol, 0.0))) / float(context.prices[symbol])
        difference = target_quantity - context.portfolio.quantity(symbol)
        if abs(difference) <= tolerance:
            continue
        orders.append(Order(symbol=symbol, side="buy" if difference > 0 else "sell", quantity=abs(difference)))
    return orders


@dataclass
class AnnualTop2MarketCapStrategy:
    selections: Mapping[int, tuple[str, str]] = field(default_factory=lambda: dict(TOP2_BY_YEAR))
    decisions: list[dict[str, object]] = field(default_factory=list)
    _last_rebalance_year: int | None = None

    def on_step(self, context: StrategyContext) -> list[Order]:
        timestamp = pd.Timestamp(context.timestamp)
        year = timestamp.year
        if year not in self.selections:
            return []
        if self._last_rebalance_year == year:
            return []

        rank1, rank2 = self.selections[year]
        target = {rank1: 0.5, rank2: 0.5}
        self._last_rebalance_year = year
        self.decisions.append(
            {
                "investment_year": year,
                "ranking_basis_year": year - 1,
                "execution_date": timestamp,
                "rank1_company": COMPANY_NAMES[rank1],
                "rank1_ticker": rank1,
                "rank2_company": COMPANY_NAMES[rank2],
                "rank2_ticker": rank2,
                "rank1_weight": 0.5,
                "rank2_weight": 0.5,
            }
        )
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
class Top2Outputs:
    ffn_stats: pd.DataFrame
    performance_summary: pd.DataFrame
    equity_curves: pd.DataFrame
    yearly_performance: pd.DataFrame
    annual_selections: pd.DataFrame
    fills: pd.DataFrame

    def write_csv(self, output_dir: str | Path) -> dict[str, Path]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        outputs: dict[str, Path] = {}

        tables = {
            "performance_summary": (self.performance_summary, False, None),
            "yearly_performance": (self.yearly_performance, False, None),
            "annual_selections": (self.annual_selections, False, None),
            "fills": (self.fills, False, None),
        }
        for name, (table, use_index, index_label) in tables.items():
            file_path = path / f"{name}.csv"
            table.to_csv(file_path, index=use_index, index_label=index_label)
            outputs[name] = file_path

        ffn_path = path / "ffn_stats.csv"
        self.ffn_stats.to_csv(ffn_path, index=True, index_label="metric")
        outputs["ffn_stats"] = ffn_path

        curves_path = path / "equity_curves.csv"
        self.equity_curves.to_csv(curves_path, index=True, index_label="timestamp")
        outputs["equity_curves"] = curves_path
        return outputs


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
    try:
        return float(series.loc[key])
    except (TypeError, ValueError):
        return float("nan")


def _performance_summary(
    results: Mapping[str, BacktestResult],
    stats_by_name: Mapping[str, pd.Series],
    start: pd.Timestamp,
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
                "avg_nominal_exposure": 1.0,
            }
        )
    return pd.DataFrame(rows)


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
        columns=[
            "strategy",
            "timestamp",
            "symbol",
            "side",
            "quantity",
            "reference_price",
            "fill_price",
            "fee",
        ],
    )


def run_pilot(
    prices: pd.DataFrame,
    start: pd.Timestamp | str,
    config: RuntimeConfig | None = None,
) -> Top2Outputs:
    missing = [column for column in REQUIRED_COLUMNS if column not in prices.columns]
    if missing:
        raise ValueError(f"prices missing required columns: {missing}")

    start_timestamp = pd.Timestamp(start)
    if start_timestamp.year != 2016:
        raise ValueError("r01 active period must start in 2016.")
    if pd.Timestamp(prices.index[-1]).year != 2025:
        raise ValueError("r01 price coverage must end in 2025.")

    config = config or RuntimeConfig(fee_rate=0.00015)
    top2 = AnnualTop2MarketCapStrategy()
    strategies: list[tuple[str, object]] = [
        ("S&P 500 Top-2 Market Cap", top2),
        ("SPY Buy & Hold", BuyAndHoldStrategy("SPY")),
    ]

    results: dict[str, BacktestResult] = {}
    for name, strategy in strategies:
        results[name] = Runtime(strategy, initial_cash=1_000_000.0, config=config).run(prices, start=start_timestamp)

    curves = pd.concat([result.performance.rename(name) for name, result in results.items()], axis=1)
    ffn_table, stats_by_name = _ffn_stats(results)
    decisions = pd.DataFrame(top2.decisions)

    return Top2Outputs(
        ffn_stats=ffn_table,
        performance_summary=_performance_summary(results, stats_by_name, start_timestamp),
        equity_curves=curves,
        yearly_performance=_yearly_performance(results, start_timestamp),
        annual_selections=decisions,
        fills=_fills(results),
    )
