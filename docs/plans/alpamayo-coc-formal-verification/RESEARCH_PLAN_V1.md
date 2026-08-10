# CoC 계약 기반 E2E 자율주행의 학습 및 폐루프 안전성 연구 계획 v1

- 버전: v1
- 기준일: 2026-08-02
- 검증 대상: 실제 모델이 생성한 Chain-of-Causation(CoC) reasoning trace와 trajectory의 의미적ㆍ시간적ㆍ물리적 일관성
- 1차 정형기법: Signal Temporal Logic(STL), Control Barrier Function(CBF)
- 목표: NeurIPS급 기계학습 연구
- 상세 선택 근거: `METHOD_SELECTION_SURVEY.md`
- 이전 UPPAAL 우선안: `UPPAAL_FIRST_OPTION.md`

## 1. 연구 목적과 범위

E2E 자율주행 모델은 영상과 차량 상태로부터 reasoning trace와 미래 trajectory를 함께 생성할 수 있다. CoC reasoning trace는 원인, 판단, 행동, 예상 결과를 명시하지만, 자연어 설명이 그럴듯하다는 사실만으로 그것이 장면에 근거하거나 trajectory가 안전하다고 결론 내릴 수는 없다.

본 연구는 실제 모델이 외부로 생성한 CoC reasoning trace를 다음과 같이 사용한다.

1. trace의 cause, judgment, action, effect, trigger, deadline, hold, release 의미를 구조적으로 분석한다.
2. 각 의미 요소를 원문 CoC span, 영상 객체ㆍtrack, map/scene predicate 및 차량 상태에 grounding한다.
3. 검증 가능한 Grounded Contract IR과 STL 시간계약으로 변환한다.
4. CoC가 주장한 행동과 실제 생성 trajectory 및 폐루프 상태가 일치하는지 검사한다.
5. STL 위반과 CBF 개입을 CoC span과 trajectory segment까지 역추적한다.
6. 이렇게 얻은 반례와 quantitative robustness를 post-training에 재사용한다.

```text
multi-camera + ego state
          |
          v
 E2E model: CoC reasoning trace + trajectory
          |
          v
 span-level CoC trace analysis
          |
          v
 typed + grounded Contract IR
          |
          +--> calibrated STL monitor --> robustness/counterexample
          |
          +--> CBF-QP safety filter --> safe control/intervention
                                      |
                                      v
                    hard-negative / preference / fine-tuning
```

연구의 핵심 주장은 “CoC가 안전을 증명한다”가 아니다. CoC는 검증 가능한 시간계약을 생성하는 중간 인터페이스이며, CBF는 명시적인 동역학ㆍ상태 추정ㆍfeasibility 가정 아래 실행 단계의 물리 안전을 보완한다.

### 1.1 포함 범위

- 외부로 생성된 CoC reasoning trace의 구조적ㆍ의미적 분석
- CoC 원문 span과 scene evidence의 grounding
- reasoning-action 및 reasoning-trajectory 일관성 검사
- CoC-to-STL 변환과 quantitative monitoring
- STL 반례와 CBF 개입을 이용한 verification-guided learning
- open-loop 및 closed-loop 안전ㆍ성능 평가

### 1.2 제외 범위

- 모델 내부의 비공개 hidden reasoning 복원
- 신경망 회로 수준의 mechanistic interpretability
- 생성 CoC가 모델 내부 의사결정 과정을 충실히 반영한다는 보증
- 생성 CoC가 현실의 참된 인과 설명이라는 보증
- 10B E2E 신경망 전체에 대한 완전 형식 검증

## 2. 중심 가설과 연구 질문

> 영상에 근거한 CoC reasoning trace를 정량적 STL 계약으로 변환하고, 위반 robustness와 CBF 개입으로 생성한 반례를 학습에 재사용하면, trajectory-only 또는 reasoning-only 학습보다 연속 사건의 계약 만족률과 폐루프 안전성을 향상시키면서 nominal driving quality의 손실을 제한할 수 있다.

### 2.1 하위 가설

- H1: CoC는 trajectory만으로 관측하기 어려운 trigger, deadline, hold, release 의미를 복원한다.
- H2: span-level grounding은 자유 형식 또는 ungrounded CoC-to-STL 변환보다 false formula를 줄인다.
- H3: quantitative STL robustness는 binary label보다 경계 사례 채굴과 fine-tuning에 유용하다.
- H4: STL 학습과 CBF 실행 필터를 결합하면 어느 하나만 사용할 때보다 의미 일관성과 물리 안전을 함께 개선한다.
- H5: 학습 후 CBF 개입률과 수정량이 감소하면 nominal policy가 unsafe manifold를 일부 학습했음을 보일 수 있다.

