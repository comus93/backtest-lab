from __future__ import annotations

import pandas as pd
import pytest

from backtest_lab.core import Runtime, RuntimeConfig
from backtest_lab.strategies.tripod_nasdaq_leverage.r01 import (
    DRAWDOWN_RISK,
    REGIME_DOWN_HIGH_VOL,
    REGIME_DOWN_LOW_VOL,
    REGIME_UNKNOWN,
    REGIME_UP_LOW_RISK,
    REGIME_UP_RISK,
    TripodStrategy,
    _signal_snapshot,
    _target_for_state,
    _update_trend,
    find_active_start,
    run_pilot,
)


def make_prices(periods: int = 270) -> pd.DataFrame:
    index = pd.bdate_range("2020-01-02", periods=periods)
    return pd.DataFrame(
        {
            "QQQ": [100.0] * periods,
            "QLD": [50.0] * periods,
            "TQQQ": [25.0] * periods,
            "NDX": [100.0] * periods,
            "VIX": [20.0] * periods,
        },
        index=index,
    )


def test_signal_windows_use_only_required_trailing_observations() -> None:
    prices = make_prices(260)
    prices.iloc[:8, prices.columns.get_loc("NDX")] = 1_000.0
    prices.iloc[:8, prices.columns.get_loc("VIX")] = 100.0
    prices.iloc[-252, prices.columns.get_loc("NDX")] = 120.0
    signal = _signal_snapshot(prices, prices.index[-1])

    assert signal["sma250"] == pytest.approx(100.0)
    assert signal["high252"] == pytest.approx(120.0)
    assert signal["vix10"] == pytest.approx(20.0)
    assert signal["ndx_close"] == pytest.approx(100.0)


def test_signal_snapshot_rejects_insufficient_history() -> None:
    prices = make_prices(251)
    with pytest.raises(ValueError, match="252"):
        _signal_snapshot(prices, prices.index[-1])


@pytest.mark.parametrize(
    ("previous", "ratio", "expected"),
    [
        ("UNKNOWN", 0.01, "UP"),
        ("DOWN", 0.02, "UP"),
        ("UNKNOWN", -0.05, "DOWN"),
        ("UP", -0.06, "DOWN"),
        ("UP", 0.0099, "UP"),
        ("DOWN", -0.0499, "DOWN"),
        ("UNKNOWN", 0.0, "UNKNOWN"),
    ],
)
def test_trend_hysteresis_boundaries(previous: str, ratio: float, expected: str) -> None:
    assert _update_trend(previous, ratio) == expected


@pytest.mark.parametrize(
    ("trend", "vix10", "dd52", "weights", "regime", "exposure"),
    [
        ("UP", 27.999, -0.09, {"TQQQ": 1.0}, REGIME_UP_LOW_RISK, 3.0),
        ("UP", 28.0, -0.09, {"QQQ": 0.5, "QLD": 0.5}, REGIME_UP_RISK, 1.5),
        ("UP", 10.0, -0.090001, {"QQQ": 0.5, "QLD": 0.5}, REGIME_UP_RISK, 1.5),
        ("DOWN", 17.999, -0.50, {"QQQ": 0.5, "QLD": 0.5}, REGIME_DOWN_LOW_VOL, 1.5),
        ("DOWN", 18.0, 0.0, {}, REGIME_DOWN_HIGH_VOL, 0.0),
        ("UNKNOWN", 10.0, 0.0, {}, REGIME_UNKNOWN, 0.0),
    ],
)
def test_target_regimes(
    trend: str,
    vix10: float,
    dd52: float,
    weights: dict[str, float],
    regime: str,
    exposure: float,
) -> None:
    actual_weights, actual_regime, actual_exposure = _target_for_state(trend, vix10, dd52)
    assert actual_weights == weights
    assert actual_regime == regime
    assert actual_exposure == exposure


def test_drawdown_boundary_is_inclusive_for_low_risk() -> None:
    weights, regime, _ = _target_for_state("UP", 20.0, DRAWDOWN_RISK)
    assert weights == {"TQQQ": 1.0}
    assert regime == REGIME_UP_LOW_RISK


def test_find_active_start_leaves_252_complete_warmup_rows() -> None:
    prices = make_prices(260)
    active_start = find_active_start(prices)
    assert active_start == prices.index[252]
    assert len(prices.loc[prices.index < active_start]) == 252


def test_first_active_day_stays_cash_and_first_signal_executes_t_plus_one() -> None:
    prices = make_prices(254)
    start = prices.index[252]
    prices.loc[start, "NDX"] = 102.0

    strategy = TripodStrategy()
    result = Runtime(strategy, 1_000_000.0, RuntimeConfig()).run(prices, start=start)

    assert strategy.decisions[0]["signal_date"] == start
    assert strategy.decisions[0]["execution_date"] == prices.index[253]
    assert strategy.decisions[0]["trend"] == "UP"
    assert strategy.decisions[0]["regime"] == REGIME_UP_LOW_RISK
    assert len(result.fills) == 1
    assert result.fills[0].timestamp == prices.index[253]
    assert result.fills[0].symbol == "TQQQ"


