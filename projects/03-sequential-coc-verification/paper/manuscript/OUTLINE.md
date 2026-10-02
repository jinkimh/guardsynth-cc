# 논문 아웃라인

## 가제

**Reasoning-Augmented E2E 자율주행 데이터의 판단-반응 시간 일관성 검증: CoC-Nusc와 UPPAAL 기반 에피소드 모델 체킹**

## 한 문장 주장

Reasoning-augmented E2E 자율주행 데이터는 행동의 원인을 설명하는 유용한 학습 신호를 제공하지만, 그 자체로 안전한 제어 명세가 되지는 않는다. 본 논문은 CoC reasoning event와 자차 motion trace를 출처 추적 가능한 시간 계약으로 변환하고, UPPAAL 모델 체킹을 통해 단일 이벤트 및 최종 결과 중심 평가가 놓치는 반복 판단, 지연 반응, 고아 반응, scene 경계 전파 오류를 검출한다.

## 논문이 주장하는 범위

- **검증 대상:** reasoning event와 ego-motion witness 사이의 프로토콜 수준 시간 일관성
- **검증하지 않는 대상:** 신경망 policy 자체, actuator-level brake/throttle/steering 명령, 충돌 가능성, 안전거리, TTC, 차량 동역학
- **안전성 결론:** 현재 evidence만으로 물리적 안전성은 `UNKNOWN`이며, 본 논문은 폐루프 및 물리 안전성 평가 이전의 정형 screening 계층을 제안한다.

## 핵심 기여

1. Reasoning-augmented E2E driving sample을 자연어 설명이 아니라 **시간 의무(obligation)** 와 **반응 witness** 로 재해석하는 문제 정의를 제시한다.
2. CoC-Nusc record를 `CoCSource`, `EgoTrace`, `ObligationManager`, `ReactionObserver`, `DecisionValidator`로 구성된 UPPAAL 네트워크로 컴파일하는 절차를 제안한다.
3. 반복 reasoning event의 Preserve, Reset, Deduplicate 의미론이 동일 trace의 판정을 뒤집을 수 있음을 실제 scene으로 보인다.
4. 94개 scene, 403개 annotation에 대해 282개 모델과 1,128개 query를 실행하여 reasoning-motion 정합성 후보를 선별한다.
5. scene 연속성 metadata audit와 loop-indexed multi-scene model을 통해, 근거 없는 scene 연결을 차단하고 연속성이 입증된 경우 장기 episode 검증으로 확장할 수 있음을 보인다.

## 초록 초안

Reasoning-augmented end-to-end(E2E) driving은 주행 영상과 ego trajectory에 “왜 감속, 정지, 양보, 가속했는가”를 설명하는 언어적 또는 구조적 reasoning signal을 추가하여, 단순 trajectory imitation보다 해석 가능한 학습 신호를 제공한다. 그러나 reasoning text가 존재한다는 사실은 그 판단이 시간 안에 올바른 차량 반응으로 이어졌음을 보장하지 않는다. 특히 같은 판단이 반복될 때 기존 deadline을 유지해야 하는지, 반복 event가 clock을 새로 시작하는지, 또는 중복으로 병합되는지에 따라 동일한 ego-motion trace의 판정이 달라질 수 있다. 본 논문은 CoC-Nusc reasoning annotation과 ego-motion trace를 timed automata network로 변환하고, UPPAAL 모델 체킹을 사용해 reasoning event, 추상 제어 의도, response witness 사이의 시간 계약을 검사한다. 단일 scene feasibility, 94개 scene batch screening, 의심 후보 민감도 분석, scene 연속성 audit, multi-scene chain pilot을 통해 본 방법이 deadline boundary, 반복 의미론 판정 반전, command-response lineage 오류, 근거 없는 scene 연결을 발견할 수 있음을 보인다. 본 결과는 차량의 물리적 안전성 증명이 아니라, reasoning-augmented E2E 학습 데이터가 폐루프 시뮬레이션과 물리 안전성 평가로 넘어가기 전에 수행할 수 있는 protocol-level consistency gate로 해석되어야 한다.

---

# 1. 서론

## 1.1 배경: E2E 주행에서 reasoning-augmented E2E/VLA로

E2E 자율주행은 카메라, 자차 상태, 경로 조건 등으로부터 미래 궤적 또는 제어 의도를 직접 예측하는 방식이다. Planning-oriented E2E 연구는 perception, prediction, planning을 모듈별 규칙으로 분리하기보다 대규모 주행 로그에서 관측 입력과 행동 출력의 관계를 학습한다 [1][2]. 이 접근은 복잡한 주행 장면에서 현실적인 행동 패턴을 학습할 수 있다는 장점이 있지만, 모델이 왜 특정 행동을 선택했는지 설명하기 어렵고, 장면 속 위험 요인과 행동 사이의 인과적 연결을 직접 평가하기 어렵다.

최근 연구는 여기에 reasoning augmentation을 결합한다. 기존 E2E sample이 주로 “관측 입력 -> 미래 궤적” 쌍을 제공했다면, reasoning-augmented E2E/VLA sample은 “전방 트럭 때문에 감속한다”, “보행자 때문에 양보한다”, “공사 구간을 피하기 위해 좌측으로 nudge한다”와 같은 판단 이유를 추가한다 [3][4][5]. DriveLM은 주행 장면을 graph visual question answering 형태로 구조화하고 [3], DriveVLM, Senna, Senna-2, UniDriveVLA는 VLM 기반 장면 이해와 E2E planning/action을 연결한다 [4][6][7][8]. Alpamayo-R1은 Chain-of-Causation(CoC) reasoning과 trajectory/action prediction을 결합하여 long-tail 주행 상황에서 reasoning과 행동을 함께 학습하는 흐름을 보여준다 [5].

Reasoning augmentation이 중요한 이유는 그것이 자연어 장식이 아니라 학습 가능한 중간 표현이기 때문이다. 순수 trajectory supervision에서는 감속이 발생했다는 사실은 볼 수 있어도 그 감속이 선행차, 보행자, 신호, 공사 구간 중 무엇 때문인지 알기 어렵다. 반면 CoC reasoning은 행동 의도와 원인을 함께 제공하므로, 데이터 큐레이션, human review, counterexample-guided fine-tuning, closed-loop 평가 대상 선정에 사용할 수 있다 [5][9][10].

## 1.2 문제: reasoning은 시간 계약을 자동으로 닫지 않는다

Reasoning signal은 유용하지만, reasoning text가 존재한다는 사실만으로 그 sample이 안전한 제어 명세가 되지는 않는다. 첫째, 기록된 주행은 한 운전자가 한 상황에서 선택한 하나의 행동일 뿐, 가능한 모든 안전 행동이나 counterfactual 결과를 포함하지 않는다. 둘째, 기록 차량의 질량, 제동 한계, 마찰 조건, actuator delay, 제어 주기 제약은 학습될 차량과 다를 수 있다. 셋째, VLM/LLM이 생성한 reasoning annotation은 회고적 약한 레이블이므로, 시각적으로 그럴듯해도 causal object를 잘못 지목하거나 기록 trajectory의 정보를 암묵적으로 반영할 수 있다 [9][12].

더 구체적으로, reasoning-augmented E2E driving에는 **판단과 반응 사이의 시간 의미론**이 빠져 있다. 예를 들어 “전방 트럭 때문에 감속한다”는 CoC 문장은 감속 의도와 원인을 제공하지만, 다음 질문에는 답하지 않는다.

