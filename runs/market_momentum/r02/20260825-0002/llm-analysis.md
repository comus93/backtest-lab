# Run Analysis

Strategy: `market_momentum`
Revision: `r02`
Run: `20260825-0002`
Analyzed: `2026-08-25`

## Key Results

### Standalone performance

| Strategy | CAGR | Sharpe | MDD | Avg monthly turnover |
| --- | ---: | ---: | ---: | ---: |
| Momentum 3M | 6.39% | 0.42 | -41.25% | 43.45% |
| Momentum 6M | 12.04% | 0.68 | -30.57% | 31.28% |
| Momentum 12M | 13.87% | 0.76 | -28.44% | 20.23% |
| SPY Buy & Hold | 15.22% | 0.88 | -33.72% | 0.00% |

12M은 3M/6M 대비 CAGR, Sharpe, MDD, turnover의 균형이 가장 좋았다.

### Overall correlation

Momentum 12M의 전체기간 weekly correlation:

- SPY: 0.82
- QQQ: 0.81
- AIA: 0.78
- XLF: 0.63
- XLE: 0.40
- SLV: 0.39
- GDX: 0.38

Momentum 12M의 monthly correlation은 SPY 0.80, QQQ 0.79였다.

### Down-period correlation

QQQ 하락주:

- 3M correlation: 0.66, strategy avg return: -1.51%
- 6M correlation: 0.68, strategy avg return: -1.56%
- 12M correlation: 0.71, strategy avg return: -1.57%
- QQQ avg return: -2.17%

SPY 하락주:

- 3M correlation: 0.71, strategy avg return: -1.58%
- 6M correlation: 0.72, strategy avg return: -1.56%
- 12M correlation: 0.75, strategy avg return: -1.55%
- SPY avg return: -1.67%

12M은 하락주에서 기준자산보다 평균 손실은 작았지만 높은 positive correlation을 유지했다.

### Yearly 12M behavior

연도별 SPY/QQQ correlation은 고정적이지 않았다.

- 2017: SPY 0.51, QQQ 0.67. 중국 MCHI, 한국 EWY 중심으로 rotation.
- 2018: SPY 0.98, QQQ 0.95. QQQ/DIA/SPY 중심으로 미국 exposure가 강하게 유지됨.
- 2020: SPY 0.96, QQQ 0.97. QQQ 12개월, MCHI 11개월, SPY 8개월.
- 2022: SPY 0.84, QQQ 0.79. EWW 11개월, EIDO 10개월, INDY 6개월, QQQ는 0개월.
- 2024: SPY 0.95, QQQ 0.94. QQQ와 SPY가 각각 12개월 Top3에 포함됨.
- 2026 partial: SPY 0.66, QQQ 0.73. EWY/EWW/EWJ 등 미국 외 국가 비중이 커짐.

## Interpretation

### 1. 12M Momentum의 주된 가치는 단기 하락 방어가 아니다

12M은 SPY/QQQ와 전체기간뿐 아니라 기준자산 하락주에서도 높은 correlation을 유지한다.

따라서 미국 주식의 hedge 또는 crash protection 전략으로 해석하는 것은 적절하지 않다.

다만 QQQ 하락주에서 평균 손실이 QQQ보다 작았으므로 equity exposure를 유지하면서 하락 충격을 일부 완화하는 성격은 존재한다.

### 2. 전략의 핵심 기능은 국가 간 장기 leadership rotation이다

미국이 상대강도 winner일 때는 SPY/QQQ와 correlation이 0.94~0.97까지 상승한다. 다른 국가가 winner가 되면 portfolio identity가 바뀌면서 correlation도 낮아진다.

따라서 Country Momentum은 상시 저상관 전략이 아니라 장기간 지속되는 regional leadership 변화에 따라 exposure를 이동시키는 전략으로 보는 것이 적절하다.

### 3. 국가 rotation이 발생해도 global equity beta는 남는다

2022년에는 QQQ가 Top3에 한 번도 포함되지 않았지만 12M과 QQQ의 연간 correlation은 0.79였다.

이는 ticker overlap 감소와 true diversification이 동일하지 않다는 것을 보여준다. 국가별 주식시장도 금리, 달러, 글로벌 경기, risk-on/off 같은 공통 equity factor에 노출된다.

### 4. Momentum horizon에는 명확한 trade-off가 있다

3M은 12M보다 correlation 전환이 빠르고 QQQ 하락주 correlation도 낮았다. 그러나 전체기간 CAGR, MDD, turnover는 크게 불리했다.

반대로 12M은 장기성과와 운용 효율이 가장 좋지만 기존 winner에 오래 머물기 때문에 regime reversal 대응이 느리다.

## Implications

### Portfolio role

현재 결과만으로 Momentum 12M을 독립적인 defensive asset으로 분류하지 않는다.

보다 적절한 역할은 다음과 같다.

- 미국 중심 equity portfolio의 보조 equity engine
- 장기간 미국 leadership이 약화될 경우 다른 국가로 exposure를 이동시키는 rotation sleeve
- 주식 exposure를 유지하면서 지역 concentration risk를 완화하는 메커니즘

Gold, Silver, Energy처럼 구조적으로 낮은 correlation을 제공하는 자산과는 역할이 다르다.

