# CoC–KG–UPPAAL 기반 자율주행 결론 모델체킹 설계

- 작성일: 2026-07-31
- 상태: 취약점 분석 및 개선 요구사항 반영
- 대상: NVIDIA Alpamayo 계열의 Chain of Causation(CoC) 추론과 그에 대응하는 차량 궤적

## 1. 목적

본 연구는 자율주행 VLA가 생성한 CoC를 자연어 설명으로만 평가하지 않고, provenance가 있는 지식그래프(KG) 명세로 변환한 뒤 UPPAAL timed automata와 query를 자동 생성하여 형식적으로 검증하는 방법을 설계한다. 검증 범위는 충돌 회피 같은 안전성에 한정하지 않는다. Verification IR에 명시적으로 포함된 환경 변화와 시간 지연 전체에서 차량이 위험에 제때 반응하는지, 안전해진 후 진행을 재개하는지, 불필요하게 느리거나 정지해 있지 않은지도 함께 검사한다.

핵심 명제는 다음과 같다.

> CoC의 관측 사실, 인과 주장, 주행 결정을 KG로 정규화하고, KG에서 timed-automata 네트워크와 안전성·반응성·진행성·서비스 품질 query를 생성하여 UPPAAL로 가능한 실행 경로 전체를 모델체킹한다.

본 연구에서 “CoC 결론의 정합성”은 두 층으로 구분한다.

1. **정적 의미 정합성:** CoC의 객체·관측·규칙·결론이 KG에서 grounding되고 서로 직접 모순되지 않는가.
2. **시간적 운영 정합성:** 그 결론이 허용된 결정 상태로 이어지고, 모든 모델링된 환경 분기와 시간 지연에서 안전하고 제때 실행되는가.

초기 연구의 형식 검증 중심은 2번이다. 일반 SMT 이론에 대한 순수 논리 함의 증명은 Z3를 사용하는 선택적 확장으로 분리한다.

## 2. 연구 질문

1. CoC가 언급한 객체와 사건은 과거 관측 구간에 실제로 존재하는가?
2. CoC의 주행 결정은 관측에 grounding되며 적용 규칙에서 허용되거나 요구되는가?
3. CoC 결론을 반영한 결정 모델은 허용된 차량 행동에 도달 가능한가?
4. 모델에 허용된 환경 분기와 시간 지연 전체에서 그 행동은 안전하면서도 충분히 신속하고 진행성이 있는가?
5. 기록된 미래 궤적은 검증된 추상 행동과 시간 계약을 실제로 이행하는가?
6. 검증 실패 시 어떤 KG 사실·규칙·automaton 전이·시간 제약이 반례 경로를 구성하는지 추적 가능하게 제시할 수 있는가?

## 3. 범위

### 포함 범위

- 공개 Alpamayo CoC 라벨과 동일 클립의 영상·egomotion·미래 궤적
- 과거 관측에 대한 객체·상태·관계의 KG 표현
- CoC 자연어의 구조화 및 관측 KG와의 grounding
- 교통 규칙과 사용자 주행 선호의 명세
- KG에서 UPPAAL extended timed automata와 symbolic query 생성
- 환경·차량·규칙·시간 관찰자 automata의 합성
- UPPAAL symbolic model checking과 diagnostic counterexample trace 생성
- 기록 궤적을 사건 열로 변환한 trace replay/conformance 검사
- 속성별 PASS, FAIL, UNKNOWN 판정과 전체 `REJECT`, `REVIEW`, `SAFE_BUT_UNSATISFACTORY`, `ACCEPT` 집계
- UPPAAL SMC를 이용한 확률적·하이브리드 성능 평가 확장

### 제외 범위

- 전체 신경망의 모든 입력에 대한 완전한 수학적 검증
- 실제 차량 배포를 승인하는 automotive-grade safety case
- perception 모델의 종단간 정확성 증명
- 자연어 CoC가 인간의 실제 내부 추론 과정과 동일하다는 심리적 의미의 증명
- 공개되지 않은 Alpamayo 내부 학습 데이터의 재현

### 최초 구현 범위

최초 구현은 대표 CoC 20–50 event를 대상으로 하는 UPPAAL symbolic verification 파이프라인으로 제한한다. Observation KG는 공개 배포본에서 실제 존재와 의미가 확인된 기계 라벨을 우선 사용하고, 라벨이 부족한 event는 소규모 human gold annotation으로 보완한다. Physical AI AV 26.03 데이터 카드는 `egomotion.offline`과 `obstacle.offline`이 97%의 clip에 추가되었다고 명시한다. 구현 전 선택 샘플을 내려받아 실제 column schema, 단위, timestamp 기준을 다시 고정한다. 새로운 범용 perception 모델 학습은 최초 구현에 포함하지 않는다. 연속 신호의 정량적 STL monitoring, 일반 SMT 함의 증명, 확률적 hybrid verification은 symbolic timed-automata 파이프라인이 검증된 후의 독립 확장 단계로 둔다.

### 사전 feasibility evidence

공개 PhysicalAI-AV 호환 CoC-nuScenes에서 `scene-0001` 샘플을 내려받아 CoC, camera timestamp, 2초 history, 6초 future egomotion의 join을 재현했다. 단일 `t0=4.8s`의 `Decelerate`는 이후 속도 감소와 방향적으로 일치했다. 이어서 같은 clip의 연속 CoC 6개를 episode로 합성하고 최초 truck-related `DECELERATE` 의무를 2.5초에 생성했다. 반복 CoC에서 clock을 리셋하지 않았을 때 지속 감속 시작은 약 4.66초, 반응 지연은 약 2.16초로 나타나 1초·2초 deadline은 FAIL, 3초 deadline은 PASS였다. 이는 stateful episode 검사의 기술적 feasibility와 계약 민감도를 보여주지만, deadline의 안전 등급, 공식 NVIDIA human-refined CoC의 품질, 안전거리, 인과 타당성 또는 symbolic safety proof의 근거는 아니다. 재현 절차와 증거 경계는 [feasibility README](../../../projects/03-sequential-coc-verification/experiments/feasibility/README.md)에 기록한다.

