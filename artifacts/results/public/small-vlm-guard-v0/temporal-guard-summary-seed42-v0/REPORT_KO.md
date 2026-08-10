# STOP–HOLD–RELEASE–GO 시간적 Guard 실험

- 모델: `Qwen/Qwen3-VL-2B-Instruct` (LoRA)
- 학습 장면: 192개, 장면당 short/long release 계약 2개
- 보행자 conflict zone이 clear가 된 시점은 storyboard 이미지에서 판독한다.
- 후보: 점유 중 조기 진입, 짧은 대기 후 출발, 긴 대기 후 출발, horizon 내 계속 정지.

## Held-out

| 조건 | 정확도 | Guard 위반 ↓ | Hold 위반 ↓ | Deadlock ↓ | 안전+목표완료 ↑ | 계약전환 pair ↑ |
|---|---:|---:|---:|---:|---:|---:|
| R1-like requirement CoC | 0.500 | 0.375 | 0.000 | 0.000 | 0.625 | 0.000 |
| Temporal constraint inside CoC | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| CoC + natural temporal guard | 0.698 | 0.302 | 0.000 | 0.000 | 0.698 | 0.396 |
| CoC + shuffled guard | 0.531 | 0.344 | 0.000 | 0.000 | 0.656 | 0.062 |
| CoC + temporal logic guard | 0.552 | 0.323 | 0.000 | 0.000 | 0.677 | 0.104 |

## 일반화

| 조건 | Paraphrase 정확도 | Paraphrase safe-goal | Unseen-time 정확도 | Unseen-time safe-goal |
|---|---:|---:|---:|---:|
| R1-like requirement CoC | 0.500 | 0.625 | 0.500 | 0.625 |
| Temporal constraint inside CoC | 0.823 | 0.906 | 0.625 | 0.625 |
| CoC + natural temporal guard | 0.625 | 0.719 | 0.500 | 0.500 |
| CoC + shuffled guard | 0.417 | 0.667 | 0.458 | 0.656 |
| CoC + temporal logic guard | 0.531 | 0.656 | 0.500 | 0.625 |

## 사전 판정

- FAIL: `natural_violation_at_most_0p10`
- PASS: `natural_deadlock_at_most_0p10`
- FAIL: `natural_safe_goal_at_least_0p85`
- FAIL: `natural_swap_pair_at_least_0p80`
- PASS: `natural_beats_shuffled_pair_by_0p20`
- FAIL: `unseen_natural_safe_goal_at_least_0p70`

## 해석 제한

- requirement-only CoC에는 release 안정시간이 없으므로 계약쌍을 구분할 수 없다. 이 대조는 정보 누락 효과를 측정한다.
- rich CoC와 별도 guard는 같은 정보를 받는다. 두 조건의 차이만이 표현 구조 효과에 해당한다.
- 자연어 guard는 short 계약은 1.000이지만 long 계약은 0.396이었다. Guard 존재 자체는 인식했으나 더 긴 release 대기로 충분히 전환하지 못했다.
- 자연어 guard의 계약전환 pair는 shuffled보다 0.333 높아 의미 신호는 있으나, 사전 기준 0.800에는 크게 미달한다.
- rich CoC의 1.000과 별도 guard의 격차는 단일 seed 결과다. 입력 위치 효과인지 안정적인 표현 효과인지 다중 seed 없이는 구분할 수 없다.
- 계속 정지는 guard 위반은 아니지만 운전 목표 실패이므로 deadlock 및 safe-goal 지표로 벌점 처리했다.
- 합성 storyboard와 후보 선택 결과이며 연속 제어 또는 실제 도로 안전 증거는 아니다.

전체: 2/6 criteria 통과.
