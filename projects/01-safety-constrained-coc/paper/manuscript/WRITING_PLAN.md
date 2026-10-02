# 논문 1 작성 계획: Safety-Constrained Chain-of-Causation

- 작성일: 2026-08-04
- 목표 분야: 자율주행 AI, Vision-Language Model, AI safety
- 목표 수준: 국내 SCOPUS 등재 학술지
- 현재 단계: 핵심 feasibility, 시간적 Guard 및 2-maneuver 3-seed 재현, hard-test 완료
- 후속 계획: 국내 저널 투고 완료 후 `INTERNATIONAL_JOURNAL_EXPANSION_PLAN.md`에 따라 폐루프 국제 저널 연구로 확장
- 국내 저널 상세 아웃라인: `PAPER_OUTLINE_KO.md`

## 1. 가제

### 권장 영문 제목

**Safety-Constrained Chain-of-Causation for Goal-Preserving Trajectory Selection in Vision-Language Driving Models**

### 대안 제목

**Beyond Behavioral Justification: Augmenting Chain-of-Causation with Explicit Safety Constraints**

### 한국어 제목

**비전-언어 자율주행 모델의 목표 보존형 궤적 선택을 위한 안전 제약 Chain-of-Causation**

## 2. 한 문장 주장

> 요구사항 중심 CoC를 명시적 자연어 안전 제약이 포함된 Safety-Constrained CoC로 확장하고 학습하면, 작은 VLM은 운전 목표를 포기하지 않으면서 명시된 제약을 위반하는 trajectory 선택을 줄일 수 있다.

## 3. 연구 문제

기존 CoC는 “보행자에게 양보한다”, “교차로를 통과한다”와 같이 행동의 원인과 목표를 설명한다. 그러나 다음 정보는 항상 명시하지 않는다.

- Guard 활성화 조건
- 활성화 중 유지할 invariant
- 속도ㆍ거리ㆍ가속도 상한과 하한
- 금지 영역과 행동
- hold 및 release 조건
- 불확실성 fallback
- maneuver 완료 조건

그 결과 복수의 trajectory가 같은 CoC 목표를 달성하더라도, 그중 일부가 현재 허용조건을 위반할 수 있다.

## 4. 연구 질문

- **RQ1 효과:** Safety-Constrained CoC는 requirement-only CoC보다 Guard 위반 trajectory 선택을 줄이는가?
- **RQ2 목표 보존:** 위반 감소가 always-stop이나 deadlock이 아니라 운전 목표를 유지하면서 나타나는가?
- **RQ3 시간적 전환:** 모델은 STOP–HOLD–RELEASE–GO와 같은 phase-dependent Guard를 학습하는가?
- **RQ4 Maneuver coverage:** 효과가 주행 유지, 주행 중 정지, 재출발, 차선 변경ㆍ중단 및 Yield 진입에서 반복되는가?
- **RQ5 일반화:** 학습하지 않은 문장, 수치, phase 및 Guard 조합에서도 효과가 유지되는가?

## 5. 핵심 개념

### 5.1 Safety-Constrained CoC

```text
Requirement: 무엇을 달성할 것인가
Constraint:  어떤 조건ㆍ경계 안에서 달성해야 하는가
```

예:

```text
보행자에게 양보한 뒤 교차로를 통과한다.
보행자가 conflict zone에 있는 동안 정지선을 넘지 않는다.
Conflict zone이 1.5초 동안 연속으로 clear인 이후에만 출발한다.
```

### 5.2 Guard taxonomy

```text
ACTIVATION
INVARIANT
BOUND
PROHIBITION
RELEASE
FALLBACK
TERMINATION
```

### 5.3 Goal-compliant hard negative

CoC 목표를 달성하지만 Guard를 위반하는 trajectory를 뜻한다. 사고 trajectory일 필요는 없다.

```text
CoC: 교차로를 통과한다.
A: 6 m/s로 통과한다.
B: 3 m/s로 통과한다.
Guard: max_speed <= 4 m/s
```

A와 B 모두 CoC 목표를 달성하지만 A만 Guard를 위반한다.

## 6. 현재 확보한 증거

### 6.1 Alpamayo-R1 zero-shot Guard 진단

- CoC 문장 추가는 R1 trajectory에 영향을 줬다.
- Hold와 반대 의미 Guard의 차이는 약 0.008 m로 매우 작았다.
- 무관한 문장 효과와 분리하기 어려워 `WEAK_DIRECTIONAL_NOT_SEMANTICALLY_SPECIFIC`으로 판정했다.
- 해석: 학습하지 않은 Guard를 prompt로 삽입하는 것만으로는 의미 준수를 기대하기 어렵다.

### 6.2 작은 VLM Guard 학습

- 올바른 Guard 학습 정확도: 0.990
- Shuffled Guard 정확도: 0.719
- 동일 장면 counterfactual 완전 정답률: 0.958 대 0.000

