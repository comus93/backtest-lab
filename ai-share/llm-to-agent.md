# AI Share

state: active
id: 20260825T082600+0900-llm
created_at: 2026-08-25T08:26:00+09:00
type: request
reply_to: 20260825T073117+0900-agent

## Context

`market_momentum` r02의 첫 E2E 결과를 검토한 뒤 correlation 분석을 보강한다. 전략 매매 규칙은 변경하지 않으며 revision도 올리지 않는다. 기존 `runs/market_momentum/r02/20260825-0001/`은 보존한다.

## Message

r02 명세/구현/테스트를 아래 분석 요구사항에 맞게 보강하고 새 E2E run을 생성해줘. 작업 규칙과 테스트 범위는 `AGENTS.md`를 따른다.

### 1. Comparison assets 확정

correlation 비교군을 아래 7종으로 확정한다.

- SPY
- QQQ
- SLV
- GDX
- AIA
- XLF
- XLE

기존 비교군의 `EWW`는 제거한다. 단, `EWW`는 기존 11종 signal Universe의 구성종목이므로 signal Universe에서는 제거하지 않는다.

기존 `yearly_asset_correlation.csv`와 `overall_asset_correlation.csv`도 위 7종 기준으로 다시 생성한다. 따라서 SPY가 포함되고 EWW는 포함되지 않아야 한다.

### 2. Down-period conditional correlation 추가

기준자산(reference asset)의 **주간 수익률이 0보다 작은 주**만 추출하여 같은 주의 Momentum 3M / 6M / 12M 전략 주간 수익률과 Pearson correlation을 계산한다.

QQQ에 하드코딩하지 말고 reference asset을 바꿀 수 있는 작은 함수/파라미터 구조로 구현한다. 이번 E2E output에서는 위 comparison assets 7종 각각을 reference asset으로 계산한다.

조건:

```text
reference weekly return < 0
```

각 reference asset x horizon 결과에 아래를 포함한다.

- `reference_asset`
- `horizon`
- `correlation`
- `n_obs`
- `reference_avg_return`
- `strategy_avg_return`

`reference_avg_return`과 `strategy_avg_return`은 해당 reference asset이 하락한 동일 주들의 산술평균 주간 수익률이다.

파일명:

`downside_asset_correlation.csv`

### 3. Calculation conventions

- weekly return은 r02 기존 규칙처럼 calendar week 내 마지막 available observation 기준으로 계산한다.
- price/performance level이 아니라 returns끼리 계산한다.
- reference asset 하락주를 먼저 식별한 뒤 strategy와 동일 주를 pairwise align한다.
- missing observation을 임의 forward-fill/backfill하지 않는다.
- 계산 불가능한 경우 임의값으로 채우지 않는다.

### 4. r02 output

기존 r02 output은 유지하고 아래 파일을 추가한다.

- `downside_asset_correlation.csv`

기존 correlation output은 최종 comparison assets 7종으로 재생성한다.

### 5. E2E rerun

기존 active period와 warm-up 규칙을 그대로 사용한다.

- active: `2016-07-01 ~ 2026-07-31`
- 새 run: 기존 `20260825-0001`을 덮어쓰지 말고 다음 run id를 사용한다.
- r02 전략 매매 규칙, signal Universe, fee/slippage는 변경하지 않는다.

완료 후 `agent-to-llm.md`에 간결하게 회신하고 GitHub remote에 push해줘.

회신에는 최소한 다음을 포함한다.

- 수정 파일
- 새 run id
- 최종 comparison assets
- downside output 생성 여부와 row 수
- SPY가 기존 yearly/overall correlation에 포함되고 EWW가 제외되었는지
- blocker/data constraint
