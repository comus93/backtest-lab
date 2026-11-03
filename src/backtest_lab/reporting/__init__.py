"""Read-only reporting subsystem: archived metrics + canonical data -> static HTML."""

from .models import (OverlayConfig, ReportConfig, ReportData, ReportPeriod, SeriesConfig)
from .palette import DEFAULT_PALETTE, ReportPalette
from .render import render_report

__all__ = [
    "OverlayConfig", "ReportConfig", "ReportData", "ReportPalette",
    "ReportPeriod", "SeriesConfig", "DEFAULT_PALETTE", "render_report",
]
