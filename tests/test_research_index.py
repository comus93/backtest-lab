from pathlib import Path
import re
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
    for strategy in ("gold_trend_research","multi_asset_weekly_sma","market_momentum"):
        candidates = [p for p in (ROOT/"runs"/strategy).glob("r*/*")
                      if p.is_dir() and re.fullmatch(r"\d{8}-\d{4}",p.name)]
        latest = max(candidates,key=lambda p:(p.name,p.parent.name))
        assert f"Latest run: {latest.parent.name} / {latest.name}" in html
        assert f'/tree/main/{latest.relative_to(ROOT).as_posix()}"' in html


def test_new_research_discovered_without_catalog_edit(tmp_path):
    docs = tmp_path / "doc" / "strategies"
    docs.mkdir(parents=True)
    (docs / "20261127-new-idea-r01.md").write_text("# New <idea>\n", encoding="utf-8")
    (tmp_path / "runs" / "new_idea" / "r01" / "20261127-0001").mkdir(parents=True)
    html = render_index(tmp_path, tmp_path / "site").read_text(encoding="utf-8")
    assert 'data-strategy="new_idea"' in html
    assert "New &lt;idea&gt;" in html
    assert "20261127-0001" in html


def test_new_run_replaces_latest_index_link(tmp_path):
    root=tmp_path/"runs"/"new_idea"/"r01"
    (root/"20261127-0001").mkdir(parents=True)
    site=tmp_path/"site"
    assert "Latest run: r01 / 20261127-0001" in render_index(tmp_path,site).read_text(encoding="utf-8")
    (root/"20261128-0001").mkdir()
    html=render_index(tmp_path,site).read_text(encoding="utf-8")
    assert "Latest run: r01 / 20261128-0001" in html
    assert 'runs/new_idea/r01/20261128-0001"' in html
    assert "Latest run: r01 / 20261127-0001" not in html