- 감속 의무는 어느 시점에 시작되는가?
- 반복된 감속 문장은 기존 deadline을 유지하는가, 아니면 clock을 다시 시작하는가?
- 어떤 ego-speed 변화가 해당 reasoning event의 response witness인가?
- low-quality reasoning event가 기존 trusted 의무를 덮어쓸 수 있는가?
- scene boundary를 넘어 pending obligation을 유지해도 되는가?

이 질문들은 충돌 여부만 보는 closed-loop outcome 평가나, event마다 독립 clock을 시작하는 단일 이벤트 검사로는 충분히 다룰 수 없다. 충돌이 없더라도 판단-반응 lifecycle이 늦거나 잘못 연결될 수 있고, 반복 event가 deadline을 부당하게 초기화하면 최종 trajectory만으로는 문제가 드러나지 않을 수 있다.

## 1.3 동기 사례: scene-0001의 반복 감속 판단

`CoC-Nusc`의 `scene-0001`은 본 논문의 문제를 압축해서 보여준다. 이 장면에는 전방 트럭과 공사 구간을 이유로 한 trusted `DECELERATE` reasoning event가 2.5초에 발생하고, 유사한 감속 reasoning이 3.5초와 4.8초에 반복된다. Ego speed trace에서 기본 detector가 찾은 sustained speed decrease onset은 4.6597초이며, 최초 trusted trigger 기준 response latency는 약 2.1597초이다.

Preserve 의미론을 사용하면 2.5초의 최초 감속 판단이 하나의 pending obligation을 열고, 3.5초와 4.8초의 반복 판단은 clock을 새로 시작하지 않는 repeat trigger로 기록된다. 이 경우 candidate deadline이 2초이면 실패하고, 3초이면 통과한다. 반대로 3.5초의 반복 event를 독립 sample로 취급하면 동일한 ego response가 1.1597초 뒤에 발생한 것으로 계산되어 2초 deadline도 통과한 것처럼 보일 수 있다. 같은 관측 trace가 서로 다른 verdict를 갖는 이유는 차량 움직임이 바뀌었기 때문이 아니라, 반복 reasoning event의 시간 의미론이 정의되지 않았기 때문이다.

여기서 reasoning event는 actuator command가 아니다. `CoC-Nusc` record에는 brake pedal, throttle, steering command가 포함되어 있지 않다. 각 event는 자연어 `cot`에서 추출한 추상 제어 의도 또는 행동 의무를 제공하며, 본 논문에서 관측 가능한 response는 ego speed/trajectory에서 도출한 weak response witness이다. 따라서 정확한 표현은 “각 event가 제어 신호를 출력한다”가 아니라, “각 reasoning event가 추상 제어 의도 또는 시간 의무를 생성하고, 그 의무가 기록된 ego response 또는 학습될 E2E trajectory/control output과 매칭된다”이다.

## 1.4 연구 간극과 연구 질문

본 논문의 간극은 “reasoning이 맞는가” 또는 “차량이 충돌했는가”가 아니라, reasoning-augmented driving data가 **연속 시간 속에서 일관된 판단-반응 protocol trace를 이루는가**이다. 이를 위해 다음 연구 질문을 둔다.

- **RQ1 모델링:** CoC reasoning event와 ego-motion trace를 출처 추적 가능한 timed automata network로 변환할 수 있는가?
- **RQ2 검출:** Episode-level model checking은 단일 이벤트 검사에서 보이지 않는 반복 의미론, deadline, orphan response, provenance 오류를 발견하는가?
- **RQ3 확장:** Scene 간 연속성 증거가 없을 때 근거 없는 장기 sequence 학습을 차단하고, 연속성이 입증된 경우 multi-scene episode 검증으로 확장할 수 있는가?
- **RQ4 활용:** PASS/FAIL 결과를 과도한 안전 주장 없이 E2E 학습 데이터 routing과 closed-loop 평가 triage에 어떻게 사용할 수 있는가?

## 1.5 접근 개요

본 논문은 CoC reasoning annotation을 바로 안전 label로 사용하지 않는다. 대신 각 record를 다음 단계로 변환한다.

```text
CoC reasoning event
        |
        v
intent / hazard / quality parsing
        |
        v
trusted trigger와 audit-only event 구분
        |
        v
ego-motion trace에서 weak response witness 도출
        |
        v
episode-level timed event stream 구성
        |
        v
UPPAAL synchronized automata network 생성
        |
        v
deadline, repeat, provenance, boundary query 검증
        |
        v
학습/검토/폐루프 평가 routing
```

UPPAAL 네트워크는 `CoCSource`, `EgoTrace`, `ObligationManager`, `ReactionObserver`, `DecisionValidator`로 구성된다. `CoCSource`는 reasoning event와 반복 event를 재생하고, `EgoTrace`는 ego-motion에서 도출된 response를 재생한다. `ObligationManager`는 의무의 생성, 대기, 완료, 실패 상태를 관리하고, `ReactionObserver`는 deadline과 반복 clock policy를 검사한다. `DecisionValidator`는 low-quality reasoning이 trusted obligation을 덮어쓰지 못하도록 한다.

## 1.6 결과 요약

단일 장면 feasibility에서 `scene-0001` 정상 모델은 $D=3$초 계약을 만족했지만, $D=2$초 변이는 deadline query에서 실패했다. `no_response`, `clock_reset`, `untrusted_overwrite` mutation은 각각 response 도달성, 반복 clock reset, provenance query를 의도대로 실패시켰다.

94개 scene batch screening에서는 403개 CoC annotation 중 290개가 quality gate를 통과했고, 그중 134개가 longitudinal weak-response contract 적용 가능 event였다. 기본 $D=3$초와 기본 detector에서 129개는 통과했고 5개는 review candidate로 남았다. `scene-0028`과 `scene-0074`에서는 Preserve와 Reset 의미론에 따라 동일 trace의 PASS/FAIL이 뒤집혔다. `scene-0028`의 Deduplicate 실험에서는 command만 제거하고 response lineage가 남아 orphan response가 발생하는 데이터 처리 오류를 확인했다.

Scene continuity audit에서는 로컬 `CoC-Nusc` 단독 데이터가 inter-scene global continuity를 제공하지 않으므로 기본적으로 모든 scene을 독립 episode로 닫아야 함을 확인했다. 추가 nuScenes 호환 metadata mirror를 사용한 pilot에서는 gap 1초 이하의 13개 chain을 구성하고 loop-indexed UPPAAL model로 검증했다. 모든 strict chain은 boundary query를 통과했지만, 9개 chain은 deadline/response query에서 실패하여 continuity audit와 sequence-level contract verification이 서로 다른 정보를 제공함을 보였다.

---

# 2. 데이터와 증거 수준

## 2.1 데이터 출처

본 논문은 nuScenes 기반 driving record에 reasoning annotation이 결합된 `CoC-Nusc` 형식 데이터를 사용한다. 물리적 기록은 nuScenes의 camera와 ego-motion trace에서 오며, reasoning annotation은 CoC autolabeling 형식을 따른다 [12]. 이 annotation은 인간 안전 명세가 아니라 VLM/LLM 기반 회고적 약한 레이블이다. 따라서 `quality_pass`와 validator score는 trusted obligation을 만들기 위한 약한 gate일 뿐, 인간 gold label이나 물리 안전성 증거가 아니다.

