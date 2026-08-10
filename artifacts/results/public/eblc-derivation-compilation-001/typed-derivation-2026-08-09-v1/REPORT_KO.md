# EBLC typed derivation→Core→SMT 실행 보고서

- 상태: **EXECUTED**
- run ID: `typed-derivation-2026-08-09-v1`
- solver: project-local Z3 `5.0.0`
- 주장 범위: `SYNTHETIC_TYPED_DERIVATION_AND_BOUNDED_TRANSLATION_NOT_VEHICLE_SAFETY`

## TDD 및 변환 결과

| 항목 | 결과 |
|---|---:|
| 구현 전 EBLC 기준선 | 89/89 |
| derivation 신규 테스트 | 11/11 |
| 전체 EBLC 테스트 | 100/100 |
| P0a 회귀 | 7/7 |
| locked trace canonical/Core-SMT agreement | 8/8 |
| SMT-LIB 직접 replay | 2/2 |

실패 테스트를 먼저 작성한 뒤 typed `SUB` derivation으로 `0.0 m - 1.5 m = -1.5 m`을
Core 식으로 생성했다. 기존의 정적 `bind_stop_position` 절은 명시적으로 교체됐고,
Z3 witness는 `-3/2`를 반환했다. 미등록 ref, DAG cycle, 연산 arity, 근거 누락,
unit/frame mismatch 및 0 나눗셈 definedness도 fail-closed로 검사한다.

## 주장 경계

현재 v0.1은 유한 typed arithmetic DAG (`ADD/SUB/MUL/DIV/NEG/MIN/MAX`)의 bounded
symbolic replay다. free-form `operation` 문자열을 자동 해석하지 않으며 실제 source,
차량 profile 또는 안전성을 입증하지 않는다.
