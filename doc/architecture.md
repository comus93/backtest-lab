# Architecture

## 1. Purpose

`backtest-lab`은 자연어 투자 아이디어를 자유로운 Python Strategy로 구현하고, 이를 작고 예측 가능한 백테스트 Runtime에서 실행하기 위한 경량 프로젝트다.

핵심 목표는 전략 표현력을 제한하지 않으면서도 실행과 회계의 책임을 명확하게 분리하는 것이다.

## 2. Core structure

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
       Analysis
          ↓
         FFN
```

## 3. Responsibilities

### Strategy

투자 판단을 담당한다.

- 무엇을 살지 / 팔지 결정
- 언제 거래할지 결정
- 얼마나 거래할지 결정
- 자산 선택 및 포트폴리오 구성
- 리밸런싱 조건
- drawdown, moving average, regime 등 전략 계산
- 전략에 필요한 자체 상태 관리

Strategy는 일반 Python / pandas / numpy 코드를 자유롭게 사용할 수 있어야 한다.

Strategy는 다음을 직접 수행하지 않는다.

- fee/slippage 계산
- Fill 생성
- Portfolio cash/position 직접 수정

### Runtime

백테스트 실행을 담당한다.

- 입력 데이터의 timestamp/step 순서대로 실행
- Strategy에 현재 timestamp까지의 normalized price history와 현재 price 전달
- Strategy의 매매 요청 처리
- reference price에 fee/slippage 적용
- Fill 생성
- Fill을 Portfolio에 반영
- 외부 cash flow 반영
- fills 기록
- performance series 생성

Runtime은 입력 데이터 주기를 그대로 따른다. daily로 고정하지 않는다.

입력 data에는 warm-up 기간을 포함할 수 있다. `start` 이전 row는 Strategy history에만 포함하고 주문, Portfolio valuation, fills, performance series 생성에는 사용하지 않는다. pre-start reference point는 첫 active step 직전에 둔다.

### Portfolio

현재 회계 상태를 담당한다.

- cash
- symbol별 aggregate position quantity
- 현재 가격 기준 portfolio valuation
- Fill 적용에 따른 cash/position 변경

Portfolio는 전략 판단이나 시간 진행을 알지 않는다.

Lot은 core에 포함하지 않는다. 차수별 진입 등 특수 전략의 상태는 해당 Strategy가 필요에 따라 별도로 관리한다.

### Analysis

백테스트 실행 이후의 공통 성과 분석과 연구용 후처리를 담당한다.

`backtest_lab.analysis`는 단일 파일이 아니라 확장 가능한 package boundary로 유지한다.

현재 공통 책임:

- FFN `calc_stats()` 결과 추출과 canonical 성과 metric
- monthly turnover
- 여러 start/end window의 반복 평가
- Start × End metric matrix 변환

Strategy별 evaluator는 어떤 window를 조사할지, 어떤 benchmark를 비교할지 같은 실험 설계를 담당하고, 공통 계산과 변환은 Analysis package를 재사용한다.

Analysis는 다음을 수행하지 않는다.

- 주문 의사결정
- Fill 생성
- Portfolio 회계 변경
- market data 조회
- GitHub Actions dispatch

향후 drawdown episode, regime, attribution, benchmark comparison 등 반복 요구가 생기면 동일 package 아래에 추가한다. 실제 반복 요구가 없는 추상화 계층은 선제적으로 만들지 않는다.

## 4. Runtime outputs

### fills

Runtime이 실제로 체결한 거래 기록이다.

최소 정보:

```text
timestamp
symbol
side
quantity
reference_price
fill_price
fee
```

fills는 append-only 실행 기록으로 유지한다.

### performance series

Runtime이 Portfolio valuation을 이용해 생성하는 flow-adjusted performance index다.

- Runtime valuation step마다 기록
- external cash flow는 투자성과에서 제거
- fee와 거래비용은 성과에 반영
- 시작 기준값은 100
- FFN에 직접 전달 가능한 time series 형태

개념적으로:

```text
period_return = current_value / (previous_value + net_external_flow) - 1
performance_index = previous_index * (1 + period_return)
```

## 5. Pre-start reference point

첫 실행 step 이전에 synthetic reference point를 둔다.

목적:

- 첫 step의 거래비용이나 손익이 시작값에 묻히는 것을 방지
- performance index = 100인 깨끗한 기준점 확보

이 값은 개념적인 `t0-1`이며 반드시 하루 전을 의미하지 않는다. 입력 주기와 무관하게 첫 valuation step 이전의 기준점이다.

## 6. Fee and slippage

fee와 slippage는 Runtime 책임이다.

v1에서는 별도 모델 객체를 만들지 않고 전역 설정으로 단순하게 시작한다.

예:

```text
FEE_RATE
SLIPPAGE_BPS
```

Strategy는 이 값을 직접 처리하지 않는다.

## 7. Market data boundary

market data는 data boundary에서 선택한다. 기본 source는 `.env` 접속 정보를 사용하는 Local MySQL이며, FinanceDataReader와 Yahoo Finance(yfinance) on-demand source도 지원한다.

`MarketDataConfig`는 source, 명시적 symbol mapping, price column 같은 입력 설정만 가진다. 모든 loader는 timestamp index와 symbol별 가격을 가진 normalized DataFrame을 반환한다. source별 ticker 차이는 mapping으로 명시하며 자동 추측하지 않는다.

DB 및 on-demand 접근 코드는 Runtime core와 분리한다. Runtime과 Strategy는 data source를 알지 않는다.

## 8. FFN boundary

FFN은 Analysis package가 사용하는 성과 계산 엔진이다.

- CAGR
- Sharpe
- drawdown
- 기타 FFN 성과 통계
- 여러 백테스트 성과 비교에 필요한 기초 metric

백테스트 실행이나 Portfolio accounting은 FFN의 책임이 아니다.

가능하면 동일 성과 지표를 전략별 수식으로 중복 계산하지 않고 공통 Analysis 함수를 통해 FFN 결과를 사용한다.

## 9. Design principle

- Strategy 표현을 고정 DSL이나 과도한 객체 모델로 제한하지 않는다.
- Runtime과 Portfolio는 작고 결정론적으로 유지한다.
- 흔한 포트폴리오 백테스트를 가장 단순하게 처리한다.
- 특수 전략 요건은 Strategy의 자유로운 Python 코드와 필요한 추가 상태로 구현한다.
- 특수 전략 하나를 편하게 만들기 위해 core 데이터 모델을 확장하지 않는다.
- 반복되는 사후 분석 요구는 `backtest_lab.analysis` package로 수용하되, 전략별 실험 설계까지 framework에 강제하지 않는다.
- `bt`는 dependency가 아니라 accounting/performance 설계의 reference로 활용한다.
