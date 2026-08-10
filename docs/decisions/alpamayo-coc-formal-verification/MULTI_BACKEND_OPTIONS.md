# Alpamayo CoC 검증의 다중 Backend 확장 선택지

> 상태: 비활성 참고안. 현재 연구의 실행 계획은 [STL+CBF 연구 계획 v1](../../plans/alpamayo-coc-formal-verification/RESEARCH_PLAN_V1.md)이다. 이 문서의 SAT/SMT 설계는 주 실험에서 구체적인 표현 한계가 확인된 뒤 필요한 부분만 선택적으로 사용한다.

- 문서 상태: 다음 단계 연구 계획
- 작성일: 2026-08-02
- 대상 모델: revision을 고정한 `nvidia/Alpamayo-R1-10B` 및 후속 호환 모델
- 핵심 방법: UPPAAL 시간 모델 체킹, SAT 기반 유계 모델 체킹, SMT 기반 제약 검증

## 1. 연구 개요

### 1.1 연구의 출발점

기존 단계에서는 회고적으로 생성된 행동 주석과 기록된 자차 움직임을 연속 에피소드로 연결하여 UPPAAL로 검사하였다. 이 과정에서 다음 가능성을 확인하였다.

- 반복 명령의 의미론에 따라 동일한 추적의 판정이 달라질 수 있다.
- 단순 중복 제거가 명령만 삭제하고 반응을 남겨 고아 반응을 만들 수 있다.
- 단일 이벤트 검사는 이전 제어 의무의 유지, 대체, 선점 및 종료를 표현하기 어렵다.
- 형식적으로 실행 가능한 시나리오도 원천 증거가 부족하면 정상 학습 목표가 될 수 없다.

다음 단계에서는 평가 대상을 회고적 행동 주석에서 **Alpamayo가 새로 생성한 Chain-of-Causation(CoC) reasoning trace와 대응 trajectory**로 전환한다. Alpamayo는 다중 카메라 영상과 자차 움직임 이력으로부터 CoC 텍스트와 6.4초 미래 궤적을 함께 출력한다. 공식 공개 구현은 이를 reasoning trace와 trajectory prediction의 결합으로 설명한다.

### 1.2 핵심 문제

CoC는 모델의 판단을 설명하지만 자연어 설명만으로는 다음 질문에 기계적으로 답하기 어렵다.

1. **왜 이 제어가 시작됐는가?**
2. **이 제어는 언제, 어떤 조건에서 끝나야 하는가?**
3. **무엇이 다음 행동을 허용하거나 금지하는가?**

본 연구는 CoC를 이 세 질문에 답하는 **검증 가능한 제어 의무 계약**으로 변환한다. 변환된 계약과 모델이 생성한 trajectory를 UPPAAL, SAT 및 SMT 기반 검증기에 입력하여 reasoning, 제어 전환 및 물리 제약 사이의 불일치를 찾는다.

### 1.3 중심 가설

> Alpamayo CoC를 원인, 의무, 종료 조건, 전환 guard 및 출처를 포함하는 중간 명세로 구조화하면, 궤적 오차나 충돌 결과만으로는 보이지 않는 reasoning-action 불일치, 시간 의무 위반, 잘못된 제어 전환 및 누락된 요구사항을 반례로 발견할 수 있다.

### 1.4 CoC를 모델 체킹에 사용하는 가장 큰 장점

CoC의 가장 강한 역할은 안전 증명 자체가 아니라 **E2E 모델과 형식 검증 사이의 계약 생성 인터페이스**가 되는 것이다.

```text
다중 카메라 영상 + 자차 상태
              |
              v
       Alpamayo inference
       CoC + predicted trajectory
              |
              v
   원인 / 의무 / 종료 / 허용 조건 추출
              |
              v
      공통 Verification IR
        /        |        \
   UPPAAL       SAT       SMT
   시간·전이    유한 분기  수치·논리 제약
        \        |        /
              v
 PASS / FAIL / UNKNOWN + 반례 + 출처
```

Raw 영상과 trajectory만으로는 알기 어려운 제어의 시작 이유, 유지 기간, 종료 조건 및 다음 행동 허용 조건을 CoC가 명시 후보로 제공한다. 그 결과 모델 체커의 반례를 사람이 이해할 수 있는 원인과 의무의 언어로 설명할 수 있다.

### 1.5 현재 증거 기준선

- NVIDIA 공식 reasoning annotation과 주행 데이터를 사용한 내부 UPPAAL feasibility는 완료하였다.
- 기존 결과는 annotation 및 기록 trajectory 검증이며 Alpamayo 모델 출력의 안전성 평가가 아니다.
- 실제 `nvidia/Alpamayo-R1-10B` 출력 생성은 [ALP-EXP-005 원격 실행 패키지](../../../experiments/alpamayo/ALP-EXP-005-REMOTE-RUNBOOK.md)가 준비된 상태이다.
- 따라서 이 계획의 첫 실증 게이트는 모델이 새로 생성한 CoC와 predicted trajectory 원본을 확보하고 provenance validator를 통과하는 것이다.
- 공식 데이터와 모델 출력의 원문 및 파생 수치는 라이선스 제한 내부 경로에만 저장한다.

