# AGENTS.md

## Source of truth

개발 전 다음 문서를 우선 확인한다.

1. `doc/architecture.md`
2. `doc/specifications.md`
3. `ai-share/PROTOCOL.md`

현재 작업 요청은 `ai-share/llm-to-agent.md`에서 확인한다.

## Development principles

- Strategy는 자유로운 Python 코드로 유지한다. 고정 DSL을 만들지 않는다.
- Core 책임은 `Strategy -> Runtime -> Portfolio` 구조를 따른다.
- Runtime은 fills와 flow-adjusted performance series를 생성한다.
- Portfolio는 cash와 symbol별 aggregate position을 중심으로 현재 회계 상태를 관리한다.
- Lot은 core에 추가하지 않는다. 특수 전략 상태는 Strategy에서 필요에 따라 관리한다.
- fee/slippage는 v1에서 전역 설정으로 유지하고 불필요한 model/object hierarchy를 만들지 않는다.
- market data는 v1에서 Local MySQL을 사용하지만 DB 접근과 Runtime core는 분리한다.
- DB 접속 정보와 비밀값은 `.env`에서 읽고 repository에 commit하지 않는다.
- FFN은 performance analysis에 사용한다. Runtime/Portfolio accounting을 FFN에 맡기지 않는다.
- `bt`는 dependency가 아니라 설계 reference다.
- 흔한 요건을 단순하게 처리하는 것을 우선하고, 특수 요건 하나 때문에 core를 일반화하지 않는다.
- 합의되지 않은 추상화나 기능을 선제적으로 추가하지 않는다.

## Implementation discipline

- 구현은 작고 추적 가능하게 유지한다.
- Strategy 판단, Runtime execution, Fill, Portfolio 변경의 경계가 코드에서 명확해야 한다.
- 동일 입력과 설정은 동일 결과를 만들어야 한다.
- 테스트는 `doc/specifications.md`의 acceptance checks를 기준으로 한다.
- 설계 결정을 바꿔야 할 필요가 생기면 임의로 확대 구현하지 말고 blocker/question으로 공유한다.

## AI Share

ChatGPT와 Codex 간 메시지 및 세션 handover에는 `./ai-share/PROTOCOL.md`를 따른다.

작업 결과는 `agent-to-llm.md`에 최소한으로 정리하고 GitHub remote에 commit/push한 뒤 완료로 간주한다.
