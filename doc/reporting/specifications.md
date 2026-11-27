# Reporting Subsystem Specifications

## Current authoritative contract: composable renderer (v2)

Effective 2026-11-27, the user designated the layer-based Bokeh ChartComposer as the canonical renderer for new backtest-lab experiments. Gold Trend Research is the first consumer; Multi-Asset Weekly SMA is the second active consumer. PSAR-specific ReportData/ReportConfig, charts.py and render_report are deprecated for new work, retained for historical reproduction and existing URLs. Older requirements below describe legacy reports, not restrictions on v2.

### Canonical chart contract

- A panel uses a shared real datetime X range, a declared Y unit, and an independent viewport-based DataRange1d. Each large chart has visible date ticks; native pan/zoom/reset and aligned plot borders are retained.
- A Layer declares a stable key, display label, unit, explicit calculation/data basis and one or more Glyph specifications. A Glyph carries display-ready columns, rendering options, hover fields, and whether it participates in Y auto-ranging. No strategy identifiers or indicator calculation parameters are interpreted by the common composer.
- Compatible layers can coexist. Line, OHLC candles (including explicitly archived transformed OHLC), formed line-break blocks with horizontal dotted connectors, scatter, segment, step, area/band and other supported Bokeh glyphs are composable. One layer may contain multiple glyphs. A unit mismatch requires a separate panel with the same X range, not silent mixed-unit overlay.
- Chart adapters supply archived values and explicit source basis: SMA105 on raw Close remains raw-close SMA105 even when 3LB or HA is visible. No indicator recalculation or investment changes in Reporting. Only visual geometry (body bounds, confirmed-state connectors, coordinate projection) is derived here.
- Extended line break uses only actual formed blocks at their formation dates. Horizontal dotted connectors carry the last confirmed close until the next formation or the last available date; no fabricated new blocks, future prices, or time compression.
- Visible data glyphs define auto-range; decorative execution/holding glyphs can opt out. Actual fills remain distinguished from projected native chart coordinates.
- The strategy selector chooses default layer visibility and existing performance/P&L/drawdown data. Independent checkboxes allow any available compatible layer combination without changing strategy or results; changing strategy restores its default layers.
- The existing selectable performance, realized P/L and drawdown panels are reusable. Future adapters should compose with ChartComposer rather than implement strategy-specific rendering engines. Missing indicators are not invented; Close-only data supports lines, not fabricated candles.
- Reports remain standalone Bokeh HTML. Existing runs are immutable. Validate composition, units, causal bridge geometry, selector behavior and shared time axes; legacy tests remain for retained historical compatibility, not as a design constraint for v2.

### Multi-Asset Weekly SMA migration

The active series and pinned 20261127-0008 dashboard use the canonical composer.
The native signal chart uses archived reference Close, archived SMA observations
on their signal dates and extended Line Break blocks. The actual long instrument
execution chart stays separate, preserving reference/long units in legacy domestic
runs. Both charts display dates and share X with performance, P/L and drawdown.
Layers can be selected independently. Only archived data are rendered: no
synthetic OHLC, no recalculated missing SMA values, no additional HA strategy.
Incomplete historical archives without input prices or instrument metadata retain
their original equity-only fallback. No change to strategy or run files.

## Legacy and historical specifications (v1)

## Purpose and scope
Reporting is a **read-only post-processing subsystem** of backtest-lab. It accepts verified backtest output, including FFN analysis results, and publishes an interactive self-contained Bokeh HTML report. It must not execute a Strategy, mutate archived runs, recompute investment returns, or change Runtime/Portfolio accounting.

This first extraction supports the existing PSAR QLD/Cash case study with no functional or visual regression. A second unrelated strategy is **out of scope** until the common boundary passes the PSAR Golden Master.

## Data contract: ReportData

`ReportData` contains an ordered tuple of `ReportPeriod` objects, one per evaluated time window. Each period must carry:

| Field | Required canonical representation |
| --- | --- |
| `window` | A stable, human-readable period label |
| `prices` | datetime-indexed, unique, sorted DataFrame: `Open, High, Low, Close` numeric finite; optional `Volume` nonnegative |
| `equity` | aligned datetime-indexed DataFrame; one numeric performance-index column per `SeriesConfig.key`; each starts from the source's original normalization, never re-based in Reporting |
| `performance` | numeric DataFrame with four metric rows `Total Return, CAGR, Sharpe, Max Drawdown` and one column per displayed series, copied from the archived FFN summary |
| `ffn_stats` | raw FFN result matrix, `metric` column plus the same series keys; no unit conversion |
| `indicators` | optional datetime-indexed DataFrame with strategy-supplied overlay and candle-hover columns |
| `events` | completed or pending **execution events**: `date, display_price, symbol, side, price, qty, fee` |
| `trades` | **completed trades only**: `date, entry_date, entry_display_price, exit_display_price, return_pct, pnl, win, symbol` |

