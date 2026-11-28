"""Static research catalog built after all report pages, without running research."""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re
from urllib.parse import quote

REPO = "https://github.com/comus93/backtest-lab"
# Lifecycle is user-directed; unclassified research is not assumed abandoned.
ACTIVE = {"gold_trend_research", "multi_asset_weekly_sma"}
LEGACY = {"psar_segment_duration"}
DESCRIPTIONS = {
    "gold_trend_research": "GLD, SPY, SLV에서 SMA105 LONG, 3LB Long/Cash 및 Long/Inverse를 독립 비교한다.",
    "multi_asset_weekly_sma": "10개 자산에서 SMA105와 3-Line Break 추세 추종을 비교한다.",
    "psar_segment_duration": "나스닥 PSAR 방향 구간 지속 기간을 이용한 비대칭 추세 추종. 기존 렌더러 보존.",
    "market_momentum": "국가 ETF 상대 모멘텀과 기존 포트폴리오 보완 효과를 검토한다.",
    "weekly_trend": "주봉 방향의 연속성과 자산별 편입·편출 전략을 검증한다.",
    "tripod_nasdaq_leverage": "나스닥 추세·변동성·낙폭에 따라 0x / 1.5x / 3x 노출을 전환한다.",
    "sp500_top2_market_cap": "S&P 500 시가총액 상위 2개 기업의 연간 리밸런싱을 비교한다.",
    "us_market_cap_leaders": "분기별 미국 시가총액 TOP1 / TOP2 집중 투자와 지수 성과를 비교한다.",
}
SPEC = re.compile(r"^\d{8}-(.+)-(r\d+)\.md$")
RUN = re.compile(r"^\d{8}-\d{4}$")


def _link(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def _repo_link(root, path, label):
    mode = "tree" if path.is_dir() else "blob"
    return _link(f"{REPO}/{mode}/main/{quote(path.relative_to(root).as_posix())}", label)


def render_index(repo_root, site_dir):
    root, site = Path(repo_root), Path(site_dir)
    docs = root / "doc" / "strategies"
    specs = {}
    for p in docs.glob("*.md"):
        match = SPEC.fullmatch(p.name)
        if match:
            key = match[1].replace("-", "_")
            specs.setdefault(key, []).append((match[2], p))
    runs = root / "runs"
    ids = set(specs) | {p.name for p in runs.glob("*") if p.is_dir()}
    ids |= {p.stem for p in (docs / "reports").glob("*.md")}
    sections = []
    for label, keys in (
        ("진행 중인 연구", ACTIVE & ids),
        ("기타 연구 기록", ids - ACTIVE - LEGACY),
        ("레거시 리포트", LEGACY & ids),
    ):
        cards = []
        for key in sorted(keys):
            versions = sorted(specs.get(key, []), key=lambda v:(int(v[0][1:]),v[1].name))
            title = key.replace("_", " ").title()
            if versions:
                title = versions[-1][1].read_text(encoding="utf-8-sig").splitlines()[0].lstrip("# ").strip()
            paths = sorted((p for p in (runs/key).glob("r*/*") if p.is_dir() and RUN.fullmatch(p.name)),
                           key=lambda p:(p.name,p.parent.name))
            latest = paths[-1] if paths else None
            details = f"Latest run: {latest.parent.name} / {latest.name}" if latest else "아카이브 Run 없음"
            links = []
            page = site / "research" / key / "index.html"
            if page.is_file():
                links.append(_link(f"research/{quote(key)}/", "대시보드"))
            else:
                links.append('<span class="muted">전용 대시보드 미게시</span>')
            report = docs / "reports" / f"{key}.md"
            if report.is_file():
                links.append(_repo_link(root, report, "연구 리포트"))
            if versions:
                links.append(_repo_link(root, versions[-1][1], "최신 전략 명세"))
            if latest:
                links.append(_repo_link(root, latest, "최신 Run"))
                links.append(_repo_link(root, runs/key, "전체 Run"))
            for archived in sorted((site/"research"/"archive"/key).glob("r*/*/index.html")):
                rel = archived.parent.relative_to(site).as_posix()
                links.append(_link(quote(rel)+"/",f"고정 Run {archived.parent.name}"))
            cards.append(f'<article data-strategy="{escape(key,quote=True)}"><h3>{escape(title)}</h3>'
                         f'<p>{escape(DESCRIPTIONS.get(key,"전략 명세와 실행 기록을 참조해."))}</p>'
                         f'<p class="meta">{escape(details)}</p><nav aria-label="{escape(title,quote=True)} links">'
                         + " ".join(links) + "</nav></article>")
        if cards:
            sections.append(f'<section><h2>{label} <span class="count">{len(cards)}</span></h2>'
                            '<div class="grid">'+"".join(cards)+"</div></section>")
    html = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Backtest-Lab | Research Index</title><style>
*{box-sizing:border-box}body{font:15px/1.6 system-ui,sans-serif;background:#f8fafc;color:#172033;margin:0}
main{max-width:1100px;padding:32px 20px;margin:auto}h1{font-size:30px;margin:0}h2{font-size:19px;margin:32px 0 12px}
h3{font-size:17px;margin:0 0 8px}p{margin:6px 0}.meta,.muted{font-size:13px;color:#475569}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:12px}
article{padding:18px;border:1px solid #dbe2ea;border-radius:8px;background:white}
nav{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:12px}a{color:#1d4ed8;text-decoration:underline;text-underline-offset:3px}
a:focus-visible{outline:2px solid #1d4ed8;outline-offset:3px}.count{font-size:13px;color:#475569;font-weight:normal}
footer{margin-top:32px;border-top:1px solid #dbe2ea;padding-top:16px}
</style></head><body><main><header><h1>Backtest-Lab</h1>
<p>Research Index · 투자 전략 연구 및 백테스트</p>
<p class="meta">연구 명세와 Run 기록에서 자동 생성된 목록. 기타 연구는 진행 상태 미지정이며 종료를 의미하지 않아.</p></header>"""
    html += "".join(sections)
    html += f'<footer>{_link(REPO,"GitHub Repository")} · {_link(REPO+"/tree/main/doc/strategies","전체 전략 명세")}</footer></main></body></html>'
    site.mkdir(parents=True,exist_ok=True)
    output = site / "index.html"
    output.write_text(html,encoding="utf-8")
    return output


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",default=".")
    p.add_argument("--site",required=True)
    a=p.parse_args()
    print(render_index(a.repo,a.site))


if __name__=="__main__":
    main()
