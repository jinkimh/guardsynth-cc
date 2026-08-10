# CoC 기반 E2E 자율주행 안전성을 위한 정형기법 선택 서베이

- 기준일: 2026-08-02
- 목표: 1차 연구에서 사용할 1--2개의 정형기법 선택
- 목표 학회: NeurIPS급 기계학습 학회
- 결론: **Signal Temporal Logic(STL) + Control Barrier Function(CBF) 기반 안전 필터**

## 1. 선택 문제

검증 대상은 거대한 신경망의 모든 가중치가 아니다. 다음 세 산출물의 관계다.

1. 영상과 차량 상태에서 생성된 Chain-of-Causation(CoC) reasoning
2. reasoning과 함께 생성된 미래 trajectory 또는 제어 명령
3. 해당 trajectory를 실행했을 때의 폐루프 차량 상태

CoC는 다음 질문에 답할 단서를 준다.

- 왜 제어가 시작됐는가?
- 언제까지 반응해야 하는가?
- 어떤 조건이 유지되는 동안 무엇을 금지해야 하는가?
- 무엇이 다음 행동을 허용하는가?

그러나 CoC가 자연어로 그럴듯하다는 사실은 trajectory의 안전성이나 차량 상태의 안전 불변성을 보증하지 않는다. 따라서 1차 연구에는 서로 다른 두 종류의 형식적 지원이 필요하다.

- **의미ㆍ시간 계층:** CoC와 연속 trajectory 사이의 계약 만족도
- **물리ㆍ실행 계층:** 차량 동역학 아래에서 안전 집합을 벗어나지 않도록 하는 폐루프 제어

## 2. 후보 비교

| 후보 | CoC 시간 의미 | 연속 trajectory | 학습 손실/보상 | 폐루프 물리 보증 | 확장성 | 1차 역할 |
|---|---:|---:|---:|---:|---:|---|
| UPPAAL timed automata | 높음 | 낮음--중간 | 낮음 | 추상 모델에 한정 | 중간 | 이산 프로토콜 baseline |
| SAT/BMC | 중간 | 낮음 | 낮음 | 유계ㆍ이산화 모델에 한정 | 중간 | mutation oracle baseline |
| SMT | 중간 | 중간 | 낮음 | 이론과 모델 범위에 한정 | 낮음--중간 | 파라미터/비선형 진단 |
| STL | **매우 높음** | **매우 높음** | **매우 높음** | 단일 trace 만족에 한정 | **높음** | **주 기법** |
| CBF 안전 필터 | 낮음 | 높음 | 중간 | **안전 집합의 전방 불변성** | **높음** | **보조 주 기법** |
| HJ reachability | 중간 | 높음 | 중간 | 강함 | 상태 차원에 취약 | oracle/소규모 benchmark |
| 신경망 verifier | 낮음 | 중간 | 낮음 | 검증한 네트워크와 입력 집합에 한정 | 전체 VLA에는 매우 낮음 | 1차 제외 |

점수의 의미는 도구 일반의 우열이 아니라 본 연구 질문과의 적합성이다.

## 3. 1순위: Signal Temporal Logic

### 3.1 선택 이유

STL은 실수값 시간 신호에 대해 시간 제한이 있는 규칙을 표현한다. CoC의 핵심 구조와 직접 대응한다.

자연어 CoC:

> 보행자가 진입했으므로 감속하고, 보행자가 있는 동안 정지 또는 양보를 유지하며, 사라진 뒤에만 속도를 회복한다.

STL 계약 예:

```text
G(ped_enter -> F_[0,D_brake](a_ego <= -a_min))
G(ped_present -> (v_ego <= v_yield))
G(resume -> previously_[0,D_clear](ped_clear))
G(TTC < tau -> F_[0,D_emg](a_ego <= -a_emg))
```

STL의 quantitative robustness `rho(phi, x)`는 단순 PASS/FAIL보다 많은 정보를 준다.

