"""Read-only reporting subsystem: archived metrics + canonical data -> static HTML."""

from .models import (OverlayConfig, ReportConfig, ReportData, ReportPeriod, SeriesConfig)
from .palette import DEFAULT_PALETTE, ReportPalette
from .render import render_report  # legacy PSAR-compatible entrypoint
from .composer import ChartComposer, Glyph, Layer, line_layer, candle_layer, line_break_layer

__all__ = [
    "ChartComposer", "Glyph", "Layer", "line_layer", "candle_layer", "line_break_layer",
    "OverlayConfig", "ReportConfig", "ReportData", "ReportPalette",
    "ReportPeriod", "SeriesConfig", "DEFAULT_PALETTE", "render_report",
]