## 2.2 Reasoning annotation 생성 절차

CoC annotation은 일반적으로 기록된 video와 ego trajectory에서 meta-action을 도출하고, action transition 주변 keyframe을 선택한 뒤, video clip, ego trajectory, meta-action hint를 VLM/LLM에 입력해 causal behavior annotation을 생성하는 절차를 따른다 [12].

```text
주행 영상 + ego trajectory
        |
        v
trajectory 기반 meta-action 추출
        |
        v
action transition 근처 keyframe 선택
        |
        v
video clip + ego trajectory + meta-action hint 입력
        |
        v
CoC reasoning text 생성
        |
        v
visual / behavior / causal quality scoring
        |
        v
reasoning-augmented sample 저장
```

이 과정에서 생성된 reasoning은 actuator command가 아니라 trajectory-conditioned behavior explanation이다. E2E/VLA 학습에서는 observation history $x_t$, causal text $z_t$, future trajectory 또는 action target $y_t$를 함께 사용하여 reasoning-action consistency를 학습할 수 있다 [5]. 그러나 본 논문은 실제 E2E model을 fine-tuning하지 않고, 이미 생성된 reasoning annotation과 기록 ego-motion이 검증 가능한 episode trace를 이루는지를 다룬다.

## 2.3 데이터 한 건의 실제 구조

`CoC-Nusc` reasoning file은 `data/baseline/coc_nusc/reasoning/ood_reasoning.parquet`이며, `clip_id`별 row 안에 `events` JSON 문자열이 저장된다. 각 event가 하나의 reasoning-augmented record이다.

핵심 필드는 다음과 같다.

- `clip_id`: scene 또는 clip 식별자
- `event_start_timestamp`: scene-local timestamp, microsecond 단위
- `cot`: 행동 의도와 원인을 담은 causal reasoning 문장
- `quality`: visual evidence, behavior match, causal consistency 등 VLM validator 점수
- `quality_pass`: trusted obligation 생성에 사용할 수 있는지 판단하는 boolean gate

`scene-0001`의 대표 event는 다음과 같다.

```json
{
  "clip_id": "scene-0001",
  "event_start_timestamp": 2500000,
  "cot": "Decelerate to maintain a safe distance from the lead truck ahead while navigating through the construction zone.",
  "quality": {
    "visual_evidence_score": 0.90,
    "behavior_match_score": 0.95,
    "decision_supported_by_video": 0.75,
    "causal_consistency_score": 0.70
  },
  "quality_pass": true
}
```

같은 `clip_id` 안의 event list를 시간순으로 정렬하면 episode trace가 된다.

| scene time | reasoning text | quality |
|---:|---|---|
| 2.5 s | lead truck / construction zone 때문에 감속 | pass |
| 3.5 s | stopped truck / construction zone 때문에 감속 반복 | pass |
| 4.8 s | stopped truck / construction zone 때문에 감속 반복 | pass |
| 6.3 s | stopped truck과 construction zone을 피하기 위한 좌측 nudge | pass |
| 9.3 s | construction zone과 worker를 이유로 좌측 nudge | fail |

Ego-motion sidecar는 `data/baseline/coc_nusc/labels/egomotion/scene-0001.egomotion.parquet`이며, timestamp, position, quaternion, velocity, acceleration, curvature 등을 포함한다. 본 논문은 `vx`, `vy`, `vz`에서 ego speed를 계산하고, reasoning event 이후의 sustained speed change를 weak response witness로 도출한다.

## 2.4 증거 수준 구분

본 논문은 모든 event와 transition을 네 수준으로 구분한다. 이 구분은 검증 결과를 안전성 주장으로 과장하지 않기 위해 필요하다.

| 수준 | 의미 | 예 | 허용되는 주장 |
|---|---|---|---|
| 관측 증거 | 원본에서 직접 읽은 값 | `cot`, timestamp, `quality_pass`, camera frame, ego-motion row | 해당 record가 존재한다 |
| 도출 증거 | 관측값에 알고리즘을 적용해 계산 | intent, ego speed, response onset, latency | 해당 규칙과 threshold 아래 response가 계산됐다 |
| 합성 가정 | 실험을 위해 선택한 계약 값 | $D=2,3$초, Preserve/Reset/Deduplicate, detector profile | requirement 후보와 민감도를 시험했다 |
| 합성 변이 | checker 시험용 의도적 오류 | no response, clock reset, untrusted overwrite, orphan response | query가 알려진 결함을 검출한다 |

이 구분에 따라 학습 사용도 달라진다. Source-backed PASS는 약한 positive 후보가 될 수 있지만, synthetic mutation은 checker regression test 또는 violation detector 학습 전용이다. Deadline이 독립 요구사항으로 정당화되지 않은 FAIL은 hard negative가 아니라 review candidate이다. Scene 간 continuity evidence가 없으면 장기 sequence sample로 묶지 않고 독립 clip/window sample로만 사용한다.

---

# 3. 문제 정의: reasoning event에서 시간 의무로

## 3.1 의무(obligation)의 의미

본 논문에서 **의무(obligation)** 는 자연어 CoC 문장이 곧바로 차량 제어 명령이라는 뜻이 아니다. 의무는 checker가 시간 안에 확인해야 할 **추상적인 판단-반응 요구사항**이다.

예를 들어 trusted CoC가 “전방 트럭/공사 구간 때문에 감속한다”라고 말하면, checker는 이를 다음과 같이 변환한다.

```text
DECELERATE 의도가 발생했으므로,
기준 시점 이후 후보 deadline 안에
ego speed/trajectory trace에서 감속 방향 response witness가 관측되어야 한다.
```

의무는 다음 요소를 가진다.

- `trigger`: trusted reasoning event
- `intent`: `DECELERATE`, `STOP`, `YIELD`, `ACCELERATE` 같은 추상 제어 의도
- `deadline`: 예: 2초 또는 3초 후보 기한
- `expected response`: actuator command가 아니라 ego-motion에서 도출한 weak response witness
- `state`: 생성됨, 대기 중, 완료됨, 실패함

따라서 `E<> Obligation.Active` query는 trusted CoC가 UPPAAL 모델 안에서 무시되지 않고 실제 검사해야 할 시간 계약으로 열렸는지 확인하는 reachability 검사이다.

## 3.2 단일 이벤트 검사와 에피소드 검사

단일 이벤트 검사는 각 reasoning event를 독립 sample로 보고 event마다 새 clock을 시작한다. 이 방식은 국소적인 action-response matching에는 유용하지만, 이전 event에서 열린 pending obligation을 유지하지 못한다.

Episode-level 검사는 같은 물리 clip 안의 event들을 시간순으로 연결하고, pending obligation, 최초 trigger 시각, 반복 event 이력, response matching 상태를 유지한다. 관련 없는 scene은 연결하지 않으며, 같은 clip 안의 reasoning event와 ego-motion response만 하나의 episode로 구성한다.

핵심 차이는 반복 event에서 드러난다. 첫 감속 판단 후 같은 감속 판단이 반복되고 실제 response가 한 번만 나타났을 때, 단일 이벤트 검사는 반복 event 기준 빠른 response로 판정할 수 있다. 반면 episode 검사는 최초 obligation 기준 지연 response로 판정할 수 있다. 반복의 의미론을 정의하지 않으면 어느 판정이 맞는지 결정할 수 없다.