## 2. 연구 목적

### 목적 P1: Alpamayo 출력의 검증 가능성 확보

Alpamayo가 생성한 자유 형식 CoC와 trajectory를 재현 가능한 구조화 데이터로 변환하고, 모든 추출 필드를 입력 프레임, 모델 revision, 생성 seed 및 trajectory 시점으로 역추적할 수 있게 한다.

### 목적 P2: 판단과 제어의 인과 및 시간 일관성 검증

CoC가 주장한 원인이 실제 과거 관측에 존재하는지, 그 원인이 해당 제어를 유발하는지, 생성 trajectory가 선언된 행동을 기한 내 이행하는지 검사한다.

### 목적 P3: 연속 제어 수명주기 검증

제어를 단일 행동 레이블이 아니라 `시작 → 대기 → 이행 → 유지 → 종료 → 다음 행동 허용`의 수명주기로 모델링한다. 반복, 중첩, 선점 및 복구를 포함한 연속 사건에서 의무가 유실되거나 잘못 초기화되는지 검사한다.

### 목적 P4: 자연어 명세의 누락과 모호성 발견

CoC를 계약으로 변환할 수 없는 이유 자체를 결과로 기록한다. 시작 기한, 종료 조건, clearance 정의, 선점 우선순위 또는 객체 식별이 빠진 CoC를 `SPECIFICATION_INCOMPLETE`로 분류한다.

### 목적 P5: 검증 결과의 학습 활용 가능성 평가

검증 결과를 약한 양성, 조건부 hard negative, 재라벨링, 격리 및 변이 전용 데이터로 분리한다. 반례가 존재한다는 이유만으로 반례 trajectory를 올바른 대안 행동으로 사용하지 않는다.

## 3. 연구 목표와 성공 기준

| 목표 | 내용 | 1차 성공 기준 |
|---|---|---|
| G1 | Alpamayo 출력 생성 및 고정 | 3개 이상 seed에서 비어 있지 않은 CoC와 64 waypoint trajectory, 완전한 manifest 확보 |
| G2 | 구조화 CoC 변환 | 원인, 결정, 행동, 종료, 다음 행동 guard를 갖는 IR 생성률 측정 |
| G3 | 의미적 grounding | CoC 핵심 객체와 사건을 과거 관측 또는 obstacle track에 연결하고 미확인 항목은 UNKNOWN 처리 |
| G4 | 시간 모델 생성 | 단일 이벤트와 연속 에피소드 UPPAAL 모델 자동 생성 및 모든 모델의 출처 포인터 보존 |
| G5 | SAT/SMT 교차 검증 | 변이 오라클에서 기대 SAT/UNSAT 결과와 도구 판정이 일치 |
| G6 | 실제 모델 오류 후보 발견 | reasoning-action 불일치, 기한 위반, 조기 복구 또는 명세 누락 후보를 추적 가능한 형태로 확보 |
| G7 | 학습 경로 지정 | 각 표본을 근거와 계약 강도에 따라 학습, 검토 또는 격리 경로로 자동 분류 |

1차 연구의 성공은 Alpamayo가 안전하다고 증명하는 것이 아니다. **실제 모델 출력으로부터 검증 가능한 계약과 재현 가능한 반례를 생성할 수 있음을 보이는 것**이 성공 기준이다.

## 4. 연구 질문

### RQ1: 계약 추출 가능성

Alpamayo가 생성한 CoC 중 어느 비율에서 원인, 제어 의무, 종료 조건 및 다음 행동 허용 조건을 명시적으로 추출할 수 있는가?

### RQ2: 의미적 근거

CoC가 언급한 객체와 위험은 판단 시점 이전의 영상 또는 객체 추적에 실제로 존재하는가? 미래 trajectory나 미래 프레임을 원인으로 재사용하는 인과적 누출은 없는가?

### RQ3: reasoning-action 일관성

CoC가 선언한 감속, 정지, 양보, 가속, 차선 유지 또는 회피 행동과 생성 trajectory의 속도 및 곡률 변화가 일치하는가?

### RQ4: 연속 시간 의무

반복 또는 중첩된 CoC가 최초 미해결 의무를 보존, 대체, 선점 또는 종료하는 규칙은 무엇이며, 그 규칙 아래에서 기한과 순서 속성이 유지되는가?

### RQ5: 다음 행동 허용 조건

위험 해소, 보행자 이탈, 신호 변경, 우선권 획득 또는 최소 정지 시간과 같은 clearance 조건이 확인되기 전에 속도 회복이나 차선 변경이 발생하는가?

