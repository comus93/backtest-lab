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

## Experiment Universe / Benchmarks

### Signal Universe

Momentum ranking과 Top3 선택에 사용한 ETF universe는 다음 11개이다.

| Ticker | ETF | Market / Exposure |
| --- | --- | --- |
| `SPY` | SPDR S&P 500 ETF Trust | 미국 대형주 |
| `QQQ` | Invesco QQQ Trust | 미국 Nasdaq-100 / 대형 성장주 |
| `DIA` | SPDR Dow Jones Industrial Average ETF Trust | 미국 Dow 30 |
| `EWJ` | iShares MSCI Japan ETF | 일본 |
| `EWY` | iShares MSCI South Korea ETF | 한국 |
| `MCHI` | iShares MSCI China ETF | 중국 |
| `DAX` | Global X DAX Germany ETF | 독일 |
| `EWW` | iShares MSCI Mexico ETF | 멕시코 |
| `EIDO` | iShares MSCI Indonesia ETF | 인도네시아 |
| `INDY` | iShares India 50 ETF | 인도 |
| `EPHE` | iShares MSCI Philippines ETF | 필리핀 |

`SPY`와 `QQQ`는 signal universe에도 포함되므로 미국 자체가 relative-momentum winner일 때 Top3에 선택될 수 있다.

### Primary Comparison Benchmarks

전략의 핵심 portfolio-complement 검증 대상은 다음 두 자산이다.

| Ticker | ETF | 비교 목적 |
| --- | --- | --- |
| `SPY` | SPDR S&P 500 ETF Trust | 미국 주식시장 전체 대비 성과·상관·방어 특성 비교 |
| `QQQ` | Invesco QQQ Trust | 미국 기술주/성장주 약세기에 방어수 또는 대체 공격수 역할을 하는지 검증 |

r02에서는 `SLV`, `GDX`, `AIA`, `XLF`, `XLE`도 correlation reference로 사용했지만, 전략의 핵심 채택 여부를 판단하는 primary comparison benchmark는 `SPY`와 `QQQ`이다. 특히 3M의 portfolio-complement 역할은 QQQ weakness episode에서 실제 손실 완화 또는 양(+)의 대체수익을 만들었는지를 중심으로 판단한다.

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
- `20260825-0003`에서 연도별 correlation, benchmark/strategy 성과, annual MDD, holdings를 연결하고 QQQ weakness episode별 3M의 실제 역할을 검토했다.

## Current Evidence

### Standalone performance

`r02 / 20260825-0003` 기준:

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

### QQQ weakness episode review

미국 기술주 약세기에 3M이 실제 방어수 또는 새로운 공격수가 되었는지를 검토한 핵심 표이다.

| QQQ 약세 episode | QQQ 상태 | 3M 전략 | 판정 |
| --- | --- | ---: | --- |
| 2018 Q4 | 3M momentum 약 -16.7% | 약 -11.6% | 부분 방어 |
| 2020 Q1 | 3M momentum 약 -10.3% | 약 -24.7% | 실패 |
| 2022 Q1 | 3M momentum 약 -8.8% | 약 -5.2% | 약한 방어 |
| 2022 Q2 | 3M momentum 약 -22.5% | 약 -12.0% | 강한 방어 |
| 2026 Q1 | 3M momentum 약 -5.9% | 약 +2.4% | 대체 공격 성공 |

QQQ 상태는 월말 기준 3M momentum, 전략 수익률은 해당 episode의 equity curve 구간을 이용한 근사 비교다. 완전히 동일한 날짜 구간은 아니므로 정밀 attribution 수치가 아니라 episode 성격 판정용으로 사용한다.

### Down-period behavior and mechanism

3M은 QQQ 하락주 correlation이 6M/12M보다 낮지만 낮은 correlation이 안정적인 방어나 양(+)의 대체수익으로 일관되게 연결되지 않았다.

