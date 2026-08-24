# Session Handover

created_at: 2026-08-24T14:09:00+09:00

## Current State

전략 검증방에서 `market_momentum` r01의 10년 E2E run(`runs/market_momentum/r01/20260824-0002/`)을 검토하던 중 `avg_monthly_turnover` 계산이 잘못 정의되어 있음을 확인했다.

현재 `src/backtest_lab/strategies/market_momentum/r01.py`의 `_average_monthly_turnover(result)`는:

- fill notional `abs(fill_price * quantity)`을 체결이 있었던 달별로 합산
- 체결이 있었던 달만 평균
- 항상 최초자금 `1_000_000`으로 나눔

하는 방식이다.

그 결과 SPY Buy & Hold의 `avg_monthly_turnover`가 약 `0.99985`로 출력된다. 이는 ongoing monthly turnover 의미와 맞지 않는다.

## Framework Issue

이 문제는 market_momentum 전략 튜닝이 아니라 framework 공통 성과지표 정의 문제로 처리한다.

현재 문제점:

1. 거래가 없는 달이 평균에서 빠진다.
2. 분모가 해당 시점 Portfolio NAV가 아니라 고정 initial cash다.
3. 최초 포트폴리오 구성 거래가 ongoing turnover를 지배한다.
4. 매도+매수를 단순 합산하면 일반적인 one-way turnover보다 이중 계상될 수 있다.
5. `avg_monthly_turnover`의 공식 정의가 `doc/specifications.md`에 없다.

## Requested Change

framework 차원에서 `avg_monthly_turnover`의 canonical 정의를 정하고 구현을 수정해줘.

권장 의미는 **초기 포트폴리오 구성 이후의 평균 월간 one-way turnover**다.

권장 계산 개념:

```text
monthly_turnover = 0.5 * sum(abs(trade_notional)) / reference_nav
avg_monthly_turnover = active 기간의 월별 turnover 평균
```

요구사항:

- active 기간의 거래 없는 달도 turnover `0`으로 포함한다.
- 분모는 고정 initial cash가 아니라 해당 월의 적절한 Portfolio NAV를 사용한다.
- 최초 포트폴리오 구축 거래는 ongoing turnover 평균에서 제외하거나 별도 initial turnover로 분리한다.
- Buy & Hold는 최초 구축 이후 거래가 없다면 `avg_monthly_turnover = 0`이 되어야 한다.
- 완전한 A→B 교체는 대략 100% turnover로 해석되는 one-way 기준을 사용한다.
- external cash flow 자체는 turnover로 계산하지 않는다.
- 정의를 적절한 framework 문서에 명시하고 regression test를 추가한다.
- 이 지표가 market_momentum 전용 helper에 머무는 것이 적절한지도 검토하고, 공통 성과 분석 책임으로 옮길 실제 필요가 있다면 최소 범위에서 정리한다.

## Acceptance Checks

최소한 다음을 검증한다.

1. Buy & Hold: 최초 매수 후 무거래이면 avg monthly turnover = 0.
2. 무거래 월이 평균에 0으로 포함된다.
3. 동일 NAV에서 10%를 A에서 B로 이동하면 월 turnover가 약 10%로 계산된다.
4. NAV가 달라져도 fixed initial cash가 아니라 해당 시점 NAV 기준으로 계산된다.
5. 기존 core/strategy tests가 모두 통과한다.

## Important Constraint

전략 검증 자체의 추가 분석(output 확장, 12M momentum 평가 등)은 별도 전략 검증방에서 계속한다. 이번 handover에서는 turnover framework 문제만 먼저 수정 대상으로 삼는다.

framework 수정 방향을 정한 뒤 Codex 구현 요청이 필요하면 기존 `ai-share/PROTOCOL.md`에 따라 `llm-to-agent.md`로 전달한다.
