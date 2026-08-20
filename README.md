# backtest-lab

LLM이 자연어 투자 아이디어를 자유로운 Python 전략 코드로 구현하고, 이를 작고 예측 가능한 런타임에서 백테스트하기 위한 경량 연구 프로젝트다.

## Goal

- Strategy는 자유로운 Python 코드로 작성한다.
- Runtime은 시간 진행, 체결, fee/slippage, Fill 생성과 성과 시계열 생성을 담당한다.
- Portfolio는 cash와 종목별 aggregate position의 현재 회계 상태를 관리한다.
- Runtime이 만든 performance series를 `ffn`으로 분석한다.
- 흔한 포트폴리오 전략은 단순하게 처리하고, 특이 전략은 전략별 추가 코드/상태로 구현할 수 있게 한다.

```text
Strategy
   ↓
Runtime
   ↓
Portfolio

Runtime
 ├─ fills
 └─ performance series
          ↓
         FFN
```

## Design stance

- 과도한 Strategy/Signal/Indicator 추상화를 만들지 않는다.
- 특이 전략 하나를 위해 Core 데이터 모델을 확장하지 않는다.
- Strategy는 엔진이 제공하는 최소 실행 기능 위에서 일반 Python/pandas/numpy 코드를 자유롭게 사용할 수 있어야 한다.
- `bt`는 dependency가 아니라 design reference다. 특히 portfolio accounting, external flow, performance series, `ffn` 연계에 관한 선택을 참고한다.
- `ffn`은 성과 분석을 담당한다.

## Documents

- [`doc/architecture.md`](doc/architecture.md): 구조와 R&R
- [`doc/specifications.md`](doc/specifications.md): v1 기능 및 검증 요구사항
