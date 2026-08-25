# Run Analysis

Strategy: `market_momentum`
Revision: `r02`
Run: `20260825-0003`

## Key Results

### Standalone performance

| Strategy | CAGR | Sharpe | MDD | Avg monthly turnover |
| --- | ---: | ---: | ---: | ---: |
| Momentum 3M | 6.39% | 0.42 | -41.25% | 43.45% |
| Momentum 6M | 12.04% | 0.68 | -30.57% | 31.28% |
| Momentum 12M | 13.87% | 0.76 | -28.44% | 20.23% |
| SPY Buy & Hold | 15.22% | 0.88 | -33.72% | 0.00% |

12M은 3M/6M/12M 중 standalone 성과, Sharpe, MDD, turnover의 균형이 가장 좋았다. 3M은 가장 빠른 horizon이지만 장기 성과와 MDD, turnover에서는 가장 불리했다.

### QQQ weakness episode review

이번 run의 핵심 검증 목적은 3M이 QQQ 약세기에 correlation을 낮추는 데 그치지 않고 실제 방어 또는 새로운 대체 공격 수익을 만들었는지 확인하는 것이었다.

| QQQ 약세 episode | QQQ 상태 | 3M 전략 | 판정 |
| --- | --- | ---: | --- |
| 2018 Q4 | 3M momentum 약 -16.7% | 약 -11.6% | 부분 방어 |
| 2020 Q1 | 3M momentum 약 -10.3% | 약 -24.7% | 실패 |
| 2022 Q1 | 3M momentum 약 -8.8% | 약 -5.2% | 약한 방어 |
| 2022 Q2 | 3M momentum 약 -22.5% | 약 -12.0% | 강한 방어 |
| 2026 Q1 | 3M momentum 약 -5.9% | 약 +2.4% | 대체 공격 성공 |

위 표의 QQQ 상태는 월말 기준 3M momentum, 전략 수익률은 해당 episode의 equity curve 구간을 이용한 근사 비교다. 완전히 동일한 날짜 구간은 아니므로 정밀 attribution 수치가 아니라 episode 성격 판정용으로 사용한다.

### Holdings behavior in the episodes

- 2018 Q4: 3M은 10~11월까지 QQQ를 Top3에 유지했고 12월에야 `EIDO / DIA / EPHE`로 QQQ가 빠졌다. 방어는 일부 있었지만 새로운 양(+)의 수익 엔진을 찾지 못했다.
- 2020 Q1: `QQQ / SPY / DIA`에서 `MCHI / QQQ / EWW`, 이후 `QQQ / MCHI / EWJ`로 움직였지만 글로벌 equity가 동시에 무너지며 대체 공격수 역할에 실패했다.
- 2022: QQQ가 Top3에서 빠르게 밀려나고 `EWW / EIDO / EPHE`, 이후 `EIDO / EWW / DIA` 등으로 이동했다. 손실은 줄였지만 전략 자체 수익률은 음수였다.
- 2026 Q1: `EWY / EIDO / INDY`에서 `EWY / EWW / EPHE`, 이후 `EWY / EWW / EWJ`로 이동했고 QQQ 약세 중 전략이 양(+)의 수익을 냈다. 현재 표본에서 가장 명확한 replacement attacker 사례다.

## Interpretation

### 1. 3M은 correlation을 낮추는 것과 실제 포트폴리오 가치를 만드는 것이 다르다는 점을 보여줬다

3M은 전체기간 QQQ 하락주 correlation이 6M/12M보다 낮지만, 낮은 correlation이 안정적인 방어나 양(+)의 대체수익으로 일관되게 연결되지는 않았다.

2018에는 QQQ보다 덜 잃었지만 여전히 의미 있는 손실을 냈고, 2020에는 오히려 큰 손실을 입었다. 따라서 낮은 correlation 자체는 전략의 유효성을 보장하지 않는다.

### 2. 글로벌 equity가 동시에 무너지면 Country Momentum은 구조적으로 방어력이 약하다

