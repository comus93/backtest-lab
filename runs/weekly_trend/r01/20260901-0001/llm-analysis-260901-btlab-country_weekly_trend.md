---
title: "BTLab Country Weekly Trend - r01 baseline analysis"
date: 2026-09-01
type: backtest-analysis
project: backtest-lab
strategy: weekly_trend
revision: r01
run_id: 20260901-0001
tags:
  - backtest
  - momentum
  - weekly-trend
  - country-etf
  - backtest-lab
---

# BTLab Country Weekly Trend - r01 baseline analysis

## 1. Run summary

- Strategy: `weekly_trend`
- Revision: `r01`
- Run: `20260901-0001`
- Validation period: `2016-07-01 ~ 2026-07-31`
- Data: Yahoo Finance adjusted close
- Universe: 11 ETFs
  - SPY
  - QQQ
  - DIA
  - EWJ
  - EWY
  - MCHI
  - DAX
  - EWW
  - EIDO
  - INDY
  - EPHE
- Entry: 2 consecutive rising weekly closes
- Exit: 2 consecutive falling weekly closes
- Execution: next trading day after signal confirmation
- Position sizing: fixed `1/N` slot per active asset
- Cash: unused slots remain cash
- Move threshold: `0`
- Fee / slippage: project default

## 2. Key results

| Strategy | CAGR | Volatility | Sharpe | MDD | Avg Monthly Turnover | Avg Exposure |
|---|---:|---:|---:|---:|---:|---:|
| Weekly Trend 1/N | 5.56% | 9.16% | 0.639 | -16.36% | 36.70% | 57.28% |
| Universe Equal Weight Buy & Hold | 10.44% | 17.56% | 0.656 | -34.88% | 0.00% | 100% |
| SPY Buy & Hold | 15.22% | 17.88% | 0.885 | -33.72% | 0.00% | 100% |

Exposure statistics:

- Average market exposure: `57.28%`
- Average cash weight: `42.72%`
- Average active positions: `6.30 / 11`
- Active position range: `0 ~ 11`

## 3. Interpretation

### Drawdown control is strong

Weekly Trend 1/N reduced maximum drawdown from roughly `-34%` in the buy-and-hold comparisons to `-16.36%`.

The strategy therefore appears to perform the intended defensive function: when fewer assets satisfy the weekly trend condition, exposure falls automatically and the unallocated portion stays in cash.

### Return sacrifice is also large

The defensive effect came with a significant opportunity cost.

- Weekly Trend CAGR: `5.56%`
- Equal Weight Buy & Hold CAGR: `10.44%`
- SPY CAGR: `15.22%`

Average exposure was only `57.28%`, so a large part of the lower drawdown can plausibly be explained by the strategy holding substantially less risky-asset exposure rather than by superior timing alone.

### Risk-adjusted return has not improved yet

The key warning sign is Sharpe ratio.

- Weekly Trend: `0.639`
- Equal Weight Buy & Hold: `0.656`
- SPY Buy & Hold: `0.885`

Despite cutting volatility and drawdown materially, the strategy did not improve Sharpe versus the equal-weight universe.

This means the current `1/N` baseline should not yet be interpreted as evidence that the 2-up / 2-down weekly signal itself creates superior risk-adjusted returns.

## 4. Provisional conclusions

1. The weekly trend rule clearly changes portfolio risk characteristics.
2. The current `1/N` implementation creates substantial implicit cash timing.
3. The strategy currently looks more like a defensive exposure-control overlay than a return-enhancing momentum strategy.
4. The first run does not establish that the signal adds alpha after controlling for lower market exposure.
5. The baseline is still useful because it gives a clean reference point before increasing slot size or changing rise/fall thresholds.

## 5. Main limitation of this run

The biggest confounder is average exposure.

A portfolio invested only `57.28%` on average should naturally have lower volatility and lower drawdown than a portfolio invested close to 100%.

Therefore the next experiments should distinguish:

- benefit from the weekly trend signal itself
- benefit simply caused by holding more cash

This distinction is more important than optimizing the rise/fall threshold at this stage.

## 6. Next experiment candidate

The originally planned next axis is to increase the slot size from `1/N` to `2/N` because average cash weight in the baseline was `42.72%`.

A non-leveraged implementation will need a total portfolio exposure cap of `100%` when the number of active signals becomes large enough that the sum of `2/N` target slots exceeds 100%.

This should be treated as the next exposure experiment before introducing additional signal thresholds such as minimum weekly percentage moves.

## 7. Validation status

- Targeted `weekly_trend` pytest: `7 passed`
- Full test suite: `43 passed`
- E2E Yahoo run completed successfully
- No strategy blocker or market-data constraint reported

## 8. Related artifacts

- `performance_summary.csv`
- `equity_curves.csv`
- `weekly_decisions.csv`
- `exposure.csv`