### RQ6: 도구별 증거 차이

UPPAAL, SAT 및 SMT가 각각 어떤 종류의 위반을 가장 효과적으로 발견하며, 동일 IR에서 판정 불일치가 발생할 때 그 원인은 추상화, bound 또는 수치 이론 중 무엇인가?

### RQ7: 학습 활용

검증 기반 선별과 조건부 hard negative가 reasoning-action consistency와 폐루프 위반율을 개선하는가?

## 5. 검증 대상의 구조화

### 5.1 Alpamayo 출력 단위

공식 모델의 한 추론 결과에서 다음 항목을 고정한다.

- 모델 ID와 revision
- 코드 및 데이터 revision
- `clip_id`, 기준 시각 `t0_us`
- 입력 카메라, 프레임 및 타임스탬프
- 자차 움직임 이력
- 생성 seed 및 decoding 설정
- 생성 CoC 원문
- 예측 6.4초 trajectory와 rotation
- 비교 가능한 경우 ground-truth trajectory

### 5.2 Verification IR

자유 형식 CoC를 다음 구조로 변환한다.

```yaml
event_id: alp-event-0001
trigger:
  entity: pedestrian_17
  predicate: entering_ego_path
  observed_interval: [t0-0.8, t0]
  evidence_refs: [camera_front_wide:frame_42, track:pedestrian_17]
decision:
  class: YIELD
obligation:
  action: DECELERATE
  start_condition: pedestrian_entering_path
  response_condition: longitudinal_acceleration <= -a_min
  deadline: D_brake
  maintain_while: pedestrian_present
termination:
  condition: pedestrian_cleared_with_margin
  minimum_hold: T_hold
next_action:
  action: RESUME_SPEED
  permitted_when: pedestrian_cleared_with_margin
  prohibited_while: pedestrian_present
preemption:
  higher_priority: [EMERGENCY_BRAKE]
provenance:
  trigger: OBSERVED_OR_GROUNDED
  action: MODEL_GENERATED
  deadline: REQUIREMENT_OR_ASSUMPTION
```

### 5.3 필수 필드와 선택 필드

필수 필드:

- 판단 기준 시각
- 원인 객체 또는 사건
- 요청 행동
- 행동의 시작 또는 탐지 조건
- 출처와 신뢰도

시간 계약에 필요한 필드:

- 반응 기한
- 유지 조건
- 종료 조건
- 다음 행동 guard
- 반복 및 선점 정책

필드가 없으면 임의로 채우지 않는다. 외부 요구사항에서 가져오면 `NORMATIVE_REQUIREMENT`, 실험 가정이면 `SYNTHETIC_ASSUMPTION`, 데이터에서 도출하면 `DERIVED`로 구분한다.

## 6. 검증 속성

### 6.1 왜 제어가 시작됐는가

#### P-TRIGGER-1: 과거 관측 근거

```text
ControlStarted(action, t0)
  -> ExistsGroundedCause(cause, [t0-H, t0])
```

- CoC가 언급한 객체가 과거 관측에 존재해야 한다.
- 해당 객체가 ego path 또는 의사결정 영역과 관련되어야 한다.
- 미래 trajectory의 결과를 원인으로 사용하면 실패 또는 검토로 분류한다.

#### P-TRIGGER-2: 원인과 행동의 규칙 일관성

```text
PedestrianEnteringPath AND EgoHasYieldDuty
  -> RequiredAction in {DECELERATE, YIELD, STOP}
```

- 규칙과 행동이 직접 모순되는지 SMT로 검사한다.
- 규칙 집합 자체가 모순되면 unsat core로 충돌한 요구사항을 보고한다.

### 6.2 언제 끝나야 하는가

#### P-RESP-1: 제한 시간 반응

```text
TrustedTrigger --> DirectionalResponse within D_response
```

#### P-MAINTAIN-1: 위험 지속 중 의무 유지

```text
PedestrianPresent --> not ResumeSpeed
```

#### P-TERM-1: 종료의 필요조건

```text
ObligationCompleted
  -> ResponseSatisfied OR ExplicitlyPreempted OR HazardCleared
```

#### P-TERM-2: 불필요한 지속 방지

```text
HazardCleared AND ResumePermitted
  --> LeaveHold within D_progress
```

안전만 검사하면 차량이 영원히 정지하는 모델도 통과할 수 있으므로 종료와 진행성 속성을 함께 둔다. 단, 진행성은 안전 조건보다 낮은 우선순위를 갖는다.

### 6.3 무엇이 다음 행동을 허용하는가

#### P-GUARD-1: clearance 전 복구 금지

```text
ResumeSpeed -> PedestrianClearedWithMargin
```

#### P-GUARD-2: 차선 변경 허용 조건

