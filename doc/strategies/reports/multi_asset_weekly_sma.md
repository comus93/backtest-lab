# Multi-Asset Weekly SMA Trend — Research Living Report

- Strategy ID: `multi_asset_weekly_sma`
- Initial revision: `r01`
- Created: `2026-11-27`
- Status: local 18-asset pilot verified; Actions and Pages deployment pending

## Background / agreed direction
The investigation began with a hypothesis that gold, silver and copper might yield more stable medium-term directional trends than stock indices. The research scope broadened to major country/region stock indices, energy and agricultural commodities, preserving **all 18 provisional candidate underlying exposures** that have a corresponding Korea-listed long ETF after listing/index checks.

The common initial signal candidate is the completed weekly closing price relative to its 21-week SMA. The historical evaluation cutoff is the last fully completed week ending 2026-11-20, with approximately ten years of active observations since 2016-11-21.

Use foreign ETFs/indexes for long signal-history research; require a Korea-listed **long ETF** for the underlying to enter the investable screening set. Domestic inverse ETFs are optional. Where no inverse ETF exists, the implementation can still assess **long/cash** and theoretical short diagnostics.

Currencies and bonds were deliberately removed from scope. Natural gas and some single-crop/livestock exposures lack verified qualifying domestic long ETFs and are currently out.

## Hypotheses (not findings)
1. Medium-term direction persists with a favorable trade-off between capture and whipsaw for some assets.
2. The relative advantage, if any, of metals versus equity indices can be quantified on a risk-adjusted basis.
3. Long/cash may outperform long/inverse ETF execution when inverse compounding and tracking losses are material.
4. Domestic listing/instrument design may change realized profitability even when the reference index signal is useful.

## Prior related work (not the same signal)
`weekly_trend/r01` already exists in this repository but enters after **two consecutive up weeks** and exits after **two consecutive down weeks**, rather than using 21-week SMA. Its 2026-09-01 archived baseline reported CAGR 5.56%, MDD -16.36%, average exposure 57.28% versus 10.44% equal-weight B&H and 15.22% SPY B&H CAGR. These are prior strategy results, not evidence that 21-week SMA works.

Reference:
- `doc/strategies/20260901-weekly-trend-r01.md`
- `runs/weekly_trend/r01/20260901-0001/llm-analysis-260901-btlab-country_weekly_trend.md`

## Research evidence
A local actual-data E2E completed all 18 candidate assets and produced a summary plus 18 Bokeh detailed reports. The canonical GitHub Actions archived run is not yet executed. Keep the underlying calculated results separate from interpretation; do not automatically add Agreed Insights.

## Risks / open issues
- Confirm Korea-listed funds, live listing status and exact index/FX/hedge/futures match; 18 is a provisional candidate count.
- Confirm weekly signal and next-session execution convention across markets.
- Confirm actual local ETF data coverage and costs; do not fabricate pre-inception returns.
- Keep actual inverse-ETF history separate from theoretical short payoffs.
- Existing GitHub Pages workflow is **PSAR-specific**; new case needs a dedicated report adapter/publication connection.

## Next research actions
1. Complete instrument and coverage audit.
2. Finalize r01 sizing and execution semantics with the user.
3. Implement isolated strategy and tests without modifying common core unless justified.
4. Register explicit automation runner, trigger GitHub Actions, inspect raw FFN/output.
5. Extend read-only reporting and publish a separate Pages case view without breaking PSAR Golden Master.


## Implementation checkpoint 2026-11-27

- Independent r01 strategy and source/ETF mapping added; uses real Korea ETF prices and weekly overseas index/ETF reference proxies when available.
- The existing canonical ten-column FFN performance table is reused without recalculation; summary has one Long/Cash row per asset.
- Report adapter produces summary and detail pages while preserving the existing PSAR root Page and common Bokeh renderer.
- Local E2E ran 18 assets and rendered 19 HTML files. Actions run and Pages deployment remain to verify.
- Shorter domestic ETF listing history, FX/futures differences, and close-only execution must be considered before interpreting returns.


## Reference-first correction (2026-11-27)

User clarified phase one evaluates the overseas reference ticker itself (GLD,
not KODEX gold futures, for example). Domestic ETF implementation is postponed.
The old 20261127-0001 archive remains immutable and must not be confused with
the phase-one reference run. Automation mode reference uses external ETF/index
prices and real inverse ETF data where available. The research summary keeps
its existing FFN columns, formats returns as percentages, and adds a separate
year-by-year table of all strategy returns. Non-US and proxy exceptions are
recorded in the coverage manifest; no conclusions about the research hypothesis
are claimed until the corrected results are reviewed.


## 2026-11-27 reporting refinement: monthly matrix

The user set strategy order to Long/Cash, Long/Inverse, Buy & Hold
(benchmark last). Each asset-specific annual table is followed immediately
by a monthly matrix with YYYY-MM rows and the three strategy columns.
The matrix uses the persisted monthly_performance.csv and does not alter
the existing FFN statistics or 18-asset overview table.


## Research assumption updated: 105-day SMA with daily monitoring

The user selected daily signal evaluation (Option B): 105 completed
trading-day SMA, daily confirmed closing price and next-eligible-trading-
session Close execution approximation. The former 21 completed-week
signal refreshed only once a week and did not match intended daily
monitoring. Prior 21-week runs remain immutable and are not comparable
as if their signal rules were identical.


## Third strategy added: Inverse/Cash

The user requested an isolated test of bearish-only exposure:
buy the actual inverse ETF only while the 105-day SMA daily
direction is negative, otherwise hold cash. This runs independently
of Long/Inverse. Detail output order is now Long/Cash,
Long/Inverse, Inverse/Cash, Buy & Hold (benchmark last).
No inverse means no investment-test series for the new strategy.
Existing returns are not rewritten.


## 3-Line Break daily long/inverse alternative

An independent daily 3-Line Break (3 confirmed-line reversal) long/
inverse strategy was added alongside SMA105. Per-asset display order is
Long/Cash, Inverse/Cash, Long/Inverse, LineBreak Long/Inverse, Buy & Hold.
The last remains benchmark. No inverse mapped means no inverse strategy
rows. Previously computed SMA105 strategy metrics remain unchanged.
The new strategy uses actual overseas ETF and inverse ETF prices
and archives a daily Line Break construction and decision trace.
