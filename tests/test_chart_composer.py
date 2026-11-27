from bokeh.models import Range1d
import pandas as pd
import pytest

from backtest_lab.reporting.composer import (
    ChartComposer, Layer, Glyph, line_layer, candle_layer, line_break_layer,
)


def test_layers_compose_without_changing_shared_time_axis():
    d = pd.date_range("2024-01-01", periods=5)
    raw = pd.Series([10.,11.,12.,11.,13.], index=d)
    lb = pd.DataFrame({"line_open":[9,10,11,11,12],"line_close":[10,11,12,12,13],
                       "line_formed":[True,True,True,False,True],"direction":[1]*5},index=d)
    xr = Range1d(start=d[0],end=d[-1])
    c = ChartComposer("Example", xr, unit="USD")
    blocks = c.add(line_break_layer("lb","3LB",lb,unit="USD"),visible=True)
    sma = c.add(line_layer("ma","SMA",raw,unit="USD"),visible=True)
    assert c.figure.x_range is xr
    assert c.figure.window_axis=="x"
    assert c.figure.y_range.only_visible
    assert all(r.visible for r in blocks+sma)
    assert set(c.figure.y_range.renderers)==set(blocks+sma)
    bridge=blocks[1].data_source.data
    assert bridge["y0"] == [10.,11.,12.]
    assert bridge["y1"] == bridge["y0"]
    assert bridge["x1"][-1] == int(d[-1].value//1_000_000)
    assert len(blocks[0].data_source.data["date"])==4
    control=c.visibility_control(["lb","ma"],["lb","ma"])
    assert control.active==[0,1]
    assert len(control.js_property_callbacks["change:active"])==1
    c.visibility_control(["lb","ma"],["ma"])
    assert not any(r.visible for r in blocks)
    assert all(r.visible for r in sma)
    assert c.figure.x_range is xr
    with pytest.raises(ValueError,match="unit"):
        c.add(line_layer("rsi","RSI",raw,unit="%"))
    with pytest.raises(ValueError,match="duplicate"):
        c.add(line_layer("ma","Another",raw,unit="USD"))


def test_candles_require_real_or_explicit_transformed_ohlc():
    d=pd.date_range("2024-01-01",periods=2)
    frame=pd.DataFrame({"Open":[10,11],"High":[12,13],"Low":[9,10],"Close":[11,12]},index=d)
    layer=candle_layer("ha","HA",frame,unit="USD",basis="Heikin Ashi OHLC")
    c=ChartComposer("Example",Range1d(start=d[0],end=d[-1]),unit="USD")
    rs=c.add(layer)
    assert [type(r.glyph).__name__ for r in rs]==["Segment","VBar"]
    assert len(c.figure.y_range.renderers)==2
    with pytest.raises(ValueError):
        candle_layer("bad","Missing",frame[["Close"]],unit="USD",basis="raw")
