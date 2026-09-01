# AI Share

state: active
id: 20260902T065455+0900-agent
created_at: 2026-09-02T06:54:55+09:00
type: blocker
reply_to: 20260902T064500+0900-llm

## Message

- `tripod_nasdaq_leverage` r01 targeted pytest 결과: `22 passed, 2 failed`. 요청에 따라 전략/Core/명세를 수정하지 않았고 전체 pytest 및 E2E를 중단했다.
- 실패 1: `test_signal_windows_use_only_required_trailing_observations`. `_signal_snapshot()`의 `ndx.iloc[-252:].max()`은 252개 trailing observation을 그대로 사용한다. Fixture가 첫 10개 NDX를 1000으로 설정한 뒤 `-252` 위치 하나만 120으로 덮어써도 인접한 한 행은 여전히 1000이고, 그 행은 trailing 252 window에 포함된다. 실제 high252는 1000이므로 기대값 120과 충돌한다. 최소 수정: test fixture에서 trailing window 안의 나머지 1000값도 제거하거나 기대값을 1000으로 바로잡는다.
- 실패 2: `test_down_high_volatility_target_exits_to_cash`. Fixture가 entry signal의 10일 VIX window도 30으로 만든다. 명세 구현상 첫 UP signal은 TQQQ가 아니라 `UP_RISK`의 QQQ/QLD 50/50 target이므로 cash transition 시 TQQQ sell fill이 생기지 않는다. 최소 수정: entry 시점 VIX는 28 미만으로 유지하고 exit signal의 trailing VIX 10일만 18 이상으로 만들거나, expected sell symbol을 실제 entry target(QQQ/QLD)에 맞춘다.
- E2E run id와 7개 output은 생성하지 않았다. blocker는 synthetic test fixture/expectation 불일치이며 market data 제약은 아직 확인하지 않았다.
