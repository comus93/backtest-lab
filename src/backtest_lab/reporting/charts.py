"""Reusable interactive Bokeh charts driven solely by ReportPeriod/ReportConfig."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .models import ReportConfig, ReportPeriod
from .palette import DAY_MS, DEFAULT_PALETTE, ReportPalette


def monthly_candles(candles: pd.DataFrame, palette: ReportPalette = DEFAULT_PALETTE) -> pd.DataFrame:
    """Aggregate display-instrument daily OHLC into direction-colored monthly bodies."""
    rows = []
    for _, group in candles.groupby(pd.Grouper(freq="MS")):
        if group.empty:
            continue
        opening = float(group["Open"].iloc[0])
        closing = float(group["Close"].iloc[-1])
        rows.append({
            "date": group.index[len(group) // 2],
            "high": float(group["High"].max()), "low": float(group["Low"].min()),
            "top": max(opening, closing), "bottom": min(opening, closing),
            "width": max(len(group) - 1, 1) * DAY_MS,
            "color": palette.monthly_bullish if closing >= opening else palette.monthly_bearish,
        })
    return pd.DataFrame(rows, columns=["date", "high", "low", "top", "bottom", "width", "color"])


def build_charts(period: ReportPeriod, config: ReportConfig):
    """Bokeh, written independently to reproduce backtesting.py-like navigation."""
    from bokeh.events import MouseLeave, MouseMove
    from bokeh.layouts import column
    from bokeh.models import (ColumnDataSource, CrosshairTool, CustomJS, HoverTool,
                              Label, NumeralTickFormatter, Range1d)
    from bokeh.plotting import figure

    candles = period.prices
    curves = period.equity
    fills, trades = period.events, period.trades
    palette = config.palette
    combined = candles.join(period.indicators)
    combined["date"] = combined.index
    combined["bullish"] = combined["Close"] >= combined["Open"]
    combined["color"] = np.where(combined["bullish"], palette.bullish, palette.bearish)
    combined["top"] = combined[["Open", "Close"]].max(axis=1)
    combined["bottom"] = combined[["Open", "Close"]].min(axis=1)
    source = ColumnDataSource(combined)

    x_range = Range1d(start=candles.index.min()-pd.Timedelta(days=15),
                      end=candles.index.max()+pd.Timedelta(days=15))
    tools = "xpan,xwheel_zoom,box_zoom,reset,save"

    def new_fig(title: str, height: int, x_axis: bool = False):
        fig = figure(
            title=title, height=height, sizing_mode="stretch_width",
            x_axis_type="datetime", x_range=x_range,
            tools=tools, active_scroll="xwheel_zoom", toolbar_location="right",
            output_backend="canvas",
        )
        fig.add_tools(CrosshairTool(dimensions="height", line_alpha=0.4))
        fig.grid.grid_line_color = palette.grid
        fig.grid.grid_line_alpha = 0.20
        fig.grid.grid_line_width = 1
        fig.xaxis.visible = x_axis
        fig.yaxis.axis_label_text_font_size = "11px"
        fig.title.text_font_size = "12px"
        return fig

    equity = new_fig(config.equity_title, 180)
    equity_frame = curves.assign(date=curves.index)
    eq_source = ColumnDataSource(equity_frame)
    equity_lines = []
    for series in config.series:
        key, label = series.key, series.label
        line = equity.line("date", key, source=eq_source, line_width=series.width,
                           color=series.color, legend_label=label, name=label)
        equity_lines.append(line)
    # Native Bokeh HoverTool resolves each renderer independently, which can
    # show several tooltips when curves overlap. Pick exactly one curve here.
    hover_point = ColumnDataSource(data={"date": [], "value": [], "color": []})
    equity.scatter("date", "value", source=hover_point, marker="circle", size=8,
                   fill_color="color", line_color="#ffffff", line_width=1)
    hover_label = Label(x=0, y=0, text="", visible=False, x_offset=12, y_offset=12,
                        text_font_size="11px", background_fill_color="#ffffff",
                        background_fill_alpha=0.95, border_line_color=palette.grid,
                        padding=5)
    equity.add_layout(hover_label)
    hover_code = """
        const times = source.data.date;
        const x = cb_obj.x;
        if (!times.length || !Number.isFinite(x) ||
            x < times[0] || x > times[times.length - 1]) {
            label.visible = false;
            point.data = {date: [], value: [], color: []};
            return;
        }
        let lo = 0, hi = times.length - 1;
        while (hi - lo > 1) {
            const mid = (lo + hi) >>> 1;
            if (times[mid] <= x) lo = mid; else hi = mid;
        }
        const fraction = times[hi] === times[lo] ? 0 :
                         (x - times[lo]) / (times[hi] - times[lo]);
        const choices = __CHOICES__;
        let nearest = null;
        for (let i = 0; i < choices.length; i++) {
            if (!lines[i].visible) continue;
            const [key, name, color] = choices[i];
            const values = source.data[key];
            const y = values[lo] + (values[hi] - values[lo]) * fraction;
            const distance = Math.abs(y - cb_obj.y);
            if (!Number.isFinite(distance)) continue;
            if (nearest === null || distance < nearest.distance)
                nearest = {name, color, y, distance};
        }
        if (nearest === null) {
            label.visible = false;
            point.data = {date: [], value: [], color: []};
            return;
        }
        label.x = x;
        label.y = nearest.y;
        label.text = `${new Date(x).toISOString().slice(0, 10)} | ` +
                     `${nearest.name}: ${nearest.y.toFixed(2)}`;
        label.visible = true;
        point.data = {date: [x], value: [nearest.y], color: [nearest.color]};
    """
    hover_code = hover_code.replace(
        "__CHOICES__", json.dumps([[s.key, s.label, s.color] for s in config.series])
    )
    equity.js_on_event(MouseMove, CustomJS(
        args={"source": eq_source, "lines": equity_lines,
              "label": hover_label, "point": hover_point}, code=hover_code,
    ))
    equity.js_on_event(MouseLeave, CustomJS(
        args={"label": hover_label, "point": hover_point},
        code="label.visible = false; point.data = {date: [], value: [], color: []};",
    ))
    equity.legend.location = "top_left"
    equity.legend.click_policy = "hide"
    equity.yaxis.axis_label = "Performance (start 100)"

    drawdown = new_fig(config.drawdown_title, 125)
    strategy_equity = curves[config.series[0].key]
    dd = (strategy_equity / strategy_equity.cummax() - 1.0) * 100.0
    dd_frame = pd.DataFrame({"date": curves.index, "drawdown": dd.to_numpy()})
    dd_source = ColumnDataSource(dd_frame)
    dd_line = drawdown.line("date", "drawdown", source=dd_source, color=palette.sell, line_width=1.8)
    drawdown.varea(x="date", y1=0, y2="drawdown", source=dd_source, color=palette.sell, fill_alpha=0.10)
    drawdown.add_tools(HoverTool(
        renderers=[dd_line], tooltips=[("Date", "@date{%F}"), ("Drawdown", "@drawdown{0.00}%")],
        formatters={"@date": "datetime"}, mode="vline",
    ))
    drawdown.yaxis.axis_label = "%"

    pnl = new_fig(config.pnl_title, 110)
    if not trades.empty:
        markers = trades.copy()
        markers["color"] = np.where(markers["win"], palette.profit, palette.loss)
        trade_source = ColumnDataSource(markers)
        result = pnl.scatter("date", "return_pct", source=trade_source, marker="triangle",
                             size=9, color="color", line_color="#333333")
        pnl.add_tools(HoverTool(renderers=[result], tooltips=[
            ("Exit", "@date{%F}"), ("Entry", "@entry_date{%F}"),
            (f"Net {config.execution_symbol} P/L", "@return_pct{+0.00}%"),
            (config.pnl_net_label, "@pnl{0,0.00}"),
        ], formatters={"@date": "datetime", "@entry_date": "datetime"}))
    pnl.yaxis.axis_label = "%"

    if config.show_volume and "Volume" not in candles.columns:
        raise ValueError(f"{config.display_symbol}_Volume data is required when show_volume=True")
    price = new_fig(config.price_title, 430, not config.show_volume)
    monthly = monthly_candles(candles, palette) if config.show_monthly else pd.DataFrame()
    if not monthly.empty:
        monthly_source = ColumnDataSource(monthly)
        price.segment("date", "high", "date", "low", source=monthly_source,
                      line_color=palette.wick, line_alpha=0.40)
        price.vbar("date", width="width", top="top", bottom="bottom", source=monthly_source,
                   fill_color="color", fill_alpha=0.25, line_alpha=0,
                   legend_label="Monthly overlay")
    candle_wick = price.segment("date", "High", "date", "Low",
                                source=source, color=palette.wick, line_width=1)
    candle_body = price.vbar("date", width=DAY_MS*0.75, top="top", bottom="bottom",
                            source=source, fill_color="color", line_color="color",
                            legend_label=f"{config.display_symbol} OHLC")
    price.add_tools(HoverTool(renderers=[candle_body], tooltips=[
        ("Date", "@date{%F}"), ("Open", "@Open{0.00}"),
        ("High", "@High{0.00}"), ("Low", "@Low{0.00}"),
        ("Close", "@Close{0.00}"), *config.price_hover_fields,
    ], formatters={"@date": "datetime"}, mode="vline"))
    for overlay in config.overlays:
        price.scatter("date", overlay.field, source=source,
                      marker=overlay.marker, size=config.indicator_marker_size,
                      color=overlay.color, legend_label=overlay.label)

    if config.show_trades and not fills.empty:
        entries = fills.loc[fills["side"] == "buy"]
        exits = fills.loc[fills["side"] == "sell"]
        for fr, marker, color, label in (
            (entries, "triangle", palette.buy, f"{config.execution_symbol} BUY"),
            (exits, "inverted_triangle", palette.sell, f"{config.execution_symbol} SELL"),
        ):
            cds = ColumnDataSource(fr)
            glyph = price.scatter("date", "display_price", source=cds, marker=marker,
                                  size=11, color=color, line_color="#ffffff", line_width=1,
                                  legend_label=label)
            price.add_tools(HoverTool(renderers=[glyph], tooltips=[
                ("Date", "@date{%F}"), ("Side", "@side"), ("Instrument", "@symbol"),
                (f"{config.execution_symbol} fill", "@price{0.0000}"), ("Quantity", "@qty{0,0}"),
                ("Fee", "@fee{0.00}"), (f"{config.display_symbol} signal-price", "@display_price{0.00}"),
            ], formatters={"@date": "datetime"}))

        if not trades.empty:
            beams = pd.DataFrame({
                "xs": [[r.entry_date, r.date] for r in trades.itertuples()],
                "ys": [[r.entry_display_price, r.exit_display_price] for r in trades.itertuples()],
                "color": np.where(trades["win"], palette.trade_span_profit,
                                  palette.trade_span_loss),
            })
            price.multi_line(xs="xs", ys="ys", source=ColumnDataSource(beams),
                             line_width=3, line_alpha=.80, line_dash=[12, 9],
                             color="color", legend_label=f"Trade spans ({config.display_symbol} axis)")
    price.legend.location = "top_left"
    price.legend.click_policy = "hide"
    currency_suffix = f" ({config.price_currency})" if config.price_currency else ""
    price.yaxis.axis_label = f"{config.display_symbol} price{currency_suffix}"
    price.xaxis.axis_label = "Trading date, scroll to zoom · drag to pan"
    plots = [equity, pnl, drawdown, price]
    if config.show_volume:
        volume = new_fig(f"{config.display_symbol} Volume", 135, True)
        volume.vbar("date", width=DAY_MS * 0.75, top="Volume", bottom=0,
                    source=source, fill_color="color", line_color="color")
        volume.yaxis.axis_label = f"{config.display_symbol} Volume"
        volume.yaxis.formatter = NumeralTickFormatter(format="0.0a")
        volume.xaxis.axis_label = "Trading date, scroll to zoom · drag to pan"
        plots.append(volume)
    return column(*plots, sizing_mode="stretch_width")

