# CoCShield 초기 서베이 노트

- 기준 연구계획: [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)
- 문서 역할: 초기 대안 탐색과 문제 재정의
- 현재 전략 근거: [GUARDSYNTH_RELATED_WORK_SURVEY_AND_RESEARCH_STRATEGY_V01.md](GUARDSYNTH_RELATED_WORK_SURVEY_AND_RESEARCH_STRATEGY_V01.md)
- 현재 권위 상태: `HISTORICAL`
- 권위 관계: 현재 전략 서베이로 대체된 초기 보조 조사 노트

결론부터 말하면, **1) CoC soundness 평가와 2) 안전 필터를 별도 연구로 나누기보다, “CoC를 신뢰하지 않는 검증 기반 실행 보증”으로 통합하는 방향이 가장 경쟁력 있습니다.**

추천하는 중심 주제는 다음입니다.

> **CoCShield: 의미 모호성을 고려한 CoC 검증, 안전 후보 선택 및 독립적인 물리 안전 보증**

핵심은 CoC가 옳다고 가정하지 않는 것입니다. CoC는 검증할 “주장”이고, 실제 제어 안전은 CoC가 틀리거나 모호해도 독립적으로 유지되어야 합니다.

## 1. 최근 연구 상황을 반영한 냉정한 판단

2026년 들어 우리가 생각한 단순한 연구 주제들은 상당 부분 이미 등장했습니다.

