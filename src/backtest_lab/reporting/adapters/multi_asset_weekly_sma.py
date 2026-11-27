"""Read-only 21-week SMA research report adapter.

The summary uses the SAME performance_summary.csv columns as existing BTLab.
No performance statistics are calculated by this reporting adapter.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd

from backtest_lab.reporting.tables import tabular_html
from backtest_lab.strategies.multi_asset_weekly_sma.r01 import STRATEGY_ORDER

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


PERCENT_COLUMNS = {"total_return", "cagr", "volatility", "max_drawdown",
                   "avg_monthly_turnover", "avg_exposure"}


def _coverage(run: Path) -> pd.DataFrame:
    path = run / "instrument_coverage.csv"
    return pd.read_csv(path, dtype=str).fillna("") if path.exists() else pd.DataFrame()


def _basis_note(coverage: pd.DataFrame) -> str:
    reference = ("study_basis" in coverage.columns
                 and not coverage.empty
                 and (coverage["study_basis"] == "reference").all())
    if reference:
        return ("1차 연구: 해외 기준 ETF 자체의 수정종가 수익률로 검증 "
                "(미국 ETF 우선, 일본 ETF는 JPY, KOSPI200은 KRW 가격지수 가상 검증). "
                "국내 ETF 실현 성과는 이번 연구에 포함하지 않음.")
    return "이전 연구: 국내 상장 ETF 가격 기반 성과 (2차 검증)."


def _signal_label(coverage: pd.DataFrame) -> str:
    # Legacy archives without daily-resolution metadata remain truthful
    # when explicitly rendered, rather than being relabeled as a new study.
    if "sma_days" in coverage.columns and not coverage.empty:
        valid = coverage["sma_days"].dropna().astype(str)
        if len(valid) and set(valid) == {"105"}:
            return "105일 SMA"
    return "21주 SMA"


def _instrument_note(row: pd.Series) -> str:
    if row.empty:
        return ""
    inv = row.get("inverse_etf", "")
    multiple = row.get("inverse_daily_multiple", "")
    suffix = f" ({float(multiple):g}x daily)" if multiple else ""
    currency = row.get("currency", "")
    return (f"Long: {row.get('long_etf', '')}"
            + (f" / Inverse: {inv}{suffix}" if inv else " / Inverse: —")
            + (f" / {currency}" if currency else "")
            + (f" · {row.get('proxy_note')}" if row.get("proxy_note") else ""))


def _annual_table(path: Path, summary: bool = False) -> str:
    """Render archived annual returns only; do not recalculate in reporting."""
    if not path.exists():
        return ""
    yearly = pd.read_csv(path)
    keys = ["asset", "strategy"] if summary else ["strategy"]
    if yearly.duplicated([*keys, "year"]).any():
        raise ValueError(f"{path}: duplicate annual return")
    years = sorted(yearly["year"].unique())
    order = yearly[keys].drop_duplicates().copy()
    order["_rank"] = order["strategy"].map({name: i for i, name in enumerate(STRATEGY_ORDER)})
    if order["_rank"].isna().any():
        raise ValueError(f"{path}: unknown strategy in annual returns")
    sort_keys = ["_rank"]
    if summary:
        order["_asset_rank"] = pd.factorize(order["asset"], sort=False)[0]
        sort_keys.insert(0, "_asset_rank")
    order = order.sort_values(sort_keys, kind="stable").loc[:, keys]
    frame = (order.merge(yearly.pivot(index=keys, columns="year", values="return").reset_index(),
                         on=keys, how="left").loc[:, [*keys, *years]])
    labels = {year: f"{year}*" if year in (2016, 2026) else str(year) for year in years}
    frame = frame.rename(columns=labels)
    return (
        '<h2 style="font-size:17px">연도별 수익률 (Calendar-year return)</h2>'
        '<p style="color:#64748b">* 2016년은 11월 21일 이후, 2026년은 11월 20일까지의 부분 수익률. '
        '빈 칸은 해당 기간 데이터 없음. 연율 환산하지 않음.</p>'
        + tabular_html(frame, percent_cols=set(labels.values()))
    )


def _monthly_matrix(path: Path) -> str:
    """One month per row, four strategy columns; read archived returns only."""
    if not path.exists():  # historical runs predate the monthly-output contract
        return ""
    monthly = pd.read_csv(path, dtype={"month": str})
    required = {"strategy", "month", "return"}
    if not required <= set(monthly.columns):
        raise ValueError(f"{path}: monthly return columns missing")
    if monthly.duplicated(["month", "strategy"]).any():
        raise ValueError(f"{path}: duplicate monthly strategy observation")
    if not monthly["strategy"].isin(STRATEGY_ORDER).all():
        raise ValueError(f"{path}: unrecognized strategy")
    if not monthly["month"].str.fullmatch(r"\d{4}-(0[1-9]|1[0-2])").all():
        raise ValueError(f"{path}: invalid YYYY-MM month")
    matrix = (monthly.pivot(index="month", columns="strategy", values="return")
              .reindex(columns=STRATEGY_ORDER)
              .sort_index()
              .rename_axis(index="연월", columns=None)
              .reset_index())
    return (
        '<h2 style="font-size:17px">월별 수익률 매트릭스 (Year-Month Return)</h2>'
        '<p style="color:#64748b">각 월의 첫 거래일부터 마지막 거래일까지 계산된 전략별 수익률이야. '
        '2016-11, 2026-11은 부분 월이며, 인버스 상품이 없는 전략의 빈칸(—)은 수익률 0%가 아니라 해당 전략 없음이야.</p>'
        '<div style="max-height:550px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:6px">'
        + tabular_html(matrix, percent_cols=set(STRATEGY_ORDER))
        + '</div>'
    )


def render_summary(run: str | Path, output: str | Path) -> Path:
    """One table, one row per asset, unchanged BTLab performance columns."""
    run = Path(run)
    summary = _read_summary(run / "performance_summary.csv")
    manifest = _read_asset_manifest(run)
    if len(summary) != len(manifest):
        raise ValueError("Each asset must have exactly one row in the summary")
    if set(summary["strategy"]) != set(manifest["display_name"]):
        raise ValueError("Summary and manifest asset labels differ")
    coverage = _coverage(run)
    signal_label = _signal_label(coverage)
    html_table = tabular_html(summary, percent_cols=PERCENT_COLUMNS)
    for row in manifest.itertuples(index=False):
        asset_id = str(row.asset_id)
        label = str(row.display_name)
        # URL is derived from a validated directory identifier, not user content.
        if not asset_id.replace("_", "").isalnum() or not (run / "assets" / asset_id).is_dir():
            raise ValueError(f"Invalid/missing asset directory: {asset_id!r}")
        old = f">{escape(label)}</td>"
        instrument = ""
        if not coverage.empty:
            matches = coverage.loc[coverage["asset_id"] == asset_id]
            if len(matches) == 1:
                instrument = str(matches.iloc[0]["long_etf"])
        link_label = f"{label} ({instrument})" if instrument else label
        new = f'><a href="assets/{escape(asset_id, quote=True)}.html">{escape(link_label)}</a></td>'
        if html_table.count(old) != 1:
            raise ValueError(f"Expected one summary row for {label}")
        html_table = html_table.replace(old, new, 1)
    return _write_html(
        Path(output), "105일 SMA | 자산별 성과",
        f'<h1>105일 SMA 추세추종 · 자산별 비교</h1>'
        '<p>각 자산의 장기 성과를 한 표에서 비교해. 자산명을 선택하면 상세 리포트로 이동해.</p>'
        + f'<p class="note">{escape(_basis_note(coverage))}</p>'
        + '<p class="note">성과 컬럼과 FFN 계산은 기존 BTLab 정의를 그대로 사용해. '
        '서로 다른 실측 데이터 기간은 start_date/end_date로 확인해. '
        '이 표는 독립 자산별 롱·현금 성과이지 하나의 포트폴리오 성과가 아니야.</p>'
        + html_table
        + _annual_table(run / "yearly_performance.csv", summary=True),
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
    coverage = _coverage(run)
    signal_label = _signal_label(coverage)
    matches = coverage.loc[coverage["asset_id"] == asset_id] if not coverage.empty else pd.DataFrame()
    instrument_note = _instrument_note(matches.iloc[0]) if len(matches) == 1 else ""
    folder = run / "assets" / asset_id
    summary = _read_summary(folder / "performance_summary.csv")
    summary = (summary.assign(_order=summary["strategy"].map(
        {name: i for i, name in enumerate(STRATEGY_ORDER)}))
        .sort_values("_order", kind="stable").drop(columns="_order"))
    raw = pd.read_csv(folder / "ffn_stats.csv")
    curves = pd.read_csv(folder / "equity_curves.csv", parse_dates=["timestamp"])
    if "metric" not in raw.columns or "timestamp" not in curves.columns:
        raise ValueError("Missing required raw data columns")
    if len(curves) == 0:
        raise ValueError("Empty curve data")
    present = [name for name in STRATEGY_ORDER if name in curves.columns]
    curves = curves.loc[:, ["timestamp", *present]]
    raw = raw.loc[:, ["metric", *(name for name in STRATEGY_ORDER if name in raw.columns)]]

    title = escape(name)
    header = Div(text=(
        '<div style="font-family:system-ui;color:#172033">'
        '<p><a href="../index.html">전체 자산 성과표로 돌아가기</a></p>'
        f'<h1 style="font-size:24px">{title}: 105일 SMA 추세추종</h1>'
        + f'<p>{escape(_basis_note(coverage))}</p>'
        + f'<p>{escape(instrument_note)}</p>'
        + '<p>FFN 원본 성과값과 누적 performance index를 그대로 표시해.</p>'
        + '<h2 style="font-size:17px">Performance summary</h2>'
        + tabular_html(summary, percent_cols=PERCENT_COLUMNS)
        + _annual_table(folder / "yearly_performance.csv")
        + _monthly_matrix(folder / "monthly_performance.csv")
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
        + '<p style="color:#64748b">지수 및 해외 ETF 기준 성과는 국내 ETF 실현 수익률이 아님. '
          '인버스 ETF 미존재 시 Long/Inverse 전략은 표시되지 않아.</p>'
        + '</div>'
    ), sizing_mode="stretch_width")
    html = file_html(column(header, fig, footer, sizing_mode="stretch_width"),
                     INLINE, title=f"{name} | {signal_label}")
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
