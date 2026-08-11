# GuardSynth-CoC 전체 마일스톤과 Todo 원장

- 문서 성격: 완료 이력과 미래 Todo를 함께 관리하는 living milestone ledger
- 기준 연구계획: [RESEARCH_PLAN_V1.md](RESEARCH_PLAN_V1.md)
- 현재 작업 결정: [PROJECT_EXECUTION_TRACKER.md](PROJECT_EXECUTION_TRACKER.md)
- 마지막 갱신일: 2026-08-10
- 현재 완료 마일스톤: `M00`~`M12`
- 현재 활성 마일스톤: `M13` (`BLOCKED`)
- 최종 목적: `CoC+scene+evidence → 제약 생성 → 검증·적용 → 효과 입증`

## 1. 상태와 사용 규칙

| 상태 | 의미 |
|---|---|
| `COMPLETE` | 아래 Todo와 종료 gate가 모두 충족되고 근거 artifact가 존재 |
| `READY_NEXT` | 선행조건이 충족된 다음 단일 마일스톤 |
| `QUEUED` | 순서는 정해졌지만 선행조건이 아직 충족되지 않음 |
| `ACTIVE` | 현재 구현·조사·실험 중 |
| `BLOCKED` | 외부 결정·입력·권한이 없어 진행 불가 |
| `PARTIAL` | 일부 산출물은 있으나 종료 gate 미통과 |
| `SUPERSEDED` | 후속 버전으로 대체됐으며 이력만 보존 |

체크박스는 완료 증거가 있을 때만 `[x]`로 변경한다. 구현이 존재한다는 사실과 연구 gate
통과를 분리하며, synthetic·bounded 결과를 실제 효과 증거로 사용하지 않는다. 이 문서는
전체 목록을 관리하고, 매 세션에서 실제로 수행할 하나의 작업은 실행 추적표가 지정한다.

## 2. 전체 마일스톤 요약

| ID | 마일스톤 | 계획 대응 | 상태 | 핵심 결과/다음 gate |
|---|---|---|---|---|
| M00 | 연구 문제·신규성·주장 경계 확정 | 연구계획/서베이 | `COMPLETE` | GuardSynth-CoC RQ와 EBLC/BCV 역할 확정 |
| M01 | P0a synthetic mechanism pilot | P0 선행 pilot | `COMPLETE` | lifecycle·fallback·mutation 7/7 |
| M02 | schema-driven EBLC P0b vertical slice | P0/P3 초기 | `COMPLETE` | canonical/runtime/finite trace와 mutation gate |
| M03 | 실제 Z3와 fail-closed robustness | E0/P3 | `COMPLETE` | Z3 5.0.0, robustness 13/13 |
| M04 | 고수준 EBLC→Core→SMT 의미 전환 | E0/P3 | `COMPLETE` | Core compiler와 generated-trace agreement |
| M05 | composition·priority·derivation·indexed binding | P3 | `COMPLETE` | 다중 계약/actor-zone bounded backend |
| M06 | EBLC v0.2 scoped release candidate | P3 release | `COMPLETE` | 명세·가이드·추적표·CNL projection |
| M07 | source-aware GuardSynth 생성기 | P2/P3 접점 | `COMPLETE` | structured synthetic input→EBLC→Z3 |
| M08 | source boundary·assurance·실제 입력 준비도 | P1 | `COMPLETE`(software) | fail-closed authoring; 실제 0/24 |
| M09 | label-light grounding interface | P1 보조 | `COMPLETE`(software) | 자동/최소검토/abstention; 실제 자동 0건 |
| M10 | 프로젝트 실행 관리 체계 | 프로젝트 관리 | `COMPLETE` | tracker·milestone·구조 검사 |
| M11 | 관할·ODD·slice·source hierarchy 결정 | P0 | `COMPLETE` | 대한민국 현행 법령과 structured-road ODD 고정 |
| M12 | 세 slice source-bearing catalog/E-1 audit | P0/E-1 | `COMPLETE` | 15 template, 3 slice, six-family coverage |
| M13 | 실제 24-scene source-complete dry run | P1 | `BLOCKED` | 24-slot plan 완료, 실제 source-complete 0/24 |
| M14 | CoC-conditioned constraint front-end | P2 | `QUEUED` | CoC+scene+evidence proposal pipeline |
| M15 | 비교 baseline과 protocol 동결 | P2/E2 | `QUEUED` | CoC/scene ablation과 선행시스템 baseline |
| M16 | 60-scene 전문가 formal pilot | P4/E1/E6 | `QUEUED` | agreement·시간·power-based main N |
| M17 | 생성 품질·BCV·일반화 intrinsic 평가 | E0–E3 | `QUEUED` | RQ1–RQ4/RQ6 gate 판단 |
| M18 | 독립 closed-loop 효과·진행성 평가 | P5/E4 | `QUEUED` | 위반 감소와 completion loss 검증 |
| M19 | Alpamayo CoC 실제 적용 | P6/E5 | `QUEUED` | external monitor/shield phase-gated 평가 |
| M20 | main GuardBench·전문가 효용·논문 | E6/main | `QUEUED` | power-based main과 submission package |

