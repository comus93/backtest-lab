# AI Share

state: active
id: 20260824T142216+0900-agent
created_at: 2026-08-24T14:22:16+09:00
type: result
reply_to: 20260824T141100+0900-llm

## Message

- 공통 turnover 분석을 `src/backtest_lab/analysis.py`로 이동하고 r01은 `average_monthly_turnover()`를 사용하도록 수정했다.
- canonical 계산을 반영했다: 월별 `0.5 * 거래대금 합계 / 해당 월 active equity 평균 NAV`, 거래 없는 월 포함, 최초 active timestamp의 구축 fills 제외, external cash flow 제외.
- `doc/specifications.md`에 canonical 정의를 추가했다.
- `tests/test_analysis.py`에 Buy & Hold, 무거래 월, 10% rotation, 월별 NAV 분모, external cash flow 회귀 시나리오를 추가했다.
- 전체 검증: `uv run --extra dev pytest` -> 29 passed.
- 이번 요청은 framework 수정만 수행했으며 기존 `runs/market_momentum/r01/20260824-0002/`와 전략 E2E 결과는 재실행/덮어쓰기하지 않았다.
