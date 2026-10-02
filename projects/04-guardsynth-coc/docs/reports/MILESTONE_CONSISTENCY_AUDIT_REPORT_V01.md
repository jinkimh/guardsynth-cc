# GuardSynth-CoC 마일스톤 일관성 감사 및 선행 보완 순서

- project_id: `guardsynth-coc`
- 감사 ID: `GS-MILESTONE-CONSISTENCY-001`
- 기준일: 2026-09-06
- 범위: Project 04 M00–M21, 연구계획 E-1–E6/E4-L, 검토 요구사항과 관련 구현
- 상태: `AUDIT_COMPLETE_REMEDIATION_NOT_EXECUTED`
- 상위 권위: [연구계획 v2.2](../plans/01_RESEARCH_PLAN_V02.md)
- 실행 원장: [마일스톤](../plans/02_PROJECT_MILESTONES.md), [추적표](../plans/03_PROJECT_EXECUTION_TRACKER.md)
- 후속 범위 변경: v2.3 [1차 논문/2차 개발 분리](../decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md).
  이 감사의 사실은 보존하지만 모든 R 보완을 1차 필수로 묶은 순서는 대체됨.
  전체24·전수 baseline·runtime·Alpamayo·전문가 효용은 2차, 사용 source·독립 gold·CNL·학습은 1차

## 1. 결론과 감사 경계

기존 backend/synthetic 실행의 가치는 보존한다. 다만 terminal shortfall, software/protocol
완료, source 확인, 독립 gold 구축, 효과 검증을 하나의 완료 상태처럼 넘겨받는 지점이 있다.
또한 상위 계획의 일부 비교군·표본·신뢰도 조건이 실행 태스크에 없고 main 데이터 준비가
이를 사용하는 실험보다 뒤에 배치됐다. 이번 변경은 그 연결과 실행 계약을 보완한다.

실제 실험을 재실행하거나 전문가 판정을 새로 만들지 않았다. 1/60은 종전 eligibility
감사값으로 유지하며 이번 감사에서 개별 장면 적격성을 재인증한 수치가 아니다. 기존 run은
변경하지 않는다. 정량 gate를 낮추거나 미확인 조건을 통과로 바꾸지 않는다.
법령/협약의 법적 타당성 재조사도 이번 감사의 범위가 아니다. 현행 내부 결정과 실행 범위의
일치 여부만 다뤘으며 source별 실질 근거 검사는 R01의 실행 산출물로 남긴다.
M12–M15의 현재 원장 상태는 `PARTIAL`(requalification)로 바꿨다. 과거 scoped/terminal
`COMPLETE` 근거와 체크는 남기되 새로운 미완료 태스크가 있는 현재 상태를 완료로 표시하지 않는다.

## 2. 앞 단계부터의 발견 사항과 보완 계약

아래 R 번호는 이 보고서의 finding ID이며 새 최상위 마일스톤 번호가 아니다. 실행 단위는
기존 M 번호의 하위 단계에 붙인다. `QUEUED` 작업을 계획에 넣었다고 완료 처리하지 않는다.

