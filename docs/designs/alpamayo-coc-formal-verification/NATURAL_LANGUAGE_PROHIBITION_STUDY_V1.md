# 자연어 금지 제약이 trajectory safety compliance에 미치는 영향: 연구 질문 및 최소 실험 v1

- 기준일: 2026-08-04
- 상태: 선행연구 검토 후 고정한 1차 feasibility 질문
- 주 대상: Alpamayo-R1-10B의 CoC-conditioned trajectory
- 주의: 이 문서에서 `compliance`는 명시한 장면별 계약의 만족을 뜻하며, 전체 자율주행 안전 보장을 뜻하지 않는다.

## 1. 고정할 연구 질문

> 동일한 장면과 요구사항 중심 CoC가 주어졌을 때, 그 CoC에 장면에 맞는 **명시적 자연어 금지 제약**을 추가하면 요구사항 중심 CoC만 사용할 때보다 trajectory의 안전 계약 준수율이 향상되는가? 그리고 그 향상이 진행성 및 승차감의 과도한 손실 없이 나타나는가?

조작 변수를 더 정확히 쓰면 다음과 같다.

```text
B-REQ:    원래/요구사항 중심 CoC
C-NEG:    B-REQ + 명시적 금지 문장 1개

고정:     영상, ego history, scene state, 모델 가중치, trajectory noise seed
측정:     계약 위반, 안전 여유, 진행성, trajectory 변화량
```

이 질문은 다음을 주장하지 않는다.

- 원래 CoC가 unsafe trajectory를 항상 만든다는 주장
- 자연어 금지 문장이 형식 안전 보장을 제공한다는 주장
- collision이 없으면 계약을 만족했다는 주장
- 금지 제약을 많이 추가할수록 항상 안전하다는 주장

## 2. 선행연구와 정확한 차이

### 2.1 가장 가까운 연구: Causal Scene Narration(CSN)

CSN은 `Turn left`와 `Pedestrian ahead`를 분리해서 주는 대신, `Turn left, BUT yield ... BEFORE executing turn`처럼 intent와 constraint를 자연어 접속사로 연결한다. LMDrive의 폐루프 CARLA 실험에서 원래 모델 대비 Driving Score가 31.1% 향상되었고, 동일 사실을 연결 없이 제공한 Flat Text와의 비교에서 causal structure가 전체 향상의 39.1%를 설명했다고 보고한다.

그러나 우리의 질문과는 다음이 다르다.

- CSN은 정보 추가, 정량 grounding, 구조 분리, intent-constraint 연결을 묶어서 적용한다.
- Flat Text 대 CSN 비교는 연결 구조의 효과를 보지만, `하지 말라`는 명시적 금지 문장의 독립 효과를 분리하지 않는다.
- 예시는 `yield`, `maintain distance`, `before` 같은 요구/순서 표현이며, `conflict zone이 비기 전에는 진입하지 말라`와 같은 금지 경계를 직접 대조하지 않는다.
- 주 지표는 Driving Score, Route Completion, Infraction Score이며, 문장에 명시된 계약별 trajectory compliance가 아니다.

따라서 단순히 “자연어 constraint가 유용하다”라고 주장하면 CSN과 크게 겹친다. 신규성은 **요구사항은 그대로 둔 채 명시적 금지 경계만 추가하고, 그 경계의 trajectory 준수 효과와 실패 조건을 직접 측정하는 것**에 둔다.

참고: https://arxiv.org/abs/2604.01723

### 2.2 VLADriveBench

VLADriveBench는 Alpamayo의 self-generated CoT/CoC를 통제된 문장으로 교체하고, 나머지 입력과 난수를 고정하여 trajectory 변화를 측정한다. Alpamayo에서는 CoC token을 다시 forward해 KV cache를 만들고 action head가 그 cache에 condition되도록 한다. Alpamayo R1에서도 가속/보행자/차량 문장 주입이 통계적으로 유의한 방향성 효과를 보였다고 보고한다.

그러나 다음 질문은 다루지 않는다.

- 원래 CoC를 통째로 교체하는 대신 원래 요구사항 CoC에 prohibition만 추가하는가?
- 동일한 안전 의미에서 positive requirement와 explicit prohibition을 비교하는가?
- 주입된 금지 문장에 명시된 동적 계약을 실제 trajectory가 만족하는가?
- 금지 문장이 stale, wrong, ambiguous할 때 언제 역효과가 나는가?

