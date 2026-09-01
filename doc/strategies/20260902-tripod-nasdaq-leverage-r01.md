# Tripod Nasdaq Leverage

Strategy ID: `tripod_nasdaq_leverage`  
Revision: `r01`  
Revision date: `2026-09-02`  
Status: `ready-for-implementation`

## 1. Purpose / hypothesis

NASDAQ-100의 장기 추세, 변동성, 52주 낙폭을 결합하여 0x / 1.5x / 3x의 노출을 동적으로 전환하는 전략을 재현 검증한다.

1차 실험의 목적은 원 전략의 파라미터를 변경하거나 최적화하는 것이 아니라, 명세 그대로 구현했을 때의 실제 성과와 위험 특성을 확인하는 것이다.

핵심 평가 관점:

- 3x 레버리지를 적극적으로 사용하면서도 큰 하락 구간에서 exposure를 1.5x 또는 0x로 줄여 손실을 완화하는지
- QQQ / QLD / TQQQ Buy & Hold 대비 CAGR, MDD, Sharpe 등 위험조정 성과가 개선되는지
- 성과 개선이 특정 파라미터에 과도하게 의존하는지 여부는 r01 이후 별도 민감도 실험에서 검증한다.

## 2. Assets / data roles

### Signal assets

- NASDAQ-100 index: `^NDX`
- VIX index: `^VIX`

Signal assets는 전략 신호 계산에만 사용하며 직접 매매하지 않는다.

### Tradable assets

- `QQQ`: NASDAQ-100 1x
- `QLD`: NASDAQ-100 daily 2x
- `TQQQ`: NASDAQ-100 daily 3x
- `CASH`: 현금

### Data source / price field

- Data source: Yahoo Finance
- `^NDX`: Close
- `^VIX`: Close
- `QQQ`, `QLD`, `TQQQ`: Adjusted Close
- Currency: USD
- Missing signal/tradable data는 임의 forward-fill/backfill 하지 않는다.
- Symbol mapping은 명시적으로 유지한다.

## 3. Validation period / warm-up

### Active period

QQQ, QLD, TQQQ, ^NDX, ^VIX가 모두 사용 가능한 공통 기간 중 최대한 긴 구간을 사용한다.

- active start는 E2E 실행 시 실제 공통 coverage를 기준으로 결정하고 run output에 기록한다.
- active end도 실제 data coverage 기준으로 기록한다.

### Warm-up

Signal 계산을 위해 active start 이전 데이터가 필요하다.

최소 warm-up 요구:

- SMA250: 250 trading observations
- High252: 252 trading observations
- VIX10: 10 trading observations

따라서 active start 이전에 최소 252 거래일 이상의 signal history를 확보한다.

Warm-up 구간에서는 주문, fill, portfolio valuation, performance 생성이 발생하지 않는다.

## 4. Signal timing

- Signal frequency: Daily
- Signal observation: T일 장 종료 후 종가 기준
- Execution: T+1 다음 거래일
- execution-day 가격은 T일 signal 계산에 절대 사용하지 않는다.
- T일 종가로 Target Portfolio가 바뀌었을 때만 T+1에 리밸런싱 주문을 생성한다.

## 5. Trend

NASDAQ-100 종가와 250거래일 단순이동평균을 사용한다.

```text
SMA250 = mean(NDX Close, last 250 trading observations)
trend_ratio = NDX_Close / SMA250 - 1
```

Trend 상태 전환:

```text
if NDX_Close >= SMA250 * 1.01:
    Trend = UP
elif NDX_Close <= SMA250 * 0.95:
    Trend = DOWN
else:
    Trend = previous Trend
```

동일 표현:

- `trend_ratio >= +0.01` -> `UP`
- `trend_ratio <= -0.05` -> `DOWN`
- `-0.05 < trend_ratio < +0.01` -> previous Trend 유지

즉 +1% / -5%의 비대칭 hysteresis를 사용한다.

## 6. Initial Trend state

백테스트 시작 시 Trend는 `UNKNOWN`으로 초기화한다.

```text
Trend = UNKNOWN
Target = CASH 100%
```

이후 최초로 아래 둘 중 하나가 발생할 때 Trend 상태를 시작한다.

- `NDX_Close >= SMA250 * 1.01` -> `UP`
- `NDX_Close <= SMA250 * 0.95` -> `DOWN`