## 3. 의존 관계

```text
M00 연구 범위
 └─ M01~M06 실행·검증 backend
     └─ M07 GuardSynth structured generator
         └─ M08~M09 source/label-light boundary
             └─ M10 관리 체계
                 └─ M11 관할·source scope
                     └─ M12 audited catalog
                         └─ M13 24-scene dry run
                             ├─ M14 CoC-conditioned front-end
                             └─ M15 baselines
                                  └─ M16 60-scene expert pilot
                                      └─ M17 intrinsic evaluation
                                          └─ M18 independent outcome
                                              └─ M19 Alpamayo
                                                  └─ M20 main/paper
```

M12 catalog authoring과 M13 adapter field audit은 일부 병렬 준비할 수 있다. 하지만 M13 종료,
M14의 `VALIDATED` 생성, M16 pilot은 각각 앞 단계 source/gate를 건너뛸 수 없다.

## 4. 완료된 마일스톤

### M00. 연구 문제·신규성·주장 경계 확정

- 계획 대응: 연구계획 v1.2, 2026 전략 서베이
- 상태: `COMPLETE`

Todo:

- [x] CoC가 상황 단서이지 법규/관측 authority가 아님을 명시
- [x] EBLC를 evidence·binding·lifecycle을 가진 실행 계약으로 정의
- [x] BCV를 과소·과잉제약 및 translation 검증 workflow로 정의
- [x] DriveReg·RTCD4ADS·SanDRA를 구성요소/비교 기준으로 재정의
- [x] 24 dry-run → 60 pilot → power-based main 계획 수립
- [x] 실제 차량 안전성·법규 타당성에 대한 주장 경계 고정

종료 근거:

- [연구계획](RESEARCH_PLAN_V1.md)
- [전략 서베이](../../surveys/guard-synth-coc/CONTEXT_AWARE_GUARD_SYNTHESIS_SURVEY_AND_STRATEGY_V1.md)

완료 경계: 연구 방향과 사전 gate를 정한 것이며 연구 가설을 입증한 것은 아니다.

### M01. P0a synthetic mechanism pilot

- 계획 대응: P0 선행 feasibility
- 상태: `COMPLETE`

Todo:

- [x] synthetic pedestrian conflict-zone rule retrieval/binding 구현
- [x] `ACTIVE→MAINTAINED→RELEASED→REACTIVATED` 실행
- [x] 활성 중 zone-entry 위반 검출
- [x] `UNKNOWN` approved fallback과 missing-profile abstention
- [x] under/overconstraint mutation witness
- [x] P0a 7/7 회귀 결과 보존

종료 근거: [P0a report](../../../artifacts/results/public/eblc-pilot-v0/pilot-2026-08-08/REPORT_KO.md)

완료 경계: mechanism feasibility이며 실제 규칙·센서·차량 근거가 아니다.

### M02. Schema-driven EBLC P0b vertical slice

