# 국내 저널 논문 아웃라인: Safety-Constrained Chain-of-Causation

- 문서 목적: 국내 SCOPUS 등재 학술지 투고용 논문의 골격과 핵심 실험 결과 고정
- 작성일: 2026-08-04
- 작성 수준: 주요 주장ㆍ절별 내용ㆍ표ㆍ그림 프롬프트 중심이며 완성 원고는 아님
- 권장 분량: 본문 12–16쪽, 부록 또는 온라인 보충자료 별도

## 0. 논문 전체의 중심

### 가제

**비전-언어 자율주행 모델의 목표 보존형 궤적 선택을 위한 Safety-Constrained Chain-of-Causation**

영문:

**Safety-Constrained Chain-of-Causation for Goal-Preserving Trajectory Selection in Vision-Language Driving Models**

### 한 문장 주장

> 요구사항 중심 CoC에 실행 가드를 명시하고 그 의미에 맞는 감독 신호로 학습하면, 작은 VLM은 운전 목표를 포기하지 않으면서 가드 위반 trajectory 후보 선택을 줄일 수 있다.

### 주장하지 않을 내용

- 기존 CoC가 일반적으로 unsafe trajectory를 만든다는 주장
- 자연어 가드만으로 실제 차량의 안전이 보장된다는 주장
- Alpamayo-R1 또는 실제 도로에서 collision이 감소했다는 주장
- 제안한 가드가 완전한 도로 안전 명세라는 주장
- VLM이 정밀 수치 제어기나 정형 verifier를 대체한다는 주장

### 논문의 증거 흐름

```text
Alpamayo-R1 zero-shot 진단
  -> 문장 삽입은 trajectory에 영향을 주지만 의미별 반응은 약함
  -> 가드 준수는 prompt만이 아니라 학습되어야 함

작은 VLM prototype 학습
  -> 자연어 Guard와 행동 대응은 학습 가능
  -> 단순 STOP/PROCEED 과제만으로는 Guard의 추가 가치가 식별되지 않음

Goal-compliant hard-negative 후보 실험
  -> 같은 CoC 목표를 달성하는 후보 중 위반 후보를 구별
  -> 명시적 제약의 고유 효과 확인

시간적 계약 및 다중 maneuver 3-seed 실험
  -> STOP-HOLD-RELEASE-GO, 정지, 차선 변경으로 확장
  -> 목표 완료를 유지하면서 위반 감소 재현

Hard test와 폐루프 보조 실험
  -> 단위 변환ㆍ미관측 phaseㆍstale 계약에서는 한계가 남음
  -> 학습된 자연어 가드와 runtime verifier의 역할을 구분해야 함
```

---

## 초록 아웃라인

### 배경 1–2문장

- Chain-of-Causation(CoC)은 주행 장면과 예측 trajectory 사이의 판단 근거를 자연어로 표현한다.
- 그러나 행동 목표를 설명하는 CoC만으로는 정지선, 최소 간격, hold/release, 속도ㆍ감속도 상한과 같은 허용조건이 항상 명시되지 않는다.

### 문제와 방법 2–3문장

- 본 논문은 요구사항 CoC에 명시적 실행 가드를 결합한 `Safety-Constrained CoC`를 제안한다.
- 동일 장면과 후보를 유지한 채 permissive/restrictive 계약만 바꾸는 paired-contract benchmark를 구성하고, Qwen3-VL-2B-Instruct를 LoRA로 학습하였다.
- 정적 후보, STOP-HOLD-RELEASE-GO 시간 계약, `CRUISE→STOP`, `LANE CHANGE→ABORT/RETRY`를 평가하였다.

### 핵심 결과 2–3문장

- 시간적 3-seed 실험에서 requirement-only CoC의 위반률은 `0.319 ± 0.052`였고, inline Safety-Constrained CoC는 `0.000 ± 0.000`이었으며 안전한 목표 완료와 계약 전환 pair 정확도는 모두 `1.000`이었다.
- 다중 maneuver 3-seed에서도 inline 조건은 위반 `0.000 ± 0.000`, 안전한 목표 완료 `1.000 ± 0.000`, 계약 pair `1.000 ± 0.000`을 기록했다.
- 단위ㆍ부정ㆍ경계 표현을 포함한 hard test에서는 위반 `0.010 ± 0.010`, 안전한 목표 완료 `0.990 ± 0.010`으로 성능이 유지됐지만, 모든 오답이 단위 변환 예에 집중되었다.

### 결론 1문장

- 결과는 Safety-Constrained CoC의 학습 가능성과 목표 보존형 위반 감소를 지지하지만, 실제 적용에는 단위 정규화와 독립 verifier가 필요함을 보여준다.

---

## 1. 서론

### 1.1 연구 배경

- E2E/VLA 주행 모델은 센서 입력에서 trajectory를 직접 예측하지만 판단 근거와 제어 의무가 불투명할 수 있다.
- CoC는 장면의 원인, 판단 및 행동을 연결하는 유용한 추론 인터페이스다.
- 하지만 `보행자에게 양보한다`, `교차로를 통과한다`는 요구사항은 무엇을 달성할지는 말해도, 모든 허용 trajectory의 경계를 정의하지 않는다.

### 1.2 핵심 문제

동일한 요구사항을 달성하는 복수의 trajectory가 있을 수 있다.

