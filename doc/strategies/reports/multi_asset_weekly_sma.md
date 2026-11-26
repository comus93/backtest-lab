# Multi-Asset Weekly SMA Trend — Research Living Report

- Strategy ID: `multi_asset_weekly_sma`
- Initial revision: `r01`
- Created: `2026-11-27`
- Status: hypothesis registered; backtest **not executed**

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
No new 21-week SMA run outputs yet. Keep calculated metrics separate from AI interpretations, and add user-agreed insights only after discussing evidence.

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
