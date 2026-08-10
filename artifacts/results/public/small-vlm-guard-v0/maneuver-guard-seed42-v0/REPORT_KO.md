# 다중 maneuver Safety-Constrained CoC 최소 실험 결과

## 한 줄 결론

작은 VLM의 합성 trajectory 후보 선택 과제에서, 요구사항 중심 CoC에 실행 가드를 함께 학습시키면 `CRUISE→STOP`과 `LANE CHANGE→ABORT/RETRY` 모두에서 가드에 맞는 후보 전환을 학습할 수 있었다. 다만 이것은 실제 차량의 연속 trajectory 생성이나 도로 안전성을 입증한 결과가 아니라, 다음 단계 실험을 진행할 가치가 있다는 feasibility evidence이다.

## 연구 질문

> 동일한 장면과 trajectory 후보가 주어졌을 때, 요구사항 중심 CoC에 빠진 실행 가드를 명시하고 학습하면 가드 위반 후보를 줄이면서 maneuver 목표 완료를 유지하는가?

예를 들어 `보행자 앞에서 정지한 뒤 진행하라`는 요구사항만으로는 정지 위치와 승차감 상한이 정해지지 않는다. Safety-Constrained CoC는 여기에 `정지선을 넘지 말고, 최대 감속과 jerk 상한을 지켜라`를 붙인다. 차선 변경에서는 `최소 간격 미달 시 중단하고 간격 회복 후 재시도하라`를 붙인다.

## 실험 설계

- 기반 모델: Qwen3-VL-2B-Instruct + LoRA
- seed: 42 한 개(최소 feasibility 단계)
- 학습: 192개의 장면, 장면당 permissive/restrictive 계약 2개, 총 384개 예
- 평가: test 48개 장면/96개 예, paraphrase 96개 예, unseen 수치 조합 96개 예
- 동일 장면의 계약만 바꾸면 최적 후보가 바뀌도록 paired-contract로 구성
- 조건: `CoC only`, `Safety-Constrained CoC`, `Shuffled constraint`
- 최적 후보: 가드를 만족하는 목표 완료 후보 중 route progress가 가장 큰 후보
- deadlock은 가드 위반으로 세지 않지만 목표 실패로 별도 집계

## Test 결과

| 조건 | 후보 정확도 | 가드 위반 | 안전한 목표 완료 | 계약 쌍 정확도 | deadlock |
|---|---:|---:|---:|---:|---:|
| CoC only | 50.0% | 25.0% | 75.0% | 0.0% | 0.0% |
| Safety-Constrained CoC | 100.0% | 0.0% | 100.0% | 100.0% | 0.0% |
| Shuffled constraint | 51.0% | 24.0% | 76.0% | 2.1% | 0.0% |

`계약 쌍 정확도`는 동일한 장면의 permissive 계약과 restrictive 계약에서 각각 다른 올바른 후보를 모두 고른 비율이다. 따라서 CoC-only의 50% 후보 정확도는 계약을 이해했다는 뜻이 아니다. 계약 입력이 없어서 쌍의 두 문제에 같은 답을 내고 하나만 맞힌 결과이며, 계약 쌍 정확도는 0%였다.

## Maneuver별 결과

| 조건 | maneuver | 정확도 | 가드 위반 | 안전한 목표 완료 | 계약 쌍 정확도 |
|---|---|---:|---:|---:|---:|
| CoC only | cruise_stop | 50.0% | 25.0% | 75.0% | 0.0% |
| CoC only | lane_change | 50.0% | 25.0% | 75.0% | 0.0% |
| Safety-Constrained CoC | cruise_stop | 100.0% | 0.0% | 100.0% | 100.0% |
| Safety-Constrained CoC | lane_change | 100.0% | 0.0% | 100.0% | 100.0% |
| Shuffled constraint | cruise_stop | 52.1% | 22.9% | 77.1% | 4.2% |
| Shuffled constraint | lane_change | 50.0% | 25.0% | 75.0% | 0.0% |

