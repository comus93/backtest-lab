# AI Share

state: active
id: 20260825T072200+0900-llm
created_at: 2026-08-25T07:22:00+09:00
type: request
reply_to: none

## Context

사용자가 `market_momentum`의 다음 revision을 `r02`로 올리기로 결정했다. r01은 보존한다.

r02의 목적은 단독 성과 최적화보다, 3M/6M/12M 상대모멘텀 전략이 기존 포트폴리오 자산과 얼마나 상호보완적인지 상관관계로 검증하는 것이다.

장기 E2E 검증에 사용한 Universe를 기준으로 `VNAM`, `KTEC`, `KSTR`는 제외하고 아래 11종을 사용한다.

`SPY, QQQ, DIA, EWJ, EWY, MCHI, DAX, EWW, EIDO, INDY, EPHE`

검증 active 기간은 `2016-07-01 ~ 2026-07-31`로 하고, 12M 계산에 필요한 warm-up은 그 이전부터 로드한다.

## Message

### 1. r02 생성

- 새 명세: `doc/strategies/20260825-market-momentum-r02.md`
- 새 Strategy: `src/backtest_lab/strategies/market_momentum/r02.py`
- 새 tests: `tests/strategies/market_momentum/test_r02.py`
- `STRATEGY_ID = "market_momentum"`, `REVISION = "r02"`
- r01 명세/구현/tests/run은 변경하거나 덮어쓰지 않는다.
- core abstraction은 확대하지 않는다. r01 구현을 재사용할 수 있으면 단순하게 재사용한다.

### 2. Momentum strategies

r02에서 비교할 momentum horizon은 아래 3개다.

- 3M
- 6M
- 12M

각 horizon은 r01과 같은 calendar-month momentum 정의, Top3 선택, 각 1/3 동일비중, 월말 signal -> 다음 거래일 실행 규칙을 유지한다.

9M은 r02 비교 대상에서 제외한다.

성과 비교용 `performance_summary`와 `equity_curves`에는 최소 Momentum 3M / 6M / 12M과 SPY Buy & Hold를 포함한다. 필요하면 Static Equal Weight도 유지해도 되지만 correlation 핵심 범위는 위 3 horizon이다.

### 3. Correlation comparison assets

아래 ticker만 비교군으로 사용한다. 숫자 비중은 없으며 ticker 자체만 사용한다.

- QQQ
- SLV
- GDX
- AIA
- XLF
- XLE
- EWW

비교군은 전략 signal Universe를 변경하지 않는다.

### 4. Yearly strategy-to-asset correlation

각 calendar year별로 Momentum 3M / 6M / 12M 전략 수익률과 위 7개 비교자산 수익률의 Pearson correlation을 계산한다.

기준은 **주간 수익률**이다.

- Strategy: 해당 strategy performance series에서 각 주의 마지막 관측값을 사용해 weekly return 계산
- Asset: adjusted close에서 각 주의 마지막 거래 가능 관측값을 사용해 weekly return 계산
- price level끼리 correlation하지 않는다.
- 동일 주간 관측값끼리 pairwise align한다.
- partial year인 2016/2026도 실제 존재하는 주간 관측치로 계산한다.
- 결과에 `n_obs`를 포함해 표본 수를 확인할 수 있게 한다.

출력 예시 long format:

`year,horizon,asset,correlation,n_obs`

파일: `yearly_asset_correlation.csv`

### 5. Overall strategy-to-asset correlation

전체 active 기간 `2016-07-01 ~ 2026-07-31`에 대해 같은 3개 horizon x 7개 비교자산 correlation을 계산한다.

전체기간에서는 두 frequency를 모두 계산한다.

- weekly return correlation
- monthly return correlation

출력 예시:

`frequency,horizon,asset,correlation,n_obs`

파일: `overall_asset_correlation.csv`

### 6. Yearly 12M constituent correlation matrix

12M Momentum 전략에 대해 calendar year별 구성종목 간 correlation을 계산한다.

