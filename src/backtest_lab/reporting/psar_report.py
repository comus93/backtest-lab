"""PSAR case-study CLI and compatibility facade over shared Reporting modules."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .adapters.psar import (
    PALETTE, PSAR_DOWN_COLOR, PSAR_UP_COLOR, WINDOWS, _performance_matrix,
    build_psar_data, load_outputs, pair_trades, psar_config,
    to_report_period, window_data,
)
from .charts import build_charts, monthly_candles
from .palette import COLORS as _COMMON_COLORS, DAY_MS

COLORS = {**_COMMON_COLORS, "psar_up": PSAR_UP_COLOR, "psar_down": PSAR_DOWN_COLOR}
from .render import render_report
from .tables import tabular_html as _tabular_html


def _monthly_candles(candles: pd.DataFrame) -> pd.DataFrame:
    """Legacy helper: public tests still provide raw QQQ_* price columns."""
    renamed = candles.rename(columns={
        "QQQ_Open": "Open", "QQQ_High": "High",
        "QQQ_Low": "Low", "QQQ_Close": "Close",
    })
    return monthly_candles(renamed)


def _table_sections(data: dict[str, pd.DataFrame],
                    block: dict[str, object]) -> tuple[str, str]:
    """Keep the previously established PSAR test/caller interface."""
    return (
        _tabular_html(_performance_matrix(data["performance_summary"], block["window"])),
        _tabular_html(block["stats"].reset_index()),
    )


def _make_charts(block: dict[str, object], *, show_volume: bool = False):
    """Compatibility entrypoint: PSAR-specific data adaptation, common charts."""
    return build_charts(to_report_period(block), psar_config(show_volume=show_volume))


def build_report(run_dir: str | Path, destination: str | Path,
                 volume_path: str | Path | None = None, *,
                 show_volume: bool = False) -> Path:
    """Render original archived PSAR outputs without running the strategy."""
    outputs = load_outputs(run_dir, volume_path if show_volume else None)
    if show_volume and "QQQ_Volume" not in outputs["input_prices"]:
        raise ValueError("Volume was requested but no QQQ_Volume source was supplied")
    return render_report(build_psar_data(outputs), psar_config(show_volume=show_volume),
                         destination)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a static PSAR backtest Bokeh report")
    parser.add_argument("--run", required=True, help="Existing run CSV directory")
    parser.add_argument("--output", required=True, help="Output HTML path")
    parser.add_argument("--volume", default=None, help="Optional QQQ volume CSV, date-aligned to immutable prices")
    parser.add_argument("--show-volume", action="store_true",
                        help="Show price-aligned volume panel for volume-dependent strategies")
    args = parser.parse_args()
    print(build_report(args.run, args.output, args.volume, show_volume=args.show_volume))


if __name__ == "__main__":
    main()
