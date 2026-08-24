# Open Issues

확정 문서와 분리해, 아직 구현하지 않는 설계 이슈만 기록한다.

## Execution timing

- 현재 상태: same-bar vs next-bar execution timing은 아직 확정하지 않았다. 현재 Runtime은 입력 step의 reference price로 즉시 체결한다.
- 재검토 조건: 전략에서 신호 생성 시점과 체결 시점의 분리가 실제 요구사항이 될 때.

## Strict market-data coverage

- 현재 상태: strict coverage는 요청 기간의 시작/종료 범위와 symbol 존재를 검증한다. 기간 중 결측의 완전성 검증은 아직 구현하지 않는다.
- 재검토 조건: 휴장일을 고려한 연속성 또는 공급자별 결측 검증 요구가 생길 때.

## Cost and PnL accounting

- 현재 상태: Portfolio는 cash와 aggregate position만 관리한다. average cost, realized PnL, unrealized PnL은 core에 포함하지 않는다.
- 재검토 조건: 성과 외 손익 보고가 반복적으로 필요해질 때.
