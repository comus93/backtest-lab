"""Golden Master capture of PSAR behavior at commit 38eee267.

This file intentionally captures Bokeh model structure and archived data facts
instead of comparing HTML bytes (Bokeh generates non-deterministic model IDs).
Do not regenerate the committed fixture while refactoring.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backtest_lab.reporting.psar_report import (
    WINDOWS, _make_charts, _performance_matrix, load_outputs, pair_trades, window_data,
)

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "psar_segment_duration" / "r01" / "20261103-0002"
FIXTURE = ROOT / "tests" / "fixtures" / "reporting" / "psar_golden_master.json"
CSV_NAMES = ("input_prices", "daily_signals", "equity_curves", "fills",
             "performance_summary", "ffn_stats")


def golden_snapshot() -> dict:
    data = load_outputs(RUN)
    result = {
        "baseline_commit": "38eee2673663c11931857b6fd71509968b193a3d",
        "csv_sha256": {
            name: hashlib.sha256(
                (RUN / f"{name}.csv").read_bytes().replace(bytes([13, 10]), bytes([10]))
            ).hexdigest()
            for name in CSV_NAMES
        },
        "windows": {},
    }
    for window in WINDOWS:
        block = window_data(data, window)
        events, trades = pair_trades(block["fills"], block["price"])
        charts = _make_charts(block)
        plots = []
        for fig in charts.children:
            glyphs = [type(renderer.glyph).__name__ for renderer in fig.renderers
                      if hasattr(renderer, "glyph")]
            plots.append({
                "title": fig.title.text,
                "height": fig.height,
                "xaxis_visible": bool(fig.xaxis[0].visible),
                "glyphs": glyphs,
            })
        spans = [
            renderer for renderer in charts.children[-1].renderers
            if getattr(getattr(renderer, "glyph", None), "__class__", type(None)).__name__ == "MultiLine"
        ]
        summary = _performance_matrix(data["performance_summary"], window)
        result["windows"][window] = {
            "days": len(block["price"]),
            "from": str(block["price"].index[0].date()),
            "to": str(block["price"].index[-1].date()),
            "fill_count": len(events),
            "completed_trades": len(trades),
            "profitable_trades": int(trades["win"].sum()),
            "last_equity": {column: round(float(block["curves"][column].iloc[-1]), 8)
                            for column in ("strategy", "QLD", "QQQ")},
            "performance": summary.to_dict(orient="records"),
            "plots": plots,
            "span_width": spans[0].glyph.line_width,
            "span_alpha": spans[0].glyph.line_alpha,
            "span_dash": list(spans[0].glyph.line_dash),
            "span_colors": sorted(set(spans[0].data_source.data["color"])),
        }
    return result


def test_psar_golden_master():
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert golden_snapshot() == expected
