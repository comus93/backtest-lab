# Multi-Asset Weekly SMA Trend Research r01 (Implementation Pilot)

- Strategy ID: `multi_asset_weekly_sma`
- Revision: `r01` (new strategy, not a revision of `weekly_trend`)
- Revision date: `2026-11-27`
- Status: **implemented and locally verified; main-branch Actions and Pages publication pending**

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

## 8. Implemented r01 pilot and integration (supersedes planned parts above)

Implementation uses the explicitly mapped instruments in the multi_asset_weekly_sma strategy data module and runs all 18 independently. The source snapshot preserves missing cross-market dates and is saved by automation as input_prices.csv.

- Primary signal: last available fully completed weekly close > 21-week simple moving average = long; below average = cash or domestic inverse ETF; equal/missing = cash.
- Signal date is strictly earlier than the Korean ETF trade date. The next available domestic ETF Close is the current fill approximation because the data source is Close-only.
- Baseline: up to 100% single domestic ETF exposure in each independent study, with project default fee and slippage. No actual naked short trades.
- Reference signal and Korean ETF execution instruments are separated. Any differences in FX hedging, proxy, spot/futures or benchmark variant appear in the asset metadata.
- Main performance_summary.csv uses the existing ten-column BTLab performance-summary format unchanged, with exactly one Long/Cash row per asset. Actual Long/Inverse and Buy & Hold results appear in separate per-asset detail tables.
- Per-asset archived outputs include performance_summary, ffn_stats, equity_curves, weekly_signals and fills CSV; the combined run also includes asset_manifest and instrument_coverage CSV. Existing FFN calculations and metrics are NOT implemented again for reporting.
- Run automation explicitly allows multi_asset_weekly_sma / r01 / baseline. The actual triggering backtest-request.json is deliberately unchanged in the research PR.
- Reporting generates a standalone summary index and individual 18 Bokeh HTML equity pages. Only existing FFN values are displayed; no synthetic OHLC candles are generated from Close-only data. The original PSAR root report stays at its existing Pages path.
- The existing PSAR Golden Master tests must remain green and Pages must deploy the combined site artifact.

## 9. Verified status and limitations

The local proof-of-concept completed all 18 reference / domestic ETF study rows on actual Yahoo and FDR data and generated 1 summary and 18 asset HTML files. The GitHub Actions canonical run, recorded price snapshot and deployed Pages URL require a subsequent main-branch run.

Important: not all domestic ETFs cover the full ten years, so the summary retains start_date and end_date and must not be sorted as if all rows had equal coverage. FDR domestic Close is PRICE only and not a confirmed distribution-adjusted total-return feed. Inverse fund compounding differs from a theoretical short.

Theoretical short diagnostics, slope/sensitivity optimization, regime-duration and yearly subreports are not included in this first runnable version. The earlier sections are the broader research roadmap, not a claim that those outputs already exist.


## 10. Reference-first correction (2026-11-27)

User clarified that phase one must evaluate the external reference instrument itself, with
domestic ETF implementation postponed. Use explicit automation mode reference (r01).
The earlier baseline mode and run 20261127-0001 are preserved as a domestic implementation
experiment, not phase-one evidence. No revision number change or overwrite.

The reference instrument is both the weekly SMA signal and the actual long execution
series. Use Yahoo adjusted daily close for ETF data. Buy & Hold and Long/Cash
use the same reference ticker; Long/Inverse uses a separately observed inverse ETF
price only where matching available. GLL, ZSL and SCO are -2x DAILY products;
their results are not symmetric -1x short returns.

US-listed ETFs are preferred. Exceptions: KS200 is the non-tradable KOSPI200 price index
(FDR; hypothetical reference-price test, not an ETF); Japan uses 1329.T/1571.T
and 1306.T/1569.T in JPY. India uses INDY. TAGS is an approximate grains proxy
that includes sugar, not the exact three-grain basket. The former CSI300 inverse CHAD
liquidated in 2023 and is not used in the full-period study. Mapping, currency,
inverse daily multiplier, and Korean eligibility code are archived in instrument_coverage.csv.
No currency conversion across USD/JPY/KRW-index is performed; mixed-currency comparisons
are reference-market returns, not a common KRW investment return.

