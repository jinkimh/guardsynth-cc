# EBLC 고수준 전개 및 canonical/Core conformance 보고서

- 상태: **EXECUTED**
- run ID: `elaboration-conformance-2026-08-08-v2`
- high-level program: `p0b_pedestrian_conflict_zone_program`
- elaborator: `eblc-program-elaborator-v0.1`
- Core/SMT compiler: `eblc-core-v0.1` / `eblc-core-smt-compiler-v0.1`
- solver: project-local Z3 `5.0.0`
- 주장 범위: `P0B_HIGH_LEVEL_ELABORATION_AND_BOUNDED_CONFORMANCE_NOT_VEHICLE_SAFETY`

## 구현 결과

수식 AST가 없는 고수준 EBLC program에서 freshness, CLAIMED-to-UNKNOWN, activation,
maintenance, consecutive-clear release, reactivation, expiry, UNKNOWN fallback, verdict,
stop-position, dynamic stopping bound, false-deadlock 및 progress permission을 typed Core
식으로 자동 전개했다. 모든 수치와 정책에는 source reference가 필요하다.

| 항목 | 결과 |
|---|---:|
| generated traces | 129/129 |
| generated frames | 266/266 |
| trace agreement | 1.000 |
| frame agreement | 1.000 |
| elaborator tests | 11/11 |
| 전체 P0b regression | 66/66 |
| P0a regression | 7/7 |
| SMT-LIB direct replay | 2/2 |

129개 trace는 기존 locked trace, `TRUE/FALSE/UNKNOWN/CONFLICT` 길이-3 전수 조합,
epistemic kind×fresh/stale/future 조합, unit/frame/target mismatch, scope expiry,
정지 위치 경계 및 고속 위반을 포함한다. 비교 필드는 post-step lifecycle,
clear counter, verdict, entry/speed/deadlock violation과 progress permission이다.

## 주장 경계

이 결과는 generated finite traces에서 canonical Python semantics와 그 명세를 바탕으로
작성한 elaborator/Core SMT가 일치한다는 번역 근거다. elaborator는 canonical 명세로부터
개발됐으므로 독립 safety oracle이 아니다. 다중 계약 composition, priority conflict
resolution, derivation DAG의 symbolic replay, 무한시간ㆍ연속 동역학 및 실제 차량 안전은
입증하지 않는다.
