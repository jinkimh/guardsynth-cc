# 1차 논문 source/CNL/VLM 실행 준비도 보고서

- project_id: `guardsynth-coc`
- 기준일: 2026-09-08 (이전 실행 이력 보존)
- 범위: M12 source inventory/개발 정책, M14 행동 계약·학습 예제 연결, M15/M18 software smoke
- 판단: `SCENE_CONDITIONED_CNL_GENERATED_REVIEW_PENDING`; 실제 학습 효과 미판정
- 설계: [선택 범위와 남은 gate](../designs/PAPER1_CNL_LEARNING_DESIGN_V01.md)

## 9. 2026-09-08 실제 관측값을 자연어 생성에 연결

기존 공통 renderer는 관측값을 받지 않아 제약의 작동 규칙을 설명했다. 한글화/A-B 화면
수정만으로는 실제 장면별 학습 문장이 되지 않았다는 지적에 따라 생성 입력 연결을 보완했다.

- 현행 run: `guardsynth-paper1-reviewed-contract-001/scene18-conditioned-cnl-2026-09-08-002`.
- 실제 검토값과 명세를 함께 입력하고 기존 Core/SMT backend로 12/12 검사 예상 일치.
- 보행자 위험 확인과 주도로 미확정은 검토에 귀속한 문장으로, 현재 진입 보류는 정책 조건부
  행동 지시로, 이후 진입 조건은 미래 관측이 아닌 재판단 조건으로 생성한다. 한·영 4문장이다.
- 문장별 binding 경로·Core 조항·질의 대응을 저장했다. UNKNOWN을 FALSE로 채우지 않으며
  solver witness의 미관측 값을 사실로 사용하지 않는다. 독립 ACTION 답변도 생성 입력에서 제외했다.
- 실제 장면·기존 검토 근거·생성 문장을 한 화면에 제공한다. 공통 규칙 A/B 검토는 이 과제에서
  대체되며 완료로 집계하지 않는다. 기존 ACTION 응답 1건은 보존한다.
- CoC+CNL 삽입은 차단된 개발 미리보기. 장면별 독립 검토·전체 source·gold/split·영문 검토가
  남아 학습 export는 0이다. 10개 integration tests에 질의 replay, UNKNOWN/조건 변화,
  잘못된 binding·gate mutation, HTML 문장/이미지 대응, 새 제출 형식·독립성, 초안/확대 복귀가 포함된다.
  UI 검사는 Node DOM-stub이며 실제 브라우저 레이아웃 검증을 뜻하지 않는다.

[설계와 주장 경계](../designs/PAPER1_SCENE_CONDITIONED_CNL_DESIGN_V01.md).

## 8. 2026-09-08 실제 검토값 연결과 독립 검토 준비 (이전 단계)

- 실행: `guardsynth-paper1-reviewed-contract-001/reviewed-scene18-execution-2026-09-08-001`.
- 원본과 사용자 추가 확인을 재검증했다. 대상/영역과 보행자 TRUE/valid는 수용하고,
  다른 차량 움직임 미확인에 따라 주도로 UNKNOWN/invalid를 단일 시점 Core 전제로 연결했다.
- Z3 4.16.0의 10/10 검사 일치: 전제 SAT, 진입 UNSAT, 보류 SAT. UNKNOWN에서 clearance와
  review 불필요를 주장할 수 없다. 과거 road 활성 여부 및 다음 ped TRUE/FALSE는 각각 SAT로
  미관측 자유 입력임을 확인했다. 이는 독립 행동 정답이나 차량 안전성 증명이 아니다.
- 공통 CNL 생성, CoC/기존 답변/솔버 결과/미래 프레임 없는 ACTION 화면, 별도 CNL 5조항
  의미 검토 화면, packet-bound 제출 검증기를 구현했다. 단위 6개·실제 자료 통합 9개 통과.
  JS 문법 및 DOM-stub 확대 복귀·초안 복원·패킷 혼입 거부 검사 통과;
  실제 브라우저 레이아웃 검증은 수행하지 않았다.
- 독립 실제 응답 0, full source-verified 0, 학습 export 0. #18은 개발 사례이며 held-out이 아니다.
- 다음 사람 개입: 미노출 ACTION 검토자를 배정하고 직접 링크만 먼저 전달한다. Jin Hyun Kim의
  기존 source 검토는 다시 요청하지 않는다. 행동 제출 이후 CNL 검토를 진행한다.
  단일 응답만으로 main cohort, 신뢰도, 학습 효과를 완료 처리하지 않는다.

