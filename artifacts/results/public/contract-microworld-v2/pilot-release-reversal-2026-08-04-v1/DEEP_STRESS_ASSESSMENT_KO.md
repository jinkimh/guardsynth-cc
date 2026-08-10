# Release-reversal 심층 stress 실험 판정

## 결론

phase-complete 성공 시연으로 기존 STOP 평가를 모두 해결했지만, 학습에 없던 `release 취소`와 위험 재등장에서는 모든 frozen 정책이 다시 차이를 보였다.

가장 중요한 결과는 다음 세 가지다.

1. 구조화 동적 계약 C는 A/B보다 크게 나았지만 위반을 완전히 제거하지 못했다.
2. 단조로운 phase one-hot C2는 C보다 오히려 나빴다. `RELEASED -> HOLD` 역전이가 학습에 없었기 때문이다.
3. 현재 상태만 검사하는 D shield도 잔여 위반이 있었다. 완벽한 미래 정보를 1.2초 보는 상한선만 0%를 달성했다.

따라서 필요한 것은 고정된 STOP/YIELD 문장이나 단조로운 phase가 아니라 다음이다.

> **새 증거가 나타나면 release를 취소할 수 있고, 미래 위험의 불확실성 집합을 고려하는 revocable predictive safety contract**

## 실험 질문

이전 재실험에서 A/B/C/C2/D가 모두 0%였던 이유가 실제 일반화인지, 아니면 평가 bank가 학습된 phase 조합 안에 있었기 때문인지 검사했다.

정책은 재학습하지 않았다. phase-complete v2에서 학습된 동일 모델을 frozen 상태로 사용했다.

```text
학습에서 본 전이:
  APPROACH -> STOP -> HOLD -> RELEASED

이번 평가의 unseen 전이:
  RELEASED -> HOLD
  visible -> occluded
  clear -> hazard reappears
```

## Stress bank

네 유형을 각각 100개 생성했다.

| 유형 | 내용 |
|---|---|
| crosswalk reentry | 보행자가 사라진 뒤 출발 직전에 다시 진입 |
| stop cross-traffic reappearance | STOP 완료 후 교차 차량이 사라졌다가 다시 등장 |
| crosswalk re-occlusion | 시야 확보 후 다시 가려짐 |
| stop re-occlusion | STOP 완료·시야 확보 후 다시 가려짐 |

총 400개 고유 장면을 seed `42/43/44`에서 반복하여 조건별 1,200 episode를 평가했다. 모든 장면은 현재 상태를 정확히 사용하는 reference controller와 shield가 안전하게 완료할 수 있고, 위험 역전 시 차량이 관련 경계 근처에 있는 경우만 선별했다.

## 비교 조건

| 조건 | 의미 |
|---|---|
| A | 상태만 입력 |
| B | 상태 + 행동 CoC one-hot |
| C | 상태 + CoC + 동적 hold/release 계약 |
| C2 | C + `APPROACH/STOP_DWELL/HOLD/RELEASED` phase one-hot |
| D correct | C2 + 현재 상태의 올바른 계약 shield |
| D oracle 0.8s | 완벽한 미래 위험을 0.8초 아는 비실용적 상한선 |
| D oracle 1.2s | 완벽한 미래 위험을 1.2초 아는 비실용적 상한선 |
| C stale 0.4s | 계약 정보만 0.4초 늦음 |
| D stale 0.4s | 정책과 shield의 계약 정보가 0.4초 늦음 |
| D shared lag 0.4s | sensor와 계약 정보가 함께 0.4초 늦음 |

oracle-lookahead는 배포 가능한 방법이 아니다. 필요한 예측 horizon의 상한 효과를 측정하기 위한 positive control이다.

## 전체 결과

