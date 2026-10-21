# 행동 제약과 행동 선택 평가의 한영 용어 정리

- 소유 프로젝트: `guardsynth-coc`
- 대상 원고: Neural Computing and Applications 투고용 원고
- 대상 독자: 저자와 공저자
- 작성일: 2026-10-17
- 상태: 현재 원고와 보충 자료의 용어 기준. 최근 합의에 따라 선호 선택 스코어를 사용하며 accuracy로 줄이지 않는다.

이 논문에서는 행동의 제약 준수 여부, 목적에 따른 행동 선택의 품질, 객관식 레이블을 통한 선호 후보 선택의 측정을 구분한다. 제약은 어떤 행동이 허용되는지를 정하고, 목적함수는 허용 행동 사이의 우선순위를 정한다. 선호 선택 스코어는 이 실험에서 정한 선호 후보를 선택한 비율이며, 실제 도로에서의 전반적인 주행 품질을 뜻하지 않는다.

## 1 용어를 구분하는 이유

기존 문장인 “Rule use requires both compliance and appropriate selection.”은 두 가지 의미를 충분히 구분하지 못한다. Compliance가 교통 법규 준수인지 공급된 실험 제약의 만족인지 명확하지 않고, appropriate selection은 맥락에 맞는 행동, 가장 높은 품질의 행동, 정답 레이블 선택으로 각각 읽힐 수 있다.

규제나 자율주행 분야 전체의 용어를 재정의하기보다, 이 논문에서 다루는 규칙의 출처와 평가 범위를 명시해야 한다. 특히 선택 품질이라는 상위 개념과, 이를 제한된 후보 선택 과제에서 측정하는 preferred-selection score를 분리한다.

