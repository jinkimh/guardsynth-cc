# GuardSynth CoC 제약의 명세와 검증 및 행동 선택 평가

방법·설정·결과·해석을 연결한 논문 집필 패키지 v0.1 · 2026-09-29

project_id: `guardsynth-coc`

이 문서는 CoC 제약의 범위·특성·요소를 제안하고, EBLC 명세·검증·테스트·CNL 생성을 행동 선택 학습에 연결하는 논문의 집필 근거다. 사용자가 제공한 laterality 패키지는 구성만 참고했고 그 연구의 내용·그림·수치는 사용하지 않았다. 새로운 학습이나 평가를 실행한 문서는 아니다.

사용자의 편집 결정에 따라 과거 adapter의 일반화 실패 표는 새 본문 구성에 넣지 않는다. 기존 기록은 보존하고 최신 동일 예산 실험을 중심으로 구성한다. 합성 환경, 평가 시 제약 제공, 실제 도로 일반화 미확인이라는 해석 범위는 유지한다.

핵심 결과는 CoC 단독 P0보다 자연어 제약 P1과 EBLC 기반 CNL 제약 P2가 통제 과제에서 더 정확한 행동을 선택했다는 것이다. 확장 시험 정확도는 49.86%, 96.81%, 98.06%였고 위반율은 19.17%, 1.39%, 0.83%였다. 별도로 명세의 경계값 검사·행동 판정·오류 탐지를 실행했다. 행동 효과와 검사 가능성은 구별되는 기여다. 기존 [6쪽 원고](main.tex)에는 최신 결과가 모두 통합되어 있지 않다.

## 1 제목과 중심 주장

한글 제안 제목: **CoC 행동 제약의 구조화와 EBLC 기반 검증 및 테스트**

영문: **Structuring CoC Behavioral Constraints for EBLC-Based Verification and Testing**

VLM 평가를 강조하려면 부제로 “A Controlled Study of Constraint-Augmented VLM Action Selection”를 사용할 수 있다. 정형 명세를 중심 기여로 두고 행동 선택 실험을 그 활용 효과의 근거로 배치한다.

> 본 연구는 CoC 행동 제약의 범위와 구성 요소를 명시하고, 이를 EBLC로 구조화하여 논리 검증과 실행 가능한 행동 테스트에 연결한다. 명세 필드에서 생성한 CNL을 CoC에 추가했을 때, 통제된 시각·시간 과제에서 CoC만 제공하는 기준보다 행동 선택 정확도와 제약 준수가 개선되었다.

검증 대상은 지정 명세와 검사 항목이다. 영상의 사실성·CoC 전체의 진실성·법규 적용·차량 안전성을 인증했다는 뜻은 아니다. “개선”은 해당 과제와 제공 정보 조건에 한정한다.

네 가지 기여는 다음과 같다.

1. **제약 모델링:** 적용 범위·조건·행동·유지·해제·불확실성·근거를 명시한다.
2. **검증과 테스트:** 실행 명세를 통해 일관성·경계값·반례·행동 후보 준수를 검사한다.
3. **학습 입력 연결:** 검증된 필드에서 CNL을 생성하여 CoC를 보강하고 대응을 추적한다.
4. **효과의 실증:** 동일 예산 P0/P1/P2와 제약 품질 검사로 행동 효과와 검사 기능을 각각 평가한다.

P1과 P2는 모두 우리가 제공하는 방식이다. P1은 외부 경쟁 방법이 아니다. P0 대비 두 방식의 효과가 주 비교이고 P2 대 P1은 정형화 이후 효과 유지와 표현 차이를 보는 내부 비교다. P2가 모든 지표에서 P1보다 좋아야 한다는 논문이 아니다.

## 2 초록 초안

자연어로 작성된 운전 판단 설명은 행동의 이유를 전달하지만, 제약이 언제 적용되고 무엇을 금지하며 어떤 조건에서 해제되는지 일관되게 검사하기 어렵다. 본 연구는 Chain of Cognition(CoC)의 행동 제약을 대상으로 적용 범위, 활성화와 해제 조건, 행동 제한, 시간 조건, 불확실성 및 근거 연결을 명시하는 체계를 제안한다. 제약을 Evidence-Bound Lifecycle Contracts(EBLC)로 구조화하고 제한된 논리 검증과 실행 가능한 행동 테스트에 연결한 뒤, 명세 필드에서 Controlled Natural Language(CNL)를 생성하여 CoC를 보강한다. 통제된 합성 시간 과제에서 Qwen3-VL-2B-Instruct를 동일한 LoRA 학습 예산과 세 개의 시드로 비교하였다. 확장 시험에서 CoC 단독 기준의 행동 선택 정확도와 제약 위반율은 49.86%와 19.17%였고, 자연어 제약 조건에서는 96.81%와 1.39%, EBLC 기반 CNL 조건에서는 98.06%와 0.83%였다. 별도의 제약 품질 검사에서는 지원하는 여섯 오류 유형의 주입 오류 144건을 모두 탐지했지만, 명세와 참조가 함께 잘못된 공유 근거 오류 24건은 탐지하지 못했다. 결과는 명시적 제약 제공의 행동 선택 효과와 정형 명세가 제공하는 검증·테스트 경로를 보여준다. 다만 평가 시에도 제약이 제공되며 제한된 합성 환경에서의 결과이므로 실제 도로의 자동 해석이나 차량 안전성에 대한 보장으로 해석할 수 없다.

초록의 성능은 확장 test만 사용한다. 비용 학습의 100%와 다른 실험의 최댓값을 섞지 않는다. 통계적 우월성·최초성·실차 적용을 주장하는 초안이 아니다.

## 3 연구 질문과 근거

