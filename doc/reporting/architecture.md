# Reporting Subsystem Architecture (v1)

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
