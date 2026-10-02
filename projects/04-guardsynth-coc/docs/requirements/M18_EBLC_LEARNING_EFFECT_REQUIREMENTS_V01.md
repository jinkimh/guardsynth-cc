# M18 EBLC→자연어 제약 기반 CoC 학습 효과 요구사항

- project_id: `guardsynth-coc`
- work package: `GS-P5-LEARNING-001`
- evaluation ID: `E4-L`
- protocol version: `paper1-method-preservation-v0.1` (v2.4 scope; v2.3 history below)
- 필수 학습 대상: `MULTIMODAL_VLM_WEIGHT_UPDATE_REQUIRED`
- milestone: `M18-S01`~`M18-S05`
- 상태: `MAIN_STUDY_QUEUED_SOFTWARE_PREFLIGHT_EXECUTED`
- 상위 권위: [연구계획](../plans/01_RESEARCH_PLAN_V02.md)
- 범위 결정: [1차 논문/2차 개발 분리](../decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)
- 입력: M12 제한 task/source, M14 CNL 경로, M15 네 arm, M16 독립 검토,
  M17-S01 split/gold 및 S02 사용 subset 품질

## 현행 v2.4: 효과 보존 비교

[승인된 범위](../decisions/PAPER1_METHOD_PRESERVATION_AND_LABELING_DECISION_V01.md)가 아래 v2.3과 충돌할 때 우선한다.
‘보존’의 사용자 기준은 앞선 논문이 지지한 개선 수준이다. 낮아진 두 조건의 동률로 대체하지 않는다.
새 결과 전에 선행 조건/수치 대응, P1 재현 기준, P2-P0 개선과 P2-P1 허용 열화를 함께 고정한다.
기존 효과 수준을 뒷받침하지 못하면 보존 성공을 주장하지 않으며 방법 구현 완료와 효과 미입증을 구분한다.
P0=제약 없는 CoC, P1=기존 자연어 제약, P2=동일 의미의 EBLC 검증→CNL 제약.
같은 시각 과제·행동 정답·모델·seed·학습 예산에서 P1/P2 제약의 학습/평가 위치를 맞춘다.
기존 controlled synthetic VLM 학습을 우선하며 계약 제공 평가를 허용한다. 답 후보를 입력하거나
평가 정답에서 제약을 역생성하지 않는다. 제공한 benchmark 계약과 자동 추출 근거를 구분한다.
실제 VLM 업데이트·시각 행동 평가·의미 보존/비누출 감사는 필수다. P2-P1 보존과 P2-P0 개선을
분리하고 위반·정상 진행·불필요 정지·coverage·CI를 함께 보고한다. 비열등성 허용폭/분석과
새 평가 장면은 결과 전 고정하며 ≥3 paired seeds를 계획한다. 미달은 탐색적/불확정으로 표시한다.
LLM 약지도 확대는 provenance와 표본 감사 계획을 요구한다. 독립 evaluator/사람 참조가 없으면
자기 일치율만으로 성능을 주장하지 않는다. 과거 test 재사용/개발 노출 및 synthetic 한계를 공개한다.
네-arm real-road/no-guard-at-test 확장은 후속이며 아래 기존 gate를 통과한 것으로 세지 않는다.

## 1. 이전 v2.3 필수 전달 경로 (후속 실제 영상 연구)

CoC·scene·source → 제약 후보 추출 → EBLC 명세 → 검증 → CNL 자연어 제약 →
CoC 학습 supervision 삽입 → 실제 가중치 학습 → 독립 held-out 행동 평가.

CNL을 예시 화면에만 보이거나 EBLC에서 preference label만 계산한 실험은 완료가 아니다.
기존 preference-only 설계는 2차 선택 실험이며 이 primary를 대체하지 않는다.
'강화된 학습'은 제약을 통한 학습 개선이며 RL을 의무적으로 의미하지 않는다.

Primary는 주 데이터셋 1개·학습 가능한 VLM 1개·선택 행동군 1~2개의 제한된 행동/궤적 선택
과제다. 학습과 test 모두 실제 이미지/영상 및 공통 텍스트 입력을 사용한다. scene text만
받는 LLM, 규칙 엔진 또는 별도 trajectory scorer의 학습으로 대체할 수 없다.

동일 초기 VLM checkpoint에서 L0–L3를 각각 SFT한다. full fine-tuning 또는 VLM 내부의
LoRA/학습 adapter를 허용하며 vision encoder 전체의 업데이트는 필수가 아니다. 다만
이미지·텍스트를 처리해 응답을 생성하는 VLM 경로의 parameter가 실제로 갱신돼야 한다.
VLM을 완전히 고정하고 별도 scorer/action head만 학습하는 결과는 보조 실험이며 primary
완료가 아니다. 모델/checkpoint·학습 module·parameter 수·SFT 방식은 dev에서 고정한다.
Alpamayo 전체 학습이나 실차 제어는 요구하지 않는다. 고정 후보 선택을 closed-loop 성공으로 확대하지 않는다.