- 계획 대응: P0/P3 초기 vertical slice
- 상태: `COMPLETE`

Todo:

- [x] Truth/Epistemic/Verdict/Lifecycle 타입과 JSON Schema
- [x] canonical interpreter와 별도 runtime target
- [x] activation/invariant/bound/release/reactivation/fallback 실행
- [x] finite locked traces의 target agreement
- [x] underconstraint 5종과 overconstraint 5종 mutation 검출
- [x] missing input의 REVIEW/UNSUPPORTED 및 data-gap artifact

종료 근거: [P0b report](../../../artifacts/results/public/eblc-p0b-001/p0b-2026-08-08-v1/REPORT_KO.md)

완료 경계: 한 synthetic pedestrian slice의 bounded semantics다.

### M03. 실제 Z3와 fail-closed robustness

- 계획 대응: E0/P3 solver·robustness gate
- 상태: `COMPLETE`

Todo:

- [x] project-local Z3 5.0.0 고정
- [x] 실제 `z3.Solver` 제약 construction
- [x] lifecycle, invariant, reactivation, false-deadlock query
- [x] non-finite, empty trace, decreasing timestamp fail-closed
- [x] runtime parameter/schema coverage 고정
- [x] 13개 adversarial robustness probe 통과

종료 근거:

- [Z3 P0b report](../../../artifacts/results/public/eblc-p0b-001/p0b-z3-smt-2026-08-08-v4/REPORT_KO.md)
- [fail-closed report](../../../artifacts/results/public/eblc-p0b-001/p0b-fail-closed-2026-08-08-v1/REPORT_KO.md)
- [robustness report](../../../artifacts/results/public/eblc-robustness-audit-001/robustness-fail-closed-2026-08-08-v6/REPORT_KO.md)

완료 경계: bounded falsification/translation evidence이며 보편 안전 증명이 아니다.

### M04. 고수준 EBLC→Core→SMT 의미 전환

- 계획 대응: E0/P3 translation validation
- 상태: `COMPLETE`

Todo:

- [x] typed Core IR와 unit/frame/time checker
- [x] domain-neutral bounded SMT lowering과 SMT-LIB export
- [x] symbol table, source map, query manifest
- [x] lifecycle/freshness/verdict/violation/progress elaboration
- [x] generated 129 trace/266 frame canonical–Core-SMT agreement
- [x] 경계·UNKNOWN·CONFLICT scenario matrix와 float roundoff 결함 수정

종료 근거:

- [Core-SMT report](../../../artifacts/results/public/eblc-core-smt-001/core-smt-2026-08-08-v4/REPORT_KO.md)
- [conformance report](../../../artifacts/results/public/eblc-elaboration-conformance-001/elaboration-conformance-2026-08-08-v3/REPORT_KO.md)
- [scenario report](../../../artifacts/results/public/eblc-scenario-test-001/scenario-matrix-2026-08-08-v3/REPORT_KO.md)

완료 경계: compiler conformance이며 독립 safety oracle은 아니다.

### M05. Composition·priority·derivation·indexed binding

- 계획 대응: P3 composer/binder/multi-target
- 상태: `COMPLETE`

Todo:

- [x] non-scalar `HARD > SERVICE > PREFERENCE` composition
- [x] same-tier conflict, explicit override와 cycle fail-closed
- [x] typed arithmetic derivation DAG와 division definedness
- [x] program v0.2에 dynamic stopping-bound derivation 통합
- [x] bundle namespace와 다중 contract Core/Z3 전파
- [x] actor–zone indexed collection과 ambiguous binding abstention

종료 근거:

- [composition report](../../../artifacts/results/public/eblc-composition-compilation-001/composition-compilation-2026-08-09-v1/REPORT_KO.md)
- [typed derivation report](../../../artifacts/results/public/eblc-derivation-compilation-001/typed-derivation-2026-08-09-v1/REPORT_KO.md)
- [v0.2 derivation report](../../../artifacts/results/public/eblc-elaboration-conformance-001/elaboration-conformance-2026-08-09-v02-typed-derivation-v4/REPORT_KO.md)
- [indexed collection report](../../../artifacts/results/public/eblc-indexed-collection-001/indexed-collection-2026-08-09-v1/REPORT_KO.md)

