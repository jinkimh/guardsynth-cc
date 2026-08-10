# Experiment Results

- `public/`: 기존 CPU/UPPAAL 재현 결과와 반례
- `restricted/`: NVIDIA 공식 데이터 및 실제 모델 출력에 기반한 제한 결과

`restricted/`는 `.gitignore` 대상이다. 공개용 집계 결과를 만들 때에도 라이선스와 confidentiality 범위를 먼저 확인한다.

현재 `restricted/alp-exp-005/`에는 실제 모델이 생성한 CoC trace와 trajectory가 있다. 성공한 seed 42ㆍ43ㆍ44는
SDPA compatibility fallback 결과이며 정식 FlashAttention 2 reference 결과와 구분한다. 세부 인덱스와 별도
무결성 manifest는 제한 디렉터리 내부에 둔다.

공개 합성 결과 `public/contract-microworld-v0/`는 NVIDIA 원문·영상·trajectory를 사용하지 않는다. 이 결과는
작은 정책에서 계약 표현과 실행 강제 메커니즘을 분리하는 feasibility gate이며 실제 차량 안전성 근거가 아니다.

`public/contract-microworld-v1/pilot-phase-complete-isolated-2026-08-04-v2/`는 v0에서 누락됐던
`STOP 완료 후 HOLD` 성공 시연을 추가한 통제 재실험이다. 최신 STOP 해석은 이 결과를 우선한다.

`public/contract-microworld-v2/pilot-release-reversal-2026-08-04-v1/`는 frozen v1 정책을 학습에 없던
재진입·재등장·재occlusion에 적용하고 correct/stale contract, reactive/oracle-lookahead shield를 비교한 심층 stress 결과다.

`public/eblc-pilot-v0/pilot-2026-08-08/`는 synthetic 보행자 conflict-zone 요구사항을 검색ㆍ결합해
EBLC lifecycle monitor에서 실행하고, BCV의 under/overconstraint mutation witness를 확인한 표준 라이브러리 기반
mechanism pilot이다. 실제 법규ㆍ센서ㆍ차량 안전성 근거가 아니다.

`public/eblc-p0b-001/p0b-2026-08-08-v1/`는 schema-driven EBLC v0의 canonical interpreter,
별도 runtime monitor와 bounded exhaustive enumerator가 8개 locked trace에서 100% 일치하고, controlled
under/overconstraint mutation을 각각 5/5 검출한 결과다. 실제 장면 연결은 필수 geometryㆍassociationㆍego-state/profile
bundle 부족으로 `P0B_REAL_ADAPTER_BLOCKED_DATA_GAP`이며, 제한 field-readiness artifact는 같은 run ID 아래
`restricted/eblc-p0b-001/`에 분리했다. 이는 bounded software semantics 결과이지 실제 법규ㆍ센서ㆍ차량 안전성 근거가 아니다.

`restricted/eblc-p0b-001/p0b-data-adapter-2026-08-08-v1/`는 위 data gap을 재감사해 기존 obstacle-event와
recorded ego-future 파생물만으로 VRU 후보 5개 중 4개의 schema-valid partial ContextGraph를 만든 후속 실행이다.
네 후보 모두 target association이 ambiguous하고 vehicle assurance profile 및 rig→canonical frame 검증이 없어
contract는 4/4 `UNSUPPORTED`다. raw IDㆍCoC 원문ㆍsensorㆍvideo는 결과에 포함하지 않았다.

`public/eblc-robustness-audit-001/robustness-multienv-2026-08-08-v3/`는 공개 EBLC 코어를 기본 Python과
z3 4.16.0 환경에서 구조 오류, 4값 상태공간, 수치 경계, 비정상 실수, 빈 trace, 시간 역행, compiler 독립성 및
solver/report 정합성으로 감사한 최신 실행이다. 13개 probe 중 5개가 통과하고 8개 gap을 발견해 상태는
`EXECUTED_WITH_GAPS`다. 특히 실제 z3 solver construction 없이 `Z3_BOUNDED_SMT`로 표시되는 문제가 있어 24-scene
연결 전 판단을 `SEMANTICS REWORK`로 교정한다. 앞선 v1/v2는 probe 확장 이력을 보존한다.

`public/eblc-p0b-001/p0b-src-cli-multiview-2026-08-08-v1/`는 `src/guard_synth_eblc`와 목적별 CLI 재구성 후
P0a 7/7, P0b 38/38, locked translation 8/8, under/over mutation 각 5/5를 재확인한 실행이다. 제한 adapter의
동일 구조 재실행은 `restricted/eblc-p0b-001/p0b-restricted-grounding-multiview-2026-08-08-v1/`에 두며 raw
clip ID와 CoC 원문을 포함하지 않는다.

