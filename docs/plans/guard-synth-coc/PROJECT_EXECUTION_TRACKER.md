# GuardSynth-CoC 프로젝트 실행 추적표

- 문서 성격: 지속 갱신하는 프로젝트 관리 기준 문서(living document)
- 기준 연구계획: [RESEARCH_PLAN_V1.md](RESEARCH_PLAN_V1.md)
- 전체 마일스톤/Todo: [PROJECT_MILESTONES.md](PROJECT_MILESTONES.md)
- 현재 상태 스냅샷: [GUARDSYNTH_PROJECT_STAGE_STATUS_V1.md](../../reports/GUARDSYNTH_PROJECT_STAGE_STATUS_V1.md)
- 마지막 갱신일: 2026-08-10
- 현재 연구 위치: `P0_SOURCE_CATALOG_COMPLETE + P1_DATA_GROUNDING_BLOCKED_INPUT`
- 현재 활성 작업 ID: `GS-P1-DRYRUN-001`
- 현재 전체 판단: `BACKEND_READY_IN_SCOPED_SYNTHETIC_SLICE / CORE_RESEARCH_NOT_YET_EVALUATED`

## 1. 이 문서의 역할

이 문서는 매 세션에서 “무엇을 할 것인가”를 결정하는 단일 실행 기준이다. 전체 연구 목적,
가설과 사전 성공 기준은 `RESEARCH_PLAN_V1.md`가 권위 문서이고, 이 문서는 그 계획을 변경하지
않은 채 현재 위치, 작업 순서, 선행조건, 완료 근거와 다음 작업을 추적한다.

문서별 책임은 다음과 같이 분리한다.

| 문서 종류 | 책임 | 갱신 시점 |
|---|---|---|
| 연구계획 | 최종 목적, RQ/가설, P0~P6, E-1~E6, Go/No-Go 기준 | 연구 범위나 gate가 실제로 변경될 때만 버전 갱신 |
| 이 실행 추적표 | 현재 단계, 활성 작업, 순서, 의존성, 완료 근거, 다음 작업 | 모든 유의미한 구현·실험 세션 종료 시 |
| 마일스톤 원장 | 완료 이력과 전체 미래 마일스톤의 Todo/종료 gate | Todo 또는 milestone 상태가 바뀔 때 |
| 요구사항 | 개별 work package의 입력, 산출물, 테스트와 주장 경계 | 해당 작업을 시작하기 전 |
| 설계 문서 | 인터페이스와 선택한 의미론/아키텍처 | 비자명한 구현 전 또는 구현과 함께 |
| 실행 artifact/report | 명령, 환경, 결과, 실패와 제한 | 실행할 때마다 새 run ID로 생성 |
| 상태 보고서 | 특정 시점의 인간 친화적 요약 | phase/gate 판단 시 snapshot으로 생성 |

## 2. 프로젝트의 최종 목적

최종 목표는 EBLC 자체가 아니라 다음 연구 가설을 검증하는 것이다.

```text
CoC + 실제 장면 + 외부 규칙/시스템 근거 + 차량 assurance
                              ↓
         현재 장면에 필요한 실행 제약 생성
                              ↓
    EBLC 구조화 → BCV/SMT/runtime 검증 → 계획에 적용
                              ↓
 위반 감소 + 과잉제약 억제 + 진행성 유지 + 전문가 효용 평가
```

EBLC, BCV와 Z3는 생성된 제약을 표현·검사하기 위한 백엔드다. 연구의 중심 주장은
`CoC+scene+evidence`가 `scene-only`, `CoC-only`, free-form 또는 flat-contract 기준선보다
더 적절한 제약을 생성하고 독립 평가에서 효과를 보이는지에 관한 것이다.

## 3. 전체 계획 대비 현재 위치

계획 순서와 구현 순서가 달랐다. compiler risk를 먼저 제거하기 위해 P3의 backend 일부를
앞당겼지만, 이것이 P0~P2와 실증 연구 완료를 뜻하지 않는다.

