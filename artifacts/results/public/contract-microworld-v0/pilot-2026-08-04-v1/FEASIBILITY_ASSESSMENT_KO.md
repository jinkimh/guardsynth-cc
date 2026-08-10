# CoC 안전 계약 micro-world feasibility 판정

> **후속 재실험 알림:** 이 문서의 STOP 결론은 phase coverage를 보완한 v2 격리 실험으로 갱신되었다. v1 학습에는 `정지 완료 후 HOLD` 상태가 0건이었다. 해당 성공 시연을 추가하자 A/B/C/C2 모두 동일 OOD STOP bank에서 조기 진입 0건이 됐다. 최신 판정은 [v2 phase-complete 판정](../../contract-microworld-v1/pilot-phase-complete-isolated-2026-08-04-v2/PHASE_COMPLETE_ASSESSMENT_KO.md)을 우선한다.

## 판정

**메커니즘 feasibility는 조건부 GO, 실제 자율주행 연구 주장으로는 아직 NO-GO다.**

이 실험은 작은 정책에서도 행동 지향 CoC와 명시적 계약/실행 강제의 차이를 만들 수 있음을 보였다. 그러나 hand-written 계약을 같은 계약 정의로 평가했기 때문에 실제 안전성, CoC 자동 변환의 정확성 또는 Alpamayo의 개선을 입증하지 않는다.

## 실험 범위

- 장면: 횡단보도, STOP 교차로, 전방 차량 제동
- 학습: 유형당 200개 성공 시연, 총 600개 장면과 24,984개 transition
- 평가: 유형당 ID 100개와 OOD 100개
- 반복: model seed 42, 43, 44
- 정책: 2-layer MLP, 4,929--5,505 parameters
- 조건:
  - A: 상태만 입력
  - B: 상태 + 행동 CoC one-hot
  - C: B + 컴파일된 동적 계약 상태
  - D: C + 실행 시점 계약 shield

ID와 OOD 장면은 학습에 사용되지 않았다. OOD에서는 보행자/교차 차량의 늦은 해제와 occlusion, 선행차의 이른 강제동을 사용했다.

## A--D 조건의 구체적인 의미

네 조건은 서로 다른 자율주행 모델을 비교한 것이 아니다. 동일한 2-layer MLP 정책과 동일한 성공 시연을 사용하고, 정책에 제공하는 정보와 실행 전 강제 단계만 변경했다. D는 새로 학습한 네 번째 모델이 아니라 **C 정책의 출력 뒤에 결정론적 shield를 연결한 조건**이다.

### 공통 상태와 출력

모든 정책은 매 0.2초마다 현재 상태를 받아 다음 종방향 가속도 하나를 출력한다. 출력 범위는 `-5.0~+1.5 m/s²`이며 이 가속도를 운동학 환경에 적용하여 다음 상태를 만든다. 이 과정을 최대 12초 동안 반복하므로, 한 번에 전체 궤적을 생성하는 대신 receding-horizon 방식의 폐루프 궤적이 형성된다.

기본 상태는 10차원이다.

```text
scenario type one-hot  : crosswalk / stop intersection / lead brake  (3)
ego speed              : 현재 ego 속도                              (1)
distance               : 정지선 또는 선행차까지 거리                 (1)
relative speed          : 선행차와의 상대속도                         (1)
hazard active           : 보행자·교차 차량 등 위험이 아직 존재하는가   (1)
visible                 : 관련 영역을 현재 관측할 수 있는가            (1)
has stopped             : STOP 의무를 이미 완료했는가                 (1)
elapsed time            : episode 경과 시간                           (1)
```

### A: 상태만 입력

```text
입력  = 10차원 기본 상태
출력  = proposed acceleration
```

예를 들어 횡단보도 7.5m 전방에서 ego 속도가 7m/s이고 보행자가 아직 횡단 중이라면 다음과 같은 상태만 제공한다.

```text
crosswalk=1, ego_speed=7.0, distance=7.5,
hazard_active=1, visible=1, has_stopped=0
```