ASAM OpenSCENARIO의 평가 개념은 안전 검사와 맥락별 성능 평가를 구분한다. 언어 참조 문서는 안전과 승차감 등 여러 성능 차원을 시나리오에 맞는 지표로 평가하고, 원시 측정값을 맥락에 따라 해석하도록 설명한다. 이 구분은 본 논문에서 제약 만족과 목적에 따른 선택을 따로 측정하는 근거로 참고할 수 있다. [ASAM 평가 개념, Section 7.1](https://www.asam.net/fileadmin/Standards/OpenSCENARIO/ASAM_OpenSCENARIO_2-0_Concept_Paper.html), [ASAM OpenSCENARIO DSL v2.0.0, Section 7.5.3](https://openscenario.asam.net/ASAM_OpenSCENARIO_DSL/v2.0.0/language-reference/coverage_main.html)

## 2 한영 용어와 논문 내 정의

아래 표는 이 논문에서 사용할 정의다. 모든 용어가 자율주행 표준이나 규제에서 동일한 의미로 정의되어 있다는 뜻은 아니다.

| 한글 권장 표현 | 영어 권장 표현 | 이 논문에서의 의미와 범위 |
|---|---|---|
| 교통 법규 및 규정 | Traffic laws and regulations | 법적 근거가 있는 요구사항. 공급된 실험 규칙 전체를 이렇게 부르지 않는다. |
| 공급된 행동 규칙 | Supplied behavioral rule | 해당 사례에 적용하도록 외부에서 제공한 행동 조건. 법규, 운영 지시, 실험 정책을 출처에 따라 구분한다. |
| 행동 제약 | Behavioral constraint | 적용 조건, 행동 제한, 수치 매개변수, 시간 및 해제 조건 등을 구체화하여 행동의 허용 여부를 판정하는 조건. |
| 형식 명세 | Formal specification | 제약과 관련 가정을 논리적으로 검사할 수 있도록 표현한 것. |
| 허용 행동 또는 후보 | Admissible action or candidate | 명시된 제약을 만족하는 행동 또는 후보. 물리적 실행 가능성이나 전반적인 안전성을 함께 보장하는 표현은 아니다. |
| 제약 준수 | Constraint compliance | 행동이 명시된 제약을 만족함. 법규 준수나 차량 안전에 대한 주장과 구분한다. |
| 제약 위반 | Constraint violation | 행동이 명시된 제약을 만족하지 않음. |
| 선택 목적함수 | Selection objective | 허용 행동 사이에서 선호 순위를 정하는 기준. |
| 진행 점수 | Progress score | 과제 생성기가 공급하는 합성 점수 J(a). 실제 이동 거리나 장기 주행 효율을 직접 측정한 값은 아니다. |
| 행동 선택의 품질 | Action-selection quality | 명시된 목적에 비추어 선택한 행동이 얼마나 좋은가를 나타내는 상위 개념. |
| 기준 행동 또는 기준 레이블 | Reference action or label | 주어진 후보 중 제약을 만족하면서 목적함수 값이 가장 높은 행동과 그 레이블. |
| 선호 선택 스코어 | Preferred-selection score | 가장 높은 진행 점수의 허용 후보를 선택하면 1점, 그 외 출력에는 0점을 부여한 평균을 백분율로 보고한다. accuracy로 줄이지 않는다. |
| 제약 위반율 | Constraint violation rate | 전체 예측 중 금지된 후보를 선택한 비율. 백분율로 보고한다. |
| 규칙 쌍 정확도 | Rule-pair accuracy | 장면과 후보를 고정하고 규칙만 바꾼 두 사례에서 기준 레이블을 모두 선택한 비율. |
| 제약 준수 완료율 | Constraint-compliant completion | 금지 후보를 선택하지 않고 과제를 완료한 예측의 비율을 백분율로 보고하는 보조 지표. |

Rule은 외부에서 공급된 행동 조건을 설명할 때, constraint는 그 조건을 허용 여부 판정에 사용할 수 있도록 구체화한 제한을 설명할 때 사용한다. 이 구분은 본 논문의 설명을 위한 것이며, 두 용어의 사용법이 모든 선행 연구에서 동일하다고 가정하지 않는다.

Admissible은 명시된 제약에 대한 허용 여부를 나타낸다. 동역학이나 제어 한계를 포함한 물리적 실행 가능성을 뜻하는 feasible과 혼용하지 않는다. 마찬가지로 constraint compliance를 regulatory compliance 또는 safety와 동의어로 쓰지 않는다.

## 3 선택 품질과 선호 선택 스코어의 관계

실제 주행에서 선택의 품질은 안전성, 진행 효율, 승차감, 다른 도로 이용자에 대한 영향 등 여러 요소로 평가할 수 있다. Rulebooks는 규칙의 위반 지표와 우선순위를 이용해 행동 결과를 비교하는 한 가지 접근이다. [Censi et al., Liability, Ethics, and Culture-Aware Behavior Specification using Rulebooks](https://arxiv.org/abs/1902.09355)

우리 실험은 공급된 제약과 진행 점수에 따른 유한 후보 선택으로 문제를 제한한다. 관측 및 상태 이력 h_t에서 제약 C를 만족하는 후보 집합을 A_C(h_t)라고 하면 기준 행동은 다음과 같다.

\[
a^\ast=\underset{a\in A_C(h_t)}{\arg\max}\;J(a),
\qquad y^\ast=\operatorname{label}(a^\ast).
\]

따라서 이 실험에서 가장 좋은 선택은 주어진 후보와 목적함수 안에서 가장 높은 점수를 갖는 허용 행동이다. 실제 도로에서 가능한 모든 행동 가운데 최상의 주행이라는 의미로 확대하지 않는다. J(a)는 논리 제약과 구분되는 공급된 점수이며, SMT가 그 점수를 최적화하는 것은 아니다. 이 정의는 [Method 3.1](03-method.tex)의 문제 설정에 따른다.

모델은 후보 레이블을 출력하고, 선호 선택 스코어는 그 레이블이 선호 후보의 기준 레이블과 일치하는지 측정한다. 최상위 허용 후보를 선택한 빈도를 나타내지만, 기준 후보보다 얼마나 낮은 품질의 행동을 선택했는지는 측정하지 않는다. 최고 진행 점수에서 조금 낮은 후보와 매우 낮은 후보 모두 선호 선택에서는 0점을 받기 때문이다. 이는 연속적인 행동 품질 점수와 구분되는 0/1 선택 점수의 평균이다.

| 선택 결과 | 제약 위반 여부 | 선호 선택 스코어의 사례별 점수 |
|---|---|---|
| 가장 높은 점수의 허용 후보 선택 | 위반 아님 | 1 |
| 점수가 더 낮은 허용 후보 선택 | 위반 아님 | 0 |
| 금지된 후보 선택 | 위반 | 0 |
| 후보 레이블 추출 실패 | 후보 위반 판정 대상이 아님 | 0 |

현재 평가에서는 레이블 추출 실패를 위반으로도 허용 선택으로도 세지 않는다. 따라서 선호 선택 스코어와 제약 위반율의 합은 일반적으로 100%가 아니며, 100%에서 제약 위반율을 뺀 값도 추출 실패가 있을 때 허용 후보 선택률과 같지 않다.

규칙 쌍 정확도는 두 규칙 아래에서 각각 기준 행동을 선택했는지 측정한다. 두 기준 행동이 다르면 규칙에 맞춘 선택 변화도 요구된다. 기준 행동이 같은 쌍에서는 두 사례를 모두 맞혔는지를 측정하므로, 이 지표를 모든 쌍에서 행동 변화가 발생한 비율로 해석하지 않는다.

## 4 서론의 권장 한영 문장

### 행동 제약과 선택 목적

English:

> Behavioral constraints determine which actions are admissible, while the task objective ranks the admissible actions. In the candidate-selection task studied here, the goal is to satisfy the applicable constraints and select the highest-ranked admissible action under the specified objective.

한국어:

> 행동 제약은 어떤 행동이 허용되는지를 정하고, 과제의 목적함수는 허용 행동 사이의 우선순위를 정한다. 본 연구의 후보 선택 과제에서는 적용되는 제약을 만족하면서, 명시된 목적함수에 따라 가장 높은 순위의 허용 행동을 선택하는 것을 목표로 한다.

### 실험 지표와의 연결

English:

> In our candidate-selection experiments, constraint violation rate measures selection of prohibited candidates, whereas the preferred-selection score measures how often the model selects the highest-scoring admissible candidate. These metrics evaluate constraint satisfaction and objective-based selection separately within the supplied candidate set.

한국어:

> 우리의 후보 선택 실험에서 제약 위반율은 금지 후보의 선택을 측정하고, 선호 선택 스코어는 모델이 가장 높은 점수의 허용 후보를 선택한 비율을 측정한다. 두 지표는 주어진 후보 집합 안에서 제약 만족과 목적함수에 따른 선택을 구분하여 평가한다.

## 5 본문과 표에 적용할 표현

본문에서는 Preferred-selection score, Constraint violation rate, Rule-pair accuracy를 사용한다. 지표 정의 이후 공간이 제한된 표에서는 PSS, CVR, RPA를 사용할 수 있으며, 캡션에 지표 순서와 백분율 단위를 명시한다. Preferred-selection score를 accuracy로 줄이지 않는다.

> The preferred-selection score assigns one to a prediction that selects the reference label of the highest-scoring admissible candidate and zero to every other output; the mean is reported as a percentage.

> 선호 선택 스코어는 가장 높은 진행 점수의 허용 후보에 해당하는 기준 레이블을 선택하면 1점, 그 외 출력에는 0점을 부여한 평균을 백분율로 보고한다.

| 기존 표현 또는 오해 가능성이 있는 표현 | 권장 표현 | 적용 이유 |
|---|---|---|
| Appropriate selection | Objective-based selection among admissible actions | 적절함의 기준이 명시된 목적함수임을 드러낸다. |
| Correct driving behavior | Selection of the reference candidate | 객관식 기준 레이블 평가를 전반적인 주행 정확성으로 확대하지 않는다. |
| Best action | Highest-scoring admissible candidate under the specified objective | 최상의 의미를 후보 집합과 목적함수에 한정한다. |
| Compliance 또는 violation의 단독 사용 | Constraint compliance 또는 constraint violation으로 범위를 먼저 정의 | 공급된 실험 제약과 실제 규제 준수를 구분한다. |
| Accuracy 또는 reference-selection accuracy | Preferred-selection score | 현재 지표는 선호 후보를 선택한 0/1 점수의 평균이며, 연속적인 행동 품질 점수가 아니다. |
| Progress를 실제 주행 진행량으로 설명 | Supplied synthetic progress score | 실험에서 공급한 효용 순위와 실제 이동량을 구분한다. |

상위 문제와 기여를 설명할 때에는 제약을 준수하면서 명시된 목적에 맞는 행동을 선택하는 능력을 기술한다. 실험 결과는 그 능력을 제한된 후보 선택 과제에서 측정한 선호 선택 스코어, 제약 위반율, 규칙 쌍 정확도로 보고한다.

검사 명칭은 Method의 다섯 계층을 기준으로 Structural check, Satisfiability check, Logic–rule comparison, Evidence correspondence check, Sentence correspondence check로 통일한다. Evidence correspondence는 명세 필드와 공급된 근거 기록의 대응을 검사하며, 기록 자체의 참·거짓을 확인한다는 뜻은 아니다. `source correspondence`는 이 검사의 별칭으로 사용하지 않는다. 같은 잘못된 값으로 함께 바뀐 근거·명세 대조군은 **jointly wrong evidence–specification controls**로 부른다.

P1은 직접 작성한 자연어 제약인 **natural-language guard (P1)**로 부른다. 본 연구의 검사는 **specification checking**으로 기술하고, 선행 연구가 수행한 formal verification과 구분한다. 학습용 명세에 보고한 논리 검사는 satisfiability와 candidate admissibility 및 logic–rule comparison이며, 일반 속성 질의의 예시와 구분한다.

## 6 관련 원고와 참고 자료

- [현재 서론](01-introduction-v03-en.tex): 행동 제약, 선택 목적, 선호 선택 스코어의 정의.
- [Method](03-method.tex): 허용 후보 집합과 진행 점수에 따른 기준 행동 정의.
- [실험 설정](04-experimental-setup.tex): 기준 레이블, 지표와 답 추출 실패 처리.
- [결과](05-results.tex): Preferred-selection score, Constraint violation rate, Rule-pair accuracy의 적용 대상.
- [ASAM OpenSCENARIO 2.0 Concept Paper, Section 7](https://www.asam.net/fileadmin/Standards/OpenSCENARIO/ASAM_OpenSCENARIO_2-0_Concept_Paper.html): 안전 검사와 맥락별 평가의 구분.
- [ASAM OpenSCENARIO DSL v2.0.0, Section 7.5.3](https://openscenario.asam.net/ASAM_OpenSCENARIO_DSL/v2.0.0/language-reference/coverage_main.html): 맥락에 따른 다차원 성능 평가와 지표 해석.
- [Censi et al., Rulebooks](https://arxiv.org/abs/1902.09355): 규칙의 위반 지표와 우선순위에 따른 행동 결과 비교.
