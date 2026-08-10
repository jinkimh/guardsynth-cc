# STOP phase-complete 격리 재실험 판정

> **후속 stress 실험 알림:** 이 문서의 평가 bank에서 0%였던 정책들을 재진입·재등장·release 취소 장면에 frozen 상태로 적용한 결과, A/B/C가 다시 실패했고 현재 상태 shield도 잔여 위반을 남겼다. 최신 일반화 판정은 [release-reversal 심층 실험](../../contract-microworld-v2/pilot-release-reversal-2026-08-04-v1/DEEP_STRESS_ASSESSMENT_KO.md)을 우선한다.

## 결론

STOP 실패의 직접 원인은 “계약 변수가 없어서”라기보다 **학습 성공 시연에 `정지 완료 후에도 계속 기다리는 HOLD phase`가 전혀 없었던 것**이었다.

v1에서 0건이던 post-stop HOLD transition을 1,404건 추가하자, 동일한 OOD STOP 평가 bank에서 A/B/C/C2 모두 세 seed에 걸쳐 조기 진입 0건을 기록했다. 따라서 이 합성 환경에서는 사용자가 제안한 다음 설명이 지지된다.

> 자연어 CoC가 모든 제약을 말하지 않더라도, 충분한 상태와 phase-complete 성공 시연이 있으면 일반 학습이 누락된 제약을 암묵적으로 보정할 수 있다.

그러나 이것은 유한한 합성 OOD bank에서의 결과이며, 보지 않은 phase 조합 전체에 대한 보장은 아니다.

## 통제 변경

v1과의 비교에서 다음만 의도적으로 바꿨다.

1. 기존 600개 학습 장면 중 STOP 후반 100개를 `STOP -> HOLD -> RELEASE` 성공 시연으로 교체했다.
2. 횡단보도 200개와 선행차 200개는 v1과 동일하게 유지했다.
3. ID/OOD 평가 장면, model seed `42/43/44`, 학습 epoch를 v1과 동일하게 고정했다.
4. 정지선 전방 0.5m를 collision으로 부르던 v1 proxy를 제거했다.
5. 계약 함수 호출 없이 실제 `x=0` 진입, 교통상태, visibility를 직접 검사하는 평가기를 사용했다.
6. 기존 계약 C와 phase one-hot을 추가한 C2를 함께 비교했다.

하나의 MLP가 세 장면 유형을 함께 학습하므로 STOP transition 변경이 공유 가중치를 통해 다른 유형에 영향을 줄 가능성은 남아 있다.

## 학습 phase coverage

| STOP phase | v1 | v2 |
|---|---:|---:|
| APPROACH | 관측됨 | 3,766 |
| STOP_DWELL | 관측됨 | 200 |
| 정지 완료 후 HOLD | **0** | **1,404** |
| RELEASED | 관측됨 | 3,600 |

v1 MLP는 `has_stopped=1`을 사실상 `출발 가능`과 동일하게 학습했다. v2에서는 처음으로 다음 조합을 학습했다.

```text
has_stopped = 1
cross_traffic_present = 1
hold_required = 1
release_allowed = 0
expert action = 정지 유지
```

## STOP 결과

v1의 `unsafe`에는 잘못된 pre-line collision proxy가 6건 포함됐으므로, 직접 비교에는 실제 정지선 조기 진입인 `forbidden_entry`만 사용한다.

| 조건 | v1 STOP 조기 진입 | v2 STOP 조기 진입 | v2 completion |
|---|---:|---:|---:|
| A 상태 | 37/300 | **0/300** | 100% |
| B 상태 + 행동 CoC | 29/300 | **0/300** | 100% |
| C 구조화 계약 | 64/300 | **0/300** | 100% |
| C2 구조화 계약 + phase | 해당 없음 | **0/300** | 100% |
| D C2 + shield | 해당 없음 | **0/300** | 100% |

A/B도 0건이 됐기 때문에 STOP 해결을 계약 feature의 고유 효과로 돌릴 수 없다. phase-complete 성공 시연만으로도 기본 상태에 포함된 `has_stopped`, `hazard_active`, `visible`의 올바른 조합을 학습했다.

