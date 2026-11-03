from __future__ import annotations

import json
from pathlib import Path

import pytest

from backtest_lab.automation import BacktestRequest, load_request, next_run_id


def test_load_request_accepts_psar_long_only_mode(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(
        json.dumps({
            "request_id": "20261103T200000+0900",
            "strategy_id": "psar_segment_duration",
            "revision": "r01",
            "mode": "long_only",
            "start": "2007-01-01",
            "end": "2026-11-04",
        }), encoding="utf-8",
    )
    request = load_request(path)
    assert (request.strategy_id, request.revision, request.mode) == (
        "psar_segment_duration", "r01", "long_only",
    )


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


def test_load_request_accepts_market_cap_leaders_modes(tmp_path: Path) -> None:
    for mode in ("baseline", "window_sensitivity"):
        path = tmp_path / f"{mode}.json"
        path.write_text(
            json.dumps(
                {
                    "request_id": "20260908T091500+0900",
                    "strategy_id": "us_market_cap_leaders",
                    "revision": "r01",
                    "mode": mode,
                    "start": "2010-03-31",
                    "end": "2026-07-01",
                }
            ),
            encoding="utf-8",
        )

        request = load_request(path)

        assert request.start == "2010-03-31"
        assert request.end == "2026-07-01"
        assert request.mode == mode


def test_load_request_rejects_market_cap_leaders_wrong_period(tmp_path: Path) -> None:
    path = tmp_path / "request.json"
    path.write_text(
        json.dumps(
            {
                "request_id": "20260908T091500+0900",
                "strategy_id": "us_market_cap_leaders",
                "revision": "r01",
                "mode": "baseline",
                "start": "2011-01-01",
                "end": "2026-07-01",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="fixed price coverage"):
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
