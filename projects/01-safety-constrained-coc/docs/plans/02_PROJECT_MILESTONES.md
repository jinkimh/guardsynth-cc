# Safety-Constrained CoC 프로젝트 마일스톤

- 프로젝트: `safety-constrained-coc`
- 문서 계층: `02` 연구계획의 단계별 분해
- 기준 연구계획: [01_RESEARCH_PLAN_V01.md](01_RESEARCH_PLAN_V01.md)
- 실행 관리: [03_PROJECT_EXECUTION_TRACKER.md](03_PROJECT_EXECUTION_TRACKER.md)

## 1. 상태 규칙

`COMPLETE`는 근거 파일이 있는 종료 단계, `READY_NEXT`는 바로 수행할 다음 단계,
`QUEUED`는 선행조건을 기다리는 단계다. 합성 실험 완료와 실제 차량 안전성 입증을
같은 상태로 취급하지 않는다.

## 2. 마일스톤 원장

| ID | 마일스톤 | 상태 | 종료 근거 또는 gate |
|---|---|---|---|
| SC-M00 | 연구 질문과 주장 경계 고정 | `COMPLETE` | 연구계획과 원고 작성계획 |
| SC-M01 | 정적 후보 선택 feasibility | `COMPLETE` | 진행 보고서와 재현 코드 |
| SC-M02 | 시간적 Guard·다중 maneuver 다중 seed 평가 | `COMPLETE` | 다중 seed 실험 보고서 |
| SC-M03 | 국내 원고와 재현 근거 정리 | `COMPLETE` | `MANUSCRIPT_READY` 상태 |
| SC-M04 | 다음 투고 경로와 중복 출판 경계 결정 | `READY_NEXT` | 명시적 제출 결정 |
| SC-M05 | IEEE IV 확장 gate 수행 | `QUEUED` | 실행 가능 궤적·동일 모델 폐루프·강한 기준선 |
| SC-M06 | 국제 저널 확장 gate 수행 | `QUEUED` | 확장계획의 Go/No-Go 기준 |

M05와 M06은 자동으로 동시에 활성화하지 않는다. M04에서 선택한 제출 경로와 출판 정책에
따라 하나의 다음 작업만 실행 추적표에 둔다.

## 3. 변경 규칙

연구 질문이나 성공 기준을 바꾸는 변경은
[01_RESEARCH_PLAN_V01.md](01_RESEARCH_PLAN_V01.md)에 먼저 기록한다. 완료 상태는 보고서,
원고 또는 재현 가능한 산출물이 확인될 때만 갱신한다.