### 6.3 정적 후보 trajectory 실험

| 조건 | 정확도 | 위반 선택률 ↓ | 계약 전환 pair ↑ |
|---|---:|---:|---:|
| Requirement CoC | 0.500 | 0.500 | 0.000 |
| Inline 자연어 제약 | 1.000 | 0.000 | 1.000 |
| Separate 자연어 Guard | 0.993 | 0.014 | 0.986 |
| Shuffled Guard | 0.465 | 0.375 | 0.153 |

### 6.4 시간적 Guard 3-seed 실험

| 조건 | Guard 위반 ↓ | 안전+목표 완료 ↑ | 계약 전환 pair ↑ |
|---|---:|---:|---:|
| Requirement CoC | 0.319 ± 0.052 | 0.681 ± 0.052 | 0.000 ± 0.000 |
| Inline 자연어 제약 | 0.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| Separate 자연어 Guard | 0.191 ± 0.136 | 0.809 ± 0.136 | 0.396 ± 0.187 |
| Shuffled Guard | 0.333 ± 0.023 | 0.667 ± 0.023 | 0.021 ± 0.029 |

Inline 자연어 제약 효과는 세 seed에서 완전히 재현됐다. 별도 자연어 Guard도 평균적으로 requirement-only보다 나았지만 seed 변동과 unseen-time 실패가 남았다.

### 6.5 다중 maneuver 3-seed 및 hard-test 실험

Qwen3-VL-2B-Instruct + LoRA를 사용해 동일 장면에서 permissive/restrictive 계약만 바뀌는 후보 선택 과제를 구성했다. `CRUISE → STOP`은 정지선, 최대 감속도와 jerk를, `LANE CHANGE → COMPLETE/ABORT`는 최소 gap과 abort 후 재시도를 평가했다.

| 조건 | Guard 위반 ↓ | 안전+목표 완료 ↑ | 계약 전환 pair ↑ |
|---|---:|---:|---:|
| Requirement CoC | 0.292 ± 0.072 | 0.708 ± 0.072 | 0.000 ± 0.000 |
| Safety-Constrained CoC | 0.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| Shuffled constraint | 0.267 ± 0.039 | 0.733 ± 0.039 | 0.028 ± 0.032 |

표준 test에서 Safety-Constrained CoC는 세 seed 모두 두 maneuver의 위반 0, 안전한 목표 완료 1.0, 계약 전환 pair 1.0을 기록했다. 경계 equality, 부정 표현, 절 순서 변경 및 단위 변환을 결합한 hard test에서는 정확도 `0.948 ± 0.063`, 위반 `0.010 ± 0.010`, 안전한 목표 완료 `0.990 ± 0.010`, 계약 pair `0.896 ± 0.127`이었다. 이는 효과 재현과 동시에 자연어ㆍ수치 일반화가 완전하지 않다는 후속 문제를 드러낸다. 상세 결과는 `artifacts/results/public/small-vlm-guard-v0/maneuver-guard-multiseed-v0/REPORT_KO.md`에 기록했다.

## 7. 논문의 핵심 기여

1. 행동 정당화 중심 CoC를 요구사항과 허용조건을 함께 갖는 Safety-Constrained CoC로 재정의한다.
2. 운전 Guard를 activation, invariant, bound, prohibition, release, fallback 및 termination으로 구조화한다.
3. 모든 후보가 CoC 목표를 달성하되 Guard 준수 여부가 다른 counterfactual benchmark를 제안한다.
4. Guard 위반 감소와 목표 완료, deadlock 및 진행성을 함께 평가하는 방법을 제안한다.
5. 정적 제약과 STOP–HOLD–RELEASE–GO 시간적 제약에서 작은 VLM의 학습 가능성을 실증한다.
6. 실제 Alpamayo-R1의 zero-shot Guard 반응과 학습된 작은 VLM의 의미 준수를 구분한다.

## 8. 추가 실험 계획

### E1. CRUISE → STOP

상태: seed 42/17/123 재현 및 결합 hard test 완료. factorial hard-test와 실제 trajectory 연결 필요.

Guard 예:

- 정지선 이전에 정지
- conflict zone 진입 금지
- 최대 감속도 및 jerk
- 불확실하면 정지 유지

후보:

- 늦게 제동해 정지선 초과
- 정지선 전에 부드럽게 정지
- 불필요하게 매우 일찍 정지
- 정지하지 않고 통과

### E2. LANE CHANGE → COMPLETE/ABORT

상태: seed 42/17/123 재현 및 결합 hard test 완료. 조향 변화율, 복귀 trajectory 및 factorial hard-test 추가 필요.

Guard 예:

- 충분한 전후방 gap에서만 시작
- 변경 중 최소 측면거리 유지
- gap이 닫히면 abort 또는 원래 차선으로 복귀
- 조향 변화율 상한

후보:

- 안전 gap에서 정상 완료
- 작은 gap에서 시작
- 위험 발생 후에도 계속 변경
- 필요 없는 무조건 abort

