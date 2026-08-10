# CoC 계약 기반 E2E 자율주행의 학습 및 폐루프 안전성 연구 계획

- 기준일: 2026-08-02
- 1차 정형기법: Signal Temporal Logic(STL), Control Barrier Function(CBF)
- 목표: NeurIPS급 기계학습 연구
- 상세 선택 근거: `METHOD_SELECTION_SURVEY.md`
- 이전 UPPAAL 우선안: `UPPAAL_FIRST_OPTION.md`

## 1. 연구 목적

E2E 자율주행은 인간 시연에서 perception-to-action 정책을 학습한다. 그러나 한 번의 성공 시연은 가능한 모든 안전 행동을 명세하지 않으며, 연속 사건에서 언제 기존 의무를 유지하거나 종료해야 하는지도 보증하지 않는다. CoC reasoning은 원인, 판단, 행동, 예상 결과를 드러내지만 그럴듯한 설명도 안전 증명은 아니다.

본 연구의 목적은 CoC를 그대로 신뢰하는 것이 아니라 다음 두 형식 계층으로 바꾸어 **검사하고, 실행을 보호하고, 다시 학습에 반영하는 것**이다.

```text
multi-camera + ego state
          |
          v
 E2E model: CoC + trajectory
          |
          +--> grounded CoC-to-STL --> robustness/counterexample
          |
          +--> CBF-QP safety filter --> safe control/intervention
                                      |
                                      v
                        hard-negative / preference / fine-tuning
```

핵심 주장은 “CoC가 안전을 증명한다”가 아니다. CoC는 **검증 가능한 시간계약을 생성하는 중간 인터페이스**이며, CBF는 명시적 동역학 가정 아래 실행 단계의 물리 안전을 보완한다.

## 2. 중심 가설

> 영상에 근거한 CoC를 정량적 STL 계약으로 변환하고, 위반 robustness와 CBF 개입으로 생성한 반례를 학습에 재사용하면, trajectory-only 또는 reasoning-only 학습보다 연속 사건의 계약 만족률과 폐루프 안전성을 향상시키면서 nominal driving quality의 손실을 제한할 수 있다.

이 가설은 세 하위 가설로 분해한다.

- H1: CoC는 trajectory만으로는 관측하기 어려운 trigger, deadline, hold, release 의미를 복원한다.
- H2: STL robustness는 binary label보다 경계 사례 채굴과 fine-tuning에 더 유용하다.
- H3: STL 학습과 CBF 실행 필터를 결합하면 어느 하나만 사용할 때보다 의미 일관성과 물리 안전을 함께 개선한다.

## 3. 연구 질문

### RQ1. 계약 생성

실제 모델 생성 CoC의 몇 퍼센트를 typed, grounded STL로 자동 변환할 수 있으며 human agreement는 어느 정도인가?

### RQ2. 신규 오류 검출

trajectory metric, collision metric, UPPAAL baseline이 놓치는 어떤 연속 reasoning-action 오류를 STL robustness가 검출하는가?

### RQ3. 계약 불확실성

`D_brake`, `TTC_min`, clearance duration을 고정 상수가 아니라 데이터ㆍ차량ㆍ센서 불확실성에서 보정하면 false alarm과 miss가 어떻게 변하는가?

### RQ4. 학습 효과

STL counterexample-guided fine-tuning이 unseen event composition에서 계약 만족도와 폐루프 안전을 개선하는가?

### RQ5. 실행 보증

CBF safety filter는 collision/road departure를 얼마나 줄이며, 개입률ㆍtrajectory deviationㆍinfeasibility 비용은 얼마인가?

### RQ6. 계층 결합

STL PASS인데 CBF가 개입하거나 STL FAIL인데 CBF가 개입하지 않는 disagreement가 어떤 데이터 및 모델 결함을 나타내는가?

## 4. 형식화

### 4.1 모델 출력

시점 `t`의 모델 출력을 다음으로 둔다.

```text
y_t = (r_t, tau_t)
r_t: generated CoC reasoning trace
tau_t = {(x_hat, y_hat, yaw_hat, v_hat)_t...t+H}: planned trajectory
```

환경 관측과 추적 상태는 `o_t`, 실제/시뮬레이션 차량 상태는 `x_t`, nominal control은 `u_nom,t`로 둔다.

### 4.2 Grounded Contract IR

CoC에서 바로 공식을 생성하지 않고 중간 표현을 둔다.

```yaml
event_id: e17
source:
  model_revision: pinned
  clip_id: ...
  inference_step: 23
cause:
  predicate: pedestrian_in_conflict_zone
  grounding: track_104
  confidence: 0.91
obligation:
  action: DECELERATE
  response_interval_s: [0.0, 1.2]
  maintain_while: pedestrian_in_conflict_zone
termination:
  condition: pedestrian_cleared
  stability_interval_s: [0.3, 0.7]
next_action:
  action: RESUME
  allowed_if: pedestrian_cleared_stably
uncertainty:
  perception_error_m: 0.4
  latency_s: [0.08, 0.18]
```

