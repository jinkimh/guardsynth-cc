# GuardSynth-CoC 전체 프로젝트 단계 현황 보고서 v1

- 기준일: 2026-08-12
- 소프트웨어 상태: `P0_SOURCE_CATALOG_COMPLETE + LABEL_LIGHT_SOFTWARE_PATH_IMPLEMENTED`
- 실증 연구 상태: `P1_SIM24_TERMINAL_SHORTFALL / 4_OF_24_EXECUTED`
- 현재 구현 단계: `P2_COC_CONDITIONED_FRONTEND_ACTIVE`
- 다음 gate: structured CoC+scene+evidence constraint proposal bundle
- 현재 작업과 고정 순서: [프로젝트 실행 추적표](../plans/03_PROJECT_EXECUTION_TRACKER.md)
- 전체 완료/미완료 Todo: [프로젝트 마일스톤 원장](../plans/02_PROJECT_MILESTONES.md)

2026-08-12 일정 결정에 따라 실제 차량 assurance와 실차 실증은 논문 원고·재현 패키지 및
적용 가능한 특허 출원 절차 이후 M21로 이관했다. M13은 실제 장면 필드 8종을 유지하고
별도 simulation vehicle binding만 사용해 4장면·17계약을 실행한 뒤 20장면 부족을 terminal
decision으로 고정했다. 이 변경은 실제 차량
안전성 주장 기준을 완화하지 않는다.

## 1. 한 문장 현황

**생성 제약을 표현·검증하는 backend는 pedestrian conflict-zone synthetic 범위에서 먼저
완성됐고 실제/파생 4장면과 가상 차량의 변환 실행도 확인했지만, 연구의 중심인
`CoC+scene+evidence → 제약 생성 → 효과 평가`는 이제 P2 front-end 구현 단계다.**

따라서 프로젝트 전체가 거의 끝난 것도 아니고, EBLC부터 다시 만들어야 하는 것도 아니다.
P0 대한민국 source catalog와 M13 terminal failure taxonomy는 완료됐다. 지금부터의 중심은
P2 CoC-conditioned front-end와 기준선을 만들고 empirical effect를 평가하는 것이다.
M13의 4/24 결과를 24장면 성공으로 해석하지 않는다.

## 2. 원래 구현 단계에 대한 위치

계획은 P0→P6 순서지만, compiler risk를 먼저 제거하기 위해 P3 일부를 앞당겨 구현했다.
그러므로 단일 진행률 대신 다음 상태를 사용한다.

| 원 계획 | 현재 상태 | 근거와 남은 일 |
|---|---|---|
| P0 source policy, EBLC 의미론, catalog | **완료** | 대한민국 현행 법령, structured-road ODD, 세 deep slice 15개 source-bearing template와 six-family audit 통과 |
| P1 adapter, ContextGraph, provenance, 24 dry run | **terminal shortfall 종결** | 4장면·17계약 실행; 20장면과 두 slice/outcome strata 부족을 합성하지 않고 기록 |
| P2 retrieval, reranker, 선행 baseline | **front-end 활성** | CoC/scene typed parser, retrieval/applicability/binding을 먼저 구현; baseline은 M15 |
| P3 composer, binder, lifecycle, BCV, compiler | **scoped software 완료** | pedestrian bounded synthetic 범위에서 composition, typed derivation, Core, Z3, mutation/translation 검증 완료 |
| P4 GuardBench, 60-scene pilot | **미착수** | 24-scene dry run 통과 후 annotation protocol·전문가 pilot 수행 |
| P5 독립 closed-loop evaluator | **미착수** | generator와 코드를 공유하지 않는 oracle/simulator 필요 |
| P6 Alpamayo/runtime 적용 | **부분 adapter 탐색만 수행** | 제한 파생 입력 read-only audit 외 실제 계약 실행·효과 평가는 미수행 |

## 3. 지금까지 실제로 완료한 software spine

1. EBLC v0.2 representation, lifecycle, composition과 priority 충돌 의미론
2. 고수준 EBLC → typed derivation → Core → SMT-LIB/Z3 변환
3. canonical/runtime/Z3 bounded translation agreement와 BCV controlled mutation
4. source-aware GuardSynth structured generator
5. exact vehicle assurance registry와 fail-closed source authoring
6. label-light target–zone proposal triage와 최소 확인 interface
7. 이미지·방법·예제·필수 항목과 fail-closed 판정을 가진 scene-evidence review kit
8. 공개 synthetic result와 restricted-derived 비식별 readiness 분리

이 완료는 software mechanism에 관한 것이며 RQ1–RQ7의 실증 가설을 입증한 것이 아니다.

## 4. 연구상 아직 남은 핵심

### 현재 구현 단계

- CoC intent/cause/action/uncertainty typed parser
- CoC claim과 observed/derived scene fact의 구조적 분리
- source catalog retrieval와 four-valued applicability
- target/zone partial binding 및 기존 GuardSynth request 연결
- missing evidence abstention과 metamorphic test

### 그 이후

