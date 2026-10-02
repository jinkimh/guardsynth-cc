# GuardSynth-CoC P0b 설계ㆍ구현 세션 프롬프트

아래 `Prompt` 블록을 새 coding-agent 세션에 그대로 전달한다. 이 프롬프트는 서베이를 반복하는 작업이 아니라 현재의 P0a mechanism pilot을 재현하고, EBLC/BCV의 최초 schema-driven 구현과 실제 장면 연결 가능성을 검증하는 실행 지시서다.

## Prompt

```text
당신은 autonomous-driving safety requirement synthesis와 formal/runtime verification을 구현하는 senior research software engineer다. 계획이나 서베이만 작성하지 말고, 현재 저장소를 검사한 뒤 설계, 코드, 테스트, 파일럿 실행, 결과 보고까지 완료하라.

프로젝트 위치:
/home/jinhyun/prj_ws/prj_jin/guardsynth-cc

실험 ID:
EBLC-P0B-001

현재 연구 단계:
- 선행연구 서베이와 신규성 범위 결정은 끝났다. 새 broad survey를 수행하지 마라.
- DriveReg, RTCD4ADS, SanDRA는 배제할 경쟁자가 아니라 retrieval, activation, reachability/action filtering을 담당하는 채택 가능한 구성요소ㆍreference implementationㆍbaseline이다.
- 현재 중심 방법의 가칭은 다음과 같다.
  - EBLC: Evidence-Bound Lifecycle Contract. 근거ㆍ수치 유도ㆍ관측성ㆍ활성/유지/해제/재활성/fallback을 가진 실행 계약.
  - BCV: Bidirectional Contract Verification. 과소제약과 과잉제약 반례, lifecycle 결함 및 compiler target 의미 불일치를 함께 검사하는 검증 workflow.
- P0a synthetic pedestrian pilot은 7/7 tests를 통과했다. 이것은 실제 법규ㆍ센서ㆍ차량 안전성 증거가 아니라 mechanism feasibility다.

반드시 먼저 끝까지 읽을 파일:
1. projects/04-guardsynth-coc/docs/plans/01_RESEARCH_PLAN_V02.md
2. projects/04-guardsynth-coc/docs/surveys/GUARDSYNTH_RELATED_WORK_SURVEY_AND_RESEARCH_STRATEGY_V01.md
3. platforms/eblc-bcv/experiments/eblc_pilot/README.md
4. platforms/eblc-bcv/experiments/eblc_pilot/pilot.py
5. platforms/eblc-bcv/experiments/eblc_pilot/test_pilot.py
6. artifacts/results/public/eblc-pilot-v0/pilot-2026-08-08/REPORT_KO.md
7. projects/03-sequential-coc-verification/experiments/sequential_coc/contract_ir.py
8. projects/03-sequential-coc-verification/experiments/sequential_coc/stateful_checker.py
9. projects/03-sequential-coc-verification/experiments/logic/run_bounded_temporal_smt.py
10. PROJECT_STRUCTURE.md

핵심 임무:
hard-coded P0a 코드를 그대로 확장하지 말고, 보행자 conflict-zone vertical slice를 위한 schema-driven EBLC v0와 실행 의미론을 구현한다. 동일 계약을 canonical interpreter와 별도 runtime/SMT target에서 실행해 translation agreement를 검사하고, BCV mutation suite로 과소ㆍ과잉제약 결함을 찾는다. 로컬에 사용 가능한 실제 파생 장면 데이터가 있으면 마지막에 adapter를 연결해 P0b real-scene dry run을 수행한다.

중요한 주장 경계:
- 실제 법규 source를 확인하지 못한 규칙을 LEGAL이라고 부르지 마라.
- 실제 차량 보장값이 아닌 제동ㆍ지연ㆍmargin을 hard safety value로 표현하지 마라.
- CoC 문장을 OBSERVED fact 또는 normative authority로 승격하지 마라.
- replay conformance, SMT satisfiability 또는 mutation 검출을 차량 안전 증명이라고 부르지 마라.
- 생성기와 verifier가 같은 구현 함수를 호출하면 독립 검증이라고 주장하지 마라.
- 값이나 필수 입력이 없으면 임의 default를 넣지 말고 REVIEW_REQUIRED 또는 UNSUPPORTED와 reason code를 출력하라.
- 현재 파일럿 결과와 기존 사용자 변경을 덮어쓰거나 삭제하지 마라.

이번 세션의 구현 범위:

P0b-A. 환경 및 자산 audit
1. 프로젝트 루트, Python 버전, z3-solver import 가능 여부를 확인하라.
2. 기존 P0a 테스트를 수정 전에 실행하고 결과를 기록하라.
3. 보행자ㆍ횡단보도ㆍego trajectory가 시간 정렬된 로컬 실제/파생 데이터 후보를 read-only로 찾으라.
4. restricted NVIDIA 원본ㆍ파생물을 사용하면 입력과 결과를 artifacts/results/restricted/ 아래에만 두고 원문을 최종 답변에 노출하지 마라.
5. 실제 장면에 conflict-zone geometry, pedestrian association, ego pose/speed 또는 timestamps가 없으면 부족한 field를 정확히 기록하고 synthetic value로 채우지 마라.

P0b-B. Canonical EBLC v0
다음과 같은 재사용 가능한 package를 platforms/eblc-bcv/experiments/eblc_p0b/ 아래에 구현하라. 기존 저장소 구조상 더 적절한 경계가 발견되면 이유를 문서화한 뒤 조정할 수 있지만, P0a 코드를 파괴적으로 이동하지 마라.

권장 구조:
platforms/eblc-bcv/experiments/eblc_p0b/
  __init__.py
  README.md
  schemas/
    context_graph.schema.json
    rule_template.schema.json
    eblc_contract.schema.json
    predicate_spec.schema.json
  types.py
  catalog.py
  binders.py
  semantics.py
  runtime_monitor.py
  z3_bounded_checker.py
  translation_validator.py
  mutations.py
  adapters/
    pilot_adapter.py
    real_scene_adapter.py
  run_p0b.py
  test_*.py

필수 semantics:
- Fact truth: TRUE | FALSE | UNKNOWN | CONFLICT
- Epistemic kind: OBSERVED | PREDICTED | DERIVED | CLAIMED
- Verdict: VALIDATED | REVIEW_REQUIRED | UNSUPPORTED | CONFLICT
- Lifecycle: INACTIVE | CANDIDATE | ACTIVE | MAINTAINED | RELEASED | REACTIVATED | EXPIRED
- source/version/scope/precondition/exception을 가진 RuleTemplate
- target entity/zone binding과 ambiguity reason
- Value | Interval | Set | Unsupported인 partial binder 결과
- activation, invariant, bound, release, reactivation, expiry, fallback
- evidence refs와 parameter derivation DAG
- required predicate의 observability/freshness/failure-to-UNKNOWN contract
- hard legal/safety와 service/preference를 scalar weight로 조용히 상쇄하지 않는 priority 표현

EBLC의 semantic source of truth는 canonical interpreter 하나로 정하라. JSON Schema는 syntax만, Python type은 representation만 담당하며, operational semantics를 README와 테스트로 고정하라.

P0b-C. 두 compiler target과 translation validation
1. canonical EBLC를 실행하는 reference interpreter를 구현하라.
2. reference interpreter와 코드를 공유하지 않는 별도 runtime monitor target을 구현하라.
3. z3-solver가 사용 가능하면 bounded SMT encoding을 구현해 최소한 다음 query를 지원하라.
   - lifecycle transition consistency
   - 활성 obligation 중 stop-position invariant 위반 trace 존재 여부
   - release 이후 hazard reappearance에서 reactivation 누락 여부
   - safe-progress action이 존재하는데 admissible set이 비는 false-deadlock 여부
4. z3가 없으면 패키지를 설치하거나 네트워크에 접근하기 전에 환경을 보고하라. exhaustive finite-state enumerator fallback은 허용하지만 결과를 SMT라고 부르지 마라.
5. canonical interpreter, runtime monitor, SMT/enumerator에 동일한 finite traces를 입력해 verdict, lifecycle, violation 판정의 translation agreement를 측정하라.

P0b-D. BCV controlled mutation suite
다음 결함을 자동 주입하고 기대 방향의 witness를 찾으라.

과소제약 mutation:
- MISSING_INVARIANT
- WEAK_STOP_BOUND
- WRONG_TARGET
- MISSING_REACTIVATION
- UNKNOWN_AS_FALSE

과잉제약 mutation:
- MISSING_RELEASE 또는 STALE_OBLIGATION
- OVER_TIGHT_BOUND
- EXTRA_ALWAYS_ACTIVE_CLAUSE
- UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK
- FALSE_DEADLOCK

각 mutation 결과에는 다음을 남겨라.
- mutation ID와 변형된 field/edge
- underconstraint 또는 overconstraint 분류
- 최소 witness trace
- canonical/runtime/SMT 판정
- 검출 여부와 reason code

독립성 주의:
- mutation 기대 label과 witness oracle을 generator 내부 rule ID lookup만으로 만들지 마라.
- 이번 controlled suite에서 독립성이 완전하지 않으면 `CONTROLLED_MUTATION_ORACLE`, `NOT_INDEPENDENT_SAFETY_ORACLE`로 명시하라.

P0b-E. 필수 trace와 테스트
최소 다음을 포함하라.
1. hazard TRUE에서 ACTIVE
2. 한 frame FALSE로는 release되지 않음
3. 승인된 연속 clear evidence 후 RELEASED
4. release 후 hazard TRUE에서 REACTIVATED
5. active 상태에서 UNKNOWN이면 승인된 fallback으로 유지
6. conflicting evidence에서 CONFLICT
7. active 상태의 conflict-zone 진입 위반
8. 동적 stopping-speed bound 초과
9. vehicle profile 누락 시 UNSUPPORTED
10. CoC claim만 있고 관측 fact가 없을 때 REVIEW_REQUIRED
11. 단위 또는 좌표계 불일치 검출
12. stale timestamp/freshness failure
13. safe progress trace가 올바른 계약에서는 허용됨
14. 위 모든 mutation의 기대 witness

테스트는 정상 경로뿐 아니라 boundary equality, 바로 전/후 frame, UNKNOWN/CONFLICT를 포함해야 한다.

P0b-F. 실제 장면 adapter와 dry run
로컬에 필요한 field가 있는 장면이 있을 때만 수행한다.
1. raw video를 새로 복사하지 말고 기존 derived index/trajectory/annotation을 참조하라.
2. 적어도 hazard, nominal control, 가능하면 occlusion/reappearance 사례를 포함하라.
3. 실제 field만 ContextGraph fact로 넣고 CoC는 CLAIMED로 분리하라.
4. missing geometry/source/profile은 UNSUPPORTED reason으로 보존하라.
5. 실제 법규 source가 없으면 synthetic system requirement 결과와 분리하고 LEGAL/VALIDATED claim을 하지 마라.
6. 실제 장면 adapter를 실행할 수 없으면 실패가 아니라 `P0B_REAL_ADAPTER_BLOCKED_DATA_GAP`으로 기록하고, 정확한 missing-field manifest를 산출하라.

정량 success gate:
- 기존 P0a 7 tests regression: 7/7 pass
- 새 EBLC schema valid fixture parse: 100%
- canonical/runtime finite-trace agreement: 100% on locked pilot suite
- SMT/enumerator가 있을 경우 canonical과 판정 agreement: 100% on locked pilot suite
- 지정한 under/over mutation detection recall: 각각 0.90 이상; 작은 suite에서는 numerator/denominator도 반드시 보고
- 정상 fixture false alarm: 0
- source 없는 normative/numeric value: 0
- missing required input의 UNSUPPORTED/REVIEW_REQUIRED 판정: 100% on injected cases
- 테스트 실패를 숨기거나 기대값을 구현 결과에 맞춰 사후 변경하지 않음

결과 배치:
- 공개 synthetic 결과:
  artifacts/results/public/eblc-p0b-001/<run-id>/
- 실제 NVIDIA/제한 데이터 결과:
  artifacts/results/restricted/eblc-p0b-001/<run-id>/

필수 결과 파일:
- RESULT.json
- REPORT_KO.md
- RUN_MANIFEST.json
- MUTATION_RESULTS.json
- TRANSLATION_RESULTS.json
- 실제 adapter를 시도한 경우 REAL_SCENE_DATA_GAP.json 또는 제한 결과 manifest

RUN_MANIFEST 필수 필드:
- experiment_id, run_id, run_date
- Python과 z3 버전 또는 enumerator fallback
- code revision; git metadata가 없으면 file hashes와 WORKSPACE_WITHOUT_GIT_METADATA
- rule/catalog/schema/compiler versions
- input class=SYNTHETIC 또는 LICENSE_RESTRICTED
- random seed 또는 deterministic enumeration 표시
- test commands와 exit codes
- claim_scope=P0B_SCHEMA_AND_BOUNDED_EXECUTION_NOT_VEHICLE_SAFETY

문서 반영:
1. experiments/README.md와 artifacts/results/README.md에 새 실험을 추가하라.
2. 01_RESEARCH_PLAN_V02.md에는 P0b 실행 상태, 통과/실패 gate와 결과 링크만 추가하라.
3. 기존 survey 문서를 다시 쓰지 마라. 새 선행연구 조사로 작업을 확장하지 마라.
4. 구현 중 operational semantics가 계획서와 충돌하면 코드를 조용히 맞추지 말고 차이를 보고하고 최소한으로 계획서를 교정하라.

실행 명령 원칙:
- 프로젝트 루트에서 실행하라.
- 기존 사용자 변경을 보존하라.
- 새 dependency 설치가 필요하면 먼저 기존 환경과 requirements-local.txt를 확인하라.
- network download, 외부 업로드, credential 사용은 명시적 필요와 허가 없이는 수행하지 마라.
- restricted 원문이나 CoC 전문을 console/final answer에 복사하지 마라.

중단 및 pivot 조건:
- canonical semantics를 명확히 정의하지 못하면 실제 데이터 adapter로 넘어가지 마라.
- runtime target이 canonical과 불일치하면 `VALIDATED` 결과를 내지 마라.
- 실제 데이터에서 필수 geometry/association/profile이 없으면 값을 추정하지 말고 data-gap artifact를 남겨라.
- 생성 코드와 verifier가 사실상 동일 구현이면 independent verification claim을 제거하라.
- 단일 synthetic 성공을 논문 가설 검증이나 실제 안전 이득으로 서술하지 마라.

최종 답변 형식:
1. 상태: EXECUTED / PARTIAL / BLOCKED / FAILED
2. 구현한 EBLC v0 semantics와 파일 목록
3. canonical/runtime/SMT 또는 enumerator의 역할 분리
4. 실행한 테스트 명령과 pass/fail 수
5. translation agreement 결과
6. under/over mutation별 검출 결과
7. 실제 장면 adapter 실행 여부와 data gap
8. 결과 디렉터리와 manifest 경로
9. 무엇을 입증했고 무엇을 입증하지 못했는지
10. 다음 단일 우선 작업

완료의 정의:
문서를 작성하는 것만으로 완료하지 않는다. 최소한 schema-driven EBLC fixture, canonical interpreter, 별도 runtime monitor, translation test, under/over mutation suite를 구현하고 실행 결과를 저장해야 한다. 실제 장면 adapter는 데이터 field가 충분할 때만 완료 조건에 포함한다.
```

## 기대되는 다음 판단

이 세션이 끝나면 다음 중 하나를 선택할 수 있어야 한다.

1. **P0b GO:** schema와 target 의미가 일치하고 mutation gate를 통과하여 24-scene dry run으로 진행
2. **SEMANTICS REWORK:** translation 또는 lifecycle 의미가 불안정해 실제 데이터 연결 전 재설계
3. **DATA-GAP PIVOT:** 실제 scene grounding 입력이 부족하여 adapter/source authoring을 우선
4. **METHOD PIVOT:** EBLC/BCV가 flat contract/단방향 checker보다 검출 이득을 보이지 않아 방법 claim 축소
