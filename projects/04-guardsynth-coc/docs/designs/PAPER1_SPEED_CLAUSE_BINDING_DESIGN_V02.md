# 승인된 속도 개발 계약 실행 설계

- project_id: `guardsynth-coc`
- 상태: `ACCEPTED_DEVELOPMENT_SEMANTICS_SOURCE_PENDING`
- 권위: [두 사항 승인 기록](../decisions/PAPER1_SPEED_DEVELOPMENT_APPROVAL_DECISION_V01.md)
- 선행 설계: [V01 제안](PAPER1_SPEED_CLAUSE_BINDING_DESIGN_V01.md), 원문/이전 run 보존

V01 표와 UNKNOWN/CONFLICT/invalid, stationary 의미 미지원 조건을 그대로 구현한다.
플랫폼 `speed_contract.py`는 versioned 단일 clause, 한 판단 시점 계약을 검증하고 기존
EBLC Core→SMT로 lowering한다. 각 행동의 clause verdict와 배제 gate를 구분한다.
Core의 최소 horizon은 2이므로 모든 clause를 INITIAL에만 적용하고 두 번째 frame은 자유
padding으로 둔다. 현재 판단 검사만 수행하며 미래 예측/전이 보장으로 해석하지 않는다.
UNRESOLVED에서는 행동을 배제하지 않지만 어떤 행동도 적절/안전/허가로 인증하지 않는다.
유효한 FALSE 역시 해당 clause만 배제하지 않는다. lifecycle·수치 강도·거리·다중 clause
합성은 지원하지 않는다. 이것은 연구용 개발 정책이며 일반 법규 또는 실제 안전 명령이 아니다.

CNL은 같은 구조를 deterministic하게 투영하고 문장별 field/source/hash를 기록한다.
감속과 정지를 구분하고, subject/target·predicate·rule_ref·네 행동 의미·불확실성·해소의
범위를 보존한다. target은 UNBOUND이며 scene 적용성은 확인되지 않았음을 표시한다.
L2/L3 공통 renderer는 solver를 호출하지 않는다. 독립 CNL 의미 검토는 여전히 미완료다.

21개 원문 연결 중 15개 감속/정지 후보만 조건부 계약/CNL을 생성한다. #79/#81도 담당자
자료에서 보류 사유와 함께 보존하되 ACTION 입력에서는 제외한다. 나머지 6건은 미지원
clause로 보존하며 가속 의무를 만들지 않는다. 원문 gentle/strong과 전체 CoC는 그대로다.
모든 실제 scene 입력은 motion UNKNOWN, applicability UNKNOWN, evidence_valid false이며
과거 ped/control 답변으로 채우지 않는다. 계약 생성 수는 수용된 장면 수가 아니다.

검증은 2 종류 × 3 motion × 4 applicability × 2 validity의 전제 SAT, action verdict의
단일성, 행동 배제 결과를 확인한다. 승인 전 V01의 유한 표는 독립 구현 oracle로 재사용한다.
action gate 제거 mutation에서는 원래 배제되던 유지 행동이 SAT가 되어야 한다.
실제 15건은 UNKNOWN 조건과 네 UNRESOLVED verdict만 검사한다. 안전성/gold 증명은 아니다.

19개 준비 입력은 기존 공통 문구와 과거 JPEG만 allowlist로 추출한다. 프레임 hash/시점과
scene identity를 확인하고 CoC/답변/도형/AI 판정/규칙/CNL은 포함하지 않는다. 응답은 전부
null, 배정 수는 미정이다. 자기 노출 선언용 빈 양식을 별도로 준비하되 검토자의 응답으로
기록하지 않는다. 새 입력은 포털에 등록하거나 검토자에게 전달하지 않는다.

완료 기준: 계약 schema/타입 및 source refs 검사, 실제 SMT와 mutation 결과, CNL field
검사, 입력 누출·시간/해시 회귀, immutable manifest. 이후 필요한 사람 입력은 Jonh 본인의
실제 노출 선언과 별도의 실제 배정/배포 결정이다. 현재 두 승인 사항을 다시 묻지 않는다.