### Portfolio construction implication

기존 portfolio가 QQQ/SPY 비중이 높을 때 미국 강세 regime에서는 Momentum 12M이 exposure 중복을 키울 수 있다.

반대로 미국 외 지역이 장기간 leadership을 가져가면 미국 집중도를 낮추는 기능을 제공할 가능성이 있다.

따라서 최종 평가는 standalone CAGR보다 실제 기존 portfolio에 추가했을 때의 MDD, Sharpe, contribution 변화가 더 중요하다.

## Hypotheses / Provisional Conclusions

### Hypothesis A

국가 Momentum의 주요 alpha는 crash protection보다 `regional leadership persistence`에서 발생한다.

현재 결과는 이 가설을 지지한다.

### Hypothesis B

12M은 leadership persistence를 포착하기에는 적합하지만 급격한 regime reversal 대응에는 지나치게 느릴 수 있다.

2018년과 2020년 결과가 이 가설을 지지한다.

### Hypothesis C

3M은 standalone 전략으로는 열위지만 QQQ 약세기에 빠른 replacement attack 역할을 제공할 가능성이 있다.

QQQ 하락주에서 3M correlation은 12M보다 낮았지만 높은 turnover와 낮은 장기성과가 비용으로 남는다. 별도 case study가 필요하다.

### Hypothesis D

6M 또는 multi-horizon 구조가 12M의 lag와 3M의 whipsaw 사이에서 더 나은 portfolio-level trade-off를 만들 수 있다.

현재 run만으로는 결론을 내릴 수 없다.

### Provisional Conclusion

현재 standalone 기본 후보는 Momentum 12M이다.

다만 채택 근거는 SPY보다 높은 수익이나 낮은 correlation이 아니다. 장기적인 지역 leadership 변화에 대응하여 미국 집중 exposure를 자동으로 완화할 가능성이 핵심 가치다.

## Risks / Limitations

- 모든 signal asset이 equity이므로 global equity beta를 제거할 수 없다.
- 12M momentum은 sudden crash와 빠른 regime reversal에 후행한다.
- 상대강도가 음수인 자산도 Top3이면 투자하므로 absolute momentum 방어 기능은 없다.
- Top3 equal weight가 최적이라는 근거는 없다.
- Universe 11종 구성 자체가 결과에 영향을 미칠 수 있다.
- 국가 ETF별 sector composition 차이가 momentum 효과와 섞일 수 있다.
- 현재 correlation 분석은 전략과 개별 asset 간 관계이며 기존 portfolio와의 실제 결합효과를 직접 측정한 것은 아니다.
- 2016과 2026은 partial year다.
- 역사적으로 좋은 결과가 특정 국가/시기의 우연한 leadership에 의존했을 가능성을 아직 제거하지 못했다.

## Next Questions / Steps

1. 3M / 6M / 12M 각각에 대해 연도별 correlation, SPY/QQQ 수익률, 전략 수익률, annual MDD, 실제 holdings를 한 표에서 비교한다.
2. 특히 QQQ 하락기에 3M이 어떤 국가를 선택했고 QQQ보다 손실을 줄이는 수준을 넘어 양(+)의 수익 또는 의미 있는 초과수익을 만들었는지 검증한다.
3. 기존 portfolio proxy와 Momentum을 실제 비중으로 결합해 CAGR, volatility, Sharpe, MDD, contribution 변화를 측정한다.
4. 6M 또는 multi-horizon signal이 12M lag를 줄이면서 3M whipsaw를 피할 수 있는지 검증한다.
5. absolute momentum filter를 추가할 경우 급락기 MDD 개선과 장기 CAGR 희생의 trade-off를 확인한다.
6. 2018, 2020, 2022, 2024를 case study로 분해해 signal transition, holdings, benchmark/strategy 성과, correlation 변화를 확인한다.

## Agreed Insights

`Agreed Insights`는 자동 생성하지 않고 User와의 후속 논의를 통해 합의된 내용을 기록한다.

1. 이번 실험은 정적 포트폴리오의 국가 슬롯을 고정하지 않고, 의미 있는 국가만 동적으로 포트폴리오 구성에 기여하게 하는 메커니즘을 만들기 위한 노력에서 시작되었다.
2. 중요한 검증 목적은 현재 정적 구성에서 큰 비중을 차지하는 미국 기술주가 취약해지는 기간에 다른 국가가 대체 공격 또는 방어 역할을 할 수 있는지 확인하는 것이다.
3. Country Momentum 자체의 성과에서는 12M이 가장 우월했다. SPY 수준에 다소 못 미치는 장기성과에도 불구하고 MDD와 turnover 등 안정성 측면에서 인상적인 결과를 보였다.
4. 하락기 대체 가능성 측면에서 12M은 이전 winner, 주로 미국 자산의 persistence가 길어 하락 방어와 correlation에서 약점이 있다. 장기 leadership rotation에는 적합하지만 빠른 미국 기술주 약세 대응에는 한계가 있다.
5. 다음 run에서는 3M이 미국 기술주 하락기에 다른 국가로 빠르게 rotation하여 손실을 완화하는 수준을 넘어 대체 공격 수익을 만들 수 있는지 검증한다.
