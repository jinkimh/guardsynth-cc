# EBLC indexed actor–zone collection 실행 보고서

- 상태: **EXECUTED**
- run ID: `indexed-collection-2026-08-09-v1`
- solver: project-local Z3 `5.0.0`
- 주장 범위: `SYNTHETIC_INDEXED_ACTOR_ZONE_EXPANSION_AND_BOUNDED_TRANSLATION_NOT_VEHICLE_SAFETY`

## 결과

| 항목 | 결과 |
|---|---:|
| 기존 EBLC 기준선 | 119/119 |
| indexed collection 신규 테스트 | 9/9 |
| 전체 EBLC 테스트 | 128/128 |
| P0a 회귀 | 7/7 |
| SMT-LIB 직접 replay | 2/2 |
| ambiguous association abstention | `REVIEW_REQUIRED`, bundle=false |

두 actor–zone binding을 하나의 v0.2 template에서 펼쳐 계약별 namespace로 분리했다.
Z3 exact stop-position witness는 `-3/2`와
`21/2`, stopping-distance witness는 `9`와 `3`이다.
모호한 association은 일부 계약만 조용히 실행하지 않고 collection 전체를
`REVIEW_REQUIRED`로 중단한다.

이는 synthetic bounded expansion/translation evidence다. 실제 association 정확성,
법규 source, 차량 성능 또는 차량 안전성을 입증하지 않는다.