```text
Requirement CoC: 보행자에게 양보한 후 진행한다.

후보 A: 정지선을 넘고 급정지한 뒤 진행
후보 B: 정지선 전에 부드럽게 정지한 뒤 진행
후보 C: 지나치게 일찍 정지한 뒤 진행
```

세 후보가 모두 최종 행동 목표를 달성하더라도 현재의 정지 위치ㆍ감속도ㆍjerk 가드에 따라 허용 여부와 최적 후보가 달라진다.

### 1.3 제안

```text
Safety-Constrained CoC = Requirement + Execution Guard
```

- Requirement: 무엇을 달성할 것인가
- Guard: 언제 활성화되고, 무엇을 유지하며, 어떤 경계를 넘지 않고, 언제 해제할 것인가

### 1.4 연구 질문

- **RQ1 — 효과:** Safety-Constrained CoC는 requirement-only CoC보다 가드 위반 후보 선택을 줄이는가?
- **RQ2 — 목표 보존:** 위반 감소가 always-stop/deadlock이 아니라 목표 완료를 유지하면서 나타나는가?
- **RQ3 — 시간ㆍmaneuver 일반성:** 효과가 시간적 hold/release, 정지 및 차선 변경에서 반복되는가?
- **RQ4 — 표현 일반화:** paraphrase, unseen 수치, 부정 표현, 경계값 및 단위 변환에서도 효과가 유지되는가?

### 1.5 기여

1. 행동 정당화 중심 CoC를 요구사항과 실행 가드를 함께 갖는 Safety-Constrained CoC로 확장한다.
2. CoC 목표를 달성하지만 현재 가드를 위반하는 `goal-compliant hard negative`와 paired-contract 평가 방법을 제시한다.
3. 가드 위반뿐 아니라 안전한 목표 완료, deadlock, 과도한 보수성과 계약 전환 pair 정확도를 함께 측정한다.
4. 정적, 시간적 및 다중 maneuver 과제에서 작은 VLM의 가드 조건부 후보 선택 학습 가능성을 3-seed로 검증한다.
5. Alpamayo-R1 zero-shot 진단과 hard/폐루프 보조 실험을 통해 prompt 반응, 학습된 준수 및 runtime enforcement의 차이를 분석한다.

### 그림 1 프롬프트 — 문제 개념도

> 학술 논문용 흰 배경 벡터 다이어그램. 왼쪽에는 동일한 교차로 장면과 “Yield to the pedestrian, then proceed”라는 Requirement CoC를 배치한다. 중앙에는 세 개의 trajectory 후보를 그린다: 정지선을 넘는 빠른 trajectory는 빨간색, 정지선 전에 부드럽게 정지하는 trajectory는 녹색, 지나치게 일찍 정지하는 trajectory는 회색. 위쪽에는 Requirement-only CoC가 세 후보를 모두 목표 충족으로 보는 모습을 표시한다. 아래쪽에는 “stop_offset ≤ 0, peak_decel ≤ d_max, peak_jerk ≤ j_max”라는 Safety Guard가 빨간 후보를 제거하고 녹색 후보를 선택하는 모습을 표시한다. 오른쪽에는 “goal preserved + guard compliant”를 강조한다. 과장된 자동차 그림 대신 간단한 도로ㆍ정지선ㆍtrajectory 선을 사용하고, IEEE/Elsevier 논문에 적합한 절제된 파랑ㆍ녹색ㆍ빨강 팔레트, 16:9 가로형, 텍스트가 선명한 벡터 스타일.

---

## 2. 관련 연구

### 2.1 Reasoning-augmented E2E/VLA driving

- CoT/CoC가 perception, planning 및 trajectory generation에 제공하는 역할
- reasoning faithfulness, grounding 및 reasoning–action consistency 연구
- 본 연구의 차이: 기존 CoC의 사실 오류 일반 검출보다, 동일 목표 내부의 허용 trajectory 경계를 명시하고 학습하는 문제

### 2.2 자율주행의 안전 제약과 runtime safety layer

- CBF, reachability, model-predictive safety filter, shield
- 이들은 정밀한 실행 강제에 적합하지만 자연어 reasoning과 제어 의무 사이의 인터페이스는 별도 문제

### 2.3 자연어 조건부 정책과 정형 명세

- 자연어의 표현 유연성과 사전학습 친숙도
- 논리 명세의 명확성과 실행 가능성
- 본 논문의 입장: 자연어와 정형 명세를 경쟁 관계로 두지 않고, 자연어 Safety-Constrained CoC를 학습 인터페이스로 평가한다. 정형 컴파일ㆍverifier 비교는 후속 확장으로 남긴다.

### 2.4 본 연구의 차별점

- 사고 trajectory를 요구하지 않는다.
- CoC 목표를 달성하는 후보 안에서 현재 가드 준수 여부를 구별한다.
- 동일 장면의 계약만 바꾸는 counterfactual pair로 장면 shortcut을 통제한다.
- 위반 감소와 목표 완료를 동시에 측정한다.

---

## 3. 문제 정의

### 3.1 기호

- 장면 입력: `x`
- Requirement CoC: `R`
- 실행 가드: `G`
- trajectory 후보 집합: `T(x) = {τ1, …, τK}`
- 목표 완료 함수: `Goal(τ, R) ∈ {0,1}`
- 가드 준수 함수: `Sat(τ, G) ∈ {0,1}`
- 진행도 또는 효용: `U(τ)`