- `rho > 0`: 만족 여유가 있음
- `rho = 0`: 계약 경계
- `rho < 0`: 위반 크기와 가장 취약한 시간 구간을 제공

이 값은 다음에 직접 사용할 수 있다.

- CoC/trajectory 출력 평가
- 데이터 품질 점수와 hard-negative 채굴
- differentiable surrogate loss
- preference pair 구성
- counterexample-guided fine-tuning

### 3.2 최신 연구 근거

- ICML 2024의 Specification-conditioned Decision Transformer는 STL로 복잡한 시간 규칙을 조건화한 offline safe RL을 보였다.
- NeurIPS 2025의 TiLoIL은 temporal logic와 imitation learning의 직접 결합이 탑 ML 학회의 유효한 연구축임을 보였다. 다만 LTL/LDBA와 무한 시간 objective가 중심이며, 본 연구는 시간 제한이 있는 연속 주행 신호와 reasoning-action consistency를 다룬다.
- RA-L 2024의 STL diffusion policy는 nuScenes에서 STL 보정, trajectory augmentation, rule-conditioned diffusion learning과 closed-loop 평가를 결합했다.
- L4DC 2025의 temporal predicate learning은 conformal prediction으로 유한표본 보장을 부여하여 CoC에서 추출한 임계값의 불확실성을 다룰 단서를 제공한다.
- ICML 2025의 grammar-forced NL-to-TL은 자연어를 형식문법에 맞춰 번역할 때 constrained generation과 검증 계층이 필요함을 뒷받침한다.
- 2026년 WorkDrive는 도로공사 장면에서 perception-grounded CoC annotation과 trajectory consistency 학습을 제시했다. 이는 CoC가 특정 모델명에 한정되지 않고 주행 데이터 구성 방식으로 확장되고 있음을 보여주지만, 형식적 안전 검증은 아직 제공하지 않는다.

### 3.3 STL만으로 충분하지 않은 이유

STL monitor가 기록된 trajectory `x`에 대해 `x |= phi`를 판정해도 다음은 자동으로 증명되지 않는다.

- 센서 오차가 있는 모든 실제 상태에서 같은 규칙을 만족하는가?
- 다른 차량이 예상과 다르게 움직여도 충돌하지 않는가?
- 차량 제동 한계로 해당 trajectory를 실제 추종할 수 있는가?
- 매 제어 주기에서 안전 집합이 유지되는가?

즉 STL은 **계약 만족도**에는 가장 적절하지만, 그 자체가 전체 폐루프 안전 보증은 아니다.

## 4. 2순위: CBF 기반 안전 필터

### 4.1 선택 이유

안전 집합을 `C = {x | h(x) >= 0}`로 두고, 제어입력 `u`가 다음 조건을 만족하도록 제한한다.

```text
dh/dx (f(x) + g(x)u) + alpha(h(x)) >= 0
```

조건과 동역학 가정이 성립하면 `C`의 전방 불변성을 보일 수 있다. Alpamayo류 E2E 모델의 출력은 nominal trajectory/control로 사용하고, QP safety filter가 필요한 최소 수정만 적용한다.

```text
u_safe = argmin_u ||u - u_nom||^2
         s.t. CBF collision, road, actuator constraints
```

이 분리는 중요하다.

- E2E 모델: 풍부한 장면 이해, reasoning, 운전 성능
- STL: CoC가 뜻하는 연속 시간 의무와 trajectory의 일관성
- CBF: 실행 시 충돌ㆍ도로경계ㆍ제어한계에 대한 hard constraint

NeurIPS 2025에는 CBF를 safe policy learning과 결합한 연구가 채택되었고, 2024 L4DC 연구는 black-box dynamics의 안전 필터를 학습하는 방향을 제시했다. 이는 거대 정책을 직접 증명하는 대신 nominal policy와 안전 계층을 분리하는 설계를 지지한다.

### 4.2 HJ reachability보다 먼저 선택하는 이유