## 2. 네 학습 arm

| Arm | supervision | 역할 |
|---|---|---|
| L0 | 원본 CoC + 공통 action/trajectory target | 제약 없는 학습 |
| L1 | 같은 CoC·scene·source로 직접 생성한 자연어 제약 + 공통 target | 직접 자연어 제약 |
| L2 | EBLC 후보 → 동일 CNL renderer, semantic 검증/repair/선별 생략 + 공통 target | 검증 생략 ablation |
| L3 | source-bound EBLC → 검증 → CNL + 공통 target | 제안 방식 |

L2는 종전 flat/preference arm과 다른 정의다. 기존 run을 재표기하지 않고 새 manifest에
v2.3 arm 의미를 기록한다. L1/L2도 실제 생성 가능한 provider/renderer여야 하며 placeholder는
baseline 완료가 아니다. malformed 출력의 parse abstention과 semantic 오류를 구분한다.
검증 선택/repair로 데이터 coverage가 달라지면 그 차이와 matched-coverage 분석을 보고한다.

모든 arm의 base scene/CoC·action label·후보 집합·모델 초기값·optimizer/tuning 예산은 동일하다.
CNL은 실제 example의 target supervision으로 넣는다. 원본 CoC와 CNL의 결합 위치, loss
mask/weight, action head/text target과 inference format은 M18-S02에서 freeze한다.
arm별로 행동 정답까지 바꾸는 것은 다른 실험이므로 primary에 섞지 않는다.

원래 CoC 문맥에 없는 임의 경로를 지정해 base task를 바꾸는 실험은 primary에 섞지 않는다.
[원본 문맥 보존 결정](../decisions/PAPER1_ORIGINAL_CONTEXT_PRESERVATION_DECISION_V01.md)에 따라
공통 task context와 정답을 암시하는 원문 행동/이유를 구분한다. 학습 supervision의 원본 CoC는
보존하지만 독립 행동 검토자에게 원문 권고를 제공해 일치 여부를 묻는 것으로 gold를 만들지 않는다.
감속/정지/조향/회복의 차이를 없애는 임의 binary label 변환도 endpoint freeze 전에 금지한다.

## 3. CNL fidelity와 독립 검토

M14/M17에서 기존 deterministic CNL renderer의 사용 가능 범위를 확인하고 source EBLC hash,
renderer version, 원 CoC hash, CNL content hash, 검증 결과, 삽입 위치를 example별 연결한다.

필수 보존 항목은 조건·subject/target·의무/금지/부정·논리 범위·수치/unit/frame 및
지원한 release/reactivation/unknown 조건이다. 임의 자연어 재작성으로 검증 내용을 바꾸지 않는다.
수치 근거가 없으면 숫자를 만들지 않고 abstain한다. CNL 역파싱의 byte round-trip만으로
의미보존을 주장하지 않으며 field-level tests와 독립 인간 semantic audit를 함께 사용한다.
중대한 의미 변형이 확인된 renderer/version은 수정·재감사 전 학습 데이터로 배포하지 않는다.
CNL fidelity와 모델이 그 제약을 행동에 사용하는 능력은 다른 평가다.

## 4. 데이터·학습 예산·추론 조건

- [조건부 수용 결정](../decisions/PAPER1_CONDITIONAL_DATA_ADMISSION_DECISION_V01.md)에 따라
  UNKNOWN 보존 사례는 전체 source 확정과 구분해 수용한다. 조건부 개발 수용만으로 본 학습을
  허용하지 않으며, 나머지 main gold/split/provider/budget gate를 모두 적용한다. 원본 CoC 지시를
  관측 사실로 오인하지 않고, confirmed-clear 정상 진입 사례 부족을 불확실성/보류 사례로 대체하지 않는다.

- 고정 24/60/18-cell quota는 1차 선행조건이 아니다. 60/98 기존 검토는 source/development
  자산이며 독립 gold로 자동 승격하지 않는다. 새 task의 eligible 수는 재감사 전 NOT_EVALUATED.
- M17-S01의 train/dev/test group 경계를 상속한다. clip/episode/파생 event/perturbation이
  split을 넘지 않게 하고 pilot과 기계 제안 노출 표본을 test로 재활용하지 않는다.
- N은 learning endpoint의 dev 분산/효과와 정상 행동 비열등성 정밀도로 test 전 동결한다.
  부족하면 INCONCLUSIVE로 보고하며 작은 임의 표본이나 seed 수로 충분성을 대신하지 않는다.
