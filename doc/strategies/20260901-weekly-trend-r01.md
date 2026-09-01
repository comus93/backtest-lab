# Weekly Trend

Strategy ID: `weekly_trend`  
Revision: `r01`  
Revision date: `2026-09-01`  
Status: `draft`

## 1. Purpose / hypothesis

주봉 방향의 짧은 연속성이 이후 추세 지속에 유효한 신호인지 검증한다.

기존 `market_momentum`의 월간 cross-sectional relative momentum과는 별도 전략이다. 이 전략은 각 자산의 weekly trend 상태에 따라 개별적으로 편입/편출한다.

핵심 가설:

- 주봉이 2회 연속 상승한 자산은 단기 추세가 이어질 가능성이 있다.
- 보유 중 주봉이 2회 연속 하락하면 추세 약화로 보고 편출한다.
- 신호가 없는 자산 슬롯을 현금으로 유지하면 시장 전체 trend 상태에 따라 총 exposure가 자연스럽게 조절된다.

## 2. Universe

초기 검증은 `market_momentum` r02와 동일한 11개 ETF를 사용한다.

- SPY
- QQQ
- DIA
- EWJ
- EWY
- MCHI
- DAX
- EWW
- EIDO
- INDY
- EPHE

Universe size: `N = 11`

## 3. Data

- Frequency: weekly signal, daily market data에서 calendar week의 마지막 available trading day를 주봉 기준일로 사용
- Price field: TBD
- Data source: TBD
- Currency: USD
- Warm-up: 최소 2개 완성 주봉 이상의 history 필요
- Validation period: TBD

## 4. Signal rules

### Entry

- 비보유 자산이 `2주 연속 상승` 상태가 되면 편입 신호를 발생시킨다.
- 신호는 두 번째 상승 주의 마지막 거래일 데이터가 확정된 뒤 생성한다.

### Exit

- 보유 자산이 `2주 연속 하락` 상태가 되면 전량 편출 신호를 발생시킨다.
- 신호는 두 번째 하락 주의 마지막 거래일 데이터가 확정된 뒤 생성한다.

### Rise / fall definition

상승·하락 판정의 세부 조건은 아직 확정하지 않는다.

예: 단순 전주 종가 대비 방향만 사용할지, 최소 상승/하락 폭 등 추가 조건을 둘지는 초기 검증 설계 과정에서 User와 추가 결정한다.

## 5. Execution timing

- signal date: 해당 주의 마지막 available trading day
- execution: signal 확정 후 다음 거래일
- signal 계산에 execution-day 가격을 사용하지 않는다.

## 6. Portfolio construction

초기 baseline은 fixed slot 방식으로 검증한다.

```text
per-asset target weight = 1 / N
```

현재 Universe에서는:

```text
1 / 11 ≈ 9.09%
```

규칙:

- Entry signal ON 자산은 해당 슬롯 비중만큼 보유한다.
- Exit signal이 발생하면 해당 자산을 전량 편출한다.
- 비어 있는 슬롯의 자금은 현금으로 유지한다.
- 다른 보유 자산에 남는 현금을 재분배하지 않는다.
- 따라서 총 투자비중은 활성 signal 수에 따라 변한다.

초기 run에서 현금 비중이 과도하면 같은 전략에서 exposure parameter를 `2/N`으로 변경한 별도 run을 비교한다.

`1/N`과 `2/N` 비교는 현재 단계에서는 전략 revision 변경이 아니라 run-level exposure 실험으로 취급한다. 실제 구현 전에 최대 총 exposure 처리 방식은 추가 확정한다.

## 7. Execution settings

- initial cash: TBD
- fee_rate: project default
- slippage_bps: project default

## 8. Benchmark / validation

TBD.

최소 검증 관점:

- 전략 전체 성과
- 평균 및 시계열 market exposure
- 현금 비중
- 진입/편출 빈도
- turnover
- benchmark 대비 CAGR / volatility / Sharpe / MDD

기본 성과 측정은 Runtime performance series를 FFN으로 분석한다.

## 9. Expected outputs

최종 구현 명세에서 확정한다.

최소 후보:

- `performance_summary.csv`
- `equity_curves.csv`
- `weekly_decisions.csv`
- `exposure.csv`

## 10. Pytest scenarios

최종 signal 정의와 portfolio 규칙이 확정된 뒤 작성한다.

최소 검증 대상:

1. calendar-week 마지막 거래일을 주봉 기준으로 사용하는지
2. 2회 연속 상승 후 다음 거래일에만 진입하는지
3. 2회 연속 하락 후 다음 거래일에 전량 편출하는지
4. execution-day 가격이 signal에 누출되지 않는지
5. `1/N` fixed slot이 유지되고 빈 슬롯이 현금으로 남는지
6. 동일 입력에서 결과가 deterministic한지

## 11. Implementation boundary

예정 위치:

- Strategy: `src/backtest_lab/strategies/weekly_trend/r01.py`
- Tests: `tests/strategies/weekly_trend/test_r01.py`
- Run: `runs/weekly_trend/r01/<run_id>/`

기존 `market_momentum` 코드를 전략 템플릿처럼 복제하지 않는다. 현재 Runtime, StrategyContext, 공통 target-weight 기능 등 필요한 framework만 재사용한다.

현재 core로 표현하기 어려운 blocker가 발견되면 core를 임의 확장하지 않고 별도 engine issue로 분리한다.

## 12. Open decisions before implementation

- 상승 / 하락의 정확한 판정 정의
- Data source / price field
- 검증 기간
- benchmark
- initial cash
- `2/N` 실험 시 총 target weight가 100%를 초과하는 경우의 처리 방식
- 최종 analysis outputs / acceptance criteria
