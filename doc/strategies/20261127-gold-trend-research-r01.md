# Gold Trend Research r01

- Strategy ID: `gold_trend_research`
- Revision: `r01`
- Parent evidence: `multi_asset_weekly_sma/r01/20261127-0008`
- Status: implementation for initial strategy-visualization experiment

## Objective

Fix gold as the research asset and compare independent rules. The central
research challenge is visualizing each strategy in its native chart form
against the actual asset price, not merely comparing aggregate returns.
The parent run remains immutable and separately accessible.

## Data and execution

Download genuine daily adjusted OHLC for GLD and GLL (Yahoo Finance,
auto_adjust=True), starting 2016-01-01 through 2026-11-20; archive the
exact input as input_prices.csv. Active period 2016-11-21 to 2026-11-20
(end-exclusive 2026-11-21). Use GLD adjusted Close for signals and long
execution; actual GLL adjusted Close for inverse execution. No synthetic
OHLC, no forward-filled prices or fabricated short returns. Fresh OHLC
data may differ from the parent's Close-only snapshot; report baseline
differences rather than overwriting parent evidence. GLD and GLL are USD;
GLL targets daily -2x and is not a symmetric spot short.

Use the parent r01 SMA105 and 3-Line Break rules and original position
variants as controls. Use Runtime/FFN, independent initial capital
1,000,000, full-position rotation, 0.015% fee per side and default zero
slippage (Runtime configuration), no cash yield or forced exit. Signals
use completed bars; fills occur at the next eligible real session Close.
Long-only uses GLD dates; inverse strategies use the common GLD/GLL calendar.

## Heikin Ashi initial rule (implementation choice)

For each actual OHLC candle:
- HA Close = (O + H + L + C)/4.
- First HA Open = (O + C)/2; subsequent HA Open = previous
  (HA Open + HA Close)/2.
- HA High = max(actual High, HA Open, HA Close).
- HA Low = min(actual Low, HA Open, HA Close).
- Bullish if HA Close > HA Open; bearish if less; equality neutral.

Long/Cash: bullish -> GLD; bearish or neutral -> cash.
Long/Inverse: bullish -> GLD; bearish -> GLL; neutral -> cash.
No extra confirmation, wick filter or optimized thresholds in this
initial experiment. Synthetic HA prices are never execution prices.

## Comparison matrix

SMA105 Long/Cash, Inverse/Cash, Long/Inverse;
3LB Long/Cash, Long/Inverse; Heikin Ashi Long/Cash, Long/Inverse;
Buy & Hold last. Additional strategies such as 4LB are deferred.

## Visualization contract

One strategy selector controls the following five vertically aligned
panels sharing the same calendar X range:

1. GLD actual price with default Close line and optional real OHLC
   candles. Actual execution dates, buy/sell markers, and holding spans.
2. Native selected strategy chart: actual price plus SMA105; 3LB
   blocks only on actual formation dates; or genuine computed HA
   candles with open/high/low/close. Buy/sell dates and holding intervals
   projected onto chart coordinates, not synthetic fill prices.
3. Performance: selected strategy against Buy & Hold.
4. Realized fee-net trade P/L.
5. Strategy drawdown.

The 3LB chart uses actual calendar dates rather than compressed line
indices, leaving gaps when no line formed. Execution markers may fall
on dates without new blocks. Preserve independent adaptive Y min/max,
manual Y tools, shared X pan/zoom and time range on selector changes.
All transformed OHLC and signal values are archived by the strategy;
reporting reads them rather than recalculating strategy rules.
Annual/monthly return matrices and FFN metrics read the archived results.

## Acceptance

Test HA recursion, causality, execution on real prices only, strategy
ordering, same linked X range, native chart glyphs, and existing PSAR
regressions. Run through the registered GitHub Actions dispatcher.
Publish the gold series separately at research/gold_trend_research/.


## Reporting v2 migration

The native strategy panel uses the canonical ChartComposer. Extended 3LB connects each last confirmed Close with horizontal dotted segments until the next block (or final date). SMA105 and other compatible archived layers can be independently enabled over 3LB or HA without altering strategy decisions. The strategy selector restores native defaults; execution marker projection remains tied to the selected strategy, with actual fills on the raw chart.
