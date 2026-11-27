import numpy as np
import pandas as pd
import pytest

from backtest_lab.strategies.gold_trend_research.r01 import heikin_ashi, run_gold
from backtest_lab.reporting.gold_trend_research_report import build_gold_charts, render


def test_heikin_ashi_recursive_and_causal():
    dates = pd.date_range("2024-01-01", periods=3)
    raw = pd.DataFrame({"Open":[10,12,9], "High":[14,15,12],
                        "Low":[8,10,7], "Close":[12,14,8]}, index=dates)
    ha = heikin_ashi(raw)
    assert ha["ha_close"].tolist() == [11,12.75,9]
    assert ha["ha_open"].tolist() == [11,11,11.875]
    assert ha["ha_high"].tolist() == [14,15,12]
    assert ha["ha_low"].tolist() == [8,10,7]
    assert ha["direction"].tolist() == [0,1,-1]
    pd.testing.assert_frame_equal(ha.iloc[:2], heikin_ashi(raw.iloc[:2]))


def test_gold_run_and_native_visuals(tmp_path):
    dates = pd.bdate_range("2016-01-04", periods=360)
    close = 100 + 10*np.sin(np.arange(len(dates))/13) + np.arange(len(dates))*.03
    raw = pd.DataFrame({"Open":close-.3,"High":close+1,"Low":close-1,
                        "Close":close,"GLL_Close":2000/close},index=dates)
    out = run_gold(raw, start="2016-11-21", end="2017-07-01")
    out.write_csv(tmp_path)
    raw.to_csv(tmp_path/"input_prices.csv",index_label="timestamp")
    s = pd.read_csv(tmp_path/"performance_summary.csv")
    assert s.strategy.tolist()[-3:] == ["Heikin Ashi Long/Cash","Heikin Ashi Long/Inverse","Buy & Hold"]
    fills = pd.read_csv(tmp_path/"fills.csv",parse_dates=["timestamp"])
    ha = fills[fills.strategy=="Heikin Ashi Long/Cash"]
    assert len(ha)>0 and set(ha.symbol)=={"GLD"}
    assert all(np.isclose(r.reference_price, raw.loc[r.timestamp,"Close"]) for r in ha.itertuples())
    decisions = pd.read_csv(tmp_path/"daily_signals.csv",parse_dates=["signal_date","execution_date"])
    assert (decisions.signal_date < decisions.execution_date).all()
    layout = build_gold_charts(tmp_path)
    selector, note, price, signal, perf, pnl, dd = layout.children
    assert all(p.x_range is price.x_range for p in (signal,perf,pnl,dd))
    assert all(p.window_axis=="x" for p in (price,signal,perf,pnl,dd))
    assert {"Line","VBar","Segment"} <= {type(r.glyph).__name__ for r in signal.renderers if hasattr(r,"glyph")}
    assert len(selector.js_property_callbacks["change:value"])==2
    assert "Heikin Ashi Long/Cash" in selector.options

    assert render(tmp_path, tmp_path/"gold.html").stat().st_size > 10000
