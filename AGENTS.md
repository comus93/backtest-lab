# AGENTS.md

## Source of truth

개발 전 다음 문서를 우선 확인한다.

1. `doc/architecture.md`
2. `doc/specifications.md`
3. Reporting 개발·변경이면 `doc/reporting/specifications.md`와 `doc/reporting/architecture.md`
4. 관련 전략 작업이면 `doc/strategies/`의 해당 revision 명세
5. 백테스트 자동 실행 작업이면 `doc/automation.md`
6. Agent handover가 필요한 작업이면 `ai-share/PROTOCOL.md`

정상적인 백테스트 실행은 GitHub Actions 자동화를 기본 경로로 사용한다. Codex Agent는 workflow 실패, 데이터 이상, 구현 결함 등 deterministic automation만으로 해결하기 어려운 예외 진단에 사용한다.

## Development principles

- Strategy는 자유로운 Python 코드로 유지한다. 고정 DSL을 만들지 않는다.
- Core 책임은 `Strategy -> Runtime -> Portfolio` 구조를 따른다.
- Runtime은 fills와 flow-adjusted performance series를 생성한다.
- Portfolio는 cash와 symbol별 aggregate position을 중심으로 현재 회계 상태를 관리한다.
- Lot은 core에 추가하지 않는다. 특수 전략 상태는 Strategy에서 필요에 따라 관리한다.
- fee/slippage는 단순 global/run-level 설정으로 유지한다.
- market data source는 Local MySQL, FinanceDataReader, Yahoo Finance를 지원하며 Strategy와 Runtime은 source-agnostic하게 유지한다.
- DB 접속 정보와 비밀값은 `.env`에서 읽고 repository에 commit하지 않는다.
- FFN은 performance analysis에 사용한다. Runtime/Portfolio accounting을 FFN에 맡기지 않는다.
- `bt`는 dependency가 아니라 설계 reference다.
- 흔한 요건을 단순하게 처리하고 실제 반복 요구가 없는 추상화는 추가하지 않는다.

## Reporting subsystem

- Reporting 계약은 `doc/reporting/specifications.md`, 설계는 `doc/reporting/architecture.md`를 따른다.
- Reporting은 이미 계산된 Runtime/FFN 결과를 읽기 전용으로 시각화하며, 매매·회계·성과 지표를 재계산하지 않는다.
- 공통 `ReportData`/`ReportConfig`와 차트/테이블/팔레트에는 전략별 종목이나 지표 이름을 하드코딩하지 않는다.
- 전략 특수 로직은 `reporting/adapters/`에 둔다. 공통화 변경 시 PSAR Golden Master 검증을 통과해야 한다.

## Strategy management

전략 명세는 `doc/strategies/YYYYMMDD-<strategy-name>-rNN.md`로 관리한다.

- 날짜는 해당 revision을 만든 날짜다.
- 명세에는 `Strategy ID`와 `Revision`을 명시한다.
- 현재는 `Strategy ID = strategy_name`으로 운영한다. 예: `market_momentum`.
- 향후 별도 식별자가 실제로 필요해지면 Strategy ID 규칙을 확장한다.
- revision을 올릴지는 사용자가 결정한다. Agent/LLM이 임의로 revision을 증가시키지 않는다.
- 새 revision이 생겨도 이전 명세와 구현은 유지한다.
- 구현 수정 이력은 Git이 담당한다.

전략 전역 연구 리포트는 다음 경로를 사용한다.

```text
doc/strategies/reports/<strategy_id>.md
```

전략 리포트는 여러 revision/run을 관통하여 전략의 배경, 핵심 개념, 누적 evidence, hypotheses, 현재 판단, risk/open issue, 다음 전략적 질문과 User-LLM 합의 insight를 기록하는 living document다.

실제 전략 소스는 다음 경로를 사용한다.

```text
src/backtest_lab/strategies/<strategy_id>/<revision>.py
```

예:

```text
src/backtest_lab/strategies/market_momentum/r01.py
```

각 revision module에는 다음 식별값을 둔다.

```python
STRATEGY_ID = "market_momentum"
REVISION = "r01"
```

revision 전략은 명시적으로 import한다.

```python
from backtest_lab.strategies.market_momentum.r01 import MarketMomentumStrategy
```

`strategies/<strategy_id>/__init__.py`에서 특정 revision을 latest/default처럼 재-export하지 않는다.

공통 재사용 전략은 기능 이름의 module로 분리한다. 예: `strategies/target_weight.py`. 기존 public import가 있으면 `strategies/__init__.py`에서 re-export해 호환성을 유지한다.

전략 revision 테스트는 다음 경로를 사용한다.

```text
tests/strategies/<strategy_id>/test_<revision>.py
```

별도 Strategy registry/manager는 실제 필요가 생기기 전까지 두지 않는다.

## Run output management

전략 실행 결과는 다음 경로에 저장한다.