[검토 분리와 남은 gate](../designs/PAPER1_INDEPENDENT_DEVELOPMENT_REVIEW_DESIGN_V01.md).

## 7. 2026-09-08 근거 수용 기계 단계와 사람 개입 지점 (완료된 준비 이력)

- 현행 run: `guardsynth-paper1-source-acceptance-001/scene18-source-acceptance-2026-09-08-003`
  (프로젝트 restricted artifact root). 001은 초기 화면 이력, 002는 zero-time assertion 실패를 보존한다.
- 32개 개발 후보를 유지하며 기존 관찰 19개와 미관찰 13개를 재감사했다. 원본 geometry
  제출 98건의 완료는 유지하지만, 두 업로드 JSON 모두 실제 polygon 좌표가 0건이다.
  “사용자가 그린 적 없음”이 아니라 “현재 export에서 복원할 좌표 없음”이라는 결론이다.
- #18 원본 영상의 과거 프레임 21개를 원해상도 JPEG로 제공하고 t0 원본 BGR pixel SHA를
  기존 geometry manifest와 대조한 뒤 무손실 PNG로 보존했다. 최대 입력 시각 9,788,396us는
  사건 9,788,430us보다 34us 이르며 미래 프레임은 넣지 않았다.
- 첫 영상 프레임의 센서 시각 -111,570us와 CASCADE 점 주석 0초는 같지 않다. 첫 프레임에
  표시하는 점은 시간 대응 미확정 context-only이며 사건 시점 위치로 보간하지 않았다.
- 대상 점/진입 영역은 명시적인 기계 시각 제안이다. 인간 답변은 전부 미선택으로 시작하고
  기존 CoC/관찰도 확인용으로 분리한다. 이 화면은 독립 행동 gold 검토가 아니다.
- strict packet SHA/ID/시점/필드·좌표·polygon·근거 검증, UNKNOWN/CONFLICT 보류,
  source 수용과 학습 export 분리를 구현했다. 단위 7개+실제 자료 통합 7개 tests 통과.
  Node DOM-stub에서 수정·undo·확대 복귀·localStorage 복원·JSON 혼입 거부도 검사했다.
  이는 실제 브라우저의 레이아웃/접근성 자동 검증을 대신하지 않는다.

**당시 필요했던 사람 개입(이후 제출·추가 확인 수신 완료):** #18의 Agent3 동일성, 공통 진입 영역,
현재 보행자/주도로 조건을 확인하거나 판단 불가로 제출해야 한다. 법규/관할/source ref 작성,
이전 60/98개 전체 설문 반복은 요청하지 않는다. 모르는 답변을 자동 FALSE로 채우지 않는다.
독립 행동 gold는 영역/과제 확정 이후, 기존 CoC/제안/미래 영상을 제외한 화면에서 다른 검토
절차로 받는다. 실제 source-verified/export는 여전히 0이며 M14/M16 전체는 PARTIAL이다.

[설계와 수용 기준](../designs/PAPER1_SOURCE_ACCEPTANCE_DESIGN_V01.md),
[검토 화면](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-source-acceptance-001/scene18-source-acceptance-2026-09-08-003/scene18_source_binding_review.html).

## 6. 2026-09-08 행동 계약의 실제 Core실행

이번 범위는 M12-R01-A 개발 정책과 M14-R01-A/B 실행 경로다. 새
[개발 계약](../designs/PAPER1_ACTION_CONTRACT_DESIGN_V01.md)은 `CLEAR_REQUIRED_FOR_ENTRY`를
명시하고 보행자·주도로 의무를 분리한다. 실제 source/gold 계약 전체의 동결은 아니다.

- 실행: `artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-action-contract-001/scene18-action-contract-2026-09-08-002/`
- 경로: 해시 재검증한 #18 CoC/annotation/video → pinned task adapter →
  `eblc-action-contract-v0.1` parser → 기존 typed Core → 기존 SMT compiler → 공통 CNL renderer.
- Z3 4.16.0: 기본 SAT 1, 전제 SAT 12, probe 12(SAT 3/UNSAT 9), 총 25/25 예상 일치.
  gate 제거 mutation의 전제·UNKNOWN 진입은 각각 SAT(별도 2질의). SMT-LIB 27개를 보존했다.
- 기존 UNKNOWN 진입 허점 2개를 새 정책 아래에서 닫았다. 전 조건 clear에서 ENTER와 DEFER
  모두 가능하므로 진행 가능성을 유지하지만 실제 진행률/liveness를 증명하지는 않는다.