```text
ChangeLane -> TargetLaneFree AND GapAcceptable AND NoHigherPriorityObligation
```

#### P-PREEMPT-1: 긴급 의무의 우선순위

```text
EmergencyBrake
  -> preempt LowerPriorityLongitudinalActions
```

#### P-LINEAGE-1: 명령과 반응 계보

```text
response_count <= accepted_obligation_count
```

중복 제거, 병합 또는 선점 시 명령과 대응 반응 계보를 원자적으로 갱신한다.

### 6.4 reasoning과 trajectory의 일관성

```text
CoC says DECELERATE
Predicted trajectory has sustained speed increase
=> REASONING_ACTION_INCONSISTENCY
```

확장 속성:

- CoC의 종방향 행동과 trajectory 속도 변화 부호
- CoC의 좌우 회피와 trajectory 곡률 부호
- STOP/HOLD와 정지 속도 및 유지 시간
- RECOVER와 clearance 이후의 속도 회복
- 복합 행동의 순서 및 동시 수행 가능성

### 6.5 물리 안전 속성

객체 상대 상태와 차량 동역학이 확보된 경우에만 활성화한다.

```text
stopping_margin =
    observed_gap
  - response_distance
  - ego_braking_distance
  + lead_braking_distance
  - uncertainty_margin

P-PHYS-1: always stopping_margin >= 0
P-PHYS-2: requested_control in feasible_control_set
P-PHYS-3: no collision within bounded horizon
```

고정 `D=1s`, `D=2s` 또는 `D=3s`를 보편적 안전 기한으로 사용하지 않는다. 기한은 요구사항 또는 상태 의존 stopping margin에서 정당화한다.

## 7. 증명 및 반례 탐색 방법

### 7.1 공통 원칙

세 방법은 경쟁 관계가 아니라 서로 다른 추상화 계층을 담당한다.

| 방법 | 주요 대상 | 강점 | 판정의 경계 |
|---|---|---|---|
| UPPAAL | 실수 시계, 동시 automata, 반복·선점·순서 | 연속 의무의 전 경로 시간 검증과 진단 추적 | 주어진 timed abstraction 안에서만 유효 |
| SAT/BMC | 유한 단계의 이산 모드, 규칙 선택, 사건 순서 | 짧은 최소 반례와 조합 폭발 탐색 | `UNSAT`은 선택한 bound 안의 반례 부재 |
| SMT/Z3 | 정수·실수 산술, 객체 관계, trajectory 제약 | 논리·수치 제약의 통합 및 unsat core | 인코딩한 이론과 구간 안에서만 유효 |
| SMT/dReal 확장 | 비선형 실수 함수와 제한된 동역학 | 비선형 물리식의 `unsat`/`delta-sat` 검사 | `delta-sat`은 완화된 식의 witness |

### 7.2 UPPAAL의 역할

UPPAAL은 다음을 검증한다.

- 판단, 반응 및 clearance의 시간 순서
- 반복 명령의 Preserve/Reset/Replace 의미론
- 병렬 종방향 및 횡방향 의무
- 긴급 제동의 선점
- 기한 초과, 데드락, livelock 및 진행성
- 저품질 또는 비grounded CoC의 신뢰 상태 덮어쓰기

주요 질의 예:

```text
A[] not DeadlineMiss
A[] not PrematureResume
A[] response_count <= obligation_count
PedestrianCleared --> ResumePermitted
A[] not deadlock
```

### 7.3 SAT 기반 유계 모델 체킹의 역할

상태 전이 관계를 $k$단계까지 펼치고 위반 상태가 존재하는지를 Boolean 식으로 변환한다.

```text
Initial(s0)
AND Transition(s0,s1)
AND ...
AND Transition(s[k-1],sk)
AND Violation(s0...sk)
```

- `SAT`: $k$단계 안에 위반 실행이 존재하며 할당값이 반례가 된다.
- `UNSAT`: 선택한 $k$ 안에는 위반 실행이 없다.
- 완전성 임계값 또는 귀납 증명이 없으면 전역 안전 증명으로 표현하지 않는다.

SAT가 특히 유용한 문제:

- 복합 CoC의 가능한 사건 순서 열거
- 선점 우선순위 조합
- 중복 제거, 대체 및 병합 정책 비교
- 최소 위반 접두 추적 탐색
- 변이 오라클의 대규모 조합 시험

### 7.4 SMT/Z3의 역할

Z3에는 다음 제약을 인코딩한다.

- CoC 원인 객체와 관측 객체의 동일성 및 시간 구간 관계
- 교통 규칙, 우선권 및 행동 허용 집합
- trajectory waypoint에서 계산한 속도, 가속도 및 곡률
- 기한, 유지 시간, 최소 간격 및 제어 한계
- 동시에 활성화할 수 없는 의무 간 모순

대표 질의:

```text
Assumptions
AND CoCClaims
AND TrafficRules
AND PredictedTrajectory
AND NOT RequiredProperty
```

- `SAT`: 제약을 만족하면서 속성을 위반하는 witness가 존재한다.
- `UNSAT`: 선언된 가정과 이론 안에서는 해당 위반이 존재하지 않는다.
- `UNKNOWN`: 비선형식, timeout 또는 지원하지 않는 이론 때문에 결론을 내리지 못한다.

SMT의 중요한 추가 출력은 unsat core다. 이를 사용해 자연어 계약 변환에서 서로 충돌하는 원인, 규칙, 기한 또는 전환 guard의 최소 집합을 찾는다.

### 7.5 비선형 물리 확장

Z3의 선형 실수 산술로 충분하지 않은 제동 거리, 마찰 또는 ODE 모델은 dReal 또는 별도의 hybrid reachability 단계로 분리한다.

- `unsat`: 지정한 식과 구간에서 위반 상태가 존재하지 않음
- `delta-sat`: 수치 오차 $\delta$로 완화한 식에서 witness 후보가 존재
- 물리 검증 결과는 timed protocol PASS와 별도 certificate로 보고

### 7.6 신경망 자체 검증의 선택적 확장

Alpamayo 전체 영상 입력 공간을 직접 검증하는 것은 초기 범위가 아니다. 검증 가능한 저차원 action expert 또는 trajectory decoder를 ONNX로 분리할 수 있을 때 Marabou 같은 SMT 기반 신경망 검증기로 제한된 입력 구간의 출력 경계를 검사한다.

## 8. 도구 간 통합 구조

### 8.1 단일 소스 Verification IR

모든 backend는 같은 IR에서 생성한다.

```text
CoC + trajectory + observations + requirements
                     |
                     v
             Verification IR
          /          |          \
 UPPAAL compiler  SAT compiler  SMT compiler
          \          |          /
                     v
         normalized evidence report
```

각 backend 결과에는 다음을 공통으로 기록한다.

- property ID
- source event 및 evidence pointer
- assumption set
- abstraction version
- bound 또는 horizon
- solver와 version
- PASS/FAIL/UNKNOWN
- witness, counterexample 또는 unsat core
- 가장 강하게 허용되는 주장

### 8.2 교차 검증

동일 속성을 두 방식으로 표현할 수 있는 작은 모델을 선택해 판정을 비교한다.

- UPPAAL의 `PrematureResume` 도달성과 SAT BMC의 유계 위반식 비교
- UPPAAL의 deadline miss와 SMT의 waypoint 시간 제약 비교
- 판정이 다르면 시간 이산화, strict/non-strict 부등식, bound 및 guard 의미론을 감사

교차 검증은 한 도구의 결과를 다른 도구가 자동으로 보증한다는 뜻이 아니다. 인코딩 오류와 추상화 차이를 발견하기 위한 독립적인 일관성 검사다.

## 9. 실험 설계

### 9.1 WP0: 실제 Alpamayo 출력 생성

기존 [ALP-EXP-005 원격 실행 패키지](../../../experiments/alpamayo/ALP-EXP-005-REMOTE-RUNBOOK.md)를 사용한다.

- 기준 seed 42 및 replication seed 43, 44
- 동일 clip과 입력 조건 유지
- CoC 원문, predicted trajectory, GT trajectory 및 manifest를 제한 디렉터리에 저장
- 빈 CoC, NaN/Inf, waypoint 수 및 revision을 검증
- CoC 전문과 제한 데이터를 공개 저장소에 노출하지 않음

### 9.2 WP1: CoC parser와 schema validator

- 결정, 핵심 원인, 행동, 예상 결과를 추출
- 유지 조건, 종료 조건 및 다음 행동 guard를 별도로 추출
- 구조화할 수 없는 표현을 자동 보완하지 않고 누락 필드로 보고
- 소규모 표본에 대해 두 명 이상의 인간 검토로 parser 정확도 평가

### 9.3 WP2: semantic grounding

- CoC 객체를 과거 카메라 프레임 및 `obstacle.offline` track과 연결
- 객체 유형, 위치, 진행 방향, ego path와의 관계를 확인
- nearest object를 자동으로 원인 객체로 확정하지 않음
- 미확인 객체는 `GROUNDING_UNKNOWN` 처리

### 9.4 WP3: reasoning-trajectory consistency

- predicted trajectory에서 속도, 가속도, yaw 및 곡률 계산
- CoC 행동 클래스를 정량 trajectory predicate로 변환
- seed별 CoC와 trajectory 조합의 일관성 비교
- 같은 입력에서 reasoning과 trajectory가 함께 변하는지, 서로 독립적으로 흔들리는지 분석

### 9.5 WP4: 연속 에피소드 UPPAAL 검증