정책은 성공 시연에서 상태와 expert 가속도의 관계를 직접 모방해야 한다. `언제까지 양보해야 하는가`라는 별도 규칙은 주어지지 않는다.

### B: 상태 + 행동 CoC one-hot

```text
입력  = 10차원 기본 상태 + 3차원 행동 CoC
출력  = proposed acceleration
```

CoC는 자연어 문장을 직접 넣은 것이 아니라 다음 세 행동 의도를 one-hot으로 정규화했다.

```text
YIELD       = [1, 0, 0]   # 횡단보도
STOP        = [0, 1, 0]   # STOP 교차로
DECELERATE  = [0, 0, 1]   # 전방 차량 제동
```

위 횡단보도 예의 입력에는 `YIELD=[1,0,0]`이 추가된다. 이것은 `보행자에게 양보한다`는 행동 방향은 알려주지만 다음 내용은 명시하지 않는다.

```text
보행자가 보이거나 가려져 불확실하면 정지선에 진입하지 않는다.
보행자가 conflict zone을 완전히 벗어난 뒤에만 의무를 해제한다.
관측이 불확실하면 정지를 기본값으로 사용한다.
```

### C: 컴파일된 동적 계약 상태 추가

```text
입력  = 10차원 기본 상태 + 3차원 행동 CoC + 6차원 계약 상태
출력  = proposed acceleration
```

계약은 자연어 문자열이 아니라 매 시점 계산되는 다음의 기계 판독 가능한 상태다.

```text
hold_required                : 현재 안전 의무를 계속 유지해야 하는가
release_allowed              : 현재 의무를 해제하고 진행해도 되는가
uncertainty_requires_stop    : 관측 불확실성을 정지로 처리해야 하는가
stop_completion_required     : STOP의 완전 정지가 아직 완료되지 않았는가
safe_margin                  : 요구되는 정지선·차간 여유
max_safe_speed               : 현 상태와 margin에서 허용되는 속도 상한
```

같은 횡단보도 예는 다음과 같이 확장된다.

```text
CoC       : YIELD=[1,0,0]
Contract  : hold_required=1
            release_allowed=0
            uncertainty_requires_stop=0
            stop_completion_required=0
            safe_margin=1.25m
            max_safe_speed≈5.59m/s
```

보행자가 가려지면 `uncertainty_requires_stop=1`이 되고, 보행자가 완전히 통과하고 시야가 확보되면 `hold_required=0`, `release_allowed=1`로 바뀐다. C 정책은 이 정보를 받아 가속도를 제안하지만, 제안값을 반드시 준수하도록 강제되지는 않는다. 따라서 STOP 실험처럼 명시적 계약을 입력으로 받아도 정책이 잘못된 가속도를 출력할 수 있다.

### D: C + 실행 시점 계약 shield

```text
입력 정책  = C와 동일
정책 출력  = proposed acceleration
shield 출력 = executable acceleration
```

shield는 C가 제안한 가속도를 그대로 실행하기 전에 다음 상태와 제동 가능성을 검사한다.

```text
횡단보도·STOP:
  hold_required라면 현재 가속도를 적용한 뒤에도
  최대 제동으로 safe margin 전에 정지할 수 있어야 한다.

선행차:
  ego와 선행차가 제동하더라도 최소 차간 여유를 남길 수 있어야 한다.
```

예를 들어 C가 위 횡단보도 상태에서 `+1.2m/s²`를 잘못 제안하면, shield는 정지 가능 조건을 만족하는 더 작은 가속도 또는 감속값으로 낮춘 뒤 실행한다. 반대로 `release_allowed=1`이고 제안값이 안전 조건을 만족하면 수정하지 않는다.

### 장면별 CoC와 계약의 차이

