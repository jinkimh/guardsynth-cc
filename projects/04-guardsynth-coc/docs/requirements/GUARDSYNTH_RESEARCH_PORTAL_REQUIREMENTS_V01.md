# GuardSynth 연구 운영 포털 요구사항 v1

- owner: `guardsynth-coc`
- 상태: `APPROVED_FOR_IMPLEMENTATION`
- 승인일: 2026-08-14
- 설계: [GUARDSYNTH_RESEARCH_PORTAL_REFACTORING_DESIGN_V01.md](../designs/GUARDSYNTH_RESEARCH_PORTAL_REFACTORING_DESIGN_V01.md)
- 범위: 저장소 연구 운영의 read-only 투영과 명시적으로 활성화한 restricted review backend

## 필수 계약

1. 프로젝트 5개와 공용 플랫폼 1개를 `PROJECT_REGISTRY.json` 순서와 소유권으로 분리한다.
2. 상태·마일스톤·현재 작업은 canonical 문서를 live read하며 tracker–ledger 불일치는 fail closed한다.
3. 논문과 산출물은 owner registry에서 열거하고 client에 절대 경로나 restricted canonical path를 보내지 않는다.
4. 기본 포털은 canonical Markdown을 수정하지 않는다.
5. review backend는 explicit CLI configuration이 있을 때만 켜며 loopback, 인증, session, CSRF와 round capability를 요구한다.
6. reviewer는 자신의 assignment만 읽고, finalize된 원 판정은 update/delete하지 않는다.
7. adjudicator는 같은 round의 reviewer assignment와 겹치지 않는다.
8. guideline/review revision은 최대 2회이며 agreement와 progress는 versioned contract로 계산한다.
9. M16은 source-complete 60/60과 quota, calibration 선행조건을 충족하기 전 empirical annotation을 거부한다.
10. 기존 정적 포털과 legacy review artifact는 immutable history로 유지하되 활성 검토 메뉴에는
    현재 reviewer workflow만 노출한다. 대체·폐기·curator 전용·선행조건 미충족 패키지는 새 포털에
    복사하지 않는다. 복수의 활성 검토가 있으면 artifact `created_at` 최신순으로 정렬한다.

## 현재 gate

현재 M16은 `PARTIAL`, eligible `1/60`, human source review `0/60`이다. 포털 UI가 준비됐다는
사실은 연구 gate 완료나 empirical annotation 허용을 뜻하지 않는다.
