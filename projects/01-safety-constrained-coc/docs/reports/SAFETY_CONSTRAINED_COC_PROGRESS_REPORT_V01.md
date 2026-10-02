# Safety-Constrained CoC 연구 진행 종합 보고서 v1

- 작성일: 2026-08-04
- 대상 모델: NVIDIA Alpamayo-R1-10B, Qwen3-VL-2B-Instruct
- 연구 단계: 문제 정의 및 합성 feasibility 검증
- 핵심 질문: 요구사항 중심 CoC에 명시적 안전 제약을 추가하고 학습하면, VLM이 운전 목표를 유지하면서 제약 위반 trajectory를 줄일 수 있는가?

## 1. 요약

Alpamayo-R1의 Chain-of-Causation(CoC)은 장면 인식, 판단, 행동과 예측 trajectory 사이에 자연어 추론 인터페이스를 제공한다. 그러나 “보행자에게 양보한다”, “교차로를 통과한다”와 같은 행동 요구사항만으로는 허용 가능한 trajectory 집합이 완전히 정해지지 않는다. 정지선, 속도 상한, 최소 여유거리, hold 조건, release 안정시간 및 불확실성 fallback과 같은 제약이 추가로 필요할 수 있다.

실제 R1 결과 분석에서는 명백한 CoC grounding 오류나 사고 반례를 쉽게 찾지 못했고, 단일 장면의 STOP/YIELD 문구와 속도만 비교하는 검증은 temporal phase를 무시해 오판하기 쉬웠다. R1에 Guard 문장을 zero-shot으로 삽입하면 trajectory는 변했지만 의미에 특이적인 변화는 매우 작았다. 따라서 연구 초점은 “기존 CoC 오류 검출”에서 “요구사항과 제약사항을 함께 갖는 Safety-Constrained CoC의 학습 및 검증”으로 이동했다.

작은 VLM 합성 실험에서는 다음을 확인했다.

1. 자연어 Guard와 행동 prototype의 대응은 학습 가능했다.
2. 단순 STOP/PROCEED 문제에서는 전통적 CoC도 같은 supervision을 통해 규칙을 암묵적으로 배웠으므로 Guard의 고유한 이점이 드러나지 않았다.
3. CoC 목표를 달성하지만 현재 제약을 위반하는 hard-negative trajectory를 포함하자, 명시적 제약을 받은 모델의 위반 선택이 크게 감소했다.
4. 시간적 STOP–HOLD–RELEASE–GO 문제에서는 제약을 CoC 내부에 자연어로 넣은 조건이 완벽하게 학습됐으나, 별도 자연어 Guard와 임의 Logic Guard는 충분히 학습되지 않았다.

현재 가장 강하게 지지되는 결론은 다음과 같다.

> 합성 환경에서 VLM을 CoC와 명시적 자연어 안전 제약으로 함께 학습하면, 요구사항만 학습한 경우보다 목표를 달성하면서 명시된 제약을 준수하는 trajectory를 더 잘 선택할 수 있다. 단, 효과는 제약의 위치ㆍ형식과 학습 방법에 민감하다.

이는 실제 도로 안전이나 Alpamayo-R1의 사고율 감소를 증명한 결과가 아니다.

## 2. 문제 정의의 변화

### 2.1 초기 문제

초기 연구는 실제 R1이 생성한 CoC를 센서 증거와 trajectory에 grounding하고 논리적 모순, reasoning–action 불일치 및 unsafe trajectory를 자동 검출하는 것을 목표로 했다. 그러나 다음 문제가 확인됐다.

- 객체 환각과 CoC–trajectory 불일치는 관련 선행연구와 상당 부분 중복될 가능성이 높다.
- 실제 사고 trajectory는 안전 데이터셋에서 거의 기대할 수 없다.
- 사고가 없었던 인간 시연은 가능한 미래 전체에 대한 안전 보증이 아니다.
- 단일 inference horizon의 속도 변화는 이전ㆍ다음 장면을 보지 않으면 STOP/YIELD 위반으로 확정할 수 없다.
- 실제 영상 grounding gold set과 정교한 재현 시뮬레이션을 대규모로 구축하는 비용이 매우 크다.

### 2.2 현재 문제

CoC는 선택한 행동의 이유를 설명할 수 있지만, “하면 안 되는 것”과 “언제까지 유지하고 언제 해제할 수 있는지”를 항상 명시하지 않는다. 따라서 현재 연구는 CoC를 다음 두 부분으로 본다.

