# CoC 계약 기반 E2E fine-tuning과 폐루프 모델체킹 서베이

- 작성일: 2026-08-01
- 상태: 방법론 서베이, 독립 challenge review 및 최소 parameter-grid falsification 완료
- 대상: CoC episode 계약을 E2E 주행 정책 학습, 반례 생성, 폐루프 검증으로 연결하는 방법

## 1. 결론

제안 방법은 연구 파이프라인으로 타당하다. 다만 한 도구로 perception부터 actuator까지 증명하는 구조가 아니라 다음 계층을 합성해야 한다.

1. 기록 trajectory의 STL/episode conformance
2. timed automata를 이용한 연속 의무와 deadline 검증
3. 차량 동역학을 포함한 bounded reachability 또는 hybrid proof
4. E2E 정책의 제한된 입력영역에 대한 출력 경계 검증
5. 모델체커 반례를 재학습하는 counterexample-guided fine-tuning
6. 배포 시 독립 safety monitor와 fallback controller

핵심 안전 속성은 고정 `D=1s` 또는 `D=2s`가 아니라 상태와 차량 능력에 따른 stopping margin이다. 고정 deadline은 서비스 계약 또는 실험 sensitivity anchor로만 유지한다.

```text
always stopping_margin(state, vehicle, uncertainty) >= 0

stopping_margin =
    observed_gap
  - response_distance
  - ego_braking_distance
  + lead_braking_distance
  - uncertainty_margin
```

## 2. 검증 질문의 분해

| 질문 | 적합한 방법 | 얻을 수 있는 결론 | 얻을 수 없는 결론 |
|---|---|---|---|
| 기록된 한 episode가 계약을 지켰는가 | trace checker, STL monitor | 해당 trace의 conformance와 robustness | 다른 환경 분기에서의 안전 |
| 반복 CoC가 clock을 부당하게 초기화하는가 | UPPAAL timed automata | 명시한 시간·환경 추상화의 전 경로 속성 | 비선형 차량 동역학 전체의 안전 |
| 차량 물리 한계에서 충돌 상태가 도달 가능한가 | bounded/hybrid reachability | 정의한 초기집합·외란·동역학 안의 reachability | 모델 밖 실제 차량의 무조건적 안전 |
| 신경망이 특정 입력 구간에서 위험 출력을 내는가 | NN verifier | 제한된 입력영역의 출력 경계 | 물리 plant가 합성된 폐루프 안전 |
| fine-tuning 후 실패가 줄었는가 | closed-loop simulation과 재검증 | 지정 분포의 성능 및 반례 감소 | 형식 증명 자체 |

검증 certificate는 `TRACE_CONFORMANCE`, `TIMED_SYMBOLIC`, `FINITE_GRID_REACHABILITY`, `HYBRID_REACHABILITY`, `NN_IO_BOUND`, `STATISTICAL_ESTIMATE`로 구분해야 한다.

## 3. 방법 서베이

### 3.1 UPPAAL과 timed automata

UPPAAL은 유한 제어구조와 실수 clock을 가진 비결정적 timed automata 네트워크에 적합하다. `A[]`, `E<>`, leads-to query를 통해 안전 불변식, error location 도달성, bounded response observer를 검증할 수 있다. 따라서 반복 CoC, mode transition, sensor/decision/actuator deadline 조합에는 잘 맞는다. 반면 상세 비선형 제동 동역학은 구간 추상화와 그 건전성 계약 없이는 직접적인 물리 증명이 되지 않는다.

