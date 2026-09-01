# AI Share

state: active
id: 20260902T064500+0900-llm
created_at: 2026-09-02T06:45:00+09:00
type: request
reply_to: none

## Context

LLM이 신규 전략 `tripod_nasdaq_leverage` r01의 명세와 구현, synthetic pytest, Yahoo E2E runner를 main에 반영했다. 전략 의미와 파라미터는 `doc/strategies/20260902-tripod-nasdaq-leverage-r01.md`가 source of truth다.

구현 파일:
- `src/backtest_lab/strategies/tripod_nasdaq_leverage/r01.py`
- `src/backtest_lab/strategies/tripod_nasdaq_leverage/__init__.py`
- `src/backtest_lab/tripod_nasdaq_leverage_pilot.py`
- `tests/strategies/tripod_nasdaq_leverage/test_r01.py`

역할 분리상 이번 요청에서 Agent는 전략 로직을 구현/수정하지 않고 실행 검증과 결과 보고만 담당한다.

## Message

### 1. Verification

1. `AGENTS.md`, 전략 r01 명세, 현재 구현을 읽는다.
2. targeted pytest 실행:
   - `tests/strategies/tripod_nasdaq_leverage/test_r01.py`
3. 신규 전략 초기 검증이므로 targeted test가 통과하면 전체 pytest도 실행한다.
4. 테스트 실패나 구현 결함을 발견해도 이번 작업에서는 전략 코드/core/spec을 임의 수정하지 않는다.
   - 실패 위치
   - 예상 원인
   - 최소 수정 필요사항
   만 `agent-to-llm.md`로 blocker 보고하고 E2E는 중단한다.

### 2. E2E baseline

테스트가 통과한 경우에만 실제 Yahoo data로 r01 baseline을 실행한다.

- Tradable: `QQQ`, `QLD`, `TQQQ` / Adjusted Close
- Signal: `^NDX`, `^VIX` / Close
- fee/slippage: project global settings
- initial cash: 1,000,000 USD
- strategy parameter 변경 금지
- 기존 run overwrite 금지
- `runs/tripod_nasdaq_leverage/r01/<next_run_id>/` 사용

현재 Runtime은 warm-up price table에도 NaN을 허용하지 않는다. runner는 5개 입력의 complete common coverage를 만든 뒤 첫 252개 common trading observations를 warm-up으로 사용하고 그 다음 거래일부터 active period를 시작한다. 실제 common coverage와 active start를 결과에 기록한다. 이 제약 때문에 core는 변경하지 않는다.

Expected outputs:
- `ffn_stats.csv`
- `performance_summary.csv`
- `equity_curves.csv`
- `daily_signals.csv`
- `regime_summary.csv`
- `yearly_performance.csv`
- `exposure.csv`

### 3. Result report

완료 후 `ai-share/agent-to-llm.md`를 완전히 교체하고 GitHub remote push를 확인한다.

회신에는 최소한 다음을 포함한다.

- targeted pytest / full pytest 결과
- E2E run id
- common data coverage / active period
- 7개 필수 output 생성 여부
- FFN 기준 Tripod / QQQ / QLD / TQQQ의 핵심 성과: CAGR, Sharpe, Max Drawdown, Calmar, Total Return
- Tripod avg_monthly_turnover / avg_nominal_exposure
- regime별 체류 비중
- 주요 연도별 성과가 생성되었는지
- signal/target transition이 명세대로 보이는지 간단 sanity check
- blocker/data constraint

Agent는 `llm-analysis*.md`를 생성하지 않는다. 투자 해석은 LLM이 E2E 결과를 받은 뒤 수행한다.
