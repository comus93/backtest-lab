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
    from bokeh.models import ResetTool
    assert price.xaxis.visible and signal.xaxis.visible
    assert all(any(isinstance(t, ResetTool) for t in p.tools) for p in (price,signal))
    assert price.min_border_left == signal.min_border_left
    assert price.min_border_right == signal.min_border_right
    assert all(p.window_axis=="x" for p in (price,signal,perf,pnl,dd))
    assert {"Line","VBar","Segment"} <= {type(r.glyph).__name__ for r in signal.renderers if hasattr(r,"glyph")}
    assert len(selector.js_property_callbacks["change:value"])==2
    assert selector.options == ["SMA105 LONG","3LB LineBreak Long/Cash","3LB LineBreak Long/Inverse","Buy & Hold"]
    assert selector.value == "SMA105 LONG"
    control=layout.select_one({"name":"gold-chart-layers"})
    assert control.labels==["Raw close","Raw candles","SMA105","3LB extended","Execution / holding"]
    assert control.active==[0,2,4]
    assert not any(str(r.name or "").startswith("ha:") for r in signal.renderers)
    assert signal.select_one({"name":"lb:1"}).glyph.line_dash
    assert signal.select_one({"name":"sma:0"}).data_source.data["value"] == pytest.approx(
        pd.read_csv(tmp_path/"sma_signals.csv").loc[lambda x:x.signal_date.between(s.start_date.min(),s.end_date.max()),"sma105"].tolist())

    # Reporting must work without HA data and must not serialize removed strategies.
    (tmp_path/"heikin_ashi_signals.csv").unlink()
    result=render(tmp_path, tmp_path/"gold.html")
    html=result.read_text(encoding="utf-8")
    assert result.stat().st_size > 10000
    assert "SMA105 LONG" in html and "3LB LineBreak Long/Inverse" in html
    assert "Heikin Ashi" not in html
    # All displayed data (including tables) use only the approved aliases.
    from bokeh.models import Div
    from backtest_lab.reporting.gold_trend_research_report import _display_rows, _display_columns
    assert _display_rows(s).strategy.tolist()==selector.options
    assert _display_columns(pd.read_csv(tmp_path/"equity_curves.csv"),"timestamp").columns.tolist()==["timestamp",*selector.options]
    assert pd.read_csv(tmp_path/"performance_summary.csv").strategy.tolist()==s.strategy.tolist()


def test_expanded_asset_native_report(tmp_path):
    from backtest_lab.strategies.gold_trend_research.r01 import load_assets, run_trend_asset
    from backtest_lab.reporting.gold_trend_research_report import publish_assets
    assets=load_assets()
    assert [a["id"] for a in assets]==["gold","sp500","silver"]
    assert (assets[-1]["long"],assets[-1]["inverse"],assets[-1]["currency"],assets[-1]["inverse_multiple"])==("SLV","ZSL","USD",-2)
    dates=pd.bdate_range("2016-01-04",periods=360)
    close=100+10*np.sin(np.arange(len(dates))/13)+np.arange(len(dates))*.03
    for a in assets:
        raw=pd.DataFrame({"Open":close-.3,"High":close+1,"Low":close-1,
            "Close":close,a["inverse"]+"_Close":2000/close},index=dates)
        folder=tmp_path/"run"/"assets"/a["id"]
        out=run_trend_asset(raw,a,start="2016-11-21",end="2017-07-01")
        out.write_csv(folder)
        raw.to_csv(folder/"input_prices.csv",index_label="timestamp")
        assert set(out.tables["fills.csv"].symbol)=={a["long"],a["inverse"]}
        assert len(out.tables["performance_summary.csv"])==8
    site=tmp_path/"site"
    publish_assets(tmp_path/"run",site)
    import json
    assert json.loads((site/"assets.json").read_text(encoding="utf-8"))==assets
    assert (site/"navigation.js").is_file()
    for a in assets:
        html=(site/a["page"]).read_text(encoding="utf-8")
        assert "navigation.js" in html and a["long"] in html
        assert "Trend Research r01" in html
        # BokehJS itself contains the literal string <body>; navigation
        # must be placed in the real document body, never in a script.
        from html.parser import HTMLParser
        class DocumentParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_body=False
                self.nav=[]
                self.external_scripts=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag=="body": self.in_body=True
                if tag=="nav" and attrs.get("id")=="trend-navigation":
                    self.nav.append((self.in_body,attrs.get("data-asset")))
                if tag=="script" and attrs.get("src")=="../navigation.js":
                    self.external_scripts.append(self.in_body)
        parser=DocumentParser()
        parser.feed(html)
        assert parser.nav==[(True,a["id"])]
        assert parser.external_scripts==[True]
    assert (site/"index.html").is_file()
    assert not (site/"assets/nikkei225.html").exists()

