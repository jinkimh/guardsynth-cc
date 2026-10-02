# EBLC program v0.2 typed derivation 통합 설계

## 1. 범위

이 문서는 broad survey를 반복하지 않고, `eblc-program-v0.1`과 별도
`eblc-derivation-v0.1`로 나뉜 현재 구현을 하나의 고수준 프로그램으로 통합하기 위한
구현 결정을 고정한다. 대상은 synthetic pedestrian conflict-zone vertical slice이며,
실제 법규나 실제 차량의 제동 성능을 주장하지 않는다.

## 2. 표적 조사 결과

- SMT-LIB Reals에서 나눗셈은 total function이고 0으로 나눈 값은 제약되지 않는다.
  따라서 `DIV` 노드는 분모가 0이 아니라는 별도 definedness constraint를 반드시
  생성해야 한다. 현재 Core→SMT compiler의 방식을 유지한다.
  - https://smt-lib.org/theories-Reals.shtml
- ASAM OpenSCENARIO DSL은 모든 식에 정적 타입이 있고, 물리량을 SI base-unit
  exponent로 표현해 계산 중 dimension 검사를 수행한다. EBLC도 문자열 수식을
  재해석하지 않고 `sort + unit dimension + coordinate frame`을 typed DAG에서
  검사한다.
  - https://publications.pages.asam.net/standards/ASAM_OpenSCENARIO/ASAM_OpenSCENARIO_DSL/v2.1.0/language-reference/types.html
- W3C PROV-DM은 결과 entity, 사용된 entity, 이를 변환한 activity를 구분한다.
  EBLC에서는 sourced symbol을 입력 entity, arithmetic node를 derivation activity,
  output binding을 생성된 entity에 대응시키되, PROV 전체 vocabulary를 구현했다고
  주장하지 않는다.
  - https://www.w3.org/TR/prov-dm/
- JSON Schema 2020-12는 embedded schema와 bundling을 공식적으로 다룬다. 다만 현재
  저장소의 dependency-free validator는 local `$ref` subset만 지원하므로, v0.2 outer
  schema와 내장 `typed_derivation`의 전용 schema를 2단계로 검증한다.
  - https://json-schema.org/draft/2020-12/release-notes

## 3. 결정한 언어 경계

`eblc-program-v0.1`은 변경 없이 계속 읽는다. 새 `eblc-program-v0.2`는 free-form
`derivation_dag` 대신 검증 가능한 `typed_derivation`을 필수로 가진다.

v0.2의 내장 derivation은 다음을 만족해야 한다.

1. derivation horizon은 `program.frames + 1`과 같다.
2. derivation source ref는 program source ref의 부분집합이다.
3. claim scope는 program과 동일하다.
4. 이 vertical slice의 출력은 정확히 `stop_position`, `stopping_distance`이다.
5. 내장 derivation이 임의의 기존 semantic clause를 삭제하지 못하도록
   `replace_clause_ids`는 비어 있어야 한다.
6. `CORE_VARIABLE`은 program이 선언하는 입력/parameter만 참조한다.
7. 출력 sort/unit/frame/time-varying metadata가 기대 interface와 일치해야 한다.

## 4. 정지거리 DAG

synthetic fixture의 계산은 다음과 같다.

```text
stop_position       = zone_entry_x - stop_margin
adjusted_speed      = ego_speed - speed_epsilon
effective_speed     = max(adjusted_speed, 0 m/s)
response_distance   = effective_speed * response_time
speed_squared       = effective_speed * effective_speed
twice_deceleration  = 2 * deceleration
braking_distance    = speed_squared / twice_deceleration
stopping_distance   = response_distance + braking_distance
```

`zone_entry_x`, `stop_margin`, 숫자 2와 `0 m/s`는 source-bearing constant이고,
`ego_speed`, `speed_epsilon`, `response_time`, `deceleration`은 typed Core variable이다.
중간 node는 Core AST로 inline되며 최종 `stopping_distance`는 시간가변 길이(`m`)로
binding된다. speed violation은 더 이상 같은 식을 Python에서 다시 만들지 않고 이
출력을 참조한다.

## 5. TDD acceptance criteria

- v0.1 fixture와 기존 결과가 그대로 유지된다.
- v0.2 valid fixture가 parse되고 내장 derivation이 program에 결합된다.
- missing derivation, horizon/source/scope/interface mismatch가 fail closed 된다.
- stop position과 stopping distance가 Core clause로 생성된다.
- speed violation Core 식이 `stopping_distance` output을 실제 사용한다.
- Z3가 stop position `-3/2`와 선택한 frame의 정지거리를 exact rational로 계산한다.
- locked 8 traces와 generated conformance suite가 canonical 결과와 100% 일치한다.
- unit/frame mismatch와 zero-divisor 경로가 기존대로 거부되거나 UNSAT이다.

## 6. 주장 경계

이 통합은 typed arithmetic translation, bounded SMT 실행, canonical/Core-SMT agreement를
검사한다. 입력 source의 진위, 공식 법규 해석, 실제 차량 보장, 독립 safety oracle,
차량 안전성을 입증하지 않는다.
