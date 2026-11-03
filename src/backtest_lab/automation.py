from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

from backtest_lab.core import RuntimeConfig
from backtest_lab.data import DataSource, MarketDataConfig, load_market_data
from backtest_lab.settings import ExecutionSettings
from backtest_lab.strategies.sp500_top2_market_cap.r01 import (
    END_EXCLUSIVE as TOP2_END_EXCLUSIVE,
    REQUIRED_COLUMNS as TOP2_REQUIRED_COLUMNS,
    START as TOP2_START,
    run_pilot as run_top2_baseline,
)
from backtest_lab.strategies.tripod_nasdaq_leverage.r01 import (
    find_active_start as find_tripod_active_start,
    run_pilot as run_tripod_baseline,
    run_sensitivity_pilot as run_tripod_sensitivity,
)
from backtest_lab.strategies.us_market_cap_leaders.evaluation import (
    run_baseline as run_market_cap_leaders_baseline,
    run_window_sensitivity as run_market_cap_leaders_window_sensitivity,
)
from backtest_lab.strategies.us_market_cap_leaders.r01 import (
    END_EXCLUSIVE as MARKET_CAP_LEADERS_END_EXCLUSIVE,
    PRICE_START as MARKET_CAP_LEADERS_PRICE_START,
    REQUIRED_COLUMNS as MARKET_CAP_LEADERS_REQUIRED_COLUMNS,
    find_active_start as find_market_cap_leaders_active_start,
)
from backtest_lab.strategies.psar_segment_duration.data import load_fdr_prices
from backtest_lab.strategies.psar_segment_duration.r01 import run_pilot as run_psar_baseline
from backtest_lab.tripod_nasdaq_leverage_pilot import load_tripod_prices

REQUEST_ID_RE = re.compile(r"^(?P<date>\d{8})T\d{6}(?:[+-]\d{4}|Z)?$")
RUN_ID_RE_TEMPLATE = r"^{date}-(\d{{4}})$"

TRIPOD_OUTPUT_FILES = (
    "input_prices.csv",
    "ffn_stats.csv",
    "performance_summary.csv",
    "equity_curves.csv",
    "daily_signals.csv",
    "regime_summary.csv",
    "yearly_performance.csv",
    "exposure.csv",
)

TOP2_OUTPUT_FILES = (
    "input_prices.csv",
    "ffn_stats.csv",
    "performance_summary.csv",
    "equity_curves.csv",
    "yearly_performance.csv",
    "annual_selections.csv",
    "fills.csv",
)

MARKET_CAP_LEADERS_BASELINE_OUTPUT_FILES = (
    "input_prices.csv",
    "ffn_stats.csv",
    "performance_summary.csv",
    "equity_curves.csv",
    "yearly_performance.csv",
    "quarterly_rankings.csv",
    "quarterly_selections.csv",
    "fills.csv",
)

MARKET_CAP_LEADERS_WINDOW_OUTPUT_FILES = (
    "input_prices.csv",
    "quarterly_rankings.csv",
    "window_performance.csv",
    "rolling_summary.csv",
    "start_end_cagr_top1_pct.csv",
    "start_end_cagr_top2_pct.csv",
    "start_end_cagr_spy_pct.csv",
    "start_end_cagr_qqq_pct.csv",
)

PSAR_OUTPUT_FILES = (
    "input_prices.csv",
    "ffn_stats.csv",
    "performance_summary.csv",
    "equity_curves.csv",
    "daily_signals.csv",
    "segment_summary.csv",
    "yearly_performance.csv",
    "fills.csv",
)


@dataclass(frozen=True)
class BacktestRequest:
    request_id: str
    strategy_id: str
    revision: str
    mode: str
    start: str = "2009-01-01"
    end: str | None = None

    @property
    def request_date(self) -> str:
        match = REQUEST_ID_RE.match(self.request_id)
        if not match:
            raise ValueError(
                "request_id must use YYYYMMDDTHHMMSS+ZZZZ, YYYYMMDDTHHMMSSZ, or equivalent format."
            )
        return match.group("date")


Runner = Callable[[pd.DataFrame, pd.Timestamp, RuntimeConfig], object]


def _tripod_baseline(prices: pd.DataFrame, active_start: pd.Timestamp, config: RuntimeConfig):
    return run_tripod_baseline(prices, start=active_start, config=config)


def _tripod_sensitivity(prices: pd.DataFrame, active_start: pd.Timestamp, config: RuntimeConfig):
    return run_tripod_sensitivity(prices, start=active_start, config=config)


def _top2_baseline(prices: pd.DataFrame, active_start: pd.Timestamp, config: RuntimeConfig):
    return run_top2_baseline(prices, start=active_start, config=config)