## 3.3 시간 계약

Trusted reasoning event가 발생하면 response obligation이 시작된다. 방향성 response는 후보 deadline $D$ 이내에 시작되어야 한다. Response onset은 ego speed trace에서 구간 길이 $W$, 최소 속도 변화 $\delta$, 방향 일치 비율 $\rho$를 사용해 탐지한다.

`STOP` 또는 `YIELD` event 시점에 ego vehicle이 이미 충분히 저속이면, 새 감속 없이 obligation이 충족된 것으로 처리한다. 이는 stop/yield 의미가 “반드시 추가 감속을 하라”가 아니라 “위험 객체 앞에서 진행을 제한하라”에 가깝기 때문이다.

## 3.4 반복 명령의 세 가지 의미론

반복 reasoning event는 세 가지 policy로 비교한다.

| 의미론 | 정의 | 검증상 효과 |
|---|---|---|
| Preserve | 최초 pending obligation의 deadline을 유지 | 반복 event가 response deadline을 완화하지 못함 |
| Reset | 반복 event가 deadline clock을 다시 시작 | 반복 판단 이후 response가 빠르면 PASS로 바뀔 수 있음 |
| Deduplicate | 짧은 시간 안의 동등한 command를 하나로 병합 | command-response lineage를 함께 병합해야 함 |

어느 의미론이 옳은지는 데이터가 자동으로 결정하지 않는다. 이는 system requirement 또는 annotation policy가 정해야 한다. 본 논문은 동일 trace가 의미론 선택에 따라 어떻게 다른 verdict를 갖는지 드러낸다.

## 3.5 추가 프로토콜 속성

Episode-level 계약은 deadline 외에도 well-formedness 속성을 가져야 한다.

- response 수는 수락된 command 수를 초과할 수 없다.
- active obligation이 없을 때 발생한 response는 orphan response이다.
- hazard clearance 전에 recovery 단계로 이동할 수 없다.
- low-quality reasoning은 기존 trusted obligation을 덮어쓸 수 없다.
- scene continuity evidence가 없는 boundary에서는 pending obligation을 다음 scene으로 carry-over하지 않는다.

이 속성들은 물리 법칙이 아니라 reasoning annotation과 ego-motion response를 검증 가능한 protocol trace로 연결하기 위한 정형 조건이다.

---

# 4. 방법: CoC trace를 UPPAAL 네트워크로 컴파일

## 4.1 전체 pipeline

1. CoC reasoning parquet와 ego-motion parquet를 읽는다.
2. `cot`에서 action intent와 hazard term을 추출한다.
3. `quality_pass`로 trusted event와 audit-only event를 구분한다.
4. Ego speed trace에서 response onset을 도출한다.
5. 같은 `clip_id` 안의 event를 시간순 episode로 정렬한다.
6. Deadline, repeat semantics, detector profile을 명시한다.
7. UPPAAL XML과 query set을 생성한다.
8. Baseline과 mutation model을 `verifyta`로 검사한다.
9. Verdict를 evidence level에 따라 PASS, FAIL, UNKNOWN, REVIEW로 해석한다.

## 4.2 UPPAAL 네트워크 구성

UPPAAL 모델은 단일 automaton이 아니라 broadcast channel로 연결된 synchronized network이다.

| Template | 역할 |
|---|---|
| `CoCSource` | trusted trigger, repeat trigger, untrusted event를 timestamp 순서로 재생 |
| `EgoTrace` | ego-motion에서 도출된 response witness를 재생 |
| `ObligationManager` | obligation 생성, Active, Responded, Failed lifecycle 관리 |
| `ReactionObserver` | deadline, repeat clock, response timing 검사 |
| `DecisionValidator` | low-quality event의 trusted state overwrite 방지 |

`CoCSource`가 `first_trigger!`를 방출하면 `ObligationManager`와 `ReactionObserver`가 동시에 `first_trigger?`로 반응한다. `EgoTrace`가 `response!`를 방출하면 obligation lifecycle과 deadline observer가 같은 response를 소비한다. 이 구조 때문에 하나의 event가 여러 property에 동시에 반영되고, pending obligation과 repeated trigger의 state가 보존된다.

## 4.3 scene-0001의 의미론 변환

`scene-0001`은 다음과 같이 원본 evidence에서 UPPAAL event로 변환된다.

| 원본/도출 정보 | UPPAAL event | 의미 |
|---|---|---|
| `2500000us`, trusted truck-related `DECELERATE` | `first_trigger!` at `0ms` | 최초 감속 obligation 생성 |
| `3500000us`, repeated `DECELERATE` | `repeat_trigger!` at `1000ms` | 같은 obligation의 반복 관측 |
| `4659711us`, speed decrease onset | `response!` at `2160ms` | ego trace에서 도출한 weak response |
| `4800000us`, repeated `DECELERATE` | `repeat_trigger!` at `2300ms` | response 이후 반복 label |
| `9300000us`, low-quality CoC | `untrusted_event!` at `6800ms` | trusted overwrite 금지 대상 |

이 변환은 `round((timestamp_us - trigger_us) / 1000)`으로 scene-local timestamp를 최초 trusted trigger 기준 millisecond 상대시간으로 양자화한다. `RESPONSE_DEADLINE=3000`은 물리적으로 검증된 안전 기한이 아니라 후보 시간 계약이다. 따라서 $D=3$초 PASS는 “이 후보 계약 아래에서 response witness가 deadline 안에 있다”는 뜻이지, 안전 인증이 아니다.

## 4.4 대표 query와 판정 의미

대표 query는 다음과 같다.

- `E<> Obligation.Active`: trusted CoC가 obligation을 실제로 생성했는지 확인한다.
- `E<> Obligation.Responded`: response witness가 obligation을 닫는 경로가 있는지 확인한다.
- `A[] not Reaction.DeadlineMiss`: 후보 deadline 안에 response가 오는지 검사한다.
- `A[] not clock_reset_violation`: 반복 event가 금지된 clock reset을 만들지 않는지 검사한다.
- `A[] not untrusted_overwrite`: low-quality reasoning이 trusted decision을 덮어쓰지 않는지 검사한다.
- `A[] not orphan_response`: command 없이 response만 남는 lineage 오류가 없는지 검사한다.
- `A[] not boundary_violation`: continuity evidence 없는 scene boundary를 넘어 obligation이 전파되지 않는지 검사한다.
- `A[] not deadlock`: 의도하지 않은 동기화 정지가 없는지 검사한다.

본 연구의 UPPAAL 모델은 closed-loop reactive controller가 아니다. 기록된 CoC event stream과 ego-motion response stream을 재생하고, monitor automata가 protocol-level property를 검사한다. 따라서 단일 deterministic trace 하나의 PASS만으로는 모델체킹의 의미가 크지 않다. 본 논문에서 UPPAAL의 가치는 여러 monitor, repeat semantics, mutation oracle, multi-scene boundary policy를 같은 formal framework 안에서 선언적으로 결합하고 반례 trace를 얻는 데 있다.

## 4.5 Mutation oracle

Mutation oracle은 baseline PASS가 공허하지 않은지 확인하기 위한 내부 검증 장치이다. 정상 trace와 함께 의도적으로 결함을 삽입한 mutation model을 만들고, 각 mutation에서 어떤 query가 실패해야 하는지 expected verdict matrix와 비교한다.

