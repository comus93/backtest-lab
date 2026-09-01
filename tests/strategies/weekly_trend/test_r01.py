import pandas as pd
import pytest

from backtest_lab.core import Runtime, RuntimeConfig
from backtest_lab.strategies.weekly_trend.r01 import (
    WeeklyTrendStrategy,
    completed_weekly_closes,
    run_pilot,
    two_week_direction,
)


def weekly_test_prices(symbols=("SPY", "AAA")) -> pd.DataFrame:
    index = pd.DatetimeIndex(
        [
            "2026-01-02",
            "2026-01-05",
            "2026-01-09",
            "2026-01-12",
            "2026-01-16",
            "2026-01-19",
            "2026-01-23",
            "2026-01-26",
            "2026-01-30",
            "2026-02-02",
        ]
    )
    values = {
        "SPY": [100.0] * len(index),
        "AAA": [100.0, 100.0, 110.0, 110.0, 120.0, 120.0, 110.0, 110.0, 100.0, 100.0],
    }
    return pd.DataFrame({symbol: values[symbol] for symbol in symbols}, index=index)


def test_completed_weekly_closes_uses_last_available_trading_day() -> None:
    prices = pd.DataFrame(
        {"AAA": [100.0, 101.0, 102.0, 103.0]},
        index=pd.DatetimeIndex(["2026-01-05", "2026-01-08", "2026-01-12", "2026-01-16"]),
    )
    weekly = completed_weekly_closes(prices, ("AAA",))
    assert list(weekly.index) == [pd.Timestamp("2026-01-08"), pd.Timestamp("2026-01-16")]
    assert weekly["AAA"].tolist() == [101.0, 103.0]


def test_two_week_direction_baseline_and_threshold() -> None:
    weekly = pd.DataFrame(
        {"AAA": [100.0, 101.0, 102.01]},
        index=pd.DatetimeIndex(["2026-01-02", "2026-01-09", "2026-01-16"]),
    )
    rising, falling, _, _ = two_week_direction(weekly, "AAA", move_threshold=0.0)
    assert rising is True
    assert falling is False

    rising, falling, _, _ = two_week_direction(weekly, "AAA", move_threshold=0.02)
    assert rising is False
    assert falling is False


def test_enters_after_two_up_weeks_and_exits_after_two_down_weeks() -> None:
    prices = weekly_test_prices()
    strategy = WeeklyTrendStrategy(symbols=("SPY", "AAA"))
    result = Runtime(strategy, 1_000.0, RuntimeConfig()).run(prices)

    aaa_fills = [fill for fill in result.fills if fill.symbol == "AAA"]
    assert [fill.side for fill in aaa_fills] == ["buy", "sell"]
    assert [fill.timestamp for fill in aaa_fills] == [pd.Timestamp("2026-01-19"), pd.Timestamp("2026-02-02")]

    actions = [(row["execution_date"], row["action"]) for row in strategy.decisions if row["symbol"] == "AAA"]
    assert (pd.Timestamp("2026-01-19"), "enter") in actions
    assert (pd.Timestamp("2026-02-02"), "exit") in actions


def test_execution_day_price_does_not_change_signal() -> None:
    baseline = weekly_test_prices()
    leaked = baseline.copy()
    leaked.loc[pd.Timestamp("2026-01-19"), "AAA"] = 10_000.0

    outputs = []
    for prices in (baseline, leaked):
        strategy = WeeklyTrendStrategy(symbols=("SPY", "AAA"))
        Runtime(strategy, 1_000.0, RuntimeConfig()).run(prices)
        outputs.append(
            [
                (row["signal_date"], row["action"], row["rise_2w"], row["fall_2w"])
                for row in strategy.decisions
                if row["symbol"] == "AAA" and row["execution_date"] == pd.Timestamp("2026-01-19")
            ]
        )
    assert outputs[0] == outputs[1]


def test_one_over_n_slot_leaves_unused_cash_and_does_not_rebalance_without_state_change() -> None:
    prices = weekly_test_prices()
    strategy = WeeklyTrendStrategy(symbols=("SPY", "AAA"))
    result = Runtime(strategy, 1_000.0, RuntimeConfig()).run(prices)

    entry = next(fill for fill in result.fills if fill.symbol == "AAA" and fill.side == "buy")
    assert entry.quantity * entry.fill_price == pytest.approx(500.0)
    assert not any(fill.timestamp == pd.Timestamp("2026-01-26") for fill in result.fills)


def test_warmup_rows_drive_signal_without_warmup_trades() -> None:
    prices = weekly_test_prices()
    start = pd.Timestamp("2026-01-19")
    strategy = WeeklyTrendStrategy(symbols=("SPY", "AAA"))
    result = Runtime(strategy, 1_000.0, RuntimeConfig()).run(prices, start=start)

    assert any(fill.symbol == "AAA" and fill.side == "buy" and fill.timestamp == start for fill in result.fills)
    assert all(fill.timestamp >= start for fill in result.fills)
    assert result.performance.index[0] < start


def test_reproducible_and_outputs_smoke(tmp_path) -> None:
    prices = weekly_test_prices()
    first = Runtime(WeeklyTrendStrategy(symbols=("SPY", "AAA")), 1_000.0, RuntimeConfig()).run(prices)
    second = Runtime(WeeklyTrendStrategy(symbols=("SPY", "AAA")), 1_000.0, RuntimeConfig()).run(prices)
    assert first.fills == second.fills

    outputs = run_pilot(
        prices,
        start=prices.index[0],
        config=RuntimeConfig(),
        symbols=("SPY", "AAA"),
    )
    assert set(outputs.performance_summary["strategy"]) == {
        "Weekly Trend 1/N",
        "Universe Equal Weight Buy & Hold",
        "SPY Buy & Hold",
    }
    assert set(outputs.weekly_decisions.columns) >= {
        "signal_date",
        "execution_date",
        "symbol",
        "weekly_return_1",
        "weekly_return_2",
        "rise_2w",
        "fall_2w",
        "action",
        "active_after",
        "target_weight",
    }
    assert outputs.exposure.loc[pd.Timestamp("2026-01-19"), "invested_weight"] == pytest.approx(0.5)
    assert outputs.exposure.loc[pd.Timestamp("2026-02-02"), "invested_weight"] == pytest.approx(0.0)

    paths = outputs.write_csv(tmp_path)
    assert pd.read_csv(paths["performance_summary"]).columns[0] == "strategy"
    assert pd.read_csv(paths["equity_curves"]).columns[0] == "timestamp"
    assert pd.read_csv(paths["exposure"]).columns[0] == "timestamp"