```text
runs/<strategy_id>/<revision>/<run_id>/
```

`run_id` 형식은 다음과 같다.

```text
YYYYMMDD-NNNN
```

운영 규칙:

- 4자리 serial은 같은 전략 revision의 같은 날짜 안에서 `0001`부터 순차 증가한다.
- 날짜가 바뀌면 serial은 다시 `0001`부터 시작한다.
- 실행마다 새 run directory를 만든다. 기존 run 결과를 덮어쓰지 않는다.
- 같은 실행에서 생성된 CSV 산출물은 모두 같은 run directory에 둔다.
- CSV 파일명에는 strategy/revision/run id를 반복하지 않고 산출물 이름만 사용한다.
- 결과 산출물의 종류와 컬럼은 해당 전략 revision 명세를 따른다.
- GitHub Actions 자동 실행은 실제 백테스트에 사용한 공통 price frame을 `input_prices.csv`로 같은 run directory에 저장한다.
- 자동 실행은 analysis report를 만들지 않는다.
- LLM은 raw output을 직접 읽어 사용자에게 먼저 분석을 설명한다.
- 사용자와 논의 후 사용자가 저장을 요청할 때만 같은 run directory에 Markdown analysis report를 작성한다.
- analysis report 기본 파일명은 `analysis-report.md`이며 사용자가 별도 파일명을 지정하면 사용자 지시를 따른다.
- analysis report는 Markdown/YAML tags를 사용하고 계산 사실, LLM 해석, 사용자와 합의된 결론을 구분한다.
- `Agreed Insights`는 자동 생성하지 않는다.
- 기존 `llm-analysis.md`는 과거 운영 방식의 유효한 historical artifact로 유지하며 자동화가 생성하거나 덮어쓰지 않는다.
- Run Analysis와 전략 전역 report는 상호 배타적일 필요가 없으며 필요한 evidence와 insight는 중복 기록할 수 있다.

예:

```text
runs/tripod_nasdaq_leverage/r01/20260904-0001/
├─ input_prices.csv
├─ ffn_stats.csv
├─ performance_summary.csv
├─ equity_curves.csv
├─ daily_signals.csv
├─ regime_summary.csv
├─ yearly_performance.csv
├─ exposure.csv
└─ analysis-report.md   # 사용자 요청이 있을 때만
```

## Backtest automation

GitHub Actions 기반 자동 실행의 상세 규칙은 `doc/automation.md`를 따른다.

Trigger:

```text
automation/backtest-request.json
```

- LLM은 실행을 요청할 때 이 파일을 갱신한다.
- request는 `strategy_id`, `revision`, `mode` 등 declarative field만 포함한다.
- shell command, Python expression, 임의 module path 같은 executable text를 넣지 않는다.
- dispatcher가 `(strategy_id, revision, mode)`를 source code의 명시적 allow-list에 매핑한다.
- LLM이 run serial을 지정하지 않는다. dispatcher가 request date와 기존 run directory를 보고 다음 serial을 배정한다.
- workflow는 pytest 통과 후에만 실데이터 backtest를 실행한다.
- output과 latest manifest는 GitHub Actions가 commit/push한다.

Latest result manifest:

```text
automation/backtest-result.md
```

- 이 파일은 performance report가 아니다.
- latest successful run의 identity, output directory, output filename, 향후 `report_url`만 지칭한다.
- CAGR, Sharpe, drawdown 등 raw result 값은 복사하지 않는다.
- LLM은 manifest가 가리키는 raw output 파일을 직접 읽는다.

## Implementation discipline

- 구현은 작고 추적 가능하게 유지한다.
- Strategy 판단, Runtime execution, Fill, Portfolio 변경의 경계가 코드에서 명확해야 한다.
- 동일 입력과 설정은 동일 결과를 만들어야 한다.
- core 테스트는 `doc/specifications.md`, 전략 테스트는 해당 revision 명세의 acceptance/test scenarios를 기준으로 한다.
- 신규 구현의 초기 검증에서는 전체 테스트를 실행한다. 이후 수정에서는 변경 영향 범위의 테스트만 실행하며, 영향 범위가 불명확하거나 공통/core 변경이 있는 경우에만 필요한 범위로 확대한다.
- 설계 결정을 바꿔야 할 필요가 생기면 임의로 확대 구현하지 말고 blocker/question으로 공유한다.

## AI Share

ChatGPT와 Codex 간 메시지 및 세션 handover가 실제로 필요한 경우 `./ai-share/PROTOCOL.md`를 따른다.

정상적인 백테스트 실행/검증 결과 전달에는 `agent-to-llm.md`를 사용하지 않는다. GitHub Actions의 `automation/backtest-result.md`와 해당 run raw outputs가 기본 전달 경로다.

Agent를 예외 진단에 사용한 경우에만 작업 결과를 `agent-to-llm.md`에 최소한으로 정리하고 GitHub remote에 commit/push한 뒤 완료로 간주한다.