| ID / 위치 | 확인한 불일치·근거 | 보완 작업 / 종료 산출물 | 차단하는 후속 작업 |
|---|---|---|---|
| R01 / M11–M12 | 원장 요약은 KR 고정인데 현행 결정은 다중 관할·협약 baseline. 협약 연결 98/98과 세부 실행 clause의 근거 충분성이 구분돼야 함 | `M12-R01 / GS-P0-SOURCE-REQUAL-001`: 현 scope별 rule→clause→precondition/exception→binder/source 추적표; direct/general fallback/system/physical 구분, 승인·범위·수치 근거 없는 hard clause 0 | M13 재검증·M14 operational mapping·M16 규범 gold |
| R02 / M01–M06·M08·M13 | bounded conformance는 독립 safety oracle이 아니며 M13은 4/24 terminal 종료. 나머지 slice/strata 실증 gate가 후속 담당 없이 남음 | `M13-R01 / GS-P1-SIM24-REQUAL-001`: pinned platform/source version으로 세 slice 8개씩 실제/파생 24-scene 재검증, binder/abstention·target agreement 보고; 부족 시 정확한 slot 보존 | M16 formal annotation start·M17 confirmatory 평가; source 수집/검토 준비는 허용 |
| R03 / M07·M14 | M14 요구사항은 operational policy 1/3, exception/NLP/dense는 후속인데 이를 맡는 태스크가 없음 | `M14-R01 / GS-P2-FRONTEND-REQUAL-001`: 세 slice의 지원 rule/materialization·exception matrix, 실제 CoC parser/retriever와 numeric binder dev 평가; 미지원은 분모에서 숨기지 않음 | 모델 출력 평가·학습 신호 생산; 일반 parser/dense 구현을 무조건 강제하지 않고 선택 모델과 주장 범위를 동결 |
| R04 / M15 | B1/B2 provider 미설정 smoke를 실행 가능 baseline으로 읽을 수 있음. 계획의 B9–B12 및 full-input free-form 동등정보 대조가 원장 태스크에서 빠짐 | `M15-R01 / GS-P2-BASELINE-REQUAL-001`: B0–B13 registry, 실제 provider smoke, B9/B10/B12 실행, B11 independent gold 입력 계약; 별도 full-input free-form arm `E2-FF-MATCHED` | formal method-output 비교·M17; gold의 blank authoring은 provider 없이 준비 가능 |
| R05 / M09·M16-S07/S09/S10 | source-review는 기계 polygon·선행 관찰 초안을 보지만 formal gold는 독립이어야 함. `build_blinded_assignment_manifest`는 두 reviewer에 서로 다른 UI mode를 주므로 방법 ID 비공개만으로 동일조건 신뢰도 검사가 되지 않음 | `M16-R01 / GS-P4-REVIEW-INDEPENDENCE-001`: source curation / blind gold / assistance 효용 cohort·노출 이력 분리, 독립 reviewer·adjudicator, metric geometry·lifecycle witness 계약과 import/zoom/autosave/export round-trip tests | 새 formal gold 수집·E1 agreement·E6 효용 claim |
| R06 / M16-S08–S11 | 상위 E1은 applicability와 guard type ≥0.67인데 요구사항/코드는 applicability α만 gate. 균형 60개로 모집단 prevalence를 추정할 수 없고 annotation 분산이 outcome/learning power를 대신하지 못함 | `M16-R02 / GS-P4-PILOT-METRICS-001`: 두 field의 pre-adjudication α, 결측/상수 label/표본 CI 정책; calibration·pilot·main 분리, endpoint별 power 입력·추정 불확실성·sampling denominator | M16 완료·main N 확정 |
| R07 / M17·M20 | main N/split·annotation이 M20에 있어 M17–M19 locked 평가의 gold보다 늦음. pilot을 확증 test로 재사용할 위험 | `M17-S01 / GS-P4-MAIN-DATA-001`: M16 이후 main cohort/split/annotation·adjudication을 먼저 구축; pilot/dry-run/dev/test 및 파생 event 누출 검사, main gold lock | M17-S02 confirmatory E0–E3; M18/M19 locked 평가 |
| R08 / M17–M18 | E0 target/독립 oracle·BCV 단방향 대조·E4 ≥2,000 rollout/≥3 seed가 상위에만 있거나 축약됨. E4-L을 앞서 보완했지만 endpoint별 power는 별도 필요 | `M17-S02 / GS-E2-INTRINSIC-001`, `M18-S01–S06`: 응용 conformance와 Project 05 결과 분리, 독립 evaluator·SMT-only/replay-only/outcome-only 대조, always-stop·matched nominal controls, outcome/learning용 dev power와 budget 동결 | 각 효과 주장; replay를 closed-loop로 집계 금지 |
| R09 / M19 | E5 ≥100 events×3 action seeds, expert control, 반대 의미/무관 prompt 대조가 원장에 없음 | `M19-R01 / GS-P6-ALPAMAYO-PROTOCOL-001`: 조건별 동일 ≥100 events×3 paired seeds, native/free-form/proposed/expert 및 verifier/shield 분리, 길이 맞춘 negative controls·source/model/prompt lock | E5 full-effect claim; 소규모는 feasibility로만 보고 |
| R10 / M20·M21 | E6 세 arm·오류 비증가·배정 통제가 원장의 시간/승인율만으로 축약됨. 조건부 M19 NO-GO가 논문 자체를 무한 대기시키는 해석 가능 | `M20-R01 / GS-E6-EXPERT-UTILITY-001`: scratch/free-form/proposed 3조건, 무작위 균형 배정·노출 분리·오류/시간/QA 비용·CI; M20에 claim→evidence 전수 검사와 조건부 gate disposition | 효용 및 논문 종료; 실제 차량은 기존 M21 권한·안전 gate 유지 |

## 3. 검토와 데이터의 상세 보완 기준

### 3.1 source curation은 formal gold와 별개

- 현재 60장면 웹문서는 source 확보를 돕는 draft다. 영상 관찰 60/60, geometry 품질 검토
  98/98, polygon 보정, expert source 확인, 8/8 source eligibility, formal guard gold 수를
  별도 집계한다. 이미 제출된 관찰/보정은 재사용하며 무조건 재검토시키지 않는다.