### 2.2 연구 질문

- RQ1 Trace structure: 실제 생성 CoC 중 cause, judgment, action, effect, trigger, hold, release를 신뢰성 있게 추출할 수 있는 비율은 얼마인가?
- RQ2 Grounding: 추출한 span을 객체 track과 observable predicate에 얼마나 정확하게 grounding할 수 있는가?
- RQ3 Contract generation: 실제 생성 CoC의 몇 퍼센트를 typed, grounded STL로 변환할 수 있으며 전문가 의미 동등성은 어느 정도인가?
- RQ4 Error detection: trajectory metric, collision metric, LLM judge 및 UPPAAL이 놓치는 reasoning-action protocol 오류를 STL robustness가 검출하는가?
- RQ5 Uncertainty: `D_brake`, `TTC_min`, clearance duration을 데이터ㆍ차량ㆍ센서 불확실성으로 보정하면 false alarm과 miss가 어떻게 변하는가?
- RQ6 Learning: counterexample-guided fine-tuning이 unseen event composition의 계약 만족도와 폐루프 안전성을 개선하는가?
- RQ7 Runtime safety: CBF가 collision과 road departure를 얼마나 줄이며 개입률, trajectory deviation, infeasibility 비용은 얼마인가?
- RQ8 Disagreement: STL과 CBF 판정의 불일치가 계약 누락, grounding 오류, 동역학 불일치 또는 policy 결함을 어떻게 드러내는가?

## 3. 분석 단위와 데이터 모델

### 3.1 모델 출력

시점 `t`의 모델 출력은 다음과 같다.

```text
y_t = (r_t, tau_t)
r_t: externally generated CoC reasoning trace
tau_t = {(x_hat, y_hat, yaw_hat, v_hat)_t...t+H}: planned trajectory
```

환경 관측과 추적 상태는 `o_t`, 실제 또는 시뮬레이션 차량 상태는 `x_t`, nominal control은 `u_nom,t`로 둔다. 같은 clip의 연속 inference step과 여러 seed를 하나의 episode family로 관리한다.

### 3.2 Span-level CoC trace annotation

CoC trace 분석을 재현 가능하게 하기 위해 원문 span을 보존하는 `CoCTraceAnnotation`을 둔다.

```yaml
trace_id: clip17_seed3_step23
model_revision: pinned
prompt_revision: pinned
decoder:
  seed: 3
  temperature: 0.2
spans:
  - span_id: s1
    text: "A pedestrian is entering the conflict zone"
    role: CAUSE
    predicate: pedestrian_in_conflict_zone
    grounding: track_104
    observable: true
    confidence: 0.91
  - span_id: s2
    text: "I should decelerate and keep yielding"
    role: ACTION
    action: DECELERATE_AND_HOLD
  - span_id: s3
    text: "resume after the pedestrian has cleared"
    role: RELEASE
    predicate: pedestrian_cleared_stably
relations:
  - [s1, CAUSES, s2]
  - [s3, RELEASES, s2]
```

필수 span role은 다음과 같다.

- `CAUSE`: 행동 의무를 촉발한 원인
- `JUDGMENT`: 위험ㆍ우선권ㆍ진행 가능성에 대한 판단
- `ACTION`: 계획하거나 지시한 행동
- `EFFECT`: 행동으로 예상한 결과
- `TRIGGER`: 의무의 시작 조건
- `DEADLINE`: 허용 응답 시간
- `HOLD`: 행동을 유지해야 하는 조건
- `RELEASE`: 의무 종료 또는 다음 행동 허용 조건
- `UNCERTAINTY`: 불확실성 또는 조건부 표현

명시되지 않은 요소를 추론으로 보완한 경우 `source=INFERRED`로 표시하고, 모델이 실제로 생성한 내용과 분리한다.

### 3.3 Grounded Contract IR

CoC에서 바로 공식을 만들지 않고 trace annotation을 Grounded Contract IR로 컴파일한다.

