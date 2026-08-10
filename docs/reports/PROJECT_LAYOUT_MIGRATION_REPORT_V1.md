# 프로젝트 폴더 구조 v2 마이그레이션 보고서

- 상태: 실행 검증 완료
- 적용일: 2026-08-09
- 기준 설계: [Project layout v2](../architecture/PROJECT_LAYOUT_V2.md)
- 상세 이동표: [Migration map](../architecture/MIGRATION_MAP.json)

## 결론

프로젝트의 정보 수명주기에 따라 소유 위치를 하나씩 지정했다.

| 정보 유형 | 표준 위치 |
|---|---|
| 개발 요구사항ㆍ계획ㆍ설계ㆍ조사ㆍ안정된 보고서 | `docs/`의 목적별 하위 폴더 |
| 공개할 재사용 코드 | `src/` |
| 사용자가 실행하는 파이프라인 | `cli/pipelines/<domain>/<purpose>/` |
| 유지보수 단위ㆍ통합ㆍ회귀 테스트 | `tests/<package>/` |
| 실험 정의ㆍ프로토콜ㆍ실험 전용 분석 | `experiments/<family>/` |
| 재생성 가능한 중간 산출물 | `artifacts/intermediate/` |
| 공개ㆍ제한 최종 실행 결과 | `artifacts/results/public|restricted/` |

기존 `research/`의 문서는 문서 역할별로 `docs/`에 분류했다. 기존
`experiments/results/`는 `artifacts/results/`로 옮겼으며 과거 결과의 내용은 수정하지
않았다. EBLC 유지보수 테스트는 `tests/guard_synth_eblc/`, 여섯 실행 파이프라인은
`cli/pipelines/eblc/<purpose>/`로 모았다. 이전 import를 사용하는 코드에는 제한된
호환 wrapper만 남겨 소유권 중복을 피했다.

루트에 있던 UPPAAL 실행 배포본은 `runtime/solvers/uppaal-5.0.0-linux64/`, Z3와
UPPAAL 원본 압축 파일은 `archive/installers/`로 이동해 코드ㆍ문서와 실행 환경을
분리했다.

재생성 가능한 438개 UPPAAL XMLㆍqueryㆍprofile은
`experiments/uppaal/models/`에서 `artifacts/intermediate/uppaal-models/`로 옮겼다.
생성기와 검증기는 새 경로를 기본값으로 사용한다.

## 자동 통제

- `tests/structure/test_project_layout.py`: 금지된 옛 경로, 파이프라인 그룹, 테스트 단일
  소유자, migration map, Markdown 링크, manifest 경로를 검사한다.
- `cli/checks/project_integrity.py`: canonical 문서의 로컬 링크를 읽기 전용으로 검사한다.
- `cli/checks/build_manifest.py`: 저장소 manifest를 동일한 제외 규칙으로 재생성ㆍ검사한다.
- `cli/pipelines/maintenance/project_layout_audit/run.py`: 구조ㆍEBLCㆍP0aㆍCLI 회귀 결과를
  하나의 변경 불가 run 디렉터리에 기록한다.

## 실행 근거

최종 검사 수치와 명령별 exit code는 아래 run 디렉터리에 고정한다.

`artifacts/results/public/project-layout-refactor-001/layout-v2-2026-08-09-v4/`

기본 Python에 `numpy`와 `pandas`가 없어 각각 일부 `contract_micro_world`와
`sequential_coc` legacy test가 import되지 않는 문제는 이동 전에도 존재한 환경 의존성
gap이다. 폴더 구조 검증과 섞지 않고, 각 실험이 사용할 runtime과 dependency lock을
명시하는 후속 작업으로 관리한다.

이 마이그레이션은 저장소의 추적성과 실행 재현성을 개선한 소프트웨어 관리 결과다.
EBLC 연구 방법, SMT 인코딩의 완전성, 실제 데이터의 품질 또는 차량 안전성을 입증하지
않는다.
