---
title: Tripod Nasdaq Leverage r01 Analysis
date: 2026-09-02
strategy_id: tripod_nasdaq_leverage
revision: r01
run_id: 20260902-0002
tags:
  - backtest
  - nasdaq
  - leverage
  - trend
  - sensitivity
---

# Tripod Nasdaq Leverage r01 분석

## 1. Scope

이 문서는 `runs/tripod_nasdaq_leverage/r01/20260902-0002/` sensitivity run을 분석한다.

검증 구간은 5개 입력(`QQQ`, `QLD`, `TQQQ`, `^NDX`, `^VIX`)의 공통 coverage `2010-02-11 ~ 2026-09-01`에서 252 거래일 warm-up 후 시작한 `2011-02-10 ~ 2026-09-01`이다.

Codex 검증 결과:

- targeted pytest: 32 passed
- full pytest: 75 passed
- blocker 없음
- BASELINE signal/trend/regime/target transition은 기존 baseline run `20260902-0001`과 3,910행 모두 일치
- equity curve의 미세 차이는 Yahoo adjusted-price 재조회에 따른 값 변화로 판단되며 전략 로직 차이는 확인되지 않음

## 2. Key Results

| Strategy | CAGR | Sharpe | Sortino | MDD | Calmar | Total Return | Avg Monthly Turnover | Avg Nominal Exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tripod BASELINE | 27.16% | 0.759 | 1.048 | -61.01% | 0.445 | 4,101.68% | 53.70% | 2.54x |
| QQQ Buy & Hold | 18.45% | 0.921 | 1.311 | -35.12% | 0.525 | 1,293.58% | 0.00% | 1.00x |
| QLD Buy & Hold | 30.44% | 0.851 | 1.207 | -63.68% | 0.478 | 6,144.85% | 0.00% | 2.00x |
| TQQQ Buy & Hold | 38.42% | 0.841 | 1.191 | -81.66% | 0.470 | 15,635.58% | 0.00% | 3.00x |

## 3. Benchmark Interpretation

### 3.1 QLD가 가장 중요한 비교 대상

Tripod는 QLD 대비:

- CAGR: `27.16% vs 30.44%` -> `-3.28%p`
- MDD: `-61.01% vs -63.68%` -> 약 `2.68%p` 개선
- Sharpe: `0.759 vs 0.851` -> 열위
- Sortino: `1.048 vs 1.207` -> 열위
- Calmar: `0.445 vs 0.478` -> 열위
- 평균 명목 exposure: `2.54x vs 2.00x`

### AI 판단

현재 결과에서 Tripod는 **QLD를 실질적으로 이겼다고 보기 어렵다.**

QLD보다 평균 exposure를 더 많이 사용하면서 CAGR은 낮고, Sharpe/Sortino/Calmar도 모두 낮다. 얻은 것은 MDD 약 2.7%p 감소뿐이다.

즉 복잡한 0x / 1.5x / 3x 동적 노출 구조가 단순 2x Buy & Hold보다 충분한 효율 개선을 만들지 못했다.

### 3.2 TQQQ 대비

Tripod는 TQQQ 대비:

- CAGR은 약 `11.26%p` 낮다.
- MDD는 약 `20.65%p` 개선된다.
- 그러나 Sharpe와 Calmar는 오히려 TQQQ보다 낮다.

따라서 극단적 drawdown은 줄였지만, 위험 감소 대비 수익 희생이 커서 전체 위험조정 성과가 개선되지는 않았다.

### 3.3 QQQ 대비

QQQ보다 CAGR은 약 `8.71%p` 높지만 MDD는 약 `25.89%p` 더 깊다. Sharpe, Sortino, Calmar는 모두 QQQ가 우수하다.

Tripod는 명확히 고수익/고위험 전략이지, QQQ보다 효율적인 전략으로 나타나지는 않는다.

## 4. Regime Structure

BASELINE 체류 비중:

| Regime | Share | Exposure |
| --- | ---: | ---: |
| UP_LOW_RISK_3X | 80.15% | 3.0x |
| UP_RISK_1_5X | 8.31% | 1.5x |
| DOWN_HIGH_VOL_CASH | 11.00% | 0x |
| DOWN_LOW_VOL_1_5X | 0.54% | 1.5x |

평균 명목 exposure는 `2.54x`다.

### AI 판단

전략 이름은 4-state 구조지만 실제로는 **대부분의 시간을 3x로 보유하는 전략**이다.

특히 `DOWN + VIX10 < 18 -> 1.5x` 상태는 전체 기간의 0.54%에 불과하다. 따라서 DOWN-side VIX18 규칙은 현재 데이터에서 전략의 핵심 축이라고 보기 어렵다.

실질적인 전략 구조는 다음 3개 상태가 대부분을 설명한다.