## 전체 OOD 결과

| 조건 | unsafe | safe-gap violation | completion | 평균 progress | jerk | shield 개입 |
|---|---:|---:|---:|---:|---:|---:|
| A | 2.6% | 3.6% | 100% | 28.111m | 1.954 | 0 |
| B | 1.4% | 7.8% | 100% | 28.166m | 2.342 | 0 |
| C | **0%** | **0%** | 100% | 28.135m | 3.561 | 0 |
| C2 | **0%** | **0%** | 100% | 28.083m | 3.402 | 0 |
| D | **0%** | **0%** | 100% | 28.005m | 3.442 | 2.539회/episode |

동일한 900개 OOD episode를 paired 비교한 결과는 다음과 같다.

- A -> C: unsafe 23건과 safe-gap violation 32건 제거, 새 위반 0건
- B -> C: unsafe 13건과 safe-gap violation 70건 제거, 새 위반 0건
- C -> C2: 모든 binary safety metric이 완전히 동일
- C2 -> D: 모든 binary safety metric이 완전히 동일

따라서 C는 A/B보다 전체적으로 나았지만, C2의 명시적 phase one-hot과 D shield는 이 평가 bank에서 추가적인 binary safety 개선을 만들지 못했다.

## shield 해석

D는 C2의 위반을 더 줄일 수 없었지만 다음과 같이 개입했다.

- 전체 OOD: episode당 평균 2.539회
- STOP OOD: episode당 평균 약 5.22회
- ID: episode당 평균 1.269회
- C2 대비 평균 progress 약 0.078m 감소
- C2 대비 jerk 소폭 증가

현재 metric에서 C2는 이미 위반 0건이므로, D의 개입은 추가 안전 이득이 아니라 보수적 비용으로 나타났다. 더 어려운 unseen 환경 분기에서 shield 효과가 다시 나타날 가능성은 있지만 이 실험은 그것을 보여주지 않는다.

## 수정된 연구 해석

현재 증거가 지지하는 순서는 다음과 같다.

1. 성공 시연의 phase coverage가 가장 먼저 필요하다.
2. A/B처럼 명시적 계약이 없는 정책도 관측된 phase 조합은 학습으로 보정할 수 있다.
3. C의 부분적 계약은 전체 OOD와 safe-gap robustness에서 A/B보다 나았다.
4. 명시적 phase feature C2는 C보다 추가 이득을 보이지 않았다.
5. shield D도 이미 해결된 bank에서는 안전 이득 없이 개입 비용만 추가했다.

따라서 연구 질문은 “CoC에 모든 제약이 없으므로 항상 shield가 필요하다”가 되어서는 안 된다. 더 타당한 질문은 다음이다.

> 성공 시연과 CoC가 어떤 안전 관련 phase 조합을 관측했고 어떤 조합을 빠뜨렸는가? 구조화 부분 계약은 보지 않은 조합에서 암묵적 학습보다 더 안정적으로 일반화하며, runtime shield가 실제로 필요한 잔여 영역은 어디인가?

## 다음 실험

1. 학습에 없는 새로운 phase 조합을 별도로 생성한다: 재진입 보행자, 반복 occlusion, 정지 후 교차 차량의 재등장, release 취소.
2. phase-complete 학습 bank와 평가 bank의 범위를 명시적으로 분리한다.
3. 올바른 계약, 누락 계약, 잘못된 release 계약을 넣어 C가 계약 오류에 얼마나 민감한지 측정한다.
4. shield의 개입 precision과 unnecessary intervention을 독립 oracle로 계산한다.
5. 이 결과가 반복될 때만 자연어 CoC에서 부분 계약을 자동 추출하는 단계로 이동한다.

이 재실험은 “계약을 추가하면 무조건 더 안전하다”보다 더 중요한 결론을 준다.

> **누락된 제약은 별도 계약으로 보완할 수도 있지만, 먼저 성공 시연의 phase coverage 결손인지 확인해야 한다. 학습이 이미 보정할 수 있는 영역에 shield를 붙이면 안전 이득 없이 보수성만 증가할 수 있다.**
