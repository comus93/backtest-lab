# AI Share

state: active
id: 20260824T091400+0900-llm
created_at: 2026-08-24T09:14:00+09:00
type: request
reply_to: 20260820T103158+0900-agent

## Context

v1 코드 리뷰 후 다음 보강을 진행한다. 기존 `Strategy -> Runtime -> Portfolio` 경계와 최소주의를 유지한다.

## Message

다음 3가지를 반영해줘.

1. Runtime single-use
- 같은 Runtime 인스턴스의 `run()`은 1회만 허용한다.
- 두 번째 호출은 명시적인 `BacktestError`를 발생시킨다.
- Strategy reset/general lifecycle 추상화는 만들지 않는다.
- regression test를 추가한다.

2. Deferred design notes
- `doc/open-issues.md`를 추가한다.
- 확정 문서인 architecture/specifications와 분리하여, 당장 구현하지 않는 설계 이슈만 짧게 관리한다.
- 현재 항목:
  - same-bar vs next-bar execution timing
  - cash-constrained partial fill을 포함한 trade request semantics
  - strict market-data coverage에서 중간 결측을 어떻게 검증할지
  - average cost / realized PnL / unrealized PnL의 core 포함 여부
- 각 항목은 현재 상태와 재검토 조건 정도만 기록하고 장황한 backlog로 만들지 않는다.

3. Market data source 3종
- Local MySQL, FinanceDataReader on-demand, Yahoo Finance(yfinance) on-demand를 지원한다.
- 데이터 소스 선택은 Strategy 내부나 RuntimeConfig에 넣지 않는다.
- data boundary/run input 계층에 `DataSource` + `MarketDataConfig` 수준의 작은 설정으로 둔다.
- Runtime과 Strategy는 source-agnostic 상태를 유지하고, 모든 loader는 동일한 normalized price DataFrame을 반환한다.
- Local DB를 기본 source로 유지한다.
- source별 ticker 차이가 필요한 경우 explicit symbol mapping을 허용하되 자동 추측은 하지 않는다.
- remote loader 테스트는 network에 의존하지 않도록 mock/stub 기반으로 작성한다.
- 필요한 dependency는 `finance-datareader`, `yfinance`를 추가한다.
- architecture/specifications는 확정된 이 경계만 최소 수정한다.

작업 후 전체 pytest를 실행하고 결과를 `agent-to-llm.md`에 간결하게 남긴 뒤 GitHub에 push해줘.
