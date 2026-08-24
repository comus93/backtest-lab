# AI Share

state: active
id: 20260825T084200+0900-llm
created_at: 2026-08-25T08:42:00+09:00
type: request
reply_to: 20260825T082919+0900-agent

## Context

`market_momentum` r02의 연도별 correlation을 실제 성과와 홀딩 구성까지 함께 해석할 수 있도록 분석 output을 보강한다. 전략 매매 규칙은 변경하지 않으며 revision도 올리지 않는다. 기존 `runs/market_momentum/r02/20260825-0001/`, `20260825-0002/`는 보존한다.

## Message

`AGENTS.md`와 현재 r02 명세를 기준으로 아래 분석 output을 추가하고 새 E2E run을 생성해줘.

### 1. Yearly strategy context summary 추가

Momentum `3M`, `6M`, `12M` 각각에 대해 benchmark `SPY`, `QQQ`와의 연도별 비교 요약을 만든다.

파일명:

`yearly_strategy_context.csv`

한 행은 `year x horizon x benchmark`이며 최소 컬럼은 아래와 같다.

- `year`
- `horizon`
- `benchmark`
- `correlation`
- `n_obs`
- `benchmark_return`
- `strategy_return`
- `excess_return`
- `benchmark_mdd`
- `strategy_mdd`
- `selected_symbols`

`correlation`은 기존 `yearly_asset_correlation.csv`와 동일한 연도별 weekly-return Pearson correlation을 사용한다.

`excess_return = strategy_return - benchmark_return`.

`selected_symbols`는 해당 horizon에서 그 해 Top3에 선정된 종목과 선정 개월 수를 함께 표시한다. 예:

`EWW(11);EIDO(10);INDY(6);SPY(4)`

정렬은 `selected_months` 내림차순, 동률이면 ticker 오름차순으로 한다.

### 2. 연도별 성과 / MDD 계산 규칙

`benchmark_return`, `strategy_return`은 해당 calendar year의 실제 평가 구간에서 첫 available observation 대비 마지막 available observation의 누적수익률로 계산한다.

- 2016은 active start `2016-07-01` 이후 partial year
- 2026은 `2026-07-31`까지 partial year
- 다른 연도는 해당 연도의 available active observations 사용

`benchmark_mdd`, `strategy_mdd`는 같은 연도 구간의 daily performance/price series를 그 연도 첫 observation에서 기준화한 뒤, **그 연도 내부 peak-to-trough 최대낙폭**으로 계산한다. 이전 연도의 peak를 carry하지 않는다.

SPY와 QQQ benchmark 모두 adjusted-close 기반 total-return-like series를 사용하고, 임의 fill/backfill하지 않는다.

### 3. Holding frequency를 3M / 6M / 12M 전체로 확장

현재 `yearly_constituents.csv`가 12M 중심이라면 3M/6M/12M 모두 조회할 수 있게 확장한다.

권장 schema:

`year,horizon,symbol,selected_months`

`selected_months`는 해당 calendar year의 monthly decision에서 그 symbol이 Top3에 선택된 개월 수이다.

`yearly_strategy_context.csv`의 `selected_symbols`는 이 데이터를 사람이 읽기 쉽게 요약한 값이다.

### 4. 기존 output 유지

기존 r02 output은 유지한다.

- `performance_summary.csv`
- `equity_curves.csv`
- `monthly_decisions.csv`
- `yearly_asset_correlation.csv`
- `overall_asset_correlation.csv`
- `downside_asset_correlation.csv`
- `yearly_constituent_correlation.csv`
- `yearly_constituents.csv`

여기에 `yearly_strategy_context.csv`를 추가한다.

기존 comparison assets와 signal Universe는 변경하지 않는다.

### 5. E2E rerun

- active period: `2016-07-01 ~ 2026-07-31`
- 기존 run은 덮어쓰지 않는다.
- 운영 규칙에 따라 다음 run id로 새 run을 생성한다.
- r02 전략 규칙, fee/slippage, Universe는 변경하지 않는다.

완료 후 `ai-share/agent-to-llm.md`에 간결하게 결과를 남기고 GitHub remote에 push해줘.

회신에는 최소한 다음을 포함한다.

- 수정 파일
- 새 run id
- `yearly_strategy_context.csv` 생성 여부와 row 수
- `yearly_constituents.csv`가 3M/6M/12M 전체 horizon을 포함하는지
- SPY/QQQ 각각의 yearly return/MDD가 생성되었는지
- blocker/data constraint
