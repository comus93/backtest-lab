# PSAR Segment Duration: Asymmetric Nasdaq Direction Strategy

Strategy ID: `psar_segment_duration`  
Revision: `r01`  
Revision date: `2026-11-03`  
Status: `draft / awaiting remaining user decisions`

> 이 문서는 사용자와 LLM이 2026-11-03 논의한 원안의 최초 전략 명세다. **확정 사항**과 **미확정 사항**을 구분한다. 사용자 승인 전 구현·백테스트를 시작하거나 다른 지표/추가 청산 규칙을 넣지 않는다.

## 1. Purpose / investment hypothesis

나스닥의 일봉 Parabolic SAR(PSAR)을 단순 방향 전환 매수·매도 신호로 쓰지 않고, **현재 PSAR 방향 구간의 지속 거래일 수가 직전 반대 방향 구간의 지속 거래일 수를 초과했을 때** 추세가 확인되었다고 간주한다.

목적은 단일 지표를 이용해 짧은 방향 전환 노이즈를 줄이면서 확인된 추세만 보유하는 것이다. 상승과 하락에 서로 다른 배수의 ETF를 사용하는 비대칭 포지셔닝을 채택한다.

이는 **검증 대상 가설**이지 성과 또는 유효성이 입증된 사실이 아니다. 특히 직전 반대 구간 길이가 확인의 좋은 기준인지, 긴 하락 후 빠른 반등을 놓치지 않는지 등을 검증한다.

## 2. Confirmed portfolio universe

- 상승 방향: `QLD` (ProShares Ultra QQQ, Nasdaq-100 **일간 +2x**), 보유 시 포트폴리오 **100%**.
- 하락 방향: `PSQ` (ProShares Short QQQ, Nasdaq-100 **일간 -1x**), 보유 시 포트폴리오 **100%**.
- 진입 조건 미충족, 전환 대기 또는 최초 미확정 기간: **현금 100%**.
- 롱/인버스 동시 보유 없음. 차입·마진·분할 진입 없음.
- 추후 PSQ가 수익률/위험을 훼손하면 제거하는 별도 실험을 고려할 수 있으나, **r01 원안에서는 포함**한다.
- ETF의 목표 일일 배수는 장기간 누적수익률 보장 배수가 아니다.

## 3. Data and observation (confirmed)

- 데이터 로더: **FinanceDataReader (FDR)**. Local MySQL 기본값 사용 안 함.
- 신호 주기: **일봉**, 미국 거래일을 기준으로 구간 길이를 센다.
- PSAR 신호 계산에는 기초자산의 일별 **High / Low** (및 초기 추세 판정에 필요한 가격 입력)를 사용한다.
- QLD/PSQ 보유 성과 및 체결에 쓰는 가격은 로더에서 일관된 일별 가격 계열을 구성한다.
- 입력 데이터에 결측, 가격 조정 불일치가 있으면 임의로 forward-fill하지 않고 기록/처리 기준을 명시한다.
- 현재 `load_market_data`는 가격 컬럼 한 종류를 반환하므로, PSAR OHLC 입력은 전략별 데이터 준비 단계에서 조합한다. 합의 없이 Runtime/Core를 변경하지 않는다.

**미확정:** PSAR을 계산할 나스닥 기초 시계열(예: Nasdaq-100 지수, QQQ 등). QLD/PSQ 자체의 서로 다른 가격에서 각각 계산하는 방식으로 임의 결정하지 않는다. FDR 해당 티커 및 OHLC 과거 coverage도 확인해야 한다.

## 4. Historical test windows (confirmed plan)

ETF 두 종목은 2006-06-19 상장. 단, **상장일과 FDR 실데이터 커버리지는 다르므로 실제 확보 가능 구간 확인이 선행되어야 한다.**

성과는 아래 **5년 단위 독립 구간**으로 구분한다.

1. `2007-01-01 ~ 2011-12-31`
2. `2012-01-01 ~ 2016-12-31`
3. `2017-01-01 ~ 2021-12-31`
4. `2022-01-01 ~ 2026-12-31`: 현재 날짜(2026-11-03) 및 FDR 마지막 유효 거래일까지만 평가하는 **미완료 구간**.

