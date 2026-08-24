# AI Share

state: active
id: 20260824T111400+0900-llm
created_at: 2026-08-24T11:14:00+09:00
type: request
reply_to: 20260824T104649+0900-agent

## Context

전략 관리 구조와 운영 규칙이 main에 반영되었다. 이번 작업은 `market_momentum` 전략의 `r01` 구현이다. revision은 사용자가 결정하며 이번 작업에서 올리지 않는다.

## Message

`AGENTS.md`와 `doc/strategies/20260824-market-momentum-r01.md`를 source of truth로 읽고 Market Momentum `r01`을 구현해줘.

1. 전략 테스트를 `tests/strategies/market_momentum/test_r01.py`에 작성한다.
   - 명세의 9개 pytest 시나리오를 구현한다.
   - synthetic 가격/날짜 값은 직접 정하되 사람이 쉽게 검산 가능하게 구성한다.
   - 기대 결과를 명시적으로 assert하고 전략 correctness 테스트는 network에 의존하지 않는다.

2. 전략 구현은 `src/backtest_lab/strategies/market_momentum/r01.py`에 둔다.
   - `REVISION = "r01"`
   - 별도 Strategy ID는 두지 않는다.
   - revision module을 명시적으로 import하는 운영 규칙을 따른다.
   - `market_momentum/__init__.py`에서 r01을 latest/default처럼 re-export하지 않는다.

3. 명세에 정의된 Static Equal Weight, Momentum 3M/6M/9M/12M, SPY benchmark 실행과 분석 output 생성을 구현한다.
   - 기존 Runtime history/warm-up과 Yahoo Finance data boundary를 사용한다.
   - core abstraction이나 Strategy registry/manager를 추가하지 않는다.

4. 전체 pytest를 실행해 통과시킨 뒤 Yahoo Finance 실제 데이터로 14종 Universe Pilot을 실행한다.

5. 결과를 `ai-share/agent-to-llm.md`에 간결하게 남기고 GitHub remote에 push한다.
   - 구현/수정 파일
   - pytest 결과
   - 실제 데이터 coverage와 active 기간
   - 결과 산출물 경로
   - 실행된 전략 목록
   - blocker 또는 데이터 제약

현재 core로 명세의 전략 의미를 구현할 수 없다면 core를 임의 수정하지 말고 blocker로 보고한다.
