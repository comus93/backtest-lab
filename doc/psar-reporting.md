# PSAR Case Study: Static Bokeh Report

This case study now uses the shared [`Reporting subsystem`](reporting/architecture.md):
`reporting/adapters/psar.py` maps PSAR artifacts to `ReportData` and `ReportConfig`, and `reporting/charts.py`, `tables.py`, `palette.py`, `render.py` supply reusable visual components. The CLI below remains compatible. The original approved view is frozen as [`Golden Master`](reporting/golden-master-psar.md).

Source outputs: `runs/psar_segment_duration/r01/20261103-0002/` (`long_only` QLD/cash).

## Objective

Reproduce the **observable chart features** of the [backtesting.py example](https://kernc.github.io/backtesting.py/#example), without importing its engine or copying its AGPL-3.0 plotting source. This module is a separate implementation using the BSD-licensed Bokeh library.

- Original FFN `performance_summary.csv` for period/CAGR/MDD/Sharpe comparisons.
- Original `ffn_stats.csv` for full raw metric matrix, one 5-year window per tab.
- Bokeh charts: equity, realized trade Profit / Loss, drawdown, QQQ candlesticks, PSAR dots, QLD buy/sell markers, trade-duration connectors, bullish/bearish muted monthly OHLC overlay. Cumulative return is omitted because it duplicates normalized equity.
- Linked date axes, mouse-wheel zoom, drag pan, box zoom, crosshair, date/price and trade hover tooltips, legend show/hide.
- Output is a single standalone HTML file with BokehJS embedded. No server, external data request, or re-run of the investing strategy.
- `Volume` is a strategy-level **opt-in** visualization (`show_volume=False` by default). When enabled, show QQQ volume in a smaller panel immediately under QQQ price candles and share the date axis. Archived PSAR run lacks Volume, so its default presentation has no Volume panel. Never synthesize volume.

## Financial interpretation

QQQ is the PSAR signal instrument; actual trades occur in **QLD**. QLD fill prices and returns **must not be drawn as QQQ price levels**. Markers and trade connectors are placed on the QQQ price series at corresponding execution dates; tooltip contains true QLD execution price. Performance curves use archived FFN performance index, normalized at 100. P/L includes entry/exit fees; open trades have no realized P/L marker. Same-bar PSAR signal and fill bias applies to the backtest itself and is displayed prominently.

## Build and publish

```bash
python -m pip install -e '.[report,dev]'
python -m pytest -q tests/test_psar_reporting.py
python -m backtest_lab.reporting.psar_report \
  --run runs/psar_segment_duration/r01/20261103-0002 \
  --output _site/index.html
```

For a strategy that needs volume, provide real date-aligned QQQ volume data alongside the run (as `qqq_volume.csv` containing `timestamp,QQQ_Volume`) or from FDR `QQQ_Volume` in new price data, and explicitly opt in:

```bash
python -m backtest_lab.reporting.psar_report \
  --run runs/psar_segment_duration/r01/20261103-0002 \
  --volume /path/to/qqq_volume.csv \
  --show-volume \
  --output _site/index.html
```

This option is intended for reuse in future reporting templates. It does not alter PSAR signals, trading fills, or FFN results. In this PSAR case study, volume remains off.

`.github/workflows/publish-psar-report.yml` performs the same steps on GitHub Actions. The HTML is uploaded as a downloadable workflow artifact even when GitHub Pages cannot be deployed.

For Pages deployment, configure **Settings → Pages → Build and deployment → Source: GitHub Actions**. GitHub Pages for a **private** repository requires an eligible paid GitHub plan; the deployed site may be publicly accessible even when the repository is private. Verify the publication intent and source CSV disclosure before enabling Pages.

Existing run CSVs and the backtest engine are not modified by the report renderer.
