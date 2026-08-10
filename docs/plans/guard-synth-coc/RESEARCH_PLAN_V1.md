# 상황 인지형 근거-생명주기 실행 계약의 합성 및 양방향 검증 연구계획서 v1

- 버전: v1.2 original constraint and verification method
- 기준일: 2026-08-08
- 연구 약칭: GuardSynth-CoC
- 영문명: *Synthesis and Bidirectional Verification of Context-Aware Evidence-Bound Lifecycle Contracts for Driving*
- 기반 연구: Safety-Constrained CoC
- 1차 목표 저널: IEEE Transactions on Intelligent Vehicles
- 상향 목표 저널: IEEE Transactions on Intelligent Transportation Systems
- 안전성 중심 대안: Reliability Engineering & System Safety
- 상태: 연구 범위 및 사전 성공 기준 정의
- 전략 근거: [2026 선행연구 서베이와 기술 전략](../../surveys/guard-synth-coc/CONTEXT_AWARE_GUARD_SYNTHESIS_SURVEY_AND_STRATEGY_V1.md)
- 현재 실행 기준: [GuardSynth-CoC 프로젝트 실행 추적표](PROJECT_EXECUTION_TRACKER.md)
- 전체 마일스톤/Todo: [GuardSynth-CoC 전체 마일스톤 원장](PROJECT_MILESTONES.md)
- 과거 P0b 구현 요구사항: [GuardSynth-CoC P0b 설계ㆍ구현 프롬프트](../../requirements/guard-synth-coc/P0B_IMPLEMENTATION_REQUIREMENTS.md)

### v1.2 변경 이유와 영향

2026년 선행연구 감사에서 regulation RAG, scene-aware rule filtering, LLM+formal rule+reachability가 각각 DriveReg, RTCD4ADS, SanDRA에서 다뤄짐을 확인했다. 이들은 배제할 대체재가 아니라 검색, runtime rule activation, reachability filtering을 담당하는 **채택 가능한 구성요소이자 강한 비교 구현**이다. 본 연구는 세 구성요소를 연결하는 데 그치지 않고, 그 사이에서 아직 정의되지 않은 두 방법을 중심 기여로 둔다.

1. **EBLC Graph(Evidence-Bound Lifecycle Contract Graph, 가칭):** 규칙 근거, 장면 적용성, 객체 grounding, 수치 유도, 활성ㆍ유지ㆍ해제ㆍ재활성, 우선순위와 fallback을 하나의 typed 실행 계약 그래프로 표현하고 합성하는 독자 제약 설계
2. **BCV(Bidirectional Contract Verification, 가칭):** 위험ㆍ규칙위반 궤적을 잘못 허용하는 과소제약과 안전ㆍ합법ㆍ진행 가능한 궤적을 잘못 거부하는 과잉제약을 동시에 반례로 탐색하고, lifecycle 및 compiler 의미보존까지 확인하는 독자 검증 방법

SEBGI는 EBLC Graph를 만드는 선택적 합성 절차로 유지한다. 12–20개 template과 세 vertical slice는 전체 연구 영역의 상한이 아니라 P0 구현ㆍ감사 gate 및 깊은 수치/lifecycle/closed-loop 검증 범위다. 여섯 행동군은 broad applicability benchmark로 유지하고, `24 dry-run → 60 pilot → power-based main`, 독립 semantic/closed-loop 평가와 2026 구성요소 baseline을 적용한다.

### 0차 실행 파일럿 상태

2026-08-08에 synthetic 보행자 conflict-zone system requirement 하나로 [EBLC executable pilot](../../../experiments/eblc_pilot/README.md)을 실행했다. rule retrieval, target/numeric binding, `ACTIVE→MAINTAINED→RELEASED→REACTIVATED→RELEASED`, 활성 중 conflict-zone 진입 거부, `UNKNOWN` hold fallback, missing profile abstention 및 BCV under/overconstraint mutation을 7개 테스트로 확인했다. 상세 결과는 [baseline report](../../../artifacts/results/public/eblc-pilot-v0/pilot-2026-08-08/REPORT_KO.md)에 있다. 이는 **기계적 실행 가능성 증거**일 뿐 실제 법규의 타당성, 실제 센서 grounding, 독립 oracle 또는 차량 안전성 증거가 아니므로 E-1/E0 gate 통과로 계산하지 않는다.

### P0b 실행 상태

2026-08-10의 후속 P0 catalog 단계에서 대한민국을 최초 관할로 고정하고 도시·근교
structured-road ODD, 세 deep slice와 source hierarchy를 결정했다. [scope decision](../../decisions/GUARDSYNTH_KR_SCOPE_AND_SOURCE_POLICY_V1.md)과
[source catalog audit](../../../artifacts/results/public/guardsynth-source-catalog-001/kr-source-catalog-2026-08-10-v2/REPORT_KO.md)은
공식 source record 6개/claim 16개, template 15개(5/6/4), six-family 6/6,
failure-to-UNKNOWN 11/11, source 없는 규범·실행 수치 0건을 기록했다. 따라서 P0/E-1
catalog gate는 통과했다. 다만 [24-slot readiness](../../../artifacts/results/public/guardsynth-24-scene-dry-run-001/kr-dry-run-readiness-2026-08-10-v1/)에서
실제 source-complete scene은 여전히 0/24이므로 P1은
`M13_BLOCKED_SOURCE_COMPLETE_SCENES`다. 이는 source 추적성 gate이지 법률 자문,
실제 장면 정확도 또는 차량 안전성 증거가 아니다.

2026-08-08에 `EBLC-P0B-001`을 실행했다. [P0b report](../../../artifacts/results/public/eblc-p0b-001/p0b-2026-08-08-v1/REPORT_KO.md)에서 P0a 회귀 7/7, P0b 테스트 21/21, schema fixture 4/4, canonical–runtime 8/8 및 canonical–bounded-enumerator 8/8 agreement, controlled under/over mutation 각 5/5 검출, 정상 false alarm 0건과 missing-input abstention 4/4를 기록했다. z3-solver가 현재 환경에 없어 결과는 SMT가 아닌 exhaustive finite-state enumerator다. 로컬 제한 파생 자산은 필수 conflict-zone geometry, pedestrian-zone association, time-aligned ego state/frame bundle 및 vehicle assurance profile이 함께 없어 `P0B_REAL_ADAPTER_BLOCKED_DATA_GAP`으로 기록했다. 따라서 schema/translation/mutation gate는 통과했지만 실제 24-scene 연결 전 판단은 **DATA-GAP PIVOT**이며, 이 결과도 실제 법규ㆍ센서ㆍ차량 안전성 또는 독립 safety oracle의 증거가 아니다.

후속 [multi-environment robustness audit](../../../artifacts/results/public/eblc-robustness-audit-001/robustness-multienv-2026-08-08-v3/REPORT_KO.md)는 기본 Python과 z3 4.16.0 환경에서 P0a 7/7, 확장 P0b 38/38 및 1,024개 4값 길이-5 trace의 세 target agreement를 재확인했지만, 적대적 13개 probe 중 8개 gap을 발견했다. non-finite scene/profile 수용, empty/non-monotonic trace 수용, runtime parameter schema 누락, 실제 solver construction 없는 `Z3_BOUNDED_SMT` label 및 환경과 모순되는 report 문구가 포함된다. 따라서 24-scene data 연결보다 fail-closed validation과 실제 SMT target을 먼저 수정해야 하며 현재 판단은 **SEMANTICS REWORK**로 교정한다.

후속 data-gap adapter 실행에서는 [restricted report](../../../artifacts/results/restricted/eblc-p0b-001/p0b-data-adapter-2026-08-08-v1/REPORT_KO.md)와 같이 기존 파생 obstacle event와 recorded ego future만 결합해 VRU 후보 5개 중 4개의 schema-valid partial ContextGraph를 만들었다. 그러나 4개 모두 복수 corridor 후보로 target association이 불명확하고 vehicle assurance profile 및 rig→canonical frame 검증이 없어 contract는 4/4 `UNSUPPORTED`다. 따라서 geometry/ego-state gap은 부분 축소됐지만 24-scene gate 판단은 계속 **DATA-GAP PIVOT**이다.

실제 SMT target 보강 후 [Z3 P0b report](../../../artifacts/results/public/eblc-p0b-001/p0b-z3-smt-2026-08-08-v4/REPORT_KO.md)는 프로젝트 로컬 Z3 5.0.0과 별도 `z3.Solver` 인코딩을 사용해 P0a 7/7, P0b 41/41, canonical–runtime 및 canonical–Z3 agreement 각 8/8, controlled under/over mutation 각 5/5를 기록했다. 네 bounded query도 기대 방향(SAT 1, UNSAT 3)과 일치해 이전의 “solver construction 없는 SMT label” 결함은 해결됐다. 그러나 [최신 robustness audit](../../../artifacts/results/public/eblc-robustness-audit-001/robustness-z3-smt-2026-08-08-v5/REPORT_KO.md)는 13개 probe 중 7개 통과, 6개 fail-closed gap을 남겼다. non-finite 값, empty/non-monotonic trace 및 runtime parameter schema coverage를 먼저 보강해야 하며, 실제 장면 연결 판단은 필수 association/profile 부족으로 계속 **DATA-GAP PIVOT**이다. 이 결과는 bounded software semantics와 controlled mutation 검출 근거일 뿐 독립 safety oracle이나 실제 차량 안전성 증거가 아니다.

후속 `EBLC-P0B-S1` 보강은 [fail-closed P0b report](../../../artifacts/results/public/eblc-p0b-001/p0b-fail-closed-2026-08-08-v1/REPORT_KO.md)와 [robustness report](../../../artifacts/results/public/eblc-robustness-audit-001/robustness-fail-closed-2026-08-08-v6/REPORT_KO.md)에 기록했다. schema/semantics v0.2와 compiler v0.3은 non-finite JSON/profile/scene/contract 값, empty trace, decreasing timestamp를 fail closed로 거부하고 runtime parameter와 derivation DAG를 schema 필수 필드로 고정했다. P0a 7/7, P0b 43/43, translation 각 8/8, mutation 각 5/5를 유지하면서 고정 강건성 probe를 13/13, gap 0으로 통과해 **SEMANTICS REWORK 항목은 이 probe 범위에서 종료**한다. 다음 판단은 실제 associationㆍframe transformㆍvehicle assurance profile 부족에 대한 **DATA-GAP PIVOT**이며, 이 결과도 차량 안전성 증거는 아니다.

후속 `EBLC-CORE-SMT-001`은 [Core→SMT report](../../../artifacts/results/public/eblc-core-smt-001/core-smt-2026-08-08-v4/REPORT_KO.md)에 기록했다. 공개 Core v0.1 schema, typed AST/parser, unitㆍframeㆍtime fail-closed checker와 domain-neutral bounded Z3 lowering을 구현해 SMT-LIBㆍsymbol tableㆍassertion-index source mapㆍquery manifest를 산출했다. synthetic P0b 대표 fixture의 7개 query는 기대 SAT/UNSAT 방향과 7/7 일치했고 Core 전용 12/12, 전체 P0b 55/55를 통과했다. 생성 SMT-LIB 8개도 project-local Z3 실행 파일에서 8/8 동일하게 재실행됐다. 이는 bounded 문법/컴파일러 구현 gate 통과이며, 모든-input canonical 의미 동등성이나 차량 안전성 증명이 아니다. 다음 compiler 작업은 generated finite trace semantic-conformance harness다.

