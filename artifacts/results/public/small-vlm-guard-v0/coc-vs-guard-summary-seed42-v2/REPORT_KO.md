# 전통적 CoC 대 자연어 safety guard 최소 실험

- 모델: `Qwen/Qwen3-VL-2B-Instruct`
- 동일 이미지, target, seed, LoRA 설정 사용
- 전통적 CoC: 객체별 행동 요구사항
- CoC+Guard: 동일 CoC + hold/release 경계

| 학습 규모 | 조건 | Held-out 정확도 | Counterfactual 전환 완전 정답률 | STOP recall | PROCEED recall | Paraphrase 정확도 |
|---|---|---:|---:|---:|---:|---:|
| 24 scenes | Traditional CoC | 0.781 | 0.208 | 0.719 | 0.844 | 0.766 |
| 24 scenes | CoC + Guard | 0.500 | 0.000 | 1.000 | 0.000 | 0.500 |
| 192 scenes | Traditional CoC | 0.974 | 0.896 | 0.948 | 1.000 | 0.906 |
| 192 scenes | CoC + Guard | 1.000 | 1.000 | 1.000 | 1.000 | 0.984 |

## Guard − CoC

- 24 scenes: accuracy -0.281, counterfactual -0.208, paraphrase -0.266
- 192 scenes: accuracy +0.026, counterfactual +0.104, paraphrase +0.078

## 사전 정의 판정

- FAIL: `low_data_sample_efficiency_signal`
- PASS: `full_data_guard_not_worse_by_more_than_0p02`
- PASS: `full_guard_stop_recall_at_least_0p80`
- PASS: `full_guard_proceed_recall_at_least_0p80`

## 사후 equal-step 진단

24개 장면 조건의 optimizer update 부족을 분리하기 위해 두 조건을 각각 16 epoch, 총 80 optimizer step으로 재학습했다.

| 조건 | Held-out 정확도 | Counterfactual 완전 정답률 | STOP recall | PROCEED recall | Paraphrase 정확도 |
|---|---:|---:|---:|---:|---:|
| Traditional CoC | 1.000 | 1.000 | 1.000 | 1.000 | 0.984 |
| CoC + Guard | 1.000 | 1.000 | 1.000 | 1.000 | 0.938 |

두 조건 모두 ID 정확도와 counterfactual 전환에서 1.000에 도달했다. 따라서 초기 저데이터 가드 모델의 always-STOP은 데이터 표현의 본질적 실패가 아니라 update 부족이었다.

## 종합 해석

- 가드를 추가해도 충분한 학습 후 hold와 release를 모두 정확히 학습할 수 있다.
- 그러나 이 단순 benchmark에서는 전통 CoC 모델도 같은 supervision으로 규칙을 암묵적으로 학습해 동일한 성능에 도달한다.
- 192-scene 2-epoch에서 보인 가드의 작은 우위는 equal-step 진단에서 재현되지 않아, 현재로서는 가드 자체의 우위라고 주장할 수 없다.
- 가드의 추가 가치를 보이려면 성공 시연만으로 경계가 식별되지 않는 re-hold, 수치 상·하한, 복수의 admissible trajectory 같은 과제가 필요하다.

전체: 3/4 criteria 통과.

이 실험은 합성 이미지에서 행동 prototype을 선택하는 학습 실험이다. 연속 궤적이나 실제 도로 안전 결과가 아니다.
