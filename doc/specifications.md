# Specifications

## 1. Scope

v1은 자유로운 Python Strategy를 실행하고, Portfolio 회계 상태와 체결 기록을 유지하며, FFN 분석용 performance series를 생성하는 최소 백테스트 코어를 구현한다.

## 2. Inputs

### Market data

기본 market data source는 **Local DB**이며, on-demand FinanceDataReader와 Yahoo Finance(yfinance)도 data boundary에서 선택할 수 있다.

- 현재 DBMS: MySQL
- 접속 정보는 repository에 저장하지 않고 별도 `.env`로 제공한다.
- `MarketDataConfig`는 source, 명시적 symbol mapping, price column, coverage 설정을 관리한다.
- source별 ticker 차이는 명시적 mapping만 허용하며 자동 추측하지 않는다.
- 모든 loader는 timestamp index와 symbol별 가격 정보를 가진 normalized DataFrame을 Runtime에 전달한다.
- Runtime core와 Strategy는 MySQL 및 on-demand source에 종속되지 않는다.

### Global execution settings

fee와 slippage는 v1에서 복잡한 model/object hierarchy를 만들지 않고 **전역 설정값**으로 둔다.

예:

```text
FEE_RATE
SLIPPAGE_BPS
```

실제 값은 코드 한 곳의 공통 설정에서 변경할 수 있어야 하며 Strategy별로 별도 구현하지 않는다.

### Strategy

Strategy는 일반 Python 코드로 작성한다. v1 구현과 검증을 위한 Sample Strategy를 함께 제공한다.

#### Sample Strategy

```text
Portfolio
- KODEX 미국S&P500: 70%
- ACE KRX 금현물: 30%

Initial Deposit: 10,000,000 KRW
Rebalancing: Monthly
Period: 2021-01-01 ~ 2026-08-01
```

- Sample Strategy는 위 목표 비중으로 최초 투자하고 월 단위로 70/30 목표 비중에 맞춰 리밸런싱한다.
- 실제 DB 조회에 사용하는 symbol/ticker 값은 Local DB의 저장값에 맞춰 연결한다.
- 이 Sample Strategy는 엔진의 고정 Strategy 형식이 아니라 v1 동작 검증을 위한 예제다.

### Optional external cash flow

Runtime은 필요 시 입금/출금 같은 external cash flow를 입력받을 수 있어야 한다.

## 3. Strategy requirements

- Strategy는 일반 Python 코드로 작성 가능해야 한다.
- 고정 Strategy DSL을 요구하지 않는다.
- Runtime에서 호출 가능한 최소 인터페이스만 요구한다.
- Strategy는 현재 market data, 현재 timestamp까지의 normalized `history` DataFrame, 필요한 Portfolio 상태를 읽을 수 있어야 한다.
- `history`에는 미래 row가 포함되어서는 안 되며 별도 history DSL을 만들지 않는다.
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

Lot은 core에서 관리하지 않는다. 차수별 진입 등 특수 전략에 필요한 별도 상태는 해당 Strategy에서 필요에 따라 관리한다.

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
- 전역 fee/slippage 설정 적용
- Fill 생성 및 Portfolio 반영
- external cash flow 반영
- Portfolio valuation
- performance series 갱신
- Runtime instance의 `run()`은 한 번만 허용하며, 재호출은 `BacktestError`를 발생시킨다.

입력 데이터 주기를 daily로 가정하지 않는다.

`run(..., start=...)`는 warm-up data를 허용한다. `start` 이전 row는 Strategy history에만 제공하며 주문, Portfolio, fills, equity, performance에는 반영하지 않는다. `start=None`이면 모든 row를 기존처럼 실행한다.

## 7. Fee and slippage

v1은 간단한 global 설정을 지원한다.

예:

```text
FEE_RATE
SLIPPAGE_BPS
```

요구사항:

- fee는 Portfolio cash와 performance에 반영되어야 한다.
- slippage는 reference price와 실제 fill price의 차이로 반영되어야 한다.
- buy/sell 방향에 맞게 불리한 execution price를 적용할 수 있어야 한다.
- v1에서는 별도의 FeeModel/SlippageModel 객체 계층을 만들지 않는다.

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

## 12. Monthly turnover

성과 분석의 `avg_monthly_turnover`는 다음 canonical 정의를 사용한다.