우리의 최소 실험은 VLADriveBench의 검증된 **CoC splice 방법**을 채택하되, intervention과 평가 대상을 위 네 항목으로 좁힌다.

참고: https://arxiv.org/abs/2606.12706

### 2.3 C-CoT, SafeAlign-VLA, Beyond Imitation

- C-CoT는 대안 행동의 결과를 미리 평가하는 counterfactual reasoning과 안전 trajectory를 함께 학습한다.
- SafeAlign-VLA는 위험 trajectory와 counterfactual safe trajectory의 쌍을 만들어 negative-enhanced SFT/RL을 수행한다.
- Beyond Imitation은 expert와 기하학적으로 가깝지만 unsafe인 hard-negative trajectory로 trajectory space의 안전 경계를 학습한다.

이 연구들은 `무엇을 피해야 하는가`를 학습에 넣는다는 상위 동기는 공유하지만, **동일 CoC에 자연어 prohibition만 추가하는 입력/중간표현 intervention**은 아니다.

참고:

- https://arxiv.org/abs/2605.10744
- https://arxiv.org/abs/2605.19524
- https://arxiv.org/abs/2605.19771

### 2.4 ICR-Drive가 주는 방법론적 경고

ICR-Drive는 동일 CARLA route와 seed에서 instruction wording만 바꾸어도 LMDrive와 BEVDriver의 폐루프 성능이 크게 달라질 수 있음을 보인다. 따라서 C-NEG의 향상을 곧바로 금지 의미의 효과라고 해석하면 안 된다. 문장 길이, 단어 선택, 위치 및 attention 변화가 원인일 수 있다.

참고: https://arxiv.org/abs/2604.05378

## 3. 최소 실험 조건

### 3.1 1차 필수 조건

| ID | CoC intervention | 목적 |
|---|---|---|
| `B-REQ` | native CoC를 그대로 self-splice | 요구사항 중심 기준선 및 injection artifact 점검 |
| `C-NEG` | native CoC 뒤에 장면에 맞는 금지 문장 추가 | 주 가설 검정 |
| `P-LEN` | 같은 token 길이의 의미 없는/비행동 문장 추가 | 길이와 cache 위치 효과 통제 |
| `P-SHUFFLE` | C-NEG의 추가 문장 단어를 섞어 의미 파괴 | 금지 의미가 아닌 token 통계 효과 통제 |

`B-REQ`와 native generation의 trajectory가 pinned seed에서 일치하지 않으면 intervention pipeline을 먼저 수정하고 본 실험을 중단한다.

### 3.2 의미 형식 ablation

1차 결과가 유의할 때 다음 조건을 추가한다.

| ID | 예시 | 분리되는 요인 |
|---|---|---|
| `C-POS` | `Enter the conflict zone only after it is clear.` | 같은 경계를 긍정 조건으로 표현 |
| `C-NEG` | `Do not enter the conflict zone while it may be occupied.` | 명시적 부정 표현 |
| `C-DUAL` | 긍정 조건 + 금지 문장 | 요구와 금지의 중복 명시 |
| `C-WRONG` | 장면과 맞지 않거나 반대인 제약 | blind compliance 및 안전한 무시 능력 |

이 ablation이 있어야 `안전 경계 정보`의 효과와 `부정문 형식` 자체의 효과를 분리할 수 있다.

## 4. 문장 쌍 예시

### 4.1 횡단 보행자

```text
B-REQ:
Yield to the pedestrian crossing ahead.

C-NEG 추가:
Do not enter the pedestrian's reachable conflict zone while the pedestrian
is crossing or its clearance is uncertain.

C-POS 추가:
Enter the conflict zone only after the pedestrian has cleared it with a safe margin.
```

### 4.2 STOP 교차로

```text
B-REQ:
Stop at the stop line and yield to cross traffic.

C-NEG 추가:
Do not cross the stop line before a complete stop, and do not enter the
intersection while cross traffic can still occupy the conflict zone.
```

### 4.3 선행차 감속

```text
B-REQ:
Decelerate for the slowing lead vehicle.

C-NEG 추가:
Do not follow so closely that the predicted stopping envelopes overlap.
```

초기 실험에서는 한 CoC에 prohibition을 하나만 추가한다. `hold`, `release`, uncertainty fallback을 한꺼번에 추가하면 무엇이 효과를 냈는지 알 수 없다.

## 5. Trajectory safety compliance 정의

주 지표는 collision 유무가 아니라 문장에 의해 명시된 계약의 trajectory-level 위반이다.