### 3.2 목표 trajectory

```text
τ* = argmax U(τ)
     subject to Goal(τ, R)=1 and Sat(τ, G)=1
```

- 가드를 위반하지만 목표를 달성하는 후보는 hard negative다.
- 가드를 지키지만 목표를 완료하지 못하는 deadlock 후보도 최적 후보가 아니다.

### 3.3 Guard taxonomy

| 유형 | 의미 | 예 |
|---|---|---|
| Activation | 가드 활성 조건 | 보행자가 conflict zone에 있음 |
| Invariant | 활성 중 유지 조건 | 정지선을 넘지 않음 |
| Bound | 상ㆍ하한 | `gap ≥ 6 m`, `decel ≤ 4 m/s²` |
| Prohibition | 금지 행동 | gap 미달 상태에서 lane change 계속 금지 |
| Release | 의무 해제 조건 | 1.5초 연속 clear 후 출발 |
| Fallback | 불확실성 대응 | 관측 불확실 시 hold |
| Termination | maneuver 완료 | 안전 간격에서 변경 완료 |

### 3.4 주요 지표

- 후보 선택 정확도
- Guard violation rate
- Safe goal completion rate
- Deadlock/always-stop rate
- Over-conservative selection 또는 progress regret
- Contract-swap pair accuracy
- Paraphrase/unseen-value/hard-test 성능

---

## 4. 제안 방법

### 4.1 Safety-Constrained CoC 표현

주 표현은 기반 VLM이 가장 안정적으로 학습한 inline 자연어 형식으로 한다.

```text
Requirement CoC:
Stop for the pedestrian before the crosswalk, then continue when allowed.
Stop before the stop line. Peak deceleration must not exceed 3.8 m/s²
and peak jerk must not exceed 5.0 m/s³.
```

비교 표현:

- Requirement-only CoC
- Constraint inside CoC, 즉 Safety-Constrained CoC
- CoC + separate natural-language Guard
- Shuffled Guard/constraint
- Logic Guard

### 4.2 Paired-contract 구성

- 동일 이미지, 동일 후보, 동일 requirement를 유지한다.
- permissive와 restrictive 계약만 바꾼다.
- permissive에서는 더 빠른 후보가 최적이고 restrictive에서는 더 보수적이지만 진행 가능한 후보가 최적이다.
- 한 장면의 두 계약을 모두 맞혀야 pair 정답으로 계산한다.

### 4.3 학습 및 추론 구조

- 모델: Qwen3-VL-2B-Instruct
- 학습: LoRA
- 입력: 합성 장면 이미지 + CoC/Guard + 후보 설명
- 출력: 후보 레이블 `A/B/C/D`
- 독립 계산기: 각 후보가 계약을 만족하는지 수치적으로 판정

### 그림 2 프롬프트 — 전체 학습ㆍ평가 아키텍처

> 학술 논문용 파이프라인 그림. 왼쪽에서 “scene image”, “Requirement CoC”, “Execution Guard” 세 입력이 Qwen3-VL-2B-Instruct + LoRA 블록으로 들어간다. 모델은 A/B/C/D trajectory candidate를 선택한다. 아래에는 독립 verifier가 candidate의 stop offset, speed, deceleration, jerk, minimum gap, entry time을 검사한다. 오른쪽에는 네 지표 Guard Violation, Safe Goal Completion, Deadlock, Contract-Swap Pair Accuracy가 출력된다. 학습 branch에는 correct contract-target pairing과 shuffled control을 나란히 보여준다. 자연어 가드는 파란색, 정량 verifier는 짙은 회색, admissible trajectory는 녹색, violation은 빨간색. 깔끔한 벡터 스타일, 가로형.

### 그림 3 프롬프트 — Paired-contract 예

> 두 행으로 구성된 논문용 비교 도식. 두 행은 완전히 동일한 차선 변경 장면과 동일한 네 후보를 가진다. 첫 행의 permissive contract는 minimum gap ≥ 5.5 m이고 early continue 후보가 선택된다. 둘째 행의 restrictive contract는 minimum gap ≥ 9.0 m이고 abort-then-retry 후보가 선택된다. 바뀐 것은 contract threshold뿐임을 중앙의 세로 점선과 “same scene / same candidates” 표기로 강조한다. Requirement-only 모델은 두 행에 같은 답을 내고, Safety-Constrained CoC 모델은 올바르게 답을 전환하는 모습을 오른쪽에 표시한다.

---

## 5. 실험 설계

### 5.1 E0: Alpamayo-R1 zero-shot responsiveness 진단

- 목적: 학습하지 않은 가드를 CoC에 삽입하는 것만으로 의미별 trajectory 제어가 가능한지 확인
- 조건: 기본 CoC, hold Guard, 반대 의미 Guard, 무관 문장
- 위치: 주 실험이 아니라 문제 동기와 학습 필요성을 설명하는 진단

### 5.2 E1: Guard-to-action prototype

- STOP/PROCEED prototype을 사용하는 최소 학습 가능성 검사
- correct Guard pair와 shuffled pair 비교
- 이 실험의 한계까지 함께 보고하여 후속 hard-negative 설계의 필요성을 설명

### 5.3 E2: 정적 goal-compliant 후보 선택

