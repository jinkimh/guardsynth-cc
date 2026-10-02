# Safety-Constrained CoC 국제 저널 확장 계획

- 작성일: 2026-08-04
- 실행 시점: 국내 저널 원고 완료 및 투고 이후
- 기반 원고: `WRITING_PLAN.md`
- 목표: 합성 feasibility 연구를 실행 가능한 trajectory와 폐루프 안전ㆍ진행성 평가를 포함한 국제 저널 논문으로 확장

## 1. 실행 원칙

이 계획은 국내 저널 논문을 중단하거나 범위를 계속 확장하기 위한 계획이 아니다. 국내 논문에서는 현재 확보한 정적ㆍ시간적 합성 결과와 추가 최소 maneuver를 사용해 Safety-Constrained CoC의 학습 가능성을 보고한다. 국내 원고가 완료된 뒤 실험 범위와 주장을 다음 단계로 확장한다.

```text
국내 저널
  통제된 합성 환경에서 Safety-Constrained CoC의 feasibility 입증
        ↓ 투고 완료
국제 저널 확장
  실행 가능한 trajectory + 폐루프 simulator + 실제 데이터 case study
```

국제 저널 확장의 핵심은 원고를 영어로 번역하는 것이 아니라 증거 수준을 높이는 것이다.

## 2. 목표 저널과 적합성

### 2.1 우선 목표: IEEE Transactions on Intelligent Vehicles

T-IV는 automated vehicles, vehicle safety, pedestrian protection, collision avoidance 및 vehicle control을 직접 다룬다. 본 연구가 연속 trajectory와 폐루프 결과를 포함하면 가장 직접적인 목표가 된다.

- 공식 scope: https://ieee-itss.org/pub/t-iv/

### 2.2 상향 목표: IEEE Transactions on Intelligent Transportation Systems

T-ITS는 AI, formal methods, simulation, control과 safety methods를 포함하지만, 실제 transportation system에 대한 이익을 요구한다. 단일 ego candidate-selection보다 주변 차량ㆍ보행자 상호작용, 통행시간, 불필요한 정지 및 운영 효율까지 보여야 한다.

- 공식 scope: https://ieee-itss.org/pub/t-its/

### 2.3 현실적 대안: IEEE Open Journal of Intelligent Transportation Systems

AI, control, simulation, decision systems, reliability 및 quality assurance를 폭넓게 다룬다. 공개 재현 패키지와 충분한 폐루프 평가를 갖추면 적합한 대안이다.

- 공식 scope: https://ieee-itss.org/pub/oj-its/

## 3. 국제 저널용 중심 주장

국내 논문의 주장은 다음 수준이다.

> 합성 VLM 후보 선택에서 자연어 안전 제약을 포함한 CoC가 명시된 제약 준수와 목표 완료를 개선한다.

국제 저널에서는 다음까지 확장한다.

> Safety-Constrained CoC와 Guard-aware 학습은 다양한 maneuver 및 미학습 계약에서 제약 위반과 폐루프 위험을 줄이면서 route completion, progress와 승차감을 유지한다.

실제 차량 안전 보장이나 완전한 정형 안전 증명은 여전히 주장하지 않는다.

## 4. 현재 증거와 국제 저널 간극

| 항목 | 현재 상태 | 국제 저널에 필요한 상태 |
|---|---|---|
| 출력 | A/B/C/D 후보 선택 | 연속 waypoint 또는 실행 가능한 candidate trajectory |
| 환경 | 2D micro-world, storyboard | Parameterized closed-loop simulator |
| Maneuver | 정적 제약, STOP–HOLD–RELEASE–GO | 최소 4개 maneuver family |
| 안전 지표 | Guard violation, safe-goal | Collision, TTC, clearance, off-road, STL robustness |
| 진행성 | progress/deadlock proxy | Route completion, traversal time, unnecessary stop |
| 승차감 | 제한적 | Acceleration, lateral/longitudinal jerk |
| 일반화 | paraphrase, 일부 unseen value | 연속 threshold, composition, phase, scenario OOD |
| 모델 | Qwen3-VL-2B 중심 | 최소 2개 공개 VLM family |
| 실제 모델 | Alpamayo-R1 zero-shot 진단 | 실제 장면 case study 또는 제한적 post-training |
| 재현성 | 코드와 합성 결과 | 공개 scenario, configs, adapter, evaluator 패키지 |

