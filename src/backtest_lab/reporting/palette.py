"""Stable report colors; strategy series colors are selected by ReportConfig."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReportPalette:
    bullish: str = "#E53935"
    bearish: str = "#1E88E5"
    monthly_bullish: str = "#E8A09D"
    monthly_bearish: str = "#9DBFDF"
    buy: str = "#16A34A"
    sell: str = "#DC2626"
    profit: str = "#16A34A"
    loss: str = "#DC2626"
    trade_span_profit: str = "#24954E"
    trade_span_loss: str = "#AD2960"
    grid: str = "#94A3B8"
    wick: str = "#64748B"


DEFAULT_PALETTE = ReportPalette()
# Shared palette mapping for callers needing key-based color access.
COLORS = {name: getattr(DEFAULT_PALETTE, name)
          for name in DEFAULT_PALETTE.__dataclass_fields__}
DAY_MS = 24 * 60 * 60 * 1000
