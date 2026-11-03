from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import pandas as pd

from backtest_lab.analysis import ffn_stats_table
from backtest_lab.core import BacktestResult, Order, Runtime, RuntimeConfig, StrategyContext

STRATEGY_ID = "psar_segment_duration"
REVISION = "r01"
PSAR_STEP = 0.02
PSAR_MAX = 0.20
INITIAL_CASH = 1_000_000.0
WINDOWS = (
    ("2007-2011", "2007-01-01", "2012-01-01"),
    ("2012-2016", "2012-01-01", "2017-01-01"),
    ("2017-2021", "2017-01-01", "2022-01-01"),
    ("2022-2026", "2022-01-01", "2026-11-04"),
)
REQUIRED_COLUMNS = ("QQQ_High", "QQQ_Low", "QQQ", "QLD", "PSQ")


def calculate_psar(
    high: pd.Series, low: pd.Series, step: float = PSAR_STEP, maximum: float = PSAR_MAX
) -> pd.DataFrame:
    """Causal Parabolic SAR, with two-prior-bar clamps and reversal at the prior EP."""
    if len(high) != len(low) or len(high) < 2 or not high.index.equals(low.index):
        raise ValueError("PSAR requires two or more indexed matching High/Low observations.")
    if not 0 < step <= maximum:
        raise ValueError("PSAR acceleration parameters must satisfy 0 < step <= maximum.")
    if high.isna().any() or low.isna().any() or (high <= 0).any() or (low <= 0).any():
        raise ValueError("PSAR High/Low must be complete and positive.")
    if (high < low).any():
        raise ValueError("PSAR requires High >= Low for every observation.")

    highs, lows = high.astype(float).to_numpy(), low.astype(float).to_numpy()
    up = (highs[1] + lows[1]) >= (highs[0] + lows[0])
    psar = float(lows[0] if up else highs[0])
    extreme = float(highs[0] if up else lows[0])
    af = step
    values = [psar]
    directions = ["UP" if up else "DOWN"]
    for i in range(1, len(highs)):
        candidate = psar + af * (extreme - psar)
        if up:
            candidate = min(candidate, lows[i - 1], lows[i - 2] if i >= 2 else lows[i - 1])
            if lows[i] < candidate:
                up, candidate, extreme, af = False, extreme, float(lows[i]), step
            elif highs[i] > extreme:
                extreme, af = float(highs[i]), min(maximum, af + step)
        else:
            candidate = max(candidate, highs[i - 1], highs[i - 2] if i >= 2 else highs[i - 1])
            if highs[i] > candidate:
                up, candidate, extreme, af = True, extreme, float(highs[i]), step
            elif lows[i] < extreme:
                extreme, af = float(lows[i]), min(maximum, af + step)
        psar = float(candidate)
        values.append(psar)
        directions.append("UP" if up else "DOWN")
    return pd.DataFrame({"psar_value": values, "psar_direction": directions}, index=high.index)


def segment_fields(directions: pd.Series) -> pd.DataFrame:
    """Strict previous-opposite-segment duration, with first seed segment ignored."""
    rows = []
    direction_before: str | None = None
    count = 0
    previous_length: int | None = None
    segment_id = 0
    for direction in directions:
        if direction not in ("UP", "DOWN"):
            raise ValueError("Unknown PSAR direction.")
        if direction != direction_before:
            if direction_before is not None:
                # The very first PSAR segment is seeded and may be incomplete.
                previous_length = count if segment_id >= 2 else None
            direction_before = direction
            count = 0
            segment_id += 1
        count += 1
        rows.append((count, previous_length, previous_length is not None and count > previous_length, segment_id))
    return pd.DataFrame(
        rows, index=directions.index,
        columns=["current_len", "previous_opposite_len", "entry_eligible", "segment_id"],
    )


def build_signals(prices: pd.DataFrame) -> pd.DataFrame:
    psar = calculate_psar(prices["QQQ_High"], prices["QQQ_Low"])
    return psar.join(segment_fields(psar["psar_direction"]))


def _target_weight_orders(context: StrategyContext, target: Mapping[str, float]) -> list[Order]:
    value = context.portfolio.value(context.prices)
    orders = []
    for symbol in sorted(set(context.portfolio.positions) | set(target)):
        desired = value * float(target.get(symbol, 0.0)) / float(context.prices[symbol])
        delta = desired - context.portfolio.quantity(symbol)
        if abs(delta) > 1e-9:
            orders.append(Order(symbol, "buy" if delta > 0 else "sell", abs(delta)))
    return orders