HJ reachability는 안전 집합과 worst-case disturbance를 강하게 다룰 수 있으나 상태 차원이 증가하면 계산량이 급격히 커진다. 자율주행의 다중 객체, perception uncertainty, 장시간 episode를 1차 연구에서 그대로 다루기 어렵다.

1차 연구에서는 다음 구성이 현실적이다.

- CBF-QP: 실시간 폐루프 필터와 주 실험
- HJ reachability: 저차원 cut-in/pedestrian benchmark에서 CBF safe set의 oracle 또는 비교군

따라서 HJ는 별도의 주 기법이 아니라 **제한된 검증 oracle**로 둔다.

### 4.3 CBF의 한계

- 올바른 동역학 모델과 상태 추정 오차 범위가 필요하다.
- 부정확하게 학습된 barrier에는 자동 보증이 없다.
- 여러 CBF 제약이 동시에 infeasible할 수 있다.
- “양보 후 회복” 같은 긴 시간 순서 의미를 CBF만으로 표현하기 어렵다.

이 한계 때문에 CBF는 STL을 대체하지 않고 보완한다.

## 5. 제외 또는 제한하는 기법

### UPPAAL

기존 feasibility에서 반복 명령의 preserve/reset 의미론, deadline, 조기 회복 같은 프로토콜 오류를 잘 찾았다. 그러나 이벤트 임계값과 위치를 사람이 이산화해야 하고, quantitative robustness나 gradient를 fine-tuning에 직접 제공하기 어렵다.

결론: 기존 결과와 동일한 이산 mutation subset에 대한 **설명 가능한 baseline**으로 유지한다.

### SAT/BMC

유한 episode의 순서 위반을 정확히 찾는 데 유용하지만 연속 차량 신호와 물리 불확실성을 Boolean encoding으로 옮기는 비용이 크다.

결론: 핵심 기법으로 채택하지 않는다.

### SMT

선형/비선형 실수 제약과 파라미터 탐색에는 유용하다. 그러나 full VLA, 긴 episode, 환경 분기를 한꺼번에 SMT로 푸는 것은 연구의 병목이 된다.

결론: CBF 조건의 offline sanity check나 threshold synthesis에 필요할 때만 내부 solver로 사용하며, 독립 연구축으로 주장하지 않는다.

### 전체 신경망 검증

10B 규모 VLA와 영상 입력, autoregressive reasoning, trajectory decoder 전체에 대한 완전 검증은 현재 1차 연구 범위에서 현실적이지 않다.

결론: decoder의 작은 surrogate나 safety head 검증은 후속 연구로 둔다.

## 6. 최종 선택

1차 연구는 **두 개의 solver가 아니라 두 개의 형식적 계층**을 선택한다.

1. **CoC-to-STL 계약 및 differentiable robustness**
2. **CBF-QP 폐루프 안전 필터**

UPPAAL은 discrete protocol baseline, HJ reachability는 저차원 oracle, SMT는 조건 검사 도구로만 사용한다.

## 7. NeurIPS급 차별점

STL과 CBF를 단순히 직렬 연결한 것만으로는 부족하다. 논문의 핵심 학습 기여는 다음이어야 한다.

### C1. Grounded CoC-to-STL compiler

CoC 텍스트만 번역하지 않고 object track, ego state, trajectory와 연결된 typed predicate를 생성한다. 문법에 맞는 공식이라도 영상 근거가 없으면 `UNGROUNDED`로 거부한다.

### C2. Contract uncertainty

deadline과 threshold를 임의 상수로 두지 않는다. 데이터, 차량 동역학, 센서 지연에서 구간 또는 분포를 추정하고 conformal calibration으로 coverage를 보고한다.

### C3. Counterexample-guided post-training

음의 STL robustness 구간과 CBF intervention을 hard-negative 또는 preference pair로 바꾼다. 학습 후 다음 세 값이 함께 좋아지는지를 측정한다.

