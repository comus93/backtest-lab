from __future__ import annotations

import argparse
from dataclasses import dataclass

from backtest_lab.core import Runtime, RuntimeConfig
from backtest_lab.data import DataCoverageError, MarketDataConfig, MySqlConfig, load_market_data
from backtest_lab.settings import ExecutionSettings
from backtest_lab.strategies import MonthlyTargetWeightStrategy


SAMPLE_TICKERS = {
    "KODEX_US_SP500": "379800",
    "ACE_KRX_GOLD": "411060",
}
SAMPLE_START = "2021-01-01"
SAMPLE_END = "2026-08-01"
SAMPLE_INITIAL_CASH = 10_000_000.0


@dataclass(frozen=True)
class SampleRunSummary:
    start: str
    end: str
    rows: int
    fills: int
    final_equity: float
    final_performance: float


def run_sample(require_full_coverage: bool = True) -> SampleRunSummary:
    db = MySqlConfig.from_env()
    settings = ExecutionSettings.from_env()
    prices = load_market_data(
        SAMPLE_TICKERS.values(),
        SAMPLE_START,
        SAMPLE_END,
        config=MarketDataConfig(require_full_coverage=require_full_coverage),
        mysql_config=db,
    )
    strategy = MonthlyTargetWeightStrategy(
        target_weights={
            SAMPLE_TICKERS["KODEX_US_SP500"]: 0.70,
            SAMPLE_TICKERS["ACE_KRX_GOLD"]: 0.30,
        }
    )
    runtime = Runtime(
        strategy=strategy,
        initial_cash=SAMPLE_INITIAL_CASH,
        config=RuntimeConfig(fee_rate=settings.fee_rate, slippage_bps=settings.slippage_bps),
    )
    result = runtime.run(prices)
    return SampleRunSummary(
        start=str(prices.index.min().date()),
        end=str(prices.index.max().date()),
        rows=len(prices),
        fills=len(result.fills),
        final_equity=float(result.equity.iloc[-1]),
        final_performance=float(result.performance.iloc[-1]),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Run on the overlapping available DB period instead of requiring full requested coverage.",
    )
    args = parser.parse_args()
    try:
        summary = run_sample(require_full_coverage=not args.allow_partial)
    except DataCoverageError as exc:
        print(f"sample_blocker: {exc}")
        return 2
    print(f"rows: {summary.rows}")
    print(f"period: {summary.start} to {summary.end}")
    print(f"fills: {summary.fills}")
    print(f"final_equity: {summary.final_equity:.2f}")
    print(f"final_performance: {summary.final_performance:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