후속 `EBLC-ELABORATION-CONFORMANCE-001`은 [실행 보고서](../../../artifacts/results/public/eblc-elaboration-conformance-001/elaboration-conformance-2026-08-08-v3/REPORT_KO.md)에 기록했다. 수식 AST가 없는 고수준 program에서 freshness, policy-disallowed epistemic-to-UNKNOWN, activation/maintenance/release/reactivation/expiry/fallback, verdict, stop/speed/deadlock violation과 progress permission을 Core로 자동 전개했다. canonical과 Core-SMT는 129개 생성 traceㆍ266개 frame의 lifecycle, clear counter, verdict, 세 위반과 progress 결과에서 100% 일치했으며 elaborator 11/11, 전체 P0b 66/66, P0a 7/7, SMT-LIB replay 2/2를 통과했다. 이것은 semantic-conformance harness gate 통과이며 elaborator가 canonical 명세로부터 개발됐으므로 독립 safety oracle이 아니다. 다음 언어 작업은 다중 계약 composition과 non-scalar priority conflict semantics다.

후속 `EBLC-SCENARIO-TEST-001`은 [다각도 단위ㆍ통합 보고서](../../../artifacts/results/public/eblc-scenario-test-001/scenario-matrix-2026-08-08-v3/REPORT_KO.md)에 기록했다. 44개 명시적 case로 schema/program 음성 입력, lifecycle/UNKNOWN/expiry/deadlock 정책, 정지 위치ㆍ동적 속도ㆍfreshness의 경계 직전/동일/직후와 failure precedence를 검사했다. 최초 실행에서 binary-float 연산 때문에 ideal-real Core-SMT와 freshness 경계 두 건이 어긋나는 결함을 발견했고, 의미 epsilon `1e-9`와 구분되는 roundoff guard `1e-15`를 canonical/runtime/enumerator에 적용해 동일 기대값으로 재실행했다. scenario 11/11, Core-SMT 12/12, elaboration 11/11, robustness 10/10, 전체 P0b 77/77, P0a 7/7을 통과했다. 언어 구현의 다음 작업은 여전히 다중 계약 composition과 non-scalar priority conflict semantics이며, 실제 장면 단계 판단은 association/profile 부족에 따른 **DATA-GAP PIVOT**을 유지한다.

2026-08-09의 `EBLC-COMPOSITION-COMPILATION-001`은 [composition 실행 보고서](../../../artifacts/results/public/eblc-composition-compilation-001/composition-compilation-2026-08-09-v1/REPORT_KO.md)에 기록했다. 단일 `eblc-program-v0.1`을 보존하면서 둘 이상의 program, 유한 action domain, `HARD > SERVICE > PREFERENCE` tier 및 비순환 명시 override를 갖는 `eblc-bundle-v0.1`을 추가했다. priority는 scalar weight로 변환하지 않으며 선택 계약 action 교집합이 빈 hard-hard 충돌은 `CONFLICT`, 다른 동급 충돌은 `REVIEW_REQUIRED`로 남긴다. bundle을 namespaced Core v0.1로 생성한 뒤 generic Core compiler로 실제 SMT-LIB/Z3에 연결했고, 기존 기준선 77/77, 신규 composition 12/12, 전체 EBLC 89/89, P0a 7/7, canonical–Core-SMT composition scenario 5/5 및 SMT-LIB 직접 replay 2/2를 통과했다. 따라서 **현재 bounded bundle v0.1 범위의 다중 계약 composition과 고수준→Core→SMT gate는 통과**했지만, 실제 장면 단계는 여전히 association/profile 부족에 따른 **DATA-GAP PIVOT**이며 독립 safety oracle이나 차량 안전성을 입증하지 않는다.

같은 날 `EBLC-DERIVATION-COMPILATION-001`은 [typed derivation 실행 보고서](../../../artifacts/results/public/eblc-derivation-compilation-001/typed-derivation-2026-08-09-v1/REPORT_KO.md)에 기록했다. RED test를 먼저 고정한 뒤 sourced value와 기존 Core variable, `ADD/SUB/MUL/DIV/NEG/MIN/MAX`, 명시적 output binding을 갖는 `eblc-derivation-v0.1`을 구현했다. synthetic stop position의 정적 binding을 `0.0 m - 1.5 m` typed DAG로 교체했고 Z3 exact witness `-3/2`, locked canonical–Core-SMT trace 8/8, 구현 전 기준선 89/89, 신규 derivation 11/11, 전체 EBLC 100/100, P0a 7/7 및 SMT-LIB replay 2/2를 통과했다. 이는 **companion typed derivation→Core→SMT gate 통과**이며 free-form operation 문자열은 계속 실행하지 않는다. 다음 언어 작업은 이 companion spec의 program v0.2 내장과 전체 dynamic stopping-bound DAG 확장이다.

후속 `eblc-program-v0.2` 통합은 [표적 조사ㆍ설계](../../designs/guard-synth-coc/EBLC_PROGRAM_V02_TYPED_DERIVATION_PLAN.md)와 [실행 보고서](../../../artifacts/results/public/eblc-elaboration-conformance-001/elaboration-conformance-2026-08-09-v02-typed-derivation-v4/REPORT_KO.md)에 기록했다. v0.1 호환성을 유지하면서 typed derivation을 고수준 program에 직접 내장하고, stop position부터 epsilon-adjusted/clamped speed, response distance, braking distance 및 total stopping distance까지 한 source-bearing DAG로 생성했다. speed-violation clause는 이 DAG의 `stopping_distance` 출력을 실제 참조한다. v0.2 신규 테스트 11/11, 전체 EBLC 111/111, P0a 7/7, canonical–Core-SMT 129 trace/266 frame, SMT-LIB replay 2/2가 통과했고 Z3 exact witness는 `stop_position=-3/2`, `stopping_distance=9`였다. 따라서 **단일 program v0.2의 고수준 EBLC→typed derivation→Core→SMT gate는 통과**했다. 다음 언어 작업은 v0.2 program을 bundle composition 경로에 전달하는 것이며, 실제 장면 판단은 association/profile 부족에 따른 **DATA-GAP PIVOT**을 유지한다.

후속 bundle 전파는 [설계](../../designs/guard-synth-coc/EBLC_BUNDLE_V02_DERIVATION_PROPAGATION.md)와 [실행 보고서](../../../artifacts/results/public/eblc-composition-compilation-001/composition-v02-typed-derivation-2026-08-09-v2/REPORT_KO.md)에 기록했다. `eblc-bundle-v0.1` 안의 각 v0.2 program을 독립 namespace로 전개하고 typed derivation output과 `DIV` definedness를 Core/SMT까지 보존했다. 두 계약의 exact stopping-distance witness는 각각 `9`, `3`이고 definedness assertion은 18개였다. 구현 전 기준선 111/111, 신규 8/8, 전체 EBLC 119/119, P0a 7/7, canonical–Core-SMT composition scenario 5/5 및 SMT-LIB replay 2/2를 통과했다. 따라서 **v0.2 다중 계약의 고수준 EBLC→typed derivation→composition→Core→SMT gate는 통과**했다. 다음 단일 언어 작업은 다중 actor/zone binding과 quantified/indexed contract collection의 최소 문법을 설계하는 것이며, 실제 장면 판단은 association/profile 부족에 따른 **DATA-GAP PIVOT**을 유지한다.

후속 indexed collection은 [설계](../../designs/guard-synth-coc/EBLC_INDEXED_COLLECTION_V01.md)와 [실행 보고서](../../../artifacts/results/public/eblc-indexed-collection-001/indexed-collection-2026-08-09-v1/REPORT_KO.md)에 기록했다. 하나의 v0.2 template과 두 actor–zone instance를 `eblc-indexed-collection-v0.1`로 표현하고 target, zone, geometry, coordinate transform 및 sourced zone-entry가 모두 확인될 때만 bundle을 생성했다. 모호ㆍ미지원ㆍ상충 association은 일부 계약만 실행하지 않고 각각 `REVIEW_REQUIRED`, `UNSUPPORTED`, `CONFLICT`로 전체 확장을 중단한다. Z3 exact stop position은 `-3/2`, `21/2`, stopping distance는 `9`, `3`이었고 구현 전 기준선 119/119, 신규 9/9, 전체 EBLC 128/128, P0a 7/7 및 SMT-LIB replay 2/2를 통과했다. 따라서 **제한된 다중 actor/zone indexed expansion gate는 통과**했다. 다음 단일 구현은 RuleTemplateㆍContextGraphㆍVehicleProfile에서 이 collection을 만드는 공개 source-aware generator/binder interface이며, 실제 Alpamayo 적용 판단은 association/profile 입력 확보 전까지 **DATA-GAP PIVOT**을 유지한다.

2026-08-09 EBLC v0.2 RC 동결은 [언어 명세](../../specifications/eblc/EBLC_LANGUAGE_SPEC_V02.md),
[요구사항 추적표](../../reports/EBLC_REQUIREMENT_TRACEABILITY_V02.md)와
[release notes](../../releases/EBLC_RELEASE_NOTES_V02.md)에 기록한다. 결정론적 EBLC→CNL
projection을 마지막 범위로 추가하고, 기존 128-test baseline, 신규 renderer 10 tests,
전체 EBLC 138 tests, P0a 7 tests, canonical–Core-SMT program 129 traces/266 frames와
bundle smoke agreement를 RC gate로 고정한다. 일반 exception algebra, quantifier,
continuous/hybrid dynamics 및 CoC→EBLC 자동 생성은 완료로 간주하지 않고 별도 버전 또는
GuardSynth 계층으로 이관한다. RC 실행 결과는
[`EBLC-RELEASE-CANDIDATE-001`](../../../artifacts/results/public/eblc-release-candidate-001/eblc-v0.2-rc1-2026-08-09/REPORT_KO.md)에 둔다.

후속 GuardSynth generator v0.1은 [설계](../../designs/guard-synth-coc/GUARDSYNTH_SOURCE_AWARE_GENERATOR_V01.md)와
[실행 보고서](../../../artifacts/results/public/guardsynth-source-aware-generator-001/source-aware-generator-2026-08-09-v3/REPORT_KO.md)에 기록했다.
EBLC 의미를 변경하지 않고 별도 `src/guard_synth` 계층에서 RuleTemplate/PredicateSpec
catalog, structured ContextGraph, VehicleProfile과 explicit compiler/composition policy를
program v0.2 및 indexed collection으로 생성했다. CoC reference는 `CLAIMED`로만 보존하고
activation evidence에서 제외했다. EBLC RC 기준선 138/138, 신규 12/12, 전체 150/150,
P0a 7/7, 구조 9/9 및 SMT-LIB replay 2/2를 통과했다. claim-only, missing profile/geometry,
ambiguous target, duplicate binding, unit mismatch 여섯 probe는 collection을 생성하지
않았다. 다음 판단은 실제 source authoring 입력 부족에 따른 **DATA-GAP PIVOT**이며,
scene association/geometry/transform adapter와 vehicle assurance registry를 먼저 구축한다.