```text
Requirement: 무엇을 달성할 것인가
Constraint:  어떤 조건ㆍ경계 안에서 달성해야 하는가
```

예시는 다음과 같다.

```text
Requirement CoC:
  보행자에게 양보한 뒤 교차로를 통과한다.

Constraint:
  보행자가 conflict zone에 있는 동안 정지선을 넘지 않는다.
  conflict zone이 1.5초 동안 연속으로 clear인 이후에만 출발한다.
```

이 구조를 본 보고서에서는 **Safety-Constrained CoC**라고 부른다.

## 3. Guard의 의미 구조

Guard는 단순 금지문만을 의미하지 않는다. maneuver별로 다음 필드를 가질 수 있다.

```text
ACTIVATION:  Guard가 활성화되는 조건
INVARIANT:   활성화 중 유지해야 하는 상태
BOUND:       속도ㆍ거리ㆍ가속도ㆍjerk의 상한과 하한
PROHIBITION: 절대 허용하지 않는 행동 또는 영역
RELEASE:     다음 행동을 허용하는 조건과 안정시간
FALLBACK:    관측이 불확실하거나 조건이 깨질 때의 행동
TERMINATION: maneuver 완료 조건
```

대표 maneuver는 다음과 같다.

- 주행 유지: 속도 범위, 차간거리, 차로 corridor
- 주행 중 정지: 정지선, conflict zone, 감속도 및 jerk
- 정지 후 출발: hold, clear stability, release, 출발 가속도
- 차선 변경: gap activation, 측면거리 invariant, abort/re-entry
- Yield 후 진입: conflict occupancy, TTC, gap acceptance, uncertainty fallback

## 4. 실제 Alpamayo-R1 분석

### 4.1 Grounding 및 phase-aware 검토

사람이 검토한 제한된 장면에서는 언급 객체와 공간ㆍ상호작용 관계가 대체로 영상에서 지지됐다. 명백한 객체 환각이나 CoC grounding 오류를 연구 출발점으로 삼을 만큼 빈번하게 발견하지 못했다.

STOP/YIELD 관련 장면에서 속도가 증가하는 사례가 있었지만, 다음 이유로 곧바로 위반이라고 결론 낼 수 없었다.

- 이전 horizon에서 이미 정지 의무를 수행했을 수 있다.
- 현재 horizon이 release 이후 phase일 수 있다.
- 다음 inference step에서 다시 정지 trajectory로 전환할 수 있다.
- 사람의 미래 이동을 예상한 조기 출발일 수 있으며, 실제 충돌은 없었다.

따라서 “CoC에 STOP/YIELD가 있고 속도가 감소했는가”만 보는 검증은 construct validity가 부족하다.

### 4.2 R1 Guard semantic contrast

실제 R1 추론에서 동일한 CoC에 hold Guard, 반대 의미 Guard 및 무관한 문장을 self-splice했다.

- 기본 CoC 대비 문장 추가에 따른 2초 trajectory 변화: 약 +0.263 m
- hold와 반대 Guard 차이: 약 0.008 m
- hold와 무관한 Guard 차이: 약 0.016 m

판정은 `WEAK_DIRECTIONAL_NOT_SEMANTICALLY_SPECIFIC`이었다. 즉, 추가 문장은 trajectory에 영향을 주지만 Guard 의미에 맞는 안정적인 zero-shot 제어라고 볼 수 없었다.

상세 결과: `artifacts/results/restricted/alp-exp-006/guard-semantic-summary-v2/REPORT_KO.md`

## 5. 작은 VLM feasibility 실험

모든 실험은 `Qwen/Qwen3-VL-2B-Instruct`에 LoRA를 적용했다. 이 단계의 목적은 실제 도로 안전 증명이 아니라 Guard 의미 학습 가능성 및 평가 설계 검증이다.

### 5.1 Guard-to-action prototype 학습

동일 교차로 이미지에 횡단 차량, 보행자, 신호등 Guard를 바꾸어 STOP 또는 PROCEED를 선택하게 했다.

| 조건 | Held-out 정확도 | 동일 장면 counterfactual 완전 정답률 |
|---|---:|---:|
| 올바른 Guard | 0.990 | 0.958 |
| Shuffled Guard | 0.719 | 0.000 |

자연어 Guard–행동 대응은 학습 가능했다. 그러나 unseen paraphrase 정확도는 두 조건 모두 약 0.74였고 counterfactual 일반화는 0이어서 표현 일반화는 확립되지 않았다.

