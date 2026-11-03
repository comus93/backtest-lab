"""Regression tests for immutable CSV-to-Bokeh case-study reporting."""
from pathlib import Path

import pandas as pd
import pytest

from backtest_lab.reporting.psar_report import (
    WINDOWS, build_report, load_outputs, pair_trades, window_data,
)

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "psar_segment_duration" / "r01" / "20261103-0002"


@pytest.fixture(scope="module")
def archived():
    return load_outputs(RUN)


@pytest.mark.parametrize("window", WINDOWS)
def test_window_mappings_and_dates_match(archived, window):
    block = window_data(archived, window)
    assert len(block["price"]) > 500
    assert block["price"].index.equals(block["curves"].index)
    assert block["signal"].index.equals(block["price"].index)
    assert not block["fills"].empty
    assert set(block["fills"]["symbol"]) == {"QLD"}
    assert list(block["stats"].columns) == ["strategy", "QLD", "QQQ"]


@pytest.mark.parametrize("window", WINDOWS)
def test_trade_event_projection_preserves_fills(archived, window):
    block = window_data(archived, window)
    events, complete = pair_trades(block["fills"], block["price"])
    assert len(events) == len(block["fills"])
    assert set(events["side"]) == {"buy", "sell"}
    assert (events["qqq"] > 0).all()
    assert (events["price"] > 0).all()
    assert len(complete) <= len(events) / 2
    assert (complete["entry_date"] <= complete["date"]).all()


def test_reject_window_without_its_independent_metrics(archived):
    bad = {k: v.copy() for k, v in archived.items()}
    bad["performance_summary"] = bad["performance_summary"].loc[
        bad["performance_summary"]["window"] != "2007-2011"
    ]
    with pytest.raises(ValueError, match="Expected strategy"):
        window_data(bad, "2007-2011")


def test_reject_synthetic_cross_symbol_position(archived):
    block = window_data(archived, "2007-2011")
    corrupt = block["fills"].copy()
    corrupt.loc[corrupt.index[0], "side"] = "sell"
    with pytest.raises(ValueError, match="Sell without"):
        pair_trades(corrupt, block["price"])


def test_generate_self_contained_bokeh_html(tmp_path):
    pytest.importorskip("bokeh")
    target = build_report(RUN, tmp_path / "site" / "index.html")
    text = target.read_text(encoding="utf-8")
    assert "PSAR QLD / Cash" in text
    assert "Cumulative return (%)" in text
    assert "QQQ OHLC" in text
    assert "Trade spans" in text
    assert "FFN result matrix" in text
    assert "QLD fill" in text
    assert "2022-2026" in text
    assert "Bokeh" in text
    assert len(text) > 500_000
    assert target.stat().st_size < 40_000_000
