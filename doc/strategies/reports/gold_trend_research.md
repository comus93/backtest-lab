# Gold Trend Research — Research Living Report

- Strategy ID: `gold_trend_research` (working ID)
- Created: 2026-11-27
- Status: research charter; no executable revision or new run yet
- Parent evidence: `multi_asset_weekly_sma/r01/20261127-0008`

## Objective and scope

Fix the asset to gold and compare alternative trading rules independently.
The original multi-asset series varies assets while comparing common rules;
this series varies rules on one asset. Neither series replaces the other.
New experiments must have their own strategy ID, revision and run directories.

## Inherited control experiment

Use [the authoritative parent specification](../20261127-multi-asset-weekly-sma-r01.md)
and [the archived gold result](../../../runs/multi_asset_weekly_sma/r01/20261127-0008/assets/gold/)
as frozen reference evidence. Parent archive commit:
`59ef7b7a4c3efe0e1b4291bf58ff547e47ae865a`.

For a fair initial comparison, propose retaining GLD adjusted daily Close as
the signal and long-price series, the observed GLL daily -2x price series for
existing inverse cases, the original price snapshot including warm-up, USD,
2016-11-21 through 2026-11-20, initial capital 1,000,000, full-position
rotation, next eligible Close fills after confirmed signals, 0.015% fee per
side, zero slippage and no cash yield. Inverse results are real product
returns, not a synthetic symmetric short. The exact inherited six controls:

| Signal | Position rule |
| --- | --- |
| SMA105 | Long/Cash |
| SMA105 | Inverse/Cash |
| SMA105 | Long/Inverse |
| Daily 3-Line Break | Long/Cash |
| Daily 3-Line Break | Long/Inverse |
| None | Buy & Hold (GLD benchmark) |

The gold-only work must not modify the parent strategy or its historical
runs. Reproduce the six control results against the frozen input before
interpreting new strategies. Domestic ETF and KRW execution remain separate.

## Candidate experiments (proposals, not approved rules)

- 4-Line Break and optionally 5-Line Break, to examine reversal sensitivity
  and whipsaw versus delayed trend capture.
- SMA hysteresis or confirmation rules, to reduce repeated crossings.
- Other independent trend indicators or combined signal models only after
  their exact entry, exit and position rules are agreed. OHLC-dependent
  indicators require real OHLC and a separately documented data change.

Avoid selecting an optimal rule using the same ten-year sample alone.
Report risk-adjusted performance, drawdown, exposure, turnover, trade
frequency and trade/holding behavior, as well as annual/monthly returns.
Any out-of-sample or walk-forward design is a subsequent decision.

## Reporting and lifecycle

Reuse Runtime, FFN and the selectable four-panel detail renderer with linked
time axes and viewport-based independent Y auto-scaling. A gold-only report
should compare strategies directly rather than require an asset selector.
Retain Buy & Hold as benchmark and read archived inputs without mutation.
Proposed independent source/output paths after r01 is agreed:

- `doc/strategies/YYYYMMDD-gold-trend-research-r01.md`
- `src/backtest_lab/strategies/gold_trend_research/r01.py`
- `runs/gold_trend_research/r01/<run_id>/`
- `research/gold_trend_research/` (future Pages route)

The next research decision is which additional strategies and position
rules enter r01. No new run or performance claim is made here.


## r01 visualization experiment (2026-11-27)

User prioritized native strategy visualization using genuine OHLC, linked raw-price and strategy panels, visible actual execution/holding intervals, plus existing performance and P/L. Heikin Ashi is the first new indicator. See [r01 specification](../20261127-gold-trend-research-r01.md). Initial HA direction and position variants are implementation choices, not an optimized strategy or a confirmed finding.