- 2018: QQQ보다 덜 잃었지만 전략도 큰 손실을 기록했다.
- 2020: 글로벌 equity가 동시에 무너지며 국가 rotation 자체가 방어 수단이 되지 못했다.
- 2022: QQQ를 빠르게 제외하고 다른 국가로 이동해 손실을 완화했지만 전략 수익률 자체는 음수였다.
- 2026 Q1: EWY 중심의 강한 아시아 leadership을 포착하면서 QQQ 약세 중 양(+)의 수익을 기록했다. 현재 표본에서 유일하게 명확한 replacement attacker 사례다.

따라서 Country Momentum은 글로벌 equity shock에서 구조적 hedge가 되기 어렵고, 다른 지역에 이미 강력한 독립 winner가 존재할 때만 대체 공격 역할이 나타날 수 있다.

## Current Hypotheses

### H1. 12M의 주요 alpha source는 crash avoidance가 아니라 regional leadership persistence이다

Status: `supported`

12M은 standalone 성과가 가장 좋지만 급격한 하락 초기에 기존 winner exposure가 오래 남는다. 반면 장기간 leadership이 이동하면 다른 국가로 rotation한다.

### H2. Country Momentum은 미국 집중위험을 줄일 수 있지만 global equity beta를 제거하지 못한다

Status: `supported`

국가가 바뀌어도 global equity shock에서는 동반 하락하는 구조가 2020과 2022에서 확인된다. ticker overlap 감소와 true diversification은 별개다.

### H3. 3M은 standalone 전략으로는 열위지만 미국 기술주 약세기의 replacement attack 역할을 제공할 수 있다

Status: `not supported for the target use case`

2018과 2022에서는 주로 손실 완화에 그쳤고 2020에는 실패했다. 2026 Q1에 양(+)의 대체수익 사례가 존재하지만 EWY의 예외적으로 강한 regime에 크게 의존한다.

### H4. 6M 또는 multi-horizon 구조가 12M lag와 3M whipsaw 사이의 절충점이 될 수 있다

Status: `de-prioritized`

2025~2026의 6M 강세는 EWY를 포함한 특정 regional leadership regime의 영향을 크게 받았을 가능성이 있다. 더 중요한 점은 horizon을 조정해도 signal universe가 모두 equity라는 구조적 한계가 남는다는 것이다. 미국 기술주 약세기의 독립 보완재라는 목표에서는 horizon 최적화보다 다른 return driver 탐색이 우선이다.

## Current Strategy View

### Momentum 12M

현재 standalone regional leadership 전략의 기본 후보이다.

- 장기 regional leadership rotation에 적합하다.
- 3M/6M보다 높은 성과와 낮은 turnover를 보인다.
- 급격한 regime reversal에는 느리다.
- defensive asset이나 crash hedge로 분류하지 않는다.

### Momentum 3M

미국 기술주 약세기의 portfolio-complement 후보로는 현재 기각한다.

- 빠른 holdings 전환 자체는 확인됐다.
- 하지만 빠른 반응이 안정적인 방어 또는 대체 공격 수익으로 이어지지 않았다.
- 2018/2022에서는 주로 손실 완화에 그쳤고 2020에는 동반 하락했다.
- 2026 Q1의 성공은 EWY라는 예외적 winner의 존재에 크게 의존했다.

### Portfolio-complement use case

현재까지의 evidence로는 Country Momentum을 미국 기술주 약세기에 전체 포트폴리오를 보완하는 핵심 전략으로 채택하지 않는다.

이 결론은 Country Momentum 자체의 모든 가치를 부정하는 것이 아니다. 12M은 standalone regional rotation strategy로 별도 가치가 있으나, 미국 기술주가 약해질 때 안정적으로 방어하거나 새로운 공격 수익원을 공급한다는 목적에는 적합하지 않았다.

## Risks / Open Issues