- 해당 year에 월별 Top3로 **한 번이라도 selected 된 symbol의 union**을 그 해 constituent set으로 정의한다.
- 그 constituent set 종목들의 해당 calendar year 전체 주간 adjusted-close 수익률을 사용한다.
- weekly return Pearson correlation을 계산한다.
- matrix 저장은 wide matrix보다 분석/후처리가 쉬운 long format을 사용한다.

출력:

`year,symbol_a,symbol_b,correlation,n_obs`

파일: `yearly_constituent_correlation.csv`

해석을 위해 constituent 목록과 보유 빈도도 별도 출력한다.

`year,symbol,selected_months`

파일: `yearly_constituents.csv`

### 7. Existing trace outputs

r02에서도 판단 추적이 가능하도록 `monthly_decisions.csv`를 유지한다.

최소 columns는 r01과 동일:

`horizon,signal_date,execution_date,symbol,momentum,rank,selected,target_weight`

3M/6M/12M만 기록한다.

### 8. Correlation calculation conventions

- returns끼리 계산하고 price/performance level끼리 계산하지 않는다.
- weekly resample은 calendar week 내 마지막 available observation 기준으로 일관되게 구현한다.
- monthly resample은 calendar month 내 마지막 available observation 기준으로 구현한다.
- pairwise missing data는 공통 관측치만 사용한다.
- correlation을 계산할 수 없는 경우 임의값으로 채우지 않는다.
- data leakage나 forward fill로 존재하지 않는 시장가격을 생성하지 않는다.

### 9. Pytest scenarios

synthetic 날짜/가격 값은 Codex가 사람이 검산하기 쉬운 값으로 정한다. 외부 network에 의존하지 않는다.

최소 아래 의미를 검증한다.

1. r02가 3M/6M/12M만 독립 실행하며 9M을 포함하지 않는다.
2. yearly asset correlation이 price level이 아니라 weekly returns로 계산된다.
3. horizon별 strategy series가 섞이지 않고 각각 별도 correlation을 만든다.
4. 비교군은 정확히 `QQQ, SLV, GDX, AIA, XLF, XLE, EWW`이며 signal Universe에는 들어가지 않는다.
5. overall correlation이 weekly와 monthly를 각각 생성한다.
6. 12M yearly constituent set은 그 해 한 번이라도 selected된 symbol의 union이고, 한 번도 selected되지 않은 symbol은 matrix 대상에서 제외한다.
7. yearly constituent correlation은 weekly returns 기준이며 `selected_months` 집계가 맞다.
8. pairwise alignment와 `n_obs`가 기대대로 계산된다.
9. 기존 r01 핵심 signal/execution semantics가 r02에서도 유지된다.
10. r02 분석 output 필수 파일/columns가 생성된다.

### 10. E2E run

pytest 통과 후 Yahoo Finance 실제 데이터로 r02 E2E를 실행한다.

- active period: `2016-07-01 ~ 2026-07-31`
- warm-up: 12M signal 계산 가능하도록 이전 history 포함
- fee/slippage: 현재 프로젝트 canonical/global 설정 사용
- 새 run directory 생성: `runs/market_momentum/r02/<YYYYMMDD-NNNN>/`
- 기존 run은 절대 덮어쓰지 않는다.

최소 산출물:

- `performance_summary.csv`
- `equity_curves.csv`
- `monthly_decisions.csv`
- `yearly_asset_correlation.csv`
- `overall_asset_correlation.csv`
- `yearly_constituent_correlation.csv`
- `yearly_constituents.csv`

### Completion

- 전체 `uv run --extra dev pytest` 실행
- r02 E2E 실행 및 새 run 저장
- 결과를 `ai-share/agent-to-llm.md`에 간결하게 남기고 GitHub remote에 push한다.
- 회신에는 아래를 포함한다.
  - 구현/명세/테스트 파일
  - pytest 결과
  - 실제 data coverage와 active 기간
  - 생성된 run id와 산출물 경로
  - 3M/6M/12M 주요 performance
  - yearly/overall correlation output 생성 여부
  - blocker 또는 데이터 제약
