# EBLC 고수준 전개 및 canonical/Core conformance 보고서

- 상태: **EXECUTED**
- run ID: `elaboration-conformance-2026-08-09-v02-typed-derivation-v3`
- high-level program: `p0b_pedestrian_conflict_zone_program_v02`
- elaborator: `eblc-program-elaborator-v0.2`
- Core/SMT compiler: `eblc-core-v0.1` / `eblc-core-smt-compiler-v0.1`
- solver: project-local Z3 `5.0.0`
- 주장 범위: `P0B_HIGH_LEVEL_ELABORATION_AND_BOUNDED_CONFORMANCE_NOT_VEHICLE_SAFETY`

## 구현 결과

고수준 EBLC program에서 freshness, CLAIMED-to-UNKNOWN, activation, maintenance,
consecutive-clear release, reactivation, expiry, UNKNOWN fallback, verdict,
stop-position, dynamic stopping bound, false-deadlock 및 progress permission을 typed Core
식으로 자동 전개했다. v0.2 입력에서는 source-bearing typed derivation DAG도 같은
program 안에서 검증·전개한다. 모든 수치와 정책에는 source reference가 필요하다.

| 항목 | 결과 |
|---|---:|
| generated traces | 129/129 |
| generated frames | 266/266 |
| trace agreement | 1.000 |
| frame agreement | 1.000 |
| elaborator tests | 11/11 |
| 전체 P0b regression | 111/111 |
| P0a regression | 7/7 |
| SMT-LIB direct replay | 2/2 |
| typed stop/stopping distance witness | -3/2 / 9 |


129개 trace는 기존 locked trace, `TRUE/FALSE/UNKNOWN/CONFLICT` 길이-3 전수 조합,
epistemic kind×fresh/stale/future 조합, unit/frame/target mismatch, scope expiry,
정지 위치 경계 및 고속 위반을 포함한다. 비교 필드는 post-step lifecycle,
clear counter, verdict, entry/speed/deadlock violation과 progress permission이다.

## 주장 경계

이 결과는 generated finite traces에서 canonical Python semantics와 그 명세를 바탕으로
작성한 elaborator/Core SMT가 일치한다는 번역 근거다. elaborator는 canonical 명세로부터
개발됐으므로 독립 safety oracle이 아니다. 이 실행은 단일 bound contract만 다루며,
별도 composition pipeline의 다중 계약 결과를 재검증하지 않는다. 무한시간ㆍ연속
동역학, source 진위, 실제 차량 성능 및 실제 차량 안전은 입증하지 않는다.