- 계약 만족률/robustness
- 폐루프 collision 및 intervention rate
- nominal driving quality

### C4. Semantic-physical disagreement taxonomy

다음 네 경우를 분리한다.

| STL | CBF | 해석 |
|---|---|---|
| PASS | 미개입 | 의미ㆍ물리 일관 후보 |
| FAIL | 미개입 | 사고 전 프로토콜/추론 오류 |
| PASS | 개입 | reasoning은 그럴듯하지만 물리적으로 위험/실행 불가 |
| FAIL | 개입 | 의미와 물리 양쪽의 강한 hard-negative |

이 불일치가 본 연구의 가장 흥미로운 신규 신호다.

## 8. 주장 경계

이 연구가 보일 수 있는 것:

- 지정된 grounding과 uncertainty 가정 아래 CoC 유래 STL 계약의 trajectory 만족 여부
- CBF 모델ㆍ상태 추정ㆍfeasibility 가정 아래 안전 집합의 전방 불변성
- 형식적 신호를 학습에 넣었을 때 폐루프 안전 지표가 개선되는지 여부

이 연구만으로 보일 수 없는 것:

- CoC 자연어가 현실의 참된 인과관계라는 보증
- 미관측 분포 전체에 대한 완전한 자율주행 안전
- perception 오류가 가정 범위를 벗어난 경우의 보증
- 모델 전체 또는 실제 차량의 인증

따라서 논문 표현은 “E2E 안전을 완전히 증명한다”가 아니라 **grounded temporal contracts와 certified execution filter로 CoC 기반 E2E의 검증 및 안전 지원 범위를 확장한다**가 되어야 한다.

## 9. 핵심 1차 문헌

1. NVIDIA, Alpamayo-R1-10B model card: https://huggingface.co/nvidia/Alpamayo-R1-10B
2. Alpamayo paper: https://arxiv.org/abs/2511.00088
3. Specification-conditioned Decision Transformer, ICML 2024: https://proceedings.mlr.press/v235/guo24j.html
4. Imitation Learning with Temporal Logic Constraints, NeurIPS 2025: https://papers.nips.cc/paper_files/paper/2025/hash/e9fa0f2895e827b15f43b1fdd15a2a04-Abstract-Conference.html
5. Diverse Controllable Diffusion Policy with STL, RA-L 2024: https://arxiv.org/abs/2503.02924
6. Learning from Demonstrations using STL, CoRL 2020: https://proceedings.mlr.press/v155/puranic21a.html
7. Learning Temporal Logic Predicates with Statistical Guarantees, L4DC 2025: https://proceedings.mlr.press/v283/soroka25a.html
8. Grammar-Forced Translation of Natural Language to Temporal Logic, ICML 2025: https://openreview.net/forum?id=p411a7WHox
9. HMARL-CBF, NeurIPS 2025: https://proceedings.neurips.cc/paper_files/paper/2025/hash/76486c7eb6056f12e7ce3addced61650-Abstract-Conference.html
10. Safety Filters for Black-Box Dynamical Systems, L4DC 2024: https://proceedings.mlr.press/v242/lavanakul24a.html
11. A Provable Approach for End-to-End Safe RL, NeurIPS 2025: https://proceedings.neurips.cc/paper_files/paper/2025/hash/6faf3b8ed0df532c14d0fc009e451b6d-Abstract-Conference.html
12. Temporal Logic-Based Multi-Vehicle Backdoor Attacks against Offline RL Agents in E2E Driving, NeurIPS 2025: https://proceedings.neurips.cc/paper_files/paper/2025/hash/656c9f7c3a322e31ce56403cca3ca0f1-Abstract-Conference.html
13. WorkDrive: Roadwork Chain of Causation for Autonomous Driving, 2026: https://arxiv.org/abs/2607.14727
14. How to Train Your Latent Control Barrier Function, L4DC 2026: https://proceedings.mlr.press/v331/nakamura26a.html