`events.price` is the **execution-instrument fill price**; `events.display_price` and `trades.*_display_price` are positions on the **display-instrument axis**. They must never be silently interchanged.

Date axes are shared among the charts inside a period. Price, equity, and indicators must align on the period's trading timestamps. Partially filled or multi-position portfolios must supply their own appropriately matched completed trades; the PSAR single-position pairing logic is not a generic accounting engine.

All DataFrames are treated as read-only after adaptation. A report may take already-calculated metrics from FFN, but must never recalculate CAGR/Sharpe/MDD from the plotted equity series.

## Configuration contract: ReportConfig

`ReportConfig` describes presentation, not investment logic.

- `series`: ordered `SeriesConfig(key, label, color, width, table_label?)`. Chart legend and comparison-table header can differ while sharing one series key; the first series is the primary strategy for drawdown.
- `overlays`: strategy-selected `OverlayConfig(field, label, color, marker)` for price overlays (e.g. PSAR, not hardcoded in the chart engine). All overlay marker sizes are controlled by one global `ReportConfig.indicator_marker_size` (default 2px).
- Titles/labels and user-facing notes, as well as `signal_symbol`, `execution_symbol`, and `display_symbol`, are explicit.
- Shared `ReportPalette` defines candles, monthly OHLC, trade-span gain/loss, execution markers, grids, and P/L dots.
- `show_volume=False` by default; enabling requires actual complete `Volume` data and adds a short chart immediately below OHLC with the **same x-range**. No synthetic zero bars.
- `show_monthly=True`, `show_trades=True`, and `show_raw_ffn=True` are presentation switches. Unused overlays are omitted rather than treated as mandatory.
- All defaults must preserve the PSAR Golden Master unless explicitly overridden in the PSAR adapter.

## Presentation acceptance criteria

1. Four windows, same normalized equity endpoints, FFN values, trade counts, plotted series and execution dates as the PSAR baseline.
2. Header summary and per-period performance tables have metrics as rows and comparators as columns. Raw FFN table retains its original units.
3. Default panels in each window: Equity, Profit / Loss, Strategy Drawdown, OHLC with monthly overlay, indicator dots, execution triangles and colored dashed trade spans. No redundant cumulative-return panel.
4. Equity hover selects one nearest visible curve, price hover shows OHLC and adapter-provided indicator fields, linked dates permit pan/zoom, and legends can hide series.
5. QQQ Korean-style bullish red / bearish blue daily candles, muted directional monthly OHLC; 3px dashed trade spans with 0.80 alpha, muted profit green and raspberry loss; shared 0.20-alpha grid.
6. Signal/Execution/Display instruments remain distinct; no projected QLD fill price is misrepresented as QQQ dollars. Open trades never receive invented realized-P/L points.
7. Optional real Volume is aligned to price dates; absent/invalid data with volume enabled raises an explicit error.
8. The renderer emits standalone HTML using embedded BokehJS and keeps the CLI/Pages entrypoint compatible.
9. Archived input CSV values and newline-normalized bytes are identical before and after refactoring; tests compare an immutable Golden Master manifest pinned to commit `38eee2673663c11931857b6fd71509968b193a3d`.
10. No new indicator calculation, new backtest run, data download, external network fetch, or PSAR revision change is permitted during report building.

## Boundaries and follow-ups

The FFN adapter here consumes **already archived FFN metrics**. An adapter from live `ffn.GroupStats` or `PerformanceStats`, a configurable multi-position trade ledger, and a second unrelated strategy are future work only after acceptance. The Golden Master freezes deterministic data and Bokeh model structure, not raster-perfect browser screenshots.


## Second case: weekly SMA summary

The 2026-11-27 second-case adapter is limited to its own read-only
archived CSVs and does not alter the PSAR ReportData/ReportConfig contracts,
common charts or immutable PSAR Golden Master fixture.

The multi-asset summary reuses the same performance_summary columns and FFN
values without recalculation. One summary HTML links to separate detail HTMLs.
The current data snapshot contains daily Close only: the adapter uses
Bokeh equity lines instead of inventing OHLC price candles or misplacing
foreign reference instrument prices on a KRW domestic ETF axis.


## Multi-asset daily SMA105 report update (2026-11-27)

New reference-first reports identify 105 trading-day SMA, daily signal
monitoring and next-session Close execution estimate. Legacy archives
without the sma_days metadata remain identifiable as historic 21-week
reports. Existing FFN metric definitions, year/month report matrix and
PSAR Golden Master remain unchanged.


## Inverse/Cash presentation (2026-11-27)

