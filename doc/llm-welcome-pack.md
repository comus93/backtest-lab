# Strategy Welcome Pack for LLM

이 문서는 새로운 ChatGPT 대화창에서 `backtest-lab`을 이용한 **신규 전략 연구·구현·검증을 바로 시작하기 위한 onboarding 문서**다.

이 문서는 새로운 규칙의 source of truth가 아니다. 내용이 다른 프로젝트 문서와 충돌하면 다음 문서를 우선한다.

1. `AGENTS.md`
2. `doc/architecture.md`
3. `doc/specifications.md`
4. 해당 전략 revision 명세
5. `ai-share/PROTOCOL.md`

## 1. 이 대화창의 역할

신규 전략 대화창은 다음 흐름을 담당한다.

```text
전략 아이디어
→ 투자 논리와 가설 정의
→ 전략 규칙 명세
→ Codex 구현 요청
→ 백테스트 실행
→ 결과 검증
→ 해석 및 다음 실험 설계
```

엔진 자체의 유지보수·공통 framework 설계는 별도의 엔진 대화창에서 담당한다.

전략방과 엔진방은 직접 통신한다고 가정하지 않는다. 공통 framework 변경이 필요하면 사용자에게 필요한 내용을 정리해 전달하고, 사용자가 두 대화창 사이를 중재한다.

## 2. 시작할 때 먼저 이해할 것

`backtest-lab`의 기본 구조는 다음과 같다.

```text
Market Data
    ↓
Strategy
    ↓
Runtime
    ↓
Portfolio

Runtime
 ├─ fills
 └─ performance series
          ↓
         FFN
```

핵심 책임:

- **Strategy**: 투자 판단, signal, 자산 선택, 목표 비중, 리밸런싱 조건, 전략 자체 상태
- **Runtime**: 시간 진행, 현재 시점까지의 history 제공, 주문 처리, execution, fee/slippage, Fill, external cash flow, performance series
- **Portfolio**: cash, symbol별 aggregate position, valuation
- **Data boundary**: Local MySQL / FinanceDataReader / Yahoo Finance를 normalized DataFrame으로 제공
- **Analysis**: 공통 성과 분석. 예: canonical monthly turnover
- **FFN**: 기본 성과 측정 및 리포팅. Runtime이 만든 performance series를 입력으로 사용한다.

Strategy는 Portfolio를 직접 수정하거나 fee/slippage를 계산하지 않는다.

## 3. 현재 엔진이 Strategy에 제공하는 것

Strategy는 `StrategyContext`를 통해 현재 step의 정보와 **현재 timestamp까지의 과거 가격 history**를 받을 수 있다.

중요 원칙:

- `history`에는 미래 row가 포함되지 않는다.
- `run(..., start=...)`를 사용하면 `start` 이전 데이터는 warm-up history로 사용할 수 있다.
- warm-up 구간에는 주문, fills, Portfolio valuation, performance가 발생하지 않는다.
- Strategy가 직접 DB/FDR/Yahoo를 호출해서 history를 수집하지 않는다.

따라서 moving average, momentum, regime 등 과거 가격이 필요한 전략은 우선 현재 `StrategyContext.history`로 표현 가능한지 검토한다.

## 4. 신규 전략 설계 순서

전략 아이디어를 바로 코드로 보내지 말고 먼저 아래를 User와 합의한다.

### 투자 가설

- 무엇을 이용해 수익 또는 분산 효과를 얻으려는가?
- 왜 이 효과가 존재한다고 보는가?
- 어떤 조건에서 실패할 수 있는가?

### Universe / Data

- 대상 자산
- data source
- 사용 price field
- currency
- 필요한 warm-up 길이
- 검증 기간
- data coverage 제약

### Signal

- 계산식
- 관찰 시점
- 필요한 lookback
- ranking / threshold / tie-break
- look-ahead 방지 기준

### Execution / Portfolio

- signal date와 execution date
- 현재 step 가격 체결인지 다음 거래일 체결인지
- 목표 비중 또는 주문 수량
- rebalance 주기
- cash 처리
- fee / slippage

### Validation

- benchmark
- FFN 기본 성과 리포트
- 전략 논리를 검증할 추가 분석
- synthetic pytest 시나리오
- 실제 데이터 E2E run

기본 성과 측정은 Runtime이 생성한 performance series를 **FFN으로 분석**한다. 별도 이유가 없는 한 FFN이 기본 제공하는 성과 척도를 표준 성과 리포트로 사용한다. 전략 고유의 signal quality, turnover, correlation, constituent 분석 등은 이 기본 성과 리포트 위에 필요한 만큼 추가한다.

전략의 경제적 의미를 먼저 명확히 한 뒤 Python Strategy로 옮긴다.

## 5. Strategy ID와 revision

현재는 다음처럼 운영한다.

```text
Strategy ID = strategy_name
```

예:

```text
market_momentum
```

향후 별도 식별자가 실제로 필요해지면 Strategy ID 규칙을 확장할 수 있다.

전략 명세:

```text
doc/strategies/YYYYMMDD-<strategy-name>-rNN.md
```

전략 구현:

```text
src/backtest_lab/strategies/<strategy_id>/<revision>.py
```

전략 테스트:

```text
tests/strategies/<strategy_id>/test_<revision>.py
```

각 revision module에는 다음을 둔다.

```python
STRATEGY_ID = "<strategy_id>"
REVISION = "r01"
```

revision 증가는 **사용자가 결정한다**. LLM이나 Agent가 전략 변경을 이유로 임의로 `r02`, `r03`을 만들지 않는다.