가장 큰 간극은 candidate-selection과 폐루프 주행 사이의 차이다.

## 5. 국제 저널용 시스템 구조

처음부터 새로운 E2E trajectory generator를 만들지 않고, 기존 candidate-selection 연구를 실행 가능한 planning architecture로 확장한다.

```text
sensor observation + route goal
              |
              v
base planner: K개 실행 가능한 trajectory 생성
              |
              v
VLM + Safety-Constrained CoC: candidate ranking
              |
              v
optional deterministic Guard verifier
              |
              v
selected trajectory closed-loop execution
              |
              v
independent safety / progress / comfort evaluation
```

이 구조는 현재 연구의 핵심인 admissible-set selection을 유지하면서 vehicle dynamics와 폐루프 결과를 추가한다.

## 6. 필수 Maneuver suite

### M1. CRUISE → STOP

Guard:

- 정지선 이전 정지
- conflict zone 진입 금지
- 최대 감속도 및 jerk
- 관측 불확실 시 hold

위반 후보:

- 늦은 제동과 정지선 초과
- 무정지 통과
- jerk 상한을 넘는 급제동
- 불필요한 조기 정지

### M2. STOP → HOLD → RELEASE → GO

현재 benchmark를 다음처럼 확장한다.

- 연속적으로 샘플링한 clear duration
- occlusion과 occupancy uncertainty
- 다음 planning cycle의 re-hold
- 실제 acceleration profile

### M3. LANE CHANGE → COMPLETE/ABORT

Guard:

- 최소 전후방 gap에서만 시작
- 변경 중 측면거리 invariant
- gap이 닫히면 abort 또는 원래 차선 복귀
- lateral acceleration과 steering-rate 상한

### M4. YIELD → GAP ACCEPTANCE → ENTER

Guard:

- conflict zone 점유 중 진입 금지
- TTC 하한
- 안전 gap 확보 후 진입
- 불확실하면 hold 또는 제한된 creep

## 7. Scenario 생성 전략

실제 CoC 장면 수백 개를 수작업으로 동일하게 재현하지 않는다. 네 개 maneuver template을 만들고 위치, 속도, gap, 보행자 이동, occlusion, friction과 sensor uncertainty를 parameterize한다.

권장 최소 규모:

```text
4 maneuver families
× 75 parameter configurations
× 3 random seeds
= 조건당 900 closed-loop episodes
```

### Simulator 선택

- MetaDrive: 빠른 parameterized scenario 구성과 대규모 state-based 폐루프 실험에 유리
- CARLA: camera 기반 VLM 입력과 보다 현실적인 visual scenario에 유리

현실적인 순서는 MetaDrive에서 planning/Guard mechanism을 검증한 뒤, 일부 핵심 장면을 CARLA에서 영상 기반으로 재현하는 것이다.

## 8. 비교 조건

| ID | 조건 | 목적 |
|---|---|---|
| B0 | Trajectory-only | CoC가 없는 하한 baseline |
| B1 | Requirement CoC | 행동 요구사항 중심 baseline |
| B2 | Safety-Constrained CoC | 제안 방법 |
| B3 | Shuffled/irrelevant constraint | 의미 대응 negative control |
| B4 | Hard-negative training | 자연어 제약 없이 위반 trajectory만 학습 |
| B5 | Deterministic verifier | 실행 가능한 Guard upper bound |
| B6 | Safety-Constrained CoC + verifier | 학습과 runtime assurance hybrid |

Hard-negative baseline은 제안 방법이 단순히 negative trajectory를 본 효과인지, 제약 의미를 배운 효과인지 구분한다.

## 9. Guard-aware 학습 방법

일반적인 target-token SFT를 다음 목적함수로 확장한다.

```text
L = L_trajectory
  + λ_pair L_pair
  + λ_violation L_violation
  + λ_goal L_goal
  + λ_comfort L_comfort
```