상세 결과: `artifacts/results/public/small-vlm-guard-v0/pilot-summary-seed42-v3/REPORT_KO.md`

### 5.2 전통적 CoC 대 CoC+Guard

객체별 CoC와 동일 CoC에 hold/release Guard를 추가한 조건을 비교했다. 충분한 optimizer update를 주자 두 조건 모두 held-out 및 counterfactual 정확도 1.000에 도달했다.

이 단순 과제에서는 전통적 CoC 모델도 dense state–action label에서 규칙을 암묵적으로 배울 수 있었다. 따라서 STOP/PROCEED 최종 label만으로 Guard의 추가 가치를 주장할 수 없었다.

상세 결과: `artifacts/results/public/small-vlm-guard-v0/coc-vs-guard-summary-seed42-v2/REPORT_KO.md`

### 5.3 목표 충족 후보 내부의 Guard 위반 선택

모든 후보가 “교차로 통과”라는 CoC 목표를 달성하지만 속도, 최소거리 또는 진입시간 제약을 일부 후보만 위반하도록 설계했다. 모델은 admissible 후보 중 진행도가 가장 큰 후보를 골랐다.

| 조건 | 정확도 | 위반 후보 선택률 ↓ | 계약 전환 pair ↑ |
|---|---:|---:|---:|
| 요구사항 CoC만 | 0.500 | 0.500 | 0.000 |
| 자연어 제약을 CoC 내부에 포함 | 1.000 | 0.000 | 1.000 |
| CoC + 별도 자연어 Guard | 0.993 | 0.014 | 0.986 |
| Shuffled Guard | 0.465 | 0.375 | 0.153 |
| CoC + Logic Guard | 1.000 | 0.000 | 1.000 |

자연어 Guard는 paraphrase 정확도 0.924, unseen-value 정확도 0.951을 기록했다. 이 결과는 명시적 제약 정보가 CoC 목표를 만족하지만 현재 허용조건을 위반하는 hard negative를 구별하는 데 유용함을 보였다.

단, 요구사항 CoC만 주어진 조건은 현재 계약 정보를 받지 못하므로 동일 입력의 상충 정답을 원리적으로 구분할 수 없다. 이는 CoC가 해롭다는 증거가 아니라 명세 정보 누락 대조군이다.

상세 결과: `artifacts/results/public/small-vlm-guard-v0/candidate-guard-summary-seed42-v0/REPORT_KO.md`

### 5.4 STOP–HOLD–RELEASE–GO 시간적 Guard

Storyboard 이미지에서 보행자 conflict zone이 clear가 되는 시점을 읽고 다음 후보 중 하나를 선택하게 했다.

- 점유 중 조기 진입
- 짧은 clear 유지 후 출발
- 긴 clear 유지 후 출발
- horizon 내 계속 정지

동일 장면에 short/long release 계약을 적용해 정답이 바뀌도록 했다.

| 조건 | 정확도 | Guard 위반률 ↓ | 안전+목표 완료 ↑ | 계약 전환 pair ↑ |
|---|---:|---:|---:|---:|
| 요구사항 CoC | 0.500 | 0.375 | 0.625 | 0.000 |
| 자연어 제약을 CoC 내부에 포함 | 1.000 | 0.000 | 1.000 | 1.000 |
| CoC + 별도 자연어 Guard | 0.698 | 0.302 | 0.698 | 0.396 |
| Shuffled Guard | 0.531 | 0.344 | 0.656 | 0.062 |
| CoC + Logic Guard | 0.552 | 0.323 | 0.677 | 0.104 |

별도 자연어 Guard는 short 계약 정확도 1.000, long 계약 0.396이었다. Guard 의미 신호는 shuffled보다 컸지만 더 긴 release 대기로 충분히 전환하지 못했다. Logic Guard도 기반 모델이 임의 논리 문법 실행에 익숙하지 않아 충분히 학습되지 않은 것으로 추정된다.

반면 자연어 제약을 일반적인 CoC 지시문 안에 넣은 조건은 완벽하게 학습됐다. 이는 별도 Guard가 본질적으로 열등하다는 증거가 아니다. 정보 위치, 형식 친숙도, 제한된 LoRA update 및 단일 seed 효과를 분리해야 한다.

상세 결과: `artifacts/results/public/small-vlm-guard-v0/temporal-guard-summary-seed42-v0/REPORT_KO.md`

### 5.5 시간적 Guard 3-seed 재현