그 전까지는 CASH 100%를 유지한다.

## 7. Volatility

VIX의 최근 10거래일 단순이동평균을 사용한다.

```text
VIX10 = mean(VIX Close, last 10 trading observations)
```

Threshold:

- UP regime risk threshold: `28`
- DOWN regime low-vol threshold: `18`

## 8. 52-week drawdown

NASDAQ-100의 최근 252거래일 최고 종가 대비 현재 낙폭을 계산한다.

```text
High252 = max(NDX Close, last 252 trading observations)
DD52 = NDX_Close / High252 - 1
```

Drawdown threshold:

```text
-0.09
```

Boundary rule:

- `DD52 >= -0.09` -> small drawdown 조건 충족
- `DD52 < -0.09` -> risk signal

## 9. Target portfolio rules

### Case 1: UP + low volatility + small drawdown

조건:

```text
Trend == UP
AND VIX10 < 28
AND DD52 >= -0.09
```

Target:

```text
TQQQ 100%
```

Nominal NASDAQ exposure: `3.0x`

### Case 2: UP + risk signal

조건:

```text
Trend == UP
AND (
    VIX10 >= 28
    OR DD52 < -0.09
)
```

Target:

```text
QQQ 50%
QLD 50%
```

Nominal NASDAQ exposure: `1.5x`

### Case 3: DOWN + low volatility

조건:

```text
Trend == DOWN
AND VIX10 < 18
```

Target:

```text
QQQ 50%
QLD 50%
```

Nominal NASDAQ exposure: `1.5x`

### Case 4: DOWN + high volatility

조건:

```text
Trend == DOWN
AND VIX10 >= 18
```

Target:

```text
CASH 100%
```

Nominal NASDAQ exposure: `0x`

## 10. Boundary semantics

Threshold equality를 다음처럼 고정한다.

- Trend UP: `>= +1%`
- Trend DOWN: `<= -5%`
- UP low volatility: `VIX10 < 28`
- UP high-risk volatility: `VIX10 >= 28`
- DOWN low volatility: `VIX10 < 18`
- DOWN high volatility: `VIX10 >= 18`
- small drawdown: `DD52 >= -9%`
- drawdown risk: `DD52 < -9%`

## 11. Rebalance / execution

매 거래일 T 종료 후 signal과 target을 계산한다.

- 현재 Target Portfolio와 새 Target Portfolio가 같으면 주문을 생성하지 않는다.
- Target이 달라질 때만 다음 거래일 T+1에 target-weight 주문을 실행한다.
- Sell orders는 buy orders보다 먼저 처리하는 현재 Runtime 규칙을 따른다.
- target weights는 해당 execution step의 portfolio value를 기준으로 계산한다.
- contribution: 없음
- tax: 제외
- transaction cost / slippage: project global settings 사용
- initial cash: `1,000,000 USD`

## 12. Benchmark

동일 active period에서 아래를 비교한다.

1. `QQQ Buy & Hold`
2. `QLD Buy & Hold`
3. `TQQQ Buy & Hold`
4. `Tripod Strategy`

추가 비교 후보인 단순 1x / 2x Gear Strategy는 r01 필수 범위에서 제외한다. 필요 시 별도 run 또는 후속 revision/strategy 실험으로 추가한다.

## 13. Performance measurement

전략 및 모든 benchmark의 performance series는 Runtime에서 생성한다.

성과 측정의 표준은 FFN이다.

각 strategy/benchmark에 대해 `BacktestResult.ffn_stats()` 또는 동일한 FFN `calc_stats()` 결과를 사용한다.

### FFN default stats output

FFN이 해당 performance series에 대해 기본 제공하는 stats를 임의 축소하지 않고 CSV로 저장한다.

파일:

```text
ffn_stats.csv
```

권장 형태:

```text
metric,Tripod Strategy,QQQ Buy & Hold,QLD Buy & Hold,TQQQ Buy & Hold
```

FFN version에서 제공되는 default metric set을 그대로 사용한다. 예시는 다음과 같으며, 실제 저장 기준은 설치된 FFN의 `calc_stats()` 결과다.