- 최소 3 paired training seeds. 공통 update·batch/sequence·모델 선택 규칙을 고정하고,
  token·FLOPs/GPU-hours 허용 차이를 사전에 정한다. L0의 짧은 supervision 및 L1–L3 길이에
  따른 학습량 차이를 기록한다. 예산이 안 맞으면 matched-budget 결론을 내리지 않는다.
- 학습된 모델은 공통 test 입력에서 평가한다. gold CNL/정답 guard의 외부 공급, verifier,
  reranker, shield는 없다. 모델이 자체 생성하는 CoC는 공통 inference protocol에 명시한다.
- 이미지/영상 hash·frame sampling·resolution·processor/vision encoder version을 고정한다.
  학습 loss가 VLM의 지정 trainable module에 연결되고 parameter가 바뀌었는지 확인한다.
  image token이 실제 입력되는지 검사하고 visually distinguishing dev 사례에서 image 제거/
  교체 진단을 수행한다. 이 진단을 별도 다섯 번째 대규모 학습 arm으로 확대하지 않는다.
- L0–L3 전체 base cohort 결과와 observed/abstained subset을 나눠 coverage·실패를 보고한다.
  generator/compile 실패를 삭제해 유리한 표본만 남기지 않는다.
- with-shield, lifecycle-off, flat 대조 및 preference-only 방법은 2차이며 필수 학습 run을
  자동 확대하지 않는다.

## 5. 독립 행동 평가와 판정

Primary 지표는 독립 판정한 제약 위반률과 nominal task-success다. offline 후보 선택이면
'정상 진행 가능한 행동/궤적을 선택한 비율'이며 실제 goal completion이 아니다. ground truth는
training template/binder/BCV/CNL을 그대로 정답으로 호출하지 않고 독립 source·전문가/별도
reference 계산으로 만든다. always-stop 후보가 안전 점수만 높이지 못하도록 정상 행동 및
불필요 정지를 동시에 측정한다. 단순 기록 trajectory를 안전 정답으로 간주하지 않는다.
점수화 대상은 학습한 VLM이 held-out 이미지/영상에서 실제로 출력한 행동/궤적 선택이다.
CNL 문장 일치율·설명 품질·학습 loss 감소만으로 행동 효과를 입증했다고 하지 않는다.

L3−대조군 차이를 paired scene/episode cluster와 training seed 변동을 반영해 보고한다.

1. 위반률 차이의 95% CI 상한 <0.
2. nominal task-success 차이의 95% CI 하한 ≥−0.05.
3. 대조군별 다중 비교, 효과 크기·coverage·불확실성을 보고.

L3 대 L0은 추가 효용, L3 대 L1은 전체 파이프라인, L3 대 L2는 검증 기여에 해당한다.
C1의 '필요성'은 이 과제의 원본 CoC에서 관측한 위반과 개선에 한정한다.
L0만 이기면 EBLC/검증 방식의 우월성을 주장하지 않는다. rollout ≥2,000/여러 simulator/
long-horizon goal completion은 2차 E4이며 1차의 선행조건이 아니다.

## 6. 산출물과 종료

출력: `artifacts/projects/guardsynth-coc/<class>/guardsynth-eblc-learning-001/<run-id>/`.
기존 run을 덮어쓰지 않는다. 필수 산출물:

- source→EBLC→검증→CNL→학습 example의 hash/provenance 및 split/노출 감사
- CNL field fidelity tests·독립 semantic audit·사용 subset과 실패 보고
- L0–L3 VLM checkpoint 또는 adapter weights·base checkpoint hash·processor/vision 설정
- trainable module/parameter 수·실제 update 확인·학습/compute 로그·seed/budget manifest
- no-shield test의 prediction/독립 verdict, 위반·nominal task-success·CI·coverage
- `RUN_MANIFEST.json`, `RESULT.json`, `REPORT_KO.md`와 비식별 집계

실행·보고는 M20 필수다. 결과는 SUPPORTED/NOT_SUPPORTED/INCONCLUSIVE이며 미실행은
NOT_EVALUATED다. 부정 결과는 정식 완료와 양립하지만 긍정 주장을 허용하지 않는다.
VLM 가중치 학습 또는 이미지/영상 기반 독립 행동 평가가 없으면 M18/M20을 완료하지 않는다.
2026-09-06: CNL supervision builder와 네 arm의 실제 Qwen3-VL-2B 내부 LoRA 업데이트를
synthetic software smoke로 실행했다. 이는 main 학습 데이터 구축이나 효과 실험이 아니다.
원본 CoC 98/98 연결·선택 32개 개발 후보와 smoke 증거는
[실행 보고서](../reports/PAPER1_CNL_LEARNING_READINESS_REPORT_V01.md)에 기록한다.
실제 source-bound provider, 독립 gold/CNL audit, 본 학습·held-out 행동 효과는 미완료다.