완료 경계: bounded synthetic multi-contract/actor backend다.

### M06. EBLC v0.2 scoped release candidate

- 계획 대응: P3 language/tooling release
- 상태: `COMPLETE`

Todo:

- [x] EBLC v0.2 language specification
- [x] operational semantics와 representation/semantic authority 구분
- [x] deterministic controlled-natural-language projection
- [x] requirement traceability와 release notes
- [x] user guide와 공개 src/CLI 구조
- [x] release artifact와 regression gate

종료 근거:

- [release artifact](../../../artifacts/results/public/eblc-release-candidate-001/eblc-v0.2-rc1-2026-08-09/REPORT_KO.md)
- [language specification](../../specifications/eblc/EBLC_LANGUAGE_SPEC_V02.md)
- [release notes](../../releases/EBLC_RELEASE_NOTES_V02.md)

완료 경계: EBLC 전체 일반 언어가 아니라 scoped v0.2 RC다.

### M07. Source-aware GuardSynth structured generator

- 계획 대응: P2/P3 접점
- 상태: `COMPLETE`

Todo:

- [x] RuleTemplate/PredicateSpec/ContextGraph/VehicleProfile 입력 계약
- [x] CoC claim과 observed activation evidence 분리
- [x] source closure, freshness, binding, unit/frame 검사
- [x] source-complete 입력만 EBLC program/indexed collection 생성
- [x] claim-only/missing/ambiguous/conflict/unit mismatch abstention
- [x] synthetic 두 instance를 EBLC→Core→Z3까지 실행

종료 근거: [generator report](../../../artifacts/results/public/guardsynth-source-aware-generator-001/source-aware-generator-2026-08-09-v3/REPORT_KO.md)

완료 경계: structured synthetic generator이며 자연어 CoC parser/검색기는 아니다.

### M08. Source boundary·vehicle assurance·실제 입력 준비도

- 계획 대응: P1 source authoring
- 상태: `COMPLETE`(software), `DATA_GAP_PIVOT`(research)

Todo:

- [x] exact vehicle binding과 source-bearing assurance registry
- [x] association/geometry/transform/assurance fail-closed authoring
- [x] generator verdict 재검증과 provenance replacement
- [x] 24-slot readiness와 실제 execution-completed 상태 분리
- [x] 24-contract synthetic scaling/Z3 adversarial test
- [x] restricted-derived input을 식별자 없이 재감사
- [x] 실제 후보 5/24, partial 4, source-complete 0/24 기록

종료 근거:

- [terminal decision](../../reports/GUARDSYNTH_P0B_TERMINAL_DECISION_V1.md)
- [thorough test report](../../reports/GUARDSYNTH_SOURCE_BOUNDARY_THOROUGH_TEST_V1.md)
- [readiness artifact](../../../artifacts/results/public/guardsynth-real-scene-readiness-001/terminal-readiness-2026-08-09-v3/REPORT_KO.md)

완료 경계: source-boundary software 종료이며 24-scene 연구 gate는 미통과다.

### M09. Label-light grounding interface

- 계획 대응: P1 annotation-cost mitigation
- 상태: `COMPLETE`(software)

Todo:

- [x] calibrated confidence interval과 policy evidence schema
- [x] unique high-confidence 자동 확인
- [x] low-confidence/multi-candidate 최소 검토
- [x] missing transform/calibration의 UNSUPPORTED와 conflict 보존
- [x] 사람 확인이 claimed/stale hazard를 승격하지 못하도록 차단
- [x] review evidence를 최종 generation request까지 전달
- [x] synthetic scenario 8/8, 집중 15/15, 전체 187/187
- [x] restricted input은 식별자 없는 집계로만 평가

종료 근거:

