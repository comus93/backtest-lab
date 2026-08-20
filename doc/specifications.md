# Specifications

## 1. Scope

v1은 자유로운 Python Strategy를 실행하고, Portfolio 회계 상태와 체결 기록을 유지하며, FFN 분석용 performance series를 생성하는 최소 백테스트 코어를 구현한다.

## 2. Inputs

Runtime은 최소한 다음 입력을 받을 수 있어야 한다.

- timestamp index를 가진 market data
- initial cash
- Strategy
- fee 설정
- slippage 설정
- 필요 시 external cash flow

특정 DB나 데이터 공급자에 종속되지 않는다.

## 3. Strategy requirements

- Strategy는 일반 Python 코드로 작성 가능해야 한다.
- 고정 Strategy DSL을 요구하지 않는다.
- Runtime에서 호출 가능한 최소 인터페이스만 요구한다.
- Strategy는 현재 market data와 필요한 Portfolio 상태를 읽을 수 있어야 한다.
- Strategy는 매매 의사결정을 Runtime에 전달한다.
- Strategy가 Portfolio 내부 상태를 직접 변경해서는 안 된다.

## 4. Portfolio requirements

Portfolio는 최소한 다음 상태를 유지한다.

```text
cash
positions[symbol] = quantity
```

필수 동작:

- Fill 반영
- 매수 시 cash 감소 및 position 증가
- 매도 시 cash 증가 및 position 감소
- 현재 market price를 이용한 total portfolio valuation

같은 symbol을 여러 번 거래해도 position은 aggregate quantity로 정확히 유지되어야 한다.

## 5. Fill requirements

Runtime은 체결마다 Fill을 생성한다.

최소 필드:

```text
timestamp
symbol
side
quantity
reference_price
fill_price
fee
```

요구사항:

- fee/slippage 적용 결과가 Fill에 반영되어야 한다.
- Fill과 Portfolio 상태 변경은 일관되어야 한다.
- 생성된 Fill은 실행 순서대로 보존되어야 한다.

## 6. Runtime requirements

Runtime은 각 입력 step에서 백테스트를 진행한다.

필수 책임:

- 현재 timestamp/market data 설정
- Strategy 실행
- 매매 요청 처리
- execution price 결정
- fee/slippage 계산
- Fill 생성 및 Portfolio 반영
- external cash flow 반영
- Portfolio valuation
- performance series 갱신

입력 데이터 주기를 daily로 가정하지 않는다.

## 7. Fee and slippage

v1은 간단한 run-level 설정을 지원한다.

예:

```text
fee_rate
slippage_bps
```

요구사항:

- fee는 Portfolio cash와 performance에 반영되어야 한다.
- slippage는 reference price와 실제 fill price의 차이로 반영되어야 한다.
- buy/sell 방향에 맞게 불리한 execution price를 적용할 수 있어야 한다.

## 8. External cash flow

Runtime은 입금/출금 같은 external cash flow를 반영할 수 있어야 한다.

요구사항:

- external flow는 Portfolio cash/value에는 반영된다.
- external flow 자체는 투자수익으로 계산되지 않는다.

예를 들어 가격 변동 없이 현금만 추가 입금한 경우 performance index는 상승하지 않아야 한다.

## 9. Performance series

Runtime은 FFN 입력용 synthetic performance index를 생성한다.

요구사항:

- valuation step마다 한 값을 기록한다.
- 시작 기준값은 100이다.
- external cash flow를 제거한 투자성과를 표현한다.
- fee/slippage로 발생한 경제적 손실은 performance에 반영한다.
- pandas time series 형태로 FFN에 직접 전달할 수 있어야 한다.

기본 계산 개념:

```text
period_return = current_value / (previous_value + net_external_flow) - 1
performance_index = previous_index * (1 + period_return)
```

## 10. Pre-start reference point

첫 실행 step 이전에 performance index 100의 synthetic reference point를 둔다.

요구사항:

- 첫 step의 거래비용/손익이 전체 성과에서 누락되지 않아야 한다.
- reference point를 '하루 전'으로 하드코딩하지 않는다.
- 입력 데이터 주기에 관계없이 첫 valuation step 이전의 논리적 기준점으로 처리한다.

## 11. FFN integration

- 단일 백테스트의 performance series를 FFN에 전달해 성과 통계를 얻을 수 있어야 한다.
- 여러 백테스트의 performance series를 FFN을 통해 비교할 수 있어야 한다.
- FFN은 Runtime이나 Portfolio 회계를 수행하지 않는다.

## 12. Acceptance checks

v1 구현은 최소한 다음을 검증해야 한다.

1. 외부 현금 입금만으로 performance index가 상승하지 않는다.
2. 보유 자산 가격 상승은 performance index에 반영된다.
3. fee는 성과를 낮춘다.
4. slippage는 Fill price와 Portfolio cash에 반영된다.
5. 동일 symbol 반복 매매 후 aggregate quantity가 정확하다.
6. 첫 step에서 발생한 거래비용/손익이 performance에 포함된다.
7. fills 기록과 Portfolio 상태가 일치한다.
8. 입력 index가 intraday여도 동일한 구조로 실행 가능하다.

## 13. Quality requirements

- deterministic: 동일 입력과 설정은 동일 결과를 만들어야 한다.
- debuggable: Strategy 판단, Fill, Portfolio 결과의 경계를 추적할 수 있어야 한다.
- minimal: 실제 반복 요구가 없는 추상화 계층을 선제적으로 추가하지 않는다.
- data-source independent: market data 저장 방식과 실행 코어를 분리한다.
