# Sequential CoC Verification 프로젝트 실행 추적표

- 프로젝트: `sequential-coc-verification`
- 문서 계층: `03` 현재 실행 관리
- 기준 연구계획: [01_RESEARCH_PLAN_V01.md](01_RESEARCH_PLAN_V01.md)
- 전체 마일스톤: [02_PROJECT_MILESTONES.md](02_PROJECT_MILESTONES.md)
- 현재 상태: `REVIEW_REVISION_FOLLOW_UP_COMPLETE`

## 1. 현재 단일 작업

`SQ-M05`의 승인된 E6 문서 제작 COMPLETE (2026-10-01): 완료된 실험을 재실행하지 않고 문제 정의·방법·결과 표·관련 연구·한계·초록·결론을 적용 가능성과 근거 추적 주장에 맞췄다. 최초 96/144와 실패 48건, 개발 후 동일 사례 재시험 144/144를 구분했다. 파란색 개정 원고와 동일 내용 clean 원고 각 8쪽, 심사위원별 답변서 9/8/11항목과 PDF 10/9/12쪽을 완성했다. 28개 반영 발췌 및 원고 절·표·쪽 참조, marked/clean 페이지별 텍스트 동일성과 원 제출본·고정 코드 해시를 검증했다. E3 사람 검토와 개발 미사용 독립 시험은 미실시이며 전체 연구 검증 완료로 표시하지 않는다.

후속 편집 COMPLETE (2026-10-01): 사용자의 설명 축소 지적에 따라 원 제출본과 세 리뷰를 다시 비교했다. 유효한 자료 출처 흐름·단계별 방법·현재 UPPAAL 배열/두 위치/전이/질의·원문 회수 사례·실패 메커니즘·결과 활용을 복원·보강하고 서론은 간결하게 유지했다. 표14는 본문10쪽의3행2/7/18요약으로 정리했고27행 상세는 R3-11 답변서13쪽에 원 사유/건수 그대로 보존했다. 현재 marked/clean은11쪽, 답변서는10/9/13쪽이며28항목 참조·발췌·레이아웃 검증 PASS다. 이전 E6 완료와 봉인 산출물1,834파일은 해시가 유지되며 실험은 재실행하지 않았다. 새 빌드는 run004, [후속 검증 보고서](../../../../artifacts/projects/sequential-coc-verification/public/kiee-review-revision-001/manuscript-validation-2026-10-01-002/REPORT_KO.md)는 validation run002다.

실행 계획: [KIEE_REVIEW_RESPONSE_REEXPERIMENT_DESIGN_V01.md](../designs/KIEE_REVIEW_RESPONSE_REEXPERIMENT_DESIGN_V01.md). 원 제출본은 `paper/manuscript/latex-kiee-review-2022-coc-audit-10pages`이며 보존했다. 완성 개정본은 [revision-v01](../../paper/manuscript/latex-kiee-review-2022-coc-audit-revision-v01/README.md), 검증 결과는 [빌드 보고서](../../../../artifacts/projects/sequential-coc-verification/public/kiee-review-revision-001/manuscript-build-2026-10-01-001/REPORT_KO.md)와 [최종 재검증](../../../../artifacts/projects/sequential-coc-verification/public/kiee-review-revision-001/manuscript-validation-2026-10-01-001/REPORT_KO.md)에 있다.

다음 단일 작업 `READY_NEXT`: 저자의 최종 검토와 미확인 접수번호·실제 심사 수정 차수 확인. E6 파일 제작을 막는 사유는 없으며 외부 제출은 이번 승인 범위에 포함되지 않는다. 10쪽은 이전 원고 분량일 뿐 필수 제한으로 단정하지 않는다. 자연 오류 정확도·자동 의미 추출·사람 재평가·독립 일반화·정량 시간·차량 안전은 남은 한계로 유지한다.

## 2. 완료 조건

- [x] 대상 출판 경로와 원고를 명시한다.
- [x] 추가 보완이 현재 주장에 필수인지 구분한다.
- [x] mutation coverage와 자연 오류 검출 정확도를 혼동하지 않는지 재검토한다.
- [x] GuardSynth 합성 작업이 이 프로젝트로 유입되지 않았는지 확인한다.
- [x] 다음 작업 하나만 `READY_NEXT` 또는 `ACTIVE`로 둔다.

## 3. 참조

- [원고 개선계획](../../paper/manuscript/IMPROVEMENT_PLAN.md)
- [국내 학술지 보완계획](../../paper/manuscript/DOMESTIC_JOURNAL_COMPLETION_PLAN.md)
- [국제 워크숍 보강계획](../../paper/manuscript/INTERNATIONAL_WORKSHOP_PLAN.md)

## 2026-10-01 작업 위치 통합

사용자 요청으로 `sequential-coc-review-20260930` 작업 트리의 모든 내용이 본 저장소로 통합되었다. 동일 파일은 유지하고 최신 개정본을 반영했으며, 충돌한 양쪽 원본은 제한 산출물의 통합 기록에 보존했다. 후속 작업은 `/home/jinhyun/prj_ws/prj_jin/guardsynth-cc`에서 진행한다. 현재 11쪽 원고·세 답변서와 실험 결과의 내용은 통합 전과 동일하다.
