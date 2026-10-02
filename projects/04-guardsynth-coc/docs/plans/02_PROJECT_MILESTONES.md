# GuardSynth-CoC 전체 마일스톤과 Todo 원장

- 문서 성격: 완료 이력과 미래 Todo를 함께 관리하는 living milestone ledger
- 기준 연구계획: [01_RESEARCH_PLAN_V02.md](01_RESEARCH_PLAN_V02.md)
- 현재 작업 결정: [03_PROJECT_EXECUTION_TRACKER.md](03_PROJECT_EXECUTION_TRACKER.md)
- EBLC 독립 연구: [Project 05 마일스톤](../../../05-eblc-language-verification/docs/plans/02_PROJECT_MILESTONES.md)
- 마지막 갱신일: 2026-09-29
- 역사적 완료 마일스톤: `M00`~`M15` (`M13` terminal shortfall, `M14`·`M15` scoped software/protocol)
- 현재 1차 경로: M12 → M14/M15 → M16 → M17 → M18 → M20
- 2차 이관: 전체 M13·M19·M21, M18 runtime 확장·M20 전문가 효용
- 현재 활성 마일스톤: `M18 통제 비교 COMPLETE`, `M20 DRAFT`; 기존 실제 도로 `M16 PARTIAL`/formal60 1/60은 별도 보존
- 1차 목적: `방법 소개 + EBLC 검증·CNL 변환 후 기존 제약 학습 효과 보존`

## 현행 v2.4 범위 (2026-09-29)

결과 열람 후 보고 개정: 모든 시드20%p 개선을 M18 결과 포함 또는 M20 작성의 gate로 사용하지 않는다.
[보고 방침](../decisions/PAPER1_METHOD_PRESERVATION_AND_LABELING_DECISION_V01.md)에 따라 모든 조건/시드의
효과 크기·무개선·저하·불확실성과 frozen 기준의 미충족 사실을 함께 보고한다.
실험 수행 완료와 과학적 가설 지지는 별도이며 원 RESULT 판정은 바꾸지 않는다.

실험 실행 마감: [전체 결과 및 감사](../../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-experiment-closure-2026-09-29-001/REPORT_KO.md).
확장18/18 fits(3,240 updates,17,280예측), 비용6/6 추가 fits(360 updates,6,480예측), 추가 지표 완료.
296개 고유 파일 해시·seed별 재집계·동일 예산·checkpoint 변화 점검 및 회귀 테스트49개 통과.
확장 NOT_SUPPORTED/비용 INCONCLUSIVE 원판정과 정확도-위반율 상충을 보존한다.
남은 현재 작업은 M20 원고/보충자료 통합이며, 기존 실제 도로 M16 전체 완료를 의미하지 않는다.

[사용자 결정](../decisions/PAPER1_METHOD_PRESERVATION_AND_LABELING_DECISION_V01.md)에 따라
통제 합성 시각 과제의 P0/P1/P2 실제 VLM 비교를 우선한다. 실제 영상은 기존 검토 기반 적용 사례다.
M16은 LLM 약지도 표본 감사/독립 평가, M17은 분할·의미 보존·동일 조건 데이터 구성,
M18은 기존 효과 보존 비교, M20은 방법·실제 결과·한계 원고다. 전수 사람 라벨/실제 영상
본 cohort·기존 네-arm/no-guard-at-test 조건은 이번 소개 논문의 일괄 blocker가 아니다.
아래 충돌하는 기존 상세 gate는 후속 범위다. 과거 미완료를 완료 처리하지 않는다.

현 실행 근거: M17 통제 temporal paired records2,016행·Core/SMT100질의 완료;
M18 실제 Qwen P0/P1/P2 3seeds·9adapters·648updates·2,592예측 및 고정 분석 완료.
표준·새seed 모두 P1/P2 위반0/안전완료1로 수준 보존 point criteria 충족. 새seed P0 .3160/.6840.
M20 `paper/main.tex` 실제 결과·CI·한계4쪽 및 PDF 완료. formal 비열등성/실도로 일반화 미입증.
6개 storyboard/24개 image-candidate 입력의 반복을 독립 새 환경으로 계산하지 않는다.

D1–D4 후속 완료: 기존9개 adapter로2,160행/1,476모델 호출, 새로운 학습0.
새 시간/경계/문구에서의 실패 및 영상 교체의 잘못된 대응을 `diversity-analysis-2026-09-29-001`에 보존.
제약 품질은 지원 주입 오류144탐지·정상24수용·공유 source 오류24미탐으로 별도 보고한다.
Core 행동 테스트2,376건과 독립 환경 불일치0; 전체 모델 행동의 옳음을 뜻하지 않는다.
M20 새6쪽 snapshot002 작성. 별도6조건×3seed 확장 학습과 비용 후속 실험은 위 감사로 완료 확인했다.
snapshot002에는 확장·비용·추가 지표가 아직 통합되지 않았으므로 원고 완료로 세지 않는다.

## 1. 상태와 사용 규칙

EBLC의 일반 표현력, multi-target 의미보존과 BCV mutation 성능은 Project 05가 독립적으로
평가한다. 이 원장의 EBLC 항목은 GuardSynth application dependency와 통합 gate만 관리한다.

| 상태 | 의미 |
|---|---|
| `COMPLETE` | 선언된 범위의 종료 gate와 근거 충족; software/protocol/terminal 한정자는 empirical 통과가 아님 |
| `READY_NEXT` | 선행조건이 충족된 다음 단일 마일스톤 |
| `QUEUED` | 순서는 정해졌지만 선행조건이 아직 충족되지 않음 |
| `ACTIVE` | 현재 구현·조사·실험 중 |
| `BLOCKED` | 외부 결정·입력·권한이 없어 진행 불가 |
| `PARTIAL` | 일부 산출물은 있으나 종료 gate 미통과 |
| `SUPERSEDED` | 후속 버전으로 대체됐으며 이력만 보존 |

체크박스는 완료 증거가 있을 때만 `[x]`로 변경한다. 구현이 존재한다는 사실과 연구 gate
통과를 분리하며, synthetic·bounded 결과를 실제 효과 증거로 사용하지 않는다. 이 문서는
전체 목록을 관리하고, 매 세션에서 실제로 수행할 하나의 작업은 실행 추적표가 지정한다.
각 실행 단계가 끝날 때는 해당 단계 상태와 전체 마일스톤 상태를 동시에 갱신한다. 하위 단계의
`COMPLETE`를 전체 마일스톤의 `COMPLETE`로 해석하지 않는다.
후속 감사로 추가된 `Mxx-Rxx`는 원래 완료 run을 고치지 않는 별도 재적격화 단계다. 과거 체크를
취소하거나 새 체크를 완료로 만들지 않고, 이 단계의 gate가 필요한 후속 실행을 막는다.
이전 감사 사실은 [일관성 보고서](../reports/MILESTONE_CONSISTENCY_AUDIT_REPORT_V01.md)에 보존한다.
현재 적용 범위는 [1차 논문/2차 개발 결정](../decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)이
대체한다. 전체 플랫폼 보완을 1차 논문의 선행조건으로 되돌리지 않는다.

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
| M11 | 관할·ODD·slice·source hierarchy 결정 | P0 | `COMPLETE`(initial scope) | 최초 KR 이력; 현행 multi-jurisdiction/treaty는 M12-R01 재감사 |
| M12 | 1차 task·사용 제약·source 동결 | PAPER1/C2 | `PARTIAL` | M12-R01: 1 dataset·1 model·1~2 행동군, 사용 clause만 감사 |
| M13 | 24-scene 전체 재검증 | PHASE2 | `QUEUED`(deferred phase2) | 과거 4/24 terminal 보존; 1차 선행조건 해제 |
| M14 | 제약 추출→EBLC 검증→자연어 생성 | PAPER1/C2·C3 | `PARTIAL` | 사용 subset과 CNL 의미·provenance 보존 |
| M15 | 효과 보존 비교·공정 예산 동결 | PAPER1/v2.4 | `PARTIAL` | P0 원본/P1 기존 제약/P2 EBLC→CNL, 기존 네-arm 후속 |
| M16 | 재사용·LLM 약지도 표본 감사·독립 참조 | PAPER1/v2.4 | `PARTIAL` | 기존19 ACTION/두 STOP 보존; 새 감사 정책 구현 필요 |
| M17 | 효과 보존 split·EBLC/CNL 품질 | PAPER1/v2.4 | `PARTIAL` | 통제 과제 동일 조건/미사용 평가 장면·의미 보존 감사 |
| M18 | 기존 제약 효과 보존 VLM 비교 | PAPER1/v2.4 | `COMPLETE (통제 template 비교 한정)` | 9fits/648updates/2,592예측; 수준 보존 point criteria 충족, formal 비열등성·새 환경 일반화 미입증 |
| M19 | Alpamayo·runtime 적용 | PHASE2 | `QUEUED`(deferred phase2) | M20 뒤 별도 적용 scope/resource gate |
| M20 | 방법 소개 논문·재현 패키지 | PAPER1/v2.4 | `PARTIAL (4쪽 결과 초안/PDF)` | 실제 비교·CI·적용 사례·한계 작성; 인용/논증/제출 형식 정리 잔여 |
| M21 | 실제 차량 심화 검증 | PHASE2 | `QUEUED`(deferred phase2) | M19·vehicle assurance·SIL/HIL·시험 승인 |

## 3. 1차 논문과 2차 개발의 실행 순서

1차 논문: **M12 → M14/M15 → M16 → M17 → M18 → M20**.
2차 개발: M20 이후 별도 scope/resource 결정 → 전체24/formal60·runtime 확장 → M19 → M21.
기존 M00–M11은 사용하는 platform/source 기반의 역사적 근거다. 새 구현을 모두 다시 만들지 않는다.

### 선행 보완 실행 원장

| 단계 | 작업 ID | 상태 | 1차 종료 근거 |
|---|---|---|---|
| M12-R01 | GS-P0-SOURCE-REQUAL-001 | `PARTIAL` | 개발 정책 완료; 실제 clause/source·action gold·새 cohort 미동결 |
| M14-R01 | GS-P2-FRONTEND-REQUAL-001 | `PARTIAL` | 조건부 action contract→Core/SMT/CNL 실행; 실제 추출/binding·독립 검토 미완료 |
| M15-R01 | GS-P2-BASELINE-REQUAL-001 | `QUEUED` | 실제 L0–L3 provider·SFT/budget 계약 |
| M16-R01 | GS-P4-REVIEW-INDEPENDENCE-001 | `QUEUED` | source curation와 독립 gold/CNL semantic audit 분리 |
| M16-R02 | GS-P4-PILOT-METRICS-001 | `QUEUED` | 선택 field 신뢰도·학습 endpoint power·분모/누출 계약 |
| M17-S01 | GS-P4-MAIN-DATA-001 | `PARTIAL` | 노출/group 원장 준비; main split/gold와 test 전 N 미동결 |
| M17-S02 | GS-E2-INTRINSIC-001 | `PARTIAL` | 조건부 subset 실행; 실제 정확도·CNL 독립 fidelity·대조 평가 미완료 |
| M18-S01–S05 | GS-P5-LEARNING-001 | `QUEUED` | 네 arm 실제 CNL 학습·독립 행동 평가 |
| M20-P01 | GS-MAIN-PAPER-001 | `QUEUED` | C1–C4 claim/evidence 및 원고·재현 패키지 |

M13-R01 전체24, 전수 B0–B13, M19-R01 및 M20-R01 효용은 PHASE2다.
source 검토는 준비할 수 있지만 독립 gold는 노출·배정·data gate 뒤에 수집한다.
구체적 표본/모델 선택은 M12-R01에서 근거로 정하며 scope 변경만으로 적격성을 계산하지 않는다.

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

- [연구계획](01_RESEARCH_PLAN_V02.md)
- [전략 서베이](../surveys/GUARDSYNTH_RELATED_WORK_SURVEY_AND_RESEARCH_STRATEGY_V01.md)

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

종료 근거: [P0a report](../../../../artifacts/results/public/eblc-pilot-v0/pilot-2026-08-08/REPORT_KO.md)

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

종료 근거: [P0b report](../../../../artifacts/results/public/eblc-p0b-001/p0b-2026-08-08-v1/REPORT_KO.md)

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

- [Z3 P0b report](../../../../artifacts/results/public/eblc-p0b-001/p0b-z3-smt-2026-08-08-v4/REPORT_KO.md)
- [fail-closed report](../../../../artifacts/results/public/eblc-p0b-001/p0b-fail-closed-2026-08-08-v1/REPORT_KO.md)
- [robustness report](../../../../artifacts/results/public/eblc-robustness-audit-001/robustness-fail-closed-2026-08-08-v6/REPORT_KO.md)

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