Calendar-year returns are calculated from the Runtime performance index before rendering.
The first anchor includes opening trade costs; each daily return belongs to its ending year.
Compounding annual returns must equal total_return. Keep the existing ten-column FFN
summary unchanged, display return/volatility/drawdown/turnover/exposure as percentages,
and add a separate annual table for all strategies in the summary and each asset detail.
2016 and 2026 are partial years, not annualized. Store yearly_performance.csv
in each asset folder and combined at the run root.


## 11. Monthly strategy return matrix and benchmark ordering (2026-11-27)

For every individual asset, report strategies in this fixed order:
Long/Cash -> Long/Inverse -> Buy & Hold, with Buy & Hold last as
the benchmark. When there is no inverse instrument, omit the strategy
from performance statistics and annual rows, but keep its monthly matrix
column as a missing observation, not as zero return.

The upstream Runtime-performance pipeline now saves monthly_performance.csv
per asset (strategy,month,return) and at the run root
(asset_id,asset,strategy,month,return). Month is YYYY-MM and return is a
fractional compounded return from daily Runtime performance increments.
The pre-first-fill anchor preserves initial transaction costs. Compounding
monthly returns by year must reproduce annual returns, and compounding
all months must reproduce total return. The existing FFN summary metrics,
their raw values and column order are unchanged.

The individual-asset report renders a chronological calendar month matrix
immediately below the year-by-year return table. Months are rows, and
Long/Cash, Long/Inverse, Buy & Hold are columns, with percentage values
to two decimals. 2016-11 and 2026-11 are partial months, not annualized.
Missing inverse is displayed as a dash. Archived historical runs are not
modified. The multi-asset overview remains focused on the existing one-row
per asset summary and its separate annual table.


## 12. Superseding signal resolution: daily 105-SMA (2026-11-27)

The user confirmed Option B after examining the 2017-03 GLD weekly
whipsaw: retain the roughly 21-week trend horizon but monitor daily.
For the next reference-first research run, 21 weeks x five sessions/week
is implemented as SMA over 105 actual daily trading closes, not a
weekly 21-close SMA, not a 105-calendar-day average. Weekly and daily
averages are not identical statistics; the studies must be separated.

- At close of reference market trading session t, evaluate daily Close[t]
  versus mean of Close[t-104..t], including t (105 closes).
- If close > SMA105: bullish; close < SMA105: bearish;
  equality/missing/warm-up: neutral cash.
- New signals are evaluated every trading day, not weekly.
- Earliest execution is on the next eligible trading session after t,
  priced at its Close under the Close-only historical input approximation;
  never assume closing price of t can be traded using its completed signal.
- Holidays are not filled. The first valid SMA requires 105 observed closes;
  pre-active history is warm-up only.
- Reference-first uses overseas ETF/index price series and actual
  inverse ETF prices, retaining documented Japan/KOSPI exceptions.
- Archive daily_signals.csv at root and in each asset folder, including
  sma105, signal_date and later execution_date. Coverage documents resolution.
- Keep existing FFN metrics, independent outputs, benchmark-last strategy
  ordering, annual and monthly tables.
- Archives 20261127-0001 through 0003 remain immutable prior weekly
  signal experiments. New reports show SMA105 without overwriting old runs.
- To reproduce in TradingView: 1D chart, SMA length 105, match provider
  adjusted-close versus unadjusted-close settings. The next-session Close
  execution estimate differs from TradingView next-session Open execution.


## 13. Independent Inverse/Cash study added (2026-11-27)

The user requested a pure inverse-position result, independent of the
existing combined Long/Inverse path. Inverse/Cash is the third visible
strategy and Buy & Hold remains the final benchmark:

1. Long/Cash: positive daily close vs 105-day SMA -> reference long;
   negative or neutral -> cash.
2. Long/Inverse: positive -> reference long, negative -> actual
   inverse ETF; neutral -> cash.
3. Inverse/Cash: **negative -> actual inverse ETF, positive or
   neutral -> cash**. No long ETF fills are allowed at any time.
4. Buy & Hold: benchmark long exposure, irrespective of SMA.

All signals use the same confirmed daily reference closes. Trades use
the following eligible trading-session Close and the original Runtime
fee/slippage settings. Inverse/Cash is independently backtested with
actual inverse ETF historical prices, including products that reset
daily (-1x or -2x, as archived in instrument coverage). It is NOT
the synthetic negative of the long ETF daily return. Where no actual
inverse exists/qualifies, both inverse-based strategies remain absent;
the two inverse columns in the monthly matrix display missing
values rather than zero performance.

