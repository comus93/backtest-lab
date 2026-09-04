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

Initial registered modes:

- `tripod_nasdaq_leverage / r01 / baseline`
- `tripod_nasdaq_leverage / r01 / sensitivity`

New strategies are added by extending the explicit dispatcher mapping and its tests.

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