- 플랫폼 9개 tests: 두 의무의 truth×valid×prior 256개 조합에 대해 행동별 512회 검사,
  schema 실패, lifecycle·invalid·mutation·CNL 대응 검사. 실제 source 통합 4개 tests도 통과.
- `RUN_MANIFEST.json`에 입력·정책·코드/schema·출력 해시와 runtime을 고정했다. 기존 ID 덮어쓰기를 거부한다.
- 001도 보존했다. 002는 CNL의 review_required 정의를 Core와 동일한 “if and only if”로 명확히 했으며 solver 결과는 같다.
- 조건부 명세/CNL 각 1건, source-verified 0건, 학습 export 0건. 실제 입력의
  target/zone/predicate/validity는 미확정을 유지하며 독립 action gold는 null이다.

기계 실행 완료는 영상 해석 정확성·범용 추출기·독립 의미보존 검토 완료가 아니다.
다음 M14-R01-C는 사건 시점의 대상/영역/predicate와 근거 수용 조건을 연결하는 작업이다.
독립 action gold와 CNL 검토 이후에만 학습 예제를 확정한다. 기존 설문 전량 반복은 요구하지 않는다.
전체 M12/M14/M16 PARTIAL, 본 VLM 학습/효과 미실행을 유지한다.

아래 1–5절은 이전 실행의 이력이다.

## 1. 실제 완료한 작업

1. PhysicalAI 원본 reasoning의 1,740 clip 행 / 2,077 events를 조사했다. events 결측 9행을
   별도 기록했다. 기존 98개 후보 모두 clip+timestamp로 원본 CoC에 정확히 연결됐으며,
   선택 보행자·자전거 양보 후보 32개/29 clips도 32/32 연결됐다.
2. 기존 source-aware generator→EBLC bundle→Core/Z3→CNL을 CoC supervision builder에
   연결했다. L2는 같은 renderer를 쓰되 semantic compiler를 호출하지 않는다. source 실패,
   UNSAT, 이미지/CNL hash 변조, arm 불일치, clip split 누출을 차단하는 tests를 추가했다.
3. 로컬 Qwen3-VL-2B의 내부 LoRA를 A100 GPU에서 네 arm 각각 1회 실제 업데이트했다.
   모든 arm의 초기 adapter hash가 같았으며, 이미지 토큰 64개와 유한 gradient,
   실제 가중치 변화 및 저장된 adapter를 확인했다.

| Arm | supervised tokens | 학습 parameters | 변화 tensor 수 | 업데이트 |
|---|---:|---:|---:|---:|
| L0 | 20 | 3,211,264 | 224 | 1 |
| L1 | 39 | 3,211,264 | 224 | 1 |
| L2 | 2,667 | 3,211,264 | 224 | 1 |
| L3 | 2,667 | 3,211,264 | 224 | 1 |

18개 새 integration test가 실제 로컬 processor를 포함해 통과했다. 인공 fixture의 image
tensor를 0으로 바꾸면 마지막-token logits가 바뀌었지만, 이는 tensor 경로 확인이며 장면
이해·올바른 시각 grounding·행동 효과 검증이 아니다. loss 값은 arm별 target이 달라 효용 비교에
사용하지 않았다. CNL 길이 차이 때문에 matched-compute 주장도 하지 않는다.

## 2. 증거와 실패 이력

owner-scoped restricted root:
`artifacts/projects/guardsynth-coc/restricted/guardsynth-eblc-learning-001/`

- [source audit 002](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-eblc-learning-001/paper1-source-audit-2026-09-06-002/RESULT.json): inventory 완료, cohort NOT_EVALUATED
- [VLM smoke 003](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-eblc-learning-001/paper1-vlm-smoke-2026-09-06-003/RESULT.json): 네 arm update·weights·image input 확인; lowercase adapter 저장 재현
- VLM smoke 002도 성공한 불변 run으로 보존한다. PEFT가 arm 이름으로 생성한 대문자
  adapter 디렉터리 4개는 manifest 보존 목적의 exact-run naming 예외를 등록했고,
  003부터 producer의 adapter 이름을 소문자로 고쳤다. 구조 test가 예외를 이 4개에 한정한다.
- 각 run의 `RUN_MANIFEST.json`에 입력/model/code/output hash와 runtime 기록
- source audit 001은 원본 events=null 처리 누락으로 FAILED, VLM smoke 001은 로컬
  multimodal processor의 assistant content 형식 불일치로 FAILED. 수정 후 새 002 run으로
  재실행했으며 001을 덮어쓰거나 성공으로 바꾸지 않았다. 두 회귀 사례를 tests에 포함했다.