- Alpamayo-R1의 CoC faithfulness를 100개 장면, 300회 추론으로 측정한 연구가 이미 있습니다. 장면 충실도, 보행자 누락, reasoning-action 불일치를 다룹니다. [Is VLA Reasoning Faithful?](https://arxiv.org/abs/2605.17268)
- CoT를 개입하여 실제 trajectory에 영향을 주는지 검사하는 벤치마크도 나왔습니다. [VLADriveBench](https://arxiv.org/abs/2606.12706)
- 반사실적 reasoning으로 unsafe action을 스스로 수정하는 방법도 있습니다. [Counterfactual VLA](https://arxiv.org/abs/2512.24426), [C-CoT](https://arxiv.org/abs/2605.10744)
- CoC를 perception에 grounding하고 trajectory consistency reward로 학습하는 WorkDrive가 2026년 7월 발표되었습니다. [WorkDrive](https://arxiv.org/abs/2607.14727)
- 일반 VLA에 CBF safety layer를 붙이는 연구도 이미 있습니다. [VLSA/AEGIS](https://arxiv.org/abs/2512.11891)
- CoC의 센서 perturbation 안정성은 약 2,000개 장면, 18,000회 추론 규모로 분석되었습니다. [Lost in Fog](https://arxiv.org/abs/2605.21446)
- 객체 제거를 통한 Alpamayo trajectory의 causal influence 분석도 210개 nuScenes 장면에서 수행되었습니다. [Counter-nuScenes](https://arxiv.org/abs/2607.16938)

따라서 다음은 단독 주제로는 약합니다.

- CoC가 맞는지 점수만 매기는 benchmark
- CoC와 trajectory의 방향 일치만 검사
- 노이즈를 넣고 CoC가 바뀌는지 측정
- CBF 필터를 단순히 추가
- LLM에게 “다시 생각해서 고쳐라”라고 요청
- UPPAAL/STL로 몇 개 사례만 모델링

좋은 구성요소이지만, 현재 시점의 top-tier 중심 기여가 되기는 어렵습니다.

## 2. 현재 우리가 가진 자산

현재 프로젝트는 단순 아이디어 단계보다 훨씬 유리합니다.

- NVIDIA PhysicalAI-AV:

  - 306,152개, 각 20초 클립
  - 전체 133TB이므로 전체 다운로드는 불필요하고 현실적으로도 부적절
  - 1,740개 OOD reasoning 클립, 2,077개 human-refined CoC event
  - 298,326개 클립에 offline egomotion·obstacle 가용
  - 공식 데이터 설명: [PhysicalAI Autonomous Vehicles](https://huggingface.co/datasets/nvidia/PhysicalAI-Autonomous-Vehicles)

- CASCADE:

  - 2,066개 장면에 human-reviewed causal graph
  - `because_of`, `influenced_by`, action, agent, traffic control, timestamp가 구조화됨
  - annotation 전체가 약 7.54MB
  - 현재 Hugging Face 접근 권한도 실제로 확인됨
  - [CASCADE dataset](https://huggingface.co/datasets/nvidia/cascade)

- 모델:

  - Alpamayo-R1-10B은 이미 실행됨
  - Alpamayo 1.5 접근 권한도 확인됨
  - 1.5는 RL post-training, navigation, flexible camera, VQA를 지원하므로 앞으로는 **1.5를 주 모델, R1을 이전 세대 baseline**으로 쓰는 것이 맞습니다. [Alpamayo 1.5](https://huggingface.co/nvidia/Alpamayo-1.5-10B)

- 로컬 CoC-NuScenes:

  - 3,218개 event
  - 2,433개가 기존 자동 quality-pass
  - quality score는 pseudo-label이므로 verifier pretraining이나 ablation에는 쓸 수 있지만 최종 gold label로 과신하면 안 됨

- 실제 Alpamayo 출력:

  - 현재는 seed 3개뿐이며 CoC가 72–94자 정도로 짧음
  - seed에 따라 trajectory ADE도 바뀜
  - [실제 출력 요약](../../../artifacts/results/restricted/alp-exp-005/summary.json)
  - 이는 feasibility 증거이지 논문 규모의 데이터는 아님

- 계산 자원:

  - A100 80GB GPU 10장이 장착되어 있고, 확인 시점에는 그중 5장이 대부분 비어 있었음
  - 저장 공간 약 65TB 가용
  - Alpamayo 1/1.5의 다중 rollout 실험과 선택적 데이터 다운로드에 충분한 편임

중요한 발견은 **CASCADE 2,066개와 OOD reasoning 1,740개의 clip overlap이 0개**라는 것입니다. 하지만 오히려 다음과 같이 독립적인 평가가 가능합니다.

- CASCADE 장면: Alpamayo가 새로 생성한 CoC와 human causal graph 비교
- OOD reasoning 장면: Alpamayo CoC와 human-refined natural-language CoC 비교
- 두 데이터 간 cross-domain generalization 측정

## 3. 가능한 방향 비교

| 연구 방향 | 신규성 | 현재 실현성 | 판단 |
|---|---:|---:|---|
| CoC soundness 평가만 수행 | 낮음 | 매우 높음 | 선행연구와 중복, 보조 실험 |
| CoC 수정/자기반성 | 낮음–중간 | 중간 | CF-VLA, C-CoT와 중복 |
| CBF safety filter만 구현 | 낮음 | 중간 | AEGIS 등과 중복 |
| CASCADE 기반 causal graph verifier | 중간–높음 | 높음 | 좋은 2순위 |
| 의미 모호성을 포함한 set-valued CoC 검증 | 높음 | 중간–높음 | 핵심 이론 기여 가능 |
| 형식 verifier 기반 K개 CoC·trajectory 선택 | 높음 | 높음 | 가장 현실적인 핵심 방법 |
| counterexample-guided post-training | 중간–높음 | 중간 | 후속 확장으로 적합 |
| 공식 NVIDIA challenge 참가 | 방법에 따라 다름 | 높음 | 외부 검증 수단, 논문 기여 자체는 아님 |

## 4. 가장 추천하는 통합 연구

### 연구 질문

> 모델이 생성한 CoC가 틀리거나 여러 의미로 해석될 수 있을 때, 모든 보정된 admissible interpretation에 대해 안전한 trajectory만 선택하고, 의미 해석 실패와 무관하게 물리적 안전을 유지할 수 있는가?

여기서 “CoC가 내포할 수 있는 어떤 의미이든”은 문자 그대로 무한한 모든 자연어 해석을 뜻할 수는 없습니다. 논문에서는 다음처럼 경계를 정해야 합니다.

- 관측 장면
- CASCADE ontology
- 차량 상태
- calibrated semantic parser

이들이 허용하는 해석 집합을 `Φα(r,o)`로 정의합니다. 이 집합이 올바른 해석을 포함할 확률을 conformal calibration으로 관리합니다. 자연어→논리 변환의 conformal correctness 연구는 이미 있지만, driving CoC, paired trajectory, causal graph 및 runtime shield까지 연결되지는 않았습니다. [ConformalNL2LTL](https://arxiv.org/abs/2504.21022)

허용 제어 집합은 다음처럼 정의할 수 있습니다.

\[
\mathcal U_{\text{accept}}
=
\mathcal U_{\text{phys}}(x)
\cap
\bigcap_{\phi\in\Phi_\alpha(r,o)}
\mathcal U_\phi(x)
\]

- `Uφ`: 각 CoC 해석이 요구하는 행동·시간 계약
- `Uphys`: collision, road boundary, actuator limit 등 CoC와 독립적인 물리 안전 집합
- 교집합이 비면 실행하지 않고 resample, repair 또는 fallback

이 구성은 두 가지를 분리합니다.

1. **Semantic guarantee:** 선택한 행동이 candidate interpretation 모두를 만족
2. **Physical guarantee:** CoC가 잘못되거나 중요한 위험을 언급하지 않아도 독립 shield가 안전 불변성을 유지

Conformal set이 true interpretation을 포함하지 못할 가능성은 `α`로 제한할 수 있지만, 물리적 안전 보증은 명시한 동역학·상태 추정·CBF feasibility 가정 아래에서만 주장해야 합니다.

### CoC soundness의 정의

CoC soundness를 하나의 pass/fail로 두면 부족합니다. 다음 벡터로 정의하는 것이 좋습니다.

- Perceptual grounding: 언급한 객체·상태가 실제 관측에 존재하는가
- Causal entailment: `because_of` 관계가 CASCADE graph 또는 개입 결과에 부합하는가
- Counterfactual sensitivity: 원인이나 reasoning을 바꾸면 trajectory가 예상 방향으로 변하는가
- Action consistency: CoC의 행동과 predicted trajectory가 일치하는가
- Temporal completeness: trigger/hold/release가 명시되거나 안전하게 abstain하는가
- Physical feasibility: 해당 행동이 현재 상태에서 실행 가능한가
- Safety completeness: 중요한 물리 위험을 CoC가 누락했더라도 독립 monitor가 검출하는가

특히 마지막 두 항목 때문에 “sound CoC”와 “safe control”은 동일한 개념이 아닙니다.

## 5. 제안하는 방법

### M1. CoC-to-Causal-Contract compiler

CoC를 바로 STL로 번역하지 않고 다음 중간 표현으로 만듭니다.

```text
entity → observed state/action
cause/influence edge
ego obligation
response interval
hold/release condition
uncertainty and grounding provenance
```

CASCADE의 graph ontology를 사용하면 임의로 ontology를 새로 만드는 부담이 크게 줄어듭니다.

### M2. Set-valued semantic parsing

하나의 CoC에서 하나의 공식만 생성하지 않고 가능한 graph/contract 집합을 반환합니다.

- 문법적으로 유효한 contract만 허용
- scene graph와 충돌하는 해석 제거
- 남은 후보를 conformal calibration
- 불확실성이 크면 abstain

가정한 trigger나 deadline을 CoC 원문에 있었던 것처럼 취급해서는 안 됩니다. 데이터·동역학·법규에서 온 요구사항은 `external safety specification`으로 분리해야 합니다.

### M3. Verifier-guided safe candidate selection

Alpamayo에서 `K=6` 정도의 `(CoC, trajectory)` 후보를 생성합니다.

각 후보에 대해:

1. causal graph grounding
2. CoC–trajectory alignment
3. STL robustness
4. obstacle/TTC/road-boundary check
5. 필요하면 CBF 또는 trajectory projection

을 수행하고 안전 후보 중 nominal quality가 가장 좋은 것을 선택합니다. 후보가 없으면 fallback합니다.

이는 단순 self-reflection과 다릅니다. 모델 스스로의 자연어 판단이 아니라 **외부의 실행 가능한 verifier**가 선택권을 가집니다.

### M4. Counterexample-guided post-training

이 단계는 첫 논문의 필수조건이라기보다 성공적인 runtime verifier 이후의 확장으로 두는 것이 좋습니다.

- false grounding
- causal edge 오류
- CoC–trajectory 부호 불일치
- premature resume
- safety filter 개입
- empty safe-set

을 hard negative 또는 preference pair로 만들어 LoRA/SFT/GRPO에 사용합니다.

## 6. 논문 실험 구성

핵심 비교군은 다음이 필요합니다.

- Alpamayo R1 top-1
- Alpamayo 1.5 top-1
- self-consistency/LLM-judge 선택
- trajectory metric만 이용한 선택
- rule-based safety 선택
- 단일 CoC-to-STL
- set-valued causal contract
- set-valued contract + independent physical shield
- oracle candidate selection

핵심 지표는 ADE/FDE보다 다음이 중요합니다.

- false-safe rate: unsafe인데 통과시킨 비율
- unsafe candidate rejection recall
- causal graph edge F1
- grounding hallucination rate
- reasoning–trajectory alignment
- coverage–risk 및 abstention curve
- Oracle@K 대비 verifier recovery
- collision, infraction, near-miss, risk exposure time
- intervention rate 및 trajectory 수정량
- nominal ADE/FDE, completion, comfort
- verifier latency와 전체 runtime overhead

특히 `top-1 → oracle@K` 차이가 작으면 candidate selection 연구 자체의 여지가 없습니다. 이것이 첫 번째 go/no-go 검사입니다.

## 7. 6주 판별 실험

### 1–2주

- Alpamayo 1.5 환경과 revision 고정
- CASCADE annotation 확보
- CASCADE와 OOD reasoning에서 각각 100–200개 장면 선택
- R1/1.5에서 장면당 6개 rollout 생성
- 100개 정도를 이중 annotation하여 causal-contract gold set 작성

### 3–4주

- CASCADE grammar 기반 compiler
- graph grounding과 CoC–trajectory checker 구현
- obstacle/egomotion 기반 independent physical monitor 연결
- `top-1`, LLM judge, rule checker, formal verifier 비교

### 5주

- set-valued parsing과 conformal calibration
- coverage–risk 및 empty-safe-set 분석
- 자연 오류와 controlled mutation을 분리하여 평가

### 6주

- NVIDIA OOD reasoning challenge 제출용 결과 생성
- 소규모 AlpaSim closed-loop 검증
- 논문 방향 go/no-go 판정

NVIDIA 공식 OOD challenge는 현재 214개 hidden-test clip, 284개 event를 사용하며 장면당 최대 6개 rollout을 제출할 수 있고, 2026년 10월 31일 마감 예정입니다. 우리의 K-candidate 방법을 외부에서 검증하기 좋은 환경입니다. 다만 AlpaJudge 점수는 safety metric이 아니므로 논문의 유일한 평가지표로 사용하면 안 됩니다. [공식 OOD Reasoning Challenge](https://nvidia-physicalai-av-ood-reasoning-challenge-2026.static.hf.space/index.html)

AlpaSim challenge도 같은 날짜에 마감되고 private closed-loop scenario에서 capability와 safety를 평가하므로 최종 시스템 검증에 유용합니다. [AlpaSim Challenge](https://nvidia-alpasime2eclosedloopchallenge2026.hf.space/)

## 8. 중단 또는 전환 조건

다음 중 하나가 나오면 방향을 조정해야 합니다.

- 후보 간 trajectory/CoC 다양성이 너무 작다  
  → test-time selection을 포기하고 verifier-guided post-training으로 이동

- 짧은 CoC에서 causal contract 추출 coverage가 낮다  
  → 자유 형식 CoC 대신 CASCADE ontology 기반 structured CoC output 연구로 전환

- verifier가 LLM judge나 단순 action-word matching보다 낫지 않다  
  → 형식 compiler 주장을 축소하고 causal grounding 모델에 집중

- offline 안전 개선이 closed-loop로 이어지지 않는다  
  → 안전 연구 주장을 중단하고 soundness/diagnostic benchmark로 제한

- 자연 발생 failure가 부족하고 mutation에서만 성능이 나온다  
  → top-tier safety claim을 하지 않고 feasibility 또는 benchmark paper로 제한

## 9. 현재 v1 계획에서 바꿔야 할 부분

현재 [Sequential CoC 연구계획](../../../03-sequential-coc-verification/docs/plans/01_RESEARCH_PLAN_V01.md)은 필요한 구성요소를 대부분 갖고 있지만 중심 의존관계를 뒤집어야 합니다.

기존:

```text
CoC → STL contract → trajectory 검증 → CBF
```

수정:

```text
scene causal graph + physical rules
                │
CoC ── untrusted claim ──> set-valued contract
                │
        candidate verification
                │
        safe selection/repair
                │
independent physical shield + fallback
```

그리고 기존 H1인 “CoC가 trigger/deadline/hold/release를 복원한다”는 가설은 약화해야 합니다. 현재 실제 출력은 매우 짧아 그런 정보가 명시되지 않았기 때문입니다. 이를 CoC에서 추정해 넣기보다 외부 safety specification으로 분리하는 것이 논리적으로 안전합니다.

## 최종 추천

연구를 세 개로 분리하지 않는 것이 좋습니다.

- **핵심 논문:** set-valued causal contract를 이용한 CoC soundness 검증 및 verifier-guided safe decoding
- **실행 보증:** CoC와 독립적인 physical shield와 fallback
- **후속 확장:** verifier counterexample을 이용한 Alpamayo post-training

제목 후보는 다음이 적절합니다.

> **CoCShield: Semantics-Robust Runtime Assurance for Reasoning Vision-Language-Action Driving**

또는

> **From Causal Claims to Safe Actions: Set-Valued Verification of Chain-of-Causation in Autonomous Driving**

확인한 선행연구 범위에서는 이 조합, 즉 **CASCADE causal graph grounding + 모호한 CoC의 set-valued semantics + 형식 verifier 기반 trajectory 선택 + 독립적 physical shield + closed-loop 평가**가 현재 자산으로 시도할 수 있는 가장 차별화되고 높은 수준의 방향입니다. 완성도에 따라 CoRL/NeurIPS 계열을 노릴 수 있고, 형식 보증을 더 강화하면 CAV/HSCC, 시스템 구현 중심이면 ICRA/RA-L에 잘 맞습니다.
