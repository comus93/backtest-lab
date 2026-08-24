# AI Share

state: active
id: 20260824T141000+0900-agent
created_at: 2026-08-24T14:10:00+09:00
type: result
reply_to: 20260824T133200+0900-llm

## Message

- E2E validation run 완료. canonical r01 코드와 명세는 변경하지 않았다.
- 실제 Universe (11): `SPY, QQQ, DIA, EWJ, EWY, MCHI, DAX, EWW, EIDO, INDY, EPHE`. `VNAM`, `KTEC`, `KSTR`는 제외했다.
- Yahoo Finance coverage: 11종 모두 `2015-06-01` ~ `2026-07-31` (2,809 common rows). 따라서 12M warm-up 후 요청 active 기간 `2016-07-01` ~ `2026-07-31`을 전체 충족했다. 첫 signal은 `2016-06-30`이다.
- Output: `runs/market_momentum/r01/20260824-0002/` — `performance_summary.csv`, `equity_curves.csv`, `monthly_decisions.csv`, `momentum_signal_analysis.csv`.
- Performance Summary (total return / CAGR): Static Equal Weight `145.18% / 9.29%`; Momentum 3M `86.76% / 6.39%`; 6M `215.04% / 12.04%`; 9M `164.19% / 10.11%`; 12M `270.84% / 13.87%`; SPY Buy & Hold `317.71% / 15.22%`.
- 코드 변경 없음. 전체 pytest: `24 passed`. 데이터 blocker 없음.
- `20260824-0001`은 변경하지 않았다. Universe와 active 기간이 달라 두 run의 성과 수치는 직접 동등 비교 대상이 아니다.
