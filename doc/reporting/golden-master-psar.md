# PSAR report Golden Master

- **Baseline Git commit:** `38eee2673663c11931857b6fd71509968b193a3d`.
- **Archived immutable source:** `runs/psar_segment_duration/r01/20261103-0002/`.
- **Fixture:** `tests/fixtures/reporting/psar_golden_master.json`.
- **Guard:** `uv run --extra report --extra dev python -m pytest tests/test_reporting_golden.py`.
- **Pre-refactor validation:** `tests/test_psar_reporting.py` passed 15/15 and a Bokeh HTML file was generated locally from the pinned source.

The fixture was generated **before extracting the common renderer**, from the original Bokeh figure models and output CSVs. It includes SHA-256 checksums for six archived inputs, exactly four windows, time ranges, normalized equity endpoints, performance matrices, execution/completed/winning trade counts, chart titles/height/x-axis visibility/glyph-layer order, and trade-span styling.

This is a deterministic **semantic and structural** Golden Master; it is not a screenshot diff. Do **not** overwrite the fixture merely to make refactored tests pass. If an intentional UI change is authorized, document the delta, preserve the historical baseline (Git), and introduce a separately reviewed baseline.

The same-bar PSAR fill/look-ahead limitation is part of the historical result and remains displayed. No strategy rerun or result correction occurs here.