1. 60장면 formal expert pilot과 agreement/작업시간 측정
2. retrieval·scene-only·flat contract·naive composition 등 baseline 비교
3. applicability, provenance, under/overconstraint, lifecycle 성능 평가
4. 독립 closed-loop/counterfactual outcome evaluation
5. phase gate 통과 시 Alpamayo-R1 CoC 적용과 runtime monitor/shield 평가
6. power analysis 후 main GuardBench 규모 확정

## 5. 현재 판단

label-light 계층은 완전 라벨 의존을 낮추는 software 해법이다. 네 장면은 transform,
association, recorded-rig binding을 포함한 8개 장면 필드를 source-linked 상태로 닫았지만,
나머지 후보와 outcome strata는 여전히 불완전하다. 현재 판단은 다음 두 문장으로 분리한다.

- **Software decision:** label-light 구조화 경로를 다음 adapter 단계에 사용할 수 있다.
- **Research decision:** M13은 4/24 terminal shortfall이며, P2 software 진행과 병행해 데이터
  부족을 후속 empirical limitation으로 유지한다.

M14 scoped front-end software는 완료했다. 세 slice의 24개 locked synthetic 경계조건에서
schema/기대 verdict 24/24, CoC authority 승격과 원문 출력 0건을 기록했다. 지원된 횡단보도
proposal은 법규 근거와 수치 근거를 분리한 채 GuardSynth→단일 EBLC→Core→Z3로 2/2
전달됐다. 이는 실제 24장면, 일반 NLP 또는 법률 적용 정확도가 아니며 operational policy
mapping도 primary rule 1/3에 한정된다.

M14 종료 당시 다음 milestone은 M15였다. M14 proposal bundle을 공통 출력으로 사용하여 CoC-only,
scene-only, free-form, flat/template 및 선행시스템 유사 adapter를 같은 source budget과
abstention metric 아래 동결한다.

M15 baseline protocol은 이후 완료됐다. B0–B8/B13의 24×10=240개 공통 결과가 schema를
통과했고 channel firewall 위반과 hidden failure는 0건이었다. 품질 점수는 독립 gold가 없어
계산하지 않았다. 이어서 M16 60-scene preflight를 실행한 결과 source-complete 장면은
4/60이며 56개가 부족했다. [preflight](../../../../artifacts/results/restricted/guardsynth-expert-pilot-preflight-001/m16-preflight-2026-08-12-v4/REPORT_KO.md)는
blinded assignment, 두-mode training UI, annotation/metrics/power 계약까지 동봉한다. 다만
annotation start는 금지되며 실제 expert gold와 관측 effect/variance가 없으므로 M17과
power 결과는 시작·생성하지 않는다.

검토 방법 자체는 [scene-evidence review kit](../../../../artifacts/results/public/guardsynth-scene-evidence-review-001/scene-evidence-review-2026-08-10-v5/SCENE_EVIDENCE_REVIEW.html)으로
고정했다. 로컬 장면 이미지를 보면서 association, transform/time, rule applicability,
필요 assurance와 lifecycle을 기록하고 자동 권고를 받을 수 있다. 이 도구의 완성은 실제
근거의 확보와 다르며 M13 결과는 4/24 terminal shortfall이다.

## 6. P0 catalog 및 24-slot 준비 근거

[대한민국 catalog audit](../../../../artifacts/results/public/guardsynth-source-catalog-001/kr-source-catalog-2026-08-10-v2/REPORT_KO.md)은
공식 source record 6개/claim 16개에 세 slice 15개 template를 연결하고 six-family 6/6,
source 없는 규범·실행 수치 0건, maintained 202/202를 기록했다. 법에 수치가 없는
필요 안전거리는 `UNSUPPORTED`로 남겼다.

[24-slot readiness](../../../../artifacts/results/public/guardsynth-24-scene-dry-run-001/kr-dry-run-readiness-2026-08-10-v1/)는
세 slice별 8개와 네 strata를 고정했다. 당시 실제 source-complete 입력은 0/24이므로
`M13_BLOCKED_SOURCE_COMPLETE_SCENES`를 기록했다. 현재는 장면 필드의 synthetic fill 없이
8개 실제/파생 근거와 별도 simulation binding을 사용해 4장면을 실행했다. [M13 terminal
batch](../../../../artifacts/results/restricted/guardsynth-sim24-batch-001/alpamayo-terminal-batch-2026-08-12-v1/REPORT_KO.md)는
17계약의 canonical/runtime/bounded-Z3/Core/direct replay 100%와 20장면 부족을 함께 기록한다.

## 7. label-light v0.1 실행 근거

[완료 run](../../../../artifacts/results/public/guardsynth-label-light-grounding-001/label-light-2026-08-10-v3/REPORT_KO.md)은
synthetic 판정 시나리오 8/8, label-light 집중 테스트 15/15, 전체 maintained 187/187,
P0a 7/7, 구조/링크 9/9를 통과했다. 자동 확인된 synthetic 두 장면은 실제 project-local
Z3 5.0.0까지 전달되어 query agreement 100%를 기록했다. 기존 제한 입력은 식별자 없는
집계에서 association review 4건, 자동 확인 0건이므로 실증 단계 판단은 바뀌지 않는다.