For comparability, Inverse/Cash and Long/Inverse use the same long and
inverse price date intersection. The existing ten-column FFN
performance_summary contract and the independent one-row-per-asset
top-level summary are unchanged. Individual asset FFN summaries,
equity curves, yearly tables, monthly matrices, fills and signal
logs use the fixed four-strategy order above. Prior archived runs
are immutable.


## 14. Daily confirmed 3-Line Break alternative strategy (2026-11-27)

The user requested moving Inverse/Cash to second position and adding a
separate daily 3-Line Break direction strategy to compare against
daily SMA105. Previous cases remain immutable.

Fixed presentation order in all per-asset results, equity charts,
annual returns and monthly return matrix:

1. Long/Cash (SMA105)
2. Inverse/Cash (SMA105)
3. Long/Inverse (SMA105)
4. LineBreak Long/Inverse (3-Line Break, daily)
5. Buy & Hold (long benchmark, always last)

LineBreak Long/Inverse is independent of SMA105 signals: each reference
ticker's daily confirmed closing prices construct traditional price-only
Line Break lines, using the latest three FORMED CONFIRMED lines, NOT the
latest three trading days.

- The initial first reference close is the construction baseline.
  The first different subsequent close confirms the initial directional line.
- If the most recent confirmed line is UP, a close above that line's close
  creates a continuation line. Only a close strictly below the lowest low
  of the last 3 confirmed lines creates a DOWN reversal.
- If the last confirmed line is DOWN, a close below its close creates a
  new down line. Only a close strictly above the highest high of the last
  3 confirmed lines creates an UP reversal.
- Before 3 lines exist, available confirmed lines set the reversal bound.
  Equality does not create new lines.
- Days without new confirmed lines hold the prior line direction, and
  projected or unconfirmed lines are not used.
- Bullish state holds the long ETF, bearish state the actual inverse ETF.
  Before the first line, hold cash.
- Signals only become available after the daily close. Orders change
  positions at the next eligible trading-session Close at the earliest,
  using the original price-only execution approximation.
- LineBreak Long/Inverse uses the same overlapping real product dates
  as the existing Long/Inverse and Inverse/Cash strategies. Missing
  actual inverse data means this strategy is ABSENT (not synthetic).
- Keep existing FFN summary column definitions, one-row-per-asset
  overview, monthly/annual returns and Buy & Hold benchmark.

Audit output: line_break_signals.csv in each asset folder and run root
records signal_date, reference_close, direction, line_formed, reversal,
line_open, line_close, prior_line_high/low, and confirmed_lines.
Coverage metadata records line_break_lines=3, and the separate trade
decision log carries the LineBreak Long/Inverse entries. Reports read
the stored data; the reporting layer cannot recalculate signals.

TradingView comparison caveat: this is deterministic daily adjusted
Close line-break construction. TradingView chart may process different
intraday/OHLC bars or price adjustment settings, so verify it on the
1D Line Break chart, Number of Lines=3, rather than assuming bars
are identical without comparing source inputs.
Official TradingView specification:
https://www.tradingview.com/support/solutions/43000502273-introduction-to-line-break-charts/


## 15. Independent daily 3-Line Break Long/Cash

Add LineBreak Long/Cash immediately before LineBreak Long/Inverse.
It uses the same existing confirmed daily 3-Line Break state (3 lines)
but holds the long instrument on bullish state, cash on bearish/neutral
state, and never buys an inverse ETF. No new line retains the state.
The initial active position follows the last confirmed warm-up state;
later changes execute at the next eligible daily Close, same fees and
slippage as existing strategies. All 18 assets are eligible, using the
long-only calendar without requiring inverse data. Keep the five previous
strategies unchanged and the Buy & Hold benchmark last.


## 16. Active candidate universe narrowed (2026-11-27)

User excluded Russell 2000, EWY, China CSI300, WTI, three-grain
basket, soybeans, broad agriculture, and copper. The active universe
now contains exactly ten assets: SPY, QQQ, KS200, 1329.T, 1306.T,
INDY, EEM, FEZ, GLD, SLV. Keep KOSPI200; only EWY is removed from
Korean exposure. Both reference and domestic mappings use this
candidate set. All six strategy definitions, execution assumptions,
fees, fixed date range and existing inverse-product availability
rules are unchanged. Seven assets have actual inverse products in
reference mode. Historical 18-asset runs through 20261127-0007
remain immutable; the next run and current dashboard contain only
these ten candidates.
