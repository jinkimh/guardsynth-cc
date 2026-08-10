# 다중 maneuver Safety-Constrained CoC 3-seed 및 hard-test 결과

## 결론

Safety-Constrained CoC의 표준 test 효과는 seed 42, 17, 123 모두에서 재현됐다. 세 seed 모두 가드 위반 0, 안전한 목표 완료 1.0, 계약 쌍 정확도 1.0이었다. 부정 표현, 경계값, 조건 순서 변경 및 단위 변환을 결합한 hard test에서는 성능이 낮아졌지만, requirement-only와 shuffled 통제보다 큰 차이를 유지했다.

## 표준 test: 3-seed 평균 ± 표본 표준편차

| 조건 | 정확도 | 가드 위반 ↓ | 안전한 목표 완료 ↑ | 계약 쌍 정확도 ↑ | deadlock ↓ |
|---|---:|---:|---:|---:|---:|
| Requirement CoC | 0.500 ± 0.000 | 0.292 ± 0.072 | 0.708 ± 0.072 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| Safety-Constrained CoC | 1.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 | 0.000 ± 0.000 |
| Shuffled constraint | 0.503 ± 0.006 | 0.267 ± 0.039 | 0.733 ± 0.039 | 0.028 ± 0.032 | 0.000 ± 0.000 |

표준 test에서 Safety-Constrained CoC는 requirement-only보다 가드 위반을 평균 0.292 줄였고, shuffled보다 계약 쌍 정확도를 평균 0.972 높였다.

## Hard test: 3-seed 평균 ± 표본 표준편차

Hard test는 학습에서 보지 않은 네 가지 변형을 결합했다: 허용 경계와 정확히 같은 값, 부정ㆍ금지형 문장, 절 순서 변경, m에서 cm로의 단위 변환.

| 조건 | 정확도 | 가드 위반 ↓ | 안전한 목표 완료 ↑ | 계약 쌍 정확도 ↑ | deadlock ↓ |
|---|---:|---:|---:|---:|---:|
| Requirement CoC | 0.500 ± 0.000 | 0.302 ± 0.065 | 0.698 ± 0.065 | 0.000 ± 0.000 | 0.000 ± 0.000 |
| Safety-Constrained CoC | 0.948 ± 0.063 | 0.010 ± 0.010 | 0.990 ± 0.010 | 0.896 ± 0.127 | 0.000 ± 0.000 |
| Shuffled constraint | 0.535 ± 0.079 | 0.260 ± 0.018 | 0.740 ± 0.018 | 0.090 ± 0.139 | 0.000 ± 0.000 |

### Safety-Constrained CoC의 seed별 hard 결과

| seed | 정확도 | 가드 위반 | 안전한 목표 완료 | 계약 쌍 정확도 |
|---:|---:|---:|---:|---:|
| 42 | 87.5% | 0.0% | 100.0% | 75.0% |
| 17 | 99.0% | 1.0% | 99.0% | 97.9% |
| 123 | 97.9% | 2.1% | 97.9% | 95.8% |

seed 42에서는 정확도 87.5%와 계약 쌍 75.0%로 하락했지만 가드 위반은 0%이고 안전한 목표 완료는 100%였다. 이는 일부 문제에서 progress-optimal 후보 대신 더 보수적인 허용 후보를 선택했음을 뜻한다. seed 17과 123에서는 소수의 실제 위반이 각각 1.0%, 2.1% 발생했다.

## Hard test의 maneuver별 결과

| 조건 | maneuver | 정확도 | 가드 위반 | 안전한 목표 완료 | 계약 쌍 정확도 |
|---|---|---:|---:|---:|---:|
| Requirement CoC | cruise_stop | 0.500 | 0.340 | 0.660 | 0.000 |
| Requirement CoC | lane_change | 0.500 | 0.264 | 0.736 | 0.000 |
| Safety-Constrained CoC | cruise_stop | 0.979 | 0.021 | 0.979 | 0.958 |
| Safety-Constrained CoC | lane_change | 0.917 | 0.000 | 1.000 | 0.833 |
| Shuffled constraint | cruise_stop | 0.486 | 0.271 | 0.729 | 0.014 |
| Shuffled constraint | lane_change | 0.583 | 0.250 | 0.750 | 0.167 |

## Hard 오류의 위치

Safety-Constrained CoC의 오답 15개는 모두 `m ↔ cm` 단위 변환 문장에서 발생했다. seed 42의 12개는 lane-change에서 가드를 만족하지만 progress가 낮은 보수적 후보를 고른 오류였고, seed 17의 1개와 seed 123의 2개는 cruise-stop의 감속ㆍjerk 상한을 실제로 위반한 선택이었다. 이번 결합 test에서는 부정 scope, 절 순서 변경 및 m 단위 경계 equality만 포함한 예에서 오답이 없었다. 다만 각 요인을 독립적으로 무작위화한 factorial test가 아니므로, 단위 변환만이 유일한 원인이라고 확정하지는 않는다.

## Bootstrap 대비 효과

seed를 cluster로 간주하여 20,000회 재표집했다. seed가 세 개뿐이므로 신뢰구간은 탐색적이며 모집단 수준의 강한 추론으로 해석하지 않는다.

| 비교 | split | 평균 차이 | seed-cluster bootstrap 95% CI |
|---|---|---:|---:|
| 위반 감소: Requirement - Safety-Constrained | test | 0.292 | [0.250, 0.375] |
| 계약 쌍 증가: Safety-Constrained - Shuffled | test | 0.972 | [0.938, 1.000] |
| 위반 감소: Requirement - Safety-Constrained | hard | 0.292 | [0.250, 0.354] |
| 계약 쌍 증가: Safety-Constrained - Shuffled | hard | 0.806 | [0.500, 0.979] |

## 연구적으로 의미하는 것

1. 표준 실험의 효과는 특정 초기화 한 번의 우연으로 보이지 않는다.
2. shuffled 통제가 지속적으로 낮아, constraint와 감독 target의 올바른 대응 관계가 필요했다.
3. hard test는 자연어 가드 학습이 완전히 해결된 문제가 아님을 보여준다. 특히 복합적인 표면형과 수치 표현에서 progress-optimal 선택과 일부 compliance가 흔들린다.
4. 그럼에도 hard test 평균에서 Safety-Constrained CoC는 requirement-only보다 위반을 크게 줄이고 목표 완료를 높였다.

## 주장 한계

이 결과는 합성 이미지와 서술된 후보를 사용하는 작은 VLM의 **가드 조건부 후보 선택 학습 가능성**을 보여준다. 실제 연속 trajectory 생성, 실제 센서 grounding, collision 감소 또는 Alpamayo-R1 수준의 일반화는 아직 증명하지 않는다.

## 다음 실험 우선순위

1. hard-test 오류를 단위 변환, 부정 scope, 경계 equality, conjunction별로 분리하는 factorial 평가
2. 학습 장면과 물리 후보 값을 더 연속화하여 템플릿 shortcut 제거
3. 자연어 가드와 구조화/logic guard의 동일 supervision 비교
4. 실제 Alpamayo 후보 trajectory에 독립 verifier를 연결한 외적 타당성 평가