- `L_trajectory`: target waypoint 또는 candidate ranking
- `L_pair`: 동일 장면의 permissive/restrictive 계약 전환
- `L_violation`: Guard robustness가 음수가 되는 trajectory에 대한 벌점
- `L_goal`: always-stop과 route failure 방지
- `L_comfort`: acceleration 및 jerk 제한

### 학습 ablation

- SFT only
- SFT + pairwise
- SFT + violation
- SFT + pairwise + violation
- full objective

## 10. 일반화 설계

### 10.1 연속 threshold

```text
max_speed        ∈ [2, 8] m/s
min_clearance    ∈ [0.5, 4.0] m
clear_duration   ∈ [0.2, 2.5] s
min_TTC          ∈ [1.0, 5.0] s
lane_change_gap  ∈ [5, 30] m
```

### 10.2 Split

- in-distribution
- interpolation
- extrapolation
- unseen Guard conjunction
- unseen phase order
- unseen paraphrase
- incomplete or conflicting Guard
- perception uncertainty

## 11. 평가 지표

### 11.1 안전과 계약

- Collision rate
- Minimum TTC
- TTC threshold 이하 노출시간
- Minimum vehicle/pedestrian clearance
- Stop-line overshoot
- Off-road 및 lane-boundary violation
- Guard/STL robustness
- Runtime verifier intervention rate

### 11.2 목표와 효율

- Route completion
- Scenario success rate
- Progress
- Traversal time
- Unnecessary stop duration
- Deadlock / always-stop rate
- False rejection of admissible trajectory

### 11.3 승차감

- Longitudinal/lateral acceleration
- Longitudinal/lateral jerk
- Steering-rate
- Nominal trajectory deviation

## 12. 실제 데이터 연결

CASCADE/PhysicalAI 전체를 다시 label하지 않는다. 대표 실제 장면 50–100개를 선택해 다음 절차를 적용한다.

1. 실제 또는 R1 trajectory 주변에 kinematic perturbation 후보 생성
2. 속도, stop line, clearance와 entry time을 변화
3. 사람은 장면 grounding과 Guard applicability만 검토
4. 독립 verifier가 후보의 제약 준수 여부 계산
5. 합성 환경에서 학습한 ranking이 실제 장면에 전이되는지 평가

Restricted 데이터 결과는 case study로 사용하고, 논문의 주요 결과는 공개 가능한 환경에서 재현 가능하게 구성한다.

## 13. 모델과 통계

### 모델

- Qwen3-VL-2B-Instruct
- 다른 공개 소형 VLM family 1개 이상
- Alpamayo-R1: zero-shot case study, 가능하면 adapter/post-training

### 통계

- 조건당 최소 3–5 seeds
- Paired scenario comparison
- Bootstrap confidence interval
- 적절한 paired significance test
- Effect size
- Maneuver family별 breakdown

## 14. 선행연구 차별화

국제 원고는 다음 연구와 직접 비교한다.

- CoC faithfulness: https://arxiv.org/abs/2605.17268
- CoT–action intervention: https://arxiv.org/abs/2606.12706
- Sensor perturbation robustness: https://arxiv.org/abs/2605.21446
- Perception-grounded CoC and trajectory consistency: https://arxiv.org/abs/2607.14727
- Counterfactual CoT: https://arxiv.org/abs/2605.10744
- Hard-negative trajectory learning: https://arxiv.org/abs/2605.19771

차별화 문장:

> 본 연구는 CoC의 장면 충실도나 행동 인과성을 다시 측정하는 데 그치지 않고, 동일 CoC 목표를 달성하는 복수 trajectory의 허용집합을 명시적 safety contract로 정의하고, 새로운 계약과 maneuver에서 목표 보존형 준수를 학습ㆍ검증한다.

## 15. 공개 및 재현 패키지

국제 투고 전 다음을 공개 가능한 형태로 정리한다.

- Micro-world와 parameterized scenario generator
- Guard schema와 compiler
- Candidate trajectory generator
- Deterministic verifier
- Training configs와 prompt templates
- Seeds와 split manifests
- Evaluation scripts
- 공개 가능한 model adapter
- Aggregate 결과와 figure 생성 코드
- Restricted 결과를 제외하고도 주요 표가 재현되는 실행 절차

## 16. 단계별 실행 계획

### Phase 0. 국내 저널 완료 Gate

