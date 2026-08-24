# AI Share

state: active
id: 20260824T103000+0900-llm
created_at: 2026-08-24T10:30:00+09:00
type: request
reply_to: 20260820T103158+0900-agent

## Context

v1 코드 리뷰 후 보강 요청이다. 기존 `Strategy -> Runtime -> Portfolio` 경계와 최소주의를 유지한다. 이전 요청에 아래 Strategy history 요구가 추가되었으므로 이 메시지를 최신 요청으로 사용한다.

## Message

다음을 반영해줘.

1. Runtime single-use
- 같은 Runtime 인스턴스의 `run()`은 1회만 허용한다.
- 두 번째 호출은 명시적인 `BacktestError`를 발생시킨다.
- Strategy reset/general lifecycle 추상화는 만들지 않는다.
- regression test를 추가한다.

2. Deferred design notes
- `doc/open-issues.md`를 추가한다.
- 확정 문서인 architecture/specifications와 분리하여 당장 구현하지 않는 설계 이슈만 짧게 관리한다.
- 현재 항목:
  - same-bar vs next-bar execution timing / signal price와 execution price 분리
  - strict market-data coverage에서 중간 결측을 어떻게 검증할지
  - average cost / realized PnL / unrealized PnL의 core 포함 여부
- 각 항목은 현재 상태와 재검토 조건 정도만 기록한다.

3. Market data source 3종
- Local MySQL, FinanceDataReader on-demand, Yahoo Finance(yfinance) on-demand를 지원한다.
- 데이터 소스 선택은 Strategy 내부나 RuntimeConfig에 넣지 않는다.
- data boundary/run input 계층에 `DataSource` + `MarketDataConfig` 수준의 작은 설정으로 둔다.
- Runtime과 Strategy는 source-agnostic 상태를 유지하고 모든 loader는 동일한 normalized price DataFrame을 반환한다.
- Local DB를 기본 source로 유지한다.
- source별 ticker 차이는 explicit symbol mapping을 허용하되 자동 추측하지 않는다.
- remote loader 테스트는 network에 의존하지 않도록 mock/stub 기반으로 작성한다.
- 필요한 dependency는 `finance-datareader`, `yfinance`를 추가한다.

4. Strategy historical market data
- 과거 market data를 Strategy가 자체 누적하거나 직접 조회하게 하지 않는다.
- `StrategyContext`에 `history: pd.DataFrame`을 추가한다.
- 각 step의 `history`에는 해당 timestamp까지의 normalized market data만 포함하고 미래 row는 절대 노출하지 않는다.
- 현재 step의 `prices`는 그대로 유지한다.
- Strategy가 history를 읽기 위해 별도 DSL/history abstraction을 만들지 말고 DataFrame을 직접 제공한다.
- look-ahead 방지를 테스트한다. 예: 각 step에서 `context.history.index.max() <= context.timestamp`.

5. Warm-up data와 성과 시작 분리
- 모멘텀/이동평균 전략은 성과 측정 시작일 이전의 history가 필요하므로 입력 price DataFrame은 warm-up 기간을 포함할 수 있어야 한다.
- `Runtime.run()`에 optional `start`(또는 동등하게 단순한 이름)를 두어, `start` 이전 row는 Strategy history에는 포함되지만 주문/Portfolio valuation/performance series의 실행 step에는 포함하지 않는다.
- 첫 active step의 `StrategyContext.history`에는 warm-up data + 현재 step까지 포함한다.
- pre-start performance reference point 100은 warm-up 시작이 아니라 첫 active step 직전에 위치해야 한다.
- `start=None`이면 기존 동작을 그대로 유지한다.
- 이 기능 때문에 별도 WarmupManager 같은 abstraction은 만들지 않는다.
- regression test를 추가한다.

architecture/specifications는 확정된 경계만 최소 수정한다.

작업 후 전체 pytest를 실행하고 결과를 `agent-to-llm.md`에 간결하게 남긴 뒤 GitHub에 push해줘.