P0b software 범위의 최종 종료 판단은
[GuardSynth-CoC P0b 종료 판정](../../reports/GUARDSYNTH_P0B_TERMINAL_DECISION_V1.md)과
[24-slot 공개 집계 결과](../../../artifacts/results/public/guardsynth-real-scene-readiness-001/terminal-readiness-2026-08-09-v3/REPORT_KO.md)에 고정했다.
source-bearing vehicle assurance registry와 fail-closed source authoring interface를 구현했고,
source authoring 8/8, source-boundary adversarial 14/14, 전체 maintained
EBLC/GuardSynth 172/172, 구조/링크 9/9를 통과했다. 철저 테스트의 발견 결함과
잔여 위험은 [별도 보고서](../../reports/GUARDSYNTH_SOURCE_BOUNDARY_THOROUGH_TEST_V1.md)에 둔다.
로컬 후보는 5/24, partial ContextGraph는 4개, source-complete scene은 0/24였으며
나머지 19 slot은 synthetic 값 없이 `MISSING_SCENE_INPUT`으로 보존했다. 따라서 software
구현 상태는 `EXECUTED`, 연구 단계는 **DATA-GAP PIVOT**으로 종료한다. association,
검증된 rig→ego-path transform, source-bearing vehicle assurance와 총 24개 실제 장면이
확보되기 전에는 EBLC 기능 확장을 반복하지 않는다.

2026-08-10에는 P1 입력 병목을 줄이기 위해
[label-light grounding v0.1 설계](../../designs/guard-synth-coc/GUARDSYNTH_LABEL_LIGHT_GROUNDING_V01.md)를
추가했다. 기존 detector/tracker/map/trajectory 출력으로 target–zone 후보를 제안하고,
유일하며 승인된 calibration을 가진 고신뢰 후보만 자동 확인한다. 저신뢰·복수 후보·claim-only는
최소 사람 확인으로 보내고 transform/evidence 누락과 충돌은 계약 생성 전에 중단한다.
이는 실제 association accuracy나 24장면 검증 완료를 뜻하지 않으며 단계 판단은 계속
**P1 DATA-GROUNDING ENTRY / DATA-GAP PIVOT**이다. 계획 대비 software와 empirical 단계의
비대칭은 [전체 프로젝트 단계 현황](../../reports/GUARDSYNTH_PROJECT_STAGE_STATUS_V1.md)에 기록한다.
완료된 [label-light v0.1 실행](../../../artifacts/results/public/guardsynth-label-light-grounding-001/label-light-2026-08-10-v3/REPORT_KO.md)은
synthetic 판정 8/8, 신규 15/15, 전체 maintained 187/187, P0a 7/7과 Z3 query agreement
100%를 기록했다. 기존 제한 입력에서는 자동 확인 0건이므로 이는 software gate 통과이며
실제 association 정확도 또는 24장면 연구 gate 통과가 아니다.

## 1. 연구 개요

### 1.1 배경

기존 Safety-Constrained CoC 연구는 행동 목표를 기술하는 Chain-of-Causation(CoC)에 정지선, 최소 간격, 금지, 대기 및 해제 조건과 같은 실행 가드를 추가하면 작은 VLM이 행동 목표를 포기하지 않으면서 가드를 만족하는 궤적 후보를 선택하도록 학습될 수 있음을 보였다. 시간 조건 실험에서는 요구사항 전용 CoC의 가드 위반률이 $0.319\pm0.052$였으나 CoC 통합형에서는 $0.000\pm0.000$으로 감소했고, 가드 준수 목표 완료율과 쌍대 계약 정확도는 모두 1.000이었다.

그러나 기존 연구에서 사용한 실행 가드는 연구자가 합성 문제의 정답이 분명하도록 사전에 작성한 조건이다. 실제 장면에서 다음 문제는 해결되지 않았다.

1. 특정 장면과 CoC에 어떤 제약이 필요한가?
2. 제약은 어느 객체와 행동에 적용되는가?
3. 거리, 속도, 시간 및 가속도 경계는 어디에서 도출되는가?
4. 의무가 언제 시작되고 해제되며 다시 활성화되는가?
5. 여러 제약이 충돌할 때 어떤 제약이 우선하는가?
6. 생성된 제약이 충분하고 실행 가능하며 지나치게 보수적이지 않은가?
7. 근거가 부족할 때 시스템이 제약 생성을 보류할 수 있는가?

따라서 기존 연구는 **주어진 가드의 학습 가능성과 사용 가능성**을 다루었고, 본 연구는 그보다 앞선 **가드의 적용성, 근거성, 수치 정당성 및 타당성**을 다룬다.

### 1.2 연구 문제

본 연구는 CoC 문장만으로 안전 제약을 자유 생성하는 문제로 정의하지 않는다. CoC는 필요한 제약을 찾기 위한 상황적 단서로 사용하고, 제약의 규범적ㆍ수치적 근거는 교통규칙, 시스템 안전 요구사항, ODD, 지도, 차량 동역학 및 센서 불확실성에서 가져온다.

장면을 $x$, CoC 행동 요구를 $R$, 근거 지식베이스를 $K$, 지도 및 교통 통제를 $M$, ODD를 $O$, 차량 한계를 $V$, 불확실성 모델을 $U$라 하면 목표 가드는 다음과 같이 정의한다.

```text
context C(x,R)   = Parse(x, R)
candidates       = Retrieve(C(x,R), K)
bound_clauses    = GroundBind(candidates, x, M, O, V, U)
Gamma*           = Compose_EBLC(bound_clauses)
certificate Pi  = BCV(Gamma*, C, U, Models)
```

수식으로는 다음과 같다.

$$
(\Gamma^*,\Pi) = \operatorname{BCV}\left(
\operatorname{Compose}_{\mathrm{EBLC}}\left(
\operatorname{GroundBind}(\operatorname{Retrieve}(C(x,R),K),x,M,O,V,U)
\right), C,U,\mathcal{M}\right).
$$

여기서 $\Gamma^*$는 서로 독립인 문장 목록이 아니라 근거ㆍ의존ㆍ충돌ㆍlifecycle edge를 가진 실행 계약 그래프이고, $\Pi$는 provenance, binding, 관측 가능성, 충족 가능성, lifecycle, 양방향 반례 및 compiler 의미보존 결과를 담는 assurance bundle이다. `VALIDATED`는 $\Pi$의 주장 범위와 가정 안에서만 부여한다.

### 1.3 중심 원칙

> CoC는 필요한 제약을 찾기 위한 상황적 단서를 제공하지만, 안전 제약의 규범적ㆍ수치적 근거가 되어서는 안 된다. 안전 관련 제약의 근거는 외부 규칙, ODD, 차량ㆍ센서 모델 및 검증된 시스템 요구사항에서 와야 한다.

## 2. 연구 목적

### 2.1 최종 목적

CoC와 실제 주행 장면에서 필요한 실행 제약을 식별해 EBLC Graph로 합성하고, BCV로 과소제약ㆍ과잉제약ㆍ시간 상태 오류ㆍ컴파일 의미 불일치를 독립적으로 검증하는 방법을 개발한다.

### 2.2 세부 목적

1. CoC 실행 제약을 표현하는 온톨로지와 EBLC Graph/typed Guard IR을 정의한다.
2. CoC와 장면에서 객체, 원인, 위험, 행동 의도 및 불확실성을 추출한다.
3. 장면에 적용 가능한 guard template과 근거 규칙을 검색한다.
4. 지도, 센서 상태, ODD 및 차량 한계로 guard parameter를 결정론적으로 결합한다.
5. activation–invariant–release–reactivation–fallback을 가진 계약 그래프를 합성한다.
6. 자연어 가드, canonical Guard IR, SMT snapshot, runtime monitor 및 planner predicate 사이의 의미보존을 검사한다.
7. 전문가 검증 데이터셋 `GuardBench-CoC`를 구축한다.
8. BCV로 과소제약과 과잉제약 반례를 대칭적으로 탐색하고 lifecycle 변이와 독립 폐루프 시뮬레이션에서 실효성을 평가한다.
9. 실제 Alpamayo-R1 출력 CoC 및 궤적에 대한 적용 가능성을 평가한다.
10. 근거가 없거나 상충하는 경우 `VALIDATED`가 아닌 `REVIEW_REQUIRED`, `UNSUPPORTED` 또는 `CONFLICT`를 반환한다.

## 3. 연구 범위와 주장 경계

### 3.1 1차 운전 행동 범위

다음 세 vertical slice는 source, 수치 binder, lifecycle 및 closed-loop outcome을 깊게 검증하는 범위다. 이는 방법의 적용 범위를 세 행동으로 제한한다는 뜻이 아니며, 여섯 행동군 전체에서 symbolic applicability, grounding 및 계약 구조를 평가한다.

1. 선행차 추종ㆍcut-in의 종방향 물리 envelope
2. 정지표지ㆍ신호 접근의 stop-position 및 release lifecycle
3. 보행자ㆍ자전거 conflict-zone yield의 activation–maintain–release–reactivation

장기 비교와 단계적 확장에 사용할 전체 taxonomy는 다음과 같다.

1. 정지표지ㆍ신호등 접근, 정지 및 재출발
2. 보행자ㆍ자전거 양보
3. 교차 차량 양보 및 gap acceptance
4. 선행차 추종과 급감속 대응
5. 차선 변경ㆍ합류ㆍ중단ㆍ재시도
6. 공사구간ㆍ장애물 회피 및 안전 간격 유지

### 3.2 가드 유형

기존 Safety-Constrained CoC의 유형을 확장하여 사용한다.

- `ACTIVATION`: 의무의 시작 조건
- `INVARIANT`: 의무가 활성화된 동안 유지해야 하는 조건
- `BOUND`: 거리ㆍ속도ㆍ가속도ㆍ시간 등의 수치 또는 관계 경계
- `PROHIBITION`: 특정 조건에서 금지되는 행동
- `RELEASE`: 의무 해제 또는 다음 행동의 허용 조건
- `FALLBACK`: 관측 불확실성이나 규칙 충돌 시 대체 행동
- `TERMINATION`: 행동 완료 조건
- `PRIORITY`: 여러 규칙과 목표 사이의 우선순위
- `UNCERTAINTY`: 불확실성 표현, 보수 여유 및 abstention 조건

시간 조건은 여러 가드 유형 중 하나이며, 모든 가드를 timed automata나 시간논리로 표현하지 않는다. 논리, 공간, 관계, 수치, 우선순위 및 불확실성 제약을 모두 허용한다.

### 3.3 1차 ODD 범위

- 도시 및 근교의 구조화된 도로
- 지도ㆍ신호ㆍ정지선 또는 차선 구조를 확인할 수 있는 장면
- ego와 주요 상호작용 객체의 위치ㆍ속도ㆍ시간 정렬이 가능한 장면
- 물리량의 단위와 좌표계를 확인할 수 있는 장면
- 촬영 지역과 법적 관할을 확인할 수 없는 경우 법적 수치 제약은 생성하지 않음

악천후, 비포장도로, 긴급차량, 복수 관할 법규 및 고속도로의 복잡한 합류는 확장 ODD로 둔다.

### 3.4 제외 범위

본 연구는 다음을 직접 주장하지 않는다.

- 완전한 도로 안전 명세의 자동 생성
- 모든 국가ㆍ지역의 교통법규 자동 해석
- 생성된 제약만으로 충돌이 방지된다는 보장
- 실차 배포 승인 또는 automotive-grade safety certification
- CoC가 항상 사실이고 완전하다는 가정
- 사람의 기록 궤적을 안전 기준 또는 전문가 가드 정답으로 간주
- 모델 내부의 비공개 reasoning 복원
- 10B급 E2E 모델 전체에 대한 완전 형식 검증

## 4. 연구 목표

### 4.1 정성적 목표

