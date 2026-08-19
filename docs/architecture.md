# Architecture

## 1. Core principle

backtest-lab은 완성형 백테스트 프레임워크를 만들지 않는다.

핵심 원칙은 다음과 같다.

1. 가장 많이 사용하는 포트폴리오 전략을 단순하고 강건하게 처리한다.
2. 특이 요건은 Core 추상화를 늘리지 않고 Strategy의 자유로운 Python 코드와 추가 상태로 처리한다.
3. Strategy / Runtime / Portfolio의 R&R을 분리해 문제 원인을 추적하기 쉽게 만든다.
4. `bt`는 dependency가 아니라 design reference로 사용한다. `bt`의 선택이 일반적인 회계/성과 BP인지, `bt`의 Strategy/Algo 구조 때문에 필요한 선택인지 구분해 참고한다.
5. 성과 분석은 `ffn`에 맡긴다.

## 2. R&R

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

### Strategy

책임:

- 무엇을, 언제, 얼마나 사고팔지 결정
- 자산 선택과 동적 포트폴리오 구성
- 리밸런싱 조건
- drawdown, moving average, regime 등 전략 계산
- 전략에만 필요한 특수 상태 관리
- 일반 Python / pandas / numpy 사용

하지 않는 것:

- fee/slippage 계산
- Fill 생성
- Portfolio의 cash/position 직접 수정

Strategy를 특정 DSL, Signal, Indicator 객체 모델에 맞추도록 강제하지 않는다.

### Runtime

책임:

- 입력 데이터의 timestamp/step 순서대로 백테스트 진행
- Strategy 호출
- 매매 요청 실행
- reference price에 fee/slippage 규칙 적용
- Fill 생성
- Fill을 Portfolio에 반영
- 외부 cash flow 적용
- flow-adjusted performance series 생성
- 발생한 fills를 실행 결과 데이터로 보존

Runtime step은 daily로 고정하지 않는다. 일봉 입력이면 일별, intraday 입력이면 해당 입력 step을 따른다.

초기 구현에서는 실제 브로커 수준의 pending/accepted/partial/cancelled order lifecycle을 만들지 않는다. 매매 요청은 백테스트 규칙에 따라 즉시 Fill로 변환한다.

### Portfolio

책임:

- 현재 cash
- 종목별 aggregate position quantity
- 현재 가격 기준 portfolio valuation
- Fill 반영에 따른 cash/position 변경

Portfolio는 현재 회계 상태를 담당하며 시간축 실행이나 전략 판단을 알지 않는다.

Core에는 acquisition lot/tranche를 두지 않는다. 차수별 진입/청산처럼 특수한 전략이 필요하면 Strategy가 별도 상태를 관리하고, Runtime에는 최종 매매 수량만 요청한다.

평균단가 및 realized/unrealized PnL의 Core 포함 여부는 아직 확정하지 않았다. 초기 구현에서 임의로 확장하지 않는다.

### fills

Fill은 Runtime이 실제로 체결했다고 판단한 거래 결과다.

최소 정보 예시:

```text
timestamp
symbol
side
quantity
reference_price
fill_price
fee
```

fills는 독립적인 실행 결과 데이터지만 별도 복잡한 Ledger/Repository/Service 계층을 만들 필요는 없다. append-only collection/DataFrame 수준으로 시작한다.

Fill의 주요 목적은 거래 결과 보존과 디버깅 가능성이다.

### performance series

모든 백테스트에서 공통으로 필요한 Core 산출물이다.

- Runtime의 valuation step마다 생성한다.
- Portfolio의 실제 금액(equity) 자체가 아니라 external flow를 성과에서 제거한 synthetic performance index를 유지한다.
- 기본 시작값은 100으로 둔다.
- `ffn`에 직접 전달할 수 있는 time series를 목표로 한다.

`bt`의 일반 포트폴리오 계산을 참고한 기본 개념은 다음과 같다.

```text
period_return = current_value / (previous_value + net_external_flow) - 1
performance_index = previous_index * (1 + period_return)
```

fee와 거래비용은 external flow가 아니며 투자성과에 영향을 준다.

### FFN

책임:

- Runtime이 만든 performance series의 성과 분석
- CAGR, Sharpe, drawdown 등 `ffn`이 제공하는 통계 계산
- 여러 전략의 성과 비교

백테스트 회계나 전략 실행 로직을 `ffn`에 맡기지 않는다.

## 3. Pre-start reference point

`bt`가 첫 거래일 이전에 synthetic reference point를 두는 선택을 참고해 채택한다.

목적:

- 첫 runtime step의 거래비용/손익이 performance series 시작값에 묻혀 사라지는 것을 방지
- 첫 실행 전 performance index = 100인 깨끗한 기준점을 확보

개념적으로는 `t0-1`이지만 반드시 "하루 전"을 뜻하지 않는다. intraday까지 고려해 첫 valuation step 이전의 synthetic reference point로 구현한다.

## 4. Fee / slippage

fee와 slippage는 Strategy가 아니라 Runtime 책임이다.

초기에는 전역/Run 설정으로 단순하게 시작한다.

예:

```text
fee_rate
slippage_bps
```

별도의 FeeModel/SlippageModel 클래스 계층은 실제 반복 요구가 생기기 전까지 만들지 않는다.

## 5. Design reference: bt

`bt`는 사용하지 않지만 구현 디자인 초이스를 정할 때 우선 참고한다.

판단 순서:

1. 우리 목표에 필요한 책임인가?
2. `bt`는 같은 문제를 어떻게 처리하는가?
3. 그 선택이 일반적인 accounting/performance BP인가?
4. 아니면 `bt`의 Strategy tree / Algo abstraction 때문에 필요한 것인가?
5. 일반적인 BP는 채택 검토하고, `bt` 세계관 의존 선택은 배제한다.

현재 채택한 참고점:

- external cash flow를 performance에서 분리
- flow-adjusted synthetic performance index
- performance series를 `ffn`에 직접 연결
- pre-start reference point (`t0-1` 개념)

현재 의도적으로 채택하지 않은 것:

- Strategy/Algo stack
- Strategy tree
- Core acquisition lot 관리
- Strategy 객체 안에서 portfolio accounting/history까지 함께 소유하는 구조

## 6. Initial implementation boundary

첫 구현에서는 다음을 우선한다.

- aggregate positions
- cash
- buy/sell → immediate Fill
- fee/slippage
- fills collection
- external cash flow
- current valuation
- performance series
- pre-start reference point
- `ffn` 연결
- 핵심 회계/성과 회귀 테스트

다음 항목은 아직 Core로 확정하지 않았으므로 임의로 확장하지 않는다.

- acquisition lot
- 평균단가
- realized/unrealized PnL 모델
- order lifecycle
- broker abstraction
- indicator/signal framework
- 데이터 소스 고정