- 모든 후보가 CoC 목표를 완료
- 속도, 최소거리 또는 진입시간 가드만 다름
- requirement-only, inline, separate NL, shuffled, logic 비교

### 5.4 E3: STOP–HOLD–RELEASE–GO 시간적 계약

- clear 후 1초/3초 대기와 같이 동일 장면에서 release 시간이 바뀌는 계약
- seed 42, 17, 123
- 시간적 계약 전환과 deadlock을 함께 평가

### 5.5 E4: 다중 maneuver

- `CRUISE → STOP`: 정지선, 최대 감속도, jerk
- `LANE CHANGE → COMPLETE/ABORT`: 최소 gap, abort 후 retry
- seed 42, 17, 123

### 5.6 E5: Hard generalization

- 허용 경계와 정확히 같은 값
- 부정ㆍ금지형 표현
- 조건 순서 변경
- m ↔ cm 단위 변환
- 표준 test와 분리된 48개 장면, 96개 예/seed

### 5.7 E6: 폐루프 보조 micro-world

- 작은 2-layer MLP와 1D 운동학 환경을 사용한 메커니즘 검사
- A: 상태, B: 상태+행동 CoC, C: 컴파일된 동적 계약, D: runtime shield
- 이 실험은 VLM 주 결과의 직접 검증이 아니라 다음 두 한계를 보이는 보조 실험으로 사용한다.
  - 충분한 phase-complete 성공 시연은 누락된 제약 일부를 암묵적으로 학습할 수 있음
  - 미관측 release reversal과 stale 계약에서는 명시적 계약과 shield도 완전하지 않음

### 5.8 재현 설정

- 모든 주 실험의 seed, 장면 수, 예제 수, epoch, batch, learning rate 명시
- seed별 원시 결과와 집계 스크립트 공개
- 단일 seed pilot 결과는 방법 개발 과정으로만 사용하고, 3-seed 결과가 있는 실험은 3-seed 표를 본문에 사용

### 그림 4 프롬프트 — 실험 suite

> 4열 학술 인포그래픽. 열 1은 static candidate selection으로 speed/gap이 다른 네 trajectory, 열 2는 STOP-HOLD-RELEASE-GO 타임라인, 열 3은 CRUISE-to-STOP 장면, 열 4는 LANE-CHANGE-to-ABORT/RETRY 장면. 각 열 아래에 해당 guard type을 짧게 표기: bound, temporal release, stopline/deceleration/jerk, minimum gap/fallback. 상단에는 동일한 Safety-Constrained CoC 학습 프레임워크가 네 과제를 연결하는 가로 화살표. 흰 배경, 논문용 벡터, 색상 범례 일관성 유지.

---

## 6. 실험 결과 및 해석

### 6.1 R1 zero-shot 진단: 문장 반응과 의미 준수는 다르다

핵심 결과:

- 기본 CoC 대비 문장 추가에 따른 2초 trajectory 변화: 약 `+0.263 m`
- hold Guard와 반대 의미 Guard 사이 차이: 약 `0.008 m`
- 판정: `WEAK_DIRECTIONAL_NOT_SEMANTICALLY_SPECIFIC`

설명:

- R1 trajectory는 CoC에 문장을 추가하면 변하므로 CoC가 trajectory 생성과 무관하다고 볼 수는 없다.
- 그러나 반대 의미의 Guard 간 차이가 무관한 문장 삽입 효과와 분리될 만큼 크지 않았다.
- 따라서 “가드를 prompt에 넣으면 R1이 즉시 준수한다”는 주장은 지지되지 않으며, 가드 의미에 맞는 학습이 필요하다.

논문 배치:

- 작은 표 또는 Figure 5의 왼쪽 패널
- 전체 restricted 데이터나 모델 출력 전문은 공개하지 않고 집계 수치와 절차만 제시

### 6.2 최소 Guard 학습: 학습 가능하지만 표현 일반화는 아직 약하다

| 지표 | 올바른 Guard pair | Shuffled Guard |
|---|---:|---:|
| Held-out 정확도 | 0.990 | 0.719 |
| Counterfactual pair 완전 정답률 | 0.958 | 0.000 |
| Paraphrase 정확도 | 0.740 | 0.745 |
| Paraphrase pair | 0.000 | 0.000 |

설명:

- 동일 장면에서 Guard가 바뀔 때 행동을 바꾸는 관계는 작은 VLM이 학습할 수 있었다.
- 하지만 paraphrase pair가 두 조건 모두 0이므로 이 단계만으로 의미 일반화를 주장할 수 없다.
- 이 실패가 이후 inline 표현, hard negative 및 paired-contract benchmark를 설계한 이유다.

### 6.3 단순 CoC와 CoC+Guard 비교만으로는 충분하지 않다

충분한 학습량에서는 두 조건 모두 쉬운 STOP/PROCEED 과제를 해결했다.

| 조건, 192 scenes | Held-out 정확도 | Counterfactual pair | Paraphrase 정확도 |
|---|---:|---:|---:|
| Traditional CoC | 0.974 | 0.896 | 0.906 |
| CoC + Guard | 1.000 | 1.000 | 0.984 |

Equal-step 사후 진단에서는 두 조건 모두 held-out와 pair가 `1.000`이었다.

설명:

- 장면 정보만으로 정답이 식별되는 쉬운 과제에서는 충분한 데이터가 CoC에 빠진 제약을 암묵적으로 보정할 수 있다.
- 따라서 논문의 핵심 증거는 단순 행동 분류가 아니라 **같은 목표를 달성하지만 가드 준수 여부가 다른 후보**에서 나와야 한다.
- 이 음성 결과를 숨기지 않고 benchmark 설계의 construct validity 근거로 사용한다.

### 6.4 정적 goal-compliant hard negative 결과

| 조건 | 정확도 | 위반 후보 선택 ↓ | 과도한 보수 선택 ↓ | 계약 pair ↑ | 목표 완료 |
|---|---:|---:|---:|---:|---:|
| Requirement-only CoC | 0.500 | 0.500 | 0.500 | 0.000 | 1.000 |
| Constraint inside CoC | **1.000** | **0.000** | **0.000** | **1.000** | 1.000 |
| Separate natural-language Guard | 0.993 | 0.014 | 0.000 | 0.986 | 1.000 |
| Shuffled Guard | 0.465 | 0.375 | 0.694 | 0.153 | 1.000 |
| Logic Guard | **1.000** | **0.000** | **0.000** | **1.000** | 1.000 |

표현ㆍ수치 일반화:

| 조건 | Paraphrase 정확도 | Paraphrase pair | Unseen-value 정확도 | Unseen-value pair |
|---|---:|---:|---:|---:|
| Requirement-only CoC | 0.500 | 0.000 | 0.500 | 0.000 |
| Constraint inside CoC | 0.875 | 0.750 | **1.000** | **1.000** |
| Separate NL Guard | **0.924** | **0.847** | 0.951 | 0.903 |
| Shuffled Guard | 0.549 | 0.125 | 0.507 | 0.208 |
| Logic Guard | **1.000** | **1.000** | 0.924 | 0.847 |

설명:

- 모든 조건의 목표 완료가 1.0이므로 위반 감소는 목표 포기나 always-stop으로 설명되지 않는다.
- requirement-only는 동일 장면의 두 계약을 구별할 정보가 없어 pair 정확도 0이었다.
- shuffled 통제보다 올바른 제약 조건이 크게 우수하므로 단순한 추가 토큰 효과와도 맞지 않는다.
- 이 실험은 제안의 가장 직접적인 construct-validity 결과다.

### 6.5 STOP–HOLD–RELEASE–GO 3-seed 결과

| 조건 | 정확도 | Guard 위반 ↓ | Deadlock ↓ | 안전+목표 완료 ↑ | 계약 pair ↑ |
|---|---:|---:|---:|---:|---:|
| Requirement CoC | 0.500 ± 0.000 | 0.319 ± 0.052 | 0.000 ± 0.000 | 0.681 ± 0.052 | 0.000 ± 0.000 |
| Inline NL constraint | **1.000 ± 0.000** | **0.000 ± 0.000** | 0.000 ± 0.000 | **1.000 ± 0.000** | **1.000 ± 0.000** |
| Separate NL Guard | 0.698 ± 0.094 | 0.191 ± 0.136 | 0.000 ± 0.000 | 0.809 ± 0.136 | 0.396 ± 0.187 |
| Shuffled Guard | 0.510 ± 0.015 | 0.333 ± 0.023 | 0.000 ± 0.000 | 0.667 ± 0.023 | 0.021 ± 0.029 |
| Logic Guard | 0.538 ± 0.027 | 0.274 ± 0.108 | 0.000 ± 0.000 | 0.726 ± 0.108 | 0.076 ± 0.055 |

설명:

- Inline 자연어 제약은 세 seed 모두에서 계약 전환을 완전히 학습했다.
- Separate NL Guard는 requirement-only와 shuffled보다 평균적으로 나았지만 seed 변동이 컸다.
- Logic Guard가 낮은 것은 논리 명세 자체가 열등해서가 아니라, 기반 모델과 현재 objective가 임의 논리 문법 실행에 충분히 적응하지 않았기 때문일 수 있다.
- 따라서 논문 1에서는 inline 표현을 대표 제안으로 사용하고, 자연어 대 정형 명세의 공정한 비교는 별도 연구로 남긴다.

### 6.6 다중 maneuver 3-seed 결과

| 조건 | 정확도 | Guard 위반 ↓ | 안전+목표 완료 ↑ | 계약 pair ↑ |
|---|---:|---:|---:|---:|
| Requirement CoC | 0.500 ± 0.000 | 0.292 ± 0.072 | 0.708 ± 0.072 | 0.000 ± 0.000 |
| Safety-Constrained CoC | **1.000 ± 0.000** | **0.000 ± 0.000** | **1.000 ± 0.000** | **1.000 ± 0.000** |
| Shuffled constraint | 0.503 ± 0.006 | 0.267 ± 0.039 | 0.733 ± 0.039 | 0.028 ± 0.032 |

Maneuver별 설명:

- `CRUISE→STOP`: 정지선, 최대 감속도 및 jerk의 permissive/restrictive 계약을 모두 구별했다.
- `LANE CHANGE→ABORT/RETRY`: 최소 gap이 닫힐 때 계속 변경할지 abort 후 재시도할지를 올바르게 전환했다.
- 두 maneuver 모두 inline 조건의 위반 0, 안전한 목표 완료 1.0, pair 1.0이었다.
- 따라서 시간적 정지 문제 하나에만 특화된 결과는 아니다.

