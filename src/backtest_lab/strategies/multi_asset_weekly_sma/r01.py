"""Independent daily 105-trading-day SMA tests. No multi-asset allocation.

Daily close signals use the reference instrument; fills use the separate
execution instrument next session. Reference-first mode trades reference ETFs
(or the documented price-index proxy); inverse positions hold actual inverse
ETFs, never a mathematically assumed short.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from backtest_lab.analysis import average_monthly_turnover, ffn_stats_table
from backtest_lab.core import BacktestResult, Order, Runtime, RuntimeConfig, StrategyContext
from .line_break import DEFAULT_REVERSAL_LINES, daily_line_break_signals

STRATEGY_ID = "multi_asset_weekly_sma"
REVISION = "r01"
START = "2016-11-21"
END = "2026-11-21"  # exclusive; last fully completed trading day is 2026-11-20
SMA_DAYS = 105
INITIAL_CASH = 1_000_000.0
STRATEGY_ORDER = ("Long/Cash", "Inverse/Cash", "Long/Inverse", "LineBreak Long/Inverse", "Buy & Hold")
SUMMARY_COLUMNS = (
    "strategy", "start_date", "end_date", "total_return", "cagr",
    "volatility", "sharpe", "max_drawdown", "avg_monthly_turnover", "avg_exposure",
)


def daily_sma_signals(reference_close: pd.Series, days: int = SMA_DAYS) -> pd.DataFrame:
    """Daily close / moving average over 105 actual completed trading closes.

    The last 105 *available trading closes* are used, including signal day t.
    Holidays are not filled. All signals are evaluated only AFTER closing;
    any resulting order is executed on the next eligible session's Close.
    """
    if days < 2:
        raise ValueError("days must be >= 2")
    s = reference_close.dropna().sort_index().astype(float)
    if not isinstance(s.index, pd.DatetimeIndex) or s.index.has_duplicates:
        raise ValueError("reference_close requires unique DatetimeIndex")
    if (s <= 0).any():
        raise ValueError("reference close must be positive")
    sma = s.rolling(days, min_periods=days).mean()
    result = pd.DataFrame({"reference_close": s, "sma105": sma})
    result.index.name = "signal_date"
    result["direction"] = pd.Series(0, index=result.index, dtype=int)
    result.loc[s > sma, "direction"] = 1
    result.loc[s < sma, "direction"] = -1
    result["direction"] = result["direction"].where(sma.notna(), 0)
    return result


def _positions_to_orders(context: StrategyContext, symbol: str | None) -> list[Order]:
    owned = context.portfolio.positions
    if symbol is not None and set(owned) == {symbol}:
        return []
    orders = [Order(s, "sell", qty) for s, qty in sorted(owned.items()) if qty > 1e-12]
    if symbol is not None:
        nav = context.portfolio.value(context.prices)
        orders.append(Order(symbol, "buy", nav / float(context.prices[symbol])))
    return orders


@dataclass
class SMARegimeStrategy:
    signals: pd.DataFrame
    long_symbol: str
    inverse_symbol: str | None = None
    inverse_only: bool = False
    decisions: list[dict[str, object]] = field(default_factory=list)
    _last_signal_date: pd.Timestamp | None = None

    def __post_init__(self) -> None:
        if self.inverse_only and not self.inverse_symbol:
            raise ValueError("Inverse/Cash requires an actual inverse ETF symbol")

    def on_step(self, context: StrategyContext) -> list[Order]:
        # Prior session's COMPLETED close only: never inspect today's close
        # or SMA to decide today's fill. searchsorted also keeps daily
        # per-asset execution O(N log N), not O(N^2).
        latest = self.signals.index.searchsorted(context.timestamp, side="left") - 1
        if latest < 0:
            return []
        signal_date = pd.Timestamp(self.signals.index[latest])
        if self._last_signal_date == signal_date:
            return []
        self._last_signal_date = signal_date
        state = self.signals.loc[signal_date]
        direction = int(state["direction"])
        # Inverse/Cash never owns the long ETF: bullish => cash.
        # All bearish positions use the actually priced inverse instrument.
        held = (
            self.long_symbol if direction > 0 and not self.inverse_only
            else self.inverse_symbol if direction < 0
            else None
        )
        orders = _positions_to_orders(context, held)
        record = {
            "signal_date": signal_date, "execution_date": context.timestamp,
            "reference_close": float(state["reference_close"]),
            "sma105": float(state["sma105"]) if "sma105" in state and pd.notna(state["sma105"]) else float("nan"),
            "direction": direction, "held_etf": held or "CASH",
            "changed_position": bool(orders),
        }
        if "line_formed" in state:
            record.update({
                "line_formed": bool(state["line_formed"]),
                "line_break_reversal": bool(state["reversal"]),
                "line_break_close": float(state["line_close"]) if pd.notna(state["line_close"]) else float("nan"),
            })
        self.decisions.append(record)
        return orders


@dataclass
class BuyAndHold:
    symbol: str
    _done: bool = False

    def on_step(self, context: StrategyContext) -> list[Order]:
        if self._done:
            return []
        self._done = True
        return _positions_to_orders(context, self.symbol)


@dataclass(frozen=True)
class AssetInput:
    asset_id: str
    display_name: str
    reference_close: pd.Series
    long_close: pd.Series
    long_symbol: str
    inverse_close: pd.Series | None = None
    inverse_symbol: str | None = None

    def __post_init__(self) -> None:
        if bool(self.inverse_close is not None) != bool(self.inverse_symbol is not None):
            raise ValueError("inverse_close and inverse_symbol must be supplied together")


@dataclass(frozen=True)
class AssetBacktest:
    asset_id: str
    display_name: str
    curves: pd.DataFrame
    performance_summary: pd.DataFrame
    ffn_stats: pd.DataFrame
    signals: pd.DataFrame
    fills: pd.DataFrame
    yearly_performance: pd.DataFrame
    monthly_performance: pd.DataFrame
    line_break_signals: pd.DataFrame


def _clean_prices(series: pd.Series, name: str) -> pd.Series:
    data = series.copy().dropna().astype(float)
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError(f"{name}: missing DatetimeIndex")
    data = data.sort_index()
    if data.index.has_duplicates or (data <= 0).any():
        raise ValueError(f"{name}: invalid prices")
    return data.rename(name)


def run_asset(
    item: AssetInput,
    start: str = START,
    end: str = END,
    config: RuntimeConfig | None = None,
    days: int = SMA_DAYS,
) -> AssetBacktest:
    if not item.asset_id or not item.long_symbol:
        raise ValueError("asset_id and long_symbol are required")
    config = config or RuntimeConfig(fee_rate=0.00015)
    reference = _clean_prices(item.reference_close, "reference")
    reference = reference.loc[reference.index < pd.Timestamp(end)]
    signals = daily_sma_signals(reference, days)
    line_break = daily_line_break_signals(reference, DEFAULT_REVERSAL_LINES)
    # Limit to execution instrument trading dates. Missing dates are never ffilled.
    long = _clean_prices(item.long_close, item.long_symbol)
    long = long.loc[(long.index >= pd.Timestamp(start)) & (long.index < pd.Timestamp(end))]
    if len(long) < 25:
        raise ValueError(f"{item.asset_id}: insufficient domestic ETF observations")
    # If history before ETF inception is unavailable, remain cash until
    # 105 actual reference trading closes exist. No synthetic warm-up.
    if not ((signals["sma105"].notna()) & (signals.index < long.index[-1])).any():
        raise ValueError(f"{item.asset_id}: fewer than 105 reference trading days before last execution")

    prices = long.to_frame()
    mode = SMARegimeStrategy(signals, item.long_symbol)
    runs: dict[str, BacktestResult] = {
        "Long/Cash": Runtime(mode, INITIAL_CASH, config).run(prices),
        "Buy & Hold": Runtime(BuyAndHold(item.long_symbol), INITIAL_CASH, config).run(prices),
    }
    decisions = [("Long/Cash", mode.decisions)]
    if item.inverse_close is not None and item.inverse_symbol is not None:
        inverse = _clean_prices(item.inverse_close, item.inverse_symbol)
        inverse = inverse.loc[(inverse.index >= pd.Timestamp(start)) & (inverse.index < pd.Timestamp(end))]
        both = pd.concat([long, inverse], axis=1).dropna()
        if len(both) >= 25:
            inverse_mode = SMARegimeStrategy(signals, item.long_symbol, item.inverse_symbol)
            runs["Long/Inverse"] = Runtime(inverse_mode, INITIAL_CASH, config).run(both)
            decisions.append(("Long/Inverse", inverse_mode.decisions))
            inverse_cash_mode = SMARegimeStrategy(
                signals, item.long_symbol, item.inverse_symbol, inverse_only=True
            )
            runs["Inverse/Cash"] = Runtime(inverse_cash_mode, INITIAL_CASH, config).run(both)
            decisions.append(("Inverse/Cash", inverse_cash_mode.decisions))
            line_break_mode = SMARegimeStrategy(line_break, item.long_symbol, item.inverse_symbol)
            runs["LineBreak Long/Inverse"] = Runtime(line_break_mode, INITIAL_CASH, config).run(both)
            decisions.append(("LineBreak Long/Inverse", line_break_mode.decisions))

    # Keep the benchmark Buy & Hold last in every archived strategy table,
    # equity curve and Bokeh legend, even when an inverse ETF is unavailable.
    runs = {name: runs[name] for name in STRATEGY_ORDER if name in runs}
    decisions = sorted(decisions, key=lambda pair: STRATEGY_ORDER.index(pair[0]))
    stats, raw = ffn_stats_table(runs)
    summary = []
    fills = []
    for name, result in runs.items():
        stat = raw[name]
        # Reuse canonical FFN metrics and the existing performance-summary column set.
        # Each asset has independent coverage. These are NOT pooled portfolio returns.
        invested = []
        position_qty: dict[str, float] = {}
        by_date: dict[pd.Timestamp, list] = {}
        for fill in result.fills:
            by_date.setdefault(pd.Timestamp(fill.timestamp), []).append(fill)
            fills.append({
                "asset": item.asset_id, "strategy": name, "timestamp": fill.timestamp,
                "symbol": fill.symbol, "side": fill.side, "quantity": fill.quantity,
                "reference_price": fill.reference_price, "fill_price": fill.fill_price,
                "fee": fill.fee,
            })
        current_prices = both if name in ("Long/Inverse", "Inverse/Cash", "LineBreak Long/Inverse") else prices
        for ts, row in current_prices.iterrows():
            for fill in by_date.get(pd.Timestamp(ts), []):
                position_qty[fill.symbol] = position_qty.get(fill.symbol, 0.0) + (
                    fill.quantity if fill.side == "buy" else -fill.quantity
                )
            invested_value = sum(q * float(row[s]) for s, q in position_qty.items())
            invested.append(invested_value / float(result.equity.loc[ts]))
        summary.append({
            "strategy": name,
            "start_date": result.equity.index[0].date(),
            "end_date": result.equity.index[-1].date(),
            "total_return": float(stat["total_return"]),
            "cagr": float(stat["cagr"]),
            "volatility": float(stat["daily_vol"]),
            "sharpe": float(stat["daily_sharpe"]),
            "max_drawdown": float(stat["max_drawdown"]),
            "avg_monthly_turnover": average_monthly_turnover(result),
            "avg_exposure": sum(invested) / len(invested),
        })
    summary_df = pd.DataFrame(summary, columns=SUMMARY_COLUMNS)
    signals_out = pd.concat([
        pd.DataFrame(records).assign(strategy=mode_name)
        for mode_name, records in decisions if records
    ], ignore_index=True) if any(records for _, records in decisions) else pd.DataFrame()
    curves = pd.concat([r.performance.rename(name) for name, r in runs.items()], axis=1)
    yearly_rows = []
    monthly_rows = []
    for name, result in runs.items():
        # Include first trade costs via the Runtime's pre-start anchor.
        # Assign each close-to-close return to its ending calendar year.
        returns = result.performance.pct_change().dropna()
        for year, group in returns.groupby(returns.index.year):
            yearly_rows.append({"strategy": name, "year": int(year),
                                "return": float((1.0 + group).prod() - 1.0)})
        for month, group in returns.groupby(returns.index.to_period("M")):
            monthly_rows.append({"strategy": name, "month": str(month),
                                 "return": float((1.0 + group).prod() - 1.0)})
    yearly = pd.DataFrame(yearly_rows, columns=["strategy", "year", "return"])
    monthly = pd.DataFrame(monthly_rows, columns=["strategy", "month", "return"])
    return AssetBacktest(item.asset_id, item.display_name, curves, summary_df, stats, signals_out,
                         pd.DataFrame(fills), yearly, monthly, line_break)


def write_asset_results(results: list[AssetBacktest], root: str | Path) -> dict[str, Path]:
    """Every asset gets a distinct immutable input/output directory.

    Combined summary is a *projection* of existing per-asset FFN metrics;
    it never recalculates investment performance.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    summary_rows = []
    manifest_rows = []
    yearly_rows = []
    monthly_rows = []
    break_rows = []
    for result in results:
        manifest_rows.append({"asset_id": result.asset_id, "display_name": result.display_name})
        path = root / "assets" / result.asset_id
        path.mkdir(parents=True, exist_ok=True)
        tables = {
            "performance_summary.csv": result.performance_summary,
            "ffn_stats.csv": result.ffn_stats.reset_index(names="metric"),
            "equity_curves.csv": result.curves.reset_index(names="timestamp"),
            "daily_signals.csv": result.signals,
            "line_break_signals.csv": result.line_break_signals.reset_index(),
            "fills.csv": result.fills,
            "yearly_performance.csv": result.yearly_performance,
            "monthly_performance.csv": result.monthly_performance,
        }
        for filename, table in tables.items():
            dest = path / filename
            table.to_csv(dest, index=False)
            paths[f"{result.asset_id}/{filename}"] = dest
        main = result.performance_summary.loc[result.performance_summary["strategy"] == "Long/Cash"].copy()
        main["strategy"] = result.display_name
        summary_rows.append(main)
        yearly_rows.append(result.yearly_performance.assign(asset_id=result.asset_id, asset=result.display_name))
        monthly_rows.append(result.monthly_performance.assign(asset_id=result.asset_id, asset=result.display_name))
        break_rows.append(result.line_break_signals.reset_index().assign(asset_id=result.asset_id))
    if not summary_rows:
        raise ValueError("No successful asset backtests.")
    combined = pd.concat(summary_rows, ignore_index=True).loc[:, SUMMARY_COLUMNS]
    manifest_path = root / "asset_manifest.csv"
    pd.DataFrame(manifest_rows).to_csv(manifest_path, index=False)
    paths["asset_manifest.csv"] = manifest_path
    output = root / "performance_summary.csv"
    combined.to_csv(output, index=False)
    paths["performance_summary.csv"] = output
    yearly_path = root / "yearly_performance.csv"
    pd.concat(yearly_rows, ignore_index=True).loc[:, ["asset_id", "asset", "strategy", "year", "return"]].to_csv(yearly_path, index=False)
    paths["yearly_performance.csv"] = yearly_path
    monthly_path = root / "monthly_performance.csv"
    pd.concat(monthly_rows, ignore_index=True).loc[:, ["asset_id", "asset", "strategy", "month", "return"]].to_csv(monthly_path, index=False)
    paths["monthly_performance.csv"] = monthly_path
    break_path = root / "line_break_signals.csv"
    pd.concat(break_rows, ignore_index=True).to_csv(break_path, index=False)
    paths["line_break_signals.csv"] = break_path
    return paths