- [design](../../designs/guard-synth-coc/GUARDSYNTH_LABEL_LIGHT_GROUNDING_V01.md)
- [execution report](../../../artifacts/results/public/guardsynth-label-light-grounding-001/label-light-2026-08-10-v3/REPORT_KO.md)

완료 경계: label-light workflow 구현이며 실제 association accuracy/절감률은 미측정이다.

### M10. 프로젝트 실행 관리 체계

- 계획 대응: cross-cutting project governance
- 상태: `COMPLETE`

Todo:

- [x] 연구계획과 상태 snapshot의 역할 분리
- [x] living execution tracker 생성
- [x] P0~P6 현재 위치와 critical path 고정
- [x] 단일 `READY_NEXT` 작업과 세션 갱신 규칙 정의
- [x] 전체 milestone/Todo 원장 생성
- [x] canonical 문서 링크와 구조 regression test

종료 근거:

- [execution tracker](PROJECT_EXECUTION_TRACKER.md)
- 이 milestone ledger
- [`test_project_layout.py`](../../../tests/structure/test_project_layout.py)

완료 경계: 관리 체계이며 연구/소프트웨어 결과가 아니다.

## 5. 현재 및 앞으로 수행할 마일스톤

### M11. 관할·ODD·vertical slice·source hierarchy 결정

- 계획 대응: P0 시작 결정
- 상태: `COMPLETE`
- work package: `GS-P0-SCOPE-001`
- 선행조건: M00, M10

Todo:

- [x] 최초 법규 관할과 적용 version/date 선택
- [x] 도시/근교 구조화 도로 ODD의 포함·제외 경계 정의
- [x] pedestrian/cyclist yield slice 범위 정의
- [x] stop sign/signal approach slice 범위 정의
- [x] following/cut-in longitudinal slice 범위 정의
- [x] 법규·검증된 시스템 요구사항·물리식·차량 assurance source hierarchy 정의
- [x] jurisdiction/source 미확인 시 `UNSUPPORTED` 정책 고정
- [x] public/restricted source 분리와 인용 정책 고정
- [x] `docs/decisions/`에 versioned scope decision 작성
- [x] M12 요구사항과 slice별 template 배분표 승인

종료 gate:

- source class별 허용/금지 주장이 문서화됨
- 세 slice의 필수 입력과 제외 예가 명확함
- 실제 법규/source를 조사할 범위가 한정됨

종료 근거:

- [대한민국 범위·source 정책 결정](../../decisions/GUARDSYNTH_KR_SCOPE_AND_SOURCE_POLICY_V1.md)
- [M12 source catalog 요구사항](../../requirements/guard-synth-coc/P0_SOURCE_CATALOG_REQUIREMENTS.md)

### M12. 세 deep slice source-bearing catalog와 E-1 audit

- 계획 대응: P0/E-1
- 상태: `COMPLETE`
- work package: `GS-P0-CATALOG-001`
- 선행조건: M11

Todo:

- [x] broad survey가 아닌 지정 관할의 authoritative source audit 수행
- [x] 세 slice에 최초 12–20개 RuleTemplate 배분
- [x] 여섯 행동군 broad applicability family coverage 표 작성
- [x] 각 template에 source/version/scope/precondition/exception 기록
- [x] PredicateSpec의 observability/freshness/failure-to-UNKNOWN 작성
- [x] target/zone binding 요구와 ambiguity reason 정의
- [x] numeric binder의 input/unit/frame/derivation DAG 작성
- [x] activation/invariant/bound/release/reactivation/fallback lifecycle 작성
- [x] hard/service/preference priority tier 지정
- [x] source가 없는 규범·수치가 0건인지 감사
- [x] 모든 fixture schema validation과 catalog lookup test 작성
- [x] E-1 feasibility audit artifact와 report 생성

종료 gate:

- 세 slice 최초 12개 이상 template의 필수 field 100%
- source 없는 normative/numeric value 0건
- six-family coverage 별도 확보
- 미달 시 model/front-end 개발을 중단하고 source authoring으로 pivot

종료 근거:

- [source catalog v0.1](../../../src/guard_synth/fixtures/source_catalog_kr_v0_1.json)
- [E-1 audit report](../../../artifacts/results/public/guardsynth-source-catalog-001/kr-source-catalog-2026-08-10-v2/REPORT_KO.md)

실행 결과: template 15개, slice 5/6/4, family 6/6, source 없는 규범·실행 수치 0건,
집중 10/10, maintained 202/202, P0a 7/7, 구조 10/10. 첫 v1 실행은 subprocess
`PYTHONPATH` 누락으로 실패했으며 결과를 보존하고 v2에서 수정했다.

### M13. 실제 24-scene source-complete dry run

- 계획 대응: P1
- 상태: `BLOCKED`
- work package: `GS-P1-DRYRUN-001`
- 선행조건: M12, 실제/파생 scene access

Todo:

- [x] 세 slice별 8개 장면 선정 slot과 필요한 event 입력 기준 고정
- [x] 위험/nominal, clear/occluded, release/reactivation을 층화
- [x] 기존 perception/tracker/map/trajectory output adapter의 현재 집계 재사용
- [x] 이미지·방법·예제·항목·자동 권고·JSON/CSV export를 갖춘 review kit 및 제한 이미지 10개 단일 HTML 준비
- [ ] label-light packet 변환과 작은 calibration/audit 표본 작성
- [ ] target–zone association evidence 작성 또는 review queue 보존
- [ ] rig/sensor→ego-path coordinate transform 검증
- [ ] timestamp, ego pose/speed, geometry와 source refs 정렬
- [ ] 실제 vehicle binding과 source-bearing assurance profile 확보
- [ ] 실제 법규/requirement source와 scene applicability 연결
- [ ] 24개 ContextGraph schema 및 source closure 검증
- [ ] source-complete scene만 GuardSynth→EBLC→Core/Z3 실행
- [x] missing field를 synthetic으로 채우지 않고 reason manifest 작성
- [ ] 자동확인율·검토율·수정률·검토시간·unsupported coverage 보고

종료 gate:

- 실제 source-complete 24/24 또는 미달 slot을 명시한 terminal decision
- binder recomputation ≥0.95
- injected `UNSUPPORTED` precision ≥0.90
- source 없는 normative/numeric value 0건

현재 blocker:

- 실제 source-complete scene 0/24
- 기존 실제 후보 5개 중 partial adapter 4개
- target-zone/lane association evidence, 검증된 coordinate transform, exact vehicle binding과
  source-bearing assurance profile 부재
- 따라서 실제 GuardSynth→EBLC→Core/Z3 scene execution 0건

준비도 근거:

- `artifacts/results/public/guardsynth-24-scene-dry-run-001/kr-dry-run-readiness-2026-08-10-v1/`
- `artifacts/results/public/guardsynth-scene-evidence-review-001/scene-evidence-review-2026-08-10-v5/`

### M14. CoC-conditioned constraint generation front-end

- 계획 대응: P2
- 상태: `QUEUED`
- work package: `GS-P2-FRONTEND-001`
- 선행조건: M12, M13 failure taxonomy

Todo:

- [ ] CoC intent/cause/action/uncertainty typed parser 구현
- [ ] CoC claim과 observed scene fact를 구조적으로 분리
- [ ] scene object/conflict-zone/maneuver semantic parser 구현
- [ ] CoC+scene evidence retrieval query 생성
- [ ] graph/BM25/dense candidate retrieval interface 구현
- [ ] jurisdiction/version/ODD/maneuver hard filter 구현
- [ ] four-valued applicability/precondition/exception evaluator 구현
- [ ] entity/zone partial binding과 ambiguity handling 구현
- [ ] deterministic numeric parameter binder 구현
- [ ] GuardSynth request/EBLC generation으로 연결
- [ ] missing evidence는 REVIEW/UNSUPPORTED로 abstain
- [ ] paraphrase/shuffle/hazard-removal metamorphic tests 작성

종료 gate:

- 24-scene structured input에서 deterministic/reproducible proposal bundle 생성
- CoC claim이 legal/observed authority로 승격된 사례 0건
- schema parse ≥0.99와 compiler success ≥0.98 목표의 pilot 측정 가능

