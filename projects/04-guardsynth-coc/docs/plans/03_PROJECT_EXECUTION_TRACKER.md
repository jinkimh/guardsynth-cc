# GuardSynth-CoC 프로젝트 실행 추적표

- 기준 연구계획: [01_RESEARCH_PLAN_V02.md](01_RESEARCH_PLAN_V02.md), v2.4
- 전체 마일스톤: [02_PROJECT_MILESTONES.md](02_PROJECT_MILESTONES.md)
- 마지막 갱신일: 2026-09-29
- 현재 연구 위치: `M18_CONTROLLED_EXPERIMENTS_CLOSED_M20_INTEGRATION_PENDING`
- 현재 활성 작업 ID: `GS-P4-PILOT-001` (자료·검토 준비의 관리 parent)
- 현재 마일스톤 상태: `M18 통제 비교 COMPLETE`, `M20 DRAFT`; 기존 실제 도로 `M16 PARTIAL` 보존
- 우선 단일 작업: 완료된 확장·비용·추가 지표와 기존 D1–D4 결과를 M20 원고/보충자료에 통합. 전체 조건·시드·불확실성·실패 사례를 포함하며 새 학습이나 성공 기준 조정은 하지 않는다.
- 현재 하위 work package: [P0 source 요구사항의 1차 범위](../requirements/P0_SOURCE_CATALOG_REQUIREMENTS.md)
- 범위 결정: [1차 논문/2차 개발 분리](../decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)
- 종전 strict formal60: eligible 1/60 (이전 집계, 완료 아님)
- 1차 개발 후보 적격성: 조건부 진입1 + 한정 속도2(#7/#68); 나머지 확인28/현재 불가1. 과제별 수용 범위를 합치지 않으며 본 cohort/split은 `NOT_FROZEN`
- 기존 실제 도로 경로 판단(현재 통제 실험과 별도): CNL builder/synthetic VLM smoke, 기존 관찰 19건 재사용 및 32건 원본 시점별 source 연결 완료.
  #18 부분 관측 EBLC/CNL·개발 ACTION/CNL 검토를 조건부 수용; 독립 정상 진입 정답 0·신규 시험 후보 0. 본 학습·효과는 미완료
- 개발용 학습 데이터: #18 1장면 L0/L3 각1행, 실제 이미지 LoRA 각1step/총2updates·두 adapter 저장 완료. 본 실험 데이터0, 성능 검증 아님
- 1차 필수 학습: 실제 이미지/영상 기반 VLM fine-tuning(full 또는 내부 adapter);
  별도 scorer·text-only 학습·prompt/SAT로 대체 불가

## 현 실행 결과: M18 통제 비교 완료 → M20 원고

2026-09-29 실험 마감: [전체 표·무결성 감사](../../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-experiment-closure-2026-09-29-001/REPORT_KO.md).
확장18/18 fits·3,240 updates·17,280예측, 비용6/6 추가 fits·360 updates·6,480예측 완료.
비용 예측에는 추가 학습 전3개 adapter 평가도 포함한다. 추가 지표도 완료했으며 독립 새 표본은 아니다.
296개 고유 파일 해시, 모든 seed별 집계, 동일 예산·학습 순서 및 adapter 변화 확인; 회귀 테스트49개 통과.
원판정 NOT_SUPPORTED/INCONCLUSIVE는 보존한다. 비용 위반 감소와 일부 정확도 저하를 함께 보고한다.
실험 대기는 끝났고 원고 통합이 남았다. 실제 도로 formal60 미완료는 이번 통제 실험 마감과 별개다.

현재 보고 방침(2026-09-29 결과 열람 후 사용자 요청): 모든 시드20%p 이상을 결과 공개 gate로 삼지 않는다.
[결정](../decisions/PAPER1_METHOD_PRESERVATION_AND_LABELING_DECISION_V01.md)에 따라 전체 조건·시드·평가 묶음의
실측 성능/차이/불확실성을 원고와 보충 결과표에 포함한다. 개선이 작거나 없는 결과도 보존한다.
확장 run의 원판정 `NOT_SUPPORTED`와 사전 기준은 그대로 두며 사후 성공 판정으로 재작성하지 않는다.
후속 비용 비교의 고정 분석/데이터/예산도 변경하지 않는다. 원고 반영은 별도 작업이며 본 기록은 완료 주장이 아니다.

### 등록·실행 이력 (아래 대기/진행 수치는 위 마감 기록으로 대체됨)

2026-09-29 후속 승인: 현재18 fits를 유지하고 그 뒤 [제약 비용 학습 비교](../designs/PAPER1_EBLC_COST_LEARNING_DESIGN_V01.md).
동일 P2 adapter에서 continued SFT와 CE+EBLC 비용을 각60 updates×3seeds로 비교한다.
clear12.0–12.9초의 새 시험 입력을 별도로 동결하며 기존 시험을 학습에 편입하지 않는다.
비용·queue 테스트16개 통과, `temporal-cost-protocol-2026-09-29-001` 동결 완료.
tmux `guardsynth-temporal-cost-20260929`에서 부모18 fits 완료 후 자동 실행을 대기한다.
현 단계는 구현·검증·예약 완료이며 실제 추가 비용 학습 완료가 아니다. 부모 run 실패 시 자동 대체하지 않는다.

사용자 추가 승인: 학습 및 평가 수행, 이전 논문 수준 이상의 평가 구성.
`temporal-training-data-2026-09-29-001`의960/240/240행으로 새6조건×3seeds를 실행한다.
`temporal-expansion-protocol-2026-09-29-001`을 먼저 동결하고
`temporal-expansion-learning-2026-09-29-001`에18개 checkpoint와17,280개 평가 예측을 계획한다.
시험·표현 변화·미학습 대기시간, 기존7지표+coverage, seed별 수치와 그룹 불확실성을 모두 보고한다.
구현/계획은 실행 완료가 아니며 현재 실제 상태는 해당 run의 RESULT.json/progress.json으로 확인한다.

2026-09-29 추가 다양성 요청: [후속 실험 설계](../designs/PAPER1_TEMPORAL_DIVERSITY_DESIGN_V01.md).
기존 통제 비교 완료는 유지한다. D1 시간·경계, D2 문장, D3 영상 개입, D4 검증 적용/생략 진단을
새 run으로 수행했다. `diversity-inference-2026-09-29-001`의2,160행/1,476실제 호출과
`diversity-analysis-2026-09-29-001`의 paired CI·실패 분석을 완료했다. P2 clear/joint 안전완료
.8194/.7222, 교체 영상 기준 정확도 .0972로 일반화/grounding 한계를 확인했다.
D4 지원 오류144탐지·정상24수용·잘못된 source 부정 대조24미탐.2,376 Core 행동 바인딩과
독립 환경 판정 불일치0. 신규6쪽 PDF `temporal-paper-2026-09-29-002`를 작성했다.
확장 학습 queue는 GPU4 반환 후 유휴 검사를 통과해 자동 시작했다. 현재18-fit 완료는 미확정이며
live progress와 tmux `guardsynth-temporal-expansion-20260929`를 읽기 전용으로 감시한다.
감시 확인: 첫 P0/seed42 fit의180updates 및4개 split960예측 완료, 총1/18fit.
전체 결과/성공 판정은 아직 미완료다. 추가 학습을 중복 실행하거나 시험 출력으로 조건을 조정하지 않았다.

`temporal-protocol-2026-09-29-001`:2,016 paired records·100 SMT 질의·사전 고정 수준/열화 기준.
`temporal-learning-2026-09-29-001`:3seeds×3arms×72updates=648updates,9 distinct adapters,
2,592 valid predictions 완료. 기존 Project01 데이터/코드의 읽기 전용 재사용이며 P0/P1은 재현 대조,
P2는 별도의 검증 CNL이다. 과거 결과를 신규 P2로 재표기하지 않았다.

`temporal-analysis-2026-09-29-001`: 각seed에서 P1/P2 위반<=.05·안전완료>=.95,
P2-P0 개선>=.20, P2-P1 열화<=.05의 point criteria 모두 충족.
표준 benchmark P0 위반/안전완료 .3194/.6806 vs P1/P2 .0000/1.0000.
새seed P0 .3160/.6840 vs P1/P2 .0000/1.0000; P2-P0 위반 차이-.3160,
template-cluster95%CI[-.4348,-.1832]. formal 비열등성 또는 최소20%p 개선의 모집단 하한은 미입증.
Unseen-time 안전완료 .6250/.6389/1.0000, 정확도 .5000/.6250/.8993.
전체 deadlock0·coverage1. 6개 storyboard/24개 P0 image-candidate 입력을 반복하는 한계와
추론 때 제약 제공, 검증-only/학습-only 인과효과 미분리 사실을 함께 기록했다.

43 tests·100 SMT 통과. `paper/main.tex` 실제 결과4쪽 및 `temporal-paper-2026-09-29-001/main.pdf`
컴파일 완료. 원고/결과/hash 원장 동기화. 다음 단일 작업은 새 scope 아래 인용과 방법 논증을
정리하는 M20 원고 개선이다. 추가 사람 응답/권한 승인으로 막힌 기계 작업은 없다.
재검증 명령(새 분석 ID 사용, 기존 run 덮어쓰기 금지):

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/analyze_temporal_preservation.py --run-id temporal-learning-2026-09-29-001 --protocol-id temporal-protocol-2026-09-29-001 --analysis-id temporal-analysis-2026-09-29-002
```

## 1. 역할과 상태 원칙

2026-09-29 [새 범위 결정](../decisions/PAPER1_METHOD_PRESERVATION_AND_LABELING_DECISION_V01.md)이
아래 v2.3 실제 속도/no-guard-at-test 네-arm 계획과 충돌할 때 우선한다. 기존 두 STOP 수용과
GPU 점유 이력은 보존하며, 이 둘만의 학습을 새 효과 보존 주 실험으로 혼동하지 않는다.
Project01 코드/결과의 읽기 전용 재사용, 새 protocol·Core/SMT/CNL bridge 및 실제 비교를
위 근거로 완료했다. 데이터/seed/예산/열화 허용폭은 새 결과 전에 고정했다.
이번 통제 과제는 프로그램 참조를 사용하며 LLM 확장 라벨을 생성하지 않았다.
아래 기존 실제 도로 실행표/기록은 명시한 후속 범위로 남긴다.

연구계획이 scope를, 원장이 작업/증거 gate를, 이 문서가 현재 단일 작업을 관리한다.
v2.3은 v2.2의 모든 보완을 1차 필수로 묶었던 순서를 대체한다. 이전 완료 이력은 보존하고
PHASE2 이관을 완료로 계산하지 않는다. 문서 반영과 validator/UI/실험 구현 완료도 구분한다.

source curation, 독립 guard/CNL gold, 학습 효과는 별도 증거다. 기존 영상60/geometry98 답변은
재사용하지만 독립 test로 자동 승격하지 않는다. 새 scope의 eligible 수는 별도 감사에서만 계산한다.

## 2. 1차 논문의 최종 목적

CoC·scene·source → 필요한 제약 추출 → EBLC 명세/검증 → 의미 보존 CNL →
CoC 학습 supervision → VLM 가중치 학습 → held-out 이미지/영상 행동 평가.

강화된 학습은 제약 supervision을 뜻하며 RL 자체를 필수로 요구하지 않는다. offline 행동/궤적
선택 실험을 실제 closed-loop 주행/goal completion으로 주장하지 않는다.

## 3. 1차 핵심 실행 순서

| 순서 | 마일스톤 / 작업 | 상태 | 종료 근거 |
|---|---|---|---|
| 1 | M12-R01 / GS-P0-SOURCE-REQUAL-001 | `PARTIAL` | 개발 선택·CoC 98/98·관찰 19건 source 감사·M12-R01-A 개발 정책 완료; main source/gold/cohort 미동결 |
| 2 | M14-R01 / GS-P2-FRONTEND-REQUAL-001 | `PARTIAL` | A/B 조건부 실행, C1–C3 부분 근거 binding·10/10 SMT·독립 검토 준비 완료; 전체 source·독립 의미보존 미완료 |
| 3 | M15-R01 / GS-P2-BASELINE-REQUAL-001 | `PARTIAL` | 네 arm synthetic smoke 실행; 실제 provider와 공정 예산 미완료 |
| 4 | M16-R01/R02 / GS-P4-PILOT-001 | `PARTIAL` | 단일 검토자 ACTION19/19 및 검토자 수 요건 충족; source/CNL·split/power 남음. ACTION 검토자 간 신뢰도 미측정 |
| 5 | M17-S01 / GS-P4-MAIN-DATA-001 | `PARTIAL` | 실제 응답 기반19행 개발 평가 bank/채점 경로 완료; main split/gold·test 전 N 미동결 |
| 6 | M17-S02 / GS-E2-INTRINSIC-001 | `PARTIAL` | 조건부 subset 16건 실행; 실제 품질·독립 CNL·대조군 평가 미완료 |
| 7 | M18 / GS-P5-LEARNING-001 | `PARTIAL` (개발 launch·pretrained 평가) | scene18 각1step 및 base Qwen19예측 완료. speed 개발 적격2/export4행; 새 학습은 GPU점유로 미실행 |
| 8 | M20 / GS-MAIN-PAPER-001 | `QUEUED` | C1–C4 증거와 E4-L 실제 결과·원고·재현 패키지 |

M13 전체24·M19·E6는 이 경로의 선행조건이 아니다. main N은 관련 endpoint의 dev 분산으로
정하고 부족하면 미확정으로 보고한다. 고정 60/18-cell을 해제했다고 소수 표본이 충분해진 것은 아니다.
동일 초기값·데이터·행동 label·예산을 유지하며 L2의 정의 변경은 v2.3 manifest에 기록한다.

원본 CoC/UNKNOWN 처리와 조건부 수용 기준은 승인·적용했다. 다음 단일 작업은 남은 source/target·통제 적용성 확인과 독립 정상 진입 정답 확보다. ACTION 1건·한글 CNL 1건·영문 의미 의견 1건을 기록했고, #18 주도로 조건은 UNKNOWN이다.
개발용 qualitative clause/policy와 실행 경로는 2026-09-08에 완료했다.
기존 numeric stopping program의 meter/deceleration 요구를 설문 답변으로 채우지 않는다.
source binding 결과의 #54/#56 동시 통제, UNKNOWN, 제약 해제와 전체 진행 허가의 차이를
사용 subset에 반영해야 한다. 표현/renderer 지원 변경은 reusable platform 소유로 구현하며,
기존 source 감사만으로 실제 장면 clause/source 동결을 완료 처리하지 않는다.

## 4. 2차 심화 개발

| 범위 | 상태 | 재개 조건 |
|---|---|---|
| M13 전체24, M16 strict formal60/18-cell·전체8-field | `QUEUED` (DEFERRED_PHASE2) | M20 이후 적용 task/source·자원 재승인 |
| 세 slice/six families·모든 catalog·B0–B13·광범위 OOD | `QUEUED` (DEFERRED_PHASE2) | 확대하려는 주장별 데이터/대조군 확보 |
| M18-S06 / GS-P5-OUTCOME-001, ≥2,000 closed-loop·with-shield | `QUEUED` (DEFERRED_PHASE2) | 독립 simulator/runtime protocol과 resource |
| M19 / GS-P6-ALPAMAYO-001 | `QUEUED` (DEFERRED_PHASE2) | M20, runtime readiness·모델/라이선스/자원 |
| M20-R01 / GS-E6-EXPERT-UTILITY-001 | `QUEUED` (DEFERRED_PHASE2) | 별도 생산성 연구 필요성·expert 예산 |
| M21 / GS-POST-ACTUAL-VEHICLE-001 | `QUEUED` (DEFERRED_PHASE2) | M19, 차량 assurance·시험 권한·안전 승인 |

일반 EBLC 언어 연구는 [Project 05](../../../05-eblc-language-verification/docs/plans/02_PROJECT_MILESTONES.md)가
소유한다. 1차/2차는 Project 04 내부 단계이며 기존 paper1/paper3를 바꾸지 않는다.

## 5. 다음 단일 작업

**후속 승인 적용 완료:** 사용자 원답 “네”를
[두 STOP 한정 개발 수용 결정](../decisions/PAPER1_STOP_COMMON_CONSEQUENCE_ADMISSION_DECISION_V01.md)과
`stop-common-consequence-acceptance-2026-09-29-001`에 기록했다. 한 답변이 두 문서의 제시된
의미/개발 사용을 포괄한다. 새 Jonh 검토·신원 인증·전문 열람 또는 미기록 시간을 만들지 않았다.
`m18-cohort-feasibility-2026-09-29-006`: 기계2/CNL 수용2/정책2/학습 적격2, main test0.
이 질문은 해결됐으며 다시 묻지 않는다. 나머지17장면·원 v0.1·motion UNKNOWN은 유지한다.

`speed-development-packaging-2026-09-29-003`: 전체38 staging행과 별도로 L0/L3 각2행의
admitted train JSONL을 생성했다. #7/#68은 원 split에서 모두 train; 평가5행 이동 없음.
기존72 updates/arm/seed·3 paired seeds를 사용하는 `train_speed_development.py`를 연결했다.
원 CoC·4행동 감독(+L3 CNL) 학습과 기존 single-action blind 진단 출력의 차이를 manifest에
명시한다. 두 장면 탐색 개발이며 본 four-arm 효과·표본수 조건을 대체하지 않는다.

실행 시도는 GPU4 점유1,093MiB/1%로 모델 할당 전에 거부됐다. 신규 update/checkpoint0.
검증:34 tests·38 processor/mask rows·6개 run의 output hash43개 통과. diff 통과, naming은 기존5건만.
나머지 GPU도 타 작업 할당이 있어 사용하지 않았다. 승인 대신 자원 가용성이 현재 실행 제약이다.
다음 명령은 해당 run ID를 아직 생성하지 않았으므로 그대로 재시도할 수 있다:

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/train_speed_development.py --run-id speed-development-learning-2026-09-29-001 --gpu 4
```

**직전 실행 이력 (아래 pending/0건 표현은 승인 전 상태):**

**현재 완료:** `m18-cohort-feasibility-2026-09-29-005`에서 행별 증거 검사로 기계 준비2,
실제 사람 CNL receipt0, 속도 개발 policy0, 학습 적격0을 각각 계산했다. 양성 fixture는 통과,
출처/문구/version/범위 drift는 실패한다. 인덱스별 hard-coded 거절을 제거했다.
`speed-development-packaging-2026-09-29-002`는 새 projection CNL hash를005 수용 감사와 대조한
실제 이미지 L0/L3 각19 staging행/총38행이다.001의 기존 조건부 CNL staging도 보존했다.
processor 검사 완료, 원 CoC·3개 mask/arm 유지. staging은 승인된 학습 데이터가 아니다.

`stop-common-consequence-2026-09-29-001`은 별도 제안 버전에서 두 물리 상태의 공통 배제를
54 SMT 질의로 확인했다. UNKNOWN을 이동/정지 사실로 바꾸지 않았고 v0.1은 그대로다.
#7/#68 CNL 의미 보존 및 **새 출발·가속 공통 배제만** 두 장면 개발 감독에 사용할지 질문했다.
이미 승인된 STOP 관찰을 재질문하지 않는다. 두 장면은 기존 split에서 모두 train이다.
나머지17장면 적용성 연결 미충족; 계약도 없는6건은 #48/#50/#85/#86/#88/#94.
정상 진행 source·실제 violation 참조, 독립 clip/power의 부족은 구현 미완료와 구분한다.

`pretrained-speed-development-2026-09-29-002`: 정답/CoC/CNL 없는133프레임·고정 프롬프트로
base Qwen 추론19/19 완료. 유휴 GPU가 없어 CPU4 threads 사용, 가중치 갱신0.
기존 split은14 train/5 evaluation행이며, 평가5행 ACTION 참조는 이미 있어 이 추론을 막지 않는다.
`pretrained-speed-evaluation-2026-09-29-001`: 최초 scorer hash·split 유지,19출력 모두 유효.
전체 참조 부적절10/16(95% clip CI .400–.857), 정상 진행2/8(.000–.667), 불필요 정지7/12(.286–.900).
기존 evaluation5행에서는 각각2/4,1/3,2/3이며 세 CI 모두[0,1]. 실제 안전 위반/goal completion은
NOT_EVALUATED. pretrained 개발 baseline이며 trained L0·새 main test·개선 효과가 아니다.

`speed-source-providers-2026-09-29-001`: source-only38출력 완료. L1 text11/기권8,
L2 parse-valid1/형식오류18(식별자17/종류1). 본 same-CoC/image arm과 동일하지 않다.
`matched-speed-providers-2026-09-29-001`: #7/#68 원 CoC·동일7프레임·source를 맞춘4출력 완료,
L1 text1/기권1, L2 JSON형식 실패2. 전체19분모 유지, 자동 의미 repair/원문 수정 없음.
이는 실제 provider 구현/출력 증거이며 qualified main arm 완료가 아니다. L2 구문 출력 계약의
개선·전체 matched coverage는 기계 과제이고, source 적용성/실제 CNL 수신/개발 수용은 별도다.

최종 검사: 신규·회귀31 tests,54 SMT,38 processor/mask checks 통과. 원 intake/STOP 수용/
기존 scene18 smoke를 포함한10개 run의 output hash79개 검증. diff 통과, naming은 기존5건만.
모든 inference/provider process 종료; 이번 update0, 기존 scene18 총2updates 보존.

재현 가능한 다음 명령(새 run ID, 학습 아님):

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/evaluate_pretrained_speed.py --baseline-run-id pretrained-speed-development-2026-09-29-002 --run-id pretrained-speed-evaluation-2026-09-29-002
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/prepare_m18_development.py --admission-evidence projects/04-guardsynth-coc/experiments/paper1_cnl_learning/real_speed_development_config.json --run-id m18-cohort-feasibility-2026-09-29-006
```

위 명령은 실행 완료001 채점의 재현 및005 감사의 재현이다. 현재 config의 receipt/policy는 비어
있으므로 새 승인을 만들지 않는다. 수용 근거가 실제 도착하면
`prepare_m18_development.py --admission-evidence <실제-receipt/policy-JSON> --run-id <새-ID>`로
정확한 scene/source/CNL hash·범위를 검사한다. 기존 run에 덮어쓰지 않는다.

**앞선 launch/코호트 판정 이력: 아래 provider 미완료 표현은 당시 상태다.**

`guardsynth-eblc-learning-001/real-development-smoke-2026-09-29-001`에서 기존 수용된
scene18/candidate26의 실제 이미지·원 CoC·검토 CNL·ACTION으로 L0/L3 각1step을 완료했다.
같은 초기adapter SHA, 각224 tensors 변경, trainable3,211,264, image tokens2040,
supervised tokens31/142. 유휴GPU4 재확인 후 실행·종료, `adapters/l0`, `adapters/l3` 저장.
이는 짧은 launch check이며 속도19건 학습이나 성능 결과가 아니다. 반복하지 않는다.

`m18-cohort-feasibility-2026-09-29-001`: 현 gate로 속도 train0/19·독립 main eval0.
기존 진입1장면은 다른 task이므로 합치지 않는다. #7/#68 조건부 speed 수용과 두 CNL의
의미 수용을 묶어 요청했다. 기존 entry-only 기준 자동확장/가상 응답 없음. 두 STOP 사례만으로
정상 진행을 평가할 수 없으며 다른17건의 source/계약 gap도 남는다. 이미 받은 ACTION을
재수집하지 않는다. 실제 성능 코호트 부재가 현재 핵심 blocker다.

19응답/17clip을 source 성공·답변과 무관한 hash로 개발 partition12/5에 고정했다.
적격0이므로 실행 가능한 성능 실험은 아니며 fresh main test로 재표기하지 않는다.
ACTION-only scorer는3마스크·판단불가를 유지하며 부적절 선택 참조율/정상 진행 참조율/
불필요 정지·coverage·장면별 출력·clip bootstrap을 보고한다. 부적절성을 실제 안전 위반
gold로 바꾸지 않는다. always-stop은 소프트웨어 진단. 실제 violation/physical completion은
NOT_EVALUATED. 새로운 reasoning1659clip은 무라벨 retrieval leads, test적격0이다.

로컬 SDK/노트북/adapter/parquet는 clip-relative microseconds를 뒷받침한다. 속도 단위·
오차·정지 기준은 미확보여서 motion UNKNOWN 유지; ACTION/임의 threshold로 만들지 않는다.
L1 실제 direct-NL provider와 L2 독립 미검증 source-candidate provider는 미완료다.
`experiments/paper1_cnl_learning/real_speed_development_config.json`은 Qwen 고정revision·
paired seeds42/17/123·공통LoRA/optimizer·개발용72step 제안 설정을 준비했다. dataset/provider는
null이며 execution BLOCKED다. 결과를 위한 조건부 gate 우회나 main 예산 확정으로 사용하지 않는다.
Project01 원 result/adapter15개를 확인했다: 실제 Qwen5조건×3seed/각72updates이며 별도
RUN_MANIFEST 부재도 기록했다. 이 supplied guard-at-inference 결과를 Project04 L3로
재표기하지 않는다. 현재 primary는 supervision-only CNL/no oracle guard at test 그대로다.

우선 matched L0/L3, 다음 L1/L2 귀속 비교. four-arm gate·원 성공 기준·표본/power를
완화하지 않는다. L0만 대비해 EBLC 우월성을 주장하지 않는다. 코호트가 확보되지 않으면
신규 real-data 효과는 INCONCLUSIVE/NOT_EVALUATED로 원고에 명시하고 선행 실제 학습과
이번 source/launch 증거를 구분한다. 플랫폼 확장·추가 smoke·반복 보고서·test tuning 중단.

실행 명령(기존 checkpoint 재학습 불필요):

```bash
cat artifacts/projects/guardsynth-coc/restricted/guardsynth-eblc-learning-001/real-development-smoke-2026-09-29-001/RESULT.json
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/score_speed_development.py --targets artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001/speed-action-intake-2026-09-29-001/development_action_targets.jsonl --predictions /tmp/speed_predictions.jsonl --output /tmp/speed_scores.json
```

두 번째 명령은 실제 prediction JSONL이 있을 때 실행한다. 현재 모델 성능 예측으로
채워진 파일은 없으며 진단 출력을 실제 예측으로 재사용하지 않는다. 아래는 직전 source 이력이다.

**M12-R01 / M16 → M17: 두 STOP source 수용·실행 완료, motion/CNL 의미 확인 단계. ACTION 검토자 수 요건은 완료했다.**

`stop-control-source-acceptance-2026-09-29-001`: 사용자 원문 두 문장을 USER_CONVERSATION으로
기록하고 #7/#68의 작업자 STOP 표지→ego 정지 지시만 개발 전제로 수용했다.
[수용 결정](../decisions/PAPER1_STOP_CONTROL_SOURCE_CONFIRMATION_DECISION_V01.md), 정확한 시각null·
새 인증 Jonh 진술 아님. applicability TRUE/evidence_valid true, motion UNKNOWN 유지.
실제 Core2/24질의 및 가정 motion Core4/48질의 통과, 장면 CNL2건/source 대응 생성.
새3+기존source8테스트 통과. 원 ACTION과 다른17행/held79·81/노출81clip은 보존했다.
현재 verdict는 모두 UNRESOLVED; #68 적색 신호·해제·실제 이동·학습 적격성은 확인하지 않았다.
남은 필드: motion 단위/clock/error/정지 해석, CASCADE 물리적 동일성, 독립 CNL fidelity,
다른 장면 source gap·불일치·split/power. 새 설문/UI·본 학습은 없다.

`speed-source-binding-2026-09-29-001`: ACTION 답/이유를 읽지 않고 19장면/17clips의 기존 source를
연결했다. 대상11건은 원답 좌표·설명과 원 표시 JPEG에 귀속, CASCADE 통제10장면은 부모/자식
interval로 검증, raw velocity19건은 사건 직전1,086–9,802us 표본으로 연결했다. 같은 clip의
다른 event를 혼동하지 않는다. 실제 motion 인증과 Agent 동일성은 별도 미확정이다.
Core13건의 reported source predicates를 실제 보고값으로 고정하고130질의 통과.
새8+기존속도3테스트, 기존 intake82/새 run89해시 검증 통과. 완료한 intake/CNL 재생은 반복하지 않았다.

이전 #7/#68 정지 통제 수용 질문은 위 사용자 확인으로 해결했다. 다시 묻지 않는다.
#68 STOP paddle은 원 CoC red-light 주장과 별개다.
다른 필드의 실패 이유·출처는 `source_speed_bindings.json`의 gaps에 남겼다. 감속과 정지 의도,
entry FALSE와 speed release를 혼동하지 않는다. 기존 답을 역으로 제약으로 만들지 않는다.

[단일 검토자 결정](../decisions/PAPER1_SINGLE_REVIEWER_ACTION_DECISION_V01.md)을 읽고 반영했다.
현재19건은 Paper-1 ACTION 검토자 수 요건을 충족하며 두 번째 검토자/합의는 요구하지 않는다.
`NOT_MEASURED_SINGLE_REVIEWER`, 합의 gold 주장 없음. 후속 policy receipt는
`speed-source-binding-policy-update-2026-09-29-001`; 이미 생성된 run/원답은 변경하지 않는다.
strict60·phase2·별도 source/guard 프로토콜만 역사적2인 gate를 유지한다. source/CNL·불일치·
split/power는 여전히 필요하다. #79/#81 보류·81clip 시험제외·main 학습 미실행 유지.

`speed-action-intake-2026-09-29-001`은 19장면/76판단/19근거를 수용하고 원본 두 파일을 보존했다.
개발 평가 입력/응답 JSONL 각19행,17 clip groups,133 causal JPEG 검증 완료. 넓은 행동 정의로
일반화할 수 없는3필드만 마스킹하고 나머지73필드는 확정72/판단불가1로 분리했다. 정답을
새로 만들거나 실제 이동 상태를 추론하지 않는다. 이 수는 학습 적격 장면 수가 아니다.
조건부 CNL13건 텍스트/대응 재생과 UNKNOWN 전제130 SMT 질의 통과. 같은 의미 템플릿은2종이나
이 재사용 검사가 사람의 의미 검토나 장면 적용성 확인을 대체하지 않는다. 새 설문은 없다.
원문 행동과 검토 판단 불일치 #52/#55/#60은 원문 그대로 분모에 유지하고 계약 없는6건도 보존했다.

실제 남은 핵심: source 참조는 위 run에서 연결했으나 물리적 target 동일성 및 motion/applicability
확정은 남았다. 독립 ACTION 정답을 제약 조건에 넣어 순환 검증하지 않는다. 본 split,
CNL 수용과 학습 export는 미완료다. 현 Paper-1 ACTION에는 두 번째 검토자가 필요하지 않다.

아래는 ACTION 수신 전 게시 이력이다. 응답0·수신 대기 표기는 당시 상태이며 현재 수용19건이다.

사용자가 정확한 19장면 배정 및 화면 점검 후 게시 질문에 “네..”라고 승인했다.
`speed-action-assigned-2026-09-29-001`은 원문 질문/답변과 실제 배정 19건/76판단을 기록한다.
실제 승인 시각은 미기록이다. 비노출 self-report와 두 개발 기준은 재사용하며 재질문하지 않았다.
실제 Chromium의 일회용 context에서 0/19, 이미지 확대/복귀·장면 이동·reload 시 응답 유지,
부분 저장/복원, 잘못된 파일 거부, 누락 안내 및 최종 JSON 저장을 점검했다.
port8766의 `guardsynth-portal-current`만 `portal-2026-09-29-001`로 교체했다.
검토자 URL: `http://127.0.0.1:8766/reviews/paper1_speed_action_jonh.html`.
담당자 목록: `http://127.0.0.1:8766/reviews.html`; 검토자에게는 전용 URL만 전달한다.
전용 화면에 원문/기존답변/도형/판정/CNL 또는 해당 자료 링크는 없으며 기존 중단 화면은 그대로다.
제출 폴더: `artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001/speed-action-submission-2026-09-29-001/`.
파일명 `jonh_speed_action_submission.json`. 다운로드는 서버 접수가 아니며 실제 파일 전달 뒤 별도 intake에서 검증한다.
테스트 응답은 /tmp에만 저장하고 운영 초안/접수 수에 포함하지 않는다. 응답/gold/학습 0.
모든 ACTION 뒤 CNL, #79/#81 보류, 2인 formal gate와 M16/M17 PARTIAL 유지. 외부 메시지 발송 없음.
실제 게시 receipt 및 브라우저 검사/스크린샷은 `speed-action-publication-2026-09-29-001`에 보존했다.
파일 화면/HTTP 두 workflow 모두 통과했다. 브라우저 테스트 다운로드는 원답이 아니며 제출 폴더는 README만 있다.
최종 검사: 배정 통합 1 + 이전 수용/준비 3 + 포털 회귀 5 = 9 tests 통과, 실제 Chromium workflow 2회 통과.
배정/게시 manifest hash 30개 일치, live HTTP 상태/목록 동기화 확인. 포털의 고정 기대 목록을 신규 ACTION 포함
9화면으로 갱신 후 회귀 통과했다. diff 검사 통과, 파일명은 기존 위반 5건만 남는다.

아래는 배정 승인 전 준비 이력이다. 당시 승인 요청은 위 명시적 승인으로 해소되었다.

2026-09-29 사용자 전달 “아니요” 및 Jonh 본인 답변 전달 여부의 “네”를
`speed-action-assignment-preparation-2026-09-29-001/reviewer_self_report.json`에 원문·질문 범위와 함께 기록했다.
대화로 전달된 reviewer self-report이며 실제 선언 시각 null, 인증된 신원/서명/웹폼/열람 로그가 아니다.
동일 질문은 다시 하지 않는다. 기존 두 개발 기준 승인도 유지한다.
기존 입력 19건/133 JPEG로 독립 ACTION 미리보기·부분 저장/JSON 복원 화면을 준비했다.
배정안 후보: #6/#7/#31/#48/#50/#52/#53/#55/#59/#60/#64/#68/#74/#84/#85/#86/#88/#93/#94.
#79/#81은 보류. 준비안은 한 검토자의 개발 점검이며 2인 formal gate를 대체하지 않는다.
모든 배정 ACTION 뒤 CNL, 기존 설문 반복 없음. 실제 배정 수 null, 배포/응답/gold/학습 0.
승인 전 포털 등록/검토자 전달은 하지 않는다. 기존 immutable run은 수정하지 않았다.
검증: 신규 수용/누출/배정/UI 스크립트 통합 3개 + 포털 회귀 5개 = 8 tests 통과.
UI 스크립트는 Node의 DOM/storage 대역으로 검사했으며 실제 브라우저 시각 검사는 미실행이다.
새 run 입력/코드/출력 해시 15개 일치, diff/신규 파일 공백 검사 통과.
파일명 검사는 기존 위반 5건만 남았다. 제안 19장면은 17 clip groups이며 본 split은 동결하지 않는다.

아래는 비노출 답변 접수 전 실행 이력이다. 본인 진술 요구는 위 수용으로 해소되었다.

사용자가 “네...두 사항을 승인합니다.”라고 후속 승인했다. [승인 기록](../decisions/PAPER1_SPEED_DEVELOPMENT_APPROVAL_DECISION_V01.md)은
감속/정지 개발 의미 및 blind 공통 입력 수용, #79/#81 문맥 확인 전 보류를 명시한다.
이미 승인된 두 항목은 다시 질문하지 않는다. source/gold·실제 배정·main freeze·학습은 승인 아님.
`speed-contract-execution-2026-09-28-001`: 기존 21원문/관찰 보존, 조건부 속도 계약/CNL 15건,
합성 Core/SMT 626·mutation 6·scene UNKNOWN 150질의 예상 일치. 실제 적용성은 모두 UNKNOWN이다.
19장면/133 causal JPEG의 미배정 공통 입력과 빈 노출 선언/응답 template을 준비했다.
CoC·기존 답변·도형·기계판정·CNL은 ACTION 입력에 없다. 포털 등록/실제 배정/배포 0,
독립 행동 gold 0/21, 독립 CNL 검토 0, 본 학습 0. ACTION→CNL 및 2인 formal gate 유지.
준비된 19건은 실제 배정 수가 아니다. Jonh 본인의 선언과 실제 검토 범위/배정 결정 없이 전달하지 않는다.
M16/M17 PARTIAL; 본 endpoint/cohort/gold/split 미동결, 위반·진행 NOT_EVALUATED.
최종 검증: 신규 platform 5·통합 3, 기존 entry 9·proposal 8·속도 준비 5·portal 5 = 35 tests 통과.
기존 Core의 horizon≥2/query 필수 조건에 맞춰 INITIAL-only와 base consistency를 적용했다.
포털 테스트의 이전 상태 기대값을 현재 선언 대기 상태로 동기화 후 재통과했다.
Z3 5.0.0, 새 manifest 해시 139개 일치, `git diff --check` 통과.
파일명 검사는 핸드오프의 기존 위반 5건만 남아 exit 1이며 신규 위반은 없다.

아래는 승인 전 제안 실행 이력이다. 당시 요청된 두 판단은 위 승인으로 해소되었다.

`speed-clause-binding-2026-09-28-001`은 21원답/원문과 기존 진입 계약 11건을 연결했다.
정확한 원문 구절·offset·hash를 보존하고 감속 9/정지 6을 승인 전 clause 후보로 분리했다.
나머지 6건은 clause를 제안하지 않으며 Resume/Adapt #48/#50/#85/#94는 단일 행동 미확정이다.
48개 합성 조건/192행동 interface 실행 및 신규 회귀 8개 통과. 기존 SMT를 재실행하거나
속도 검증으로 재표기하지 않았다. 실제 21건은 motion/applicability UNKNOWN, verdict UNRESOLVED.
[의미 제안과 두 질문](../designs/PAPER1_SPEED_CLAUSE_BINDING_DESIGN_V01.md): 감속/정지 구분 및
clause 단독 배제 표 수용 여부, 공통 과거 영상 입력 수용과 경로 민감 #79/#81 문맥 수용 전 보류 여부.
담당자 판단 없이 이를 규범 정책으로 승격하지 않는다. 이 판단 후에도 Jonh 본인의 노출 선언과
별도 배정 결정이 필요하며 2인 formal gate를 유지한다. 독립 속도 정답 0/21, 실제 배정 수 미확정,
배포·학습 0, 위반/진행 지표 NOT_EVALUATED, main endpoint/cohort/gold/split NOT_FROZEN.
전체 32후보와 노출 81 clips 제외를 유지한다. 기계 준비가 끝난 이 지점에서 사람 판단을 요청한다.
검증: 신규 8 + 기존 속도 준비 5 + frame 6 + 원문 4 + portal 5 = 28 tests 통과,
새 run manifest 입력/코드/출력 hash 25개 일치, `git diff --check` 통과.
`python3 cli/checks/file_naming.py`는 기존 위반 5건으로 exit 1이며 이번 작업의 신규 위반은 없다.

아래는 직전 준비 이력이다.

사용자가 21건의 의미와 재검토 범위 설명 후 준비 진행을 승인했다. 본 실험 범위/정답 동결
또는 21건 즉시 설문 배포의 승인은 아니다. `longitudinal-endpoint-preparation-2026-09-28-002`에서
21건 원답·메모·도형을 그대로 연결하고 147개 과거 JPEG/시점을 확인했다.
[속도 행동 평가 준비](../designs/PAPER1_LONGITUDINAL_ENDPOINT_DESIGN_V01.md)는 현재 속도 유지,
감속, 정지·대기, 출발·가속을 구분한다. 복수 적절 행동과 판단 불가를 허용하는 개발 초안이다.
독립 입력 초안은 공통 질문·프레임 참조만 포함하며 CoC·답변·노란 영역·기계 판정은 제외했다.
기존 UNKNOWN 포함 7건, legacy 해당 없음 21건, 진입 차단 FALSE 4건, 원문 근거 확인 3건,
경로 민감 2건은 중복 가능한 기계 주의 항목이며 사람 질문 건수가 아니다.
새 속도 정답 0/21: 21건이 모두 채택되면 독립 행동 판단은 최대 21장면에 필요할 수 있다.
이 공백은 기존 관찰 반복과 다르며 실제 배정 수는 미확정, 배포 0건이다. 기존 답변을 다시
요구하지 않는다. 다음은 clause와 속도 행동의 연결, 질문 해석 가능성 점검이다.
적절성 응답을 위반률/정상 진행 정답으로 자동 바꾸지 않는다. 기존 진입 EBLC의 SAT 결과도
속도 행동 검증이 아니다. M16/M17 PARTIAL, 본 학습 0 유지.

아래는 32건 예비 점검 이력이다.

`remaining-action-coverage-2026-09-28-001`에서 남은 22건을 점검했다. 20건은 4개 과거
표본씩, 후보 #26/#73은 원본 마지막 causal 프레임을 replay했다. 앞선 10건과 합해
32후보/29 clips, 122회/119개 고유 JPEG의 AI 예비 시각 점검이다. 연속 영상·독립 gold 아님.
출처·프레임·집계·정답 승격 금지 146검사를 통과했다. 원래 행동 축은 속도 조절 21,
조향 6, 차로 변경 1, 양보 4다. 양보를 정지로 강제 변환하지 않았다.
우선안은 속도 조절 21후보/19 clips이며 아직 scope 수용·학습 적격·main cohort 확정이 아니다.
나머지 11건도 분모에 남고 #37/#84, #53/#59, #86/#94는 같은 clip으로 묶인다.
#59의 신호 미관측 답변, #68의 신호등/STOP 패들 근거 차이, 기존 영상 #18/후보 #26 및
영상 #47/후보 #73 상태를 보존했다. 기존 30건 전수 재설문은 요청하지 않는다.
이후 위 승인·준비 단계에서 공통 판단 시점·선택지·복수 적절 행동/판단 불가·원문 강도
보존·CoC/독립 target 상충 처리 경계를 문서화했다. EBLC 행동 연결은 남았다. 기존 진입 명세의 검증을
새 속도 행동 검증으로 재표기하지 않는다. 새 설문 배포/독립 ACTION/CNL·본 학습은 아직 없다.

아래는 앞선 10건 점검 이력이다.

`m17-context-frame-audit-2026-09-28-001`: 문맥 후보 10건/9 clips, 70프레임 JPEG·시점 확인.
AI가 실제 시각 확인한 범위는 장면별 4개 표본, 총 40회/39개 고유 JPEG다. 연속 영상 검증이나
독립 인간 검토가 아니다. 환경 설명과 양립 8, 회전 문맥 미확정 #79, 행동 자체를 문맥으로 주면
답이 되는 #66을 구분했다. #88은 적색 신호/횡단보도 보행자와 가속 원문의 잠재 긴장이 있으나,
신호 적용·경로 미확정이므로 오류 또는 행동 정답을 단정하지 않는다. #86/#94는 같은 clip이다.
원래 평가 축은 종방향 5·측방 통로 조향 4·차로 변경 1이며 적격 수가 아니다.
[평가 질문 초안](../designs/PAPER1_ORIGINAL_ACTION_ENDPOINT_DESIGN_V01.md)을 작성했지만
배포하지 않았다. 남은 22건 점검은 위 결과로 완료했으며 기존 범위의 1~2개 행동군·공통 후보·
시점 조건 수용은 남아 있다. 학습/gold 수와 M16/M17 PARTIAL은 그대로다.

다음은 이 작업의 선행 원문 감사 이력이다.

`m17-original-coc-context-audit-2026-09-28-002`에서 32건 원문과 source hash를 확인했다.
명시 문맥 구절 후보 10, 조향 행동만 있는 2, 경로 구절 미검출 20이다. 원문 행동은 감속 9,
정지 6, 양보 4, 회복/가속 5, 조향 6, 차선 변경 1, 속도 조절 1이며 독립 정답이 아니다.
같은 CoC에 제약을 추가하는 원래 연구를 유지하고 임의 경로 배정 초안은 실행 전 철회·차단했다.
새 검토·학습은 시작하지 않았다. 문맥 후보 10건의 과거 프레임 대조는 위 예비 점검으로 진행했다.
새 경로를 만드는 작업은 아니며 [원본 문맥 보존 결정](../decisions/PAPER1_ORIGINAL_CONTEXT_PRESERVATION_DECISION_V01.md)을 따른다.

아래는 선행 감사 이력이다. 가정 경로 대안은 위 결정으로 대체되었다.

`m17-action-task-audit-2026-09-28-001`에서 32후보의 원본 주석과 30관찰을 감사했다.
16건은 TRUE 8/FALSE 8이며 모두 위험 장면이라는 단정은 철회한다. FALSE 8건 후보
#1/#48/#64/#66/#70/#79/#85/#88은 정상 진행 가능성 점검 대상일 뿐 정답이 아니다.
감사 범위에서 판단 전 예정 경로 근거 확립 0건. #27/#81의 회전 주석도 사후 행동 설명이다.
기존 두 URL은 신규 답변 대신 중단 안내와 초안 백업만 제공한다. Jonh 배정은 보류하며
새 검토 전 실제 노출을 재확인한다. 당시 가정 경로 대안은 철회했으며 원본 문맥 보존으로 보완한다.
기존 관찰을 다시 하지 않으며 M16/M17 PARTIAL, 본 학습 데이터 0을 유지한다.
근거: [과제 재설계 결정](../decisions/PAPER1_ACTION_TASK_REDESIGN_DECISION_V01.md).

아래는 중단 전 준비 이력이며 재배포 지시가 아니다.

`m17-machine-preflight-2026-09-28-002`: 30장면·210개 과거 프레임을 원본 영상에서 다시
생성해 픽셀/JPEG/시점을 검증했다. 16개 보행자-only 조건부 명세/CNL, 256/256 질의 예상 일치,
게이트 제거 반례 16건. 나머지는 점유 미확정 2·다른 통제 과제 9·대상/영역/적용성 미확정 3이며
모두 분모에 남는다. 논리 모델은 보고된 관계가 옳다는 가정이며 전체 장면 진입 허가가 아니다.
독립 ACTION 준비 16건(두 사람 응답 슬롯 32), CNL 준비 16건(64조항). 배포/실제 응답 0.
사용 가능한 검토자는 1명이며 `Jonh`로 배정 예약했다. 사용자가 기존 CoC/답변/CNL/모델 출력
미노출을 확인했지만, 본인 선언·신원·전문성 인증으로 대신하지 않는다. 담당자 과제·영역·입력
확인은 아직 필요하다. 1인 결과는 개발용 점검에 한정하며 정식 2인 검토 기준을 낮추지 않는다.
`m17-action-review-ui-2026-09-28-001`에서 담당자 미리보기와 별도로 실제 답변 입력 화면을
준비했다. 장면별 완료/자동 저장/일괄 JSON 저장·복원을 제공한다. 화면 준비를 담당자 승인이나
답변 접수로 계산하지 않으며, 기존 미리보기 주소에도 입력 화면 링크를 추가했다.
32개 후보/29개 개발 영상 원장과 기존 노출 81개 영상의 시험 제외 목록을 만들었다.
담당자가 과제·영역·입력 적합성을 확인하고, 원본 CoC/선행답/모델 출력에 미노출된 검토자
두 명을 배정해야 한다. ACTION 전에 CNL/출처 자료를 보여주지 않는다. 개발 예비 자료이며
본 시험 gold가 아니다. 신규 held-out/N·독립 정답·의미 검토·대조군 intrinsic 실측은 아직 없다.
M16 PARTIAL 유지, M17은 선행 gate를 우회하지 않은 PARTIAL 준비 상태다. 본 학습 데이터 0.

아래는 접수 및 이전 준비 이력이다.

2026-09-28 `source-observation-intake-2026-09-28-001`: Jin Hyun Kim의 최종 답변 30건과
초안 완료 30건 일치, 필드·도형 형식·시점·패킷 검증 통과. 원본 파일을 그대로 보존했다.
관찰 설문 수신은 완료이며 전체 source 확정과는 별개다. 기계 후속 큐는 grounding 16건,
적용성/범위 14건이다. 이 숫자는 학습 적격 수가 아니다. 기존 NOT_APPLICABLE 122필드는
미관찰/비적용 혼재 의미를 일괄 단정하지 않는다. #59의 신호 미관찰 사용자 설명은 별도 기록했다.
[관찰 수용 결정](../decisions/SOURCE_GAP_OBSERVATION_ACCEPTANCE_DECISION_V01.md)을 적용하며
새 전수 설문·독립 행동 정답·진입 허가·학습 승격은 생성하지 않았다. 제출 원본은 실제 업로드된
`guardsynth-paper1-source-acceptance-001/scene18-source-submission-2026-09-08-001`에서 읽었으며
폴더를 이동하거나 업로드를 변경하지 않았다. M16 PARTIAL, 본 학습 0, #18 개발 export 1 유지.

아래는 접수 전 준비 이력이다.

현재 `development-data-2026-09-08-001`에서 개발용 학습 데이터 1장면(#18)과
30장면 실제 근거 검토 화면을 생성했다. L0/L3 JSONL 각 1행·이미지·해시·processor 검증을
포함한다. 사용자 요청에 따른 별도 개발 export로, 종전 판정 파일과 본 학습 gate를 바꾸지 않는다.
정상 진입 정답 0, 본 학습 데이터 0, optimizer step 0. 단일 프레임 입력은 21프레임 검토와
동등하다고 인증하지 않았으며 본 실험용이 아니다.
새 화면은 기존 위험 미관찰 4건을 앞에 배치하고 30건 중 완료한 것만 저장할 수 있다.
#18은 기존 답변 재사용, #47은 반복 요청하지 않는다. 제출 후 source 답변을 수용한 다음
해당 영역·입력에 맞춘 독립 ACTION 검토를 별도로 생성한다. 이 화면 답변으로 행동 정답을 채우지 않는다.
제출 폴더는 `guardsynth-paper1-training-readiness-001/source-gap-submission-2026-09-08-001`이다.

아래는 그 전 단계의 이력이다. `conditional-candidates-2026-09-08-002`는 조건부 수용 결과다.
[수용 기준](../decisions/PAPER1_CONDITIONAL_DATA_ADMISSION_DECISION_V01.md)에 따라 #18을
조건부 개발 후보로 수용하고 road UNKNOWN·원본 CoC·전체 source 미확정은 보존했다.
기존 19건 source binding을 동일 재현하고 미관측 13건도 같은 interval 규칙으로 연결했다.
32건 전체 기계 연결 완료, 조건부 개발 수용 1/추가 확인 30/사용 불가 1이다.
미관측 13건의 사람 답변은 null이며, 다른 통제가 있는 장면에 #18 명세를 일괄 적용하지 않았다.
현재 독립 행동은 DEFER_ENTRY 한 건뿐이다. 정상 진입 정답과 신규 시험 후보는 0이므로
보류 편향을 평가할 수 없고 본 학습을 시작하지 않았다. `human_work_queue.json`은 30건의
누락 작업 목록이지 준비된 설문이 아니다. 포털은 읽기 전용 결과이며 같은 #18 검토를 요구하지 않는다.
남은 사람 확인과 함께 실제 L1/L2 provider, 본 frame sampling·gold/split·표본 수·동일 예산을
완성해야 한다. M16 PARTIAL, M17 미동결, 본 학습/export 0을 유지한다.

아래는 조건부 기준 적용 전 strict-source 감사와 준비 이력이다.

`candidate-readiness-2026-09-08-003`에서 32장면/29영상 전체를 감사했다. 사용 가능 0,
추가 확인 31, 현재 사용 불가 1(기존 영상 #47 관찰 불가)이며 분모에서 삭제하지 않았다.
원본 CoC·주석·영상·과거 프레임은 32/32 검증됐다. 기존 19개 관찰·32개 geometry 검토를
재사용하고, #18의 새 대상/영역·독립 ACTION·CNL을 추가 반영했다. road UNKNOWN은 유지한다.
12개 기존 nearest 표시 프레임이 t0 이후여서 마지막 과거 프레임을 따로 선택했다. 4개 영상은
manifest의 asset alias 경로로 확인했다. 표시본/원본 검토는 수정하지 않았다. 001/002는
프레임·경로 구현 점검 이력이고 003이 보존된 strict-source 결과다.
`candidate_readiness.json/.csv`, `missing_evidence.json`, `split_feasibility.json`을 생성했다.
모든 후보가 기존 개발군이므로 미검토 13건도 시험용으로 전환하지 않는다. 영상별 묶음만 정리하고
실제 train/dev/test 배정은 보류했다. 별도 미노출 시험군 및 영상 간 episode 연관성 감사가 필요하다.
부족 항목 수는 신규 설문 건수가 아니다. 연구 기준 결정 → 기계 근거 연결 → 누락만 사람 확인
순서로 진행한다. M16 PARTIAL, M17 본 데이터 미동결, 학습 export 0이다.

`scene18-training-preflight-2026-09-08-001`: 사용자 원문 “영어로다 같은 의미로 읽히는데..”와
후속 검토자 지정 Jun Choi를 연결했다. 이전 참여 여부 신고를 재사용한 대화 기반 의견이며,
새 검토 시각·문장별 설문·신원 인증을 만들지 않았다. 동일 개발 예제의 영문 전체 의미 확인이다.
실제 마지막 과거 프레임(t0-34us)·원본 CoC·독립 행동 답변으로 L0/L3 형식 미리보기 두 건을
기존 builder/processor에 연결했다. prompt 2148 tokens 동일, supervision 31/142 tokens,
이미지 tensor·assistant-only mask·무절단 검사 통과. 원본 CoC/정답/CNL은 prompt에 넣지 않았다.
학습 가중치 로딩/갱신 0; L1/L2 실제 provider·본 split·동일 예산은 미확정이다. 21프레임 검토를
1프레임 행동 평가로 바꾼 결과가 아니며, 본 frame sampling은 별도 동결해야 한다.
원본 CoC의 주도로 양보 지시와 독립 근거 UNKNOWN을 함께 보존했다. 이는 자동 학습 승인 대상이
아니며 과제별 target 처리 정책의 입력이다. M16 PARTIAL, source-verified/export 0 유지.

아래는 영문 의견 수신 전 준비 이력이다.

`scene18-cnl-intake-2026-09-08-001`에 Jun Choi의 한글 답변 4/4 SUPPORTED를 수용했다.
`scene18-review-linkage-2026-09-08-001`에서 ACTION/CNL의 시점·영역·과거 프레임 일치,
원본 근거/명세만으로 생성 문장 재현 및 12/12 검사를 확인했다. 제출 시각상 ACTION이 먼저지만
미노출·신원·전문성 인증은 아니다. 사람 검토를 솔버 답변으로 대체하거나 생성 입력에 섞지 않았다.
다음 영문 비교 자료는 해당 run의 `REPORT_KO.md`다. 한글/장면 검토를 반복하지 않고,
영문의 관측 귀속·UNKNOWN·현재 보류·두 해제조건·진입 비강제가 같은 뜻인지 판정한다.
영문 검토 0, 전체 source 수용 0, training export 0 및 M16 PARTIAL을 유지한다.

아래는 한글 검토 준비 시점의 이력이다.

현행 run: `scene18-conditioned-cnl-2026-09-08-002`. 기존 renderer가 관측값 없이 공통
규칙만 설명하던 공백을 보완했다. 보행자 TRUE/valid·주도로 UNKNOWN/invalid를 입력받아
근거에 귀속한 사실 2문장, 현재 진입 보류 지시, 이후 재판단 조건을 한·영으로 생성한다.
12/12 Core 질의가 일치하며 문장별 binding/Core/query 대응과 CoC 삽입 미리보기를 기록했다.
미리보기는 독립 검토·전체 source·gold/split·영문 검토가 없어 학습 export 금지다.
전용 화면은 실제 장면/검토 답변/생성 문장을 함께 보여준다. 독립 ACTION 답변은 생성 입력이
아니며 다시 제출하지 않는다. 새 응답 파일은 `scene18_scene_cnl_review.json`이다.
[설계](../designs/PAPER1_SCENE_CONDITIONED_CNL_DESIGN_V01.md). 다음은 아래 구 화면의 이력이다.

이전 화면은 `scene18-cnl-korean-review-2026-09-08-002`의 A/B 비교판이었다. 실제 Core 조항의
해설과 실제 생성 문장 발췌의 한글 번역을 나란히 제공한다. 보행자·주도로·결합 규칙만
질문하며 소개/출처 목록은 참고 정보로 분리했다. 원본 조항/영문 발췌를 카드마다 연결했고
긴 해시는 화면의 출처 이름으로 치환했다. 제외한 두 메타정보 조항은 승인으로 집계하지 않는다.
원본 명세·근거 식별자·기존 ACTION은 보존했다. 새 화면 답변은 새 패킷으로 수용하고
한글 보조 검토로 구분한다. 영문 renderer 의미보존이 자동 입증된 것으로 집계하지 않는다.

`scene18-action-intake-2026-09-08-001`에 Jun Choi의 실제 응답을 보존했다.
판단은 DEFER_ENTRY, 근거는 “보행자가 차량 진행 경로에 있는 것처럼 보임”이다.
패킷/원본 해시와 필수 항목 검증 통과, INDEPENDENT 선언 및 알려진 노출 충돌 없음으로
개발 독립 검토 수용 기준에 부합한다. 신원/전문성이나 모든 노출 이력을 기계가 인증한 것은 아니다.
당시 ACTION 1건, CNL 0건. 정책의 보류 허용과 부합하지만 도로 조건 UNKNOWN을 해소하거나
main gold·검토자 간 신뢰도·학습 효과를 증명하지 않는다. 아래는 준비 시점 이력이다.

실행 `guardsynth-paper1-reviewed-contract-001/reviewed-scene18-execution-2026-09-08-001`:
부분 관측을 INITIAL 전제로 연결해 10/10 예상 결과 일치(전제 SAT, 진입 UNSAT, 보류 SAT).
미관측 과거·미래는 자유 입력으로 남겼다. 공통 CNL과 별도 ACTION/CNL 화면을 준비했으며
준비 당시 독립 실제 응답은 0건이었다. 전체 source 수용·학습 export는 여전히 0건이다.
Jin Hyun Kim의 기존 source 검토는 완료지만 이미 노출된 #18의 독립 ACTION gold는 아니다.
배정자는 미노출 검토자에게 ACTION 직접 링크만 먼저 전달하고, 제출 이후에 CNL을 제공한다.
단일 개발 검토이지 held-out 성능/검토자 간 신뢰도 평가는 아니다.
[검토 분리 설계](../designs/PAPER1_INDEPENDENT_DEVELOPMENT_REVIEW_DESIGN_V01.md).

아래는 완료된 source 검토·실행 준비 이력이다.

사용자 제출과 추가 설명을 `scene18-source-clarification-2026-09-08-001`에 기록했다.
대상/영역과 보행자 TRUE는 유지, 다른 차량 움직임을 확인하지 못했다는 설명에 따라
주도로 TRUE를 UNKNOWN으로 보정했다. 원본 파일은 변경하지 않았다. 검토 완료 1건,
보행자 evidence_valid=true / 주도로=false, 전체 source 수용·학습 export는 미완료다.
동일한 영역 재작성이나 억지 TRUE/FALSE 확인은 요청하지 않는다. 아래는 준비 단계 이력이다.

C1 기계 단계 완료: 32개 분모/19개 기존 관찰/13개 미관찰 유지, 원본 해시 재검증,
geometry 두 제출 JSON의 실제 좌표 0건 확인(기존 검토 완료 취소 아님), #18 과거 프레임 21개와
t0 무손실 PNG 준비. 첫 영상 -0.111570초와 CASCADE 점 0초의 불일치를 context-only로 표시했다.
source 수용기·한 장면 검토 UI·좌표 보존/JSON 복원·future-input 배제 tests 14개 통과.
003이 현행 run이며 001 보존, 002는 잘못된 zero-time assertion 실패를 보존한다.

[#18 source 검토 화면](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-source-acceptance-001/scene18-source-acceptance-2026-09-08-003/scene18_source_binding_review.html)은
완료된 확인 절차의 보존용이다. 같은 설문 반복은 필요 없다. 기계가 사람의 확인을 작성하거나
독립 action gold로 복사하지 않는다. 아래는 선행 구현의 이력이다.

2026-09-08 실행 완료: [행동 계약](../designs/PAPER1_ACTION_CONTRACT_DESIGN_V01.md)의
M12-R01-A 개발 정책, M14-R01-A/B parser→Core→SMT→공통 CNL. #18 원본 해시를 재검증한
immutable run은 25/25 질의 일치, 전제 12/12 SAT, UNKNOWN 진입 허점 2개 UNSAT,
gate 제거 mutation SAT다. 플랫폼 9개·실제 source 통합 4개 tests가 통과했다.
조건부 EBLC/CNL 1건이며 source-verified/export는 0건이다.

부분 근거 연결·확인 불가 보류와 독립 검토 준비는 완료했다. 다음 종료 기준은 배정된 사람의
실제 독립 응답 수용과 불일치/판단 불가 처리다. 영상60/geometry98 설문 전량을 반복하거나
정책 출력을 gold로 복사하지 않는다.
전체 M12/M14/M16은 PARTIAL, M18 실제 학습·효과는 미실행으로 유지한다.

PhysicalAI 원본 CoC(+CASCADE scene 근거), Qwen3-VL-2B, 보행자·자전거 양보 행동군을
개발 대상으로 선택했다. 기존 98개 후보의 원본 CoC exact link 98/98과 선택 32개/29 clips를
감사했다. [개발 설계](../designs/PAPER1_CNL_LEARNING_DESIGN_V01.md)의 남은 clause·source·
action 후보/gold 계약을 동결한 뒤 32개 개발 표본을 그 기준으로 재감사한다. 필요한 source
없는 수치를 채우지 않으며 upstream split/노출을 보존한다. 모든 나라·모든 rule의 closure를
먼저 완성하거나 이전 1/60을 새 적격성으로 재표기하지 않는다.

2026-09-07에는 기존 영상 답변 19건을 CoC·geometry·source에 연결하고 원본 JSON/CSV,
packet/image, geometry frame/mask hash를 재검증했다. 12건 위험 보임, 4건 위험 보이지 않음,
2건 전이, 1건 관측 불가를 유지했다. 조건부 초안 18건은 기존 답변을 구조화한 것이지
독립적인 모델 예측·정확도나 검증된 CNL이 아니다. 미검토 13건도 분모에 보존했다.
[읽기 전용 대응표](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-review-constraint-alignment-001/reviewed-scene-alignment-2026-09-07-001/review_constraint_alignment.html)를
생성했으며 새 설문/전량 재검토를 요청하지 않았다.

다음 실제 연결 대상은 actor↔semantic zone, 시간창 관찰↔event-time predicate, 그리고
10건의 공사 인력·교통 통제 문맥을 구분한 operational clause다. 현재 stopping backend가
요구하는 수치/profile은 확보된 입력으로만 채운다. 이 연결 전에는 EBLC/SAT/CNL을 실행한
것으로 세지 않으며 기존 human 관찰의 완료 사실도 취소하지 않는다.

기계 실행 완료: source-aware fixture→EBLC/Core/Z3→CNL→assistant supervision,
실제 Qwen 내부 LoRA 네 arm 각 1 update 및 이미지 토큰/gradient/adapter 확인, 새 tests 18개.
[실행 보고서](../reports/PAPER1_CNL_LEARNING_READINESS_REPORT_V01.md)에 실패 run과 재실행을
함께 보존했다. software smoke는 1개 인공 이미지이며 실제 장면 학습·독립 효과가 아니다.
20/39/2667 target-token 차이를 해소할 loss/compute 계약과 실제 provider가 다음 기술 과제다.

그 다음 현재 UI/validator의 strict60 계약을 1차 protocol과 분리해 테스트한다. 그 전에는
기존 source-review 화면을 새 formal gold 설문으로 사용하지 않는다. 지금 전체 재검토를
사용자에게 요청하지 않으며, 기존 답변의 관찰·보정·노출 이력을 재사용한다.

## 6. 완료와 보고

M20 종료에는 source→EBLC→검증→CNL→실제 학습의 추적 가능성과 독립 결과가 필수다.
VLM trainable module의 실제 update/weights와 held-out 이미지/영상 행동 결과가 없으면 종료 불가다.
NOT_EVALUATED는 완료가 아니며 NOT_SUPPORTED/INCONCLUSIVE는 숨기지 않고 주장 축소로 보고한다.
시험·외부 비용·새 license/권한은 실제 실행 전에 확인한다. 기존 run을 덮어쓰거나 인간 판단을
생성하지 않는다. 변경 시 plan/ledger/tracker/STATUS를 맞추고 링크·포털·naming 검사를 수행한다.

## 7. v2.2까지의 실행·완료 근거 이력 (현재 지시 아님)

<details>
<summary>종전 acquisition·검토·artifact 등록부 보기</summary>

아래 완료 사실은 보존한다. 당시 다음 작업·전수 gate·날짜별 수치는 현행 1차 scope를
덮어쓰지 않는다. 현재 다음 작업은 위 M12-R01이고, runtime/full60는 2차다.

#### 이전 5. 현재 활성 작업: GS-P4-PILOT-001

##### 이전 목적

M14/M15의 고정 protocol을 사용해 60장면 전문가 formal pilot의 층화 표본, 독립 annotation,
adjudication, agreement, 작업시간 및 power-analysis 입력을 준비한다. locked KR scope 재감사
결과는 0/60 역사적 baseline으로 보존한다. 승인된 multi-jurisdiction 정책 아래 재판정한
현재 결과는 1/60이다. 장면별 국제협약 normative baseline과 8/8 field closure를 요구하되,
국내법 준수 판정은 이 pilot의 범위에서 제외한다.
공용 catalog schema와 generic CLI에는 국가 기본값이 없으며 catalog 경로를 명시적으로 선택한다.
대한민국 catalog는 P0 역사적 첫 인스턴스일 뿐 M16의 표본 제한이나 기본 authority가 아니다.

##### 이전 현재 단계 상태 요약

- 단계 상태: `M16-S06 COMPLETE` — classified-event calibration과 recorded-rig binding 98/98
- 완료 하위 단계: `M16-S08A COMPLETE` — 98 events/81 clips의 attrition reserve sensor·calibration 공급 풀
- 최신 완료 하위 단계: `M16-S07A COMPLETE` — 공식 calibration source audit, 98-event
  fail-closed precheck와 60-record 미완료 human-review packet
- 최신 UI 하위 단계: `M16-S07B2 COMPLETE` — 60 contact sheets/300 event-adjacent frames는
  유지하되 reviewer 문항을 영상 관찰 가능한 association·시간 상태 두 가지로 제한하고 국가·
  법규·geometry/calibration/authority ref와 source-complete 판정을 제거; 바깥 검토 목록은 기본
  접힘으로 바꾸고 workspace full-width·contact-sheet click-to-zoom·명시적 복귀 버튼을 적용;
  포털 화면 이동 후에도 답변을 복원하는 브라우저 자동저장을 보장하고 slice별 대상·lane/zone·
  시간 상태 우선순위와 STOP 신호/차량 제동등 구분을 담은 상세 예시 매뉴얼을 추가했으며,
  대체된 image/evidence, curator association, 미착수 expert-training 패키지를 활성 메뉴에서 제외
- 최신 실행 하위 단계: `M16-S07B3 COMPLETE` — 단일 검토자가 영상 관찰 60/60을 완료했고
  JSON/CSV, packet candidate 순서, slice와 image hash를 모두 검증; aggregation에는 candidate와
  reviewer 식별자를 제외
- 최신 source frontier 하위 단계: `M16-S07G COMPLETE` — curator 98/98를 검증하고 accepted
  61건의 610개 mask 파일을 source-bound road-geometry candidate로 결합; generic pixel mask를
  ego/event zone이나 dataset-rig geometry로 승격하지 않고 외부 source queue를 고정
- 최신 authority 하위 단계: `M16-S07H COMPLETE` — 공식 UN source만 허용하는 selector로
  98/98에 국제협약 연구 기준을 결합; 유럽권 35건은 Vienna 1968 직접 규칙, 미국 63건은
  Geneva 1949 일반 주의의무 fallback이며 국내법 준수 판정은 0/98로 명시
- 현재 gate: `M16-S07 PARTIAL` — human observation과 verified transform 98/98, active
  actor/control source SET 70/98과 treaty baseline 98/98은 완료했으나 lane/zone 97건,
  slice-specific semantic geometry와 lifecycle source witness는 98건 모두 미확보
- 60-scene 상태: `M16-S08 PARTIAL` — distinct eligible 1/60, shortfall 59; final outcome 0/98
- 마일스톤 상태: `M16 PARTIAL` — reviewer calibration 이후 단계는 시작하지 않음

##### 이전 완료된 준비

1. 세 slice별 8개 slot과 four-strata 계획
2. 대한민국 source-bearing catalog 15개
3. public aggregate 기반 후보/partial/data-gap 재감사
4. synthetic fill 금지와 실제 실행 0건 명시
5. 이미지·검토 방법·예제·필수 항목·fail-closed 판정·JSON/CSV export를 갖춘
   self-contained scene-evidence review kit; 기존 제한 파생 이미지 10개를 별도 단일 HTML에
   내장하고, 이미지밖에 없는 검토자용 image-only 설문을 분리해 준비
   (장면 source closure를 의미하지 않음)
6. 완료된 image-only 검토 10건을 `HUMAN_REVIEWED_IMAGE_CLAIM`으로 보존한 partial scene
   packet 10건으로 변환; 9개 M13 필수 field를 packet마다 missing으로 기록하고 source-complete
   0/10, 계약 생성 허용 0/10, synthetic fill 0건으로 중단; 기존 판정을 숨긴 판정 유형별
   calibration/audit 표본 2건을 별도 큐로 작성하고 독립 재검토 대기
7. 10개 중 source-linked field가 가장 많은 calibration 항목을 결정적으로 선택해 기존 제한
   파생 이미지에 content SHA-256으로 연결하고, 실제 4-camera×4-time timestamp와 기존 adapter의
   ego pose/speed·1-D conflict geometry·전체 actor track을 확인하고, 후속 source bundle에서
   event→model-t0 transform과 clip-specific rig binding을 검증해 필수 입력 6/9를 복구;
   이후 전체 후보의 oriented-box corridor overlap으로 두 보행자를 하나의 source-linked target
   `SET(2)`에 연결하고 공식 California Vehicle Code §21950/§21954와 이미지 단서 기반 관할을
   한계를 명시한 조건부 applicability로 연결해 필수 입력 8/9를 복구; 나머지 1/9 acquisition work order를 생성하고
   계약 실행 0건 유지
8. 선택 이벤트의 선언 후보 2개 중 기존 파생물에 nearest 후보 1개만 보존된 결함을 탐지한 뒤,
   원 obstacle archive에서 all-candidates+track-samples v2를 실행해 후보와 track을 2/2 보존하고
   association review 입력 준비
9. 선택 장면의 횡단보도·보행자 image review와 source-linked actor `SET(2)`에 California Legislature
   §21950을 연결하고 §21954를 예외 문맥으로 보존; SFMTA/SFCTA 자료로 위치 단서를 교차 확인하되
   `INFERRED_HIGH_CONFIDENCE_NOT_DATASET_GPS`로 한계를 고정하고 출처 없는 규범·수치값 0건 유지
10. 마지막 assurance field의 로컬·공식 source를 감사해 관측 egomotion, CoC 파생 response latency,
    DRIVE AGX/VehicleIO 문서를 차량별 보장값으로 사용할 수 없음을 확인; 실제 vehicle/DBW identity,
    runtime capability와 OEM 또는 통제된 제동시험이 필요하다는 data-gap manifest 작성
11. 실제 장면의 8개 source-linked field를 별도 `SIMULATED_ASSURANCE` vehicle binding에 투영해
    GuardSynth→EBLC→Core→Z3를 1장면·2계약으로 실행; 실제 frame-0에서 두 계약 `ACTIVE/VALIDATED`,
    Z3 query/direct replay 100%를 확인; recorded vehicle assurance gap은 M21 항목으로 보존
12. 기존 image review 10건과 adapter 후보 4건을 calibration overlap 기준으로 중복 제거하여
    후보 13건 inventory 작성; 근거 8/8 1건, 4/8 3건, 0/8 9건이며 식별자·synthetic fill 0건
13. 세 추가 이벤트의 source bundle·좌표 변환·rig binding·geometric SET association을 닫아
    실제/파생 장면 근거 8/8을 4건으로 확대하고, 총 17계약을 canonical/runtime/bounded Z3/
    Core에서 100% 일치시킴; 24장면 중 20장면 부족, 두 slice와 여섯 outcome strata 공백을
    합성하지 않고 `M13_TERMINAL_DATA_SHORTFALL_FRONTEND_CAN_PROCEED`로 종결
14. 연구 개요, 22개 마일스톤/Todo, 현재 M13/M16 gate와 이미지·source·association·전문가
    훈련 화면을 통합한 제한 로컬 포털을 구현; tracker 원장을 빌드 시 파싱하고 저장소 전체가
    아닌 선택된 복사본만 `127.0.0.1`에 제공
15. 포털의 현재 마일스톤·하위 태스크를 고정 문구에서 제거하고, server mode의 매
    page load에 milestone ledger·execution tracker·tracker가 지정한 하위 요구사항을 재파싱;
    active work package가 milestone 원장과 불일치하면 HTTP 503으로 fail-closed
16. M16 per-scene eligibility manifest와 fail-closed validator를 TDD로 구현하고, 로컬 source
    record 33개를 10개 alias 중복 제거 후 23개 event로 재색인; 기존 4개 중 1개 cross-event
    timestamp/evidence conflict와 4개 모두의 KR scope mismatch를 확인해 0/60 eligible로 교정
17. 연구 scope owner가 국가 제한 없는 multi-jurisdiction pilot을 승인하고, 장면별 관할·공식
    rule source·ODD 호환성과 기존 8/8 field gate를 유지하는 v2 계획과 decision을 고정
18. 전체 로컬 licensed metadata에서 135 candidate events/107 overlap clips를 확인하고 106개
    sensor-eligible clip을 식별; 실제 추가 sensor/annotation asset은 0개이므로 값을 합성하지 않고
    `BLOCKED_DATA_SHORTFALL` acquisition queue로 고정
19. 승인된 CASCADE annotation 2,066개를 materialize하고 135 events를 시간 정렬해 98개
    slice candidate, 37개 unsupported, 38개 multi-slice ambiguity로 fail-closed 분류; final
    outcome은 0개로 유지하고 잔여 quota용 59 clips/57 chunks/228 packages sensor shortlist를 고정
20. 승인된 228 remote sensor packages를 full-package 복사 없이 range-access하여 shortlist의
    354 members(1,088,704,611 bytes)를 materialize; 59/59 member·temporal closure를 검증하되
    association/calibration/rule/outcome gap을 보존해 새 8/8/outcome/eligible을 0/0/0으로 유지
21. calibration 5종 285 packages에서 shortlist 295 rows(2,431,139 bytes)만 materialize해 59/59
    5/5 closure와 recorded-rig binding을 확보; online/offline extrinsics 차이 때문에 verified
    transform은 0으로 보존하고 59-record association source-review queue를 생성
22. 남은 classified 39 events를 22개 새 clip과 기존 clip 재사용 17 events로 분리하고, 새 clip의
    132 sensor members(359,878,885 bytes)와 calibration 110 rows(906,491 bytes)만 추가 확보;
    총 98 events/81 clips의 temporal·calibration·rig closure를 98/98로 닫되 verified
    transform·8/8·outcome은 0/0/0으로 유지하고 98-event review queue를 생성
23. NVIDIA 공식 dataset card·devkit·feature catalog를 재감사해 offline-optimized feature 설명은
    있으나 일반 online/offline calibration 선택 규칙은 없고 open map도 제공되지 않음을 확인;
    근거 없는 transform 승격 없이 98-event source-review precheck와 실제 결정이 비어 있는
    60-record human-review packet을 생성하고 geometry source 필요 98/98을 고정
24. 준비된 60-record packet을 materialized front-wide video와 다시 연결해 각 이벤트의
    t-1.0s~t+1.0s 5개 frame으로 contact sheet 60개를 생성; 총 300 frames를 9.7 MiB
    self-contained restricted HTML에 내장하고 filter·autosave·JSON/CSV export와 함께 GuardSynth
    포털의 아홉 번째 독립 검토 화면으로 등록. 실제 human decision은 0/60으로 유지

##### 이전 M14/M15 종료 입력

- 제한 lexical parser, graph/BM25/dense-adapter retrieval, four-valued applicability와 binding
- 24-case/3-slice locked synthetic matrix: schema·기대 verdict 24/24, claim 승격 0건
- 별도 simulation policy를 사용한 crosswalk proposal→GuardSynth→EBLC→Core→Z3 2/2
- 운영 policy mapping 1/3과 실제 24장면 정확도 미평가를 명시적 limitation으로 보존
- B0–B8/B13 common result 240/240, channel firewall/abstention protocol 동결

##### 이전 다음 실행 조건

- M12-R01 source/operational clause 및 M13–M15 재적격화 gate; calibration variant/transform
  98/98 완료 이력은 재다운로드 작업으로 반복하지 않음
- 98 events의 source-linked lane/zone geometry 확보; 데이터셋 자체에는 open map이 없음
- 준비된 60-record packet은 source curation용이며 M16-R01 역할·노출·geometry 계약 후 활용
- association source 자체가 부족한 38 events는 외부 geometry 확보 전 reserve로만 보존
- 12개국 treaty normative baseline은 98/98 완료; outcome lifecycle witness 확보
- 세 slice 20개, 여섯 outcome 10개와 각 joint cell 3~4개 quota를 개별 record에서 재계산
- formal reviewer calibration·동일조건 독립 gold·adjudication은 source/quota 및 M16-R01/R02
  gate 후 실행; source 확인의 기계 제안 노출과 formal gold의 독립성을 구분
- 입력이 60개 미만이면 부족량과 빈 cell을 artifact로 종결하고 annotation을 시작하지 않음

M13의 부족한 실제 장면을 합성해 60-scene pilot 성공으로 바꾸지 않는다.

##### 이전 M16 preflight 결과

- protocol, 60 joint-slot manifest, annotation/assignment/metrics/power schema와 preflight 구현 완료
- deterministic blinded 2인 배정, 별도 adjudicator, 두-mode training UI와 timing export 구현
- finite-sample nominal α, field/source agreement, correction/time 집계 구현
- 관측 effect/variance source ref를 요구하는 power-planning contract 구현
- per-scene 8-field status/ref/freshness/unit/frame/scope/outcome validator와 slot binding 구현
- 로컬 source record 33개, image-event alias 10개 제거, distinct event 23개
- 기존 4개 재감사: 8/8 closure 3개, cross-event conflict 1개; 새 정책에서 eligible 1개,
  jurisdiction `UNKNOWN` review 2개
- eligible scene 1/60, shortfall 59
- slice shortfall: pedestrian 19, stop/signals 20, following/cut-in 20
- outcome shortfall: HAZARD_TRUE_ACTIVE 9, 나머지 다섯 outcome 각각 10
- 18개 joint cell 중 pedestrian×HAZARD_TRUE_ACTIVE에 1개 binding, 나머지는 0개
- annotation start `false`; M17은 독립 expert gold가 없어 계속 `QUEUED`
- synthetic required-field fill 0, unsourced normative/numeric value 0
- 새 eligible 0개이고 retained 1개는 기존 M13 실행 근거가 있어 추가 GuardSynth→EBLC→Core→Z3 실행 없음
- 상태 `PARTIAL_DATA_ACQUISITION`; annotation start `false`, M17은 계속 `QUEUED`
- licensed metadata screen: 135 events/107 clips, sensor-eligible 106 clips
- locally materialized annotation 2,066; classified 98, unsupported 37, multi-slice 38
- attrition reserve 39 events: 22 new clips, 7 same-new-clip secondary events, 10 existing-clip secondary events
- total materialized sensor 81 clips/486 members/1,448,583,496 bytes; event temporal closure 98/98
- calibration 405 rows/3,337,630 bytes; event calibration/recorded rig/verified transform 98/98/98
- association queue actor/lane 24, actor/zone 19, control/lane 17, insufficient geometry 38
- initial official calibration audit는 offline-optimized 설명만 확인했으나, post-review 재감사에서
  NVIDIA NCore pinned commit의 offline-only PhysicalAI conversion rule을 찾아 variant selection 98/98 폐쇄;
  데이터셋 open map 부재는 유지
- source-review precheck `COMPLETE`: human-review packet 60, geometry source required 98,
  auto-closable transform/rule/outcome 0/0/0
- video-observation review `COMPLETE`: 60 contact sheets/300 frames와 실제 단일 검토자 60/60;
  association clear/ambiguous/not-observable 55/1/4, temporal hazard/no-hazard/transition/
  not-observable 29/24/2/5; JSON/CSV·packet 순서·slice·image hash 일치
- post-review source closure audit `COMPLETE`: 98 events에 human observation을 연결하고 81개
  materialized clip의 offline egomotion 및 405 calibration rows를 hash 재검증; NVIDIA NCore
  commit `59c698d206da92b406a4f72619fce3b3a2c64bfd`에 따라 offline variant selection 98/98 폐쇄
- M16 review-event anchor 결정으로 event timestamp를 scene t0로 고정하고 81개 offline
  extrinsics assets·648 rows 및 egomotion 보간을 검증해 verified transform 98/98 폐쇄
- CASCADE approved human annotation 98개를 hash 재검증하고 schema-defined active
  `because_of`/`action_target`에서 actor/control source SET 70/98, strict shared containment에서
  lane relation 1/98 폐쇄; human video 답변의 source 승격 0건
- actor/control source 28건, lane/zone 97건, conflict geometry·lifecycle witness 각 98건이
  남아 있으며 새 source 없는 curator 설문은 생성하지 않음
- pinned TwinLiteNet+ large로 81개 hash-verified source video의 98 events×5 timestamps,
  총 490 frame lane/drivable-area 후보를 생성; curator pending 98, source field update 0,
  machine output ground-truth 승격 0건
- new 8/8/outcome/eligible 0/0/0
- acquisition session `M16_SOURCE_GEOMETRY_CANDIDATES_GENERATED_CURATOR_REVIEW_REQUIRED`
- 최종 package: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-source-acquisition-2026-08-14-v18/`
- source-review workbench: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-source-review-001/m16-source-review-2026-08-15-v5/`
- validated human-review result: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-source-review-001/m16-source-review-2026-09-04-v1/`
- post-review source-closure result: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-post-review-source-closure-2026-09-05-v1/`
- event-anchor transform result: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-event-anchor-transform-2026-09-05-v1/`
- structured-link audit result: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-cascade-structured-link-audit-2026-09-05-v1/`
- geometry candidate result: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-geometry-candidate-2026-09-05-v1/`
- geometry review workbench: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-geometry-review-2026-09-06-v1/`
- validated geometry curator review: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-geometry-curator-review-2026-09-06-v1/`
- 기존 업로드 JSON/CSV의 98개 품질 평가를 manifest·순서·slice·event/image hash에 대해 검증했으며
  curator review는 98/98 완료다. 기계 geometry 확인은 61건이고 수동 보정 판정 37건은 업로드
  파일에 polygon 좌표가 없어 correction data pending으로 유지한다. 없는 좌표는 생성하지 않았다.
- geometry source frontier: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-geometry-source-frontier-2026-09-06-v1/`
- accepted 61건의 다섯 시점 drivable/lane mask 610개를 manifest SHA-256으로 재검증해 source-bound
  candidate로 결합했다. 이는 ego lane, crossing conflict zone, stop line/stopping zone 또는 target
  lane의 의미를 닫지 않으므로 semantic rig geometry update는 0건이다. 남은 작업은 항목별 queue로
  고정했고 new 8/8/outcome/eligible은 0/0/0, 총 eligible은 1/60이다.
- machine-assisted expert source review: `artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-expert-source-review-001/m16-expert-source-review-2026-09-06-v2/`
- 60/60 모델 overlay와 저신뢰 ego-corridor, 24장면의 사건 시각 근접 CASCADE target anchor
  33개, 회색 context-only anchor 23개, pedestrian event-zone 후보 8건을 기계 표시로 제공한다. 기존 60건 영상 관찰은 machine
  prediction으로 바꾸지 않고 provenance-labelled draft로만 제시한다. 최소 2인 독립 확인과
  adjudication 전에는 source-complete/outcome/eligible을 변경하지 않는다.
- current portal: `artifacts/projects/guardsynth-coc/restricted/guardsynth-project-portal-001/portal-2026-09-06-v3/`

##### 이전 다음 단일 작업

**M12-R01 / GS-P0-SOURCE-REQUAL-001: 현 scope의 source→operational clause 대응을 재감사한다.**
협약 direct/general fallback, 승인된 system requirement와 physical/numeric derivation을
구분한 matrix를 만들고, 기존 retained eligible 1건을 포함해 조건부/미확인 source를 기록한다.
구체적 clause를 정당화하지 못하는 source는 추가 요구를 남기고 hard bound로 승격하지 않는다.
종료 근거는 새 owner-scoped run의 source matrix·binder/abstention tests·scope verdict다.

그 후 M13–M15, M16-R01/R02 보완을 앞에서부터 수행한다. 현재 source-review 화면은 자료
준비용이고 formal gold 설문이 아니다. 기존 영상/geometry 제출은 재사용하며 이번 감사만으로
사용자에게 60장면 전체 재검토를 요청하지 않는다. UI/schema/assignment의 보완 구현은 미실행이다.

#### 이전 6. 완료 근거 등록부

| 완료 항목 | 대표 근거 | 주장 범위 |
|---|---|---|
| EBLC v0.2 RC | [release artifact](../../../../artifacts/results/public/eblc-release-candidate-001/eblc-v0.2-rc1-2026-08-09/REPORT_KO.md) | bounded language/tooling, not safety |
| source-aware generator | [generator report](../../../../artifacts/results/public/guardsynth-source-aware-generator-001/source-aware-generator-2026-08-09-v3/REPORT_KO.md) | synthetic structured generation |
| source boundary/readiness | [terminal report](../../../../artifacts/results/public/guardsynth-real-scene-readiness-001/terminal-readiness-2026-08-09-v3/REPORT_KO.md) | readiness/abstention, 0/24 complete |
| label-light interface | [label-light report](../../../../artifacts/results/public/guardsynth-label-light-grounding-001/label-light-2026-08-10-v3/REPORT_KO.md) | synthetic workflow, not association accuracy |
| 대한민국 scope/source catalog | [catalog report](../../../../artifacts/results/public/guardsynth-source-catalog-001/kr-source-catalog-2026-08-10-v2/REPORT_KO.md) | source traceability, not legal advice/safety |
| 24-scene readiness | [readiness directory](../../../../artifacts/results/public/guardsynth-24-scene-dry-run-001/kr-dry-run-readiness-2026-08-10-v1/) | slot/data-gap audit, real execution 0/24 |
| image-review partial packet | [restricted packet directory](../../../../artifacts/results/restricted/guardsynth-image-review-partial-scene-001/alpamayo-image-review-2026-08-11-v2/) | image-only 10건 변환, source-complete 0/10, 임의 필수값 0건, blinded audit 2건 대기 |
| first calibration source audit | [restricted audit directory](../../../../artifacts/results/restricted/guardsynth-calibration-scene-source-audit-001/alpamayo-calibration-source-2026-08-11-v17-rule-applicability/) | timestamp·ego state·geometry·actor tracks·coordinate transform·clip rig binding·geometric SET association·조건부 공식 rule binding 8/9, 실제 계약 실행 0건 |
| first scene rule applicability | [restricted rule directory](../../../../artifacts/results/restricted/guardsynth-rule-applicability-001/alpamayo-episode-05-2026-08-11-v1/) | CA §21950 조건부 연결, §21954 예외 문맥, 이미지 단서 위치 추론(not dataset GPS), 안전 검증 아님 |
| scene-evidence review | [review kit](../../../../artifacts/results/public/guardsynth-scene-evidence-review-001/scene-evidence-review-2026-08-10-v5/SCENE_EVIDENCE_REVIEW.html) | 이미지-설문 1:1 카드, batch/folder import와 제한 내장 builder; 누락 source 대체 아님 |
| vehicle assurance source audit | [restricted assurance audit](../../../../artifacts/results/restricted/guardsynth-vehicle-assurance-audit-001/alpamayo-episode-05-2026-08-11-v1/) | 후보 4건 모두 보장 profile로 부적합, 8/9 유지, synthetic fill 0 |
| recorded-scene simulation projection | [restricted simulation report](../../../../artifacts/results/restricted/guardsynth-simulated-scene-dry-run-001/alpamayo-episode-05-simulation-2026-08-11-v4/REPORT_KO.md) | 실제 장면 8/9 + 별도 가상 차량, 2계약, Core/Z3 실행; 실제 차량 source closure 아님 |
| simulation-24 candidate inventory | [restricted inventory report](../../../../artifacts/results/restricted/guardsynth-sim24-candidate-audit-001/alpamayo-candidate-inventory-2026-08-12-v1/REPORT_KO.md) | 중복 제거 13건; 8/8 1, 4/8 3, 0/8 9; 식별자·synthetic fill 0 |
| M13 terminal simulation batch | [restricted terminal report](../../../../artifacts/results/restricted/guardsynth-sim24-batch-001/alpamayo-terminal-batch-2026-08-12-v1/REPORT_KO.md) | 4/24 장면·17계약; canonical/runtime/bounded-Z3/Core/direct replay 100%; 20장면 부족·slice/strata 공백, 실제 차량 안전 증거 아님 |
| M14 CoC-conditioned front-end | [locked matrix](../../../../artifacts/results/public/guardsynth-coc-frontend-matrix-001/locked-synthetic-2026-08-12-v1/REPORT_KO.md), [materialization](../../../../artifacts/results/public/guardsynth-coc-frontend-materialization-001/crosswalk-synthetic-2026-08-12-v1/REPORT_KO.md) | 24-case protocol 100%, 1-rule EBLC/Core/Z3 handoff; 실제 NLP/장면 정확도 아님 |
| M15 baseline protocol | [protocol run](../../../../artifacts/results/public/guardsynth-baseline-protocol-001/locked-interface-2026-08-12-v2/REPORT_KO.md) | 240 common results, channel violations 0; 성능 비교 아님 |
| M16 expert pilot preflight | [restricted preflight](../../../../artifacts/results/restricted/guardsynth-expert-pilot-preflight-001/m16-preflight-2026-08-12-v4/REPORT_KO.md) | locked 60-slot design, 4/60 eligibility, annotation start 금지, 부족값 합성 안 함 |
| M16 source eligibility reacquisition | [restricted run](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-source-acquisition-2026-08-13-v1/REPORT_KO.md), [public aggregate](../../../../artifacts/projects/guardsynth-coc/public/guardsynth-m16-scene-acquisition-001/m16-source-acquisition-2026-08-13-v1/REPORT_KO.md) | 33→23 candidates, 기존 4개 중 3개 8/8·0개 KR-scope eligible, annotation 미시작, 안전성/효과 결과 아님 |
| M16 geometry source frontier | [restricted frontier](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-geometry-source-frontier-2026-09-06-v1/REPORT_KO.md) | curator 98/98, accepted mask 61건/610파일 검증; semantic geometry·authority·lifecycle 승격 0, eligible 1/60 |
| M16 treaty normative baseline | [restricted binding run](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-treaty-authority-binding-2026-09-06-v2/REPORT_KO.md) | 98/98 bound; Vienna direct 35, Geneva fallback 63, domestic legal compliance not evaluated, eligible 1/60 |
| local research/review portal | [restricted portal](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-project-portal-001/portal-2026-09-05-v1/REPORT_KO.md) | 루트 first-class 앱; 52 milestone 자동 추적, offline variant 98/98 폐쇄와 남은 transform·geometry·authority·lifecycle source closure를 표시하고 상세 검토 UI를 loopback 제공; 연구 결과 아님 |
| current backend regression | M16 image-review portal 후 GuardSynth 210/210, EBLC 133/133, portal/structure 26/26 | scoped software regression; isolated local NumPy/SciPy environment와 project-local Z3 5.0.0 사용 |

#### 이전 7. 매 작업 세션의 운영 규칙

##### 이전 시작할 때

1. `01_RESEARCH_PLAN_V02.md`의 관련 RQ, 단계와 gate를 확인한다.
2. [마일스톤 원장](02_PROJECT_MILESTONES.md)의 Todo와 선행조건을 확인한다.
3. 이 문서에서 `READY_NEXT`인 작업 하나를 선택한다.
4. 선행조건이 충족됐는지 확인하고, 미충족이면 구현하지 않고 정확한 blocker를 기록한다.
5. 비자명한 작업은 먼저 `docs/requirements/` 또는 `docs/designs/`에 범위와 기대 테스트를 고정한다.

##### 이전 구현·실험할 때

1. TDD가 가능한 software는 RED 기대를 먼저 고정한다.
2. 실제/제한 입력을 synthetic 값으로 채우지 않는다.
3. public/restricted artifact를 분리하고 새 run ID를 사용한다.
4. 구현 결과에 맞춰 gate나 기대값을 사후 완화하지 않는다.

##### 이전 종료할 때

1. 실행 명령, test count, gate, 실패와 주장 범위를 artifact/report에 기록한다.
2. 마일스톤 원장의 Todo, 종료 gate와 대표 근거를 갱신한다.
3. 이 문서에서 해당 작업의 상태와 완료 근거 링크를 갱신한다.
4. 완료 조건이 모두 충족됐을 때만 `COMPLETE`로 바꾸고 다음 한 작업을 `READY_NEXT`로 지정한다.
5. 연구 범위나 사전 gate를 바꿨다면 연구계획을 새 버전으로 갱신하고 변경 이유를 남긴다.
6. 문서 링크 검사와 `MANIFEST.sha256`을 갱신한다.

허용 상태는 `QUEUED`, `READY_NEXT`, `ACTIVE`, `BLOCKED`, `PARTIAL`, `COMPLETE`,
`SUPERSEDED`뿐이다. 주관적인 완료율 숫자는 사용하지 않는다.

#### 이전 8. 현재 하지 않을 일

- 새 evidence 요구가 없는 EBLC 문법 기능의 반복 확장
- M13-R01과 M14/M15/M16 재적격화 gate 전에 formal annotation 실행(source curation 준비는 허용)
- CoC를 규범적 authority 또는 관측 fact로 취급
- 실제 source 없이 법규/차량 수치를 생성
- generator와 같은 구현을 독립 safety oracle로 주장
- synthetic/Z3 결과를 실제 차량 안전성 효과로 서술

</details>