Safety-Constrained CoC는 두 maneuver에서 모두 가드 위반 0%, 안전한 목표 완료 100%, 계약 쌍 정확도 100%였다. 즉 정지 문제 하나에만 국한된 신호는 아니었다. CoC-only와 shuffled 조건은 모두 lane-change 계약 쌍을 한 번도 완전히 해결하지 못했다.

## 표현·수치 일반화

| 조건 | split | 정확도 | 가드 위반 | 안전한 목표 완료 | 계약 쌍 정확도 |
|---|---|---:|---:|---:|---:|
| CoC only | paraphrase | 50.0% | 25.0% | 75.0% | 0.0% |
| CoC only | unseen | 50.0% | 25.0% | 75.0% | 0.0% |
| Safety-Constrained CoC | paraphrase | 100.0% | 0.0% | 100.0% | 100.0% |
| Safety-Constrained CoC | unseen | 100.0% | 0.0% | 100.0% | 100.0% |
| Shuffled constraint | paraphrase | 57.3% | 17.7% | 82.3% | 14.6% |
| Shuffled constraint | unseen | 55.2% | 19.8% | 80.2% | 10.4% |

Safety-Constrained CoC는 바꿔 쓴 제약 문장과 학습에 없던 경계값 조합에서도 모든 예를 맞혔다. Shuffled constraint는 test 계약 쌍 정확도 2.1%에 그쳐, 제약 문장이 단순히 더 많은 토큰이나 maneuver 힌트를 제공해서 생긴 결과라는 설명과 맞지 않는다.

## 사전 성공 기준

- PASS — `inline_test_guard_violation_rate_max_0.10`
- PASS — `inline_test_safe_goal_completion_rate_min_0.85`
- PASS — `inline_test_contract_swap_pair_accuracy_min_0.75`
- PASS — `inline_minus_coc_violation_reduction_min_0.20`
- PASS — `inline_minus_shuffled_pair_accuracy_gain_min_0.20`
- PASS — `inline_each_maneuver_safe_goal_completion_rate_min_0.80`
- PASS — `inline_unseen_safe_goal_completion_rate_min_0.65`

총 7/7개 기준을 통과했다.

## 해석 가능한 범위

이 실험이 지지하는 주장은 제한적이다. 작은 VLM은 명시적인 자연어 가드와 가드별 감독 신호를 받으면, 요구사항만으로는 식별할 수 없는 trajectory 후보 선택을 가드 의미에 맞게 바꿀 수 있었다. 또한 안전성과 목표 완료를 함께 최적화할 수 있어, 단순히 항상 정지하는 보수적 정책을 배운 것은 아니다.

아직 지지하지 않는 주장은 다음과 같다.

- 실제 Alpamayo-R1이 연속 trajectory를 같은 방식으로 생성한다.
- 실제 센서 잡음, 객체 누락, 장면 분포 이동에서도 가드가 유효하다.
- 자연어 가드가 완전하거나 정형 명세보다 본질적으로 우월하다.
- collision 또는 실제 도로 위험이 감소한다.
- seed 변화에도 동일한 효과 크기가 유지된다.

## 바로 다음 최소 단계

1. 동일한 세 조건을 seed 17과 123에서 반복하여 평균·표준편차와 bootstrap 신뢰구간을 계산한다.
2. 경계값 근처의 hard case와 숫자 단위/부정 표현을 추가해 100%가 템플릿 학습 때문인지 공격적으로 검사한다.
3. 그 뒤에만 실제 Alpamayo 후보 trajectory를 이 검증 틀에 연결한다. 실제 차량 safety claim은 별도의 trajectory/VRU metric 없이 하지 않는다.

## 재현 파일

- 세계/데이터: `experiments/vlm_guard_learning/maneuver_guard_world.py`
- 학습/평가: `experiments/vlm_guard_learning/train_qwen_maneuver_guard_lora.py`
- 단위 테스트: `experiments/vlm_guard_learning/test_maneuver_guard_world.py`
- 기계 판독 요약: `summary.json`