### M15. 비교 baseline과 평가 protocol 동결

- 계획 대응: P2/E2
- 상태: `QUEUED`
- work package: `GS-P2-BASELINES-001`
- 선행조건: M14 input/output protocol

Todo:

- [ ] no-guard와 human-template 기준선
- [ ] CoC-only와 scene-only ablation
- [ ] free-form LLM guard generation
- [ ] flat template/SEBGI와 naive composition
- [ ] physics-only deterministic binder
- [ ] DriveReg-style retrieval adapter
- [ ] RTCD-style applicability/activation adapter
- [ ] SanDRA-like reachability/action filtering adapter
- [ ] 동일 source budget, scene split, output schema와 evaluation budget 고정
- [ ] B0–B8/B13 ID와 version manifest 작성
- [ ] generator와 evaluation oracle의 코드/규칙 비공유 검사

종료 gate:

- 모든 방법이 동일 locked input에서 실행 가능
- 실패/abstention을 숨기지 않는 공통 metric contract
- 실험 시작 후 baseline 기대값/분할 변경 금지

### M16. 60-scene 전문가 formal pilot

- 계획 대응: P4/E1/E6
- 상태: `QUEUED`
- work package: `GS-P4-PILOT-001`
- 선행조건: M13, M14, M15

Todo:

- [ ] 60장면 층화 sampling과 leakage-free split
- [ ] 가드 type/target/operator/range/source/lifecycle annotation protocol
- [ ] 최소 확인 UI와 complete authoring UI 비교
- [ ] reviewer training/calibration session
- [ ] 복수 전문가 독립 annotation
- [ ] disagreement adjudication과 허용 가드 집합 작성
- [ ] applicability α와 field별 agreement 계산
- [ ] review correction rate와 장면당 작업시간 측정
- [ ] 최대 두 차례 guideline revision 이력 보존
- [ ] cluster effect와 variance로 main N power analysis

종료 gate:

- applicability α ≥0.67, 미달 시 ontology/scope 축소
- 전문가 작업시간·adjudication 예산 실측
- power-based main N/split 결정

### M17. 생성 품질·BCV·일반화 intrinsic 평가

- 계획 대응: E0–E3
- 상태: `QUEUED`
- work package: `GS-E2-INTRINSIC-001`
- 선행조건: M16 gold/pilot

Todo:

- [ ] applicability macro-F1과 type/target/operator 정확도
- [ ] unit/frame, numeric-range와 provenance 정확도
- [ ] `VALIDATED` precision과 coverage를 분리 보고
- [ ] hallucinated source/numeric value 측정
- [ ] under/over/lifecycle/translation mutation recall
- [ ] flat contract 대비 EBLC semantic/lifecycle/false-deadlock 비교
- [ ] CoC+scene 대 CoC-only/scene-only 비교
- [ ] shuffled-CoC와 paraphrase ablation
- [ ] OOD maneuver/source/dataset generalization
- [ ] confidence interval, paired test와 failure taxonomy
- [ ] 모든 사전 Go/No-Go gate 판정

종료 gate:

- CoC+scene가 scene-only보다 ≥3%p 개선하지 못하면 CoC-centric claim 제거
- strongest applicability baseline보다 macro-F1 5%p 개선 및 CI gate
- `VALIDATED` precision ≥0.90
- BCV mutation recall ≥0.90, translation agreement ≥0.99

### M18. 독립 closed-loop 효과와 진행성 평가

- 계획 대응: P5/E4
- 상태: `QUEUED`
- work package: `GS-P5-OUTCOME-001`
- 선행조건: M17과 evaluator independence gate

Todo:

- [ ] generator와 코드·규칙을 공유하지 않는 evaluator 구현
- [ ] 기록 replay와 독립 physics oracle
- [ ] counterfactual perturbation/hard negative 생성
- [ ] 경량 closed-loop simulator 또는 MetaDrive/CARLA 핵심 scene 재현
- [ ] no-guard/free-form/baseline/GuardSynth 동일 조건 비교
- [ ] rule/safety violation, collision proxy와 TTC 계열 지표
- [ ] goal completion, deadlock, unnecessary stop, false rejection 측정
- [ ] lifecycle reappearance/occlusion stress
- [ ] paired/clustered confidence interval과 residual risk 보고

