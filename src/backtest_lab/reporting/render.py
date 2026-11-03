"""Compose a standalone Bokeh HTML report from canonical data and configuration."""
from __future__ import annotations

from html import escape
from pathlib import Path

from .charts import build_charts
from .models import ReportConfig, ReportData
from .tables import performance_matrix, tabular_html


def render_report(data: ReportData, config: ReportConfig, destination: str | Path) -> Path:
    from bokeh.embed import file_html
    from bokeh.layouts import column
    from bokeh.models import Div, TabPanel, Tabs
    from bokeh.resources import INLINE

    data.validate(config)
    summary_html = "".join(
        f'<h3 style="font-size:14px;margin:18px 0 6px">{escape(period.window)}</h3>'
        + tabular_html(performance_matrix(period.performance, config))
        for period in data.periods
    )
    intro = Div(text=(
        '<div style="font-family:system-ui;padding:10px 6px;color:#172033">'
        f'<h1 style="font-size:25px;margin:0">{escape(config.title)}</h1>'
        f'<p style="color:#475569">{escape(config.subtitle)}</p>'
        f'<p style="color:#475569">{escape(config.interaction_note)}</p>'
        f'<p style="color:#9a3412">{escape(config.caution)}</p>'
        f'<h2 style="font-size:18px">{escape(config.performance_heading)}</h2>'
        + summary_html + '</div>'
    ), sizing_mode="stretch_width")
    tabs = []
    for period in data.periods:
        rendered = performance_matrix(period.performance, config)
        per_period = Div(text=(
            f'<div style="font-family:system-ui"><h3>{escape(period.window)}: Performance</h3>'
            + tabular_html(rendered) + '</div>'
        ), sizing_mode="stretch_width")
        children = [per_period, build_charts(period, config)]
        if config.show_raw_ffn:
            header = Div(text=(
                f'<div style="font-family:system-ui"><h3>{escape(period.window)}: FFN result matrix (raw)</h3>'
                f'<p style="color:#64748b;font-size:12px">{escape(config.raw_ffn_note)}</p>'
                + tabular_html(period.ffn_stats) + '</div>'
            ), sizing_mode="stretch_width")
            children.append(header)
        tabs.append(TabPanel(child=column(*children, sizing_mode="stretch_width"),
                             title=period.window))
    layout = column(intro, Tabs(tabs=tabs, sizing_mode="stretch_width"),
                    sizing_mode="stretch_width")
    html = file_html(layout, INLINE, title=config.page_title)
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    return dest