@dataclass(frozen=True)
class MultiAssetOutputs:
    assets: tuple[AssetBacktest, ...]
    coverage: pd.DataFrame

    def write_csv(self, output_dir: str | Path) -> dict[str, Path]:
        root = Path(output_dir)
        written = write_asset_results(list(self.assets), root)
        combined_stats = pd.concat([
            r.ffn_stats.rename(columns={c: f"{r.asset_id}::{c}" for c in r.ffn_stats.columns})
            for r in self.assets
        ], axis=1)
        combined_curves = pd.concat([
            r.curves.rename(columns={c: f"{r.asset_id}::{c}" for c in r.curves.columns})
            for r in self.assets
        ], axis=1)
        signal_frames = [
            r.signals.assign(asset_id=r.asset_id)
            for r in self.assets if not r.signals.empty
        ]
        tables = {
            "ffn_stats.csv": combined_stats.reset_index(names="metric"),
            "equity_curves.csv": combined_curves.reset_index(names="timestamp"),
            "daily_signals.csv": pd.concat(signal_frames, ignore_index=True)
            if signal_frames else pd.DataFrame(),
            "fills.csv": pd.concat([r.fills for r in self.assets], ignore_index=True),
            "instrument_coverage.csv": self.coverage,
        }
        for filename, table in tables.items():
            dest = root / filename
            table.to_csv(dest, index=False)
            written[filename] = dest
        return written