후속으로 UPPAAL 5.0.0을 설치하고 scene-0001의 최초·반복 trigger, heuristic response, low-quality event를 다섯 timed-automata mutation model로 생성했다. obligation reachability, bounded response, clock reset, untrusted overwrite와 deadlock query를 정의하고 총 30개 query를 `verifyta`로 symbolic verification했다. baseline은 모두 PASS했고 네 mutation은 의도한 query만 FAIL하여 mutation oracle과 전부 일치했다. 최초 실행에서 의도적인 terminal state가 deadlock으로 검출된 반례를 이용해 terminal stutter를 명시한 후 deadlock query도 통과했다. 이는 timed-protocol과 observer의 mutation feasibility이며 collision 또는 실제 차량 안전의 symbolic proof는 아니다.

반복 가능성을 보기 위해 같은 공개 호환 데이터의 13개 독립 scene으로 cohort를 확장했다. 85개 CoC 중 78개가 trusted였고, 복합·비방향 명령을 제외한 30개 단일 종방향 weak contract에서 29개가 3초 이내 heuristic response를 보였다. `scene-0028@6.5s`의 red-light deceleration 한 건은 기본 설정에서 FAIL했고 UPPAAL baseline에서도 weak-response 반례로 재현되었다. 13개 baseline과 scene별 provenance/response mutation을 포함한 39개 모델, 156개 symbolic query가 모두 사전 oracle과 일치했다. 다만 이 후보는 3초 threshold profile 27개 중 5개가 반응을 검출하고 해당 scene의 영상·raw actuator가 없으므로 `CAMERA_AND_RAW_ACTUATOR_CONFIRMATION_REQUIRED`로 유지한다. scene들은 연속 주행으로 합치지 않았으며, 이 결과는 다중 독립 trace replay의 반복 가능성이지 정책 전체의 안전 증명이 아니다.

이후 chunk 0의 라벨·egomotion 교집합 전체 94개 scene으로 확장했다. 403개 CoC 중 290개가 trusted였고 134개 단일 종방향 weak contract에서 최초 8개 FAIL 후보를 얻었다. 우선순위 영상 10개를 고정 revision에서 선택 다운로드해 검토한 결과, 이미 거의 정지한 STOP/YIELD 3건에 추가 감속을 요구한 observer 오류를 발견했다. `speed <= 0.5m/s`의 이미 만족된 상태를 수용하도록 명세를 수정하고 전체를 재실행한 최종 결과는 129 PASS와 5 `UNKNOWN_REVIEW_REQUIRED`다. UPPAAL은 94 baseline과 scene별 두 mutation, 총 282개 모델의 1,128개 query에서 oracle과 모두 일치했다. 남은 후보는 반복/stale 또는 anticipatory CoC, semantic grounding 오류, 실제 response delay를 raw actuator 없이 구분할 수 없으므로 안전 위반으로 확정하지 않는다.

## 4. 설계 원칙

1. **역할 분리:** KG는 의미 정규화와 추적성을, UPPAAL은 상태 전이·시간 제약·환경 분기 검증을 담당한다.
2. **과거 관측 제한:** CoC 원인으로 사용하는 사실은 decision keyframe 이전 관측에서만 가져온다.
3. **안전 우선:** 안전 속성은 hard constraint이며, 진행성·승차감은 안전 조건이 만족되는 구간에서만 적용한다.
4. **불확실성 보존:** 필요한 사실이 불확실하거나 누락되면 PASS로 간주하지 않고 UNKNOWN을 반환한다.
5. **증거 추적:** 모든 KG 사실과 생성된 automaton location·edge·guard·query는 원본 프레임, timestamp, sensor 또는 규칙 ID로 역추적 가능해야 한다.
6. **결론과 실행 분리:** CoC 결론의 정당성과 실제 궤적의 이행 여부를 별도로 판정한다.
7. **보장 범위 명시:** UPPAAL의 결과는 생성된 추상 모델과 환경 가정 안에서의 보장이며 실제 차량 전체에 대한 무조건적 안전 증명으로 해석하지 않는다.
8. **운영 정합성 우선:** 초기 연구는 일반 논리식의 완전한 함의보다 시간에 따른 결정 가능성, 반응성, 안전성, 진행성을 우선 검증한다.

## 5. 전체 아키텍처

```text
과거 영상·egomotion·미래 궤적·CoC·교통 규칙·선호 프로필
                         │
          ┌──────────────┼──────────────┐
          │              │              │
   Observation KG   CoC Claim KG   Normative & Preference KG
          │              │              │
          └──────────────┼──────────────┘
                         │ grounding·규칙 선택·일관성 검사
                         │
             Verification IR Builder
                         │
          ┌──────────────┴──────────────┐
          │                             │
 UPPAAL Automata Generator      UPPAAL Query Generator
          │                             │
          └──────────────┬──────────────┘
                         │
                 UPPAAL verifyta
                         │
       PASS / FAIL / UNKNOWN + diagnostic trace
                    + provenance
```

## 6. 입력과 출력

### 입력

- `clip_id`
- decision keyframe `t0`
- `t0` 이전의 카메라 프레임과 frame timestamp
- ego trajectory history
- Alpamayo CoC 텍스트
- Alpamayo predicted future trajectory 또는 ground-truth future trajectory
- 적용 가능한 교통 규칙과 도로 문맥
- 주행 선호 프로필의 수치 파라미터
- UPPAAL 환경 가정과 automata template 버전

### 출력

