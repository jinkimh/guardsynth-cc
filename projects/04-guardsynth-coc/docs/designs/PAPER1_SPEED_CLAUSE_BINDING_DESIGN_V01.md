# 속도 행동과 source clause 연결 제안

- project_id: `guardsynth-coc`
- 상태: `PROPOSED_NOT_ACCEPTED`; 담당자 판단 전 장면 적용·EBLC/CNL export 금지
- 기준: [연구계획](../plans/01_RESEARCH_PLAN_V02.md), [속도 endpoint 초안](PAPER1_LONGITUDINAL_ENDPOINT_DESIGN_V01.md)
- 범위: 기존 21건 재사용, source 구절 연결 및 유한 인터페이스 검사. 독립 gold/SMT 검증 아님.

## 출처와 실행 전제

원본 CoC의 선두 행동 구절을 정확한 문자 offset 및 SHA-256으로 연결한다. gentle/strong과
이유·경로를 포함한 전체 원문을 보존한다. 이는 source recommendation이지 의무 성립 근거가
아니다. `Resume speed`는 현재 감속 중이면 가속, 이미 회복했으면 유지일 수 있으므로
START_OR_ACCELERATE로 확정하지 않는다. `Adapt speed`도 방향을 정하지 않는다.

기존 `person_occupies_designated_entry_path`/`CLEAR_REQUIRED_FOR_ENTRY`는 영역 진입
조건이다. 모든 관련 기존 계약의 hash·obligation을 연결하되 속도 행동으로 변환하지 않는다.
TRUE는 감속/정지 필요성, FALSE는 속도 회복 허가를 자동 증명하지 않는다. 기존 NA, UNKNOWN,
통제 FALSE, #59 설명, #68/#88 근거 문제와 #86/#94 메모는 원래 기록에 연결해 보존한다.

제안 인터페이스는 `clause_kind`, `motion_state`(MOVING/STATIONARY/UNKNOWN),
`applicability`(TRUE/FALSE/UNKNOWN/CONFLICT), `evidence_valid`(bool)를 받는다.
applicability는 **새 속도 의무 자체의 현재 적용성**이며 기존 ped/control truth를 복사하지
않는다. 실제 21건은 motion UNKNOWN, applicability UNKNOWN, evidence_valid false다.
승인된 규칙·대상·인과 시점·움직임·적용성 근거가 없으므로 이 값을 자동 채우지 않는다.

## 담당자 수용이 필요한 제안 표

현재 한 번의 의도적 속도 선택만 다룬다. 아래 표는 유효한 TRUE 속도 의무가 별도로
성립했다는 가정 아래의 **그 clause 단독 배제**이며 전체 장면 행동 적절성/허가가 아니다.

| 제안 clause | MOVING에서 배제할 행동 | STATIONARY |
|---|---|---|
| SPEED_REDUCTION_REQUIRED | MAINTAIN_SPEED, START_OR_ACCELERATE | 의미 미지원, UNRESOLVED |
| STOP_REQUIRED | MAINTAIN_SPEED, DECELERATE, START_OR_ACCELERATE | 출발/가속 배제; 정지 유지 배제 안 함 |

DECELERATE는 완전 정지를 목표로 하지 않는 선택이다. STOP_REQUIRED 아래 DECELERATE를
배제하는 것은 이 endpoint 정의에 따른 제안이며, 실제 정지 동작의 감속을 금지한다는 뜻이
아니다. 반대로 SPEED_REDUCTION_REQUIRED가 STOP_OR_WAIT를 배제하지 않아도 불필요 정지가
적절하다는 뜻은 아니다. progress reference는 별도로 필요하다.

- motion UNKNOWN 또는 적용성 UNKNOWN/CONFLICT 또는 invalid면 네 행동 모두 UNRESOLVED.
- 유효한 FALSE이면 해당 clause는 행동을 배제하지 않는다. 다른 의무의 해소/전체 허가 아님.
- STATIONARY의 MAINTAIN_SPEED/DECELERATE는 선택지 정의와 맞지 않아 UNRESOLVED로 둔다.
  이는 사람의 INAPPROPRIATE 답변을 자동 생성하는 규칙이 아니다.
- 속도 회복/가속을 강제하는 clause는 제안하지 않는다. #48/#50/#85의 Resume 및 #94 Adapt는
  단일 행동 연결 미확정이다. #86/#88의 acceleration은 원문 주장만 연결한다.
- lifecycle, 정지선 도달, 수치 강도·거리, 동시 lateral maneuver, 실제 안전성은 미지원이다.
  두 clause의 합성이나 실제 EBLC lowering/CNL은 수용된 의미와 source가 확보된 뒤 구현한다.

## 실행 검사와 사람 판단

새 runner는 출처 manifest와 기존 계약을 검증하고 2 clause × 3 motion × 4 truth × 2 validity ×
4 action의 192개 합성 interface 결과를 남긴다. 승인 상태는 항상 PROPOSED이며 실제 장면
출력은 UNRESOLVED다. 테스트는 UNKNOWN→STOP, FALSE→가속 허가, 진입→속도 정책 혼동 및
원문/식별자 변경을 차단한다. old SMT를 재실행하거나 speed SMT 통과로 재표기하지 않는다.

다음 두 판단을 담당자에게 요청한다.

1. 위 clause 표와 ‘완전 정지를 목표로 하지 않는 감속’ 구분을 개발 의미로 수용할지,
   아니면 감속/정지 선택지 정의를 수정할지. 수용해도 scene applicability/source/gold는 미확정이다.
2. 동일 과거 영상과 네 선택지만으로 판단 불가를 허용하는 공통 입력을 개발 검토에 수용할지.
   경로 민감 #79/#81은 문맥 수용 전 보류한다는 제안이다. 21건 전체 분모와 노출 이력은 유지한다.
   이는 장면 배정·전수 배포 요청이 아니다.

수용 후에도 Jonh 본인의 실제 노출 선언과 담당자 입력 수용, 별도 배정 결정이 필요하다.
ACTION 후 CNL 순서를 지킨다. 1인은 개발 검토만 가능하며 2인 formal gate를 대체하지 않는다.
적절성 gold 0/21, 독립 위반·progress reference 없음, main cohort/split/endpoint NOT_FROZEN.
