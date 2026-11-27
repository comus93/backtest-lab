"""The 18-asset report must reuse the existing performance table without recomputation."""
from __future__ import annotations

from html import escape

import numpy as np
import pandas as pd
import pytest

from backtest_lab.reporting.adapters.multi_asset_weekly_sma import (
    publish_run, render_detail, render_summary,
)
from backtest_lab.strategies.multi_asset_weekly_sma.r01 import (
    AssetInput, run_asset, write_asset_results, SUMMARY_COLUMNS,
)


@pytest.fixture
def prepared_run(tmp_path):
    dates = pd.bdate_range("2015-01-01", periods=570)
    reference = pd.Series(100 + np.linspace(0, 25, len(dates)), index=dates)
    price = pd.Series(1000 + np.linspace(0, 150, len(dates)), index=dates)
    results = []
    for id_, label in (("gold", "금"), ("silver", "은"), ("copper", "구리")):
        result = run_asset(AssetInput(id_, label, reference, price, f"KR_{id_.upper()}"),
                           start="2016-01-01", end="2018-01-01")
        results.append(result)
    write_asset_results(results, tmp_path / "run")
    return tmp_path / "run"


def test_summary_exact_existing_columns_and_one_row_per_asset(prepared_run, tmp_path):
    output = render_summary(prepared_run, tmp_path / "site" / "index.html")
    html = output.read_text(encoding="utf-8")
    assert html.count('<a href="assets/') == 18  # 3 assets x 6 selectable panels
    for label in ("금", "은", "구리"):
        assert f">{escape(label)}</a></td>" in html
    summary = pd.read_csv(prepared_run / "performance_summary.csv")
    assert list(summary.columns) == list(SUMMARY_COLUMNS)
    assert len(summary) == 3
    assert all(f">{escape(name)}</th>" in html for name in SUMMARY_COLUMNS)


def test_detail_bokeh_and_existing_metrics(prepared_run, tmp_path):
    files = publish_run(prepared_run, tmp_path / "site")
    assert len(files) == 4
    html = (tmp_path / "site" / "assets" / "gold.html").read_text(encoding="utf-8")
    assert "Long/Cash" in html
    assert "Buy &amp; Hold" in html or "Buy & Hold" in html
    assert "../index.html" in html
    assert "bokeh" in html.lower()
    assert "21주 SMA" in html
    # Read-only reporting must not touch archived source CSVs.
    assert (prepared_run / "assets" / "gold" / "ffn_stats.csv").is_file()


def test_missing_manifest_fails_clearly(prepared_run, tmp_path):
    (prepared_run / "asset_manifest.csv").unlink()
    with pytest.raises(FileNotFoundError):
        render_summary(prepared_run, tmp_path / "index.html")


def test_annual_return_tables_reuse_saved_returns(prepared_run, tmp_path):
    html = render_summary(prepared_run, tmp_path / "annual.html").read_text(encoding="utf-8")
    assert "Calendar-year return" in html
    assert "2016*" in html
    yearly = pd.read_csv(prepared_run / "yearly_performance.csv")
    gold = yearly.loc[(yearly.asset_id == "gold") & (yearly.strategy == "Buy & Hold")]
    assert len(gold) > 0
    assert f"{float(gold.iloc[0]['return'])*100:+.2f}%" in html
    path = render_detail(prepared_run, "gold", tmp_path / "gold.html")
    assert "Calendar-year return" in path.read_text(encoding="utf-8")


def test_monthly_matrix_uses_archived_returns_and_exact_order(prepared_run, tmp_path):
    from backtest_lab.reporting.adapters.multi_asset_weekly_sma import _monthly_matrix
    root = prepared_run / "assets" / "gold"
    source = root / "monthly_performance.csv"
    saved = pd.read_csv(source)
    month = "2017-01"
    hold_return = saved.loc[(saved["month"] == month)
                            & (saved["strategy"] == "Buy & Hold"), "return"].iloc[0]
    matrix = _monthly_matrix(source)
    assert "Year-Month Return" in matrix
    assert (matrix.index(">Long/Cash</th>") < matrix.index(">Inverse/Cash</th>")
            < matrix.index(">Long/Inverse</th>") < matrix.index(">LineBreak Long/Cash</th>") < matrix.index(">LineBreak Long/Inverse</th>")
            < matrix.index(">Buy &amp; Hold</th>"))
    assert month in matrix
    assert f"{hold_return * 100:+.2f}%" in matrix
    detail = render_detail(prepared_run, "gold", tmp_path / "gold.html").read_text(encoding="utf-8")
    assert detail.index("Calendar-year return") < detail.index("Year-Month Return")
    assert "2017-01" in detail
    saved_summary = pd.read_csv(root / "performance_summary.csv")
    assert saved_summary.columns.tolist() == list(SUMMARY_COLUMNS)


def test_matrix_with_no_inverse_uses_missing_not_zero(prepared_run, tmp_path):
    from backtest_lab.reporting.adapters.multi_asset_weekly_sma import _monthly_matrix
    source = prepared_run / "assets" / "silver" / "monthly_performance.csv"
    matrix = _monthly_matrix(source)
    assert "Long/Inverse" in matrix
    assert "Inverse/Cash" in matrix
    assert "LineBreak Long/Inverse" in matrix
    assert "—" in matrix
    detail = render_detail(prepared_run, "silver", tmp_path / "silver.html").read_text(encoding="utf-8")
    assert "Year-Month Return" in detail