`public/eblc-p0b-001/p0b-z3-env-audit-2026-08-08-v1/`는 z3 4.16.0이 import되는 환경에서 기존 P0b runner를
실행한 진단 결과다. runner는 `Z3_BOUNDED_SMT`를 기록하지만 실제 checker에는 solver construction이 없고 보고서에는
동시에 “z3-solver가 없다”는 문구가 남아 있다. 따라서 이 실행의 8/8 agreement를 SMT 검증 결과로 사용하지 않는다.

`public/eblc-p0b-001/p0b-z3-smt-2026-08-08-v4/`는 프로젝트 로컬 Z3 5.0.0을 명시적으로 선택하고 실제
`z3.Solver` 제약 인코딩을 실행한 최초 P0b 결과다. P0a 7/7, P0b 41/41, canonical–runtime 및 canonical–Z3
locked-trace agreement 각 8/8, under/over mutation 각 5/5를 기록했다. lifecycle 불허 전이, reactivation 누락 및
false-deadlock baseline query는 UNSAT, 활성 stop-position 위반 탐색은 SAT이었다. 이는 bounded translation 및
falsification 결과이며 독립 safety oracle이나 차량 안전 증명이 아니다. solver 경로는 사용자별 절대경로가 아닌 저장소
상대경로로 manifest에 기록하며 solver 선택 코드의 hash도 포함한다.

`public/eblc-robustness-audit-001/robustness-z3-smt-2026-08-08-v5/`는 실제 Z3 construction과 report/engine
정합성 문제가 해결됐음을 확인한 fail-closed 보강 이전 감사다. 다만 13개 probe 중 7개만 통과했다. non-finite schema/profile/scene,
empty trace, non-monotonic timestamp 및 runtime parameter schema coverage의 6개 fail-closed gap은 기대값을 바꾸지 않고
그대로 보존했다. 따라서 SMT target 구현은 완료됐지만 24-scene 확장 전 의미론 입력 방어를 보강해야 한다.

`public/eblc-p0b-001/p0b-fail-closed-2026-08-08-v1/`는 schema/semantics v0.2 및 compiler v0.3의 최신
P0b 실행이다. non-finite JSONㆍbindingㆍscene/contract 수치, empty trace, decreasing timestamp를 `UNSUPPORTED`로
거부하고 runtime이 소비하는 다섯 parameter와 derivation DAG를 contract schema 필수 필드로 고정했다. P0a 7/7,
P0b 43/43, 두 translation agreement 각 8/8, under/over mutation 각 5/5와 실제 Z3 네 query의 기존 방향을 유지했다.

`public/eblc-robustness-audit-001/robustness-fail-closed-2026-08-08-v6/`는 동일 구현의 고정 적대적 감사를
13/13, gap 0으로 통과한 최신 결과다. 이는 명시된 13개 software robustness probe에서 추가 gap을 찾지 못했다는 뜻이며,
실제 법규ㆍ센서ㆍ차량 안전성 또는 감사 집합 밖 결함의 부재를 증명하지 않는다.

`public/eblc-core-smt-001/core-smt-2026-08-08-v4/`는 공개 typed EBLC Core v0.1을
일반 Z3 식으로 변환한 최초 고정 실행이다. 14개 선언ㆍ16개 clauseㆍhorizon 5의 synthetic P0b 대표 fixture에서
논리ㆍ산술ㆍ`ite`ㆍbounded `always/eventually/until`을 컴파일하고, query 7/7 기대 방향, Core 전용 12/12 및
전체 P0b 55/55 회귀를 통과했다. 생성한 SMT-LIB 8개도 project-local Z3 실행 파일에서 8/8 동일하게 재실행됐다.
SMT-LIB, symbol table, source map과 query witness를 보존한다. 이는 bounded compiler
mechanism evidence이며 P0b canonical interpreter와의 모든-input 동등성이나 차량 안전 증명이 아니다.

`public/eblc-elaboration-conformance-001/elaboration-conformance-2026-08-08-v3/`는 수식 AST가 없는
evidence-bearing 고수준 EBLC program을 freshnessㆍepistemic failureㆍlifecycleㆍverdictㆍ위반ㆍprogress Core 식으로
자동 전개한 최초 실행이다. canonical과 Core-SMT는 129개 생성 trace/266개 frame에서 비교 필드 전체가 100% 일치했고,
elaborator 11/11, 전체 P0b 66/66, P0a 7/7 및 SMT-LIB 직접 재실행 2/2를 통과했다. v1은 runner가 최종
RESULT를 쓰기 전에 종료된 불완전 실행으로 별도 marker만 보존한다. 이 결과는 번역 근거이며 독립 safety oracle이나
차량 안전 증명이 아니다.

