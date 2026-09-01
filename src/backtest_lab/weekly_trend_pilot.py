from __future__ import annotations

import argparse
from pathlib import Path

from backtest_lab.core import RuntimeConfig
from backtest_lab.data import DataSource, MarketDataConfig, load_market_data
from backtest_lab.settings import ExecutionSettings
from backtest_lab.strategies.weekly_trend.r01 import UNIVERSE, run_pilot

DEFAULT_DATA_START = "2016-06-01"
DEFAULT_ACTIVE_START = "2016-07-01"
DEFAULT_END = "2026-08-01"


def run_live_pilot(
    data_start: str = DEFAULT_DATA_START,
    active_start: str = DEFAULT_ACTIVE_START,
    end: str = DEFAULT_END,
    output_dir: str | Path = "runs/weekly_trend/r01",
    move_threshold: float = 0.0,
) -> tuple[dict[str, Path], str, str]:
    prices = load_market_data(
        UNIVERSE,
        data_start,
        end,
        config=MarketDataConfig(source=DataSource.YAHOO_FINANCE),
    )
    settings = ExecutionSettings.from_env()
    outputs = run_pilot(
        prices,
        start=active_start,
        config=RuntimeConfig(fee_rate=settings.fee_rate, slippage_bps=settings.slippage_bps),
        move_threshold=move_threshold,
    )
    return outputs.write_csv(output_dir), str(prices.index.min().date()), str(prices.index.max().date())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-start", default=DEFAULT_DATA_START)
    parser.add_argument("--active-start", default=DEFAULT_ACTIVE_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--output-dir", default="runs/weekly_trend/r01")
    parser.add_argument("--move-threshold", type=float, default=0.0)
    args = parser.parse_args()

    paths, coverage_start, coverage_end = run_live_pilot(
        data_start=args.data_start,
        active_start=args.active_start,
        end=args.end,
        output_dir=args.output_dir,
        move_threshold=args.move_threshold,
    )
    print(f"coverage: {coverage_start} to {coverage_end}")
    print(f"active_start: {args.active_start}")
    print(f"move_threshold: {args.move_threshold}")
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