종료 gate:

- no-guard 대비 violation 상대 감소 ≥30% 목표
- free-form 대비 상대 감소 ≥15% 목표
- goal completion 절대 손실 ≤5%p
- 독립 evaluator 미확보 시 full outcome claim NO-GO

### M19. Alpamayo CoC 실제 적용

- 계획 대응: P6/E5
- 상태: `QUEUED`
- work package: `GS-P6-ALPAMAYO-001`
- 선행조건: M17, M18 phase gate

Todo:

- [ ] restricted Alpamayo CoC/trajectory adapter version 고정
- [ ] CoC claim과 실제 scene evidence 분리
- [ ] generated constraint를 external monitor/shield input으로 연결
- [ ] prompt-only, structured input, verifier, reranker, shield 조건 분리
- [ ] nominal/hazard/occlusion/reappearance case 실행
- [ ] no-guard와 matched control 비교
- [ ] restricted 상세와 public aggregate 분리
- [ ] prompt semantics가 약할 때 external verifier/shield 결과만 보고

종료 gate:

- phase-gated E5 report
- 실제 source 누락을 추정으로 채운 사례 0건
- 효과가 없으면 Alpamayo-centric claim 축소

### M20. Main GuardBench·전문가 효용·논문

- 계획 대응: main study/E6/산출물
- 상태: `QUEUED`
- work package: `GS-MAIN-PAPER-001`
- 선행조건: M16 power analysis, M17–M19 phase gate

Todo:

- [ ] power-based main GuardBench 장면 수와 split 동결
- [ ] main annotation/adjudication 실행
- [ ] 모든 baseline과 GuardSynth locked evaluation
- [ ] 전문가 작성·검토 시간과 승인율 평가
- [ ] missing/unsupported/conflict와 부정 결과 포함
- [ ] preregistered 통계와 sensitivity analysis
- [ ] 데이터/model/prompt/KB/schema/evaluator version manifest
- [ ] 공개 코드·synthetic fixture·비식별 통계 artifact
- [ ] 제한 데이터 license/confidentiality 감사
- [ ] failure taxonomy와 residual risk 작성
- [ ] 주장 수준에 맞는 target venue 결정
- [ ] 논문 본문·부록·재현 패키지 완성

종료 gate:

- 최소/목표/확장 성공 수준 중 실제 달성 수준 명시
- 전문가 중대한 수정 없는 승인 ≥70% 목표
- 작성/검토 시간 감소 ≥30% 목표
- 결과가 gate 미달이어도 기대값을 바꾸지 않고 축소된 결론으로 보고

## 6. 매 마일스톤 갱신 절차

마일스톤을 시작할 때:

1. 실행 추적표에서 해당 work package를 `ACTIVE`로 변경한다.
2. 이 문서의 선행조건과 미완료 Todo를 확인한다.
3. 요구사항/설계와 locked test/gate를 먼저 작성한다.

마일스톤을 종료할 때:

1. Todo마다 코드·문서·artifact 근거를 확인해 `[x]`로 변경한다.
2. 종료 gate의 분자/분모, 실패와 주장 범위를 기록한다.
3. 대표 결과 링크를 “종료 근거”에 추가한다.
4. 모든 gate가 충족됐을 때만 `COMPLETE`로 바꾼다.
5. 실행 추적표에서 다음 하나만 `READY_NEXT`로 지정한다.
6. 문서 링크 검사와 public manifest를 갱신한다.

연구계획의 RQ, 목표 수치나 Go/No-Go 기준이 바뀌면 이 문서만 조용히 수정하지 않는다.
`RESEARCH_PLAN_V1.md`의 새 버전과 변경 이유를 먼저 기록한 뒤 마일스톤을 동기화한다.
