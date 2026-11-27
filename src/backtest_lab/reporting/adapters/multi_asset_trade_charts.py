"""Adapt archived multi-asset close-only curves and full-position fills.

No strategy execution or FFN recalculation. Pair sequential full-position
fills only; reject mismatched quantity, instrument or order.
"""
from __future__ import annotations

from html import escape
import math
import pandas as pd
from ..palette import DEFAULT_PALETTE


def _ms(value):
    return pd.Timestamp(value).value // 1_000_000


def _columns(rows, keys):
    return {k: [r[k] for r in rows] for k in keys}


def _curve(series):
    s=series.dropna()
    if s.empty or not s.index.is_unique or not s.index.is_monotonic_increasing:
        raise ValueError("Invalid archived strategy curve")
    if not all(math.isfinite(float(v)) and v > 0 for v in s):
        raise ValueError("Invalid archived strategy performance")
    return {"date": [_ms(x) for x in s.index], "value": s.astype(float).tolist()}


EVENT_KEYS=("date","display_price","signal_date","symbol","position","fill_price","quantity","fee")
HOLD_KEYS=("entry_date","exit_date","entry_price","exit_price","symbol","position","status","days","result","color")
PNL_KEYS=("date","entry_date","symbol","return_pct","pnl","days","color")


def prepare_trade_charts(prices, curves, fills, signals, summary, long_symbol, inverse_symbol=""):
    """Return generic renderer inputs with one real long-price axis.

    The long instrument is the reference itself in reference-mode runs;
    legacy domestic runs use their actual long execution instrument.
    All markers are projected on that axis, never onto inverse dollars.
    """
    palette=DEFAULT_PALETTE
    curves=curves.set_index("timestamp")
    stats=summary.set_index("strategy")
    start=pd.to_datetime(stats.start_date).min()
    end=pd.to_datetime(stats.end_date).max()
    prices=prices.dropna().sort_index().loc[start:end]
    if prices.empty or not prices.index.is_unique or not all(math.isfinite(float(v)) and v>0 for v in prices):
        raise ValueError("Invalid archived display closes")
    display={"date":[_ms(d) for d in prices.index],"close":prices.astype(float).tolist()}
    benchmark=_curve(curves["Buy & Hold"])
    strategies={}
    for name in curves.columns:
        performance=_curve(curves[name])
        vals=curves[name].dropna()
        drawdown={"date":performance["date"],"value":((vals/vals.cummax()-1)*100).tolist()}
        actual_start=pd.Timestamp(stats.loc[name,"start_date"])
        actual_end=pd.Timestamp(stats.loc[name,"end_date"])
        if actual_start not in prices.index or actual_end not in prices.index:
            raise ValueError(f"{name}: missing active display dates")
        subset=fills.loc[fills.strategy==name].sort_values("timestamp",kind="stable")
        signal_dates={}
        if not signals.empty:
            sf=signals.loc[signals.strategy==name]
            if sf.execution_date.duplicated().any():
                raise ValueError(f"{name}: duplicate decision dates")
            signal_dates=dict(zip(sf.execution_date,sf.signal_date))
        buys=[]; sells=[]; holds=[]; pnl=[]
        position=None
        for row in subset.itertuples(index=False):
            date=pd.Timestamp(row.timestamp)
            if date not in prices.index or not actual_start<=date<=actual_end:
                raise ValueError(f"{name}: fill outside archived display dates")
            if row.symbol not in {long_symbol,inverse_symbol} or not row.symbol:
                raise ValueError(f"{name}: unexpected execution symbol {row.symbol}")
            signal=signal_dates.get(date)
            event=dict(date=_ms(date),display_price=float(prices.loc[date]),
                       signal_date=pd.Timestamp(signal).strftime("%Y-%m-%d") if pd.notna(signal) else "—",
                       symbol=row.symbol,position="LONG" if row.symbol==long_symbol else "INVERSE",
                       fill_price=float(row.fill_price),quantity=float(row.quantity),fee=float(row.fee))
            if row.side=="buy":
                if position is not None:
                    raise ValueError(f"{name}: overlapping full positions")
                buys.append(event)
                position=event
                continue
            if row.side!="sell" or position is None or position["symbol"]!=row.symbol:
                raise ValueError(f"{name}: unmatched exit")
            if not math.isclose(position["quantity"],event["quantity"],rel_tol=1e-10,abs_tol=1e-8):
                raise ValueError(f"{name}: partial exit unsupported")
            sells.append(event)
            cost=position["fill_price"]*position["quantity"]+position["fee"]
            proceeds=event["fill_price"]*event["quantity"]-event["fee"]
            net=proceeds-cost
            ret=100*net/cost
            days=(event["date"]-position["date"])//86400000
            pnl.append(dict(date=event["date"],entry_date=position["date"],symbol=row.symbol,
                            return_pct=ret,pnl=net,days=days,
                            color=palette.profit if net>=0 else palette.loss))
            holds.append(dict(entry_date=position["date"],exit_date=event["date"],
                              entry_price=position["display_price"],exit_price=event["display_price"],
                              symbol=row.symbol,position=position["position"],status="CLOSED",
                              days=days,result=f"{ret:+.2f}%",
                              color=palette.trade_span_profit if net>=0 else palette.trade_span_loss))
            position=None
        if position is not None:
            holds.append(dict(entry_date=position["date"],exit_date=_ms(actual_end),
                              entry_price=position["display_price"],exit_price=float(prices.loc[actual_end]),
                              symbol=position["symbol"],position=position["position"],status="OPEN",
                              days=(_ms(actual_end)-position["date"])//86400000,
                              result="Not realized",color="#64748b"))
        note=(f"<b>{escape(name)}</b> · {len(pnl)} closed trades · "
              f"{int(position is not None)} open position<br>"
              "P/L: fee-net realized trades only. Green/pink dashed spans: profitable/loss trades; "
              "gray span: open at end. Gaps: cash (within strategy dates). "
              "Markers use display close; tooltip shows actual instrument and fill. "
              "Same-day sell/buy may overlap. Holding days are calendar days.")
        strategies[name]=dict(performance=performance,drawdown=drawdown,
                              pnl=_columns(pnl,PNL_KEYS),buys=_columns(buys,EVENT_KEYS),
                              sells=_columns(sells,EVENT_KEYS),holds=_columns(holds,HOLD_KEYS),
                              note=note)
    return display,benchmark,strategies
