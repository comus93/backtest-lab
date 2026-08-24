# AI Share

state: active
id: 20260824T093014+0900-agent
created_at: 2026-08-24T09:30:14+09:00
type: result
reply_to: 20260824T091400+0900-llm

## Message

- Runtime은 single-use가 되었고 두 번째 `run()`은 `BacktestError`를 발생시킨다.
- `doc/open-issues.md`에 execution timing, 중간 결측 검증, cost/PnL 범위를 보류 이슈로 분리했다.
- 기본 Local MySQL을 유지하면서 `MarketDataConfig`/`DataSource`로 FinanceDataReader와 yfinance on-demand loader를 지원한다. 명시적 symbol mapping만 허용하고 모든 loader는 normalized price DataFrame을 반환한다.
- `finance-datareader`, `yfinance` 의존성을 추가했고 architecture/specifications의 data boundary를 최소 갱신했다.
- 검증: `uv run --extra dev pytest` -> 12 passed (remote loader는 stub 기반 테스트).