- [ ] 국내 논문 실험 revision 고정
- [ ] 국내 원고 전체 작성
- [ ] Claim audit
- [ ] 투고 형식 적용
- [ ] 국내 저널 투고 완료

이 gate가 완료되기 전에는 국제 확장을 위해 국내 원고 범위를 계속 늘리지 않는다.

### Phase 1. 국제 benchmark 기반

- [ ] 실행 가능한 candidate trajectory 정의
- [ ] MetaDrive 또는 CARLA 환경 연결
- [ ] 독립 Guard/STL monitor 구현
- [ ] CRUISE → STOP template
- [ ] LANE CHANGE → COMPLETE/ABORT template
- [ ] YIELD → ENTER template

완료 기준: 네 maneuver에서 requirement-only와 deterministic verifier baseline을 폐루프로 실행할 수 있다.

### Phase 2. Guard-aware 학습

- [ ] Pairwise contract-swap loss
- [ ] Violation robustness loss
- [ ] Goal/deadlock loss
- [ ] Comfort loss
- [ ] Hard-negative baseline

완료 기준: Safety-Constrained CoC가 shuffled와 hard-negative baseline을 safe-goal 및 OOD에서 안정적으로 능가한다.

### Phase 3. 규모와 일반화

- [ ] 조건당 최소 900 episode
- [ ] 3–5 seeds
- [ ] 연속 threshold
- [ ] Unseen conjunction/phase/scenario
- [ ] 두 번째 VLM family
- [ ] 통계 분석

완료 기준: 주요 효과 방향이 모델, seed와 maneuver에 걸쳐 재현된다.

### Phase 4. 실제 데이터 case study

- [ ] 실제 장면 50–100개 선정
- [ ] Candidate perturbation 생성
- [ ] 2인 Guard applicability 검토
- [ ] Inter-rater agreement
- [ ] 실제 장면 transfer 분석

### Phase 5. 국제 원고

- [ ] 영문 title/abstract/introduction
- [ ] 최신 related-work matrix
- [ ] Methods와 formal problem formulation
- [ ] Main/ablation/OOD tables
- [ ] Threats to validity
- [ ] Reproducibility statement
- [ ] 내부 reviewer-style audit
- [ ] 목표 저널 형식 적용

## 17. Go/No-Go 기준

### 국제 저널 투고 Go

- Safety-Constrained CoC가 requirement-only와 shuffled보다 폐루프 Guard 위반을 유의하게 감소
- Route completion 및 progress 저하가 사전 허용범위 이내
- Hard-negative baseline 대비 OOD contract 또는 composition에서 추가 이점
- 최소 3 maneuver, 2 model family, 3 seeds에서 방향 재현
- 공개 가능한 주요 benchmark와 evaluator 준비

### 설계 수정

- 위반은 줄지만 always-stop 또는 traversal time이 크게 증가
- ID에서만 개선되고 OOD threshold/composition에서는 이점이 없음
- Hard-negative baseline과 차이가 없음
- Inline 제약 효과가 다른 VLM에서 재현되지 않음

이 경우 국제 논문의 중심을 “새로운 안전 학습법”에서 “CoC safety-contract benchmark와 failure analysis”로 조정한다.

## 18. 국제 투고 전 최소 체크리스트

- [ ] 최소 4 maneuver family
- [ ] 연속 또는 실행 가능한 trajectory
- [ ] Parameterized closed-loop simulation
- [ ] Collision, TTC, route completion, comfort
- [ ] Hard-negative baseline
- [ ] Deterministic verifier와 hybrid
- [ ] Guard-aware objective
- [ ] Unseen threshold와 Guard composition
- [ ] 공개 VLM 2개 이상
- [ ] 3–5 seeds 및 통계
- [ ] 공개 재현 패키지

## 19. 근거 문서

- `WRITING_PLAN.md`
- `../../docs/reports/SAFETY_CONSTRAINED_COC_PROGRESS_REPORT_V01.md`
- `../../docs/reports/TEMPORAL_GUARD_MULTISEED_EXPERIMENT_REPORT_V01.md`
- `../../artifacts/results/public/small-vlm-guard-v0/temporal-guard-multiseed-v0/`

