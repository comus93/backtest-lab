# Session Handover

created_at: 2026-09-07T06:20:00+09:00

## 1. Project Overview

Repository: `comus93/backtest-lab`

이 프로젝트는 자연어/LLM 기반으로 투자 전략을 정의하고, Python Runtime + Strategy + Portfolio 구조로 백테스트를 수행하며, FFN을 성과 분석에 사용하는 개인 연구용 백테스트 랩이다.

핵심 운영 방향은 다음과 같다.

- LLM은 전략 설계, 코드/테스트 작성, 실행 요청 생성, raw output 분석을 담당한다.
- 정상적인 백테스트 실행은 Codex Agent가 아니라 GitHub Actions가 담당한다.
- Codex Agent는 Action 실패, 데이터 이상, 구현 문제처럼 원인 분석이 필요한 예외 상황에만 사용한다.
- 실제 계산 결과와 LLM 해석을 분리한다.
- 사용자와 LLM이 논의하여 합의한 결론은 사용자 요청이 있을 때만 analysis report markdown으로 저장한다.

Source of truth는 `AGENTS.md`, `doc/architecture.md`, `doc/specifications.md`, 관련 전략 revision 명세를 우선 확인한다.

---

## 2. GitHub Actions Backtest Automation: Phase 1 완료

Phase 1의 목표는 Agent 없이 아래 흐름으로 백테스트를 실행하는 것이었다.

```text
LLM
  -> automation/backtest-request.json 수정
  -> GitHub Actions trigger
  -> pytest
  -> registered backtest 실행
  -> run raw outputs 생성
  -> automation/backtest-result.md 갱신
  -> GitHub Actions가 output을 commit/push
  -> LLM이 raw output 직접 읽음
  -> 사용자에게 분석 보고
  -> 사용자 요청 시 analysis report 저장
```

### 주요 파일

```text
automation/
├─ backtest-request.json
└─ backtest-result.md

.github/workflows/
└─ backtest.yml

src/backtest_lab/
└─ automation.py

tests/
└─ test_automation.py

doc/
└─ automation.md
```

### `automation/backtest-request.json`

LLM이 변경하는 실행 요청 파일이며 이 파일 변경이 GitHub Actions trigger다.

현재 request는 다음 새 전략 실행 상태다.

```json
{
  "request_id": "20260907T062500+0900",
  "strategy_id": "sp500_top2_market_cap",
  "revision": "r01",
  "mode": "baseline",
  "start": "2016-01-01",
  "end": "2026-01-01"
}
```

중요 원칙:

- request에는 shell command를 넣지 않는다.
- `(strategy_id, revision, mode)`가 `src/backtest_lab/automation.py`의 allow-list/registry에 등록된 실행만 가능하다.
- `run_id`는 LLM이 입력하지 않고 dispatcher가 자동 생성한다.
- 기존 run directory는 절대 overwrite하지 않는다.

### `automation/backtest-result.md`

이 파일은 성과 내용을 복사하는 보고서가 아니다.

역할은 오직 최신 실행의:

- status
- request_id
- strategy_id
- revision
- mode
- run_id
- output_directory
- default output filenames
- 향후 `report_url`

을 가리키는 manifest다.

LLM은 이 manifest에서 run 위치를 알아낸 뒤 실제 CSV/MD raw outputs를 직접 읽어서 사용자에게 리포팅해야 한다.

### Analysis report 운영 원칙

자동 실행 직후 analysis report를 자동 생성하지 않는다.

정상 흐름:

```text
raw result
 -> LLM 분석
 -> 사용자에게 설명
 -> 사용자와 논의
 -> 사용자 요청
 -> 합의된 분석을 Markdown analysis report로 저장
```

analysis report에는 YAML/Markdown tags를 사용한다.

기본 위치는 해당 run directory다.

예:

```text
runs/<strategy>/<revision>/<run_id>/analysis-report.md
```

사용자가 파일명을 별도로 지정하면 사용자 지시를 우선한다.

---

## 3. Automation Phase 1 실제 검증

초기 POC로 `tripod_nasdaq_leverage/r01/baseline`을 GitHub Actions로 실행했고 성공했다.

- 전체 pytest 성공
- Yahoo 실데이터 백테스트 성공
- raw output 생성
- `input_prices.csv` 저장
- manifest 생성
- GitHub Actions bot commit/push 성공

그 실행은:

```text
runs/tripod_nasdaq_leverage/r01/20260904-0001/
```

이었다.

`input_prices.csv`를 각 run에 저장하도록 한 이유는 Yahoo adjusted price가 재조회 시 미세하게 달라질 수 있어 과거 실험 입력을 snapshot으로 고정하기 위해서다.

현재 dispatcher에는 최소한 다음 실행이 등록되어 있다.