`public/eblc-scenario-test-001/scenario-matrix-2026-08-08-v3/`는 공개 EBLC를 44개 명시적 단위ㆍ통합
시나리오로 재검증한 최신 실행이다. schema/program 음성 입력 9개, lifecycle/policy 변형 9개, 정지 위치ㆍfreshnessㆍ
미래 timestampㆍ동적 속도 경계 23개와 failure/epistemic/horizon 3개를 포함한다. scenario 11/11, Core-SMT 12/12,
elaboration 11/11, robustness 10/10, 전체 P0b 77/77, P0a 7/7이 모두 통과했다. 최초 실행에서 binary-float
경계 오차 두 건을 발견해 의미 epsilon과 분리된 1e-15 roundoff guard로 수정하고 동일 기대값으로 재실행했다.
v1은 target별 coverage 표의 범위가 과도하게 묶인 기록이고 v2는 이를 정정했지만 version manifest 보강 전이다. v3가 최신 보고다. 이는 synthetic software
validation이며 법규ㆍ차량 안전성 증거가 아니다.

`public/eblc-composition-compilation-001/composition-compilation-2026-08-09-v1/`는 둘 이상의 고수준
EBLC program을 non-scalar `HARD > SERVICE > PREFERENCE`와 비순환 override로 구성하고, 선택 계약의 action
교집합ㆍ충돌ㆍreviewㆍfalse-deadlock을 namespaced Core와 실제 Z3 SMT로 변환한 고정 실행이다. 기존 기준선
77/77, 신규 composition 12/12, 전체 EBLC 89/89, P0a 7/7, canonical/Core-SMT scenario 5/5와 SMT-LIB
직접 replay 2/2를 통과했다. 이는 bounded synthetic translation evidence이며 독립 safety oracle, 실제 법규 또는
차량 안전성 증거가 아니다.

`public/eblc-derivation-compilation-001/typed-derivation-2026-08-09-v1/`는 TDD로 구현한
`eblc-derivation-v0.1` companion spec을 기존 program Core에 적용해 synthetic stop position의 정적 binding을
typed `SUB` DAG로 교체한 실행이다. Z3 exact witness `-3/2`, locked trace agreement 8/8, 구현 전 기준선
89/89, 신규 derivation 11/11, 전체 EBLC 100/100, P0a 7/7 및 SMT-LIB replay 2/2를 통과했다.
이는 bounded symbolic replay evidence이며 free-form operation 해석, 실제 규칙/차량 값 또는 안전성 증거가 아니다.

`public/eblc-elaboration-conformance-001/elaboration-conformance-2026-08-09-v02-typed-derivation-v4/`는
`eblc-program-v0.2` 안에 typed derivation을 직접 포함하고 stop position, response distance, braking distance와
total stopping distance를 하나의 source-bearing DAG에서 Core/SMT로 전개한 최신 실행이다. speed-violation clause가
derived `stopping_distance`를 실제 사용하며, Z3 exact witness `-3/2 m`와 `9 m`, canonical–Core-SMT
129/129 traceㆍ266/266 frame, v0.2 신규 11/11, 전체 EBLC 111/111, P0a 7/7 및 SMT-LIB replay 2/2를
기록했다. v1~v3은 nonnegative effective-speed, input artifact 및 fail-closed interface를 확정하는 과정의 이전 실행으로 보존한다.
이는 bounded synthetic translation evidence이며 source 진위, 실제 차량 성능 또는 안전성 증거가 아니다.

`public/eblc-composition-compilation-001/composition-v02-typed-derivation-2026-08-09-v2/`는
두 `eblc-program-v0.2`의 typed stopping-distance DAG를 계약별 namespace로 분리해 bundle composition,
Core와 실제 Z3 SMT까지 전달한 최신 실행이다. 구현 전 기준선 111/111, 신규 composition-v0.2 8/8,
전체 EBLC 119/119, P0a 7/7, canonical/Core-SMT scenario 5/5 및 SMT-LIB replay 2/2를 통과했다.
Z3 exact stopping-distance witness는 계약별 `9`, `3`이며, 두 계약×아홉 frame의 분모 비영 assertion
18개를 보존했다. 이는 bounded synthetic translation evidence이며 실제 규칙ㆍ차량 성능 또는 안전성 증거가 아니다.

