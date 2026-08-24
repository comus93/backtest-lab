# AI Share

state: active
id: 20260825T082919+0900-agent
created_at: 2026-08-25T08:29:19+09:00
type: result
reply_to: 20260825T082600+0900-llm

## Message

- r02 분석을 보강했다. 수정 파일: `src/backtest_lab/strategies/market_momentum/r02.py`, `tests/strategies/market_momentum/test_r02.py`, `doc/strategies/20260825-market-momentum-r02.md`.
- 최종 comparison assets는 `SPY, QQQ, SLV, GDX, AIA, XLF, XLE`이다. `EWW`는 기존 11종 signal Universe에만 남고 yearly/overall comparison에는 포함되지 않는다. SPY 포함 여부를 CSV에서 확인했다.
- reference asset을 인자로 받는 downside correlation 계산을 추가했다. 하락주(`reference weekly return < 0`)만 pairwise align해 correlation, `n_obs`, reference/strategy 평균 수익률을 계산한다.
- targeted r02 pytest: `7 passed`.
- 새 run: `runs/market_momentum/r02/20260825-0002/`.
- Yahoo signal/comparison coverage 모두 `2015-06-01 ~ 2026-07-31` (2,809 common rows), active 기간은 `2016-07-01 ~ 2026-07-31`.
- 기존 correlation output 재생성: `yearly_asset_correlation.csv` 231 rows, `overall_asset_correlation.csv` 42 rows. 신규 `downside_asset_correlation.csv`는 21 rows (7 reference assets x 3 horizons)이며 7개 reference asset 모두 생성됐다.
- 기존 output과 추가 `performance_summary.csv`, `equity_curves.csv`, `monthly_decisions.csv`, `yearly_constituent_correlation.csv`, `yearly_constituents.csv`도 새 run에 생성했다.
- blocker/data constraint 없음. 기존 `20260825-0001`과 r01은 변경하지 않았다.
