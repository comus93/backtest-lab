from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

import pandas as pd

from backtest_lab.core import BacktestResult

from .metrics import performance_metrics


@dataclass(frozen=True)
class WindowSpec:
    """One start/end evaluation window plus optional strategy-specific metadata."""

    start_date: pd.Timestamp
    end_date: pd.Timestamp
    metadata: Mapping[str, object] = field(default_factory=dict)


RunFromStart = Callable[[pd.Timestamp], Mapping[str, BacktestResult]]


def performance_metrics_through(series: pd.Series, end_date: pd.Timestamp | str) -> dict[str, float]:
    """Calculate canonical metrics from a run's own start through end_date."""
    end_timestamp = pd.Timestamp(end_date)
    sliced = series.loc[series.index <= end_timestamp]
    if len(sliced) < 2:
        raise ValueError("window must contain at least two performance observations.")
    return performance_metrics(sliced)


def evaluate_windows(
    windows: Iterable[WindowSpec],
    run_from_start: RunFromStart,
) -> pd.DataFrame:
    """Evaluate many start/end windows while running each distinct start only once.

    The caller defines which starts and ends are meaningful for the strategy.
    backtest-lab owns the repeated-run grouping and canonical performance metrics.
    """
    specs = [
        WindowSpec(
            start_date=pd.Timestamp(spec.start_date),
            end_date=pd.Timestamp(spec.end_date),
            metadata=dict(spec.metadata),
        )
        for spec in windows
    ]
    if not specs:
        return pd.DataFrame(
            columns=[
                "start_date",
                "end_date",
                "strategy",
                "total_return",
                "cagr",
                "volatility",
                "sharpe",
                "sortino",
                "max_drawdown",
                "calmar",
            ]
        )

    grouped: dict[pd.Timestamp, list[WindowSpec]] = defaultdict(list)
    for spec in specs:
        if spec.end_date < spec.start_date:
            raise ValueError(f"window end {spec.end_date} is before start {spec.start_date}.")
        grouped[spec.start_date].append(spec)

    rows: list[dict[str, object]] = []
    for start_date, start_specs in grouped.items():
        results = run_from_start(start_date)
        if not results:
            raise ValueError(f"run_from_start returned no results for {start_date.date()}.")

        for spec in start_specs:
            for strategy_name, result in results.items():
                metrics = performance_metrics_through(result.performance, spec.end_date)
                rows.append(
                    {
                        **dict(spec.metadata),
                        "start_date": start_date.date(),
                        "end_date": spec.end_date.date(),
                        "strategy": strategy_name,
                        **metrics,
                    }
                )

    return pd.DataFrame(rows)


def _eligible_mask(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values.dtype):
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def start_end_matrix(
    window_performance: pd.DataFrame,
    *,
    strategy: str,
    metric: str = "cagr",
    eligible_column: str | None = None,
    scale: float = 1.0,
) -> pd.DataFrame:
    """Pivot long-form window performance into Start x End form.

    Rows are start dates, columns are end dates, and cells contain the selected
    absolute metric. `scale=100.0` is convenient for percentage-form CSV views.
    """
    required = {"start_date", "end_date", "strategy", metric}
    if eligible_column is not None:
        required.add(eligible_column)
    missing = sorted(required - set(window_performance.columns))
    if missing:
        raise ValueError(f"window_performance missing required columns: {missing}")

    selected = window_performance.loc[window_performance["strategy"] == strategy].copy()
    if eligible_column is not None:
        selected = selected.loc[_eligible_mask(selected[eligible_column])]

    if selected.empty:
        return pd.DataFrame()

    selected["start_date"] = pd.to_datetime(selected["start_date"])
    selected["end_date"] = pd.to_datetime(selected["end_date"])

    duplicate_mask = selected.duplicated(subset=["start_date", "end_date"], keep=False)
    if duplicate_mask.any():
        duplicates = selected.loc[duplicate_mask, ["start_date", "end_date"]].drop_duplicates()
        raise ValueError(f"duplicate start/end cells for {strategy}: {duplicates.to_dict('records')}")

    matrix = selected.pivot(index="start_date", columns="end_date", values=metric).sort_index().sort_index(axis=1)
    matrix = matrix.astype(float) * float(scale)
    matrix.index.name = "start_date"
    matrix.columns.name = "end_date"
    return matrix
