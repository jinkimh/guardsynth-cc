# 상황 인지형 CoC 실행 가드 합성: 선행연구 서베이와 기술 전략 v1

- 버전: v1.1 original-method alignment
- 기준일: 2026-08-08
- 기준 연구계획: [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)
- 조사 기준일: 2026-08-08
- 검색 데이터베이스: arXiv, PMLR, AAAI, CVF, ISO/ASAM, NASA NTRS 및 기관 원문
- 검색 범위: 교통규칙, 안전 요구사항, 제약 학습, NL-to-logic, runtime assurance, ODD와 planning
- 포함 기준: 원문 확인 가능성과 제약의 생성·적용·검증 역할 식별 가능성
- 제외 기준: 출처 불명 2차 블로그, 제품 홍보만 있는 자료, 원문 미확인 수치
- 현재 권위 상태: `CURRENT`
- 직접 지원하는 연구 질문: evidence-grounded GuardSynth 합성과 EBLC/BCV 적용 경계
- 직접 지원하는 baseline 또는 방법 결정: DriveReg·RTCD4ADS·SanDRA 계열 구성요소와 B9–B10 비교
- 후속 문서: [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)
- 대상 계획: [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)
- 연구 약칭: GuardSynth-CoC
- 문서 성격: 2026년 기준 scoping survey, 신규성 감사, 기술 전략 및 Go/No-Go 결정
- 핵심 판정: **GO — DriveRegㆍRTCD4ADSㆍSanDRA의 강점을 구성요소로 채택하되, EBLC Graph 제약 설계와 BCV 양방향 검증을 중심 방법으로 명확히 할 때 진행**

## 0. Executive summary

### 0.1 가장 중요한 결론

현재 장면에서 필요한 실행 제약을 안전하게 만드는 문제는 하나의 생성 문제가 아니다. 최소한 다음 네 문제를 분리해야 한다.

1. `Applicability`: 어떤 정적 규칙 또는 안전 템플릿이 현재 장면에 적용되는가?
2. `Grounding`: 규칙의 subject, target, lane, signal, stop line, conflict zone이 어떤 관측 엔터티인가?
3. `Binding`: 거리, 속도, 시간, 가감속도 등의 값을 어떤 출처와 함수로 계산하는가?
4. `Assurance`: 생성된 부분 계약이 관측 가능하고, 충족 가능하며, 누락·충돌·과잉제약·stale 상태가 없는가?

서베이는 자유형 LLM, CoC 분류, 규정 RAG, 교통규칙 형식화, rulebook, RSS, constraint learning, NL-to-temporal-logic, program synthesis, runtime verification, shield/CBF/reachability 및 planning 연구를 비교했다. 결론은 다음과 같다.

