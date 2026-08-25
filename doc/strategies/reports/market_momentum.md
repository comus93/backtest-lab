# Market Momentum Strategy Report

Strategy ID: `market_momentum`
Updated: `2026-08-25`

## Origin / Motivation

이 전략은 정적 포트폴리오의 국가 노출을 고정 슬롯으로 두지 않고, 상대적으로 의미 있는 국가만 포트폴리오 구성에 기여하도록 만드는 동적 국가 배분 메커니즘을 검토하는 과정에서 시작되었다.

또한 현재 정적 포트폴리오에서 큰 비중을 차지하는 미국 기술주와 미국 주식이 취약해지는 기간에 다른 국가가 대체 공격 또는 방어 역할을 수행할 수 있는지 검증하는 것이 핵심 배경이다.

## Core Concept

- 국가 간 relative momentum으로 지역 leadership을 식별한다.
- 상대적으로 강한 국가만 Top3로 선택해 국가 exposure를 동적으로 구성한다.
- 미국 중심 정적 포트폴리오에 장기적인 regional rotation 기능을 추가할 수 있는지 검증한다.
- standalone 성과와 함께 기존 자산 대비 correlation, 하락기 특성, 실제 holdings를 함께 평가한다.

## Strategy Evolution

### r01

- 3M / 6M / 9M / 12M relative momentum Top3를 비교했다.
- standalone 성과와 rank의 다음 달 수익 예측력을 검토했다.
- 10년 재실행에서 12M winner status가 약 3~6개월 강하게 지속되고 9~12개월 사이 상당 부분 소진되는 persistence 특성을 확인했다.

### r02

- 3M / 6M / 12M에 집중했다.
- SPY, QQQ, SLV, GDX, AIA, XLF, XLE와의 weekly/monthly correlation을 추가했다.
- reference asset 하락주 conditional correlation을 추가했다.
- 연도별 constituent와 correlation을 통해 portfolio identity가 시간에 따라 어떻게 변하는지 검토했다.
- 다음 단계로 연도별 correlation, benchmark/strategy 성과, annual MDD, 실제 holdings를 한 표에서 연결하는 분석을 추가한다.

## Current Evidence

### Standalone performance

`r02 / 20260825-0002` 기준:

| Strategy | CAGR | Sharpe | MDD | Avg monthly turnover |
| --- | ---: | ---: | ---: | ---: |
| Momentum 3M | 6.39% | 0.42 | -41.25% | 43.45% |
| Momentum 6M | 12.04% | 0.68 | -30.57% | 31.28% |
| Momentum 12M | 13.87% | 0.76 | -28.44% | 20.23% |
| SPY Buy & Hold | 15.22% | 0.88 | -33.72% | 0.00% |

12M은 Momentum horizon 중 수익, Sharpe, MDD, turnover의 균형이 가장 좋았다. SPY보다 CAGR과 Sharpe는 낮지만 MDD는 더 작았다.

### Correlation structure

전체기간 weekly correlation에서 Momentum 12M은 SPY 0.82, QQQ 0.81, AIA 0.78로 높았고 SLV/GDX/XLE와는 약 0.38~0.40 수준이었다.

연도별 correlation은 고정적이지 않았다. 미국이 상대강도 winner인 2018, 2020, 2024에는 SPY/QQQ와 0.94~0.97 수준까지 높아졌고, 다른 국가가 leadership을 가져가는 구간에는 낮아졌다.

이는 Country Momentum이 고정된 저상관 자산이 아니라, 보유 국가와 시장 regime에 따라 correlation 구조가 변하는 rotation strategy임을 보여준다.

### Down-period behavior

QQQ 하락주에서 Momentum 12M correlation은 0.71이었다. 같은 주의 평균 수익률은 QQQ -2.17%, Momentum 12M -1.57%였다.

SPY 하락주에서 Momentum 12M correlation은 0.75였고 평균 수익률은 SPY -1.67%, Momentum 12M -1.55%였다.

따라서 12M은 crash hedge가 아니며 미국 equity 하락을 완전히 분리하지 못한다. 다만 일부 하락 충격을 줄이는 성격은 관찰된다.

## Current Hypotheses

### H1. 12M의 주요 alpha source는 crash avoidance가 아니라 regional leadership persistence이다

Status: `supported`

12M은 standalone 성과가 가장 좋지만 급격한 하락 초기에 기존 winner exposure가 오래 남는다. 반면 장기간 leadership이 이동하면 다른 국가로 rotation한다.

### H2. Country Momentum은 미국 집중위험을 줄일 수 있지만 global equity beta를 제거하지 못한다

Status: `supported`