def test_ohlc_roundoff_tolerated_without_accepting_bad_prices():
    from backtest_lab.strategies.gold_trend_research.r01 import validate_ohlc
    dates=pd.date_range("2024-01-01",periods=2)
    raw=pd.DataFrame({"Open":[100.,200.],"High":[np.nextafter(100.,0),201.],
        "Low":[99.,np.nextafter(200.,np.inf)],"Close":[100.,200.]},index=dates)
    cleaned=validate_ohlc(raw)
    assert cleaned.High.iloc[0]==100.
    assert cleaned.Low.iloc[1]==200.
    pd.testing.assert_series_equal(cleaned.Close,raw.Close)
    for col,row,value in [("High",0,99.9),("Low",1,200.1)]:
        bad=raw.copy()
        bad.iloc[row,bad.columns.get_loc(col)]=value
        with pytest.raises(ValueError,match="Invalid OHLC geometry"):
            validate_ohlc(bad)

def test_line_break_sensitivity_reproduces_archived_control():
    from pathlib import Path
    from backtest_lab.strategies.gold_trend_research.r01 import load_line_break_snapshot, run_line_break_sensitivity
    root=Path("runs/gold_trend_research/r01/20261128-0002/assets")
    prices=load_line_break_snapshot()
    out=run_line_break_sensitivity(prices)
    for asset in ("gold","sp500"):
        prefix=f"line_break_sensitivity/{asset}/"
        summary=out.tables[prefix+"performance_summary.csv"]
        assert summary.strategy.tolist()==["3LB Long/Cash","4LB Long/Cash","5LB Long/Cash","Buy & Hold"]
        old=pd.read_csv(root/asset/"performance_summary.csv").set_index("strategy")
        new=summary.set_index("strategy")
        for name,baseline in [("3LB Long/Cash","LineBreak Long/Cash"),("Buy & Hold","Buy & Hold")]:
            for metric in ("total_return","cagr","sharpe","max_drawdown"):
                assert new.loc[name,metric]==pytest.approx(old.loc[baseline,metric],abs=1e-10)
        signals=out.tables[prefix+"line_break_signals.csv"]
        assert set(signals.reversal_lines)=={3,4,5}
        assert not signals[signals.reversal_lines==3].direction.reset_index(drop=True).equals(
            signals[signals.reversal_lines==5].direction.reset_index(drop=True))
        decisions=out.tables[prefix+"daily_signals.csv"]
        assert (decisions.signal_date<decisions.execution_date).all()
        assert set(out.tables[prefix+"fills.csv"].symbol)=={("GLD" if asset=="gold" else "SPY")}
    assert not any("silver" in name for name in out.tables)


def test_er10_causal_and_flat():
    from backtest_lab.analysis.trend_diagnostics import efficiency_ratio_10
    dates=pd.bdate_range("2024-01-01",periods=14)
    p=pd.Series([100,101,102,103,104,105,106,107,108,109,110,109,108,107],index=dates)
    er=efficiency_ratio_10(p)
    assert er.iloc[:10].isna().all()
    assert er.iloc[10]==pytest.approx(1)
    assert er.iloc[11]==pytest.approx(.8)
    assert er.iloc[13]==pytest.approx(.4)
    pd.testing.assert_series_equal(er.iloc[:12],efficiency_ratio_10(p.iloc[:12]))
    assert efficiency_ratio_10(-p).iloc[10]==pytest.approx(1)
    assert efficiency_ratio_10(pd.Series(100.,index=dates)).iloc[10]==0


def test_er10_report_panel_from_diagnostic_artifact(tmp_path):
    from pathlib import Path
    from backtest_lab.analysis.trend_diagnostics import write_trend_diagnostics
    from backtest_lab.reporting.gold_trend_research_report import build_gold_charts
    run=Path("runs/gold_trend_research/r01/20261128-0002")
    paths=write_trend_diagnostics(run,tmp_path)
    assert set(paths)=={"gold","sp500","silver"}
    folder=run/"assets"/"gold"
    layout=build_gold_charts(folder,diagnostics=paths["gold"])
    er=layout.select_one({"name":"trend-er10"})
    price=layout.children[2]
    assert er.x_range is price.x_range
    assert er.y_range.start==0 and er.y_range.end==1
    assert er.min_border_left==price.min_border_left
    data=er.select_one({"name":"er10:0"}).data_source.data
    assert len(data["date"])==2514
    assert np.isfinite(data["value"]).all()
    assert all(0<=v<=1 for v in data["value"])
    assert layout.children[4] is er
    assert not (folder/"er10.csv").exists()