통계 대비 효과:

- Requirement 대비 평균 위반 감소: `0.292`, seed-cluster bootstrap 95% CI `[0.250, 0.375]`
- Shuffled 대비 평균 pair 증가: `0.972`, 95% CI `[0.938, 1.000]`
- seed가 3개뿐이므로 이 CI는 탐색적으로 해석한다.

### 6.7 Hard generalization 결과

| 조건 | 정확도 | Guard 위반 ↓ | 안전+목표 완료 ↑ | 계약 pair ↑ |
|---|---:|---:|---:|---:|
| Requirement CoC | 0.500 ± 0.000 | 0.302 ± 0.065 | 0.698 ± 0.065 | 0.000 ± 0.000 |
| Safety-Constrained CoC | **0.948 ± 0.063** | **0.010 ± 0.010** | **0.990 ± 0.010** | **0.896 ± 0.127** |
| Shuffled constraint | 0.535 ± 0.079 | 0.260 ± 0.018 | 0.740 ± 0.018 | 0.090 ± 0.139 |

실패 분석:

- Safety-Constrained CoC의 총 오답 15개는 모두 `m ↔ cm` 단위 변환 문장에 있었다.
- seed 42의 12개는 가드를 위반하지 않았지만 progress가 낮은 보수적 lane-change 후보 선택이었다.
- seed 17과 123의 3개는 cruise-stop의 감속도ㆍjerk 상한을 실제로 위반했다.
- 이번 결합 hard test에서 부정 scope, 절 순서 변경 및 m 단위 경계 equality만 포함한 예는 오답이 없었다.
- 그러나 factorial 설계가 아니므로 단위 변환만을 유일한 인과 요인으로 단정하지 않는다.

해석:

- 자연어 가드 학습은 표현 변화에도 상당 부분 유지되지만 정밀 단위 변환까지 VLM에 맡기면 취약성이 남는다.
- 실제 시스템에서는 자연어에서 `type/operator/value/unit`을 추출한 뒤 단위를 정규화하고, 경계 판정은 deterministic verifier가 수행하는 구조가 타당하다.
- 이 결과는 논문의 한계를 숨기지 않으면서 후속 typed-contract 아키텍처를 정당화한다.

### 그림 5 프롬프트 — 핵심 결과 패널

> 3개 패널로 구성된 논문용 결과 그림. 패널 A는 R1에서 base CoC 대비 문장 추가 trajectory 변화 0.263m와 hold-versus-opposite 차이 0.008m를 비교하는 막대 그래프. 패널 B는 시간적 3-seed 실험의 Requirement, Inline NL, Separate NL, Shuffled, Logic 조건별 Guard violation과 Safe Goal Completion을 나란히 표시한 grouped bar chart이며 error bar를 포함한다. 패널 C는 다중 maneuver standard와 hard test에서 Requirement, Safety-Constrained, Shuffled의 contract-pair accuracy를 비교한다. 안전 성능은 녹색, 위반은 빨간색, 통제군은 회색, 색맹 친화 팔레트, 과도한 3D 효과 없이 저널용 벡터 그래프.

### 6.8 폐루프 보조 실험: 성공 시연, 계약 및 shield의 역할

### Phase-complete bank

- post-stop HOLD transition이 0건이던 데이터에 1,404건을 추가하자 A/B/C/C2 모두 STOP 조기 진입 `0/300`이 됐다.
- 전체 OOD에서 A unsafe 2.6%, B 1.4%, C 0%, C2 0%, D 0%였다.
- 이미 해결된 bank에서는 shield가 추가 안전 이득 없이 episode당 2.539회 개입하고 progress를 약 0.078m 감소시켰다.

설명:

- CoC에 제약이 명시되지 않아도 충분한 상태와 phase-complete 성공 시연이 있으면 학습이 일부 제약을 암묵적으로 보정할 수 있다.
- 따라서 “명시적 계약을 추가하면 언제나 더 안전하다”는 주장은 부적절하다.

### Unseen release-reversal stress bank

| 조건 | Unsafe ↓ | Collision ↓ | Completion | Progress |
|---|---:|---:|---:|---:|
| A 상태 | 46.6% | 26.6% | 100% | 25.026m |
| B 상태+CoC | 48.6% | 27.3% | 100% | 25.064m |
| C 동적 계약 | **21.4%** | **14.3%** | 100% | 25.055m |
| C2 단조 phase | 37.9% | 25.9% | 100% | 25.026m |
| D 현재상태 shield | **4.8%** | **1.8%** | 100% | 25.025m |
| D oracle 1.2s | **0%** | **0%** | 100% | 24.897m |
| C stale 0.4s | 48.1% | 24.8% | 100% | 25.020m |
| D stale 0.4s | 34.8% | 16.3% | 100% | 25.057m |

설명:

- phase-complete 학습으로 해결된 평가 bank도 `RELEASED→HOLD`, 위험 재등장 및 재-occlusion에서는 다시 실패했다.
- 동적 계약 C는 A/B보다 크게 나았지만 완전하지 않았다.
- 단조 phase C2는 release 취소를 표현하지 못해 C보다 악화됐다.
- 현재 상태 shield도 미래 재진입을 알 수 없어 4.8% 잔여 위반이 있었고, 비현실적인 1.2초 oracle만 0%를 달성했다.
- 계약 정보를 0.4초 늦추면 C는 21.4%에서 48.1%, D는 4.8%에서 34.8%로 악화됐다. 계약의 내용뿐 아니라 갱신 시점도 중요하다.

