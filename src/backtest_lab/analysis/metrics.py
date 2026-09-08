from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from backtest_lab.core import BacktestResult


def raw_ffn_stats(series: pd.Series) -> pd.Series:
    """Return the raw FFN calc_stats() series for a performance index."""
    import ffn  # noqa: F401

    stats_object = series.calc_stats()
    raw = getattr(stats_object, "stats", None)
    if raw is None:
        raise ValueError("FFN calc_stats() result does not expose .stats.")
    return pd.Series(raw)


def stat_value(stats: pd.Series, key: str) -> float:
    """Read one numeric FFN stat, returning NaN when unavailable."""
    if key not in stats.index:
        return float("nan")
    try:
        return float(stats.loc[key])
    except (TypeError, ValueError):
        return float("nan")


def performance_metrics(series: pd.Series) -> dict[str, float]:
    """Return the canonical performance metrics used by backtest-lab analyses."""
    stats = raw_ffn_stats(series)
    return {
        "total_return": stat_value(stats, "total_return"),
        "cagr": stat_value(stats, "cagr"),
        "volatility": stat_value(stats, "daily_vol"),
        "sharpe": stat_value(stats, "daily_sharpe"),
        "sortino": stat_value(stats, "daily_sortino"),
        "max_drawdown": stat_value(stats, "max_drawdown"),
        "calmar": stat_value(stats, "calmar"),
    }


def ffn_stats_table(
    results: Mapping[str, BacktestResult],
) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    """Return an FFN metric table plus the raw stats keyed by result name."""
    columns = {name: raw_ffn_stats(result.performance) for name, result in results.items()}
    return pd.concat(columns, axis=1), columns


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