def _market_cap_leaders_baseline(prices: pd.DataFrame, active_start: pd.Timestamp, config: RuntimeConfig):
    return run_market_cap_leaders_baseline(prices, start=active_start, config=config)


def _market_cap_leaders_window_sensitivity(
    prices: pd.DataFrame, active_start: pd.Timestamp, config: RuntimeConfig
):
    return run_market_cap_leaders_window_sensitivity(prices, start=active_start, config=config)


def _psar_baseline(prices: pd.DataFrame, active_start: pd.Timestamp, config: RuntimeConfig):
    return run_psar_baseline(prices, config=config)


ALLOWED_RUNNERS: dict[tuple[str, str, str], Runner] = {
    ("tripod_nasdaq_leverage", "r01", "baseline"): _tripod_baseline,
    ("tripod_nasdaq_leverage", "r01", "sensitivity"): _tripod_sensitivity,
    ("sp500_top2_market_cap", "r01", "baseline"): _top2_baseline,
    ("us_market_cap_leaders", "r01", "baseline"): _market_cap_leaders_baseline,
    ("us_market_cap_leaders", "r01", "window_sensitivity"): _market_cap_leaders_window_sensitivity,
    ("psar_segment_duration", "r01", "baseline"): _psar_baseline,
}

REQUIRED_OUTPUTS_BY_KEY: dict[tuple[str, str, str], tuple[str, ...]] = {
    ("tripod_nasdaq_leverage", "r01", "baseline"): TRIPOD_OUTPUT_FILES,
    ("tripod_nasdaq_leverage", "r01", "sensitivity"): TRIPOD_OUTPUT_FILES,
    ("sp500_top2_market_cap", "r01", "baseline"): TOP2_OUTPUT_FILES,
    ("us_market_cap_leaders", "r01", "baseline"): MARKET_CAP_LEADERS_BASELINE_OUTPUT_FILES,
    ("us_market_cap_leaders", "r01", "window_sensitivity"): MARKET_CAP_LEADERS_WINDOW_OUTPUT_FILES,
    ("psar_segment_duration", "r01", "baseline"): PSAR_OUTPUT_FILES,
}


def load_request(path: str | Path) -> BacktestRequest:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"request_id", "strategy_id", "revision", "mode"}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"Missing request fields: {missing}")

    request = BacktestRequest(
        request_id=str(data["request_id"]),
        strategy_id=str(data["strategy_id"]),
        revision=str(data["revision"]),
        mode=str(data["mode"]),
        start=str(data.get("start") or "2009-01-01"),
        end=str(data["end"]) if data.get("end") else None,
    )
    _ = request.request_date
    key = (request.strategy_id, request.revision, request.mode)
    if key not in ALLOWED_RUNNERS:
        allowed = ", ".join("/".join(item) for item in sorted(ALLOWED_RUNNERS))
        raise ValueError(f"Unsupported backtest request {key}. Allowed: {allowed}")

    if key == ("sp500_top2_market_cap", "r01", "baseline"):
        if request.start != TOP2_START or request.end != TOP2_END_EXCLUSIVE:
            raise ValueError(
                f"sp500_top2_market_cap/r01 fixed period is start={TOP2_START}, end={TOP2_END_EXCLUSIVE}."
            )
    if request.strategy_id == "us_market_cap_leaders" and request.revision == "r01":
        if request.start != MARKET_CAP_LEADERS_PRICE_START or request.end != MARKET_CAP_LEADERS_END_EXCLUSIVE:
            raise ValueError(
                "us_market_cap_leaders/r01 fixed price coverage is "
                f"start={MARKET_CAP_LEADERS_PRICE_START}, end={MARKET_CAP_LEADERS_END_EXCLUSIVE}."
            )
    return request


def next_run_id(runs_root: str | Path, request: BacktestRequest) -> str:
    revision_dir = Path(runs_root) / request.strategy_id / request.revision
    pattern = re.compile(RUN_ID_RE_TEMPLATE.format(date=request.request_date))
    serials: list[int] = []
    if revision_dir.exists():
        for child in revision_dir.iterdir():
            if not child.is_dir():
                continue
            match = pattern.match(child.name)
            if match:
                serials.append(int(match.group(1)))
    serial = max(serials, default=0) + 1
    return f"{request.request_date}-{serial:04d}"