논문 내 역할:

- 본문에서는 한 개의 압축 표와 핵심 해석만 제시한다.
- 상세 paired episode와 oracle/stale 분석은 부록으로 이동한다.
- 이 결과를 작은 VLM 후보 선택 결과와 직접적인 수치 비교로 사용하지 않는다.

### 그림 6 프롬프트 — 폐루프 release-reversal 메커니즘

> 시간축 기반 자율주행 안전 개념도. t0에서 conflict zone clear로 provisional release, t0+0.6s에서 ego 진입 시작, t0+0.8s에서 보행자 또는 교차 차량 재등장. 위쪽에는 monotonic phase APPROACH→HOLD→RELEASED가 위험 재등장을 처리하지 못하는 모습을 빨간 경고로 표시한다. 아래쪽에는 revocable contract가 RELEASED에서 HOLD로 되돌아가고 runtime shield가 제동하는 모습을 그린다. 오른쪽에 current-state shield는 미래 재등장을 놓칠 수 있고 predictive occupancy가 필요하다는 작은 inset을 둔다. 논문용 간결한 벡터 타임라인.

### 6.9 결과 종합

본문에서 다음 순서로 결론을 연결한다.

1. R1 zero-shot 문장 삽입은 trajectory를 바꾸지만 Guard 의미 준수는 확립되지 않았다.
2. 작은 VLM은 올바른 감독 신호가 있으면 Guard–행동 대응을 학습할 수 있다.
3. 쉬운 행동 분류에서는 일반 학습도 제약을 보정하므로 goal-compliant hard negative가 필요하다.
4. 정적, 시간적 및 다중 maneuver 실험에서 inline Safety-Constrained CoC가 requirement-only와 shuffled 통제보다 일관되게 우수했다.
5. 위반 감소는 deadlock이나 목표 포기에 의한 것이 아니었다.
6. 단위 변환, 미관측 release reversal 및 stale 계약은 학습된 Guard가 안전 보장과 동일하지 않음을 보여준다.

---

## 7. 논의

### 7.1 CoC와 안전 계약의 관계

- CoC는 trajectory를 생성하거나 선택하기 위한 행동 근거와 목표를 제공한다.
- Safety-Constrained CoC는 그 목표를 달성하는 동안 지켜야 할 부분 계약을 추가한다.
- 이는 CoC 전체가 잘못됐다는 주장이 아니라 CoC의 기능을 확장하는 제안이다.

### 7.2 왜 inline 자연어가 현재 가장 강했는가

- 기반 VLM의 사전학습 표현과 가장 가깝다.
- requirement와 constraint의 attention/학습 경로가 분리되지 않는다.
- separate/logic 표현은 추가적인 format adaptation이 필요했을 가능성이 있다.
- 현재 결과만으로 자연어가 정형 명세보다 본질적으로 우수하다고 결론 내리지 않는다.

### 7.3 경계값은 어디에서 처리해야 하는가

```text
Natural-language Safety-Constrained CoC
  -> typed guard compiler: type/operator/value/unit/fallback
  -> unit normalization
  -> deterministic trajectory verifier or runtime shield
```

- 자연어에서 `미만/이하`, 대상, 단위 및 fallback을 추출하는 것은 언어–명세 인터페이스 문제다.
- 실제 `<`, `≤`, 거리, 속도 및 jerk 판정은 제어ㆍ검증 계층에 배치하는 것이 타당하다.
- hard-test의 cm 오류는 이 역할 분리의 필요성을 보여준다.

### 7.4 학습과 runtime enforcement

- 학습은 일반적인 가드 준수 후보의 likelihood를 높인다.
- runtime verifier는 명시된 계약의 최종 준수를 검사한다.
- shield는 잔여 위반을 줄이지만 불필요한 개입과 progress/comfort 비용을 만들 수 있다.
- 미래 의존 hazard에는 현재 상태 invariant만이 아니라 predictive uncertainty가 필요하다.

### 7.5 활용 범위

- 데이터 생성 또는 학습 supervision: requirement와 constraint를 함께 제공
- trajectory 후보 ranking: admissible 후보 중 목표 효용 최대화
- 실행 전 검증: typed contract와 independent verifier

---

## 8. 타당성 위협

### 8.1 Construct validity

- 주 실험은 연속 trajectory 생성이 아니라 서술된 후보 선택이다.
- 합성 후보의 물리량과 verifier가 hand-designed다.
- pair accuracy와 safe goal completion으로 단순 장면 shortcut과 always-stop을 일부 통제하지만 실제 운전 안전을 대체하지 않는다.

### 8.2 Internal validity

- candidate label 위치를 회전하여 정답 위치 shortcut을 줄였다.
- shuffled contract로 추가 텍스트 효과를 통제했다.
- 세 seed를 사용했지만 더 많은 seed와 독립 구현 재현이 필요하다.
- hard test는 여러 표현 요인을 결합했으므로 각 요인의 인과 효과를 분리하지 못한다.

### 8.3 External validity

