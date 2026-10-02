# 속도 source 조건·대상 바인딩

- project_id: `guardsynth-coc`
- 기준일: 2026-09-29
- 상태: `MACHINE_BINDING_IMPLEMENTED_SOURCE_ACCEPTANCE_PENDING`
- 상위: [연구계획](../plans/01_RESEARCH_PLAN_V02.md), [승인된 속도 의미](PAPER1_SPEED_CLAUSE_BINDING_DESIGN_V02.md)
- 근거 수용 경계: [source 관찰 수용 결정](../decisions/SOURCE_GAP_OBSERVATION_ACCEPTANCE_DECISION_V01.md)

`bind_speed_sources.py`는 완료된 ACTION intake와 독립적으로 기존 source 관찰·CASCADE·
raw egomotion을 읽는다. ACTION 제출물/정답/이유/추가 설명은 입력 목록에 없다. 기존
19장면/17 clips를 유지하고 #79/#81은 보류한다. 32분모와 81clip 시험제외 원장을 보존한다.

관찰의 대상 설명/normalized point를 원답 JSON pointer와 마지막 과거 표시 JPEG에 연결한다.
기존 immutable 화면의 마지막 프레임 전용 그리기 제한을 확인하고 이미지 해시·시점을
검사한다. 생성한 source_target ID는 관찰 레코드의 식별자다. CASCADE Agent와 같은 사람이라는
판단, 실제 metric 위치, 충돌 영역 인증이 아니다. 원답 description/좌표를 수정하지 않는다.

CASCADE는 원본 SHA·clip ID를 검증한 후 부모/자식 interval이 모두 사건을 포함하는 actor와
signal/light 상태를 연결한다. ego 행동 및 because_of/action_target은 이 바인딩의 입력
전제로 사용하지 않는다. 동시 통제를 모두 보존하며 부재를 해제 근거로 만들지 않는다.
Stop/Slow Down 주석은 시점별 source 주장이다. observer control UNKNOWN을 덮어쓰지 않는다.

egomotion은 기존 materialization manifest의 clip/video/파일 SHA로 연결한다. 같은 영상의
파생 사건은 원 materialization candidate와 요청 event를 별도 보존하고 각 event 이전의
마지막 raw velocity row를 선택한다. 미래 보간·offline-smoothed 위치 미분은 사용하지 않는다.
velocity norm은 원 단위의 수치 근거로 기록한다. pinned parquet schema의 단위, 센서 오차,
clock/freshness와 stationary 기준이 확정되지 않아 현재 MOVING/STATIONARY로 인증하지 않는다.
표본 0은 실제 정지 의도 또는 STOP_OR_WAIT 적절성 정답이 아니다.

기존13 speed Core에 `reported_ped_truth`, `reported_road_truth`, `reported_control_truth`를
별도 typed enum 변수로 추가하고 실제 source 보고값으로 INITIAL 고정한다. legacy NA는 원값과
미해결 사유를 보존하며 reported UNKNOWN으로 나타낸다. 이 변수에서 speed applicability로의
함의는 없다. 기존 speed 전제 UNKNOWN/invalid를 명시적으로 고정하고 관찰값 변조,
근거없는 applicability TRUE/FALSE 및 확정 verdict를 UNSAT로 검사한다. base SAT도 검사한다.
이는 새 source 연결 검증이며 이미 완료된 CNL 템플릿 재생이나 독립 정답 검증을 반복한 것이 아니다.

속도 source 의무를 확정하려면 해당 관찰의 속도 과제 범위 수용과 명시적인 충분조건 정책이
필요하다. 기존 ped TRUE는 경로 점유 보고이며 감속/정지 중 어떤 의무인지 자동 결정하지 않는다.
control FALSE는 진입 제한의 부정이며 speed release가 아니다. 각 행의 `gaps`는 필요한
필드·원본 참조·실패 이유를 남긴다. 계약 없는6건은 임의로 stop/reduction 계약을 받지 않는다.

현재 가장 좁은 사람 판단 후보는 #7/#68이다. 기존 control APPLICABLE+TRUE와 사건 시점
CASCADE Stop이 함께 있으나, 이를 정지 통제의 개발 전제로 수용하는 판단은 미기록이다.
#68의 STOP paddle 근거는 원 CoC의 red-light 주장과 별개다. 이 둘의 동일성을 만들거나
원문을 수정하지 않는다. 이 수용 판단은 이미 승인된 감속/정지 출력 의미의 재질문이 아니다.
다른 source/시간/정책 gap과 독립 CNL 의미 확인, 2인 formal gate는 별도로 남는다.

검증: ACTION 필드/ego action 변경 불변성, 미래·offline/비정상 motion 거부, 원답 identity,
부모 interval, 같은 clip의 다른 event, Core source binding 제거 mutation, immutable
end-to-end 해시/분모 검사를 수행한다. 학습/export·새 UI·검토 배포는 이 실행의 출력이 아니다.