| 질문 | 자료 | 가능한 결론 |
|---|---|---|
| RQ1 무엇을 CoC 행동 제약으로 구조화하는가 | 요소·프로파일·예제 | 모델링 체계와 제한된 구현 제안 |
| RQ2 구조화하면 무엇을 검사할 수 있는가 | Core/SMT·경계·오류 주입 | 지정 의미·오류 모델에서 명세와 행동 검사 |
| RQ3 제약 추가가 행동 선택에 도움이 되는가 | 동일 예산 P0/P1/P2 | supplied-constraint 과제에서 P1/P2의 이점 |
| RQ4 표현·시간 변경에도 효과가 유지되는가 | 최신 paraphrase·unseen_duration | 제한된 변화 조건의 성능 |
| RQ5 명세를 학습 비용으로 활용할 수 있는가 | CE_ONLY 대 CE_EBLC | 실행 가능성과 위반·정확도 절충 탐색 |

RQ1–RQ3가 중심이며 RQ5는 보조 실험이다. Studio는 별도 엔지니어링 개발이고 현재 합성 학습 데이터를 만든 전자동 시스템이 아니다.

## 4 제약의 범위와 특성 및 요소

### 4.1 제약의 범위

CoC의 모든 문장을 정형화할 필요는 없다. 행동 제약은 특정 상황·대상·기간에 허용되는 행동 집합을 제한한다. “보행자가 있다”는 관측, “보행자를 배려한다”는 설명, “영역이 점유되어 있으면 진입하지 않는다”는 실행 가능한 제약 후보다. 최적 행동은 허용 집합 안에서 별도 목표로 정한다.

현재 중심은 영역 진입의 보류·해제와 해제 후 시간 조건이다. 모든 교통 법규, 연속 동역학, 경로, 충돌 회피 궤적을 포괄하는 완전한 분류가 아니다. 속도·조향·거리로의 확장은 후속 적용이다.

### 4.2 구성 요소

| 요소 | 답해야 할 질문 | 구현 및 예 |
|---|---|---|
| 주체·대상 | 누가 무엇에 대해 행동하는가 | ego, 보행자 관련 진입 영역 |
| 공간·장면 범위 | 어느 영역·관측 구간인가 | zone 식별자, 판단 시점 |
| 활성화 | 언제 제한이 시작되는가 | 유효한 위험 근거 있음 |
| 행동 제한 | 무엇을 금지하거나 요구하는가 | ENTER_ZONE 금지 |
| 유지·해제 | 언제까지 유지하고 무엇으로 해제하는가 | clear 확인 또는 clear 후 0.5초 |
| 재적용 | 해제 뒤 조건이 다시 생기면 어떻게 하는가 | 정성적 계약의 재적용; 시간 실험은 제외 |
| 시간·단위 | 시점·기간·경계는 무엇인가 | 정수 ms, 임계값 이상 |
| 불확실성·충돌 | 모름·근거 충돌을 어떻게 처리하는가 | 정성적 UNKNOWN·CONFLICT |
| 근거·버전 | 조건과 규칙은 어디서 왔는가 | source_refs, profile version |
| 조합 정책 | 여러 의무가 있을 때 언제 진입하는가 | 모든 관련 해제 확인 |
| 주장 범위 | 검사 결과는 어디까지 유효한가 | bounded logical check |

제안 요소와 구현의 대응이지 필요충분성·현실 전체의 완전성 증명이 아니다. 불확실성과 재적용은 정성적 프로파일에 있지만 주 시간 학습 실험에서 평가된 요소는 아니다.

### 4.3 특성과 검사

| 특성 | 의미 | 확인 방법 |
|---|---|---|
| 명시성 | 조건·행동·해제·단위가 숨지 않음 | 필수값·프로파일 검사 |
| 추적성 | 관측·규칙·버전을 구별 | source·manifest 연결 |
| 일관성 | 제한된 조건의 동시 만족 가능성 | SAT/UNSAT·기대 결과 |
| 비공허성 | 모든 행동을 막기만 하지 않음 | 허용 사례·해제·진행 지표 |
| 시간 의미 | 임계값 전·동일·직후 구별 | 정수 ms 경계 테스트 |
| 표현 대응 | 문장과 명세 필드의 대응 | renderer·CNL 오류 검사 |
| 테스트 가능성 | 후보 행동의 판정 | 독립 환경 oracle 대 EBLC |

자연어도 사람 검토와 경험적 시험을 할 수 있다. “자연어는 검증 불가능하다” 대신 “자유 자연어만으로는 고정된 실행 의미에 따른 자동·재현 가능한 검증이 어렵고, 명시적 명세가 그 경로를 제공한다”고 쓴다.

## 5 방법과 사람의 역할

```text
CoC + 장면 관측 + 규칙 또는 외부 근거
  → 적용 제약·가정 명시 → EBLC 계약
  → 스키마 검사 → Core/SMT → 경계 및 행동 테스트
  → 필드 기반 CNL 생성 → 원래 CoC와 결합
  → VLM 학습 및 행동 선택
  → 독립 참조와 EBLC 행동 판정으로 평가
```

합성 실험은 알려진 환경과 공급된 규칙에서 계약을 만든다. 실제 영상에서 법규까지 전자동 추출한 실험이 아니다. 실제 장면은 기존 CoC·원영상·사람 검토·외부 규범 후보를 구분한다. 두 경로의 자동화 수준을 혼동하지 않는다.

| 단계 | 기계 수행 | 사람 또는 별도 근거 |
|---|---|---|
| 제약 선택 | 템플릿·합성 규칙 연결 | 현실 적용 여부 확인 |
| 명세 | 파싱·검사·Core 변환 | 의미·가정 승인 |
| 검사 | SMT·경계·오류 주입·행동 판정 | 모델 밖 조건 검토 |
| CNL | 필드 기반 결정적 생성 | 범용 자연어 등가성은 별도 문제 |
| 학습·평가 | 데이터 구성·LoRA·예측 저장 | 실제 정답 독립성·공개권한 |

주 실험 참조는 LLM의 채점만으로 만들지 않는다. 합성 환경 시간과 후보 진행 점수에서 별도 정수 연산으로 계산하고 EBLC와 대조한다. 구현 분리는 공유 환경 가정의 오류까지 제거하지 않는다.

## 6 두 실행 프로파일

### 6.1 주 학습 실험의 시간 계약