`public/eblc-indexed-collection-001/indexed-collection-2026-08-09-v1/`는 하나의
`eblc-program-v0.2` template에서 두 actor–conflict-zone instance를 확장해 bundle, Core와
실제 Z3 SMT로 전달한 실행이다. Z3 exact stop position은 `-3/2`, `21/2`, stopping distance는
`9`, `3`이고 division definedness 18개를 보존했다. 모호한 target probe는
`REVIEW_REQUIRED`와 bundle 미생성을 반환했다. 기존 119/119, 신규 9/9, 전체 EBLC
128/128, P0a 7/7 및 SMT-LIB replay 2/2를 통과했다. 이는 synthetic bounded
expansion evidence이며 실제 associationㆍgeometryㆍ차량 성능 또는 안전성 증거가 아니다.

`public/eblc-release-candidate-001/eblc-v0.2-rc1-2026-08-09/`는 bounded EBLC
v0.2 언어·tooling 범위를 scoped release candidate로 동결한 결과다. program/bundle의
결정론적 controlled-natural-language projection, field/evidence mapping, input/output
hash, 요구사항 추적표와 최종 회귀 결과를 포함한다. CNL은 model prompt용 one-way
표현이며 구조화 EBLC가 실행 권위다. 자연어 CoC generator, 실제 association/profile
authoring 및 차량 안전성은 이 release의 완료 주장에 포함하지 않는다.

`public/guardsynth-source-aware-generator-001/source-aware-generator-2026-08-09-v3/`는
동결된 EBLC 앞단에 별도 `src/guard_synth` 생성 계층을 구현한 최초 공개 실행이다.
RuleTemplate/PredicateSpec catalog, structured ContextGraph, vehicle profile과 explicit
compiler policy가 완전할 때 program v0.2 및 두-instance indexed collection을 생성해
bundle→Core→Z3까지 전달했다. EBLC RC 기준선 138/138, 신규 12/12, 전체 150/150,
P0a 7/7, 구조 9/9 및 SMT-LIB replay 2/2가 통과했다. claim-only/missing/ambiguous/
conflict/unit-mismatch 6 probes는 collection을 만들지 않았다. 이는 synthetic source-flow
근거이며 free-form CoC 해석, 실제 association/profile 또는 차량 안전성 증거가 아니다.

`public/guardsynth-real-scene-readiness-001/terminal-readiness-2026-08-09-v3/`는
P0b의 24-slot 실제 입력 준비도를 종료 판정한 공개 집계다. 현재 후보 event는 5/24,
partial ContextGraph는 4개, source-complete scene은 0/24이고 입력 없는 19 slot은
`MISSING_SCENE_INPUT`으로 보존했다. source authoring 8/8, 적대적 source-boundary
14/14, 전체 172/172, 구조/링크 9/9를 통과했으며 판단은 `DATA_GAP_PIVOT`이다.
제한 상세 matrix는
`restricted/guardsynth-real-scene-readiness-001/terminal-readiness-2026-08-09-v3/`에
두며 raw identifier나 CoC 본문을 포함하지 않는다. 이는 readiness/abstention 결과이지
24개 실제 장면 계약 검증이나 차량 안전성 증거가 아니다.

`public/guardsynth-label-light-grounding-001/label-light-2026-08-10-v1/`은 기존
perception/map/trajectory proposal을 유일성·승인된 calibration·confidence 하한으로
자동 확인하거나 최소 검토/지원 불가/충돌로 분기하는 label-light v0.1 최초 실행이다.
공개 synthetic scenario와 두 장면 GuardSynth→EBLC→Core→Z3 handoff만 포함하고,
기존 제한 입력은 식별자 없는 집계만 기록한다. v1은 전체 185/185로 완료됐지만,
사람의 association 확인이 claim-only hazard를 승격하지 못하도록 시간·인식 경계를
추가한 후속 v2를 거쳐, 현재 코드 해시와 일치하는 v3를 최신 결과로 사용한다.

`public/guardsynth-label-light-grounding-001/label-light-2026-08-10-v3/`는 현재 코드 해시와
일치하는 완료된 label-light v0.1 기준 실행이다. v2도 같은 gate를 통과했지만 runner 정리 전
기록으로 보존한다. v3는 synthetic 판정 방향 8/8, 신규 15/15, 전체 maintained
187/187, P0a 7/7, 구조/링크 9/9와 두 장면 GuardSynth→EBLC→Core→Z3 query agreement
100%를 기록했다. 기존 제한 집계에서는 후보 5개 중 association review 4개, 자동 확인
0개, contract 입력 부족 4개로 판단해 `LABEL_LIGHT_SOFTWARE_GO_DATA_GAP_PIVOT_REMAINS`다.
이는 label-light workflow 구현 결과이며 실제 association 정확도나 차량 안전성 증거가 아니다.
