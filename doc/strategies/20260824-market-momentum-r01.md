# Market Momentum Pilot

Revision: `r01`  
Revision date: `2026-08-24`

## 1. Purpose

글로벌 투자시장 ETF의 중기 상대 모멘텀을 이용한 동적 리밸런싱이 정적 동일비중 및 SPY buy & hold보다 투자적으로 유효한지 검증한다.

성과 비교와 함께 3M/6M/9M/12M 모멘텀 순위가 이후 1개월 수익률과 연결되는지도 분석한다.

## 2. Universe

USD 기준 미국 상장 ETF 14종을 고정 Universe로 사용한다.

- SPY
- QQQ
- DIA
- EWJ
- EWY
- VNAM
- MCHI
- KTEC
- KSTR
- DAX
- EWW
- EIDO
- INDY
- EPHE

## 3. Data

- Source: Yahoo Finance
- Price: adjusted close (`AdjClose` normalized column)
- Currency: USD
- Strategy는 Runtime이 `StrategyContext.history`로 제공하는 과거 가격만 사용한다.
- 백테스트 입력에는 12M 모멘텀 계산을 위한 warm-up을 포함한다.
- active start는 14종 모두가 직전 12개월 월말 history를 확보한 뒤 가능한 최초 공통 시점으로 정한다.
- end는 14종의 최신 공통 가격 시점으로 정한다.

## 4. Strategies

### Static Equal Weight

- 14종 전체 보유
- 각 1/14 동일비중
- 월 1회 리밸런싱

### Momentum Top 3

다음 4개 horizon을 각각 독립 실행한다.

- 3M
- 6M
- 9M
- 12M

각 전략은 매월 모멘텀 상위 3종을 선택하고 각 1/3 동일비중으로 리밸런싱한다.

모멘텀은 `현재 signal 월의 마지막 거래일 가격 / N개월 전 월의 마지막 거래일 가격 - 1`로 계산한다. 거래일 수(63/126/189/252) 기준은 사용하지 않는다.

동률은 ticker 문자열 오름차순으로 결정하여 deterministic하게 처리한다.

### Benchmark

- SPY buy & hold

SPY는 Momentum Universe에도 포함된다.

## 5. Signal and execution timing

- 매월 마지막 거래일까지의 데이터로 signal을 확정한다.
- 해당 signal에 따른 주문은 다음 거래일에 실행한다.
- 실행일 가격은 signal 계산에 사용하지 않는다.
- 월별 리밸런싱은 1회만 수행한다.

## 6. Execution settings

프로젝트 기본 설정을 사용한다.

- initial cash: 1,000,000 USD
- fee_rate: 0.00015
- slippage_bps: 0

## 7. Analysis outputs

### `performance_summary`

전략별 한 행.

- strategy
- start_date
- end_date
- total_return
- cagr
- volatility
- sharpe
- max_drawdown
- avg_monthly_turnover

대상 전략:

- Static Equal Weight
- Momentum 3M
- Momentum 6M
- Momentum 9M
- Momentum 12M
- SPY Buy & Hold

### `equity_curves`

일자별 6개 전략의 누적 performance series를 한 테이블에 정렬한다.

### `monthly_decisions`

모멘텀 전략의 매월 판단을 추적할 수 있어야 한다.

- horizon
- signal_date
- execution_date
- symbol
- momentum
- rank
- selected
- target_weight

각 signal date마다 Universe 14종 전체를 기록한다.

### `momentum_signal_analysis`

horizon별로 다음을 집계한다.

- horizon
- top3_next_1m_return
- bottom3_next_1m_return
- top3_minus_bottom3
- spread_win_rate
- observation_months

`next_1m_return`은 해당 signal 이후 다음 월말까지의 수익률을 사용한다.

## 8. Pytest scenarios

테스트용 synthetic 가격 값과 날짜는 Codex가 선택한다. 값은 사람이 쉽게 검산할 수 있게 단순하게 구성하고, 각 테스트에서 기대 결과를 명시적으로 assert한다. 전략 correctness 테스트는 외부 네트워크에 의존하지 않는다.

1. **Calendar-month momentum**
   - 3M/6M/9M/12M이 각각 N개월 전 월의 마지막 거래일 가격을 사용하는지 검증한다.
   - 거래일 수 기반 계산과 혼동되지 않는 fixture를 사용한다.

2. **Signal cutoff / no execution-day leakage**
   - 다음 달 첫 거래일 가격을 크게 변경해도 직전 월말 기준 momentum과 Top 3가 변하지 않아야 한다.

3. **Ranking and Top 3**
   - 명확한 momentum 순위를 가진 synthetic Universe에서 기대한 3종만 선택되는지 검증한다.

4. **Horizon independence**
   - 같은 fixture에서 3M/6M/9M/12M의 기대 Top 3가 서로 다르게 나오도록 구성한다.
   - 각 horizon 전략이 해당 horizon 결과만 사용하는지 검증한다.

5. **Next-trading-day monthly rebalance**
   - 월말 signal 이후 첫 거래일에만 리밸런싱하고 같은 달에 반복 주문하지 않는지 검증한다.
   - 다음 달에는 새 signal로 다시 리밸런싱하는지 검증한다.

6. **Target weights and rotation**
   - Dynamic은 선택 3종이 각 1/3 목표비중이 되는지 검증한다.
   - Top 3에서 탈락한 기존 보유종목의 매도와 신규 편입 주문이 발생하는지 검증한다.
   - Static은 14종 각 1/14 목표비중을 검증한다.

7. **Tie and reproducibility**
   - 3위/4위 momentum 동률에서 ticker 오름차순 tie-break가 적용되는지 검증한다.
   - 동일 입력으로 반복 실행했을 때 selection과 fills가 동일해야 한다.

8. **Warm-up usage**
   - active start 이전 12개월 history를 signal 계산에 사용하되 warm-up 기간에는 주문이 발생하지 않는지 검증한다.

9. **Analysis output smoke test**
   - synthetic data 실행으로 `performance_summary`, `equity_curves`, `monthly_decisions`, `momentum_signal_analysis`가 생성되고 필수 컬럼 및 데이터가 존재하는지 검증한다.

## 9. Implementation boundary

- Strategy source: `src/backtest_lab/strategies/market_momentum/r01.py`
- Strategy tests: `tests/strategies/market_momentum/test_r01.py`
- Module revision: `REVISION = "r01"`

기존 자유로운 Python Strategy와 Runtime history를 사용한다. Pilot 구현을 위해 core abstraction을 선제적으로 확대하지 않는다.

현재 엔진으로 전략 의미를 구현할 수 없는 blocker가 발견되면 core를 임의 변경하지 말고 `ai-share/agent-to-llm.md`에 필요한 최소 기능과 이유를 보고한다.

## 10. Completion

Codex는 pytest 통과 후 Yahoo Finance 실제 데이터로 Pilot을 실행하고 다음을 `ai-share/agent-to-llm.md`에 간결하게 보고한다.

- 구현/수정 파일
- pytest 결과
- 실제 데이터 coverage와 active 기간
- 결과 산출물 경로
- 실행된 전략 목록
- 발견된 blocker 또는 데이터 제약
