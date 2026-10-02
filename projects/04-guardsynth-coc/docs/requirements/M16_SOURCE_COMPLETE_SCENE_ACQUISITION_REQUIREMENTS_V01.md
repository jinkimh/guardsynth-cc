# M16 1차 source 준비와 2차 strict-cohort 요구사항

- 상태: `PARTIAL`; 1차 새 적격성 `NOT_EVALUATED`, 기존 strict60 1/60
- 권위: [1차/2차 분리 결정](../decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)
- 현재 단일 작업: [M12 사용 task/source 동결](P0_SOURCE_CATALOG_REQUIREMENTS.md)
- 1차 검토: [M16 독립 검토 계약](M16_EXPERT_PILOT_REQUIREMENTS.md)

고정24→60/18-cell/전체8-field 재획득을 1차 선행조건으로 사용하지 않는다. 사용 task의
실제 claim에 필요한 source만 감사하고 geometry/calibration이 필요한 정량 clause에는 그
근거를 계속 요구한다. source가 없는 숫자·관할·track을 합성해 실제 자료로 승격하지 않는다.

기존 source/영상60/geometry98 결과는 수정하지 않고 재사용한다. source eligibility와 생성기
execution readiness를 분리하며 실패를 평가 분모에서 제거하지 않는다. 현재 strict validator의
행동은 계획 변경으로 바뀌지 않으며 새 1차 protocol·tests·manifest를 구현한 뒤 새 적격성을 산정한다.
아래 acquisition 수치와 Prompt는 2차/이력이고 새 세션 실행 프롬프트로 사용하지 않는다.

## 이전 상세 요구사항 (2차/구현 이력)

<details>
<summary>기존 완료 근거와 확장 protocol 보기</summary>

아래 현재/필수/선행조건 표현은 당시 범위다. 1차 적용은 위 v2.3 계약이 대체한다.

### 이전 M16 source-complete 장면 확보·적격성 확장 요구사항

- 문서 역할: M16 acquisition 하위 work package 요구사항과 새 세션 실행 프롬프트
- 상위 연구계획: [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)
- 마일스톤 원장: [02_PROJECT_MILESTONES.md](../plans/02_PROJECT_MILESTONES.md)
- 현재 실행 기준: [03_PROJECT_EXECUTION_TRACKER.md](../plans/03_PROJECT_EXECUTION_TRACKER.md)
- 상위 요구사항: [M16_EXPERT_PILOT_REQUIREMENTS.md](M16_EXPERT_PILOT_REQUIREMENTS.md)
- work package: `GS-P4-PILOT-001`
- 이번 실행 slice: `M16_SOURCE_COMPLETE_SCENE_ACQUISITION`
- 현재 기준 상태: `M16_LOCAL_SOURCE_FRONTIER_AUDITED_EXTERNAL_SOURCES_REQUIRED`
  (1/60 eligible)
- 범위 결정: [GUARDSYNTH_MULTI_JURISDICTION_PILOT_SCOPE_DECISION_V01.md](../decisions/GUARDSYNTH_MULTI_JURISDICTION_PILOT_SCOPE_DECISION_V01.md)
- 2026-09-06 일관성 보완: [감사 R01–R06](../reports/MILESTONE_CONSISTENCY_AUDIT_REPORT_V01.md).
  현재 다음 작업은 M12-R01이며, 아래 과거 Prompt를 새 세션 실행 지시로 사용하지 않음

#### 이전 다음 태스크 판정

M14의 CoC-conditioned front-end와 M15의 baseline protocol은 완료됐다. M16의 per-scene
validator 재감사에서는 locked KR scope 기준 0/60이었고, 2026-08-14 연구 scope owner가
국가 제한 없는 multi-jurisdiction pilot을 승인했다. 새 정책 재실행 결과는 1/60이며,
annotation start gate는 source-complete 60/60과 모든 slice/outcome quota로 유지한다.
2026-09-06에는 이 결정을 구현 수준에서도 재확인하여 공용 catalog schema의 KR 고정과 generic
CLI의 암묵적 KR 기본값을 제거했다. catalog는 경로를 명시적으로 선택하며 각 catalog가 공식
source host를 선언한다. 국가 whitelist는 없다. 2026-09-06 이후 M16 연구 기준은 장면 국가의
UN 협약 당사국 상태와 slice별 공식 협약문을 결합하며, 국내법 준수 판정은 별도 범위로 제외한다.
세부 결정은 [M16 국제협약 연구 기준](../decisions/M16_INTERNATIONAL_TREATY_BASELINE_DECISION_V01.md)을 따른다.

