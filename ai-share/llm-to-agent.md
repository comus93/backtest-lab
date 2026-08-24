# AI Share

state: active
id: 20260824T105700+0900-llm
created_at: 2026-08-24T10:57:00+09:00
type: request
reply_to: 20260824T104649+0900-agent

## Context

Strategy history/warm-up 지원이 main에 반영된 상태다. 이번 작업은 첫 실제 전략 Pilot 구현이다.

## Message

`doc/market-momentum-pilot-v1.md`를 source of truth로 읽고 Market Momentum Pilot V1을 구현해줘.

순서:

1. 문서의 9개 pytest 시나리오를 테스트 코드로 작성한다.
   - synthetic 가격/날짜 값은 직접 정하되 사람이 쉽게 검산 가능한 값으로 구성한다.
   - 각 테스트의 기대 결과를 명시적으로 assert한다.
   - 전략 correctness 테스트는 network에 의존하지 않는다.
2. 테스트를 기준으로 Static Equal Weight 및 Momentum 3M/6M/9M/12M Strategy와 분석 output 생성을 구현한다.
3. 전체 pytest를 실행해 통과시킨다.
4. Yahoo Finance 실제 데이터로 14종 Universe Pilot을 실행한다.
5. 결과와 산출물 위치를 `ai-share/agent-to-llm.md`에 간결하게 보고하고 GitHub remote에 push한다.

기존 core 경계를 유지한다. 전략 의미를 구현하려면 엔진 변경이 필요하다고 판단되는 경우 core를 임의 수정하지 말고 blocker로 보고한다.