| 장면 | 계약 위반 예 | 연속값 robustness 예 |
|---|---|---|
| 횡단보도 | 보행자 reachable occupancy와 ego footprint가 conflict zone에서 시간적으로 겹침 | 최소 predicted separation 또는 time gap |
| STOP | 완전 정지 전 stop line 통과, 또는 cross traffic clearance 전 진입 | stop-line 여유, 최소 속도, conflict-zone time gap |
| 선행차 | stopping envelope 중첩 또는 설정 TTC/거리 아래 진입 | 최소 headway/TTC margin |
| 차선변경 | 수용 가능한 gap 형성 전 target lane 진입 | 전후방 time-gap margin |

반드시 함께 보고할 지표는 다음과 같다.

- 계약 위반률과 scene-level paired difference
- minimum robustness와 하위 분위수/CVaR
- 충돌 proxy 또는 collision
- horizon progress와 route completion
- 과도 정지 시간, 가속도/jerk
- native trajectory 대비 displacement

안전 위반이 줄어도 차량이 항상 멈춘다면 가설을 지지하지 않는 것으로 판정한다.

## 6. 실제 Alpamayo에서 가능한 이유

공개 Alpamayo-R1 코드는 다음 순서로 동작한다.

1. VLM이 `<|cot_start|>` 이후 CoC를 autoregressive하게 생성한다.
2. `<|traj_future_start|>`까지의 CoC/vision KV cache를 보존한다.
3. diffusion action head가 그 KV cache를 사용해 trajectory를 생성한다.

따라서 모델을 재학습하지 않고도 native CoC token을 `native + prohibition` token으로 바꾸어 동일 vision, ego history, action noise에서 trajectory의 paired causal effect를 측정할 수 있다. 이는 현재 MLP micro-world의 structured contract 입력과 달리, 실제 자연어 CoC의 효과를 직접 묻는 실험이다.

## 7. 현실적인 실행 순서와 go/no-go 기준

### Stage 0: intervention correctness

- 3개 장면, 3개 trajectory seed
- native generation과 `B-REQ self-splice`가 수치적으로 동일해야 한다.
- 불일치하면 no-go: 주입 코드 artifact를 먼저 해결한다.

### Stage 1: open-loop semantic feasibility

- 우선 20~40개의 명확한 장면을 사용한다.
- 각 장면에서 `B-REQ`, `C-NEG`, `P-LEN`, `P-SHUFFLE`을 같은 seed로 비교한다.
- 장면당 최소 5개 trajectory noise seed를 사용한다.
- 모든 금지 문장은 관측 가능한 하나의 predicate와 하나의 violation metric에 연결한다.

다음을 동시에 만족하면 다음 단계로 진행한다.

1. `C-NEG`가 `B-REQ`보다 violation을 일관되게 줄인다.
2. `C-NEG`가 `P-LEN` 및 `P-SHUFFLE`보다 낫다.
3. progress/comfort 손실이 사전에 정한 허용 범위 안이다.
4. 효과가 특정 한 문장 template이나 한 장면에만 의존하지 않는다.

### Stage 2: 표현 및 오류 내성

- `C-POS`, `C-DUAL`, paraphrase를 추가한다.
- stale/wrong/ambiguous prohibition을 넣어 과도 보수성과 blind following을 측정한다.
- 모델이 prohibition을 지켜야 하는 때와 무시해야 하는 때를 함께 평가한다.

### Stage 3: 공개 폐루프 benchmark

Stage 1~2를 통과한 경우에만 CARLA/LMDrive 계열 또는 재현 가능한 공개 VLA에서 폐루프 실험을 수행한다. NVIDIA 제한 데이터에서 얻은 내부 결과는 go/no-go에만 사용하고, 공개 가능한 주장은 라이선스가 허용되는 benchmark에서 재검증한다.

## 8. 현재 판단

이 연구 질문은 타당하지만, 다음처럼 써야 선행연구와 구분된다.

> 기존 action/requirement CoC가 이미 주어진 상태에서, **동일 의미 내용에 명시적 prohibition boundary를 추가하는 최소 intervention**이 장면별 trajectory contract compliance를 개선하는가? 그 효과는 단순한 text enrichment, causal connective, token length 또는 보수적 정지로 설명되지 않는가?

현재 structured micro-world에서 C가 B보다 나았다는 결과는 이 질문의 mechanism upper bound일 뿐이다. 자연어 CoC 가설의 직접 증거는 위 Alpamayo splice 실험부터 시작한다.