단일 seed의 optimization variance를 확인하기 위해 seeds 42, 17, 123에서 동일한 192개 학습 장면, 3 epoch, 72 optimizer update로 다섯 조건을 반복했다.

| 조건 | 정확도 | Guard 위반률 ↓ | 안전+목표 완료 ↑ | 계약 전환 pair ↑ |
|---|---:|---:|---:|---:|
| 요구사항 CoC | 0.500 ± 0.000 | 0.319 ± 0.052 | 0.681 ± 0.052 | 0.000 ± 0.000 |
| Inline 자연어 제약 | 1.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| 별도 자연어 Guard | 0.698 ± 0.094 | 0.191 ± 0.136 | 0.809 ± 0.136 | 0.396 ± 0.187 |
| Shuffled Guard | 0.510 ± 0.015 | 0.333 ± 0.023 | 0.667 ± 0.023 | 0.021 ± 0.029 |
| Logic Guard | 0.538 ± 0.027 | 0.274 ± 0.108 | 0.726 ± 0.108 | 0.076 ± 0.055 |

Inline 자연어 제약은 세 seed 모두에서 완벽하게 재현됐다. 별도 자연어 Guard도 평균적으로 requirement-only 및 shuffled보다 나았으며, 계약 전환 pair는 shuffled보다 0.375 높았다. 그러나 seed별 pair 성능은 0.167–0.625, 안전 목표 완료는 0.698–1.000으로 변동이 컸다. 따라서 별도 Guard는 의미 신호를 학습하지만 현재 objective로 안정적으로 활용하지 못한다.

추가 seed 실행 전에 선언한 다섯 진단 기준 중 네 개가 통과했다. 별도 자연어 Guard의 unseen-time 안전 목표 완료 0.70 기준은 통과하지 못했다. Inline 형식의 학습 가능성은 강하게 재현됐지만, 새로운 시간값 일반화와 별도 필드 학습 안정성은 다음 단계의 미해결 문제다.

상세 결과: `artifacts/results/public/small-vlm-guard-v0/temporal-guard-multiseed-v0/REPORT_KO.md`

## 6. 표현 조건의 재정의

기존의 `Rich CoC` 명칭은 실제 비교 내용을 명확히 나타내지 못하므로 다음처럼 부르는 것이 적절하다.

- `INLINE_NL_CONSTRAINT`: 자연어 제약을 CoC 문장 안에 포함
- `SEPARATE_NL_GUARD`: 동일 자연어 제약을 별도 Guard 필드에 배치
- `LOGIC_GUARD`: 구조화된 논리 표현을 별도 필드에 배치
- `SHUFFLED_GUARD`: 학습 중 Guard–정답 대응을 깨뜨린 negative control

`INLINE_NL_CONSTRAINT`도 본 연구 제안에 포함된다. 본 연구의 상위 아이디어는 Guard 필드 분리 자체가 아니라 **요구사항 중심 CoC를 명시적 제약이 포함된 Safety-Constrained CoC로 확장하는 것**이다.

## 7. 현재 지지되는 주장

1. R1 trajectory는 CoC 문장 변화에 반응한다.
2. R1이 학습하지 않은 Guard를 zero-shot으로 의미에 맞게 안정적으로 준수한다는 증거는 없다.
3. 작은 VLM은 자연어 Guard–행동 대응을 학습할 수 있다.
4. 목표를 달성하는 후보끼리 비교할 때 명시적 제약은 Guard 위반 후보 선택을 크게 줄일 수 있다.
5. 제약을 CoC 내부 자연어로 포함하는 방식은 정적 및 시간적 합성 과제에서 효과적이었다.
6. 위반 감소만으로는 부족하며 목표 완료, deadlock, false conservatism을 함께 평가해야 한다.
7. 시간적 inline 자연어 제약의 효과는 세 seed에서 동일하게 재현됐다.
8. 별도 자연어 Guard는 shuffled보다 유의미한 방향 신호를 보였지만 seed 변동과 unseen-time 일반화 실패가 남았다.

## 8. 아직 지지되지 않는 주장

1. 실제 R1 또는 실제 자동차의 충돌률이 감소한다.
2. 기존 CoC가 일반적으로 unsafe trajectory를 유발한다.
3. 별도 Guard 필드가 CoC 내부 제약보다 우수하다.
4. 임의 Logic Guard를 VLM에 텍스트로 입력하면 정확히 실행한다.
5. 자연어 제약이 실제 도로의 완전한 안전 명세가 된다.
6. 단일 seed 합성 결과가 다른 모델ㆍ장면ㆍmaneuver에 일반화된다.
7. Guard가 실제 안전을 보장한다.