승인된 annotation-first audit은 CASCADE annotation 2,066개를 확보하고 135 events를 시간 정렬해
98개 slice candidate, 37개 unsupported, 38개 multi-slice ambiguity로 분류했다. 주석만으로
final outcome은 하나도 확정하지 않았다. 승인된 sensor acquisition은 228 remote packages에서
shortlist member만 range-streaming하여 59 candidates×6 members=354 files, 1,088,704,611 bytes를
확보했다. 59/59가 네 time stream coverage를 충족했지만 field closure는 timestamps와 ego
pose/speed 2/8뿐이었다. 후속 calibration acquisition은 59 candidates×5 features=295 selected
rows, 2,431,139 bytes를 확보해 exact recorded-rig binding을 59/59로 닫았다. 그러나 online/offline
extrinsics가 전 후보에서 달라 verified transform은 0/59다. 이어 39-event attrition reserve를
22개 새 clip과 기존 asset 재사용 17 events로 구성하고 선택 sensor/calibration만 추가 확보했다.
현재 98 classified events 모두 temporal·5/5 calibration·recorded-rig evidence를 가진다. 초기
공식 데이터셋 카드·devkit·feature catalog 감사에서는 offline feature가 최적화되었다는 설명만
확인했지만, 2026-09-05 post-review 재감사에서 NVIDIA NCore의 고정 커밋이 PhysicalAI 변환에
offline egomotion·extrinsics를 요구하고 non-offline 변형을 지원하지 않는다는 규칙을 확인했다.
81개 materialized clip의 offline 입력과 405 calibration rows를 hash 재검증해 variant selection을
98/98 폐쇄했다. 이어 M16 review event timestamp를 scene t0로 고정하고 81개 offline extrinsics
assets·648 rows와 offline egomotion 보간 및 inverse closure를 검증해 verified transform도 98/98
폐쇄했다. 후속 CASCADE source 재감사는 approved human annotation 98개를 hash 검증하고 active
`because_of`/`action_target` SET으로 relevant actor/control 70/98, strict shared containment로
lane relation 1/98을 폐쇄했다. 다만 나머지 geometry·lifecycle이 없어 새 8/8·final
outcome은 여전히 0/0이다.
또한 공식 카드가 open map 부재를 명시한다. `M16-S07A` precheck는 98 events를 자동 검사해
60-record human review packet을 만들었지만, lane/zone geometry source는 98/98에 필요하므로 장면을
자동 승격하지 않았다. 이어 `M16-S07B1`은 60 events 각각에 이벤트 전후 5개 frame을 배치한
contact sheet 60개를 단일 restricted HTML에 내장하고 웹 포털 GuardSynth 검토 워크스페이스에
등록했다. `M16-S07B2`는 국가·법규·source ref·source-complete처럼 검토자가 영상만으로 답할 수
없는 문항을 제거하고 영상 관찰 두 문항만 남겼다. `M16-S07B3`에서 단일 검토자가 60/60을
완료했으며 JSON/CSV, packet candidate 순서, slice와 image hash가 모두 일치했다. 이 결과는
영상 관찰만 닫으며 curator source field나 eligible scene을 승격하지 않는다.
위 문단은 acquisition 진행 이력이다. geometry 품질 검토 98/98, 협약 binding 98/98,
기계 보조 source 화면 준비까지의 최신 상태는 STATUS와 실행 추적표를 따른다.
현재 후속 실행 계약은 다음과 같다.

