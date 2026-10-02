# 통제 temporal 효과 보존 비교

- project_id: `guardsynth-coc`
- protocol: `paper1-method-preservation-v0.1`
- Project01 generator/시각 collator/LoRA trainer를 읽기 전용으로 재사용한 신규 Project04 결과.
- P1/P2는 학습·추론 모두 CoC 안에 제약을 제공한다. 실제 도로 자동 추출/무제약 추론 시험이 아니다.
- 기존 benchmark와 새 seed 표본 모두 반복 template 평가이며 독립 새 환경으로 세지 않는다.

실제 checkpoint 9개, optimizer updates 합계 648. 각 adapter/loss/raw prediction은 학습 run에 보존된다.

## benchmark_regression

고유 semantic template clusters: 12. 각 seed/arm 48 생성 장면·96 판단; seed를 독립 환경으로 세지 않는다.

| 조건 | 위반 | 안전 완료 | 불필요 정지(deadlock) | 정확도 | coverage | 계약쌍 정확도 |
|---|---:|---:|---:|---:|---:|---:|
| P0 | 0.3194 | 0.6806 | 0.0000 | 0.5000 | 1.0000 | 0.0000 |
| P1 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| P2 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |

P2의 paired 차이와 template-cluster bootstrap 95% 구간:
- P2-P0 guard_violation_rate: -0.3194 [-0.4448, -0.1903]
- P2-P0 safe_goal_completion_rate: 0.3194 [0.1903, 0.4448]
- P2-P1 guard_violation_rate: 0.0000 [0.0000, 0.0000]
- P2-P1 safe_goal_completion_rate: 0.0000 [0.0000, 0.0000]

사전 고정 point criteria: **SUPPORTED_ON_REUSED_TEMPLATES**.
각 seed별 P1/P2 수준, P2-P0 개선, P2-P1 허용 열화를 모두 검사했다.
formal 비열등성/동등성 또는 새로운 시각 환경 일반화는 입증하지 않았다.

## new_seed_confirmation

고유 semantic template clusters: 12. 각 seed/arm 48 생성 장면·96 판단; seed를 독립 환경으로 세지 않는다.

| 조건 | 위반 | 안전 완료 | 불필요 정지(deadlock) | 정확도 | coverage | 계약쌍 정확도 |
|---|---:|---:|---:|---:|---:|---:|
| P0 | 0.3160 | 0.6840 | 0.0000 | 0.5000 | 1.0000 | 0.0000 |
| P1 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |
| P2 | 0.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 1.0000 |

P2의 paired 차이와 template-cluster bootstrap 95% 구간:
- P2-P0 guard_violation_rate: -0.3160 [-0.4348, -0.1832]
- P2-P0 safe_goal_completion_rate: 0.3160 [0.1832, 0.4348]
- P2-P1 guard_violation_rate: 0.0000 [0.0000, 0.0000]
- P2-P1 safe_goal_completion_rate: 0.0000 [0.0000, 0.0000]

사전 고정 point criteria: **SUPPORTED_ON_REUSED_TEMPLATES**.
각 seed별 P1/P2 수준, P2-P0 개선, P2-P1 허용 열화를 모두 검사했다.
formal 비열등성/동등성 또는 새로운 시각 환경 일반화는 입증하지 않았다.

## unseen_time

고유 semantic template clusters: 12. 각 seed/arm 48 생성 장면·96 판단; seed를 독립 환경으로 세지 않는다.

| 조건 | 위반 | 안전 완료 | 불필요 정지(deadlock) | 정확도 | coverage | 계약쌍 정확도 |
|---|---:|---:|---:|---:|---:|---:|
| P0 | 0.3750 | 0.6250 | 0.0000 | 0.5000 | 1.0000 | 0.0000 |
| P1 | 0.3611 | 0.6389 | 0.0000 | 0.6250 | 1.0000 | 0.2778 |
| P2 | 0.0000 | 1.0000 | 0.0000 | 0.8993 | 1.0000 | 0.7986 |

P2의 paired 차이와 template-cluster bootstrap 95% 구간:
- P2-P0 guard_violation_rate: -0.3750 [-0.4537, -0.2889]
- P2-P0 safe_goal_completion_rate: 0.3750 [0.2889, 0.4537]
- P2-P1 guard_violation_rate: -0.3611 [-0.4843, -0.2175]
- P2-P1 safe_goal_completion_rate: 0.3611 [0.2175, 0.4843]

## 해석 한계

표준3·unseen3의 총6 storyboard만 존재한다. 좁은 template 재사용 연구이며 CI도 이 조건부 범위다.
CoC 원문과 정답은 변경하지 않았다. 제약은 supplied source duration에서 생성하며 ACTION 정답에서 역생성하지 않았다.
Core는 한 번의 clear 전환 아래 진입 시간 허용성을 검증한다. 전체 차량 운동/재점유/시각 grounding을 인증하지 않는다.
원 Project01 평균 .319/.000 위반 및 .681/1.000 안전 완료는 역사적 참조이며 이 신규 결과로 재표기하지 않는다.
원 unseen-time .625/.649 안전 완료 한계는 보존한다. 새 unseen 결과와 별도로 해석한다.
본 run에는 LLM 확장 라벨/추가 인간 설문이 없으며 실제 도로 gate나 원답을 변경하지 않았다.
