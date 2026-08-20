# AI Share

state: active
id: 20260820T101600+0900-llm
created_at: 2026-08-20T10:16:00+09:00
type: request
reply_to: none

## Context

설계 검토가 끝났고 v1 구현을 시작한다.

Source of truth:

- `AGENTS.md`
- `doc/architecture.md`
- `doc/specifications.md`

## Message

위 문서를 읽고 v1을 구현해줘.

첫 구현의 end-to-end 검증 대상은 `doc/specifications.md`의 Sample Strategy다.

- KODEX 미국S&P500 70%
- ACE KRX 금현물 30%
- Initial Deposit 10,000,000 KRW
- Monthly rebalancing
- 2021-01-01 ~ 2026-08-01
- Local MySQL market data 사용
- DB 접속 정보는 로컬 `.env` 사용
- fee/slippage는 v1 global settings 사용

특히 다음 설계 경계를 유지해줘.

- Strategy -> Runtime -> Portfolio
- Runtime outputs: fills, flow-adjusted performance series
- performance series는 pre-start reference point 100을 포함하고 FFN에 직접 연결
- Portfolio는 aggregate position 기반
- Lot core 도입 금지
- 고정 Strategy DSL 금지
- 별도 FeeModel/SlippageModel hierarchy 금지
- `bt` dependency 도입 금지

DB schema와 실제 ticker 저장값은 로컬 환경에서 확인해서 연결하되, 확인할 수 없는 값을 임의로 추측하지 말 것.

`doc/specifications.md`의 acceptance checks를 테스트로 검증해줘.

작업 완료 후 `ai-share/PROTOCOL.md`에 따라 `agent-to-llm.md`에 다음만 간결하게 남기고 GitHub에 push해줘.

- 구현 요약
- 주요 파일
- 테스트 결과
- Sample Strategy 실행 결과 또는 실행 blocker
- 추가 판단이 필요한 사항
