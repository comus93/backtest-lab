"""Shared FFN metric table conversion and escaped HTML formatting."""
from __future__ import annotations

from html import escape

import numpy as np
import pandas as pd

from .models import ReportConfig


METRIC_ORDER = ("Total Return", "CAGR", "Sharpe", "Max Drawdown")
PERCENT_METRICS = frozenset({"Total Return", "CAGR", "Max Drawdown"})


def performance_matrix(frame: pd.DataFrame, config: ReportConfig) -> pd.DataFrame:
    """Format numeric FFN results for display, preserving original underlying data."""
    columns = [s.key for s in config.series]
    if not set(METRIC_ORDER) <= set(frame.index) or set(columns) != set(frame.columns):
        raise ValueError("Invalid performance matrix shape")
    display = {"Metric": list(METRIC_ORDER)}
    for series in config.series:
        display[series.table_label or series.label] = [
            (f"{float(frame.loc[metric, series.key]) * 100:+.2f}%"
             if metric in PERCENT_METRICS else
             f"{float(frame.loc[metric, series.key]):.3f}")
            for metric in METRIC_ORDER
        ]
    return pd.DataFrame(display)


def tabular_html(frame: pd.DataFrame, percent_cols: set[str] | None = None) -> str:
    """Compact comparison table appearance, with safe escaped cells."""
    percent_cols = percent_cols or set()
    th = "padding:7px 10px;text-align:right;border-bottom:1px solid #334155;white-space:nowrap;"
    td = "padding:6px 10px;text-align:right;border-bottom:1px solid #e2e8f0;font-variant-numeric:tabular-nums;"
    output = ['<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font:13px system-ui;color:#172033">']
    output.append("<thead><tr>" + "".join(
        f'<th style="{th}">{escape(str(c))}</th>' for c in frame.columns
    ) + "</tr></thead><tbody>")
    for _, row in frame.iterrows():
        cells = []
        for col in frame.columns:
            value = row[col]
            if pd.isna(value):
                formatted = "—"
            elif isinstance(value, (float, np.floating)):
                formatted = f"{value * 100:+.2f}%" if col in percent_cols else f"{value:,.4f}"
            else:
                formatted = str(value)
            cells.append(f'<td style="{td}">{escape(formatted)}</td>')
        output.append("<tr>" + "".join(cells) + "</tr>")
    output.append("</tbody></table></div>")
    return "".join(output)
