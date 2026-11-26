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
    assert html.count('<a href="assets/') == 3
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
    # Read-only reporting must not touch archived source CSVs.
    assert (prepared_run / "assets" / "gold" / "ffn_stats.csv").is_file()


def test_missing_manifest_fails_clearly(prepared_run, tmp_path):
    (prepared_run / "asset_manifest.csv").unlink()
    with pytest.raises(FileNotFoundError):
        render_summary(prepared_run, tmp_path / "index.html")