def test_execution_day_price_does_not_change_signal() -> None:
    baseline = make_prices(254)
    start = baseline.index[252]
    baseline.loc[start, "NDX"] = 102.0
    shocked = baseline.copy()
    shocked.loc[shocked.index[253], "NDX"] = 1_000.0
    shocked.loc[shocked.index[253], "VIX"] = 100.0
    shocked.loc[shocked.index[253], "TQQQ"] = 250.0

    decisions = []
    for prices in (baseline, shocked):
        strategy = TripodStrategy()
        Runtime(strategy, 1_000_000.0, RuntimeConfig()).run(prices, start=start)
        decisions.append(strategy.decisions[0])

    keys = ["signal_date", "trend", "regime", "sma250", "vix10", "dd52", "target_tqqq"]
    assert {key: decisions[0][key] for key in keys} == {key: decisions[1][key] for key in keys}


def test_neutral_zone_keeps_previous_trend_and_does_not_rebalance_same_target() -> None:
    prices = make_prices(255)
    start = prices.index[252]
    prices.loc[start, "NDX"] = 102.0
    prices.loc[prices.index[253], "NDX"] = 100.0

    strategy = TripodStrategy()
    result = Runtime(strategy, 1_000_000.0, RuntimeConfig()).run(prices, start=start)

    assert [row["trend"] for row in strategy.decisions] == ["UP", "UP"]
    assert strategy.decisions[0]["target_changed"] is True
    assert strategy.decisions[1]["target_changed"] is False
    assert len(result.fills) == 1


def test_initial_unknown_neutral_signal_remains_cash() -> None:
    prices = make_prices(254)
    start = prices.index[252]
    strategy = TripodStrategy()
    result = Runtime(strategy, 1_000_000.0, RuntimeConfig()).run(prices, start=start)

    assert strategy.decisions[0]["trend"] == "UNKNOWN"
    assert strategy.decisions[0]["regime"] == REGIME_UNKNOWN
    assert strategy.decisions[0]["target_changed"] is False
    assert result.fills == []


def test_down_low_volatility_allocates_half_qqq_half_qld() -> None:
    prices = make_prices(254)
    start = prices.index[252]
    prices.loc[start, "NDX"] = 94.0
    prices.loc[prices.index[:253], "VIX"] = 10.0

    strategy = TripodStrategy()
    result = Runtime(strategy, 1_000_000.0, RuntimeConfig()).run(prices, start=start)

    decision = strategy.decisions[0]
    assert decision["trend"] == "DOWN"
    assert decision["regime"] == REGIME_DOWN_LOW_VOL
    assert decision["target_qqq"] == pytest.approx(0.5)
    assert decision["target_qld"] == pytest.approx(0.5)
    assert {fill.symbol for fill in result.fills} == {"QQQ", "QLD"}


def test_down_high_volatility_target_exits_to_cash() -> None:
    prices = make_prices(256)
    start = prices.index[252]
    prices.loc[start, "NDX"] = 102.0
    prices.loc[prices.index[253], "NDX"] = 100.0
    prices.loc[prices.index[254], "NDX"] = 90.0

    strategy = TripodStrategy()
    result = Runtime(strategy, 1_000_000.0, RuntimeConfig()).run(prices, start=start)

    assert strategy.decisions[-1]["trend"] == "DOWN"
    assert strategy.decisions[-1]["regime"] == REGIME_DOWN_HIGH_VOL
    assert strategy.decisions[-1]["target_cash"] == pytest.approx(1.0)
    assert any(fill.side == "sell" and fill.symbol == "TQQQ" for fill in result.fills)


def test_run_pilot_outputs_ffn_and_strategy_analysis() -> None:
    prices = make_prices(270)
    start = prices.index[252]
    prices.loc[start:, "NDX"] = 102.0

    outputs = run_pilot(prices, start=start, config=RuntimeConfig())

    assert set(outputs.performance_summary["strategy"]) == {
        "Tripod Strategy",
        "QQQ Buy & Hold",
        "QLD Buy & Hold",
        "TQQQ Buy & Hold",
    }
    assert set(outputs.ffn_stats.columns) == {
        "Tripod Strategy",
        "QQQ Buy & Hold",
        "QLD Buy & Hold",
        "TQQQ Buy & Hold",
    }
    assert set(outputs.daily_signals.columns) >= {
        "signal_date", "execution_date", "trend", "vix10", "dd52", "regime", "nominal_exposure", "target_changed"
    }
    assert set(outputs.regime_summary.columns) == {"regime", "days", "share_of_active_days", "nominal_exposure"}
    assert set(outputs.yearly_performance.columns) == {"year", "strategy", "return", "max_drawdown"}
    assert set(outputs.exposure.columns) == {
        "timestamp", "trend", "regime", "qqq_weight", "qld_weight", "tqqq_weight", "cash_weight", "nominal_exposure"
    }
