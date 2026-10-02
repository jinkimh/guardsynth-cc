# Safety-Constrained CoC 연구계획 v1

- 프로젝트: `safety-constrained-coc`
- 문서 계층: `01` 최상위 연구계획
- 상태: `MANUSCRIPT_READY`
- 하위 마일스톤: [02_PROJECT_MILESTONES.md](02_PROJECT_MILESTONES.md)
- 실행 관리: [03_PROJECT_EXECUTION_TRACKER.md](03_PROJECT_EXECUTION_TRACKER.md)
- 관련연구: [RELATED_WORK_SURVEY_V01.md](../surveys/RELATED_WORK_SURVEY_V01.md)
- 논문 작성계획: [WRITING_PLAN.md](../../paper/manuscript/WRITING_PLAN.md)

## 1. 연구 질문

명시적으로 주어진 실행 제약이 목표를 보존하면서 VLM의 제약 위반 궤적 선택을 줄이는가?

## 2. 범위

- 동일 장면과 목표에서 실행 제약만 바꾸는 paired-contract 비교
- 정적·시간적·다중 maneuver 후보 선택 평가
- 위반률, 목표 완료율, 교착 및 과도한 보수성의 분리 보고
- 합성 및 제한된 실험 결과에 맞춘 주장 경계 관리

다음 항목은 이 프로젝트의 주장 범위가 아니다.

- 장면과 외부 근거에서 실행 제약을 자동 합성하는 문제
- 실제 도로 또는 실제 차량의 안전성 보증
- 별도 모델에서 얻은 폐루프 결과를 동일 VLM 시스템의 증거로 합치는 것

## 3. 현재 근거

- [진행 보고서](../reports/SAFETY_CONSTRAINED_COC_PROGRESS_REPORT_V01.md)
- [시간적 Guard 다중 seed 실험 보고서](../reports/TEMPORAL_GUARD_MULTISEED_EXPERIMENT_REPORT_V01.md)
- 국내 원고 및 재현 코드

현재 근거는 feasibility와 제한된 재현 결과를 지지한다. 실제 차량 안전성이나 일반적인
폐루프 안전성 증명으로 확대하지 않는다.

## 4. 산출물과 성공 기준

1. 연구 질문·평가 단위·주장 경계를 원고 전반에서 일치시킨다.
2. 기존 실험의 재현 근거와 원시 예측 단위 집계를 보존한다.
3. 투고 경로를 결정한 뒤 해당 경로의 사전 gate를 통과한 증거만 원고에 사용한다.
4. 국제 확장을 선택하면 실행 가능한 궤적, 동일 모델 폐루프, 강한 기준선과 통계를 별도
   단계에서 확보한다.

## 5. 하위 계획

논문별 계획은 이 연구계획의 범위를 바꾸지 않는 하위 산출물이다.

- [국내 논문 작성계획](../../paper/manuscript/WRITING_PLAN.md)
- [IEEE IV 2027 제출 마일스톤](../../paper/manuscript/IEEE_IV_2027_SUBMISSION_MILESTONES.md)
- [국제 저널 확장계획](../../paper/manuscript/INTERNATIONAL_JOURNAL_EXPANSION_PLAN.md)

범위나 성공 기준을 바꿀 때는 이 문서를 먼저 개정하고 마일스톤과 실행 추적표를 동기화한다.
