# Backtest Automation

## Purpose

Backtest execution and mechanical verification are automated with GitHub Actions.

LLM responsibilities:

- strategy design and specification
- implementation and test authoring
- writing `automation/backtest-request.json`
- reading raw run outputs and explaining results to the user
- writing an analysis report only after user discussion and only when the user requests it

GitHub Actions responsibilities:

- detect a change to `automation/backtest-request.json`
- install the project
- run pytest
- validate the request against an explicit allow-list
- execute the registered backtest runner
- save the exact input price snapshot used by the run
- save calculated raw outputs under the normal run directory
- update `automation/backtest-result.md` as the latest-run manifest
- commit and push generated run outputs and the manifest

Codex Agent is not the default execution path. Use an Agent only when a failed workflow, data issue, or implementation defect requires diagnosis beyond deterministic automation.

## Request protocol

Trigger file:

```text
automation/backtest-request.json
```

Changing this file on `main` triggers the workflow.

Example:

```json
{
  "request_id": "20260904T200000+0900",
  "strategy_id": "tripod_nasdaq_leverage",
  "revision": "r01",
  "mode": "baseline"
}
```

Optional fields:

```json
{
  "start": "2009-01-01",
  "end": "2026-09-05"
}
```

`end` follows the underlying loader's end-exclusive convention where applicable.

### Security / determinism rule

The request file must never contain a shell command, Python expression, module path, or arbitrary executable text.

The dispatcher maps only the tuple:

```text
(strategy_id, revision, mode)
```

to an explicitly registered runner in source code.

Unknown combinations fail before the E2E backtest starts.

Registered modes include:

- `tripod_nasdaq_leverage / r01 / baseline`
- `tripod_nasdaq_leverage / r01 / sensitivity`
- `sp500_top2_market_cap / r01 / baseline`
- `us_market_cap_leaders / r01 / baseline`
- `us_market_cap_leaders / r01 / window_sensitivity`
- `psar_segment_duration / r01 / baseline`
- `psar_segment_duration / r01 / long_only` (same QQQ PSAR signals; QLD or cash, never PSQ)

`us_market_cap_leaders/r01` uses fixed price coverage `2010-03-31` through end-exclusive `2026-07-01`. Its baseline mode compares TOP1, TOP2, SPY Buy & Hold, and QQQ Buy & Hold.

Its `window_sensitivity` mode defines the strategy-specific 3Y/5Y/10Y and start/end research windows, but delegates repeated start execution, canonical performance metrics, and Start × End matrix transformation to the common `backtest_lab.analysis` package. The framework dispatcher does not implement those experiment rules itself.

New strategies are added by extending the explicit dispatcher mapping and its tests. Reusable post-run calculations should be added to `backtest_lab.analysis` instead of copied into each strategy evaluator.

## Run ID allocation

LLM does not assign a run serial.

The dispatcher uses the date portion of `request_id`, scans:

```text
runs/<strategy_id>/<revision>/
```

and allocates the next unused:

```text
YYYYMMDD-NNNN
```

Existing run directories are never overwritten.

## Run outputs

Normal output location:

```text
runs/<strategy_id>/<revision>/<run_id>/
```

In addition to strategy-specific outputs, automated runs save:

```text
input_prices.csv
```

This is the exact common price frame supplied to the backtest. It exists so a historical run can be reproduced even if Yahoo or another external data provider later revises adjusted prices.

For the initial Tripod runner the expected files are:

```text
input_prices.csv
ffn_stats.csv
performance_summary.csv
equity_curves.csv
daily_signals.csv
regime_summary.csv
yearly_performance.csv
exposure.csv
```

For `us_market_cap_leaders/r01/baseline` the expected files are:

```text
input_prices.csv
ffn_stats.csv
performance_summary.csv
equity_curves.csv
yearly_performance.csv
quarterly_rankings.csv
quarterly_selections.csv
fills.csv
```

For `us_market_cap_leaders/r01/window_sensitivity` the expected files are:

```text
input_prices.csv
quarterly_rankings.csv
window_performance.csv
rolling_summary.csv
start_end_cagr_top1_pct.csv
start_end_cagr_top2_pct.csv
start_end_cagr_spy_pct.csv
start_end_cagr_qqq_pct.csv
```

The Start × End CSVs are absolute CAGR matrices expressed in percentage units. Rows are strategy start dates, columns are end dates, and each cell is that strategy's CAGR for the corresponding interval. They are not benchmark-relative excess-return matrices.

The common analysis API can build the same matrix for another metric by selecting a different `metric` when calling `start_end_matrix()`.