- Start
- End
- Risk-free rate
- Total Return
- Daily Sharpe
- Daily Sortino
- CAGR
- Max Drawdown
- Calmar Ratio
- MTD
- 3m
- 6m
- YTD
- 1Y
- 3Y (ann.)
- 5Y (ann.)
- 10Y (ann.)
- Since Incep. (ann.)
- Daily Volatility
- Monthly Volatility
- Yearly Volatility
- Best Day
- Worst Day
- Best Month
- Worst Month
- Best Year
- Worst Year
- Avg. Drawdown
- Avg. Drawdown Days
- Avg. Up Month
- Avg. Down Month
- Win Year %
- Win 12m %

FFN version 차이로 metric 이름 또는 제공 항목이 일부 달라질 경우, 설치된 FFN의 실제 default output을 source of truth로 한다.

### Human-readable performance summary

FFN 전체 stats와 별도로 핵심 비교용 파일을 제공한다.

파일:

```text
performance_summary.csv
```

최소 컬럼:

- `strategy`
- `start_date`
- `end_date`
- `total_return`
- `cagr`
- `volatility`
- `sharpe`
- `max_drawdown`
- `calmar`
- `avg_monthly_turnover`
- `avg_nominal_exposure`

가능하면 `total_return`, `cagr`, `volatility`, `sharpe`, `max_drawdown`, `calmar`는 FFN stats에서 가져오고 동일 지표를 별도 수식으로 중복 계산하지 않는다.

Turnover는 project canonical `average_monthly_turnover()` 정의를 사용한다.

## 14. Strategy-specific analysis outputs

### 14.1 equity_curves.csv

각 전략/benchmark의 Runtime performance series.

최소 컬럼:

- `Tripod Strategy`
- `QQQ Buy & Hold`
- `QLD Buy & Hold`
- `TQQQ Buy & Hold`

Index:

- `timestamp`

### 14.2 daily_signals.csv

Tripod의 일별 signal 상태와 target 기록.

최소 컬럼:

- `signal_date`
- `execution_date`
- `ndx_close`
- `sma250`
- `trend_ratio`
- `trend`
- `vix_close`
- `vix10`
- `high252`
- `dd52`
- `regime`
- `target_qqq`
- `target_qld`
- `target_tqqq`
- `target_cash`
- `nominal_exposure`
- `target_changed`

`execution_date`는 실제 다음 trading day가 존재하는 경우 기록한다.

### 14.3 regime_summary.csv

각 regime의 체류 비중과 성과 해석을 위한 요약.

최소 컬럼:

- `regime`
- `days`
- `share_of_active_days`
- `nominal_exposure`

Regime names:

- `UP_LOW_RISK_3X`
- `UP_RISK_1_5X`
- `DOWN_LOW_VOL_1_5X`
- `DOWN_HIGH_VOL_CASH`
- `INITIAL_UNKNOWN_CASH`

### 14.4 yearly_performance.csv

Tripod 및 benchmark의 calendar-year 성과를 비교한다.

최소 컬럼:

- `year`
- `strategy`
- `return`
- `max_drawdown`

첫해/마지막해가 partial year이면 실제 active observations만 사용한다.

연도별 MDD는 해당 calendar year 내부에서 기준화하여 계산하고 전년도 peak를 carry하지 않는다.

### 14.5 exposure.csv

Tripod의 actual target exposure 시계열을 저장한다.

최소 컬럼:

- `timestamp`
- `trend`
- `regime`
- `qqq_weight`
- `qld_weight`
- `tqqq_weight`
- `cash_weight`
- `nominal_exposure`

## 15. Expected run artifacts

Run path:

```text
runs/tripod_nasdaq_leverage/r01/<run_id>/
```

필수 output:

- `ffn_stats.csv`
- `performance_summary.csv`
- `equity_curves.csv`
- `daily_signals.csv`
- `regime_summary.csv`
- `yearly_performance.csv`
- `exposure.csv`

LLM이 run을 분석할 경우 분석 문서는 동일 run directory에 저장한다. 파일명은 사용자 지시가 있으면 그 이름을 따른다.

## 16. Pytest scenarios

Strategy correctness는 synthetic data로 검증하며 외부 network에 의존하지 않는다.

최소 테스트:

1. `SMA250`이 현재 signal date까지의 마지막 250 observations만 사용하는지
2. `High252`가 현재 signal date까지의 마지막 252 observations만 사용하는지
3. `VIX10`이 현재 signal date까지의 마지막 10 observations만 사용하는지
4. `trend_ratio >= +1%`에서 UP으로 전환되는지
5. `trend_ratio <= -5%`에서 DOWN으로 전환되는지
6. neutral zone에서 previous Trend가 유지되는지
7. initial UNKNOWN 상태에서 threshold 미충족 시 CASH를 유지하는지
8. 최초 UP threshold 충족 시 UP 상태가 시작되는지
9. 최초 DOWN threshold 충족 시 DOWN 상태가 시작되는지
10. `UP / VIX10 < 28 / DD52 >= -9%` -> TQQQ 100%
11. `UP / VIX10 >= 28` -> QQQ 50% + QLD 50%
12. `UP / DD52 < -9%` -> QQQ 50% + QLD 50%
13. `DOWN / VIX10 < 18` -> QQQ 50% + QLD 50%
14. `DOWN / VIX10 >= 18` -> CASH 100%
15. VIX 18/28 및 DD -9%, Trend +1%/-5% equality boundary가 명세와 동일한지
16. T signal 이후 T+1 거래일에만 execution되는지
17. execution-day price 변경이 T signal을 바꾸지 않는지
18. Target Portfolio가 동일한 연속 구간에서는 추가 rebalance fill이 없는지
19. Target 변경 시 기존 포지션 청산/신규 포지션 편입 후 target weights가 기대값과 일치하는지
20. warm-up history가 signal 계산에는 사용되지만 warm-up 주문/fill/performance가 생성되지 않는지
21. 동일 입력/settings에서 deterministic한 fills/performance를 생성하는지
22. `ffn_stats.csv`가 Tripod + 3 benchmark 전체의 FFN default stats를 포함하는지
23. 필수 output 7개가 모두 생성되고 schema가 기대값과 일치하는지

## 17. Implementation boundary

예정 위치:

```text
src/backtest_lab/strategies/tripod_nasdaq_leverage/r01.py
tests/strategies/tripod_nasdaq_leverage/test_r01.py
```

필요 시 E2E entrypoint는:

```text
src/backtest_lab/tripod_nasdaq_leverage_pilot.py
```

을 사용한다.

현재 Runtime / StrategyContext / target-weight helper / FFN integration / canonical turnover를 우선 재사용한다.

Strategy-specific SMA, hysteresis state, VIX10, DD52, regime 결정 로직은 Strategy module에 둔다.

이 전략 하나를 위해 core에 indicator framework, state machine abstraction, strategy DSL, special leverage model 등을 추가하지 않는다.

현재 engine으로 표현 불가능한 blocker가 발견되면 core를 임의 확장하지 않고 최소 요구 기능과 이유를 별도 engine issue로 정리한다.

## 18. 1st experiment fixed parameters

r01 1차 재현 실험에서는 아래 값을 변경하지 않는다.

```text
SMA window = 250
Trend UP threshold = +0.01
Trend DOWN threshold = -0.05
VIX SMA window = 10
UP VIX threshold = 28
DOWN VIX threshold = 18
Drawdown lookback = 252
Drawdown threshold = -0.09
Exposure states = 0x / 1.5x / 3x
```

파라미터 민감도, 대칭/비대칭 threshold 비교, SMA 기간 변경, VIX threshold 변경, DD threshold 변경 등은 r01 baseline 결과 확인 후 별도 2차 실험으로 수행한다.

## 19. Acceptance criteria

구현 완료 조건:

1. synthetic pytest에서 signal/state/execution 경계가 모두 검증된다.
2. 신규 전략 targeted test가 통과한다.
3. 신규 구현 초기 검증으로 project full pytest를 통과한다.
4. Yahoo Finance real-data E2E가 blocker 없이 완료된다.
5. 실제 active coverage와 warm-up coverage가 run 결과에 기록된다.
6. Tripod + QQQ/QLD/TQQQ benchmark의 FFN default stats가 `ffn_stats.csv`에 저장된다.
7. 필수 strategy-specific output 6개와 `ffn_stats.csv`가 생성된다.
8. 기존 전략/run을 수정하거나 덮어쓰지 않는다.
9. run은 운영 규칙에 따라 신규 `run_id` directory에 저장한다.
10. r01 파라미터는 원 명세 그대로 유지한다.
