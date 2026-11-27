"""Universe completeness, source mapping and automation contract tests."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from backtest_lab.automation import ALLOWED_RUNNERS, load_request
from backtest_lab.strategies.multi_asset_weekly_sma.data import ASSETS, load_price_snapshot
from backtest_lab.strategies.multi_asset_weekly_sma.r01 import run_pilot


def test_exactly_eighteen_tracked_and_domestic_eligible_assets():
    assert len(ASSETS) == len({a.asset_id for a in ASSETS}) == 18
    assert all(a.long_etf.isdigit() and len(a.long_etf) == 6 for a in ASSETS)
    assert not any("currency" in a.asset_id or "bond" in a.asset_id for a in ASSETS)
    assert any(a.inverse_etf is None for a in ASSETS)
    assert any(a.inverse_etf is not None for a in ASSETS)


def test_snapshot_preserves_cross_market_missing_days():
    us = pd.Series([100.0, 101.0, 102.0], index=pd.to_datetime(
        ["2016-01-04", "2016-01-05", "2016-01-06"]))
    korea = pd.Series([500.0, 501.0, 502.0], index=pd.to_datetime(
        ["2016-01-04", "2016-01-06", "2016-01-07"]))
    prices = load_price_snapshot("2016-01-01", "2016-01-08",
                                 yahoo_reader=lambda *_: us,
                                 fdr_reader=lambda *_: korea)
    assert len({c.split("__")[0] for c in prices.columns}) == 18
    assert pd.isna(prices.loc[pd.Timestamp("2016-01-05"), "gold__long"])
    assert pd.isna(prices.loc[pd.Timestamp("2016-01-07"), "gold__reference"])
    assert not pd.isna(prices.loc[pd.Timestamp("2016-01-07"), "grains__reference"])


def test_all_18_run_independently_from_synthetic_snapshot(tmp_path):
    dates = pd.bdate_range("2015-01-01", periods=535)
    def synthetic(ticker, *_):
        return pd.Series(np.linspace(100.0, 180.0, len(dates)), index=dates)
    prices = load_price_snapshot("2015-01-01", "2018-01-01",
                                 yahoo_reader=synthetic, fdr_reader=synthetic)
    outputs = run_pilot(prices, start="2016-01-01", end="2018-01-01")
    assert len(outputs.assets) == 18
    written = outputs.write_csv(tmp_path)
    summary = pd.read_csv(written["performance_summary.csv"])
    assert len(summary) == 18
    assert summary["strategy"].is_unique
    assert len(list((tmp_path / "assets").iterdir())) == 18
    coverage = pd.read_csv(written["instrument_coverage.csv"])
    assert len(coverage) == 18
    assert coverage["asset_id"].is_unique


def test_dispatcher_registered_with_user_approved_fixed_period(tmp_path):
    assert ("multi_asset_weekly_sma", "r01", "baseline") in ALLOWED_RUNNERS
    path = tmp_path / "request.json"
    data = {
        "request_id": "20261127T080000+0900",
        "strategy_id": "multi_asset_weekly_sma", "revision": "r01",
        "mode": "baseline", "start": "2016-11-21", "end": "2026-11-21",
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_request(path).strategy_id == "multi_asset_weekly_sma"
    data["end"] = "2026-11-20"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="fixed dates"):
        load_request(path)


def test_reference_mode_does_not_use_domestic_etf_prices(tmp_path):
    from backtest_lab.strategies.multi_asset_weekly_sma.data import REFERENCE_ASSETS
    from backtest_lab.core import RuntimeConfig
    assert len(REFERENCE_ASSETS) == 18
    assert next(a for a in REFERENCE_ASSETS if a.asset_id == "gold").long_etf == "GLD"
    assert next(a for a in REFERENCE_ASSETS if a.asset_id == "gold").inverse_etf == "GLL"
    dates = pd.bdate_range("2015-01-01", periods=535)
    seen = []
    def yahoo(ticker, *_):
        seen.append(("yahoo", ticker))
        return pd.Series(np.linspace(100.0, 180.0, len(dates)), index=dates)
    def fdr(ticker, *_):
        seen.append(("fdr", ticker))
        return pd.Series(np.linspace(200.0, 300.0, len(dates)), index=dates)
    prices = load_price_snapshot("2015-01-01", "2018-01-01", yahoo_reader=yahoo,
                                 fdr_reader=fdr, reference_only=True)
    assert [x for x in seen if x[0] == "fdr"] == [("fdr", "KS200")]
    assert prices["gold__long"].equals(prices["gold__reference"])
    outputs = run_pilot(prices, start="2016-01-01", end="2018-01-01",
                        config=RuntimeConfig(fee_rate=0.00015), reference_only=True)
    gold = next(x for x in outputs.assets if x.asset_id == "gold")
    assert gold.signals["sma105"].notna().any()
    assert "sma21" not in gold.signals.columns
    assert set(gold.fills.symbol) <= {"GLD", "GLL"}
    assert "Long/Inverse" in gold.performance_summary.strategy.values
    assert "Inverse/Cash" in gold.performance_summary.strategy.values
    assert "LineBreak Long/Inverse" in gold.performance_summary.strategy.values
    assert gold.line_break_signals["line_formed"].any()
    assert set(gold.fills.loc[gold.fills.strategy == "LineBreak Long/Inverse","symbol"]) <= {"GLD", "GLL"}
    assert set(gold.fills.loc[gold.fills.strategy == "Inverse/Cash", "symbol"]) <= {"GLL"}
    p = prices.loc[prices.index >= pd.Timestamp("2016-01-01"), "gold__long"].dropna()
    expected = p.iloc[-1] / p.iloc[0] / 1.00015 - 1.0
    actual = gold.performance_summary.loc[gold.performance_summary.strategy == "Buy & Hold",
                                           "total_return"].iloc[0]
    assert actual == pytest.approx(expected)
    for name, group in gold.yearly_performance.groupby("strategy"):
        total = gold.performance_summary.loc[gold.performance_summary.strategy == name,
                                              "total_return"].iloc[0]
        assert (1.0 + group["return"]).prod() - 1.0 == pytest.approx(total)
    written = outputs.write_csv(tmp_path)
    assert len(pd.read_csv(written["performance_summary.csv"])) == 18
    annual = pd.read_csv(written["yearly_performance.csv"])
    assert annual.asset_id.nunique() == 18
    assert set(outputs.coverage.study_basis) == {"reference"}
    assert set(outputs.coverage.currency) == {"USD", "JPY", "KRW index"}


def test_reference_dispatcher_is_explicit(tmp_path):
    assert ("multi_asset_weekly_sma", "r01", "reference") in ALLOWED_RUNNERS
    path = tmp_path / "request.json"
    path.write_text(json.dumps({
        "request_id": "20261127T080000+0900", "strategy_id": "multi_asset_weekly_sma",
        "revision": "r01", "mode": "reference", "start": "2016-11-21", "end": "2026-11-21"
    }), encoding="utf-8")
    assert load_request(path).mode == "reference"