`supplied-temporal-eblc-profile-v0.1`은 영역이 한 번 점유에서 clear로 바뀌고 재점유되지 않는다고 가정한다. clear_ms는 전환, release_clear_ms는 대기 기간, entry_ms는 후보 진입 시점이다.

```text
enters → entry_ms ≥ clear_ms + release_clear_ms
```

대기는 enters=false이므로 진입 금지를 위반하지 않는다. 정수 ms로 부동소수점 경계 오차를 피한다. Core 단위 표기 `1`은 ms tick 수이며 초 단위 실수와 혼용하지 않는다. horizon=2는 유한 모델의 범위이지 2초 실제 주행 검증이 아니다. 지속적인 clear를 이 식으로 나타낼 수 있는 것은 단일 전환·재점유 없음 가정 때문이다. UNKNOWN·가림·재점유는 주 실험에서 평가하지 않았다.

### 6.2 실제 장면의 정성적 계약

별도 `eblc-action-contract-v0.1`은 ENTER_ZONE·DEFER_ENTRY와 TRUE/FALSE/UNKNOWN/CONFLICT, 근거 유효성을 쓴다. [설계](../docs/designs/PAPER1_ACTION_CONTRACT_DESIGN_V01.md)에 실행 대응이 있다.

```text
시작 확인 = valid AND truth=TRUE
해제 확인 = valid AND truth=FALSE
active(t) = 시작 확인이면 true, 해제 확인이면 false,
            둘 다 아니면 이전 active 유지
진입 허용 = 관련된 모든 의무의 해제 확인
실제 진입 → 진입 허용
```

UNKNOWN에서 이전 active=false라도 모든 해제가 확인되지 않았으면 진입이 허용되지 않는다. 모두 해제되었다고 진입을 강제하지도 않는다. 첫 판단 이전 상태를 명시하고 진행 목표를 별도로 다룬다. 이 의미는 시간 실험의 수치 대기조건과 다르다. 정성적 계약 전체를 P2 학습으로 평가했다고 쓰지 않는다.

## 7 끝까지 연결되는 예제

### 7.1 CoC와 환경 및 규칙

실제 생성 규칙에 맞춘 설명 사례이며 특정 모델의 출력 사례는 아니다. 원 합성 CoC는 “Yield to the crossing pedestrian, then proceed through the intersection.”이다. 영역이 11.0초에 clear가 되고 규칙이 0.5초 또는 1.5초 대기를 요구한다고 하자. 이는 추정 법규가 아닌 공급된 실험 규칙이다.

| 후보 | 진입 시점 | 진행 점수 | 0.5초 계약 | 1.5초 계약 |
|---|---:|---:|---|---|
| A | 10.5초 | 110 | 위반 | 위반 |
| B | 11.5초 | 100 | 허용·최적 | 위반 |
| C | 12.5초 | 85 | 허용 | 허용·최적 |
| D | 진입 안 함 | 0 | 허용·목표 미완료 | 허용·목표 미완료 |

진행 점수는 거리나 속도가 아닌 합성 효용이다. 실제 데이터의 라벨은 회전하므로 B가 항상 정답은 아니다. 같은 영상도 계약에 따라 최적 후보가 달라진다.

### 7.2 EBLC와 solver 의미

```json
{
  "version": "supplied-temporal-eblc-profile-v0.1",
  "subject": "ego",
  "target": "pedestrian_conflict_zone",
  "hold": "NO_ENTRY_WHILE_OCCUPIED",
  "release_clear_ms": 500,
  "time_unit": "ms",
  "source_kind": "SUPPLIED_SYNTHETIC_RULE",
  "assumption": "SINGLE_CLEAR_TRANSITION_NO_REOCCUPATION",
  "source_refs": [
    "Project01/temporal_guard_world.py::_guard",
    "paper1-method-preservation-v0.1"
  ]
}
```

아래는 Core 의미를 읽기 쉽게 나타낸 SMT-LIB 설명이며 compiler 출력 파일 자체의 복사본은 아니다.

```text
(declare-const enters Bool)
(declare-const entry_ms Int)
(declare-const clear_ms Int)
(assert (=> enters (>= entry_ms (+ clear_ms 500))))
(assert (= clear_ms 11000))
(assert enters)
; entry_ms=11499: UNSAT
; entry_ms=11500: SAT
; entry_ms=11501: SAT
```

UNSAT는 바인딩한 후보가 계약과 양립하지 않는다는 뜻이다. 위반 후보의 UNSAT는 기대한 검사 성공이다. SAT는 지정 계약 만족이지 최적 진행·현실 안전 인증은 아니다.

### 7.3 CNL과 데이터 결합

실제 renderer 출력:

> Do not enter the pedestrian conflict zone while it is occupied. Enter only after the zone has remained clear for at least 0.5 s.

해설: “보행자 관련 충돌 영역이 점유되어 있으면 진입하지 않는다. 해당 영역이 최소 0.5초 동안 비어 있는 상태가 된 뒤에만 진입한다.” 해석에는 재점유 없음 가정이 필요하다.

P0에는 이미지·원 CoC·후보를, P1에는 기존 자연어 제약을 추가하여, P2에는 renderer CNL을 추가하여 제공한다. 정답은 허용 후보 중 최대 진행 후보다. CNL 생성에는 정답 라벨·진행 점수를 넘기지 않는다.

```text
P2 input = image + original CoC + rendered CNL + candidates
target   = 허용 후보 중 최대 진행 후보
test     = model answer → 독립 참조 + EBLC 행동 검사
```

평가에도 CNL을 제공하되 정답 라벨을 입력하지 않는다. 공급된 규칙을 따르는 과제이지, 제약 없이 내재화한 규칙만으로 운전하는 과제가 아니다.

## 8 실제 장면 예제의 역할