def _load_prices(request: BacktestRequest) -> pd.DataFrame:
    if request.strategy_id == "psar_segment_duration" and request.revision == "r01":
        if request.end is None:
            raise ValueError("psar_segment_duration/r01 requires an explicit end date.")
        return load_fdr_prices("2006-01-01", request.end)
    if request.strategy_id == "tripod_nasdaq_leverage" and request.revision == "r01":
        end = request.end or str(date.today() + timedelta(days=1))
        return load_tripod_prices(request.start, end)

    if request.strategy_id == "sp500_top2_market_cap" and request.revision == "r01":
        if request.end is None:
            raise ValueError("sp500_top2_market_cap/r01 requires an explicit end date.")
        return load_market_data(
            TOP2_REQUIRED_COLUMNS,
            request.start,
            request.end,
            config=MarketDataConfig(
                source=DataSource.YAHOO_FINANCE,
                price_column="AdjClose",
            ),
        )

    if request.strategy_id == "us_market_cap_leaders" and request.revision == "r01":
        if request.end is None:
            raise ValueError("us_market_cap_leaders/r01 requires an explicit end date.")
        return load_market_data(
            MARKET_CAP_LEADERS_REQUIRED_COLUMNS,
            request.start,
            request.end,
            config=MarketDataConfig(
                source=DataSource.YAHOO_FINANCE,
                price_column="AdjClose",
            ),
        )

    raise ValueError(f"No market-data loader registered for {request.strategy_id}/{request.revision}")


def _active_start(request: BacktestRequest, prices: pd.DataFrame) -> pd.Timestamp:
    if request.strategy_id == "psar_segment_duration" and request.revision == "r01":
        return pd.Timestamp(prices.index[0])
    if request.strategy_id == "tripod_nasdaq_leverage" and request.revision == "r01":
        return find_tripod_active_start(prices)
    if request.strategy_id == "sp500_top2_market_cap" and request.revision == "r01":
        return pd.Timestamp(prices.index[0])
    if request.strategy_id == "us_market_cap_leaders" and request.revision == "r01":
        return find_market_cap_leaders_active_start(prices)
    raise ValueError(f"No active-start resolver registered for {request.strategy_id}/{request.revision}")


def _write_manifest(
    path: str | Path,
    request: BacktestRequest,
    run_id: str,
    output_dir: Path,
    output_files: list[str],
) -> None:
    lines = [
        "# Latest Backtest Result",
        "",
        "status: success",
        f"request_id: {request.request_id}",
        f"strategy_id: {request.strategy_id}",
        f"revision: {request.revision}",
        f"mode: {request.mode}",
        f"run_id: {run_id}",
        "",
        "output_directory:",
        f"`{output_dir.as_posix()}/`",
        "",
        "default_outputs:",
    ]
    lines.extend(f"- `{name}`" for name in output_files)
    lines.extend(
        [
            "",
            "report_url: pending",
            "",
            "> 이 파일은 성과 수치를 복사해 두는 보고서가 아니라 최신 자동 실행의 output 위치와 파일명을 가리키는 manifest다.",
            "> LLM은 위 raw output을 직접 읽어 사용자에게 분석하며, analysis report는 사용자 요청 후 별도로 작성한다.",
            "",
        ]
    )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def execute_request(
    request_path: str | Path = "automation/backtest-request.json",
    runs_root: str | Path = "runs",
    result_path: str | Path = "automation/backtest-result.md",
) -> Path:
    request = load_request(request_path)
    key = (request.strategy_id, request.revision, request.mode)
    run_id = next_run_id(runs_root, request)
    output_dir = Path(runs_root) / request.strategy_id / request.revision / run_id
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing run directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    prices = _load_prices(request)
    if prices.empty:
        raise ValueError("No market data returned for request.")
    prices.to_csv(output_dir / "input_prices.csv", index=True, index_label="timestamp")

    active_start = _active_start(request, prices)
    settings = ExecutionSettings.from_env()
    runtime_config = RuntimeConfig(
        fee_rate=settings.fee_rate,
        slippage_bps=settings.slippage_bps,
    )
    runner = ALLOWED_RUNNERS[key]
    outputs = runner(prices, active_start, runtime_config)
    written = outputs.write_csv(output_dir)

    output_files = ["input_prices.csv", *sorted(path.name for path in written.values())]
    required_outputs = REQUIRED_OUTPUTS_BY_KEY[key]
    missing = [name for name in required_outputs if name not in output_files]
    if missing:
        raise RuntimeError(f"Required output files were not produced: {missing}")

    _write_manifest(result_path, request, run_id, output_dir, output_files)
    print(f"run_id={run_id}")
    print(f"output_directory={output_dir.as_posix()}")
    print(f"active_start={active_start.date()}")
    print(f"coverage_start={prices.index.min().date()}")
    print(f"coverage_end={prices.index.max().date()}")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request_path", nargs="?", default="automation/backtest-request.json")
    parser.add_argument("--runs-root", default="runs")
    parser.add_argument("--result-path", default="automation/backtest-result.md")
    args = parser.parse_args()
    execute_request(args.request_path, runs_root=args.runs_root, result_path=args.result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