```json
{
  "clip_id": "...",
  "event_t0": 5100000,
  "semantic_grounding": "PASS",
  "decision_feasibility": "PASS",
  "operational_decision_consistency": "PASS",
  "symbolic_safety_consistency": "PASS",
  "symbolic_service_consistency": "FAIL",
  "trace_conformance": "NOT_RUN",
  "checker_type": "UPPAAL_SYMBOLIC",
  "model_version": "coc-uppaal-v1",
  "bounded_horizon": "event-specific",
  "assumptions": ["env-profile:urban-crossing-v1"],
  "abstraction_contract": "abstraction-profile:v1",
  "excluded_scope": ["unmodeled sensor failure", "agents outside configured bounds"],
  "residual_risks": ["perception correctness is not proved"],
  "properties": {
    "safety": "PASS",
    "responsiveness": "FAIL",
    "progress": "FAIL",
    "comfort": "PASS"
  },
  "property_severity": {
    "safety": "HARD_SAFETY",
    "responsiveness": "SERVICE",
    "progress": "SERVICE",
    "comfort": "SERVICE"
  },
  "safety_decision": "ACCEPT",
  "service_quality": "UNSATISFACTORY",
  "queries": {
    "SAFE-001": "SATISFIED",
    "RESP-PED-001": "VIOLATED",
    "PROG-001": "VIOLATED"
  },
  "counterexample": {
    "property_id": "RESP-PED-001",
    "trace_id": "diag-trace-0042",
    "elapsed_time": 1.2,
    "locations": ["Ego.Cruise", "Ego.HazardDetected", "Observer.DeadlineMiss"],
    "expected": "deceleration begins within response bound",
    "observed": "a modeled execution reaches DeadlineMiss before Braking"
  },
  "evidence_refs": [
    "camera_front_wide:frame_42",
    "track:pedestrian_17",
    "kg:claim_12",
    "uppaal:ReactionObserver.edge_3"
  ],
  "overall": "SAFE_BUT_UNSATISFACTORY"
}
```

예시 숫자는 출력 형식을 설명하기 위한 것이며 시스템의 기본 임계값으로 사용하지 않는다.

정량적 STL robustness는 초기 필수 출력이 아니다. 이후 RTAMT 계층을 추가하면 `trace_metrics` 아래에 별도 기록하며, UPPAAL symbolic 판정과 혼합하지 않는다.

## 7. KG 설계

### 7.1 Observation KG

과거 관측 구간에서 확인된 사실만 저장한다.

#### 주요 엔터티

- `EgoVehicle`
- `Vehicle`, `Pedestrian`, `Cyclist`, `EmergencyVehicle`
- `Lane`, `LaneBoundary`, `Crosswalk`, `Intersection`, `StopLine`
- `TrafficLight`, `TrafficSign`
- `RoadEvent`, `ConstructionZone`, `OcclusionRegion`
- `Observation`, `Frame`, `Sensor`, `Track`

#### 주요 관계

- `locatedIn`, `locatedNear`, `inEgoPath`
- `movingToward`, `movingAway`, `crossing`, `cuttingIn`
- `hasState`, `hasVelocity`, `hasAcceleration`
- `hasRightOfWay`, `conflictsWith`, `occludedBy`
- `observedAt`, `derivedFromSensor`, `supportedByFrame`

#### 필수 provenance

각 fact는 다음 속성을 가진다.

- 시작·종료 timestamp
- source sensor와 frame ID
- detector 또는 annotator ID
- confidence 또는 uncertainty interval
- observed/predicted/derived 구분

### 7.2 CoC Claim KG

CoC가 주장하는 원인과 결론을 저장한다.

#### 주요 엔터티

- `CoCStatement`
- `CausalFactor`
- `DrivingDecision`
- `ExpectedAction`
- `ResumeCondition`

#### 주요 관계

- `hasCause`
- `hasDecision`
- `hasExpectedAction`
- `affectsAgent`
- `hasResumeCondition`
- `supportedByObservation`
- `contradictedByObservation`

주행 결정은 Alpamayo의 종방향·횡방향 closed set에 정렬한다. 한 event에는 종방향 최대 한 개, 횡방향 최대 한 개를 허용한다.

### 7.3 Normative & Preference KG

교통 규칙, 안전 계약, 사용자 선호 프로필을 저장한다.

- 규칙 ID 및 적용 관할·도로 문맥
- 규칙의 trigger condition
- required, permitted, prohibited action
- safety precedence
- response bound, resume bound
- minimum acceptable progress
- 추상 speed·acceleration·deceleration·jerk band와 구간 경계
- property severity: `HARD_SAFETY`, `LEGAL`, `SERVICE`

사용자 만족은 직접적인 참·거짓 사실로 저장하지 않는다. 사용자 연구나 preference data에서 추정한 수치 파라미터를 프로필로 저장하고, 모델체커가 해당 프로필의 조건 만족 여부를 검사한다.

## 8. CoC 분석 파이프라인

1. CoC에서 객체, 상태, 인과 표현, 주행 결정, 예상 행동, 재개 조건을 추출한다.
2. 객체 표현을 KG ontology ID로 정규화한다.
3. CoC 객체를 과거 Observation KG의 track과 연결한다.
4. 각 causal factor가 keyframe 이전에 관측됐는지 확인한다.
5. 결정과 무관한 배경 설명은 검증 전제에서 제외한다.
6. 결정에 필요한 직접 원인이 없으면 `UNSUPPORTED`로 표시한다.
7. 관측과 상충하는 주장은 `CONTRADICTED`로 표시한다.
8. 적용 가능한 규칙·선호 프로필을 Normative KG에서 선택한다.
9. KG subgraph를 typed Verification IR로 변환한다.
10. Automata Generator가 IR을 location, edge, guard, clock, invariant, synchronization channel로 변환한다.
11. Query Generator가 안전·반응·진행·서비스 품질 속성을 UPPAAL query와 observer automaton으로 변환한다.

LLM은 1단계 후보 추출에 사용할 수 있지만 최종 KG 삽입 전에 ontology, type, temporal-locality 검사를 통과해야 한다.

## 9. UPPAAL 모델과 형식 속성

### 9.1 모델 구성

각 event는 필요한 template만 포함하는 작은 automata 네트워크로 생성한다.

- `EgoDecision`: `Cruise`, `HazardDetected`, `Yielding`, `Braking`, `Stopped`, `Resume`, `EmergencyBrake`
- `EnvironmentAgent`: 보행자·차량·신호의 가능한 상태 변화
- `TrafficRule`: required, permitted, prohibited action을 전이 guard와 error location으로 표현
- `ReactionObserver`: 위험 감지 후 반응 기한 감시
- `ResumeObserver`: 안전 회복 후 재출발 기한 감시
- `ProgressObserver`: 불필요한 정지 또는 저속 지속 감시
- `TraceReplay`: 기록 궤적을 사건 열로 재생할 때만 포함

고전 UPPAAL symbolic 모델의 연속 차량 신호는 유한 구간으로 추상화한다.

```text
SpeedBand        = STOPPED | LOW | NORMAL | HIGH
AccelerationBand = HARD_BRAKE | BRAKE | STEADY | ACCELERATE
DistanceBand     = CRITICAL | NEAR | SAFE
ComfortBand      = UNCOMFORTABLE | ACCEPTABLE
```

