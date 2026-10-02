# 두 STOP 장면의 공통 배제 CNL 및 한정 개발 수용

- project_id: `guardsynth-coc`
- 기록일: 2026-09-29
- 상태: `ACCEPTED_SCOPED_DEVELOPMENT_SPEED_SUPERVISION`
- 상위: [연구계획](../plans/01_RESEARCH_PLAN_V02.md)
- 선행 source: [STOP 확인 결정](PAPER1_STOP_CONTROL_SOURCE_CONFIRMATION_DECISION_V01.md)
- 출처: `USER_CONVERSATION`; 정확한 발화 시각 미기록

직전 질문의 승인 대상:

> #7/#68에서 “STOP 지시가 적용되는 현재 판단에는 이동 여부가 불명이어도 새 출발·가속을 배제하되, 정지 목적 감속·정지 유지는 금지하지 않는다”는 문구가 의미를 보존하며, 이 공통 배제만 두 장면의 개발용 감독에 사용해도 될까요?

사용자 원답:

> 네

하나의 사용자 답변이 두 문서의 제시된 의미와 한정 개발 사용을 함께 수용했다.
Jonh의 새 진술, 인증 신원·서명·웹폼, 전문 열람 로그 또는 독립 검토자 두 명의 검토로
과장하지 않는다. 제시한 CNL 요약에 대한 사용자 동의이며, 두 문서 hash에 범위를 연결한다.

대상은 `stop-common-consequence-2026-09-29-001`의 candidate_7_cnl.txt와
candidate_68_cnl.txt, 버전 `eblc-speed-common-consequence-v0.1-proposal`이다.
이 버전 이름과 과거 proposal 상태는 보존하고 이번 프로젝트 내 한정 수용을 별도로 기록한다.
허용된 추가 감독은 `START_OR_ACCELERATE`의 공통 배제뿐이다. MOVING/STATIONARY를
새 관측 사실로 만들지 않으며 motion은 UNKNOWN이다. 기존 speed-contract v0.1 의미는 불변이다.

유지·비정지 목적 감속의 추가 배제, 정지 완료·해제, #68 원 CoC의 red-light 주장, 다른 장면,
전역 행동 허가·안전성·법적 인증 또는 본 학습/본 test 수용으로 확대하지 않는다.
기존 원 CoC, ACTION19/3마스크, 불일치, held #79/#81, 81clip 노출 제외를 보존한다.
단일 검토자 ACTION 결정은 유지하며 새 정답·추가 ACTION 응답을 만들지 않는다.

기존 clip split에서 두 장면은 모두 train이다. 두 장면의 조건부 개발 감독 수용은
정상 진행 source coverage, 충분한 독립 clip/power 또는 네 arm 본 학습 완료를 뜻하지 않는다.
가중치 업데이트 수·예산·모델·평가 프로토콜은 별도 실행 기록으로 남기며 이번 승인 자체를
학습 완료로 계산하지 않는다. 원본 응답과 과거 immutable run은 덮어쓰지 않는다.
