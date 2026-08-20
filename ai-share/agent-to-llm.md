# AI Share

state: active
id: 20260820T103158+0900-agent
created_at: 2026-08-20T10:31:58+09:00
type: result
reply_to: 20260820T101600+0900-llm

## Context

v1 구현 요청에 대한 Codex 결과다.

## Message

구현 요약:

- `Strategy -> Runtime -> Portfolio` 경계를 유지한 v1 core를 추가했다.
- Runtime은 immediate Fill, fee/slippage, aggregate position, external cash flow, pre-start reference point 100, flow-adjusted performance series를 처리한다.
- Local MySQL `global_price` 조회 loader와 Sample 70/30 monthly rebalancing strategy를 추가했다.
- `bt` dependency, Lot core, FeeModel/SlippageModel hierarchy, 고정 Strategy DSL은 도입하지 않았다.

주요 파일:

- `src/backtest_lab/core.py`
- `src/backtest_lab/data.py`
- `src/backtest_lab/strategies.py`
- `src/backtest_lab/sample.py`
- `tests/test_core.py`
- `pyproject.toml`

테스트 결과:

- `uv run --extra dev pytest`
- 결과: 7 passed

Sample Strategy 실행 결과 또는 blocker:

- 확인된 DB symbol: KODEX 미국S&P500 = `379800`, ACE KRX 금현물 = `411060`
- 엄격 실행 `uv run python -m backtest_lab.sample` 결과 blocker:
  - `379800`: available 2021-04-09 to 2025-06-25, requested 2021-01-01 to 2026-08-01
  - `411060`: available 2021-12-15 to 2025-11-03, requested 2021-01-01 to 2026-08-01
- 추측/보간 없이 `--allow-partial` smoke 실행:
  - rows: 862
  - period: 2021-12-15 to 2025-06-25
  - fills: 86
  - final_equity: 17280388.80
  - final_performance: 172.803888

추가 판단이 필요한 사항:

- 요청 기간 전체를 검증하려면 Local DB에 두 symbol의 2021-01-01 ~ 2026-08-01 가격 coverage가 필요하다.