```text
tripod_nasdaq_leverage / r01 / baseline
tripod_nasdaq_leverage / r01 / sensitivity
sp500_top2_market_cap / r01 / baseline
```

새 전략 추가를 위해 automation의 required outputs는 전략별 manifest를 허용하도록 일반화했다. Tripod 전용 7개 output을 모든 전략에 강제하지 않는다.

---

## 4. 향후 Automation Roadmap

Phase 1 이후 사용자가 공유한 방향이다. 아직 구현하지 않았다.

### Phase 2 이후 목표

GitHub Actions에 Analyzer/Reporter를 추가한다.

```text
Backtest raw outputs
  -> Analyzer
  -> Reporting layer
  -> Dynamic HTML
  -> GitHub Pages publish
  -> automation/backtest-result.md에 report_url 기록
  -> LLM이 사용자에게 GitHub Pages 링크 안내
```

Reporting 기능은 사용자의 다른 프로젝트:

```text
comus93/portfolio-optimizer-kr
```

의 Backtesting module reporting 기능을 재활용한다.

단, Backtest Lab에서는 FFN `calc_stats()`의 전체 metric을 누락 없이 보여줄 수 있도록 확장해야 한다.

Reporter 구조는 장기적으로:

```text
공통 FFN/portfolio 성과 영역
+ strategy-specific visualization 영역
```

을 목표로 한다.

이 단계는 사용자가 step-by-step으로 검토하며 진행하기로 했으므로 바로 구현하지 말 것.

---

## 5. 신규 전략: `sp500_top2_market_cap` r01

사용자가 현재 자동화 상태로 새로운 전략을 실제로 돌려보자고 요청했고 새 전략으로 정식 등록했다.

### 파일

```text
doc/strategies/20260907-sp500-top2-market-cap-r01.md
src/backtest_lab/strategies/sp500_top2_market_cap/r01.py
tests/strategies/sp500_top2_market_cap/test_r01.py
```

### 전략 정의

Strategy ID:

```text
sp500_top2_market_cap
```

Revision:

```text
r01
```

기간:

```text
2016-01-01 ~ 2025-12-31
```

즉 완결된 10개 연도.

규칙:

1. 전년도 마지막 거래일 기준 S&P 500 시가총액 1위, 2위 기업을 선정한다.
2. 다음 해 첫 거래일에 두 기업을 50% / 50%로 보유한다.
3. 연 1회 리밸런싱한다.
4. 비교 benchmark는 SPY Buy & Hold다.
5. global fee/slippage 설정을 그대로 사용한다.
6. Alphabet 기업 순위는 Alphabet 단위로 판단하고 실제 tradable ticker는 `GOOGL`을 사용한다.

### 연도별 실제 selection

```text
2016: Apple / Alphabet
2017: Apple / Alphabet
2018: Apple / Alphabet
2019: Microsoft / Apple
2020: Apple / Microsoft
2021: Apple / Microsoft
2022: Apple / Microsoft
2023: Apple / Microsoft
2024: Apple / Microsoft
2025: Apple / Nvidia
```

selection raw output:

```text
runs/sp500_top2_market_cap/r01/20260907-0001/annual_selections.csv
```

---

## 6. `sp500_top2_market_cap` r01 GitHub Actions Run

Run:

```text
runs/sp500_top2_market_cap/r01/20260907-0001/
```

GitHub Actions run은 성공했다.

- full pytest: `87 passed`
- data coverage: 2016-01-04 ~ 2025-12-31
- manifest 검증 성공
- raw output commit/push 성공

생성 output:

```text
input_prices.csv
annual_selections.csv
equity_curves.csv
ffn_stats.csv
fills.csv
performance_summary.csv
yearly_performance.csv
```

### 핵심 성과

Top-2 Strategy:

- total return: `+891.96%`
- CAGR: `25.81%`
- volatility: `26.72%`
- Sharpe: `0.995`
- Sortino: `1.447`
- Max Drawdown: `-33.83%`
- Calmar: `0.763`
- avg monthly turnover: `1.02%`

SPY Buy & Hold:

- total return: `+300.19%`
- CAGR: `14.89%`
- volatility: `18.00%`
- Sharpe: `0.863`
- Sortino: `1.215`
- Max Drawdown: `-33.72%`
- Calmar: `0.442`

### 현재 LLM 해석

단순한 규칙임에도 2016~2025 구간에서는 Top-2가 SPY 대비 매우 강한 성과를 냈다.

특히:

```text
CAGR 25.81% vs 14.89%
MDD -33.83% vs -33.72%
Sharpe 0.995 vs 0.863
```

이어서 연구할 가치가 높다.

