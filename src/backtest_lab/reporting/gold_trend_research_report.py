"""Gold research report: archived raw price and native signal charts."""
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from .adapters.multi_asset_trade_charts import prepare_trade_charts
from .selectable_charts import build_selectable_charts
from .tables import tabular_html

DAY_MS = 86_400_000


def _source(frame, dates):
    return {"date": [int(t.value//1_000_000) for t in dates],
            **{k: frame[k].tolist() for k in frame.columns}}


def _read(run, file, dates=()):
    return pd.read_csv(run/file, parse_dates=list(dates))


def build_gold_charts(run):
    from bokeh.layouts import column, row
    from bokeh.models import ColumnDataSource, CrosshairTool, CustomJS, DataRange1d, HoverTool, Toggle
    from bokeh.plotting import figure
    from .palette import DEFAULT_PALETTE as palette

    run = Path(run)
    raw = _read(run,"input_prices.csv",("timestamp",)).set_index("timestamp")
    summary = _read(run,"performance_summary.csv")
    curves = _read(run,"equity_curves.csv",("timestamp",))
    fills = _read(run,"fills.csv",("timestamp",))
    decisions = _read(run,"daily_signals.csv",("signal_date","execution_date"))
    prices, benchmark, strategies = prepare_trade_charts(raw.Close,curves,fills,decisions,summary,"GLD","GLL")
    old = build_selectable_charts(prices,benchmark,strategies,display_symbol="GLD",currency="USD")
    selector,note,perf,pnl,dd,price = old.children
    active = raw.loc[pd.Timestamp(summary.start_date.min()):pd.Timestamp(summary.end_date.max())]
    candle_frame = active[["Open","High","Low","Close"]].copy()
    candle_frame["top"] = candle_frame[["Open","Close"]].max(axis=1)
    candle_frame["bottom"] = candle_frame[["Open","Close"]].min(axis=1)
    candle_frame["color"] = [palette.bullish if c>=o else palette.bearish
                              for o,c in zip(candle_frame.Open,candle_frame.Close)]
    candle = ColumnDataSource(_source(candle_frame,active.index),name="gold-raw-ohlc")
    rawline = price.y_range.renderers[0]
    wick = price.segment("date","High","date","Low",source=candle,line_color="color",visible=False)
    body = price.vbar("date",width=.75*DAY_MS,top="top",bottom="bottom",source=candle,
                      fill_color="color",line_color="color",visible=False)
    price.y_range.renderers = [rawline,wick,body]
    price.add_tools(HoverTool(renderers=[body],tooltips=[("Date","@date{%F}"),("Open","@Open{0.00}"),
        ("High","@High{0.00}"),("Low","@Low{0.00}"),("Close","@Close{0.00}")],
        formatters={"@date":"datetime"}))
    toggle = Toggle(label="Raw candles",active=False,width=125)
    toggle.js_on_change("active",CustomJS(args=dict(line=rawline,wick=wick,body=body),code="""
        line.visible = !cb_obj.active;
        wick.visible = body.visible = cb_obj.active;
    """))
    price.title.text="GLD actual price & executions | "+selector.value

    # One date axis for raw and transformed charts. 3LB is deliberately
    # calendar-aligned (gaps on sessions with no newly confirmed block).
    sig = figure(title="Strategy chart | SMA105",height=330,sizing_mode="stretch_width",
                 x_axis_type="datetime",x_range=price.x_range,window_axis="x",
                 y_range=DataRange1d(only_visible=True),name="gold-signal-chart",
                 tools="xpan,xwheel_zoom,ypan,ywheel_zoom,xbox_zoom,reset,save",
                 active_drag="xpan",active_scroll="xwheel_zoom",toolbar_location="right")
    sig.add_tools(CrosshairTool(dimensions="height",line_alpha=.4))
    sig.grid.grid_line_alpha=.2
    sig.yaxis.axis_label="Signal price (USD)"
    sma = _read(run,"sma_signals.csv",("signal_date",)).set_index("signal_date").reindex(active.index)
    smasrc = ColumnDataSource(_source(sma[["reference_close","sma105"]],active.index),name="gold-sma")
    line = sig.line("date","reference_close",source=smasrc,color="#475569",line_width=1.5)
    ma = sig.line("date","sma105",source=smasrc,color="#f59e0b",line_width=2)
    sig.add_tools(HoverTool(renderers=[ma],tooltips=[("Date","@date{%F}"),("SMA105","@sma105{0.00}")],
                            formatters={"@date":"datetime"},mode="vline"))
    lb = _read(run,"line_break_signals.csv",("signal_date",)).set_index("signal_date").reindex(active.index)
    blocks = lb.loc[lb.line_formed.eq(True)].copy()
    blocks["top"] = blocks[["line_open","line_close"]].max(axis=1)
    blocks["bottom"] = blocks[["line_open","line_close"]].min(axis=1)
    blocks["color"] = [palette.bullish if d>0 else palette.bearish for d in blocks.direction]
    lbsrc = ColumnDataSource(_source(blocks[["line_open","line_close","top","bottom","color"]],blocks.index),name="gold-3lb")
    block = sig.vbar("date",width=.82*DAY_MS,top="top",bottom="bottom",source=lbsrc,
                     fill_color="color",line_color="color",visible=False)
    sig.add_tools(HoverTool(renderers=[block],tooltips=[("Formation date","@date{%F}"),
        ("Line open","@line_open{0.00}"),("Line close","@line_close{0.00}")],
        formatters={"@date":"datetime"}))
    ha = _read(run,"heikin_ashi_signals.csv",("signal_date",)).set_index("signal_date").reindex(active.index)
    ha["top"] = ha[["ha_open","ha_close"]].max(axis=1)
    ha["bottom"] = ha[["ha_open","ha_close"]].min(axis=1)
    ha["color"] = [palette.bullish if d>=0 else palette.bearish for d in ha.direction]
    hasrc = ColumnDataSource(_source(ha[["ha_open","ha_close","ha_high","ha_low","top","bottom","color"]],ha.index),name="gold-heikin-ashi")
    hawick = sig.segment("date","ha_high","date","ha_low",source=hasrc,line_color="color",visible=False)
    habody = sig.vbar("date",width=.75*DAY_MS,top="top",bottom="bottom",source=hasrc,
                      fill_color="color",line_color="color",visible=False)
    sig.add_tools(HoverTool(renderers=[habody],tooltips=[("Date","@date{%F}"),("HA open","@ha_open{0.00}"),
        ("HA high","@ha_high{0.00}"),("HA low","@ha_low{0.00}"),("HA close","@ha_close{0.00}")],
        formatters={"@date":"datetime"}))
    sig.y_range.renderers=[line,ma,block,hawick,habody]

    # Actual execution dates projected onto the corresponding indicator
    # coordinates, never represented as a fill at a synthetic HA price.
    visuals = {}
    for name, data in strategies.items():
        mode = "lb" if name.startswith("LineBreak") else "ha" if name.startswith("Heikin Ashi") else "hold" if name=="Buy & Hold" else "sma"
        projection = lb.line_close if mode=="lb" else ha.ha_close if mode=="ha" else active.Close
        values = {int(t.value//1_000_000): float(v) for t,v in projection.items() if pd.notna(v)}
        entry = data["holds"]["entry_date"]
        exit_ = data["holds"]["exit_date"]
        visuals[name] = {"mode":mode,
            "buys":{"date":data["buys"]["date"],"y":[values.get(d,float("nan")) for d in data["buys"]["date"]]},
            "sells":{"date":data["sells"]["date"],"y":[values.get(d,float("nan")) for d in data["sells"]["date"]]},
            "holds":{"entry":entry,"exit":exit_,
                     "y0":[values.get(d,float("nan")) for d in entry],
                     "y1":[values.get(d,float("nan")) for d in exit_],
                     "color":data["holds"]["color"]}}
    initial = visuals[selector.value]
    buys = ColumnDataSource(initial["buys"])
    sells = ColumnDataSource(initial["sells"])
    holds = ColumnDataSource(initial["holds"])
    sig.segment("entry","y0","exit","y1",source=holds,line_color="color",line_width=3,line_dash="dashed",line_alpha=.75)
    sig.scatter("date","y",source=buys,marker="triangle",size=10,color=palette.buy)
    sig.scatter("date","y",source=sells,marker="inverted_triangle",size=10,color=palette.sell)
    selector.js_on_change("value",CustomJS(args=dict(payload=visuals,line=line,ma=ma,block=block,
        hawick=hawick,habody=habody,buys=buys,sells=sells,holds=holds,sig=sig,price=price),code="""
        const v=payload[cb_obj.value], m=v.mode;
        line.visible = m==="sma" || m==="hold";
        ma.visible = m==="sma";
        block.visible = m==="lb";
        hawick.visible = habody.visible = m==="ha";
        buys.data=v.buys; sells.data=v.sells; holds.data=v.holds;
        buys.change.emit(); sells.change.emit(); holds.change.emit();
        sig.title.text = "Strategy chart | " + ({sma:"SMA105",lb:"3-Line Break (formation dates)",ha:"Heikin Ashi (synthetic OHLC)",hold:"GLD Buy & Hold"}[m]);
        price.title.text = "GLD actual price & executions | " + cb_obj.value;
    """))
    for p in (price,sig,perf,pnl,dd):
        p.min_border_left=95
        p.min_border_right=10
        p.xaxis.visible=False
    # Both large charts need their own date ticks when viewed separately.
    price.xaxis.visible=True
    sig.xaxis.visible=True
    price.xaxis.axis_label="Trading date"
    sig.xaxis.axis_label="Trading date"
    dd.xaxis.visible=True
    dd.xaxis.axis_label="Trading date · X linked · independent adaptive Y"
    return column(selector,row(note,toggle,sizing_mode="stretch_width"),price,sig,perf,pnl,dd,
                  sizing_mode="stretch_width",name="gold-research")


def render(run, output):
    from bokeh.embed import file_html
    from bokeh.layouts import column
    from bokeh.models import Div
    from bokeh.resources import INLINE
    run=Path(run)
    summary=_read(run,"performance_summary.csv")
    annual=_read(run,"yearly_performance.csv").pivot(index="strategy",columns="year",values="return").reindex(summary.strategy).reset_index()
    monthly=_read(run,"monthly_performance.csv").pivot(index="month",columns="strategy",values="return").reindex(columns=summary.strategy).reset_index()
    header=Div(text="<h1>Gold Trend Research r01</h1><p>GLD adjusted OHLC · GLL actual inverse prices · USD · next eligible Close. HA and 3LB values are signal/display prices only.</p><h2>Performance Summary</h2>"+tabular_html(summary,percent_cols={"total_return","cagr","volatility","max_drawdown","avg_monthly_turnover","avg_exposure"}),sizing_mode="stretch_width")
    footer=Div(text="<h2>Annual returns</h2>"+tabular_html(annual,percent_cols=set(annual.columns[1:]))+"<h2>Monthly returns</h2>"+tabular_html(monthly,percent_cols=set(monthly.columns[1:]))+"<h2>Raw FFN</h2>"+tabular_html(_read(run,"ffn_stats.csv")),sizing_mode="stretch_width")
    audit_path=run/"parent_control_comparison.csv"
    if audit_path.exists():
        audit=pd.read_csv(audit_path)
        footer.text += "<h2>Parent run 20261127-0008 comparison</h2><p>Fresh adjusted OHLC may differ from archived Close-only inputs.</p>"+tabular_html(audit,percent_cols={c for c in audit.columns if c.startswith(("total_return","cagr","max_drawdown"))})
    target=Path(output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(file_html(column(header,build_gold_charts(run),footer,sizing_mode="stretch_width"),INLINE,title="Gold Trend Research"),encoding="utf-8")
    return target


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    render(args.run,args.output)


if __name__=="__main__":
    main()