@dataclass
class PSARSegmentDurationStrategy:
    signals: pd.DataFrame
    decisions: list[dict[str, object]] = field(default_factory=list)
    _entered_segment: int | None = None

    def on_step(self, context: StrategyContext) -> list[Order]:
        signal = self.signals.loc[context.timestamp]
        direction = str(signal["psar_direction"])
        symbol = "QLD" if direction == "UP" else "PSQ"
        eligible = bool(signal["entry_eligible"])
        segment_id = int(signal["segment_id"])
        holdings = context.portfolio.positions

        # Buy only once per segment. If a window begins during a qualified
        # trend, start the independent window by entering on its first bar.
        if holdings and symbol not in holdings:
            action = "EXIT_ON_REVERSAL"
            orders = _target_weight_orders(context, {})
            after = "CASH"
        elif not holdings and eligible and self._entered_segment != segment_id:
            action = "ENTER_QLD" if direction == "UP" else "ENTER_PSQ"
            self._entered_segment = segment_id
            orders = _target_weight_orders(context, {symbol: 1.0})
            after = symbol
        else:
            action = "HOLD" if holdings else "CASH"
            orders = []  # Never rebalance or liquidate an unchanged trend.
            after = symbol if holdings else "CASH"

        self.decisions.append({
            "signal_date": context.timestamp,
            "psar_value": float(signal["psar_value"]),
            "psar_direction": direction,
            "current_len": int(signal["current_len"]),
            "previous_opposite_len": signal["previous_opposite_len"],
            "entry_eligible": eligible,
            "held_symbol": after,
            "action": action,
            "bias_note": "same-bar close execution uses full-day High/Low signal (look-ahead)",
        })
        return orders


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
class PSAROutputs:
    ffn_stats: pd.DataFrame
    performance_summary: pd.DataFrame
    equity_curves: pd.DataFrame
    daily_signals: pd.DataFrame
    segment_summary: pd.DataFrame
    yearly_performance: pd.DataFrame
    fills: pd.DataFrame

    def write_csv(self, output_dir: str | Path) -> dict[str, Path]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        tables = {
            "ffn_stats": (self.ffn_stats, True, "metric"),
            "performance_summary": (self.performance_summary, False, None),
            "equity_curves": (self.equity_curves, True, "timestamp"),
            "daily_signals": (self.daily_signals, False, None),
            "segment_summary": (self.segment_summary, False, None),
            "yearly_performance": (self.yearly_performance, False, None),
            "fills": (self.fills, False, None),
        }
        result = {}
        for name, (frame, index, label) in tables.items():
            target = path / f"{name}.csv"
            frame.to_csv(target, index=index, index_label=label)
            result[name] = target
        return result


def _fills(results: Mapping[str, BacktestResult]) -> pd.DataFrame:
    rows = []
    for name, result in results.items():
        window = name.split(" ")[-1]
        for fill in result.fills:
            rows.append({
                "window": window, "strategy": name, "timestamp": fill.timestamp,
                "symbol": fill.symbol, "side": fill.side,
                "quantity": fill.quantity, "reference_price": fill.reference_price,
                "fill_price": fill.fill_price, "fee": fill.fee,
            })
    return pd.DataFrame(rows, columns=[
        "window", "strategy", "timestamp", "symbol", "side",
        "quantity", "reference_price", "fill_price", "fee",
    ])


def run_pilot(prices: pd.DataFrame, config: RuntimeConfig | None = None) -> PSAROutputs:
    missing = sorted(set(REQUIRED_COLUMNS) - set(prices.columns))
    if missing:
        raise ValueError(f"prices missing required columns: {missing}")
    prices = prices.sort_index()
    if prices.index.has_duplicates or prices.isna().any().any():
        raise ValueError("Backtest input must have unique dates and complete prices.")
    if (prices[list(REQUIRED_COLUMNS)] <= 0).any().any():
        raise ValueError("Backtest prices must be positive.")
    config = config or RuntimeConfig()
    signals = build_signals(prices)  # Precomputed strictly from past/current QQQ bars.
    all_results: dict[str, BacktestResult] = {}
    daily_frames = []
    segment_frames = []
    summary_rows = []
    yearly_rows = []

    for window, start, end in WINDOWS:
        sliced = prices.loc[(prices.index >= start) & (prices.index < end)]
        if sliced.empty:
            raise ValueError(f"No active rows for window {window}.")
        # The frame passed to Runtime ends at this window boundary, never 2026
        # for 2007-2011. Signal state, however, retains the 2006 warm-up.
        strategy = PSARSegmentDurationStrategy(signals)
        runs = {
            f"PSAR {window}": Runtime(strategy, INITIAL_CASH, config).run(sliced),
            f"QLD Buy & Hold {window}": Runtime(BuyAndHoldStrategy("QLD"), INITIAL_CASH, config).run(sliced),
            f"QQQ Buy & Hold {window}": Runtime(BuyAndHoldStrategy("QQQ"), INITIAL_CASH, config).run(sliced),
        }
        all_results.update(runs)
        decisions = pd.DataFrame(strategy.decisions)
        decisions.insert(0, "window", window)
        daily_frames.append(decisions)
        counted = signals.loc[sliced.index].copy()
        segment_frames.append(pd.DataFrame([{
            "window": window, "direction": direction,
            "segments": int(group["segment_id"].nunique()),
            "observations": len(group),
            "max_length": int(group["current_len"].max()),
        } for direction, group in counted.groupby("psar_direction")]))

        for name, result in runs.items():
            returns = result.performance.pct_change().dropna()
            for year, group in returns.groupby(returns.index.year):
                curve = (1.0 + group).cumprod()
                yearly_rows.append({
                    "window": window, "year": int(year), "strategy": name,
                    "return": float(curve.iloc[-1] - 1.0),
                    "max_drawdown": float((curve / pd.concat([
                        pd.Series([1.0], index=[curve.index[0] - pd.Timedelta(nanoseconds=1)]), curve
                    ]).cummax().loc[curve.index] - 1.0).min()),
                })

    stats, raw = ffn_stats_table(all_results)
    for name, result in all_results.items():
        window = name.split(" ")[-1]
        row = raw[name]
        summary_rows.append({
            "window": window, "strategy": name,
            "start_date": result.equity.index[0].date(),
            "end_date": result.equity.index[-1].date(),
            "total_return": float(row.get("total_return", float("nan"))),
            "cagr": float(row.get("cagr", float("nan"))),
            "sharpe": float(row.get("daily_sharpe", float("nan"))),
            "max_drawdown": float(row.get("max_drawdown", float("nan"))),
        })
    return PSAROutputs(
        stats, pd.DataFrame(summary_rows),
        pd.concat([r.performance.rename(n) for n, r in all_results.items()], axis=1),
        pd.concat(daily_frames, ignore_index=True),
        pd.concat(segment_frames, ignore_index=True),
        pd.DataFrame(yearly_rows), _fills(all_results),
    )
