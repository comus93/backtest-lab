from __future__ import annotations

import pandas as pd

from backtest_lab.core import BacktestResult


def monthly_turnover_series(result: BacktestResult) -> pd.Series:
    """Return one-way monthly turnover for every active calendar month."""
    if result.equity.empty:
        return pd.Series(dtype=float, name="monthly_turnover")

    equity_index = pd.DatetimeIndex(result.equity.index)
    months = pd.period_range(equity_index[0].to_period("M"), equity_index[-1].to_period("M"), freq="M")
    monthly_nav = result.equity.groupby(equity_index.to_period("M")).mean().reindex(months)
    monthly_notional = pd.Series(0.0, index=months, name="monthly_notional")
    first_active_timestamp = equity_index[0]

    for fill in result.fills:
        if pd.Timestamp(fill.timestamp) == first_active_timestamp:
            continue
        month = pd.Timestamp(fill.timestamp).to_period("M")
        if month in monthly_notional.index:
            monthly_notional.loc[month] += abs(fill.fill_price * fill.quantity)

    turnover = 0.5 * monthly_notional.div(monthly_nav).fillna(0.0)
    turnover.name = "monthly_turnover"
    return turnover


def average_monthly_turnover(result: BacktestResult) -> float:
    """Return average turnover across all active calendar months, including zero months."""
    series = monthly_turnover_series(result)
    return float(series.mean()) if not series.empty else 0.0