- polygon이 있으면 해당 보정 제출은 완료로 기록할 수 있지만, 좌표의 의미·frame/timestamp·
  depth/ground-plane/uncertainty·transform·source linkage가 검증되기 전 metric rig geometry
  완료로 바꾸지 않는다. 2D 점/박스는 전체 충돌 영역·차선 점유·시간 연속 track이 아니다.
- 현재 `machine_visual_proposal`의 ego corridor는 모든 장면에 같은 정규화 사다리꼴을 쓰고,
  pedestrian zone은 사건 근처 target point의 주변 사각형이다. 모델의 lane/drivable overlay와
  이 휴리스틱은 다른 산출물이며 장면별 의미 영역으로 평가되지 않았다. R05에서 종류별
  독립 품질 표본·실패 유형·수정량/coverage를 측정하고 일반적인 자동 geometry 정확도 주장을 금지한다.
- source package reviewer는 자신의 전문 역할에서 확인 가능한 항목만 답한다. 법규/수치/
  calibration은 해당 source와 전문 근거가 있는 담당 단계에서 처리한다. 모름/미관측/
  불일치는 정상 결과이며, 사람의 동의만으로 누락된 실제 자료를 생성하지 않는다.
- formal gold는 동일 중립 source packet에서 두 사람이 제안 guard·이전 답·방법 결과를
  보지 않고 작성한다. neutral source에도 기계 제안을 그대로 정답 표식으로 남기지 않는다.
  source curation 참여·draft 노출 이력을 기록하고, 노출된 동일 항목은 독립 gold가 아닌
  assisted/development로 구분하거나 미노출 reviewer로 재배정한다.
- adjudicator는 독립 답변을 lock한 후 불일치를 판정한다. E1 α는 adjudication 전 계산한다.
  `MINIMAL_CONFIRMATION` 대 `COMPLETE_AUTHORING`의 비교는 E6/efficiency cohort로 분리한다.
- calibration용 항목은 pilot 본 60개를 잠식하지 않으며 main locked test와도 분리한다.
  최대 2회 guideline revision 이력과 그 영향·재라벨링 범위를 보존한다.

### 3.2 source eligibility와 시스템 성능 분리

8/8은 필요한 관측/근거 packet의 완결성이지 hazard가 항상 관측된다는 뜻이 아니다.
UNKNOWN은 근거 있는 관측 불가능성, CONFLICT는 출처가 있는 불일치, RELEASE/REACTIVATION은
시간 witness가 필요하다는 기존 요구사항을 유지한다. geometry가 없어 못 푸는 장면을
UNKNOWN quota 채우기용으로 쓰지 않는다. 장면 국가/authority의 추론·조건부 상태도 보존한다.

생성기/translation 실패는 source-eligible 장면을 평가 분모에서 삭제하는 이유가 아니다.
`source_eligible`과 `execution_ready`를 분리하고 실패를 성능·coverage에 포함한다. unsafe
실행/자동 승격은 막되 평가 표본을 유리하게 선택하지 않는다. implementation/schema 변경과
회귀 테스트는 R05 실행에서 수행하며 이번 문서 수정만으로 validator가 바뀌었다고 하지 않는다.

### 3.3 표본·power·동일정보 비교

- 60 pilot의 18개 joint quota(3–4개/셀), slice 20개/outcome 10개는 유지한다. 자연분포가
  아니므로 prevalence는 별도 candidate sampling frame에서 추정하거나 estimand를 균형
  benchmark로 제한한다. eventful 자료에서 없는 nominal을 임의 생성하지 않는다.
- E1은 annotation reliability, E2는 paired scene accuracy, E4는 clustered rollout,
  E4-L은 training seed까지, E6는 reviewer×scene 배정을 반영한 power가 필요하다.
  해당 endpoint의 pilot 값이 없으면 `POWER_INPUT_PENDING`으로 둔다. 별도 dev/feasibility
  자료를 확보해 lock 전에 추정하며 annotation 시간/α로 학습 효과 분산을 대체하지 않는다.
- B1(CoC-only) 대 B10은 정보와 방법이 함께 바뀐다. 근거 공급량 효과와 EBLC 표현 효과를
  분리하기 위해 `E2-FF-MATCHED`에 B10과 같은 source·scene·CoC·model/tuning budget을 준다.
  원 B1 ID와 channel firewall은 유지한다. method-off input ablation과 representation/
  BCV ablation을 별도 보고한다. 효과 없는 placeholder는 실행된 baseline이 아니다.
