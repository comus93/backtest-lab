"""Gold research report: archived raw price and native signal charts."""
from __future__ import annotations

import argparse
import shutil
from html import escape
from ..strategies.gold_trend_research.r01 import load_assets
from pathlib import Path
import pandas as pd

from .adapters.multi_asset_trade_charts import prepare_trade_charts
from .selectable_charts import build_selectable_charts
from .tables import tabular_html
from .composer import ChartComposer, Glyph, Layer, line_layer, candle_layer, line_break_layer

def _read(run, file, dates=()):
    return pd.read_csv(run/file, parse_dates=list(dates))


# Presentation-only whitelist. The archived names and strategy calculations
# remain unchanged; hidden strategies never enter the serialized chart payload.
DISPLAY_STRATEGIES = {
    "Long/Cash": "SMA105 LONG",
    "LineBreak Long/Cash": "3LB LineBreak Long/Cash",
    "LineBreak Long/Inverse": "3LB LineBreak Long/Inverse",
    "Buy & Hold": "Buy & Hold",
}


def _display_rows(frame):
    selected = frame.loc[frame.strategy.isin(DISPLAY_STRATEGIES)].copy()
    selected["strategy"] = selected.strategy.map(DISPLAY_STRATEGIES)
    return selected


def _display_columns(frame, index):
    return frame[[index, *DISPLAY_STRATEGIES]].rename(columns=DISPLAY_STRATEGIES)


