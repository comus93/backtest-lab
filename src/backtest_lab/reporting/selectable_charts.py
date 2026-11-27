"""Reusable selected-strategy four-panel report, following the PSAR chart layout.

Only display-ready data enters this renderer. No trade matching or accounting.
The same four figures and sources are reused when the strategy changes.
"""
from __future__ import annotations

from .palette import DEFAULT_PALETTE


def build_selectable_charts(prices, benchmark, strategies, *, display_symbol, currency=""):
    from bokeh.layouts import column
    from bokeh.models import (ColumnDataSource, CrosshairTool, CustomJS, HoverTool,
                              Range1d, Select, Div, Legend, LegendItem)
    from bokeh.plotting import figure

    if not strategies or not prices["date"]:
        raise ValueError("Selectable charts require prices and strategy data")
    palette = DEFAULT_PALETTE
    names = list(strategies)
    initial = strategies[names[0]]
    sources = {key: ColumnDataSource(data=initial[key], name=f"trade-chart-{key}")
               for key in ("performance", "drawdown", "pnl", "buys", "sells", "holds")}
    benchmark_source = ColumnDataSource(data=benchmark, name="trade-chart-benchmark")
    price_source = ColumnDataSource(data=prices, name="trade-chart-price")
    xr = Range1d(start=min(prices["date"]+benchmark["date"]),
                 end=max(prices["date"]+benchmark["date"]), name="trade-chart-range")

    def panel(title, height, bottom=False, name=""):
        f = figure(title=title, height=height, sizing_mode="stretch_width",
                   x_axis_type="datetime", x_range=xr, name=name,
                   tools="xpan,xwheel_zoom,box_zoom,reset,save",
                   active_scroll="xwheel_zoom", toolbar_location="right",
                   output_backend="canvas")
        f.add_tools(CrosshairTool(dimensions="height", line_alpha=.4))
        f.grid.grid_line_color = palette.grid
        f.grid.grid_line_alpha = .20
        f.xaxis.visible = bottom
        f.title.text_font_size = "12px"
        f.yaxis.axis_label_text_font_size = "11px"
        return f

    def hover(fig, glyph, fields, *, date_fields=(), mode="mouse"):
        fig.add_tools(HoverTool(renderers=[glyph], tooltips=fields, mode=mode,
                               formatters={f"@{k}": "datetime" for k in date_fields}))

    perf = panel("Performance | "+names[0], 180, name="trade-panel-performance")
    selected_line = perf.line("date", "value", source=sources["performance"],
                              line_width=2.2, color="#2563eb")
    benchmark_line = perf.line("date", "value", source=benchmark_source,
                               line_width=1.5, color="#71717a")
    selected_item = LegendItem(label=names[0], renderers=[selected_line])
    benchmark_item = LegendItem(label="Buy & Hold", renderers=[benchmark_line])
    legend = Legend(items=[selected_item, benchmark_item], location="top_left", click_policy="hide")
    perf.add_layout(legend)
    hover(perf, selected_line, [("Date","@date{%F}"),("Strategy","@value{0.00}")],
          date_fields=("date",), mode="vline")
    hover(perf, benchmark_line, [("Date","@date{%F}"),("Buy & Hold","@value{0.00}")],
          date_fields=("date",), mode="vline")
    perf.yaxis.axis_label = "Performance (start 100)"

    pnl = panel("Profit / Loss | "+names[0], 110, name="trade-panel-pnl")
    pl = pnl.scatter("date", "return_pct", source=sources["pnl"], marker="triangle",
                     size=9, color="color", line_color="#333333")
    hover(pnl, pl, [("Exit","@date{%F}"),("Entry","@entry_date{%F}"),
                    ("Instrument","@symbol"),("Net P/L","@return_pct{+0.00}%"),
                    ("Net amount"+(f" ({currency})" if currency else ""), "@pnl{0,0.00}"),
                    ("Holding days","@days")], date_fields=("date","entry_date"))
    pnl.yaxis.axis_label = "%"

    dd = panel("Strategy Drawdown | "+names[0], 125, name="trade-panel-drawdown")
    dd_line = dd.line("date","value",source=sources["drawdown"],color=palette.sell,line_width=1.8)
    dd.varea(x="date",y1=0,y2="value",source=sources["drawdown"],color=palette.sell,fill_alpha=.10)
    hover(dd, dd_line, [("Date","@date{%F}"),("Drawdown","@value{0.00}%")],
          date_fields=("date",),mode="vline")
    dd.yaxis.axis_label = "%"

    price = panel("Execution Date | "+names[0], 430, True, name="trade-panel-execution")
    close_line = price.line("date","close",source=price_source,color="#475569",line_width=1.5,
                            legend_label=f"{display_symbol} Close")
    hover(price, close_line, [("Date","@date{%F}"),("Close","@close{0,0.0000}")],
          date_fields=("date",),mode="vline")
    spans = price.segment("entry_date","entry_price","exit_date","exit_price",
                          source=sources["holds"],line_width=3,line_dash=[12,9],
                          line_alpha=.8,line_color="color",legend_label="Holding spans")
    hover(price, spans, [("Entry","@entry_date{%F}"),("End","@exit_date{%F}"),
                        ("Position","@position"),("Instrument","@symbol"),
                        ("Status","@status"),("Calendar days","@days"),("Realized P/L","@result")],
          date_fields=("entry_date","exit_date"))
    for key, marker, color, size, label in (
        ("buys","triangle",palette.buy,14,"BUY"),
        ("sells","inverted_triangle",palette.sell,10,"SELL"),
    ):
        glyph = price.scatter("date","display_price",source=sources[key],marker=marker,size=size,
                              color=color,line_color="#ffffff",line_width=1,legend_label=label)
        hover(price,glyph,[("Execution","@date{%F}"),("Signal","@signal_date"),
                           ("Position","@position"),("Instrument","@symbol"),
                           ("Fill price","@fill_price{0,0.0000}"),("Quantity","@quantity{0,0.0000}"),
                           ("Fee","@fee{0,0.00}"),(f"{display_symbol} close","@display_price{0,0.0000}")],
              date_fields=("date",))
    price.legend.location="top_left"
    price.legend.click_policy="hide"
    price.yaxis.axis_label=f"{display_symbol} close"+(f" ({currency})" if currency else "")
    price.xaxis.axis_label="Trading date · zoom and pan synchronized"
    selector = Select(title="Strategy Analysis · 전략 선택",value=names[0],
                      options=names,sizing_mode="stretch_width",name="trade-strategy-select")
    note = Div(text=initial["note"],sizing_mode="stretch_width",name="trade-chart-note")
    benchmark_line.visible = names[0] != "Buy & Hold"
    if not benchmark_line.visible:
        legend.items = [selected_item]
    selector.js_on_change("value",CustomJS(args=dict(
        payload=strategies,sources=sources,perf=perf,pnl=pnl,dd=dd,price=price,
        note=note,benchmark_line=benchmark_line,selected_line=selected_line,
        selected_item=selected_item,benchmark_item=benchmark_item,legend=legend),
        code="""
        const key = cb_obj.value;
        const p = payload[key];
        for (const name of Object.keys(sources)) {
            sources[name].data = p[name];
            sources[name].change.emit();
        }
        perf.title.text = "Performance | " + key;
        pnl.title.text = "Profit / Loss | " + key;
        dd.title.text = "Strategy Drawdown | " + key;
        price.title.text = "Execution Date | " + key;
        selected_item.label = {value: key};
        selected_line.visible = true;
        benchmark_line.visible = key !== "Buy & Hold";
        legend.items = benchmark_line.visible ? [selected_item, benchmark_item] : [selected_item];
        note.text = p.note;
        // Deliberately do not alter the shared x_range.
        """))
    return column(selector,note,perf,pnl,dd,price,sizing_mode="stretch_width",name="trade-analysis")
