import numpy as np
import pandas as pd
import pytest

from backtest_lab.core import Runtime, RuntimeConfig
from backtest_lab.strategies.market_momentum.r02 import (
    COMPARISON_ASSETS,
    HORIZONS,
    UNIVERSE,
    MarketMomentumStrategy,
    _constituent_outputs,
    _correlation,
    _resampled_returns,
    run_pilot,
)


def synthetic_prices() -> tuple[pd.DataFrame, pd.DataFrame]:
    index = pd.date_range("2021-01-01", periods=620, freq="B")
    signal = {}
    for position, symbol in enumerate(UNIVERSE):
        daily_return = 0.0002 + ((np.arange(len(index)) + position * 7) % (position + 5) - 2) * 0.0001
        signal[symbol] = 100.0 * np.cumprod(1.0 + daily_return)
    prices = pd.DataFrame(signal, index=index)
    assets = {}
    for position, symbol in enumerate(COMPARISON_ASSETS):
        daily_return = 0.0001 + ((np.arange(len(index)) * (position + 2)) % 9 - 4) * 0.00012
        assets[symbol] = 100.0 * np.cumprod(1.0 + daily_return)
    return prices, pd.DataFrame(assets, index=index)


def test_r02_runs_only_requested_horizons_and_preserves_execution_timing() -> None:
    assert HORIZONS == (3, 6, 12)
    with pytest.raises(ValueError):
        MarketMomentumStrategy(9)

    index = pd.DatetimeIndex([*pd.date_range("2022-01-31", periods=13, freq="ME"), "2023-02-01"])
    prices = pd.DataFrame({symbol: np.arange(100.0, 100.0 + len(index)) for symbol in UNIVERSE}, index=index)
    strategy = MarketMomentumStrategy(3)
    Runtime(strategy, 1_000, RuntimeConfig()).run(prices, start="2023-02-01")
    assert {row["signal_date"] for row in strategy.decisions} == {pd.Timestamp("2023-01-31")}
    assert {row["execution_date"] for row in strategy.decisions} == {pd.Timestamp("2023-02-01")}


def test_weekly_correlation_uses_returns_not_levels() -> None:
    index = pd.to_datetime(["2024-01-05", "2024-01-12", "2024-01-19", "2024-01-26"])
    strategy_levels = pd.Series([100.0, 110.0, 99.0, 108.9], index=index)
    asset_levels = pd.Series([100.0, 90.0, 99.0, 89.1], index=index)
    correlation, n_obs = _correlation(_resampled_returns(strategy_levels, "weekly"), _resampled_returns(asset_levels, "weekly"))
    assert correlation == pytest.approx(-1.0)
    assert n_obs == 3


def test_comparison_assets_are_exact_and_not_signal_universe() -> None:
    assert COMPARISON_ASSETS == ("QQQ", "SLV", "GDX", "AIA", "XLF", "XLE", "EWW")
    assert set(COMPARISON_ASSETS) - set(UNIVERSE) == {"SLV", "GDX", "AIA", "XLF", "XLE"}


def test_pairwise_alignment_retains_shared_observation_count() -> None:
    left = pd.Series([0.1, 0.2, 0.3], index=pd.to_datetime(["2024-01-05", "2024-01-12", "2024-01-19"]))
    right = pd.Series([0.4, 0.6], index=pd.to_datetime(["2024-01-12", "2024-01-19"]))
    correlation, n_obs = _correlation(left, right)
    assert n_obs == 2
    assert correlation == pytest.approx(1.0)


def test_yearly_constituents_use_selected_union_and_weekly_returns() -> None:
    index = pd.date_range("2024-01-01", periods=15, freq="B")
    prices = pd.DataFrame({
        "AAA": np.linspace(100, 114, len(index)),
        "BBB": np.linspace(100, 86, len(index)),
        "CCC": np.linspace(100, 100, len(index)),
    }, index=index)
    decisions = pd.DataFrame([
        {"horizon": 12, "signal_date": "2024-01-31", "symbol": "AAA", "selected": True},
        {"horizon": 12, "signal_date": "2024-02-29", "symbol": "AAA", "selected": True},
        {"horizon": 12, "signal_date": "2024-02-29", "symbol": "BBB", "selected": True},
        {"horizon": 12, "signal_date": "2024-02-29", "symbol": "CCC", "selected": False},
    ])
    matrix, constituents = _constituent_outputs(prices, decisions, pd.Timestamp("2024-01-01"))
    assert constituents.to_dict("records") == [
        {"year": 2024, "symbol": "AAA", "selected_months": 2},
        {"year": 2024, "symbol": "BBB", "selected_months": 1},
    ]
    assert set(matrix["symbol_a"]) | set(matrix["symbol_b"]) == {"AAA", "BBB"}
    assert matrix["n_obs"].min() > 1


def test_r02_outputs_include_independent_horizons_and_correlation_files(tmp_path) -> None:
    prices, assets = synthetic_prices()
    outputs = run_pilot(prices, assets, start="2022-02-01", config=RuntimeConfig())
    assert set(outputs.performance_summary["strategy"]) == {"Momentum 3M", "Momentum 6M", "Momentum 12M", "SPY Buy & Hold"}
    assert set(outputs.monthly_decisions["horizon"]) == set(HORIZONS)
    assert set(outputs.yearly_asset_correlation["horizon"]) == set(HORIZONS)
    assert set(outputs.overall_asset_correlation["frequency"]) == {"weekly", "monthly"}
    assert set(outputs.overall_asset_correlation["horizon"]) == set(HORIZONS)
    assert set(outputs.yearly_asset_correlation.columns) == {"year", "horizon", "asset", "correlation", "n_obs"}
    assert set(outputs.yearly_constituent_correlation.columns) == {"year", "symbol_a", "symbol_b", "correlation", "n_obs"}
    assert set(outputs.monthly_decisions.columns) >= {"horizon", "signal_date", "execution_date", "symbol", "momentum", "rank", "selected", "target_weight"}
    assert set(outputs.yearly_constituents.columns) == {"year", "symbol", "selected_months"}
    paths = outputs.write_csv(tmp_path)
    assert set(paths) == {
        "performance_summary", "equity_curves", "monthly_decisions", "yearly_asset_correlation",
        "overall_asset_correlation", "yearly_constituent_correlation", "yearly_constituents",
    }
    assert pd.read_csv(paths["equity_curves"]).columns[0] == "timestamp"
