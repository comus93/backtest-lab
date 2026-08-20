# Session Handover

created_at: 2026-08-20T11:42:00+09:00

## Current State

새 백테스트 프로젝트 `comus93/backtest-lab`을 만들고 설계 문서 및 Codex 협업 구조를 초기화했다.

현재 source of truth:

- `AGENTS.md`
- `doc/architecture.md`
- `doc/specifications.md`
- `ai-share/PROTOCOL.md`

Codex에는 `ai-share/llm-to-agent.md`로 v1 구현 요청이 이미 전달되어 있다. 다음 ChatGPT 세션에서는 Agent 결과가 왔다면 `ai-share/agent-to-llm.md`를 먼저 확인하고 구현을 설계 의도와 비교 검토한다.

## Decisions

### 프로젝트 철학

- 자연어 투자 아이디어를 자유로운 Python Strategy 코드로 구현하는 경량 백테스트 프로젝트다.
- 고정 Strategy DSL이나 대형 백테스트 프레임워크를 만들지 않는다.
- 가장 많이 쓰는 포트폴리오 백테스트 요건을 core가 단순하고 정확하게 처리한다.
- 특이 전략 요건은 Strategy의 자유로운 Python 코드와 전략별 추가 상태로 처리한다.
- `bt`는 dependency가 아니라 accounting/performance 설계의 reference로 활용한다.

### Core R&R

```text
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

- Strategy: 무엇을/언제/얼마나 거래할지 판단. Portfolio 직접 mutation 금지.
- Runtime: time step 진행, Strategy 호출, execution price, fee/slippage, Fill 생성, Portfolio 반영, external flow, fills 기록, performance series 생성.
- Portfolio: 현재 cash + symbol별 aggregate position + 현재 valuation.
- FFN: Runtime이 만든 performance series의 성과 분석 전용.

### Lot / Fill

- Lot은 core에서 제외한다.
- 기존 레거시의 차수별 진입/청산 같은 특이 전략을 일반 core 요구로 확대하지 않는다.
- 그런 전략이 필요하면 Strategy가 별도 tranche/entry 상태를 관리한다.
- Fill은 유지한다. 실제 체결 결과이고 Runtime과 Portfolio 사이 디버깅 경계로 가치가 있다.
- 다만 거대한 FillLedger subsystem은 만들지 않는다. Runtime의 append-only `fills` 산출 데이터 정도로 유지한다.

### Performance series

- core에 유지한다.
- daily 고정이 아니라 Runtime valuation step과 동일한 주기로 기록한다.
- external cash flow를 제거한 flow-adjusted synthetic performance index다.
- 시작값 100.
- FFN에 직접 전달한다.
- `bt`의 노하우를 따라 첫 실행 step 이전에 synthetic pre-start reference point를 둔다.
- 이것은 실제 '하루 전'이 아니라 첫 valuation step 이전의 논리적 기준점이다.
- 첫 step의 거래비용/손익이 시작값에 묻히지 않도록 한다.

### Fee / Slippage

- Runtime 책임.
- v1에서는 `FEE_RATE`, `SLIPPAGE_BPS` 같은 단순 전역/run-level 설정으로 시작한다.
- FeeModel/SlippageModel 객체 hierarchy는 만들지 않는다.

### Market data

- 현재 실제 입력은 Local MySQL market DB.
- DB 접속정보는 로컬 `.env`를 사용한다.
- DB adapter와 Runtime core는 분리한다.
- `.gitignore`를 추가했고 `.env`, private keys, virtualenv/cache/build/IDE/log 파일 등을 제외한다.
- `.env.example`, `.env.sample`은 커밋 가능하도록 예외 처리한다.

### Sample Strategy / v1 end-to-end test

- KODEX 미국S&P500 70%
- ACE KRX 금현물 30%
- Initial Deposit: 10,000,000 KRW
- Monthly rebalancing
- Period: 2021-01-01 ~ 2026-08-01
- Local MySQL market data 사용
- 실제 ticker 저장값과 DB schema는 Agent가 로컬 DB에서 확인한다. 추측하지 않는다.

## Important Constraints

- Lot core 도입 금지.
- 고정 Strategy DSL 금지.
- `bt` dependency 도입 금지.
- 대형 framework abstraction을 되살리지 않는다.
- Strategy가 Portfolio cash/positions를 직접 수정하지 않는다.
- performance series를 daily로 하드코딩하지 않는다.
- 아직 합의하지 않은 average cost / realized PnL / unrealized PnL / full order lifecycle을 선제적으로 core에 추가하지 않는다.
- 구현보다 먼저 필요하지 않은 추상화를 만들지 않는다.

## AI Share

프로젝트 루트 `./ai-share/PROTOCOL.md`가 ChatGPT↔Codex 공유 규약의 source of truth다.

주요 파일:

- `llm-to-agent.md`: ChatGPT → Codex
- `agent-to-llm.md`: Codex → ChatGPT
- `llm-to-llm.md`: ChatGPT 세션 handover
- `agent-to-agent.md`: Codex 세션 handover

현재 `llm-to-agent.md`에는 v1 구현 요청이 active 상태다.

## Open Issues

다음 설계 항목은 아직 확정하지 않았다.

- Portfolio가 average cost를 core로 보유해야 하는지
- realized / unrealized PnL을 core 상태로 관리할지, 필요 시 계산할지
- Strategy → Runtime trade request의 최소 인터페이스
- exact Fill schema의 세부 필드 확정
- Runtime의 step 내부 처리 순서와 valuation timing 세부사항
- external flow의 입력 인터페이스 세부 설계

## Next

1. Agent가 작업을 완료했다면 `ai-share/agent-to-llm.md` 최신본을 확인한다.
2. 구현이 `AGENTS.md`, `doc/architecture.md`, `doc/specifications.md`의 설계 경계를 지키는지 검토한다.
3. Sample Strategy가 Local MySQL 데이터로 end-to-end 실행되는지 확인한다.
4. acceptance tests, 특히 external flow / fee / slippage / pre-start reference point / aggregate positions / fills 일관성을 검증한다.
5. 구현 중 드러난 실제 필요를 근거로 아직 미확정인 Portfolio 상태와 trade request 인터페이스를 다음 설계 토론 대상으로 삼는다.