각 구간 경계값은 데이터에서 임의로 학습하지 않고 safety contract, 차량 한계, 사용자 연구 또는 명시적인 실험 프로필에서 가져와 provenance와 함께 저장한다.

#### 추상화 건전성 계약

각 연속 신호의 이산 구간에는 다음 계약을 함께 기록한다.

- `abstraction_direction`: `OVER_APPROX`, `UNDER_APPROX`, `EXACT_ON_BOUNDARY_SET`
- 경계값의 단위, 폐구간·개구간 여부, sensor error와 sampling jitter
- 추상 상태가 대표하는 연속값 집합과 전이 가능성
- 계약이 보존하는 속성 종류와 보존하지 못하는 속성 종류
- concrete-to-abstract mapping `alpha`와 초기 상태·전이·안전 predicate에 대한 proof obligation

안전성 검증에는 실제 가능한 연속 상태와 전이를 포함하는 over-approximation을 기본으로 사용한다. 모든 concrete 초기 상태와 전이가 `alpha`를 통해 abstract 초기 상태와 전이에 포함되고, abstract safe predicate가 concrete safe predicate를 보수적으로 함의해야 한다. 이 proof obligation이 충족된 모델에서 안전 속성이 PASS이면 명시된 추상화 오차와 환경 가정 안에서 보수적 안전 근거로 해석할 수 있다. 반대로 under-approximation의 PASS는 실제 전체 상태에 대한 안전 보장이 아니며 탐색된 동작의 실행 가능성 근거로만 사용한다. 경계값, 오차 범위, 추상화 방향 또는 proof obligation을 확정할 수 없으면 해당 속성은 PASS가 아니라 UNKNOWN이다. 추상화 전후의 결과 변화는 경계값 sensitivity analysis와 representative concrete trace refinement로 추가 검사한다.

### 9.2 안전성

```text
A[] not Collision
A[] not UnsafeDistance
A[] not DecisionConflict
A[] not deadlock
A[] not RuleObserver.IllegalStopLineCrossing
```

안전거리에는 단순 고정 거리 외에 속도·제동능력·반응시간을 포함하는 RSS 계열 경계를 구간 guard로 연결할 수 있다. 이 결과는 추상 구간 모델에 대한 검증이며 연속 RSS 동역학 전체의 수학적 증명은 아니다.

### 9.3 반응성

```text
HazardDetected --> ProperResponse
A[] not ReactionObserver.DeadlineMiss
A[] not StopObserver.DeadlineMiss
```

UPPAAL의 `p --> q`는 시간 상한 없는 eventual response이므로 bounded response는 clock을 가진 observer automaton으로 구현한다. `ProperResponse`는 CoC 결정에 따라 감속, 정지, nudge, lane-change abort 등으로 구체화한다.

### 9.4 진행성

```text
RoadClearAndDrivePermitted --> Ego.Driving
A[] not ResumeObserver.DeadlineMiss
A[] not ProgressObserver.PersistentLowSpeed
A[] not ProgressObserver.UnnecessaryStop
```

위험이 지속되는 동안에는 진행성 위반을 발생시키지 않도록 guard condition을 둔다.

### 9.5 서비스 품질과 승차감

```text
A[] not ComfortObserver.HardBrakeWithoutEmergency
A[] not ComfortObserver.ExcessiveJerkBand
A[] not ServiceObserver.ExcessiveResponseDelay
```

고전 UPPAAL에서는 acceleration과 jerk를 구간화하여 검사한다. 원시 연속 신호의 정확한 크기와 STL robustness가 필요하면 동일 계약을 RTAMT 속성으로 별도 평가한다.

### 9.6 CoC–행동 일관성

```text
E<> Ego.ExpectedDecision
A[] not DecisionObserver.ContradictoryAction
A[] not DecisionObserver.DecisionDeadlineMiss
A[] not TraceObserver.BehaviorMismatch
```

`E<> Ego.ExpectedDecision`은 CoC 결론을 따르는 실행이 하나 이상 존재하는지 확인하는 **결정 실행 가능성** 검사다. 이 query의 PASS만으로 모든 허용 환경에서 결론이 이행된다고 판정하지 않는다. 환경 전체에 대한 결정 의무는 `DecisionRequired`가 활성화된 동안 deadline miss가 어느 경로에서도 도달하지 않는지 observer로 별도 검사한다. 이것은 전제에서 결론이 일반 논리적으로 필연 도출된다는 SMT 함의 증명과도 동일하지 않다.

`TraceObserver.BehaviorMismatch` query는 `TraceReplay`가 포함된 conformance 모델에서만 생성하며 symbolic environment 모델에는 생성하지 않는다.

### 9.7 속성 우선순위

1. 법규상 의무와 충돌 회피
2. 최소 위험 상태 유지
3. CoC 결론 이행
4. 반응성과 진행성
5. 승차감과 사용자 선호

낮은 우선순위 속성은 높은 우선순위 속성을 위반하도록 요구할 수 없다.

## 10. 검증 방식

### 10.1 핵심: UPPAAL symbolic model checking

KG에서 event별 UPPAAL automata 네트워크와 query를 생성하고 `verifyta`로 검사한다. Verification IR에 유한하게 부호화된 환경의 비결정적 행동과 허용된 시간 지연을 모델에 포함하여 그 모델의 상태 공간을 전수 탐색한다. 결과는 현실의 모든 환경 변화가 아니라 명시된 환경 가정과 추상화 경계 안에서만 유효하다.

- error location이 도달 가능한가
- 모든 경로에서 안전 invariant가 유지되는가
- 위험 감지 후 모든 경로에서 적절한 반응이 발생하는가
- bounded observer의 `DeadlineMiss`가 도달 가능한가
- 안전 회복 후 모든 경로에서 진행을 재개하는가
- deadlock이 존재하는가
- bounded progress observer의 deadline miss가 도달 가능한가

검증 실패 시 UPPAAL diagnostic trace를 받아 automaton 요소에서 Verification IR, KG claim, 원본 frame으로 역매핑한다.

