# 장면 #18: CoC에서 제약 명세·검증·CNL·학습 데이터 구성까지

- project_id: `guardsynth-coc`
- 작성일: 2026-09-08
- 용도: 방법 설명용 상세 예제, 논문 부록/보충자료의 초안
- 상태: **실제 source + 수작업 조건부 명세 + 실행된 bounded SMT 검사 + 학습 데이터 미리보기**
- 상위 범위: [1차 논문/2차 개발 분리](../../docs/decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)
- 본문용 요약: [영문 LaTeX 삽입문](scene18-worked-example.tex)
- 재현 코드: [worked_example.py](../../experiments/paper1_cnl_learning/worked_example.py)
- 실행 자료: [화면](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper-worked-example-001/scene18-pipeline-example-2026-09-08-002/worked_example.html), [RESULT](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper-worked-example-001/scene18-pipeline-example-2026-09-08-002/RESULT.json), [manifest](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper-worked-example-001/scene18-pipeline-example-2026-09-08-002/RUN_MANIFEST.json)

## 1. 이 예제가 보여주는 것과 보여주지 않는 것

핵심 질문은 원본의 짧은 운전 이유를 그대로 반복하는 대신, 제약의 대상·조건·금지 행동·
유지·해제·다른 의무와의 관계를 명시하고, 그 논리를 검사한 후 자연어 supervision으로
전달하는 과정을 어떻게 설명할 것인가이다.

```text
원본 CoC + 사건 영상 + CASCADE 주석 + 외부 규범 참조
    → 기존 관찰을 활용한 제약 후보와 적용 조건 정리
    → EBLC 구조의 설계 초안 / 수작업 논리식 대응
    → Z3 검사: 일관성, 반례, UNKNOWN 정책 누락
    → 조항별 CNL 대응문
    → 원본 CoC + CNL + 독립 행동 정답의 학습 구조 미리보기
```

위 화살표를 모두 자동 실행했다고 주장하지 않는다. 특히 다음 경계를 본문에서도 유지한다.

| 구분 | 실제 수행 | 미수행/제한 |
|---|---|---|
| CoC 확보 | 데이터셋에 이미 존재하는 문장을 exact clip/timestamp로 읽음 | 이번 이미지에서 VLM으로 새 CoC 생성하지 않음 |
| 제약 추출 | 기존 설문 상태→공통 초안 템플릿, CoC 단어 패턴, source ID/interval 연결 | 영상·법규를 종합하는 학습된 자동 추출기 미완성 |
| 명세 | 설명용 EBLC 구조와 논리식을 수작업 작성 | 기존 `eblc-program-v0.1/v0.2` parser가 받는 실행 명세 아님 |
| 검증 | Z3 4.16.0, 추상 판단 3단계, 실제 11개 질의 | 영상 해석·법적 적용·metric 안전·무한 시간 안전 증명 아님 |
| CNL | 명세 조항과 수작업 대응한 문장을 고정 순서로 조립 | 기존 범용 renderer 실행이나 독립 의미보존 평가 아님 |
| 학습 삽입 | 원본/강화 target 구성의 JSON 미리보기 | action gold 미확정, finalized target=null, export=false, 학습 미실행 |

따라서 제목/캡션에는 **worked illustration**, **conditional specification** 또는
**bounded logical check**를 사용한다. “자동 추출 성공 사례”, “검증된 실제 주행 정답”,
“EBLC 학습 효과 입증”으로 소개하지 않는다. 이 자료 작성으로 M12/M14/M16/M18/M20을
완료 처리하지 않으며, 종전 strict60 eligible 1/60과 새 cohort 미판정도 바뀌지 않는다.

## 2. 입력 장면과 원본 CoC

### 2.1 정확한 식별자

| 필드 | 값 |
|---|---|
| 기존 영상 설문 번호 | #18 · PEDESTRIAN_CYCLIST_YIELD |
| 이미지 파일의 폴더 번호 | `geometry/event-026/` — 설문 번호와 다름 |
| clip ID | `a508e4e3-1381-462a-ad65-cf938a438187` |
| 사건 시점 | `9,788,430 µs = 9.788430 s` |
| upstream split | `train` — 독립 test로 재표기하지 않음 |
| source-linked 보행자 후보 | `Agent3` |
| 원본 reasoning event frame | 99 |
| 디코딩된 검토 영상의 기준 frame index | 297 |