| Mutation | 삽입 결함 | 기대 실패 |
|---|---|---|
| `deadline_2s` | response는 유지하되 deadline을 2초로 축소 | deadline query |
| `no_response` | ego response event 제거 | response reachability, deadline |
| `clock_reset` | repeat trigger에서 clock reset | clock reset query |
| `untrusted_overwrite` | low-quality event가 trusted state overwrite | provenance query |
| `orphan_response` | command는 제거하고 response만 유지 | orphan response query |
| `late_stop` | stop/hold phase가 deadline 이후 발생 | phase deadline |
| `skip_hold` | hold phase 생략 | reachability/order |
| `premature_recovery` | clearance 전 recovery | clearance precedence |

Mutation은 실제 데이터 결함이라고 주장하기 위한 것이 아니다. 그것은 checker와 query set이 알려진 protocol defect를 구분할 수 있는지 확인하기 위한 synthetic test이며, positive trajectory supervision으로 사용해서는 안 된다.

## 4.6 Multi-scene 확장

로컬 `CoC-Nusc` 단독 데이터에는 scene 간 global timestamp, log id, prev/next relation, global ego pose가 부족하다. 따라서 기본 정책은 모든 scene을 독립 episode로 닫고, scene boundary를 넘어 pending obligation을 carry-over하지 않는 것이다. 이 정책 자체는 negative-control 실험이 된다. 올바른 checker는 continuity evidence가 없는 boundary에서 obligation을 닫거나 `UNKNOWN/discarded_at_boundary`로 처리해야 하며, 이전 scene의 STOP/YIELD/DECELERATE obligation이 다음 scene까지 살아 있으면 pipeline 오류로 본다.

연속성이 입증된 경우에는 여러 scene을 하나의 long episode로 연결할 수 있다. 이때 global timestamp, same log, 짧은 boundary gap, ego pose continuity, object/hazard continuity가 필요하다. Pilot에서는 nuScenes 호환 metadata mirror를 사용해 same-log adjacent scene pair를 찾고, gap 1초 이하이며 로컬 reasoning/egomotion이 있는 scene들을 chain으로 묶었다. 이후 각 scene-local event timestamp에 global scene offset을 더해 하나의 timeline을 만들고, loop-indexed UPPAAL model로 검증했다.

Loop-indexed model은 event마다 transition을 모두 쓰는 대신 `idx`, `event_time[]`, `event_kind[]`, `event_gap[]` 배열을 사용한다. `LoopSource`가 현재 index의 event를 읽어 channel을 발생시키고 `idx++` 하므로, scene 수가 늘어나도 automaton 구조는 유지되고 데이터 배열만 커진다. 동일한 pattern이 많은 대규모 scenario collection에서는 이 방식이 하나의 거대한 unfolded model보다 구조적으로 안정적이다.

---

# 5. 실험 설계

## 5.1 실험 1: 단일 장면 feasibility

대상은 `scene-0001`이다. 이 장면은 반복 감속 reasoning, 도출 가능한 ego-speed response, low-quality event가 모두 포함되어 있어 최소 예제로 적합하다.

검증 절차는 다음과 같다.

1. 2.5초 trusted `DECELERATE` event를 최초 obligation으로 설정한다.
2. 3.5초와 4.8초의 유사 event를 repeat trigger로 처리한다.
3. Ego speed에서 4.6597초 response onset을 도출한다.
4. Preserve semantics와 $D=3$초 baseline을 생성한다.
5. `deadline_2s`, `clock_reset`, `no_response`, `untrusted_overwrite` mutation을 생성한다.
6. Active, Responded, Deadline, Clock reset, Overwrite, Deadlock query를 실행한다.

이 실험은 전체 pipeline이 source-backed single episode에서 동작하는지, 그리고 mutation oracle이 의도한 결함을 검출하는지 확인한다.

## 5.2 실험 2: 다단계 protocol mutation

`scene-0001-chained` 모델은 `FOLLOW -> DECELERATE -> STOP/HOLD -> RECOVER` 흐름을 하나의 network로 구성한다. `DECELERATE` request와 speed response는 `scene-0001` evidence에서 가져오지만, STOP/HOLD/RECOVER 관련 timestamp는 protocol feasibility를 보이기 위한 synthetic assumption이다.

정상 모델과 `late_stop`, `skip_hold`, `premature_recovery`, `no_recovery` mutation을 비교하여 reachability, deadline, order, clearance, deadlock query가 의도한 결함을 검출하는지 확인한다. 이 실험의 목적은 실제 scene이 네 국면을 수행했다는 주장이 아니라, 여러 판단 국면을 연결한 protocol monitor의 표현력과 mutation 검출력을 보이는 것이다.

## 5.3 실험 3: 94개 장면 batch screening

Chunk~0의 94개 scene과 403개 CoC annotation을 대상으로 batch screening을 수행한다. 403개 annotation 중 290개가 `quality_pass`를 통과했고, 134개가 longitudinal weak-response contract 적용 가능 event였다.

각 scene에 대해 baseline, provenance mutation, response mutation model을 생성한다. 총 282개 모델에 대해 네 개 query를 실행하여 1,128개 property evaluation을 수행한다.

| 항목 | 값 |
|---|---:|
| scene | 94 |
| CoC annotation | 403 |
| quality-pass annotation | 290 |
| evaluable longitudinal contract | 134 |
| generated UPPAAL model | 282 |
| property evaluation | 1,128 |

Baseline PASS scene은 weak positive candidate로 남기고, baseline FAIL scene은 곧바로 unsafe case가 아니라 review candidate로 보낸다.

## 5.4 실험 4: 의심 후보 집중 분석

대상은 `scene-0019`, `scene-0028`, `scene-0042`, `scene-0065`, `scene-0074`이다. 이들은 기본 $D=3$초, 기본 detector에서 실패하거나 반복 semantics가 verdict에 영향을 주는 장면이다.

분석 축은 네 가지이다.

- $D=1,2,3,4,5$초 deadline sweep
- Preserve, Reset, Deduplicate repeat semantics 비교
- $W\in\{0.25,0.5,1.0\}$, $\delta\in\{0.05,0.1,0.2\}$, $\rho\in\{0.5,0.7,0.9\}$의 27개 detector profile 민감도
- Camera/contact sheet 기반 visual grounding triage

목적은 FAIL을 바로 hard negative로 확정하는 것이 아니라, deadline boundary, repeat ambiguity, detector sensitivity, grounding uncertainty를 분해해 scene별 routing decision을 정하는 것이다.

## 5.5 실험 5: scene 연속성 metadata audit

장기 inter-scene episode를 만들 수 있는지 확인하기 위해 로컬 `CoC-Nusc`, `nvidia_physicalai` metadata, nuScenes 호환 external metadata mirror를 감사한다. 찾는 정보는 global timestamp, same log/session id, prev/next relation, global ego pose, object track continuity, map context이다.

로컬 `CoC-Nusc` 단독 데이터는 scene 간 continuity evidence를 제공하지 않으므로, 기본적으로 모든 scene을 독립 episode로 닫는다. 외부 metadata mirror에서는 850개 scene, 782개 same-log adjacent pair, 619개 CoC-labeled adjacent pair, 81개 local CoC+egomotion adjacent pair를 찾았다. 예를 들어 `scene-0056 -> scene-0057`은 gap 약 0.5초, `scene-0027 -> scene-0028`은 gap 약 0.6초로 short adjacent 후보이다. 반면 `scene-0001 -> scene-0002`는 gap 약 169.5초로 연속 scene으로 보기 어렵다.