`A[] not deadlock`은 교착 부재만 검사하며 무한 비진행, starvation 또는 Zeno 실행의 부재를 뜻하지 않는다. 초기 구현은 무한 liveness를 직접 증명했다고 주장하지 않고, 명시적 시간 상한을 가진 `ResumeObserver`와 `ProgressObserver`로 bounded progress를 검사한다. 이후 unbounded liveness가 필요하면 시간 발산 가정, urgent/committed location 사용, fairness 가정을 각각 명시하고 별도 검증한다.

### 10.2 기록 궤적 trace replay와 conformance

예측 또는 ground-truth trajectory를 바로 연속 신호로 모델체킹했다고 주장하지 않는다. 먼저 다음 사건으로 변환한다.

```text
HazardDetected, BrakingStarted, Stopped, RoadClear, Resume,
PersistentLowSpeed, HardBrake, ComfortViolation
```

timestamp가 붙은 사건 열을 deterministic `TraceReplay` automaton으로 생성하고 동일 observer와 query를 재사용한다. 이 단계는 한 개의 기록된 실행에 대한 Boolean conformance 검사이며, 모델링된 환경 경로 전체에 대한 symbolic model checking과 결과를 분리해 보고한다.

원시 속도·가속도·jerk 신호의 정량 robustness가 연구 질문에 필요해질 때만 RTAMT를 추가한다.

### 10.3 확장: UPPAAL statistical model checking

동일 CoC 시나리오의 객체 위치, 속도, 반응시간, occlusion을 허용 범위 안에서 변화시켜 시뮬레이션한다. 정책 rollout이 속성을 만족할 확률과 신뢰구간을 계산한다.

UPPAAL SMC는 stochastic hybrid automata, bounded simulation, 확률 추정을 사용할 수 있으나 symbolic proof와 동일한 보장을 제공하지 않는다. 출력에는 실행 수, 시간 bound, random seed, 확률 신뢰구간, 모델 분포, 수치 적분 설정을 함께 기록한다.

### 10.4 선택적 도구 확장

| 필요 질문 | 추가 도구 | UPPAAL과의 역할 차이 |
|---|---|---|
| CoC 전제와 규칙이 결론을 순수 논리적으로 함의하는가 | Z3 | 정적 SMT satisfiability와 implication 검사 |
| 고정 궤적이 연속 신호 계약을 얼마나 여유 있게 만족하는가 | RTAMT | STL offline monitoring과 quantitative robustness |
| 연속 차량 동역학이 모든 제어·외란에서 수학적으로 안전한가 | KeYmaera X | differential dynamic logic 기반 hybrid-system proof |

Z3, RTAMT, KeYmaera X는 최초 구현의 필수 의존성이 아니다. UPPAAL 결과가 답하지 못하는 연구 질문이 실제 실험에서 확인된 경우에만 각각 독립적으로 추가한다.

### 10.5 후속: 제한된 hybrid-system proof

대표적인 종방향 제동·추종·양보 시나리오에 한해 추상 차량 동역학과 nondeterministic 환경을 정의하고 안전 envelope를 증명한다. 이는 전체 VLA 신경망을 증명하는 것이 아니라 policy output이 지켜야 하는 formal contract를 증명하는 단계다.

### 10.6 E2E fine-tuning과 counterexample-guided verification

모델체커를 학습 loss의 대체물로 사용하지 않는다. E2E 정책을 closed-loop plant와 합성한 rollout에서 계약 robustness를 계산하고, symbolic 또는 hybrid checker가 생성한 재현 가능한 반례를 prioritized replay data로 환원한다. 재학습 후에는 기존 반례 한 점뿐 아니라 그 주변 초기 상태·물리 파라미터 구간을 holdout verification domain으로 검사한다.

```text
policy -> closed-loop rollout -> contract checker
  ^                                 |
  |                                 v
  +------- counterexample fine-tuning
```

고정 `D=1s`, `D=2s`는 service sensitivity profile로만 유지한다. hard safety deadline은 gap, 상대속도, 사용 가능한 제동도, brake build-up, sensor/actuator uncertainty를 합성한 `stopping_margin >= 0` 불변식 또는 그로부터 유도된 상태 의존 `D_safe`로 정의한다. 실제 차량 envelope의 provenance가 없으면 hard safety 판정은 UNKNOWN이다.

E2E 정책 검증은 assume-guarantee 방식으로 perception uncertainty, policy output envelope, vehicle dynamics를 분리한다. 신경망 입출력 검증, timed symbolic verification, hybrid reachability, simulation 결과에는 각각 다른 certificate type을 부여하며 어느 한 계층의 PASS를 전체 시스템 PASS로 승격하지 않는다. 상세 서베이와 scene-0001 parameter-grid falsification은 [01_RELATED_WORK_SURVEY_V01.md](../surveys/01_RELATED_WORK_SURVEY_V01.md)에 기록한다.

## 11. 판정 의미론

### PASS

- 필요한 전제가 충분히 관측되었다.
- 해당 UPPAAL query가 모델과 명시된 환경 가정에서 만족된다.
- 해당 속성에 필요한 추상화 건전성 계약이 충족된다.
- 관련 hard constraint가 모두 만족된다.

### FAIL

- 관측과 CoC가 직접 모순된다.
- 결정이 적용 규칙상 금지된다.
- symbolic model 또는 trace replay에서 하나 이상의 hard constraint 반례가 생성된다.
- guard가 활성화된 preference property가 위반된다.

### UNKNOWN

- 필수 객체나 신호 상태의 confidence가 판정 기준보다 낮다.
- 지도·관할 규칙·right-of-way 정보가 부족하다.
- CoC 표현을 closed-set decision으로 유일하게 정규화할 수 없다.
- 모델링된 환경 범위 밖의 시나리오다.
- UPPAAL 모델 생성, 검증, 또는 추상화 타당성을 확정할 수 없다.

`결정 실행 가능성`, `symbolic safety`, `symbolic service`, `trace conformance`, `SMC estimate`는 서로 대체하지 않는 별도 certificate field로 보고한다. 특히 `E<> Ego.ExpectedDecision`의 만족은 `decision_feasibility=PASS`일 뿐 `symbolic_safety_consistency` 또는 `operational_decision_consistency`의 PASS를 자동으로 만들지 않는다.

전체 판정은 `PASS > UNKNOWN > FAIL` 같은 임의 순서를 사용하지 않는다. 각 property에는 다음 severity가 부여된다.