마지막 두 frame index는 동일한 번호 체계라고 가정하지 않는다. 현재 연결 키는 clip ID와
timestamp이며, 선택된 실제 프레임 시각은 실행 `source_example.json`에 따로 기록한다.
이 파일 대응은 PhysicalAI/CASCADE 시계 정렬의 독립 실측 검증을 대신하지 않는다.

### 2.2 표시 이미지

![장면 #18의 기준 시점 기계 표시 이미지](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001/m16-geometry-candidate-2026-09-05-v1/geometry/event-026/frame-p0000-overlay.jpg)

야간, 전방의 보행자와 도로/차량이 보이는 장면이다. 녹색은 기계가 제안한 road 영역이며,
에고 차로·횡단 충돌 영역·보행자 위치의 정답 마스크가 아니다. 단일 그림만으로 횡단의
전체 궤적, 충돌 관계, 정지 거리, 주도로 차량의 우선권을 확정하지 않는다.

이 이미지는 **방법 설명/검토용**이다. 학습 입력에는 녹색 표시나 기존 답변을 넣지 않고,
판단 시점까지의 원본 영상만 사용하도록 별도 sampling 계약을 정해야 한다. 원본 이미지와
영상은 restricted 저장소에 남겨 두었으며 공개 논문에 실을 권한은 아직 확인되지 않았다.
공개 제출 전 재사용 조건·출처 표기를 검토하고 필요하면 비식별 도식으로 대체한다.

### 2.3 원본 CoC

> Yield to the traffic on the main road and keep a safe distance from the pedestrian crossing the road.

번역: “주도로의 교통에 양보하고, 도로를 건너는 보행자와 안전한 거리를 유지한다.”

원문은 `data/restricted/nvidia_physicalai/reasoning/ood_reasoning.parquet`의 해당 event에
이미 존재한다. 우리의 기여는 이 문장 자체의 작성이 아니라, 그 문맥에서 필요한 제약을
근거에 따라 명시·검사하여 supervision을 보강하려는 것이다. 위 문장은 CLAIMED 설명이며
모든 장면 사실이나 최적 행동의 독립 정답이 아니다.

## 3. 외부 근거와 관찰의 역할

### 3.1 근거 목록

| ID | 출처 | 이 예제에서 사용할 수 있는 내용 | 자동으로 따라오지 않는 결론 |
|---|---|---|---|
| S1 | 원본 CoC event | 보행자 보호와 주도로 양보라는 행동 이유의 후보 | 실제 충돌 존재, 양보 적용 확정 |
| S2 | 원본 영상/검토 프레임 | 관측을 점검할 시각 자료 | 녹색 영역=정답 충돌 zone |
| S3 | 기존 사람 설문 | `CLEAR_VISIBLE`, `HAZARD_VISIBLE`이라는 전후 시간창 관찰 | t0 truth, 거리/해제 시각, 독립 action gold |
| S4 | CASCADE 원본 주석 | Agent3와 행동 ID, 선언된 interval 및 ego causal link | 사람의 실제 동일성·trajectory·규범적 안전 정답 |
| S5 | 1968 도로교통협약 제21조 | 보행자를 위험하게 하는 행동 회피와 조건부 횡단 의무의 규범적 참조 | 어느 국가의 국내법 준수, 모든 횡단 상황에서 동일 STOP, 수치 정지거리 |
| P1 | 이 예제의 연구용 설계 선택 | lifecycle, UNKNOWN 처리, 영역 진입이라는 추상 행동과 조합 정책 | 협약에 쓰인 그대로의 문장, 이미 승인된 실행 정책 |

S5의 공식 참조는 [UNECE 협약 원문, Article 21](https://unece.org/DAM/trans/conventn/Conv_road_traffic_EN.pdf)이다.
프로젝트의 연결 기록은 기존 treaty audit을 사용한다. 조문의 조건부 의무를 적용하려면
횡단시설·통제 상태 등의 전제가 추가로 확인되어야 한다. 제21조를 주도로 차량 양보의
포괄적 법적 근거로 사용하지 않는다. 이 예제의 C5는 CoC에서 제기된 별도 의무가 **확인될
경우를 가정한 조합 규칙**이지, 주도로 우선권을 제21조로 증명한 것이 아니다.

### 3.2 CASCADE에서 실제로 연결된 내용

원본 파일:
`8d209566-1d20-4876-a4dd-e1040909521a__a508e4e3-1381-462a-ad65-cf938a438187.json`

- Agent3: `Pedestrian (Adult)`; `AgentAction3 = oxd:Walk`, interval 0.0–18.6초.
- `EgoAction2 = fst:Yield`, interval 8.8–15.3초.
- EgoAction2의 `because_of` 참조에 AgentAction3가 포함된다.
- 사건 시점 9.788430초는 두 선언 interval 안에 있다.

이는 “이 시점의 주석에서 ego 행동과 person source가 연결됨”이라는 결과다. 다른 참조가
모두 시점상 유효하다고 일반화하지 않으며, unique source-linked person도 reviewer가
Agent3의 신원을 직접 확인했다는 뜻은 아니다. 대상의 keypoint는 다른 시점에 있으므로
그 점을 t0의 위치나 polygon으로 복사하지 않는다.

원본 파일/CoC/영상/표시 이미지의 SHA-256과 실제 값은
[source_example.json](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper-worked-example-001/scene18-pipeline-example-2026-09-08-002/source_example.json)과 run manifest에 기록한다.

## 4. 필요한 행동 제약 후보 만들기

### 4.1 지금까지 실제 구현한 추출

1. clip ID와 event timestamp가 정확히 일치하는 CoC·관찰·source를 연결한다.
2. CoC의 `pedestrian`, `crossing` 등의 단어 패턴을 문맥 flag로 기록한다.
3. 기존 `HAZARD_VISIBLE` 답변에 공통 `CONDITIONAL_CONFLICT_ENTRY_RESTRICTION` 템플릿을 대응한다.
4. 원본 주석의 대상과 시점, 다른 통제 문맥을 추적한다.

18건의 조건부 초안은 18가지 독립적으로 발견한 규칙이 아니라, 관찰 상태에 맞춘 공통
템플릿의 사건별 대응이다. image-to-constraint 또는 law-to-constraint 모델 정확도는
아직 평가하지 않았다. 이 제한은 논문 예제의 자동화 정도를 설명할 때 반드시 남긴다.

### 4.2 이 장면에서 설명할 제약 후보

> 대상 보행자와 에고의 진행 경로 사이에 충돌 관계가 유효한 근거로 확인되어 유지되는
> 동안, 해당 충돌 영역에 진입하지 않는다. 충돌 해소가 확인되면 보행자 제약을 해제한다.
> 보행자 제약이 해제되어도 별도로 확인된 주도로 양보 의무는 유지한다.

이 문장은 CoC만의 논리적 귀결이 아니다. 영역/행동 정의와 운영 정책 P1이 추가된
**연구용 조건부 구체화**다. `ENTER_CONFLICT_ZONE`과 `WAIT_OUTSIDE`는 방법 설명용
행동이며 실제 차량의 throttle/brake 제어나 이미 동결된 학습 행동 후보가 아니다.

| 명세 필드 | 예제 값 | 상태 |
|---|---|---|
| subject | ego | 역할 식별 |
| target candidate | Agent3 | 원본 source 연결, 시각적 동일성 미확정 |
| conflict zone | UNBOUND | 의미 영역과 source binding 미확정 |
| activation predicate | pedestrian_conflict | predicate 정의/관측 근거 계약 필요 |
| current predicate truth | UNKNOWN | 기존 시간창의 HAZARD_VISIBLE을 t0 TRUE로 승격하지 않음 |
| restricted action | ENTER_CONFLICT_ZONE | 연구용 추상 행동 설계 |
| release | valid evidence of clearance | 현재 해제 시각/근거 없음 |
| other obligation | main-road yield, if confirmed | 적용 여부 미확정 |

## 5. EBLC 구조와 논리 명세

### 5.1 실행 가능성 구분

[eblc_design_draft.json](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper-worked-example-001/scene18-pipeline-example-2026-09-08-002/eblc_design_draft.json)은
EBLC의 binding/evidence/predicate/lifecycle/constraint/composition 구조에 대응한 **설계 투영**이다.
기존 platform의 수치 stopping program은 zone position, response time, deceleration 등을
요구하므로 이 정성적 JSON을 기존 parser에 입력해 성공했다고 주장할 수 없다.
이번 Z3 실행은 아래 식을 직접 작성한 것이며 EBLC frontend/translation correctness는 미검증이다.

### 5.2 기호와 범위

| 기호 | 뜻 |
|---|---|
| `p_t` | 보행자 충돌 여부: TRUE / FALSE / UNKNOWN / CONFLICT |
| `v^p_t` | 대상·시점 등을 포함한 보행자 근거가 유효하다는 추상 전제 |
| `r_t` | 주도로 양보 의무 여부: 같은 네 값 |
| `v^r_t` | 주도로 근거 유효성 전제 |
| `a_t` | 이번 판단 후 보행자 의무 활성 여부 |
| `a_prev` | 직전 활성 상태; t=0 이전 상태는 자유 입력 |
| `e_t` | 해당 판단에서 충돌 영역으로 진입하는 행동 |
| `q_t` | 보행자 관련 검토 필요 flag |

유효성 Boolean은 영상에서 측정한 값이 아니며 단위/허용 age를 대신하는 구현도 아니다.
확인된 값의 논리적 효과를 검사하는 전제다. UNKNOWN과 CONFLICT는 FALSE와 다르다.
시간은 `t=0,1,2`의 **추상 판단 세 단계**이며 #18의 실제 세 프레임을 뜻하지 않는다.

### 5.3 조항 C1–C5

```text
C1: on_t    := valid_p_t AND (p_t = TRUE)
    clear_t := valid_p_t AND (p_t = FALSE)

C2: active_t := IF on_t THEN TRUE
               ELSE IF clear_t THEN FALSE
               ELSE previous_active_t

C3: review_t := (p_t = CONFLICT)
               OR (NOT(on_t OR clear_t) AND NOT previous_active_t)

C4: active_t → NOT enter_t

C5: (valid_r_t AND r_t = TRUE) → NOT enter_t
```

C2는 제약 해제 후에도 같은 전이식을 적용하므로 재확인된 충돌에서 재활성화한다.
CONFLICT에서 기존 상태를 유지하고 검토를 요구하는 것은 이 수작업 모델의 해석 선택이며
범용 EBLC semantics의 완전한 구현을 선언하는 것이 아니다. C3는 검토 flag를 계산할 뿐
진입을 금지하지 않는다. 이 차이가 실제 반례로 드러난다.

수치 정지거리, 물리 제어 가능성, 상대 속도, 다중 actor의 공간 관계는 이 모델에 없다.
따라서 `a_t → ¬e_t`가 성립해도 실제 차가 안전하게 멈출 수 있음을 증명하지 못한다.

## 6. Z3에 넣은 입력과 결과

### 6.1 재현 명령

저장소 루트에서 실행한다. 기존 ID는 덮어쓰지 않으므로 다음 실행은 새 ID를 사용한다.

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/worked_example.py --run-id scene18-pipeline-example-2026-09-08-003
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p test_paper_worked_example.py -v
```

생성 run에는 각 질의의 `.smt2`와 `_premises.smt2`가 별도로 있다. 어떤 compatible SMT-LIB
solver에서도 재검사할 수 있다. 기록한 결과는 Z3 Python 4.16.0 기준이다. solver가 달라져도
SAT/UNSAT는 비교할 수 있지만 자유 변수의 구체적인 SAT witness는 달라질 수 있다.

### 6.2 질의 방법

각 사례에서 `B = C1–C5 + domain + 해당 시나리오 전제`를 먼저 검사해 SAT인지 확인한다.
그 후 `B AND 검사할 상황`을 검사한다. 모든 사례의 전제가 SAT였으므로, 아래 UNSAT는
불가능한 전제 때문에 자동으로 성립한 공허한 결과가 아니다. 다만 코드가 입력 명세를
충실하게 옮겼다는 독립적인 증명까지 되는 것은 아니다.

예: 충돌 확인 시 진입 가능성을 묻는 SMT-LIB 핵심은 다음과 같다. 실제 전체 3단계 입력은
run의 `q02_conflict_entry.smt2`에 보존한다.

```lisp
; 아래는 전체 파일이 아니라 추가하는 반례 조건이다.
; TRUE는 정수 0, FALSE=1, UNKNOWN=2, CONFLICT=3으로 인코딩한다.
(assert (= ped_truth_0 0))
(assert ped_evidence_valid_0)
(assert enter_conflict_zone_0)
(check-sat) ; UNSAT, 기존 C1–C5가 이미 assertion으로 들어 있는 경우
```

### 6.3 실제 결과

| 질의 | 검사할 경우 | 결과 | 해석 |
|---|---|---|---|
| Q01 | 기본 명세의 만족 가능성 | SAT | 내부 모순으로 모두 막히지는 않음 |
| Q02 | 유효한 충돌 확인 + 진입 | UNSAT | 입력된 진입 금지와 양립 불가 |
| Q03 | 기존 활성 + UNKNOWN → 해제 | UNSAT | 판단 불가만으로 기존 의무를 해제하지 않음 |
| Q04 | 기존 활성 + 유효하지 않은 FALSE → 해제 | UNSAT | 오래되거나 부적합한 clear 전제로 해제하지 않음 |
| Q05 | 유효한 clear → 해제하면서 대기 | SAT | 해제가 출발을 강제하지 않음 |
| Q06 | 보행자 clear + 확인된 주도로 양보 + 진입 | UNSAT | 다른 의무를 보행자 해제가 무효화하지 않음 |
| Q07 | TRUE → FALSE → TRUE인데 재활성화 안 함 | UNSAT | 명시한 전이 모델에서 재활성화 누락 불가 |
| Q08 | 두 의무 모두 유효한 FALSE + 진입 | SAT | 이 제한된 모델의 정상 진행 가능성 |
| Q09 | 이전 비활성 + 보행자 UNKNOWN + 검토 필요 + 진입 | SAT | **미정 정책의 반례** |
| Q10 | 보행자 clear + 주도로 의무 UNKNOWN + 진입 | SAT | **다른 의무 미확인의 반례** |
| Q11 | C4를 제거한 모델에서 충돌 확인 + 진입 | SAT | 진입 금지 mutation이 위반을 노출 |

총 11개 질의 중 SAT 6 / UNSAT 5, 전제 SAT 11이다. 이는 정확도나 “6개 실패/5개 성공”
비율이 아니다. 가능해야 할 시나리오와 불가능해야 할 반례를 서로 다르게 물었다.
Q11만 C4를 제거한 mutant이며 기본 명세의 결과와 섞지 않는다.

### 6.4 UNKNOWN 반례의 구체적 해석

Q09의 t0 witness:

```text
previously_active = FALSE
ped_truth_0 = UNKNOWN
ped_evidence_valid_0 = TRUE
road_yield_required_0 = FALSE
road_evidence_valid_0 = TRUE
ped_active_0 = FALSE
ped_review_required_0 = TRUE
enter_conflict_zone_0 = TRUE
```

유효한 근거가 “판단할 수 없음”을 보고할 수 있으므로 valid=true와 UNKNOWN은 모순이
아니다. 기존 비활성 상태를 유지하는 C2와 진입만 검사하는 C4 사이에서, C3의 review flag는
진입을 차단하지 않는다. 결과는 “이런 주행이 안전하다”가 아니라 **현재 명세로는 이것을
금지할 수 없다**는 뜻이다. Q10도 main-road UNKNOWN을 TRUE 의무로 보지 않기 때문에 남는다.

이 빈틈을 채우는 선택은 “review 필요 시 진입 보류”, “모든 관련 clear 확인 시에만 진입”,
“더 나은 관측을 얻는 행동” 등일 수 있다. 그러나 어떤 선택이 적절한지는 과제·관측 가능성·
정상 진행 손실을 함께 검토해야 한다. 이 예제는 몰래 보수 정책을 추가해 성공으로 만들지
않는다. 정책 수정 후에는 Q09/Q10뿐 아니라 Q08 같은 정상 진행 사례도 재검사해야 한다.

## 7. 의미를 보존하도록 구성한 CNL 대응

### 7.1 생성 방식

`worked_example.py`의 `CLAUSES`에는 C1–C5의 식과 영문 문장을 사람이 짝지어 작성했다.
runner는 이 목록을 고정 순서로 조립하고
[cnl_correspondence.json](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper-worked-example-001/scene18-pipeline-example-2026-09-08-002/cnl_correspondence.json)에 저장한다.
따라서 **deterministic assembly of manually authored clause pairs**이다. 자동으로 의미를
증명하는 번역기나 platform의 기존 CNL renderer가 실행된 것으로 기술하지 않는다.

### 7.2 실제 생성 문자열

```text
[C1] A pedestrian conflict is confirmed if and only if its truth is TRUE and its evidence is valid. Conflict clearance is confirmed if and only if its truth is FALSE and its evidence is valid.
[C2] Activate the pedestrian obligation when conflict is confirmed. Deactivate it when clearance is confirmed. Otherwise retain its previous activation state. Apply this rule again at each decision, including after release.
[C3] Mark review as required when pedestrian evidence is conflicting, or when neither conflict nor clearance is confirmed and the previous activation state is inactive. Otherwise do not set this review flag.
[C4] While the pedestrian obligation is active, do not enter the conflict zone.
[C5] Do not enter the conflict zone when a main-road yielding obligation is confirmed by valid evidence, regardless of the pedestrian obligation's activation state.
```

### 7.3 의미 대응 점검표

| 보존할 요소 | CNL 대응 | 금지할 의미 변경 |
|---|---|---|
| evidence validity | C1의 valid evidence | CoC나 존재만으로 conflict TRUE |
| positive/negative predicate | TRUE와 FALSE의 별도 조건 | 안 보임=FALSE |
| state retention | C2의 otherwise retain | UNKNOWN이면 항상 해제/항상 새 의무 활성화 |
| reactivation | C2의 including after release | 한 번 해제되면 계속 진행 허가 |
| review flag | C3의 mark review | 원래 식에 없는 review→진입 금지를 추가 |
| prohibition | C4의 do not enter | 단순 주의 권고로 약화 |
| independent obligation | C5의 regardless | 보행자 해제=전체 PROCEED |

이 표는 저자의 조항 대응 설명이며 독립 reviewer의 fidelity 평가 결과가 아니다.
특히 현재 명세의 UNKNOWN 빈틈을 CNL에서 조용히 고치면 원래 명세와 의미가 달라진다.
안전 정책 수정은 명세→재검증→CNL 재생성 순으로 해야 한다.

## 8. CoC 학습 데이터에 삽입하는 구체적 예

### 8.1 입력과 정답 출력의 분리

모델 입력은 원본 영상, 질문, 동일 행동 후보다. 원본 CoC와 CNL은 assistant supervision에
들어가며, 정답 CNL을 user prompt나 평가 시 외부 guard로 주지 않는다.

```text
USER INPUT (설명용 구성)
  visual: clip a508e4e3-...의 판단 시점 9.788430초까지 원본 프레임
  question: Explain the scene and relevant constraints, then select an action.
  choices (아직 동결되지 않은 예):
    A: Wait outside the conflict zone
    B: Enter the conflict zone

ASSISTANT TARGET COMPONENTS
  COC: 원본 문장 (수정하지 않음)
  CONSTRAINTS: C1–C5 CNL (강화 조건에만 추가)
  ACTION: 독립 판정이 들어갈 자리 — 현재 null
```

정답이 없는 자리에 WAIT를 채우거나 `UNRESOLVED`를 임의의 학습 label로 넣지 않는다.
최종 assistant 문자열은 `null`이다. 이 예제의 실제 이미지를 붙인 synthetic action 정답도
만들지 않았다. 모든 관련 근거가 확보되고 독립 행동 정답이 생긴 후에만 finalized target을
조립하고 export해야 한다.

### 8.2 원본과 강화 구성의 비교

| 구성 | 공통 input | assistant target |
|---|---|---|
| 원본 구성 미리보기 | 원본 영상 + 같은 질문/행동 후보 | 원본 CoC + 동일 독립 action |
| 강화 구성 미리보기 | 완전히 같은 input | 원본 CoC + C1–C5 CNL + 동일 독립 action |

이는 L0와 L3가 비교할 데이터 형태를 설명하지만 **현재 미리보기를 validated L3 sample로
세지 않는다**. 실제 실험에는 L1(동일 source 직접 NL), L2(동일 renderer·검증 생략)도 필요하다.
L0/L3만으로 EBLC 검증 고유의 효과를 주장할 수 없고 CNL 추가에 따른 target token/loss/compute
차이도 동결·통제해야 한다.

### 8.3 생성된 JSON의 중요 필드

```json
{
  "status": "ILLUSTRATIVE_NOT_TRAINABLE",
  "learning_export_allowed": false,
  "action_gold": null,
  "finalized_assistant_target": null,
  "is_validated_L3_example": false,
  "original_target_components": {"coc": "원본 문장", "action": null},
  "enriched_target_components": {"coc": "동일 원본 문장", "constraints": "C1–C5 문장", "action": null}
}
```

위는 필드 설명용 발췌이며 전체 실제 값은
[training_example_preview.json](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper-worked-example-001/scene18-pipeline-example-2026-09-08-002/training_example_preview.json)에 있다.
자동화된 tests는 원본 CoC의 동일성, action/finalized target의 null, export 차단, SMT-LIB
재입력 결과, source hash, 98개 geometry 번호와 설문 번호의 차이 등을 검사한다.

## 9. 본문에는 무엇을 남기고 무엇을 부록으로 옮길까

본문은 [영문 요약](scene18-worked-example.tex)의 약 1쪽 규모 methods illustration을 사용한다.
이 파일은 투고 양식이 정해지기 전 삽입 가능한 snippet이며 전체 원고가 아니다.

- 본문: 원본 CoC 한 문장, 5단계 대응표, 핵심 논리식, 대표 UNKNOWN 반례와 현재 한계.
- 부록: 본 문서의 source/ID·시간·조항 C1–C5·CNL 대응·전체 query/미리보기 구조.
- 재현 패키지: 실행 코드, 22개 SMT-LIB 입력, RESULT/manifest, 반례 witness, CNL/preview JSON.
- restricted 자료: 원본 영상·이미지·주석과 해시. 공개 재배포는 별도 승인/조건 확인 후 결정.

권장 한글 본문 요약:

> 실제 개발 장면의 원본 CoC는 주도로 교통에 양보하고 횡단 보행자와 안전거리를 유지할
> 것을 설명한다. 우리는 기존 영상 관찰과 사건 시점의 구조화 주석을 연결하고, 보행자
> 보호 규범을 참조하여 조건부 영역 진입 제약을 예시한다. 명세는 근거 유효성, 활성화·
> 유지·해제, 진입 금지와 별도 양보 의무를 구분한다. 수작업 논리 모델의 3단계 Z3 검사에서
> 확인된 충돌 중 진입과 다른 양보 의무 무시는 불가능했지만, 초기 UNKNOWN 상태와 다른
> 의무 미확인 상태의 진입은 배제되지 않았다. 각 조항을 대응하는 자연어 문장으로 구성해
> 원본 CoC에 추가하는 supervision 구조를 제시한다. 이는 자동 추출·실제 영상 안전성·
> 독립 CNL 충실성·학습 효과의 검증 결과가 아니며, 미확정 정책과 행동 정답 때문에 학습
> export를 차단한 방법 설명용 예제다.

권장 이미지 캡션(이미지 공개 권한 확인 후):

> 방법 설명용 개발 장면 #18. 원본 CoC와 사건 timestamp로 연결된 프레임을 보인다.
> 녹색은 기계 road 후보이며 검증된 ego lane/충돌 zone이 아니다. 원본 scene과 조건부
> 명세를 연결하는 과정을 설명하기 위한 그림으로, ground-truth 안전 행동을 제시하지 않는다.

## 10. 이 예제가 실제 논문 증거가 되기 위한 남은 작업

1. 선택한 행동 제약 subset과 적용/예외/UNKNOWN 정책을 확정하고 source 요구를 정의한다.
2. target/zone/event predicate를 근거로 연결한다. 현재 설문을 무조건 반복하지 않는다.
3. 실제 EBLC frontend/검증/동일 CNL renderer 경로를 구현하고 수작업 모델과의 대응을 검증한다.
4. UNKNOWN 반례를 정책적으로 처리하면서 정상 진행 가능성을 다시 검사한다.
5. 독립 action gold와 CNL fidelity 검토, 노출 이력·clip split·sampling 계약을 확보한다.
6. L0–L3의 동일 base data/action/예산 학습과 독립 held-out 행동 평가를 실행한다.

이 절차를 거치기 전에는 이 예제를 학습 효과 결과 표나 성공률 분자에 포함하지 않는다.

## 11. 편집·재현 메모

001 run은 보존했고, C1의 정의가 필요충분조건임을 CNL에서도 명확히 하기 위해
`only when`을 `if and only if`로 고친 002 run을 현재 예제로 사용한다. 논리식과 SAT/UNSAT
집계는 동일하다. 문장 수정 자체를 독립 의미보존 검증으로 세지는 않는다.
Q08의 SAT는 적어도 한 진행 모델의 존재이며 모든 실행의 진행 보장이나 실제 영상의
nominal-success 측정은 아니다.
