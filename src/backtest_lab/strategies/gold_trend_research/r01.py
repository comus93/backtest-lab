"""Gold-only control and Heikin Ashi experiments, executed on actual prices."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import numpy as np
import pandas as pd

from backtest_lab.analysis import average_monthly_turnover, ffn_stats_table
from backtest_lab.core import Runtime, RuntimeConfig
from backtest_lab.strategies.multi_asset_weekly_sma.r01 import (
    AssetInput, SMARegimeStrategy, run_asset, daily_sma_signals, START, END,
    INITIAL_CASH, SUMMARY_COLUMNS,
)

STRATEGY_ID = "gold_trend_research"
REVISION = "r01"
OHLC = ["Open", "High", "Low", "Close"]
HA_NAMES = ("Heikin Ashi Long/Cash", "Heikin Ashi Long/Inverse")


def validate_ohlc(frame):
    raw = frame.loc[:, OHLC].astype(float).sort_index()
    if not isinstance(raw.index, pd.DatetimeIndex) or raw.empty or raw.index.has_duplicates:
        raise ValueError("Gold requires unique daily OHLC dates")
    if not np.isfinite(raw.to_numpy()).all() or (raw <= 0).any().any():
        raise ValueError("Gold OHLC must be finite and positive")
    if ((raw.High < raw[["Open", "Close", "Low"]].max(axis=1)) |
        (raw.Low > raw[["Open", "Close", "High"]].min(axis=1))).any():
        raise ValueError("Invalid OHLC geometry")
    return raw


def heikin_ashi(frame):
    raw = validate_ohlc(frame)
    close = raw.mean(axis=1).to_numpy()
    opening = np.empty(len(raw))
    opening[0] = (raw.Open.iloc[0] + raw.Close.iloc[0]) / 2
    for i in range(1, len(raw)):
        opening[i] = (opening[i-1] + close[i-1]) / 2
    return pd.DataFrame({
        "reference_close": raw.Close,
        "ha_open": opening, "ha_close": close,
        "ha_high": np.maximum.reduce([raw.High.to_numpy(), opening, close]),
        "ha_low": np.minimum.reduce([raw.Low.to_numpy(), opening, close]),
        "direction": np.sign(close-opening).astype(int),
    }, index=raw.index.rename("signal_date"))


def load_assets():
    """Manually maintained universe and navigation manifest; never generated."""
    assets=json.loads(Path(__file__).with_name("assets.json").read_text(encoding="utf-8"))
    if len({a["id"] for a in assets}) != len(assets):
        raise ValueError("Duplicate trend asset id")
    for a in assets:
        if not a["id"].replace("_","").isalnum() or a["page"] != f'assets/{a["id"]}.html':
            raise ValueError("Invalid trend asset page")
        if not a["long"] or not a["inverse"] or a["long"]==a["inverse"]:
            raise ValueError("Invalid trend asset instruments")
    return assets


def load_trend_prices(asset, start="2016-01-01", end=END):
    import yfinance as yf
    def download(symbol):
        frame = yf.download(symbol, start=start, end=end, auto_adjust=True,
                            progress=False, threads=False)
        if isinstance(frame.columns, pd.MultiIndex):
            frame = frame.xs(symbol, axis=1, level=-1)
        frame.index = pd.to_datetime(frame.index).tz_localize(None)
        return validate_ohlc(frame)
    long, inverse = download(asset["long"]), download(asset["inverse"])
    out = long.join(inverse.add_prefix(asset["inverse"]+"_"), how="left")
    out.index.name = "timestamp"
    return out


def load_gold_prices(start="2016-01-01", end=END):
    return load_trend_prices(next(a for a in load_assets() if a['id']=='gold'),start,end)


def load_expanded_prices(start="2016-01-01",end=END):
    frames=[]
    for a in load_assets():
        if a["id"]=="gold":
            raw=pd.read_csv("runs/gold_trend_research/r01/20261127-0001/input_prices.csv",
                            parse_dates=["timestamp"]).set_index("timestamp")
        else:
            raw=load_trend_prices(a,start,end)
        frames.append(raw.add_prefix(a["id"]+"__"))
    return pd.concat(frames,axis=1).sort_index().rename_axis("timestamp")


@dataclass
class GoldOutputs:
    tables: dict
    def write_csv(self, output_dir):
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        paths = {}
        for name, frame in self.tables.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(path, index=False)
            paths[name] = path
        return paths


def run_trend_asset(prices, asset, start=START, end=END, config=None):
    long_symbol, inverse_symbol = asset['long'], asset['inverse']
    config = config or RuntimeConfig(fee_rate=.00015)
    raw = validate_ohlc(prices.loc[prices.index < pd.Timestamp(end)])
    inv = prices[inverse_symbol+"_Close"].dropna().astype(float)
    if inv.empty or inv.index.has_duplicates or not np.isfinite(inv).all() or (inv <= 0).any():
        raise ValueError(f"{inverse_symbol} actual prices required")
    controls = run_asset(AssetInput(asset["id"], asset["label"], raw.Close, raw.Close, long_symbol, inv, inverse_symbol),
                         start=start, end=end, config=config)
    ha = heikin_ashi(raw)
    sma = daily_sma_signals(raw.Close)
    active = raw.Close.loc[raw.index >= pd.Timestamp(start)].rename(long_symbol).to_frame()
    common = active.join(inv.rename(inverse_symbol), how="inner")
    if len(common) < 25:
        raise ValueError(f"Insufficient {inverse_symbol} common calendar")
    cases = {}
    extra_decisions = []
    extra_fills = []
    summary = []
    yearly = []
    monthly = []
    for name, calendar, inverse in ((HA_NAMES[0], active, None), (HA_NAMES[1], common, inverse_symbol)):
        strategy = SMARegimeStrategy(ha, long_symbol, inverse)
        result = Runtime(strategy, INITIAL_CASH, config).run(calendar)
        cases[name] = result
        extra_decisions.append(pd.DataFrame(strategy.decisions).assign(strategy=name))
        quantities = {}
        fills_by_date = {}
        for fill in result.fills:
            fills_by_date.setdefault(pd.Timestamp(fill.timestamp), []).append(fill)
            extra_fills.append(dict(asset=asset["id"], strategy=name, timestamp=fill.timestamp,
                symbol=fill.symbol, side=fill.side, quantity=fill.quantity,
                reference_price=fill.reference_price, fill_price=fill.fill_price, fee=fill.fee))
        exposure = []
        for ts, row in calendar.iterrows():
            for fill in fills_by_date.get(ts, []):
                quantities[fill.symbol] = quantities.get(fill.symbol, 0) + (
                    fill.quantity if fill.side == "buy" else -fill.quantity)
            exposure.append(sum(q*float(row[s]) for s,q in quantities.items()) / result.equity.loc[ts])
        stat = ffn_stats_table({name: result})[1][name]
        summary.append(dict(strategy=name, start_date=result.equity.index[0].date(),
            end_date=result.equity.index[-1].date(), total_return=stat["total_return"],
            cagr=stat["cagr"], volatility=stat["daily_vol"], sharpe=stat["daily_sharpe"],
            max_drawdown=stat["max_drawdown"], avg_monthly_turnover=average_monthly_turnover(result),
            avg_exposure=np.mean(exposure)))
        returns = result.performance.pct_change().dropna()
        for period, group in returns.groupby(returns.index.year):
            yearly.append(dict(strategy=name, year=period, return_=(1+group).prod()-1))
        for period, group in returns.groupby(returns.index.to_period("M")):
            monthly.append(dict(strategy=name, month=str(period), return_=(1+group).prod()-1))
    order = [c for c in controls.curves if c != "Buy & Hold"] + list(HA_NAMES) + ["Buy & Hold"]
    curves = pd.concat([controls.curves, *[r.performance.rename(n) for n,r in cases.items()]],axis=1)[order]
    stats = pd.concat([controls.ffn_stats, ffn_stats_table(cases)[0]],axis=1)[order]
    def combine_ordered(base, extra):
        combined = pd.concat([base, extra],ignore_index=True)
        return combined.assign(_rank=combined.strategy.map({n:i for i,n in enumerate(order)})).sort_values(
            "_rank",kind="stable").drop(columns="_rank")
    return GoldOutputs({
        "performance_summary.csv": combine_ordered(controls.performance_summary,pd.DataFrame(summary))[list(SUMMARY_COLUMNS)],
        "ffn_stats.csv": stats.reset_index(names="metric"),
        "equity_curves.csv": curves.reset_index(names="timestamp"),
        "daily_signals.csv": combine_ordered(controls.signals,pd.concat(extra_decisions,ignore_index=True)),
        "fills.csv": combine_ordered(controls.fills,pd.DataFrame(extra_fills)),
        "yearly_performance.csv": combine_ordered(controls.yearly_performance,pd.DataFrame(yearly).rename(columns={"return_":"return"})),
        "monthly_performance.csv": combine_ordered(controls.monthly_performance,pd.DataFrame(monthly).rename(columns={"return_":"return"})),
        "line_break_signals.csv": controls.line_break_signals.reset_index(),
        "sma_signals.csv": sma.reset_index(),
        "heikin_ashi_signals.csv": ha.reset_index(),
    })


def run_gold(prices, start=START, end=END, config=None):
    return run_trend_asset(prices,next(a for a in load_assets() if a['id']=='gold'),start,end,config)


def run_expanded(prices, start=START, end=END, config=None):
    tables={}
    for a in load_assets():
        prefix=a["id"]+"__"
        frame=prices.loc[:,prices.columns.str.startswith(prefix)].copy()
        frame.columns=frame.columns.str.removeprefix(prefix)
        frame=frame.dropna(subset=OHLC)
        result=run_trend_asset(frame,a,start,end,config)
        root=f'assets/{a["id"]}/'
        tables.update({root+k:v for k,v in result.tables.items()})
        tables[root+"input_prices.csv"]=frame.reset_index(names="timestamp")
    return GoldOutputs(tables)