## Result manifest

Latest manifest:

```text
automation/backtest-result.md
```

This is not a performance report.

It contains only the latest successful automated run identity, output directory, default output file names, and a reserved future `report_url` field.

CAGR, drawdown, Sharpe, regime statistics, investment interpretation, and copied raw values do not belong in this file.

LLM reads the referenced raw files directly.

## LLM analysis and analysis report

A successful Action run does not automatically create an analysis report.

Flow:

```text
raw outputs
-> LLM reads and analyzes
-> user and LLM discuss the evidence
-> user requests persistence
-> LLM writes analysis report
```

Default analysis-report location:

```text
runs/<strategy_id>/<revision>/<run_id>/analysis-report.md
```

If the user specifies a different Markdown filename, the user's filename wins.

The report should use Markdown/YAML tags so it can be reused in Obsidian or other Markdown knowledge systems.

The report must distinguish calculated facts from interpretation and preserve the conclusions actually reached with the user. It must not fabricate `Agreed Insights` before user discussion.

Historical `llm-analysis.md` files remain valid historical artifacts; the automated workflow must never overwrite them.

## Future reporting roadmap

`automation/backtest-result.md` reserves:

```text
report_url: pending
```

A later phase may generate dynamic HTML using a reporting layer derived from `portfolio-optimizer-kr`, expose the full FFN result set, publish the report with GitHub Pages, and replace `pending` with the published URL.

That HTML reporting phase is outside the current automation scope.


## Multi-asset weekly SMA integration (2026-11-27)

The explicitly allowed request is strategy_id multi_asset_weekly_sma, revision r01,
mode baseline, start 2016-11-21, end exclusive 2026-11-21. The runner loads
Yahoo/FDR daily references and Korea ETF prices from 2016-01-01 onward as warmup,
saves the unmodified cross-market price snapshot to input_prices.csv, and runs
18 completely independent strategies. A missing source fails explicitly.

Main performance_summary.csv uses the established ten columns unchanged and
contains one Long/Cash row per asset. Per-asset directories also hold FFN stats,
equity curves, fills, and signal decisions. No calculated metrics are recreated
in the presentation subsystem.

After the backtest workflow commits an actual successful run to main it dispatches
the existing publish-psar-report.yml Pages workflow. That workflow preserves the
existing PSAR site root while adding the new study under research/multi_asset_weekly_sma/.
A generated report is optional until a completed archived SMA run exists.
The run manifest continues to be the latest-run locator, not a performance report.

This is a study-specific integration; it does not promise Pages URLs in the result
manifest until the publication mechanism records them there.


Reference-first research uses mode reference, same r01 and dates. It preserves
the baseline domestic execution mode but does not fetch domestic ETF prices
in phase one (KS200 is a price index). Both modes now produce archived
yearly_performance.csv. The newest successful archived run is used by the
existing Pages publisher; previous run directories remain immutable.


The SMA study additionally produces monthly_performance.csv at run-root
and per-asset locations, with complete strategy calendar-month returns.
This is computed in the backtest and not by the Pages renderer.


Current SMA105 reference-mode research compares every daily confirmed
Close with 105 daily trading closes, and trades no earlier than next
session Close. New runs save daily_signals.csv, not weekly_signals.csv.
instrument_coverage.csv records SMA length, signal frequency and execution
assumptions. Older archived weekly result files remain unchanged.


Daily SMA105 reference-mode runs now additionally calculate Inverse/Cash
when a verified inverse ETF exists. This strategy uses real inverse
price data, shares the overlap window with Long/Inverse, and logs
only inverse ETF fills. The archived result files and FFN metric schema
are unchanged, but per-asset strategy rows can now contain four
distinct strategies including benchmark Buy & Hold last.


The reference-first multi-asset runner now also creates
line_break_signals.csv at run root and each asset's folder.
The 3-Line Break signal is built from confirmed reference daily
adjusted closes and uses actual inverse product returns where
available. This contributes LineBreak Long/Inverse as the fourth
study comparator, keeping Buy & Hold last. Prior archived runs
are immutable; latest completed archive is published by Pages.


New multi_asset_weekly_sma runs use the ten active candidate IDs from the
strategy data registry. Historical 18-asset runs are not rewritten.


The active multi-asset trend research universe is ten candidates from
2026-11-27 onward (see strategy specification section 16). New
reference and domestic snapshots exclude the eight removed mappings.
Archived 18-asset runs are not rewritten; reporting uses the manifest
of the selected run rather than assuming a fixed asset count.