| 장면 | 행동 CoC가 말하는 것 | 컴파일된 계약이 추가하는 것 |
|---|---|---|
| 횡단보도 | 보행자에게 `YIELD` | 보행자 존재·occlusion 동안 진입 금지, 완전 통과 후 release, 불확실하면 hold |
| STOP 교차로 | 정지선에서 `STOP` | 완전 정지 완료를 기억하고, 교차 차량이 사라지고 시야가 확보될 때까지 hold |
| 전방 급제동 | 선행차 때문에 `DECELERATE` | 동적 safe gap과 허용 속도 상한, 제동 가능 여유를 매 시점 검사 |

## 실험 아키텍처

### 학습 데이터 생성

```text
파라미터형 ID 장면 생성기
  ├─ 횡단보도 200개
  ├─ STOP 교차로 200개
  └─ 전방 제동 200개
             │
             ▼
hand-written contract + contract-aware expert controller
             │
             ▼
성공한 state-action transition 24,984개
             │
       ┌─────┼──────────┐
       ▼     ▼          ▼
   A features  B features  C features
       │         │          │
       ▼         ▼          ▼
   동일 구조의 작은 MLP 정책 3개 학습
   (각 조건을 seed 42, 43, 44로 반복)
```

학습에는 expert가 만든 성공 trajectory만 사용했다. collision이나 금지 상태 진입을 보여주는 negative demonstration은 제공하지 않았다.

### 폐루프 평가

```text
ID 또는 OOD 장면의 현재 상태 s(t)
               │
               ▼
       A/B/C feature composer
               │
               ▼
        tiny policy network
               │
               ▼
      proposed acceleration
               │
         ┌─────┴──────────────┐
         │ A/B/C              │ D
         ▼                    ▼
     바로 실행        contract monitor + shield
                              │
                              ▼
                   executable acceleration
         └────────────┬─────────┘
                      ▼
       1D longitudinal point-mass kinematic world
                      │
                      ▼
       다음 상태 s(t+0.2s) ── 반복 ── 최대 12초
                      │
                      ▼
  forbidden entry / collision / safe-gap violation
  completion / progress / release 후 정지 / jerk / shield 개입
```

ID 평가는 학습과 같은 범위에서 새로 생성한 장면이고, OOD 평가는 보행자·교차 차량의 늦은 해제, occlusion, 선행차의 이른 강제동을 포함한다. 모든 조건과 seed는 동일한 평가 장면을 사용하므로 episode 단위 paired 비교가 가능하다.

### 현재 아키텍처의 중요한 한계

`contract-aware expert`, C의 계약 feature, D의 shield 및 결과 판정이 동일한 hand-written 계약 정의를 공유한다. 따라서 D의 0% 결과는 실제 세계의 독립 안전 증명이 아니라, 주어진 계약을 실행 시점에 강제할 수 있다는 내부 일관성 결과다. 다음 실험에서 계약 실행 코드와 독립된 평가 oracle을 두어 이 순환성을 제거해야 한다.

## 핵심 결과

| 조건 | ID unsafe | OOD unsafe | OOD completion | OOD 평균 progress | OOD jerk | OOD shield 개입 |
|---|---:|---:|---:|---:|---:|---:|
| A 상태 | 0.0% | 26.4% | 99.2% | 28.066 m | 2.607 | 0.000 |
| B 행동 CoC | 0.0% | 38.7% | 100.0% | 28.152 m | 2.007 | 0.000 |
| C 컴파일 계약 | 0.0% | 7.8% | 100.0% | 28.072 m | 3.619 | 0.000 |
| D 계약 + shield | 0.0% | 0.0% | 100.0% | 27.998 m | 3.696 | 2.961 |

A/B가 ID에서 모두 0% unsafe와 100%에 가까운 completion을 보였으므로, OOD 차이를 단순한 모방 학습 실패만으로 설명하기는 어렵다.

## paired episode 분석

동일 장면과 동일 seed의 결과를 직접 비교했다. 총 900 OOD episode다.