공식 nuScenes mini metadata를 내려받아 schema를 재확인했으며, `scene`, `sample`, `sample_data`, `ego_pose`, `log` 구조를 확인했다. 다만 공식 trainval metadata 전체는 로그인/약관 문제로 직접 재현하지 못했으므로, external mirror 기반 수치는 pilot evidence로 제한한다.

## 5.6 실험 6: connected scene chain pilot

Gap 1초 이하, same-log, local reasoning+egomotion 존재 조건을 만족하는 chain을 loop-indexed UPPAAL model로 검증한다. Pilot에서는 13개 strict chain을 만들었고, 각 chain의 event timeline에 reasoning request, speed response, scene boundary event를 포함했다.

대표 chain은 `scene-0130 -> scene-0131 -> scene-0132 -> scene-0133`이다. 이 chain은 4개 scene, 총 길이 약 79.35초, boundary gap 0.65초/0.60초/0.65초를 가진다. Boundary query는 통과했지만, 첫 yield/slow obligation에 대한 3초 speed response가 부족해 deadline/response query에서 실패했다.

---

# 6. 실험 결과

## 6.1 단일 장면 feasibility

`scene-0001-normal`은 $D=3$초 Preserve semantics에서 모든 query를 통과했다. 첫 trusted deceleration event는 2.5초, response onset은 4.6597초이므로 최초 trigger 기준 latency는 약 2.1597초이다. 따라서 $D=3$초에서는 PASS이고 $D=2$초에서는 FAIL이다.

| variant | Active | Responded | Deadline | Clock reset | Untrusted overwrite | Deadlock |
|---|---:|---:|---:|---:|---:|---:|
| `normal` | PASS | PASS | PASS | PASS | PASS | PASS |
| `deadline_2s` | PASS | PASS | FAIL | PASS | PASS | PASS |
| `clock_reset` | PASS | PASS | PASS | FAIL | PASS | PASS |
| `no_response` | PASS | FAIL | FAIL | PASS | PASS | PASS |
| `untrusted_overwrite` | PASS | PASS | PASS | PASS | FAIL | PASS |

이 결과는 CoC reasoning event와 ego-speed witness를 하나의 timed episode model로 컴파일할 수 있고, mutation oracle이 non-vacuous하게 동작함을 보여준다.

## 6.2 94개 장면 screening

94개 scene, 403개 annotation 중 290개가 quality gate를 통과했다. 이 중 134개가 longitudinal weak-response contract 적용 가능 event였고, 기본 $D=3$초와 기본 detector에서 129개가 통과, 5개가 review candidate로 남았다.

초기에는 8개 실패가 나왔지만, 3개는 이미 충분히 저속인 stop/yield 상황이었다. `already-stopped` 규칙을 추가한 뒤 오탐이 제거되어 최종 실패 후보는 5개가 되었다. 이는 모델체킹 FAIL이 항상 데이터 결함이 아니라, 계약 정의가 관측 가능한 행동 의미를 충분히 반영하지 못한 결과일 수 있음을 보여준다.

## 6.3 반복 의미론에 따른 판정 반전

`scene-0028`에서는 첫 deceleration request 이후 response가 약 3.24초 뒤에 나타나지만, 반복 request 이후에는 약 1.24초 뒤에 나타난다. $D=3$초에서 Preserve는 실패하고 Reset은 통과한다.

`scene-0074`에서도 유사한 acceleration pattern이 나타난다. 첫 acceleration request 기준 response는 약 3.36초 뒤이지만, 반복 request 기준 response는 약 0.86초 뒤이다. Preserve는 실패하고 Reset은 통과한다.

이 결과의 핵심은 동일한 주행 trace가 반복 event 의미론에 따라 서로 다른 verdict를 갖는다는 점이다. 따라서 repeat policy는 실험 후 편의적으로 고르는 parameter가 아니라, E2E 학습 데이터와 checker가 공유해야 할 명시적 요구사항이다.

## 6.4 Deduplicate와 orphan response

`scene-0028`의 Deduplicate-1s 실험에서는 0.7초 간격의 STOP command 하나가 중복으로 제거되었지만, 제거된 command에 연결된 derived response가 trace에 남았다. UPPAAL monitor는 이를 `orphan_response`로 검출했다.

이는 단순한 XML 오류가 아니라 데이터 preprocessing policy의 결함이다. Reasoning text만 deduplicate하고 response lineage를 함께 병합하지 않으면, command 없이 response만 남거나 response가 잘못된 command에 연결될 수 있다. 따라서 deduplication은 command와 response provenance를 원자적으로 병합해야 한다.

## 6.5 Deadline boundary와 detector sensitivity

`scene-0042`와 `scene-0065`는 3초에서는 실패하고 4초 또는 5초에서는 통과하는 deadline boundary 사례이다. 이들은 물리적 위험 사례로 단정할 수 없다. $D=3$초가 법규, 차량 요구사항, actuator delay, braking envelope, 상대 객체 거리/속도에서 도출된 값이 아니기 때문이다.

Detector sensitivity도 크다. 27개 profile 중 3초 안 response를 찾은 profile은 `scene-0019` 4개, `scene-0028` 5개, `scene-0042` 4개, `scene-0065` 5개 수준이었다. `scene-0028`은 4초에서 16개, 5초에서 24개 profile이 response를 찾아 threshold-sensitive boundary candidate로 해석된다.

따라서 단일 detector setting의 FAIL을 unconditional violation으로 승격해서는 안 된다. 민감도는 학습 가중치, human review 우선순위, detector 개선 방향에 반영해야 한다.

## 6.6 다단계 protocol mutation 결과

`scene-0001-chained` 정상 모델은 `FOLLOW -> DECELERATE -> STOP/HOLD -> RECOVER` 흐름의 reachability, deadline, order, clearance, deadlock 속성을 모두 만족했다. 변이 모델은 의도한 query에서만 실패했다.

| variant | Decel | Hold | Recovered | deadline | order | clearance | deadlock |
|---|---:|---:|---:|---:|---:|---:|---:|
| `normal` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `late_stop` | PASS | PASS | PASS | FAIL | PASS | PASS | PASS |
| `skip_hold` | PASS | FAIL | FAIL | FAIL | FAIL | PASS | PASS |
| `premature_recovery` | PASS | PASS | PASS | PASS | PASS | FAIL | PASS |
| `no_recovery` | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS |

다만 이 모델의 일곱 전환 중 실제 source-backed 전환은 두 개뿐이다. Deceleration request는 observed CoC evidence이고, speed response는 ego-motion에서 도출한 derived evidence이다. STOP/HOLD/RECOVER 관련 전환은 synthetic assumption이다. 따라서 이 결과는 protocol monitor와 mutation oracle의 feasibility를 보이는 것이지, 실제 scene의 positive trajectory supervision으로 사용할 수 없다.

## 6.7 Scene continuity와 connected chain pilot

로컬 `CoC-Nusc` 단독 데이터에서는 inter-scene continuity를 증명할 metadata가 부족하다. 따라서 기본 정책은 모든 scene을 독립 episode로 닫고 boundary를 넘어 obligation을 carry-over하지 않는 것이다.