def run_pilot(
    prices: pd.DataFrame,
    start: str = START,
    end: str = END,
    config: RuntimeConfig | None = None,
    *, reference_only: bool = False,
) -> MultiAssetOutputs:
    """Run ALL 18 independent underlying-asset studies from saved price data.

    Strict by design: absent assets are failures, not silently excluded from
    research ranking. Comparisons involving inverse ETF periods show each
    strategy's original start/end and must not be called common-window tests.
    """
    from .data import ASSETS, REFERENCE_ASSETS, extract_assets, reference_metadata

    mappings = REFERENCE_ASSETS if reference_only else ASSETS
    inputs = extract_assets(prices, reference_only=reference_only)
    if len(inputs) != len(mappings):
        raise ValueError("Incomplete research universe")
    results = []
    coverage = []
    for item, spec in zip(inputs, mappings, strict=True):
        if item.asset_id != spec.asset_id:
            raise ValueError("Asset order does not match source registry")
        result = run_asset(item, start=start, end=end, config=config)
        if len(result.curves) < 25:
            raise ValueError(f"{item.asset_id}: insufficient result coverage")
        results.append(result)
        coverage.append({
            "asset_id": item.asset_id,
            "display_name": item.display_name,
            "reference_source": spec.reference_source,
            "reference_ticker": spec.reference_ticker,
            "long_etf": spec.long_etf,
            "inverse_etf": spec.inverse_etf or "",
            "proxy_note": spec.proxy_note,
            "study_basis": "reference" if reference_only else "domestic",
            "signal_frequency": "daily",
            "sma_days": SMA_DAYS,
            "line_break_lines": DEFAULT_REVERSAL_LINES,
            "line_break_source": "confirmed daily reference close",
            "signal_evaluation": "confirmed daily close vs SMA105 inclusive",
            "fill_assumption": "following trading session Close; fee/slippage from Runtime",
            **(reference_metadata(item.asset_id) if reference_only else {}),
            "reference_start": item.reference_close.index.min().date(),
            "reference_end": item.reference_close.index.max().date(),
            "long_start": item.long_close.index.min().date(),
            "long_end": item.long_close.index.max().date(),
            "inverse_start": item.inverse_close.index.min().date()
            if item.inverse_close is not None and not item.inverse_close.empty else "",
            "inverse_end": item.inverse_close.index.max().date()
            if item.inverse_close is not None and not item.inverse_close.empty else "",
        })
    return MultiAssetOutputs(tuple(results), pd.DataFrame(coverage))