[장면 #18](examples/SCENE18_PIPELINE_EXAMPLE_REPORT_V01.md)은 실제 CoC·관측을 제약에 연결하는 사례다. 원문 “Yield to the traffic on the main road and keep a safe distance from the pedestrian crossing the road.”는 데이터에 이미 있었다. 보행자·주도로 의무의 후보를 제공하지만 현재 적용의 독립 정답은 아니다. 다른 차량의 움직임이 보이지 않으면 CoC 문장으로 확인을 대신하지 않는다.

초기 예제는 수작업 조건부 명세·11개 Z3 질의·학습 미리보기였고 이후 정성적 계약 실행과 명시적 UNKNOWN 정책으로 이어졌다. 초기 예제를 전자동 실행 성공으로 재표기하지 않는다. 실제 이미지 한 장면의 학습 smoke test도 실행 확인이지 성능 증명이 아니다.

본문에는 관측→두 의무→알려짐/모름→진입 판단 도식을 사용할 수 있다. restricted 이미지·응답을 공개 패키지에 복사하지 않는다. 재배포 권한 확인 전에는 비식별 도식으로 설명하며 합성 학습 결과와 같은 모집단으로 합산하지 않는다.

## 9 검증과 테스트 근거

| 검사 층 | 확인 내용 | 보장하지 않는 것 |
|---|---|---|
| 스키마·프로파일 | 필드·단위·버전 | 현실 규칙 선택 |
| SAT 일관성 | 제한된 조건의 만족 가능성 | 모든 주행 안전 |
| 경계·반례 | 임계값 전·동일·직후 | 모델 밖 상황 |
| 독립 oracle 대조 | 환경 판정과 Core 일치 | 공유 source 오류 부재 |
| CNL 대응 | 제한 문법·필드 대응 | 자유 자연어 전체 등가성 |
| 행동 평가 | 예측의 준수·진행 | 사고율·폐루프 안정성 |

temporal bridge는 네 대기시간에서 100개 기대 결과 질의를 실행했다. 확장 데이터 검사는 5,760개 후보 바인딩, 960개 고유 SMT 할당이다. 반복 실행과 고유 사례를 구별한다. 근거는 [시간 계약 코드](../experiments/paper1_cnl_learning/temporal_preservation.py)와 [확장 데이터 보고서](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-training-data-2026-09-29-001/REPORT_KO.md)다.

### 9.1 제약 품질 오류 주입

| 오류 또는 대조 | 건수 | 결과 |
|---|---:|---|
| CNL 부정 의미 변경 | 24 | 24 탐지 |
| CNL 임계값 변경 | 24 | 24 탐지 |
| 해제 삭제 | 24 | 24 탐지 |
| 비교 연산 반전 | 24 | 24 탐지 |
| 명세 임계값 변경 | 24 | 24 탐지 |
| 단위 오류 | 24 | 24 탐지 |
| 정상 계약 | 24 | 24 수용, 오탐 0 |
| source와 계약의 공유 오류 | 24 | 24 미탐 |

192개 중 지원 오류 144개를 탐지했고 정상 24개와 공유 오류 24개를 수용했다. 전체 오류 168개가 분모이면 탐지율은 85.71%다. 모든 오류 100% 탐지라고 쓰지 않는다. 균형을 맞춘 오류 주입이므로 자연 오류율·배포 정밀도를 추정하지 않는다.

SAT만의 성과도 아니다. 단위 오류를 제외한 여러 잘못된 계약도 자체적으로 SAT가 된다. 스키마·source 대응·독립 판정·CNL을 함께 검사한 결과다. [원 보고서 D4](../../../artifacts/projects/guardsynth-coc/public/paper1-temporal-diversity-001/diversity-analysis-2026-09-29-001/REPORT_KO.md)가 출처다. 같은 보고서의 과거 일반화 실험은 새 주 성능 표에 넣지 않는다.

## 10 실험 구성과 표본 단위

| 계열 | 규모 | 역할 |
|---|---|---|
| 확장 학습 | 6조건×3시드, 18 fits, 각 180 updates, 17,280 예측 | 주 행동 비교 |
| 제약 품질 | 192개 계약·CNL 사례 | 검사 기능 |
| 비용 학습 | 2조건×3시드, 6 fits, 각 60 updates, 6,480 예측 | 명세 비용 활용 |
| 추가 지표 | 확장의 동일 예측 재분석 | 진행 손실·오류 양상 |
| 실제 장면 | 별도 source 검토·조건부 계약 | 적용 과정 설명 |

비용 예측 수에는 추가 학습 전 P2 세 모델의 평가가 포함된다. 파생 prompt·시드·반복 평가를 수만 개의 독립 도로 장면으로 세지 않는다. 과거 소규모 실험과 최신 예산·분할을 합쳐 동일 조건 비교로 만들지 않는다.

## 11 확장 데이터와 학습 설정

### 11.1 분할

| 분할 | 고유 합성 이미지 | clear 시점 | 조건별 행 |
|---|---:|---|---:|
| train | 40 | 6.0–9.9초 | 960 |
| validation | 10 | 10.0–10.9초 | 240 |
| test | 10 | 11.0–11.9초 | 240 |

시점별 후보 패턴 3×라벨 회전 4×계약 2=24행이다. 분할 간 이미지 중복은 없지만 같은 이미지의 파생 행은 독립 표본이 아니다. 학습 대기는 0.5/1.5초, 미학습 조건은 0.8/1.8초와 후보 진입 시간 0.3초 이동이다. paraphrase·unseen_duration은 test 이미지를 재사용한다.

P0에는 대기시간을 제공하지 않아 동일 입력에 계약별 다른 정답이 있을 수 있다. 약 50% 정확도는 모델 능력뿐 아니라 정보 비대칭과 과제 구성의 영향을 받는다. 명시적 제약 제공의 이점을 보여주지만 동일 정보를 제공한 상태에서 검증 알고리즘 자체의 효과를 분리하지 않는다.

### 11.2 조건

| 조건 | 표현 | 역할 |
|---|---|---|
| P0 | 원 CoC, 계약 시간 없음 | 제약 미제공 기준 |
| P1 | 원 CoC+기존 자연어 제약 | 우리의 제약 강화 |
| P2 | 원 CoC+EBLC 생성 CNL | 우리의 정형화 경로 |
| NATURAL_GUARD | 별도 자연어 guard | 표현·배치 대조 |
| SHUFFLED_GUARD | 학습 guard·사례 대응을 섞음 | 올바른 연결의 중요성 |
| LOGIC_GUARD | 논리형 텍스트 | 표현 대조, 내부 solver 아님 |

SHUFFLED_GUARD 시험에는 정상 guard를 제공한다. paraphrase의 P1/P2는 같은 held-out 문구다. P0/LOGIC_GUARD 입력은 변하지 않으므로 그 반복 결과는 추가적인 표현 강건성 증거가 아니다.

### 11.3 모델과 예산

| 설정 | 값 |
|---|---|
| 모델 | Qwen3-VL-2B-Instruct |
| revision | `89644892e4d85e24eaac8bacfd4f463576704203` |
| 초기화 | 같은 pretrained base, 과거 adapter 재사용 없음 |
| 시드 | 42, 17, 123 |
| LoRA | rank 8, alpha 16, dropout 0.05 |
| 적용 | language attention q/k/v/o projection |
| optimizer | AdamW, lr 0.0002, weight decay 0.01 |
| batch | 2×accumulation 8=effective 16 |
| 예산 | 3 epochs, 조건·시드당 180 updates |
| 수치·attention | bfloat16, SDPA |
| loss | assistant 정답 토큰만 |
| checkpoint | 최종 고정 예산, validation/test 선택 없음 |

실제 이미지 processor와 LoRA 갱신을 사용했다. 전체 vision encoder 학습은 아니다. examples·updates는 같지만 prompt 길이가 달라 토큰 수·FLOPs까지 동일하지는 않다. 총 18 fits, 3,240 updates다. [동결 설정](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-expansion-protocol-2026-09-29-001/protocol.json)과 [학습 코드](../experiments/paper1_cnl_learning/train_temporal_expansion.py)가 근거다.

## 12 지표와 통계

| 지표 | 정의 | 주의 |
|---|---|---|
| 정확도 | 최적 허용 후보와 일치 | 허용과 최적은 다름 |
| 위반율 | entry < clear+duration인 진입 | 충돌률 아님 |
| 점유 중 진입 | entry < clear | 전체 위반의 일부 |
| 목표 완료율 | 진입 후보 선택 | 위반 진행도 포함 |
| 준수·목표 달성 | 위반 없이 진입 | safe는 모델 내 준수 의미 |
| deadlock | 진행 가능하지만 대기 | 제한된 정지 과잉 |
| coverage | 유효 라벨 출력 | 무응답 확인 |
| 계약쌍 정확도 | 같은 사례의 두 계약 모두 정답 | 240행은 120쌍 |

세 시드 평균과 모집단 SD(ddof=0)를 보고한다. 조건부 95% CI는 clear-time cluster를 2,000회 bootstrap한다. 후보·회전·계약쌍은 같은 cluster에 유지한다. 3시드·10개 test cluster이므로 광범위한 환경·모델 모집단의 CI나 정형적 비열등성 검정이 아니다.

확장 평가의 coverage·목표 완료는 모두 100%, deadlock은 0%다. 이때 준수·목표 달성은 위반율의 보수이므로 독립적인 여러 개선 증거처럼 세지 않는다. 허용되지만 최적이 아닌 선택은 정확도·진행 손실로 구별한다.

## 13 주 성능 비교

### 13.1 확장 test

단위 %, 평균±시드 SD. 시드당 240행이다.

| 조건 | 정확도 | 위반율 | 준수·목표 달성 | 계약쌍 |
|---|---:|---:|---:|---:|
| P0 | 49.861 ± 0.196 | 19.167 ± 5.803 | 80.833 ± 5.803 | 0.000 ± 0.000 |
| P1 | 96.806 ± 1.712 | 1.389 ± 1.678 | 98.611 ± 1.678 | 93.611 ± 3.425 |
| P2 | 98.056 ± 1.534 | 0.833 ± 0.680 | 99.167 ± 0.680 | 96.111 ± 3.068 |

P0 대비 P1 정확도는 +46.944%p, 위반은 −17.778%p다. P2 정확도는 +48.194%p, 위반은 −18.333%p다. P2 대 P1 test 위반 차이는 0.556%p로 작고 준수·목표 달성 paired CI는 0을 포함한다. 두 제약 방식의 이점을 중심으로 해석하며 P2의 모든 조건 통계적 우월성을 주장하지 않는다.

### 13.2 시드별 test

| 시드 | 조건 | 정확도 | 위반율 | 준수·목표 달성 |
|---|---|---:|---:|---:|
| 42 | P0 | 49.583 | 25.000 | 75.000 |
| 42 | P1 | 97.083 | 0.000 | 100.000 |
| 42 | P2 | 96.250 | 0.833 | 99.167 |
| 17 | P0 | 50.000 | 11.250 | 88.750 |
| 17 | P1 | 94.583 | 3.750 | 96.250 |
| 17 | P2 | 100.000 | 0.000 | 100.000 |
| 123 | P0 | 50.000 | 21.250 | 78.750 |
| 123 | P1 | 98.750 | 0.417 | 99.583 |
| 123 | P2 | 97.917 | 1.667 | 98.333 |

P2가 P1보다 모든 시드에서 좋지는 않다. [마감 보고서](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-experiment-closure-2026-09-29-001/REPORT_KO.md)와 [전체 시드·SD·CI CSV](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-experiment-closure-2026-09-29-001/all_primary_metrics.csv)를 근거로 사용한다.

### 13.3 최신 표현·시간 변화

| 평가 | 조건 | 정확도 | 위반율 | 준수·목표 달성 | 계약쌍 |
|---|---|---:|---:|---:|---:|
| paraphrase | P0 | 49.861 | 19.167 | 80.833 | 0.000 |
| paraphrase | P1 | 90.556 | 5.000 | 95.000 | 81.111 |
| paraphrase | P2 | 96.944 | 1.250 | 98.750 | 93.889 |
| unseen_duration | P0 | 49.861 | 18.472 | 81.528 | 0.000 |
| unseen_duration | P1 | 96.667 | 2.222 | 97.778 | 93.333 |
| unseen_duration | P2 | 96.667 | 1.528 | 98.472 | 93.333 |

같은 합성 과제의 정해진 변형이다. 새 도시·날씨·카메라·교통 맥락의 일반화가 아니다. 시각 근거에 충실한 이해와 실제 도로 일반화는 이 결과만으로 확립되지 않는다.

## 14 여섯 조건의 보충 수치

세 시드 평균(%). 앞 절의 P0/P1/P2 test·변화 조건과 함께 네 평가 묶음 전체를 구성한다.

| 평가 | 조건 | 정확도 | 위반율 | 준수·목표 달성 | 계약쌍 |
|---|---|---:|---:|---:|---:|
| validation | P0 | 49.861 | 17.917 | 82.083 | 0.000 |
| validation | P1 | 97.222 | 1.944 | 98.056 | 94.444 |
| validation | P2 | 98.194 | 0.694 | 99.306 | 96.389 |
| validation | NATURAL_GUARD | 98.750 | 0.556 | 99.444 | 97.500 |
| validation | SHUFFLED_GUARD | 50.694 | 19.722 | 80.278 | 3.611 |
| validation | LOGIC_GUARD | 99.306 | 0.139 | 99.861 | 98.611 |
| test | NATURAL_GUARD | 98.056 | 1.111 | 98.889 | 96.111 |
| test | SHUFFLED_GUARD | 50.556 | 19.722 | 80.278 | 3.333 |
| test | LOGIC_GUARD | 99.167 | 0.139 | 99.861 | 98.333 |
| paraphrase | NATURAL_GUARD | 93.889 | 0.000 | 100.000 | 87.778 |
| paraphrase | SHUFFLED_GUARD | 51.250 | 19.028 | 80.972 | 3.889 |
| paraphrase | LOGIC_GUARD | 99.167 | 0.139 | 99.861 | 98.333 |
| unseen_duration | NATURAL_GUARD | 98.611 | 0.556 | 99.444 | 97.222 |
| unseen_duration | SHUFFLED_GUARD | 50.972 | 18.889 | 81.111 | 3.611 |
| unseen_duration | LOGIC_GUARD | 81.250 | 0.833 | 99.167 | 62.500 |

SHUFFLED_GUARD는 올바른 제약 연결의 중요성을 보여준다. LOGIC_GUARD는 canonical에서 높지만 미학습 시간 정확도가 낮아진다. NATURAL_GUARD가 일부 지표에서 P2보다 좋으므로 모든 표현에서 P2가 일관되게 우월하다고 쓰지 않는다.

## 15 명세 기반 비용 학습

같은 시드 P2 adapter에서 CE_ONLY와 CE_EBLC를 각각 60 updates 추가 학습했다. optimizer를 재설정하고 데이터 순서·토큰 수·파라미터·updates를 맞췄다. PRE_ADAPTER는 추가 학습 전 모델이다. clear 12.0–12.9초의 별도 합성 이미지 10개에서 세 묶음을 각각 240행 평가했다.

```text
L = L_CE + λ × Σ_a p(a) cost(a)
cost(a) = 1 × constraint_violation(a) + 0.25 × deadlock(a)
CE_ONLY: λ=0       CE_EBLC: λ=1
```

확률은 네 후보 토큰의 정규화 확률이다. 미분 가능한 보조 loss이며 정책 gradient RL·환경 상호작용 강화학습·추론 시 shield가 아니다. [비용 프로토콜](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-cost-protocol-2026-09-29-001/protocol.json)에 설정이 있다.

| 평가 | 조건 | 정확도 | 위반율 | 준수·목표 달성 | 계약쌍 |
|---|---|---:|---:|---:|---:|
| canonical | PRE_ADAPTER | 99.028 | 0.417 | 99.583 | 98.056 |
| canonical | CE_ONLY | 99.167 | 0.556 | 99.444 | 98.333 |
| canonical | CE_EBLC | 98.333 | 0.000 | 100.000 | 96.667 |
| paraphrase | PRE_ADAPTER | 95.972 | 1.944 | 98.056 | 91.944 |
| paraphrase | CE_ONLY | 97.639 | 1.806 | 98.194 | 95.278 |
| paraphrase | CE_EBLC | 96.250 | 0.139 | 99.861 | 92.500 |
| unseen_duration | PRE_ADAPTER | 96.944 | 1.528 | 98.472 | 93.889 |
| unseen_duration | CE_ONLY | 98.611 | 1.250 | 98.750 | 97.222 |
| unseen_duration | CE_EBLC | 98.889 | 0.139 | 99.861 | 97.778 |

canonical에서는 위반이 0.556→0%로 낮아졌지만 정확도도 99.167→98.333%로 낮아졌다. paraphrase에서도 같은 절충이 나타난다. unseen_duration은 위반 감소와 정확도 소폭 증가다. 위반 비용과 최적 선택의 절충으로 해석한다. canonical 위반 차이 CI는 −1.25~0%p, 정확도 차이 CI는 −2.222~0.556%p다. 무위반 관측은 확률 0의 보장이 아니다.

## 16 추가 행동 지표와 처리 시간

결과 열람 후 정의한 탐색적 분석이지 사전 주 지표가 아니다. test 세 시드 합계 720행이다.

| 조건 | 준수 선택 수 | 준수 선택 내 진행 손실 | 전체 유효 진행 손실 % | 위반 수 | 위반당 조기 진입 초 |
|---|---:|---:|---:|---:|---:|
| P0 | 582 | 7.096 | 24.652 | 138 | 0.960 |
| P1 | 710 | 0.331 | 1.686 | 10 | 0.910 |
| P2 | 714 | 0.231 | 1.045 | 6 | 0.700 |
| NATURAL_GUARD | 712 | 0.119 | 1.222 | 8 | 1.000 |
| SHUFFLED_GUARD | 578 | 6.955 | 25.050 | 142 | 0.964 |
| LOGIC_GUARD | 719 | 0.070 | 0.202 | 1 | 0.100 |

준수 선택 내 손실은 최적 허용 후보의 점수에서 선택 점수를 뺀 값으로 준수 선택만 분모로 한다. 전체 유효 손실은 위반·무응답의 진행을 0으로 두는 정규화 복합 지표다. 조기 진입은 max(0, clear+duration−entry)를 위반 사례에서 평균한다. 진행은 실제 거리, 조기 진입은 충돌 위험 크기가 아니다. 조건별 분모 차이도 명시한다.

CPU 시간은 고유 binding 48개를 두 경로에서 각 3회 측정했다. compile-and-solve 평균 3.462ms·중앙값 3.524ms·p95 3.782ms, 컴파일 재사용 solve 평균 2.322ms·중앙값 2.368ms·p95 2.621ms였다. 초기화·모델·영상·I/O를 제외한 값이지 차량 전체 지연 보장이 아니다. [추가 지표 보고서](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-secondary-metrics-2026-09-29-001/REPORT_KO.md)에 전체 평가가 있다.

## 17 사전 판정과 보고 초점

확장 프로토콜은 모든 시드의 P2 대 P0 개선 20%p를 요구했고 원판정은 NOT_SUPPORTED다. 비용 실험은 canonical 위반 2%p 감소를 요구했으나 CE_ONLY가 이미 0.556%여서 감소 여지가 부족했고 INCONCLUSIVE다. 설정과 판정을 유지한다.

이는 실행 중단·개선 부재가 아니라 지정 크기 기준 미충족이다. 결과 열람 후 모든 크기의 결과를 보고하고 P0/P1/P2·검사 가능성 중심으로 집필하기로 한 결정과 사전 기준을 구분한다. 날짜·verdict를 덮어쓰지 않는다. 본문 또는 보충에 효과 크기·불확실성과 보고 초점 변경을 명시한다.

## 18 주장과 근거의 경계

| 주장 | 근거 | 경계 |
|---|---|---|
| 제약 구조를 제안한다 | 요소·스키마·프로파일 | 완전한 교통 규칙 분류 아님 |
| 검증·테스트 경로를 제공한다 | Core/SMT·경계·oracle | source·현실 안전 증명 아님 |
| P1/P2가 P0보다 정확하고 준수한다 | 최신 동일 예산 비교 | 합성·평가 시 규칙·정보 비대칭 |
| P2는 높은 수준을 유지한다 | 주·변화 평가 | 모든 시드·표현 우월 아님 |
| 지원 오류를 탐지한다 | 144/144 주입 오류 | 공유 source 오류 미탐 |
| 비용으로 위반 감소 경향을 보인다 | CE 대 CE+cost | 정확도 절충·작은 headroom·RL 아님 |
| 실제 장면 연결을 설명한다 | #18 | 주 효과·자동 추출 검증과 별도 |

“검증 때문에 모델이 좋아졌다”, “CoC 전체가 옳다”, “실차 안전성을 검증했다”, “모든 표현에 우월하다”, “실제 영상에서 전자동으로 정확히 추출했다”, “Alpamayo 학습 효과를 입증했다”는 현재 근거를 넘는다.

## 19 관련 연구의 연결 축

이번 패키지는 새 문헌 조사 결과가 아니다. 기존 인용도 투고 전 원문·서지를 확인하며 최초성·외부 방법 대비 우월성을 새로 단정하지 않는다.

| 축 | 비교 질문 | 우리 위치 |
|---|---|---|
| CoC·VLM 운전 판단 | 설명과 행동 제한의 차이 | 명시적 제약 대상으로 확장 |
| 자연어 규칙 행동 선택 | 규칙 제공 효과 | P1은 우리 계열, P0 대비 비교 |
| 형식 명세·monitoring·테스트 | 어떤 의미·oracle인가 | 조건·해제·불확실성과 CNL |
| 제약 학습·비용·shield | 어디서 제한하는가 | supplied-CNL·보조 loss, shield 아님 |

범용 EBLC 언어 독립 검증 전체는 별도 프로젝트다. 이 논문에는 사용 프로파일·컴파일·검사 사례를 제시한다. 언어 논문의 모든 증명 의무나 Studio 제품 개발을 함께 넣지 않는다.

## 20 본문과 보충자료 구성

본문 순서는 Introduction → Constraint model → Method → Experimental setup → Results → Discussion → Conclusion이다. 설명만 있는 CoC의 문제, 요소, 실행 예제, 최신 P0/P1/P2, 검사 품질을 연결한다.

| 자산 | 내용 | 배치·준비 상태 |
|---|---|---|
| 그림 1 | 흐름과 검증 대상 구분 | 본문; 5절 기반 제작 필요 |
| 표 1 | 요소와 실행 대응 | 본문; 4절 축약 |
| 그림 2 | clear·두 계약·후보·경계 | 본문; 7절 수치로 제작 가능 |
| 표 2 | 데이터·모델·예산 | 본문; 11절 |
| 표 3 | P0/P1/P2·SD | 본문; 13.1절 |
| 표 4 | 표현·시간 변화 | 본문; 13.3절 |
| 표 5 | 오류 주입·정상·공유 source | 본문; 9.1절 |
| 표 6 | 비용의 위반·정확도 절충 | 본문 또는 보충; 15절 |
| 부록 A | schema/Core/SMT/CNL | 코드·검사 artifact |
| 부록 B | 여섯 조건·시드·CI·사전 판정 | 원 CSV |
| 부록 C | 추가 지표·시간 | 원 결과 |
| 부록 D | 실제 #18 근거 연결 | 이미지 권한 확인 전 텍스트·도식 |

제작 예정 그림을 완성 자산으로 세지 않는다. 실제 모델 사례를 넣을 때는 예측 JSONL에서 고정 선정 기준으로 입력·예측·참조·검사를 제시한다. 7절 설명 예제를 모델 성공 사례로 바꾸지 않는다.

과거 adapter의 일반화 실패 표는 본문·보충 표 계획에 추가하지 않는다. 원자료는 보존한다. 최신 결과의 합성 환경·시각 근거 미확립·실제 도로 미검증 한계는 유지한다. 실차·궤적·Alpamayo·국가별 법규·대규모 자동 주석·Studio 완성은 후속 개발이며 기존 설문 전체 재수행도 이 패키지의 요구가 아니다.

## 21 재현 자료 색인

본문에는 의미 있는 출처 이름을 사용하고 해시는 manifest에 남긴다.

| 자료 | 역할 |
|---|---|
| [기존 원고](main.tex) | 이전 초안 |
| [범위 결정](../docs/decisions/PAPER1_METHOD_PRESERVATION_AND_LABELING_DECISION_V01.md) | 합성 주 실험·실제 장면 후속 |
| [정성적 설계](../docs/designs/PAPER1_ACTION_CONTRACT_DESIGN_V01.md) | UNKNOWN·다중 의무 |
| [시간 계약 코드](../experiments/paper1_cnl_learning/temporal_preservation.py) | 계약·Core·CNL |
| [D4 원 보고서](../../../artifacts/projects/guardsynth-coc/public/paper1-temporal-diversity-001/diversity-analysis-2026-09-29-001/REPORT_KO.md) | 제약 품질 |
| [데이터 설정](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-training-data-2026-09-29-001/protocol.json) | 분할·후보·시간 |
| [확장 동결 설정](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-expansion-protocol-2026-09-29-001/protocol.json) | 예산·기준 |
| [확장 결과](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-expansion-learning-2026-09-29-001/RESULT.json) | 조건·시드·CI |
| [확장 manifest](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-expansion-learning-2026-09-29-001/RUN_MANIFEST.json) | 추적 |
| [비용 설정](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-cost-protocol-2026-09-29-001/protocol.json) | loss·대조 |
| [비용 결과](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-cost-learning-2026-09-29-001/REPORT_KO.md) | 효과·절충 |
| [추가 지표](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-secondary-metrics-2026-09-29-001/REPORT_KO.md) | 진행·조기 진입·시간 |
| [통합 CSV](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-experiment-closure-2026-09-29-001/all_primary_metrics.csv) | 평균·SD·시드·CI 전량 |
| [마감 manifest](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-experiment-closure-2026-09-29-001/RUN_MANIFEST.json) | 마감 시 296개 근거 파일 확인 |
| [실제 장면 예제](examples/SCENE18_PIPELINE_EXAMPLE_REPORT_V01.md) | 실제 CoC·관측·규범 연결 |

재현은 원 run을 덮어쓰지 않고 새 owner-scoped artifact run에서 수행한다. 패키지 작성으로 학습을 재시작하지 않는다. GPU·라이브러리 버전은 과거 실행 기록에서 확인하고 현재 환경으로 대신 적지 않는다. 코드·model revision·분할·prompt·adapter·예측·집계를 공개 가능한 범위로 묶는다.

## 22 투고 전 남은 집필 작업

현재 자료로 방법과 통제 실험 중심 초안을 작성할 수 있다. 다음은 제출물 완성 작업이지 실험 확대 목록이 아니다.

- 제목·초록·기여와 최신 결과를 main.tex에 통합한다.
- 방법 도식·시간 예제 그림을 제작하고 캡션에 분모·시드·단위를 적는다.
- 주요 CI를 원 JSON/CSV에서 인용하고 사전 기준·보고 초점 변경을 기술한다.
- 관련 연구 원문·서지를 확인하며 근거 없는 최초성을 주장하지 않는다.
- 과거 실행 환경을 보충자료에 넣고 GPU·버전을 추정하지 않는다.
- 저자·소속·기여·지원·이해관계·공개 정책·윤리 문구를 사실 확인 후 확정한다.
- 이미지·데이터셋 문장의 공개·인용 조건을 확인하며 restricted 파일은 제출본에 임의 복사하지 않는다.
- 투고 형식으로 개정·컴파일하고 본문·표·부록·참고문헌을 대조한다.

새 대규모 학습·추가 설문은 패키지 완료 조건이 아니다. 더 강한 실제 도로·시각 이해·검증의 인과 효과 주장을 원할 때만 그 주장에 맞는 별도 실험이 필요하다.

## 23 IEEE Access 원고 준비

이 한글 패키지와 그 PDF는 집필 기초자료이며 제출용 영문 원고가 아니다. IEEE Access는 공식 템플릿을 사용한 영문 원고와 편집 가능한 Word 또는 LaTeX 파일 및 PDF를 요구한다. 제출 형식은 2단·단일 행간이다. [공식 작성 안내](https://ieeeaccess.ieee.org/authors/preparing-your-article/)와 [제출 안내](https://ieeeaccess.ieee.org/authors/submission-guidelines/)를 기준으로 최종 제출 전에 다시 확인한다. 이번 확인일은 2026-09-29다.

| 원고 구성 | 패키지에서 가져올 내용 | 남은 준비 |
|---|---|---|
| Title·Abstract·Index Terms | 1–2절 | 영문화, 키워드 확정 |
| Introduction·Related Work | 1·3·19절 | 선행 논문 인용과 새 기여 구분 |
| Constraint Model·Method | 4–9절 | 요소 표, 방법 도식, 시간 예제 그림 |
| Experimental Setup | 10–12절 | 실행 환경 기록, 정확한 재현 정보 |
| Results | 13–16절 | 주 비교와 보조 실험 배치 |
| Discussion·Conclusion | 17–18절 | 주장 범위와 보고 초점 반영 |
| Supplement·Reproducibility | 20–21절 | 전체 수치, 코드와 데이터 공개 범위 |

제안 키워드는 Chain of Cognition, behavioral constraints, formal specification, satisfiability modulo theories, controlled natural language, vision-language models이다. 공식 분류어 확인과 최종 선택은 영문 원고 작성 단계에서 한다.

저자·소속·교신저자·지원·이해관계는 추정해 채우지 않는다. 기존 논문과의 관계 및 재사용 자료를 명확히 밝히고 저작권·공개 조건을 확인한다. AI가 생성한 본문·그림·코드 등을 원고에 사용한다면, 사용 시스템과 해당 부분·사용 범위를 acknowledgments에 공개해야 한다는 [IEEE Access 지침](https://ieeeaccess.ieee.org/authors/preparing-your-article/)을 반영한다. 구체적인 공개 문구는 실제 사용 내역과 저자의 확인을 거쳐 작성한다.