```yaml
event_id: e17
source:
  trace_id: clip17_seed3_step23
  cause_span: s1
  action_span: s2
  release_span: s3
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

- span 및 relation type validity
- object/track grounding
- temporal interval validity
- trigger와 termination의 관측 가능성
- repeated command의 preserve, update, reset semantics
- reasoning action과 trajectory action의 방향 일치
- provenance completeness
- 물리적 실행 가능성

변환할 수 없는 trace는 억지로 공식화하지 않고 `SPECIFICATION_INCOMPLETE`, `UNGROUNDED`, `AMBIGUOUS` 또는 `PHYSICALLY_INFEASIBLE`로 판정한다.

## 4. 형식 계층

### 4.1 STL 계약과 robustness

대표 formula template은 다음과 같다.

```text
Response:              G(trigger -> F_[l,u] response)
Hold:                  G(hazard -> safe_mode)
Release:               G(next_action -> cleared_stably)
No premature recovery: G(hazard -> !resume)
Physical margin:       G(TTC >= TTC_min and d_front >= d_safe(v, latency, a_brake))
```

각 공식에 quantitative robustness `rho`를 계산한다. episode 평가는 satisfaction rate, mean robustness, minimum robustness 및 CVaR 또는 하위 분위수를 함께 사용한다. 최초 음의 robustness 시점, 위반 predicate, 관련 CoC span, grounding 객체 및 trajectory segment를 하나의 counterexample record로 저장한다.

### 4.2 Contract calibration

deadline과 물리 threshold를 임의의 단일 상수로 고정하지 않는다. 다음 자료에서 interval을 보정한다.

- 차량 제동 성능과 actuator delay
- ego 및 상대 속도와 거리
- perception 및 inference latency
- expert demonstration의 response distribution
- 법규 또는 검증된 domain rule

데이터 기반 threshold에는 train/calibration/test 분리를 적용하고 conformal coverage와 sensitivity curve를 보고한다. 물리적으로 불가능한 deadline은 모델 오류가 아니라 contract 오류로 분리한다.

### 4.3 CBF 안전 필터

저차원 차량 모델에서 collision, road boundary 및 actuator envelope에 barrier `h_i(x)`를 정의한다.

```text
u_safe = argmin_u ||u - u_nom||^2_Q + lambda * ||slack||

subject to
  L_f h_i(x) + L_g h_i(x) u + alpha_i(h_i(x)) >= -slack_i
  u_min <= u <= u_max
