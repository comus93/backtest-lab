# Weekly Trend

Strategy ID: `weekly_trend`  
Revision: `r01`  
Revision date: `2026-09-01`  
Status: `implemented / pending verification`

## 1. Purpose / hypothesis

주봉 방향의 짧은 연속성이 이후 추세 지속에 유효한 신호인지 검증한다.

기존 `market_momentum`의 월간 cross-sectional relative momentum과는 별도 전략이다. 이 전략은 각 자산의 weekly trend 상태에 따라 개별적으로 편입/편출한다.

핵심 가설:

- 주봉이 2회 연속 상승한 자산은 단기 추세가 이어질 가능성이 있다.
- 보유 중 주봉이 2회 연속 하락하면 추세 약화로 보고 편출한다.
- 신호가 없는 자산 슬롯을 현금으로 유지하면 시장 전체 trend 상태에 따라 총 exposure가 자연스럽게 조절된다.

## 2. Universe

초기 검증은 `market_momentum` r02와 동일한 11개 ETF를 사용한다.

`SPY, QQQ, DIA, EWJ, EWY, MCHI, DAX, EWW, EIDO, INDY, EPHE`

Universe size: `N = 11`

## 3. Data

- Source: Yahoo Finance
- Price: adjusted close (`AdjClose` normalized column)
- Currency: USD
- Signal frequency: weekly
- 주봉 기준: calendar week의 마지막 available trading day
- Warm-up: 최소 3개 완성 주봉. 2개의 연속 weekly return 계산에 필요하다.
- Data load start baseline: `2016-06-01`
- Active validation period: `2016-07-01 ~ 2026-07-31`

검증 기간은 기존 `market_momentum` r02와 동일하게 맞춘다.

## 4. Signal rules

### Baseline direction rule

상승/하락의 최종 강도 조건은 아직 확정하지 않는다.

첫 run은 가장 단순한 baseline으로 시작한다.

```text
move_threshold = 0
상승 = weekly return > move_threshold
하락 = weekly return < -move_threshold
그 외 = neutral
```

구현은 `move_threshold` 파라미터를 지원하여 첫 결과를 본 뒤 최소 상승/하락 폭을 별도 run에서 실험할 수 있게 한다.

### Entry

- 비보유 자산의 최근 2개 weekly return이 모두 상승이면 편입한다.
- 두 번째 상승 주의 마지막 available trading day에 signal이 확정된다.

### Exit

- 보유 자산의 최근 2개 weekly return이 모두 하락이면 전량 편출한다.
- 두 번째 하락 주의 마지막 available trading day에 signal이 확정된다.

### Neutral / opposite signal

- 비보유 자산이 Entry 조건을 만족하지 않으면 현금 상태를 유지한다.
- 보유 자산이 Exit 조건을 만족하지 않으면 보유 상태를 유지한다.
- 단일 상승/하락이나 neutral week는 그 자체로 진입/편출을 발생시키지 않는다.

## 5. Execution timing

- signal date: 해당 주의 마지막 available trading day
- execution: signal 확정 후 다음 거래일
- signal 계산에는 execution-day 가격을 사용하지 않는다.

## 6. Portfolio construction

초기 baseline은 fixed slot `1/N` 방식이다.

```text
per-asset target weight = 1 / N
```

현재 Universe에서는 약 `9.09%`다.

운영 규칙:

- Entry 발생 시 해당 자산을 `1/N` 슬롯으로 편입한다.
- Exit 발생 시 해당 자산의 target weight를 0으로 만든다.
- 비어 있는 슬롯은 현금으로 유지한다.
- 다른 active 자산에 빈 슬롯을 재분배하지 않는다.
- 상태 변화가 발생한 execution day에는 active 자산을 각 `1/N` target weight로 맞춘다.
- 상태 변화가 없는 주에는 단순 weight drift만으로 재리밸런싱하지 않는다.

