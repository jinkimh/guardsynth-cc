# GuardSynth source-aware generator v0.1 실행 보고서

- 상태: **FAILED**
- run ID: `source-aware-generator-2026-08-09-v2`
- solver: project-local Z3 `5.0.0`
- 주장 범위: `SOURCE_AWARE_SYNTHETIC_GENERATION_AND_BOUNDED_TRANSLATION_NOT_VEHICLE_SAFETY`

## 결과

| 항목 | 결과 |
|---|---:|
| EBLC v0.2 RC 기준선 | 138/138 |
| source-aware generator 신규 테스트 | 12/12 |
| 전체 EBLC/GuardSynth 테스트 | 150/150 |
| P0a 회귀 | 7/7 |
| 구조/문서 링크 | 0/9 |
| SMT-LIB 직접 replay | 2/2 |

정상 synthetic request는 RuleTemplate, predicate, vehicle profile, 관측/association,
geometry/transform 근거와 explicit compiler policy를 결합해 program v0.2 및 두 instance
indexed collection을 생성했다. Z3 exact stop position은
`-3/2`, `21/2`이고
stopping distance는 `9`, `3`이다.

CoC claim-only, missing profile/geometry, ambiguous target, duplicate binding 및 unit mismatch
probe는 모두 collection을 생성하지 않았다. CoC evidence는 `CLAIMED`로 provenance에
보존하지만 activation evidence에는 포함하지 않았다.

이는 공개 synthetic source-flow와 bounded translation의 구현 근거다. 실제 법규 source,
perception association, 차량 보장값 또는 차량 안전성을 입증하지 않는다.
