"""Canonical read-only input contract for Bokeh/FFN reporting.

Frozen dataclasses do not deep-freeze pandas objects; callers must treat frames
as immutable report inputs. Adapters copy source slices before constructing them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .palette import DEFAULT_PALETTE, ReportPalette


@dataclass(frozen=True, slots=True)
class SeriesConfig:
    key: str
    label: str
    color: str
    width: float = 1.5
    table_label: str | None = None


@dataclass(frozen=True, slots=True)
class OverlayConfig:
    field: str
    label: str
    color: str
    marker: str = "circle"
    size: int = 3


@dataclass(frozen=True, slots=True)
class ReportConfig:
    title: str
    page_title: str
    subtitle: str
    interaction_note: str
    caution: str
    signal_symbol: str
    execution_symbol: str
    display_symbol: str
    price_title: str
    series: tuple[SeriesConfig, ...]
    performance_heading: str = "Period performance"
    raw_ffn_note: str = "Raw FFN values are shown without unit conversion."
    pnl_net_label: str = "Net"
    price_currency: str = ""
    overlays: tuple[OverlayConfig, ...] = ()
    price_hover_fields: tuple[tuple[str, str], ...] = ()
    palette: ReportPalette = DEFAULT_PALETTE
    equity_title: str = "Equity | strategy vs benchmarks (performance index)"
    pnl_title: str = "Profit / Loss"
    drawdown_title: str = "Strategy drawdown (%)"
    show_volume: bool = False
    show_monthly: bool = True
    show_trades: bool = True
    show_raw_ffn: bool = True


@dataclass(frozen=True, slots=True)
class ReportPeriod:
    window: str
    prices: pd.DataFrame
    equity: pd.DataFrame
    performance: pd.DataFrame
    ffn_stats: pd.DataFrame
    indicators: pd.DataFrame = field(default_factory=pd.DataFrame)
    events: pd.DataFrame = field(default_factory=pd.DataFrame)
    trades: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass(frozen=True, slots=True)
class ReportData:
    periods: tuple[ReportPeriod, ...]

    def validate(self, config: ReportConfig) -> None:
        if not self.periods:
            raise ValueError("ReportData has no periods")
        keys = [s.key for s in config.series]
        if not keys or len(set(keys)) != len(keys):
            raise ValueError("ReportConfig requires unique non-empty series keys")
        if any(not s.key or not s.label for s in config.series):
            raise ValueError("ReportConfig series require a key and label")
        if len({p.window for p in self.periods}) != len(self.periods):
            raise ValueError("Duplicate report period labels")
        for period in self.periods:
            prices = period.prices
            for frame, label in ((prices, "prices"), (period.equity, "equity")):
                if not isinstance(frame.index, pd.DatetimeIndex):
                    raise ValueError(f"{period.window}: {label} must have datetime index")
                if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
                    raise ValueError(f"{period.window}: {label} timestamps must be sorted/unique")
                if frame.empty:
                    raise ValueError(f"{period.window}: {label} is empty")
            if not prices.index.equals(period.equity.index):
                raise ValueError(f"{period.window}: equity and price dates differ")
            if not set(("Open", "High", "Low", "Close")) <= set(prices.columns):
                raise ValueError(f"{period.window}: OHLC columns missing")
            if set(keys) != set(period.equity.columns):
                raise ValueError(f"{period.window}: equity keys do not match configuration")
            if set(keys) != set(period.performance.columns):
                raise ValueError(f"{period.window}: performance keys do not match configuration")
            if not {"Total Return", "CAGR", "Sharpe", "Max Drawdown"} <= set(period.performance.index):
                raise ValueError(f"{period.window}: missing canonical performance metrics")
            if list(period.ffn_stats.columns) != ["metric", *keys]:
                raise ValueError(f"{period.window}: raw FFN matrix keys do not match configuration")
            if period.indicators is not None and not period.indicators.empty:
                if not period.indicators.index.equals(prices.index):
                    raise ValueError(f"{period.window}: indicator dates differ from price dates")
            required_numeric = prices.loc[:, ["Open", "High", "Low", "Close"]]
            if not np.isfinite(required_numeric.to_numpy(dtype=float)).all():
                raise ValueError(f"{period.window}: invalid OHLC values")
            if (required_numeric <= 0).any().any():
                raise ValueError(f"{period.window}: OHLC prices must be positive")
            if (prices["High"] < prices[["Open", "Close"]].max(axis=1)).any():
                raise ValueError(f"{period.window}: High is below Open or Close")
            if (prices["Low"] > prices[["Open", "Close"]].min(axis=1)).any():
                raise ValueError(f"{period.window}: Low is above Open or Close")
            if not np.isfinite(period.performance.to_numpy(dtype=float)).all():
                raise ValueError(f"{period.window}: non-finite FFN performance metrics")
            if not np.isfinite(period.equity.to_numpy(dtype=float)).all():
                raise ValueError(f"{period.window}: invalid equity values")
            if config.show_volume:
                if "Volume" not in prices:
                    raise ValueError("Volume data is required when show_volume=True")
                vol = prices["Volume"].to_numpy(dtype=float)
                if not np.isfinite(vol).all() or (vol < 0).any():
                    raise ValueError(f"{period.window}: Volume is invalid")
            for overlay in config.overlays:
                if overlay.field not in period.indicators.columns:
                    raise ValueError(f"{period.window}: missing overlay field {overlay.field}")
            if config.show_trades:
                required_event = {"date", "display_price", "symbol", "side", "price", "qty", "fee"}
                required_trade = {"date", "entry_date", "entry_display_price",
                                  "exit_display_price", "return_pct", "pnl", "win", "symbol"}
                if not required_event <= set(period.events.columns):
                    raise ValueError(f"{period.window}: execution event fields missing")
                if not required_trade <= set(period.trades.columns):
                    raise ValueError(f"{period.window}: completed trade fields missing")