1. 정상 상승장 -> 3x
2. 상승 중 위험 신호 -> 1.5x
3. 하락 + 높은 변동성 -> cash

## 5. Sensitivity: 각 조건의 기여

| Variant | CAGR | MDD | Sharpe | Calmar | Turnover | Avg Exposure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BASELINE | 27.16% | -61.01% | 0.759 | 0.445 | 53.70% | 2.537x |
| NO_DOWN_VIX18 | 26.73% | -62.48% | 0.752 | 0.428 | 52.62% | 2.529x |
| NO_UP_VIX28 | 25.41% | -65.12% | 0.723 | 0.390 | 57.77% | 2.578x |
| NO_DD9 | 25.81% | -68.34% | 0.720 | 0.378 | 12.21% | 2.609x |
| MA_ONLY | 24.06% | -68.34% | 0.682 | 0.352 | 6.37% | 2.654x |

### 5.1 DD52 -9% filter

`NO_DD9` 대비 BASELINE:

- CAGR `+1.35%p`
- MDD 약 `7.33%p` 개선
- Sharpe `+0.039`
- Calmar `+0.067`

가장 눈에 띄는 것은 MDD 개선이다.

반면 turnover가 `12.21% -> 53.70%`로 크게 증가하고 target change도 `36 -> 118`로 증가한다.

### AI 판단

현재 구성요소 중 **DD52 -9% 필터가 tail-risk 완화에 가장 강하게 기여한 것으로 보인다.** 다만 이 필터가 많은 3x <-> 1.5x 전환을 유발한다.

이 결과만으로 `-9%`라는 특정 숫자가 최적이라는 뜻은 아니다. 오히려 이후 민감도 검증에서 가장 우선적으로 threshold robustness를 확인해야 할 항목이다.

### 5.2 UP regime VIX28 filter

`NO_UP_VIX28` 대비 BASELINE:

- CAGR `+1.74%p`
- MDD 약 `4.12%p` 개선
- Sharpe `+0.037`
- Calmar `+0.055`

### AI 판단

VIX28 필터도 의미 있는 기여가 있다. 단순한 수익 희생형 risk-off가 아니라 CAGR과 MDD를 동시에 개선했다는 점에서 DD9와 함께 유지 가치가 있는 조건으로 보인다.

### 5.3 DOWN regime VIX18 filter

`NO_DOWN_VIX18` 대비 BASELINE:

- CAGR `+0.43%p`
- MDD 약 `1.48%p` 개선
- Sharpe `+0.007`
- Calmar `+0.017`

`DOWN_LOW_VOL_1_5X` 자체가 전체의 0.54%, 21 거래일뿐이다.

### AI 판단

VIX18 규칙의 기여는 **매우 작다.** 현재 r01 구조에서 가장 먼저 단순화 후보로 볼 수 있다. 다만 제거를 확정하려면 더 긴 synthetic/proxy 기간 또는 threshold 주변 민감도를 확인할 필요가 있다.

### 5.4 MA_ONLY 대비 전체 필터 효과

MA_ONLY -> BASELINE 변화:

- CAGR `24.06% -> 27.16%`
- MDD `-68.34% -> -61.01%`
- Sharpe `0.682 -> 0.759`
- Calmar `0.352 -> 0.445`

즉 VIX/DD 조건을 추가한 것은 현재 데이터에서 분명히 전략을 개선했다.

다만 이 개선은 **Tripod 내부의 개선**이지, QLD라는 단순 benchmark를 넘어섰다는 의미는 아니다.

## 6. Stress-year Comparison

### 2020

| Strategy | Return | Year MDD |
| --- | ---: | ---: |
| Tripod | +96.78% | -40.91% |
| QQQ | +45.97% | -28.56% |
| QLD | +82.89% | -51.72% |
| TQQQ | +100.13% | -69.92% |

2020은 Tripod가 가장 잘 작동한 사례다. TQQQ에 가까운 수익을 유지하면서 TQQQ/QLD보다 drawdown을 크게 줄였다.

### 2022

| Strategy | Return | Year MDD |
| --- | ---: | ---: |
| Tripod | -47.66% | -47.66% |
| QQQ | -33.22% | -34.83% |
| QLD | -61.33% | -63.08% |
| TQQQ | -79.68% | -81.02% |

2022에는 leverage B&H보다 방어했지만 손실이 여전히 매우 컸다. 전략이 bear market을 회피했다기보다 **3x 손실을 1x~2x 중간 수준으로 완화한 것**에 가깝다.

### 문제 구간

- 2011 partial year: Tripod `-45.74%`, QLD `-11.65%`, TQQQ `-23.39%`
- 2015: Tripod `-26.40%`, QQQ `+9.77%`, QLD `+15.22%`, TQQQ `+18.20%`
- 2025: Tripod 약 `0%`, QQQ `+21.01%`, QLD `+30.94%`, TQQQ `+35.21%`