```

hard safety constraint에는 원칙적으로 slack을 허용하지 않는다. infeasible 상태는 숨기지 않고 별도 지표로 보고하며, perception/state uncertainty는 robust margin 또는 bounded disturbance로 포함한다.

### 4.4 STL-CBF disagreement taxonomy

STL 판정과 CBF 개입을 다음 네 범주로 나누어 분석한다.

| STL | CBF | 1차 해석 가설 | 필수 진단 |
|---|---|---|---|
| PASS | 미개입 | 의미ㆍ물리 계층이 모두 nominally consistent | 경계 robustness와 near-miss 확인 |
| PASS | 개입 | 계약의 물리 제약 누락, threshold 오류 또는 동역학 불일치 가능성 | 개입 barrier, control delta, 관련 CoC span |
| FAIL | 미개입 | 즉시 물리 위험은 없지만 response/hold/release protocol 위반 가능성 | 위반 formula와 장기 결과 |
| FAIL | 개입 | 의미적 판단과 물리적 실행의 결합 실패 가능성 | 최초 위반과 최초 개입의 시간 순서 |

표의 해석은 자동 결론이 아니라 진단 가설이다. 전문가 adjudication과 controlled intervention으로 원인을 구분한다.

## 5. 핵심 방법

### M1. Span-aware Grounded CoC-to-STL compiler

1. CoC 원문에서 span과 cause-action-effect-temporal relation을 추출한다.
2. cause와 effect 명사를 tracker 및 map/scene predicate에 grounding한다.
3. 허용된 typed grammar와 formula template만 생성한다.
4. formula를 trajectory/state signal에 실행해 즉시 검증한다.
5. 생성 공식에서 원문 span까지 양방향 provenance를 보존한다.
6. 전문가는 원문, 장면 근거, 공식 및 실행 반례를 함께 검토한다.

자유 형식 LLM 번역, grammar-constrained 번역, ungrounded 변환 및 span-aware grounded 변환을 비교한다.

### M2. Counterexample generation and localization

실제 출력과 다음 controlled mutation을 검사한다.

- response delay 삽입
- premature resume
- hold 삭제
- cause 또는 track 교체
- repeated command의 preserve/reset 변경
- trajectory와 reasoning action의 부호 반전
- sensor clearance delay
- cut-in 또는 pedestrian persistence 연장
- CoC span 삭제, 교환 또는 temporal cue 변형

자연 발생 오류와 합성 mutation 결과를 분리하여 보고한다.

### M3. Verification-guided learning

다음 학습 방식을 동일한 base model, 데이터 예산 및 가능한 한 동일한 compute budget에서 비교한다.

1. trajectory-only SFT
2. CoC + trajectory SFT
3. random hard-negative training
4. STL-weighted SFT
5. STL preference optimization
6. STL robustness regularization

```text
L = L_traj + beta L_reason_action + gamma L_STL
```

CoC 텍스트 자체를 정답으로 과신하지 않는다. grounding 실패, 계약 모호성, span provenance 누락 또는 물리 infeasibility가 있는 표본은 positive SFT에서 제외한다.

### M4. Runtime safety filtering

fine-tuned policy의 nominal control을 CBF-QP로 필터링한다. 반복 개입 구간, 큰 수정량 및 infeasible QP를 각각 policy 결함, semantic-physical mismatch 및 barrier/상태 가정의 한계 후보로 기록한다. nominal policy와 filtered system의 성능을 분리해 보고한다.

## 6. 실험 설계

### E0. 실제 모델 출력 확보

`ALP-EXP-005`를 실행하여 동일 clip의 여러 seed와 연속 inference step에서 실제 생성 CoC와 trajectory를 확보한다. model/dataset/prompt revision, seed, decoder setting 및 inference step을 기록한다. annotation 기반 기존 결과와 실제 모델 출력을 섞지 않는다.

### E1. Phase-1 trace feasibility와 gold set

30 episode를 이중 annotation하여 span-level CoC gold set과 CoC-to-STL gold set을 함께 만든다.

평가 항목:

- span role precision/recall/F1
- relation extraction F1
- trace-level trigger/hold/release coverage
- inter-annotator agreement와 adjudication rate
- predicate grounding precision/recall
- temporal bound error
- human semantic equivalence
- abstention accuracy

중단 또는 재정의 조건:

- 실제 CoC의 contract coverage가 30% 미만이면 prompt 또는 structured output head 연구로 재정의한다.
- span agreement가 낮으면 annotation ontology를 축소하고 judgment와 inferred field를 분리한다.
- grounding이 주 병목이면 perception oracle과 trajectory/scene-state contract baseline을 병행한다.

### E2. CoC-to-STL benchmark

- 초기 100--300 episode
- 확대 시 사건 유형을 균형화한 1,000+ episode
- single-event와 composed multi-event split 분리
- scene-disjoint 및 geography/weather-disjoint test
- 동일 clip의 seed와 augmentation은 동일 split에 배치

비교군:

- trajectory-only STL
- annotation-derived pseudo-CoC
- free-form CoC-to-STL
- grammar-constrained CoC-to-STL
- ungrounded CoC-to-STL
- span-aware grounded CoC-to-STL

핵심 지표:

- exact/template validity
- false-formula rate
- span extraction 및 relation F1
- grounding precision/recall
- temporal bound error
- semantic equivalence
- coverage-risk curve와 abstention accuracy

### E3. 오류 검출 benchmark

정상 출력, 자연 발생 오류 및 controlled mutation을 섞되 evaluator가 label을 보지 않게 한다.

비교군:

- ADE/FDE
- collision/TTC metric
- LLM-as-judge
- rule-based event checker
- UPPAAL episode checker
- binary STL monitor
- quantitative STL monitor

측정:

- 오류 유형별 AUROC/AUPRC
- first-detection time
- false alarm per driving hour
- minimum perturbation to detection
- counterexample localization IoU
- CoC span localization precision/recall
- natural-error와 mutation 성능의 차이

### E4. Open-loop fine-tuning

동일 base model과 데이터 예산에서 여섯 학습 방식을 비교한다.

측정:

- ADE/FDE 및 trajectory feasibility
- CoC-action consistency
- span 및 grounding 품질의 학습 전후 변화
- STL satisfaction rate
- mean/min/CVaR robustness
- unseen composition generalization
- calibration 및 abstention 성능

### E5. Closed-loop simulation

CARLA 또는 동등한 simulator에서 다음 사건을 구성한다.

- pedestrian enter-persist-clear
- lead brake-stop-recover
- cut-in followed by signal change
- occlusion with delayed clearance
- repeated reasoning/command update
- simultaneous longitudinal and lateral obligation

속도, 마찰, actuator lag, perception latency/noise, actor persistence, weather, visibility 및 사건 순서ㆍ중첩을 factorial하게 변화시킨다.

### E6. CBF 및 end-to-end ablation

CBF 비교군:

- no filter
- heuristic emergency brake
- CBF with nominal dynamics
- robust CBF with bounded uncertainty
- 저차원 HJ reachability oracle

결합 비교:

| STL 학습 | CBF 필터 | 목적 |
|---|---|---|
| 없음 | 없음 | base policy |
| 있음 | 없음 | verification-guided learning 효과 |
| 없음 | 있음 | runtime filter 효과 |
| 있음 | 있음 | 결합 효과와 필터 의존도 감소 |

측정:

- collision, road departure 및 near-miss/TTC
- intervention rate/duration과 control deviation
- QP infeasibility
- task completion과 comfort
- STL-CBF 네 범주별 빈도와 원인 taxonomy
- 학습 전후 CBF 개입률 및 수정량 변화

## 7. 데이터 분할과 누수 방지

- 같은 원본 clip의 seed, augmentation 및 연속 inference step은 하나의 split에만 둔다.
- 동일 actor track 또는 연속 frame이 train/test에 교차하지 않게 한다.
- contract calibration에는 test trajectory를 사용하지 않는다.
- mutation 규칙 일부와 event composition 일부를 test에서 hold out한다.
- annotation-derived pseudo-CoC와 actual CoC를 별도 field와 결과 표로 관리한다.
- inferred span과 model-explicit span을 구분한다.
- model/dataset/prompt revision, seed 및 decoder setting을 기록한다.

## 8. 성공 기준

수치는 pilot과 power analysis 후 확정하되 1차 게이트는 다음과 같다.

- 30-episode pilot에서 trace-level contract coverage 30% 이상
- CoC-to-STL human semantic equivalence 85% 이상과 오류 유형별 confidence interval
- span role 및 relation extraction이 사전 정의한 전문가 agreement 대비 실용 가능한 수준
- grammar/grounding 없는 변환보다 false-formula rate의 유의한 감소
- span-aware grounded 변환이 trajectory-only 또는 ungrounded baseline보다 reasoning-action 오류 검출에서 개선
- unseen composed event에서 minimum/CVaR STL robustness 개선
- no-filter 대비 collision/road departure 감소
- 학습 후 CBF intervention rate와 평균 수정량 감소
- nominal ADE/FDE, comfort 및 completion의 허용 가능한 trade-off
- 실제 출력에서 최소 하나 이상의 자연 발생 semantic-physical disagreement 발견

합성 mutation만 검출하고 실제 출력 오류를 찾지 못하면 feasibility 결과로 한정한다. 최종 수치 기준과 허용 trade-off는 pilot 이전에 고정하지 않고, calibration set과 power analysis 이후 test 평가 전에 preregister한다.

## 9. 예상 기여

### C1. Span-grounded CoC-to-Contract benchmark

실제 reasoning trace, 원문 span, grounded predicate, STL formula, trajectory 및 counterexample를 연결한 benchmark와 annotation protocol.

### C2. Grounded and calibrated compiler

자연어 형식 변환을 넘어 scene evidence, span provenance와 차량 가능성으로 계약을 검증하는 compiler.

### C3. Verification-guided post-training

정량적 robustness, 최소 반례 및 reasoning-action consistency를 E2E trajectory/reasoning 학습에 연결하는 방법.

### C4. Semantic-physical dual safety

STL 의미계약과 CBF 실행 불변성을 결합하고 네 범주의 disagreement를 데이터, 계약 및 모델 실패 신호로 사용하는 방법.

### C5. Episode-level evaluation

단일 프레임 또는 최종 collision 여부가 아니라 연속 사건에서 의무의 생성ㆍ유지ㆍ종료ㆍ선점과 관련 reasoning span을 함께 평가하는 protocol.

## 10. 실행 순서

### Phase 1: 4주, trace 측정 가능성

- ALP-EXP-005 실제 출력 생성
- annotation ontology와 span schema 동결
- 30 episode 이중 annotation 및 adjudication
- span-level CoC와 CoC-to-STL gold set 작성
- quantitative STL monitor 구현
- 기존 UPPAAL 결과와 교차 비교
- coverage 30% 및 agreement gate 판정

### Phase 2: 6주, benchmark와 calibration

- 100--300 episode 확장
- span-aware typed grammar와 grounding
- deadline/threshold calibration
- 자연 발생 및 mutation 오류 taxonomy
- STL-CBF disagreement annotation protocol 확정

### Phase 3: 8주, 학습

- SFT, preference 및 robustness 세 방식 구현
- unseen event composition 실험
- bootstrap confidence interval과 통계 검정
- 학습 전후 trace 품질과 CBF 개입 예측

### Phase 4: 8주, 폐루프

- CBF-QP 및 robust margin
- CARLA factorial scenarios
- HJ oracle 소규모 비교
- end-to-end 및 disagreement ablation

### Phase 5: 4주, 제출 준비

- claim audit와 reproducibility package
- benchmark/data license 범위 확인
- failure case와 negative result 포함
- 익명화된 schema, formula, code 및 simulator config 공개 준비

## 11. 위험과 대응

| 위험 | 대응 |
|---|---|
| CoC가 근거 없는 설명을 생성 | grounding 실패 시 abstain, perception oracle 병행 |
| trace role이 모호함 | explicit/inferred 분리, ontology 축소, 이중 annotation |
| span annotation 비용이 큼 | active sampling과 disagreement 중심 adjudication |
| 시간 임계값이 임의적 | 동역학/latency/data calibration과 sensitivity curve |
| STL 만족이 실제 안전과 불일치 | CBF와 closed-loop physical metric 병행 |
| CBF가 지나치게 보수적 | intervention/deviation/comfort 동시 보고 |
| CBF infeasibility | feasibility 공개, backup controller와 robust design 비교 |
| 실제 모델 오류가 희소 | 자연 오류와 mutation을 분리하고 자연 오류를 과장하지 않음 |
| full fine-tuning 비용 과다 | trajectory head 또는 LoRA부터 시작하고 compute budget 통제 |
| 데이터 라이선스 제약 | 원본 재배포 없이 ID, span offset, 파생 formula와 script 중심 공개 |

## 12. 주장 경계

### 주장할 수 있는 것

- 외부로 생성된 CoC trace에서 지정 의미 role을 추출하고 장면에 grounding하는 성능
- CoC 유래 계약이 지정 trajectory에서 만족되는지와 위반 여유
- 위반을 관련 CoC span, 객체 및 trajectory 구간으로 국소화하는 성능
- 명시한 차량 모델ㆍ불확실성ㆍCBF feasibility 조건 아래 filtered system의 안전 불변성
- 검증 신호를 학습에 사용했을 때 held-out composition에서의 개선
- 충돌 전에 나타나는 reasoning-action protocol 위반의 탐지

### 주장할 수 없는 것

- 생성 CoC가 현실의 참된 인과 설명이라는 보증
- 생성 CoC가 모델 내부 계산 또는 의사결정을 충실히 노출한다는 보증
- hidden chain-of-thought의 복원 또는 검증
- 모든 도로와 모든 perception 오류에 대한 안전
- 원본 10B E2E 신경망 전체의 형식 검증
- 실제 차량 인증 또는 무조건적 무충돌 보증

## 13. NeurIPS 제출 판단

다음만으로는 main-track 주장이 약하다.

- 소수 scene의 수동 모델링
- 합성 mutation 검출만 성공
- CoC를 자연어 설명으로만 평가
- safety filter 적용 후 collision 감소만 보고

경쟁력 있는 제출에는 다음이 함께 필요하다.

- 재현 가능한 실제 모델 출력 benchmark
- span-aware grounded CoC-to-STL 변환의 algorithmic novelty
- 불확실성을 포함한 calibrated contract
- counterexample-guided fine-tuning의 일반화 이득
- 폐루프 대규모 평가와 안전/성능 trade-off
- STL-CBF disagreement에서 발견한 실제 failure taxonomy
- temporal-logic learning, safe imitation 및 safety filter 대비 강한 baseline

논문 제목 후보:

> **From Causal Reasoning to Certified Control: Grounded Temporal Contracts for End-to-End Driving**

“certified E2E model”이라는 표현은 사용하지 않는다. certification 대상은 명시된 contract monitor와 CBF-filtered execution이며 전체 VLA가 아니다.

## 14. 관련 문서

- 방법 선택 서베이: `METHOD_SELECTION_SURVEY.md`
- 기존 연구 계획: `../../../archive/research/RESEARCH_PLAN_PRE_V1.md`
- UPPAAL 우선 대안: `UPPAAL_FIRST_OPTION.md`
- 다중 backend 대안: `MULTI_BACKEND_OPTIONS.md`
- 실제 Alpamayo inference runbook: `../../../experiments/alpamayo/ALP-EXP-005-REMOTE-RUNBOOK.md`
- 원격 실행 prompt: `../../../experiments/alpamayo/ALP-EXP-005-REMOTE-AGENT-PROMPT.md`
