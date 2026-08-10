# EBLC-P0B-001 실행 보고서

- 상태: **EXECUTED**
- 실행일: 2026-08-08
- run ID: `p0b-z3-smt-2026-08-08-v4`
- 입력: 공개 가능한 synthetic pedestrian conflict-zone fixture
- 판단: **DATA-GAP PIVOT**
- 주장 범위: `P0B_SCHEMA_AND_BOUNDED_EXECUTION_NOT_VEHICLE_SAFETY`

## 구현 결과

EBLC v0는 4값 fact, 4종 epistemic kind, partial binder, source/version/scope/precondition/exception, target/zone association, evidence/parameter derivation DAG, observability/freshness/failure-to-UNKNOWN, activation/invariant/bound/release/reactivation/expiry/fallback 및 비-scalar partial priority를 포함한다. 규칙과 차량 값은 실제 법규나 실제 차량 보장값이 아니라 명시적인 synthetic system requirement/profile이다.

canonical interpreter가 operational semantic source of truth다. runtime monitor는 canonical 함수를 import하지 않는 별도 구현이다. 이 실행은 프로젝트 로컬 Z3 `5.0.0`을 `runtime/solvers/z3-5.0.0-x86_64-glibc-2.36/lib/python3.11/site-packages/z3/__init__.py`에서 선택했다. 세 번째 target `Z3_BOUNDED_SMT`은 고정 trace의 lifecycleㆍverdictㆍ위반을 Z3 제약으로 풀고 네 symbolic query를 SAT/UNSAT으로 판정한다. 이는 bounded translation/falsification evidence이며 독립 safety oracle이나 차량 안전 증명이 아니다.

## 정량 gate

| 항목 | 결과 |
|---|---:|
| P0a 회귀 | 7/7 PASS |
| P0b 테스트 | 41/41 PASS |
| 실제 Z3 solver encoding | True (22 constructions) |
| schema fixture parse | 4/4 (1.000) |
| canonical/runtime agreement | 8/8 (1.000) |
| canonical/bounded-target agreement | 8/8 (1.000) |
| underconstraint detection | 5/5 (1.000) |
| overconstraint detection | 5/5 (1.000) |
| 정상 fixture false alarm | 0 |
| missing-input abstention | 4/4 |
| source 없는 normative/numeric value | 0 |

10개 mutation은 각각 최소 controlled witness에서 검출됐다. 이것은 `CONTROLLED_MUTATION_ORACLE`이며 `NOT_INDEPENDENT_SAFETY_ORACLE`이다.

## 실제 장면 adapter

로컬 제한 파생 자산을 raw 복사나 원문 출력 없이 read-only audit했다. timestamp와 일부 actor/trajectory 단서는 있으나 conflict-zone geometry, pedestrian-zone association, time-aligned ego pose/speed/frame bundle, vehicle assurance profile을 한 장면에서 함께 확보하지 못했다. 값을 합성하지 않았으며 상태를 `P0B_REAL_ADAPTER_BLOCKED_DATA_GAP`으로 기록했다.

## 입증 범위

이번 실행은 schema-driven fixture가 canonical/runtime/Z3 bounded target에서 같은 bounded trace 판정을 내고 controlled under/overconstraint mutation을 찾는다는 software mechanism evidence다. 실제 법규 정확성, 실제 센서 grounding, 독립 safety oracle, closed-loop risk reduction, 실제 차량 안전성은 입증하지 않는다.

## 다음 단일 우선 작업

24-scene dry run 전에 conflict-zone geometry와 pedestrian association을 time-aligned ego state에 결합하는 source/adapter authoring을 완료한다. 따라서 현재 선택은 **DATA-GAP PIVOT**이다.