| 목표 | 내용 |
|---|---|
| 근거성 | 안전 관련 가드에 규칙, 시스템 요구사항 또는 물리 모델의 출처를 부여한다. |
| 실행 가능성 | 자연어 설명뿐 아니라 프로그램이 검사할 수 있는 구조화 가드를 생성한다. |
| 추적 가능성 | CoC span과 장면 객체에서 가드, 근거, 수치 계산 및 검증 결과까지 추적한다. |
| 불확실성 보존 | 필요한 사실이나 근거가 없을 때 임의로 보완하지 않고 보류 판정을 반환한다. |
| 보수성 통제 | 위반 감소와 함께 교착, 불필요한 정지 및 진행성 손실을 평가한다. |
| 독립 검증 | 생성에 사용한 규칙과 분리된 전문가, 물리 계산 및 시뮬레이션으로 평가한다. |
| 일반화 | 새로운 표현, 수치, 행동, ODD 및 데이터 출처에서 성능을 평가한다. |
| 모듈성 | 특정 LLM, VLM, temporal logic 또는 simulator에 종속되지 않게 설계한다. |
| 재현성 | 데이터 분할, 지식베이스, 모델, prompt, 가드 및 평가기의 버전을 고정한다. |

### 4.2 정량적 핵심 목표

아래 수치는 연구 수행 전의 사전 성공 기준이며 실험 결과를 의미하지 않는다. 파일럿에서 분산과 라벨 난이도를 확인한 후 변경이 필요하면 locked test 실행 전에 변경 근거와 버전을 기록한다.

| 평가 영역 | 지표 | 목표 |
|---|---|---:|
| 출력 안정성 | Schema/JSON parse 성공률 | $\geq 99\%$ |
| 실행 가능성 | 가드 compiler 성공률 | $\geq 98\%$ |
| 적용성 | Guard applicability macro-F1 | $\geq 0.80$ |
| 구조 정확도 | 유형ㆍ대상ㆍ연산자 정확도 | $\geq 0.85$ |
| 단위 처리 | 단위ㆍ좌표계 정확도 | $\geq 0.95$ |
| 수치 타당성 | `VALIDATED` subset의 전문가 허용 범위 내 비율 | $\geq 0.90$; coverage 별도 보고 |
| 근거 추적 | Provenance 정확도 | $\geq 0.90$ |
| 근거 환각 | `VALIDATED`에서 존재하지 않는 근거ㆍ수치 생성률 | $0\%$ |
| 정적 검증 | satisfiableㆍnon-conflicting 비율 | $\geq 0.95$ |
| 컴파일 의미보존 | canonical IR–SMT–monitor 간 bounded trace 판정 일치 | $\geq 0.99$ |
| 과소제약 검출 | 주입한 missing/weak-clause 반례 검출 recall | $\geq 0.90$ |
| 과잉제약 검출 | 주입한 extra/over-tight-clause 반례 검출 recall | $\geq 0.90$ |
| lifecycle 검출 | stale releaseㆍmissed reactivation 변이 검출 recall | $\geq 0.90$ |
| 전문가 평가 | 중대한 수정 없이 승인 | $\geq 70\%$ |
| 전문가 효율 | 작성ㆍ검토 시간 감소 | $\geq 30\%$ |
| 실행 효과 | no-guard 대비 위반률 상대 감소 | $\geq 30\%$ |
| 기준선 효과 | 자유생성 LLM 대비 위반률 상대 감소 | $\geq 15\%$ |
| 진행성 | 목표 완료율 감소 | $\leq 5$%p |
| 과잉 제약 | 정상 궤적 false rejection | $\leq 10\%$ |
| 일반화 | OOD macro-F1 하락 | $\leq 10$%p |

### 4.3 확장 목표

- 실제 Alpamayo-R1 출력에서 가드 적용 효과의 95% 신뢰구간이 0을 제외한다.
- 두 데이터셋 간 cross-dataset generalization을 입증한다.
- `UNSUPPORTED` 및 `REVIEW_REQUIRED` 판정 precision 0.85 이상을 달성한다.
- 반례 탐색으로 발견한 제약 결함 중 전문가 확인률 60% 이상을 달성한다.
- 생성 가드의 독립 실행 성능이 전문가 가드 효과의 80% 이상에 도달한다.

## 5. 연구 질문과 가설

### RQ1. 가드 적용성

> CoC와 장면으로부터 현재 필요한 가드 유형과 적용 대상을 식별할 수 있는가?

- H1: `CoC+scene+evidence` 모델은 CoC-only 및 scene-only보다 applicability macro-F1이 높다.

### RQ2. 근거 및 수치 결합

> 외부 지식을 사용하면 자유생성 LLM보다 수치, 단위 및 출처가 정확한 가드를 생성할 수 있는가?

- H2: 근거 검색과 결정론적 parameter binding은 수치 오류 및 출처 환각을 감소시킨다.

### RQ3. 독자 실행 제약 설계

> EBLC Graph가 독립 가드 목록보다 근거 의존성, 복합 규칙, 해제ㆍ재활성 및 fallback을 더 정확하고 실행 가능하게 표현하는가?

- H3: EBLC Graph는 flat guard set보다 lifecycle 오류, 근거 없는 조합 및 `NO_ADMISSIBLE_ACTION` 누락을 줄이고 전문가 semantic acceptance를 높인다.

### RQ4. 양방향 검증

> BCV가 단방향 satisfiability 또는 violation 검사보다 과소제약과 과잉제약을 함께 더 잘 검출하며 compiler target 간 의미 불일치를 찾는가?

- H4: BCV는 SMT-only, replay-only 및 safety-outcome-only 검증보다 주입한 missing/extra/bound/lifecycle/translation 결함의 macro recall이 높다.

### RQ5. 실행 효과와 보수성

> 생성 가드가 독립적으로 만든 반례의 위반을 줄이면서 목표 진행성을 유지하는가?

- H5: evidence-grounded EBLC는 no-guard 및 free-form guard보다 위반률이 낮고 목표 완료율 손실은 5%p 이내이다.

### RQ6. 일반화와 구성요소 이식성

> 학습하지 않은 maneuver, 표현, 수치, ODD 및 데이터셋에서도 작동하며 DriveRegㆍRTCD4ADSㆍSanDRA 계열 구성요소를 교체해도 EBLC/BCV 의미가 유지되는가?

- H6: 템플릿과 근거 기반 계약 구조는 순수 생성 모델보다 OOD 성능 저하가 작고, 구성요소 교체 후에도 canonical contract 판정이 안정적이다.

### RQ7. 실제 CoC 모델 적용

> 실제 Alpamayo-R1 출력 CoC에 생성 가드를 결합하거나 외부 검증기로 사용할 수 있는가?

- H7: prompt-only 방식보다 EBLC와 독립 BCV/runtime verifier 조합이 안정적인 준수 효과를 보인다.

## 6. 독자 제약 설계: EBLC Graph

### 6.1 계약 원자와 그래프 의미론

본 연구의 기본 단위는 자유형 문장이나 독립 predicate가 아니라 다음 계약 원자다.

$$
g=\langle S,A,M,P,B,R,X,F,\rho,E,O\rangle
$$

- $S$: jurisdiction, ODD, route, entity를 포함한 scope
- $A$: activation condition
- $M$: obligation, prohibition, permission, preference modality
- $P$: 유지해야 할 invariant/predicate
- $B$: source와 uncertainty를 가진 bound 또는 parameter derivation
- $R$: release condition
- $X$: reactivation/expiration condition
- $F$: 관측 실패ㆍ충돌ㆍ실행 불가능 시 승인된 fallback
- $\rho$: source-aware partial priority
- $E$: normative/physical evidence와 derivation DAG
- $O$: observability/freshness contract

EBLC Graph $\Gamma=(V,E_\Gamma)$의 node는 `ContextFact`, `Evidence`, `Derivation`, `GuardClause`, `LifecycleState`, `Fallback`이고, edge는 `APPLIES_TO`, `ACTIVATES`, `BINDS`, `REFINES`, `DEPENDS_ON`, `EXCEPTS`, `OVERRIDES`, `CONFLICTS_WITH`, `RELEASES`, `REACTIVATES`다. 따라서 검색된 규칙, 물리 envelope 및 시간 상태를 단순히 이어 붙이지 않고, 어느 근거가 어떤 predicate와 수치를 정당화하며 어떤 사건이 의무를 바꾸는지 기계적으로 추적할 수 있다.

### 6.2 Canonical Guard IR

각 가드는 다음 필드를 갖는다.

```yaml
guard_id: guard-...
contract_id: contract-...
context:
  odd: ...
  jurisdiction: KNOWN | UNKNOWN
trigger:
  predicate: ...
  evidence_refs: [...]
subject: ego
target:
  entity_id: ...
  entity_type: ...
modality: OBLIGATION | PROHIBITION | PERMISSION | PREFERENCE
guard_type: ACTIVATION | INVARIANT | BOUND | PROHIBITION | RELEASE | FALLBACK | TERMINATION | PRIORITY | UNCERTAINTY
predicate: ...
comparator: ...
value: ...
unit: ...
reference_frame: ...
active_interval: ...
release_condition: ...
reactivation_condition: ...
expiration_condition: ...
fallback: ...
priority: ...
dependencies: [...]
conflicts_with: [...]
uncertainty: ...
assumptions: [...]
provenance:
  evidence_type: ...
  source_id: ...
  source_version: ...
  derivation_id: ...
confidence: ...
status: VALIDATED | REVIEW_REQUIRED | UNSUPPORTED | CONFLICT
natural_language: ...
```

모든 필드를 항상 채우지는 않는다. 해당하지 않는 필드와 근거가 부족한 필드를 명시적으로 구분한다.