- A -> C: unsafe 202건을 제거했지만 34건을 새로 만들었고 36건은 계속 실패했다.
- B -> C: unsafe 316건을 제거했지만 38건을 새로 만들었고 32건은 계속 실패했다.
- C -> D: C의 unsafe 70건을 모두 제거했고 새 unsafe는 없었다.
- 전방 제동의 safe-gap violation은 A -> C에서 55건, B -> C에서 105건이 제거됐고 새 위반은 없었다.

유형별로 보면 결론이 다르다.

- 횡단보도: C는 세 seed에서 unsafe 0%로 일관되게 개선됐다.
- 전방 제동: 모든 조건에서 collision은 없었으나 A/B의 safe-gap violation을 C가 제거했다.
- STOP 교차로: C unsafe가 seed별 26%, 0%, 44%로 불안정했다. 입력에 계약 상태를 제공하는 것만으로 stateful stop 의무를 안정적으로 실행하지 못했다.
- D: 세 유형과 세 seed에서 모두 unsafe 0%였지만, 이 결과는 hand-written shield와 평가 계약이 같은 정의를 공유하므로 부분적으로 construction에 의한 결과다.

## 비용과 비자명성

D는 항상 정지하는 trivial policy가 아니다. OOD completion은 100%였고 C 대비 평균 progress 감소는 약 0.074 m였다. release가 허용된 뒤 정지한 시간은 평균 0.13초였다.

그러나 비용도 존재한다.

- D는 OOD episode당 평균 2.96회 개입했다.
- ID에서도 episode당 1.11회 개입했으며, shield 없이도 ID unsafe는 0%였다. 따라서 불필요하거나 지나치게 보수적인 개입 가능성을 후속 실험에서 분리해야 한다.
- C/D의 jerk가 A/B보다 높다. 안전 제약 준수가 comfort 저하와 교환됐을 가능성이 있다.

## 이 실험이 지지하는 주장

> 성공 시연만 학습한 작은 폐루프 정책은 ID에서는 안전하게 모방하면서도 hold/release 조건이 변한 OOD 장면에서 실패할 수 있다. 동적 계약 상태는 일부 유형에서 이 실패를 줄이지만 stateful STOP 의무에는 불안정하다. 실행 시점 shield는 이 toy world의 명시된 금지 상태를 진행성 붕괴 없이 차단할 수 있다.

## 아직 지지하지 않는 주장

1. 기존 자연어 CoC가 실제로 unsafe trajectory를 유발한다.
2. CoC에서 정확한 안전 계약을 자동 추출할 수 있다.
3. 이 계약이 실제 도로의 완전한 안전 명세다.
4. shield가 독립적인 실제 안전 metric에서 collision을 줄인다.
5. Alpamayo 또는 다른 대형 VLA에서도 같은 효과가 난다.
6. B가 A보다 나빴으므로 CoC가 해롭다. B의 one-hot은 장면 유형과 중복되고 작은 모델의 최적화 변동도 있으므로 그런 결론을 낼 수 없다.

## 다음 증거 게이트

다음 단계에서는 실험의 순환성을 먼저 깨야 한다.

1. 계약 실행 코드와 독립된 평가 oracle을 구현한다.
2. 올바른 계약, 누락 계약, 잘못된 hold/release 계약을 넣는 contract corruption 대조군을 추가한다.
3. STOP을 `approach -> stopped -> hold -> released`의 상태기계로 명시하고 C의 seed 불안정을 재검사한다.
4. 개입 precision, false block, comfort cost를 정식 metric으로 만든다.
5. 이 네 게이트가 통과한 뒤에만 작은 언어모델의 `CoC -> 구조화 계약` 변환을 평가한다.
6. 마지막으로 공개 폐루프 환경으로 옮긴다. restricted NVIDIA 결과는 라이선스상 논문 근거로 바로 사용하지 않는다.

현재 가장 가치 있는 관찰은 “CoC 문장을 더 잘 생성하자”가 아니라 다음이다.

> **행동 설명을 정책 입력으로 주는 것과, 상태를 가지는 안전 의무를 명시하고 실행 시점에 강제하는 것은 서로 다른 문제다.**
