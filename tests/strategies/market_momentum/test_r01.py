import pandas as pd
import pytest

from backtest_lab.core import Runtime, RuntimeConfig
from backtest_lab.strategies.market_momentum.r01 import (
    HORIZONS,
    UNIVERSE,
    MarketMomentumStrategy,
    StaticEqualWeightStrategy,
    monthly_momentum,
    rank_symbols,
    run_pilot,
)


def monthly_prices(symbols=UNIVERSE, periods=14) -> pd.DataFrame:
    index = pd.date_range("2022-01-31", periods=periods, freq="ME")
    return pd.DataFrame(
        {symbol: [100.0 + position * 10 + month for month in range(periods)] for position, symbol in enumerate(symbols)},
        index=index,
    )


def execution_prices(symbols=UNIVERSE, periods=14) -> pd.DataFrame:
    warmup = monthly_prices(symbols, periods)
    first_execution = warmup.index[-1] + pd.Timedelta(days=1)
    next_signal = warmup.index[-1] + pd.offsets.MonthEnd(1)
    second_execution = next_signal + pd.Timedelta(days=1)
    extra = pd.DataFrame(
        {symbol: [warmup.iloc[-1][symbol], warmup.iloc[-1][symbol], warmup.iloc[-1][symbol]] for symbol in symbols},
        index=pd.DatetimeIndex([first_execution, next_signal, second_execution]),
    )
    return pd.concat([warmup, extra]).sort_index()


def test_calendar_month_momentum_uses_month_end_prices() -> None:
    prices = monthly_prices(("AAA",), 13)
    prices.iloc[0, 0] = 100
    prices.iloc[3, 0] = 200
    prices.iloc[6, 0] = 250
    prices.iloc[9, 0] = 400
    prices.iloc[12, 0] = 500
    signal_date = prices.index[-1]

    assert monthly_momentum(prices, signal_date, 3, ("AAA",)).iloc[0] == pytest.approx(0.25)
    assert monthly_momentum(prices, signal_date, 6, ("AAA",)).iloc[0] == pytest.approx(1.0)
    assert monthly_momentum(prices, signal_date, 9, ("AAA",)).iloc[0] == pytest.approx(1.5)
    assert monthly_momentum(prices, signal_date, 12, ("AAA",)).iloc[0] == pytest.approx(4.0)


def test_signal_cutoff_ignores_execution_day_price() -> None:
    symbols = ("AAA", "BBB", "CCC", "DDD")
    warmup = monthly_prices(symbols, 13)
    execution = warmup.index[-1] + pd.Timedelta(days=1)
    baseline = pd.concat([warmup, pd.DataFrame({symbol: [100.0] for symbol in symbols}, index=[execution])])
    leaked = baseline.copy()
    leaked.loc[execution, "DDD"] = 10_000.0

    selected = []
    for prices in (baseline, leaked):
        strategy = MarketMomentumStrategy(3, symbols)
        Runtime(strategy, 1_000, RuntimeConfig()).run(prices, start=execution)
        selected.append([row["symbol"] for row in strategy.decisions if row["selected"]])
    assert selected[0] == selected[1]


def test_ranking_selects_expected_top_three() -> None:
    momentum = pd.Series({"AAA": 0.10, "BBB": 0.40, "CCC": 0.20, "DDD": 0.30})
    assert rank_symbols(momentum)[:3] == ["BBB", "DDD", "CCC"]


def test_horizons_are_independent() -> None:
    symbols = ("AAA", "BBB", "CCC", "DDD")
    prices = pd.DataFrame(100.0, index=pd.date_range("2022-01-31", periods=13, freq="ME"), columns=symbols)
    prices.iloc[0] = [2, 1, 3, 4]   # 12M: BBB, AAA, CCC
    prices.iloc[3] = [3, 4, 1, 2]   # 9M: CCC, DDD, AAA
    prices.iloc[6] = [4, 3, 2, 1]   # 6M: DDD, CCC, BBB
    prices.iloc[9] = [1, 2, 3, 4]   # 3M: AAA, BBB, CCC
    expected = {3: ["AAA", "BBB", "CCC"], 6: ["DDD", "CCC", "BBB"], 9: ["CCC", "DDD", "AAA"], 12: ["BBB", "AAA", "CCC"]}

    for horizon in HORIZONS:
        assert rank_symbols(monthly_momentum(prices, prices.index[-1], horizon, symbols))[:3] == expected[horizon]


