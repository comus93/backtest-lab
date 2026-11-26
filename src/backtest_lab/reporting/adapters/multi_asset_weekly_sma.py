"""Read-only 21-week SMA research report adapter.

The summary uses the SAME performance_summary.csv columns as existing BTLab.
No performance statistics are calculated by this reporting adapter.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd

from backtest_lab.reporting.tables import tabular_html

# Must agree with the existing weekly_trend performance-summary contract.
SUMMARY_COLUMNS = (
    "strategy", "start_date", "end_date", "total_return", "cagr",
    "volatility", "sharpe", "max_drawdown", "avg_monthly_turnover", "avg_exposure",
)


def _read_summary(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if list(frame.columns) != list(SUMMARY_COLUMNS):
        raise ValueError(f"{path}: performance_summary columns do not match existing contract")
    return frame


def _read_asset_manifest(run: Path) -> pd.DataFrame:
    manifest = pd.read_csv(run / "asset_manifest.csv", dtype=str).fillna("")
    if not {"asset_id", "display_name"} <= set(manifest.columns):
        raise ValueError("asset_manifest.csv is missing required fields")
    if manifest["asset_id"].duplicated().any():
        raise ValueError("Duplicate asset_id in manifest")
    return manifest


def render_summary(run: str | Path, output: str | Path) -> Path:
    """One table, one row per asset, unchanged BTLab performance columns."""
    run = Path(run)
    summary = _read_summary(run / "performance_summary.csv")
    manifest = _read_asset_manifest(run)
    if len(summary) != len(manifest):
        raise ValueError("Each asset must have exactly one row in the summary")
    if set(summary["strategy"]) != set(manifest["display_name"]):
        raise ValueError("Summary and manifest asset labels differ")
    html_table = tabular_html(summary)
    for row in manifest.itertuples(index=False):
        asset_id = str(row.asset_id)
        label = str(row.display_name)
        # URL is derived from a validated directory identifier, not user content.
        if not asset_id.replace("_", "").isalnum() or not (run / "assets" / asset_id).is_dir():
            raise ValueError(f"Invalid/missing asset directory: {asset_id!r}")
        old = f">{escape(label)}</td>"
        new = f'><a href="assets/{escape(asset_id, quote=True)}.html">{escape(label)}</a></td>'
        if html_table.count(old) != 1:
            raise ValueError(f"Expected one summary row for {label}")
        html_table = html_table.replace(old, new, 1)
    return _write_html(
        Path(output), "21주 SMA | 자산별 성과",
        f'<h1>21주 SMA 추세추종 · 자산별 비교</h1>'
        '<p>각 자산의 장기 성과를 한 표에서 비교해. 자산명을 선택하면 상세 리포트로 이동해.</p>'
        '<p class="note">성과 컬럼과 FFN 계산은 기존 BTLab 정의를 그대로 사용해. '
        '서로 다른 실측 데이터 기간은 start_date/end_date로 확인해. '
        '이 표는 독립 자산별 롱·현금 성과이지 하나의 포트폴리오 성과가 아니야.</p>'
        + html_table,
    )


def render_detail(run: str | Path, asset_id: str, output: str | Path) -> Path:
    """Existing metric tables + self-contained Bokeh equity charts.

    Raw OHLC is not available in the canonical run contract, so never
    fabricate candles/price overlays or pass close-only bars as OHLC.
    """
    from bokeh.embed import file_html
    from bokeh.layouts import column
    from bokeh.models import Div, HoverTool
    from bokeh.plotting import figure
    from bokeh.resources import INLINE

    run = Path(run)
    manifest = _read_asset_manifest(run)
    selected = manifest.loc[manifest["asset_id"] == asset_id]
    if len(selected) != 1:
        raise ValueError(f"Unknown asset_id {asset_id}")
    name = str(selected.iloc[0]["display_name"])
    folder = run / "assets" / asset_id
    summary = _read_summary(folder / "performance_summary.csv")
    raw = pd.read_csv(folder / "ffn_stats.csv")
    curves = pd.read_csv(folder / "equity_curves.csv", parse_dates=["timestamp"])
    if "metric" not in raw.columns or "timestamp" not in curves.columns:
        raise ValueError("Missing required raw data columns")
    if len(curves) == 0:
        raise ValueError("Empty curve data")

    title = escape(name)
    header = Div(text=(
        '<div style="font-family:system-ui;color:#172033">'
        '<p><a href="../index.html">전체 자산 성과표로 돌아가기</a></p>'
        f'<h1 style="font-size:24px">{title}: 21주 SMA 추세추종</h1>'
        '<p>FFN 원본 성과값과 실제 ETF의 누적 performance index를 그대로 표시해.</p>'
        + '<h2 style="font-size:17px">Performance summary</h2>'
        + tabular_html(summary)
        + '<p style="color:#64748b">인버스 전략이 있는 경우 진입 가능일·실제 가격 시계열의 '
          '시작일이 다를 수 있으니 각각의 start_date/end_date를 확인해.</p>'
        + '</div>'
    ), sizing_mode="stretch_width")
    fig = figure(title=f"{name} | 누적 성과 (기준 100)", height=350,
                 sizing_mode="stretch_width", x_axis_type="datetime",
                 tools="xpan,xwheel_zoom,box_zoom,reset,save", active_scroll="xwheel_zoom")
    palette = ("#2563eb", "#a855f7", "#ea580c", "#0d9488")
    for i, strategy in enumerate([str(c) for c in curves.columns if c != "timestamp"]):
        line = fig.line(curves["timestamp"], curves[strategy], legend_label=strategy,
                        line_width=2, color=palette[i % len(palette)])
        fig.add_tools(HoverTool(renderers=[line], tooltips=[
            ("Date", "@x{%F}"), (strategy, "@y{0.00}")
        ], formatters={"@x": "datetime"}))
    fig.legend.click_policy = "hide"
    fig.xaxis.axis_label = "Date"
    fig.yaxis.axis_label = "Performance index"
    footer = Div(text=(
        '<div style="font-family:system-ui">'
        '<h2 style="font-size:17px">FFN 원본 성과표</h2>'
        + tabular_html(raw)
        + '<p style="color:#64748b">실제 국내 ETF 가격 기반 결과만 투자 가능한 성과로 해석해야 해. '
          '인버스 ETF 미존재 시 Long/Inverse 전략은 표시되지 않아.</p>'
        + '</div>'
    ), sizing_mode="stretch_width")
    html = file_html(column(header, fig, footer, sizing_mode="stretch_width"),
                     INLINE, title=f"{name} | 21주 SMA")
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target


def publish_run(run: str | Path, site_dir: str | Path) -> list[Path]:
    run, site_dir = Path(run), Path(site_dir)
    manifest = _read_asset_manifest(run)
    files = [render_summary(run, site_dir / "index.html")]
    for asset_id in manifest["asset_id"]:
        files.append(render_detail(run, asset_id, site_dir / "assets" / f"{asset_id}.html"))
    return files


def _write_html(output: Path, title: str, body: str) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    html = (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{escape(title)}</title>'
        '<style>body{font:15px system-ui,sans-serif;max-width:1250px;margin:32px auto;padding:0 18px;'
        'color:#172033;background:#fff}h1{font-size:25px}a{color:#2563eb;text-decoration:none}'
        'a:hover{text-decoration:underline}.note{color:#64748b;font-size:13px;line-height:1.5}'
        'table{overflow-x:auto}</style></head><body>'
        + body + '</body></html>'
    )
    output.write_text(html, encoding="utf-8")
    return output