첫 run에서 현금 비중이 과도하면 `2/N` exposure 실험을 별도 run으로 비교한다. `2/N`에서 active 자산이 많아 총 target weight가 100%를 넘는 경우의 처리 방식은 첫 `1/N` 결과를 본 뒤 결정한다.

## 7. Execution settings

- initial cash: `1,000,000 USD`
- fee_rate: project default
- slippage_bps: project default

## 8. Benchmarks / validation

첫 baseline 비교 대상:

- `Universe Equal Weight Buy & Hold`: 동일 11개 Universe를 최초 `1/N`으로 편입 후 보유
- `SPY Buy & Hold`

기본 성과는 Runtime performance series를 기준으로 측정한다.

주요 검증 관점:

- total return / CAGR
- volatility / Sharpe / MDD
- avg monthly turnover
- 평균 및 시계열 market exposure
- 현금 비중
- active position 수
- 진입/편출 빈도

## 9. Outputs

- `performance_summary.csv`
  - strategy
  - start_date
  - end_date
  - total_return
  - cagr
  - volatility
  - sharpe
  - max_drawdown
  - avg_monthly_turnover
  - avg_exposure
- `equity_curves.csv`
- `weekly_decisions.csv`
  - signal_date
  - execution_date
  - symbol
  - weekly_return_1
  - weekly_return_2
  - rise_2w
  - fall_2w
  - action
  - active_before
  - active_after
  - target_weight
  - move_threshold
- `exposure.csv`
  - timestamp
  - invested_weight
  - cash_weight
  - active_positions

## 10. Pytest scenarios

Synthetic data를 사용하며 외부 네트워크에 의존하지 않는다.

1. calendar week의 마지막 available trading day가 주봉 종가로 사용된다.
2. baseline `move_threshold=0`과 양수 threshold가 구분되어 동작한다.
3. 2회 연속 상승 후 다음 거래일에 편입한다.
4. 2회 연속 하락 후 다음 거래일에 편출한다.
5. execution-day 가격을 크게 변경해도 해당 signal은 변하지 않는다.
6. `1/N` 슬롯만 사용하고 남는 자금은 현금으로 유지한다.
7. 상태 변화가 없는 주에는 불필요한 재리밸런싱이 발생하지 않는다.
8. active start 이전 warm-up 주봉은 signal 계산에 사용되지만 warm-up 거래는 발생하지 않는다.
9. 동일 입력은 동일 fills를 생성한다.
10. `performance_summary`, `equity_curves`, `weekly_decisions`, `exposure` output smoke test를 수행한다.

## 11. Implementation boundary

- Strategy: `src/backtest_lab/strategies/weekly_trend/r01.py`
- Strategy package: `src/backtest_lab/strategies/weekly_trend/__init__.py`
- Tests: `tests/strategies/weekly_trend/test_r01.py`
- E2E runner: `src/backtest_lab/weekly_trend_pilot.py`
- Run: `runs/weekly_trend/r01/<run_id>/`

기존 `market_momentum` 구현을 복사하지 않고 현재 Runtime/StrategyContext와 필요한 target-weight 주문 패턴만 사용한다.

## 12. Acceptance criteria

- targeted synthetic pytest가 모두 통과한다.
- 공통/core 회귀가 발생하지 않는다.
- Yahoo Finance 실제 데이터로 `2016-07-01 ~ 2026-07-31` active run이 완료된다.
- 기존 run을 덮어쓰지 않고 `runs/weekly_trend/r01/<run_id>/`에 4개 output을 생성한다.
- 첫 E2E 결과에서 평균 exposure와 cash 비중을 확인해 `1/N` 유지 또는 `2/N` 후속 실험 여부를 판단할 수 있어야 한다.

## 13. Open decisions after first run

- 상승 / 하락 최소 폭(`move_threshold`)
- `1/N`의 현금 비중이 과도한지
- 필요 시 `2/N` 적용
- `2/N`에서 총 target weight가 100%를 넘는 경우의 처리 방식
- 첫 결과에서 필요한 추가 분석 output
