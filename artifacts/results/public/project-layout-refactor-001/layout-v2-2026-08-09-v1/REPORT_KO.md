# 프로젝트 폴더 구조 v2 리팩토링 검증 보고서

- 상태: **EXECUTED**
- 실행일: 2026-08-09
- run ID: `layout-v2-2026-08-09-v1`
- 범위: `REPOSITORY_LAYOUT_AND_SOFTWARE_REGRESSION_NOT_RESEARCH_OR_VEHICLE_SAFETY`

## 변경 결과

문서, 공개 코드, 실행 파이프라인, 테스트, 실험 정의, 생성 산출물을 각각
`docs/`, `src/`, `cli/pipelines/<domain>/<purpose>/`, `tests/`, `experiments/`,
`artifacts/`로 분리했다. 기존 `research/`와 `experiments/results/`는 제거했고,
과거 결과 파일의 내용은 바꾸지 않은 채 `artifacts/results/public|restricted/`로 이동했다.

EBLC 공개 구현의 소유자는 `src/guard_synth_eblc/`이며, 아홉 개 유지보수 테스트는
`tests/guard_synth_eblc/`, 여섯 실행 진입점은 `cli/pipelines/eblc/<purpose>/`가 소유한다.
`experiments/eblc_p0b/`에는 과거 호환 wrapper와 실험 설명만 남겼다.

## 검증 결과

| 검사 | 결과 |
|---|---:|
| 구조 계약 | 7/7 PASS |
| EBLC 단위ㆍ통합 회귀 | 77/77 PASS |
| P0a 회귀 | 7/7 PASS |
| EBLC CLI import/도움말 | 6/6 PASS |
| canonical 문서의 깨진 로컬 링크 | 0건 |

기본 Python 환경에 `numpy`와 `pandas`가 없어 일부 비-EBLC legacy suite가 import되지
않는 기존 dependency gap은 이번 폴더 이동의 회귀로 계산하지 않았다. 해당 suite는
각 실험용 runtime을 명시하는 후속 환경 정규화 작업으로 분리한다.

## 해석

이 결과는 새 경로에서 EBLC와 P0a가 동일한 테스트를 통과하고, 공개 CLI가 import되며,
문서 링크와 산출물 소유 규칙이 일관됨을 보인다. 연구 방법의 타당성, SMT의 완전성,
실제 차량 안전성 또는 제한 데이터 품질을 입증하지는 않는다.
