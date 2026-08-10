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

전체: 3/4 criteria 통과.

이 실험은 합성 이미지에서 행동 prototype을 선택하는 학습 실험이다. 연속 궤적이나 실제 도로 안전 결과가 아니다.