검증: 새 CNL/runner integration 18, 기존 source generator 12, platform CNL 10,
portal/projection 9, checkpoint naming 예외 범위 1로 targeted tests 50개가 통과했다.
새 문서 링크와 성공 run output hash를 검증했다. naming 검사는 기존 사용자 제출
`m16_geometry_candidate_review (1).csv`/`.json` 및 root `portal_exec.md` 3건만 남는다.
이 사용자 파일들은 변경하지 않았다. 기존 structure suite도 20/21 통과하며 같은 naming
3건을 보고하는 검사 1개만 실패한다.

GPU는 일반 agent sandbox에서 보이지 않았으나 승인된 read-only `nvidia-smi` 진단에서
호스트 GPU가 확인됐다. 사용 중인 GPU 0 대신 여유 GPU 1에서 실행했고 기존 process나
드라이버를 변경하지 않았다. 외부 다운로드/데이터 전송 없이 로컬 cache를 사용했다.

## 3. 아직 완료하지 않은 연구 결과

- M12-R01: model/data/family 개발 선택과 source inventory는 완료. main clause/source·
  action label 계약·cohort/N은 미동결이다.
- M14/M15: 소프트웨어 연결과 synthetic provider 실행 완료. 실제 32장면의 source-bound
  EBLC/CNL 생성, 실제 L1 provider, 전체 실패/coverage registry는 아직 미완료다.
- M16/M17: 독립 gold/CNL semantic audit, 새 표본의 source eligibility, 노출 없는 test,
  endpoint-specific power는 미완료다. 원본 CoC 연결 98/98은 source-complete 98/98이 아니다.
- M18/M20: **실제 장면 본 학습과 held-out 행동 효과는 NOT_EVALUATED**다. 이번 인공
  이미지 1개/seed 1개/1 update smoke를 실험·논문 gate 완료로 세지 않는다.

종전 strict formal60 eligible 1/60을 유지한다. 새 1차 cohort는 NOT_EVALUATED다.
source inventory에는 2026-09-05의 prior field status가 포함되며, 이를 이후 treaty authority
완료를 취소하는 현재 재판정으로 해석하지 않는다.

다음 작업은 선택 보행자 과제의 사용 clause·필요 source·관찰 가능한 행동 후보/gold 계약을
정하고, 그 기준으로 실제 32개 개발 표본을 재감사하는 것이다. 기계가 source 검증과 초안을
먼저 만들되 독립 인간 판정이나 부족한 metric geometry는 생성하지 않는다.

## 4. 2026-09-07 기존 검토 재사용 실행

위 다음 작업 중 기존 답변과 실제 장면 source의 연결을 실행했다.
[읽기 전용 대응표](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-review-constraint-alignment-001/reviewed-scene-alignment-2026-09-07-001/review_constraint_alignment.html),
[집계 결과](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-review-constraint-alignment-001/reviewed-scene-alignment-2026-09-07-001/RESULT.json),
[전체 JSON](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-review-constraint-alignment-001/reviewed-scene-alignment-2026-09-07-001/scene_constraint_alignment.json)에 보존한다.

- 60건 영상 설문의 JSON/CSV·packet·이미지 연결 및 이미지 실제 bytes hash를 재검증했다.
- 98건 geometry 제출의 JSON/CSV·candidate hash를 재검증하고, 선택 19건의 5-frame
  overlay/drivable/lane 파일 해시 285개를 확인했다. 기존 답변·제출 파일은 수정하지 않았다.
- 선택 32건 중 기존 영상 답변 19건을 재사용했다: 위험 보임 12, 위험 보이지 않음 4,
  상태 전이 2, 관측 불가 1. 나머지 13건도 분모에 남겼다.
- 관측 가능한 18건에 review-derived 조건부 초안을 만들었다. 이 가운데 위험 보이지
  않음 4건은 불필요한 활성화를 막는 검토 항목이며 진행 허가를 생성한 것이 아니다.
- CoC에 공사 인력·교통 통제 문맥이 포함된 10건을 구분했다. 이 lexical context flag는
  사람/CoC 오류 판정이 아니며 모든 사례를 보행자 STOP 의무로 단순화하지 않기 위한 것이다.