- [UPPAAL 공식 문서](https://docs.uppaal.org/)
- [UPPAAL symbolic query 의미론](https://docs.uppaal.org/language-reference/query-syntax/symbolic_queries/)
- [UPPAAL controller synthesis](https://docs.uppaal.org/language-reference/query-syntax/controller_synthesis/)

### 3.2 STL monitoring과 학습 손실

STL quantitative semantics는 기록 trajectory가 계약을 얼마나 여유 있게 만족했는지를 실수 robustness로 표현할 수 있다. RTAMT는 discrete/dense-time STL monitoring을 제공한다. STL robustness를 policy rollout의 손실로 사용하는 neural predictive control과, 미분 가능한 QP/barrier 계층으로 STL 조건을 강제하는 연구도 존재한다. 이 계층은 fine-tuning에 유용하지만 유한 학습 데이터에서 robustness가 개선되었다는 사실을 전역 안전 증명으로 해석하면 안 된다.

- [RTAMT](https://arxiv.org/abs/2005.11827)
- [Signal Temporal Logic Neural Predictive Control](https://arxiv.org/abs/2309.05131)
- [BarrierNet 기반 STL controller 학습](https://arxiv.org/abs/2304.06160)

### 3.3 신경망 입출력 검증

Marabou는 ONNX 등으로 표현된 piecewise-linear 신경망과 선형 입출력 제약을 SMT 문제로 검사한다. E2E 정책 전체의 고차원 영상 공간보다는, 검증 가능한 저차원 state interface 또는 perception uncertainty set에서 `unsafe control output`이 가능한지를 검사하는 데 적합하다.

- [Marabou 공식 문서](https://neuralnetworkverification.github.io/)
- [Marabou Python API](https://neuralnetworkverification.github.io/Marabou/)

### 3.4 연속·하이브리드 동역학 검증

dReach/dReal은 비선형 ODE와 discrete mode를 포함한 bounded delta-reachability를 다룬다. `unsat`과 `delta-sat`의 의미를 구분해야 하며, 후자는 수치적으로 완화된 문제의 witness다. Verisig는 신경망 controller와 plant를 hybrid system으로 합성하는 방향을 제시한다. KeYmaera X는 differential dynamic logic으로 제어 프로그램과 연속 물리를 함께 증명할 수 있지만 모델과 invariant 작성 비용이 크므로 대표 종방향 안전 envelope에 제한하는 것이 적절하다.

- [dReach/dReal](https://dreal.github.io/dReach/)
- [Verisig](https://arxiv.org/abs/1811.01828)
- [KeYmaera X](https://keymaerax.org/)

### 3.5 closed-loop simulation과 scenario evaluation

nuPlan과 Waymax는 정책 출력을 다음 상태에 반영하는 closed-loop 평가를 지원한다. 이는 open-loop trajectory 오차보다 정책 상호작용 평가에 적합하지만 simulation coverage는 proof가 아니다. ISO 34502도 ADS 개발에서 scenario-based safety evaluation framework를 제공한다. 따라서 simulation은 반례 탐색과 통계적 평가에, symbolic/hybrid verification은 정의된 영역의 보장에 사용한다.

- [nuPlan](https://www.nuplan.org/nuplan)
- [Waymax](https://github.com/waymo-research/waymax)
- [ISO 34502:2022](https://www.iso.org/standard/78951.html?browse=ics)

### 3.6 counterexample-guided 학습

Perception과 controller를 대상으로 falsifier가 안전 속성 위반 trace를 찾고, 그 반례로 모델과 controller를 반복 개선하는 선행 연구가 있다. 본 연구에서는 이 구조를 CoC obligation과 provenance까지 확장한다.

- [Counterexample-Guided Synthesis of Perception Models and Control](https://arxiv.org/abs/1911.01523)
- [Safe Policy Learning for Continuous Control](https://proceedings.mlr.press/v155/chow21a.html)

## 4. 제안 아키텍처

```text
sensor/state history
        |
        v
E2E policy pi_theta -----> planned trajectory or target control
        |                              |
        |                       runtime safety filter
        v                              |
closed-loop plant and environment <----+
        |
        v
CoC obligation + STL/timed/hybrid checker
        |
        +-- PASS/robustness
        +-- counterexample + provenance
                       |
                       v
              prioritized replay buffer
                       |
                       v
                 fine-tuning
```

E2E 출력은 raw throttle/brake보다 planned trajectory 또는 target acceleration으로 제한하는 편이 검증 interface를 작게 만든다. Raw actuator E2E를 검토할 때는 action projection, control barrier 또는 검증된 fallback controller를 정책 밖에 유지한다.

## 5. 형식 모델

### 5.1 상태와 외란

```text
x = (gap, v_ego, v_lead, a_ego, brake_state, mode, obligation_clock)
u = (requested_acceleration, requested_steering)
w = (lead_acceleration, friction, grade, sensor_error, actuator_delay)
```

모든 물리 파라미터는 source, unit, interval, calibration date를 가진다. 차량 사양 또는 측정 근거가 없으면 `SYNTHETIC_EXPERIMENT_PROFILE`로 표시하고 safety PASS를 만들지 않는다.

### 5.2 속성

```text
P-SAFE-1: A[] not Collision
P-SAFE-2: A[] stopping_margin >= 0
P-PHYS-1: A[] requested_control in feasible_control_set
P-RESP-1: critical --> effective_braking
P-MRM-1: unavoidable --> minimal_risk_maneuver
P-PROG-1: road_clear_and_permitted --> resumed_progress
```

가변 `D_safe(x)`는 고정 clock bound로 억지 변환하기보다 `stopping_margin >= 0` 불변식으로 우선 검사한다. 구현상 deadline observer가 필요하면 상태공간을 안전 deadline band로 분할하고 각 band의 추상화 방향을 기록한다.

### 5.3 assume-guarantee 경계

```text
A_perception: true object state lies in reported uncertainty interval
G_policy:     policy output lies in the verified control envelope
A_vehicle:    calibrated plant parameters lie in declared intervals
G_system:     unsafe set is unreachable within the verified horizon
```

어느 assumption도 실제 증거로 닫히지 않으면 최종 판정은 PASS가 아니라 UNKNOWN이다.

## 6. Counterexample-guided fine-tuning 절차

1. 정상 trajectory로 behavior cloning 또는 planner fine-tuning을 수행한다.
2. 물리 파라미터와 환경 행동을 변화시키며 closed-loop rollout을 생성한다.
3. STL monitor로 robustness를 계산하고 timed/hybrid checker로 unsafe reachability를 검사한다.
4. 실제 simulator에서 재현되는 반례만 counterexample buffer에 저장한다.
5. 추상화에서만 발생한 반례는 입력 구간과 plant abstraction을 세분화한다.
6. imitation loss, contract robustness, collision margin, physical feasibility, comfort를 함께 최적화한다.
7. train 반례와 분리된 holdout initial set에서 다시 모델체킹한다.
8. 종료 시 남은 UNKNOWN, timeout, 제외 범위와 runtime fallback을 함께 보고한다.

```text
L_total = L_imitation
        + lambda_contract * softplus(-rho_STL)
        + lambda_collision * relu(-stopping_margin)
        + lambda_physical * distance(u, feasible_control_set)
        + lambda_comfort * jerk_penalty
```

## 7. scene-0001 최소 parameter-grid falsification 실험

### 7.1 구현

`experiments/feasibility/check_longitudinal_falsification.py`는 최초 trusted truck-related `DECELERATE` 시점의 실제 ego 속도를 읽고, 누락된 물리 상태는 유한 합성 grid로 열거한다. reachable state graph, nondeterministic transition 또는 SAT/SMT encoding을 사용하지 않으므로 이 구현 자체를 bounded model checker라고 부르지 않는다.

```bash
python experiments/feasibility/check_longitudinal_falsification.py \
  > artifacts/results/public/scene-0001/longitudinal-falsification-result.json
```

기본 profile은 다음과 같다.

```text
ego speed               4.8143 m/s, scene에서 관측
initial gap             5, 10, 15, 20, 25, 30 m, 합성
lead speed              0 m/s, 정지 lead 가정
available ego decel     3, 5, 7 m/s^2, 합성
brake build-up          0.2, 0.5 s, 합성
response delay          0.5, 1, 2 s + 2.1597 s heuristic anchor
horizon / step          5 s / 0.1 s
```

### 7.2 결과

| response delay | 열거 상태 | collision witness | 모든 합성 제동조건에서 안전한 최소 시험 gap |
|---:|---:|---:|---:|
| 0.5 s | 36 | 3 | 10 m |
| 1.0 s | 36 | 6 | 10 m |
| 2.0 s | 36 | 12 | 15 m |
| 2.1597 s | 36 | 13 | 20 m |

이 실험은 응답 지연, 초기 gap, 제동능력과 build-up을 합성한 연속 episode falsifier가 witness를 생성할 수 있음을 보인다. 특정 speed-trace heuristic의 `2.1597s`를 사용하면 시험 grid의 일부 상태가 collision에 도달하지만, 이 값은 active braking이나 actuator latency 측정값이 아니다.

그러나 실제 scene의 gap, lead track, 노면 마찰, ego 제동 envelope가 없으므로 이 witness는 scene-0001의 실제 반례가 아니다. 반대로 20m 이상 시험점에서 witness가 없었다는 사실도 유한 grid와 5초 horizon 밖의 안전을 증명하지 않는다.

### 7.3 checker 분류

```text
checker_type      PARAMETER_GRID_FALSIFICATION
certificate_kind  DETERMINISTIC_SCENARIO_SWEEP
soundness_scope   NOT_A_CONTINUOUS_OR_REAL_VEHICLE_SAFETY_PROOF
```

## 8. 브레인스토밍 결과와 대안 비교

### 대안 A: 모든 것을 UPPAAL에 구간화

가장 빠르게 CoC와 deadline을 합성할 수 있다. 하지만 stopping distance 경계에서 구간 폭이 크면 거짓 반례가 늘고, under-approximation을 사용하면 거짓 PASS가 생길 수 있다. 초기 episode 검증에는 채택하되 물리 안전 증명의 최종 도구로 단독 사용하지 않는다.

### 대안 B: E2E 네트워크와 비선형 plant를 한 번에 검증

목표 보장은 가장 강하지만 영상 입력, 긴 horizon, recurrent state, multi-agent dynamics 때문에 초기 feasibility 범위를 벗어난다. 대표 저차원 latent/state interface와 짧은 종방향 horizon으로 제한할 때만 후속 검토한다.

### 대안 C: simulation과 adversarial search만 사용

반례 발견과 fine-tuning에는 효율적이지만 `반례를 찾지 못함`을 안전 증명으로 바꿀 수 없다. statistical evidence 계층으로 유지한다.

### 대안 D: runtime shield만 사용

배포 위험을 줄일 수 있으나 CoC 정책 자체의 결함과 과도한 intervention을 숨길 수 있다. shield intervention을 학습 metric과 counterexample provenance에 포함하고, offline verification을 대체하지 않는다.

### 채택안

```text
Phase 1  trace checker + parameter-grid falsification
Phase 2  UPPAAL episode automata + observer mutation tests
Phase 3  calibrated longitudinal hybrid reachability
Phase 4  E2E policy interface NN verification
Phase 5  counterexample-guided fine-tuning + independent runtime shield
```

## 9. 타당성 위협

1. 현재 finite grid는 deterministic simulation의 유한 parameter sample이므로 no-witness는 proof가 아니다.
2. scene-0001의 장애물 track이 없어 실제 gap과 상대속도를 검증하지 못했다.
3. egomotion은 실제 actuator command가 아니며 정책 출력도 아니다.
4. 제동 model은 1차원이며 steering, grade, tire saturation과 combined-slip을 제외한다.
5. CoC trigger를 perception detection time으로 간주하는 가정이 아직 정당화되지 않았다.
6. 합성 제동 파라미터는 실제 차량 calibration이 아니다.
7. 한 scene에서의 결과는 E2E 정책 분포 전체로 일반화되지 않는다.
8. model checker timeout과 abstraction refinement 비용이 위험 사례에 편중될 수 있다.
9. `quality_pass`는 같은 계열 VLM의 self-evaluation이며 trusted event 선택에 독립 gold evidence가 없다.
10. speed 감소 heuristic은 active braking과 coasting을 구분하지 못한다. 36개 threshold profile 중 9개는 응답을 찾지 못했고, 검출 latency는 `1.7790~4.0197초`였다.
11. falsifier의 충돌 검사는 현재 `0.1초` step 경계에서 수행되므로 step 내부 crossing 시점에는 양자화 오차가 있다.

### 9.1 독립 challenge review 반영

읽기 전용 외부 reviewer로 문서와 구현을 다시 검토했다. 그 결과 finite-grid 구현의 model-checking 용어 오용, hardcoded clock verdict, 감속 heuristic의 construct validity, self-evaluated `quality_pass` 누락을 blocking issue로 식별했다. 구현 유형을 falsification으로 정정하고 clock anchor를 계산하도록 변경했으며, 36개 감속 threshold sensitivity와 headline 결과 회귀 테스트를 추가했다. 실제 obstacle 및 raw brake evidence가 확보되기 전에는 `2.1597초`를 calibrated delay로 사용하지 않는다.

## 10. 다음 증거 게이트

1. `obstacle.offline` 또는 nuScenes annotation에서 truck track, gap, relative speed를 확보한다.
2. 대상 차량의 제동시험 또는 datasheet로 deceleration, build-up, latency interval을 고정한다.
3. 유한 grid를 interval over-approximation 또는 dReal hybrid model로 교체한다.
4. 동일 계약의 positive, negative, boundary, mutation model을 만든다.
5. 작은 state-to-control policy를 ONNX로 export하고 Marabou input/output bound를 검사한다.
6. 생성 반례를 closed-loop simulator에서 재현한 뒤 fine-tuning 전후 violation rate와 최소 robustness를 비교한다.

## 11. UPPAAL timed-episode 구현 상태

UPPAAL 5.0.0 명령행 verifier를 설치하고 scene-0001의 timed protocol을 다섯 모델로 생성했다. 모델은 `CoCSource`, `EgoTrace`, `ObligationManager`, `ReactionObserver`, `DecisionValidator`로 구성되며 최초 trigger 이후 반복 CoC가 clock을 reset하지 않는지, candidate deadline을 넘는지, response가 존재하는지, low-quality event가 trusted decision을 덮어쓰는지 검사한다.

```text
E<> Obligation.Active
E<> Obligation.Responded
A[] not Reaction.DeadlineMiss
A[] not clock_reset_violation
A[] not untrusted_overwrite
A[] not deadlock
```

정상·2초 deadline·clock reset·no response·untrusted overwrite variant의 XML과 expected mutation matrix를 생성하고 UPPAAL 5.0.0 `verifyta`로 총 30개 query를 symbolic verification했다. 결과는 다음 mutation oracle과 모두 일치했다.

```text
normal                 all six queries PASS
deadline_2s            bounded response FAIL
clock_reset            clock-reset integrity FAIL
no_response            response reachability, bounded response FAIL
untrusted_overwrite     trust-policy integrity FAIL
```

첫 실행에서 terminal state가 deadlock으로 검출된 반례를 확인해 의도적 종료에 terminal stutter를 명시했다. 수정 후 모든 variant의 deadlock query가 PASS했다. 따라서 `UPPAAL_TIMED_PROTOCOL_MUTATION_FEASIBILITY=PASS`로 판정한다. 이는 명시한 event replay와 mutation에 대한 symbolic 결과이며 collision dynamics, 실제 active braking 또는 E2E policy 전체의 안전 증명은 아니다.

이 게이트 전의 올바른 결론은 다음과 같다.

> CoC 연속 의무, 응답 지연과 차량 물리를 합성하여 유한 합성 scenario에서 collision witness를 생성하는 파이프라인은 구현 가능하다. 현재 scene-0001의 실제 충돌 안전성은 필수 물리 증거 누락으로 UNKNOWN이다.
