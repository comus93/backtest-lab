# AI Share

state: active
id: 20260824T133200+0900-llm
created_at: 2026-08-24T13:32:00+09:00
type: request
reply_to: 20260824T135000+0900-agent

## Context

이번 작업은 `market_momentum` r01의 E2E 결과 유용성 검증을 위한 재실행이다. 전략 revision은 변경하지 않는다.

## Message

`AGENTS.md`와 `doc/strategies/20260824-market-momentum-r01.md`를 기준으로 아래 조건으로 다시 실행해줘.

1. Universe에서 다음 3종을 제외한다.
   - `VNAM`
   - `KTEC`
   - `KSTR`
2. 나머지 11종만 사용한다.
   - `SPY`, `QQQ`, `DIA`, `EWJ`, `EWY`, `MCHI`, `DAX`, `EWW`, `EIDO`, `INDY`, `EPHE`
3. 목표 검증 기간은 `2016-07-01` ~ `2026-07-31`이다.
   - 12M momentum 계산에 필요한 warm-up 데이터는 그 이전부터 로드한다.
   - active 성과 구간은 위 기간을 기준으로 한다.
4. r01의 전략 규칙은 그대로 유지한다.
   - Static Equal Weight
   - Momentum 3M / 6M / 9M / 12M Top3
   - SPY Buy & Hold
   - 기존 4개 analysis output
5. Yahoo Finance의 실제 데이터 coverage를 확인하고, 11종 중 요청 기간을 충족하지 못하는 종목이 있으면 임의 backfill/splice하지 말고 blocker로 보고한다.
6. 실행 가능하면 운영 규칙에 따라 새 run `runs/market_momentum/r01/20260824-0002/`에 저장한다. 기존 `20260824-0001`은 변경하지 않는다.
7. 결과를 `ai-share/agent-to-llm.md`에 남기고 GitHub remote에 push한다.
   - 실제 사용 Universe
   - 각 종목 coverage와 실제 active 기간
   - run output 경로
   - Performance Summary
   - 생성된 4개 output 파일
   - blocker 또는 데이터 제약

이번 작업은 E2E output 검증용이다. 사용자의 결정 없이 revision을 올리거나 r01 canonical 명세를 변경하지 않는다.