2020 Q1이 대표적이다. 국가를 바꾸더라도 signal universe 전체가 equity이기 때문에 공통 global equity beta가 지배하면 선택 가능한 대안 자체가 함께 하락한다.

이 구조에서는 relative momentum이 새로운 공격수를 만드는 것이 아니라 단지 "덜 나쁜 equity"를 고르는 데 그칠 수 있다.

### 3. 2022는 방어 기능은 확인했지만 replacement attack은 아니었다

3M은 QQQ를 빠르게 제외하고 다른 국가로 이동하여 QQQ 대비 손실을 크게 줄였다. 하지만 전략 수익률 자체는 음수였다.

따라서 2022는 `Defense = Yes`, `Attack = No`로 분류하는 것이 적절하다.

### 4. 2026 Q1은 대체 공격 성공이지만 일반화하기 어렵다

2026 Q1에서는 QQQ 약세 중 3M이 EWY 중심의 아시아 winner로 이동하며 양(+)의 수익을 냈다.

그러나 EWY는 3M/6M/12M 모든 horizon에서 매우 큰 trailing momentum을 보인 역사적으로 특이한 강세 regime이었다. 따라서 이 사례 하나만으로 3M이 일반적으로 미국 기술주 약세기의 replacement attacker라고 결론내리기 어렵다.

더 적절한 해석은 다음과 같다.

> 다른 지역에 이미 매우 강력하고 독립적인 winner가 존재할 경우 3M은 이를 빠르게 포착할 수 있다. 그러나 그러한 winner가 존재하지 않는 하락장에서는 방어 또는 대체 공격 능력이 안정적으로 나타나지 않는다.

### 5. 3M의 빠른 responsiveness 자체는 확인됐지만 연구 목적에는 충분하지 않았다

3M은 12M보다 빠르게 holdings identity를 바꾼다. 하지만 `reaction speed`와 `successful rotation`은 동일하지 않다.

이번 실험의 목적은 빠른 회전 자체가 아니라 미국 기술주 약세기에 실제 포트폴리오 보완 효과를 만드는지 검증하는 것이었고, 그 기준에서는 3M의 evidence가 부족하다.

## Implications

- Country Momentum을 미국 기술주 약세기의 구조적 hedge로 분류하지 않는다.
- 3M을 자동 replacement attacker로 분류하지 않는다.
- 2022처럼 손실 완화는 가능하지만, 이것만으로 전체 포트폴리오의 공격적 보완재 역할을 충족하지 않는다.
- 2026 Q1의 성공은 EWY라는 강한 독립 winner가 존재했기 때문에 가능했을 가능성이 크며, 반복 가능성을 입증하지 못한다.
- 따라서 미국 기술주 약세기에 포트폴리오를 보완하려는 목적이라면 country equity 내부 rotation보다 더 독립적인 return driver를 가진 다른 공격 자산 또는 전략을 탐색할 필요가 있다.
- 12M의 standalone regional leadership 전략으로서의 가치는 별도로 유지한다. 이번 결론은 Country Momentum 자체를 폐기하는 것이 아니라, 현재 검증한 portfolio-complement use case를 기각하는 것이다.

## Hypotheses / Provisional Conclusions

### H1. 12M의 주요 alpha source는 crash avoidance가 아니라 regional leadership persistence이다

Status: `supported`

Standalone 성과와 turnover, persistence 결과는 계속 이 가설을 지지한다.

### H2. Country Momentum은 미국 집중위험을 줄일 수 있지만 global equity beta를 제거하지 못한다

Status: `supported`

국가가 바뀌어도 global equity shock에서는 동반 하락하는 구조가 2020 및 2022에서 확인된다.

### H3. 3M은 미국 기술주 약세기의 replacement attack 역할을 제공할 수 있다

Status: `not supported for the target use case`

2018과 2022에서 주로 손실 완화에 그쳤고 2020에는 실패했다. 2026 Q1에 양(+)의 대체수익 사례가 존재하지만 EWY의 예외적 강세 regime에 크게 의존한다.

### Provisional Conclusion

