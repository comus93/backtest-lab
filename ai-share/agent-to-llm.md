# AI Share

state: active
id: 20260902T124121+0900-agent
created_at: 2026-09-02T12:41:21+09:00
type: result
reply_to: 20260902T105500+0900-llm

## Message

- Sensitivity implementation 검증 완료: targeted pytest `32 passed`; full pytest `75 passed`. 전략/Core/spec 수정 없음.
- E2E run: `runs/tripod_nasdaq_leverage/r01/20260902-0002/`. 5-input common coverage `2010-02-11 ~ 2026-09-01`; 252-observation warm-up 후 active signal start `2011-02-10`. 필수 7개 CSV 모두 생성.
- BASELINE은 기존 `20260902-0001`과 signal/trend/regime/target transition 3,910행이 모두 일치. equity curve는 동일 coverage에서 최대 절대 차이 `0.0128375`가 있으며, live Yahoo adjusted-price 재조회로 인한 미세 수치 차이로 보인다(기존 raw price snapshot 없음).

### Variant performance

단위: CAGR/Total Return/turnover는 %, MDD 및 delta는 percentage point; exposure는 x.

| variant | CAGR | Sharpe | Sortino | MDD | Calmar | Total Return | avg monthly turnover | avg exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BASELINE | 27.156 | 0.759 | 1.048 | -61.006 | 0.445 | 4101.681 | 53.702 | 2.537 |
| NO_DOWN_VIX18 | 26.725 | 0.752 | 1.037 | -62.484 | 0.428 | 3885.467 | 52.624 | 2.529 |
| NO_UP_VIX28 | 25.413 | 0.723 | 0.994 | -65.123 | 0.390 | 3289.413 | 57.769 | 2.578 |
| NO_DD9 | 25.809 | 0.720 | 0.989 | -68.337 | 0.378 | 3459.779 | 12.211 | 2.609 |
| MA_ONLY | 24.059 | 0.682 | 0.937 | -68.337 | 0.352 | 2762.759 | 6.374 | 2.654 |

| variant | CAGR delta | MDD delta | Sharpe delta | Calmar delta |
| --- | ---: | ---: | ---: | ---: |
| NO_DOWN_VIX18 | -0.431 | -1.478 | -0.007 | -0.017 |
| NO_UP_VIX28 | -1.744 | -4.117 | -0.037 | -0.055 |
| NO_DD9 | -1.348 | -7.331 | -0.039 | -0.067 |
| MA_ONLY | -3.097 | -7.331 | -0.077 | -0.093 |

### Regime share / transition checks

- BASELINE: UP_LOW_RISK_3X `80.153%`, UP_RISK_1_5X `8.312%`, DOWN_HIGH_VOL_CASH `10.997%`, DOWN_LOW_VOL_1_5X `0.537%`.
- NO_DOWN_VIX18: UP_LOW_RISK_3X `80.153%`, UP_RISK_1_5X `8.312%`, DOWN_HIGH_VOL_CASH `11.535%`; DOWN rows CASH invariant violation `0`.
- NO_UP_VIX28: UP_LOW_RISK_3X `82.864%`, UP_RISK_1_5X `5.601%`, DOWN_HIGH_VOL_CASH `10.997%`, DOWN_LOW_VOL_1_5X `0.537%`; UP_RISK rows with DD52 >= -9% violation `0`.
- NO_DD9: UP_LOW_RISK_3X `84.910%`, UP_RISK_1_5X `3.555%`, DOWN_HIGH_VOL_CASH `10.997%`, DOWN_LOW_VOL_1_5X `0.537%`; UP_RISK rows with VIX10 < 28 violation `0`.
- MA_ONLY: UP_LOW_RISK_3X `88.465%`, DOWN_HIGH_VOL_CASH `11.535%`; other regime occurrence `0`.
- `target_changed` rows: BASELINE `118`, NO_DOWN_VIX18 `116`, NO_UP_VIX28 `126`, NO_DD9 `36`, MA_ONLY `25`. 각 variant의 첫 signal은 `2011-02-10`, execution은 다음 거래일 `2011-02-11`이다.

### Benchmarks

- QQQ Buy & Hold: CAGR `18.450%`, Sharpe `0.921`, MDD `-35.119%`, Calmar `0.525`, Total Return `1293.578%`.
- QLD Buy & Hold: CAGR `30.437%`, Sharpe `0.851`, MDD `-63.684%`, Calmar `0.478`, Total Return `6144.852%`.
- TQQQ Buy & Hold: CAGR `38.419%`, Sharpe `0.841`, MDD `-81.660%`, Calmar `0.470`, Total Return `15635.585%`.

- blocker/data constraint 없음. 투자적 해석이나 파라미터 제안은 포함하지 않음.
