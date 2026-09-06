# S&P 500 Top-2 Market Cap Strategy r01

- Strategy ID: `sp500_top2_market_cap`
- Revision: `r01`
- Status: initial approved implementation

## 1. Research question

S&P 500 구성 기업 가운데 시가총액 1위와 2위 기업에만 집중 투자하고, 매년 시가총액 순위를 갱신해 동일가중으로 리밸런싱했을 때 단순 S&P 500 투자(SPY Buy & Hold)보다 우수한 장기 성과를 만들었는지 확인한다.

이 전략은 과거 각 연도의 수익률을 보고 종목을 고르는 것이 아니라 **전년도 말에 이미 관측 가능한 시가총액 순위**를 다음 연도 투자에 사용한다. 따라서 다음 연도의 수익을 미리 사용하는 look-ahead를 허용하지 않는다.

## 2. Backtest period

완결된 10개 달력연도를 사용한다.

- Start: `2016-01-01`
- End: `2026-01-01` exclusive
- Active trading period: 2016년 첫 거래일 ~ 2025년 마지막 거래일

## 3. Selection rule

연도 `Y`의 포트폴리오는 `Y-1`년 말 기준 S&P 500 기업 시가총액 순위 1위와 2위 기업으로 결정한다.

- 각 기업 50%
- 매년 첫 거래일에 50/50으로 리밸런싱
- 같은 두 기업이 연속해서 선정되어도 연 1회 50/50으로 비중을 복원한다.
- 현금 목표 비중은 0%다.
- 세금/납입은 없다.
- fee/slippage는 project global run-level 설정을 따른다.

### Fixed historical selections for r01

| 투자연도 | 순위 기준 | 1위 | 2위 | 실제 ticker |
| --- | --- | --- | --- | --- |
| 2016 | 2015 year-end | Apple | Alphabet | AAPL / GOOGL |
| 2017 | 2016 year-end | Apple | Alphabet | AAPL / GOOGL |
| 2018 | 2017 year-end | Apple | Alphabet | AAPL / GOOGL |
| 2019 | 2018 year-end | Microsoft | Apple | MSFT / AAPL |
| 2020 | 2019 year-end | Apple | Microsoft | AAPL / MSFT |
| 2021 | 2020 year-end | Apple | Microsoft | AAPL / MSFT |
| 2022 | 2021 year-end | Apple | Microsoft | AAPL / MSFT |
| 2023 | 2022 year-end | Apple | Microsoft | AAPL / MSFT |
| 2024 | 2023 year-end | Apple | Microsoft | AAPL / MSFT |
| 2025 | 2024 year-end | Apple | Nvidia | AAPL / NVDA |

Alphabet은 기업 단위 시가총액 순위로 선택하며 투자 가능한 대표 share class로 `GOOGL`을 사용한다.

## 4. Historical ranking provenance

r01의 연말 순위는 연말 시가총액 historical tables를 사용해 고정한다. 주요 source는 Financial Times 기반 historical market-cap tables를 정리한 아래 자료다.

- https://en.wikipedia.org/wiki/List_of_public_corporations_by_market_capitalization

해당 자료의 2015~2024 year-end fourth-quarter ranking을 사용했다. 모든 r01 선정 기업은 해당 시점 S&P 500 구성 기업이다.

향후 ranking data source를 교체하거나 point-in-time S&P constituent database를 도입하면 revision 변경 여부를 사용자와 별도 결정한다.

## 5. Market data

Yahoo Finance adjusted close를 사용한다.

Required price symbols:

- `AAPL`
- `GOOGL`
- `MSFT`
- `NVDA`
- `SPY`

각 자동 run은 실제 사용 가격을 `input_prices.csv`로 저장한다.

## 6. Execution semantics

- 전년도 말 순위는 다음 연도 첫 거래일 이전에 알려진 정보로 간주한다.
- 해당 연도 첫 active trading step에서 즉시 목표 50/50 포트폴리오로 리밸런싱한다.
- 이후 해당 연도에는 추가 리밸런싱하지 않는다.
- 다음 연도 첫 거래일에 새 순위 기반 50/50 목표로 리밸런싱한다.
- Runtime의 sell-first execution과 global fee/slippage 규칙을 그대로 따른다.

## 7. Benchmark

`SPY Buy & Hold`를 동일 active period, 동일 initial cash, 동일 fee/slippage 조건에서 비교한다.

## 8. Initial capital

- $1,000,000

## 9. Required outputs

자동 실행 run directory에 다음 raw outputs를 저장한다.

- `input_prices.csv`
- `ffn_stats.csv`
- `performance_summary.csv`
- `equity_curves.csv`
- `yearly_performance.csv`
- `annual_selections.csv`
- `fills.csv`

### performance_summary.csv

최소 포함:

- total_return
- cagr
- volatility
- sharpe
- max_drawdown
- calmar
- avg_monthly_turnover
- avg_nominal_exposure

성과 통계는 가능한 경우 FFN 결과를 사용한다.

### ffn_stats.csv

설치된 FFN `calc_stats()`가 제공하는 default metric set을 축약하지 않고 저장한다.

## 10. Acceptance tests

1. 2016 첫 거래일에 AAPL/GOOGL 50/50 목표가 생성된다.
2. 한 연도 내 두 번째 step에서는 rebalance하지 않는다.
3. 2019 첫 거래일에 MSFT/AAPL 50/50으로 전환된다.
4. 2025 첫 거래일에 AAPL/NVDA 50/50으로 전환된다.
5. 연속 연도에 같은 두 종목이 선정되어도 새해 첫 거래일에는 50/50 비중 복원 주문을 생성할 수 있다.
6. output에 strategy와 SPY benchmark 모두 존재한다.
7. 자동화 request는 `sp500_top2_market_cap/r01/baseline`만 허용한다.
8. 자동화 run은 고정 기간 2016-01-01 ~ 2026-01-01을 요구한다.

## 11. Interpretation boundary

GitHub Actions는 계산과 raw output 생성만 담당한다. 투자적 해석은 자동 생성하지 않는다.

LLM은 `automation/backtest-result.md`가 가리키는 raw outputs를 직접 읽고 사용자에게 결과를 보고한다. 사용자와 논의 후 사용자 요청이 있을 때만 run directory에 Markdown analysis report를 생성한다.