- `HARD_SAFETY`: 충돌 회피, 안전거리, 동역학적으로 필요한 최대 반응시간
- `LEGAL`: 신호, 정지선, 우선권 등 적용 법규
- `SERVICE`: 불필요한 저속·정지, 정상 상황에서의 재출발 지연, 승차감

`HARD_SAFETY` 또는 `LEGAL`에 FAIL이 하나라도 있으면 `REJECT`, 이 계층에 UNKNOWN이 있으면 `REVIEW`다. 두 계층이 모두 PASS이고 `SERVICE`가 FAIL이면 `SAFE_BUT_UNSATISFACTORY`, 모든 필수 판정이 PASS이면 `ACCEPT`로 집계한다. 같은 반응시간 속성도 충돌 회피에 필요한 한계는 `HARD_SAFETY`, 사용자가 답답함을 느끼는 더 엄격한 목표는 `SERVICE`로 각각 정의할 수 있다.

## 12. 오류 처리

- CoC 파싱 실패: 원문과 실패 위치를 보존하고 UNKNOWN 반환
- ontology 미등록 개념: out-of-KG 플래그와 후보 상위개념 반환
- timestamp 불일치: 해당 샘플을 검증에서 제외하고 data-alignment 오류 기록
- trajectory 누락 또는 길이 부족: 검증 불가능한 horizon을 명시하고 UNKNOWN 반환
- 규칙 충돌: 안전 우선순위와 관할 metadata로 해결하지 못하면 REVIEW 반환
- automata/query compiler 오류: UPPAAL 검증을 실행하지 않고 컴파일 진단과 관련 KG subgraph 반환
- checker timeout: FAIL로 오판하지 않고 UNKNOWN/TIMEOUT 반환
- diagnostic trace 역매핑 실패: 원본 UPPAAL trace를 보존하고 explanation 상태를 PARTIAL로 반환
- 연속 신호의 사건 추상화 경계값 누락: trace replay를 수행하지 않고 UNKNOWN 반환

## 13. 실험 설계

### 13.1 파일럿 데이터

- 공개 CoC train/validation split을 유지한다.
- 초기 파일럿은 접근 가능한 대표 CoC event 가운데 20–50개를 사용한다.
- 각 event는 front-wide 영상, egomotion, CoC, 미래 궤적을 포함한다.
- multi-camera grounding은 파일럿 이후 확장한다.
- 동일 clip의 여러 event가 train과 validation에 나뉘지 않게 clip 단위로 분리한다.

### 13.2 비교 방법

1. LLM-as-a-judge로 CoC를 직접 평가
2. KG 없이 CoC를 바로 UPPAAL template parameter로 변환
3. KG semantic check만 수행
4. 제안 방식: KG intermediate representation + automata/query compiler + UPPAAL symbolic model checking
5. 기록 궤적에 대해서는 단순 임계값 스크립트와 UPPAAL trace replay 비교

### 13.3 의도적 오류 주입

- 존재하지 않는 객체를 원인으로 삽입
- 신호 색상 반전
- left/right 결정 반전
- 위험 감지 후 행동 시작 지연
- 장애물 해소 후 불필요한 정지 연장
- 급제동·고 jerk trajectory 삽입
- CoC 결론과 trajectory 행동 불일치
- 미래 프레임의 정보를 CoC 원인으로 누출

## 14. 평가 지표

### 의미 계층

- entity extraction precision/recall
- ontology normalization accuracy
- observation grounding accuracy
- temporal-locality violation recall
- contradiction detection accuracy

### 명세 계층

- UPPAAL model/query compilation success rate
- type-correct automata/query rate
- KG fact에서 location·edge·guard·clock·query까지의 provenance coverage
- human-authored gold UPPAAL model/query와의 semantic agreement
- observer deadline encoding accuracy

### 검증 계층

- seeded fault detection recall
- false acceptance rate
- false rejection rate
- UNKNOWN rate와 원인 분포
- diagnostic trace의 fault localization accuracy
- symbolic model checking과 trace replay 판정의 구분 정확성
- human expert verdict와의 agreement

### 주행 품질 계층

- safety violation rate
- response-time violation rate
- progress violation rate
- comfort violation rate
- CoC–trajectory consistency rate
- 사용자 선호 판정과 모델체커 판정의 agreement

## 15. 성공 기준

파일럿은 다음 조건을 만족하면 설계 타당성이 있다고 본다.

1. 모든 생성 location, edge, guard, clock, observer, query는 원천 CoC claim, KG node, 관측 provenance 또는 규칙 ID로 역추적된다.
2. 필수 전제가 불확실한 샘플을 PASS로 처리하지 않는다.
3. 합성 단위 테스트에 삽입한 각 오류 유형에서 최소 하나의 대응 query가 위반되고 UPPAAL diagnostic trace가 반환된다.
4. 동일 clip과 동일 설정에서 반복 실행한 판정은 결정적이다.
5. KG를 사용하는 제안 방식과 KG를 사용하지 않는 직접 변환 방식의 grounding 오류 및 잘못된 automata/query 발생률을 비교할 수 있다.
6. 안전성만 만족하지만 과도하게 느리거나 반응이 늦는 모델 경로와 기록 trajectory를 진행성·반응성 위반으로 분리 검출한다.
7. symbolic 검증 결과와 한 개의 기록 궤적 replay 결과를 혼동하지 않고 별도 필드로 보고한다.
8. 반례의 각 핵심 전이를 KG와 원본 증거로 역매핑한다.
9. 안전 속성 PASS에는 over-approximation 또는 동등한 건전성 근거가 연결되고, 근거가 없으면 UNKNOWN으로 판정된다.
10. `E<>` 실행 가능성, 전 경로 bounded obligation, deadlock 부재, bounded progress를 서로 다른 테스트와 출력 필드로 보고한다.

실제 데이터에서의 정량 목표치는 파일럿 결과와 human audit을 바탕으로 사전등록한다. 근거 없는 임의 목표 수치는 본 설계 단계에서 고정하지 않는다.

## 16. 테스트 전략

### 단위 테스트