The multi-asset SMA105 reporting adapter displays individual strategy
statistics, equity curves, yearly tables and monthly return matrices
in the same order: Long/Cash, Long/Inverse, Inverse/Cash, Buy & Hold.
Inverse/Cash is missing rather than zero when no eligible inverse
product exists. The combined asset-level FFN summary remains unchanged.
Reporting reads stored results, never calculates inverse gains.


## Reference study Line Break and order (2026-11-27)

All per-asset read-only reporting sequences use:
Long/Cash -> Inverse/Cash -> Long/Inverse ->
LineBreak Long/Inverse -> Buy & Hold (benchmark).
The monthly matrix shows five column positions, with missing values
rather than zero when inverse tickers are absent. Yearly tables
and FFN only show executed strategies. The Line Break signal is
computed in the strategy, not Bokeh/shared FFN tables.
Older archived results and PSAR Golden Master remain untouched.


## Multi-asset summary selector and monthly sticky headers (2026-11-27)

The overview Performance Summary offers a strategy selector in the
canonical five-strategy order, defaulting to Long/Cash. Every selected
view retains one row and detail link per asset, the existing ten FFN
columns, and archived per-asset metric values. Unavailable strategy
metrics are shown as missing, never zero. Show coverage counts and
switch views client-side without recomputing returns or fetching data.
The annual overview remains a comparison of all strategies.
The per-asset monthly matrix uses a single horizontal/vertical scroll
container with sticky opaque header cells, so column labels stay
visible during internal vertical scrolling. These changes are confined
to the multi-asset reporting adapter; archived runs and PSAR are unchanged.


## LineBreak Long/Cash addition

The six-strategy order is Long/Cash, Inverse/Cash, Long/Inverse,
LineBreak Long/Cash, LineBreak Long/Inverse, Buy & Hold.
The overview selector, individual FFN tables, curves, annual and monthly
matrices include the new strategy. Monthly sticky headers remain enabled.
The new long-only strategy is available even without an inverse product.


## Active universe refinement

The latest multi-asset run uses the ten user-selected candidates.
Report links, selector coverage and annual tables follow the archived
asset manifest, not a hardcoded count. The six-strategy order and sticky
monthly headers are unchanged. Historical run reports remain renderable.


## Selectable PSAR-style trade analysis

For each asset with archived closes and instrument coverage, render one
strategy selector and exactly four linked figures: Performance (selected
strategy and Buy & Hold, no duplicate benchmark), realized fee-net
trade P/L, Strategy Drawdown from the archived performance path, and
Execution Date on actual archived daily long closes. For reference-mode
studies the long ticker is the reference ticker. For domestic-mode
archives use and label the actual long execution instrument as the display
axis. Never synthesize OHLC. Source switches preserve the shared date range.
Buy/sell markers use actual fill dates; tooltips distinguish decision
dates, actual instrument and fill price from projected display close.
Trade spans indicate actual holding intervals and fee-net outcome; the
open position extends only to the strategy's last active day and has no
realized P/L point. Cash gaps are uninvested intervals within the active
strategy dates. Use calendar holding days. Same-day rotations may overlap
markers; both fills remain recorded. Only available strategies are selectable.
Read all archived data without changing the run or FFN values. Legacy
incomplete archives may render the original equity-only plot with an
explicit note. Preserve annual/monthly tables and sticky headers.

## Selectable chart viewport Y scaling

All four selectable detail panels use independent Bokeh DataRange1d
ranges with window_axis="x": visible-window data min/max with native
padding, not full-history limits. Use visible performance curves,
realized P/L points, drawdown values and daily display closes respectively.
Decorative zero-fill and holding spans do not influence ranges; execution
markers already lie on daily display closes. No special forced zero bound.
For empty windows Bokeh uses its native fallback; flat ranges use its
default span. Horizontal pan, wheel and box zoom retain the shared X
range; vertical pan/wheel zoom are optional per-panel toolbar tools.
Native Reset restores auto-ranging and resets the selected time window.
This is presentation only; PSAR renderer and archived runs are unchanged.


## Gold native strategy visualization

Gold report composes the shared selectable renderer with a native signal panel. Raw GLD Close is default, real OHLC optional. SMA price/average, calendar-aligned formed 3LB blocks and archived HA candles switch with the selected strategy. All five panels share calendar X and independent viewport Y ranges. Execution prices remain actual instrument prices; synthetic signal chart marker coordinates are only projections. PSAR and existing multi-asset views are unchanged.

The raw price and native strategy charts each show their own date ticks on the shared X range, while retaining aligned plot borders. Each retains its native Bokeh Reset tool for zoom/pan reset; no custom reset callback is introduced.


## Research index

GitHub Pages root is the static research catalog, built after published reports from strategy specifications, living reports, and archived run directories. New series are discovered automatically. Active status is explicit; unspecified series are not deemed retired. Link only to existing generated dashboards, and otherwise link repository documents and run records. The legacy PSAR report is published at research/psar_segment_duration/. No run mutation or backtest execution.