## 9. 최종 연구 질문과 가설

### RQ1: 학습 효과

> Safety-Constrained CoC로 학습한 VLM은 요구사항 중심 CoC로 학습한 VLM보다 운전 목표 달성을 유지하면서 명시된 시간적ㆍ기하학적ㆍ동역학적 제약 위반을 줄이는가?

### RQ2: 표현 및 일반화

> Inline 자연어 제약, 별도 자연어 Guard 및 실행 가능한 Logic Guard 중 어떤 표현ㆍ학습 구조가 새로운 문장, 수치, phase 및 Guard 조합에 가장 잘 일반화되는가?

### RQ3: Maneuver coverage

> 같은 효과가 주행 유지, 주행 중 정지, 정지 후 출발, 차선 변경ㆍ중단 및 Yield 후 진입에서 일관되게 나타나는가?

### 중심 가설

> VLM에 요구사항 CoC와 명시적 자연어 안전 제약을 함께 제공하고 Guard-aware objective로 학습하면, requirement-only 학습보다 admissible trajectory 선택률을 높이면서 deadlock과 진행도 손실을 제한할 수 있다.

## 10. 평가 원칙

주요 평가는 일반 classification accuracy가 아니라 다음을 사용한다.

- Guard violation trajectory selection rate
- 전체 적용 Guard의 conjunction satisfaction
- hold 및 premature release violation
- false rejection of admissible trajectory
- deadlock 또는 always-stop rate
- CoC goal completion rate
- safe goal completion rate
- admissible 집합 내부 progress regret
- 동일 장면 contract-swap pair accuracy
- unseen phrase, value, phase 및 composition generalization

## 11. 다음 단계

### 11.1 즉시 수행: 재현성 및 형식 친숙도

1. 완료: 시간적 실험을 seeds 42, 17, 123에서 반복했다.
2. 완료: `INLINE_NL_CONSTRAINT`, `SEPARATE_NL_GUARD`, `LOGIC_GUARD`, `SHUFFLED_GUARD`의 평균과 분산을 보고했다.
3. 다음: 학습량별 learning curve로 sample-efficiency 차이를 측정한다.
4. 다음: 동일 정보를 XML, JSON, 자연어 및 논리식으로 제시해 형식 친숙도를 분리한다.

### 11.2 Guard-aware 학습

- 동일 장면의 short/long 계약을 같은 batch에 묶는 pairwise objective
- 위반 후보에 직접 벌점을 주는 auxiliary violation loss
- Guard 전용 delimiter 또는 special token
- 자연어 Guard와 구조화 Guard의 alignment objective

### 11.3 Maneuver 확장

1. `CRUISE → STOP`
2. `STOP → HOLD → RELEASE → GO`
3. `KEEP LANE → LANE CHANGE → COMPLETE/ABORT`
4. `YIELD → GAP ACCEPTANCE → ENTER`

각 maneuver에서 조기 행동, 늦은 행동, 경계 위반 및 과도한 보수 후보를 분리한다.

### 11.4 실제 모델 확장

- Alpamayo-R1 zero-shot Guard 실험은 responsiveness 진단으로만 사용한다.
- 가능한 경우 Guard-aware post-training 또는 adapter 학습으로 의미 준수를 검사한다.
- 논리 Guard는 VLM이 직접 해석하게 하기보다 compiler와 deterministic verifier/shield로 실행하는 구조를 함께 평가한다.

## 12. 최종 결론

본 연구의 현재 핵심은 CoC가 틀렸음을 일반적으로 증명하는 것이 아니다. CoC가 표현하는 행동 요구사항을 유지하면서, 그 행동이 허용되는 시간적ㆍ기하학적ㆍ동역학적 범위를 명시하고 학습ㆍ검증하는 것이다.

> 현재 합성 결과는 VLM을 CoC와 자연어 안전 제약으로 함께 학습하면 목표를 포기하지 않으면서 명시된 제약을 준수하는 trajectory를 더 잘 선택할 수 있음을 지지한다. 시간적 inline 자연어 제약 효과는 세 seed에서 완전히 재현됐다. 그러나 같은 제약을 별도 Guard 또는 논리 텍스트로 주는 방식은 아직 안정적이지 않으며, 형식 적응과 Guard-aware 학습이 다음 핵심 단계다.
