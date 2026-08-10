네. 이 주장의 핵심 구성요소는 이미 상당 부분 실험적으로 확인됐습니다. 다만 “수학적으로 증명됐다”기보다, 여러 논문이 각각의 부분을 실험으로 보여준 상태입니다.

정확한 결론은 다음과 같습니다.

> CoC는 trajectory 생성에 실제 영향을 미치는 하나의 조건이지만 trajectory를 유일하게 결정하지 않는다. 후속 RL은 CoC 정합성뿐 아니라 별도의 trajectory·safety reward를 통해 동일한 CoC 의미 범위 안에서도 다른 trajectory 분포를 학습할 수 있다. 그러나 그 결과가 안전하다는 보장은 없다.

## 1. CoC가 trajectory 생성에 실제로 영향을 주는가?

이 부분은 이미 확인됐습니다.

Alpamayo의 생성 구조는 개념적으로 다음과 같습니다.

\[
\tau \sim
p_\theta
\left(
\tau
\mid
\text{camera},
\text{egomotion},
\text{route},
\text{CoC},
\text{sampling}
\right)
\]

CoC가 trajectory보다 먼저 생성되고, trajectory decoder는 reasoning output에 condition됩니다. 그러나 카메라, ego history, route, diffusion sampling도 동시에 영향을 줍니다. [Alpamayo-R1](https://arxiv.org/html/2511.00088v2)

VLADriveBench는 CoC/CoT 문장을 직접 교체하는 intervention으로 이를 더 강하게 확인했습니다.

- 가속 CoT를 넣으면 예상 전진 거리가 증가
- pedestrian/car brake CoT를 넣으면 전진 거리가 감소
- self-splice는 거의 변화 없음
- closed-loop에서도 brake CoT 효과가 누적됨

특히 Alpamayo v1.5에서는 pedestrian CoT를 넣었을 때 5.9초 후 baseline보다 약 14.9m 적게, car CoT에서는 약 20.1m 적게 진행했습니다. 즉 CoC는 단순한 사후 설명이 아니라 trajectory에 인과적 영향을 주는 조건입니다. [VLADriveBench](https://arxiv.org/html/2606.12706v1)

## 2. 그렇다면 CoC가 trajectory 전체를 결정하는가?

아닙니다. 이 부분도 기존 연구에서 상당히 확인됐습니다.

VLADriveBench의 시각적 salience 실험이 가장 직접적입니다.

- “도로가 비어 있으니 가속하라”는 잘못된 CoT를 주입
- 보행자가 눈에 덜 띄는 위치에 있으면 CoT가 vision을 압도하여 충돌
- 보행자가 중앙으로 이동하면 충돌 빈도가 감소
- 차로를 막은 큰 정지 차량은 잘못된 CoT의 영향을 받지 않고 계속 정지

즉 trajectory는 CoC만 따르는 것이 아닙니다.

\[
\text{trajectory}
=
f(\text{CoC},\text{visual salience},\text{egomotion},\text{other context})
\]

강한 시각 증거가 CoC를 무시할 수도 있고, 약한 시각 증거에서는 CoC가 vision을 압도할 수도 있습니다. [VLADriveBench](https://arxiv.org/html/2606.12706v1)

우리 실험도 이 점을 소규모로 재현했습니다.

- 서로 다른 CoC 의미인데 첫 0.5초 trajectory가 거의 동일
- 같은 CoC semantic signature인데 장기 trajectory는 크게 다름
- early RELEASE seed가 HOLD seed보다 더 공격적이지 않음

하지만 이 현상 자체는 이미 알려진 “CoC는 영향 요소이지 trajectory의 완전한 명세가 아니다”라는 사실의 재현에 가깝습니다.

## 3. RL이 CoC에 없는 trajectory 정보를 추가로 학습할 수 있는가?

네. Alpamayo 논문 자체가 가장 직접적인 증거를 제공합니다.

Alpamayo의 RL reward는 하나가 아니라 세 종류입니다.

\[
r =
r_{\text{reason}}
+
r_{\text{consistency}}
+
r_{\text{safety}}
\]

- \(r_{\text{reason}}\): CoC reasoning 품질
- \(r_{\text{consistency}}\): CoC–trajectory 행동 정합성
- \(r_{\text{safety}}\): unsafe 또는 물리적으로 부적절한 trajectory에 대한 별도 벌점

결과는 다음과 같습니다.

| 학습 | Reasoning-action consistency | Close encounter |
|---|---:|---:|
| SFT | 0.62 | 6.9% |
| + reasoning RL | 0.53 | 5.8% |
| + reasoning/consistency RL | 0.85 | 6.2% |
| + reasoning/consistency/safety RL | 0.83 | 3.7% |

여기서 중요한 사실은 reasoning–action consistency를 크게 올려도 close encounter가 6.2%로 남았고, 별도의 safety reward를 추가했을 때 3.7%로 감소했다는 점입니다.

즉:

> CoC와 trajectory를 일치시키는 것만으로 안전해지지 않는다. CoC와 별도로 trajectory-level safety reward가 필요하다.

Alpamayo 논문도 이를 명시적으로 인정합니다. reasoning과 consistency reward는 안전한 motion을 직접 제한하지 않기 때문에 safety reward를 별도로 추가했다고 설명합니다. [Alpamayo-R1의 RL 결과](https://arxiv.org/html/2511.00088v2)

따라서 사용자님의 해석은 맞습니다.

> 강화학습은 CoC가 자연어로 명시한 행동 의미를 유지하면서도, clearance·동역학·close encounter 같은 CoC에 세밀하게 표현되지 않은 trajectory 특성을 추가로 최적화할 수 있다.

다만 논문이 “CoC에 없는 어떤 정보가 각 trajectory waypoint를 바꿨는지”를 장면별로 분리해 증명한 것은 아닙니다. 위 결과는 aggregate reward ablation 증거입니다.

## 4. 인간 시연에 없는 trajectory도 학습할 수 있는가?

이것도 일반적인 E2E 연구에서는 이미 확인되고 있습니다.

Beyond Imitation은 expert trajectory 주변에 안전하지 않은 hard-negative trajectory를 생성하고, 정책이 expert trajectory에 가까워지면서 동시에 unsafe trajectory에서는 멀어지도록 학습합니다.

즉 학습 신호는 더 이상:

\[
\text{expert trajectory를 모방하라}
\]

만이 아니라:

\[
\text{expert 쪽으로 가되, 가까이 있는 unsafe trajectory는 피하라}
\]

가 됩니다. 따라서 모델은 인간 시연의 정확한 기하를 복제하는 대신, 학습된 safety boundary 안에서 다른 trajectory를 선택할 수 있습니다. [Beyond Imitation](https://arxiv.org/html/2605.19771v1)

다만 이 연구는 Alpamayo CoC 모델을 대상으로 한 것은 아닙니다. “후속 safety 학습이 인간 시연 이외의 trajectory 구조를 가르칠 수 있다”는 일반적 근거입니다.

## 5. 무엇이 이미 밝혀졌고 무엇이 아직 아닌가

| 주장 | 기존 연구 상태 |
|---|---|
| CoC가 trajectory에 영향을 준다 | 확인됨 |
| CoC는 단순한 사후 설명만은 아니다 | Alpamayo에서는 확인됨 |
| CoC가 trajectory를 유일하게 결정한다 | 부정됨 |
| vision이 CoC를 무시하거나 압도할 수 있다 | 확인됨 |
| 잘못된 CoC가 안전 행동을 악화할 수 있다 | VLADriveBench에서 확인됨 |
| CoC–trajectory 정합성이 높으면 안전하다 | 부정됨 |
| 별도 safety reward가 trajectory를 개선할 수 있다 | 확인됨 |
| safety reward가 안전을 보장한다 | 확인되지 않음 |
| CoC가 언급하지 않은 정확히 어떤 정보를 RL이 사용했는지 | 장면별로 분리되지 않음 |
| RL로 생성된 모든 새로운 trajectory가 안전하다 | 확인되지 않음 |

## 가장 정확한 표현

사용자님의 주장을 논문에서 사용할 수 있는 형태로 다듬으면 다음과 같습니다.

> CoC는 고수준의 원인 및 행동 의도를 표현하고 trajectory 생성에 기능적으로 관여하지만, 연속 trajectory를 완전히 명세하거나 그 안전성을 보증하지 않는다. 실제 trajectory는 시각 입력, ego-motion, route context, stochastic action decoder 및 후속 RL reward의 공동 결과다. 특히 trajectory-level safety reward는 CoC–action consistency와 독립적인 개선을 제공할 수 있지만, 이는 경험적인 위험 감소이지 형식적 안전 보장은 아니다.

## 우리 연구에 대한 의미

이 결론 자체를 다시 보이는 것은 새 연구가 되기 어렵습니다.

- “CoC가 trajectory에 영향을 준다” → VLADriveBench가 수행
- “CoC만으로 trajectory가 결정되지 않는다” → visual-salience intervention이 수행
- “CoC consistency만으로 안전하지 않다” → Alpamayo RL ablation이 수행
- “별도 safety learning이 필요하다” → Alpamayo와 Beyond Imitation이 수행

따라서 우리가 새롭게 보이려면 다음 단계가 필요합니다.

> CoC를 더 정확하게 검증하는 것이 아니라, CoC의 영향은 유지하면서도 그 영향으로 trajectory가 독립적인 안전 경계를 넘어가지 못하게 만드는 방법.

그러나 이것 역시 단순한 CBF safety layer라면 기존 연구와 겹칩니다. 결국 새로운 연구가 되려면 `CoC 영향의 허용 범위`, `독립 safety endpoint`, `closed-loop 효과`를 함께 정의해야 합니다. 현재 데이터만으로는 그 마지막 안전 endpoint가 부족하다는 기존 결론은 그대로 유지됩니다.

--------

네. 실제 데이터와 Alpamayo 설계를 확인해 보니, 대부분의 CoC는 “무엇을 할 것인가와 그 이유”를 표현하지만 “무엇을 절대 해서는 안 되는가”라는 안전 제약은 거의 명시하지 않습니다.

이는 단순한 느낌이 아니라 공식 human-refined CoC 전체에서도 확인됩니다.

## 실제 CoC 집계

로컬 공식 PhysicalAI-AV의 [ood_reasoning.parquet](/home/jinhyun/prj_ws/prj_jin/guardsynth-cc/data/restricted/nvidia_physicalai/reasoning/ood_reasoning.parquet)에 있는 1,740개 clip, 2,077개 CoC event를 보수적인 규칙으로 검사했습니다.

| 표현 유형 | CoC 수 | 비율 |
|---|---:|---:|
| 명시적 금지: `do not`, `must not`, `never`, `shall not`, `should not` 등 | 0 | 0% |
| `always`, `at all times`, `under no circumstances` 같은 invariant | 0 | 0% |
| 거리·시간·속도 수치 경계 | 0 | 0% |
| `avoid`, `prevent`, `without crossing…` 계열 | 36 | 1.73% |
| `safe distance`, `safe gap`, `clearance` 등 암묵적 거리 제약 | 665 | 32.02% |
| 어떤 형태로든 암묵적 제약 표현 포함 | 700 | 33.70% |
| 명시적·암묵적 제약 표현 모두 없음 | 1,377 | 66.30% |
| `after`, `while`, `if`, `before` 등의 조건 표현 | 794 | 38.23% |

여기서 조건 표현 38.23%도 대부분 형식적인 guard는 아닙니다. 예를 들어 어떤 객체가 지나가는 동안 감속한다거나, 통과한 후 속도를 회복한다는 수준입니다. 다음은 거의 없습니다.

- 언제까지 정지해야 하는가
- 어느 영역에 진입하면 안 되는가
- 최소 clearance는 얼마인가
- 어떤 조건이면 계획을 포기해야 하는가
- 센서 증거가 불충분할 때 fallback은 무엇인가

### 모델이 생성한 CoC에서도 동일한 패턴

우리의 Alpamayo base 30회 추론에서는:

- 명시적 금지: 0/30
- 수치 제약: 0/30
- safe-distance 계열: 9/30

두 rolling 실험의 신규 42개 출력에서는:

- 명시적 금지: 0/42
- 수치 제약: 0/42
- safe-distance 계열: 0/42
- 조건 표현: 3/42

작은 목적 표본이므로 비율을 일반화할 수는 없지만, 공식 human CoC 전체 집계와 방향이 일치합니다.

이 결과는 lexical audit입니다. 즉 자연어에 내포된 모든 의미를 완전히 판정한 semantic gold audit은 아닙니다. 그래도 명시적 금지·불변식·수치 경계가 사실상 없다는 결론은 상당히 강합니다.

## 왜 이런 구조인가?

Alpamayo CoC는 처음부터 requirements specification으로 설계되지 않았기 때문입니다.

공식 설계에서는 각 sample이 다음으로 구성됩니다.

\[
\text{관찰된 causal factor}
+
\text{선택된 첫 driving decision}
\rightarrow
\text{간결한 CoC}
\]

주요 원칙은:

- keyframe 직후 첫 행동에 연결
- longitudinal/lateral channel당 최대 한 decision
- 행동에 직접 관련된 원인만 포함
- annotation economy, 즉 불필요한 요소는 제거

입니다. [Alpamayo-R1 CoC 설계](https://arxiv.org/html/2511.00088v2)

따라서 CoC가 표현하는 것은 대체로 다음입니다.

- “보행자가 있으므로 YIELD한다.”
- “선행 차량 때문에 감속한다.”
- “차선이 막혀 있으므로 오른쪽으로 nudge한다.”
- “장애물이 해소되어 속도를 회복한다.”

반면 완전한 안전 요구사항은 다음과 같은 형태여야 합니다.

- 보행자가 conflict zone을 점유하는 동안 ego는 그 zone에 진입해서는 안 된다.
- 선행차와의 time gap은 항상 \(T_{\min}\) 이상이어야 한다.
- 회피 중 차량 footprint는 drivable area를 벗어나서는 안 된다.
- target identity가 불확실하면 RELEASE해서는 안 된다.
- 계획이 안전하지 않으면 최소위험상태로 전환해야 한다.

이 차이는 requirements engineering 관점에서 다음과 같습니다.

| 구분 | CoC에서 주로 제공 | 대부분 누락 |
|---|---|---|
| 원인 | 보행자, 선행차, 신호, 공사구간 | 복수 원인의 우선순위 |
| 의도·목표 | 감속, 정지, 양보, 회피, 진행 | 대안 행동 집합 |
| safety invariant | 일부 `safe distance`처럼 암묵적 | 명시적 forbidden state |
| 수치 경계 | 거의 없음 | 거리·TTC·속도·시간 |
| 지속 조건 | 가끔 `while`, `after` | 정확한 trigger/hold/release |
| 실패 처리 | 거의 없음 | abort, fallback, minimal-risk state |
| 불확실성 | 장면 설명에 일부 존재 가능 | 불확실성별 허용 제어 |

따라서 CoC는 다음에 가깝습니다.

> 특정 행동을 선택하도록 유도하는 긍정적인 reasoning hint

다음은 아닙니다.

> 생성 가능한 모든 trajectory가 만족해야 하는 완전한 안전 계약

## 중요한 증거: 안전은 CoC 밖에서 따로 학습된다

Alpamayo 학습 구조도 이 해석을 지지합니다.

CoC SFT와 후속 RL에는 서로 다른 reward가 있습니다.

\[
r =
r_{\text{reason}}
+
r_{\text{consistency}}
+
r_{\text{safety}}
\]

Alpamayo 논문은 reasoning reward와 reasoning–action consistency reward만으로는 안전 trajectory를 명시적으로 제한하지 못한다고 설명합니다. 그래서 unsafe 또는 physically implausible trajectory를 벌점화하는 `safety reward`를 별도로 추가합니다.

실제로:

- reasoning + consistency reward: close encounter 6.2%
- 여기에 safety reward 추가: 3.7%

로 감소했습니다. [Alpamayo RL ablation](https://arxiv.org/html/2511.00088v2)

즉 안전 제약은 CoC 문장에 모두 표현되는 것이 아니라 다음에 분산되어 있습니다.

- 학습 데이터에 내재된 운전 패턴
- vision/egomotion feature
- trajectory decoder의 동역학 prior
- RL consistency reward
- 별도의 safety reward
- downstream MPC와 vehicle dynamics

## 데이터 구성도 negative constraints를 약화시킨다

공식 human-labeling 단계에서는 unsafe 또는 illegal driving example을 safety exclusion filter로 먼저 제거한 뒤 CoC를 작성합니다.

그러므로 CoC dataset은 주로 다음을 학습합니다.

\[
\text{이 장면에서 성공적으로 수행된 행동}
\]

반면 다음은 직접 제공하지 않습니다.

\[
\text{비슷해 보이지만 실패하는 행동}
\]

\[
\text{절대로 진입해서는 안 되는 상태}
\]

\[
\text{안전 행동과 unsafe 행동 사이의 경계}
\]

SafeAlign-VLA와 Beyond Imitation 같은 최근 연구가 negative trajectory와 counterfactual safe trajectory를 별도로 도입하는 이유도 이것입니다. 성공 시연만으로는 안전 경계를 명확히 학습할 수 없기 때문입니다. [SafeAlign-VLA](https://arxiv.org/html/2605.19524v1), [Beyond Imitation](https://arxiv.org/html/2605.19771v1)

## 이 사실이 바로 문제인가?

자동차 모델 자체에는 반드시 결함이라고 할 수 없습니다.

CoC가 계획을 돕는 reasoning channel이고 안전은 별도의 reward와 controller가 담당한다면, CoC가 완전한 safety specification일 필요는 없습니다.

하지만 다음과 같이 사용하려면 큰 문제가 됩니다.

- CoC를 trajectory의 안전 justification으로 제시
- CoC를 runtime safety monitor의 입력으로 사용
- CoC를 STL/SMT로 변환해 안전 검증
- CoC–trajectory consistency를 safety score로 사용
- CoC를 규제기관이나 사람에게 설명 증거로 제공

이때는 CoC가 무엇을 하겠다는지만 말하고, 허용되지 않는 행동 집합을 말하지 않기 때문에 검증기의 명세가 불완전해집니다.

예를 들어:

\[
\text{CoC: YIELD to pedestrian}
\]

만으로는 다음을 알 수 없습니다.

\[
\begin{aligned}
&\text{어느 보행자인가?}\\
&\text{어느 conflict zone인가?}\\
&\text{얼마나 감속해야 하는가?}\\
&\text{언제까지 진입하면 안 되는가?}\\
&\text{무엇을 관측하면 RELEASE해도 되는가?}\\
&\text{불확실하면 무엇을 해야 하는가?}
\end{aligned}
\]

우리가 단순 STOP/YIELD 검증에서 계속 `UNKNOWN`과 오탐을 얻었던 직접적인 이유가 여기에 있습니다.

## 연구적으로 남는 문제

따라서 더 정확한 문제 정의는 다음이 될 수 있습니다.

> CoC가 틀렸는지를 검증하는 것이 아니라, action-oriented CoC에 명시적으로 누락된 safety constraints를 별도의 machine-checkable contract로 보완할 수 있는가?

예를 들면 기존 CoC에 다음 구조를 추가합니다.

```text
Cause:
  crossing pedestrian in conflict zone

Intent:
  yield

Forbidden:
  ego must not enter the conflict zone while occupied

Guard:
  pedestrian occupancy uncertain or active

Release:
  tracked pedestrian clears zone with sufficient margin

Fallback:
  if identity or clearance is uncertain, remain stopped
```

하지만 단지 이런 문장을 만드는 것으로는 부족합니다. 새 연구가 되려면 다음을 보여야 합니다.

1. 기존 CoC보다 constraint coverage가 실제로 증가한다.
2. 사람과 자동 parser가 동일한 constraint를 재현한다.
3. SMT/STL monitor가 정상 행동을 과도하게 막지 않는다.
4. closed-loop에서 unsafe trajectory가 감소한다.
5. 진행성·comfort를 지나치게 훼손하지 않는다.

## 최종 판정

사용자님의 관찰은 맞습니다.

> 대부분의 CoC는 원인과 선택 행동을 표현하지만, forbidden behavior, invariant, quantitative boundary, fallback을 명시하는 안전 요구사항은 거의 포함하지 않습니다.

그리고 이것은 우연한 annotation 누락이라기보다 CoC가 `decision-grounded causal explanation`으로 설계됐기 때문입니다.

따라서 CoC에 대한 가장 정확한 해석은:

> trajectory 생성을 유도하는 기능적 CoT이지만 완전한 safety specification은 아니다.

입니다. 다만 “CoC에 제약이 없다”는 빈도 분석만으로는 논문 기여가 약합니다. 연구 가치가 생기려면 명시적 negative contract를 추가했을 때 기존 safety reward만 사용하는 방식보다 closed-loop 안전성과 검증 가능성이 실제로 개선된다는 것을 보여야 합니다.