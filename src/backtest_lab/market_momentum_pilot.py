from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from backtest_lab.core import RuntimeConfig
from backtest_lab.data import DataSource, MarketDataConfig, load_market_data
from backtest_lab.settings import ExecutionSettings
from backtest_lab.strategies.market_momentum.r01 import UNIVERSE, find_active_start, run_pilot


def run_live_pilot(
    start: str = "2010-01-01",
    end: str | None = None,
    output_dir: str | Path = "runs/market_momentum/r01",
) -> tuple[dict[str, Path], str, str, str]:
    end = end or str(date.today() + timedelta(days=1))
    prices = load_market_data(
        UNIVERSE,
        start,
        end,
        config=MarketDataConfig(source=DataSource.YAHOO_FINANCE),
    )
    active_start = find_active_start(prices)
    settings = ExecutionSettings.from_env()
    outputs = run_pilot(
        prices,
        start=active_start,
        config=RuntimeConfig(fee_rate=settings.fee_rate, slippage_bps=settings.slippage_bps),
    )
    return (
        outputs.write_csv(output_dir),
        str(prices.index.min().date()),
        str(prices.index.max().date()),
        str(active_start.date()),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--end")
    parser.add_argument("--output-dir", default="runs/market_momentum/r01")
    args = parser.parse_args()
    paths, coverage_start, coverage_end, active_start = run_live_pilot(args.start, args.end, args.output_dir)
    print(f"coverage: {coverage_start} to {coverage_end}")
    print(f"active_start: {active_start}")
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
