# GuardSynth-CoC 전체 프로젝트 단계 현황 v1

- 기준일: 2026-08-10
- 소프트웨어 상태: `P0_SOURCE_CATALOG_COMPLETE + LABEL_LIGHT_SOFTWARE_PATH_IMPLEMENTED`
- 실증 연구 상태: `P1_24_SLOT_READY / BLOCKED_SOURCE_COMPLETE_INPUT`
- 다음 gate: source-complete 실제 24장면 dry run
- 현재 작업과 고정 순서: [프로젝트 실행 추적표](../plans/guard-synth-coc/PROJECT_EXECUTION_TRACKER.md)
- 전체 완료/미완료 Todo: [프로젝트 마일스톤 원장](../plans/guard-synth-coc/PROJECT_MILESTONES.md)

## 1. 한 문장 현황

**생성 제약을 표현·검증하는 backend는 pedestrian conflict-zone synthetic 범위에서 먼저
완성됐지만, 연구의 중심인 `CoC+scene+evidence → 제약 생성 → 효과 평가`는 아직 실제
24장면 dry run 전 단계다.**

따라서 프로젝트 전체가 거의 끝난 것도 아니고, EBLC부터 다시 만들어야 하는 것도 아니다.
P0 대한민국 source catalog는 완료됐다. 지금부터의 중심은 P1 실제 입력 24개를
source-complete로 만든 뒤, P2 CoC-conditioned front-end와 기준선을 만들고 empirical
effect를 평가하는 것이다.

## 2. 원래 구현 단계에 대한 위치

계획은 P0→P6 순서지만, compiler risk를 먼저 제거하기 위해 P3 일부를 앞당겨 구현했다.
그러므로 단일 진행률 대신 다음 상태를 사용한다.

| 원 계획 | 현재 상태 | 근거와 남은 일 |
|---|---|---|
| P0 source policy, EBLC 의미론, catalog | **완료** | 대한민국 현행 법령, structured-road ODD, 세 deep slice 15개 source-bearing template와 six-family audit 통과 |
| P1 adapter, ContextGraph, provenance, 24 dry run | **진행 중/입력 차단** | adapter·registry·label-light interface는 구현. 후보 5/24, partial 4, source-complete 0/24 |
| P2 retrieval, reranker, 선행 baseline | **미착수** | DriveReg/RTCD/SanDRA adapter와 B0–B8/B13 비교 구현 필요 |
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

### 현재 차단 단계

- 기존 파생 perception/map/trajectory 출력을 source-complete label-light packet으로 바꾸는 adapter
- 작은 층화 calibration/audit set 작성
- 검증된 rig→ego-path transform source
- 실제 vehicle binding과 validation/assurance source
- source-complete 24장면 dry run

### 그 이후

1. 60장면 formal expert pilot과 agreement/작업시간 측정
2. retrieval·scene-only·flat contract·naive composition 등 baseline 비교
3. applicability, provenance, under/overconstraint, lifecycle 성능 평가
4. 독립 closed-loop/counterfactual outcome evaluation
5. phase gate 통과 시 Alpamayo-R1 CoC 적용과 runtime monitor/shield 평가
6. power analysis 후 main GuardBench 규모 확정

## 5. 현재 판단

label-light 계층은 완전 라벨 의존을 낮추는 software 해법이다. 그러나 현재 제한 파생물에는
승인된 confidence calibration, 검증된 transform과 실제 vehicle assurance가 없으므로 기존
네 partial scene을 자동 `VALIDATED`로 승격할 수 없다. 현재 판단은 다음 두 문장으로 분리한다.

- **Software decision:** label-light 구조화 경로를 다음 adapter 단계에 사용할 수 있다.
- **Research decision:** 실제 source-complete 24장면이 없어 `DATA_GAP_PIVOT`을 유지한다.

다음 종료 가능한 단일 milestone은 “24장면 전부 수작업 라벨”이 아니라, 현재 5개 후보의
association/transform/assurance 근거를 보강하고 확보 가능한 장면을 추가해 24-slot을
source-complete로 채우는 것이다. slot 계획은 완료됐지만 실제 실행은 0/24다.

검토 방법 자체는 [scene-evidence review kit](../../artifacts/results/public/guardsynth-scene-evidence-review-001/scene-evidence-review-2026-08-10-v5/SCENE_EVIDENCE_REVIEW.html)으로
고정했다. 로컬 장면 이미지를 보면서 association, transform/time, rule applicability,
필요 assurance와 lifecycle을 기록하고 자동 권고를 받을 수 있다. 이 도구의 완성은 실제
근거의 확보와 다르므로 `DATA_GAP_PIVOT` 및 0/24 상태는 유지된다.

## 6. P0 catalog 및 24-slot 준비 근거

[대한민국 catalog audit](../../artifacts/results/public/guardsynth-source-catalog-001/kr-source-catalog-2026-08-10-v2/REPORT_KO.md)은
공식 source record 6개/claim 16개에 세 slice 15개 template를 연결하고 six-family 6/6,
source 없는 규범·실행 수치 0건, maintained 202/202를 기록했다. 법에 수치가 없는
필요 안전거리는 `UNSUPPORTED`로 남겼다.

[24-slot readiness](../../artifacts/results/public/guardsynth-24-scene-dry-run-001/kr-dry-run-readiness-2026-08-10-v1/)는
세 slice별 8개와 네 strata를 고정한다. 실제 source-complete 입력은 0/24이므로 synthetic
fill 없이 `M13_BLOCKED_SOURCE_COMPLETE_SCENES`로 중단한다.

## 7. label-light v0.1 실행 근거

[완료 run](../../artifacts/results/public/guardsynth-label-light-grounding-001/label-light-2026-08-10-v3/REPORT_KO.md)은
synthetic 판정 시나리오 8/8, label-light 집중 테스트 15/15, 전체 maintained 187/187,
P0a 7/7, 구조/링크 9/9를 통과했다. 자동 확인된 synthetic 두 장면은 실제 project-local
Z3 5.0.0까지 전달되어 query agreement 100%를 기록했다. 기존 제한 입력은 식별자 없는
집계에서 association review 4건, 자동 확인 0건이므로 실증 단계 판단은 바뀌지 않는다.