- ontology type·cardinality 제약
- CoC decision closed-set mapping
- timestamp와 past-only causal evidence 검사
- KG-to-UPPAAL template 치환
- automata XML과 query syntax validation
- bounded-response observer의 positive/negative synthetic model
- 안전성·진행성·deadlock query의 positive/negative model
- continuous signal-to-event abstraction 경계 테스트
- over-approximation/under-approximation 방향과 PASS/UNKNOWN 전파 테스트
- `E<>`는 만족하지만 일부 경로가 decision deadline을 위반하는 반례 모델
- deadlock은 없지만 progress deadline을 위반하는 순환 모델
- 3값 판정 집계 규칙

### 통합 테스트

- 한 CoC event에서 영상 metadata부터 최종 certificate까지의 전체 경로
- 실제 CoC와 의도적으로 조작한 CoC 비교
- symbolic environment model과 deterministic trace replay의 판정 분리
- predicted trajectory와 ground-truth trajectory 교환 시 conformance 판정 변화
- preference profile 변화에 따른 comfort/progress 판정 변화

### 메타모픽 테스트

- 위험 객체 제거 시 해당 객체를 원인으로 하는 CoC 정당성이 유지되지 않아야 한다.
- 위험 객체의 접근 속도 band를 증가시켰을 때 기존 collision counterexample이 사라져서는 안 된다.
- 동일 안전 조건에서 반응 deadline을 더 엄격하게 하면 기존 DeadlineMiss가 사라져서는 안 된다.
- 장애물 제거 후 정지 허용시간을 줄이면 기존 progress violation이 사라져서는 안 된다.

### 사람 검토

- ontology·교통 규칙 전문가의 automata/query template 검토
- UPPAAL 경험자의 automata·observer·query 검토
- 자율주행 전문가의 diagnostic trace와 추상화 판정 검토
- 사용자 연구를 통한 preference parameter 및 만족 판정 검증

## 17. 모듈 경계

1. **CoC Parser:** 자연어에서 claim 후보 추출
2. **Ontology Normalizer:** 후보를 typed KG vocabulary로 변환
3. **Observation Grounder:** claim과 sensor-derived entities 연결
4. **KG Validator:** type, contradiction, causal locality 검사
5. **Rule Resolver:** 적용 규칙과 preference profile 선택
6. **Verification IR Builder:** 검증에 필요한 최소 subgraph 생성
7. **Automata Generator:** IR을 UPPAAL templates, declarations, composition으로 변환
8. **Query Generator:** IR을 symbolic query와 deadline observer로 변환
9. **Trace Event Abstractor:** trajectory와 egomotion을 timestamp 사건 열로 변환
10. **TraceReplay Generator:** 한 개의 사건 열을 deterministic automaton으로 변환
11. **UPPAAL Runner:** `verifyta` 실행, verdict와 diagnostic trace 수집
12. **Counterexample Mapper:** UPPAAL trace를 Verification IR, KG, frame provenance로 역매핑
13. **Certificate Builder:** provenance와 보장 범위가 있는 최종 보고서 생성

각 모듈은 입력·출력 schema를 통해 연결하며, LLM 출력은 KG Validator와 Verification IR Builder를 우회해 Automata Generator 또는 Query Generator로 직접 전달될 수 없다.

## 18. 취약점 분석 및 개선 요구사항

다음 취약점은 구현 오류만이 아니라 연구 결론을 과장하거나 잘못된 PASS를 만들 수 있는 validity threat다. 우선순위 `P0`은 파일럿 전에 차단해야 하고, `P1`은 파일럿 결과 해석 전에 충족해야 하며, `P2`는 확장 단계에서 다룬다.

| 우선순위 | 취약점 | 실패 또는 과장 가능성 | 필수 개선 | 검증 기준 |
|---|---|---|---|---|
| P0 | 존재 경로와 전 경로 의무 혼동 | `E<> ExpectedDecision`만 만족해도 위험한 다른 경로가 남는다 | 실행 가능성과 bounded universal obligation을 별도 query·필드로 생성 | 하나의 성공 경로와 하나의 deadline 위반 경로가 공존하는 합성 모델에서 feasibility만 PASS, obligation은 FAIL |
| P0 | 연속값 추상화의 비건전성 | 위험 상태가 구간화 과정에서 제거되어 false PASS가 발생한다 | 안전 속성에는 over-approximation 계약, `alpha`의 전이 보존 proof obligation, 경계·오차·단위 provenance, UNKNOWN 전파를 의무화 | proof obligation 검토 후 경계값 perturbation과 concrete trace refinement에서 보존 관계 확인 |
| P0 | 환경 완전성 과장 | 모델에 없는 cut-in, occlusion, 지연을 포함해 현실 전체를 검증한 것처럼 해석된다 | certificate에 environment assumption set, excluded behaviors, horizon, domain bounds 기록 | 가정 밖 입력은 PASS가 아닌 UNKNOWN과 `OUT_OF_SCOPE` 사유 코드로 보고 |
| P0 | 불확실성의 비결정성 누락 | 단일 최빈 라벨만 사용해 가능한 위험 관측을 제거한다 | 임계 구간의 perception uncertainty를 bounded nondeterministic alternatives로 부호화 | 대체 관측 중 하나가 위험하면 safety PASS가 나오지 않음 |
| P0 | observer/query 오부호화 | deadline을 잘못 리셋하거나 guard가 비활성화되어 위반을 놓친다 | 검증된 observer template, 독립 gold query, mutation test 도입 | 각 observer에 positive, negative, boundary, reset mutation 테스트 통과 |
| P1 | deadlock과 liveness 혼동 | `A[] not deadlock`인데도 차량이 영원히 진행하지 않을 수 있다 | 초기에는 bounded progress만 주장하고 시간 발산·fairness·Zeno 가정을 분리 | non-deadlock 순환 모델의 progress deadline 위반 검출 |
| P1 | KG/규칙 불완전성 | 누락 사실을 거짓으로 보거나 적용 법규를 잘못 선택한다 | open-world/closed-world predicate 구분, jurisdiction·유효기간·우선순위 기록 | 필수 사실 또는 관할 정보 누락 시 UNKNOWN/REVIEW |
| P1 | LLM 파싱 환각과 방향 오류 | 객체, 좌우, 신호, 부정 표현이 잘못된 형식 사실로 변환된다 | closed-set schema, type/negation/direction 검사, 원문 span provenance, human audit | 의도적 좌우·부정·객체 주입 오류에 대한 검출률 보고 |
| P1 | 데이터 schema 의존성 | 공개 배포본에 없는 필드나 변경된 의미를 전제로 구현한다 | dataset version별 schema manifest와 adapter를 만들고 필드 존재·단위 검사 | 지원되지 않는 version은 조용히 대체하지 않고 ingestion 실패로 보고 |
| P1 | 판정 집계의 모순 | 서비스 FAIL이 전체 temporal FAIL로 표현되면서 safety ACCEPT와 충돌한다 | safety와 service certificate를 분리하고 severity 기반 집계만 사용 | 예시 출력과 집계 truth table의 모든 조합이 일치 |
| P1 | 기록 궤적과 반사실 검증 혼동 | 한 trajectory의 성공을 정책 전체의 안전으로 일반화한다 | replay 결과와 symbolic 결과를 별도 certificate type으로 유지 | replay PASS, symbolic FAIL 조합을 정상적으로 표현 |
| P1 | state explosion과 timeout 편향 | 어려운 위험 사례만 UNKNOWN이 되어 성능이 과대평가된다 | timeout·state count·memory를 보고하고 UNKNOWN 원인별 비율을 층화 | 난이도/시나리오별 timeout 및 UNKNOWN 분포 공개 |
| P2 | SMC 결과의 증명 오인 | 유한 simulation의 높은 만족 확률을 안전 증명으로 표현한다 | 실행 수, bound, seed, 신뢰구간, 모델 분포와 `STATISTICAL_ESTIMATE` 유형 기록 | symbolic certificate와 문구·필드를 자동으로 구분 |
| P2 | 설명 정합성과 실제 인과 혼동 | 그럴듯하게 grounding된 CoC를 counterfactual cause로 간주한다 | semantic justification와 intervention 기반 causal validity를 별도 연구 질문으로 분리 | 원인 제거·교체 메타모픽 실험 결과를 독립 보고 |

