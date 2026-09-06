from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

START = "2006-01-01"
END = "2025-12-31"
# Large-cap leaders that plausibly matter for a 20-year S&P 500 top-2 market-cap strategy.
TICKERS = ("AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "META", "XOM", "GE", "BRK-B", "WMT", "JPM")


def main() -> int:
    rows: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    quarters = pd.period_range("2006Q1", "2025Q4", freq="Q")

    for ticker in TICKERS:
        series = yf.Ticker(ticker).get_shares_full(start=START, end=END)
        if series is None or len(series) == 0:
            for quarter in quarters:
                rows.append({"ticker": ticker, "quarter": str(quarter), "observations": 0, "first_date": "", "last_date": ""})
            summaries.append({
                "ticker": ticker,
                "observed_quarters": 0,
                "total_quarters": len(quarters),
                "coverage_ratio": 0.0,
                "first_observation": "",
                "last_observation": "",
                "max_gap_days": None,
            })
            continue

        s = pd.Series(series).dropna().sort_index()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        qgroups = s.groupby(s.index.to_period("Q"))
        observed = 0
        for quarter in quarters:
            if quarter in qgroups.groups:
                q = qgroups.get_group(quarter)
                observed += 1
                rows.append({
                    "ticker": ticker,
                    "quarter": str(quarter),
                    "observations": int(len(q)),
                    "first_date": str(q.index.min().date()),
                    "last_date": str(q.index.max().date()),
                })
            else:
                rows.append({"ticker": ticker, "quarter": str(quarter), "observations": 0, "first_date": "", "last_date": ""})

        gaps = s.index.to_series().diff().dropna().dt.days
        summaries.append({
            "ticker": ticker,
            "observed_quarters": observed,
            "total_quarters": len(quarters),
            "coverage_ratio": observed / len(quarters),
            "first_observation": str(s.index.min().date()),
            "last_observation": str(s.index.max().date()),
            "max_gap_days": int(gaps.max()) if len(gaps) else None,
        })

    out = Path("research")
    out.mkdir(exist_ok=True)
    detail = pd.DataFrame(rows)
    summary = pd.DataFrame(summaries)
    detail.to_csv(out / "yahoo-shares-quarterly-coverage.csv", index=False)

    lines = [
        "# Yahoo Finance historical shares outstanding quarterly coverage",
        "",
        f"Period: {START} to {END}",
        "",
        summary.to_markdown(index=False),
        "",
        "## Quarterly completeness",
        "",
    ]
    for ticker in TICKERS:
        missing = detail[(detail["ticker"] == ticker) & (detail["observations"] == 0)]["quarter"].tolist()
        lines.append(f"- {ticker}: missing {len(missing)} / {len(quarters)} quarters" + (f"; {', '.join(missing)}" if missing else ""))
    (out / "yahoo-shares-quarterly-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