필수 검사는 다음과 같다.

- type validity
- object/track grounding
- temporal interval validity
- trigger와 termination의 관측 가능성
- repeated command semantics
- provenance completeness

변환 불가능한 CoC는 억지로 공식화하지 않고 `SPECIFICATION_INCOMPLETE` 또는 `UNGROUNDED`로 판정한다.

### 4.3 STL 계약

대표 formula template은 다음과 같다.

```text
Response:
G(trigger -> F_[l,u] response)

Hold:
G(hazard -> safe_mode)

Release:
G(next_action -> cleared_stably)

No premature recovery:
G(hazard -> !resume)

Physical margin:
G(TTC >= TTC_min and d_front >= d_safe(v, latency, a_brake))
```

각 공식에 quantitative robustness `rho`를 계산한다. episode 점수는 단순 평균뿐 아니라 minimum robustness와 하위 분위수를 함께 사용하여 짧은 중대 위반이 평균에 묻히지 않게 한다.

### 4.4 CBF 안전 필터

저차원 차량 모델에서 collision, road boundary, actuator envelope마다 barrier `h_i(x)`를 정의한다.

```text
u_safe = argmin_u ||u - u_nom||^2_Q + lambda * ||slack||

subject to
  L_f h_i(x) + L_g h_i(x) u + alpha_i(h_i(x)) >= -slack_i
  u_min <= u <= u_max
```

hard safety constraint에는 원칙적으로 slack을 허용하지 않는다. 실험에서 infeasible 상태를 숨기지 않고 별도 지표로 보고한다. perception/state uncertainty는 robust margin 또는 bounded disturbance로 포함한다.

## 5. 핵심 방법

### M1. Grounded CoC-to-STL compiler

1. CoC에서 cause, action, effect, temporal cue를 추출한다.
2. cause/effect 명사를 tracker와 map/scene predicate에 grounding한다.
3. 허용된 formula template과 typed grammar만 생성한다.
4. formula를 trajectory/state signal에 대해 실행하여 즉시 검증한다.
5. 전문가가 공식과 근거를 함께 검토한다.

자유 형식 LLM 번역과 grammar-constrained 번역을 비교한다. 컴파일 성공률만 높이는 것이 아니라 semantic equivalence와 grounding precision을 평가한다.

### M2. Contract calibration

deadline을 임의로 `D=1 s` 또는 `2 s`로 고정하지 않는다.

- 차량 제동 성능과 actuator delay
- ego/상대 속도와 거리
- perception 및 inference latency
- expert demonstration의 response distribution
- 법규 또는 검증된 domain rule

에서 interval을 만든다. 데이터 기반 threshold에는 train/calibration/test 분리를 적용하고 conformal coverage를 보고한다. 물리적으로 불가능한 deadline은 contract 오류로 판정한다.

### M3. Counterexample generation

실제 출력과 다음 mutation을 검사한다.

- response delay 삽입
- premature resume
- hold 삭제
- cause/track 교체
- repeated command의 preserve/reset 변경
- trajectory와 reasoning action의 부호 반전
- sensor clearance delay
- cut-in 또는 pedestrian persistence 연장

각 반례는 최초 음의 robustness 시점, 위반 predicate, 관련 CoC span, trajectory segment를 포함한다.

### M4. Verification-guided learning

세 학습 방식을 비교한다.

1. `STL-weighted SFT`: 만족 여유에 따른 sample weighting
2. `STL preference optimization`: positive trajectory와 최소 변형 counterexample pair
3. `STL robustness regularization`: differentiable surrogate를 trajectory loss에 결합

```text
L = L_traj + beta L_reason_action + gamma L_STL
```

CoC 텍스트 자체를 정답으로 과신하지 않는다. grounding 실패, 계약 모호성, 물리 infeasibility가 있는 표본은 positive SFT에서 제외한다.

### M5. Runtime safety filtering

fine-tuned policy의 nominal control을 CBF-QP로 필터링한다. intervention은 단순 실패가 아니라 학습 신호가 된다.

- 반복 개입 구간: policy가 학습하지 못한 unsafe manifold
- 큰 수정량: reasoning과 물리 가능성의 강한 불일치
- infeasible QP: 초기 상태, uncertainty bound, barrier 설계의 한계

필터로 안전해진 결과만 보고하지 않고, nominal policy 안전성과 filtered system 안전성을 분리해 보고한다.

## 6. 실험 설계

### E0. 실제 모델 출력 확보

`ALP-EXP-005`를 실행하여 동일 clip의 여러 seed와 연속 inference step에서 실제 생성 CoC와 trajectory를 확보한다. annotation 기반 기존 실험은 별도 표기하며 모델 생성 출력과 섞지 않는다.