### 18.1 구현 게이트

파일럿 실행 전 다음 조건을 모두 충족해야 한다.

1. query catalog에서 각 query의 경로 양화, 시간 bound, severity, 활성화 guard를 기계 판독 가능하게 정의한다.
2. abstraction manifest에서 모든 연속 신호의 방향, 경계, 오차, 단위, provenance를 정의한다.
3. environment assumption manifest에서 포함·제외 행동, 변수 범위, 검증 horizon을 정의한다.
4. dataset schema manifest를 실제 공개 배포본에 대해 검증하고 version을 고정한다.
5. 출력 schema와 판정 truth table을 합성 테스트로 검증한다.
6. observer template마다 독립적인 positive/negative/boundary/mutation test를 통과한다.

### 18.2 잔여 위험의 보고

개선 후에도 perception 자체의 정확성, 환경 모델 밖의 행동, 연속 동역학 전체, 자연어 설명의 실제 인과성은 완전히 증명되지 않는다. 최종 certificate에는 `assumptions`, `abstraction_contract`, `excluded_scope`, `checker_type`, `bounded_horizon`, `residual_risks`를 필수로 포함한다. 논문과 보고서에서는 “CoC 결론을 증명했다” 대신 “명시된 KG 사실, 추상화 계약, 환경 가정과 시간 범위 안에서 해당 속성을 검증했다”라고 기술한다.

## 19. 주요 위험의 운영상 완화

- **Perception 오류:** confidence와 UNKNOWN 판정, human-verified subset, bounded alternative observation 사용
- **KG 불완전성:** out-of-KG routing 및 open-world/closed-world 구분
- **규칙의 지역 차이:** jurisdiction, 유효기간, road context를 규칙 적용 조건에 포함
- **사용자 만족의 주관성:** 수치 프로필과 안전 hard constraint를 분리
- **추상화의 비건전성:** 건전성 계약, sensitivity analysis, concrete trace refinement 수행
- **state explosion:** event별 최소 subgraph, bounded data domain, compositional template, symmetry reduction 사용
- **deadline 속성 오부호화:** 검증된 observer pattern과 합성·mutation model 사용
- **LLM의 형식 명세 환각:** template 기반 compiler와 syntax/type/negation validation 사용
- **기록 궤적의 반사실 부족:** UPPAAL symbolic environment model과 SMC로 확장
- **설명과 실제 인과의 혼동:** semantic justification와 counterfactual causal validity를 별도 결과로 보고
- **도구 보장의 과장:** symbolic, trace replay, SMC, hybrid proof 결과에 서로 다른 certificate type 부여

## 20. 예상 연구 기여

1. 자율주행 CoC를 provenance-aware verification KG로 표현하는 schema
2. KG claim에서 UPPAAL timed automata와 안전성·반응성·진행성·서비스 품질 query를 생성하는 compiler
3. 자연어 설명의 grounding, 시간적 운영 정합성, trajectory conformance를 분리하는 3계층 판정 체계
4. 사용자 만족을 safety와 충돌하지 않는 bounded temporal contract로 정식화하는 방법
5. UPPAAL diagnostic trace와 KG claim·규칙·근거 프레임을 연결한 CoC verification certificate

## 21. 참고 자료

- NVIDIA, *Alpamayo-R1: Bridging Reasoning and Action Prediction for Generalizable Autonomous Driving in the Long Tail*, 2025/2026.
- UPPAAL Team, *UPPAAL Documentation: System Description, Symbolic Queries, Statistical Queries*, https://docs.uppaal.org/.
- G. Behrmann, A. David, and K. G. Larsen, *A Tutorial on UPPAAL*, 2004.
- A. David et al., *Statistical Model Checking for Networks of Priced Timed Automata*, FORMATS 2011.
- Parameshwaran and Wang, *Safety Verification and Navigation for Autonomous Vehicles based on Signal Temporal Logic Constraints*, 2024.
- Reimann et al., *Temporal Logic Formalisation of ISO 34502 Critical Scenarios*, 2024.
- Strauss and Mitsch, *Formal Verification, Refinement, and Testing of the Responsibility-Sensitive Safety Model*, 2023.
- Zipfl et al., *Ontologies for Scenario-based Testing in Autonomous Driving*, 2023.
- Bogdoll et al., *One Ontology to Rule Them All: Corner Case Scenarios for Autonomous Driving*, 2022.
