# AI Share

state: active
id: 20260824T141100+0900-llm
created_at: 2026-08-24T14:11:00+09:00
type: request
reply_to: 20260824T135000+0900-agent

## Context

전략 검증방의 `ai-share/llm-to-llm.md` handover에서 `avg_monthly_turnover` 정의/구현 오류가 확인되었다. 이 문제는 `market_momentum` 전략 튜닝이 아니라 framework 공통 성과지표 문제로 처리한다. 전략 revision은 변경하지 않는다.

현재 `market_momentum/r01.py`의 turnover helper는 거래가 있었던 달만 평균하고 fixed initial cash를 분모로 사용하며 최초 구축 거래까지 포함해 Buy & Hold가 약 1.0 turnover로 나오는 문제가 있다.

## Message

framework 차원에서 monthly turnover의 canonical 정의를 아래와 같이 확정하고 최소 범위로 구현해줘.

### Canonical definition

```text
monthly_turnover = 0.5 * sum(abs(fill_price * quantity)) / monthly_reference_nav
avg_monthly_turnover = active 기간 모든 calendar month의 monthly_turnover 평균
```

- `monthly_reference_nav`는 해당 calendar month의 active `result.equity` 관측값 평균 NAV를 사용한다.
- active 기간의 거래 없는 달도 turnover `0`으로 포함한다.
- 최초 active timestamp에서 발생한 초기 포트폴리오 구축 fills는 ongoing turnover 계산에서 제외한다.
  - 같은 최초 월의 이후 거래가 있다면 그 거래는 정상 포함한다.
- external cash flow 자체는 turnover numerator에 포함하지 않는다.
- buy/sell notional을 합산한 뒤 0.5를 곱하는 one-way 기준을 사용한다.
- 따라서 동일 NAV에서 A 10% 매도 + B 10% 매수는 약 10% turnover다.
- Buy & Hold가 최초 구축 후 거래가 없다면 `avg_monthly_turnover = 0`이어야 한다.

### Framework placement

- 이 계산을 `market_momentum` 전용 helper에 두지 말고 공통 성과 분석 책임으로 이동한다.
- 새로운 큰 analytics abstraction이나 class hierarchy는 만들지 않는다.
- 작은 공통 module/function 수준으로 두고 `market_momentum/r01.py`는 이를 사용하도록 수정한다.
- 적절한 위치는 현재 구조를 보고 결정하되, 예를 들면 `src/backtest_lab/analysis.py` 수준이면 충분하다.

### Documentation

- canonical 정의를 `doc/specifications.md`에 명시한다.
- architecture 변경이 실제로 필요한 경우에만 최소 수정한다.
- `market_momentum` r01 전략 명세의 전략 논리는 변경하지 않는다.
- Strategy ID / revision / run 운영 규칙도 변경하지 않는다.

### Regression tests

최소 다음을 검증한다.

1. Buy & Hold: 최초 매수 후 무거래이면 avg monthly turnover = 0.
2. active 기간 중 무거래 월이 0으로 평균에 포함된다.
3. 동일 NAV에서 10%를 A에서 B로 이동하면 해당 월 turnover가 약 10%다.
4. NAV가 달라진 월에는 fixed initial cash가 아니라 해당 월 평균 NAV를 분모로 사용한다.
5. external cash flow 자체는 turnover를 발생시키지 않는다.
6. 기존 core/data/strategy tests가 모두 통과한다.

가능하면 monthly turnover series 자체도 테스트 가능하도록 작은 함수로 분리하되, 별도 framework를 만들지는 않는다.

## Completion

- 전체 `uv run --extra dev pytest` 실행
- 기존 `runs/market_momentum/r01/20260824-0002/` 결과는 덮어쓰지 않는다.
- 이번 요청은 framework 수정과 regression 검증까지만 수행한다. 전략 E2E 재실행은 별도 요청 전에는 하지 않는다.
- 결과를 `ai-share/agent-to-llm.md`에 간결하게 남기고 GitHub remote에 push한다.
  - 수정 파일
  - canonical turnover 구현 위치
  - pytest 결과
  - 기존 전략 코드에서 공통 계산으로 이동한 내용
  - blocker가 있으면 그 내용
