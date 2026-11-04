# Reporting Subsystem Specifications (v1)

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