| 계획 단계 | 계획상 완료 조건 요약 | 현재 상태 | 완료 근거 | 남은 핵심 |
|---|---|---|---|---|
| P0 | 한 관할, 세 deep slice 최초 12개 이상 audited template, six-family coverage, source/binder/observability/lifecycle 100% | `COMPLETE` | 대한민국 scope decision, source-bearing 15 template, 3 slice, six families | 전문가 적용 검토와 후속 versioning |
| P1 | adapter, 4값 ContextGraph/provenance, 실제 24-scene dry run | `ACTIVE_BLOCKED_INPUT` | source authoring, label-light interface, 후보 5개/partial 4개 | source-complete 24개, transform, association calibration, vehicle assurance |
| P2 | CoC/scene parser, evidence retrieval/reranking, B0–B8/B13와 선행 시스템 adapter | `NOT_STARTED` | 없음 | front-end 생성기와 비교 기준선 전체 |
| P3 | composer, binder, lifecycle, BCV, multi-target translation | `SCOPED_BACKEND_COMPLETE` | bounded pedestrian synthetic Core/Z3, 187 maintained tests | 실제 catalog/장면과 타 slice에서 통합 검증, 독립 oracle |
| P4 | GuardBench 도구와 60-scene 전문가 formal pilot | `NOT_STARTED` | 없음 | annotation protocol, agreement, adjudication, power analysis |
| P5 | 생성기와 독립된 closed-loop evaluator와 E4 | `NOT_STARTED` | 없음 | evaluator independence와 outcome suite |
| P6 | Alpamayo adapter, runtime monitor/shield, E5 | `PARTIAL_EXPLORATION` | 제한 파생 입력 read-only audit | phase-gated 실제 적용과 효과 평가 |

연구 질문 관점에서는 RQ3/RQ4의 **기계적 feasibility 일부**만 확인했다. RQ1·RQ2의
CoC-conditioned 생성 정확도, RQ5의 효과/진행성, RQ6의 일반화, RQ7의 Alpamayo 적용은
아직 답하지 않았다.

## 4. 앞으로의 고정 실행 순서

아래 순서는 선행조건을 만족하지 않은 상태에서 뒤 단계로 넘어가지 않기 위한 critical path다.
`READY`인 첫 작업만 다음 활성 작업으로 선택한다.

| 순서 | 작업 ID | 작업 | 상태 | 선행조건 | 종료 gate/산출물 |
|---:|---|---|---|---|---|
| 0 | GS-PM-TRACKER-001 | 전체 계획과 실행 추적 체계 수립 | `COMPLETE` | 없음 | 이 문서, canonical link, integrity test |
| 1 | GS-P0-SCOPE-001 | 한 관할·ODD·세 deep slice·source hierarchy 확정 | `COMPLETE` | 연구계획 | 대한민국 현행 법령, structured-road ODD와 source policy |
| 2 | GS-P0-CATALOG-001 | 세 slice 12–20 source-bearing RuleTemplate/PredicateSpec와 six-family coverage 작성 | `COMPLETE` | GS-P0-SCOPE-001 | 15개, schema/source closure, 6/6 family, unsourced 0 |
| 3 | GS-P1-DRYRUN-001 | slice별 8개, 총 24장면 ContextGraph/label-light adapter dry run | `BLOCKED` | catalog 완료, 실제 adapter input | slot plan 완료; source-complete 0/24, 외부 scene/assurance 필요 |
| 4 | GS-P2-FRONTEND-001 | CoC+scene semantic parser, evidence retrieval, applicability와 parameter binding 구현 | `QUEUED` | P0 catalog, P1 failure taxonomy | structured constraint proposal bundle |
| 5 | GS-P2-BASELINES-001 | CoC-only, scene-only, free-form, template/flat, DriveReg/RTCD/SanDRA-like 기준선 동결 | `QUEUED` | 입력/출력 protocol 확정 | B0–B8/B13 locked baseline package |
| 6 | GS-P4-PILOT-001 | 60-scene 전문가 formal pilot와 최소검토 UI | `QUEUED` | P1 gate, front-end/baseline freeze | agreement, correction/time, unsupported, power-based main N |
| 7 | GS-E2-INTRINSIC-001 | CoC ablation, 생성 정확도, provenance, BCV/lifecycle/translation 비교 | `QUEUED` | formal pilot gold | E0–E3 report와 Go/No-Go 판단 |
| 8 | GS-P5-OUTCOME-001 | 독립 closed-loop/counterfactual 효과·진행성 평가 | `QUEUED` | evaluator independence gate | E4 violation/progress report |
| 9 | GS-P6-ALPAMAYO-001 | phase gate를 통과한 GuardSynth를 Alpamayo CoC에 적용 | `QUEUED` | E0–E4 gate | E5 package, external monitor/shield 결과 |
| 10 | GS-MAIN-PAPER-001 | power-based main study, 전문가 효용, 통계와 논문 artifact | `QUEUED` | pilot와 phase gates | GuardBench main, E6, submission package |

P0 catalog authoring과 P1 adapter의 read-only field audit은 병렬 준비할 수 있지만,
`GS-P1-DRYRUN-001`의 종료 판정은 source catalog와 assurance가 갖춰진 뒤에만 내린다.

## 5. 현재 차단 작업: GS-P1-DRYRUN-001

### 목적

M12 catalog를 실제 24장면에 연결해 binder와 abstention을 검사한다. 24-slot plan과 field
manifest는 준비됐지만 실제 source-complete 입력이 없어 계약 실행은 중단돼 있다.

