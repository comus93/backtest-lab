"""Read-only diagnostic preparation from frozen Trend Research price inputs."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def efficiency_ratio_10(close: pd.Series) -> pd.Series:
    """Ten trading-session changes (eleven closes); flat windows yield zero."""
    distance = close.diff().abs().rolling(10, min_periods=10).sum()
    net = (close - close.shift(10)).abs()
    return (net / distance.where(distance != 0)).mask(distance == 0, 0.).rename("er10")


def write_trend_diagnostics(run, output):
    run, output = Path(run), Path(output)
    if output.resolve().is_relative_to(run.resolve()):
        raise ValueError("Diagnostics must not modify an archived Run")
    output.mkdir(parents=True, exist_ok=True)
    folders = sorted((run / "assets").glob("*/input_prices.csv"))
    if not folders and (run / "input_prices.csv").is_file():
        folders = [run / "input_prices.csv"]
    paths = {}
    for path in folders:
        key = path.parent.name if path.parent != run else "gold"
        raw = pd.read_csv(path, parse_dates=["timestamp"]).set_index("timestamp")
        close = raw.Close.dropna().sort_index()
        if not close.index.is_unique:
            raise ValueError("Duplicate diagnostic price dates")
        target = output / f"{key}.csv"
        efficiency_ratio_10(close).to_csv(target, index_label="timestamp")
        paths[key] = target
    if not paths:
        raise ValueError("No archived diagnostic price inputs")
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write_trend_diagnostics(args.run, args.output)


if __name__ == "__main__":
    main()