| 조건 | unsafe | collision | completion | progress | 개입/episode |
|---|---:|---:|---:|---:|---:|
| A | 46.6% | 26.6% | 100% | 25.026m | 0 |
| B | 48.6% | 27.3% | 100% | 25.064m | 0 |
| C | **21.4%** | **14.3%** | 100% | 25.055m | 0 |
| C2 | 37.9% | 25.9% | 100% | 25.026m | 0 |
| D correct | **4.8%** | **1.8%** | 100% | 25.025m | 9.935 |
| D oracle 0.8s | 0.08% | 0% | 100% | 24.905m | 8.789 |
| D oracle 1.2s | **0%** | **0%** | 100% | 24.897m | 8.863 |
| C stale 0.4s | 48.1% | 24.8% | 100% | 25.020m | 0 |
| D stale 0.4s | 34.8% | 16.3% | 100% | 25.057m | 10.399 |
| D shared lag 0.4s | 34.9% | 16.4% | 100% | 25.046m | 10.373 |

모든 조건의 completion이 100%이므로, 낮은 위반율이 항상 정지하는 trivial policy 때문에 나온 것은 아니다. 1.2초 oracle-lookahead의 A/B 대비 progress 감소도 약 0.13~0.17m 범위였다. 다만 개입 횟수는 많았다.

## Paired episode 효과

동일한 장면·seed의 1,200 episode를 직접 비교했다.

| 비교 | 개선 | 악화 | 둘 다 실패 | 둘 다 성공 |
|---|---:|---:|---:|---:|
| A -> C | 352 | 50 | 207 | 591 |
| B -> C | 352 | 26 | 231 | 591 |
| C -> C2 | 26 | **224** | 231 | 719 |
| C2 -> D correct | **406** | 9 | 49 | 736 |
| D correct -> oracle 0.8s | 58 | 1 | 0 | 1,141 |
| oracle 0.8s -> 1.2s | 1 | 0 | 0 | 1,199 |
| C correct -> C stale | 90 | **410** | 167 | 533 |
| D correct -> D stale | 30 | **389** | 28 | 753 |

C는 A/B보다 순효과가 분명하지만 모든 episode를 단조롭게 개선하지는 않았다. 특히 C2는 C보다 224개 episode를 새로 악화시켰다. 반면 D correct는 C2 실패 406건을 제거하면서 9건을 새로 만들었다. 경로가 바뀌면 동일한 미래 위험과 만나는 시점도 바뀌므로 shield 추가가 episode별로 완전히 단조롭지는 않았다.

## 유형별 핵심 결과

### 보행자 재진입

- A/B collision: 약 86~89%
- C collision: 39%
- C2 collision: 33.7%
- D correct collision: 6%
- 0.8초 이상 oracle-lookahead: 0%

현재 위험이 사라졌다는 사실만으로 진입하면, 보행자가 짧은 시간 뒤 다시 나타날 때 이미 conflict zone 안에 있을 수 있다. 현재 상태 shield는 미래 재진입을 알 수 없어 완전하지 않았다.

### STOP 후 교차 차량 재등장

- C unsafe: 20.3%
- C2 unsafe: **72.7%**
- D correct unsafe: 1.3%
- stale D unsafe: 65%
- oracle-lookahead: 0%

C2의 큰 악화는 phase label이 본질적으로 안전 계약이 아님을 보여준다. 학습에서는 phase가 항상 앞으로만 진행했기 때문에, `RELEASED` 뒤에 다시 `HOLD`로 돌아가는 입력 조합에서 취약했다.

### 재-occlusion

실제 hazard collision보다 불확실한 상태에서 진입하는 금지 위반을 측정했다. C와 D가 A/B보다 개선했지만 stale 계약에서는 다시 크게 악화됐다. 이는 계약 정확성뿐 아니라 **계약 갱신 시각**이 안전 속성임을 뜻한다.

## 왜 현재 상태 D도 0%가 아닌가

D는 현재 시점에 `hold_required`가 참이면 정지 가능성을 검사한다. 그러나 다음 상황은 방지할 수 없다.

