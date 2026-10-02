# 실제 장면 근거의 가상 차량 assurance 투영 설계 v0.1

## 목적

실제 차량의 제동·지연 보장값이 없는 상태에서도 장면 grounding 이후 파이프라인을 검증할
수 있도록 실제 장면 근거와 가상 차량 동역학을 명시적으로 분리한다.

```text
recorded scene evidence (8/9) ─┐
                               ├─ simulation projection request
simulated vehicle binding ─────┘              │
                                              ▼
                               GuardSynth → EBLC → Core → Z3
```

## 불변식

1. recorded-rig binding과 simulation binding은 같을 수 없다.
2. 실제 차량의 `source_bearing_vehicle_assurance_profile` gap은 닫지 않는다.
3. 모델 수치는 `SIMULATION_MODEL_SPECIFICATION`으로만 표시한다.
4. Alpamayo CoC는 `CLAIMED` provenance로만 보존한다. 조건부 공식 규칙 근거는
   별도의 applicability provenance이며, 둘 다 activation 또는 제동 수치가 아니다.
5. 현재 hazard는 `DERIVED_GEOMETRIC_PEDESTRIAN_TRACK_EGO_CORRIDOR_OVERLAP`이다. 충돌
   예측이나 법적 conflict-zone 판정으로 승격하지 않는다.

## 종방향 모델

초기 속도를 `v`, 응답 지연을 `t_r`, 일정 감속 크기를 `a`라 하면 모델 내부 정지거리는

```text
d_stop = v * t_r + v^2 / (2 * a)
```

이다. 고정 시간 간격 trace는 각 구간의 등가속도 식으로 적분하며 마지막 구간을 정확한
정지 시점에서 자른다. 노면, 경사, 온도, 타이어, jerk와 actuator fault는 모델링하지 않는다.

## 종료 판정

시뮬레이션 경로는 생성·Core 변환·Z3 query agreement와 관측 속도 대입을 모두 통과하면
`SIMULATION_PATH_EXECUTED_REAL_VEHICLE_PATH_STILL_BLOCKED`로 기록한다. 이는 실제 24장면
source-complete gate나 실제 차량 안전 gate의 통과가 아니다.
