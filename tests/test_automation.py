from __future__ import annotations

import json
from pathlib import Path

import pytest

from backtest_lab.automation import BacktestRequest, load_request, next_run_id


def test_load_request_accepts_registered_tripod_mode(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(
        json.dumps(
            {
                "request_id": "20260904T200000+0900",
                "strategy_id": "tripod_nasdaq_leverage",
                "revision": "r01",
                "mode": "baseline",
            }
        ),
        encoding="utf-8",
    )

    request = load_request(path)

    assert request.request_date == "20260904"
    assert request.start == "2009-01-01"
    assert request.end is None


def test_load_request_accepts_sp500_top2_fixed_period(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(
        json.dumps(
            {
                "request_id": "20260907T062000+0900",
                "strategy_id": "sp500_top2_market_cap",
                "revision": "r01",
                "mode": "baseline",
                "start": "2016-01-01",
                "end": "2026-01-01",
            }
        ),
        encoding="utf-8",
    )

    request = load_request(path)

    assert request.start == "2016-01-01"
    assert request.end == "2026-01-01"


def test_load_request_rejects_sp500_top2_wrong_period(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(
        json.dumps(
            {
                "request_id": "20260907T062000+0900",
                "strategy_id": "sp500_top2_market_cap",
                "revision": "r01",
                "mode": "baseline",
                "start": "2017-01-01",
                "end": "2026-01-01",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="fixed period"):
        load_request(path)


def test_load_request_rejects_unregistered_command_surface(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(
        json.dumps(
            {
                "request_id": "20260904T200000+0900",
                "strategy_id": "tripod_nasdaq_leverage",
                "revision": "r01",
                "mode": "shell:rm -rf /",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported backtest request"):
        load_request(path)


def test_request_id_must_contain_date() -> None:
    request = BacktestRequest(
        request_id="latest",
        strategy_id="tripod_nasdaq_leverage",
        revision="r01",
        mode="baseline",
    )

    with pytest.raises(ValueError, match="request_id"):
        _ = request.request_date


def test_next_run_id_uses_next_same_day_serial(tmp_path: Path) -> None:
    revision_dir = tmp_path / "tripod_nasdaq_leverage" / "r01"
    revision_dir.mkdir(parents=True)
    (revision_dir / "20260904-0001").mkdir()
    (revision_dir / "20260904-0003").mkdir()
    (revision_dir / "20260903-0099").mkdir()

    request = BacktestRequest(
        request_id="20260904T200000+0900",
        strategy_id="tripod_nasdaq_leverage",
        revision="r01",
        mode="sensitivity",
    )

    assert next_run_id(tmp_path, request) == "20260904-0004"