2022년처럼 QQQ를 Top3에서 제외하고 멕시코, 인도네시아, 인도 중심으로 이동해도 QQQ correlation은 여전히 높았다. ticker overlap 감소와 true diversification은 별개다.

### H3. 3M은 standalone 전략으로는 열위지만 미국 기술주 약세기의 replacement attack 역할을 제공할 수 있다

Status: `open`

3M은 turnover와 MDD, 장기성과에서 12M보다 불리하지만 SPY/QQQ와의 correlation 전환이 더 빠르다. 미국 기술주 하락기에 다른 국가를 빠르게 선택해 손실을 줄이거나 양(+)의 대체수익을 만드는지 별도 검증이 필요하다.

### H4. 6M 또는 multi-horizon 구조가 12M lag와 3M whipsaw 사이의 절충점이 될 수 있다

Status: `open`

현재 결과만으로는 standalone 성과와 portfolio-level 역할을 동시에 최적화하는 horizon을 확정할 수 없다.

## Current Strategy View

### Momentum 12M

현재 standalone 기본 후보이다.

- 장기 regional leadership rotation에 적합하다.
- 3M/6M보다 높은 성과와 낮은 turnover를 보인다.
- 급격한 regime reversal에는 느리다.
- defensive asset이나 crash hedge로 분류하지 않는다.

### Momentum 3M

현재 standalone 채택 후보라기보다 빠른 replacement mechanism 후보이다.

- 미국 기술주 약세 초기에 다른 국가로 빠르게 이동할 가능성을 검증한다.
- 빠른 rotation의 이점이 높은 turnover와 whipsaw 비용을 상쇄하는지가 핵심 질문이다.

## Risks / Open Issues

- 모든 signal asset이 equity이므로 global equity beta가 남는다.
- 12M은 sudden crash와 빠른 regime reversal에 후행한다.
- 상대강도가 음수인 자산도 Top3이면 투자하므로 absolute momentum 방어 기능은 없다.
- Top3 equal weight가 최적이라는 근거는 아직 없다.
- Universe 구성에 따라 결과가 달라질 수 있다.
- 국가 ETF의 sector composition 차이가 국가 momentum 효과와 섞일 수 있다.
- 단독 전략과 개별 자산의 correlation만으로 실제 portfolio-level 개선을 확정할 수 없다.

## Next Strategic Questions

1. 3M이 QQQ 하락기에 어떤 국가를 선택했고 실제 대체 공격 수익을 만들었는지 검증한다.
2. 3M / 6M / 12M 각각에 대해 연도별 correlation, SPY/QQQ 성과, 전략 성과, annual MDD, holdings를 함께 비교한다.
3. 기존 portfolio proxy에 Momentum을 실제 비중으로 결합해 CAGR, Sharpe, MDD, contribution 변화를 측정한다.
4. 6M 또는 multi-horizon signal이 12M lag를 줄이면서 3M whipsaw를 피할 수 있는지 검토한다.
5. absolute momentum filter가 급락기 방어와 장기성과 사이에서 어떤 trade-off를 만드는지 검증한다.

## Run Evidence

- `r01 / 20260824-0002`: 10년 horizon 비교와 12M persistence 분석.
- `r02 / 20260825-0001`: correlation pilot 최초 E2E.
- `r02 / 20260825-0002`: 최종 comparison assets, downside correlation, yearly constituent/correlation 분석.

## Agreed Insights

`Agreed Insights`는 자동 생성하지 않고 User와의 후속 논의를 통해 합의된 내용을 기록한다.

1. 이번 실험은 정적 포트폴리오의 국가 슬롯을 고정하지 않고, 의미 있는 국가만 동적으로 포트폴리오 구성에 기여하게 하는 메커니즘을 만들기 위한 노력에서 시작되었다.
2. 중요한 검증 목적은 현재 정적 구성에서 큰 비중을 차지하는 미국 기술주가 취약해지는 기간에 다른 국가가 대체 공격 또는 방어 역할을 할 수 있는지 확인하는 것이다.
3. Country Momentum 자체의 성과에서는 12M이 가장 우월했다. SPY 성과에 다소 못 미치지만 MDD와 turnover 등 안정성 측면에서 인상적인 결과를 보였다.
4. 하락기 대체 가능성 측면에서 12M은 이전 winner, 주로 미국 자산의 persistence가 길어 하락 방어와 correlation에서 약점이 있다. 장기 leadership rotation에는 적합하지만 빠른 미국 기술주 약세 대응에는 한계가 있다.
5. 다음 실험에서는 3M이 미국 기술주 하락기에 다른 국가로 빠르게 rotation하여 손실 완화뿐 아니라 대체 공격 수익을 만들 수 있는지 검증한다.
