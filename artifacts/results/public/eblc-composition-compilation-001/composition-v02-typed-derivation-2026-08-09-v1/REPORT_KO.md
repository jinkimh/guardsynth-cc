# EBLC 다중 계약 composition 및 고수준→Core→SMT 실행 보고서

- 상태: **EXECUTED**
- run ID: `composition-v02-typed-derivation-2026-08-09-v1`
- solver: project-local Z3 `5.0.0`
- 주장 범위: `SYNTHETIC_MULTI_CONTRACT_COMPOSITION_AND_BOUNDED_TRANSLATION_NOT_VEHICLE_SAFETY`

## 결과

| 항목 | 결과 |
|---|---:|
| 기존 EBLC 111개 기준선 회귀 | 111/111 |
| v0.2 composition 신규 테스트 | 8/8 |
| 전체 EBLC 테스트 | 119/119 |
| P0a 회귀 | 7/7 |
| composition canonical/Core-SMT agreement | 5/5 |
| SMT-LIB 직접 replay | 2/2 |

bundle v0.1 컨테이너 안에서 `EBLCProgram v0.2`의 typed derivation을 계약별로
namespace하여 Core와 SMT까지 전달했다. priority는 scalar
weight가 아니라 `HARD > SERVICE > PREFERENCE` 및 근거 있는 비순환 override로
처리한다. 선택 계약의 허용 action 교집합이 비면 hard-hard는 `CONFLICT`, 그 밖은
`REVIEW_REQUIRED`다. 생성된 namespaced Core는 generic compiler를 통해 실제
SMT-LIB/Z3로 변환됐다. 두 계약의 정지거리 식과 나눗셈 분모 비영 조건도
각각 독립된 SMT assertion으로 보존된다.

## 주장 경계

결과는 synthetic bounded trace에서 composition 의미와 Core/Z3 번역이 일치한다는
근거다. 독립 safety oracle, 실제 법규 해석, 실제 차량 성능 보장 또는 차량 안전
증명이 아니다. 현재 typed derivation 문법이 허용하는 유한 산술 DAG만 다루며,
무한시간/연속 동역학과 임의 사용자 정의 함수는 아직 범위 밖이다.
