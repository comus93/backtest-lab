# Multi-Asset Weekly SMA Trend Research r01 (Draft)

- Strategy ID: `multi_asset_weekly_sma`
- Revision: `r01` (new strategy, not a revision of `weekly_trend`)
- Revision date: `2026-11-27`
- Status: **research specification draft; not implemented or registered for automated execution**

## 1. Purpose / hypotheses

Test whether medium-term trend persistence differs materially across precious/industrial metals, energy, agriculture, and major equity indices, and whether a simple 21-week moving-average rule produces attractive risk-adjusted outcomes.

Separate three questions:
1. Do individual reference assets display useful trend persistence and limited whipsaw versus equity indices?
2. Does a common weekly 21-SMA signal improve outcomes against each asset's buy-and-hold and cash alternatives?
3. How much of theoretical trend performance survives when invested through **Korea-listed ETFs** (including locally listed inverse ETFs where available)?

The initial claim that metals are less volatile than equities is a hypothesis, not an assumed result.

## 2. Universe and inclusion rule

**Domestic listing is the universe-entry filter, not an inverse-ETF requirement.** Every accepted asset must have at least one Korea-listed long ETF. An inverse ETF is optional and affects only the executable short-side analysis. Use overseas reference ETFs or the actual benchmark index to study signals, with explicit symbol mapping.

Initial 18 **candidate underlying exposures**, subject to current domestic listing and index-match audit:

| Group | Candidate underlying | Overseas signal proxy / reference |
| --- | --- | --- |
| Equity | US S&P 500 | SPY |
| Equity | US Nasdaq 100 | QQQ |
| Equity | US Russell 2000 | IWM |
| Equity | Korea KOSPI 200 | KOSPI 200 index (EWY is **not** equivalent) |
| Equity | Korea MSCI | EWY / matched MSCI Korea index (check variants) |
| Equity | Japan Nikkei 225 | Nikkei 225 index (EWJ is **not** equivalent) |
| Equity | Japan TOPIX | TOPIX index |
| Equity | China CSI 300 | CSI 300 index (FXI / MCHI are **not** equivalent) |
| Equity | India Nifty 50 | Nifty 50 index (INDY may differ; check) |
| Equity | Emerging markets | EEM, matching benchmark to Korea ETF |
| Equity | Euro Stoxx 50 | EURO STOXX 50 index |
| Metals | Gold | GLD or suitably matched gold futures series |
| Metals | Silver | SLV or suitably matched silver futures series |
| Metals | Copper | CPER / matched copper futures index |
| Energy | WTI crude oil | USO / matched WTI futures index |
| Agriculture | Grains basket | Matched grains futures index |
| Agriculture | Soybeans | SOYB / matched soybeans futures index |
| Agriculture | Agriculture basket | Matched agriculture futures index |

**Excluded:** FX/currency pairs, bonds, natural gas and single wheat/corn/sugar/livestock markets unless an appropriate domestic long ETF is verified. No universe asset is excluded merely for lacking a domestic inverse.

Before implementing, audit each Korea-listed ETF's current listed/tradable status, underlying benchmark (spot/futures/index variant), currency hedge, leverage and effective dates. Do not silently equate unmatched US and Korea ETFs.

## 3. Data and period

- Active evaluation: `2016-11-21` through **completed weekly bar ending `2026-11-20`** (Asia/Seoul research cutoff). Some data loaders use end-exclusive `2026-11-21`.
- Obtain pre-active warm-up history sufficient for 21 **completed** weekly closes; prefer an extra margin for calendar interruptions.
- Signal sources: overseas ETF adjusted close or the representative index/futures series, as explicitly mapped per asset.
- Actual investment-performance sources: matching **Korea-listed ETF** adjusted prices in KRW, with inception/coverage constraints openly stated.
- Show per-asset actual coverage, backfill/source changes, and a common overlapping period separately; do not invent simulated Korean ETF history.
- Price index vs total-return / futures roll yield / FX hedge differences must be documented.

## 4. Initial signal model to test (not yet final execution specification)

At a completed weekly bar `t`, calculate `SMA21_t = mean(close[t-20:t])` from **21 completed weekly prices**, including week `t`.

Proposed baseline classification:
- `close_t > SMA21_t`: bullish
- `close_t < SMA21_t`: bearish
- equality/missing/warm-up: neutral (cash; detailed missing-data rules to confirm)

Observation is based solely on confirmed prior weekly closes. A position arising from week `t` must be executed at the next eligible trading session, not at the already-known signal close. Use each underlying's exchange holiday calendar and its matched trading ETF execution calendar.

Do **not** optimize or add slope, hysteresis, stop, leverage, confirmation or volatility threshold to the first baseline. These are subsequent independent experiments.

## 5. Independent experiments and real-world tradability