- 한 추론 시점의 CoC만 보지 않고 겹치는 연속 inference 출력을 연결
- stale reasoning, 반복 의무, 선점 및 clearance를 모델링
- Preserve, Reset, Replace 및 Deduplicate 의미론 비교
- 기한과 detector profile 민감도 보고

### 9.6 WP5: SAT/SMT 반례 탐색

- $k$단계 사건 순서와 선점 정책을 SAT BMC로 탐색
- CoC, 교통 규칙 및 trajectory 산술 제약을 Z3로 검사
- mutation suite로 solver oracle 검증
- 가능한 경우 최소 반례와 최소 unsat core 생성

### 9.7 WP6: 환경 분기와 물리 계층

다음 불확실성을 유계 비결정 분기로 추가한다.

- 보행자가 계속 횡단, 정지 또는 후퇴
- clearance 센서 보고 지연
- 새 차량의 cut-in
- 제동 응답 및 build-up 지연
- 마찰, 경사 및 최대 감속 범위
- 객체 추적 오차와 timestamp 오차

물리 근거가 없는 범위는 합성 sensitivity profile로 표시하고 실제 장면의 안전 판정을 생성하지 않는다.

### 9.8 WP7: 학습 연결

검증 결과를 다음과 같이 경로 지정한다.

| 검증 결과 | 학습 활용 |
|---|---|
| CoC grounded, 계약과 trajectory 일치 | 약한 positive 후보 |
| 정당화된 계약 위반, 대안 행동 별도 검증 | 조건부 hard negative 또는 preference pair |
| CoC와 trajectory 불일치 | reasoning-action consistency 학습 후보 |
| CoC 구조 또는 grounding 불충분 | 재라벨링 또는 인간 검토 |
| 물리적으로 실행 불가능한 trajectory | 학습 제외 또는 feasibility penalty |
| 출처 불명확 | 격리 |
| 의미론에 따라 판정 변경 | human review 및 요구사항 확정 |
| 합성 mutation | 위반 탐지기와 검사기 시험 전용 |

## 10. 변이 및 반례 카탈로그

### CoC 변이

- 원인 객체 교체 또는 삭제
- 판단과 행동의 부호 반전
- 종료 조건 삭제
- clearance 조건을 모호한 표현으로 치환
- 반복 명령을 새 의무로 변경
- 더 높은 우선순위 의무 삭제

### trajectory 변이

- 반응 삭제
- 반응 지연 삽입
- 감속 reasoning에 가속 trajectory 연결
- clearance 전 속도 회복
- 조향 방향 반전
- 물리 한계를 초과하는 가속도 또는 곡률 삽입

### 에피소드 변이

- 사건 순서 교환
- 이전 의무의 clock 초기화
- 명령만 중복 제거하고 반응 유지
- 저신뢰 CoC가 신뢰 의무를 덮어쓰기
- 긴급 제동과 일반 가속을 동시에 유지
- terminal state의 잘못된 deadlock 처리

변이 검출률은 모델 안전 지표가 아니라 **검증 파이프라인 구현의 오라클 일치도**로 보고한다.

## 11. 평가 지표

### 변환 품질

- CoC schema 완전성
- 필수 필드 추출률
- 인간 검토 대비 action/trigger/termination 정확도
- provenance coverage

### 검증 품질

- 모델 및 solver 실행 성공률
- mutation oracle 검출률
- backend 간 판정 일치율
- 반례 최소 길이와 인간 재현 가능성
- timeout 및 UNKNOWN 비율
- property별 실행 시간과 상태 공간 크기

### 모델 출력 품질

- semantic grounding 성공률
- reasoning-action inconsistency 비율
- deadline 및 transition violation 비율
- seed 간 CoC 구조 변화와 trajectory pairwise ADE
- closed-loop에서 재현된 반례 비율

### 학습 효과

- held-out reasoning-action consistency
- held-out 계약 위반율
- 폐루프 충돌, TTC, off-road 및 close-encounter 지표
- comfort 및 progress 회귀
- 기존 반례의 재발률과 새로운 반례 발견률

## 12. 단계별 실행 계획과 게이트

### 단계 A: 단일 출력 feasibility

- Alpamayo 실제 출력 1개와 seed replication 확보
- CoC와 trajectory의 기본 일관성 검사
- 성공 게이트: 완전한 provenance와 비어 있지 않은 결과

### 단계 B: 구조화 계약 feasibility

- 5개에서 10개 모델 출력에 IR 생성
- 보행자, 신호, 선행 차량, cut-in 등 서로 다른 의무 포함
- 성공 게이트: 원인, 행동, 종료, 다음 guard의 누락률과 parser 오류를 정량 보고

### 단계 C: 다중 backend 검증

- 같은 핵심 속성을 UPPAAL, SAT 및 SMT로 표현
- 변이 suite와 교차 검증 수행
- 성공 게이트: 사전 오라클과 판정 일치, 불일치 원인 설명 가능