- 모든 signal asset이 equity이므로 global equity beta가 남는다.
- relative momentum은 전체 universe가 하락할 때도 Top3를 선택하므로 절대적 방어 기능이 없다.
- 낮은 correlation이 반드시 양(+)의 수익이나 낮은 MDD로 연결되지 않는다.
- 2026 Q1의 replacement attack 성공은 EWY라는 역사적으로 특이한 강세 사례에 크게 의존할 수 있다.
- Top3 equal weight가 최적이라는 근거는 아직 없다.
- Universe 구성에 따라 결과가 달라질 수 있다.
- 국가 ETF의 sector composition 차이가 국가 momentum 효과와 섞일 수 있다.
- `yearly_strategy_context.csv`의 selected-symbol 연도 귀속과 calendar-year return/MDD 정의에는 보정이 필요한 분석 output 이슈가 있다.

## Next Strategic Questions

1. 미국 기술주 약세기의 보완재 탐색은 Country Momentum horizon 조정보다 다른 공격 자산 또는 전략으로 확장한다.
2. 다음 후보는 QQQ weakness episode에서 `benchmark state / candidate return / verdict` 형식으로 동일하게 비교한다.
3. 특히 다음 세 조건을 중점 평가한다.
   - QQQ 하락기에 낮은 downside correlation
   - QQQ 하락 중 양(+)의 수익 또는 반복적인 명확한 초과수익
   - global equity beta와 다른 독립적인 return driver
4. Momentum 12M은 별도의 standalone regional leadership strategy 후보로 필요 시 후속 검증한다.
5. r02 분석 output의 execution-year 귀속 및 calendar-year return/MDD 정의는 보정한다.

## Run Evidence

- `r01 / 20260824-0002`: 10년 horizon 비교와 12M persistence 분석.
- `r02 / 20260825-0001`: correlation pilot 최초 E2E.
- `r02 / 20260825-0002`: 최종 comparison assets, downside correlation, yearly constituent/correlation 분석.
- `r02 / 20260825-0003`: yearly strategy context와 QQQ weakness episode 분석. 3M의 방어 및 replacement attack 역할을 직접 검토.

## Agreed Insights

`Agreed Insights`는 자동 생성하지 않고 User와의 후속 논의를 통해 합의된 내용을 기록한다.

1. 이번 실험은 정적 포트폴리오의 국가 슬롯을 고정하지 않고, 의미 있는 국가만 동적으로 포트폴리오 구성에 기여하게 하는 메커니즘을 만들기 위한 노력에서 시작되었다.
2. 중요한 검증 목적은 현재 정적 구성에서 큰 비중을 차지하는 미국 기술주가 취약해지는 기간에 다른 국가가 대체 공격 또는 방어 역할을 할 수 있는지 확인하는 것이다.
3. Country Momentum 자체의 standalone 성과에서는 12M이 가장 우월했다. SPY 성과에 다소 못 미치지만 MDD와 turnover 등 안정성 측면에서 인상적인 결과를 보였다.
4. 12M은 장기 leadership rotation에는 적합하지만 기존 winner persistence 때문에 빠른 미국 기술주 약세 대응에는 한계가 있다.
5. 3M의 빠른 회전 자체는 확인됐지만, QQQ 약세기에 안정적인 방어수 또는 새로운 공격수 역할을 수행하지 못했다. 2018과 2022에서는 주로 덜 잃는 수준이었고 2020에는 동반 하락했다.
6. 2026 Q1은 EWY 중심 rotation으로 양(+)의 대체 공격 수익을 만든 예외적 성공 사례다. 그러나 EWY의 역사적으로 특이한 강세 regime 영향이 커 일반화할 근거는 부족하다.
7. QQQ 약세 episode별 `QQQ 상태 / 3M 전략 성과 / 판정` 표를 run report와 전략 전역 report 모두에 핵심 evidence로 유지한다.
8. 현재까지의 결론은 Country Momentum이 미국 기술주 약세기의 전체 포트폴리오 보완재로는 적절하지 않다는 것이다. 다만 12M의 standalone regional leadership 전략 가치는 별개로 유지한다.
9. 다음 연구는 국가 momentum의 horizon을 더 최적화하기보다 미국 기술주 약세기에 독립적인 수익 엔진을 제공할 수 있는 다른 공격 자산 또는 전략을 찾는 방향으로 전환한다.