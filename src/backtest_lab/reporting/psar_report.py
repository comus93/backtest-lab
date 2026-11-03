"""Standalone Bokeh/FFN PSAR report generator; no backtesting.py code is imported."""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd


WINDOWS = ("2007-2011", "2012-2016", "2017-2021", "2022-2026")
PALETTE = {"strategy": "#2563eb", "QLD": "#f97316", "QQQ": "#71717a"}
COLORS = {
    "bullish": "#E53935", "bearish": "#1E88E5",
    "monthly_bullish": "#E8A09D", "monthly_bearish": "#9DBFDF",
    "psar_up": "#F59E0B", "psar_down": "#8B5CF6",
    "buy": "#16A34A", "sell": "#DC2626",
    "profit": "#16A34A", "loss": "#DC2626",
    "grid": "#94A3B8", "wick": "#64748B",
}
DAY_MS = 24 * 60 * 60 * 1000


def load_outputs(run_dir: str | Path, volume_path: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Read existing run results as immutable inputs, never regenerate statistics."""
    path = Path(run_dir)
    names = ("input_prices", "daily_signals", "equity_curves", "fills",
             "performance_summary", "ffn_stats")
    if not all((path / f"{name}.csv").is_file() for name in names):
        raise FileNotFoundError(f"Missing required report input in {path}")
    data = {name: pd.read_csv(path / f"{name}.csv") for name in names}
    for name in ("input_prices", "equity_curves"):
        data[name]["timestamp"] = pd.to_datetime(data[name]["timestamp"])
        if data[name]["timestamp"].duplicated().any():
            raise ValueError(f"Duplicate timestamps in {name}")
        data[name] = data[name].set_index("timestamp").sort_index()
    for name, column in (("daily_signals", "signal_date"), ("fills", "timestamp")):
        data[name][column] = pd.to_datetime(data[name][column])
    supplement = Path(volume_path) if volume_path else path / "qqq_volume.csv"
    if supplement.is_file():
        if "QQQ_Volume" in data["input_prices"]:
            raise ValueError("QQQ_Volume is present in both source prices and supplement")
        volume = pd.read_csv(supplement, parse_dates=["timestamp"])
        if set(volume.columns) != {"timestamp", "QQQ_Volume"}:
            raise ValueError("Invalid QQQ volume columns")
        if volume["timestamp"].duplicated().any():
            raise ValueError("Duplicate QQQ volume timestamps")
        volume = volume.set_index("timestamp")["QQQ_Volume"]
        data["input_prices"]["QQQ_Volume"] = volume.reindex(data["input_prices"].index)
    if "QQQ_Volume" in data["input_prices"]:
        values = data["input_prices"]["QQQ_Volume"]
        if values.isna().any() or (~np.isfinite(values)).any() or (values < 0).any():
            raise ValueError("QQQ Volume must have complete non-negative finite observations")
    return data


def window_data(data: dict[str, pd.DataFrame], window: str) -> dict[str, object]:
    """Validate and isolate one independent backtest window."""
    if window not in WINDOWS:
        raise ValueError(f"Unsupported window: {window}")
    selected = data["performance_summary"].query("window == @window")
    if len(selected) != 3:
        raise ValueError(f"Expected strategy + 2 benchmarks for {window}")
    strategy_rows = selected[selected["strategy"].str.startswith("PSAR Long Only ")]
    if len(strategy_rows) != 1:
        raise ValueError(f"Expected PSAR Long Only results for {window}")
    strategy = strategy_rows.iloc[0]["strategy"]
    names = {"strategy": strategy,
             "QLD": f"QLD Buy & Hold {window}",
             "QQQ": f"QQQ Buy & Hold {window}"}
    times = data["daily_signals"].query("window == @window").copy().sort_values("signal_date")
    if times.empty or times["signal_date"].duplicated().any():
        raise ValueError(f"Bad or absent daily signals for {window}")
    start, end = times["signal_date"].min(), times["signal_date"].max()
    price = data["input_prices"].loc[start:end].copy()
    if not pd.DatetimeIndex(price.index).equals(pd.DatetimeIndex(times["signal_date"])):
        raise ValueError(f"QQQ candles and signal trading dates disagree in {window}")
    curve = data["equity_curves"].loc[start:end, list(names.values())].copy()
    if curve.isna().any().any() or not curve.index.equals(price.index):
        raise ValueError(f"Equity curves do not match trading dates in {window}")
    fill = data["fills"].loc[(data["fills"]["window"] == window)
                             & (data["fills"]["strategy"] == strategy)].copy()
    if (fill["symbol"] != "QLD").any():
        raise ValueError(f"Long-only fills unexpectedly contain another instrument in {window}")
    stats = data["ffn_stats"].set_index("metric").loc[:, list(names.values())]
    stats = stats.rename(columns={v: k for k, v in names.items()})
    return {"window": window, "price": price, "signal": times.set_index("signal_date"),
            "curves": curve.rename(columns={v: k for k, v in names.items()}),
            "fills": fill, "stats": stats, "names": names}


def pair_trades(fills: pd.DataFrame, prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map QLD fills onto QQQ signal-date candles; never mistake QLD dollars for QQQ."""
    events = []
    closed = []
    open_position = None
    for fill in fills.sort_values("timestamp").to_dict("records"):
        date = pd.Timestamp(fill["timestamp"])
        if date not in prices.index:
            raise ValueError(f"Missing QQQ candle for trade at {date}")
        if fill["side"] not in ("buy", "sell"):
            raise ValueError(f"Invalid trade side {fill['side']}")
        event = {
            "date": date, "qqq": float(prices.loc[date, "QQQ_Close"]),
            "symbol": fill["symbol"], "side": fill["side"],
            "price": float(fill["fill_price"]), "qty": float(fill["quantity"]),
            "fee": float(fill["fee"]),
        }
        events.append(event)
        if fill["side"] == "buy":
            if open_position is not None:
                raise ValueError("Simultaneous trades are unsupported in single-position PSAR")
            open_position = event
        elif open_position is None:
            raise ValueError("Sell without prior buy")
        else:
            entry = open_position
            capital = entry["price"] * entry["qty"] + entry["fee"]
            proceeds = event["price"] * event["qty"] - event["fee"]
            ret = proceeds / capital - 1
            closed.append({
                "date": date, "entry_date": entry["date"],
                "entry_qqq": entry["qqq"], "exit_qqq": event["qqq"],
                "return_pct": 100 * ret, "pnl": proceeds - capital,
                "win": ret > 0,
                "symbol": fill["symbol"],
            })
            open_position = None
    return pd.DataFrame(events, columns=["date", "qqq", "symbol", "side", "price", "qty", "fee"]), pd.DataFrame(
        closed, columns=["date", "entry_date", "entry_qqq", "exit_qqq",
                         "return_pct", "pnl", "win", "symbol"]
    )


def _tabular_html(frame: pd.DataFrame, percent_cols: set[str] | None = None) -> str:
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


def _performance_matrix(frame: pd.DataFrame, window: str) -> pd.DataFrame:
    """One window, metrics as rows and strategy comparators as columns."""
    selected = frame.loc[frame["window"] == window].copy()
    names = ("PSAR Long Only", "QLD Buy & Hold", "QQQ Buy & Hold")
    selected["strategy"] = selected["strategy"].str.replace(f" {window}", "", regex=False)
    if len(selected) != 3 or set(selected["strategy"]) != set(names):
        raise ValueError(f"Expected three strategies for performance matrix {window}")
    metrics = {"total_return": "Total Return", "cagr": "CAGR",
               "sharpe": "Sharpe", "max_drawdown": "Max Drawdown"}
    table = selected.set_index("strategy").loc[list(names), list(metrics)]
    table = table.T.rename(index=metrics).reset_index(names="Metric")
    for name in names:
        table[name] = [f"{v * 100:+.2f}%" if metric != "Sharpe" else f"{v:.3f}"
                       for metric, v in zip(table["Metric"], table[name])]
    return table


def _monthly_candles(candles: pd.DataFrame) -> pd.DataFrame:
    """Aggregate QQQ daily OHLC into broad, direction-colored monthly bodies."""
    rows = []
    for _, group in candles.groupby(pd.Grouper(freq="MS")):
        if group.empty:
            continue
        opening = float(group["QQQ_Open"].iloc[0])
        closing = float(group["QQQ_Close"].iloc[-1])
        rows.append({
            "date": group.index[len(group) // 2],
            "high": float(group["QQQ_High"].max()), "low": float(group["QQQ_Low"].min()),
            "top": max(opening, closing), "bottom": min(opening, closing),
            "width": max(len(group) - 1, 1) * DAY_MS,
            "color": COLORS["monthly_bullish"] if closing >= opening else COLORS["monthly_bearish"],
        })
    return pd.DataFrame(rows, columns=["date", "high", "low", "top", "bottom", "width", "color"])


def _table_sections(data: dict[str, pd.DataFrame], block: dict[str, object]) -> tuple[str, str]:
    window = block["window"]
    table = _tabular_html(_performance_matrix(data["performance_summary"], window))
    stats = block["stats"].reset_index()
    raw_ffn = _tabular_html(stats)
    return table, raw_ffn


def _make_charts(block: dict[str, object], *, show_volume: bool = False):
    """Bokeh, written independently to reproduce backtesting.py-like navigation."""
    from bokeh.events import MouseLeave, MouseMove
    from bokeh.layouts import column
    from bokeh.models import (ColumnDataSource, CrosshairTool, CustomJS, HoverTool,
                              Label, NumeralTickFormatter, Range1d)
    from bokeh.plotting import figure

    candles = block["price"]
    signals = block["signal"]
    curves = block["curves"]
    fills, trades = pair_trades(block["fills"], candles)
    combined = candles.join(signals[["psar_value", "psar_direction", "action", "current_len"]])
    combined["date"] = combined.index
    combined["bullish"] = combined["QQQ_Close"] >= combined["QQQ_Open"]
    combined["color"] = np.where(combined["bullish"], COLORS["bullish"], COLORS["bearish"])
    combined["top"] = combined[["QQQ_Open", "QQQ_Close"]].max(axis=1)
    combined["bottom"] = combined[["QQQ_Open", "QQQ_Close"]].min(axis=1)
    combined["up_psar"] = combined["psar_value"].where(combined["psar_direction"] == "UP")
    combined["down_psar"] = combined["psar_value"].where(combined["psar_direction"] == "DOWN")
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
        fig.grid.grid_line_color = COLORS["grid"]
        fig.grid.grid_line_alpha = 0.20
        fig.grid.grid_line_width = 1
        fig.xaxis.visible = x_axis
        fig.yaxis.axis_label_text_font_size = "11px"
        fig.title.text_font_size = "12px"
        return fig

    equity = new_fig("Equity | strategy vs buy-and-hold (FFN performance index, initial 100)", 180)
    equity_frame = curves.assign(date=curves.index)
    eq_source = ColumnDataSource(equity_frame)
    equity_lines = []
    for key, label in (("strategy", "PSAR QLD/Cash"), ("QLD", "QLD B&H"), ("QQQ", "QQQ B&H")):
        line = equity.line("date", key, source=eq_source, line_width=2.2 if key == "strategy" else 1.5,
                           color=PALETTE[key], legend_label=label, name=label)
        equity_lines.append(line)
    # Native Bokeh HoverTool resolves each renderer independently, which can
    # show several tooltips when curves overlap. Pick exactly one curve here.
    hover_point = ColumnDataSource(data={"date": [], "value": [], "color": []})
    equity.scatter("date", "value", source=hover_point, marker="circle", size=8,
                   fill_color="color", line_color="#ffffff", line_width=1)
    hover_label = Label(x=0, y=0, text="", visible=False, x_offset=12, y_offset=12,
                        text_font_size="11px", background_fill_color="#ffffff",
                        background_fill_alpha=0.95, border_line_color=COLORS["grid"],
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
        const choices = [
            ["strategy", "PSAR QLD/Cash", "#2563eb"],
            ["QLD", "QLD B&H", "#f97316"],
            ["QQQ", "QQQ B&H", "#71717a"],
        ];
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

    drawdown = new_fig("Strategy drawdown (%)", 125)
    dd = (curves["strategy"] / curves["strategy"].cummax() - 1.0) * 100.0
    dd_frame = pd.DataFrame({"date": curves.index, "drawdown": dd.to_numpy()})
    dd_source = ColumnDataSource(dd_frame)
    dd_line = drawdown.line("date", "drawdown", source=dd_source, color=COLORS["sell"], line_width=1.8)
    drawdown.varea(x="date", y1=0, y2="drawdown", source=dd_source, color=COLORS["sell"], fill_alpha=0.10)
    drawdown.add_tools(HoverTool(
        renderers=[dd_line], tooltips=[("Date", "@date{%F}"), ("Drawdown", "@drawdown{0.00}%")],
        formatters={"@date": "datetime"}, mode="vline",
    ))
    drawdown.yaxis.axis_label = "%"

    pnl = new_fig("Profit / Loss", 110)
    if not trades.empty:
        markers = trades.copy()
        markers["color"] = np.where(markers["win"], COLORS["profit"], COLORS["loss"])
        trade_source = ColumnDataSource(markers)
        result = pnl.scatter("date", "return_pct", source=trade_source, marker="triangle",
                             size=9, color="color", line_color="#333333")
        pnl.add_tools(HoverTool(renderers=[result], tooltips=[
            ("Exit", "@date{%F}"), ("Entry", "@entry_date{%F}"),
            ("Net QLD P/L", "@return_pct{+0.00}%"), ("Net $", "@pnl{0,0.00}"),
        ], formatters={"@date": "datetime", "@entry_date": "datetime"}))
    pnl.yaxis.axis_label = "%"

    if show_volume and "QQQ_Volume" not in candles.columns:
        raise ValueError("QQQ_Volume data is required when show_volume=True")
    price = new_fig("QQQ OHLC / Parabolic SAR / QLD execution dates", 430, not show_volume)
    monthly = _monthly_candles(candles)
    if not monthly.empty:
        monthly_source = ColumnDataSource(monthly)
        price.segment("date", "high", "date", "low", source=monthly_source,
                      line_color=COLORS["wick"], line_alpha=0.40)
        price.vbar("date", width="width", top="top", bottom="bottom", source=monthly_source,
                   fill_color="color", fill_alpha=0.25, line_alpha=0,
                   legend_label="Monthly overlay")
    candle_wick = price.segment("date", "QQQ_High", "date", "QQQ_Low",
                                source=source, color=COLORS["wick"], line_width=1)
    candle_body = price.vbar("date", width=DAY_MS*0.75, top="top", bottom="bottom",
                            source=source, fill_color="color", line_color="color",
                            legend_label="QQQ OHLC")
    price.add_tools(HoverTool(renderers=[candle_body], tooltips=[
        ("Date", "@date{%F}"), ("Open", "@QQQ_Open{0.00}"),
        ("High", "@QQQ_High{0.00}"), ("Low", "@QQQ_Low{0.00}"),
        ("Close", "@QQQ_Close{0.00}"), ("PSAR", "@psar_value{0.00}"),
        ("State", "@psar_direction"), ("Segment days", "@current_len"), ("Action", "@action"),
    ], formatters={"@date": "datetime"}, mode="vline"))
    price.scatter("date", "up_psar", source=source, marker="circle", size=3,
                  color=COLORS["psar_up"], legend_label="PSAR UP")
    price.scatter("date", "down_psar", source=source, marker="circle", size=3,
                  color=COLORS["psar_down"], legend_label="PSAR DOWN")

    if not fills.empty:
        entries = fills.loc[fills["side"] == "buy"]
        exits = fills.loc[fills["side"] == "sell"]
        for fr, marker, color, label in ((entries, "triangle", COLORS["buy"], "QLD BUY"),
                                         (exits, "inverted_triangle", COLORS["sell"], "QLD SELL")):
            cds = ColumnDataSource(fr)
            glyph = price.scatter("date", "qqq", source=cds, marker=marker,
                                  size=11, color=color, line_color="#ffffff", line_width=1,
                                  legend_label=label)
            price.add_tools(HoverTool(renderers=[glyph], tooltips=[
                ("Date", "@date{%F}"), ("Side", "@side"), ("Instrument", "@symbol"),
                ("QLD fill", "@price{0.0000}"), ("Quantity", "@qty{0,0}"),
                ("Fee", "@fee{0.00}"), ("QQQ signal-price", "@qqq{0.00}"),
            ], formatters={"@date": "datetime"}))

        if not trades.empty:
            beams = pd.DataFrame({
                "xs": [[r.entry_date, r.date] for r in trades.itertuples()],
                "ys": [[r.entry_qqq, r.exit_qqq] for r in trades.itertuples()],
                "color": np.where(trades["win"], COLORS["profit"], COLORS["loss"]),
            })
            price.multi_line(xs="xs", ys="ys", source=ColumnDataSource(beams),
                             line_width=6, line_alpha=.80, line_dash=[12, 9],
                             color="color", legend_label="Trade spans (QQQ axis)")
    price.legend.location = "top_left"
    price.legend.click_policy = "hide"
    price.yaxis.axis_label = "QQQ price (USD)"
    price.xaxis.axis_label = "Trading date, scroll to zoom · drag to pan"
    plots = [equity, pnl, drawdown, price]
    if show_volume:
        volume = new_fig("QQQ Volume", 135, True)
        volume.vbar("date", width=DAY_MS * 0.75, top="QQQ_Volume", bottom=0,
                    source=source, fill_color="color", line_color="color")
        volume.yaxis.axis_label = "QQQ Volume"
        volume.yaxis.formatter = NumeralTickFormatter(format="0.0a")
        volume.xaxis.axis_label = "Trading date, scroll to zoom · drag to pan"
        plots.append(volume)
    return column(*plots, sizing_mode="stretch_width")


def build_report(run_dir: str | Path, destination: str | Path,
                 volume_path: str | Path | None = None, *,
                 show_volume: bool = False) -> Path:
    """Export a self-contained Bokeh HTML dashboard from immutable run CSVs."""
    from bokeh.embed import file_html
    from bokeh.layouts import column
    from bokeh.models import Div, TabPanel, Tabs
    from bokeh.resources import INLINE

    data = load_outputs(run_dir, volume_path if show_volume else None)
    if show_volume and "QQQ_Volume" not in data["input_prices"]:
        raise ValueError("Volume was requested but no QQQ_Volume source was supplied")
    summary = data["performance_summary"]
    if not all((summary["window"] == window).any() for window in WINDOWS):
        raise ValueError("Missing one or more PSAR evaluation windows")
    summary_html = "".join(
        f'<h3 style="font-size:14px;margin:18px 0 6px">{window}</h3>'
        + _tabular_html(_performance_matrix(summary, window))
        for window in WINDOWS
    )
    intro = Div(text=(
        '<div style="font-family:system-ui;padding:10px 6px;color:#172033">'
        '<h1 style="font-size:25px;margin:0">PSAR QLD / Cash · Case Study</h1>'
        '<p style="color:#475569">Source: immutable backtest-lab CSV outputs · '
        'Signal: QQQ Parabolic SAR · execution: QLD only · '
        '5-year windows · same-bar look-ahead bias (not tradable performance).</p>'
        '<p style="color:#475569">Interactive: mouse wheel zoom, drag pan, box zoom, '
        'hover date/price/PSAR/QLD fills. Trade spans are projected on QQQ prices '
        '(QLD execution dollars are only in marker tooltips).</p>'
        '<p style="color:#9a3412">Open trades have an entry marker but no realized P/L dot. '
        + ("Volume: QQQ actual market volume, independent from archived backtest P/L.</p>"
           if show_volume else
           "Volume panel is optional and disabled for this strategy.</p>")
        + '<h2 style="font-size:18px">Period performance & buy-and-hold</h2>'
        + summary_html + '</div>'
    ), sizing_mode="stretch_width")
    tabs = []
    for window in WINDOWS:
        block = window_data(data, window)
        period_table, ffn_table = _table_sections(data, block)
        header = Div(text=(
            f'<div style="font-family:system-ui"><h3>{window}: FFN result matrix (raw)</h3>'
            '<p style="color:#64748b;font-size:12px">Values are read verbatim from ffn_stats.csv; '
            'decimal rates have not been silently converted to percentages.</p>'
            + ffn_table + '</div>'
        ), sizing_mode="stretch_width")
        per_period = Div(text=(
            f'<div style="font-family:system-ui"><h3>{window}: Performance</h3>'
            + period_table + '</div>'
        ), sizing_mode="stretch_width")
        tabs.append(TabPanel(child=column(per_period, _make_charts(block, show_volume=show_volume), header,
                                          sizing_mode="stretch_width"), title=window))
    layout = column(intro, Tabs(tabs=tabs, sizing_mode="stretch_width"),
                    sizing_mode="stretch_width")
    html = file_html(layout, INLINE, title="PSAR QLD/Cash Backtest Case Study")
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a static PSAR backtest Bokeh report")
    parser.add_argument("--run", required=True, help="Existing run CSV directory")
    parser.add_argument("--output", required=True, help="Output HTML path")
    parser.add_argument("--volume", default=None, help="Optional QQQ volume CSV, date-aligned to immutable prices")
    parser.add_argument("--show-volume", action="store_true",
                        help="Show price-aligned volume panel for volume-dependent strategies")
    args = parser.parse_args()
    print(build_report(args.run, args.output, args.volume, show_volume=args.show_volume))


if __name__ == "__main__":
    main()