def test_legacy_archive_without_monthly_file_is_still_renderable(prepared_run, tmp_path):
    (prepared_run / "assets" / "gold" / "monthly_performance.csv").unlink()
    detail = render_detail(prepared_run, "gold", tmp_path / "gold.html").read_text(encoding="utf-8")
    assert "Calendar-year return" in detail
    assert "Year-Month Return" not in detail


def test_new_105_day_report_is_labeled_correctly(prepared_run, tmp_path):
    pd.DataFrame({
        "asset_id": ["gold", "silver", "copper"],
        "display_name": ["금", "은", "구리"],
        "study_basis": ["reference"] * 3,
        "sma_days": [105] * 3,
        "line_break_lines": [3] * 3,
        "long_etf": ["GLD", "SLV", "CPER"],
        "inverse_etf": ["GLL", "", ""],
        "currency": ["USD"] * 3,
    }).to_csv(prepared_run / "instrument_coverage.csv", index=False)
    summary = render_summary(prepared_run, tmp_path / "latest.html").read_text(encoding="utf-8")
    detail = render_detail(prepared_run, "gold", tmp_path / "gold.html").read_text(encoding="utf-8")
    assert "105일 SMA" in summary
    assert "105일 SMA" in detail
    assert "3-Line Break" in summary
    assert "3-Line Break" in detail
    assert "21주 SMA" not in summary
    assert "21주 SMA" not in detail


def test_inverse_cash_in_annual_detail_and_monthly_report(tmp_path):
    from backtest_lab.reporting.adapters.multi_asset_weekly_sma import _annual_table, _monthly_matrix
    dates = pd.bdate_range("2015-01-01", periods=570)
    reference = pd.Series(100 + np.linspace(0, 25, len(dates)), index=dates)
    reference.iloc[220:270] *= 0.80
    price = pd.Series(1000 + np.linspace(0, 150, len(dates)), index=dates)
    inverse = pd.Series(300 - np.linspace(0, 50, len(dates)), index=dates)
    result = run_asset(AssetInput("gold", "금", reference, price, "GLD", inverse, "GLL"),
                       start="2016-01-01", end="2018-01-01")
    run_dir = tmp_path / "run"
    write_asset_results([result], run_dir)
    root = run_dir / "assets" / "gold"
    summary = pd.read_csv(root / "performance_summary.csv")
    assert summary["strategy"].tolist() == ["Long/Cash", "Inverse/Cash", "Long/Inverse", "LineBreak Long/Cash", "LineBreak Long/Inverse", "Buy & Hold"]
    detail = render_detail(run_dir, "gold", tmp_path / "gold.html").read_text(encoding="utf-8")
    assert detail.index("Long/Cash") < detail.index("Inverse/Cash") < detail.index("Long/Inverse") < detail.index("LineBreak Long/Cash") < detail.index("LineBreak Long/Inverse") < detail.index("Buy &amp; Hold")
    annual = _annual_table(root / "yearly_performance.csv")
    monthly = _monthly_matrix(root / "monthly_performance.csv")
    assert "Inverse/Cash" in annual
    assert monthly.index(">Inverse/Cash</th>") < monthly.index(">Long/Inverse</th>") < monthly.index(">LineBreak Long/Cash</th>") < monthly.index(">LineBreak Long/Inverse</th>") < monthly.index(">Buy &amp; Hold</th>")
    assert "Inverse/Cash" in pd.read_csv(root / "ffn_stats.csv").columns
    assert "LineBreak Long/Inverse" in pd.read_csv(root / "ffn_stats.csv").columns


def test_strategy_selector_reads_archived_metrics_and_preserves_missing_assets(prepared_run, tmp_path):
    import re
    path = prepared_run / "assets" / "gold" / "performance_summary.csv"
    stats = pd.read_csv(path)
    inverse = stats.iloc[0].copy()
    inverse["strategy"] = "Inverse/Cash"
    inverse["total_return"] = 0.123456
    pd.concat([stats, inverse.to_frame().T], ignore_index=True).to_csv(path, index=False)
    html = render_summary(prepared_run, tmp_path / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'<option value="[^"]+">([^<]+)</option>', html) == [
        "Long/Cash", "Inverse/Cash", "Long/Inverse", "LineBreak Long/Cash", "LineBreak Long/Inverse", "Buy &amp; Hold"
    ]
    panels = re.findall(r'<section id="strategy-summary-\d+"[^>]*>.*?</section>', html)
    assert len(panels) == 6
    assert ' hidden' not in panels[0].split('>')[0]
    assert all(' hidden' in panel.split('>')[0] for panel in panels[1:])
    assert all(panel.count('<a href="assets/') == 3 for panel in panels)
    assert "+12.35%" in panels[1]
    assert "1/3" in panels[1]
    assert panels[1].count("—</td>") >= 18
    assert "+12.35%" not in panels[0]
    assert "3/3" in panels[3]  # LineBreak Long/Cash does not require inverse
    assert "0/3" in panels[4]
    assert 'select.addEventListener("change",update)' in html


def test_monthly_sticky_header_has_one_scroll_container(prepared_run):
    from backtest_lab.reporting.adapters.multi_asset_weekly_sma import _monthly_matrix
    html = _monthly_matrix(prepared_run / "assets" / "gold" / "monthly_performance.csv")
    assert html.count('overflow:auto') == 1
    assert 'overflow-x:auto' not in html
    assert html.count('position:sticky;top:0;z-index:2;background:#f1f5f9;') == 7
    assert 'border-collapse:separate;border-spacing:0;' in html