External metadata mirror 기반 pilot에서는 13개 strict chain을 구성했다. 그중 4개는 모든 query를 통과했고, 9개는 실패했다. 실패 중 8개는 deadline fail, 7개는 responded fail이었고 boundary violation은 0개였다. 이는 scene 연결 자체는 metadata 기준으로 정합하지만, 연결된 장기 episode 안에서 reasoning-response deadline mismatch가 별도로 발생할 수 있음을 보여준다.

Exploratory pattern analysis에서는 speed bump가 포함된 fail group이 7/7, parked vehicle 5/5, construction 6/8, lead vehicle 11/17로 관찰되었다. 그러나 이는 인과 증명이 아니라 review queue를 정렬하기 위한 pattern signal이다. 공식 trainval metadata와 object/hazard continuity가 확인되기 전까지 강한 결론으로 사용하지 않는다.

---

# 7. 논의와 활용

## 7.1 안전성 측면의 의미

본 논문이 발견한 것은 물리적 충돌이 아니라 protocol-level specification ambiguity와 data-processing defect이다. 반복 command의 의미가 없으면 response deadline을 일관되게 평가할 수 없고, command-response lineage가 깨지면 학습 데이터의 reasoning-action pair가 왜곡될 수 있다.

따라서 본 결과는 안전 인증이 아니라 safety engineering pipeline의 앞단 signal이다. 충돌이 없더라도 판단-반응 lifecycle은 위반될 수 있고, 모델체킹에서 PASS하더라도 closed-loop policy가 같은 상황에서 다른 trajectory를 만들 수 있다. 최종 안전 판단에는 model checking, human review, closed-loop simulation, physical reachability analysis가 함께 필요하다.

## 7.2 E2E 학습 데이터 routing

검증 결과는 다음과 같이 학습 데이터 처리에 사용할 수 있다.

| 결과 | 학습 사용 | 조건 |
|---|---|---|
| Source-backed PASS | weak positive | quality, grounding, response witness 존재 |
| 정당화된 계약 FAIL | conditional hard negative | deadline/repeat policy가 독립 requirement로 승인됨 |
| Detector-sensitive FAIL | low weight 또는 review | threshold에 따라 verdict 변화 |
| Grounding uncertain | review-only | causal object 확인 부족 |
| Synthetic assumption | checker-only | positive trajectory target 금지 |
| Synthetic mutation | violation detector/checker test | nominal supervision 금지 |
| Continuity absent | independent clip/window | 장기 sequence로 묶지 않음 |
| Continuity proven + contract PASS | sequence-level candidate | 추가 closed-loop/physical 평가 필요 |

중요한 원칙은 반례 자체를 올바른 대안 trajectory로 쓰지 않는 것이다. Mutation trace는 결함 검출기 학습이나 checker regression에는 유용하지만, 정상 주행 행동의 positive label이 아니다.

## 7.3 폐루프 평가와의 관계

모델체킹과 폐루프 평가는 다른 질문에 답한다. 모델체킹은 기록된 reasoning event와 ego-motion witness가 명시한 시간 계약을 만족하는지 묻는다. 폐루프 시뮬레이션은 학습된 policy가 환경과 상호작용할 때 어떤 trajectory를 만드는지 평가한다. 물리 검증은 그 trajectory가 제동 한계, 마찰, actuator delay, TTC, safety distance 안에서 가능한지 평가한다.

권장 pipeline은 다음 순서이다.

```text
reasoning-motion pair
        |
        v
model checking으로 protocol ambiguity / lineage defect 선별
        |
        v
human review
        |
        v
closed-loop replay / simulation
        |
        v
physical safety analysis
```

이 순서가 유용한 이유는 비용과 해석 가능성이다. Model checking은 빠르고 반례 trace가 명확하지만 추상화가 강하다. Closed-loop와 physical analysis는 더 강한 evidence를 주지만 비용이 크다. 따라서 checker는 비싼 평가 이전에 review queue를 줄이고, 어떤 요구사항을 집중적으로 확인해야 하는지 알려주는 triage 역할을 한다.

## 7.4 모델체킹이 꼭 필요한가

현재 single-scene replay처럼 trace가 거의 결정적인 경우, 동일한 deadline 검사는 일반 script로도 구현할 수 있다. 그러므로 본 논문은 “UPPAAL을 썼기 때문에 안전성이 증명된다”고 주장하지 않는다.

UPPAAL의 장점은 요구사항을 timed automata와 temporal query로 명시하고, 여러 observer와 mutation을 같은 framework에서 결합하며, 반례 trace를 일관된 형식으로 얻는 데 있다. 특히 repeat semantics, clock reset, orphan response, boundary carry-over, recovery order처럼 protocol policy가 많아질수록 model checking의 장점이 커진다. 단순 집계는 값은 빨리 줄 수 있지만, 어떤 lifecycle state에서 어떤 temporal property가 깨졌는지 설명하기 어렵다.

## 7.5 대규모 scenario collection으로의 확장

많은 scenario를 모아 하나의 큰 모델을 만들면 다음을 할 수 있다.

- scene별 독립 오류가 아니라 long-horizon obligation lifecycle 오류를 찾는다.
- 같은 hazard pattern이 반복될 때 deadline/response 실패가 특정 상황에 몰리는지 본다.
- continuity evidence가 없는 scene 연결을 boundary policy로 차단한다.
- continuity가 입증된 scene에서는 stale obligation, premature recovery, stop-before-go violation, unresolved yield를 찾는다.
- 반복 구조가 많은 경우 unfolded model 대신 loop-indexed model로 scaling한다.

다만 모든 scene을 무조건 하나의 큰 positive sequence로 묶는 것은 위험하다. 연결의 근거가 없는 scene은 독립 sample로 유지해야 하며, 연결 가능한 chain도 object/hazard continuity가 검증되기 전까지는 exploratory evidence로 제한해야 한다.

---

# 8. 타당성 위협

## 8.1 구성 타당성

본 논문에서 response는 actuator command가 아니라 ego-motion trace에서 계산한 speed/trajectory witness이다. “감속 response가 관측되었다”는 말은 “브레이크 명령이 특정 시각에 발생했다”는 뜻이 아니며, response가 없다는 말도 actuator failure를 의미하지 않는다.

## 8.2 Deadline 타당성

기본 $D=3$초는 feasibility anchor이지 법규나 차량 요구사항에서 도출된 규범적 deadline이 아니다. `scene-0042`, `scene-0065`처럼 3초에서는 실패하고 4초에서는 통과하는 boundary 사례는 이 한계를 보여준다. 실제 안전 요구사항으로 만들려면 actuator delay, braking envelope, relative distance, relative speed, TTC, road friction 등이 필요하다.

## 8.3 Detector 타당성

Response detector는 $W$, $\delta$, $\rho$에 민감하다. 27개 profile을 실행했지만 모든 적절한 detector를 포괄하지는 않는다. 이미 저속인 stop/yield, speed bump, parked vehicle, construction zone처럼 완만한 속도 조절이 중요한 경우에는 단순 speed decrease/increase witness가 행동 의미를 충분히 포착하지 못할 수 있다.

## 8.4 Annotation 타당성

