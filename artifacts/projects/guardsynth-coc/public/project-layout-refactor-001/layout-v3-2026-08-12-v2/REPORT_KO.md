# 프로젝트 폴더 구조 v3 리팩토링 검증 보고서

- 상태: **EXECUTED**
- 실행일: 2026-08-12
- run ID: `layout-v3-2026-08-12-v2`
- 범위: `REPOSITORY_LAYOUT_AND_SOFTWARE_REGRESSION_NOT_RESEARCH_OR_VEHICLE_SAFETY`

## 변경 결과

연구 질문별 문서, 코드, 파이프라인, 테스트, 실험, 논문을 `projects/<project-id>/`에
함께 배치했다. 재사용 가능한 EBLC/BCV 구현은 `platforms/eblc-bcv/`, 포털은
`apps/research_portal/`가 소유한다. 루트 `src/`, `experiments/`와 domain CLI에는
이전 import/명령을 위한 forwarding shim만 남겼다.

## 검증 결과

| 검사 | 결과 |
|---|---:|
| 구조 계약 | 18/18 PASS |
| EBLC 단위ㆍ통합 회귀 | 133/133 PASS |
| GuardSynth 회귀 | 170/170 PASS |
| Safety-Constrained CoC micro-world | 11/11 PASS |
| Sequential CoC | 166/166 PASS |
| bounded logic/SMT | 12/12 PASS |
| P0a 회귀 | 7/7 PASS |
| UPPAAL 모델 생성 회귀 | 14/14 PASS |
| domain CLI import/도움말 | 8/8 PASS |
| canonical 문서의 깨진 로컬 링크 | 0건 |

NumPy/Pandas가 필요한 기존 실험은 등록된 Alpamayo runtime으로 분리 실행했다.
UPPAAL의 라이선스가 필요한 실제 `verifyta` 동등성 검사는 해당 suite에서 명시적으로
skip되며, 모델 생성과 판정 파서 회귀는 실행한다.

## 해석

이 결과는 새 경로에서 EBLC와 P0a가 동일한 테스트를 통과하고, 공개 CLI가 import되며,
문서 링크와 산출물 소유 규칙이 일관됨을 보인다. 연구 방법의 타당성, SMT의 완전성,
실제 차량 안전성 또는 제한 데이터 품질을 입증하지는 않는다.
