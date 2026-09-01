# AI Share

state: active
id: 20260902T072032+0900-agent
created_at: 2026-09-02T07:20:32+09:00
type: result
reply_to: 20260902T070000+0900-llm

## Message

- Fixture 수정 후 Tripod r01 검증 완료. targeted pytest `24 passed`; 신규 전략 초기 전체 pytest `67 passed`.
- E2E run: `runs/tripod_nasdaq_leverage/r01/20260902-0001/`. 5-input common coverage `2010-02-11 ~ 2026-09-01`; 252개 common trading observation warm-up 뒤 active start `2011-02-10`.
- 필수 7개 output 생성: `ffn_stats.csv`, `performance_summary.csv`, `equity_curves.csv`, `daily_signals.csv`, `regime_summary.csv`, `yearly_performance.csv`, `exposure.csv`.
- FFN core performance (CAGR / Sharpe / Max Drawdown / Calmar / Total Return): Tripod `27.16% / 0.759 / -61.01% / 0.445 / 4101.69%`; QQQ `18.45% / 0.921 / -35.12% / 0.525 / 1293.58%`; QLD `30.44% / 0.851 / -63.68% / 0.478 / 6144.85%`; TQQQ `38.42% / 0.841 / -81.66% / 0.470 / 15635.58%`.
- Tripod avg_monthly_turnover `53.70%`; avg_nominal_exposure `2.537x`.
- Regime active-day share: UP_LOW_RISK_3X `80.15%`, UP_RISK_1_5X `8.31%`, DOWN_HIGH_VOL_CASH `11.00%`, DOWN_LOW_VOL_1_5X `0.54%`.
- `yearly_performance.csv` 생성: Tripod/QQQ/QLD/TQQQ 각각 2011~2026 16개 연도 행.
- Transition sanity: 첫 signal `2011-02-10`이 다음 거래일 `2011-02-11`에 TQQQ 100% target으로 실행되며, 이후 UP_RISK 50/50 QQQ/QLD와 DOWN_HIGH_VOL_CASH target transition도 daily_signals에 기록됐다.
- 전략/Core/spec 수정 없음. blocker/data constraint 없음.