### E1. CoC-to-STL benchmark

- 초기: 100--300 episode
- 확대: 사건 유형별 균형을 맞춘 1,000+ episode
- 이중 전문가 annotation과 adjudication
- single-event와 composed multi-event split 분리
- scene-disjoint, geography/weather-disjoint test

평가:

- exact/template validity
- predicate grounding precision/recall
- temporal bound error
- human semantic equivalence
- coverage, abstention accuracy

### E2. 오류 검출 benchmark

정상 출력과 controlled mutation을 섞되 evaluator가 mutation label을 보지 않게 한다.

비교군:

- trajectory ADE/FDE만 사용
- collision/TTC metric
- LLM-as-judge
- rule-based event checker
- 기존 UPPAAL episode checker
- binary STL monitor
- quantitative STL monitor

측정:

- 오류 유형별 AUROC/AUPRC
- first-detection time
- false alarm per driving hour
- minimum perturbation to detection
- counterexample localization IoU

### E3. Open-loop fine-tuning

동일 base model과 동일 데이터 예산에서 비교한다.

- trajectory-only SFT
- CoC + trajectory SFT
- random hard-negative
- STL-weighted SFT
- STL preference
- STL robustness regularization

측정:

- ADE/FDE 및 trajectory feasibility
- CoC-action consistency
- STL satisfaction rate
- mean/min/CVaR robustness
- unseen composition generalization

### E4. Closed-loop simulation

CARLA 또는 동등한 폐루프 simulator에서 다음 사건을 구성한다.

- pedestrian enter-persist-clear
- lead brake-stop-recover
- cut-in followed by signal change
- occlusion with delayed clearance
- repeated reasoning/command update
- simultaneous longitudinal and lateral obligation

factorial variation:

- speed, friction, actuator lag
- perception latency/noise
- actor behavior and persistence
- weather/visibility
- event order and overlap

### E5. CBF ablation

- no filter
- heuristic emergency brake
- CBF nominal dynamics
- robust CBF with bounded uncertainty
- 저차원 HJ reachability oracle

측정:

- collision and road departure
- near-miss/TTC distribution
- CBF intervention rate/duration
- control and trajectory deviation
- QP infeasibility
- task completion and comfort

### E6. End-to-end ablation

| STL 학습 | CBF 필터 | 목적 |
|---|---|---|
| 없음 | 없음 | base policy |
| 있음 | 없음 | 학습 효과 |
| 없음 | 있음 | 실행 필터 효과 |
| 있음 | 있음 | 결합 효과 |

추가 ablation:

- CoC 없이 trajectory에서 직접 STL
- ungrounded CoC-to-STL
- fixed deadline vs calibrated interval
- single event only vs composed episode
- binary satisfaction vs quantitative robustness
- actual CoC vs annotation-derived pseudo-CoC

## 7. 데이터 분할과 누수 방지

- 같은 원본 clip의 seed/augmentation은 하나의 split에만 둔다.
- 동일 actor track 또는 연속 frame이 train/test에 교차하지 않게 한다.
- contract calibration에는 test trajectory를 사용하지 않는다.
- mutation 생성 규칙 일부를 test에서 hold out한다.
- 모델 revision, dataset revision, prompt, seed, decoder setting을 기록한다.

## 8. 성공 기준

수치는 pilot 후 power analysis로 확정하되 1차 게이트는 다음과 같다.

- CoC-to-STL semantic equivalence 85% 이상, 오류 유형별 confidence interval 보고
- grammar/grounding 없는 변환보다 유의한 false-formula 감소
- unseen composed events에서 baseline 대비 minimum STL robustness 개선
- no-filter 대비 collision/road departure 감소
- CBF intervention rate가 학습 후 감소하여 필터 의존성이 줄어듦
- nominal ADE/FDE, comfort, completion의 허용 가능한 trade-off
- 실제 출력에서 최소 하나 이상의 자연 발생 semantic-physical disagreement 발견

합성 mutation 검출만 성공하고 실제 출력 오류를 찾지 못하면 feasibility 결과로 한정한다.

## 9. 예상 기여

### C1. CoC-to-Contract benchmark

실제 reasoning, grounded predicate, STL formula, trajectory, counterexample를 연결한 benchmark와 판정 protocol.

### C2. Grounded and calibrated compiler

자연어 형식 변환을 넘어 scene evidence와 차량 가능성으로 계약을 검증하는 compiler.

### C3. Verification-guided post-training

정량적 robustness와 최소 반례를 E2E trajectory/reasoning 학습에 연결하는 방법.

### C4. Semantic-physical dual safety

STL 의미계약과 CBF 실행 불변성을 결합하고 disagreement를 데이터 품질 및 모델 실패 신호로 사용하는 방법.