### AI 판단

이 전략의 가장 큰 약점은 **하락장 그 자체보다 trend/risk signal이 흔들리는 구간의 whipsaw**일 가능성이 높다.

2015처럼 NASDAQ B&H가 플러스인데 Tripod가 큰 마이너스를 기록한 연도는 단순한 leverage risk만으로 설명되지 않는다. 신호 전환 시점과 3x 재진입 과정의 손실 누적을 별도로 분석할 필요가 있다.

2011은 active period가 2월부터 시작하는 partial year이므로 초기화 효과도 함께 점검해야 한다.

## 7. FFN Distribution / Drawdown Signals

FFN 기준:

- Tripod win year: `66.7%`
- QQQ / QLD / TQQQ win year: 각각 `86.7%`
- Tripod 12-month win rate: `71.2%`
- QQQ: `91.0%`
- QLD: `85.3%`
- TQQQ: `83.1%`

평균 drawdown:

- Tripod: `-7.99%`
- QQQ: `-2.48%`
- QLD: `-5.02%`
- TQQQ: `-7.39%`

평균 drawdown duration:

- Tripod: `42.7일`
- QQQ: `20.0일`
- QLD: `25.0일`
- TQQQ: `29.4일`

Worst month:

- Tripod: `-33.34%`
- QLD: `-26.03%`
- TQQQ: `-38.13%`

### AI 판단

Tripod는 단순히 drawdown을 부드럽게 만드는 전략이 아니다.

최대 MDD는 TQQQ보다 줄지만, 평균 drawdown과 회복기간은 QLD보다 나쁘고 worst month도 QLD보다 깊다. 즉 risk control이 **일상적 변동성을 줄이는 대신 일부 대형 붕괴를 차단하는 형태**로 작동한다.

이 특성이 전략의 목표와 맞는지 별도로 판단해야 한다.

## 8. Overall Assessment

### 재현 여부

원 전략은 정상적으로 재현되었다. 테스트, baseline consistency, signal transition sanity check 모두 통과했다.

### 전략 효과

세 가지 risk control 요소 중:

1. `DD52 -9%` -> 가장 강한 drawdown 개선
2. `UP VIX28` -> 유의미한 CAGR/MDD 동시 개선
3. `DOWN VIX18` -> 영향 매우 작음

이라는 순서가 현재 데이터에서 나타난다.

### AI 판단

**현재 r01은 흥미로운 아이디어지만 실전 후보로 바로 채택할 수준의 우위는 확인되지 않았다.**

가장 큰 이유는 단순 QLD Buy & Hold가 더 낮은 평균 nominal exposure로:

- 더 높은 CAGR
- 더 높은 Sharpe
- 더 높은 Sortino
- 더 높은 Calmar

를 기록했기 때문이다.

Tripod의 장점은 TQQQ의 catastrophic drawdown을 약화시키는 데 있지만, 그 대가를 고려한 위험조정 성과가 충분히 좋아지지 않았다.

따라서 다음 단계에서 바로 여러 threshold를 최적화하는 것은 권하지 않는다. 그러면 QLD를 못 이긴 구조에 숫자를 맞추는 overfitting으로 흐르기 쉽다.

## 9. Next Questions / Steps

우선순위 제안:

1. **단순 1x / 2x Gear Strategy를 먼저 비교**한다.
   - Trend UP -> QLD
   - Trend DOWN -> QQQ 또는 CASH 등 최소 규칙
   - 복잡한 Tripod가 단순 기어 전략 대비 실제 추가가치를 만드는지 확인

2. **2011 / 2015 / 2025 transition 분석**을 수행한다.
   - 어떤 신호가 손실을 확대했는지
   - 3x 재진입 또는 3x <-> 1.5x whipsaw가 원인인지 확인

3. 이후에만 DD9와 VIX28의 넓은 parameter sensitivity를 검토한다.
   - 단일 최적점 탐색보다 plateau / robustness를 확인

4. DOWN VIX18은 우선순위가 낮다.

## 10. Risks / Limitations

- 검증 시작은 TQQQ 실데이터와 warm-up 제약 때문에 2011년이다.
- 2000~2002, 2008과 같은 장기 구조적 bear market을 실제 TQQQ 데이터로 검증하지 못했다.
- Yahoo adjusted price는 재조회 시 과거 값이 미세하게 변할 수 있다.
- 이번 sensitivity는 조건 제거(ablation)이며 threshold robustness 검증이 아니다.
- 높은 성과는 2010년대 이후 NASDAQ 강세 regime의 영향을 크게 받는다.
- nominal exposure는 ETF daily-reset path dependency를 완전히 표현하는 위험척도가 아니다.

## 11. Agreed Insights

사용자와 합의된 insight는 아직 기록하지 않는다. 후속 논의에서 합의된 내용만 이 섹션에 추가한다.
