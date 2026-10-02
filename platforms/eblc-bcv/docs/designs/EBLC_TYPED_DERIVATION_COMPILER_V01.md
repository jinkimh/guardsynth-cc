# EBLC typed derivation compiler 설계·TDD 기록 V1

## 1. 목적

기존 고수준 program의 `derivation_dag.operation`은 사람이 읽는 문자열 provenance였다.
이를 임의로 파싱하면 수치와 단위를 추정할 위험이 있으므로, 실행 가능한 유도는 별도
`eblc-derivation-v0.1` typed DAG로만 받는다.

이번 vertical slice는 synthetic stop position을 다음 식으로 재생한다.

```text
zone_entry_x = 0.0 m
stop_margin  = 1.5 m
stop_position = zone_entry_x - stop_margin = -1.5 m
```

이는 실제 법규 수치나 실제 차량 보장값이 아니다.

## 2. TDD 순서

### RED

먼저 `tests/guard_synth_eblc/test_derivation_compiler.py`를 추가했다. 구현 전 실행은
`ModuleNotFoundError: src.guard_synth_eblc.derivation`으로 실패했다. 테스트는 다음
계약을 선행 고정했다.

- valid typed DAG parse
- unknown symbol/node reference 거부
- DAG cycle 및 연산 arity 오류 거부
- unknown evidence ref 거부
- unit/frame mismatch 거부
- 단위가 유효한 0 나눗셈의 SMT definedness `UNSAT`
- Z3 exact value `-3/2`
- 기존 `bind_stop_position`을 typed output 절로 교체
- locked 8개 trace의 canonical/Core-SMT 결과 보존

### GREEN

최소 schema/parser/compiler를 구현한 뒤 신규 테스트 11/11, 구현 전 기준선 89/89,
전체 EBLC 100/100 및 P0a 7/7을 통과했다.

## 3. 입력 문법

`symbols`는 다음 두 종류만 허용한다.

- `SOURCED_VALUE`: 근거, 유한 값, sort, unit, frame이 있는 상수
- `CORE_VARIABLE`: 값 대신 기존 또는 새 Core declaration을 가리키는 typed 입력

`nodes`는 `ADD`, `SUB`, `MUL`, `DIV`, `NEG`, `MIN`, `MAX`만 허용한다. 입력은
`symbol:<id>` 또는 `node:<id>`로 명시한다. `outputs`는 node 결과가 binding될 Core
declaration과 교체할 기존 clause ID를 명시한다.

## 4. Core/SMT 변환

Sourced value마다 constant declaration과 `INITIAL` binding clause를 만든다. DAG는
재귀적으로 Core arithmetic/`ite` AST로 전개하며 중간 node는 inline한다. 따라서
제곱속도처럼 Core의 공개 unit 문자열에 없는 중간 차원도 최종 출력 equality에서
dimension checking을 받을 수 있다.

`DIV`는 generic Core→SMT compiler가 분모 `!= 0` side constraint를 생성한다.
출력 expression이 time-varying symbol을 참조하면 출력도 반드시 time-varying이어야
한다.

## 5. 범위와 다음 단계

입증한 것은 bounded synthetic numeric derivation의 typed replay와 기존 trace 결과
보존이다. free-form 자연어/operation parsing, source 진위, 차량 성능, 독립 safety
oracle 또는 안전성을 입증하지 않는다.

다음 단계는 companion spec을 `eblc-program-v0.2`에 직접 포함하고, stop position뿐
아니라 response distance와 braking distance를 포함한 전체 dynamic stopping-bound
DAG를 같은 typed source graph로 전개하는 것이다.