모든 기간의 시작·종료는 실제 거래일에 맞추고, 각 구간의 수익률/포트폴리오는 독립 초기화한다. 신호 계산에만 이전 히스토리를 warm-up으로 활용한다. 첫 분석 기간 이전 2006년 하반기를 초기 PSAR 계산 및 직전 구간 식별에 활용한다. 이후 분석 구간도 이전 거래일 데이터를 신호 warm-up으로 사용할 수 있지만 미래 가격을 쓰지 않는다.

**미확정/실행 시 검증:** FDR의 신호 기초자산 및 QLD/PSQ가 필요한 모든 기간을 실제로 제공하는지. PSAR 초기화 알고리즘과 완전한 직전 구간을 확보하는 최소 warm-up 조건.

## 5. PSAR state definition and segment counting

PSAR 점이 가격 아래에 있으면 `UP`, 위에 있으면 `DOWN` 상태로 정의한다. PSAR 전환이 확정된 **해당 거래일을 새 구간 1일째**로 센다.

- `current_len`: 오늘까지 연속된 현재 PSAR 상태의 거래일 수. 시작일 포함.
- `previous_opposite_len`: 현재 구간 바로 앞에 **완료된 직전 반대 방향 PSAR 구간**의 거래일 수.
- 매매 확인 조건은 엄격한 `current_len > previous_opposite_len` (**같으면 진입하지 않음**)이다.
- 첫 데이터 구간처럼 직전 반대 구간의 길이를 모르거나 완전하지 않으면 확인할 수 없으므로 진입하지 않는다.
- 거래일 수는 가격 변화 폭, 달력 일수 또는 현재 가격과 PSAR 간격으로 대체하지 않는다.

## 6. Entry / exit / position rules (confirmed strategy logic)

### UP segment

- 현재 PSAR이 `UP`이고 `current_len > previous_opposite_len`이 되는 첫 거래일에 QLD 100% 진입.
- 진입 후 PSAR `UP`이 지속되는 동안 계속 보유한다.
- PSAR이 `DOWN`으로 전환되는 거래일에는 **즉시 QLD 전량 청산**한다.
- 그날 새 `DOWN` 구간 길이가 직전 `UP` 구간 길이를 초과할 수 없으므로 자동으로 PSQ에 진입하는 것은 아니다. 다음 하락 확인 신호를 기다리며 현금 보유.

### DOWN segment

- 현재 PSAR이 `DOWN`이고 `current_len > previous_opposite_len`이 되는 첫 거래일에 PSQ 100% 진입.
- 진입 후 PSAR `DOWN`이 지속되는 동안 계속 보유한다.
- PSAR이 `UP`으로 전환되는 거래일에는 **즉시 PSQ 전량 청산**한다.
- 상승 확인 신호 전에는 현금 보유.

### Other rules

- 진입은 한 구간당 최대 한 번이며, 같은 PSAR 구간 안에서 추가 매수·조기 청산·재진입 없음.
- PSAR 기울기, PSAR-가격 간격의 축소/확대, SMA, MACD, RSI 등은 **r01 매매 조건으로 추가하지 않는다**.
- 기울기/간격은 향후 연구용 관찰 필드로만 기록할 수 있다.

## 7. Initial exploratory execution semantics (confirmed, intentional limitation)

- 1차 탐색 백테스트는 **현 Runtime의 same-step reference-price 즉시 체결**을 사용한다.
- 즉 오늘의 완성된 PSAR 신호를 사용하고 같은 날짜 입력 기준 가격으로 체결하는 비현실적 가정을 **의도적으로 허용**한다.
- PSAR이 당일 High/Low를 사용하므로 이런 결과에는 **look-ahead/same-bar fill bias**가 있고 실거래 가능 성과로 해석하면 안 된다.
- 1차 결과가 유망할 경우, 별도 논의를 통해 `T일 종가 신호 → T+1 거래일 실제 체결 가능 가격` 등의 현실적 검증을 한다.
- fee/slippage는 전략별 임의 계산하지 않고 프로젝트 전역/실행 설정을 따른다.

## 8. Baselines and evaluation

최초 목표는 사용자 원안 자체의 유효성을 판단하는 것이다. 다음 비교는 **연구 제안**이며 추가 거래 규칙으로 확정된 것이 아니다.

