# AI Share

state: active
id: 20260820T083700+0900-llm
created_at: 2026-08-20T08:37:00+09:00
type: request
reply_to: none

## Context

새 프로젝트 `backtest-lab`의 첫 구현이다. 먼저 `README.md`, `docs/architecture.md`, `ai-share/PROTOCOL.md` 최신본을 읽고 그 내용을 source of truth로 삼아라.

핵심 방향은 `bt` 같은 완성형/추상화 중심 프레임워크를 재구현하는 것이 아니라, 자유 Python Strategy를 실행하는 최소 Runtime + Portfolio + ffn 연결이다. `bt`는 dependency가 아니라 design reference다.

## Message

첫 vertical slice를 구현해줘.

필수 범위:

1. Python 프로젝트/package 기본 구조를 만든다. import package 이름은 `backtest_lab`.
2. Strategy는 BaseStrategy/Algo/Signal DSL을 만들지 말고, plain callable/function 방식으로 Runtime에서 실행 가능하게 한다.
3. Portfolio는 `cash + symbol별 aggregate quantity + current valuation`을 관리한다.
4. Runtime은 timestamp/step 진행, Strategy 호출, 즉시 체결, fee/slippage, Fill 생성, Portfolio 반영을 담당한다.
5. Fill 최소 필드: timestamp, symbol, side, quantity, reference_price, fill_price, fee. Runtime의 append-only 결과 데이터로 보존한다.
6. external cash flow를 지원하고 performance에서 제외한다.
7. Runtime valuation step마다 flow-adjusted synthetic performance series를 만든다. 시작값은 100.
8. 첫 step의 거래비용/손익이 사라지지 않도록 `bt`의 t0-1 노하우를 참고해 pre-start synthetic reference point를 둔다. 반드시 하루 전으로 하드코딩하지 말고 첫 valuation step 이전 기준점이라는 의미를 보존한다.
9. performance series를 `ffn`에 직접 넘겨 성과 통계를 얻는 최소 연결을 만든다.
10. 일봉으로 하드코딩하지 않는다. 입력 index의 runtime step을 따른다.

반드시 테스트할 것:

- 외부 cash deposit만으로 performance index가 상승하지 않는다.
- 자산 가격 상승은 performance index에 반영된다.
- fee는 성과를 낮춘다.
- slippage가 Fill 가격과 cash/position에 반영된다.
- 같은 symbol을 여러 번 매수하면 aggregate quantity가 정확하다.
- 첫 step 거래 fee/손익이 pre-start reference point 때문에 누락되지 않는다.
- fills 기록과 Portfolio 상태가 일치한다.

구현 원칙:

- `docs/architecture.md`의 현재 R&R과 초기 구현 범위만 구현한다.
- 필요하지 않은 클래스 계층, DSL, 플러그인, broker/order lifecycle, indicator framework 등을 추가하지 않는다.
- 새로운 Core 설계 결정이 필요하면 임의로 확장하지 말고 최소 구현을 유지한 채 `agent-to-llm.md`에 질문/판단 포인트를 남긴다.

완료 후 테스트 결과, 변경한 주요 파일, 남은 설계 질문을 `agent-to-llm.md`에 기록하고 GitHub에 push해줘.