### 단계 D: 연속 inference episode

- 겹치는 시점의 Alpamayo 출력을 하나의 episode로 연결
- stale reasoning, 반복 및 선점을 검증
- 성공 게이트: 최소 하나 이상의 상태 기반 반례 또는 모든 property의 근거 있는 PASS/UNKNOWN 보고

### 단계 E: 물리 및 폐루프 확장

- 객체 상대 상태, 차량 동역학 및 sensor delay 범위 추가
- UPPAAL 반례를 AlpaSim 또는 다른 폐루프 시뮬레이터에서 재생
- 성공 게이트: 추상 반례와 시뮬레이션 재현 여부를 구분하여 보고

### 단계 F: 검증 유도 학습

- 검증 결과를 이용한 SFT, preference 또는 violation-head 학습
- 독립 holdout에서 전 과정을 재실행
- 성공 게이트: 모방 성능과 진행성을 심각하게 훼손하지 않으면서 검증 및 폐루프 위반 감소

## 13. 예상 연구 기여

### 기여 C1: CoC-to-Contract compiler

Alpamayo CoC를 시작 원인, 유지 의무, 종료 조건 및 다음 행동 guard로 변환하는 출처 추적형 중간 표현과 컴파일러를 제안한다.

### 기여 C2: 다중 검증 backend

같은 Verification IR에서 UPPAAL, SAT 및 SMT 모델을 생성하여 시간 전이, 이산 조합 및 수치 제약을 역할별로 검증한다.

### 기여 C3: 과정 수준 반례

충돌 발생 여부 이전에 잘못된 판단, 늦은 반응, 조기 복구, 의무 유실 및 reasoning-action 불일치를 설명 가능한 반례로 제시한다.

### 기여 C4: 자연어 명세 품질 진단

계약 변환 실패와 unsat core를 사용하여 CoC annotation에 필요한 종료, clearance, 선점 및 기한 필드를 제안한다.

### 기여 C5: 검증 결과의 안전한 학습 활용

반례를 곧바로 정상 행동 정답으로 사용하지 않고 provenance와 계약 강도에 따라 학습 경로를 제한하는 절차를 제안한다.

## 14. 위험과 대응

| 위험 | 영향 | 대응 |
|---|---|---|
| CoC가 자유 형식이고 필드가 누락됨 | 계약 자동 생성 실패 | 불완전 명세 판정과 human-in-the-loop 구조화 |
| CoC 원인 객체의 grounding 실패 | 잘못된 트리거 계약 | 과거 관측 제한, track association, UNKNOWN 유지 |
| 고정 deadline의 자의성 | 허위 안전 위반 | 요구사항 기반 또는 상태 의존 margin, 민감도 분석 |
| SAT/SMT의 bound 의존성 | UNSAT 과대해석 | bound와 completeness 조건을 결과에 명시 |
| UPPAAL 추상화 오류 | 공허한 PASS 또는 거짓 반례 | mutation oracle, reachability prerequisite, backend 교차 검사 |
| 비선형 물리 모델 비용 | timeout 또는 부정확한 단순화 | 종방향 대표 계약부터 시작하고 dReal/hybrid 검증 분리 |
| 제한 데이터 라이선스 | 결과 공개 불가 | restricted artifact, 공개용 합성 예, 승인 게이트 |
| 모델 seed 변화 | 결과 선택 편향 | 성공과 실패 seed 모두 보존하고 replication 보고 |

## 15. 주장 및 판정 경계

### 주장할 수 있는 것

- 특정 Alpamayo revision과 입력에서 생성된 CoC 및 trajectory의 계약 준수 여부
- 명시된 시간, 반복, 선점 및 환경 추상화에서의 UPPAAL 속성 결과
- 선택한 bound 안의 SAT 반례 존재 또는 부재
- 선언한 SMT 이론과 제약 아래의 SAT/UNSAT/UNKNOWN
- 출처가 연결된 reasoning-action 및 프로토콜 반례

### 주장할 수 없는 것

- CoC 내용이 실제 세계에서 항상 참이라는 증명
- Alpamayo 모델 전체 입력 공간의 안전성
- 충돌이 없는 단일 trajectory가 정책 안전성을 증명한다는 주장
- 합성 deadline과 차량 파라미터를 이용한 실제 차량 인증
- finite bound의 UNSAT을 무조건적인 전역 안전 증명으로 해석
- 모델 체커 반례를 올바른 대안 궤적으로 간주

### 최종 판정 체계

- `PASS`: 명시된 모델, 가정, bound 및 속성에서 위반이 없음
- `FAIL`: 추적 가능한 위반 witness 또는 counterexample 존재
- `UNKNOWN`: grounding, 요구사항, 물리 입력 또는 solver 결론이 부족
- `SPECIFICATION_INCOMPLETE`: 시작, 종료 또는 다음 행동 guard를 구성할 필드가 부족
- `REVIEW_REQUIRED`: 의미론 또는 계약 권위에 따라 판정이 달라짐