- 자연어 법규를 LTL/MTL로 형식화하거나 규정 문서를 검색하는 연구는 존재하지만, **현재 장면의 센서·지도 사실에 규칙을 결합하고 모든 수치와 lifecycle을 근거 있게 생성하는 문제**를 완결하지 않는다.
- [DriveReg](https://doi.org/10.1609/aaai.v40i45.41168)의 지역별 규정 검색과 행동 compliance 평가, [RTCD4ADS](https://www.sciencedirect.com/science/article/pii/S0164121226001615)의 scene-aware runtime rule activation, [SanDRA](https://arxiv.org/abs/2510.06717)의 temporal-rule/reachability action filtering은 각각 강한 선행 구성요소다. 세 연구는 retrieval–activation–action filtering의 서로 다른 층을 담당하므로 상호 대체적이지 않으며, 재현 가능한 범위에서 채택ㆍ연결하는 것 자체도 의미 있는 engineering/research contribution이다.
- 다만 단순 직렬 연결만으로는 중심 방법 기여가 약하다. 세 시스템의 출력 사이에는 자연어 규정→typed rule, Boolean scene tag→불확실한 context fact, 법적 상수→지도ㆍ차량ㆍ동역학 bound, active rule→lifecycle contract, temporal rule→planner/reachability interface라는 의미적 공백이 남는다.
- 본 연구는 이 공백을 **EBLC Graph(Evidence-Bound Lifecycle Contract Graph, 가칭)** 로 설계하고, 과소제약과 과잉제약 및 컴파일 의미보존을 **BCV(Bidirectional Contract Verification, 가칭)** 로 검증하는 것을 중심 신규성으로 둔다.
- [DRIVE](https://arxiv.org/abs/2508.04066)는 시연에서 문맥별 soft behavioral constraint를 학습한다. 이는 통계적 인간 관행과 preference 학습에는 강하지만 법적·물리적 hard safety의 근거가 될 수 없다.
- RSS, CBF 및 reachability는 상태 의존 안전 envelope를 계산하거나 집행할 수 있지만, 어떤 법규·ODD·maneuver lifecycle 의무가 현재 필요한지를 스스로 발견하지 않는다.
- 현재 프로젝트 데이터는 CoC parsing, 장면 grounding 후보, lifecycle 사례 채굴 및 replay에는 유용하다. 그러나 어느 자산도 실제 안전 가드의 완전한 정답이나 안전 수치의 근거가 아니다.

### 0.2 채택 전략

권장 구조는 **SEBGI 합성 절차 + EBLC Graph 제약 의미론 + BCV 검증**이다.

```text
sensor/map/ego/route + CoC claims
        |
        v
typed Context & Hazard Graph  -- CoC claim != observed fact
        |
        v
DriveReg-style regulation RAG + audited rule catalog hard filter
  jurisdiction / validity / ODD / maneuver / required predicates
        |
        v
hybrid candidate retrieval
  graph match + lexical/dense retrieval + learned reranking
        |
        v
RTCD-style activation + deterministic applicability (TRUE/FALSE/UNKNOWN/CONFLICT)
        |
        v
entity grounding + partial deterministic binders
  value | interval | set | UNSUPPORTED_VALUE
        |
        v
EBLC Graph composition + lifecycle automata
        |
        v
BCV: underconstraint + overconstraint + lifecycle + translation validation
        |
        +--> no sufficient evidence: REVIEW_REQUIRED / UNSUPPORTED / CONFLICT
        v
SanDRA-style reachability/action interface + independent outcome evaluation
        |
        v
scoped assurance bundle + runtime receding-horizon update
        |
        v
offline counterexample-guided rule/template refinement
```

LLM/VLM은 scene/CoC 구조화, 검색 질의 생성, candidate reranking 및 자연어 설명에만 사용한다. 다음은 LLM이 확정하지 못한다.

- 법규 또는 안전 규칙의 존재와 유효성
- hard-safety 수치
- 관측되지 않은 predicate의 진리값
- 서로 충돌하는 hard constraint의 임의 해소
- `VALIDATED` 최종 판정

### 0.3 폭넓은 적용성 평가와 깊은 실증의 분리

여섯 행동군 전체는 rule-family discovery, applicability, grounding 및 symbolic contract structure의 broad benchmark로 유지한다. 다음 세 vertical slice는 source, 수치 binder, lifecycle, BCV 반례 및 closed-loop outcome을 깊게 검증한다.

1. 선행차 추종·cut-in의 종방향 물리 envelope
2. 신호·정지표지 접근의 stop-position 및 release lifecycle
3. 보행자·자전거 conflict-zone yield의 activation–maintain–release–reactivation

초기 12–20개 audited template은 P0 feasibility gate이지 논문의 최종 template 수나 연구 영역의 상한이 아니다. 차선 변경, 복잡한 gap acceptance, 공사구간도 broad benchmark에는 포함하되, 필요한 지도-신호-차선 연결, 관할, 마찰, 차량 보장 제동성능 또는 센서 오차가 없으면 해당 수치/outcome claim만 `UNSUPPORTED` 또는 `REVIEW_REQUIRED`로 둔다.

### 0.4 Go/No-Go

- **GO:** EBLC operational semantics, BCV의 양방향 반례 정의, compiler translation relation과 깊은 slice의 rule source/binder/oracle을 사전에 고정할 수 있을 때.
- **NO-GO:** 선행 세 시스템을 접착 코드로만 연결하거나 CoC/장면을 LLM에 넣어 완성된 자연어/STL 가드를 직접 생성하면서 독자 제약ㆍ검증 방법을 제시하지 못할 때.
- **PIVOT:** 실제 데이터의 `VALIDATED` coverage가 낮더라도 high-precision selective synthesis, insufficiency detection 및 expert authoring support 연구로 전환할 수 있다.

## 1. 핵심 문제의 재정의

### 1.1 생성이 아니라 부분 함수의 안전한 합성

장면 문맥을 (C_t), 감사된 규칙 집합을 ℛ, 관측·지도·차량 증거를 (E_t), 활성 의무 ledger를 (L_{t-1})라 하자. 가드 합성은 모든 입력에 답을 내는 total generation 함수가 아니라, 근거가 있을 때만 값을 내는 partial function이어야 한다.

\[
\operatorname{Select}: (C_t, \mathcal{R}) \rightarrow 2^{\mathcal{R}} \times \{T,F,U,C\}
\]

\[
\operatorname{Bind}: (r,C_t,E_t) \rightharpoonup
\operatorname{Value}\;|\;\operatorname{Interval}\;|\;\operatorname{Set}
\]

\[
\Gamma_t = \operatorname{Compose}_{EBLC}(\operatorname{Bind}(\operatorname{Select}(C_t)),L_{t-1})
\qquad
\Pi_t,z_t = \operatorname{BCV}(\Gamma_t,C_t,E_t,\mathcal M)
\]

여기서 $\Gamma_t$는 EBLC Graph, $\Pi_t$는 evidence/binding/observability/consistency/lifecycle/bidirectional-counterexample/translation 결과를 담는 assurance bundle이다. (T,F,U,C)는 각각 `TRUE`, `FALSE`, `UNKNOWN`, `CONFLICT`이고, (z_t\in\{VALIDATED, REVIEW_REQUIRED, UNSUPPORTED, CONFLICT\})다. `Bind`가 정의되지 않으면 LLM 추정값으로 구멍을 채우지 않는다.

### 1.2 서로 분리할 정보 층

| 층 | 질문 | 허용 근거 | 금지되는 혼합 |
|---|---|---|---|
| 장면 사실 | 지금 무엇이 관측되거나 예측되는가? | 센서, track, 지도, 신호, timestamp, uncertainty | CoC 문장을 관측 사실로 승격 |
| CoC claim | 모델이 원인·행동·대상을 무엇이라 주장하는가? | 원문 span과 grounding 후보 | 규범적 의무 또는 안전 수치로 사용 |
| 규범 | 무엇이 의무·금지·허용되는가? | 관할 법규, 승인된 시스템 요구사항, ODD contract | 사람 궤적 빈도를 법적 의무로 간주 |
| 물리 | 어떤 상태·제어가 충돌 회피와 실행 가능성에 필요한가? | 동역학, latency, friction, geometry, RSS/CBF/reachability | comfort 값을 hard safety로 승격 |
| 통계·관행 | 보통 사람은 어떻게 행동하는가? | 시연, naturalistic data, calibrated distribution | 관찰 행동을 안전 경계 정답으로 간주 |
| preference | 어떤 admissible 행동을 선호하는가? | 서비스/승차감 profile, 사용자 연구 | hard constraint와 하나의 가중합으로 상쇄 |

### 1.3 연구 산출물의 정확한 정의

본 연구가 생성해야 하는 것은 “안전한 문장”이 아니라 다음 여섯 산출물이다.

1. 적용 가능한 `RuleInstance` 집합
2. 각 instance의 entity와 parameter binding derivation
3. 근거ㆍ의존ㆍ충돌 edge와 activation–maintenance–release–reactivation 상태를 갖는 `EBLC Graph`
4. canonical Guard IR에서 SMT, runtime monitor, planner predicate로의 verified compilation artifact
5. 과소제약과 과잉제약 반례를 모두 포함한 BCV assurance bundle
6. 선택적으로 abstain한 이유를 포함한 scoped verdict

완전한 도로 안전 명세를 생성한다는 주장은 하지 않는다. 특정 ODD, rule catalog, vehicle profile 및 observable predicate vocabulary 안에서 **부분 계약을 높은 precision으로 인스턴스화**하는 것이 목표다.

## 2. 체계적 검색 범위와 방법

### 2.1 검색 시점과 출처

- 검색 기준일: 2026-08-08
- 검색 대상: arXiv 원문, PMLR, AAAI, CVF, 공식 ISO/ASAM 페이지, NASA NTRS, MIT STPA 자료, 저자·기관 원문 및 공식 코드/문서
- 우선순위: 표준 공식 페이지와 논문 원문 > 공식 proceedings > 기관 repository > survey
- 제외: 출처가 불명확한 2차 블로그, 제품 홍보만 있는 자료, safety와 comfort를 구분하지 않는 주장, 원문을 확인할 수 없는 수치
- 서베이 유형: 분야 간 연결을 목표로 한 scoping survey. 검색 결과 수와 중복 제거를 고정한 PRISMA systematic review는 아니므로 그렇게 주장하지 않는다.

### 2.2 검색 축과 대표 검색식

| 축 | 대표 검색어 |
|---|---|
| A 교통규칙 | `machine interpretable traffic rules`, `digital highway code`, `rulebook autonomous driving`, `RSS safe distance`, `jurisdiction driving regulation retrieval` |
| B 안전 요구사항 | `SOTIF scenario safety requirement`, `ISO/PAS 8800 AI safety`, `STPA unsafe control action constraint`, `HARA traceability automated driving` |
| C 제약 학습 | `inverse constraint learning demonstrations`, `specification mining temporal logic traces`, `learned safe set viability`, `learn control barrier function demonstrations` |
| D NL/LLM 명세 | `natural language to LTL STL`, `typed constrained decoding specification`, `retrieval augmented temporal logic`, `verifiable NL-to-LTL grounding` |
| E runtime assurance | `runtime verification uncertainty`, `shield synthesis`, `CBF safety filter`, `HJ reachability filter`, `receding horizon temporal logic` |
| F 상황·ODD | `driving scene graph`, `traffic ontology knowledge graph`, `ASAM OpenODD`, `OpenSCENARIO DSL`, `conflict zone representation` |
| G planning | `behavior planner constraint generation`, `trajectory admissibility hard soft constraint`, `uncertainty aware motion planning`, `specification compliant reachable set` |

### 2.3 포함 여부를 판단한 질문

각 연구를 다음 질문으로 읽었다.

- 제약을 실제로 새로 생성하는가, 이미 주어진 제약을 변환·검사·집행하는가?
- 적용성을 어떤 장면 사실로 판단하는가?
- 수치가 규칙, 물리식, 데이터 추정 또는 연구자 상수 중 어디에서 오는가?
- trigger, 유지, release, 재활성화를 다루는가?
- 불확실하거나 관측할 수 없을 때 abstain하는가?
- 법규, 물리 안전, 시스템 요구, 통계적 관행 및 preference를 구분하는가?
- 생성에 쓴 규칙과 다른 독립 oracle로 검증하는가?
- 안전뿐 아니라 진행성과 과잉제약을 평가하는가?

## 3. 분야별 선행연구 서베이

### 3.1 A. 교통규칙과 운전 규범

[Formalizing Traffic Rules for Machine Interpretability](https://arxiv.org/abs/2007.00330)는 법률 검토를 거쳐 dual-carriageway 규칙을 LTL로 형식화하고 데이터에서 만족 여부를 검사했다. 이 연구는 자연어 법규를 기계 판독 가능한 규칙으로 만드는 강한 근거지만, 센서 불확실성이 있는 한 장면에 어떤 rule instance를 활성화하고 값을 결합할지는 별도 문제다.

[Digital Highway Code](https://arxiv.org/abs/2209.14036)는 공간 교통논리 USL-TR 규칙으로부터 behavior diagram과 timed automata를 만드는 방향을 제시한다. 이는 규칙 lifecycle 표현에 유용하지만, rule corpus의 정확성과 scene grounding을 전제로 한다.

[Rulebooks](https://arxiv.org/abs/1902.09355)는 violation metric들의 부분 우선순위로 실현 가능한 trajectory들을 비교한다. [Safety of the Intended Driving Behavior Using Rulebooks](https://arxiv.org/abs/2105.04472)는 이를 SOTIF functional specification 및 V&V와 연결한다. 본 연구의 conflict resolution은 단일 scalar reward보다 rulebook partial order를 채택해야 한다. 다만 rulebook은 rule과 violation metric을 누가 어떻게 만들지 해결하지 않는다.

[RSS](https://arxiv.org/abs/1708.06374)는 상태 의존 longitudinal/lateral safe distance와 proper response를 제공하며, [KeYmaera X 기반 형식 검증](https://arxiv.org/abs/2305.08812)은 종방향 RSS의 안전성·최적성과 verified refinement를 보였다. RSS는 물리 envelope binder의 후보이지 모든 법규, conflict-zone priority, ODD 또는 release 의무를 대신하지 않는다. RSS parameter도 차량과 환경의 보장값 없이 확정할 수 없다.

2026년 근접 연구인 [DriveReg](https://doi.org/10.1609/aaai.v40i45.41168)는 Boston, Singapore, Los Angeles 규정 문서를 검색하고 후보 행동의 mandatory compliance와 non-mandatory safety guideline 준수를 LLM으로 평가한다. 규정 RAG 자체는 이미 강한 baseline이다. 반면 본 연구는 행동 선택보다 rule instance의 typed parameter, 관측 가능성, lifecycle 및 abstention certificate를 목표로 해야 차별화된다.

[RTCD4ADS](https://www.sciencedirect.com/science/article/pii/S0164121226001615)는 scene feature와 semantic tag를 매칭해 runtime rule subset을 선택하고, STL robustness와 rule conflict를 검사한다. 이는 본 연구 applicability stage의 직접 baseline이다. 본 연구는 CoC-conditioned retrieval이 이 tag/scene baseline에 추가 가치를 주는지 반드시 검정해야 한다.

### 3.2 B. 안전 요구사항 생성

[ISO 21448:2022](https://www.iso.org/standard/77490.html)는 intended functionality의 specification/performance insufficiency와 scenario 기반 V&V를 다룬다. 2025년 revision 결정 이후 [2판 working draft](https://www.iso.org/fr/standard/93071.html)가 2026-07-03 단계 20.20에 진입했다. 따라서 논문은 표준 버전과 유효일을 고정해야 한다.

[ISO/PAS 8800:2024](https://www.iso.org/standard/83303.html)는 차량 AI element의 output insufficiency, systematic error 및 safety-related property를 safety assurance claim과 연결한다. 이 표준은 “LLM 출력에 validator를 붙였다”는 것보다 source/version, evidence, residual risk 및 independent assurance case가 필요함을 지지한다. 표준 자체가 장면별 수치를 제공하지는 않는다.

[STPA Handbook](https://psas.scripts.mit.edu/home/books-and-handbooks/)은 loss, hazard, unsafe control action 및 causal scenario에서 system-level safety constraint를 도출하고 refinement·traceability·test requirement로 연결한다. STPA/HARA는 rule catalog를 만드는 upstream 절차에 적합하지만, 매 frame의 scene-to-guard instantiation 알고리즘은 아니다.

[ISO 34502:2022](https://www.iso.org/standard/78951.html)는 ADS scenario-based safety evaluation framework를, [ISO 34503:2023](https://www.iso.org/standard/78952.html)는 ODD 조건의 계층적 taxonomy와 표현 요구를, [ISO 34505:2025](https://www.iso.org/cms/%20render/live/en/sites/isoorg/contents/data/standard/07/89/78954.html?browse=tc)는 scenario 평가와 test-case generation 및 requirements/OD coverage를 다룬다. 이 계열은 outcome validation 설계의 근거이며 guard 생성 ground truth를 자동 제공하지 않는다.

[Agent-based RAG safety requirement derivation](https://doi.org/10.1609/aaaiss.v5i1.35605)은 self-driving use case에서 domain 문서를 검색해 요구사항 도출을 보조한다. 이는 expert authoring baseline으로 포함할 가치가 있지만, 검색 관련성 향상과 safety requirement의 타당성·수치 정당성·runtime applicability는 서로 다른 평가다.

### 3.3 C. 제약 학습과 명세 채굴

[Learning Constraints from Demonstrations](https://arxiv.org/abs/1812.07084)는 dynamics, control constraint, task cost를 알고 있다는 가정 아래 safe demonstration과 더 낮은 비용의 unsafe sample을 이용해 unknown constraint의 보장 가능한 부분집합을 학습한다. [Inverse Constrained Reinforcement Learning](https://proceedings.mlr.press/v139/malik21a.html)도 constraint-abiding demonstration에서 제약을 역추정한다. 두 접근은 제약이 ill-posed하며 demonstration만으로 유일한 규범을 복원할 수 없음을 오히려 분명히 한다.

[Learning Task Specifications from Demonstrations](https://arxiv.org/abs/1710.03875)는 후보 logical trace property에서 MAP specification을 찾고, [Learning Linear Temporal Specifications with Uncertainty](https://arxiv.org/abs/2607.10918)는 불완전 trace 주위의 uncertainty set과 일치하는 최소 LTL을 학습한다. 이는 lifecycle pattern mining에 유용하지만, 빈번한 행동이 법적·물리적 safety requirement임을 의미하지 않는다.

[Learning Autonomous Vehicle Safety Concepts from Demonstrations](https://arxiv.org/abs/2210.02761)는 데이터에서 surrounding-agent의 reasonable behavior assumption을 학습하고 high-order CBF와 HJ reachability로 safety concept을 합성한다. 이 연구는 본 연구의 데이터 기반 safety-envelope 대안 중 가장 강하다. 다만 학습되는 것은 관찰 분포에 근거한 reasonable-behavior assumption이며, 관할 법규나 시스템 요구사항과 같은 규범적 source를 대체하지 않는다.

2026년 [Active Constraint Learning](https://proceedings.mlr.press/v331/qiu26a.html)은 informative demonstration을 능동 질의하여 constraint inference 효율을 높인다. 향후 expert labeling의 active sampling에는 유용하지만 현재 보유 trajectory만으로 적용할 수 없다.

[DRIVE](https://arxiv.org/abs/2508.04066)는 inD/highD/roundD trajectory의 state transition에서 probabilistic soft rules를 학습해 convex planner에 넣는다. 논문 자체가 comfort, cautious reaction 및 social norm과 같은 **soft constraint**를 대상으로 한다. 본 연구는 DRIVE류 출력을 `STATISTICAL_HEURISTIC` 또는 `HUMAN_CONVENTION`으로만 저장하고 hard safety로 승격하지 않아야 한다.

### 3.4 D. 자연어·LLM 기반 형식 명세 생성

[Formal Specifications from Natural Language](https://arxiv.org/abs/2206.01962)은 언어모델이 regex, FOL, LTL로 번역할 수 있음을 보였고, [Guiding LLM Temporal Logic Generation with Explicit Separation of Data and Control](https://arxiv.org/abs/2406.07400)은 data predicate를 사전 정의하고 control 구조만 생성하게 할 때 성능이 개선됨을 보였다. 이는 본 연구에서 predicate와 binder를 DSL에 고정하고 LLM은 조합 구조만 제안해야 한다는 직접 근거다.

[KGST/STL-DivEn](https://arxiv.org/abs/2505.20658)은 16,000 NL-STL pair와 external knowledge를 이용한 generate-then-refine으로 변환 정확도를 높였다. 그러나 문장과 공식의 번역 정확도가 그 atomic predicate가 실제 센서 state space에 grounding됨을 보장하지 않는다.

[VLTL-Bench](https://arxiv.org/abs/2507.00877)는 기존 NL-to-LTL benchmark가 grounding을 미리 알고 있어 성능을 과대평가한다고 지적하고 lifting, grounding, translation, verification을 분리한다. 본 연구도 동일하게 scene parsing, grounding, applicability, binding, verification을 독립 지표로 평가해야 한다.

문법 또는 type-constrained decoding은 syntax 오류를 줄이지만 semantic validity를 보장하지 않는다. [Type-Constrained Code Generation](https://doi.org/10.1145/3729274)과 semantic constraint까지 다루는 [ChopChop](https://doi.org/10.1145/3776708)은 Guard IR 생성기의 유효 출력 공간을 제한하는 구현 근거다. 하지만 source가 없는 안전 수치의 의미적 정당성은 decoding으로 해결되지 않는다.

### 3.5 E. 열린 환경과 runtime assurance

[Shield Synthesis](https://arxiv.org/abs/1501.02573)는 critical property를 runtime에 감시하고 잘못된 출력을 최소한으로 수정한다. [CBF-QP](https://arxiv.org/abs/1609.06408)는 forward-invariant safe set 제약과 performance objective를 실시간 QP에서 결합한다. [HJ reachability safety/liveness filters](https://arxiv.org/abs/2312.15347)는 상태별 admissible control set과 nominal control의 최소 수정을 제공한다.

이들은 모두 **주어진 specification/safe set**을 집행하거나 계산한다. 어떤 규칙이 현재 필요한지, 그 규칙의 법적·시스템적 source가 무엇인지, release를 언제 허용할지는 입력으로 필요하다. 따라서 본 연구의 synthesis와 runtime assurance는 대체 관계가 아니라 producer–consumer 관계다.

[LTL/TLTL runtime verification](https://openresearch-repository.anu.edu.au/items/6fdb8d50-57cd-4882-bdf8-2b290465442f)는 partial trace에 `true/false/inconclusive` 3값 semantics가 필요함을 보였고, [Symbolic Runtime Verification under Uncertainty](https://arxiv.org/abs/2207.05678)는 imprecise/missing observation과 assumptions를 symbolic formula로 유지한다. 현재 프로젝트의 `UNKNOWN`과 abstention은 부가 기능이 아니라 sound monitoring의 핵심이다.

[Receding Horizon Temporal Logic Planning](https://authors.library.caltech.edu/records/t8589-smq26/latest)과 [dynamic request receding-horizon control](https://www.roboticsproceedings.org/rss09/p13.pdf)은 현재 관측으로 작은 문제를 반복 해결하면서 global temporal property를 유지한다. Guard lifecycle은 one-shot sentence가 아니라 매 tick context와 ledger를 함께 갱신해야 한다.

### 3.6 F. 상황·ODD·시나리오 표현

[ASAM OpenODD 1.0.0](https://www.asam.net/standards/detail/openodd/)은 ODD/OD/current OD/target OD를 technology-independent UML model과 YAML, table, OpenSCENARIO DSL 등으로 교환한다. [ISO 34503](https://www.iso.org/standard/78952.html)은 ODD taxonomy를 요구하지만 ODD attribute monitoring 자체는 범위 밖이라고 명시한다. 따라서 본 연구는 ODD 표현과 runtime ODD monitor를 분리해야 한다.

2026년 현재 [ASAM OpenSCENARIO DSL 2.2.0](https://www.asam.net/standards/detail/openscenario-dsl/)은 abstract/logical/concrete scenario, KPI, check 및 coverage를 지원하고, [OpenSCENARIO XML 1.4.0](https://www.asam.net/standards/detail/openscenario-xml/)은 정확한 trigger-action scenario 교환에 적합하다. [OpenDRIVE 1.9.0](https://www.asam.net/standards/detail/opendrive/)은 lane, road geometry, roadmark 및 signal의 static network 표현을 제공한다. 이 표준들은 evaluation scenario와 map adapter에 사용하되 Guard IR 자체를 OpenSCENARIO로 대체하지 않는다.

[One Ontology to Rule Them All](https://arxiv.org/abs/2209.00342)은 corner-case ontology에서 OpenSCENARIO를 생성한다. ontology는 entity/type/relation과 rule precondition graph matching에 강하지만, 숫자 binder와 open-world UNKNOWN 처리는 별도 설계가 필요하다.

현재 프로젝트의 CASCADE는 human causal/temporal action graph, traffic control, agent 및 bounding-box track을 제공하므로 typed context의 중요한 seed다. 그러나 environment/containment가 optional이고 eventful/non-nominal selection bias가 있으며 실제 smoke test에서 dangling causal reference가 발견됐다. CASCADE graph를 검증 없이 gold context로 간주하면 안 된다.

### 3.7 G. planning 및 behavior generation

[Apollo EM planner](https://arxiv.org/abs/1807.08048)는 Frenet frame에서 DP와 spline-QP를 결합하여 traffic rule, obstacle decision 및 smoothness를 동시에 처리한다. 이는 planner가 hard/soft constraint를 실행 가능한 trajectory optimization으로 소비하는 대표 사례이지, constraint source를 발견하는 방법은 아니다.

[Rule-based Behaviour Planner](https://arxiv.org/abs/2407.00460)는 perceived environment에서 feasible parameterized behavior를 생성하고 보수적 maneuver를 선택한 뒤 parameter를 reconcile한다. 본 연구의 template instantiation baseline과 가깝지만, 규칙 corpus와 expert decision에 의존한다.

[Risk-averse Behavior Planning under Uncertainty](https://arxiv.org/abs/1812.01254), chance-constrained planning 및 [occlusion-aware contingency planning](https://pubmed.ncbi.nlm.nih.gov/41525599/)은 prediction uncertainty와 phantom actor reachable set을 planning boundary로 변환한다. uncertainty margin binder와 outcome evaluator에 유용하지만, risk budget과 distribution assumption을 provenance 없이 hard safety로 사용할 수 없다.

[SanDRA](https://arxiv.org/abs/2510.06717)는 현재 가장 강한 downstream formal-action-filter 구성요소다. scene description에서 LLM이 longitudinal/lateral action pair를 순위화하고, action을 temporal logic으로 변환한 뒤 formal traffic rule과 set-based prediction을 포함한 reachability로 unsafe action을 제거한다. 본 연구는 이를 배제하지 않고 EBLC의 planner/reachability consumer로 채택한다. 차별화 실증은 아래 항목을 모두 별개 기능으로 최초 주장하는 것이 아니라 EBLC–BCV interface가 이 항목들을 보존ㆍ검사하는지에 둔다.

- 행동 후보가 아니라 guard instance 자체의 적용성·누락·과잉 생성을 평가
- CoC claim과 observed fact의 분리 및 span-to-guard provenance
- 법규/물리/ODD/system/preference source class의 분리
- scene-specific numerical binder와 derivation audit
- observability와 selective abstention
- release/reactivation/staleness lifecycle
- 독립 rule/evaluator를 통한 circularity 통제

## 4. 상세 비교표

표에서 `생성`은 새로운 constraint structure 또는 값을 산출함을, `검사`는 이미 주어진 규칙의 만족 여부만 판정함을 뜻한다.

| 접근/연구 | 입력 | 제약의 원천 | 상황 적용성 판단 | 수치 산출 | 출력 표현 | 시간·release | 불확실성/abstention | 충돌·우선순위 | 검증 방법 | CoC 적용 가능성 | 장점 | 한계 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. Free-form LLM guard generation | CoC, scene text/image | 모델 기억과 prompt | 암묵적 attention | 모델이 자유 생성 | 자연어/JSON | 문장으로 임의 생성 | confidence가 비보정, 보통 강제 응답 | prompt 내 임의 서열 | self-check/LLM judge가 흔함 | 높음 | 빠른 baseline, broad coverage | 근거·수치 환각, 누락·과잉·순환 검증, 안전 사용 부적합 |
| 2. CoC 기반 guard classification | CoC 또는 CoC+scene feature | 사전 정의 label set | learned multi-label classifier | 생성 불가; class/slot만 | class/score | lifecycle class가 있을 때만 | selective classifier를 별도 보정 가능 | label 간 충돌 후처리 필요 | expert label test | 높음 | 현재 CoC 대량 데이터와 잘 맞음 | label source가 필요하고 숫자·규범을 만들지 못함 |
| 3. Template retrieval and slot filling | structured scene, CoC query | 감사된 template library | metadata/precondition+retrieval | slot source에 따라 결정 | typed template instance | template state machine 가능 | 필수 slot 누락 시 abstain | template priority | schema/expert/replay | 높음 | 통제 가능하고 설명 가능 | library coverage와 precondition 품질에 제한 |
| 4. Ontology/KG rule matching | scene graph, rule KG | 법규/ODD/system ontology | graph pattern, subsumption | computable predicate가 있을 때만 | RDF/JSON-LD/rule instance | event/temporal ontology 필요 | open-world UNKNOWN 표현 가능 | priority relation/exception graph | reasoner, competency questions | 높음 | entity와 provenance에 강함 | geometry·numeric dynamics와 noisy grounding에 약함 |
| 5. Evidence retrieval + deterministic binding | typed context, source registry | versioned rules+physics/system evidence | hard scope filter+hybrid retrieval+precondition evaluation | audited partial functions가 value/interval/set 반환 | Guard IR+derivation DAG | explicit trigger/hold/release binder | missing source/input이면 `UNSUPPORTED` | rulebook+SMT | independent expert/physics/simulator | 매우 높음 | 안전 근거성·수치 추적성이 가장 높음 | source engineering 비용과 selective coverage |
| 6. Program/formal specification synthesis | grammar, predicates, examples/spec | user grammar와 correctness spec | synthesis assumptions에 포함 | solver가 template constant 탐색 가능 | program/LTL/STL/automaton | reactive synthesis로 강함 | spec 불완전성은 자동 해결 못함 | realizability 우선, objective priority는 외부 | solver/proof/replay | 중간 | correct-by-construction 가능 | 올바른 상위 specification과 bounded grammar가 먼저 필요, state explosion |
| 7. Constraint mining from demonstrations | trajectory, dynamics, task cost | 관찰된 expert behavior | context feature likelihood | 통계/optimization으로 boundary 추정 | unsafe set, soft rule, STL | trace pattern을 학습 가능 | posterior/uncertainty 가능 | 규범 priority는 식별 불가 | held-out demos/simulation | 중간 | human convention과 template discovery | ill-posed; 관찰 행동은 safety/legal truth가 아님 |
| 8. Physics/RSS/CBF safety envelope | state, dynamics, uncertainty | motion model, safe set, RSS assumptions | geometry/dynamics condition | 상태 의존 식/QP/reachability | inequality/admissible control set | continuous invariant, release는 set exit | robust set/chance bound 가능 | safety가 performance보다 hard | theorem proof, reachability, closed loop | CoC 없이도 가능 | 강한 수치·실행 근거 | 어떤 규범·maneuver 의무가 필요한지 발견하지 않음 |
| 9. Rulebook 기반 우선순위 | candidate trajectories, violation metrics | 법규·윤리·문화·system rule | 각 rule violation 계산 | metric은 외부 정의 | partially ordered rules | temporal metric이면 가능 | rule uncertainty는 별도 | 핵심 기능 | preference/order properties | CoC action을 lower-level goal로 연결 가능 | hard/soft 충돌을 scalar reward보다 명확히 처리 | rule/metric 생성과 scene grounding은 미해결 |
| 10. Hybrid neuro-symbolic synthesis | multimodal context, rule KB, typed DSL | evidence+learned parsing | learned proposal+symbolic precondition | deterministic binder | NL+IR+certificate | automata/ledger | selective prediction+3/4-valued logic | rulebook+solver | 3층 독립 평가 | 매우 높음 | coverage와 assurance의 균형 | 모듈 수가 많고 attribution/latency 평가가 어려움 |
| 11. Counterexample-guided refinement | candidate guard, formal/sim model | 초기 template+counterexamples | failing context가 refinement guide | solver/search로 parameter/condition 수정 | refined rule/program | release/stale 반례 추가 가능 | modeled uncertainty만 반영 | counterexample로 conflict 발견 | independent verifier loop | 중간 | 누락·과잉을 반복 개선 | verifier model 밖 위험, overfitting, 온라인 사용 부적합 |
| 12. Runtime receding-horizon update | current context+active ledger | 검증된 rule instance와 current evidence | 매 tick 재평가 | state/uncertainty 재결합 | active guard set+monitor/shield | 가장 강함; reactivation/staleness 처리 | partial observation에 inconclusive/abstain | runtime arbitration | monitor+closed loop | 높음 | 열린 환경 변화에 필수 | 초기 rule과 binder가 틀리면 정확히 잘못 집행; latency 비용 |
| 13. DriveReg | multi-view scene, navigation, region query | 3개 지역 규정 corpus와 RAG | VLM/LLM scene-query 및 검색 | scene-specific dynamics binder 없음 | coarse action별 compliance/safety 판정 | action-local | 정형 status/abstention 없음 | 해당 없음 | expert scenario benchmark, shadow-mode | retrieval producer로 높음 | multi-region regulation retrieval 자산 | executable Guard IR, 수치 유도, lifecycle, guard-set 적절성 미평가 |
| 14. RTCD4ADS | scene semantic tags, preformalized rules, runtime state | 중국 교통규정 structured rule set | tag subset matching | 주로 rule constant/constraint | STL robustness와 conflict report | formalized rule horizon | open-world 4값 grounding 없음 | 동시 활성 rule의 constraint conflict | CARLA runtime verification | activation/monitor로 높음 | 저지연 rule activationㆍ위반ㆍ충돌 검사 | noisy entity binding, source-separated dynamic binder, 일반 lifecycle/guard synthesis 미해결 |
| 15. SanDRA | scene description, fixed high-level action pairs, predictions | 사전 형식화한 traffic rules | LLM action ranking 후 formal filtering | reachability/set prediction parameter | admissible action과 reachable corridor | formal rule/horizon | model/prediction 가정에 의존 | infeasible action 제거 | CommonRoad/highway-env closed loop | downstream consumer로 높음 | formal rule+reachability의 강한 behavior filter | rule discovery/source provenance, scene-specific guard authoring, missing/overconstraint/lifecycle 미평가 |

## 5. 기존 연구와 본 연구의 차이 및 신규성 감사

### 5.1 신규하지 않은 주장

다음은 이미 선행연구가 강하게 다루므로 본 연구의 headline contribution으로 삼지 않는다.

- 자연어 교통규칙을 temporal logic으로 변환
- 규정 문서를 RAG로 검색하여 운전 행동을 평가
- scene tag에 따라 runtime rule subset을 선택
- LLM이 제안한 행동을 formal rule과 reachability로 필터링
- RSS/CBF/HJ로 safe set 또는 안전 필터 구성
- 시연에서 soft constraint나 temporal pattern 학습
- ontology/KG로 scenario entity와 relation 표현

### 5.2 방어 가능한 신규성 후보

신규성은 기능 체크리스트를 모두 동시에 넣는 데서 나오지 않고, 다음 두 명명된 방법과 그 검증 가능한 interface에서 나온다.

1. **EBLC Graph 제약 설계:** `CoC as clue, not authority`, typed partial binding, observability, source-separated priority 및 activation–release–reactivation을 하나의 operational contract graph로 통합한다. 핵심은 field를 많이 붙이는 것이 아니라 graph edge와 lifecycle state가 runtime 판정을 어떻게 바꾸는지 명시하는 것이다.
2. **BCV 검증:** guard가 위험/위반 trace를 허용하는 과소제약과 safe/legal/progress trace를 거부하는 과잉제약을 대칭적으로 탐색하고, canonical IR→SMT/monitor/planner compiler의 bounded-trace 의미보존을 확인한다.
3. **선행 구성요소를 위한 verified interface:** DriveReg retrieval, RTCD activation, SanDRA reachability를 교체 가능한 producer/consumer로 두고, EBLC input/output contract와 BCV certificate로 결합한다.
4. **독립 evidence package:** expert semantic truth, 독립 physics/outcome oracle, locked counterfactual test를 생성 rule code와 분리해 방법의 실효성을 평가한다.

여기서 각 재료의 최초성을 주장해서는 안 된다. [Isabelle/HOL 기반 교통규칙 구체화](https://www21.in.tum.de/~nipkow/pubs/ifm17.html)는 추상 교통규칙의 atomic proposition을 차량 상태로 검증되게 구체화했고, [ADS 다층 의미론](https://arxiv.org/abs/2109.06478)은 지도ㆍ장면ㆍtraffic rule의 specification/validation 층을 연결했으며, [NIST의 SysML executability 연구](https://www.nist.gov/publications/verifying-executability-sysml-behavior-models-using-satisfiability-modulo-theory)는 SMT로 overconstraint를 찾는다. [CoCoSaFe](https://www.sciencedirect.com/science/article/pii/S0164121225001670)도 automated-driving controller의 compositional contract와 bounded model checking을 다룬다. 따라서 방어할 단위는 provenance graph, lifecycle 또는 SMT 각각이 아니라, **open-world 장면에서 선택ㆍgroundingㆍ수치 결합한 계약에 이를 통합하고 과소/과잉 및 다중 runtime target 의미보존을 함께 검증하는 EBLC–BCV workflow**다. `EBLC`와 `BCV`는 exact-name 1차 검색에서 동명 방법을 확인하지 못한 가칭이며, 투고 전 systematic novelty search로 재확인한다.

### 5.3 신규성 위험

- SanDRA 또는 RTCD4ADS의 rule filtering에 provenance field만 추가하거나 세 시스템을 순차 호출하는 수준이면 T-IV/T-ITS 방법 신규성이 부족하다.
- EBLC가 flat guard set보다 lifecycle/false-deadlock/semantic acceptance를 개선하지 못하거나 BCV가 단방향 SMT/replay 검증보다 missing/extra/bound/translation 결함을 더 찾지 못하면 독자 방법 claim을 축소해야 한다.
- GuardBench가 같은 template을 생성과 평가에 공유하면 높은 정확도는 compiler self-consistency일 뿐이다.
- CoC가 scene-only baseline보다 guard applicability 또는 expert 효율을 개선하지 않으면 연구명에서 CoC 중심성을 낮춰야 한다.
- `VALIDATED` coverage를 높이기 위해 unknown을 임의 상수로 채우면 연구 원칙과 safety assurance가 동시에 무너진다.

## 6. 후보 아키텍처 점수

점수는 2026-08-08 현재의 본 프로젝트 기준 상대 평가다. 안전 근거성 등은 1=낮음, 5=높음이다. **구현 난이도만 1=쉬움, 5=매우 어려움**이므로 높은 점수가 장점이 아니다. 학술적 신규성과 논문 잠재력은 강한 baseline과 독립 평가를 포함한다는 조건부 점수다.

| 후보 | 안전 근거성 | 설명·provenance | 장면별 적용성 | 수치 신뢰성 | open-world 대응 | 구현 난이도 | 현재 데이터 적합성 | 확장성 | 실시간 가능성 | 학술적 신규성 | T-IV/T-ITS 잠재력 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 Free-form LLM | 1 | 1 | 3 | 1 | 2 | 1 | 4 | 4 | 4 | 1 | 1 |
| 2 CoC guard classification | 2 | 2 | 3 | 1 | 2 | 2 | 4 | 4 | 5 | 2 | 2 |
| 3 Template retrieval/slot filling | 4 | 4 | 4 | 3 | 3 | 3 | 4 | 3 | 4 | 3 | 3 |
| 4 Ontology/KG matching | 4 | 5 | 4 | 2 | 3 | 4 | 3 | 3 | 3 | 3 | 3 |
| 5 Evidence retrieval+deterministic bind | 5 | 5 | 4 | 5 | 4 | 4 | 3 | 4 | 4 | 4 | 4 |
| 6 Program/formal synthesis | 4 | 4 | 3 | 4 | 2 | 5 | 2 | 2 | 2 | 3 | 4 |
| 7 Demonstration constraint mining | 2 | 2 | 4 | 3 | 3 | 4 | 4 | 4 | 4 | 3 | 3 |
| 8 Physics/RSS/CBF envelope | 5 | 5 | 3 | 5 | 3 | 4 | 3 | 3 | 4 | 2 | 3 |
| 9 Rulebook priority | 4 | 5 | 3 | 2 | 3 | 3 | 3 | 4 | 4 | 2 | 3 |
| 10 Hybrid neuro-symbolic | 5 | 5 | 5 | 5 | 4 | 5 | 4 | 4 | 3 | 4 | 5 |
| 11 Counterexample-guided refinement | 4 | 4 | 4 | 4 | 4 | 5 | 3 | 3 | 1 | 4 | 5 |
| 12 Runtime receding-horizon update | 5 | 4 | 5 | 4 | 5 | 5 | 4 | 3 | 3 | 4 | 5 |

### 6.1 점수 해석

- 5번은 offline/static synthesis core로 가장 적합하다.
- 8번은 종방향·geometry safety binder로 필수지만 단독 architecture가 아니다.
- 9번은 composition 정책으로 채택하되 rule 생성기로 오해하지 않는다.
- 10번은 3+4+5+8+9를 조합한 최종 architecture다.
- 11번은 locked evaluation 이후 offline refinement에만 사용한다.
- 12번은 lifecycle 연구에 필수지만 1차 파일럿에서 full real-time deployment를 약속하지 않는다.

## 7. 권장 최종 아키텍처: SEBGI–EBLC–BCV

### 7.1 모듈별 책임과 실패 출력

| 단계 | 입력 | 책임 | 성공 출력 | 실패 출력 |
|---|---|---|---|---|
| Scene/CoC parser | sensor/map/ego/CoC | claim과 fact를 분리한 typed graph | `ContextGraph` | `UNSUPPORTED_CONTEXT`, `UNGROUNDED_CLAIM` |
| Scope filter | context, rule metadata | jurisdiction/version/ODD/maneuver hard filter | scoped catalog | `UNSUPPORTED_JURISDICTION`, `OUT_OF_ODD` |
| Candidate retrieval | scoped rules, graph, CoC spans | DriveReg-style RAG를 포함한 high-recall 후보 제안 | ranked rule IDs+source spans | 후보 없음은 `UNSUPPORTED_RULE_COVERAGE` |
| Applicability evaluator | rule precondition, facts | RTCD-style activation을 4값 precondition·exception으로 확장 | applicable/candidate/rejected | `UNKNOWN_PRECONDITION`, `CONFLICTING_EVIDENCE` |
| Entity grounder | rule roles, tracks/map | subject/target/zone association | entity set+probability/interval | `AMBIGUOUS_TARGET`, `UNOBSERVABLE_TARGET` |
| Parameter binder | rule binder ID, typed inputs | deterministic value/interval/set 계산 | derivation DAG | `UNSUPPORTED_VALUE`, `UNIT_OR_FRAME_ERROR` |
| EBLC composer | bound clauses, active ledger | evidence/dependency/conflict edge, partial priority, lifecycle 합성 | EBLC Graph+ledger update | `CONFLICT`, `NO_ADMISSIBLE_ACTION` |
| BCV | EBLC, compiler targets, model/oracle | 과소ㆍ과잉제약, lifecycle, translation 의미보존 검사 | assurance bundle+minimal counterexamples | `MISSING/EXTRA/BOUND/LIFECYCLE/TRANSLATION_DEFECT` |
| Semantic assurance | source-independent experts | 의미·규범·NL/IR equivalence | semantic certificate | `REVIEW_REQUIRED`/`CONFLICT` |
| Reachability/action adapter | validated EBLC | SanDRA-style formal rule/reachability 소비 interface | admissible action/corridor | infeasible horizon/model-assumption diagnostic |
| Outcome assurance | independent simulator/oracle | violation, risk, progress, conservatism | outcome certificate | 실패 taxonomy와 counterexample |
| Runtime updater | current context+ledger | maintain/release/reactivate/expire | current active guards | stale/latency/unknown fallback |

### 7.2 왜 이 구조를 채택하는가

이 구조는 선행 구성요소를 폐기하지 않는다. DriveReg 계열은 규정 검색, RTCD4ADS 계열은 runtime activation, SanDRA 계열은 formal-rule/reachability action filtering에 재사용한다. 본 연구는 이들이 주고받을 **근거-수치-시간 계약의 의미론**을 EBLC로 정의하고, 단순 연결이 만든 missing/extra/stale/infeasible/translation 오류를 BCV로 검증한다.

### 7.3 배제와 채택의 구분

- Free-form LLM: safety-critical source와 수치에 사용할 수 없어 baseline으로만 유지.
- CoC classification only: 필요한 guard type 탐지는 가능하지만 value와 lifecycle을 만들지 못함.
- pure KG matching: 단독 해결책으로는 숫자·geometry·uncertainty 계산이 부족하지만 provenance/relationship backend로 채택.
- demonstration mining as safety source: hard 규범의 근거로는 기각하지만 관행, preference 및 candidate family discovery에는 채택.
- program synthesis first: correct specification과 grammar가 아직 없으므로 순서가 반대.
- RSS/CBF only: 단독 해결책으로는 법규·maneuver-specific obligation을 선택하지 못하지만 numeric binder와 runtime shield로 채택.
- one-shot synthesis: 최종 방식으로는 기각하되 event-local ablation으로 유지.
- DriveReg/RTCD4ADS/SanDRA: 대체재로 기각하지 않고 구성요소ㆍreference implementationㆍbaseline으로 채택. 단순 직렬 결합은 B13 integration baseline으로 둔다.

## 8. 표현 계층과 데이터 모델

### 8.1 Typed `ContextGraph`

상황 표현은 하나의 자연어 caption이 아니라 시간·좌표계·불확실성을 가진 typed graph여야 한다. 최소 schema는 다음과 같다.

| 영역 | 필수 필드 | 주의사항 |
|---|---|---|
| 메타데이터 | scene/frame/time, source revision, jurisdiction, coordinate frames | 모든 fact에 생성 시각과 freshness를 연결 |
| ego | pose, velocity, acceleration, dimensions, covariance/interval, controller latency | point mass가 아니라 vehicle footprint와 보장 envelope 사용 |
| route/maneuver | route segment, intended maneuver, maneuver phase | planner intention이며 관측 사실이나 법적 우선권이 아님 |
| actors | track ID, class probability, state estimate, covariance, footprint/occupancy tube, observation source | detection과 prediction을 구분하고 ID switch 가능성 유지 |
| road/map | lane graph, boundaries, stop lines, crosswalks, signals, conflict zones, map version | lane–signal–stop-line association을 명시적으로 검증 |
| environment | visibility/occlusion, weather, road surface, friction interval | 결측이면 정상 조건으로 간주하지 않음 |
| ODD | ODD profile/version과 현재 membership evidence | `in_odD` 단일 Boolean 대신 4값 판정 |
| CoC | 원문 span, cause/action/target/time claim, grounding candidates | `CLAIMED` provenance를 유지하고 `OBSERVED`로 승격 금지 |
| ledger | active obligation ID, bound entities, state, activation/release evidence, expiry | frame 사이 identity와 lifecycle 연속성을 보존 |

각 atomic fact는 `(value, status, epistemic_kind, source, timestamp, uncertainty)`를 갖는다. `status`는 `TRUE/FALSE/UNKNOWN/CONFLICT`, `epistemic_kind`는 `OBSERVED/PREDICTED/DERIVED/CLAIMED` 중 하나다. 예를 들어 CoC의 “보행자가 건너려 한다”는 `CLAIMED`이고, track의 reachable occupancy가 crosswalk와 겹친다는 것은 model/version/시간 지평을 가진 `PREDICTED`다.

### 8.2 감사 가능한 `RuleTemplate`

```yaml
rule_id: US-PA-YIELD-PED-CZ-001
source:
  class: LEGAL
  uri: ...
  version: ...
  section: ...
  jurisdiction: ...
  valid_from: ...
  content_hash: ...
scope:
  odd_profile: ...
  maneuver_phases: [approach, traverse]
roles:
  ego: Vehicle
  target: VulnerableRoadUser
  zone: ConflictZone
precondition: ...              # typed 4-valued predicate
exceptions: [...]              # emergency/officer direction 등
guard_skeleton: ...            # Guard IR
binders: [...]                  # versioned deterministic functions
lifecycle:
  activate: ...
  maintain: ...
  release: ...
  reactivate: ...
  expire: ...
priority:
  class: MANDATORY_LEGAL
  overrides: [...]
observability: [...]            # required PredicateSpec IDs
review:
  author: ...
  legal_reviewer: ...
  approved_at: ...
```

`source.class`는 최소 `LEGAL`, `PHYSICS_DERIVED`, `SYSTEM_REQUIREMENT`, `ODD_REQUIREMENT`, `HUMAN_CONVENTION`, `STATISTICAL_HEURISTIC`, `COMFORT_SERVICE`를 구분한다. 하나의 guard가 여러 source를 결합하면 각 clause별 source를 유지한다. 법적 의무와 물리적 stopping envelope를 하나의 “safety rule” 출처로 뭉치지 않는다.

### 8.3 `EvidenceRecord`, `GuardInstance`, certificate

`EvidenceRecord`는 source URI/문서 hash/section/authority/jurisdiction/validity와 함께 입력 fact, 가정, 좌표 변환, 단위, 계산식과 binder version을 기록한다. `GuardInstance`는 다음을 포함한다.

- template 및 source version
- subject/target/zone binding과 association confidence
- 각 parameter의 `Value | Interval | Set | Unsupported`
- 계산 전체의 derivation DAG
- lifecycle instance ID와 현재 상태
- intrinsic/semantic/outcome certificate 및 적용 scope
- 최종 `VALIDATED/REVIEW_REQUIRED/UNSUPPORTED/CONFLICT`와 reason code

`VALIDATED`는 문장이 자연스럽거나 SMT가 satisfiable하다는 뜻이 아니다. 선언된 scope 안에서 필수 provenance·관측성·binding이 완전하고 intrinsic 및 semantic certificate가 통과했으며, outcome 주장을 할 경우 별도 outcome certificate까지 있을 때만 부여한다.

### 8.4 EBLC Graph의 operational semantics

계약 원자는 다음 tuple로 정규화한다.

$$
g=\langle S,A,M,P,B,R,X,F,\rho,E,O\rangle,
$$

여기서 $S$는 scope, $A$는 activation, $M$은 modality, $P$는 유지 predicate, $B$는 source-bound parameter, $R$은 release, $X$는 reactivation/expiry, $F$는 승인된 fallback, $\rho$는 partial priority, $E$는 evidence/derivation, $O$는 observability contract다. EBLC Graph의 node는 `ContextFact/Evidence/Derivation/GuardClause/LifecycleState/Fallback`, edge는 `APPLIES_TO/ACTIVATES/BINDS/REFINES/DEPENDS_ON/EXCEPTS/OVERRIDES/CONFLICTS_WITH/RELEASES/REACTIVATES`다.

합성은 검색 순서대로 clause를 누적하지 않는다. 필요한 obligation 누락 $L_{miss}$, nominal safe-progress trace 배제 $L_{over}$, 중복ㆍ복잡도 $C$, 미결정 evidence $U$를 줄이되 다음 hard condition을 만족하는 graph를 구성한다.

$$
\Gamma^*=\arg\min_{\Gamma}\lambda_mL_{miss}+\lambda_oL_{over}+\lambda_cC+\lambda_uU
$$

$$
Evidence(\Gamma)\land Applicable(\Gamma)\land Monitorable(\Gamma)\land
LifecycleComplete(\Gamma)\land
(RobustFeasible(\Gamma)\lor ApprovedFallback(\Gamma)).
$$

hard legal/safety clause를 objective weight로 조용히 버리지 않는다. 실행 가능한 action이 없으면 `NO_ADMISSIBLE_ACTION/CONFLICT`를 출력하고 source에 승인된 exception/fallback으로 넘긴다. 이 operational semantics가 flat guard list 및 세 선행시스템의 naive composition과 구분되는 핵심 제약 설계다.

## 9. 장면별 적용 가능한 제약 선택

### 9.1 선택 알고리즘

1. **Hard scope filter:** jurisdiction, rule validity date, road class, ODD profile/version 및 maneuver phase가 맞지 않는 rule을 검색 전에 제외한다.
2. **High-recall proposal:** 남은 catalog에서 graph pattern, lexical/BM25, dense retrieval, CoC span query를 합쳐 후보를 얻는다. 학습 모델은 후보 제안·순위화만 한다.
3. **Deterministic applicability:** 각 rule의 typed precondition과 exception을 `ContextGraph`에서 4값으로 계산한다.
4. **Coverage check:** 현재 hazard/obligation slot에 적용 가능한 rule이 하나도 없는지 별도로 탐지한다. 검색 결과 없음은 안전함이 아니라 `UNSUPPORTED_RULE_COVERAGE`다.
5. **Entity grounding and binding:** 적용 규칙의 역할과 값이 완전히 결합될 수 있는지 평가한다. 적용 가능성과 실행 가능 binding을 별도 지표로 기록한다.

```text
SELECT(context C, catalog R, ledger L):
  S <- hard_scope_filter(R, C.jurisdiction, C.time, C.ODD, C.maneuver)
  Q <- union(graph_match(S,C), lexical_dense(S,C), coc_proposal(S,C.CoC))
  Q <- learned_rerank_only(Q, C)
  selected <- []
  diagnostics <- []
  for r in Q:
      p <- eval4(r.precondition, C)
      x <- eval4(any(r.exceptions), C)
      if x == TRUE: diagnostics += EXCEPTED(r)
      else if p == TRUE and x == FALSE: selected += r
      else if p == UNKNOWN or x == UNKNOWN: diagnostics += REVIEW_UNKNOWN(r)
      else if p == CONFLICT or x == CONFLICT: diagnostics += CONFLICTING_EVIDENCE(r)
  diagnostics += coverage_check(C, selected, R)
  return selected, diagnostics
```

`UNKNOWN`을 `FALSE`로 닫으면 필요한 가드를 누락하고, `TRUE`로 닫으면 상시 정지와 같은 과잉제약을 만든다. 따라서 두 경우 모두 candidate/review path로 보내되, 즉시 위험의 보수적 조치는 별도의 승인된 ODD fallback 또는 minimal-risk rule로만 수행한다.

### 9.2 CoC의 정확한 역할

CoC는 cause/action vocabulary, 중요한 actor 후보 및 temporal span을 제공하여 검색 recall과 expert triage를 높일 수 있다. 그러나 최종 applicability는 센서·지도 fact와 승인된 rule precondition으로 결정한다. 필수 ablation은 `scene only`, `CoC only`, `scene+CoC`, `scene+shuffled CoC`이며, 마지막 조건으로 모델이 단순 언어 prior를 사용하는지 검사한다.

## 10. 수치 파라미터 결합 원칙

모든 binder는 입력 type, 단위, 좌표계, source, validity, uncertainty propagation, 실패 조건을 갖는 versioned partial function이다. 연구자 편의 상수와 LLM 추정은 `VALIDATED` binder가 아니다.

| 파라미터 | 허용 계산·출처 | `UNSUPPORTED`가 되는 대표 조건 |
|---|---|---|
| 정지 위치 | versioned HD map의 regulatory stop line–lane–signal association, ego front-bumper의 lane 좌표 투영, map/localization uncertainty interval | stop line 미탐지, 신호 연결 불명, map version 불일치. vision geometry 추정만 있으면 법적 exact stop은 review |
| 안전 거리 | 승인된 RSS 또는 braking envelope와 vehicle guarantee, brake build-up/response latency, friction/grade interval, actor state uncertainty | 보장 제동 성능·마찰·상대 actor association 부재 |
| TTC | 동일 충돌 경로에서 `gap/max(closing_speed, eps)` 또는 predicted occupancy/reachable-time intersection | 평행/교차 경로를 scalar gap으로 축약, 가속·occlusion 가정을 숨김. TTC는 indicator이지 보편 안전 threshold가 아님 |
| 최저/최고 속도 | 검증된 signed/map statutory limit와 curvature–friction–visibility feasibility envelope를 source별 clause로 분리 | 표지/관할/차선 association 불명, 법정속도와 물리속도를 하나로 합침 |
| 가감속도·jerk | 차량·controller·road의 guaranteed control envelope는 hard, 승인 comfort profile은 service | 로그의 평균값만 존재. jerk는 별도 system requirement 없이 hard safety가 아님 |
| 횡방향 clearance | 두 swept occupancy의 Minkowski separation + localization/perception/shape error interval; 통과 법규는 별도 clause | actor shape/track/좌표계 불명 또는 임의 고정 거리 |
| hold duration | 위험/의무 predicate가 참인 동안 condition-based 유지; 법규 timer나 승인 system timer가 있을 때만 숫자 | 단일 trajectory에서 관찰된 대기시간을 일반화 |
| release stability time | 검증된 perception dropout, confirmation window, sensor/controller latency requirement로부터 도출 | “2초 정도” 같은 휴리스틱. 단지 부드러움을 위한 값이면 comfort source |
| confidence threshold | predicate별 held-out calibration의 coverage–risk 곡선에서 사전 정의한 오류 위험을 만족하도록 선택 | raw detector score, 생성/eval 동일 split, class/domain drift |
| uncertainty margin | bounded interval/reachable set, 명시된 risk budget의 chance constraint, 또는 held-out exchangeability가 성립하는 conformal bound | 분포/coverage 가정 또는 model version 누락 |

종방향 safe-distance binder의 한 예는 RSS 계열 가정 아래 다음 구조를 가진다.

\[
d_{safe}=\left[v_e\rho+\frac12 a_{e,max}\rho^2+
\frac{(v_e+\rho a_{e,max})^2}{2b_{e,min}}-
\frac{v_l^2}{2b_{l,max}}\right]_+ + m_{geometry}+m_{uncertainty}.
\]

여기서 각 속도·가속도·반응시간과 margin은 source 및 유효 범위를 가져야 한다. 이 식의 사용은 동일 차선 종방향 모델, 선행차/후행차 역할, braking convention 등 가정을 certificate에 기록할 때만 정당하다. 교차로의 보행자 yield에 이 식을 재사용하지 않는다.

## 11. 시간·lifecycle·재위험 의미론

### 11.1 상태 기계

```text
INACTIVE --trigger--> CANDIDATE --evidence/binding--> ACTIVE
ACTIVE --hold true--> MAINTAINED
ACTIVE/MAINTAINED --release true--> RELEASED
RELEASED --trigger returns, same/new hazard identity--> REACTIVATED
any live state --rule/context validity ends--> EXPIRED
any state --missing required evidence--> UNSUPPORTED/REVIEW diagnostic
any state --incompatible hard obligation--> CONFLICT diagnostic
```

`RELEASED`와 `EXPIRED`를 구분한다. 전자는 동일 rule instance가 위험 재등장 시 재활성화될 수 있고, 후자는 rule/map/version/route scope가 끝나 새 instance를 만들어야 한다. target track ID만으로 identity를 정하지 않고 spatial entity/zone 및 association history를 함께 써서 ID switch로 stale guard가 남는 것을 막는다.

| 전이 | 필요한 evidence | 대표 오류 |
|---|---|---|
| activate | trigger TRUE, exception FALSE, roles/binders sufficient | CoC 언급만으로 활성화 |
| maintain | hold predicate TRUE 또는 release UNKNOWN인 승인된 conservative policy | 한 frame 미검출로 즉시 해제 |
| release | release predicate TRUE와 필요한 stability evidence | 임의 timer 또는 planner 희망으로 해제 |
| reactivate | 위험/의무 predicate 재등장, source·scope 여전히 유효 | 한 번 해제된 guard를 영구 삭제 |
| expire | rule validity, ODD, route segment, target/zone scope 종료 | release와 validity 만료 혼동 |

hysteresis/debounce는 필요할 수 있지만 임의 상수가 아니다. sensor rate, dropout 분포, validated system requirement 및 control latency에서 도출하고 source를 남긴다. lifecycle state와 preemption state는 별도 축이다. 낮은 우선순위 task가 preempt되어도 관련 safety obligation은 ledger에 보존된다.

## 12. 충돌 해소와 우선순위

### 12.1 먼저 충돌을 분류한다

- **source conflict:** 서로 다른 법규 버전·관할·시스템 요구가 상반됨
- **predicate conflict:** 동일 사실에 `TRUE`와 `FALSE` 증거가 공존
- **feasibility/resource conflict:** 모든 hard guard를 동시에 만족하는 action이 없음
- **lifecycle conflict:** release된 의무와 재활성화된 의무가 중복·상충
- **epistemic conflict:** 관측과 prediction/CoC claim이 불일치

물리적 실행 가능성은 preference 우선순위 이전에 검사한다. 권장 partial rulebook은 다음과 같다.

1. 충돌 회피와 물리적 road containment 같은 검증된 hard safety
2. ODD boundary 및 승인된 minimal-risk/fallback requirement
3. mandatory legal rule와 그 문서화된 emergency/authorized exceptions
4. route·mission progress
5. human convention
6. comfort/service preference
7. statistical heuristic

이는 “안전이면 언제나 법규를 무시한다”는 총순서가 아니다. 예를 들어 적색신호 진입의 예외는 구급차 회피 등 source에 명시된 exception으로 표현해야 하며, 모델이 safety라는 이름으로 임의 생성할 수 없다. hard rule끼리 실행 불가능하면 scalar weight로 하나를 조용히 버리지 않고 `NO_ADMISSIBLE_ACTION/CONFLICT`를 출력하고, 해당 ODD에 승인된 minimal-risk maneuver 또는 operator escalation으로 넘긴다. fallback이 항상 정지는 아니다. 후방 충돌 위험, 철도 건널목, 교차로 내부 정지처럼 정지 자체가 위험할 수 있기 때문이다.

## 13. 관측 가능성, 불확실성, 상태 판정

### 13.1 Predicate observability contract

모든 atomic predicate는 다음 `PredicateSpec`을 가져야 한다.

```text
PredicateSpec = {
  id, argument_types, measurement_or_derivation_fn,
  allowed_sources, coordinate_frame, update_rate,
  maximum_latency, maximum_age, uncertainty_model,
  monitorability: NOW | BOUNDED_FUTURE | UNMONITORABLE,
  calibration_id, failure_value: UNKNOWN
}
```

compiler는 guard가 요구하는 입력을 센서·지도·prediction adapter가 공급하는지, runtime에는 값이 freshness budget 안에 있는지를 검사한다. `pedestrian_intends_to_cross`처럼 직접 측정할 수 없는 심리 predicate는 그대로 hard guard에 쓰지 않는다. 필요하면 “보행자 occupancy tube가 horizon H 안에 ego conflict zone과 겹친다”라는 측정 가능한 보수적 refinement로 바꾸고, prediction model과 가정을 명시한다. 그것은 여전히 `PREDICTED`이지 `OBSERVED`가 아니다.

`BOUNDED_FUTURE` predicate는 horizon 종료 전에는 inconclusive일 수 있고, `UNMONITORABLE` predicate를 포함한 runtime guard는 검증된 observable refinement 또는 외부 증거가 없으면 `UNSUPPORTED`다. 이를 통해 semantic monitorability와 물리적 sensor availability를 모두 확인한다.

### 13.2 불확실성과 selective status

관측/예측 불확실성은 point estimate를 confidence 문구로 감싸는 것이 아니라 interval, set, probability distribution 또는 symbolic unknown으로 계산을 통해 전파한다. 최종 상태는 다음처럼 결정한다.

| 상태 | 필요·충분 조건의 운영적 정의 | 허용 동작 |
|---|---|---|
| `VALIDATED` | scope/source/version 유효, precondition·exception 결정 가능, 필수 entity·값 binding 완료, predicate observable, intrinsic+semantic certificate 통과, 주장 범위에 필요한 outcome certificate 존재 | 선언된 scope에서 planner/runtime 소비 허용 |
| `REVIEW_REQUIRED` | source 해석, entity association, novel composition 또는 경계값에 제한된 인간 판단이 필요하나 직접 충돌은 없음 | 자동 hard enforcement 금지; expert queue/보수적 ODD policy |
| `UNSUPPORTED` | 관할 rule, 필수 입력, binder, map/vehicle profile, 관측 predicate 또는 catalog coverage가 없음 | 빈 값을 생성하지 말고 reason code와 운영 scope 축소 |
| `CONFLICT` | 동급/상위 hard rule 또는 evidence가 양립하지 않거나 admissible action이 없음 | 승인된 conflict/MRM policy, operator escalation, evidence 보존 |

직전 guard를 유지하는 fallback은 source scope와 entity identity가 여전히 유효하고 freshness budget 안일 때만 가능하다. 그 밖에는 stale constraint가 된다. 즉시 위험에 대한 risk-reducing 행동도 사전에 승인된 ODD/system fallback이어야 하고, “모르면 계속 정지”를 일반 정책으로 삼지 않는다. abstention 품질은 coverage와 conditional error를 함께 그리는 risk–coverage curve 및 unsupported-reason 정확도로 평가한다.

## 14. 검증 체계와 독립성

### 14.1 세 층의 서로 다른 질문

| 층 | 질문 | 검사 항목 | 독립성 요구 |
|---|---|---|---|
| Intrinsic | Guard IR 자체가 잘 형성되었는가? | schema/type/unit/frame, source/version, precondition, observability, binder recomputation, satisfiability, vacuity, redundancy, lifecycle completeness, physical feasibility | generator와 다른 deterministic validator/solver 구현 |
| Semantic | 자연어 source·장면 의무와 같은 뜻인가? | applicability, target, 누락/과잉 guard, exception, 숫자 source, release/reactivation, multi-valid guard set | source를 볼 수 있는 독립 expert, blinded output order, adjudication |
| Outcome | 실제 실행에서 risk를 낮추면서 진행 가능한가? | collision/near miss/min clearance/TTC/CVaR, rule violation, completion, deadlock, progress regret, false rejection, shield intervention | 생성 rule/template을 공유하지 않는 simulator/evaluator/oracle와 locked scenarios |

replay에서 기록 trajectory가 guard를 만족한다는 것은 **trace conformance**일 뿐 안전 검증이 아니다. 기록 trajectory가 안전 경계보다 멀리 있었을 수 있고, 반사실적 planner reaction과 rare hazard를 관찰할 수 없기 때문이다. 반대로 closed-loop 사고가 없었다는 것만으로 rule 의미가 맞다고 할 수 없다.

### 14.2 BCV: 과소제약과 과잉제약의 대칭적 반례

환경ㆍ차량 가정 $\mathcal A$와 독립 oracle 아래, BCV는 다음 두 식을 별도의 primary objective로 푼다.

$$
CE_{under}=\{\tau\mid\mathcal A(\tau)\land Accept_\Gamma(\tau)\land
(Unsafe(\tau)\lor RuleViolation(\tau))\},
$$

$$
CE_{over}=\{\tau\mid\mathcal A(\tau)\land SafeLegalProgress(\tau)\land
\neg Accept_\Gamma(\tau)\}.
$$

첫 집합은 missing clause, wrong target, weak bound 같은 **과소제약**, 둘째 집합은 extra clause, over-tight bound, stale guard, false deadlock 같은 **과잉제약**을 드러낸다. collision 감소만 보는 검증은 두 번째 집합을 놓치고, satisfiability만 보는 검증은 두 집합 모두의 규범적 충분성을 보장하지 못한다.

BCV는 네 단계로 구현한다.

1. schema/type/unit/frame/provenance/binder/satisfiability/vacuity/feasibility의 contract well-formedness
2. release, one-frame dropout, identity switch, reappearance, expiry, fallback에 대한 lifecycle bounded model checking
3. canonical Guard IR, SMT snapshot, runtime monitor, planner predicate의 boundary/UNKNOWN/CONFLICT trace 판정 등가성 검사
4. paraphrase invariance, shuffled-CoC sensitivity, hazard-removal release, hazard-reappearance reactivation, source/map/vehicle dependency locality의 metamorphic verification

각 반례는 `MISSING_CLAUSE/WRONG_TARGET/WEAK_BOUND/EXTRA_CLAUSE/OVER_TIGHT_BOUND/STALE_RELEASE/MISSED_REACTIVATION/TRANSLATION_DEFECT` 최소 원인 집합으로 축약한다. dev 반례는 offline CEGIS refinement에 사용할 수 있지만 locked-test 반례로 같은 버전을 고치지 않는다. BCV 결과는 선언한 bounded model과 oracle 가정 안의 검증이지 open-world 완전 안전 증명이 아니다.

### 14.3 circularity 방지

- generator의 rule ID를 evaluator가 그대로 lookup해 정답을 만들지 않는다.
- 숫자 binder와 outcome physics oracle은 별도 구현·검토하고, 가능하면 다른 source parameter를 사용해 sensitivity를 평가한다.
- train/dev counterexample로 template을 고칠 수 있지만 locked test counterexample은 다음 버전 연구에만 사용한다.
- 동일 LLM을 generator와 judge로 사용한 점수는 보조 분석만 허용한다.
- expert는 자유형 단일 답 대신 허용 가능한 guard set/interval, source와 `UNSUPPORTED` 가능성을 label할 수 있어야 한다.
- matched nominal control scene을 포함해 missing-guard recall과 false activation/overconstraint를 동시에 측정한다.
- always-stop/always-yield baseline을 반드시 넣어 collision 감소만으로 보수적 실패가 높은 점수를 받지 못하게 한다.

### 14.4 필수 지표

- rule applicability micro/macro precision, recall, F1 및 family별 성능
- guard-set exact/partial match, missing-guard recall, false activation rate
- entity grounding accuracy와 ambiguous/unsupported detection
- binder exact/interval coverage, unit/source correctness, numerical recomputation rate
- lifecycle transition accuracy, stale-release 및 missed-reactivation rate
- status selective risk, calibration error 및 risk–coverage AUC
- intrinsic pass, expert semantic acceptance, source agreement 및 inter-rater agreement
- closed-loop safety risk와 progress/deadlock/false-rejection trade-off
- under/overconstraint defect-family별 precision/recall과 최소 원인 localization
- lifecycle mutation detection과 canonical IR–compiler target disagreement rate
- metamorphic relation satisfaction rate 및 BCV 전후 expert acceptance
- p50/p95 latency와 catalog/scene complexity scaling

## 15. 현재 데이터 자산의 적합성 감사

현재 자산은 서로 다른 부분 문제에 유용하지만 guard gold, numeric boundary와 독립 outcome oracle을 혼동하면 안 된다.

| 데이터 자산 | 학습에 사용 | 전문가 평가 sample | 제약 gold | 수치 경계 근거 | 독립 평가 | bias/circularity 위험 |
|---|---|---|---|---|---|---|
| nuScenes auto CoC 3,218개/743 clips | CoC span parser, retrieval/reranker, guard-family weak label | 원 sensor와 함께 stratified sample 가능 | **아님** | **아님** | held-out scene을 expert가 원 sensor에서 새로 label할 때만 | Qwen-3.5 auto label/self-score, 평균 camera 변환 오차 약 62 ms, synthetic tele-crop, 2,433 clean/785 flagged |
| PhysicalAI official 2,077 events/1,740 clips | event/action phrase parser, event sampling | 공식 sensor+event에서 가능 | **아님**; human-refined short event/action text | **아님** | held-out sensor와 별도 source expert 조건부 | eventful selection; 공개 reasoning은 긴 R1 trace가 아님. 23-event pilot에서 CoC–track association과 normative deadline 부재 |
| Sequential CoC 2,475 adjacent pairs | lifecycle/temporal candidate mining | adjudicated 27 clusters는 calibration evidence | **아님** | **아님** | controlled mutation은 stateful consistency만 평가 | natural contradiction 0/27, 초기 약한 inter-rater, auto-label/adjacency 편향; mutation 40/40 대 event-local 20/40은 safety 근거가 아님 |
| Trajectory subset 403 events/94 scenes/309 pairs | ego dynamics·replay feature, lifecycle time alignment | quality-known subset 가능 | **아님** | **아님**; human trajectory는 safety boundary가 아님 | conformance/replay만 | 27 cluster 중 aligned 2, not aligned 7, unknown 18; 94 scenes 중 60 full-scene unknown |
| CASCADE 2,066 clips | typed causal/action graph, grounding·traffic-control pretraining | human-reviewed graph sample 가능 | scene-causal gold는 일부, guard gold는 아님 | **아님** | scene grounding evaluator로 조건부 | eventful/non-nominal bias, environment/containment optional, dangling `because_of` ref; official CoC와 교집합 107(기능 풍부 106) |
| R1 direct guard outputs | 현재 학습용으로 사용하지 않음 | target-level failure analysis | **아님** | **아님** | independent rule/simulator가 있을 때만 | 3 scenes/9 pairs; text insertion은 trajectory를 바꿨지만 의미 contrast가 2초 8 mm 수준이거나 관련 없는 단축 |
| Synthetic guard benchmark+폐루프 micro-world | compiler/parser/validator, known mutation 및 controlled lifecycle 학습 | real-world expert sample 대체 불가 | synthetic grammar 안에서만 gold | synthetic parameter만 | 별도 simulator·rule 구현과 real test일 때만 | 생성 template/rule을 evaluator가 공유하는 circularity, 작은 상태공간과 synthetic-to-real gap |

### 15.1 자산별 판정

- 대규모 auto CoC는 **candidate generation 학습 데이터**이지 safety label이 아니다.
- PhysicalAI와 CASCADE는 expert labeling할 장면을 고르고 context/grounding schema를 만드는 데 가장 유용하다.
- sequential/trajectory 자산은 release/reactivation episode 후보 및 trace conformance에 유용하지만 결과 안전성을 증명하지 않는다.
- synthetic data는 compiler와 mutation detector unit test에는 강하나 논문의 real semantic/outcome 성능을 대신할 수 없다.
- 현재 어떤 자산에도 jurisdiction-specific rule version, vehicle guaranteed envelope, friction/latency, map regulatory association이 완전하지 않으므로 실제 수치 `VALIDATED` coverage가 낮은 것은 예상되는 정상 결과다.

## 16. 추가 데이터·전문가·라벨링 설계

### 16.1 필요한 추가 근거

1. **Versioned rule corpus:** 한 관할부터 시작하여 공식 법규·highway code·traffic-control manual·승인 시스템/ODD 요구를 section/exception과 함께 저작권·라이선스 범위 내 보관.
2. **Vehicle assurance profile:** braking/steering/control limits, response/build-up latency, dimension 및 sensor calibration의 보장 범위.
3. **Map/regulatory association:** lane–signal–stop-line–crosswalk–conflict-zone 연결과 map version/quality.
4. **Observability manifest:** predicate별 sensor/model, rate, latency, freshness, uncertainty, calibration split.
5. **Expert GuardBench:** multi-valid guard set, applicable/not-applicable/unknown, entities, numeric value/interval/unsupported, source, lifecycle, exception, status.
6. **Lifecycle episodes:** 일시 occlusion, actor reappearance, signal/priority change, route change, release와 reactivation이 포함된 연속 구간.
7. **Matched nominal controls:** 같은 road/maneuver지만 위험 trigger가 없는 장면으로 false activation과 과잉제약 측정.
8. **Independent outcome suite:** 생성 catalog와 별도 rule oracle, 다양한 physics parameter와 counterfactual actor policy를 가진 closed-loop simulator.

### 16.2 전문가와 표본

필요 역할은 교통법/규정, ADS safety 및 SOTIF/STPA, 차량 동역학·제어, perception/map 전문가다. semantic gold는 항목당 독립 2인과 adjudicator 1인을 기본으로 하고, 숫자는 해당 domain expert와 source citation이 없으면 정답으로 확정하지 않는다.

기존 계획의 고정 `40-scene pilot → 360-scene main`은 아직 power justification이 없으므로 다음 staged design으로 바꾼다.

- **Schema dry-run 24 scenes:** 세 vertical slice에서 각 8개, source·label ontology·annotation UI 오류 제거용. 결과 보고용 test가 아님.
- **Formal pilot 60 scenes:** 위험/nominal, day/night, clear/occluded, release/reactivation을 층화하고 agreement, prevalence, annotation time, unsupported rate 추정.
- **Main study N:** pilot의 효과크기와 cluster correlation에 기반해 power analysis로 결정. clip/frame leakage를 막고 scene/route cluster 단위 split.

두 번의 ontology/지침 refinement 후에도 applicability agreement가 Krippendorff α 0.67 미만이면 main-scale gold 생성을 중단하고 label 정의 또는 연구 범위를 좁힌다. 0.67은 탐색적 최소 gate이며 출판용 high-stakes gold는 더 높은 agreement와 항목별 adjudication을 목표로 한다.

## 17. 실험 설계

### 17.1 연구 질문과 실험

| ID | 연구 질문 | 데이터/방법 | 핵심 비교와 판정 |
|---|---|---|---|
| E0 Source/semantics feasibility | 실제로 감사·결합 가능한 rule family와 명확한 EBLC semantics가 있는가? | 한 관할, 세 deep slice 최초 12–20 templates+여섯 family coverage; source/binder/predicate/EBLC manifest | template coverage, binder 입력, observability, graph/lifecycle completeness. 12–20은 gate이지 최종 cap이 아님 |
| E1 Context/observability | 센서·지도·CoC를 typed fact/claim으로 안정적으로 만들 수 있는가? | 24-scene dry-run, CASCADE/PhysicalAI 교집합 및 nominal control | entity grounding, fact provenance, UNKNOWN precision, adapter failure; CoC를 fact로 승격한 오류 0건 목표 |
| E2 Applicability | CoC가 scene-only 규칙 선택보다 추가 가치를 주는가? | 60-scene pilot 이후 locked GuardBench | free LLM, CoC classifier, template, KG, DriveReg-style RAG, RTCD-style scene tags, SEBGI 및 CoC/shuffled ablation |
| E3 EBLC/BCV | flat guard나 naive integration보다 제약 의미와 결함 검출이 나은가? | source-known subset+missing/extra/weak/over-tight/lifecycle/translation mutations | flat SEBGI, SMT-only, replay-only, DriveReg→RTCD→SanDRA naive composition; under/over recall, translation agreement, false deadlock |
| E4 Lifecycle | release/reactivation/staleness가 event-local보다 나은가? | sequential episodes, controlled mutations, curated occlusion/reappearance, simulator | event-local, timer-based, ledger SEBGI; transition F1, missed reactivation, stale guard, latency |
| E5 Semantic GuardBench | guard set의 규범·의미가 전문가와 일치하는가? | 독립 2인+adjudication, multi-valid set | missing/extra/wrong target/source/number/lifecycle/status taxonomy; source-blind vs source-aware 분석 |
| E6 Outcome | 안전 이득이 단순 보수성 때문이 아닌가? | 독립 closed-loop counterfactual suite | no guard, always-stop/yield, free LLM, template, SanDRA-like, naive composition, expert guard, EBLC+BCV |
| E7 Planner/R1 transfer | validated external guard가 R1/planner 행동을 바꾸고 준수하는가? | E0–E6 통과 뒤에만, prompt vs external monitor/shield | guard adherence, prompt-ignore, risk, progress. 3-scene 기존 결과는 feasibility anecdote로만 사용 |

### 17.2 통계와 split

- scene/route/clip cluster 단위로 train/dev/test를 분리하고 adjacent frame leakage를 금지한다.
- family, day/night, occlusion, nominal/hazard, supported/unsupported strata를 사전 정의한다.
- paired scene comparison에는 bootstrap confidence interval 또는 cluster-aware mixed model을 사용하고 효과크기와 불확실성을 보고한다.
- 여러 metric/architecture 비교의 primary endpoint를 사전 등록하고 보조 분석에는 multiple-comparison 보정을 적용한다.
- coverage를 올리면 conditional error가 변하므로 단일 threshold 점수뿐 아니라 risk–coverage curve 전체를 보고한다.
- E6는 collision만 보지 않고 completion/deadlock/progress regret를 공동 endpoint로 둔다.

### 17.3 강한 baseline이 필요한 이유

DriveReg-style RAG는 규정 검색, RTCD-style semantic tag filter는 scene activation, SanDRA-like temporal-logic+reachability는 behavior safety filtering, physics-only RSS/CBF는 numeric envelope에 **채택 가능한 구성요소이자 component baseline**이다. 세 시스템을 가능한 범위에서 직렬 연결한 naive composition을 추가해, 단순 결합의 효과와 EBLC semantic interface/BCV의 순효과를 분리한다. [NASA의 runtime assurance framework](https://ntrs.nasa.gov/citations/20240006522), [assume–guarantee AV verification](https://arxiv.org/abs/1909.04850), [chance-constrained temporal logic](https://people.eecs.berkeley.edu/~sseshia/pubs/b2hd-jha-jar18.html)은 outcome/RTA 및 불확실성 설계 참고선이다. [CEGIS의 기초](https://escholarship.org/uc/item/7dj862k9)와 [control-certificate CEGIS](https://arxiv.org/abs/1510.06108)는 locked test가 아닌 offline refinement baseline으로만 사용한다.

## 18. 구현 우선순위와 산출물

| 순서 | 구현 내용 | 종료 산출물·gate | 미루는 것 |
|---|---|---|---|
| P0 | source policy, `ContextGraph/RuleTemplate/EvidenceRecord/PredicateSpec/EBLC/GuardIR` semantics, 세 deep slice 최초 12–20 audited templates+six-family coverage | E0 audit report; source·exception·required input 없는 template 0개, EBLC transition test | end-to-end LLM training |
| P1 | nuScenes/PhysicalAI/CASCADE/map/vehicle context adapter와 4값 evaluator | 24-scene dry-run, provenance/UNKNOWN unit tests | six-family expansion |
| P2 | graph/BM25/dense retrieval, learned reranker, DriveReg/RTCD/SanDRA adapters와 mandatory baselines | E2 reproducible inference bundle, CoC/shuffled ablation, naive composition | free-form numerical generation |
| P3 | EBLC composer, deterministic partial binders, active-obligation ledger, BCV, multi-target compiler/translation validator | bidirectional mutation suite, assurance bundle, injected-missing tests | online CEGIS |
| P4 | GuardBench UI/guideline, 60-scene pilot, adjudication 및 power analysis | agreement/prevalence/time/unsupported report; main N 결정 | provisional 360 labeling |
| P5 | independent evaluator 및 closed-loop outcome suite | evaluator independence checklist, locked test manifest | R1 headline claim |
| P6 | runtime receding-horizon updater, external monitor/shield, R1 integration, offline CEGIS | E4/E6 통과 후 E7 report | full production deployment |

권장 코드 경계는 `schemas/`, `catalog/`, `context_adapters/`, `retrieval/`, `applicability/`, `eblc/`, `binders/`, `lifecycle/`, `compilers/`, `bcv/`, `evaluation_independent/`, `prior_system_adapters/`다. 특히 `binders`, `bcv/oracles`, `evaluation_independent`가 동일 rule/physics 함수를 import하지 못하도록 package와 test fixture를 분리한다. 모든 artifact는 rule/model/map/vehicle profile version과 random seed를 manifest에 고정한다.

## 19. 예상 실패와 fallback/pivot

| 실패 신호 | 해석 | 즉시 fallback | 연구 pivot |
|---|---|---|---|
| 공식 rule/exception coverage가 낮음 | 생성 문제가 아니라 upstream requirement gap | unsupported reason과 authoring queue 출력 | selective safety-requirement authoring/coverage audit 논문 |
| 두 차례 지침 수정 후 α<0.67 | label ontology가 불안정하거나 multi-valid성이 큼 | main annotation 중단, disagreement taxonomy | ontology/refinement 및 expert-assistance 연구 |
| map/vehicle/friction 근거 부족 | real numeric validation 불가능 | geometry-free symbolic guard 또는 longitudinal source-known subset | applicability/provenance paper; 수치 safety claim 삭제 |
| CoC가 scene-only보다 유의한 이득 없음 | CoC 중심 가설 기각 | scene-only system 유지, CoC는 diagnostic explanation만 | 제목·기여에서 CoC 제거 |
| binder exact/interval 성능이 낮음 | grounding/physics model 병목 | `REVIEW_REQUIRED/UNSUPPORTED` coverage 축소 | symbolic rule selection 논문 |
| risk는 감소하나 completion/deadlock 악화 | always-conservative 실패 | rulebook/progress monitor와 false-activation 수정 | safety gain 주장 보류, overconstraint detector 연구 |
| R1이 prompt guard를 무시 | prompt conditioning은 enforcement가 아님 | 외부 monitor/shield 또는 planner constraint interface | R1 통합을 보조 실험으로 축소 |
| evaluator가 generator rule을 공유 | 결과 circularity | 결과 폐기 후 별도 oracle/physics 구현 | intrinsic/semantic까지만 보고 |
| p95 latency가 budget 초과 | runtime architecture 미성숙 | offline/low-rate guard authoring+fast verified monitor | runtime claim 삭제 |
| 독립 E6에서 outcome 이득 없음 | guard 의미 또는 planner interface 실패 | 반례 taxonomy만 dev에 반영 | safety requirement quality/diagnostic tool로 전환 |

실패 fallback은 status를 `VALIDATED`로 유지한 채 내부 상수를 바꾸는 방식이 아니다. 지원 범위를 줄이고 근거 부족을 측정 가능한 결과로 공개하는 것이 본 연구의 신뢰성 기여다.

## 20. T-IV/T-ITS 수준에 필요한 evidence package

### 20.1 현재 판정

초기 한 관할·세 vertical slice 연구는 **IEEE Transactions on Intelligent Vehicles(T-IV)형 method+vehicle-behavior evaluation**이 더 자연스럽다. T-ITS를 목표로 하려면 multi-jurisdiction 또는 multi-system portability, broader traffic-system interaction과 runtime scalability를 추가해야 한다. venue 적합성이나 게재는 보장할 수 없고, 아래는 선행근접도를 고려한 최소 경쟁력 조건이다.

| Evidence | 왜 필요한가 | 최소 형태 |
|---|---|---|
| 2026 novelty/adoption audit | SanDRA·DriveReg·RTCD4ADS의 중복과 재사용 가능 지점 분리 | claim-by-claim 표, adapter, component/naive-composition baseline |
| real multi-source context | synthetic compiler 성능을 넘음 | nuScenes/PhysicalAI/CASCADE 중 최소 2개, provenance/adapter 차이 보고 |
| EBLC artifact | “LLM guard 문장”이나 접착 pipeline이 아닌 재현 가능 제약 방법 | operational semantics, source metadata, initial 12–20 deep templates+broader family set, transition/compiler tests |
| BCV artifact | 독자 검증 방법의 재현성과 단방향 검증 대비 이득 | under/over defect suite, lifecycle/translation mutations, minimal counterexamples, independent oracles |
| expert GuardBench | 생성과 독립된 semantic truth | 2인+adjudication, multi-valid set, agreement, source/unsupported labels |
| strong alternatives | 쉬운 baseline과만 비교하는 문제 방지 | free LLM, template, DriveReg-style, RTCD-style, physics-only, SanDRA-like, three-system naive composition |
| component attribution | 복합 시스템에서 기여 식별 | CoC/shuffled, retrieval, binder, EBLC graph/flat, BCV/SMT-only, lifecycle, reachability ablation |
| independent closed loop | replay/self-check circularity 제거 | locked counterfactual suite, 별도 oracle, safety+progress, sensitivity |
| uncertainty/statistics | selective system의 정직한 성능 | confidence interval, calibration, risk–coverage, cluster-aware analysis |
| negative-result discipline | low coverage를 숨기지 않음 | unsupported/conflict/failure taxonomy와 명시된 operating scope |
| portability/latency | T-ITS 확장 시 필수 | 관할/ODD change audit, rule version migration, p95 runtime scaling |

핵심 논문 주장은 다음처럼 방법 중심으로 두는 것이 타당하다.

> Can EBLC synthesize evidence-, dynamics-, and lifecycle-carrying executable contracts from heterogeneous retrieval/monitoring/safety components, and can BCV detect both underconstraint and overconstraint while preserving semantics across runtime targets?

한국어로는 다음과 같다.

> EBLC는 이질적인 규정 검색ㆍruntime activationㆍ물리/reachability 구성요소를 근거ㆍ동역학ㆍ생명주기를 가진 실행 계약으로 합성할 수 있으며, BCV는 과소제약과 과잉제약을 동시에 찾아 compiler target 사이의 의미를 보존할 수 있는가?

CoC가 유의한 추가 이득을 보이지 않더라도 evidence-bound selective instantiation 자체는 남을 수 있지만, 그 경우 CoC는 headline contribution에서 제거한다.

## 21. 기존 연구계획서에 반영할 변경

서베이 이후 [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)에 필요한 변경은 전면 재작성보다 다음 최소 delta다.

1. 제목과 핵심 claim을 EBLC Graph 합성과 BCV 양방향 검증으로 변경하고 SEBGI는 합성 절차로 배치.
2. six-group broad benchmark와 세 deep vertical slice를 분리하고, 최초 12–20 audited template을 cap이 아닌 E0 gate로 명시.
3. `ContextGraph`, 4값 applicability, source class, partial binder, EBLC graph edge/operational semantics, observability contract, lifecycle ledger 및 네 verdict를 명시.
4. `40→360` 고정 sample을 `24 dry-run→60 pilot→power-based main`으로 변경.
5. DriveReg/RTCD4ADS/SanDRA-like를 채택 가능한 구성요소와 baseline으로 재분류하고 three-system naive composition을 추가.
6. replay/SMT를 단방향 intrinsic evidence로 제한하고 BCV under/over counterexample, translation validation, independent semantic+closed-loop evaluator를 필수화.
7. flat SEBGI 대비 EBLC와 SMT/replay-only 대비 BCV의 순효과 gate를 추가.
8. 아래 Go/No-Go와 pivot 조건을 phase gate로 삽입.

이 변경은 현재의 evidence-grounding, Guard IR, 여섯 maneuver taxonomy 및 synthetic/compiler 자산을 폐기하지 않는다. 여섯 taxonomy는 broad applicability/structure benchmark로 유지하고, 세 deep slice에서만 수치ㆍlifecycleㆍclosed-loop safety claim을 강하게 한다.

## 22. 구체적 Go/No-Go 결정 규칙

수치는 pilot 전에 preregister할 초기 gate다. pilot에서 prevalence 또는 cluster effect가 가정과 크게 다르면 **locked test를 보기 전에** 근거를 남기고 조정한다.

### 22.1 Phase-0/1 GO

아래를 모두 만족할 때 60-scene formal pilot으로 진행한다.

- 세 deep vertical slice에 최초 최소 12개 audited template이 있고, 각 template에 source/version/scope/precondition/exception/binder/observability/lifecycle/priority가 100% 채워짐. 이는 broad benchmark 또는 main study의 최대 template 수가 아님.
- EBLC node/edge, lifecycle transition, 4값 predicate 및 compiler target의 operational semantics를 executable test로 고정함.
- source 없는 규범 또는 임의 safety 수치가 audit sample에서 0건.
- required predicate마다 measurement/derivation과 failure-to-UNKNOWN path가 있음.
- binder recomputation 성공률 ≥0.95, injected missing/corrupt input의 `UNSUPPORTED` precision ≥0.90.
- 24-scene dry-run 후 ontology/annotation guideline을 freeze할 수 있음.
- 생성 코드와 rule/physics를 공유하지 않는 outcome evaluator 설계와 locked-test manifest가 pilot 전에 문서화됨.

하나라도 충족하지 못하면 모델 규모를 키우지 않고 P0/P1을 반복하거나 applicability/authoring 연구로 pivot한다.

### 22.2 Main-study GO

다음을 모두 만족할 때 power-based main annotation과 E6/E7로 진행한다.

- 두 번 이내 지침 refinement 후 expert applicability agreement α≥0.67, source/숫자 disagreement는 100% adjudication 가능.
- `VALIDATED` subset semantic precision ≥0.90. coverage는 최소값으로 강제하지 않고 risk–coverage curve와 `UNSUPPORTED` 이유를 보고.
- 가장 강한 scene-only/RTCD-style baseline 대비 SEBGI applicability macro-F1의 절대 개선 ≥5 percentage points이고 paired 95% CI 하한이 0 초과, 또는 expert annotation time을 ≥20% 줄이면서 acceptance가 비열등.
- CoC headline을 유지하려면 `scene+CoC`가 `scene-only` 대비 primary metric에서 ≥3 percentage points 개선하고 shuffled-CoC에는 개선이 사라짐.
- lifecycle ledger가 event-local baseline 대비 stale-release 또는 missed-reactivation primary error를 상대 30% 이상 줄임.
- EBLC가 flat guard set 또는 naive three-system composition보다 사전 정의한 lifecycle/false-deadlock/semantic-acceptance endpoint 중 primary endpoint를 유의하게 개선함.
- BCV가 missing/extra/weak/over-tight/lifecycle/translation mutation에서 macro recall ≥0.90이고 canonical IR–target 판정 일치 ≥0.99를 달성함.

### 22.3 Outcome claim GO

- independent E6에서 strongest non-expert baseline 대비 사전 정의한 violation/risk primary endpoint가 개선되고 paired 95% CI가 0을 넘지 않는 방향으로 분리됨.
- completion의 절대 저하는 5 percentage points 이하이며 deadlock/false rejection이 always-conservative baseline보다 유의하게 낮음.
- 결과가 physics parameter, occlusion 및 actor-policy sensitivity 범위에서 방향적으로 유지됨.
- generator failure/abstention과 runtime fallback을 포함한 end-to-end p95가 선언된 control budget을 충족함. 미충족 시 offline guard-authoring claim으로 제한.

### 22.4 NO-GO/PIVOT

- `VALIDATED` precision 0.90을 달성하지 못하면 automatic runtime enforcement를 **NO-GO**하고 expert review tool로 전환.
- scene-only 대비 SEBGI 이득이 없으면 hybrid complexity를 줄여 template+deterministic binder로 전환.
- CoC 추가 이득 gate를 못 넘으면 CoC-centric claim과 제목을 제거.
- EBLC가 flat/naive composition보다 이득이 없으면 독자 제약 설계 claim을 축소하고 integration artifact로 분리.
- BCV가 단방향 validator보다 양방향 defect 검출을 개선하지 못하면 automatic `VALIDATED`를 중단하고 verification semantics를 재설계.
- outcome risk가 개선되지 않거나 completion loss가 5 points를 넘으면 vehicle-safety outcome claim을 제거하고 requirement quality/coverage 연구로 전환.
- independent evaluator를 확보하지 못하면 T-IV/T-ITS full paper claim을 **NO-GO**하고 intrinsic/semantic pilot 또는 workshop artifact로 제한.

**최종 권고는 phase-gated GO다.** 연구 영역을 세 행동으로 축소하는 결정이 아니라, 여섯 행동군의 broad benchmark와 세 deep slice를 분리하고 EBLC/BCV의 독자 방법 gate를 먼저 통과시키는 결정이다. 지금 즉시 해야 할 일은 대규모 LLM 학습이 아니라 P0의 source/rule/binder/observability/contract-semantics audit이다.

## 23. 근거 문서와 참고문헌

### 23.1 프로젝트 내부 근거

- [현재 guard synthesis 연구계획](../plans/01_RESEARCH_PLAN_V02.md)
- [논문 서론](../../../../projects/01-safety-constrained-coc/paper/manuscript/latex-kiee-review-2022/sections/01-introduction.tex), [문제정의](../../../../projects/01-safety-constrained-coc/paper/manuscript/latex-kiee-review-2022/sections/03-problem.tex), [논의](../../../../projects/01-safety-constrained-coc/paper/manuscript/latex-kiee-review-2022/sections/07-discussion.tex)
- [연구 진행 보고서](../../../01-safety-constrained-coc/docs/reports/SAFETY_CONSTRAINED_COC_PROGRESS_REPORT_V01.md)
- [기존 formal verification 계획](../../../03-sequential-coc-verification/docs/plans/01_RESEARCH_PLAN_V01.md)
- [CoC–KG–UPPAAL 설계](../../../03-sequential-coc-verification/docs/designs/2026-07-31-coc-kg-model-checking-design.md)
- [nuScenes CoC 자산 설명](../../../../data/baseline/coc_nusc/UPSTREAM_README.md)
- [PhysicalAI 내부 실험 보고서](../../../../data/restricted/nvidia_physicalai/internal-derived/ALPAMAYO_EXPERIMENT_REPORT.md)
- [CASCADE 자산 설명](../../../../data/restricted/nvidia_cascade/README.md), [CASCADE smoke test](../../../../data/restricted/nvidia_cascade/internal-derived/smoke-test-1/README.md)
- [Sequential inventory](../../../../artifacts/results/restricted/sequential-coc-consistency-v1/inventory.json), [Sequential run log](../../../../artifacts/results/restricted/sequential-coc-consistency-v1/RUN_LOG.md)
- [Alpamayo stage-1 report](../../../../artifacts/results/restricted/alp-exp-006/stage1-summary-v2/REPORT_KO.md), [Guard semantic report](../../../../artifacts/results/restricted/alp-exp-006/guard-semantic-summary-v2/REPORT_KO.md)

### 23.2 외부 핵심 참고군

- 교통규칙/규정: [Formalizing Traffic Rules](https://arxiv.org/abs/2007.00330), [Digital Highway Code](https://arxiv.org/abs/2209.14036), [Rulebooks](https://arxiv.org/abs/1902.09355), [SOTIF Rulebooks](https://arxiv.org/abs/2105.04472), [RSS](https://arxiv.org/abs/1708.06374), [formal RSS](https://arxiv.org/abs/2305.08812), [DriveReg](https://doi.org/10.1609/aaai.v40i45.41168), [RTCD4ADS](https://www.sciencedirect.com/science/article/pii/S0164121226001615), [SanDRA](https://arxiv.org/abs/2510.06717).
- 안전/표준: [ISO 21448:2022](https://www.iso.org/standard/77490.html), [ISO 21448 edition-2 WD](https://www.iso.org/fr/standard/93071.html), [ISO/PAS 8800:2024](https://www.iso.org/standard/83303.html), [ISO 34502](https://www.iso.org/standard/78951.html), [ISO 34503](https://www.iso.org/standard/78952.html), [ISO 34505](https://www.iso.org/cms/%20render/live/en/sites/isoorg/contents/data/standard/07/89/78954.html?browse=tc), [STPA Handbook](https://psas.scripts.mit.edu/home/books-and-handbooks/).
- 제약/명세 학습: [constraints from demonstrations](https://arxiv.org/abs/1812.07084), [ICRL](https://proceedings.mlr.press/v139/malik21a.html), [task specifications](https://arxiv.org/abs/1710.03875), [uncertain LTL](https://arxiv.org/abs/2607.10918), [learned AV safety concepts](https://arxiv.org/abs/2210.02761), [active constraint learning](https://proceedings.mlr.press/v331/qiu26a.html), [DRIVE soft constraints](https://arxiv.org/abs/2508.04066).
- NL/LLM 형식화: [NL to formal specifications](https://arxiv.org/abs/2206.01962), [data/control separation](https://arxiv.org/abs/2406.07400), [KGST/STL-DivEn](https://arxiv.org/abs/2505.20658), [VLTL-Bench](https://arxiv.org/abs/2507.00877), [type-constrained generation](https://doi.org/10.1145/3729274), [ChopChop](https://doi.org/10.1145/3776708), [SpecSyn](https://arxiv.org/abs/2604.21570).
- Runtime assurance: [shield synthesis](https://arxiv.org/abs/1501.02573), [CBF-QP](https://arxiv.org/abs/1609.06408), [HJ safety/liveness filters](https://arxiv.org/abs/2312.15347), [partial-trace RV](https://openresearch-repository.anu.edu.au/items/6fdb8d50-57cd-4882-bdf8-2b290465442f), [RV under uncertainty](https://arxiv.org/abs/2207.05678), [receding-horizon temporal logic](https://authors.library.caltech.edu/records/t8589-smq26/latest).
- 상황/표현: [ASAM OpenODD](https://www.asam.net/standards/detail/openodd/), [OpenSCENARIO DSL](https://www.asam.net/standards/detail/openscenario-dsl/), [OpenSCENARIO XML](https://www.asam.net/standards/detail/openscenario-xml/), [OpenDRIVE](https://www.asam.net/standards/detail/opendrive/), [OpenXOntology](https://www.asam.net/standards/asam-openxontology/), [One Ontology](https://arxiv.org/abs/2209.00342).
- Planning: [Apollo EM](https://arxiv.org/abs/1807.08048), [rule-based behavior planner](https://arxiv.org/abs/2407.00460), [risk-averse MCTS](https://arxiv.org/abs/1812.01254), [occlusion-aware contingency](https://pubmed.ncbi.nlm.nih.gov/41525599/).