def build_gold_charts(run, asset=None):
    asset=asset or next(a for a in load_assets() if a['id']=='gold')
    symbol,inverse,currency=asset['long'],asset['inverse'],asset['currency']
    from bokeh.layouts import column, row
    from bokeh.models import CustomJS, Toggle, Div
    from .palette import DEFAULT_PALETTE as palette

    run = Path(run)
    raw = _read(run,"input_prices.csv",("timestamp",)).set_index("timestamp")
    summary = _display_rows(_read(run,"performance_summary.csv"))
    curves = _display_columns(_read(run,"equity_curves.csv",("timestamp",)), "timestamp")
    fills = _display_rows(_read(run,"fills.csv",("timestamp",)))
    decisions = _display_rows(_read(run,"daily_signals.csv",("signal_date","execution_date")))
    prices, benchmark, strategies = prepare_trade_charts(raw.Close,curves,fills,decisions,summary,symbol,inverse)
    old = build_selectable_charts(prices,benchmark,strategies,display_symbol=symbol,currency=currency)
    selector,note,perf,pnl,dd,price = old.children
    active = raw.loc[pd.Timestamp(summary.start_date.min()):pd.Timestamp(summary.end_date.max())]
    # Adapt archived columns into independent, reusable display layers.
    raw_composer = ChartComposer("Raw price", price.x_range, unit=currency, figure=price)
    rawline = price.y_range.renderers[0]
    wick, body = raw_composer.add(candle_layer("gold-raw-ohlc",f"{symbol} candles",active,
        unit=currency,basis=f"{symbol} adjusted OHLC"),visible=False)
    toggle = Toggle(label="Raw candles",active=False,width=125)
    toggle.js_on_change("active",CustomJS(args=dict(line=rawline,wick=wick,body=body),code="""
        line.visible = !cb_obj.active;
        wick.visible = body.visible = cb_obj.active;
    """))
    price.title.text=f"{symbol} actual price & executions | "+selector.value

    composer = ChartComposer("Strategy chart | "+selector.value,price.x_range,
        unit=currency,name="gold-signal-chart")
    sig = composer.figure
    sig.yaxis.axis_label=f"Signal price ({currency})"
    sma = _read(run,"sma_signals.csv",("signal_date",)).set_index("signal_date").reindex(active.index)
    lb = _read(run,"line_break_signals.csv",("signal_date",)).set_index("signal_date").reindex(active.index)
    composer.add(line_layer("raw-line","Raw close",active.Close,unit=currency,basis=f"{symbol} adjusted Close"))
    composer.add(candle_layer("raw-candle","Raw candles",active,unit=currency,basis=f"{symbol} adjusted OHLC"),visible=False)
    composer.add(line_layer("sma","SMA105",sma.sma105,unit=currency,
        basis=f"105 trading-day {symbol} adjusted Close",color="#b98a42",width=1.6))
    composer.add(line_break_layer("lb","3LB extended",lb,unit=currency,
        basis=f"Archived confirmed {symbol} Close blocks"),visible=False)
    keys=["raw-line","raw-candle","sma","lb"]
    # Project execution dates onto the selected indicator coordinates.
    visuals = {}
    for name, data in strategies.items():
        mode = "lb" if name.startswith("3LB LineBreak") else "hold" if name=="Buy & Hold" else "sma"
        projection = lb.line_close if mode=="lb" else active.Close
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
    trade_layer=Layer("execution","Execution / holding",currency,"Actual fills; projected on native strategy prices",(
        Glyph("segment",initial["holds"],dict(x0="entry",y0="y0",x1="exit",y1="y1",
              line_color="color",line_width=3,line_dash="dashed",line_alpha=.75),auto_range=False),
        Glyph("scatter",initial["buys"],dict(x="date",y="y",marker="triangle",size=10,color=palette.buy),
              (("Execution","@date{%F}"),("Projected","@y{0.00}")),auto_range=False),
        Glyph("scatter",initial["sells"],dict(x="date",y="y",marker="inverted_triangle",size=10,color=palette.sell),
              (("Execution","@date{%F}"),("Projected","@y{0.00}")),auto_range=False),
    ))
    span,buy,sell=composer.add(trade_layer)
    holds,buys,sells=span.data_source,buy.data_source,sell.data_source
    # Include the execution layer in the independent visibility controls.
    layer_control=composer.visibility_control([*keys,"execution"],["raw-line","sma","execution"],
        name="gold-chart-layers")
    selector.js_on_change("value",CustomJS(args=dict(payload=visuals,
        control=layer_control,buys=buys,sells=sells,holds=holds,sig=sig,price=price,symbol=symbol),code="""
        const v=payload[cb_obj.value], m=v.mode;
        control.active = ({sma:[0,2,4],lb:[3,4],hold:[0,4]})[m];
        buys.data=v.buys; sells.data=v.sells; holds.data=v.holds;
        buys.change.emit(); sells.change.emit(); holds.change.emit();
        sig.title.text = "Strategy chart | " + cb_obj.value;
        price.title.text = symbol + " actual price & executions | " + cb_obj.value;
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
    return column(selector,column(row(note,toggle,sizing_mode="stretch_width"),
        Div(text="Strategy layers: select any combination. SMA105 uses raw Close; execution markers remain projected on the selected strategy native prices. Changing strategy restores its default layers."),
        layer_control,sizing_mode="stretch_width"),price,sig,perf,pnl,dd,
                  sizing_mode="stretch_width",name="gold-research")


def render(run, output, asset=None, *, navigation=False):
    asset=asset or next(a for a in load_assets() if a['id']=='gold')
    from bokeh.embed import file_html
    from bokeh.layouts import column
    from bokeh.models import Div
    from bokeh.resources import INLINE
    run=Path(run)
    summary=_display_rows(_read(run,"performance_summary.csv"))
    annual=_display_rows(_read(run,"yearly_performance.csv")).pivot(index="strategy",columns="year",values="return").reindex(summary.strategy).reset_index()
    monthly=_display_rows(_read(run,"monthly_performance.csv")).pivot(index="month",columns="strategy",values="return").reindex(columns=summary.strategy).reset_index()
    header=Div(text=f"<h1>Trend Research r01 · {escape(asset['label'])}</h1><p>{escape(asset['long'])} adjusted OHLC · {escape(asset['inverse'])} actual inverse prices ({asset['inverse_multiple']}x daily) · {escape(asset['currency'])} · next eligible Close. 3LB values are signal/display prices only.</p><h2>Performance Summary</h2>"+tabular_html(summary,percent_cols={"total_return","cagr","volatility","max_drawdown","avg_monthly_turnover","avg_exposure"}),sizing_mode="stretch_width")
    footer=Div(text="<h2>Annual returns</h2>"+tabular_html(annual,percent_cols=set(annual.columns[1:]))+"<h2>Monthly returns</h2>"+tabular_html(monthly,percent_cols=set(monthly.columns[1:]))+"<h2>Raw FFN</h2>"+tabular_html(_display_columns(_read(run,"ffn_stats.csv"),"metric")),sizing_mode="stretch_width")
    audit_path=run/"parent_control_comparison.csv"
    if audit_path.exists():
        audit=_display_rows(pd.read_csv(audit_path))
        footer.text += "<h2>Parent run 20261127-0008 comparison</h2><p>Fresh adjusted OHLC may differ from archived Close-only inputs.</p>"+tabular_html(audit,percent_cols={c for c in audit.columns if c.startswith(("total_return","cagr","max_drawdown"))})
    target=Path(output)
    target.parent.mkdir(parents=True,exist_ok=True)
    # Use Bokeh's supported template hook, not string replacement inside
    # the serialized HTML (the inline JS itself contains "<body>").
    template_kwargs = {}
    if navigation:
        template_kwargs = {
            "template": """
{% block contents %}
<nav id="trend-navigation" data-asset="{{ asset_id | e }}" aria-label="Asset navigation"><a href="../index.html">Trend Research</a></nav>
<script defer src="../navigation.js"></script>
{{ super() }}
{% endblock %}
""",
            "template_variables": {"asset_id": asset["id"]},
        }
    html=file_html(column(header,build_gold_charts(run,asset),footer,sizing_mode="stretch_width"),
                   INLINE,title=f"Trend Research · {asset['label']}",**template_kwargs)
    target.write_text(html,encoding="utf-8")
    return target


def publish_assets(run, site):
    """Publish manually declared assets only; do not generate the manifest."""
    run,site=Path(run),Path(site)
    site.mkdir(parents=True,exist_ok=True)
    assets=load_assets()
    manifest=Path(__file__).resolve().parents[1]/"strategies"/"gold_trend_research"/"assets.json"
    shutil.copyfile(manifest,site/"assets.json")
    shutil.copyfile(Path(__file__).with_name("trend_navigation.js"),site/"navigation.js")
    for asset in assets:
        folder=run/"assets"/asset["id"]
        if asset["id"]=="gold" and not folder.is_dir() and (run/"performance_summary.csv").is_file():
            folder=run
        if folder.is_dir():
            render(folder,site/asset["page"],asset,navigation=True)
    # The old series root remains valid; the lightweight landing page has
    # a fallback Gold link even without JavaScript.
    (site/"index.html").write_text("""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Trend Research r01</title></head>
<body style="font:16px system-ui;margin:24px"><h1>Trend Research r01</h1>
<nav id="trend-navigation" data-asset="" aria-label="Asset navigation"><a href="assets/gold.html">Gold · GLD</a></nav>
<p>자산을 선택하면 독립 상세 리포트로 이동해.</p><script defer src="navigation.js"></script></body></html>""",encoding="utf-8")
    return site/"index.html"


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--site",action="store_true",help="Publish independent asset pages")
    args=parser.parse_args()
    if args.site:
        publish_assets(args.run,args.output)
    else:
        render(args.run,args.output)


if __name__=="__main__":
    main()
