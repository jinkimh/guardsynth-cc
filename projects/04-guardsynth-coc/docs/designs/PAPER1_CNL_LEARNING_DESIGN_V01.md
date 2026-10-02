# 1차 논문 CNL/VLM 개발 설계

- project_id: `guardsynth-coc`
- 기준: [연구계획 v2.3](../plans/01_RESEARCH_PLAN_V02.md), [M18 계약](../requirements/M18_EBLC_LEARNING_EFFECT_REQUIREMENTS_V01.md)
- 상태: `DEVELOPMENT_SELECTION_COMPLETE_MAIN_TASK_SOURCE_FREEZE_PENDING`
- 기준일: 2026-09-06

## 1. 개발 선택과 근거

| 항목 | 선택 | 경계 |
|---|---|---|
| 주 dataset | 로컬 NVIDIA PhysicalAI 이미지/영상 + 원본 reasoning CoC | CASCADE는 동일 clip의 장면 근거이며 두 번째 효과 dataset으로 계산하지 않음 |
| VLM | Qwen3-VL-2B-Instruct, snapshot `89644892e4d85e24eaac8bacfd4f463576704203` | 로컬 checkpoint/processor 해시 고정, 새 다운로드 없음 |
| trainable module | VLM language attention의 q/k/v/o projection LoRA | 별도 scorer가 아님; vision encoder는 고정 가능 |
| 주 행동군 | `PEDESTRIAN_CYCLIST_YIELD` | 대비 행동군은 현재 추가하지 않음 |
| 기존 개발 자산 | 32 events / 29 clips, 원본 CoC 정확 연결 32/32 | source/development pool; 독립 test로 자동 승격 금지 |

원본 reasoning 파일은 1,740 clip 행, 2,077 events이며 9행에 events가 없다. 결측 행을
기록하고 새로운 CoC를 만들지 않는다. 기존 98개 후보는 clip ID와 event timestamp가
정확히 일치하는 원본 CoC와 모두 연결된다. nearest timestamp로 근사 연결하지 않는다.
선택 32 events는 upstream train 31 / val 1이다. 이 표기를 무시하고 같은 clip을 무작위로
train/test로 나누지 않는다. 추가 split은 upstream 경계·clip/episode·노출 이력을 함께 보존한다.

## 2. source 역할과 아직 동결하지 않은 main 계약

| 입력 | 허용하는 역할 | 불허하는 승격 / 남은 작업 |
|---|---|---|
| 원본 CoC | intent·target·제약 후보의 CLAIMED 문맥, 공통 supervision | 관측 사실이나 독립 안전 정답으로 사용하지 않음 |
| 원본 영상·timestamp | decision 시점까지의 관측 | event 이후 frame으로 정답을 예견하지 않음 |
| CASCADE / 기존 영상·polygon 검토 | 출처와 노출 이력이 있는 장면 근거 | 기계 제안 확인을 독립 gold로 재표기하지 않음 |
| actor↔ego/crossing zone | 선택 대상·충돌 영역의 관계 | generic drivable mask나 화면 polygon을 metric geometry로 승격하지 않음 |
| 규범 | 출처를 명시한 선택 rule 또는 선언된 benchmark system requirement | KR 기본값·전 세계 국내법 준수·출처 없는 수치 금지 |
| 물리 수치 | 사용 clause가 요구할 때만 source/profile/단위/frame 검증 | 원본 장면에 synthetic 차량 수치를 이식하지 않음 |
| action gold | 공통 후보 행동에 대한 독립 판정 | 기록 행동·CoC·생성 EBLC를 그대로 정답으로 복제하지 않음 |

M12-R01의 남은 동결 대상은 **실제로 사용할 clause, 필요한 source/관측량, 행동 후보의
해석, violation/nominal 판정과 abstention 계약**이다. 위 개발 선택은 이 계약 완료가 아니다.
국가 법규의 보편적 적용을 주장하지 않고, 필요한 scene source가 없으면 보류한다.
수치 claim을 제외하는 선택도 사용할 EBLC subset과 표현 의미를 확인한 뒤 명시적으로 기록한다.

기존 renderer/생성기에서 software fixture가 성공했다고 새 실제 장면의 binding이 구현된 것은
아니다. 현재 source-aware fixture는 numeric stopping/lifecycle 입력을 포함한다. 선택 장면의
부족한 geometry/profile을 그 fixture의 숫자로 채우지 않는다. 1차 subset에 필요한 지원만
구현하며 범용 언어 연구/플랫폼을 Project 04에 복제하지 않는다.

## 3. 학습과 추론 경계

공통 user 입력은 원본 visual input + 과제 질문 + 동일 후보 행동이다. 원본 CoC와 정답 CNL은
assistant target에만 넣는다. 순서는 `COC → CONSTRAINTS(있을 때) → ACTION`이며 prompt와
padding의 loss는 제외한다. L0에는 CONSTRAINTS 부분이 없다. 이미지/CoC/행동 정답/constraint
해시와 renderer/compiler version을 example에 연결한다. 정답·제안 overlay와 미래 frame이
섞인 기존 검토 contact sheet를 학습/추론 이미지로 사용하지 않는다.