- 작은 Qwen VLM과 합성 이미지 결과가 Alpamayo-R1의 실제 연속 trajectory로 그대로 전이된다고 볼 수 없다.
- R1 분석은 zero-shot responsiveness 진단일 뿐 학습 후 개선 실험이 아니다.
- 실제 센서 grounding, VRU geometry 및 collision risk는 별도 평가가 필요하다.

### 8.4 Specification validity

- 제안 가드는 부분 계약이며 완전한 도로 안전 명세가 아니다.
- 잘못되거나 stale한 가드는 이득을 제거할 수 있다.
- 실제 시스템에서는 독립 oracle, timestamp alignment 및 불확실성 처리가 필요하다.

---

## 9. 결론 아웃라인

- Requirement-only CoC는 행동 목표를 표현하지만 동일 목표를 달성하는 후보의 허용 경계를 항상 식별하지 않는다.
- Safety-Constrained CoC와 올바른 감독 신호는 정적, 시간적 및 다중 maneuver 합성 과제에서 목표 완료를 유지하면서 가드 위반 선택을 크게 줄였다.
- 이 효과는 세 seed와 shuffled 통제에서 재현됐다.
- hard test와 폐루프 stress 결과는 학습된 자연어 가드가 안전 보장과 같지 않음을 보여준다.
- 향후에는 자연어 Guard를 typed contract로 컴파일하고 독립 trajectory verifier와 결합하여 실제 trajectory에서 외적 타당성을 평가해야 한다.

---

## 10. 본문 표ㆍ그림 배치 권장안

### 본문 그림

1. Figure 1: Requirement-only CoC와 Safety-Constrained CoC 개념 비교
2. Figure 2: VLM 학습ㆍ후보 선택ㆍ독립 verifier 아키텍처
3. Figure 3: 동일 장면 paired-contract 예
4. Figure 4: 정적ㆍ시간적ㆍ다중 maneuver 실험 suite
5. Figure 5: R1 진단, 시간적 및 다중 maneuver 핵심 결과
6. Figure 6: 선택 사항 — release-reversal과 revocable contract

### 본문 표

1. Table 1: Guard taxonomy
2. Table 2: 실험 조건과 지표
3. Table 3: 정적 goal-compliant hard-negative 결과
4. Table 4: 시간적 Guard 3-seed 결과
5. Table 5: 다중 maneuver standard/hard 결과
6. Table 6: 선택 사항 — 폐루프 release-reversal 압축 결과

### 부록 또는 보충자료

- Guard-to-action pilot와 equal-step 진단의 전체 표
- seed별 원시 결과
- paraphrase/unseen-value 세부 표
- hard-test 오답 15개 목록
- 폐루프 paired episode, stale/oracle 전체 표
- prompt template, 학습 hyperparameter, verifier 정의

---

## 11. 논문에서 제외하거나 축약할 내용

- 초기 blind grounding 14개 장면이 모두 지지된 결과는 본문 핵심 결과로 사용하지 않는다. 이는 오류 검출 연구가 어려웠다는 배경으로 한 문장만 언급한다.
- 단일 STOP/YIELD 문구와 순간 속도 증가를 unsafe violation으로 확정하지 않는다. temporal phase가 없으면 오판 가능하다는 교훈만 남긴다.
- 사고 사례를 발견했다는 표현을 사용하지 않는다.
- 같은 실험의 seed-42 표와 3-seed 표를 중복 제시하지 않는다.
- Logic Guard의 낮은 결과를 정형 명세의 열등성으로 해석하지 않는다.
- Oracle shield의 0%를 배포 가능한 안전 보장으로 표현하지 않는다.

---

## 12. 결과 출처와 재현 파일

- 종합 진행 보고서: `docs/reports/SAFETY_CONSTRAINED_COC_PROGRESS_REPORT_V01.md`
- R1 결과: `artifacts/results/restricted/alp-exp-005/`
- 최소 Guard 학습: `artifacts/results/public/small-vlm-guard-v0/pilot-summary-seed42-v3/`
- 전통 CoC 대 Guard: `artifacts/results/public/small-vlm-guard-v0/coc-vs-guard-summary-seed42-v2/`
- 정적 후보: `artifacts/results/public/small-vlm-guard-v0/candidate-guard-summary-seed42-v0/`
- 시간적 3-seed: `artifacts/results/public/small-vlm-guard-v0/temporal-guard-multiseed-v0/`
- 다중 maneuver 3-seed/hard: `artifacts/results/public/small-vlm-guard-v0/maneuver-guard-multiseed-v0/`
- Phase-complete 폐루프: `artifacts/results/public/contract-microworld-v1/pilot-phase-complete-isolated-2026-08-04-v2/`
- Release-reversal stress: `artifacts/results/public/contract-microworld-v2/pilot-release-reversal-2026-08-04-v1/`

## 13. 집필 우선순위

1. Figure 1과 Figure 3을 먼저 만들어 문제 정의를 고정한다.
2. 3절 문제 정의와 5절 실험 설계를 작성한다.
3. 6.4–6.7의 주 결과를 표와 함께 먼저 완성한다.
4. 서론과 관련 연구를 주 결과에 맞춰 작성한다.
5. R1과 폐루프 실험은 본문 분량에 따라 진단/보조 결과로 축약한다.
6. 마지막으로 타당성 위협과 주장 한계를 점검한다.
