# EBLC 다각도 단위·통합 검증 보고서

- 상태: **EXECUTED**
- run ID: `scenario-matrix-2026-08-08-v2`
- solver: project-local Z3 `5.0.0`
- 명시적 신규 시나리오: 44개
- 주장 범위: `SYNTHETIC_EBLC_SOFTWARE_UNIT_INTEGRATION_VALIDATION_NOT_VEHICLE_SAFETY`

## 검증 관점

| 그룹 | case 수 | 실행 target |
|---|---:|---|
| `PROGRAM_AND_SCHEMA_NEGATIVE_INPUTS` | 9 | JSON_SCHEMA, PROGRAM_PARSER |
| `LIFECYCLE_AND_POLICY_VARIANTS` | 9 | CANONICAL, RUNTIME, Z3_BOUNDED, CORE_SMT, ENUMERATOR |
| `NUMERIC_AND_FRESHNESS_BOUNDARIES` | 23 | CANONICAL, RUNTIME, Z3_BOUNDED, CORE_SMT, ENUMERATOR |
| `COMBINED_FAILURE_PRECEDENCE` | 1 | CANONICAL, RUNTIME, Z3_BOUNDED, CORE_SMT, ENUMERATOR |
| `EPISTEMIC_POLICY_LOWERING` | 1 | CORE_SMT |
| `MINIMUM_BOUNDED_HORIZON` | 1 | CANONICAL, CORE_SMT |

경계 행렬은 정지 위치, 동적 허용 속도, freshness, 미래 timestamp에 대해
경계 직전·경계값·경계 직후를 비교한다. 정책 행렬은 release/reactivation,
UNKNOWN 처리, expiry, invariant, deadlock을 변형한다. 정책·경계 trace를 canonical,
별도 runtime monitor, 기존 bounded Z3 target, 고수준 program에서 전개된 Core-SMT,
finite-state enumerator에 통과시켜 결과 일치를 검사한다.

## 실행 결과

| test suite | pass | exit code |
|---|---:|---:|
| scenario_matrix | 11/11 | 0 |
| core_smt_compiler | 12/12 | 0 |
| elaboration_conformance | 11/11 | 0 |
| robustness | 10/10 | 0 |
| all_p0b | 77/77 | 0 |
| p0a_regression | 7/7 | 0 |

초기 실행에서 binary-float 계산 때문에 freshness 경계 두 건이 ideal-real Core-SMT와
불일치했다. 의미 epsilon(1e-9)보다 훨씬 작은 roundoff guard(1e-15)를 적용한 뒤
동일 고정 기대값으로 재실행하여 전부 통과했다.

## 해석 한계

이 결과는 명시된 synthetic 유한 시나리오와 software target 사이의 일치 및
fail-closed 동작을 확인한다. 실제 법규의 정당성, 차량 제동 성능, 센서 정확도,
무한시간 성질 또는 실제 차량 안전을 입증하지 않는다.