구현 버그 수정이나 리팩터링은 반드시 revision 증가를 의미하지 않는다. 구현 이력은 Git이 담당한다.

## 6. 전략 명세 작성 원칙

신규 전략의 첫 구현 전에 revision 명세를 작성한다.

명세에는 최소한 다음을 포함한다.

- Strategy ID / Revision / Revision date
- Purpose / hypothesis
- Universe
- Data source / price / period / warm-up
- Signal rules
- Execution timing
- Portfolio construction / rebalance
- Execution settings
- Benchmark
- FFN 기본 성과 리포트와 전략별 추가 outputs
- Pytest scenarios
- Implementation boundary
- Completion / acceptance criteria

명세는 전략의 의미를 정의한다. 코드 구현 세부사항을 과도하게 적지 않는다.

## 7. Codex 구현 요청

ChatGPT ↔ Codex 전달은 `ai-share/PROTOCOL.md`를 따른다.

전략 명세가 합의되면 `ai-share/llm-to-agent.md`에 현재 revision 구현 요청을 기록한다.

Codex에는 가능한 한 다음만 전달한다.

- 읽어야 할 revision 명세
- 구현 위치
- 테스트 위치
- 필요한 run 조건
- expected outputs
- blocker 처리 규칙

이미 명세에 있는 전략 규칙을 장황하게 반복하지 않는다.

Codex 결과 확인 시에는 로컬 추측이 아니라 GitHub remote의 최신 `ai-share/agent-to-llm.md`와 실제 변경 파일을 확인한다.

## 8. Engine blocker 처리

전략 구현 중 현재 core로 의미를 정확히 표현할 수 없는 문제가 발견되어도 전략방에서 임의로 core를 확장하지 않는다.

먼저 Strategy 코드로 자연스럽게 해결 가능한지 판단한다.

공통 engine 변경이 정말 필요하다면 사용자에게 다음 정도로 정리한다.

```text
### 엔진방 전달사항
- 전략에서 하려는 것:
- 현재 엔진에서 막히는 부분:
- 필요한 최소 기능:
- 필요한 이유:
- 전략 코드로 우회 가능한지:
```

엔진 변경 여부와 범위는 엔진방에서 별도로 결정한다.

## 9. Run 관리

실행 결과는 다음 경로에 저장한다.

```text
runs/<strategy_id>/<revision>/<run_id>/
```

Run ID:

```text
YYYYMMDD-NNNN
```

예:

```text
runs/market_momentum/r02/20260825-0003/
```

운영 원칙:

- 같은 날짜·revision에서 `0001`부터 순차 증가
- 새 실행마다 새 run directory 생성
- 기존 run 결과 덮어쓰기 금지
- 같은 실행의 CSV는 한 run directory에 보관
- CSV 이름에는 strategy/revision/run id를 반복하지 않고 산출물 이름만 사용
- 기본 성과 결과는 FFN이 제공하는 성과 척도를 기준으로 리포팅하고, 전략별 추가 분석 output은 revision 명세에서 정의한다.

## 10. Run 해석과 전략 연구 기록

LLM이 특정 run을 분석하면 같은 run directory에 다음 파일을 사용한다.

```text
llm-analysis.md
```

이 파일은 LLM이 작성하며 Agent는 생성하거나 덮어쓰지 않는다.

권장 내용:

- Key Results
- Interpretation
- Implications
- Hypotheses / Provisional Conclusions
- Risks / Limitations
- Next Questions / Steps
- Agreed Insights

`Agreed Insights`는 LLM이 자동으로 채우지 않는다. User와 후속 논의를 거쳐 합의된 내용만 기록한다.

여러 revision과 run을 관통하는 전략 전체 연구 상태는 다음 living document에 누적한다.

```text
doc/strategies/reports/<strategy_id>.md
```

## 11. 테스트 운영

신규 구현의 초기 검증에서는 전체 테스트를 실행한다.

이후 수정은 우선 변경 영향 범위의 테스트를 실행한다. 공통/core 변경이 있거나 영향 범위가 불명확하면 필요한 범위로 확대한다.

전략 correctness 테스트는 가능한 한 synthetic data를 사용하고 외부 네트워크에 의존하지 않는다.

실제 Yahoo/FDR/DB 데이터는 E2E 검증용으로 사용한다.

## 12. 피해야 할 것

- 전략 하나 때문에 Strategy DSL이나 indicator framework를 만드는 것
- Strategy registry/manager를 필요 전에 만드는 것
- 미래 가격 전체를 Strategy에 노출하는 것
- 데이터 source별 ticker를 자동 추측하는 것
- 전략방에서 합의 없이 core abstraction을 확대하는 것
- User 승인 없이 revision을 증가시키는 것
- 기존 run 결과를 덮어쓰는 것
- FFN이 이미 제공하는 기본 성과 지표를 특별한 이유 없이 전략마다 다시 구현하는 것
- 성과가 좋아지도록 규칙을 사후적으로 몰래 조정하는 것

## 13. 새 대화창에서의 첫 행동

이 문서를 읽은 뒤에는 먼저 최신 `AGENTS.md`, `doc/architecture.md`, `doc/specifications.md`를 확인한다.

그 다음 User가 제시한 전략 아이디어를 기준으로 **투자 가설과 전략 규칙을 자연어로 정제하는 것부터 시작한다.**

기존 전략을 이어가는 경우에만 해당 revision 명세와 `doc/strategies/reports/<strategy_id>.md`를 추가로 읽는다.

새 전략은 기존 `market_momentum` 구현을 템플릿처럼 기계적으로 복제하지 않는다. 현재 framework와 운영 규칙만 재사용하고 전략 구조는 아이디어에 맞게 결정한다.
