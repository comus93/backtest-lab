# AI Share

state: active
id: 20260901T181000+0900-llm
created_at: 2026-09-01T18:10:00+09:00
type: request
reply_to: none

## Context

LLM이 신규 전략 `weekly_trend` r01의 명세, 구현, synthetic pytest, E2E runner를 main에 반영했다. 기존 `market_momentum`의 새 revision이 아니라 별도 전략이다.

## Message

`AGENTS.md`와 `doc/strategies/20260901-weekly-trend-r01.md`를 기준으로 구현을 검증하고 첫 E2E run을 생성해줘.

### Verification

1. 우선 targeted test 실행:
   - `tests/strategies/weekly_trend/test_r01.py`
2. 신규 코드가 공통/core 동작에 영향을 줄 가능성이 발견될 때만 필요한 회귀 범위로 확대한다.
3. 실패 시 명세 의미를 바꾸지 않는 구현 버그는 수정하고 targeted test를 재실행한다.
4. 전략 의미나 core 변경이 필요하면 임의 확대하지 말고 blocker로 회신한다.

### E2E baseline

- Strategy: `weekly_trend` r01
- Universe: `SPY, QQQ, DIA, EWJ, EWY, MCHI, DAX, EWW, EIDO, INDY, EPHE`
- Source: Yahoo Finance adjusted close
- data load start: `2016-06-01`
- active period: `2016-07-01 ~ 2026-07-31`
- `move_threshold = 0`
- exposure: `1/N`
- fee/slippage: project default
- 기존 run은 덮어쓰지 않는다.
- 운영 규칙에 따라 `runs/weekly_trend/r01/20260901-0001/`을 첫 run으로 사용한다. 이미 존재하면 다음 serial을 사용한다.

Expected outputs:

- `performance_summary.csv`
- `equity_curves.csv`
- `weekly_decisions.csv`
- `exposure.csv`

### Result report

완료 후 `ai-share/agent-to-llm.md`에 아래만 간결하게 남기고 GitHub remote에 push해줘.

- 수정 파일이 있다면 목록과 이유
- pytest 결과
- E2E run id
- 실제 data coverage / active period
- 4개 output 생성 여부
- Weekly Trend의 CAGR, MDD, avg_exposure, avg_monthly_turnover
- 평균 cash weight와 active position 수의 대략적 수준
- blocker/data constraint
