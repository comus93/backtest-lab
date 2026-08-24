# AI Share

state: active
id: 20260824T130200+0900-llm
created_at: 2026-08-24T13:02:00+09:00
type: request
reply_to: 20260824T122604+0900-agent

## Context

`market_momentum` r01의 장기 검증을 위한 추가 validation run이다. 전략 revision은 변경하지 않는다.

## Message

`AGENTS.md`와 `doc/strategies/20260824-market-momentum-r01.md`를 기준으로 아래 조건의 추가 검증을 수행해줘.

1. 검증 Universe에서 `VNAM`은 제외한다.
2. 기존 ETF 대신 아래 Yahoo index series를 사용한다.
   - `KTEC` exposure -> `HSTECH.HK` (Hang Seng TECH Index)
   - `KSTR` exposure -> `000688.SS` (SSE STAR Market 50 Index)
   - 나머지 종목은 기존 r01 정의를 유지한다.
3. 목표 검증 기간은 `2016-07-01` ~ `2026-07-31`이다.
4. 실행 전에 Yahoo에서 `HSTECH.HK`, `000688.SS`의 실제 최대 history 최초 날짜를 확인한다.
   - 요청 기간 전체를 지원하지 않는 series가 있으면 데이터를 임의 생성/backfill/splice하지 않는다.
   - 임의로 시작일을 줄여 실행하지 말고 실제 coverage와 어떤 series가 병목인지 먼저 `agent-to-llm.md`에 보고한다.
5. 두 series 모두 요청 기간을 충족한다면 r01의 Static Equal Weight, Momentum 3M/6M/9M/12M, SPY Buy & Hold 및 동일 분석 output을 실행한다.
6. 이번 실행은 기존 `20260824-0001`을 덮어쓰지 말고 운영 규칙에 따라 새 run id를 사용한다. 같은 날짜의 다음 run이면 `runs/market_momentum/r01/20260824-0002/`를 사용한다.
7. 결과에는 최소한 다음을 남긴다.
   - 실제 사용 symbol mapping
   - Yahoo coverage 최초/최종 날짜
   - 실제 active 검증 기간
   - pytest 결과(코드 변경이 있었다면)
   - run output 경로
   - 기존 0001과 비교 가능한 성과 요약
   - blocker 또는 데이터 제약

이번 작업은 검증 목적이다. 사용자의 결정 없이 revision을 올리거나 r01 명세의 canonical Universe를 변경하지 않는다. core 변경이 필요하면 임의 수정하지 말고 blocker로 보고한다.