Each candidate underlying is first tested as an **independent strategy**, not an equal-weight multi-asset portfolio.

- **Signal diagnostics** (all 18): duration of bullish/bearish runs, switch/whipsaw count, weeks per regime, next-period conditional returns, cross-asset comparison.
- **Reference-asset long/cash** (all 18): long bullish periods, cash otherwise.
- **Theoretical long/short** (all 18): long bullish and short bearish to assess signal symmetry; explicitly not an investable ETF result.
- **Korea ETF long/cash** (where domestic price history available): invest only in the domestic long ETF during bullish states.
- **Korea ETF long/inverse** (only where corresponding domestic inverse exists and is verified): bullish -> domestic long ETF, bearish -> domestic inverse ETF. Measure actual inverse prices, **never** calculate inverse P&L as negative long return.

Compare by underlying and by experiment: buy-and-hold, cash baseline, and strategy returns. Keep a separate accounting of long versus short contribution. The 18 assets are not ranked on raw CAGR alone without normalizing for volatility/exposure and coverage.

## 6. Execution / portfolio questions requiring resolution before implementation

1. Signal series index/ETF benchmark mapping, Korea-listed ETF ticker and inception coverage; treatment of mixed USD/reference vs KRW-execution.
2. Entry/exit execution price: next open versus next close; ETF calendar misalignment and crossed foreign/Korean hours.
3. Position size: 100% exposure for each independent single-asset test is the initial comparison candidate, **not yet user-approved**.
4. Neutral equality/missing signal policy and rebalancing detail.
5. Consistent global project fee/slippage settings and optional turnover controls; no ad-hoc fees in Strategy.
6. Inverse ETFs with daily reset, leverage factors, tracking/roll costs and survivorship; special handling must be evidence-backed.

## 7. Reporting and expected outputs (plan)

Reuse Runtime and FFN. Do **not** duplicate FFN canonical metrics; preserve raw FFN stats plus normalized comparative summary:
- total return / CAGR / volatility / Sharpe / max drawdown
- average monthly turnover, exposure, trade count, annual performance and equity curve
- weekly signal diagnostics, regime duration, switches/whipsaws, long vs short contributions
- per-asset coverage and symbol/instrument metadata

Proposed outputs include `input_prices.csv`, `ffn_stats.csv`, `performance_summary.csv`, `equity_curves.csv`, `weekly_signals.csv`, `regime_summary.csv`, `yearly_performance.csv`, `instrument_coverage.csv`, and `fills.csv`. Final file schemas are deferred until execution rules are agreed.

For the Pages view, create a **strategy-specific reporting adapter** mapping immutable run artifacts to `ReportData`/`ReportConfig`. Reuse existing Bokeh renderer without embedding commodity or ticker-specific assumptions in common charts. Run the PSAR Golden Master tests before changing shared reporting. Present per-asset tabs/tables and distinct reference-signal versus Korea ETF execution prices.

## 8. Integration with the existing repository

- Spec (this document): `doc/strategies/20261127-multi-asset-weekly-sma-r01.md`
- Living research report: `doc/strategies/reports/multi_asset_weekly_sma.md`
- **Future**, once agreed: `src/backtest_lab/strategies/multi_asset_weekly_sma/r01.py`
- **Future** tests: `tests/strategies/multi_asset_weekly_sma/test_r01.py`
- **Future** dispatcher: explicit allow-list in `src/backtest_lab/automation.py`
- **Future** trigger only after allow-list and tests: `automation/backtest-request.json`
- **Future** output: `runs/multi_asset_weekly_sma/r01/<run_id>/`
- **Future** Pages: report adapter and publishing workflow, preserving PSAR report.

Do not edit `automation/backtest-request.json` at specification stage: changing that file triggers a live GitHub Actions backtest, and this new strategy has no registered runner yet.

## 9. Acceptance tests (for implementation phase)

- Weekly resampling uses last available completed trading day, handles Korean/foreign calendar boundaries.
- 21-week SMA uses no future bar and has sufficient warm-up without pre-start fills.
- Prices above/below/equal SMA map to explicitly agreed signals.
- Changed next-day execution prices cannot alter the previous signal.
- Independent assets have independent decisions and exposure.
- Reference theoretical short is never passed off as Korea inverse ETF return.
- Price / currency / benchmark mismatches and insufficient coverage are surfaced, never silently filled.
- FFN and reporting metrics are computed upstream; reporting is strictly read-only.
- Existing automation and PSAR reporting Golden Master regression suite passes.
- End-to-end run uses verified real data and preserves immutable outputs with reproducible `input_prices.csv`.

## 10. Status and blockers

This is a **registration draft** of the agreed research direction, not evidence that data were downloaded, a strategy was implemented, tests passed, Actions ran, or Pages published. Further discussion is required to finalize execution timing, ETF symbol mapping and sizing.