L1은 동일 source의 직접 NL provider, L2는 parseable EBLC 후보를 semantic compiler 없이
같은 renderer로 투영, L3는 source gate→Core/SMT check 이후 투영한다. malformed 후보와
semantic 실패는 별도 abstention으로 원래 분모에 남긴다. matched-coverage 분석과 전체
cohort 결과를 구분한다. 현재 builder는 matched four-arm pack을 검사하며 실제 provider의
실패 registry/전체 cohort evaluator는 아직 구현하지 않았다.

현재 GPU smoke의 질문/이미지는 동일하며 내부 LoRA 3,211,264 parameters를 학습했다.
rank 8, alpha 16, dropout 0, seed 42, 1 update는 **software smoke 설정**이지 본 실험의
동결된 학습 예산이 아니다. 실제 visual resolution/frame sampling, action 후보, loss weighting,
개발 seed/예산을 정한 후 본 실험은 최소 3 paired seeds로 별도 수행한다.

중요한 smoke 관찰: supervised tokens가 L0 20 / L1 39 / L2·L3 2,667로 달랐다.
단순히 optimizer update 수를 맞추는 것으로 동일 학습 예산이라 주장하지 않는다. provenance
boilerplate를 포함한 긴 CNL과 action loss 비중 문제를 dev에서 점검하고 사용 clause의
충실한 렌더링·loss weighting·token/compute 허용 차이를 **test 전에** 동결해야 한다.
깨끗한 fixture의 L2/L3 텍스트가 같은 것은 정상이며 검증 기여의 효과 증거가 아니다.

## 4. 독립 평가와 진행 조건

source 정리 후 neutral packet에서 2명의 독립 reviewer와 별도 adjudicator가 필요한
action/guard gold를 판정한다. CNL의 의미보존 검토도 별도로 필요하다. 기존 source 검토
19건/미요청 13건이라는 선택 pool의 상태를 보존하며 무조건 32건을 다시 검토시키지 않는다.

새 main cohort, exposure/clip split, dev endpoint power, 실제 L1/L2/L3 provider, 독립 gold가
준비되기 전 confirmatory training/test는 시작하지 않는다. EBLC의 bounded SAT 결과는 source
진실성·장면 안전성·CNL 의미보존의 증거를 대신하지 않는다. test 시점 외부 gold CNL/guard,
verifier/reranker/shield는 없다. 평가 대상은 VLM이 실제 시각 입력에서 출력한 행동이다.

개발 실행 명령과 재현 범위는 [runner](../../experiments/paper1_cnl_learning/README.md),
실행 결과와 오류 보존은 [보고서](../reports/PAPER1_CNL_LEARNING_READINESS_REPORT_V01.md)를 따른다.

2026-09-07의 기존 검토 연결은 19개 실제 장면에 대한 review-derived 조건부 초안까지만
수행했다. 기존 답변과 CoC를 맞춰 본 기록이지, 이를 입력으로 쓰지 않은 모델의 독립
예측 정확도가 아니다. actor/semantic-zone ID, event-time predicate, 운영 규칙 및 필요한
numeric source가 미결이라 실행 EBLC/SAT/CNL은 아직 생성하지 않았다. 전체 설문 반복 없이
다음 source binding의 입력으로 재사용한다.

## 5. 사건 source 연결 이후의 구현 경계

2026-09-08 갱신: 아래는 당시 구현 요구의 기록이다. 이후
[행동 계약 v0.1](PAPER1_ACTION_CONTRACT_DESIGN_V01.md)의 별도 schema/parser→기존 Core/SMT→
공통 CNL renderer를 구현하고 #18 조건부 실행을 완료했다. numeric 프로그램은 바꾸지 않았다.
실제 source-verified 제약·독립 CNL 검토·action gold·학습 export는 아직 미완료다.

후속 exact-interval run은 19건에서 직접 causal target 9건/단일 person source ID 6건을
연결했다. source ID의 유일성은 hazard truth나 독립 action gold가 아니다. #54/#56의
release 문맥에는 다른 control 주석이 있으므로 한 제약의 해제가 전체 PROCEED 허가는 아니다.

현재 platform `EBLCProgram` v0.1/v0.2와 renderer는 numeric stopping/lifecycle 모델에
연결돼 있다. 단지 action domain을 바꾸거나 geometry에 0을 넣는 방법으로 qualitative
명세를 지원했다고 주장하지 않는다. 다음 사용 subset 설계는 아래 경계를 명시해야 한다.

- 연구용 행동 제약과 source 관측을 분리하고, treaty 일반 의무를 특정 수치/행동으로 자동 변환하지 않는다.
- 제약별 대상·predicate·UNKNOWN 및 독립적인 다른 통제 의무를 표현한다. UNKNOWN은 FALSE가 아니다.
- 전제의 만족 가능성을 먼저 검사하고 금지 행동의 반례를 검사한다. 모순된 전제로 얻은 UNSAT를 성공으로 세지 않는다.
- 동일 subset을 L2/L3의 동일 renderer에 공급하고 의미 검증 여부만 분리한다. 기존 수치 모델을 묵시적으로 약화하지 않는다.
- source 충족·추출 검증·CNL 충실성·독립 gold·학습 export를 각각 판정한다. 현재 source JSON은 학습 export가 아니다.

이는 다음 구현의 요구 경계이며 subset 인터페이스/행동 후보 동결이나 해당 EBLC 검증 완료가 아니다.
공통 언어·Core·renderer 구현은 `platforms/eblc-bcv/`, 장면 source adapter는 Project 04에 둔다.