- [Core-SMT report](../../../../artifacts/results/public/eblc-core-smt-001/core-smt-2026-08-08-v4/REPORT_KO.md)
- [conformance report](../../../../artifacts/results/public/eblc-elaboration-conformance-001/elaboration-conformance-2026-08-08-v3/REPORT_KO.md)
- [scenario report](../../../../artifacts/results/public/eblc-scenario-test-001/scenario-matrix-2026-08-08-v3/REPORT_KO.md)

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

- [composition report](../../../../artifacts/results/public/eblc-composition-compilation-001/composition-compilation-2026-08-09-v1/REPORT_KO.md)
- [typed derivation report](../../../../artifacts/results/public/eblc-derivation-compilation-001/typed-derivation-2026-08-09-v1/REPORT_KO.md)
- [v0.2 derivation report](../../../../artifacts/results/public/eblc-elaboration-conformance-001/elaboration-conformance-2026-08-09-v02-typed-derivation-v4/REPORT_KO.md)
- [indexed collection report](../../../../artifacts/results/public/eblc-indexed-collection-001/indexed-collection-2026-08-09-v1/REPORT_KO.md)

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

- [release artifact](../../../../artifacts/results/public/eblc-release-candidate-001/eblc-v0.2-rc1-2026-08-09/REPORT_KO.md)
- [language specification](../../../../platforms/eblc-bcv/docs/specifications/EBLC_LANGUAGE_SPEC_V02.md)
- [release notes](../../../../platforms/eblc-bcv/docs/releases/EBLC_RELEASE_NOTES_V02.md)

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

종료 근거: [generator report](../../../../artifacts/results/public/guardsynth-source-aware-generator-001/source-aware-generator-2026-08-09-v3/REPORT_KO.md)

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

- [terminal decision](../reports/GUARDSYNTH_P0B_TERMINAL_DECISION_REPORT_V01.md)
- [thorough test report](../reports/GUARDSYNTH_SOURCE_BOUNDARY_THOROUGH_TEST_REPORT_V01.md)
- [readiness artifact](../../../../artifacts/results/public/guardsynth-real-scene-readiness-001/terminal-readiness-2026-08-09-v3/REPORT_KO.md)

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

- [design](../designs/GUARDSYNTH_LABEL_LIGHT_GROUNDING_DESIGN_V01.md)
- [execution report](../../../../artifacts/results/public/guardsynth-label-light-grounding-001/label-light-2026-08-10-v3/REPORT_KO.md)

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
- [x] 연구 개요·마일스톤·검토 화면을 통합한 loopback 제한 포털 구현
- [x] milestone ledger·execution tracker·현재 하위 요구사항을 page load에 재파싱하는
  fail-closed 포털 자동 연동

종료 근거:

- [execution tracker](03_PROJECT_EXECUTION_TRACKER.md)
- 이 milestone ledger
- [`test_project_layout.py`](../../../../tests/structure/test_project_layout.py)
- [`project_portal`](../../../../apps/research_portal/README.md)

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

- [대한민국 범위·source 정책 결정](../decisions/GUARDSYNTH_KR_SCOPE_AND_SOURCE_POLICY_DECISION_V01.md)
- [M12 source catalog 요구사항](../requirements/P0_SOURCE_CATALOG_REQUIREMENTS.md)

현행 해석: 위 근거는 최초 KR catalog의 완료 이력이다. 이후 승인된 multi-jurisdiction 및
국제협약 scope는 상위 연구계획을 따른다. M12-R01이 그 scope의 실행 clause 근거를 재감사한다.

### M12. 1차 task·제약·source 동결

- 상태: `PARTIAL`
- work package: `GS-P0-SOURCE-REQUAL-001` / M12-R01
- 선행조건: v2.3 scope 결정, 기존 catalog와 source 자산

Todo:

- [x] 개발 대상 선정: PhysicalAI 원본 CoC(+CASCADE 근거), Qwen3-VL-2B, 보행자·자전거 양보 32개 후보; main 적격성은 미판정
- [x] CoC intent/target 후보, scene 관측, rule/system 규범, 물리 수치의 출처 역할을 개발 설계에서 분리
- [x] 기존 관찰 19건의 원본 CASCADE 시점·대상·통제 근거 연결: 직접 대상 9건, 단일 person ID 6건; 미래 정보와 #54/#56의 동시 통제 분리
- [x] M12-R01-A: [개발 행동 계약 v0.1](../designs/PAPER1_ACTION_CONTRACT_DESIGN_V01.md)의 두 행동·UNKNOWN 정책·lifecycle·source/binder 역할 고정 (실제 source/action gold 동결 아님)
- [ ] 실제 사용하는 clause의 조건·예외·단위·해제·필요 관측량 및 source/binder matrix 동결
- [ ] 원본 CoC의 관측 가능한 실패와 nominal 성공을 함께 측정할 독립 과제/후보 정의
- [ ] 새 cohort eligibility/분모·sampling·split 계획과 N 산정용 dev 입력 정의

Gate: 필요한 source 없는 clause·숫자를 만들지 않음. 국가 whitelist를 만들지 않으며 선언한
benchmark source 범위 밖의 법적 적용·차량 안전을 주장하지 않음. 모든 catalog/관할의 완결은 불필요.
기존 KR 15-template 완료 이력은 아래 과거 상세에 보존한다.

개발 선택/98개 원본 CoC 정확 연결 근거:
[source·VLM 실행 보고서](../reports/PAPER1_CNL_LEARNING_READINESS_REPORT_V01.md).
선택 32개는 독립 gold/test cohort가 아니며 M12-R01의 clause/source/action 계약은 계속 PARTIAL이다.

### M13. 24-scene 전체 재검증 (2차)

- 상태: `QUEUED` (DEFERRED_PHASE2)
- work package: `GS-P1-SIM24-REQUAL-001`
- 선행조건: M20 이후 2차 scope/resource 승인

Todo:

- [ ] 세 slice 각 8개 실제/파생 장면의 geometry·binder·translation 확장 검증

과거 4/24·17계약 terminal 완료를 보존한다. 1차는 사용하는 파이프라인의 필요한 smoke/test만
M14/M17에서 수행하며 고정 24장면 확보를 기다리지 않는다.

### M14. 제약 추출·EBLC 검증·자연어 생성

- 상태: `PARTIAL`
- work package: `GS-P2-FRONTEND-REQUAL-001` / M14-R01
- 선행조건: M12-R01 사용 task/source

Todo:

- [ ] CoC+scene+source에서 선언된 subset의 제약 추출·binding 구현
- [x] M14-R01-A: 별도 버전 schema/parser→기존 Core 자동 변환, bounded SMT 및 UNKNOWN/해제/재활성화/nominal/mutation 검사
- [x] M14-R01-B: 공통 CNL renderer·field/source/hash 대응과 #18 조건부 실행; 25/25 질의, gate 제거 mutation SAT, source-verified/export 0
- [ ] M14-R01-C: 실제 사건 시점 target/zone/predicate·근거 수용 연결, 독립 action gold/CNL 검토를 통한 source-verified 예제 작성
- [x] M14-R01-C1: 32개 분모/기존 19개 관찰·geometry export 재감사, 시점/누출 검사, source 수용기와 #18 단일 확인 화면 구현 (14 tests)
- [x] M14-R01-C2: #18 사람 확인과 추가 설명 수용·실행 연결. 대상/영역·보행자 TRUE 유지, 주도로 UNKNOWN 보류; 실제 한 시점 Core/SMT 10/10 확인 (전체 source 수용 아님)
- [x] M14-R01-C3: 공통 CNL 생성·별도 독립 ACTION/CNL 패킷과 제출 검증 구현. 기존 CoC/답변/솔버를 ACTION 입력에서 배제; 준비 시점 실제 독립 응답은 0건
- [ ] M14-R01-C4 / M16: 미노출 ACTION 검토자 배정·실제 응답, 독립 CNL 의미 검토 및 판단 불가/불일치 처리. 개발 1건 검토를 main gold·신뢰도·학습 효과로 승격하지 않음
- [x] C4 ACTION 응답 수용: Jun Choi, DEFER_ENTRY, 독립성 선언/알려진 노출 검사 통과 (`scene18-action-intake-2026-09-08-001`). 당시 CNL 응답 0건; 신원·전문성 인증 및 main gold 승인 아님
- [x] M14-R01-C5: 실제 관측값+명세→현재 행동/재판단 조건의 한·영 CNL 생성. #18 12/12 질의·문장별 근거 대응·전용 장면 검토 화면·CoC 삽입 미리보기 구현; 10 tests. 공통 규칙 설명을 장면별 CNL로 간주하던 연결 공백 보완
- [ ] C5/M16 장면별 CNL 수용: 실제 생성 문장 4개에 대한 사람 검토·왜곡/누락 처리, 영문 의미 보존 및 독립성 확인. source/학습 export gate 유지
- [x] C5/M16 한글 장면 CNL 응답 수용: Jun Choi, 4/4 SUPPORTED, 독립성 선언/알려진 노출 검사 통과 (`scene18-cnl-intake-2026-09-08-001`). ACTION과 시점/영역/프레임 연결 및 문장 재생성·12/12 검사 완료 (`scene18-review-linkage-2026-09-08-001`); 동일 개발 사례 1건이며 신뢰도·영문 의미보존·main gold·학습 효과 아님
- [x] C5/M16 영문 의미 의견 수신: 사용자 지정 Jun Choi가 전체 영문의 의미 일치를 확인. 기존 SCENE_CNL 참여 여부 신고 재사용, 대화 원문·검토자 귀속·문서 hash 보존 (`scene18-training-preflight-2026-09-08-001`); 새로운 문장별 설문·신원 인증·일반 renderer 증명 아님
- [x] M14/M16 실제 입력 preflight: #18 실제 프레임·원본 CoC·독립 개발 ACTION·영문 CNL로 L0/L3 형식 미리보기 연결 및 로컬 processor 검사. 동일 prompt 2148 tokens, supervision 31/142 tokens; 이미지 tensor·assistant-only mask·무절단 확인. 단일 개발 프레임 검사이며 L1/L2·본 source/gold/split·공정 예산·학습 export는 미완료
- [x] #18 사람 답변 및 추가 확인 기록: 대상/영역·보행자 TRUE 유지, 주도로 UNKNOWN. 검토 완료 1건이며 C2 전체 source 수용/독립 검토 완료는 아님
- [ ] EBLC type/unit·모순·지원 bounded lifecycle 검증과 실패/abstention 경로 고정
- [ ] 검증한 EBLC를 기존 CNL renderer로 자연어 제약에 변환하고 field 의미보존 tests
- [x] source→EBLC→bounded 검증 verdict→CNL→학습 example의 hash/provenance·renderer 기록 구현 및 synthetic 연결 검증
- [x] CoC supervision에 CNL을 삽입하는 builder와 assistant-only loss mask 구현; 실제 local processor로 전 arm 회귀 검증
- [ ] 실제 장면 provider 적용과 독립 CNL 의미 검토, 본 실험용 loss/길이/예산 동결
- [x] 기존 검토 19개 실제 장면의 CoC/source/geometry 연결표 및 조건부 초안 18건 작성; 관측 불가 1건·미검토 13건 보존

