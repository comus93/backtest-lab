# Reporting Subsystem Architecture

## Current authoritative architecture (v2)

Canonical path for new experiments: archived Runtime/FFN and indicator traces -> strategy adapter -> typed Layer/Glyph descriptions -> ChartComposer -> Bokeh Figure -> standalone report. The shared selectable_charts.py builder supplies the existing performance, P/L and drawdown views and execution selector.

- composer.py owns generic ChartComposer, Layer, Glyph, line_layer, candle_layer and line_break_layer. It composes compatible renderers on a supplied shared datetime range, validates unit/identity/column lengths, manages visible-layer auto-ranging and optional independent visibility controls.
- Strategy adapters own provenance, data mapping, indicator calculation upstream, layer defaults and trade-coordinate projection. The renderer is not a trading DSL, portfolio engine or indicator library.
- Gold Trend Research is the first consumer, combining raw Close/candles, SMA105, extended 3LB and execution layers on shared dates (HA is retained in archived results but excluded from the active Trend Research report). New indicators can use existing generic glyphs without modifying the composer; add helpers only when useful across cases.
- New experiments must use this composition contract and shared performance panels. Multi-Asset Weekly SMA is an active second consumer of the canonical composer, including its fixed-run dashboard. PSAR v1 alone remains deprecated for new development; historical URLs and raw runs remain intact.

## Legacy and historical architecture (v1)

## Module boundary

```text
Strategy / Runtime outputs  ─┐
FFN computed statistics      ─┼─> strategy adapter ─> ReportData + ReportConfig
Other archived source data   ─┘                           │
                                                        v
src/backtest_lab/reporting/                          common renderer
  models.py                  (typed data/config contracts) │
  palette.py                 (shared colors)               ├─ tables.py
  tables.py                  (formatting FFN tables)         ├─ charts.py
  charts.py                  (Bokeh panel constructors)     └─ render.py
  render.py                  (tabs, HTML output)
  adapters/psar.py           (archived PSAR CSV mapping and QLD/QQQ trade projection)
  psar_report.py             (backward-compatible CLI and public wrapper)
```

Reporting is downstream of `backtest_lab.analysis`. It does not modify `ffn`, modify the Strategy, or use `backtesting.py` (whose AGPL plotting source is not copied).

## Responsibilities

- **Adapter** validates and maps source-specific column names, evaluation windows, QQQ indicator dates, QLD fills and paired trades into canonical fields. Pairing is PSAR-specific and must not be silently reused for multi-asset strategies.
- **ReportData** is the normalized result package, without implementation-specific chart decisions. Its pandas frames are input-only; the reporting functions do not mutate them.
- **ReportConfig** controls visible charts, labels, series ordering, indicator overlays, globally shared indicator marker size, price/display symbols, axis details and color scheme. It does not perform data fetching or strategy decisions.
- **Tables** own metric formatting and escaping. Canonical percentages are converted for display only. Raw FFN rows are displayed verbatim.
- **Charts** create independent Bokeh panels with a common time range and shared palette. Only generic overlay definitions/fields enter the price renderer.
- **Renderer** composes period tabs, summary matrices and self-contained HTML. A strategy supplies display strings/notes through its configuration.
- **CLI compatibility**: `python -m backtest_lab.reporting.psar_report --run ... --output ... [--show-volume --volume ...]` remains the supported PSAR entrypoint.

## Baseline and regression

Golden Master: `tests/fixtures/reporting/psar_golden_master.json` generated from the original PSAR report at commit `38eee267...`, with newline-normalized archived CSV SHA-256, four windows' metric tables, date ranges, trade counts, per-plot Bokeh glyph structure, and span colors/geometry.

`tests/test_reporting_golden.py` compares **all these immutable facts** after the refactor. The original source at the pinned commit can be checked out and its HTML rebuilt as the historical implementation reference. Since Bokeh model IDs are randomly generated, byte-identical HTML is not an appropriate assertion. Browser pixel regression is a separate future test and must not be claimed without execution.

## Extension protocol

A second strategy implements its own adapter returning `ReportData` and `ReportConfig`. It must not import `adapters.psar`. `charts.py` must not refer to QQQ, QLD, PSAR or fixed date windows. Add new generic chart types only for demonstrated repeat needs.

To change the renderer: update this architecture and the reporting specifications, modify the common implementation, extend tests and confirm the PSAR Golden Master. Change trade semantics in the adapter or accounting layer, not the chart constructor.


## Shared selectable four-panel chart extension

The common selectable_charts.py builder follows the PSAR panel order,
shared range, palette and execution/holding visualization. It consumes
display-ready column arrays from an adapter and switches the six active
data sources through Bokeh Select/CustomJS, rather than duplicating
figures per strategy. The multi_asset_trade_charts adapter reads archived
performance and sequential full-position fills, validates symbol/quantity
pairing, maps actual execution dates onto recorded long closes, and derives
visual drawdown and fee-net closed-trade P/L from the archived inputs.
No Runtime accounting or FFN summary is recomputed. Open positions are
separate from realized P/L. This does not alter existing OHLC-based
ReportData validation or the PSAR renderer/Golden Master.

The selectable builder enables Bokeh native windowed Y auto-ranging on
each figure and explicitly selects data renderers for its range. It uses
native horizontal and vertical navigation tools; no extra client-side
range engine or dependency is needed.


The independent gold_trend_research_report composes selectable_charts with an additional native signal plot and reorders the raw price first. It reads archived OHLC/indicator traces and uses the shared trade adapter; chart switching is standalone BokehJS. No changes to the parent renderer or Runtime.