### C5. Episode-level evaluation

단일 프레임 성공이나 최종 collision 여부가 아닌, 연속 사건에서 제어 의무의 생성ㆍ유지ㆍ종료ㆍ선점을 평가하는 protocol.

## 10. NeurIPS 제출 판단

다음 수준이면 NeurIPS main-track 주장이 약하다.

- UPPAAL로 몇 개 scene를 수동 모델링
- 합성 mutation만 검출
- CoC를 자연어 설명으로만 평가
- safety filter 적용 후 collision 감소만 보고

다음이 함께 있어야 경쟁력이 생긴다.

- 재현 가능한 실제 모델 출력 benchmark
- grounded CoC-to-STL 변환의 학습 또는 algorithmic novelty
- 불확실성을 포함한 calibrated contract
- counterexample-guided fine-tuning의 일반화 이득
- 폐루프 대규모 평가와 안전/성능 trade-off
- 기존 temporal-logic learning, safe imitation, safety filter 대비 강한 baseline

논문의 1차 제목 후보:

> **From Causal Reasoning to Certified Control: Grounded Temporal Contracts for End-to-End Driving**

과도한 “certified E2E model” 표현은 피한다. certification 대상은 명시한 contract monitor와 CBF-filtered execution이며 전체 VLA가 아니다.

## 11. 실행 순서

### Phase 1: 4주, 측정 가능성

- ALP-EXP-005 실제 출력 생성
- 30 episode 수동 CoC-to-STL gold set
- quantitative STL monitor
- 기존 UPPAAL 결과와 교차 비교

중단 조건: 실제 CoC가 trigger/termination을 거의 포함하지 않아 계약 coverage가 30% 미만이면, CoC 생성 prompt/structured head 연구로 문제를 재정의한다.

### Phase 2: 6주, benchmark와 calibration

- 100--300 episode 확장
- typed grammar와 grounding
- deadline/threshold calibration
- 자연 발생 및 mutation 오류 taxonomy

### Phase 3: 8주, 학습

- SFT/preference/robustness 세 방식 구현
- unseen event composition 실험
- bootstrap confidence interval과 통계 검정

### Phase 4: 8주, 폐루프

- CBF-QP 및 robust margin
- CARLA factorial scenarios
- HJ oracle 소규모 비교
- end-to-end ablation

### Phase 5: 4주, 제출 준비

- claim audit와 reproducibility package
- benchmark/data license 범위 확인
- failure case와 negative result 포함
- 익명화된 코드, schema, formula, simulator config 공개 준비

## 12. 위험과 대응

| 위험 | 대응 |
|---|---|
| CoC가 근거 없는 설명을 생성 | grounding 실패 시 abstain, perception oracle 실험 병행 |
| 시간 임계값이 임의적 | 동역학/latency/data calibration 및 sensitivity curve |
| STL 만족이 실제 안전과 불일치 | CBF 및 closed-loop physical metric 병행 |
| CBF가 지나치게 보수적 | intervention/deviation/comfort를 함께 최적화하고 보고 |
| CBF infeasibility | feasibility rate 공개, backup controller와 robust design 비교 |
| 실제 모델 오류가 희소 | adversarial composition과 mutation을 분리 보고, 자연 오류를 과장하지 않음 |
| full fine-tuning 비용 과다 | trajectory head/LoRA부터 시작하고 동일 compute budget 비교 |
| 데이터 라이선스 제약 | 원본 재배포 없이 ID, 파생 formula, 실행 script 중심 공개 |

## 13. 주장 경계

### 주장할 수 있는 것

- CoC 유래 계약이 지정 trajectory에서 만족되는지와 위반 여유
- 명시한 차량 모델ㆍ불확실성ㆍCBF feasibility 조건 아래 filtered system의 안전 불변성
- 검증 신호를 학습에 사용했을 때 실험 분포와 held-out composition에서의 개선
- 충돌 전에 나타나는 reasoning-action protocol 위반의 탐지

### 주장할 수 없는 것

- 생성 CoC가 현실의 참된 인과 설명이라는 보증
- 모든 도로와 모든 perception 오류에 대한 안전
- 원본 10B E2E 신경망 전체의 형식 검증
- 실제 차량 인증 또는 무조건적 무충돌 보증

## 14. 관련 문서

- 방법 선택 서베이: `METHOD_SELECTION_SURVEY.md`
- UPPAAL 우선 대안: `UPPAAL_FIRST_OPTION.md`
- 다중 backend 대안: `MULTI_BACKEND_OPTIONS.md`
- 실제 Alpamayo inference runbook: `../../alpamayo-experiments/ALP-EXP-005-REMOTE-RUNBOOK.md`
- 원격 실행 prompt: `../../alpamayo-experiments/ALP-EXP-005-REMOTE-AGENT-PROMPT.md`