2026-09-07 대응표의 초안은 review-derived proposal이다. EBLC 생성 0·SAT 실행 0·검증된
CNL 0이며, 정확한 target/zone·event-time predicate·operational/numeric source 연결 대기였다.
2026-09-08에는 수치 없는 개발 행동 subset의 실행 가능한 조건부 명세/CNL 1건을 추가했다.
이는 이전 run을 덮어쓰거나 source-verified 1건으로 올린 것이 아니다. 실제 추출·검토 gate는 유지한다.
근거: [실행 보고서](../reports/PAPER1_CNL_LEARNING_READINESS_REPORT_V01.md#6-2026-09-08-행동-계약의-실제-core실행).

Gate: CNL은 단순 부록 예시가 아니라 실제 학습 데이터다. 수치·부정·조건·대상·해제의 중대한
의미 변형은 수정/재검토 전 사용 금지. SAT를 장면의 진실성 또는 안전 보증으로 해석하지 않음.
일반 NLP/dense retrieval·모든 slice operational mapping은 2차다.

### M15. 네 학습 arm과 공정 비교

- 상태: `PARTIAL`
- work package: `GS-P2-BASELINE-REQUAL-001` / M15-R01
- 선행조건: M14 output/학습 계약

Todo:

- [ ] L0 원본 CoC, L1 직접 NL, L2 검증 생략 EBLC→CNL, L3 검증 EBLC→CNL provider 실행
- [ ] 같은 base data/action labels·모델 초기값·학습/tuning 예산·inference 조건 동결
- [ ] parse 오류/semantic 검증/선별·repair 및 coverage 차이를 분리 기록
- [ ] 텍스트 길이·학습 token·compute와 test 누출/label 재사용 통제
- [x] 네 arm software fixture 실행 및 동일 base input/action/초기 adapter hash 확인; L2 compiler bypass 테스트

위 software smoke의 L1은 synthetic-policy projection이고 실제 data provider가 아니다.
L0/L1/L2·L3 supervised tokens 20/39/2667 차이를 기록했으며 matched-compute 효과를 주장하지 않는다.

Gate: placeholder/미설정 provider는 실행 baseline이 아님. B0–B13 전수 재현은 1차 필수 아님.
v2.3 L2는 이전 flat/preference 조건과 다르므로 manifest version으로 구분한다.

### M16. 1차 source·독립 정답 검토

- 상태: `PARTIAL`
- work package: `GS-P4-PILOT-001`, M16-R01/R02
- 선행조건: M12 task/source 기준; formal gold는 neutral packet·독립 배정/metric 계약
- 종전 formal60: eligible 1/60; 새 1차 cohort: `NOT_EVALUATED`

현재 ACTION 권위: [단일 검토자 결정](../decisions/PAPER1_SINGLE_REVIEWER_ACTION_DECISION_V01.md).
Jonh19건은 검토자 수 요건 충족. 이 제한 과제에 두 번째 reviewer/합의/α를 요구하지 않으며
`NOT_MEASURED_SINGLE_REVIEWER`로 보고한다. strict60·2차·별도 source/guard 프로토콜은 유지한다.

Todo:

- [x] `speed-action-intake-2026-09-29-001`: Jonh 개발 ACTION 19/19장면·76판단·19근거 수용 완료. 배정·133 causal JPEG 검증 및 원본 보존. 추가 설명 3필드만 해석 범위 제한, 나머지 73필드 중 확정72/판단불가1. 2인 formal gold나 학습 적격 수는 아님; 반복 ACTION 요청 없음
- [x] `speed-source-binding-2026-09-29-001`: 기존 source19장면/대상anchor11/통제10장면/raw motion19 기계 연결; source Core13건/130질의 통과. 실제 대상 동일성·motion·속도 적용성 인증과 source 수용은 별개
- [x] `speed-source-binding-policy-update-2026-09-29-001`: 후속1인 ACTION 결정 반영. 기존19건 검토자 수 요건 충족; 원답/immutable run 보존, 합의 gold·검토자 간 신뢰도 주장 없음
- [x] `stop-control-source-acceptance-2026-09-29-001`: #7/#68 사용자 원문을 USER_CONVERSATION으로 보존, 작업자 STOP→ego 정지 개발 전제 수용. 새 인증 Jonh 진술·red-light/motion/해제 확인 아님. 실제24+가정48 SMT질의 및 CNL2건 연결, 새3+source8테스트 통과
- [x] 기존 영상60/geometry98 제출을 재검증하고 선택 범위의 영상 관찰 19건과 geometry 답변을 대응표에 재사용
- [x] 선택한 32개 개발 후보의 현재 자료 적격성 재감사 (`candidate-readiness-2026-09-08-003`): READY 0/추가 확인 31/현재 사용 불가 1(#47), 원본 자료·causal frame 32/32 검증. 19개 관찰·32개 geometry·#18 후속 검토 재사용; 시간창 관찰·pixel 검토를 사건 시점 정답/metric geometry로 승격하지 않음
- [x] 32건/29영상 분할 가능성·부족 항목 표 작성: 모든 기존 개발 후보의 시험용 유입 차단, 신규 시험 후보 0. 실제 train/dev/test 배정은 하지 않음
- [x] [조건부 데이터 수용 기준](../decisions/PAPER1_CONDITIONAL_DATA_ADMISSION_DECISION_V01.md) 승인·구현: UNKNOWN을 보존하고 원본 CoC 지시와 관측 사실을 구분. 전체 source 확정·조건부 개발 수용·본 학습 승인을 분리하며 혼합 통제 미확정은 보류
- [x] `conditional-candidates-2026-09-08-002`: 기존 19건 source binding 동일 재현·미검토 13건 추가, 전체 32건 기계 연결 완료. 사람 답변 추론 0. #18 조건부 개발 수용 1/추가 확인 30/사용 불가 1; 전체 source 확정 0·본 학습 승인 0 유지
- [x] `development-data-2026-09-08-001`: 사용자 요청에 따른 #18 개발 SFT 데이터 1장면(L0/L3 각 1행) export와 실제 processor 검증. 본 학습 승인 0 유지. 30장면 누락 근거 검토 화면·부분 저장·수용 validator 준비; #18 재사용·#47 반복 제외, 기존 위험 미관찰 4건 우선 배치(정상 진입 정답 아님)
- [x] `source-observation-intake-2026-09-28-001`: 관찰 검토 30/30 접수·원본 보존·형식 검증 완료. 미관찰/비적용 혼재를 유지하고 #59 추가 설명 별도 기록. 기계 후속 큐 grounding 16/적용성 14; 신규 학습·독립 행동 정답 0, 전수 재설문 없음
- [ ] 남은 대상/영역/조건·동시 통제 적용성과 독립 정상 진입 정답 확보 후 본 cohort 적격성 동결
- [ ] 주장에 필요한 source/geometry만 검증; pixel polygon 완료와 metric 근거 완료 분리
- [x] 현재 Paper-1 속도 ACTION의 단일 검토자 참조19건 수용. 이 범위의 두 reviewer/adjudication은 종료 조건에서 제외; strict60·별도 source/guard-type 요구는 해당 범위에만 유지
- [ ] 사용된 CNL의 조건·대상·수치·의무/금지·해제 의미를 독립 semantic audit
- [ ] calibration/dev/test 구분, 필요한 field 신뢰도·오류·결측 및 학습 endpoint power 입력 확보

Gate: formal60/18-cell/8-field 전수 계약은 1차에 강제하지 않음. 필요한 주장 근거가 없는
표본은 여전히 보류한다. 두 reviewer 합의만으로 누락 geometry·법규·수치를 생성하지 않는다.
적용성/guard type을 gold endpoint로 쓰면 adjudication 전 α≥0.67과 CI/정의불가 처리를 유지한다.
표본 수는 임의로 줄이지 않고 효과·nominal 성공 정밀도에 맞춰 test 전에 산정한다.
기계 보조 source 화면을 독립 gold 화면으로 자동 전환하지 않으며 새 UI/validator는 아직 미구현이다.

### M17. 1차 split/gold와 생성·CNL 품질 평가

- 상태: `PARTIAL` (19장면 실제 ACTION 수용·개발 평가 데이터 생성 완료; 본 split/source/CNL gate 미충족)
- work package: `GS-P4-MAIN-DATA-001` / S01, `GS-E2-INTRINSIC-001` / S02
- 선행조건: M12–M16의 1차 계약

Todo:

- [x] `m17-machine-preflight-2026-09-28-002`: 30장면/210프레임 원본 재생성·해시/시점 연결 검증, 기존 32개 후보 분모 보존. 29개 개발 영상 그룹과 기존 노출 81개 영상의 시험 제외 원장 생성; 실제 분할/N 동결 아님
- [x] 보행자-only 조건부 EBLC/CNL 16건, 256/256 질의 예상 일치 및 gate 제거 반례 16건 재현. 다른 조건의 적용성·실제 안전·관찰 정확성은 증명하지 않음
- [x] 배정 전 ACTION 16패킷(2인 응답 슬롯 32), 별도 CNL 16패킷(64조항) 준비 이력 보존. 2026-09-28 노란 영역 과제는 답 유도 가능성으로 수집 중단; 준비 완료가 수용/독립 gold/학습 승격을 뜻하지 않음
- [x] `m17-action-task-audit-2026-09-28-001`: 32후보·30관찰 경로 근거 감사, 16건의 TRUE 8/FALSE 8 확인 및 FALSE 8건 점검 목록 생성. 기존 URL 중단·초안 백업 제공; 정상 진행 정답 생성 0
- [x] `m17-original-coc-context-audit-2026-09-28-002`: 원본 CoC 32건 hash/연결 보존, 문맥 구절 후보 10·조향 행동만 있는 2·명시 경로 미검출 20 분리. 임의 경로 초안 철회·실행 차단. 문맥 수용/행동 정답/학습 승격 아님
- [x] `m17-context-frame-audit-2026-09-28-001`: 10문맥 후보/9 clips의 과거 JPEG·시점 70건 확인, AI 시각 표본 40회/39 JPEG 점검. #66 답 노출·#79 문맥 불확실·#88 원문/시각 잠재 긴장·#86/#94 동일 clip 기록. 원래 행동 평가 초안 작성; 독립 수용/gold 아님
- [x] `remaining-action-coverage-2026-09-28-001`: 남은 22건 원문 행동/AI 표본 점검, 전체 32후보/29 clips coverage 완료. 속도 조절 21·조향 6·차로 변경 1·양보 4 구분 및 146개 무결성 검사. 속도 조절 21후보 평가안은 담당자 수용 전이며 적격/gold 아님; 기존 답변 보존
- [x] `longitudinal-endpoint-preparation-2026-09-28-002`: 사용자 준비 진행 승인 후 21원답/147과거 JPEG 재사용·검증, 네 속도 행동/복수 적절·판단 불가 초안과 답 단서 없는 입력 참조 생성. 독립 속도 정답 0/21, 실제 배정 수 미확정·배포 0; main endpoint 동결/행동 연결 검증 아님
- [ ] M17-S01 선행: 원본 CoC 문맥과 평가 행동군 호환성 확인·답 유도 제거. 임의 경로 생성 없이 같은 과제 보존; 감속/정지/조향을 이진 진입 판단으로 자동 변환하지 않음
- [x] `speed-clause-binding-2026-09-28-001`: 21원문 구절/offset·기존 진입 계약 11건 연결, 감속 9/정지 6 승인 전 제안 및 Resume/Adapt 4건 단일 행동 미확정. 합성 48조건/192행동 결과·신규 회귀 8개 통과. 실제 적용성/속도 SMT/gold 검증 아님
- [x] [두 개발 사항 수용](../decisions/PAPER1_SPEED_DEVELOPMENT_APPROVAL_DECISION_V01.md): 사용자 후속 승인으로 감속/정지 의미 및 blind 공통 입력 수용, #79/#81 문맥 확인 전 보류. 장면 적용성·실제 배정·본 freeze 승인이 아님
- [x] `speed-contract-execution-2026-09-28-001`: 조건부 속도 계약/CNL 15건, 합성 626 + mutation 6 + scene UNKNOWN 150 = 782 SMT질의 예상 일치. 19장면/133 causal JPEG 미배정 ACTION 입력 준비. gold/독립 CNL·배포·학습 0
- [x] `speed-action-assignment-preparation-2026-09-29-001`: “아니요”/전달 확인 “네”를 Jonh 본인의 사용자 경유 self-report로 수용. 정확한 시각·신원/서명/웹폼/열람 로그 인증은 미기록/없음. 19건/76판단 배정안과 blind ACTION 초안 화면 준비
- [x] 사용자 “네..” 승인으로 `speed-action-assigned-2026-09-29-001`의 Jonh 19건/76판단 실제 배정. 실제 Chromium 점검 뒤 port8766 전용 ACTION URL 게시, 담당자 목록과 분리. 이전 원답/중단 화면 보존
- [x] 실제 ACTION JSON 수신·검증: `speed-action-intake-2026-09-29-001`, 19/19 완료. 입력/응답 분리 JSONL 각19행·17 clip groups와 고정분모 채점 함수 생성; 범위 제한3/판단불가1 제외한 개발 판정72개로 비교 가능. 상수 baseline은 소프트웨어 진단이며 VLM 성능 아님
- [x] 검토 장면 중 조건부 CNL13건 텍스트·field mapping 재생성 및 UNKNOWN 전제 SMT130질의 재현. 반복 규칙 문장은2종으로 색인화, 신규 설문 없음. 원본 CoC 행동과 응답 불일치 #52/#55/#60 보존; 계약 없는6건도 분모에 유지
- [x] `speed-source-binding-2026-09-29-001`: ACTION 답 없는 source/대상 관찰 anchor·시점별 CASCADE/raw motion 연결 및 source Core130질의. 신규8+기존속도3테스트 통과, intake82/신규89해시 검증
- [x] 현 Paper-1 ACTION19건의 단일 reviewer 요건 충족. 두 번째 reviewer/합의/α는 이 범위의 blocker가 아니며 검토자 간 신뢰도는 미측정
- [x] #7/#68 작업자 STOP 표지→ego 정지 개발 source 전제 수용 및 Core2/CNL2 연결. applicability TRUE/evidence_valid true, motion UNKNOWN; USER_CONVERSATION 원문·시점null·범위 기록. #68 원 red-light와 분리, 원답/이전 run 보존
- [ ] 나머지 source/규칙/target·motion gap과 CNL 독립 의미 확인. ACTION은 생성 근거로 재사용하지 않음. #79/#81 보류, 불일치·split/power 유지. 새 속도 학습 export0; 두 STOP 관찰 재질문 없음
- [ ] M17-S01 선행: 정상 진행·보류·판단 불가 구성 및 항상 보류 진단, 다른 통제/선정·노출 감사 후 새 ACTION 수집. 기존 관찰 전수 반복 없음
- [ ] M17-S01: 제한 task의 main N·group split·독립 gold·노출/누출 감사 및 held-out lock
- [ ] M17-S02: 사용 clause의 적용성·source 정확도·abstention/coverage 평가
- [ ] 사용 EBLC subset의 type/unit/모순·bounded 검증과 CNL field fidelity/독립 semantic audit
- [ ] 직접 NL 및 검증 생략 대조의 오류·성공·보류를 같은 분모로 보고

Gate: 중대한 source/CNL 오류의 미해결 상태에서 학습 데이터를 배포하지 않음. 실패 장면은
평가 분모에 남김. 정확도/coverage/지원 subset을 공개하고 범용 언어 성능을 주장하지 않음.
일반 multi-target 경쟁은 Project 05, 광범위 OOD 및 모든 BCV baseline은 2차다.

### M18. EBLC→자연어 CoC 학습 효과

2026-09-29 후속 다양성 요청: [최소 확장 설계](../designs/PAPER1_TEMPORAL_DIVERSITY_DESIGN_V01.md).
기존 통제 비교 완료를 취소하지 않고 별도 후속 실험으로 관리한다.

- [ ] D1: 새 시간값·경계 조건 실제 checkpoint 평가 및 고유성/중복 감사
- [ ] D2: 의미 보존 문장 변형의 paired 행동 평가
- [ ] D3: 원본/빈 영상/교체 영상의 입력 의존성 진단
- [ ] D4: 같은 source의 오류 주입 검증 적용/생략·정상 계약 오탐 비교
- [x] 추가 학습 자료:960/240/240 paired rows 및 EBLC 행동 판정·독립 환경5760건 대조
- [ ] 추가6조건×3seeds 학습: 기존5조건+EBLC/CNL, 각180 updates, 실제18 checkpoints
- [ ] 사용자 승인 후속: 부모 실험 완료 후 동일 P2에서 continued SFT 대 EBLC 비용 추가 학습, 각60 updates×3seeds 및 신규 시간 구간 시험 — [설계](../designs/PAPER1_EBLC_COST_LEARNING_DESIGN_V01.md)
- [ ] 이전 평가 항목 유지·확장:4평가 묶음, 기존7지표+coverage, seed/그룹 불확실성 및 실패 포함

후속 진단은 새 run에 고정하며, 검증기 탐지를 학습 ablation의 인과 효과로 확대하지 않는다.

현행 v2.4 우선 Todo:

- [ ] P01: 기존 temporal 학습/평가 구현·분할·제약 가시성을 고정하고 P0/P1/P2 프로토콜 작성
- [ ] P02: 동일 제약의 실제 EBLC→Core/SMT→CNL 연결 및 필드/반례/독립 의미 검사
- [ ] P03: 동일 시각 입력·정답·예산으로 실제 VLM 비교 실행(≥3 paired seeds 계획)
- [ ] P04: 미사용 통제 장면의 위반·정상 진행·불필요 정지·효과 보존/CI 보고
- [ ] P05: 기존 연구 귀속과 실제 장면 사례를 분리해 M20 원고에 반영

v2.4의 계약 제공 평가는 P1/P2에 동일하게 적용하며 oracle 행동 답변을 입력하지 않는다.
아래 no-guard-at-test/네-arm 조건과 실제 속도 실험 기록은 이전 범위/후속 이력으로 유지한다.

2026-09-29 후속: 사용자 “네”로 두 STOP 공통 결과 CNL/한정 개발 사용 수용.
`m18-cohort-feasibility-2026-09-29-006`의 적격2, `speed-development-packaging-2026-09-29-003`의
L0/L3 각2행 train export 완료. 기존72-step/3-seed 개발 학습 실행기를 연결했으나 GPU 점유로
모델 할당 전 거부되어 이번 update0이다. 다음 단계는 유휴 GPU에서 한정 개발 실행이며,
동일 CNL 승인을 재요청하지 않는다. main gate·다른17장면·held scenes·원답은 유지한다.

- 상태: `PARTIAL` (실제 이미지 개발 launch 완료; main 학습·성능은 미실행)
- work package: `GS-P5-LEARNING-001` / E4-L
- 선행조건: M17 gold/split·CNL 품질과 실제 learning endpoint dev power
- 요구사항: [M18 학습 계약](../requirements/M18_EBLC_LEARNING_EFFECT_REQUIREMENTS_V01.md)

2026-09-29 후속 실행: 행별 수용검사(기계2/사람 CNL0/속도 정책0), L0/L3 실제 영상
staging38행 processor·마스크 검사, 별도 UNKNOWN-motion 공통 결과54 SMT 검사 완료.
19장면 pretrained blind inference·고정 scorer 채점 및 source-only L1/L2 provider38출력 완료.
원 CoC·같은 영상까지 맞춘 두 source-supported 장면의 provider4출력도 완료했지만
L2 구문 실패2이며 qualified main arm은 아니다. 전체 baseline 참조 부적절10/16,
정상 진행2/8, 불필요 정지7/12; evaluation5행은2/4·1/3·2/3, 세 CI[0,1].
`pretrained-speed-evaluation-2026-09-29-001`에 장면별 예측/참조/coverage/불확실성 보존.
기존14/5행 clip 분할 유지, 추가 update0. pretrained 개발 결과는 trained L0 또는 main 효과가 아니다.
새 제안 CNL의 제한 개발 사용 판단과 충분한 source-supported 학습 코호트는 남아 있다.

2026-09-29 개발 실행: `real-development-preflight-2026-09-29-001`의 실제 scene18 L0/L3
processor·loss-mask 검사, `real-development-smoke-2026-09-29-001`의 각1step/총2updates·
두 adapter 저장 완료. 같은 초기값/각224tensor 변경. 성능 또는 main 효과가 아니다.
48시간 evidence-first 코호트 판정 `m18-cohort-feasibility-2026-09-29-001`: 속도 train0/19·
독립 main eval0,17clip 개발 partition12/5 고정(적격0으로 성능 실행불가). 독립 scorer와
prior Project01 primary15run 감사 완료. #7/#68 speed 수용·CNL 의미와 충분한 source-supported
정상 진행/독립clip 코호트가 필요하다. 기존 ACTION/STOP 관찰 재질문, 임의 main gate 완화 없음.

Todo:

- [ ] S01: generator/BCV와 독립된 제한 과제의 violation·nominal 행동 evaluator
- [ ] S02: VLM checkpoint·image/video processor·trainable module·SFT/CNL loss·N·≥3 paired seeds·예산 동결
- [ ] S03: L0–L3 실제 training examples 생성, CNL 삽입/hash·coverage·누출 감사
- [ ] S04: 같은 초기 VLM·이미지/영상·텍스트·예산으로 full 또는 내부 adapter fine-tuning, update/checkpoint/log 증거
- [ ] S05: held-out 이미지/영상에서 VLM의 행동/궤적 선택을 평가; 외부 gold guard/shield 없이 위반·nominal 성공·CI 보고
- [x] Software preflight: Qwen3-VL-2B 내부 LoRA 3,211,264 parameters, 네 arm 각 1 update·이미지 토큰·유한 gradient·adapter 저장 확인

Software preflight는 인공 이미지 1개/seed 1개의 실행 경로 검증이다. 실제 장면 S03/S04 및
독립 효과 S05를 완료로 세지 않으며 main study 상태는 QUEUED다.

Gate: L3−baseline 위반률 CI 상한<0 및 nominal task-success CI 하한≥−5%p를 함께 판정.
대조군별 claim·다중 비교·seed/scene 변동·coverage를 보고한다. 원본 CoC 대비 효과를 보편적
필요성으로 확대하지 않는다. offline 선택 성공을 실제 goal completion이라 부르지 않는다.
부정/불확정 결과도 실행 완료와 양립하지만 NOT_EVALUATED는 완료가 아니다.
VLM 자체의 학습과 시각 입력 기반 독립 행동 평가가 필수다. 고정 VLM 위 별도 scorer만 학습,
text-only 모델, prompt 추가, SAT 결과 또는 문장 품질만으로 이 gate를 통과할 수 없다.

2차 이관: S06/GS-P5-OUTCOME-001의 ≥2,000 closed-loop rollout, with-shield, 다양한 simulator,
장기 진행성 및 추가 lifecycle/flat/preference-only 학습 ablation. 1차 선행조건이 아니다.

### M19. Alpamayo·runtime 적용 (2차)

- 상태: `QUEUED` (DEFERRED_PHASE2)
- work package: `GS-P6-ALPAMAYO-001`
- 선행조건: M20 후 별도 2차 scope/resource 승인, runtime evaluator gate

Todo:

- [ ] 실제 Alpamayo CoC/trajectory adapter·prompt/verifier/reranker/shield 분리 평가
- [ ] 2차 protocol에서 100 events×3 seeds 및 negative/expert controls 재동결
- [ ] latency·intervention·long-horizon progress와 failure/residual risk 보고

M19는 M20의 선행조건이 아니며, 모델 학습/추론 적용 및 simulated/actual 효과를 구분한다.

### M20. 1차 논문과 재현 패키지

- 상태: `QUEUED`
- work package: `GS-MAIN-PAPER-001`
- 선행조건: M12/M14–M18 1차 계약; M13 전체24·M19/E5·E6는 불필요

Todo:

- [ ] C1–C4 주장→방법→대조군→metric→실제 artifact 대응표
- [ ] E4-L 실제 CNL 사용 VLM examples·weights/adapter·update/예산·held-out 시각 행동 평가 및 부정 결과 확인
- [ ] source/제약 예시·생성/CNL 품질·네 arm 학습 효과 중심 원고 작성
- [ ] 지원 task/model 범위·반례·coverage·한계와 재현 가능한 code/hash/split 부록
- [ ] 제한 데이터 공개 감사와 공개 전 필요한 발명/출원 판단

Gate: 학습 미실행 또는 CNL 미사용이면 완료 불가. 결과가 부정이면 그에 맞는 결론을 쓴다.
VLM fine-tuning과 독립 이미지/영상 행동 평가가 없으면 1차 논문 종료도 불가하다.
runtime 실차 효과·모든 국가 법규 준수·범용 언어 우월성·전문가 생산성은 1차 주장에 포함하지 않는다.
M20-R01/GS-E6-EXPERT-UTILITY-001의 3-arm 전문가 시간·오류 연구는 2차 선택 과제다.

### M21. 실제 차량 심화 검증 (2차)

- 상태: `QUEUED` (DEFERRED_PHASE2)
- work package: `GS-POST-ACTUAL-VEHICLE-001`
- 선행조건: M20, M19 runtime readiness, 차량/시험 권한·안전 승인

Todo:

- [ ] 실제 vehicle/DBW binding·response/deceleration/uncertainty source 검증
- [ ] SIL/HIL/shadow·통제 시험장·안전운전자·중단 조건 승인 후 단계별 실행
- [ ] simulation/실차 결과·개입·사고/중단 기록·residual risk 분리 보고

이 단계의 허가 없이 실제 차량 시험을 시작하지 않는다.

## 6. 상태 갱신 규칙

현재 scope의 실행 증거가 있어야 checkbox를 완료로 바꾼다. DEFERRED_PHASE2는 완료가 아니다.
1차 scope로 이전 1/60을 재집계하지 않는다. 새 cohort 수와 기존 formal60 수는 별도 명시한다.
소프트웨어/실험 수행 완료와 가설 지지는 별도 판정한다. 다음 단일 작업은 M12-R01이다.

## 7. v2.2까지의 M12–M21 상세 이력 (현재 1차 실행 체크리스트 아님)

<details>
<summary>이전 완료 근거·source 획득·검토 이력·확장 gate 보기</summary>

아래는 scope 축소 전 기록이다. 완료/미완료 사실은 보존하지만 현행 선행조건과 단계 배치는
v2.3 및 위 1차/2차 원장을 따른다. '당시 미완료'는 이번에 완료했다는 뜻이 아니다.

#### 이전 M12. 세 deep slice source-bearing catalog와 E-1 audit

- 계획 대응: P0/E-1
- 상태: `PARTIAL` (재적격화); 최초 catalog `COMPLETE` 이력 보존
- work package: `GS-P0-CATALOG-001`
- 선행조건: M11

Todo:

- 역사적 완료: broad survey가 아닌 지정 관할의 authoritative source audit 수행
- 역사적 완료: 세 slice에 최초 12–20개 RuleTemplate 배분
- 역사적 완료: 여섯 행동군 broad applicability family coverage 표 작성
- 역사적 완료: 각 template에 source/version/scope/precondition/exception 기록
- 역사적 완료: PredicateSpec의 observability/freshness/failure-to-UNKNOWN 작성
- 역사적 완료: target/zone binding 요구와 ambiguity reason 정의
- 역사적 완료: numeric binder의 input/unit/frame/derivation DAG 작성
- 역사적 완료: activation/invariant/bound/release/reactivation/fallback lifecycle 작성
- 역사적 완료: hard/service/preference priority tier 지정
- 역사적 완료: source가 없는 규범·수치가 0건인지 감사
- 역사적 완료: 모든 fixture schema validation과 catalog lookup test 작성
- 역사적 완료: E-1 feasibility audit artifact와 report 생성

종료 gate:

- 세 slice 최초 12개 이상 template의 필수 field 100%
- source 없는 normative/numeric value 0건
- six-family coverage 별도 확보
- 미달 시 model/front-end 개발을 중단하고 source authoring으로 pivot

종료 근거:

- [source catalog v0.1](../../../../projects/04-guardsynth-coc/src/guard_synth/fixtures/source_catalog_kr_v0_1.json)
- [E-1 audit report](../../../../artifacts/results/public/guardsynth-source-catalog-001/kr-source-catalog-2026-08-10-v2/REPORT_KO.md)

실행 결과: template 15개, slice 5/6/4, family 6/6, source 없는 규범·실행 수치 0건,
집중 10/10, maintained 202/202, P0a 7/7, 구조 10/10. 첫 v1 실행은 subprocess
`PYTHONPATH` 누락으로 실패했으며 결과를 보존하고 v2에서 수정했다.

선행 보완 M12-R01 (역사적 catalog 완료와 별도):

- 당시 미완료: 현 scope의 scene/country/catalog/treaty 또는 system source 선택과 version/승인 근거 감사
- 당시 미완료: direct rule·general fallback·physical/system clause를 나눠 precondition/exception/lifecycle 연결
- 당시 미완료: fallback을 구체적 stop/distance 수치로 승격하지 않고 binder 근거·unit/frame·uncertainty 검증
- 당시 미완료: 필수 source field·binder recomputation ≥0.95·injected UNSUPPORTED precision ≥0.90 재검증
- 당시 미완료: 현재 retained eligible 1건의 조건부 jurisdiction/source 근거를 재확인하고 유지/보류 근거 기록

#### 이전 M13. 실제 장면 근거 × 가상 차량 24-scene dry run

- 계획 대응: P1
- 상태: `PARTIAL` (재적격화); 역사적 `COMPLETE / M13_TERMINAL_DATA_SHORTFALL_FRONTEND_CAN_PROCEED` 보존
- work package: `GS-P1-SIM24-001`
- 선행조건: M12, 실제/파생 scene access
- 요구사항: [M13 simulation 24-scene requirements](../requirements/M13_SIMULATED_24_SCENE_REQUIREMENTS.md)
- 일정 결정: [실제 차량 검증 후속 단계 이관](../decisions/ACTUAL_VEHICLE_VALIDATION_DEFERRAL_DECISION_V01.md)

Todo:

- 역사적 완료: 세 slice별 8개 장면 선정 slot과 필요한 event 입력 기준 고정
- 역사적 완료: 위험/nominal, clear/occluded, release/reactivation을 층화
- 역사적 완료: 기존 perception/tracker/map/trajectory output adapter의 현재 집계 재사용
- 역사적 완료: 이미지·방법·예제·항목·자동 권고·JSON/CSV export를 갖춘 review kit 및 제한 이미지 10개 단일 HTML 준비
- 역사적 완료: 완료된 image-only 검토 10건을 fail-closed partial scene packet으로 변환하고 누락 manifest 작성
- 역사적 완료: 기존 판정을 숨긴 판정 유형별 calibration/audit 표본 2건 작성(독립 재검토 대기)
- 역사적 완료: 기존 obstacle 파생물의 전체 actor 후보 미보존을 탐지하고 fail-closed blocker 작성
- 역사적 완료: all-candidates+track-samples v2 추출기와 privacy-safe adapter 경로 구현
- 역사적 완료: 첫 calibration 장면 target–zone geometric set association evidence 작성
- 역사적 완료: 첫 calibration 장면 rig/sensor→ego-path coordinate transform 검증
- 역사적 완료: 첫 calibration 장면 timestamp, ego pose/speed, geometry와 source refs 정렬
- 역사적 완료: 24장면에 적용할 simulation assurance profile과 binding version 동결
- 역사적 완료: 관측 egomotion·CoC response latency·공식 platform/API 문서의 assurance 적합성 감사와 data-gap manifest 작성
- 역사적 완료: 실제 장면 근거와 가상 차량 binding을 분리한 simulation projection 경로 구현 및 1장면 Core/Z3 실행
- 역사적 완료: 기존 review/adapter/audit를 중복 제거한 privacy-safe 후보 inventory 작성
- 역사적 완료: 첫 calibration 장면의 실제 법규 source와 조건부 scene applicability 연결
- 당시 미완료: 24개 장면의 실제/파생 근거 8/8 source closure 검증(4/24에서 terminal shortfall)
- 역사적 완료: 근거 8/8 장면만 별도 simulation binding으로 GuardSynth→EBLC→Core/Z3 실행(4장면·17계약)
- 역사적 완료: missing field를 synthetic으로 채우지 않고 reason manifest 작성
- 역사적 완료: 실행/abstention/source-closure/translation coverage와 terminal failure taxonomy 보고

종료 gate:

- scene-source-complete 8/8 장면 24/24 또는 미달 slot을 명시한 terminal decision
- recorded/simulation vehicle binding 분리 100%
- canonical/Core/Z3 판정 agreement 100%
- binder recomputation ≥0.95
- injected `UNSUPPORTED` precision ≥0.90
- source 없는 normative/numeric value 0건

현재 입력 현황:

- simulation projection 실행 scene 4/24, 계약 17개
- 중복 제거 후보 13개: 근거 8/8 4개, image-only 0/8 9개; 목표 대비 absent slot 11개
- 첫 calibration 장면은 심사 이미지와 기존 파생 이미지를 SHA-256으로 유일하게 연결하고
  multi-camera timestamp, recorded-future ego pose/speed, 1-D conflict geometry와 전체 actor track,
  event→model-t0 coordinate transform 및 clip-specific rig binding, 공식 California Vehicle Code
  §21950/§21954의 조건부 scene applicability를 근거로 확인해 필수 입력 8/9 확보; 나머지 1/9는
  source-bearing vehicle assurance profile은 M21로 이관하고 현재는 별도 simulation binding 사용
- all-candidates v2의 선택 이벤트 후보 2개와 track sample을 2/2 보존하고, 두 후보 모두
  10/10 sample에서 ego corridor와 oriented-box overlap을 가져 source-linked `SET(2)`로 association
- 기존 실제 후보 5개 중 partial adapter 4개
- 첫 calibration 장면의 지역 rule source는 조건부 연결했으나 source-bearing assurance profile 부재
- assurance 후보 4건은 각각 관측값, 행동 파생값 또는 vehicle-unbound platform/API 문서로 판정되어
  hard bound 사용 불가; 동일 vehicle/DBW의 runtime capability와 OEM/통제시험 근거가 필요
- 실제 차량 assurance를 사용한 GuardSynth→EBLC→Core/Z3 scene execution은 0건이며 M21 전에는 요구하지 않음
- 별도 가상 차량 binding으로 4장면·17계약을 실행해 frame-0 `ACTIVE/VALIDATED`,
  canonical/runtime/bounded-Z3/Core agreement와 SMT-LIB 직접 replay 100%를 확인
- 24장면 empirical gate, STOP_SIGNALS/FOLLOWING_CUT_IN 및 nominal/UNKNOWN/CONFLICT/
  release/reactivation 실제 장면 coverage는 미통과; 부족분을 합성하지 않고 terminal decision으로 종결
- 실제 차량 assurance 및 실차 검증은 닫지 않았으며 M21 전에는 요구하지 않음

준비도 근거:

- `artifacts/results/public/guardsynth-24-scene-dry-run-001/kr-dry-run-readiness-2026-08-10-v1/`
- `artifacts/results/public/guardsynth-scene-evidence-review-001/scene-evidence-review-2026-08-10-v5/`
- `artifacts/results/restricted/guardsynth-image-review-partial-scene-001/alpamayo-image-review-2026-08-11-v2/`
- `artifacts/results/restricted/guardsynth-calibration-scene-source-audit-001/alpamayo-calibration-source-2026-08-11-v7/`
- `artifacts/results/restricted/guardsynth-calibration-scene-source-audit-001/alpamayo-calibration-source-2026-08-11-v10-tracks-linked/`
- `artifacts/results/restricted/guardsynth-calibration-scene-source-audit-001/alpamayo-calibration-source-2026-08-11-v12-transform-binding/`
- `artifacts/results/restricted/guardsynth-geometric-association-001/alpamayo-episode-05-event-01-2026-08-11-v2/`
- `artifacts/results/restricted/guardsynth-calibration-scene-source-audit-001/alpamayo-calibration-source-2026-08-11-v15-association/`
- `artifacts/results/restricted/guardsynth-rule-applicability-001/alpamayo-episode-05-2026-08-11-v1/`
- `artifacts/results/restricted/guardsynth-calibration-scene-source-audit-001/alpamayo-calibration-source-2026-08-11-v17-rule-applicability/`
- `artifacts/results/restricted/guardsynth-vehicle-assurance-audit-001/alpamayo-episode-05-2026-08-11-v1/`
- `artifacts/results/restricted/guardsynth-simulated-scene-dry-run-001/alpamayo-episode-05-simulation-2026-08-11-v4/`
- `artifacts/results/restricted/guardsynth-sim24-candidate-audit-001/alpamayo-candidate-inventory-2026-08-12-v1/`
- `artifacts/results/restricted/guardsynth-sim24-candidate-audit-001/alpamayo-candidate-inventory-2026-08-12-v2/`
- `artifacts/results/restricted/guardsynth-sim24-batch-001/alpamayo-terminal-batch-2026-08-12-v1/`

선행 보완 M13-R01:

- 당시 미완료: current scope/platform hash로 실제/파생 세 slice 각 8개 장면을 확보해 재검증
- 당시 미완료: nominal/hazard·UNKNOWN/CONFLICT·release/reactivation 지원/미지원과 slot shortfall 보고
- 당시 미완료: binder recomputation ≥0.95, injected UNSUPPORTED precision ≥0.90, target/direct replay agreement 검증
- 당시 미완료: dry-run/dev/pilot 노출 이력을 기록하고 main locked test에서 제외
- 당시 미완료: source eligibility와 execution readiness를 분리해 생성/translation 실패도 분모에 포함

기존 4/24 terminal 완료는 보존한다. 새 보완의 미달은 재적격화 미완료이며 다시 terminal로
표시해 empirical gate를 면제하지 않는다. 24개는 source가 맞으면 pilot 개발 표본과 재사용할 수
있지만 독립 main test와는 분리하며 24+60개의 별도 인간 검토를 무조건 요구하지 않는다.

#### 이전 M14. CoC-conditioned constraint generation front-end

- 계획 대응: P2
- 상태: `PARTIAL` (재적격화); 역사적 `COMPLETE`(scoped software) 보존
- work package: `GS-P2-FRONTEND-001`
- 선행조건: M12, M13 failure taxonomy

Todo:

- 역사적 완료: CoC intent/cause/action/uncertainty typed lexical parser v0.1 구현
- 역사적 완료: CoC claim과 observed scene fact를 구조적으로 분리
- 역사적 완료: scene predicate/semantic-tag 입력 protocol 구현(원시 perception parser는 후속)
- 역사적 완료: CoC+scene evidence retrieval query 생성
- 역사적 완료: graph/BM25/dense candidate retrieval interface 구현(dense는 caller-supplied embedding adapter)
- 역사적 완료: jurisdiction/catalog version/date/ODD/slice hard filter 구현
- 역사적 완료: required-predicate와 typed precondition tag의 four-valued evaluator 구현(exception 확장은 후속)
- 역사적 완료: entity/zone partial binding과 ambiguity handling 구현
- 역사적 완료: 별도 system requirement/simulated-assurance 기반 deterministic numeric binder 구현(지원 rule 1개)
- 역사적 완료: 지원 proposal을 GuardSynth request/단일 EBLC/Core/SMT generation으로 연결
- 역사적 완료: missing evidence는 REVIEW/UNSUPPORTED로 abstain
- 역사적 완료: paraphrase/shuffle/hazard-removal metamorphic tests 작성

종료 gate:

- 24-scene structured input에서 deterministic/reproducible proposal bundle 생성
- CoC claim이 legal/observed authority로 승격된 사례 0건
- schema parse ≥0.99와 compiler success ≥0.98 목표의 pilot 측정 가능

종료 근거:

- `artifacts/results/public/guardsynth-coc-frontend-001/crosswalk-synthetic-2026-08-12-v3/`
- `artifacts/results/public/guardsynth-coc-frontend-materialization-001/crosswalk-synthetic-2026-08-12-v1/`
- `artifacts/results/public/guardsynth-coc-frontend-matrix-001/locked-synthetic-2026-08-12-v1/`
- 신규 front-end 단위/통합 테스트 16/16, 전체 maintained 286/286
- 공개 synthetic crosswalk에서 source-linked proposal 1건, 다른 precondition은
  `NOT_APPLICABLE/REVIEW_REQUIRED`, source에 없는 safe-distance 수치는 생성하지 않음
- 24 locked synthetic cases에서 schema/기대 verdict 24/24, claim 승격 0, 지원 proposal compile 2/2
- 현재 제한: 실제 24장면 정확도 미평가, 일반 NLP/production dense model 미포함,
  operational policy mapping은 primary rule 1/3. 미지원 rule은 임의 수치 없이 abstain

선행 보완 M14-R01:

- 당시 미완료: 세 slice의 supported/unsupported rule·precondition/exception·numeric policy matrix 작성
- 당시 미완료: STOP_SIGNALS/FOLLOWING_CUT_IN을 pedestrian 전용 binder 복사 없이 source-bound materialization
- 당시 미완료: 실제 CoC dev 입력에서 parser/retriever 오류·coverage와 modality provenance 측정
- 당시 미완료: 선택한 lexical/dense/model provider·version·범위를 동결하고 B10 baseline과 공유 입력 계약 검사

일반 NLP/dense 모델 자체를 필수 기여로 가정하지 않는다. 선택 방법의 지원 범위를 명시하고
미지원이 많은 상태를 전체 세 slice 학습 신호 준비 완료로 취급하지 않는다.

#### 이전 M15. 비교 baseline과 평가 protocol 동결

- 계획 대응: P2/E2
- 상태: `PARTIAL` (재적격화); 역사적 `COMPLETE`(protocol freeze) 보존
- work package: `GS-P2-BASELINES-001`
- 선행조건: M14 input/output protocol

Todo:

- 역사적 완료: B0 controlled prior와 B3 template-retrieval 하한선(전문가 B11은 M16 gold)
- 역사적 완료: CoC-only와 scene-only provider adapter/channel firewall
- 역사적 완료: free-form model provider adapter와 invalid-output abstention(provider 자체는 평가 환경에서 주입)
- 역사적 완료: flat template retrieval과 B13 naive composition
- 역사적 완료: physics-only deterministic binder
- 역사적 완료: DriveReg-style deterministic BM25 retrieval adapter
- 역사적 완료: RTCD-style scene-only applicability adapter
- 역사적 완료: SanDRA-like reachability/action filtering adapter
- 역사적 완료: 동일 source budget, locked input, output schema와 metric contract 고정
- 역사적 완료: B0–B8/B13 ID와 version manifest 작성
- 역사적 완료: baseline이 locked expected label을 읽지 않는 oracle independence 경계 고정

종료 gate:

- 모든 방법이 동일 locked input에서 실행 가능
- 실패/abstention을 숨기지 않는 공통 metric contract
- 실험 시작 후 baseline 기대값/분할 변경 금지

종료 근거:

- `artifacts/results/public/guardsynth-baseline-protocol-001/locked-interface-2026-08-12-v2/`
- 24 cases × 10 baselines = 240/240 schema-valid result
- channel firewall 0건, hidden failure 0건
- B0/B3/B4/B5/B6/B7/B8/B13은 controlled input에서 실행; B1/B2는 provider adapter 테스트
  통과, 공개 smoke에는 provider 미설정 `UNSUPPORTED`를 보존
- 전체 maintained 293/293, P0a 7/7, structure 10/10

완료 경계: baseline **interface/protocol freeze**이며 품질 순위·원 논문 재현 성능·실제 장면
효과가 아니다. B1/B2 model provider와 독립 expert gold는 M16 실행 환경에서 필요하다.

선행 보완 M15-R01:

- 당시 미완료: 실제 B1/B2 provider/model을 연결해 dev smoke 실행(미설정 UNSUPPORTED로 대체 불가)
- 당시 미완료: B9 flat/B10 EBLC+BCV/B12 always-stop 실행과 B11 independent expert-gold 입력 계약 확보
- 당시 미완료: B0–B13 및 E2-FF-MATCHED의 입력·정보·model/tuning budget·output·지원 범위 registry 동결
- 당시 미완료: full-input free-form과 B10의 동일정보 비교, input ablation과 representation/BCV ablation 분리
- 당시 미완료: baseline failure·abstention/coverage, 원 논문 재현 여부와 단순 style adapter 경계 보고

B11 gold 값은 M16/M17 독립 annotation 후 결합한다. 따라서 여기서는 입력 계약을 검증하며
gold의 실제 존재를 선행조건으로 만들어 순환 의존하지 않는다.

#### 이전 M16. 60-scene 전문가 formal pilot

- 계획 대응: P4/E1/E6
- 상태: `PARTIAL` (`M16_LOCAL_SOURCE_FRONTIER_AUDITED_EXTERNAL_SOURCES_REQUIRED`, eligible 1/60)
- work package: `GS-P4-PILOT-001`
- 선행조건: source curation 준비는 허용; formal annotation은 M13-R01/M14-R01/M15-R01,
  M16-R01/R02 및 S08/S09 gate 뒤에 실행

단계 게이트 원장:

| 단계 | 범위 | 상태 | 완료 근거/현재 shortfall |
|---|---|---|---|
| M16-S01 | pilot 계약·quota·UI·배정·metric software | `COMPLETE` | locked 60-slot, 두 UI mode, blinded assignment와 metric contract |
| M16-S02 | per-scene eligibility validator와 기존 장면 재감사 | `COMPLETE` | 33 records→23 events, 기존 4건 중 8/8 closure 3건, cross-event conflict 1건 |
| M16-S03 | 국가 제한 없는 장면별 관할 정책 | `COMPLETE` | multi-jurisdiction decision, jurisdiction-neutral catalog schema, explicit catalog selection과 scope-aware validator |
| M16-S04 | licensed annotation 후보 screen | `COMPLETE` | 2,066 annotations; 135 events 중 98 classified, 37 unsupported |
| M16-S05 | sensor candidate cohort materialization | `COMPLETE` | 81 unique clips, 486 selected members; classified-event temporal closure 98/98 |
| M16-S06 | calibration 자료 확보와 recorded-rig binding | `COMPLETE` | 405 feature rows; classified-event calibration/rig binding 98/98 |
| M16-S07 | calibration compatibility·association·rule·outcome 폐쇄 | `PARTIAL` | offline variant·event-anchor transform·treaty baseline 98/98; actor/control relation 70/98, lane containment 1/98; semantic geometry·lifecycle 미완료 |
| M16-S07A | official calibration audit·source-review precheck·human packet | `COMPLETE` | 일반 variant rule 없음과 open map 부재 확인; 98-event precheck, 60-record 미완료 human packet |
| M16-S07B1 | 60-event image-embedded review UI·portal packaging | `COMPLETE` | 60 contact sheets/300 frames, restricted self-contained HTML, portal 등록 |
| M16-S07B2 | reviewer observability scope·화면 가독성 분리 | `COMPLETE` | 비관찰 문항 제거, slice별 대상·lane/zone·시간 상태 상세 매뉴얼과 예시·영상 관찰 2문항·full-width zoom·명시적 복귀·navigation-safe autosave 제공; 대체·curator·미착수 패키지 활성 목록 제외 |
| M16-S07B3 | 60-event human video observation 실행·검증 | `COMPLETE` | 단일 검토자 60/60; JSON/CSV·packet 순서·slice·image hash 일치, aggregate artifact 확정 |
| M16-S07B | curator source closure와 human video observation | `PARTIAL` | human observation 60/60 완료; transform은 후속 폐쇄, geometry·lifecycle source 미완료 |
| M16-S07C | post-review 98-event source closure 재감사 | `COMPLETE` | NVIDIA NCore pinned rule로 offline variant 선택 98/98 폐쇄; 81-clip offline input·405 calibration row hash 검증; 사람 답변으로 source field 승격 0건 |
| M16-S07D | M16 review-event anchor·offline coordinate transform 폐쇄 | `COMPLETE` | event timestamp를 M16 scene t0로 고정; 81 offline extrinsics assets·648 rows 검증, offline egomotion 보간과 inverse closure로 verified transform 98/98 |
| M16-S07E | CASCADE structured relation·optional containment source 감사 | `COMPLETE` | approved annotation hash 98/98; active source relation SET 70/98, strict shared lane containment 1/98; 빈 curator 설문 생성 0건 |
| M16-S07F | source-bound lane/drivable-area 후보 생성·curator UI | `COMPLETE` | pinned TwinLiteNet+ large로 98 events×5 timestamps=490 frame 후보 생성; source video/frame/model hash 결합, curator 98건 대기, source field 승격 0건 |
| M16-S07G | geometry curator 결과 통합·source frontier 감사 | `COMPLETE` | curator 98/98, accepted 61건의 mask 610파일 hash 재검증; semantic rig geometry 승격 0, 37건 polygon과 외부 source queue 고정 |
| M16-S07H | UN 국제협약 normative baseline 결합 | `COMPLETE` | 98/98 결합; Vienna 직접 규칙 35, Geneva 일반 주의의무 fallback 63, 국내법 준수 판정 0; authority 획득 task 제거 |
| M16-S08A | attrition-aware reserve candidate supply pool | `COMPLETE` | reserve 39 events; 22 new clips와 asset 재사용 17 events |
| M16-S08 | 60 eligible scene cohort와 quota binding | `PARTIAL` | distinct eligible 1/60; slice/outcome joint quota 미충족 |
| M16-S09 | reviewer training/calibration | `NOT_STARTED` | S08 60/60 gate 대기 |
| M16-S10 | 독립 annotation·adjudication·agreement/time | `NOT_STARTED` | S09 대기 |
| M16-S11 | pilot power analysis와 M16 종료 판정 | `NOT_STARTED` | S10 대기 |
| M16-R01 | source curation·독립 gold·assistance 검토 분리 | `QUEUED` | 기존 기계 보조 화면은 source draft; 독립 gold 배정/노출·geometry/import 계약 보완 필요 |
| M16-R02 | 두-field α·sampling·endpoint별 power 계약 | `QUEUED` | applicability-only metric과 혼합 UI mode 비교 보완 필요 |

현재 전체 완료 상태는 `M16 PARTIAL`이다. S07D가 coordinate transform을 닫았지만 source-linked
geometry·lifecycle이 없으므로 개별 장면 eligibility 또는 60-scene 구축 완료를 뜻하지
않는다.

Todo:

- 역사적 완료: 60장면 slice/outcome quota, joint slot manifest와 deterministic split seed 사전 고정
- 역사적 완료: 가드 type/target/operator/range/source/lifecycle annotation schema
- 역사적 완료: 최소 확인/complete authoring training UI와 timing export 구현
- 역사적 완료: deterministic blinded 2인 배정과 별도 adjudicator protocol 구현
- 역사적 완료: applicability/field agreement·correction/time metrics 계약 구현
- 역사적 완료: source-ref-required power planning 계약 구현
- 역사적 완료: per-scene 8-field eligibility manifest와 fail-closed validator 구현
- 역사적 완료: 기존 4개 장면의 중복·timestamp·관할·ODD·rule scope 재감사
- 역사적 완료: 로컬 파생 event 전수 인덱스, alias 중복 제거와 acquisition gap manifest 작성
- 역사적 완료: 국가 제한 없는 versioned multi-jurisdiction scope 변경 승인
- 역사적 완료: 공용 catalog schema의 KR 고정과 generic CLI의 암묵적 KR 기본값 제거; catalog별 공식 source host 검증
- 역사적 완료: 새 scope로 기존 23개 distinct candidate의 장면별 적격성 재평가
- 역사적 완료: 전체 로컬 licensed metadata에서 135개 candidate event/107 overlap clip screen
- 역사적 완료: 106개 sensor-eligible clip과 local materialization 증분 0개를 fail-closed 기록
- 역사적 완료: CASCADE annotation 2,066개 확보와 135-event annotation-first 분류
- 역사적 완료: 59-clip shortlist의 선택 sensor member 354개와 temporal closure 확보
- 역사적 완료: calibration feature row 295개와 recorded-rig binding 59/59 확보
- 역사적 완료: 남은 39 events의 attrition reserve와 22개 새 clip sensor/calibration 선택 확보
- 역사적 완료: 98 classified events의 temporal·calibration·recorded-rig evidence 재감사
- 역사적 완료: 공식 calibration source 재감사와 98-event source-review precheck 수행
- 역사적 완료: association-reviewable 60 events의 최소 human-review 입력 packet 생성
- 역사적 완료: 60 events×5 frames의 image-embedded review HTML과 제한 포털 메뉴 생성
- 역사적 완료: reviewer UI에서 국가·법규·source ref·source-complete 판정을 제거하고 영상 관찰 범위로 제한
- 역사적 완료: 검토 workspace의 관련 없는 목록을 기본 접고 contact sheet 폭 확대·click-to-zoom 제공
- 역사적 완료: 답변 요령 추가와 운영 문구 제거; reviewer-facing 활성 설문을 현재 M16 영상 관찰 1개로 정리
- 역사적 완료: 확대 화면의 명시적 복귀 버튼과 포털 내 화면 이동 후에도 유지되는 브라우저 자동저장 제공
- 역사적 완료: 제목의 사건 유형과 실제 대상을 구분하고 slice별 lane/zone·시간 상태 선택 순서·오답 예시를 설명하는 상세 검토 매뉴얼 제공
- 역사적 완료: 단일 검토자의 60/60 영상 관찰 JSON/CSV를 packet·slice·image hash와 대조해 restricted aggregate artifact로 확정
- 역사적 완료: NVIDIA NCore 고정 커밋으로 calibration offline variant compatibility 98/98 폐쇄
- 역사적 완료: M16 review event timestamp를 scene t0로 고정하고 수치 inverse closure로 verified transform 98/98 폐쇄
- 역사적 완료: CASCADE `because_of`/`action_target`와 optional containment를 재감사해 actor/control source SET 70/98, lane relation 1/98 폐쇄
- 역사적 완료: 완료된 영상 설문을 활성 포털에서 제거하고 source geometry 없는 curator 설문 생성을 차단
- 역사적 완료: 공개 MIT 모델과 고정 가중치로 98-event lane/drivable-area 후보를 생성하고 source video/frame/model hash에 결합
- 역사적 완료: 국가·법규·calibration·source-complete 문항 없이 overlay 확인과 normalized pixel polygon 보정만 받는 curator 화면 생성
- 역사적 완료: 업로드된 98-event source geometry curator 품질 평가 export 및 무결성 검증
- 역사적 완료: accepted 61건의 610개 mask 파일을 source-bound candidate로 결합하고 semantic geometry와 구분해 fail-closed source queue 생성
- 당시 미완료: 수동 보정 판정 37건의 normalized pixel polygon 데이터 확보
- 역사적 완료: 98-event 국제협약 normative baseline authority 결합
- 역사적 완료: 60-scene 기계 보조 전문가 source-review 화면 생성 및 활성 포털 등록
- 당시 미완료: 최소 2인 독립 전문가 확인과 불일치 adjudication
- 당시 미완료: 98-event association·outcome lifecycle source closure
- 당시 미완료: 결정된 scope에서 60개 distinct 8/8 eligible scene과 모든 joint quota 확보
- 당시 미완료: 두 UI mode의 실제 전문가 작업시간·correction 비교
- 당시 미완료: reviewer training/calibration session
- 당시 미완료: 복수 전문가 독립 annotation
- 당시 미완료: disagreement adjudication과 허용 가드 집합 작성
- 당시 미완료: 실제 annotation의 applicability α와 field별 agreement 계산
- 당시 미완료: 실제 review correction rate와 장면당 작업시간 측정
- 당시 미완료: 최대 두 차례 guideline revision 이력 보존
- 당시 미완료: 관측 cluster effect와 variance로 main N power analysis

이전 locked-KR preflight:

- [M16 source acquisition restricted run](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-source-acquisition-2026-08-13-v1/)
- 로컬 source record 33개에서 image-event alias 10개를 결정적으로 제거해 distinct event 23개
- 기존 적격 집계 4개를 개별 field에서 재감사: 8/8 closure 3개, cross-event timestamp/evidence
  conflict 1개, locked KR scope compatible 0개
- eligible 0/60, 총 60장면 부족; 세 slice 각각 0/20, 여섯 outcome 각각 0/10
- 18개 slice×outcome joint cell은 locked cell size 그대로 3~4개씩 부족
- synthetic required-field fill 0, unsourced normative/numeric value 0, annotation start `false`
- 새 eligible 0개이므로 GuardSynth→EBLC→Core→Z3 추가 실행은 수행하지 않음
- 결과 상태 `SEMANTICS_OR_SCOPE_REWORK`; 연구계획 scope는 변경하지 않았고 명시적 결정 대기
- 2026-08-14 [multi-jurisdiction 결정](../decisions/GUARDSYNTH_MULTI_JURISDICTION_PILOT_SCOPE_DECISION_V01.md)으로
  KR-only 제한을 해제했으며, 위 0/60은 새 정책 적용 전 역사적 baseline으로 유지

현재 multi-jurisdiction preflight:

- [M16 multi-jurisdiction restricted run](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-source-acquisition-2026-08-14-v3/)
- 23개 distinct candidate 중 8/8 source-complete 3개, scene jurisdiction까지 닫힌 eligible 1개
- 나머지 source-complete 2개는 촬영 관할 `UNKNOWN`, 기존 1개는 cross-event conflict로 제외
- eligible 1/60, shortfall 59; pedestrian 1/20, stop/signals 0/20, following/cut-in 0/20
- HAZARD_TRUE_ACTIVE 1/10, 나머지 다섯 outcome 0/10; annotation start `false`
- retained eligible 1개는 기존 M13 실행 근거가 있고 새 승격은 0개이므로 추가 translation 실행 없음
- [latest source-review precheck](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-source-acquisition-2026-08-14-v18/)
- annotation 2,066개 materialized; 135 events 중 classified 98, unsupported 37, multi-slice 38
- total sensor cohort 81 clips/486 members/1,448,583,496 bytes; event temporal closure 98/98
- v18 precheck calibration 405 rows/3,337,630 bytes; 당시 event calibration/rig binding 98/98,
  verified transform 0/98
- association queue actor/lane 24, actor/zone 19, control/lane 17, insufficient geometry 38
- source-review precheck `COMPLETE`; human packet 60, geometry source required 98
- human video observation 60/60 완료 후 post-review audit에서 98 events를 다시 연결하고,
  NVIDIA NCore pinned source의 offline-only 변환 규칙을 98/98 calibration variant에 적용
- M16 event-anchor 결정에 따라 review event timestamp를 scene t0로 고정하고 81개 offline
  extrinsics asset·648 rows와 egomotion 보간을 검증해 verified transform 98/98 폐쇄
- CASCADE approved annotation 98개를 hash 재검증하고 active structured relation SET 70/98,
  strict shared lane containment 1/98을 source-linked로 폐쇄; 나머지는 새 source 없이 검토 금지
- geometry source frontier session `M16_SOURCE_FRONTIER_AUDITED_EXTERNAL_SOURCES_REQUIRED`;
  curator 98/98를 검증하고 accepted 61건의 610 mask 파일을 source-bound road-geometry candidate로
  결합했지만 semantic rig geometry update 0건, new 8/8/outcome 0/0, eligible 1/60

단일 다음 작업:

- M12-R01의 source/operational-clause 재적격화부터 수행한다. 현재 60-scene 화면은 source
  curation draft이며 formal E1/E2 gold 수집 요청이 아니다. R01–R06 보완 후 검토 목적에 맞게
  배정한다. 이미 받은 영상/geometry 답변은 재사용하고 전체 재검토를 자동 요청하지 않는다.
- M16-R01에서 pixel 제출 완료·metric geometry 검증·lifecycle source·source eligibility·formal
  annotation을 별도 상태로 둔다. formal gold는 기계/선행 답을 숨긴 동일 중립 packet으로
  작성하고, 두 UI mode의 시간 비교는 별도 assistance 평가로 분리한다.

종료 gate:

- 선행 보완 gate와 60 distinct source/quota, 별도 calibration·독립 gold·adjudication 완료
- adjudication 전 applicability와 guard type α 각각 ≥0.67; 정의 불가도 미통과,
  최대 두 차례 guideline revision 후 미달 시 main annotation 중단 및 ontology/scope 재검토
- 전문가 작업시간·adjudication 예산 실측
- annotation용 main N/split과 endpoint별 power 입력 확보/미확보 판정. E4/E4-L/E6 미측정
  분산은 POWER_INPUT_PENDING으로 해당 실험 lock 전에 별도 dev로 확보

#### 이전 M17. Main gold 구축과 생성 품질·BCV·일반화 intrinsic 평가

- 계획 대응: main data, E0–E3
- 상태: `QUEUED`
- work package: `GS-E2-INTRINSIC-001`
- 선행조건: M16 독립 gold/pilot 및 M13–M15 재적격화

M17-S01 (`GS-P4-MAIN-DATA-001`) → M17-S02 (`GS-E2-INTRINSIC-001`) 순서로 실행한다.
S01은 공통 main cohort/split·독립 annotation/adjudication·gold freeze를 먼저 수행한다.
pilot/dry-run 결과는 development로 구분하고 S02의 확증 성능으로 재사용하지 않는다.

Todo:

- 당시 미완료: applicability macro-F1과 type/target/operator 정확도
- 당시 미완료: M17-S01 power-based main cohort·group split·독립 gold와 누출/노출 감사 완료
- 당시 미완료: B0–B13·E2-FF-MATCHED 실행, 동일정보 비교와 input/representation/BCV ablation 보고
- 당시 미완료: pinned platform release·source-map·CNL/IR/SMT/monitor/planner 지원 target별 응용 conformance
- 당시 미완료: BCV 대 SMT-only/replay-only/outcome-only 비교, false alarm·결함 localization·독립 oracle 판정
- 당시 미완료: macro-F1·구조·unit/frame·provenance·compile·false rejection·OOD 수치를 상위 목표 전수 대조
- 당시 미완료: unit/frame, numeric-range와 provenance 정확도
- 당시 미완료: `VALIDATED` precision과 coverage를 분리 보고
- 당시 미완료: hallucinated source/numeric value 측정
- 당시 미완료: under/over/lifecycle/translation mutation recall
- 당시 미완료: flat contract 대비 EBLC semantic/lifecycle/false-deadlock 비교
- 당시 미완료: CoC+scene 대 CoC-only/scene-only 비교
- 당시 미완료: shuffled-CoC와 paraphrase ablation
- 당시 미완료: OOD maneuver/source/dataset generalization
- 당시 미완료: confidence interval, paired test와 failure taxonomy
- 당시 미완료: 모든 사전 Go/No-Go gate 판정

종료 gate:

- CoC+scene가 scene-only보다 ≥3%p 개선하지 못하면 CoC-centric claim 제거
- strongest applicability baseline보다 macro-F1 5%p 개선 및 CI gate
- `VALIDATED` precision ≥0.90
- BCV mutation recall ≥0.90, translation agreement ≥0.99
- E0 정상 compile ≥0.98, 주입 오류 recall ≥0.95, false alarm ≤0.05 및 두 독립 evaluator 일치 ≥0.99
- lifecycle stale/missed-reactivation 상대 오류 감소 ≥30% gate; Project 05 일반 언어 결과와
  GuardSynth 응용 결과를 분리하며 generic language 신규성은 가져오지 않음

#### 이전 M18. EBLC 학습 효과와 독립 closed-loop 평가

- 계획 대응: P5/E4·E4-L, RQ5/H5·H5-L
- 상태: `QUEUED`
- work package: `GS-P5-OUTCOME-001`
- 필수 학습 work package: `GS-P5-LEARNING-001` (E4-L)
- 선행조건: M16 pilot/power analysis, M17 생성 품질 gate; 독립 evaluator는 M18-S01에서 확보
- 상세 요구사항: [M18_EBLC_LEARNING_EFFECT_REQUIREMENTS_V01.md](../requirements/M18_EBLC_LEARNING_EFFECT_REQUIREMENTS_V01.md)
- 보완 근거: [EBLC_LEARNING_EVALUATION_DECISION_V01.md](../decisions/EBLC_LEARNING_EVALUATION_DECISION_V01.md)

필수 하위 마일스톤:

| 단계 | 작업 | 상태 | 선행조건 | 종료 근거 |
|---|---|---|---|---|
| M18-S01 | 생성기·학습 labeler와 독립된 outcome evaluator 확보 | `QUEUED` | M17 | 규칙/코드 독립성 audit, oracle tests |
| M18-S02 | 학습 protocol·모델·예산·학습 증분 cohort 동결 | `QUEUED` | M17 공통 split/gold, S01, 학습 endpoint dev power | checkpoint/architecture, loss, ≥3 paired seeds, sample-size rationale, inherited split/compute manifest |
| M18-S03 | 동일 장면·후보 trajectory의 L0–L3 학습 신호 생성·감사 | `QUEUED` | S02 | source-bound label artifacts, abstention/coverage, split contamination audit |
| M18-S04 | 동등 예산 실제 가중치 학습과 ablation 실행 | `QUEUED` | S03 | seed별 checkpoint, optimizer/update/compute logs, lifecycle-off·BCV-off runs |
| M18-S05 | shield 없는 학습 효과 평가·통계·결론 확정 | `QUEUED` | S04 | 독립 held-out closed-loop 결과, violation·nominal progress CI, shield 추가 대조, E4-L report |
| M18-S06 | 기존 runtime 적용 효과·진행성 평가 | `QUEUED` | S01, S02 protocol freeze | E4 runtime report, learning/runtime claim 분리 |

S02–S05는 `GS-P5-LEARNING-001`에 속한다. S06은 동결된 평가 조건 안에서 병렬 실행 가능하나
S05를 대체하지 않는다. M16의 60장면은 pilot이며 전체 학습 데이터로 간주하지 않는다.
공통 main split/gold는 M17-S01에서 확보한다. 학습 증분 표본 수·split binding은 S02에서
확보·동결하며 pilot annotation 분산을 learning power로 대체하지 않는다. M20은 이 동결본과
보고서를 통합한다.

학습 Todo (E4-L):

- 당시 미완료: 동일 trainable trajectory model·초기 checkpoint·장면·후보·optimizer·업데이트 예산 고정
- 당시 미완료: L0 기본 학습 / L1 free-form 신호 / L2 flat·event-local 신호 / L3 GuardSynth EBLC+BCV 신호 비교
- 당시 미완료: 동일 loss frame과 공통 goal supervision 아래 guard 신호만 변경; test split 학습 유입 금지
- 당시 미완료: ≥3 paired training seeds와 lifecycle-off·BCV-off ablation의 실제 가중치 갱신 실행
- 당시 미완료: 주평가에서는 추가 EBLC 입력·외부 verifier·reranker·shield 없이 동일 inference 조건 적용
- 당시 미완료: 독립 evaluator로 violation과 nominal goal completion, deadlock·불필요 정지·coverage 측정
- 당시 미완료: seed/scene 변동, 다중 비교, compute disparity와 matched-coverage sensitivity 보고
- 당시 미완료: 실제 checkpoint·학습 로그·비용·held-out 결과·부정 결과를 E4-L 보고서로 등록

Runtime Todo (E4):

- 당시 미완료: generator와 코드·규칙을 공유하지 않는 evaluator 구현
- 당시 미완료: 기록 replay와 독립 physics oracle
- 당시 미완료: counterfactual perturbation/hard negative 생성
- 당시 미완료: 경량 closed-loop simulator 또는 MetaDrive/CARLA 핵심 scene 재현
- 당시 미완료: no-guard/free-form/baseline/GuardSynth 동일 조건 비교
- 당시 미완료: rule/safety violation, collision proxy와 TTC 계열 지표
- 당시 미완료: goal completion, deadlock, unnecessary stop, false rejection 측정
- 당시 미완료: lifecycle reappearance/occlusion stress
- 당시 미완료: paired/clustered confidence interval과 residual risk 보고
- 당시 미완료: E4 held-out scene별 10–20 perturbations, 조건별 ≥3 seeds, 독립 rollout ≥2,000의 집계
  단위를 lock하고 paired 조건별 실제 실행 수·독립 scene 수를 분리 보고(미달은 full protocol 미완료)
- 당시 미완료: always-stop/always-yield와 matched nominal control, generator/BCV dev 반례와 test seed 분리

종료 gate:

- E4-L: S02–S05 실제 실행·재현 보고서 필수; protocol 작성 또는 runtime-only 결과는 대체 불가
- 학습 효과 지지 기준: 사전 지정 대조군 대비 L3 violation 차이의 95% CI 상한 <0,
  nominal completion 차이의 CI 하한 ≥−5%p; 독립 평가·동등 예산·coverage 조건 함께 충족
- 학습 결과 `SUPPORTED | NOT_SUPPORTED | INCONCLUSIVE`를 대조군별 보고. 부정/불확정 결과도
  실행·보고 요건을 충족하면 완료 가능하나 학습 효용 주장은 그에 맞춰 축소; `NOT_EVALUATED`는 미완료
- E4 runtime: no-guard 대비 violation 상대 감소 ≥30%, free-form 대비 ≥15% 목표
- E4 runtime: goal completion 절대 손실 ≤5%p
- 독립 evaluator 미확보 시 full outcome claim NO-GO

#### 이전 M19. Alpamayo CoC 실제 적용

- 계획 대응: P6/E5
- 상태: `QUEUED`
- work package: `GS-P6-ALPAMAYO-001`
- 선행조건: M17, M18 runtime phase gate와 E4-L 실행·보고 완료

M19는 Alpamayo external monitor/shield 적용 단계이며 M18의 실제 학습을 대체하지 않는다.
E4-L의 부정 결과 자체는 runtime 적용을 금지하지 않지만 학습 효용 주장의 근거로 쓰지 않는다.
Alpamayo 자체 fine-tuning은 license·자원·실험 protocol을 별도 확정한 경우에만 포함한다.

Todo:

- 당시 미완료: restricted Alpamayo CoC/trajectory adapter version 고정
- 당시 미완료: M19-R01: 최소 100개 event×3 paired action seeds를 각 비교 조건에 동일 적용하고 실제 run 수 보고
- 당시 미완료: native/free-form/proposed/expert 비교와 길이 맞춘 반대 의미·무관 guard negative controls
- 당시 미완료: CoC claim과 실제 scene evidence 분리
- 당시 미완료: generated constraint를 external monitor/shield input으로 연결
- 당시 미완료: prompt-only, structured input, verifier, reranker, shield 조건 분리
- 당시 미완료: nominal/hazard/occlusion/reappearance case 실행
- 당시 미완료: no-guard와 matched control 비교
- 당시 미완료: restricted 상세와 public aggregate 분리
- 당시 미완료: prompt semantics가 약할 때 external verifier/shield 결과만 보고

종료 gate:

- phase-gated E5 report
- full protocol 미달 표본은 feasibility로만 보고; NO-GO 시 사유·미실행 주장·축소 범위를 기록
- 실제 source 누락을 추정으로 채운 사례 0건
- 효과가 없으면 Alpamayo-centric claim 축소

#### 이전 M20. Main GuardBench·전문가 효용·논문·출원 gate

- 계획 대응: main study/E6/산출물
- 상태: `QUEUED`
- work package: `GS-MAIN-PAPER-001`
- 선행조건: M16, M17–M18 실행·보고 및 claim disposition, M19 실행 보고 또는 명시적 조건부
  NO-GO disposition, E4-L 실제 학습·평가 보고서(면제 불가)

Todo:

- 당시 미완료: M17-S01에서 동결한 power-based main GuardBench 장면 수·split·gold manifest 확인
- 당시 미완료: M18에서 동결·사용한 학습 cohort/split을 통합하고 test 재사용·사후 튜닝 여부 감사
- 당시 미완료: E4-L checkpoint·학습/compute 로그·독립 평가·CI·ablation 보고서 확인
- 당시 미완료: 학습 효용과 runtime shield 효용을 별도 결과표·주장으로 작성
- 당시 미완료: 핵심 주장별 RQ/H → work package → 대조군·지표 → 실제 artifact 대응표 감사
- 당시 미완료: M17-S01 main annotation/adjudication 결과와 독립성 감사 통합
- 당시 미완료: M17–M19 baseline/GuardSynth locked evaluation 결과 통합; test 재실행을 tuning에 사용하지 않음
- 당시 미완료: 전문가 작성·검토 시간과 승인율 평가
- 당시 미완료: M20-R01: scratch/free-form 수정/proposed 수정의 3-arm 균형 무작위 배정·노출 분리
- 당시 미완료: 중대한 오류 비증가·수정량·workload·source 확인·QA/adjudication 총 비용 및 CI 보고
- 당시 미완료: missing/unsupported/conflict와 부정 결과 포함
- 당시 미완료: preregistered 통계와 sensitivity analysis
- 당시 미완료: 데이터/model/prompt/KB/schema/evaluator version manifest
- 당시 미완료: 공개 코드·synthetic fixture·비식별 통계 artifact
- 당시 미완료: 제한 데이터 license/confidentiality 감사
- 당시 미완료: failure taxonomy와 residual risk 작성
- 당시 미완료: 주장 수준에 맞는 target venue 결정
- 당시 미완료: 논문 본문·부록·재현 패키지 완성
- 당시 미완료: 공개 전 발명사항과 공개 범위 정리
- 당시 미완료: 특허 출원 필요성 검토 및 출원하기로 결정한 경우 출원 신청 완료

종료 gate:

- 최소/목표/확장 성공 수준 중 실제 달성 수준 명시
- E4-L 미실행 또는 protocol-only 상태이면 현재 범위의 M20 종료 불가; 학습 보고서 누락을
  scope 축소로 자동 면제하지 않으며 변경이 필요하면 명시적 scope 재승인
- 실제 실험의 부정/불확정 결과는 허용하되 학습 효용을 입증했다고 쓰지 않음
- 전문가 중대한 수정 없는 승인 ≥70% 목표
- 작성/검토 시간 감소 ≥30% 목표
- 시간 감소와 중대한 오류 비증가를 함께 판정; source 확인 시간만으로 전체 효용을 주장하지 않음
- 결과가 gate 미달이어도 기대값을 바꾸지 않고 축소된 결론으로 보고
- 실제 차량 실증 전 논문 원고·재현 패키지와 적용 가능한 출원 절차 완료

#### 이전 M21. 출원·논문 이후 실제 차량 실증

- 계획 대응: post-research actual-vehicle validation
- 상태: `QUEUED`
- work package: `GS-POST-ACTUAL-VEHICLE-001`
- 선행조건: M20, 실제 차량/시험 권한, 실제 vehicle assurance source, 안전·법무 승인

Todo:

- 당시 미완료: 대상 차량과 DBW/runtime capability를 정확히 binding
- 당시 미완료: OEM 자료 또는 통제시험 기반 response/deceleration/uncertainty assurance 작성
- 당시 미완료: simulation profile과 실제 vehicle profile을 교체 가능하게 version 고정
- 당시 미완료: 폐쇄 시험장·안전운전자·중단 조건을 포함한 시험계획 승인
- 당시 미완료: 실제 차량 적용 전 SIL/HIL과 shadow monitor 수행
- 당시 미완료: 단계별 nominal/hazard/occlusion/reappearance 실증
- 당시 미완료: 기록·사고·개입·중단 로그와 residual risk 보존
- 당시 미완료: simulation 결과와 실제 결과의 차이 및 외삽 한계 보고

종료 gate:

- 실제 vehicle binding과 assurance source completeness 100%
- 승인된 안전 절차 밖의 시험 0건
- simulation/실차 결과를 분리 보고
- 실제 결과가 기존 주장과 다르면 논문·특허 후속 공개에서 차이를 숨기지 않음

완료 경계: 이 단계 전까지 GuardSynth 결과는 실제 차량 안전성 또는 배포 승인 근거로
사용하지 않는다.

#### 이전 갱신 규칙 6. 매 마일스톤 갱신 절차

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
`01_RESEARCH_PLAN_V02.md`의 후속 버전과 변경 이유를 먼저 기록한 뒤 마일스톤을 동기화한다.

</details>