하지만 해당 10년은 미국 mega-cap technology가 역사적으로 매우 강했던 기간이므로, 이 결과만으로 전략 우수성을 확정하면 안 된다.

아직 사용자와 최종 합의된 analysis report는 생성하지 않았다.

---

## 7. 다음 연구 전략: 월/분기 시총 Top-2

사용자가 다음 실험으로 연간 selection보다 더 자주 시가총액 1위/2위를 재계산하는 전략을 원한다.

처음 제안은:

```text
월말 시가총액 1·2위 계산
 -> 다음 달 첫 거래일 50% / 50%
 -> 매월 리밸런싱
 -> 20년
```

이후 데이터 문제를 검토하면서 **분기 리밸런싱으로 20년 결과를 낼 수 있는지 먼저 확인**하기로 했다.

향후 benchmark는 반드시 둘 다 포함한다.

```text
SPY Buy & Hold
QQQ Buy & Hold
```

### 사용자와 확정한 전략 철학

- 시가총액 1위/2위가 근소한 차이로 뒤집히더라도 그대로 기계적으로 1위/2위를 선택한다.
- 순위 안정화를 위한 임의 buffer/hysteresis를 넣지 않는다.
- 전략 정의 자체가 `매 시점 산출된 시총 1위/2위를 보유`하는 것이다.
- 일반적인 survivorship-bias 경고를 이 전략의 주된 문제로 과장하지 않는다.
- 사용자는 3위 이하 기업은 보유 대상이 아니므로 일반적인 survivor universe 문제와 성격이 다르다고 지적했다.
- 다만 과거 어떤 기업이 실제 당시 Top-2였는데 현재 데이터 universe에서 완전히 사라진 경우를 놓치지 않는지는 별도의 data completeness 문제로 구분한다.

---

## 8. Yahoo Finance 과거 시가총액 계산 문제

Yahoo에서 장기 가격 자체는 충분히 구할 수 있다.

시가총액은:

```text
market_cap = historical price * historical shares outstanding
```

으로 계산 가능하다.

문제는 historical shares outstanding이다.

`yfinance.Ticker.get_shares_full(start, end)`가 historical shares series를 제공하지만:

- 모든 거래일에 값이 있는 형태가 아니다.
- 불규칙한 날짜에 관측된다.
- 요청한 20년 전체를 실제로 반환하지 않는다.
- 일부 긴 기간에 큰 공백이 존재한다.

사용자가 "적어도 분기마다 하나 이상은 존재하는가? 그러면 분기 리밸런싱 가능하지 않은가?"라고 질문했고, 이를 추측하지 않고 실제 GitHub Actions에서 Yahoo 데이터를 조회해 진단했다.

---

## 9. Yahoo Shares 20-Year Quarterly Coverage Diagnostic

기간:

```text
2006-01-01 ~ 2025-12-31
```

총:

```text
80 quarters
```

진단 ticker 후보군:

```text
AAPL
MSFT
GOOGL
NVDA
AMZN
META
XOM
GE
BRK-B
WMT
JPM
```

이 후보군은 지난 20년 large-cap / potential Top-2 relevance를 보기 위해 넓게 잡았다.

### 결과 파일

진단용 일회성 Action/script는 실행 후 제거했다.

결과 증거만 repo에 남겼다.

```text
research/yahoo-shares-quarterly-coverage.csv
research/yahoo-shares-quarterly-summary.md
```

### 핵심 결과

Yahoo `get_shares_full()`만으로 20년 분기별 shares coverage는 불가능했다.

대표 결과:

| ticker | observed quarters / 80 | coverage | first observation | max gap days |
|---|---:|---:|---|---:|
| AAPL | 36 | 45.0% | 2015-10-28 | 468 |
| MSFT | 38 | 47.5% | 2015-10-23 | 393 |
| GOOGL | 37 | 46.3% | 2015-10-29 | 477 |
| NVDA | 30 | 37.5% | 2015-11-18 | 629 |
| AMZN | 37 | 46.3% | 2015-10-23 | 472 |
| XOM | 37 | 46.3% | 2015-11-04 | 469 |
| GE | 37 | 46.3% | 2015-11-20 | 473 |
| BRK-B | 37 | 46.3% | 2015-11-06 | 466 |
| WMT | 37 | 46.3% | 2015-12-02 | 438 |
| JPM | 37 | 46.3% | 2015-11-02 | 461 |

핵심은 대부분의 주요 종목이 **2015년 4분기 이전 historical shares outstanding을 Yahoo가 반환하지 않았다는 것**이다.

또 2016년 이후에도 모든 분기에 값이 존재하지 않는다.

예를 들어 AAPL도 2016Q2, 2017Q4, 2018Q1~Q3 등에 직접 관측값이 없다.

### 판정

