from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pytest

from backtest_lab.analysis import WindowSpec, evaluate_windows, start_end_matrix


@dataclass
class DummyResult:
    performance: pd.Series


def test_evaluate_windows_runs_each_distinct_start_once() -> None:
    calls: list[pd.Timestamp] = []

    def run_from_start(start: pd.Timestamp):
        calls.append(start)
        index = pd.date_range(start, periods=8, freq="YS")
        performance = pd.Series([100.0, 110.0, 121.0, 133.1, 146.41, 161.051, 177.1561, 194.87171], index=index)
        return {"Strategy A": DummyResult(performance)}

    windows = [
        WindowSpec("2010-01-01", "2015-01-01", {"matrix_eligible": True}),
        WindowSpec("2010-01-01", "2016-01-01", {"matrix_eligible": True}),
        WindowSpec("2011-01-01", "2016-01-01", {"matrix_eligible": True}),
    ]

    frame = evaluate_windows(windows, run_from_start)

    assert calls == [pd.Timestamp("2010-01-01"), pd.Timestamp("2011-01-01")]
    assert len(frame) == 3
    assert set(frame["strategy"]) == {"Strategy A"}
    assert {"cagr", "sharpe", "max_drawdown", "matrix_eligible"}.issubset(frame.columns)


def test_start_end_matrix_uses_absolute_metric_and_scale() -> None:
    frame = pd.DataFrame(
        [
            {
                "start_date": "2010-01-01",
                "end_date": "2015-01-01",
                "strategy": "Strategy A",
                "cagr": 0.10,
                "matrix_eligible": True,
            },
            {
                "start_date": "2010-01-01",
                "end_date": "2016-01-01",
                "strategy": "Strategy A",
                "cagr": 0.12,
                "matrix_eligible": True,
            },
            {
                "start_date": "2011-01-01",
                "end_date": "2016-01-01",
                "strategy": "Strategy A",
                "cagr": 0.08,
                "matrix_eligible": True,
            },
            {
                "start_date": "2011-01-01",
                "end_date": "2015-01-01",
                "strategy": "Strategy A",
                "cagr": 0.50,
                "matrix_eligible": False,
            },
        ]
    )

    matrix = start_end_matrix(
        frame,
        strategy="Strategy A",
        metric="cagr",
        eligible_column="matrix_eligible",
        scale=100.0,
    )

    assert matrix.loc[pd.Timestamp("2010-01-01"), pd.Timestamp("2015-01-01")] == pytest.approx(10.0)
    assert matrix.loc[pd.Timestamp("2010-01-01"), pd.Timestamp("2016-01-01")] == pytest.approx(12.0)
    assert matrix.loc[pd.Timestamp("2011-01-01"), pd.Timestamp("2016-01-01")] == pytest.approx(8.0)
    assert pd.isna(matrix.loc[pd.Timestamp("2011-01-01"), pd.Timestamp("2015-01-01")])


def test_start_end_matrix_rejects_duplicate_cells() -> None:
    frame = pd.DataFrame(
        [
            {"start_date": "2010-01-01", "end_date": "2015-01-01", "strategy": "A", "cagr": 0.1},
            {"start_date": "2010-01-01", "end_date": "2015-01-01", "strategy": "A", "cagr": 0.2},
        ]
    )

    with pytest.raises(ValueError, match="duplicate start/end cells"):
        start_end_matrix(frame, strategy="A")