현재까지의 evidence로는 Country Momentum을 미국 기술주 약세기에 전체 포트폴리오를 보완하는 핵심 전략으로 채택하지 않는다.

- 3M은 하락장에서 자주 함께 하락했다.
- 방어가 나타난 경우에도 주로 `덜 잃는` 수준이었고 안정적인 양(+)의 방어수 역할을 만들지 못했다.
- 새로운 공격수 역할은 2026 Q1 한 사례에서 뚜렷했지만 EWY라는 특이한 대형 winner에 의존했다.
- Country Momentum의 signal universe가 모두 equity이므로 global equity beta를 구조적으로 벗어나기 어렵다.

따라서 다음 탐색은 국가 간 rotation을 더 빠르게 만드는 방향보다 미국 기술주 약세기에 독립적인 수익 엔진을 제공할 수 있는 다른 공격 자산 또는 전략을 찾는 쪽이 우선이다.

12M은 별개의 standalone regional rotation strategy 후보로 유지할 수 있다.

## Risks / Limitations

- QQQ weakness episode 표의 QQQ 3M momentum과 전략 수익률 구간은 완전히 동일한 날짜 정의가 아니므로 정밀 event attribution이 아니다.
- `yearly_strategy_context.csv`의 `selected_symbols`는 현재 `signal_date.year` 기준으로 집계되어 실제 execution year와 1개월 귀속 차이가 있을 수 있다.
- 연간 return/MDD 계산도 calendar-year 표준 정의와 약간 다를 수 있다.
- 2026은 7월까지의 partial year이다.
- 명확한 replacement attack 성공 사례가 사실상 2026 Q1 한 번뿐이라 표본 수가 작다.
- signal universe가 국가 equity ETF로 제한되어 있어 다른 자산군의 독립 수익 엔진 가능성을 검증하지 않는다.

## Next Questions / Steps

1. Country Momentum의 portfolio-complement 목적 검증은 현재 단계에서 종료 또는 보류한다.
2. 12M은 standalone regional leadership strategy로 별도 평가할 수 있다.
3. 다음 공격수 후보는 QQQ 약세 episode에서 다음 세 조건을 동시에 평가한다.
   - QQQ와 낮은 downside correlation
   - QQQ 하락 중 양(+)의 수익 또는 명확한 초과수익
   - global equity beta와 다른 독립적인 return driver
4. 후보 자산/전략도 동일한 `QQQ weakness episode / benchmark state / candidate return / verdict` 표로 비교해 이번 연구와 직접 연결한다.
5. `selected_symbols`의 execution-year 귀속 및 calendar-year return/MDD 정의 오류는 r02 분석 output 보정 대상으로 별도 수정한다.

## Agreed Insights

`Agreed Insights`는 자동 생성하지 않고 User와의 후속 논의를 통해 합의된 내용을 기록한다.

1. QQQ 약세 episode별 `QQQ 상태 / 3M 전략 성과 / 판정` 표는 이번 run과 전략 전역 report 모두에 핵심 evidence로 유지한다.
2. 이번 실험의 목적은 3M의 빠른 회전 자체가 아니라, QQQ 하락기에 실제 방어수 또는 새로운 공격수가 되는지를 검증하는 것이었다.
3. 3M은 2018과 2022에서 일부 손실 완화는 했지만 안정적으로 양(+)의 방어수 역할을 하지 못했고, 2020에는 동반 하락했다.
4. 2026 Q1에서는 EWY 중심 rotation으로 대체 공격에 성공했지만, EWY의 예외적 강세라는 특이한 사례의 영향이 커 일반화 근거가 부족하다.
5. 현재까지의 결론은 Country Momentum이 미국 기술주 약세기의 전체 포트폴리오 보완재로는 적절하지 않다는 것이다. 다만 12M의 standalone regional leadership 전략 가치는 별개로 남긴다.
6. 다음 연구는 국가 rotation horizon을 더 미세 조정하기보다 미국 기술주 약세기에 독립적인 수익 엔진을 제공할 수 있는 다른 공격 자산 또는 전략을 찾는 방향으로 전환한다.