```text
Yahoo historical price only: 충분
Yahoo get_shares_full 20년 분기 Top-2: 불가
Yahoo + latest-known shares 2016~2025 근사: 계산은 가능하지만 품질 낮음
```

latest-known shares를 forward-fill하면 계산은 가능하지만 주요 종목의 관측 공백이 1년 이상인 경우가 있어 20년 전략의 기준 데이터로 쓰기는 부적절하다고 판단했다.

---

## 10. Current Research Question / Next Step

다음 창에서 가장 먼저 이어갈 문제는 이것이다.

> **2006~2025 약 20년 동안 분기말마다 S&P 500 시가총액 1위/2위를 산출할 수 있는 historical market-cap 또는 historical shares outstanding 데이터 소스를 확보하고, 분기 Top-2 50/50 전략을 SPY와 QQQ Buy & Hold와 비교할 것.**

### 원하는 전략 초안

새 Strategy ID는 아직 확정/등록하지 않았다. 새 창에서 사용자와 이름을 정해도 된다.

예상 규칙:

```text
기간: 약 20년, 우선 2006~2025
ranking date: 각 분기 마지막 거래일
ranking metric: 당시 시가총액
selection: 1위 / 2위
weight: 50% / 50%
execution: 다음 분기 첫 거래일
rebalance: quarterly
benchmark: SPY Buy & Hold + QQQ Buy & Hold
T+1/no-lookahead semantics 유지
```

시총 순위가 근소하게 뒤집혀도 그대로 기계적 순위를 따른다.

### 데이터 source 탐색 우선순위

Yahoo shares는 20년용으로 탈락했다.

다음 창에서는 먼저:

1. 무료 또는 저비용으로 20년 이상 historical market cap / shares outstanding을 제공하는 데이터 source 조사
2. 분기 기준 coverage와 라이선스/API 제한 확인
3. 필요하면 market-cap ranking 전용 source와 price source(Yahoo)를 분리
4. raw ranking evidence를 반드시 run output으로 저장

을 진행한다.

예상 output은 다음 형태가 좋다.

```text
input_prices.csv
quarterly_market_cap_ranking.csv
quarterly_selections.csv
fills.csv
ffn_stats.csv
performance_summary.csv
yearly_performance.csv
equity_curves.csv
```

`quarterly_market_cap_ranking.csv`에는 최소한:

```text
ranking_date
company
ticker
price
shares_outstanding
shares_reference_date
market_cap
rank
data_age_days
source
```

를 남겨, LLM이 raw 데이터를 보고 특정 분기의 ranking 근거를 검증할 수 있게 한다.

---

## 11. Important Files to Read First in New Chat

새 창의 LLM은 다음 순서로 읽고 바로 이어가면 된다.

```text
AGENTS.md
doc/architecture.md
doc/specifications.md
doc/automation.md
ai-share/llm-to-llm.md

doc/strategies/20260907-sp500-top2-market-cap-r01.md
src/backtest_lab/strategies/sp500_top2_market_cap/r01.py
src/backtest_lab/automation.py

automation/backtest-request.json
automation/backtest-result.md

runs/sp500_top2_market_cap/r01/20260907-0001/performance_summary.csv
runs/sp500_top2_market_cap/r01/20260907-0001/ffn_stats.csv
runs/sp500_top2_market_cap/r01/20260907-0001/annual_selections.csv
runs/sp500_top2_market_cap/r01/20260907-0001/yearly_performance.csv

research/yahoo-shares-quarterly-summary.md
research/yahoo-shares-quarterly-coverage.csv
```

---

## 12. Immediate Instruction for the Next LLM

새 창에서 사용자가 이 handover를 읽고 이어가자고 하면:

1. 현재 GitHub Actions automation Phase 1은 완료 상태로 간주한다.
2. annual `sp500_top2_market_cap/r01`을 다시 구현하거나 반복 실행하지 않는다.
3. 먼저 Yahoo 20-year shares diagnostic 결과를 확인한다.
4. 다음 연구 목표는 **20년 quarterly market-cap Top-2 전략을 위한 데이터 source 확보**다.
5. data source를 정하기 전 임의 synthetic market cap을 사용하지 않는다.
6. 최종 백테스트에는 SPY와 QQQ를 모두 benchmark로 포함한다.
7. ranking이 근소하게 바뀌어도 1위/2위를 그대로 선택한다.
8. 전략 구현 후 실행은 `automation/backtest-request.json` 변경으로 GitHub Actions를 사용한다.
9. 실행 후 LLM은 `automation/backtest-result.md`가 가리키는 raw outputs를 직접 읽어 사용자에게 분석한다.
10. analysis report는 사용자와 논의 후 사용자 요청이 있을 때만 저장한다.
