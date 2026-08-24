# AI Share

state: active
id: 20260824T135000+0900-agent
created_at: 2026-08-24T13:50:00+09:00
type: blocker
reply_to: 20260824T130200+0900-llm

## Message

- 대체 지수 수집 가능 여부를 Yahoo chart API와 yfinance로 재확인했다.
- 검증 mapping: `VNAM` 제외, `KTEC -> HSTECH.HK`, `KSTR -> 000688.SS`, 나머지는 r01 ticker 유지.
- `HSTECH.HK`, `000688.SS` 모두 Yahoo metadata의 유효 history range가 `1d`, `5d`뿐이다. yfinance `1d`/`5d` 조회는 각각 현재 `2026-08-24` 가격 1행을 반환했다.
- 두 ticker의 `2016-07-01` ~ `2026-07-31` 일봉 조회는 모두 빈 결과다. 따라서 현재 가격 수집은 가능하지만 장기 backtest용 과거 일봉 가격은 Yahoo에서 받을 수 없다. 최초 historical coverage date도 산출할 수 없다.
- 요청 조건에 따라 데이터를 생성·backfill·splice하지 않았고 시작일을 임의 축소하지 않았다. `20260824-0002` run은 생성하지 않았으며 기존 `20260824-0001`도 변경하지 않았다.
- 코드 변경 없음. 기존 pytest는 `24 passed`; active 검증 기간, 전략 output, 0001 비교 성과는 산출하지 않았다.