```text
t       : conflict zone이 비어 있음 -> release
t+0.6s  : ego가 conflict zone에 진입
t+0.8s  : 보행자 또는 교차 차량이 다시 등장
```

위험이 다시 관측됐을 때는 제동하더라도 이미 conflict zone 안일 수 있다. 따라서 상태 기반 invariant만으로는 부족하고, 진입 전 미래 occupancy와 ego reachable tube를 함께 검사해야 한다.

## Stale 계약의 의미

올바른 C의 unsafe 21.4%가 계약을 0.4초 늦추자 48.1%로 증가했다. 올바른 D도 4.8%에서 34.8%로 증가했다.

이는 다음을 뜻한다.

> 부정확하거나 stale한 안전 계약은 단순히 효과가 없는 것이 아니라, 올바른 상태 증거와 shield의 개입 시점을 놓쳐 안전 이득 대부분을 제거할 수 있다.

따라서 `CoC -> 계약` 변환 정확도만 측정해서는 부족하다. perception timestamp, contract timestamp, trajectory 실행 timestamp의 정렬과 최대 허용 지연도 계약 일부가 되어야 한다.

## Conformal guardrail과의 연결

1.2초 oracle-lookahead가 0%를 달성한 결과는 미래를 정확히 안다는 비현실적 가정이다. 실제 연구에서는 이를 다음 구조로 바꿀 수 있다.

```text
sensor history
    -> VRU/vehicle future occupancy predictor
    -> conformal calibration
    -> coverage 1-alpha의 occupancy set

ego candidate trajectory
    -> reachable tube

if occupancy set intersects reachable tube:
    HOLD / speed cap / reject trajectory
else:
    provisional RELEASE
```

여기서 release는 영구적인 phase가 아니라 다음 sensor update에서 취소 가능한 `PROVISIONAL_RELEASE`여야 한다.

핵심 trade-off는 다음과 같다.

- coverage가 크면 missed hazard는 줄지만 불필요한 HOLD가 증가한다.
- horizon이 짧으면 재진입을 놓치고, 길면 progress와 comfort가 나빠진다.
- sensor/contract 지연이 calibration 가정보다 크면 coverage 보장이 깨질 수 있다.

## 현재 가장 타당한 연구 질문

> 성공 시연만 학습한 주행 정책에서 unseen release reversal이 발생할 때, conformal future-occupancy set과 revocable temporal contract를 결합한 guardrail이 현재 상태 계약이나 정적 phase 표현보다 unsafe entry를 줄이면서 progress와 intervention cost를 유지할 수 있는가?

이 질문은 기존의 “CoC가 틀렸는가”보다 좁고 측정 가능하다. CoC는 원인과 행동 의도를 제공하고, 별도 계약은 `금지/hold/release 취소/fallback`을 담당한다.

## 아직 주장할 수 없는 것

1. 실제 도로에서 1.2초가 충분한 horizon이라는 주장
2. conformal predictor를 실제로 학습·calibrate했다는 주장
3. 현재 합성 occupancy schedule이 사람·차량의 실제 행동 분포를 대표한다는 주장
4. 실제 Alpamayo trajectory에 같은 감소율이 나타난다는 주장
5. oracle-lookahead 결과가 배포 가능한 안전 보장이라는 주장

## 다음 증거 게이트

1. oracle future를 noisy probabilistic occupancy predictor로 교체한다.
2. calibration/test를 장면과 phase 기준으로 완전히 분리한다.
3. horizon `0.4/0.8/1.2/1.6초`, coverage `90/95/99%`를 교차 평가한다.
4. unsafe, collision, progress, jerk, intervention precision, unnecessary HOLD를 함께 측정한다.
5. sensor delay를 calibration feature 또는 uncertainty inflation에 포함한다.
6. 그다음 공개 폐루프 환경에서 같은 메커니즘을 검증한다.

