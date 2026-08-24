# AGENTS.md

## Source of truth

개발 전 다음 문서를 우선 확인한다.

1. `doc/architecture.md`
2. `doc/specifications.md`
3. 관련 전략 작업이면 `doc/strategies/`의 해당 revision 명세
4. `ai-share/PROTOCOL.md`

현재 작업 요청은 `ai-share/llm-to-agent.md`에서 확인한다.

## Development principles

- Strategy는 자유로운 Python 코드로 유지한다. 고정 DSL을 만들지 않는다.
- Core 책임은 `Strategy -> Runtime -> Portfolio` 구조를 따른다.
- Runtime은 fills와 flow-adjusted performance series를 생성한다.
- Portfolio는 cash와 symbol별 aggregate position을 중심으로 현재 회계 상태를 관리한다.
- Lot은 core에 추가하지 않는다. 특수 전략 상태는 Strategy에서 필요에 따라 관리한다.
- fee/slippage는 단순 global/run-level 설정으로 유지한다.
- market data source는 Local MySQL, FinanceDataReader, Yahoo Finance를 지원하며 Strategy와 Runtime은 source-agnostic하게 유지한다.
- DB 접속 정보와 비밀값은 `.env`에서 읽고 repository에 commit하지 않는다.
- FFN은 performance analysis에 사용한다. Runtime/Portfolio accounting을 FFN에 맡기지 않는다.
- `bt`는 dependency가 아니라 설계 reference다.
- 흔한 요건을 단순하게 처리하고 실제 반복 요구가 없는 추상화는 추가하지 않는다.

## Strategy management

전략 명세는 `doc/strategies/YYYYMMDD-<strategy-name>-rNN.md`로 관리한다.

- 날짜는 해당 revision을 만든 날짜다.
- 명세에는 `Strategy ID`와 `Revision`을 명시한다.
- revision을 올릴지는 사용자가 결정한다. Agent/LLM이 임의로 revision을 증가시키지 않는다.
- 새 revision이 생겨도 이전 명세와 구현은 유지한다.
- 구현 수정 이력은 Git이 담당한다.

실제 전략 소스는 다음 경로를 사용한다.

```text
src/backtest_lab/strategies/<strategy_id>/<revision>.py
```

예:

```text
src/backtest_lab/strategies/market_momentum/r01.py
```

각 revision module에는 최소한 다음 식별값을 둔다.

```python
STRATEGY_ID = "market_momentum"
REVISION = "r01"
```

revision 전략은 명시적으로 import한다.

```python
from backtest_lab.strategies.market_momentum.r01 import MarketMomentumStrategy
```

`strategies/<strategy_id>/__init__.py`에서 특정 revision을 latest/default처럼 재-export하지 않는다.

공통 재사용 전략은 기능 이름의 module로 분리한다. 예: `strategies/target_weight.py`. 기존 public import가 있으면 `strategies/__init__.py`에서 re-export해 호환성을 유지한다.

전략 revision 테스트는 다음 경로를 사용한다.

```text
tests/strategies/<strategy_id>/test_<revision>.py
```

별도 Strategy registry/manager는 실제 필요가 생기기 전까지 두지 않는다.

## Implementation discipline

- 구현은 작고 추적 가능하게 유지한다.
- Strategy 판단, Runtime execution, Fill, Portfolio 변경의 경계가 코드에서 명확해야 한다.
- 동일 입력과 설정은 동일 결과를 만들어야 한다.
- core 테스트는 `doc/specifications.md`, 전략 테스트는 해당 revision 명세의 acceptance/test scenarios를 기준으로 한다.
- 설계 결정을 바꿔야 할 필요가 생기면 임의로 확대 구현하지 말고 blocker/question으로 공유한다.

## AI Share

ChatGPT와 Codex 간 메시지 및 세션 handover에는 `./ai-share/PROTOCOL.md`를 따른다.

작업 결과는 `agent-to-llm.md`에 최소한으로 정리하고 GitHub remote에 commit/push한 뒤 완료로 간주한다.
