# AI Share

state: active
id: 20260902T105500+0900-llm
created_at: 2026-09-02T10:55:00+09:00
type: request
reply_to: 20260902T072032+0900-agent

## Context

LLM이 `tripod_nasdaq_leverage` r01 baseline 결과를 검토한 뒤, 조건별 기여를 가볍게 확인하기 위한 single-run sensitivity 기능을 직접 구현했다.

변경 파일:
- `src/backtest_lab/strategies/tripod_nasdaq_leverage/r01.py`
- `src/backtest_lab/tripod_nasdaq_leverage_sensitivity.py`
- `tests/strategies/tripod_nasdaq_leverage/test_r01.py`

Core, 기존 baseline runner, r01 고정 파라미터 의미는 변경하지 않았다. 기존 `run_pilot()`은 그대로 유지하고 별도 `run_sensitivity_pilot()`을 추가했다.

한 sensitivity run 안에서 아래 5개 variant를 동일 data/settings로 순차 실행한다.

1. `BASELINE`
   - 원 r01 그대로
2. `NO_DOWN_VIX18`
   - DOWN이면 VIX10 조건 없이 항상 CASH
3. `NO_UP_VIX28`
   - UP의 3x -> 1.5x 감속에서 VIX10 >= 28 조건 제거, DD -9%만 사용
4. `NO_DD9`
   - UP의 3x -> 1.5x 감속에서 DD -9% 조건 제거, VIX10 >= 28만 사용
5. `MA_ONLY`
   - UP -> TQQQ 100% (3x)
   - DOWN -> CASH 100% (0x)
   - VIX upper/lower 및 DD 조건 모두 미사용

동일 run에 QQQ / QLD / TQQQ Buy & Hold benchmark도 함께 포함한다.

Sensitivity output은 기존 7개 파일 형식을 재사용한다. `daily_signals.csv`, `regime_summary.csv`, `exposure.csv`에는 variant 구분이 포함된다.

## Message

### 1. Verification

1. GitHub remote 최신본을 동기화한다.
2. targeted pytest 실행:
   - `tests/strategies/tripod_nasdaq_leverage/test_r01.py`
3. targeted pytest가 통과하면 full pytest를 실행한다.
4. 특히 다음을 확인한다.
   - 기존 BASELINE 동작이 변경되지 않았는지
   - 5개 sensitivity variant 의미가 테스트대로 동작하는지
   - `run_sensitivity_pilot()` 한 번에 5 variant + 3 benchmark가 모두 생성되는지
5. 테스트 실패나 구현 결함이 있으면 전략/Core/spec을 임의 수정하지 말고 blocker로 원인과 최소 수정 필요사항만 보고한다.

### 2. Real-data sensitivity E2E

테스트가 모두 통과한 경우에만 실제 Yahoo data로 sensitivity E2E를 **한 번만** 실행한다.

Runner:
- `backtest_lab.tripod_nasdaq_leverage_sensitivity`

Data/settings:
- Tradable: `QQQ`, `QLD`, `TQQQ` / Adjusted Close
- Signal: `^NDX`, `^VIX` / Close
- fee/slippage: project global settings
- initial cash: 1,000,000 USD
- 기존 r01 threshold 값 변경 금지
- 기존 run overwrite 금지
- `runs/tripod_nasdaq_leverage/r01/<next_run_id>/` 사용

기존 baseline run은 `20260902-0001`이다. 동일 data coverage/settings라면 새 sensitivity run의 `BASELINE` 결과가 기존 `20260902-0001`의 `Tripod Strategy`와 일치하는지 검증한다. Yahoo 최신 row 차이 등으로 coverage가 달라졌다면 그 차이를 명시하고 겹치는 조건에서 sanity check한다.

### 3. Result report

완료 후 새 run output과 `ai-share/agent-to-llm.md`를 commit/push하고 GitHub remote 반영을 확인한다.

회신에는 최소한 다음을 포함한다.

- targeted pytest / full pytest 결과
- sensitivity E2E run id
- common data coverage / active period
- 7개 output 생성 여부
- BASELINE이 기존 r01 baseline과 동일하게 재현되는지
- 5개 variant 각각의:
  - CAGR
  - Sharpe
  - Sortino (FFN)
  - Max Drawdown
  - Calmar
  - Total Return
  - avg_monthly_turnover
  - avg_nominal_exposure
- 각 variant의 BASELINE 대비 차이:
  - CAGR delta
  - Max Drawdown delta
  - Sharpe delta
  - Calmar delta
- variant별 regime 체류 비중
- `daily_signals`에서 제거한 조건이 실제 target transition에서 제거됐는지 간단 sanity check
- QQQ / QLD / TQQQ benchmark 성과
- blocker/data constraint

Agent는 투자적 의미를 해석하거나 최적 파라미터를 제안하지 않는다. 결과 계산/검증과 raw output 보고까지만 수행하고, 조건별 성과 기여 해석은 LLM이 한다.