## 16. 필수 산출물

```text
docs/plans/alpamayo-coc-formal-verification/
  RESEARCH_PLAN_V1.md
  schemas/
    verification-ir.schema.json
    evidence-report.schema.json
  properties/
    property-catalog.yaml
  examples/
    pedestrian-yield.example.yaml
  compiler/
    coc_to_ir.py
    ir_to_uppaal.py
    ir_to_sat.py
    ir_to_smt.py
  tests/
    mutation-oracle.yaml
  reports/
    feasibility-summary.md
```

모델 출력 원문, 제한 데이터 및 trajectory 배열은 이 공개 설계 폴더가 아니라 접근 통제된 기존 `artifacts/results/restricted` 또는 `internal-derived` 경로에 저장한다.

## 17. 첫 번째 실행 실험

가장 작은 실행 단위는 다음과 같다.

1. `ALP-EXP-005`에서 Alpamayo 출력 1개와 seed 3개를 생성한다.
2. CoC에서 하나의 명확한 종방향 의무를 추출한다.
3. predicted trajectory에서 속도와 가속도 시계열을 계산한다.
4. `왜 시작됐는가`, `언제 끝나는가`, `무엇이 다음 행동을 허용하는가`를 IR에 기록한다.
5. UPPAAL로 반응 기한, 유지 및 조기 복구를 검사한다.
6. SAT로 $k$단계 안의 잘못된 전환 순서를 탐색한다.
7. Z3로 CoC 행동과 trajectory 산술 제약의 모순을 검사한다.
8. 반응 삭제, 지연 및 clearance 전 복구 변이를 주입해 오라클을 확인한다.
9. 모든 결과를 PASS/FAIL/UNKNOWN과 출처 포인터로 보고한다.

이 실험이 성공하면 5개에서 10개 clip, 연속 inference episode, 물리 상태 및 폐루프 재생 순으로 확장한다.

## 18. 근거 자료

- [NVIDIA Alpamayo 공식 저장소](https://github.com/NVlabs/alpamayo): 공개 모델은 CoC reasoning trace와 trajectory를 함께 출력하며, 연구 및 평가 목적의 도구임을 명시한다.
- [Alpamayo-R1-10B 공식 모델 카드](https://huggingface.co/nvidia/Alpamayo-R1-10B): 입력 형식, CoC 텍스트 출력, 6.4초 64-waypoint trajectory 및 데이터 구성을 설명한다.
- [Alpamayo-R1 논문](https://arxiv.org/abs/2511.00088): CoC, trajectory planning 및 reasoning-action consistency 학습의 연구 배경을 제시한다.
- [UPPAAL symbolic query 문서](https://docs.uppaal.org/language-reference/query-syntax/symbolic_queries/): timed automata의 전 경로, 존재 경로, 도달성 및 leads-to query 의미론을 정의한다.
- [Z3 공식 가이드](https://microsoft.github.io/z3guide/docs/logic/intro/): SAT/SMT 기반 논리 및 산술 제약의 만족 가능성 검사를 설명한다.
- [Bounded Model Checking](https://www.cs.cmu.edu/~svc/papers/view-publications-bccsz03.html): 전이 시스템을 유한 깊이로 펼쳐 SAT로 반례를 탐색하는 기반 방법이다.
- [dReal 공식 문서](https://dreal.github.io/): 비선형 실수식의 `unsat` 및 `delta-sat` 의미를 설명한다.
- [Marabou 공식 문서](https://neuralnetworkverification.github.io/): 제한된 신경망 입출력 속성에 대한 SMT 기반 검증 확장에 사용한다.

## 19. 최종 요약

이 연구는 Alpamayo가 생성한 CoC를 설명문으로 평가하는 데서 멈추지 않는다. CoC를 제어 의무의 중간 명세로 바꾸어 다음을 검증한다.

```text
왜 시작됐는가  = 과거 관측에 근거한 trigger와 규칙
언제 끝나는가  = 반응 기한, 유지 조건, 종료 조건
무엇이 허용하는가 = clearance, 우선권, 선점 및 물리 guard
```

UPPAAL은 시간과 연속 전환을, SAT는 유한 이산 반례를, SMT는 논리 및 수치 제약을 담당한다. 세 방법의 결과를 공통 출처 체계로 묶으면, 사고가 발생하지 않은 장면에서도 사고로 이어질 수 있는 잘못된 의사결정 과정과 누락된 명세를 조기에 발견할 수 있다. 다만 어떤 solver도 CoC가 현실에서 참임을 자동으로 증명하지 않으므로 semantic grounding, reasoning-action consistency 및 physical safety를 분리하여 검증해야 한다.