- M17-S01에서 공통 main split/group IDs를 먼저 lock한다. M18-S02는 그 split을 이어받아
  추가 학습 데이터와 예산을 고정한다. M19 및 E6의 disjoint/overlap 역할도 manifest에 둔다.
  어떠한 locked test 결과도 후속 tuning/label production에 되돌리지 않는다.
- M17-S01의 main N은 E1/E2 power로 정하고 후속 endpoint용 dev·미개봉 reserve의 역할을
  분리한다. M18 실행에서 나올 분산을 M17의 선행조건으로 요구하지 않는다. M17 test를 보고
  방법을 바꿨다면 그 test는 dev로 재분류하고 새 미개봉 test 없이 confirmatory 주장을 하지 않는다.

## 4. 실행 순서와 완료 판정

첫 다음 작업은 **M12-R01 source/operational-clause 재적격화**다. 이미 받은 검토를 반복 요청하거나
M18 학습부터 시작하지 않는다. 완료된 98/98 협약 binding을 취소하는 것이 아니라 그것이
어떤 clause를 정당화할 수 있는지와 어떤 근거가 더 필요한지를 검사한다.

R01 → R02/R03/R04(입력 확보 후) → R05/R06 → M16 formal pilot → R07 main data →
M17 confirmatory → M18 learning/runtime → M19 conditional application → M20 E6/paper 순서다.
R02용 자료 수집과 R05의 source curation 준비는 병행할 수 있다. 모델/평가기 작업의 dev
준비도 허용하되 필수 gate 전에 formal annotation·locked 효과 결과로 발표하지 않는다.

각 R 단계의 근거는 소유자 artifact namespace의 새 run에 `RUN_MANIFEST.json`, `RESULT.json`,
`REPORT_KO.md`와 해당 matrix/metrics를 남긴다. 기존 artifact를 수정하지 않는다.
소프트웨어 준비 완료, 실제 실행 완료, 가설 지지 여부는 각각 별도 상태다. 조건부 실험의
NO-GO는 이유·미검증 주장과 scope disposition을 보고하되 수행한 것으로 표시하지 않는다.
E4-L은 앞서 승인된 필수 실행·보고 조건을 그대로 유지하고 자동 면제하지 않는다.

## 5. 근거와 미실행 항목

- [원장 M13–M20](../plans/02_PROJECT_MILESTONES.md): 4/24 terminal, 1/3 mapping,
  provider adapter, source/annotation gate, main 배치의 대조 근거.
- [formal pilot 요구사항](../requirements/M16_EXPERT_PILOT_REQUIREMENTS.md),
  [source acquisition 요구사항](../requirements/M16_SOURCE_COMPLETE_SCENE_ACQUISITION_REQUIREMENTS_V01.md):
  source와 annotation 경계, UNKNOWN/CONFLICT 정의 및 translation 실패 처리.
- [expert protocol 구현](../../src/guard_synth/expert_pilot_protocol.py): 혼합 UI mode 배정과
  applicability-only α; [source-review builder](../../pipelines/cli/m16_source_review_portal/build_expert_source_review.py):
  기계 polygon/target anchor는 candidate이고 source-complete 변경 없음.
- [협약 결정](../decisions/M16_INTERNATIONAL_TREATY_BASELINE_DECISION_V01.md):
  직접 규칙/일반 주의의무와 국내법 비주장 경계.

이번 세션은 계획/요구사항 불일치를 수정했으며 R01–R10의 empirical 완료 근거를 만들지는
않았다. 특히 reviewer assignment/metric/schema/UI 및 eligibility 코드 변경은 후속 구현이다.
독립 gold 준비 전 현재 source 화면에서 받은 답변은 formal E1/E2 정답으로 자동 등록하지 않는다.

## 6. 계획 반영 검증

- 포털 build/live projection tests: 9/9 통과. M00–M21의 22개 ID, M12–M16 PARTIAL,
  현재 parent M16 및 next M12-R01, M17 main-data와 M20 E4-L task 노출을 확인했다.
- 구조 tests: 20/21 통과. 유일한 실패는 기존 업로드 `(1).csv`/`(1).json` 및 root
  `portal_exec.md`의 naming 위반 3건이다. 사용자 제출 파일을 임의로 rename/delete하지 않았다.
- 변경 문서의 local links·신규 anchors·공백 검사와 `git diff --check` 통과.
- 이전 단계 상태 문자열을 고정한 projection test는 source override로 상태/게이트 독립성을
  검사하도록 보완했다. 새 current-state 및 선행 보완 표시도 portal build test에 추가했다.
- 이 검증은 연구 실험·review 독립성 구현 또는 source 재적격화 실행 완료를 뜻하지 않는다.
