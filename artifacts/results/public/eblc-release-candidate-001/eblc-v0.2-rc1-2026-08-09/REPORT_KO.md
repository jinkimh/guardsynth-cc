# EBLC v0.2 scoped release candidate 보고서

- 상태: **EXECUTED**
- release decision: `EBLC_V02_FEATURE_COMPLETE_SCOPED_RC1`
- run ID: `eblc-v0.2-rc1-2026-08-09`
- solver: project-local Z3 `5.0.0`
- 주장 범위: `EBLC_V02_LANGUAGE_AND_TOOLING_RELEASE_CANDIDATE_NOT_VEHICLE_SAFETY`

## 검증 결과

| 항목 | 결과 |
|---|---:|
| 동결 전 EBLC 기준선 | 128/128 |
| CNL renderer 신규 테스트 | 10/10 |
| 전체 EBLC 테스트 | 138/138 |
| P0a 회귀 | 7/7 |
| 프로젝트 구조/문서 링크 | 8/8 |
| program canonical–Core-SMT | 129/129 traces, 266/266 frames |
| bundle canonical–Core-SMT | 일치 |

## 동결 판단

EBLC v0.2는 bounded discrete contract 표현, lifecycle, evidence/derivation,
non-scalar composition, indexed actor-zone expansion, Core/SMT lowering 및 결정론적
CNL projection 범위에서 **scoped feature complete RC**로 동결한다. CNL은 모델 입력을
위한 읽기 표현이며 구조화 EBLC를 실행 권위로 대체하지 않는다.

자연어 CoC에서 source-aware 계약을 만드는 기능은 다음 GuardSynth generator 계층이다.
일반 exception algebra, quantifier, continuous/hybrid dynamics는 v0.2 완료 조건이 아니며
traceability에서 명시적으로 이관했다. 실제 association, 법규 근거, 차량 assurance 및
차량 안전성은 이 실행이 입증하지 않는다.
