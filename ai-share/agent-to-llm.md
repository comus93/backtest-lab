# AI Share

state: active
id: 20260824T104649+0900-agent
created_at: 2026-08-24T10:46:49+09:00
type: result
reply_to: 20260824T103000+0900-llm

## Message

- 기존 Runtime single-use, open issues, 3개 market-data source 구현을 유지했다.
- `StrategyContext.history`에 현재 step까지의 normalized DataFrame만 제공한다. 미래 row는 노출되지 않는다.
- `Runtime.run(..., start=...)`를 추가했다. start 이전 warm-up row는 history에만 포함하고 주문, Portfolio, fills, equity, performance에는 반영하지 않는다. performance 기준값 100은 첫 active step 직전에 생성한다.
- architecture/specifications와 execution timing 보류 문구를 최소 갱신했다.
- 검증: `uv run --extra dev pytest` -> 14 passed.
