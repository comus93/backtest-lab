from pathlib import Path
import math
import pandas as pd
import pytest
from backtest_lab.reporting.adapters.multi_asset_trade_charts import prepare_trade_charts
from backtest_lab.reporting.selectable_charts import build_selectable_charts

def inputs():
    dates=pd.date_range("2024-01-01",periods=5)
    price=pd.Series([100.,102.,98.,95.,99.],index=dates)
    curves=pd.DataFrame({"timestamp":dates,"Long/Inverse":[100.,102.,98.,103.,101.],
                         "Buy & Hold":[100.,102.,98.,95.,99.]})
    summary=pd.DataFrame({"strategy":["Long/Inverse","Buy & Hold"],"start_date":[dates[1]]*2,"end_date":[dates[-1]]*2})
    fills=pd.DataFrame([
      ("Long/Inverse",dates[1],"L","buy",102.,10.,1.),
      ("Long/Inverse",dates[2],"L","sell",98.,10.,1.),
      ("Long/Inverse",dates[2],"I","buy",50.,19.,1.),
      ("Buy & Hold",dates[1],"L","buy",102.,10.,1.),
    ],columns=["strategy","timestamp","symbol","side","fill_price","quantity","fee"])
    signals=pd.DataFrame({"strategy":["Long/Inverse"]*2,"signal_date":dates[:2],"execution_date":dates[1:3]})
    return price,curves,fills,signals,summary

def test_full_position_rotation_and_open_trade():
    prices,benchmark,strategies=prepare_trade_charts(*inputs(),"L","I")
    selected=strategies["Long/Inverse"]
    assert selected["pnl"]["pnl"]==[-42.]
    assert selected["pnl"]["return_pct"]==pytest.approx([-42/1021*100])
    assert selected["holds"]["status"]==["CLOSED","OPEN"]
    assert selected["holds"]["position"]==["LONG","INVERSE"]
    assert selected["buys"]["display_price"]==[102.,98.]
    assert selected["buys"]["fill_price"]==[102.,50.]
    assert selected["buys"]["signal_date"]==["2024-01-01","2024-01-02"]
    assert selected["holds"]["days"]==[1,2]
    assert selected["drawdown"]["value"]==pytest.approx([0,0,100*(98/102-1),0,100*(101/103-1)])
    assert strategies["Buy & Hold"]["pnl"]["date"]==[]
    assert strategies["Buy & Hold"]["holds"]["status"]==["OPEN"]
    assert prices["close"]==[102.,98.,95.,99.]
    assert benchmark["value"]==[100.,102.,98.,95.,99.]

def test_unmatched_quantity_fails():
    args=list(inputs())
    args[2].loc[1,"quantity"]=9.
    with pytest.raises(ValueError,match="partial exit"):
        prepare_trade_charts(*args,"L","I")

def test_selectable_charts_four_figures_one_range():
    from bokeh.models import Select
    from bokeh.plotting import figure
    prices,benchmark,strategies=prepare_trade_charts(*inputs(),"L","I")
    layout=build_selectable_charts(prices,benchmark,strategies,display_symbol="L")
    selector,note,*plots=layout.children
    assert isinstance(selector,Select)
    assert selector.options==["Long/Inverse","Buy & Hold"]
    assert len(plots)==4
    assert all(p.x_range is plots[0].x_range for p in plots)
    assert len(selector.js_property_callbacks["change:value"])==1