원본 설문은 사건 전후 시간창의 관찰이다. 이를 event t0의 hazard truth/freshness로 바꾸거나,
상태 전이 메모를 정량 release 조건으로 바꾸지 않았다. CASCADE의 actor/control 후보도
검토 대상과의 동일성이 확인된 단일 ID로 자동 선택하지 않았다. treaty baseline과
pixel geometry를 구체적인 행동 의무·metric 수치로 승격하지 않았다.

따라서 이번 run의 **실행 가능한 EBLC 0, SAT query 0, 검증된 CNL 0, 학습 export 0**이다.
18개 자연어 초안은 EBLC renderer 출력이 아니며 독립 모델 정확도 평가도 아니다.
기존 설문 재요청은 0건이다. 화면은 읽기 전용이고 이미지 확대 후 닫기/Esc로 복귀한다.

새 unit tests 15개와 실제 source 재사용을 포함한 runner tests 4개가 통과했다. 다음은
기존 관찰을 actor/semantic-zone 및 사건 시점 근거로 연결하고, 혼합 문맥을 구분해 실행
clause를 동결하는 작업이다. 이미 완료한 human 관찰을 취소하거나 전량 반복하지 않는다.

## 5. 2026-09-07 사건 시점 source binding 실행

[사건별 보고서](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-review-constraint-alignment-001/event-source-binding-2026-09-07-002/REPORT_KO.md),
[집계 결과](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-review-constraint-alignment-001/event-source-binding-2026-09-07-002/RESULT.json),
[대상·시점·출처 JSON](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-review-constraint-alignment-001/event-source-binding-2026-09-07-002/event_source_bindings.json).

기존 run의 입력 해시를 다시 확인하고 18개 CASCADE 원본 파일을 해시·clip ID·event 시점으로
연결했다. 19개 사건/32개 개발 후보 분모와 기존 응답을 보존했다.

| 연결 결과 | 사건 수 / 19 |
|---|---:|
| 정확한 선언 interval에 직접 causal actor/control target 존재 | 9 |
| 직접 연결된 person ID가 하나 | 6 |
| visible interval의 person source 존재 | 18 |
| active 사람 신호 또는 신호등 상태 주석 존재 | 9 |
| ego/대상 공통 lane source | 0 |
| person keypoint의 정확한 t0 일치 | 0 |

단일 source ID 6건은 원본 주석의 관계 해석이 진행됐다는 뜻이다. 검토자가 같은 ID를
확인했다거나 충돌이 관측됐다는 뜻은 아니다. 기존 ±0.5초 audit과 target 집합이 다른 사건은
#47/#56이다. 새 감사는 원본 interval을 확장하지 않으며 선언된 시간축을 비교한다.
PhysicalAI/CASCADE 시계 정렬 자체를 독립 검증했다는 주장은 하지 않는다.

중요 사례: #54는 t0=3.0초에 Stop 행동·사람 Stop 신호·Red 주석이 있고, #56은
t0=7.841848초에 Red 주석과 `illegal_flag=true`인 DrivingInLane 행동이 있다.
CoC/기존 관찰은 보행자·flagger가 비켜나는 문맥이다. 이는 **출발 허가 전에 다른 의무와
시간 정렬을 확인해야 한다는 신호**이지, 사용자 답변이 틀렸거나 주석이 법적 정답이라는
판정은 아니다. 신호의 ego 적용 차로도 아직 독립 확인되지 않았다.

미래 행동과 과거/미래 keypoint는 offset과 context-only 역할을 기록했다. 이들을 현재 위치,
polygon, hazard truth, 학습 입력이나 gold로 승격하지 않았다. EBLC/SAT/CNL/학습 export는 0이다.
001 run은 보존하고 parent visibility interval 누락도 fail-closed 처리하는 002로 재실행했다.
실제 데이터 집계는 동일하며 새 unit 16개 + 실제 source/immutable runner 2개가 통과했다.

현재 병목은 **source 누락뿐 아니라 1차 행동 과제와 기존 수치 정지거리 backend 사이의
불일치**다. `program.py`는 meter 기반 stop position/stopping distance, response time,
deceleration 등의 인터페이스를 요구한다. 관측만으로 이 값을 채울 수 없으므로 다음은
1차 qualitative 행동 제약 subset·source 전제·UNKNOWN·release/동시 의무·독립 action 계약의
설계/구현이다. 기존 설문을 다시 받는 것으로 대체하지 않는다. M12-R01 및 M16은 PARTIAL,
1차 cohort/효과는 NOT_EVALUATED, 종전 strict60 eligible 1/60은 그대로다.
