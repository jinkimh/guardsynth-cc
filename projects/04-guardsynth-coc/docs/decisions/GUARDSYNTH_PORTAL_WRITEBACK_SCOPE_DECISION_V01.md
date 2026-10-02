# GuardSynth 포털 writeback 범위 결정 v1

- 결정 ID: `GS-PORTAL-WRITEBACK-001`
- 결정일: 2026-08-14
- 상태: `APPROVED`
- 적용 범위: `apps/research_portal/`

## 결정

포털은 `PROJECT_REGISTRY.json`, `PROJECT.yaml`, `STATUS.md`, 연구계획, 마일스톤 원장, 실행
트래커, survey/result index와 platform 문서를 read-only로 투영한다. 포털 API는 이 canonical
Markdown과 registry를 수정하지 않는다.

동적 write는 새 round의 restricted SQLite review 운영 데이터에만 허용한다. 연구 질문, 성공
기준, claim boundary와 scope 변경은 project owner가 decision record와 versioned plan으로 수행한다.
향후 Markdown writeback이 필요하면 별도 decision에서 allowlist, original hash, optimistic lock,
field-level patch와 audit 계약을 먼저 승인한다.