CoC annotation은 인간이 직접 작성한 안전 명세가 아니라 VLM/LLM 기반 autolabeling으로 생성된 회고적 약한 label이다. `quality_pass`와 validator score는 이 위협을 줄이는 gate이지만, human gold annotation이나 독립 sensor grounding을 대체하지 않는다.

## 8.5 합성 전환과 mutation 타당성

`scene-0001-chained` 같은 다단계 모델에는 synthetic assumption이 포함된다. STOP/HOLD/RECOVER 전환은 protocol feasibility를 보이기 위한 값이지 실제 source-backed driving evidence가 아니다. Mutation도 checker 시험용 synthetic fault이므로 positive trajectory supervision으로 사용할 수 없다.

## 8.6 외적 타당성

단일 장면 실험은 chunk~0의 94개 scene과 403개 annotation에 기반한다. 다른 nuScenes split, PAD/CoC 추가 chunk, 다른 reasoning-augmented driving dataset, 실제 학습된 E2E/VLA model output에 적용해야 일반성을 강화할 수 있다.

## 8.7 Scene continuity 타당성

로컬 `CoC-Nusc` 단독 공개 데이터에는 scene 간 global timestamp, log id, prev/next relation, global ego pose, object track continuity가 없다. 따라서 기본 정책은 모든 scene을 독립 episode로 닫는 것이다. Metadata mirror 기반 13개 chain pilot은 inter-scene 검증 가능성을 보였지만, 공식 trainval metadata 전체와 object/hazard continuity로 재확인되어야 한다.

## 8.8 물리 안전성 타당성

본 논문은 상대 객체 거리, 상대 속도, obstacle geometry, actuator 상태, 차량 질량, tire-road friction, braking limit, controller delay를 사용하지 않는다. 따라서 충돌 회피, 안전거리, physical feasibility, deployable control safety는 `UNKNOWN`이다.

---

# 9. 결론

Reasoning-augmented E2E driving data는 행동의 이유를 제공하지만, 판단이 언제 의무를 만들고 언제 반응으로 닫히는지는 별도 시간 의미론이 필요하다. 본 논문은 CoC reasoning event와 ego-motion trace를 UPPAAL timed automata network로 변환하여, 반복 event의 deadline 의미론, response matching, provenance, orphan response, scene boundary policy를 검사하는 방법을 제시했다.

실험은 이 접근이 단일 scene에서는 source-backed feasibility와 mutation 검출력을 보이고, 94개 scene batch에서는 review candidate를 선별하며, connected scene pilot에서는 continuity audit와 sequence-level contract verification이 서로 다른 정보를 제공함을 보였다. 이 결과는 안전 인증이 아니라, reasoning-augmented E2E 학습 데이터가 폐루프 및 물리 안전성 평가로 넘어가기 전에 수행할 수 있는 정형 consistency gate로 해석해야 한다.

향후 연구는 공식 nuScenes trainval metadata 전체, object/hazard track continuity, actuator-level command, 차량 동역학, closed-loop policy output을 통합하여 protocol-level conformance를 물리 안전성 분석과 연결해야 한다.

---

# 권장 그림과 표

| 순서 | 항목 | 목적 |
|---:|---|---|
| 그림 1 | Reasoning-augmented E2E 데이터에서 시간 계약 검증까지의 전체 pipeline | 논문 문제를 한 장에 제시 |
| 그림 2 | `scene-0001` timeline: CoC trigger, repeat, ego response | 반복 의미론 동기 사례 |
| 표 1 | 단일 이벤트 검사 vs episode-level 검사 | 기존 평가와 본 논문 차이 |
| 표 2 | Evidence level taxonomy | 주장 범위 통제 |
| 그림 3 | UPPAAL network templates | 방법 구조 설명 |
| 표 3 | `scene-0001` mutation oracle verdict matrix | non-vacuity 증명 |
| 표 4 | 94개 scene batch screening 결과 | 규모와 feasibility |
| 그림 4 | `scene-0028` 또는 `scene-0074` Preserve/Reset 판정 반전 | 핵심 결과 시각화 |
| 표 5 | 후보 scene deadline/detector sensitivity | review routing 근거 |
| 그림 5 | Multi-scene chain과 boundary policy | scene 연결 확장 설명 |

# 작성 원칙

- 논문 전반에서 “안전성 증명”이 아니라 “protocol-level consistency gate”라는 표현을 유지한다.
- `FAIL`은 충돌 또는 위험이 아니라 지정한 계약 아래의 review signal로 해석한다.
- 모든 실험 결과에는 evidence level, deadline, detector profile, repeat semantics를 함께 표기한다.
- Synthetic assumption과 mutation은 positive driving supervision으로 사용하지 않는다고 반복해서 명시한다.
- UPPAAL은 reactive controller verification이 아니라 trace-replay monitor checking으로 위치시킨다.

---

# 참조 문헌

[1] Y. Hu et al., “Planning-Oriented Autonomous Driving,” CVPR, 2023.

[2] B. Jiang et al., “VAD: Vectorized Scene Representation for Efficient Autonomous Driving,” ICCV, 2023.

[3] C. Sima et al., “DriveLM: Driving with Graph Visual Question Answering,” arXiv:2312.14150, 2023.

[4] X. Tian et al., “DriveVLM: The Convergence of Autonomous Driving and Large Vision-Language Models,” CoRL, 2024.

[5] Y. Wang et al., “Alpamayo-R1: Bridging Reasoning and Action Prediction for Generalizable Autonomous Driving in the Long Tail,” arXiv:2511.00088, 2025.

[6] B. Jiang et al., “Senna: Bridging Large Vision-Language Models and End-to-End Autonomous Driving,” CVPR, 2025.

[7] Y. Song et al., “Senna-2: Aligning VLM and End-to-End Driving Policy for Consistent Decision Making and Planning,” arXiv:2603.11219, 2026.

[8] Y. Li et al., “UniDriveVLA: Unifying Understanding, Perception, and Action Planning for Autonomous Driving,” arXiv:2604.02190, 2026.

[9] S. Xie et al., “Are VLMs Ready for Autonomous Driving? An Empirical Study from the Reliability, Data, and Metric Perspectives,” ICCV, 2025.

[10] L. Zhang et al., “CAT: Closed-Loop Adversarial Training for Safe End-to-End Driving,” arXiv:2310.12432, 2023.

[11] G. Behrmann, A. David, and K. G. Larsen, “A Tutorial on UPPAAL,” Formal Methods for the Design of Real-Time Systems, LNCS 3185, 2004.

[12] NVIDIA Corporation, “Alpamayo CoC Autolabeler,” GitHub repository, 2026.

[13] H. Arai et al., “CoVLA: Comprehensive Vision-Language-Action Dataset for Autonomous Driving,” WACV, 2025.

[14] S. Wang et al., “OmniDrive: A Holistic Vision-Language Dataset for Autonomous Driving with Counterfactual Reasoning,” CVPR, 2025.

[15] H. Caesar et al., “nuPlan: A Closed-Loop ML-Based Planning Benchmark for Autonomous Vehicles,” arXiv:2106.11810, 2021.

[16] D. Dauner et al., “NAVSIM: Data-Driven Non-Reactive Autonomous Vehicle Simulation and Benchmarking,” arXiv:2406.15349, 2024.

[17] S. Shalev-Shwartz, S. Shammah, and A. Shashua, “On a Formal Model of Safe and Scalable Self-Driving Cars,” arXiv:1708.06374, 2017.
