# US Market Cap Leaders r01

## Identity

- Strategy ID: `us_market_cap_leaders`
- Revision: `r01`
- Research period: 2010 Q2 through 2026 Q2
- Ranking source: reconstructed quarter-end US market-cap Top-2 dataset derived from `second/inbox/2026-09-08-us-market-cap-historical-source-reconstruction.md`

## Research question

Compare concentrated ownership of the largest US company/companies by point-in-time market capitalization against broad and growth-heavy US equity benchmarks.

Variants:

1. `TOP1`: hold the quarter-end US market-cap rank #1 company at 100%.
2. `TOP2`: hold quarter-end ranks #1 and #2 at 50% / 50%.
3. `SPY Buy & Hold` benchmark.
4. `QQQ Buy & Hold` benchmark.

## Signal and execution semantics

- Ranking is observed at each calendar quarter end.
- The ranking may only affect trades on the first available market-data timestamp strictly after the ranking date.
- This preserves no-lookahead / T+1 semantics.
- If the same Top-2 names remain selected, `TOP2` still rebalances to 50/50 at the next quarter's first trading day.
- `TOP1` remains 100% invested in the current rank #1.
- The 2026-06-30 ranking is retained as source evidence but does not affect performance ending at 2026-06-30 because its first eligible execution is in 2026 Q3.

## Backtest period

- Price coverage start: `2010-03-31`
- Active investment start: first trading day after `2010-03-31`
- Performance end: `2026-06-30`
- Loader end-exclusive value: `2026-07-01`

## Market data

Yahoo Finance adjusted close is used for all tradable symbols and both benchmarks so portfolio returns are measured on one consistent price basis.

Required symbols across the reconstructed ranking history:

- `AAPL`
- `AMZN`
- `GOOGL`
- `MSFT`
- `NVDA`
- `XOM`
- `SPY`
- `QQQ`

Ranking data is decision input only. It is not used as an execution-price source.

## Automation modes

### baseline

One GitHub Actions run compares:

- TOP1
- TOP2
- SPY Buy & Hold
- QQQ Buy & Hold

Expected outputs:

- `input_prices.csv`
- `ffn_stats.csv`
- `performance_summary.csv`
- `equity_curves.csv`
- `yearly_performance.csv`
- `quarterly_rankings.csv`
- `quarterly_selections.csv`
- `fills.csv`

### window_sensitivity

One GitHub Actions run repeatedly starts the same four portfolios at quarter-start execution dates and evaluates multiple ending quarters.

Primary fixed windows:

- 3 years
- 5 years
- 10 years

The same run also evaluates all start/end quarter combinations with at least five years of elapsed history.

Expected outputs:

- `input_prices.csv`
- `quarterly_rankings.csv`
- `window_performance.csv`
- `rolling_summary.csv`

`window_performance.csv` includes strategy-level FFN metrics and benchmark deltas for each start/end window.

`rolling_summary.csv` summarizes fixed 3Y / 5Y / 10Y window robustness for TOP1 and TOP2 versus SPY and QQQ, including median, quartiles, extremes, and win rates.

## Primary metrics

Preserve the full FFN statistics in baseline output. Summary/evaluation outputs emphasize:

- Total Return
- CAGR
- Daily Volatility
- Daily Sharpe
- Daily Sortino
- Max Drawdown
- Calmar
- Average Monthly Turnover

Window comparison additionally records:

- excess CAGR vs SPY / QQQ
- Sharpe delta vs SPY / QQQ
- MDD improvement vs SPY / QQQ

Positive MDD improvement means the strategy suffered a less severe drawdown than the benchmark.

## Data-quality boundary

The reconstructed ranking table is treated as a research input with source/confidence metadata.

Current confidence summary:

- 2010-2017: high, FT / archived FT centered
- 2018-2020: medium-high, FT + PwC + secondary cross-checks
- 2021-2025: medium, additional point-in-time verification remains desirable
- 2026 Q1-Q2: medium-high, FinanceCharts and LSEG cross-checks

The backtest must preserve this ranking evidence in raw outputs. Strategy logic must not synthesize missing market caps or silently change a supplied rank.

## Acceptance checks

1. 2010-03-31 ranking cannot trade on 2010-03-31 itself.
2. TOP1 invests 100% in rank #1 on the next available timestamp.
3. TOP2 invests 50/50 in rank #1 and #2 on the next available timestamp.
4. A new quarter ranking is applied only after its ranking date.
5. TOP2 rebalances to equal weights each quarter even if the same two names remain selected.
6. SPY and QQQ are evaluated from the exact same active start/end dates as TOP1/TOP2.
7. Baseline ends at 2026-06-30; the 2026-06-30 ranking must not generate a Q3 fill.
8. Window sensitivity is computed from fresh Runtime runs for each start date, not by merely slicing one full-period strategy path.
9. Each start-date Runtime run may be sliced across multiple end dates for FFN evaluation.
10. Core Runtime / Portfolio behavior is not changed for this strategy.
