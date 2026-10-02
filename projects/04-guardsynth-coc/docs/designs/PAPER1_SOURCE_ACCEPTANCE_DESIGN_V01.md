# 1차 사건 근거 수용 및 최소 검토 설계

- project_id: `guardsynth-coc`
- 버전/기준일: `paper1-source-acceptance-v0.1`, 2026-09-08
- 작업: M14-R01-C (M12-R01 근거 수용 gate 포함)
- 상위 계약: [개발 행동 계약](PAPER1_ACTION_CONTRACT_DESIGN_V01.md)
- 범위: 기존 기록 재사용, #18 사건 근거 검토 준비/수용 소프트웨어. 독립 gold·학습 효과 아님.

## 1. 기계 확인과 사람 판단의 분리

SHA 일치는 동일한 자료임을 확인한다. 승인된 원본 annotation의 causal ID, 기존 영상 시간창
답변, geometry 품질 동의는 각각 다른 근거다. 하나를 사건 시점의 충돌 TRUE/FALSE나 독립
action gold로 바꾸지 않는다. 제출 완료 이력을 취소하지 않고 실제 저장된 좌표만 재사용한다.
현재 두 geometry 제출 JSON에는 normalized_pixel_polygons가 모두 비어 있다. 이는 브라우저에서
사용자가 그리지 않았다는 증거가 아니라, 확인한 export에 좌표가 없다는 뜻이다.

기계 단계는 32개 개발 후보 분모를 유지하고 19개 기존 관찰/13개 미관찰을 구분한다.
각 기존 관찰에 원본 geometry 품질·실제 좌표·source ID/시점·동시 통제를 연결한다.
공통 의미 영역과 사건 조건이 없으면 source-verified로 세지 않는다.

## 2. #18의 현재 입력과 시간 경계

원본 판단 시점 9,788,430us에 대해 영상 timestamp table의 마지막 과거 프레임은
297번/9,788,396us다. 미래 프레임 298번은 9,821,727us이므로 검토 입력에서 배제한다.
프레임 번호를 reasoning event_start_frame=99와 혼용하지 않는다. timestamp table의 기존
시계 대응 가정은 기록하고, 34us 차이를 독립적인 센서 동기화 증명으로 주장하지 않는다.

첫 영상 프레임의 센서 시각은 -111,570us이고 CASCADE 점의 주석은 0초다. 두 시점이 같다는
가정을 하지 않는다. 첫 프레임의 점 표시는 context-only 투영이며 정확한 시점 위치로 수용하지
않는다. 대상 동일성이 불명확하면 보류한다. 시간 offset을 몰래 보정하지 않는다.

검토 패킷은 주석상 0초 source anchor와 사건 이전의 무표시 프레임을 원해상도 JPEG로 제공하고,
t0의 원본 디코딩 픽셀은 PNG로 별도 보존한다. JPEG 표시본을 원본 pixel hash로 인증하지 않는다. CASCADE의
Agent3 점은 첫 프레임의 context-only 참고로만 표시하며 현재 위치로 이동/보간하지 않는다. 기계가 원본 이미지에서
제안한 t0 대상 점·진입 영역은 `MODEL_VISUAL_PROPOSAL_REQUIRES_CONFIRMATION`으로 명시한다.
초안 좌표와 사람의 확인 상태는 별도 필드이며 처음에는 어떤 답변도 확정되어 있지 않다.
녹색 drivable mask는 의미 conflict zone이 아니므로 원본 화면에 덮어쓰지 않는다.

## 3. 사람이 확인할 최소 정보

검토는 #18 한 장면만 먼저 요청한다. 이전 60/98개 설문을 다시 받지 않는다.

- 대상: 0초 Agent3 후보와 t0 대상의 동일성이 확인되는가? 다르거나 불명확하면 보류.
- 영역: 에고가 진입하려는 공통 충돌 영역을 영상에서 특정할 수 있는가? 초안이 틀리면 수정.
  차로 전체/반대차로/사람 몸 윤곽과 동일하지 않으며 metric geometry를 뜻하지 않는다.
- 보행자 조건: 그 사람이 해당 진입 경로를 점유하거나 횡단 중임이 현재 입력에서 확인되는가?
  TRUE=확인, FALSE=관계가 해소됐음이 확인, UNKNOWN=모름, CONFLICT=근거 충돌.
- 주도로 조건: CoC의 주도로 합류 문맥이 영상에서도 확인되고, 그 영역 진입에 앞서 양보해야
  할 교통 흐름이 관측되는가? 적용 문맥을 특정하지 못하면 UNKNOWN. 특정 국가 법규를 묻지
  않는다. 이는 연구용 operational 판단이며 법적 우선권 판정이 아니다.
- 각 판단의 짧은 근거. 불명확한 FALSE를 clearance로 사용하지 않는다.

이 화면은 CoC/기존 관찰/기계 제안을 보여주는 **source curation**이다. 독립 gold 화면이 아니다.
모르는 답변도 제출할 수 있으며 완료와 source 수용은 분리한다. 대상을 확인하지 못했거나
영역이 불명확하거나 어느 조건이 UNKNOWN/CONFLICT이면 evidence_valid=false로 남긴다.

## 4. 수용/내보내기 계약

응답은 packet SHA, candidate digest, event timestamp, schema version, reviewer ID/시각에
binding한다. 불일치·빈 근거·잘못된 enum·범위 밖/퇴화/자기교차 polygon을 거부한다.
서명 검증된 인간 신원을 주장하지 않으며 reviewer ID는 제출자 선언이다.

동일 대상·영역·적용 문맥과 TRUE/FALSE 근거가 모두 명시된 경우에만 이 개발 과제의
`HUMAN_REVIEWED_DEVELOPMENT_SOURCE`로 수용한다. 과거 시점 값을 만들거나 3시점 trace를
보간하지 않는다. 수용된 단일 시점 입력이라도 독립 action gold/CNL 검토 이전에는 학습 export=false.
필드가 불명확하면 응답은 보존하되 `REVIEW_RECORDED_SOURCE_UNRESOLVED`로 남긴다.

초안 저장은 packet SHA별 localStorage와 JSON export/import를 함께 제공한다. 저장 실패는
실제로 발생했을 때만 알리고, 확대는 dialog 안에서 열어 닫기/Esc로 돌아온다. 초안 polygon
수정은 point/zone 모드를 구분하고 undo/reset도 답변과 함께 보존한다.

## 5. 다음 독립 검토의 gate

영역/과제를 먼저 확정한 후 같은 사건 이전 시각 입력으로 별도의 행동 정답 화면을 만든다.
그 화면에는 CoC·기계 제안·이전 답변·EBLC/CNL·미래 영상·관측된 미래 ego 행동을 넣지 않는다.
이미 #18 CoC/검토에 노출된 연구 책임자는 새로운 독립 test reviewer로 자동 인정하지 않는다.
#18은 개발 사례이며 held-out 효과 검증 표본으로 승격하지 않는다.

CNL은 해당 구조화 명세와 조항별 대응을 독립 검토한다. 이 두 독립 판단은 기계가 서명하거나
정답을 복제해 대체할 수 없다. source 검토 준비 완료와 M14/M16 전체 완료를 구분한다.