- Benchmarks: `QQQ Buy & Hold`, `QLD Buy & Hold` (가능한 동일 검증 기간).
- 선택적 비교 실험: 필터 없이 PSAR 전환 즉시 진입하는 전략, 고정 N 거래일 확인 전략, 인버스 PSQ를 제외한 QLD/현금 전략.
- FFN 기본 성과 통계: CAGR, 총수익률, Sharpe, MDD 등 표준 전 항목.
- 추가 진단: 구간별 보유 비율/거래 횟수, long vs inverse 기여도, PSAR 구간 길이 분포, 필터로 회피한 거래와 놓친 수익 구간, 기간별 성과와 거래비용.

## 9. Expected run outputs

정상적인 자동 백테스트 결과는 프로젝트 규칙에 따라 다음에 **각 실행별 새 디렉터리**로 저장한다.

`runs/psar_segment_duration/r01/<run_id>/`

예정 아티팩트:
- `input_prices.csv`: 실제 백테스트에 사용한 입력 스냅샷(PSAR 신호에 필요한 High/Low 포함하도록 포맷 명시)
- `ffn_stats.csv`
- `performance_summary.csv`
- `equity_curves.csv`
- `daily_signals.csv` (signal_date, psar_value, psar_direction, current_len, previous_opposite_len, entry_eligible, held_symbol, action)
- `segment_summary.csv`
- `yearly_performance.csv`
- `fills.csv`

분석 리포트 `analysis-report.md`는 결과를 사용자와 논의한 다음 사용자가 **저장 요청할 경우에만** 작성한다.

## 10. Acceptance / test scenarios (implementation stage)

Synthetic data로 다음을 검증한다.

1. 동일 길이에서는 진입하지 않고, 현재 구간이 직전 구간보다 1거래일 길어지면 진입.
2. PSAR 전환 당일 보유 포지션 전량 청산 및 현금 전환.
3. 상승 +2x QLD, 하락 -1x PSQ의 종목 매핑과 100% 비중.
4. 동일 구간 중복 주문 없음, 각 PSAR 전환마다 count 초기화.
5. 최초 불완전 구간은 잘못된 진입 없음.
6. 5년 구간별 독립 초기 자금/성과, 과거 warm-up을 이용한 신호 계산과 미래 정보 유출 방지.
7. same-bar 체결 한계가 명세/리포트에 명시되고, 기존 Runtime fee/slippage와 Fill 일관성 유지.
8. 데이터 부족·결측·OHLC 불일치에 대해 조용히 왜곡하지 않고 오류/기록.

## 11. Implementation boundary / execution

- Strategy 소스 예정: `src/backtest_lab/strategies/psar_segment_duration/r01.py`
- Strategy 테스트 예정: `tests/strategies/psar_segment_duration/test_r01.py`
- 정상 E2E 실행 환경: **GitHub Actions** (Python 3.11, pytest 선행).
- 별도 승인 후 GitHub Actions dispatcher에 `(psar_segment_duration, r01, baseline)` 명시적 매핑을 추가하고, 요청 파일 `automation/backtest-request.json`으로 실행한다.
- 전략 구현은 Core와 분리하고, FDR 데이터 준비 코드는 data boundary에 두며, 불필요한 추상화·엔진 변경을 금지한다.
- 기존 전략과 run 디렉터리는 변경하지 않는다. 아직 자동 실행 요청을 생성하지 않는다.

## 12. Open decisions before implementation

1. **PSAR 신호 기초자산 및 FDR 티커**: Nasdaq-100 지수 vs QQQ 등 중 선택.
2. **PSAR 계산 파라미터/초기화**: 통상적인 AF 시작/증분 0.02, 최대 0.20을 기본 후보로 두지만 사용자 확정은 아직 없음. 구현 라이브러리의 초기화·반전·경계조건 확인 필요.
3. **FDR OHLC와 ETF 시계열 coverage**: 고가/저가, 배당·분할 조정, 데이터 품질/거래일 교집합 검증.
4. **초기 투자금** 및 정확한 거래비용 환경 설정은 프로젝트 기본 설정을 재사용하되 run 전 확인.
5. 1차 성과가 좋을 때에만 현실적 다음 거래일 체결 검증과 필터/인버스 제거 대조군을 추가할지 논의.

**Current stage:** 전략 명세 저장만 진행. 구현, dispatcher 등록, Actions 트리거, 백테스트는 아직 요청·수행되지 않음.