```text
monthly_turnover = 0.5 * sum(abs(fill_price * quantity)) / monthly_reference_nav
avg_monthly_turnover = active 기간 모든 calendar month의 monthly_turnover 평균
```

- `monthly_reference_nav`는 해당 calendar month의 active `equity` 관측값 평균 NAV다.
- 거래가 없는 active month도 `0`으로 평균에 포함한다.
- 최초 active timestamp의 초기 포트폴리오 구축 fills는 ongoing turnover에서 제외한다. 같은 달의 이후 거래는 포함한다.
- external cash flow 자체는 turnover numerator에 포함하지 않는다.
- buy/sell notional 합계에 `0.5`를 곱하는 one-way 기준을 사용한다.

## 13. Acceptance checks

v1 구현은 최소한 다음을 검증해야 한다.

1. Sample Strategy가 Local DB market data를 사용해 지정 기간에 실행된다.
2. Sample Strategy가 최초 70/30 목표 비중을 구성하고 monthly rebalancing을 수행한다.
3. 외부 현금 입금만으로 performance index가 상승하지 않는다.
4. 보유 자산 가격 상승은 performance index에 반영된다.
5. fee는 성과를 낮춘다.
6. slippage는 Fill price와 Portfolio cash에 반영된다.
7. 동일 symbol 반복 매매 후 aggregate quantity가 정확하다.
8. 첫 step에서 발생한 거래비용/손익이 performance에 포함된다.
9. fills 기록과 Portfolio 상태가 일치한다.
10. 입력 index가 intraday여도 동일한 core 구조로 실행 가능하다.
11. Strategy history에는 현재 step 이후의 미래 market data가 노출되지 않는다.
12. warm-up row는 history에 포함되지만 첫 active step 이전의 주문, valuation, performance에는 포함되지 않는다.

## 14. Quality requirements

- deterministic: 동일 입력과 설정은 동일 결과를 만들어야 한다.
- debuggable: Strategy 판단, Fill, Portfolio 결과의 경계를 추적할 수 있어야 한다.
- minimal: 실제 반복 요구가 없는 추상화 계층을 선제적으로 추가하지 않는다.
- data-source boundary: v1은 Local MySQL을 사용하지만 market data 조회와 실행 코어의 책임은 분리한다.

## Reporting visual subsystem (separate from research narrative)

공통 HTML Reporting은 [`doc/reporting/specifications.md`](reporting/specifications.md)를 따른다. 이는 아래의 사용자·LLM 해석을 기록하는 Run Analysis / Strategy Report 문서와 별도의 읽기 전용 시각화 기능이다. 기존 FFN 계산값을 그대로 표시하며 Runtime, Strategy, archived run을 수정하지 않는다.

## 15. Strategy and run research reporting

백테스트의 계산 산출물뿐 아니라 그 결과에 대한 해석과 전략의 누적 연구 상태도 repository에 보존한다.

### Run Analysis

LLM이 특정 run을 분석한 경우 다음 위치에 기록한다.

```text
runs/<strategy_id>/<revision>/<run_id>/llm-analysis.md
```

Run Analysis는 해당 실행을 중심으로 다음 내용을 기록할 수 있다.

- Key Results
- Interpretation
- Implications
- Hypotheses / Provisional Conclusions
- Risks / Limitations
- Next Questions / Steps
- Agreed Insights

`Agreed Insights`는 자동 생성하지 않고 User와의 후속 논의를 통해 합의된 내용을 기록하며 마지막 섹션에 둔다.

계산/실행 산출물은 Agent가 생성하고 `llm-analysis.md`는 LLM이 작성한다. Agent는 `llm-analysis.md`를 생성하거나 덮어쓰지 않는다.

### Strategy Report

전략 전역 연구 상태는 다음 위치의 living document로 관리한다.

```text
doc/strategies/reports/<strategy_id>.md
```

Strategy Report는 여러 revision과 run을 관통하여 다음 내용을 누적한다.

- 전략의 시작 배경과 목적
- 핵심 컨셉
- revision/run을 통해 축적된 evidence
- 현재 hypotheses와 provisional view
- risks / open issues
- 다음 전략적 질문
- User와 LLM이 합의한 핵심 insights

Run Analysis와 Strategy Report는 상호 배타적일 필요가 없으며 같은 evidence나 insight를 목적에 맞게 중복 기록할 수 있다.
