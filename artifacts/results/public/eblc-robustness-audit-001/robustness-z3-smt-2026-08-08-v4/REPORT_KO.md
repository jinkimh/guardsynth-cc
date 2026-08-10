# EBLC 공개 구현 강건성 감사

- run ID: `robustness-z3-smt-2026-08-08-v4`
- 상태: **EXECUTED_WITH_GAPS**
- 통과 probe: 7/13
- 발견 gap: 6
- 범위: software robustness only; 차량 안전성 검증 아님

## 발견된 gap

- `SCHEMA_REJECTS_NONFINITE_NUMBER` (HIGH): expected REJECT, observed `"ACCEPT"`
- `BINDER_REJECTS_NONFINITE_VEHICLE_PROFILE` (CRITICAL): expected UNSUPPORTED, observed `"VALIDATED"`
- `MONITORS_REJECT_NONFINITE_SCENE_VALUE` (CRITICAL): expected ALL_REJECT, observed `{"bounded": false, "canonical": true, "runtime": true}`
- `MONITORS_REJECT_EMPTY_TRACE` (HIGH): expected ALL_REJECT, observed `{"bounded": true, "canonical": true, "runtime": true}`
- `MONITORS_REJECT_NONMONOTONIC_TIMESTAMPS` (HIGH): expected ALL_REJECT, observed `{"bounded": true, "canonical": true, "runtime": true}`
- `CONTRACT_SCHEMA_COVERS_RUNTIME_PARAMETERS` (HIGH): expected NO_MISSING_FIELDS, observed `["derivation_dag", "maximum_service_deceleration_mps2", "position_uncertainty_m", "predicate_maximum_age_s", "response_time_s"]`

## 해석

translation agreement와 controlled mutation 검출은 별도 의미론 target 간 일치를 보여주지만, 모든 target이 공유하는 입력 검증 공백을 제거하지는 않는다. gap은 사후 기대값 변경 없이 그대로 기록했다.