### 완료된 준비

1. 세 slice별 8개 slot과 four-strata 계획
2. 대한민국 source-bearing catalog 15개
3. public aggregate 기반 후보/partial/data-gap 재감사
4. synthetic fill 금지와 실제 실행 0건 명시

### 재개 조건

- source-complete 실제 scene packet 24개 또는 미달 slot의 terminal selection decision
- 유일한 target-zone/lane association과 검증된 coordinate transform
- exact vehicle binding과 source-bearing assurance profile
- 24 ContextGraph에 대한 source closure 및 binder/unsupported metric 실행

입력 확보 전에는 M14 front-end를 활성화하거나 synthetic 장면으로 24-slot 성공을 만들지 않는다.

## 6. 완료 근거 등록부

| 완료 항목 | 대표 근거 | 주장 범위 |
|---|---|---|
| EBLC v0.2 RC | [release artifact](../../../artifacts/results/public/eblc-release-candidate-001/eblc-v0.2-rc1-2026-08-09/REPORT_KO.md) | bounded language/tooling, not safety |
| source-aware generator | [generator report](../../../artifacts/results/public/guardsynth-source-aware-generator-001/source-aware-generator-2026-08-09-v3/REPORT_KO.md) | synthetic structured generation |
| source boundary/readiness | [terminal report](../../../artifacts/results/public/guardsynth-real-scene-readiness-001/terminal-readiness-2026-08-09-v3/REPORT_KO.md) | readiness/abstention, 0/24 complete |
| label-light interface | [label-light report](../../../artifacts/results/public/guardsynth-label-light-grounding-001/label-light-2026-08-10-v3/REPORT_KO.md) | synthetic workflow, not association accuracy |
| 대한민국 scope/source catalog | [catalog report](../../../artifacts/results/public/guardsynth-source-catalog-001/kr-source-catalog-2026-08-10-v2/REPORT_KO.md) | source traceability, not legal advice/safety |
| 24-scene readiness | [readiness directory](../../../artifacts/results/public/guardsynth-24-scene-dry-run-001/kr-dry-run-readiness-2026-08-10-v1/) | slot/data-gap audit, real execution 0/24 |
| current backend regression | 같은 label-light run의 187/187와 Z3 agreement | scoped software regression |

## 7. 매 작업 세션의 운영 규칙

### 시작할 때

1. `RESEARCH_PLAN_V1.md`의 관련 RQ, 단계와 gate를 확인한다.
2. [마일스톤 원장](PROJECT_MILESTONES.md)의 Todo와 선행조건을 확인한다.
3. 이 문서에서 `READY_NEXT`인 작업 하나를 선택한다.
4. 선행조건이 충족됐는지 확인하고, 미충족이면 구현하지 않고 정확한 blocker를 기록한다.
5. 비자명한 작업은 먼저 `docs/requirements/` 또는 `docs/designs/`에 범위와 기대 테스트를 고정한다.

### 구현·실험할 때

1. TDD가 가능한 software는 RED 기대를 먼저 고정한다.
2. 실제/제한 입력을 synthetic 값으로 채우지 않는다.
3. public/restricted artifact를 분리하고 새 run ID를 사용한다.
4. 구현 결과에 맞춰 gate나 기대값을 사후 완화하지 않는다.

### 종료할 때

1. 실행 명령, test count, gate, 실패와 주장 범위를 artifact/report에 기록한다.
2. 마일스톤 원장의 Todo, 종료 gate와 대표 근거를 갱신한다.
3. 이 문서에서 해당 작업의 상태와 완료 근거 링크를 갱신한다.
4. 완료 조건이 모두 충족됐을 때만 `COMPLETE`로 바꾸고 다음 한 작업을 `READY_NEXT`로 지정한다.
5. 연구 범위나 사전 gate를 바꿨다면 연구계획을 새 버전으로 갱신하고 변경 이유를 남긴다.
6. 문서 링크 검사와 `MANIFEST.sha256`을 갱신한다.

허용 상태는 `QUEUED`, `READY_NEXT`, `ACTIVE`, `BLOCKED`, `PARTIAL`, `COMPLETE`,
`SUPERSEDED`뿐이다. 주관적인 완료율 숫자는 사용하지 않는다.

## 8. 현재 하지 않을 일

- 새 evidence 요구가 없는 EBLC 문법 기능의 반복 확장
- source-complete 24장면 전에 60장면 formal pilot 실행
- CoC를 규범적 authority 또는 관측 fact로 취급
- 실제 source 없이 법규/차량 수치를 생성
- generator와 같은 구현을 독립 safety oracle로 주장
- synthetic/Z3 결과를 실제 차량 안전성 효과로 서술