### E3. YIELD → GAP ACCEPTANCE → ENTER

Guard 예:

- conflict zone 점유 중 진입 금지
- TTC 하한
- 안전 gap 확보 후 진입
- 불확실하면 hold 또는 제한된 creep

### E4. 일반화

- 연속적으로 샘플링한 threshold
- 학습하지 않은 Guard conjunction
- 학습하지 않은 phase 순서
- 자연어 paraphrase
- 최소 3–5 seeds

## 9. 조건과 지표

### 주요 조건

- Requirement-only CoC
- Safety-Constrained CoC
- Shuffled/irrelevant constraint
- 필요 시 external deterministic verifier upper bound

별도 자연어와 형식 표현 비교는 논문 2의 중심 실험으로 이동하고, 논문 1에서는 검증된 대표 형식을 사용한다.

### 주요 지표

- Guard violation rate
- Conjunction satisfaction rate
- Safe goal completion
- Deadlock / always-stop rate
- False rejection of admissible trajectory
- Progress regret
- Contract-swap pair accuracy
- Unseen phrase/value/composition accuracy

## 10. 논문 구성

1. **Introduction**
   - CoC의 행동 정당화 가치와 안전 명세 한계
   - 요구사항과 허용조건의 구분
   - 연구 질문과 기여
2. **Related Work**
   - Reasoning-augmented E2E/VLA
   - CoT/CoC faithfulness와 causal intervention
   - Driving safety constraints와 shield
   - 자연어 기반 policy conditioning
3. **Problem Formulation**
   - Requirement CoC, Guard, candidate trajectory, admissible set
   - Goal completion과 Guard compliance의 동시 목적
4. **Safety-Constrained CoC**
   - Guard taxonomy
   - Inline representation
   - Counterfactual contract pair
5. **Benchmark and Method**
   - Micro-world와 maneuver suite
   - Qwen3-VL LoRA
   - 독립 verifier와 metrics
6. **Experiments**
   - R1 zero-shot diagnostic
   - 정적 constraint
   - 시간적 release
   - 추가 maneuver
7. **Results**
   - 위반 감소, 목표 보존, 일반화
8. **Discussion**
   - CoC justification과 safety contract의 차이
   - Guard 학습과 runtime verifier의 역할
9. **Threats to Validity**
10. **Conclusion**

## 11. 표와 그림 계획

### 그림

1. 기존 CoC와 Safety-Constrained CoC 비교 개요
2. Requirement–Guard–trajectory admissible set 구조
3. 정적 후보 trajectory 예시
4. STOP–HOLD–RELEASE–GO storyboard
5. Maneuver별 Guard state machine
6. 학습 및 독립 verifier 아키텍처

### 표

1. 관련연구 비교
2. Guard taxonomy와 maneuver mapping
3. 데이터 및 학습 설정
4. 정적 실험 결과
5. 시간적 3-seed 결과
6. Maneuver별 위반ㆍsafe-goal 결과
7. 일반화 및 ablation
8. 주장 가능 범위와 한계

## 12. 주장 경계

### 주장 가능

- 합성 VLM 후보 선택에서 자연어 제약이 명시된 Guard 준수를 개선했다.
- Inline 자연어 시간 제약 효과는 3개 seed에서 반복됐다.
- 위반 감소는 deadlock 없이 목표 완료를 유지하면서 나타났다.

### 주장 불가

- 실제 도로 사고율 감소
- Alpamayo-R1의 실제 안전 향상
- 완전한 안전 명세
- 연속 제어 안정성 보장
- 모든 VLM 및 maneuver로의 일반화

## 13. 완료 기준

- [x] 연구 질문과 Safety-Constrained CoC 정의
- [x] 정적 candidate benchmark
- [x] 시간적 release benchmark
- [x] 시간적 실험 3-seed 재현
- [ ] CRUISE → STOP 실험
- [ ] LANE CHANGE → COMPLETE/ABORT 실험
- [ ] Maneuver 통합 결과표
- [ ] 최신 선행연구 체계적 정리
- [ ] 초록ㆍ서론ㆍ방법 초안
- [ ] 전체 원고 작성
- [ ] 내부 claim audit
- [ ] 목표 저널 형식 적용

## 14. 근거 자료

- `../../docs/reports/SAFETY_CONSTRAINED_COC_PROGRESS_REPORT_V01.md`
- `../../docs/reports/TEMPORAL_GUARD_MULTISEED_EXPERIMENT_REPORT_V01.md`
- `../../artifacts/results/public/small-vlm-guard-v0/candidate-guard-summary-seed42-v0/`
- `../../artifacts/results/public/small-vlm-guard-v0/temporal-guard-multiseed-v0/`
- `../../artifacts/results/restricted/alp-exp-006/guard-semantic-summary-v2/`
- `INTERNATIONAL_JOURNAL_EXPANSION_PLAN.md`