v1.2에서는 `context`를 ego/route/actors/map-control/conflict-zone/visibility-road/ODD/CoC-claim/active-ledger로 구성한 typed `ContextGraph`로 정의한다. 각 atomic fact는 `TRUE | FALSE | UNKNOWN | CONFLICT`와 `OBSERVED | PREDICTED | DERIVED | CLAIMED`, source, timestamp, freshness 및 uncertainty를 갖는다. CoC claim은 관측 fact로 승격하지 않는다. 각 rule에는 source class, jurisdiction/version/validity, precondition, exception, typed role, binder ID, observability contract, lifecycle, priority가 필수다. parameter binding은 `Value | Interval | Set | Unsupported`인 partial function이며 계산 derivation DAG를 보존한다. 상세 schema와 판정 조건은 [전략 문서 §8–14](../../surveys/guard-synth-coc/CONTEXT_AWARE_GUARD_SYNTHESIS_SURVEY_AND_STRATEGY_V1.md#8-표현-계층과-데이터-모델)를 따른다.

### 6.3 근거 등급

```text
LEGAL                 교통법규, 신호 또는 지도 기반 규범
PHYSICS_DERIVED       제동거리, 차량 동역학, 충돌 기하 기반 조건
SYSTEM_REQUIREMENT    검토ㆍ승인된 시스템 안전 요구사항
ODD_REQUIREMENT       정의된 ODD의 진입ㆍ유지ㆍ이탈 조건
STATISTICAL_HEURISTIC 데이터에서 추정한 경험적 기준
COMFORT_SERVICE       승차감, 진행성 또는 서비스 목표
UNKNOWN               출처 또는 정당성을 확보하지 못한 조건
```

`STATISTICAL_HEURISTIC`와 `COMFORT_SERVICE`를 자동으로 hard safety constraint로 승격하지 않는다. `UNKNOWN` 근거를 가진 수치 제약은 실행 강제 전에 사람의 검토를 요구한다.

### 6.4 다중 실행 표현과 translation contract

동일 계약은 다음 표현을 동시에 제공한다.

1. 사람이 검토할 수 있는 자연어 가드
2. 의미의 기준이 되는 canonical Guard IR
3. snapshot 충족 가능성ㆍ충돌 검사용 SMT/interval constraint
4. partial trace용 runtime monitor automaton
5. planner/action filter용 executable predicate 또는 admissible-set interface

canonical Guard IR만 의미의 기준이며 나머지는 compiler target이다. 자연어가 IR에 없는 의무를 추가하거나, compiler target이 IR의 activation/release/UNKNOWN 의미를 누락하면 불일치로 판정한다. 제한된 trace와 경계값에서 target 간 판정을 비교하는 translation validation을 매 build마다 수행한다.

### 6.5 세 선행시스템과의 결합 및 독창성 경계

| 채택 가능한 선행 구성요소 | 본 연구에서 가져오는 기능 | EBLC/BCV가 새로 담당하는 경계 |
|---|---|---|
| DriveReg 계열 | 장면ㆍ지역 조건의 규정 검색과 후보 근거 | 검색 결과를 typed scope/exception/evidence node로 변환하고 객체ㆍ수치ㆍlifecycle과 결합 |
| RTCD4ADS 계열 | scene-aware rule activation과 runtime compliance signal | Boolean tag를 4값 fact로 확장하고 active obligation ledger, source-aware composition, fallback을 구성 |
| SanDRA 계열 | temporal-rule/action filtering과 reachability 분석 | 합성된 계약을 monitor/planner interface로 컴파일하고 규범적 충분성, 과잉제약 및 lifecycle 의미를 BCV로 검사 |

세 기능의 순차 연결은 강한 integration baseline으로 사용한다. 우리의 방법 기여는 retrieval, tag matching 또는 reachability 자체가 아니라 **서로 다른 출력 사이의 의미적 interface를 EBLC로 정의하고, 합성된 계약의 양방향 적절성과 컴파일 의미보존을 BCV로 검증하는 것**이다.

개별 재료의 최초성을 주장하지 않는다. 교통규칙 atomic proposition의 검증된 구체화, 다층 ADS 의미론, SMT 기반 overconstraint/executability 검사 및 compositional contract verification은 이미 존재한다. EBLC/BCV의 검증 대상 신규성은 **open-world 장면별로 선택ㆍgroundingㆍ수치 결합된 계약**에 evidence와 lifecycle을 보존하면서, under/overconstraint와 여러 runtime target의 번역 등가성을 한 assurance workflow에서 다루는지에 둔다. `EBLC`와 `BCV`는 1차 명칭 검색에서 정확한 동명 방법을 확인하지 못한 가칭이며, 투고 전 systematic novelty search와 용어 확정을 다시 수행한다.

## 7. 전체 접근 방법

```text
주행 영상ㆍ센서ㆍ지도 + CoC
              |
              v
1. Scene-CoC semantic parser
              |
    객체ㆍ원인ㆍ행동ㆍ위험ㆍ불확실성
              v
2. Guard template and evidence retrieval
              |
 DriveReg-style RAG + RuleㆍRequirementㆍPhysics catalog
              v
3. Four-valued applicability, entity and parameter binding
              |
 RTCD-style activation + 대상ㆍ수치ㆍ단위ㆍ좌표계
              v
4. EBLC Graph composition and lifecycle construction
              |
              v
5. BCV and translation validation
              |
 underconstraintㆍoverconstraintㆍlifecycleㆍcompiler equivalence
              v
6. SanDRA-style reachability/action filter + independent outcome validation
              |
              v
VALIDATED / REVIEW_REQUIRED / UNSUPPORTED / CONFLICT
              |
              v
CoC 학습ㆍ후보 선택ㆍruntime monitorㆍshield
```

후보 검색은 graph/lexical/dense/CoC query를 이용한 high-recall proposal로 제한하고, 최종 적용성은 jurisdiction/version/ODD/maneuver hard filter와 4값 precondition/exception evaluator가 결정한다. `UNKNOWN`을 임의로 참 또는 거짓으로 닫지 않는다. runtime에는 `INACTIVE→CANDIDATE→ACTIVE→MAINTAINED→RELEASED→REACTIVATED/EXPIRED` ledger를 사용하며, stale identity와 `NO_ADMISSIBLE_ACTION`을 별도 진단한다. LLM은 parsing/retrieval/reranking/설명에만 사용하고 rule source, hard-safety 수치, 관측 fact, conflict resolution 또는 `VALIDATED`를 확정하지 않는다.

### 7.1 Scene-CoC semantic parsing

CoC와 장면에서 다음을 추출한다.

- ego 행동 의도와 목표
- 원인 객체 및 영향 대상
- 객체 간 상충 관계와 conflict zone
- 현재 요구 행동과 금지 행동
- 유지ㆍ해제ㆍ행동 전환 단서
- 지도ㆍ신호ㆍ차선 상태
- 센서 및 추적 불확실성
- 안전 제약 생성에 필요한 누락 정보

출력은 자유 텍스트가 아니라 typed scene graph로 제한한다. CoC가 주장한 객체와 센서에서 관측한 객체를 분리하고, 연결이 확인되지 않으면 `UNGROUNDED_CAUSE`를 반환한다.

### 7.2 Guard template 및 근거 검색

LLM이 기억에 의존해 안전 규칙을 작성하지 않고 지식베이스에서 적용 가능한 후보를 검색한다.

```text
CoC: 보행자에게 양보한 뒤 진행한다.
Scene: 보행자가 횡단보도 상충 영역에 있음.

검색 후보:
- pedestrian_conflict_activation
- stop_line_invariant
- conflict_zone_clear_release
- perception_uncertainty_fallback
```

검색 결과에는 source ID, version, jurisdiction, 적용 ODD, 필수 입력 및 예외 조건을 포함한다.

### 7.3 Entity 및 parameter binding

수치는 원칙적으로 LLM이 직접 생성하지 않는다.

| Parameter | 우선 근거 |
|---|---|
| 정지선 위치 | 지도ㆍ차선 geometryㆍ신호 연결 |
| 상대 간격 | obstacle track과 좌표 변환 |
| 정지 가능 거리 | ego 속도ㆍ반응 지연ㆍ제동 한계ㆍ불확실성 |
| 제한속도 | 지도ㆍ표지ㆍ확인된 법적 출처 |
| 해제 안정시간 | 검증된 시스템 요구사항 또는 uncertainty profile |
| 차선 변경 가능성 | 목표 차선 객체의 상대 위치ㆍ속도ㆍ예측 범위 |
| 승차감 경계 | 서비스 요구사항 및 차량 profile |

값을 정당화할 수 없으면 `UNSUPPORTED_VALUE`로 출력하며, CoC나 사람의 기록 궤적에서 임의로 안전 경계를 추정하지 않는다.

### 7.4 EBLC Graph composition

여러 가드를 결합하면서 다음을 검사한다.

- 동일 대상의 중복 가드
- 상충하는 경계와 의무
- hard safety와 service preference의 우선순위
- release 이후 위험 재등장 시 재활성화
- 예외 조건과 ODD 이탈
- fallback 및 termination 누락
- 진행 불가능한 교착 계약

합성은 검색 점수 순으로 clause를 누적하는 과정이 아니다. 후보 집합 $Q$에서 계약 그래프를 선택ㆍ구성할 때 다음 목적과 hard obligation을 분리한다.

$$
\Gamma^*=\arg\min_{\Gamma\subseteq Q}
\lambda_m L_{miss}(\Gamma)+\lambda_o L_{over}(\Gamma)+
\lambda_c C(\Gamma)+\lambda_u U(\Gamma),
$$

subject to

$$
Evidence(\Gamma)\land Applicable(\Gamma,C)\land Monitorable(\Gamma)
\land LifecycleComplete(\Gamma)\land
\big(RobustFeasible(\Gamma,C,U)\lor ApprovedFallback(\Gamma)\big).
$$

$L_{miss}$는 필요한 rule family/obligation의 누락, $L_{over}$는 nominal safe-progress set의 잘못된 배제, $C$는 중복ㆍ복잡도, $U$는 미결정 evidence/parameter 비용이다. hard legal/safety clause를 scalar score로 임의 삭제하지 않으며, robust feasible action이 없으면 `NO_ADMISSIBLE_ACTION/CONFLICT`와 승인된 fallback을 출력한다.

### 7.5 BCV: 양방향 반례 검증

BCV는 “가드가 모순이 없는가”만 검사하지 않고, 다음 두 종류 반례를 같은 중요도로 탐색한다. 환경ㆍ차량 가정 집합을 $\mathcal A$, 계약 monitor가 trace $\tau$를 허용하는 판정을 $Accept_\Gamma(\tau)$라 한다.

**과소제약 반례**는 계약이 허용하지만 독립 rule/safety oracle이 위험 또는 규칙 위반으로 판정하는 trace다.

$$
\exists\tau:\mathcal A(\tau)\land Accept_\Gamma(\tau)\land
(RuleViolation(\tau)\lor Unsafe(\tau)).
$$

**과잉제약 반례**는 독립 oracle상 안전ㆍ합법ㆍ진행 가능하지만 계약이 거부하는 trace다.

$$
\exists\tau:\mathcal A(\tau)\land SafeLegalProgress(\tau)\land
\neg Accept_\Gamma(\tau).
$$

또한 $A_\Gamma(C,U)=\varnothing$인데 독립 oracle에는 안전ㆍ합법ㆍ진행 가능한 action이 존재하면 `false deadlock` 과잉제약 반례로 분류한다. 반례에는 `MISSING_CLAUSE`, `WRONG_TARGET`, `WEAK_BOUND`, `EXTRA_CLAUSE`, `OVER_TIGHT_BOUND`, `STALE_RELEASE`, `MISSED_REACTIVATION`, `NO_FALLBACK` 등의 최소 원인 집합을 붙인다.

### 7.6 BCV의 네 검증 단계

1. **Contract well-formedness:** schema, entity/predicate type, unit/frame, evidence/provenance, binder recomputation, satisfiability, conflict, implication, redundancy, vacuity, physical feasibility를 검사한다.
2. **Lifecycle model checking:** `INACTIVE→ACTIVE→MAINTAINED→RELEASED→REACTIVATED/EXPIRED` 전이에서 release 누락, stale identity, one-frame dropout, 재위험 미활성 및 fallback 부재를 bounded model checking과 sequential mutation으로 찾는다.
3. **Translation validation:** canonical IR, SMT snapshot, runtime monitor 및 planner predicate에 동일한 boundary/UNKNOWN/CONFLICT trace를 입력해 판정 등가성을 확인한다. compiler와 verifier는 독립 구현을 사용한다.
4. **Metamorphic verification:** CoC paraphrase는 계약 의미를 보존해야 하고, shuffled CoC는 효과가 사라져야 하며, hazard 제거는 관련 의무만 해제하고, hazard 재등장은 재활성화하며, map/vehicle/source 변화는 의존 edge가 연결된 bound만 바꿔야 한다.

BCV는 dev 단계에서 반례를 EBLC 수정에 돌려주는 CEGIS loop로 사용할 수 있지만, locked test의 반례로 같은 버전을 수정하지 않는다. bounded model, source completeness 및 독립 oracle 가정 밖의 보편 안전을 주장하지 않는다.

### 7.7 Assurance bundle과 독립 실행 검증

각 계약은 다음 artifact를 가진다.

- evidence/applicability certificate
- entity/parameter derivation certificate
- observability/freshness certificate
- consistency/robust-feasibility certificate
- lifecycle transition certificate
- bidirectional counterexample report
- compiler translation-equivalence report

생성 가드의 작성에 사용하지 않은 다음 평가기를 사용한다.

- 전문가 gold guard
- 기록 궤적 replay
- 독립 물리 계산
- counterfactual perturbation
- 기존 경량 폐루프 simulator
- 필요 시 MetaDrive 또는 CARLA 기반 핵심 장면 재현

## 8. 데이터 계획

### 8.1 현재 보유 데이터

| 데이터 | 현재 규모 | 연구 용도 | 한계 |
|---|---:|---|---|
| nuScenes CoC | 3,218 events, 743 clips | 대규모 CoC parsing, 사전학습, 외부 평가 후보 | Qwen 기반 자동 라벨이며 안전 정답이 아님 |
| PhysicalAI official event/action text | 2,077 events, 1,740 clips | 실제 장면의 행동 요구, GuardBench 표본 | human-refined short text이며 긴 Alpamayo reasoning trace가 아님 |
| 연속 CoC | 2,475 adjacent pairs | 유지ㆍ해제ㆍ행동 전환 후보 발굴 | 실제 위험 해소에는 외부 상태 필요 |
| trajectory-linked subset | 403 events, 94 scenes | 궤적 정합성 및 replay | 다수 장면이 현재 기준 UNKNOWN |
| CASCADE | 2,066 annotated clips | 객체ㆍ행동ㆍ원인ㆍ시간ㆍ대상 grounding | 전체 annotation의 로컬 획득 필요 |
| Alpamayo-R1 direct pilot | 3 scenes, 9 paired runs 이상 | 모델 직접 출력 수집 feasibility | 안전 의미 효과를 입증하기에는 작음 |
| 합성 Guard benchmark | 정적ㆍ시간ㆍ복합 maneuver | schema, compiler, controlled mutation | 실제 가드 생성의 타당성을 입증하지 못함 |

근거 파일:

- [nuScenes CoC 데이터 설명](../../../data/baseline/coc_nusc/UPSTREAM_README.md)
- [PhysicalAI 데이터 및 provenance 보고서](../../../data/restricted/nvidia_physicalai/internal-derived/ALPAMAYO_EXPERIMENT_REPORT.md)
- [연속 CoC 인벤토리](../../../artifacts/results/restricted/sequential-coc-consistency-v1/inventory.json)
- [CASCADE 데이터 설명](../../../data/restricted/nvidia_cascade/README.md)
- [CASCADE-PhysicalAI 매핑 결과](../../../data/restricted/nvidia_cascade/internal-derived/smoke-test-1/README.md)
- [Alpamayo-R1 직접 실험 요약](../../../artifacts/results/restricted/alp-exp-006/stage1-summary-v2/REPORT_KO.md)

### 8.2 GuardBench-CoC 파일럿

- schema dry-run: 세 vertical slice별 8개, 총 24장면
- formal pilot: 위험/nominal, day/night, clear/occluded, release/reactivation을 층화한 60장면
- 라벨러: 교통규정ㆍADS safetyㆍ차량동역학ㆍperception/map 역할을 포함한 2인 독립 라벨과 제3자 adjudication
- 합의: 최대 두 차례 ontology/지침 수정 후 applicability α 0.67 이상
- 사용: prevalence, unsupported rate, 효과크기, cluster correlation, annotation time 및 main-study power 추정
- 제외: 24장면 dry-run은 결과 보고용 locked test에서 제외

### 8.3 GuardBench-CoC 본 데이터

- 총 장면 수는 60장면 formal pilot의 효과크기와 cluster correlation으로 power analysis하여 결정한다. 360은 더 이상 사전 고정하지 않는다.
- 세 vertical slice와 matched nominal control을 먼저 구성하고 여섯 행동군 확장은 Phase gate 이후 결정한다.
- PhysicalAI/CASCADE/nuScenes 비율은 지원 가능한 mapㆍsensorㆍsource availability를 기준으로 층화하며, 데이터 규모 때문에 고정하지 않는다.
- 2인 독립 라벨 후 제3자 adjudication하고, 장면당 복수의 허용 가능한 가드 집합ㆍ수치 intervalㆍsourceㆍ`UNSUPPORTED` 가능성을 기록한다.
- clip, route/episode, scenario family, 주요 원인 객체 및 데이터 출처 단위 split로 누수를 방지한다. 정확히 동일한 template parameter만 바꾼 표본은 서로 다른 split에 배치하지 않는다.
- main N과 train/development/locked-test 비율은 power report와 함께 locked test 실행 전에 고정한다.

### 8.4 전문가 라벨 구조

각 장면에 다음을 라벨링한다.

- 가드 적용 필요 여부
- 가드 유형과 modality
- subject 및 target
- trigger와 active interval
- predicate, comparator, value, unit 및 reference frame
- 수치의 허용 범위와 근거
- release, fallback 및 termination
- priority와 예외
- evidence source와 provenance
- ODD 및 assumptions
- `VALIDATED`, `REVIEW_REQUIRED`, `UNSUPPORTED`, `CONFLICT`

한 가지 자연어 문장을 유일한 정답으로 강제하지 않는다. 동일한 의미의 복수 표현과 허용 가능한 parameter interval을 지원한다.

### 8.5 예상 전문가 작업량

장면당 12분과 총 360장면은 검증되지 않은 가정이므로 예산 기준으로 사용하지 않는다. 24장면 dry-run과 60장면 formal pilot에서 field별 시간, source 확인 시간 및 adjudication 비율을 측정하고, power-based main N과 함께 전문가 시간ㆍQA 예산을 산정한다.

## 9. 실험 계획

### E-1. Sourceㆍbinderㆍobservability feasibility audit

모델 학습 전에 한 관할의 세 deep vertical slice에서 최초 12–20개 rule template을 작성하고, 여섯 행동군의 family-level coverage catalog를 병행한다. 12–20개는 EBLC/BCV semantics와 source engineering의 P0 gate이지 main study의 최대 template 수가 아니다. 각 template은 공식 source/version/scope/precondition/exception, typed role, deterministic partial binder, required `PredicateSpec`, lifecycle 및 priority를 가져야 한다. source 없는 규범ㆍ수치는 0건이어야 하고, binder recomputation ≥0.95와 injected missing/corrupt input의 `UNSUPPORTED` precision ≥0.90을 만족해야 한다. 실패하면 대규모 라벨링과 runtime enforcement를 시작하지 않고 rule authoring/applicability 연구로 범위를 줄인다.

### E0. EBLC 의미론과 compiler translation 검증

#### 목적

자연어, canonical Guard IR, SMT constraint, runtime monitor 및 planner predicate가 동일한 EBLC 의미를 보존하고, 의도적으로 주입한 구조ㆍ번역 오류를 검출하는지 확인한다.

#### 입력 변이

- 정상 가드
- 잘못된 단위와 차원
- 좌표계 누락 또는 불일치
- 상충하는 경계
- release 없는 의무
- 존재하지 않는 객체
- 순환된 priority
- 물리적으로 실행 불가능한 조건
- 의미가 다른 자연어와 Guard IR
- activation/release 경계에서 SMT와 monitor의 off-by-one 불일치
- `UNKNOWN`을 target별로 TRUE/FALSE로 다르게 닫는 번역
- release 후 hazard reappearance를 누락한 automaton

#### 지표와 기준

- 정상 가드 compile 성공률 $\geq 98\%$
- 의도적 오류 검출 recall $\geq 95\%$
- 정상 가드 false alarm $\leq 5\%$
- canonical IR–SMT–monitor–planner bounded trace 판정 일치율 $\geq 99\%$
- 두 독립 evaluator의 결함 판정 일치율 $\geq 99\%$

### E1. 전문가 GuardBench 신뢰도

#### 목적

가드 라벨의 재현성과 어려운 필드를 확인하고, 본 라벨링 전에 지침을 고정한다.

#### 지표

- Krippendorff's alpha 또는 Fleiss' kappa
- applicability 및 guard type 합의도
- subject/target 합의도
- 수치 허용 범위의 overlap
- release/fallback 합의도
- adjudication 필요 비율

#### 진행 기준

applicability와 guard type의 사전 합의도 0.67 이상을 목표로 한다. 이보다 낮으면 본 라벨링 전에 schema와 지침을 재설계하고 새 파일럿 버전을 수행한다.

### E2. 가드 생성 정확도

#### 비교 조건

| ID | 조건 | 목적 |
|---|---|---|
| B0 | Frequency/template prior | 빈번한 가드를 반복하는 하한선 |
| B1 | CoC-only free-form LLM | 장면 및 근거 없는 자유생성 기준선 |
| B2 | Scene-only LLM/VLM | CoC의 추가 가치 평가 |
| B3 | Template retrieval only | 생성 없이 검색만 사용 |
| B4 | CoC+scene template retrieval | CoC-conditioned 적용성 평가 |
| B5 | DriveReg-style regulation RAG | 지역 규정 검색 대비 기여 |
| B6 | RTCD4ADS-style scene-tag rule filter | semantic tag 기반 적용성 대비 기여 |
| B7 | Physics/RSS/CBF-only envelope | 수치 물리 envelope 대비 규범 선택 기여 |
| B8 | SanDRA-like TL+formal-rule+reachability action filter | 2026 통합 behavior filtering 대비 기여 |
| B9 | Flat SEBGI without EBLC/BCV | 독립 guard list와 계약 그래프의 차이 |
| B10 | EBLC Graph + BCV 전체 | 독자 제약 설계와 양방향 검증의 전체 효과 |
| B11 | Expert guard | 전문가 상한선 |
| B12 | Always-stop/always-yield | collision 감소의 과잉보수성 통제 |
| B13 | DriveReg→RTCD4ADS→SanDRA naive composition | 선행 구성요소의 단순 직렬 결합과 semantic interface 기여 분리 |

#### 주요 지표

- applicability macro-F1
- guard type, target 및 predicate 정확도
- 수치 허용 범위 정확도
- 단위 및 좌표계 정확도
- provenance 정확도
- 근거 환각률
- abstention precision/recall
- 전문가 승인율 및 수정량

#### 핵심 비교

```text
B10 vs B1: 근거 기반 selective instantiation의 효과
B10 vs B4/B5/B6: parameter binding, 4값 applicability 및 provenance의 효과
B10 vs B7/B8: rule selectionㆍlifecycle 기여와 behavior safety filter의 차이
B10 vs B9: EBLC dependency/lifecycle semantics와 BCV의 순효과
B10 vs B13: 기존 구성요소를 합치는 것과 검증 가능한 semantic interface를 설계하는 것의 차이
B10 vs B11: 전문가 상한과의 차이
B10 vs B12: safety 이득이 always-conservative 정책과 다른지 확인
```

필수 input ablation은 `scene only`, `CoC only`, `scene+CoC`, `scene+shuffled CoC`다. CoC를 headline contribution으로 유지하려면 scene-only 대비 primary metric의 절대 개선이 3%p 이상이고 shuffled-CoC에서는 개선이 사라져야 한다.

### E3. 강건성과 일반화

다음 요인을 한 번에 하나씩 변경한다.

- CoC paraphrase
- 단위 변환: m/cm, km/h/m/s
- 숫자와 수치 근거 누락
- CoC 객체와 scene 객체 불일치
- irrelevant 또는 shuffled CoC
- shuffledㆍirrelevant evidence
- 상충하는 두 규칙
- obstacle track 누락
- 좌표계 또는 timestamp 불일치
- 관할 법규 미확인
- unseen maneuver
- unseen dataset
- 위험 해제 후 동일 위험 재등장
- missing/extra clause와 weak/over-tight bound
- compiler target별 activation/release/UNKNOWN 번역 불일치

지표는 성능 저하, 잘못된 가드 생성률, conflict detection, abstention 및 unsupported value 판정뿐 아니라 다음 BCV primary metric을 포함한다.

- 과소제약과 과잉제약 결함별 detection precision/recall 및 최소 원인 localization
- lifecycle mutation의 stale-release/missed-reactivation detection recall
- metamorphic relation satisfaction rate
- canonical IR–compiler target의 bounded-trace disagreement rate
- BCV 전후 expert acceptance 및 false-deadlock rate

### E4. 독립 실행 효과 평가

E4 outcome evaluator와 rule oracle은 generator의 template/binder 및 BCV oracle 구현을 import하지 않고, scenario와 primary endpoint를 학습 전에 lock한다. 기록 trajectory replay는 trace conformance로만 보고하며 안전 정답으로 승격하지 않는다. BCV가 dev에서 찾은 반례와 locked E4 test는 scene, parameter seed 및 rule realization을 분리한다.

#### 궤적 집합

- 기록 human trajectory
- Alpamayo-R1 predicted trajectory
- 거리ㆍ속도ㆍ시점이 변형된 counterfactual trajectory
- 행동 목표는 달성하지만 가드를 위반하는 hard negative
- 항상 정지하거나 지나치게 보수적인 후보

기록 human trajectory는 관찰된 행동이며 안전 정답으로 사용하지 않는다.

#### Counterfactual 요인

- actor 속도와 출현 시점
- 센서 및 계약 전달 지연
- ego 제동 성능과 반응시간
- 마찰계수와 불확실성
- 상대 거리와 closing speed
- 객체의 일시 소실과 재등장
- 신호 상태 변경
- 객체 예측 오차

#### 초기 규모

```text
held-out scene별 10-20 perturbations
독립 rollout 2,000개 이상
조건별 random seed 3개 이상
```

#### 평가 지표

- guard violation
- collision 및 near-miss
- TTC와 최소 clearance
- goal completion
- deadlock
- false rejection
- traversal time 및 progress loss
- shield intervention count와 trajectory deviation

### E5. Alpamayo-R1 적용 실험

E5는 E-1부터 E4까지의 phase gate를 통과한 뒤 수행한다. prompt guard를 따르지 않으면 prompt semantics를 safety enforcement로 주장하지 않고 외부 monitor/shield 결과와 분리한다.

#### 표본

- 최소 100개 event
- event별 3개 action seed
- 총 300개 이상의 direct run
- 자원 허용 시 validation 349 events 전체로 확장

#### 비교 조건

1. Native CoC
2. Native CoC + free-form guard
3. Native CoC + proposed guard
4. Native CoC + expert guard
5. Proposed guard + external trajectory verifier
6. Proposed guard + runtime shield

#### 평가

- 동일 seed에서의 paired trajectory 변화
- independent guard compliance
- goal progress 및 과잉 정지
- 객체 및 conflict zone clearance
- prompt insertion effect와 guard semantic effect의 분리

동일 길이의 반대 의미 가드와 무관 가드를 negative control로 유지한다. prompt-only 효과가 약한 경우 이를 숨기지 않고 external verifier 및 shield의 효과와 분리하여 보고한다.

### E6. 전문가 효용 평가

#### 조건

- 전문가가 처음부터 가드 작성
- free-form LLM 결과 수정
- 제안 시스템 결과 수정

#### 지표

- 총 소요 시간
- 수정한 필드 수
- 중대한 오류 수
- 출처 확인 시간
- subjective workload
- 최종 승인율

중대한 오류를 증가시키지 않으면서 작성ㆍ검토 시간을 30% 이상 줄이는 것을 목표로 한다.

## 10. 통계 분석 계획

- 주요 분석 단위는 개별 guard가 아닌 독립 scene 또는 episode로 둔다.
- 동일 장면의 여러 가드와 여러 seed는 clustered sample로 처리한다.
- 학습 및 모델 실험은 최소 3개 random seed로 반복한다.
- 주요 비율과 차이는 scene-cluster bootstrap 95% 신뢰구간을 보고한다.
- paired binary 결과는 McNemar test 또는 paired bootstrap을 사용한다.
- 연속 지표는 paired permutation 또는 clustered bootstrap을 사용한다.
- 다중 가설에는 적절한 다중 비교 보정을 적용한다.
- 전체 macro 평균과 행동군별 결과를 함께 보고한다.
- p-value뿐 아니라 효과 크기와 신뢰구간을 우선 보고한다.
- 파일럿의 분산으로 locked test의 최종 power analysis를 수행한다.
- 주요 가설, 제외 기준, split 및 primary metric은 locked test 실행 전에 고정한다.

## 11. 구현 계획

### 11.1 권장 디렉터리 구조

```text
guard_synth_coc/
|-- schemas/
|   |-- scene_graph.schema.json
|   |-- eblc_graph.schema.json
|   |-- guard_ir.schema.json
|   `-- evidence.schema.json
|-- ontology/
|   |-- guard_ontology.ttl
|   |-- maneuver_ontology.ttl
|   `-- provenance_ontology.ttl
|-- data/
|   |-- adapters/
|   |-- guardbench/
|   `-- splits/
|-- knowledge_base/
|   |-- rule_templates/
|   |-- vehicle_envelopes/
|   |-- odd_profiles/
|   `-- source_registry/
|-- synthesis/
|   |-- coc_parser/
|   |-- retriever/
|   |-- binder/
|   `-- eblc_composer/
|-- compilers/
|   |-- smt/
|   |-- runtime_monitor/
|   `-- planner_predicate/
|-- bcv/
|   |-- schema_checker/
|   |-- unit_checker/
|   |-- contract_checker/
|   |-- underconstraint/
|   |-- overconstraint/
|   |-- lifecycle_model_checker/
|   `-- translation_validator/
|-- simulation/
|   |-- replay/
|   |-- perturbation/
|   `-- closed_loop/
|-- integrations/
|   |-- small_vlm/
|   |-- alpamayo/
|   `-- prior_system_adapters/
`-- evaluation/
    |-- intrinsic/
    |-- robustness/
    |-- trajectory/
    |-- independent_oracles/
    `-- reports/
```

실제 구현 시 프로젝트의 기존 모듈과 중복되는 부분은 재사용하며, 위 구조를 그대로 강제하지 않는다.

### 11.2 구현 원칙

- JSON Schema 또는 Pydantic 기반 typed representation을 사용한다.
- Guard IR은 JSON-LD 또는 RDF mapping을 통해 KG와 연결한다.
- 수치 단위와 차원 검사는 전용 unit engine으로 수행한다.
- 거리, 제동 및 간격 계산은 결정론적 함수로 구현한다.
- LLM은 semantic parsing, retrieval query 및 후보 제안에 사용한다.
- LLM이 근거 없는 안전 수치를 직접 확정하지 못하도록 제한한다.
- satisfiability와 conflict에는 SMT solver를 사용할 수 있다.
- 모든 결과에 데이터, 모델, prompt, KB, schema 및 evaluator 버전을 기록한다.
- restricted 데이터와 공개 가능한 코드ㆍ통계ㆍ비식별 파생물을 분리한다.
- parser, generator, BCV oracle 및 outcome evaluator가 동일한 규칙ㆍbinder 코드를 공유하지 않도록 package 경계와 test fixture를 분리한다.

### 11.3 구현 단계와 산출물

| 단계 | 구현 항목 | 산출물 |
|---|---|---|
| P0 | source policy, EBLC/Guard IR semantics, 세 deep slice 최초 12–20 audited template+six-family coverage, binder/observability manifest | E-1 feasibility audit |
| P1 | 데이터 adapter, 4값 `ContextGraph`와 provenance registry | 24-scene dry-run, 통합 event index |
| P2 | graph/BM25/dense retrieval, reranker, DriveReg/RTCD/SanDRA adapter와 B0–B8/B13 baseline | applicability/integration inference bundle |
| P3 | EBLC composer, partial binder, lifecycle ledger, BCV, multi-target compiler와 translation validator | B9–B10 pipeline, bidirectional mutation suite, assurance bundle |
| P4 | GuardBench tool, 60-scene formal pilot, adjudication과 power analysis | pilot report, main N/split 결정 |
| P5 | generator와 코드ㆍ규칙을 공유하지 않는 closed-loop evaluator | locked E4 suite, independence checklist |
| P6 | runtime updater, Alpamayo adapter, external monitor/shield, offline CEGIS | E5 package와 locked report |

## 12. 일정

12개월 기준 일정은 다음과 같다.

| 기간 | 단계 | 주요 산출물 |
|---|---|---|
| 1개월 | 한 관할ㆍ세 deep slice source/binder/observability audit+six-family catalog | initial 12–20 templates, E-1 report, EBLC schema v0 |
| 2개월 | 24장면 schema dry-run | adapter/failure report, schema v1 |
| 3-4개월 | evidence catalog, parser, retriever, 선행 구성요소 adapter와 strong baseline 구현 | source registry, B0-B8/B13 |
| 3-5개월 | 60장면 formal pilot | agreement report, power-based main N/split |
| 5-7개월 | EBLC composer, binder, lifecycle ledger, BCV와 translation validator 구현 | B9-B10 pipeline, assurance bundle |
| 5-8개월 | power-based GuardBench main 구축 | adjudicated expert gold |
| 7-8개월 | intrinsic 및 robustness 평가 | E0-E3 report |
| 8-10개월 | 독립 closed-loop counterfactual simulation | E4 report |
| 9-10개월 | phase gate 통과 시 Alpamayo-R1 평가 | E5 report |
| 10-11개월 | 전문가 효용 및 추가 ablation | E6, failure taxonomy |
| 11-12개월 | 통계, artifact, 논문 작성 | T-IV submission package |

### 12.1 Go/No-Go gate

| 시점 | Gate | 조치 |
|---|---|---|
| P0 종료 | 세 deep slice 최초 12개 이상 template의 필수 source/binder/observability/lifecycle field 100%, source 없는 규범ㆍ수치 0건 미달; six-family catalog 별도 확보 | 모델 학습 금지; source coverage/requirements authoring 연구로 pivot. 12개를 main-study cap으로 해석하지 않음 |
| dry-run 종료 | binder recomputation <0.95 또는 injected `UNSUPPORTED` precision <0.90 | binder/context adapter 수정, 자동 hard enforcement 금지 |
| formal pilot | 최대 두 차례 지침 수정 후 applicability α<0.67 | main annotation 중단, ontology와 범위 축소 |
| semantic 평가 | `VALIDATED` precision <0.90 | expert review tool로 pivot; coverage를 높이기 위한 임의 값 생성 금지 |
| applicability 평가 | B10이 strongest scene-only/RTCD-style baseline보다 macro-F1 5%p 이상 개선하지 못하거나 95% CI 하한≤0 | hybrid complexity 축소; template+deterministic binder 검토 |
| 제약 설계 평가 | EBLC가 flat SEBGI(B9) 또는 naive composition(B13)보다 lifecycle/false-deadlock/semantic acceptance에서 이득 없음 | 그래프 edge와 composition objective 축소; 통합 기여와 제약 기여를 분리 보고 |
| BCV 평가 | 과소ㆍ과잉제약 mutation macro recall <0.90 또는 target 판정 일치 <0.99 | automatic `VALIDATED` 금지; verifier/translation semantics 수정 |
| CoC ablation | scene+CoC가 scene-only보다 3%p 이상 개선하지 못하거나 shuffled-CoC에도 유지 | CoC-centric claim과 제목 제거 |
| lifecycle 평가 | event-local 대비 stale/missed-reactivation error 상대 30% 감소 실패 | runtime claim 축소, lifecycle 오류 taxonomy로 pivot |
| outcome 평가 | risk 개선 없음 또는 completion 절대 손실 >5%p | vehicle-safety outcome 주장 제거, requirements quality 연구로 전환 |
| evaluator gate | 생성기와 독립된 closed-loop oracle 확보 실패 | T-IV/T-ITS full outcome claim NO-GO |
| Alpamayo 평가 | prompt 의미 효과 없음 | external verifier/shield 결과만 별도로 보고 |

## 13. 예상 산출물

1. EBLC Graph ontology, canonical Guard IR/DSL 및 formal operational semantics
2. 근거와 provenance를 포함한 guard knowledge graph
3. `GuardBench-CoC` 전문가 데이터셋과 annotation protocol
4. CoC-conditioned evidence retrieval 및 guard synthesis 모델
5. 과소ㆍ과잉제약, lifecycle 및 compiler 의미보존을 검사하는 BCV와 assurance bundle
6. bidirectional counterexample benchmark 및 독립 counterfactual simulation/trajectory 평가 환경
7. Alpamayo-R1 integration과 평가 adapter
8. 가드 생성 및 적용 오류 taxonomy
9. 재현 가능한 실험 코드, split 및 evaluation protocol
10. DriveReg/RTCD4ADS/SanDRA adapter와 naive-composition baseline
11. 국제저널 논문 1편과 후속 정형검증 연구 입력물

## 14. 위험과 대응

| 위험 | 영향 | 대응 |
|---|---|---|
| 전문가 간 가드 합의가 낮음 | gold 신뢰도 저하 | 단일 문장 대신 허용 가드 집합ㆍ수치 범위 라벨, 파일럿 반복 |
| CoC가 원인 객체를 잘못 지목 | 잘못된 guard target | CoC claim과 sensor evidence를 분리하고 `UNGROUNDED_CAUSE` 반환 |
| 법적 관할을 확인할 수 없음 | 잘못된 legal guard | `UNSUPPORTED_JURISDICTION`, 법규 독립 물리 조건과 분리 |
| 수치 근거가 없음 | 안전 수치 환각 | 결정론적 binder만 사용하고 `UNSUPPORTED_VALUE` 반환 |
| 생성과 평가의 순환성 | 인위적으로 높은 성능 | 전문가 gold, 독립 physics 및 별도 simulator 사용 |
| 항상 정지하는 과잉제약 | 안전 지표만 개선 | goal completion, deadlock, progress loss, false rejection 동시 평가 |
| CASCADE의 eventful 편향 | nominal false rejection 과소평가 | 명목 장면 matched control 추가 |
| 자연 위반 사례 부족 | 통계력 저하 | 독립 counterfactual perturbation과 hard negative 생성 |
| Alpamayo의 약한 prompt semantics | E2E 효과 미확인 | 구조화 입력, verifier, reranker, shield 조건을 분리 |
| restricted data 공개 제한 | 재현성 제한 | 공개 코드ㆍIDㆍhashㆍ통계ㆍ합성 대체자료 제공 |
| 규칙과 ODD 변화 | stale guard | source version, validity interval 및 ODD scope 기록 |

## 15. 연구 윤리와 안전 주장 정책

1. 생성 가드는 운전자 또는 실차 배포를 위한 직접 지시로 사용하지 않는다.
2. `VALIDATED`는 정의된 데이터, 규칙, ODD 및 검증 범위 안의 판정이다.
3. 시뮬레이션 결과를 실제 차량 충돌 감소로 일반화하지 않는다.
4. 통계적 상관과 법적ㆍ물리적 안전 요구사항을 분리한다.
5. 생성 실패, 보류, 충돌 및 부정적 결과를 포함해 보고한다.
6. 모델과 데이터 라이선스, 접근 제한 및 redistribution 조건을 준수한다.
7. 전문가 의견은 출처와 adjudication 과정을 기록한다.

## 16. 성공 수준과 투고 전략

### 16.1 최소 성공

- EBLC Graph ontology, BCV와 GuardBench 구축
- applicability, 구조 및 provenance에서 baseline보다 유의하게 우수
- 실행 가능한 typed guard 생성
- 단위, 모순, 과소ㆍ과잉제약, lifecycle, translation 및 unsupported condition 검출
- 전문가 작성ㆍ검토 시간 감소

이 수준에서는 Journal of Systems and Software, Information and Software Technology 또는 Requirements Engineering 계열을 우선 검토한다.

### 16.2 목표 성공

- 실제 데이터와 외부 데이터에서 일반화
- 독립 시뮬레이션 위반률의 유의한 감소
- 목표 완료율 손실 5%p 이하
- Alpamayo-R1 직접 출력 적용
- 전문가 가드 효과에 근접

이 수준에서는 IEEE Transactions on Intelligent Vehicles를 1차 목표로 한다.

### 16.3 확장 성공

- 다중 데이터셋과 ODD 일반화
- 불확실성과 residual risk 정량화
- 수천 개의 폐루프 counterfactual 평가
- runtime verifier/shield와 통합
- 교통 상호작용과 운영 효율에 대한 명확한 효과

이 수준에서는 IEEE Transactions on Intelligent Transportation Systems 또는 Reliability Engineering & System Safety를 목표로 한다.

저널 공식 범위:

- [IEEE Transactions on Intelligent Vehicles](https://ieee-itss.org/pub/t-iv/)
- [IEEE Transactions on Intelligent Transportation Systems](https://ieee-itss.org/pub/t-its/)
- [Reliability Engineering & System Safety](https://www.sciencedirect.com/journal/reliability-engineering-and-system-safety)
- [Journal of Systems and Software](https://www.sciencedirect.com/journal/journal-of-systems-and-software)
- [Information and Software Technology](https://www.sciencedirect.com/journal/information-and-software-technology)

## 17. 선행ㆍ후속 연구와의 관계

```text
기존 Safety-Constrained CoC 연구
  주어진 guard가 행동 선택에 사용될 수 있는가?
                         |
                         v
본 연구: GuardSynth-CoC
  실제 장면에서 어떤 guard가 필요하며 EBLC로 어떻게 합성되고 BCV로 검증되는가?
                         |
                         v
후속 정형 행위 모델 연구
  생성ㆍ검증된 guard가 열린 환경의 모든 관련 실행에서 지켜지는가?
                         |
                         v
장기 통합 연구
  반례 유도 guard 생성ㆍ수정ㆍ실행 assurance loop
```

본 연구는 기존 정형 행위 모델 연구를 대체하지 않는다. 본 연구가 검증 가능한 규범적ㆍ물리적 guard를 공급하면, 정형 행위 모델은 여러 guard의 합성, 환경 분기, 교착, 위험 재등장 및 시간 지연에 대한 반례를 탐색한다. 장기적으로는 정형 검증의 반례를 guard 수정에 되돌리는 counterexample-guided guard synthesis로 통합한다.

## 18. 즉시 실행 항목

1. 한 관할과 세 deep vertical slice의 최초 12–20개 rule을 감사하되, 여섯 행동군 broad applicability benchmark의 family coverage 표를 함께 만든다.
2. `ContextGraph`, `RuleTemplate`, `EvidenceRecord`, `PredicateSpec`, EBLC Graph 및 canonical Guard IR v0의 operational semantics를 확정한다.
3. 각 rule의 partial binder, lifecycle edge와 관측 입력/freshness/failure-to-UNKNOWN path를 구현ㆍ검사한다.
4. 세 slice별 8개, 총 24장면 schema dry-run과 전문가 UI를 수행한다.
5. BCV의 과소/과잉제약 논리, translation relation과 생성기 코드ㆍrule을 공유하지 않는 evaluator 설계/locked-test manifest를 라벨링 전에 고정한다.
6. free-form, template, DriveReg-style, RTCD-style, physics-only, SanDRA-like 및 세 시스템 naive-composition baseline을 구현한다.
7. CASCADE–PhysicalAI 교집합과 matched nominal control을 포함한 60장면 formal pilot을 선정한다.
8. missing/extra/bound/lifecycle/translation defect mutation suite를 구축해 BCV 검출률과 원인 localization을 먼저 확인한다.
9. agreement, unsupported rate, 작업시간과 cluster effect로 main GuardBench N과 예산을 power analysis한다.

## 19. 참고 문서와 관련 연구

### 프로젝트 내부 문서

- [EBLC-P0b CoCㆍ제약사항→SMT 변환ㆍ검증 보고서](../../reports/EBLC_P0B_COC_CONSTRAINT_SMT_VERIFICATION_REPORT_V1.md)
- [상황 인지형 가드 합성 선행연구 서베이와 기술 전략](../../surveys/guard-synth-coc/CONTEXT_AWARE_GUARD_SYNTHESIS_SURVEY_AND_STRATEGY_V1.md)
- [Safety-Constrained CoC 진행 보고서](../../reports/SAFETY_CONSTRAINED_COC_PROGRESS_REPORT_V1.md)
- [기존 국제저널 확장 계획](../../../papers/paper1-safety-constrained-coc/INTERNATIONAL_JOURNAL_EXPANSION_PLAN.md)
- [CoC 정형검증 연구계획](../alpamayo-coc-formal-verification/RESEARCH_PLAN_V1.md)
- [CoC-KG-UPPAAL 배경 설계](../../designs/system/2026-07-31-coc-kg-model-checking-design.md)

### 외부 관련 연구ㆍ표준

- [Formalizing Traffic Rules for Machine Interpretability](https://arxiv.org/abs/2007.00330)
- [Enhancing Transformation from Natural Language to Signal Temporal Logic Using LLMs with Diverse External Knowledge](https://arxiv.org/abs/2505.20658)
- [Guiding LLM Temporal Logic Generation with Explicit Separation of Data and Control](https://arxiv.org/abs/2406.07400)
- [Safety of Intended Driving Behavior Using Rulebooks](https://arxiv.org/abs/2105.04472)
- [Formal RSS verification for autonomous driving](https://arxiv.org/abs/2305.08812)
- [DriveReg: Multi-Region Retrieval-Augmented Autonomous Driving with Traffic Regulations](https://doi.org/10.1609/aaai.v40i45.41168)
- [Runtime Traffic-Rule Compliance Detection for ADS](https://www.sciencedirect.com/science/article/pii/S0164121226001615)
- [SanDRA: Safe Driving with LLM Reasoning and Formal Verification](https://arxiv.org/abs/2510.06717)
- [ISO 21448:2022, Road vehicles — Safety of the intended functionality](https://www.iso.org/standard/77490.html)
- [ISO/PAS 8800:2024, Road vehicles — Safety and artificial intelligence](https://www.iso.org/standard/83303.html)
