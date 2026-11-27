from pathlib import Path
from backtest_lab.reporting.research_index import render_index

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_links_only_to_existing_pages(tmp_path):
    site = tmp_path / "site"
    for route in ("multi_asset_weekly_sma", "gold_trend_research", "psar_segment_duration",
                  "archive/multi_asset_weekly_sma/r01/20261127-0008"):
        p = site / "research" / route / "index.html"
        p.parent.mkdir(parents=True)
        p.write_text("report", encoding="utf-8")
    html = render_index(ROOT, site).read_text(encoding="utf-8")
    for path in (ROOT / "runs").iterdir():
        if path.is_dir():
            assert f'data-strategy="{path.name}"' in html
    assert 'href="research/gold_trend_research/"' in html
    assert 'href="research/archive/multi_asset_weekly_sma/r01/20261127-0008/"' in html
    assert 'href="research/psar_segment_duration/"' in html
    assert 'href="research/weekly_trend/"' not in html
    assert "20261127-0001" in html
    assert "20261127-0008" in html
    assert "20260825-0003" in html


def test_new_research_discovered_without_catalog_edit(tmp_path):
    docs = tmp_path / "doc" / "strategies"
    docs.mkdir(parents=True)
    (docs / "20261127-new-idea-r01.md").write_text("# New <idea>\n", encoding="utf-8")
    (tmp_path / "runs" / "new_idea" / "r01" / "20261127-0001").mkdir(parents=True)
    html = render_index(tmp_path, tmp_path / "site").read_text(encoding="utf-8")
    assert 'data-strategy="new_idea"' in html
    assert "New &lt;idea&gt;" in html
    assert "20261127-0001" in html
