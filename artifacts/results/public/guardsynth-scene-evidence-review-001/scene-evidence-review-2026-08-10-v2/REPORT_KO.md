# GuardSynth 장면 근거 검토 패키지

- 상태: **EXECUTED**
- HTML: `SCENE_EVIDENCE_REVIEW.html`
- 합성 도식: 3개
- 판정 예제: 4개
- 자동 판정: CONFLICT → UNSUPPORTED → REVIEW_REQUIRED → SOURCE_COMPLETE
- 이미지 처리: 로컬 preview만 허용, JSON/CSV에 bytes 미포함
- 주장 범위: `REVIEW_WORKFLOW_AND_EVIDENCE_TRIAGE_NOT_SOURCE_CREATION_OR_VEHICLE_SAFETY`

이 패키지는 누락 근거를 만들어 주지 않는다. 검토 결과가 `SOURCE_COMPLETE`가 되려면
장면 association, geometry/transform/time, 적용 규칙과 필요한 차량 assurance가 실제
reference로 닫혀야 한다. 자동 권고보다 높은 `SOURCE_COMPLETE` 판정으로 우회할 수 없다.
