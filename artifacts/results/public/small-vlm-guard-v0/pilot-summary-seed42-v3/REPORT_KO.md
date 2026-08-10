# 작은 VLM 가드 학습 최소 실험

- 모델: `Qwen/Qwen3-VL-2B-Instruct`
- 조건별 학습 예: 576개
- 학습: 2 epoch, LoRA
- 출력: 연속 궤적이 아니라 `STOP/PROCEED` trajectory prototype

| 지표 | 올바른 가드 pair 학습 | 가드 pair 셔플 통제 |
|---|---:|---:|
| 학습하지 않은 장면 정확도 | 0.990 | 0.719 |
| 장면별 counterfactual 가드 전환 완전 정답률 | 0.958 | 0.000 |
| 학습하지 않은 paraphrase 정확도 | 0.740 | 0.745 |
| paraphrase 장면별 완전 정답률 | 0.000 | 0.000 |
| STOP 선택률 | 0.490 | 0.406 |

## 판정

- 올바른 pair의 held-out 이득: +0.271
- 올바른 가드 학습은 동일 장면에서 가드가 바뀔 때 STOP/PROCEED를 함께 바꾸는 능력을 학습했다.
- 셔플 통제군은 개별 정확도가 일부 상승했지만 counterfactual 장면 완전 정답률은 0이었다.
- 따라서 in-distribution 자연어 가드와 trajectory prototype의 정렬은 작은 VLM에서 학습 가능하다는 feasibility evidence가 있다.

## 중요한 한계

- paraphrase 정확도 차이는 -0.005으로 올바른 pair의 우위가 없었다.
- 올바른 모델도 paraphrase counterfactual 장면 완전 정답률은 0이므로, 새로운 표현으로 가드가 바뀔 때 안정적으로 행동을 전환하지 못했다.
- 현재 출력은 두 개의 행동 prototype이며 연속 궤적, 정량 상·하한 또는 실제 도로 안전을 검증하지 않았다.
- 다음 단계는 다양한 paraphrase로 학습한 뒤 완전히 새로운 표현에 재평가하고, 성공한 경우 CREEP·감속·차선변경 prototype과 정량 bound로 확장하는 것이다.
