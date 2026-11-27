"""Canonical, strategy-agnostic, composable Bokeh chart layers.

Adapters provide already calculated, timestamped values. The composer only
maps them to glyphs; it never computes trading signals or investment returns.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .palette import DEFAULT_PALETTE, DAY_MS


@dataclass(frozen=True)
class Glyph:
    kind: str
    data: Mapping[str, Any]
    options: Mapping[str, Any]
    hover: tuple[tuple[str, str], ...] = ()
    date_fields: tuple[str, ...] = ("date",)
    auto_range: bool = True


@dataclass(frozen=True)
class Layer:
    key: str
    label: str
    unit: str
    basis: str
    glyphs: tuple[Glyph, ...]


def _dates(index):
    if not isinstance(index, pd.DatetimeIndex) or index.has_duplicates or not index.is_monotonic_increasing or index.hasnans:
        raise ValueError("Layer requires ordered unique timestamps")
    return [int(t.value // 1_000_000) for t in index]


def _columns(frame):
    return {"date": _dates(frame.index), **{c: frame[c].tolist() for c in frame}}


class ChartComposer:
    """One panel, arbitrary same-unit layers, shared external datetime range."""

    def __init__(self, title, x_range, *, unit, height=330, name=None, figure=None):
        from bokeh.plotting import figure as make_figure
        from bokeh.models import DataRange1d, CrosshairTool
        self.unit = unit
        self.figure = figure if figure is not None else make_figure(
            title=title, height=height, sizing_mode="stretch_width",
            x_axis_type="datetime", x_range=x_range, window_axis="x",
            y_range=DataRange1d(only_visible=True), name=name,
            tools="xpan,xwheel_zoom,ypan,ywheel_zoom,xbox_zoom,reset,save",
            active_drag="xpan", active_scroll="xwheel_zoom", toolbar_location="right")
        if self.figure.x_range is not x_range:
            raise ValueError("Composer must use the shared X range")
        if not isinstance(self.figure.y_range, DataRange1d):
            raise ValueError("Composer requires a DataRange1d Y range")
        self.figure.window_axis = "x"
        self.figure.y_range.only_visible = True
        if figure is None:
            self.figure.add_tools(CrosshairTool(dimensions="height",line_alpha=.4))
            self.figure.grid.grid_line_alpha=.2
            self.figure.yaxis.axis_label=unit
            self.figure.xaxis.axis_label="Trading date"
        self.layers: dict[str, Layer] = {}
        self.renderers: dict[str, list] = {}

    def add(self, layer: Layer, *, visible=True):
        from bokeh.models import ColumnDataSource, HoverTool
        if layer.key in self.layers:
            raise ValueError(f"duplicate layer: {layer.key}")
        if layer.unit != self.unit:
            raise ValueError(f"layer unit {layer.unit!r} incompatible with panel unit {self.unit!r}")
        if not layer.key or not layer.basis or not layer.glyphs:
            raise ValueError("Layer key, source basis and glyphs required")
        allowed = {"line","step","segment","vbar","scatter","varea","patch","multi_line","quad"}
        for g in layer.glyphs:
            if g.kind not in allowed:
                raise ValueError(f"Unsupported glyph {g.kind}")
            if len({len(v) for v in g.data.values()}) > 1:
                raise ValueError(f"Unequal column lengths in {layer.key}")
        rs = []
        ranges = list(self.figure.y_range.renderers)
        for i, g in enumerate(layer.glyphs):
            source=ColumnDataSource({k:list(v) for k,v in g.data.items()},name=f"{layer.key}-{i}")
            renderer=getattr(self.figure,g.kind)(source=source,visible=visible,
                name=f"{layer.key}:{i}",**dict(g.options))
            rs.append(renderer)
            if g.auto_range:
                ranges.append(renderer)
            if g.hover:
                self.figure.add_tools(HoverTool(renderers=[renderer],
                    tooltips=[("Layer",layer.label),("Basis",layer.basis),*g.hover],
                    formatters={f"@{k}":"datetime" for k in g.date_fields}))
        self.figure.y_range.renderers=ranges
        self.layers[layer.key]=layer
        self.renderers[layer.key]=rs
        return rs

    def visibility_control(self, keys, active, *, name="chart-layers"):
        """Independent checkboxes; any compatible layers may coexist."""
        from bokeh.models import CheckboxGroup, CustomJS
        keys=list(keys)
        if len(keys)!=len(set(keys)) or not set(active)<=set(keys):
            raise ValueError("Invalid layer selection")
        control=CheckboxGroup(labels=[self.layers[k].label for k in keys],
            active=[i for i,k in enumerate(keys) if k in active],inline=True,name=name)
        groups=[self.renderers[k] for k in keys]
        for i,rs in enumerate(groups):
            for r in rs:
                r.visible=i in control.active
        control.js_on_change("active",CustomJS(args=dict(groups=groups),code="""
            const enabled = new Set(cb_obj.active);
            for (let i=0;i<groups.length;i++) {
                for (const r of groups[i]) r.visible=enabled.has(i);
            }
        """))
        return control


def line_layer(key, label, values, *, unit, basis="archived series", color="#475569", width=1.5):
    return Layer(key,label,unit,basis,(Glyph("line",
        {"date":_dates(values.index),"value":values.tolist()},
        dict(x="date",y="value",line_color=color,line_width=width),
        (("Date","@date{%F}"),(label,"@value{0.0000}"))),))


def candle_layer(key, label, frame, *, unit, basis, width=.75*DAY_MS):
    cols=["Open","High","Low","Close"]
    if not set(cols)<=set(frame.columns):
        raise ValueError("Candles require explicit OHLC")
    data=frame[cols].copy()
    if not np.isfinite(data.to_numpy(dtype=float)).all() or ((data.High<data[["Open","Low","Close"]].max(axis=1)) |
            (data.Low>data[["Open","High","Close"]].min(axis=1))).any():
        raise ValueError("Invalid OHLC")
    data["top"]=data[["Open","Close"]].max(axis=1)
    data["bottom"]=data[["Open","Close"]].min(axis=1)
    data["color"]=[DEFAULT_PALETTE.bullish if c>=o else DEFAULT_PALETTE.bearish
                   for o,c in zip(data.Open,data.Close)]
    d=_columns(data)
    return Layer(key,label,unit,basis,(
        Glyph("segment",d,dict(x0="date",y0="High",x1="date",y1="Low",line_color="color")),
        Glyph("vbar",d,dict(x="date",width=width,top="top",bottom="bottom",
              fill_color="color",line_color="color"),
              (("Date","@date{%F}"),*((c,f"@{c}{{0.00}}") for c in cols))),
    ))


def line_break_layer(key,label,frame,*,unit,basis="confirmed reference Close",bridge=True,width=.82*DAY_MS):
    """Confirmed block geometry + horizontal state connectors; no signals computed."""
    dates=_dates(frame.index)
    blocks=frame.loc[frame.line_formed.eq(True),["line_open","line_close","direction"]].copy()
    blocks["top"]=blocks[["line_open","line_close"]].max(axis=1)
    blocks["bottom"]=blocks[["line_open","line_close"]].min(axis=1)
    color=lambda d: DEFAULT_PALETTE.bullish if d>0 else DEFAULT_PALETTE.bearish
    blocks["color"]=[color(d) for d in blocks.direction]
    glyphs=[Glyph("vbar",_columns(blocks),dict(x="date",width=width,top="top",bottom="bottom",
        fill_color="color",line_color="color"),(("Formation","@date{%F}"),
        ("Open","@line_open{0.00}"),("Close","@line_close{0.00}")))]
    if bridge:
        data={k:[] for k in ("x0","x1","y0","y1","color")}
        # Collapse adjacent unchanged states into one connector. Begin at
        # the visible archive start if a pre-window block was already confirmed.
        begin = None
        last = None
        for i,(v,direction,formed) in enumerate(zip(frame.line_close,frame.direction,frame.line_formed)):
            valid = pd.notna(v) and pd.notna(direction) and direction != 0
            state = (float(v),int(direction)) if valid else None
            if state != last or bool(formed):
                if last is not None and begin is not None and dates[i]>begin:
                    for k,vv in zip(data,(begin,dates[i],last[0],last[0],color(last[1]))):
                        data[k].append(vv)
                begin=dates[i] if valid else None
                last=state
        if last is not None and begin is not None and dates[-1]>begin:
            for k,vv in zip(data,(begin,dates[-1],last[0],last[0],color(last[1]))):
                data[k].append(vv)
        glyphs.append(Glyph("segment",data,dict(x0="x0",x1="x1",y0="y0",y1="y1",
            line_color="color",line_dash="dotted",line_width=1.2,line_alpha=.7),
            (("From","@x0{%F}"),("Confirmed close","@y0{0.00}")),("x0",)))
    return Layer(key,label,unit,basis,tuple(glyphs))