def test_rebalances_on_next_trading_day_only_once_per_month() -> None:
    prices = execution_prices()
    strategy = MarketMomentumStrategy(3)
    Runtime(strategy, 1_000, RuntimeConfig()).run(prices, start="2023-03-01")

    assert {row["execution_date"] for row in strategy.decisions} == {pd.Timestamp("2023-03-01"), pd.Timestamp("2023-04-01")}
    assert len(strategy.decisions) == 2 * len(UNIVERSE)


def test_target_weights_rotation_and_static_equal_weight() -> None:
    prices = execution_prices()
    prices.loc[pd.Timestamp("2023-03-31"), "SPY"] = 1.0
    prices.loc[pd.Timestamp("2023-03-31"), "QQQ"] = 2.0
    prices.loc[pd.Timestamp("2023-03-31"), "DIA"] = 3.0
    dynamic = MarketMomentumStrategy(3)
    dynamic_result = Runtime(dynamic, 1_000_000, RuntimeConfig()).run(prices, start="2023-03-01")
    selected = [row for row in dynamic.decisions if row["selected"]]
    assert len(selected) == 6
    assert all(row["target_weight"] == pytest.approx(1 / 3) for row in selected)
    assert any(fill.side == "sell" for fill in dynamic_result.fills)

    static_result = Runtime(StaticEqualWeightStrategy(), 1_400, RuntimeConfig()).run(prices, start="2023-03-01")
    assert all(static_result.portfolio.quantity(symbol) > 0 for symbol in UNIVERSE)
    assert static_result.portfolio.value({symbol: prices.iloc[-1][symbol] for symbol in UNIVERSE}) == pytest.approx(1_400)


def test_tie_break_and_reproducibility() -> None:
    assert rank_symbols(pd.Series({"DDD": 0.1, "CCC": 0.1, "BBB": 0.2, "AAA": 0.3})) == ["AAA", "BBB", "CCC", "DDD"]
    prices = execution_prices()
    first = Runtime(MarketMomentumStrategy(3), 1_000, RuntimeConfig()).run(prices, start="2023-03-01")
    second = Runtime(MarketMomentumStrategy(3), 1_000, RuntimeConfig()).run(prices, start="2023-03-01")
    assert first.fills == second.fills


def test_warmup_history_is_used_without_warmup_orders() -> None:
    prices = execution_prices()
    start = pd.Timestamp("2023-03-01")
    result = Runtime(MarketMomentumStrategy(12), 1_000, RuntimeConfig()).run(prices, start=start)
    assert result.fills
    assert all(fill.timestamp >= start for fill in result.fills)
    assert result.performance.index[0] < start


def test_analysis_outputs_smoke(tmp_path) -> None:
    prices = execution_prices()
    outputs = run_pilot(prices, start="2023-03-01", config=RuntimeConfig())
    assert set(outputs.performance_summary["strategy"]) == {
        "Static Equal Weight", "Momentum 3M", "Momentum 6M", "Momentum 9M", "Momentum 12M", "SPY Buy & Hold"
    }
    assert set(outputs.monthly_decisions.columns) >= {"horizon", "signal_date", "execution_date", "symbol", "momentum", "rank", "selected", "target_weight"}
    assert set(outputs.momentum_signal_analysis.columns) >= {"horizon", "top3_next_1m_return", "bottom3_next_1m_return", "top3_minus_bottom3", "spread_win_rate", "observation_months"}
    assert not outputs.equity_curves.empty
    paths = outputs.write_csv(tmp_path)
    assert list(pd.read_csv(paths["performance_summary"]).columns)[0] == "strategy"
    assert pd.read_csv(paths["equity_curves"]).columns[0] == "timestamp"
