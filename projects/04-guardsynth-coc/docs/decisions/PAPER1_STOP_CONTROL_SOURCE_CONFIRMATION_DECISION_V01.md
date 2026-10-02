# 두 장면의 작업자 STOP 통제 source 확인

- project_id: `guardsynth-coc`
- 기록일: 2026-09-29
- 상태: `ACCEPTED_SCOPED_DEVELOPMENT_SOURCE_PREMISE`
- 출처: `USER_CONVERSATION`, 사용자 후속 메시지로 전달된 확인
- 발화의 정확한 시각: 미기록
- 신원·서명·웹폼 인증: 없음. Jonh의 새로운 인증 진술로 기록하지 않음
- 상위: [연구계획](../plans/01_RESEARCH_PLAN_V02.md)
- ACTION 기준: [단일 검토자 결정](PAPER1_SINGLE_REVIEWER_ACTION_DECISION_V01.md)

사용자가 전달한 원문:

> #7 - 작업자의 STOP 표지가 에고 차량에 대한 정지 지시로 보임

> #68 - 작업자의 STOP 표지가 에고 차량에 대한 정지 지시로 보임

이 답변은 직전 요청한 두 후보의 정지 통제 개발 전제 수용을 해결한다. 기존 source
바인딩의 candidate digest와 사건 시점을 유지하고, 그 시점에 작업자의 STOP 표지가
ego에 적용된다는 제한된 개발 source 전제를 수용한다. `STOP_REQUIRED`의 적용성은
TRUE, 해당 source 전제의 evidence_valid는 true로 연결한다. 이는 근거가 없는 새로운
일반 정책이 아니라 사용자가 확인한 두 장면의 정지 지시와 이미 승인된 정지 의미의 결합이다.

대상 ID는 사용자 확인의 작업자 STOP 표지를 지칭하는 scene-local 식별자다. CASCADE
Agent1의 물리적 동일성·좌표를 인증하지 않는다. CASCADE Stop Sign interval은 별도
보조 근거로 연결한다. #68의 원 CoC red-light 주장은 그대로 보존하되 이번 확인으로
참임을 인증하지 않는다. STOP paddle과 red light를 서로 대체하거나 원문을 수정하지 않는다.

motion은 UNKNOWN이다. 정지 완료·감속 정도·정지 의도 관측·해제·다른 통제·다른 장면·
학습 적격성을 확인한 답변이 아니다. 기존 speed v0.1은 UNKNOWN motion에서 모든 행동
verdict를 UNRESOLVED로 유지한다. 실제 전제를 고정한 Core와 motion별 가정 검사를
분리하며, 가정 검사는 현재 이동 상태나 ACTION 참조값을 생성하지 않는다.

원 ACTION19건·3마스크와 이전 immutable run을 보존한다. ACTION 정답/이유를 제약
입력으로 읽지 않는다. 이 source 확인을 다시 묻지 않으며 새 설문/UI를 만들지 않는다.
독립 CNL 의미 확인, 남은 motion/target/source gap, 불일치와 split/power 요건은 별도다.