1. M12-R01에서 현행 authority의 clause별 근거와 직접 규칙/일반 fallback/수치 source를
   재적격화한다. 협약 연결 98/98 자체를 취소하거나 국내법 준수로 확대하지 않는다.
2. M16-R01에서 source curation·독립 gold·assistance 검토를 분리한다. 기존 검토는 재사용하고
   pixel polygon 제출 완료와 metric rig geometry·연속 track/lifecycle source 검증을 별도 기록한다.
3. source eligibility와 execution readiness를 분리해 생성/translation 실패를 평가 분모에서
   제외하지 않는다. UNKNOWN/CONFLICT는 근거 있는 관측 상태이며 source packet 누락이 아니다.
4. M13–M15 재적격화와 M16-R01/R02, 60/60 quota·독립 reviewer calibration이 모두 충족된
   뒤에만 formal gold annotation으로 전환한다. 현재 source 화면은 그 formal gold가 아니다.

계획 보완은 구현 완료가 아니다. 다음 M16 구현에서 field 분리·독립 배정·두 α·import/export
회귀 tests와 실제 preflight를 실행한다. 현재 eligible 1/60은 재실행 전 종전 값이다.

#### 이전 역사적 acquisition Prompt (SUPERSEDED_EXECUTION_PROMPT)

아래 블록은 초기 확보 절차의 추적용 이력이다. 현재 active task는 위 계약과 실행 추적표이며
`curator pending 98/98` 등의 당시 수치를 현재 상태로 사용하지 않는다.

```text
당신은 autonomous-driving requirement synthesis, evidence provenance, dataset curation 및
formal/runtime verification을 구현하는 senior research software engineer다. 계획서만 다시
쓰지 말고 저장소를 검사한 뒤 TDD, 코드 구현, 제한 데이터 read-only 감사, 실제 실행,
artifact 생성, gate 판정과 프로젝트 관리 문서 갱신까지 완료하라.

프로젝트 루트:
/home/jinhyun/prj_ws/prj_jin/guardsynth-cc

프로젝트 owner:
guardsynth-coc

현재 마일스톤:
M16 / GS-P4-PILOT-001 / 60-scene expert formal pilot

이번 세션의 직접 임무:
materialized 81-clip sensor/calibration evidence와 98-event review queue를 사용해 curator가
source-linked lane/zone·conflict geometry와 남은 actor/control association을
폐쇄한다. 완료된
60/60 영상 관찰 결과를 입력으로 사용하되 reviewer 답변으로 source ref나 법규 적용을 대체하지
않고 60-slot preflight를 다시 실행한다.
60/60과 모든 quota를 충족하기 전에는 전문가 empirical annotation을 시작하지 않는다.

현재 알려진 상태:
- M14 front-end: scoped software COMPLETE
- M15 baseline protocol: COMPLETE
- M16 software preflight: COMPLETE
- 현재 multi-jurisdiction 결과: 1/60, shortfall 59
- 후보: source record 33개 → alias 제거 후 distinct event 23개
- 기존 네 장면 재감사: 8/8 closure 3개, cross-event conflict 1개; 새 정책에서 eligible 1개,
  jurisdiction `UNKNOWN` review 2개
- 승인 scope: 국가 제한 없음; legal rule은 같은 관할이어야 하며 verified system requirement는 승인·버전·적용 범위 필수
- licensed metadata screen: 135 candidate events/107 overlap clips, 106 sensor-eligible clips
- annotation screen: 2,066 files local; 98 classified, 37 unsupported, 38 multi-slice ambiguous
- sensor materialization: 81 unique clips, 486 selected members, 1,448,583,496 bytes
- sensor audit: classified-event temporal closure 98/98; new 8/8/outcome 0/0
- calibration: 405 selected feature rows, 3,337,630 bytes; event recorded rig 98/98
- association queue: actor/lane 24, actor/zone 19, control/lane 17, insufficient geometry 38
- verified transform/new 8/8/outcome: 98/0/0 across 98 classified events
- CASCADE structured relation: actor/control source SET 70/98, strict lane containment 1/98;
  새 source 없는 curator 화면 생성 0건
- human video observation: 단일 검토자 60/60, JSON/CSV·packet 순서·slice·image hash 검증 완료
- NVIDIA NCore pinned rule로 offline calibration variant selection: 98/98 source-linked
- acquisition session: `M16_SOURCE_GEOMETRY_CANDIDATES_GENERATED_CURATOR_REVIEW_REQUIRED`
- pinned TwinLiteNet+ large candidate 98/98, five-frame candidate 490/490, curator pending 98/98,
  source field update 0건
- 실제 차량 assurance와 실차 검증: M21로 이관
- 현재 단계의 차량 수치는 별도 SIMULATED_ASSURANCE binding만 허용
- EBLC/Core/Z3 backend 추가 확장은 이번 세션의 목적이 아님

반드시 먼저 끝까지 읽을 파일:
1. AGENTS.md
2. docs/architecture/PROJECT_STRUCTURE_CODEX.md
3. docs/architecture/FILE_NAMING_CODEX.md
4. PROJECT_REGISTRY.json
5. projects/04-guardsynth-coc/STATUS.md
6. projects/04-guardsynth-coc/PROJECT.yaml
7. projects/04-guardsynth-coc/docs/plans/01_RESEARCH_PLAN_V02.md
8. projects/04-guardsynth-coc/docs/plans/02_PROJECT_MILESTONES.md
9. projects/04-guardsynth-coc/docs/plans/03_PROJECT_EXECUTION_TRACKER.md
10. projects/04-guardsynth-coc/docs/requirements/M16_EXPERT_PILOT_REQUIREMENTS.md
11. projects/04-guardsynth-coc/docs/requirements/M13_SIMULATED_24_SCENE_REQUIREMENTS.md
12. projects/04-guardsynth-coc/docs/decisions/ACTUAL_VEHICLE_VALIDATION_DEFERRAL_DECISION_V01.md
13. projects/04-guardsynth-coc/src/guard_synth/expert_pilot_protocol.py
14. projects/04-guardsynth-coc/src/guard_synth/scene_source_closure.py
15. projects/04-guardsynth-coc/src/guard_synth/simulated_scene_inventory.py
16. projects/04-guardsynth-coc/src/guard_synth/sim24_batch.py
17. projects/04-guardsynth-coc/pipelines/cli/expert_pilot_preflight/run.py
18. projects/04-guardsynth-coc/pipelines/cli/simulated_scene_dry_run/README.md
19. projects/04-guardsynth-coc/tests/integration/test_expert_pilot_protocol.py
20. data/OWNERSHIP.json
21. artifacts/results/restricted/guardsynth-expert-pilot-preflight-001/m16-preflight-2026-08-12-v4/REPORT_KO.md
22. artifacts/results/restricted/guardsynth-sim24-batch-001/alpamayo-terminal-batch-2026-08-12-v1/REPORT_KO.md
23. artifacts/results/restricted/guardsynth-sim24-candidate-audit-001/alpamayo-candidate-inventory-2026-08-12-v2/REPORT_KO.md

핵심 연구 경계:
- CoC는 CLAIMED 상황 단서이지 관측 fact나 규범 authority가 아니다.
- 실제/파생 장면 field를 합성하거나 파일명·단일 이미지·CoC 문장만으로 채우지 마라.
- 실제 차량 assurance를 요구하거나 simulation 값을 실제 차량 보장값으로 표현하지 마라.
- source-complete eligibility, annotation agreement, GuardSynth 효과, 차량 안전성을 구분하라.
- Z3 SAT/UNSAT와 translation agreement를 안전 증명이라고 부르지 마라.
- 생성기와 같은 구현을 독립 expert 또는 safety oracle로 주장하지 마라.
- 제한 데이터의 원문, 실제 경로, 식별자, CoC 전문을 공개 artifact나 최종 답변에 노출하지 마라.
- 기존 immutable artifact를 수정하거나 덮어쓰지 마라.
- 기존 사용자 변경과 dirty worktree를 보존하고, 이 세션 변경만 분리해 보고하라.

이번 세션의 구현 범위:

M16-A. 환경·baseline·자산 audit
1. 프로젝트 루트, 현재 branch/worktree, Python, project-local Z3 경로를 기록한다.
2. 수정 전 GuardSynth, EBLC platform, P0a 및 structure 테스트를 실행해 실제 pass count와
   exit code를 기록한다.
3. 다음 로컬 제한 자료를 read-only로 감사한다.
   - data/restricted/nvidia_cascade
   - data/restricted/nvidia_physicalai
   - 기존 restricted derived scene/source/association/inventory artifact
4. 기존 13개 후보에 한정하지 말고, 시간 정렬된 ego state와 actor/traffic-control 근거를
   가진 모든 로컬 후보 event를 결정적으로 인덱싱한다.
5. raw video를 새로 복사하지 않는다. 기존 trajectory, annotation, timestamps, map/geometry,
   rig metadata 및 derived index를 source ref/hash로 참조한다.
6. 제한 원문과 식별자는 새 owner-scoped restricted artifact 안에서만 다룬다.

M16-B. 장면 적격성 계약과 TDD
현재 preflight는 M13 aggregate count를 신뢰한다. 이를 대체하거나 보강하여 각 장면 record로
eligibility와 quota를 계산하는 최소 구현을 만든다. 기존 모듈을 확장할 수 있으면 새 추상화를
만들지 마라.

장면별 필수 실제/파생 근거 8종:
1. timestamps
2. time-aligned ego pose와 speed
3. 관련 actor 또는 traffic-control state의 시간 연속 track/state
4. target-zone/lane association
5. conflict/stop/following geometry
6. 검증된 coordinate transform
7. 적용 가능한 rule source와 scope/precondition/exception 판정
8. recorded-rig binding

eligibility record 필수 정보:
- 비식별 scene/event hash와 중복 검사용 content/source hash
- slice: PEDESTRIAN_CYCLIST_YIELD | STOP_SIGNALS | FOLLOWING_CUT_IN
- outcome: NOMINAL | HAZARD_TRUE_ACTIVE | UNKNOWN | CONFLICT | RELEASE | REACTIVATION
- 8개 field 각각의 AVAILABLE_SOURCE_LINKED/REVIEW_REQUIRED/UNSUPPORTED/CONFLICT
- field별 evidence ref/hash, freshness, frame/unit, reason code
- jurisdiction, ODD, rule catalog/version과 scope compatibility
- recorded-rig binding과 별도 simulation vehicle binding
- source_complete, eligible, assigned_slot_id와 exclusion reason
- synthetic_required_field_fill=false

반드시 RED test를 먼저 추가한 뒤 구현할 적대 조건:
- 필수 field 하나라도 없으면 eligible=false
- source ref 없는 값은 eligible=false
- 동일 event/content의 중복 계산 금지
- 동일 장면을 이름만 바꾼 duplicate 금지
- 잘못된 unit/frame 또는 timestamp 역행 금지
- target/zone ambiguity 보존
- 관할·ODD·rule scope mismatch 금지
- aggregate count와 개별 record 수가 다르면 실패
- slice/outcome quota를 aggregate 숫자로 속일 수 없어야 함
- UNKNOWN은 source packet 누락이 아니라 승인된 observability/freshness 결과일 때만 outcome으로 인정
- CONFLICT는 두 source-bearing evidence의 명시적 불일치가 있어야 함
- RELEASE/REACTIVATION은 시간 연속 lifecycle witness가 있어야 함
- NOMINAL은 관련 장면과 safe-progress 근거가 있어야 하며 단순 hazard 미관측과 구분
- 장면 관할과 다른 국가·지역의 rule source를 조용히 혼합하지 않음
- public export에 raw identifier/path/CoC 전문이 포함되지 않음

중요한 scope audit:
P0의 대한민국 catalog는 첫 jurisdiction-specific catalog로 유지하지만 M16 표본에는 국가
제한을 두지 않는다. 기존 후보를 자동으로 유지하지 말고 다음 중 증거가 있는 판정을 내려라.
- JURISDICTION_SOURCE_COMPATIBLE
- EXCLUDED_JURISDICTION_OR_ODD_MISMATCH
- REVIEW_REQUIRED_JURISDICTION_EVIDENCE

국가가 달라도 배제하지 않되 legal rule은 각 장면 관할의 versioned 공식 source를 연결하고,
verified system requirement는 승인·버전·적용 범위를 연결한다. 실제 근거 없이 관할을 이미지·파일명·CoC 문장에서 확정하지 말고, 국가별 catalog가
없으면 source snapshot을 먼저 작성하거나 `REVIEW_REQUIRED_JURISDICTION_EVIDENCE`로 남긴다.

M16-C. 60-slot binding과 preflight 강화
1. 기존 60-slot manifest의 joint cell 크기(각 slice×outcome 3~4개)를 유지한다.
2. 60개의 서로 다른 eligible scene record를 실제 slot에 결정적으로 binding한다.
3. slice 주변 합계 20개씩, outcome 주변 합계 10개씩을 개별 binding에서 재계산한다.
4. slot 부족은 정확한 slice×outcome cell 단위로 보고한다.
5. 다음 조건을 모두 만족할 때만 annotation_start_allowed=true로 한다.
   - 60 distinct eligible scenes
   - 모든 joint/slice/outcome quota 충족
   - 8/8 source-linked evidence
   - scene-specific jurisdiction/ODD/rule scope 일치
   - raw/restricted/public 경계 검증
   - synthetic required-field fill 0
6. reviewer availability나 calibration이 실제로 완료되지 않았다면 scene gate가 통과해도
   empirical annotation을 실행하지 말고 READY_FOR_REVIEWER_CALIBRATION으로 종료한다.

M16-D. 로컬 장면 source closure 확대
1. 부족 셀 우선순위는 STOP_SIGNALS, FOLLOWING_CUT_IN, 그리고 hazard-active 외 outcome이다.
2. 후보마다 자동으로 확보 가능한 field와 인간/외부 source가 필요한 field를 구분한다.
3. 기존 source bundle, actor candidate, geometric association, rule applicability 코드를 재사용한다.
4. pedestrian 전용 가정을 다른 slice에 복사하지 않는다. 필요한 경우 slice-specific geometry와
   observability adapter를 최소 범위로 구현하고 단위/통합 테스트를 추가한다.
5. 규칙은 해당 관할의 versioned catalog와 공식 source snapshot에서만 연결한다. 법률 자문이나 최종 적용 판단을
   주장하지 않는다.
6. 로컬 자료에서 field를 닫을 수 없는 후보는 값을 추정하지 않고 acquisition work order에
   정확한 missing field, 필요한 source owner, 확보 방법과 검증 방법을 기록한다.
7. 네트워크 다운로드, 외부 업로드, credential 사용, 새 데이터 license 수락은 명시적 허가
   없이 수행하지 않는다.

M16-E. eligible scene의 GuardSynth→EBLC→Core→Z3 실행
1. 새로 eligible이 된 장면만 명시적 SIMULATED_ASSURANCE binding으로 실행한다.
2. recorded-rig binding과 simulation vehicle binding을 반드시 분리한다.
3. CoC claim을 activation evidence로 사용하지 않는다.
4. canonical/runtime/bounded Z3/Core/direct SMT replay agreement를 장면별로 기록한다.
5. [v2.2 보완] translation 불일치는 execution_ready=false로 기록하고 결함 재현 test를 추가한다.
   source-eligible 장면 자체를 제외하지 않고 실패를 평가 분모에 남긴다. 자동 실행 승격은 금지한다.
6. 실제 차량 안전성, 충돌 감소 또는 법규 준수 증거로 표현하지 않는다.

M16-F. 구현 위치
- project-specific domain code:
  projects/04-guardsynth-coc/src/guard_synth/
- M16 workflow CLI가 새로 필요할 때:
  projects/04-guardsynth-coc/pipelines/cli/m16_scene_acquisition/
- tests:
  projects/04-guardsynth-coc/tests/unit/
  projects/04-guardsynth-coc/tests/integration/
- reusable EBLC platform은 실제 interface 결함이 재현되지 않는 한 수정하지 않는다.
- legacy root src/, tests/, experiments/, cli/pipelines/guardsynth/에는 새 canonical logic을
  추가하지 않는다.

M16-G. 새 결과 배치
제한 상세:
artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/<run-id>/

공개 비식별 집계가 필요한 경우:
artifacts/projects/guardsynth-coc/public/guardsynth-m16-scene-acquisition-001/<run-id>/

기존 artifacts/results/ 아래 run은 immutable history이므로 수정하지 않는다.

제한 결과 필수 파일:
- RESULT.json
- RUN_MANIFEST.json
- REPORT_KO.md
- SCENE_ELIGIBILITY_MANIFEST.json
- SCENE_SOURCE_CLOSURE.json
- SLOT_BINDING_MANIFEST.json
- SCOPE_COMPATIBILITY_AUDIT.json
- ACQUISITION_GAP_MANIFEST.json
- LICENSED_CANDIDATE_SCREEN.json (licensed metadata screen을 수행한 경우)
- PILOT_PREFLIGHT.json
- TRANSLATION_RESULTS.json (eligible 실행이 있을 때)

RUN_MANIFEST 필수 정보:
- experiment_id, run_id, run_date
- code revision; dirty worktree면 hash와 WORKSPACE_WITH_UNCOMMITTED_CHANGES
- Python/Z3 version과 runtime path
- input class와 license boundary
- input hashes; 공개본에는 raw path/identifier 금지
- deterministic seed
- candidate/eligible/newly-eligible/deduplicated/excluded counts
- test commands, pass counts와 exit codes
- synthetic required-field fill count
- annotation_started=false (실제 reviewer 작업을 수행하지 않은 경우)
- claim_scope=M16_SCENE_ELIGIBILITY_AND_ACQUISITION_NOT_EXPERT_EFFECT_OR_VEHICLE_SAFETY

정량 success gate:
- eligibility validator adversarial cases: 100% 기대 판정
- eligible record의 8/8 source linkage: 100%
- eligible record의 scope compatibility: 100%
- distinct scene/content hash: 100%
- slot/slice/outcome counts derived from individual records: 100%
- missing input의 fail-closed 판정: 100%
- synthetic required-field fill: 0
- unsourced normative/numeric values: 0
- restricted identifier leakage to public output: 0
- eligible 실행의 canonical/runtime/Z3/Core/direct replay agreement: 100%
- 기존 maintained tests regression: 0 failures
- annotation_start_allowed는 60/60과 모든 gate가 실제 충족된 경우에만 true

세션 종료 판정:
- READY_FOR_REVIEWER_CALIBRATION:
  60 distinct source-complete scenes와 모든 quota/scope gate 통과. reviewer calibration은 다음
  인간 참여 단계로 넘기며 가짜 annotation을 생성하지 않는다.
- PARTIAL_DATA_ACQUISITION:
  적격 장면 수를 늘렸지만 60 미달. 새 장면과 정확한 cell별 shortfall을 보존한다.
- BLOCKED_DATA_SHORTFALL:
  로컬에서 추가 적격 장면을 만들 수 없음. 동일 감사를 반복하지 않도록 source owner,
  필요한 field, 획득 방법, 검증 방법이 있는 acquisition manifest를 남긴다.
- SEMANTICS_OR_SCOPE_REWORK:
  eligibility 의미나 jurisdiction/ODD scope가 불일치하여 장면을 신뢰성 있게 셀 수 없음.

60 미달은 software 실패로 숨기지 않는다. 반대로 manifest/validator만 구현했다고 M16을
COMPLETE로 표시하지 않는다. M16 완료에는 실제 reviewer calibration, 독립 annotation,
adjudication, agreement/timing과 power analysis가 추가로 필요하다.

문서 갱신:
1. 실행 결과에 따라 projects/04-guardsynth-coc/STATUS.md를 갱신한다.
2. 02_PROJECT_MILESTONES.md의 M16 단계 게이트 상태, Todo와 대표 근거를 사실대로 갱신한다.
3. 03_PROJECT_EXECUTION_TRACKER.md의 방금 수행한 단계 상태, M16 전체 완료 상태, eligible 수,
   blocker와 단일 다음 작업을 갱신한다.
4. projects/04-guardsynth-coc/results/RESULT_INDEX.md에 새 owner-scoped run을 등록한다.
5. 연구 scope/gate가 바뀌지 않았다면 01_RESEARCH_PLAN_V02.md를 수정하지 않는다.
6. scope 변경이 필요하면 기존 계획을 조용히 편집하지 말고 명시적 decision과 새 plan version이
   필요하다고 보고한다.

실행 연속성:
- 각 하위 단계 종료 시 단계 상태와 M16 전체 상태를 표시하되, 이를 승인 대기점으로 사용하지 않는다.
- 선행조건을 만족하는 다음 단계는 같은 실행 흐름에서 자동으로 계속한다.
- 사용자 검토가 연구 근거 자체인 human review/adjudication, scope·gate 변경, 새 외부 권한 또는
  파괴적 조치가 필요한 경우에만 중지한다.

필수 검증 명령 원칙:
- 수정 전후 동일한 baseline suite를 실행한다.
- 최소한 GuardSynth project tests, EBLC platform tests, P0a, structure/link, naming check를 실행한다.
- python3 cli/checks/file_naming.py를 반드시 실행한다.
- python3 -m cli.checks.build_manifest로 MANIFEST.sha256을 마지막에 갱신하고 check한다.
- git diff --check를 실행한다.
- 테스트 실패를 숨기거나 기대값을 구현 결과에 맞춰 사후 완화하지 않는다.

최종 답변 형식:
1. 방금 수행한 M16 단계 ID와 단계 상태: COMPLETE / PARTIAL / BLOCKED / FAILED
2. M16 전체 완료 상태와 eligible 수; 하위 단계 완료를 전체 완료로 표시하지 않음
3. 세션 판정: READY_FOR_REVIEWER_CALIBRATION / PARTIAL_DATA_ACQUISITION /
   BLOCKED_DATA_SHORTFALL / SEMANTICS_OR_SCOPE_REWORK / FAILED
4. 기존 4개 재감사 결과와 scope compatibility
5. 발견 후보·중복 제거·8/8 source-complete·새 eligible 수
6. slice×outcome slot coverage와 정확한 shortfall
7. 구현/수정 파일과 eligibility 의미
8. GuardSynth→EBLC→Core→Z3 실행 및 agreement 결과
9. 실행 테스트 명령과 pass/fail 수
10. restricted/public 결과 디렉터리
11. 무엇을 입증했고 무엇을 입증하지 못했는지
12. M16 완료까지 남은 단일 다음 작업

완료의 정의:
문서만 작성하는 것으로 끝내지 않는다. 최소한 per-scene eligibility manifest, fail-closed
validator, adversarial tests, 현재 장면 재감사, 로컬 후보 audit, slot binding/preflight 재실행과
immutable artifact를 완료해야 한다. 로컬 데이터가 부족해도 임의값을 만들지 말고 재실행 가능한
acquisition gap manifest로 세션을 닫는다.
```

#### 이전 기대되는 다음 판단

이 세션이 끝나면 다음 중 하나를 선택할 수 있어야 한다.

1. **REVIEWER CALIBRATION GO:** 60/60과 모든 quota/scope gate를 통과해 실제 전문가 준비로 이동
2. **CONTINUE TARGETED ACQUISITION:** 적격 장면은 늘었으나 특정 joint cell이 부족
3. **EXTERNAL DATA ACQUISITION:** 로컬 자료로는 더 닫을 수 없어 명시된 외부 source가 필요
4. **SCOPE REWORK:** 장면별 관할·authority compatibility 의미를 신뢰성 있게 판정할 수 없음

</details>
