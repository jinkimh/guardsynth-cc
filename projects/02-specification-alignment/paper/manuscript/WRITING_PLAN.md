# 논문 2 작성 계획: AI 제어 모델의 Specification Alignment Gap

- 작성일: 2026-08-04
- 목표 분야: 소프트웨어공학, 요구공학, AI engineering, formal methods
- 목표 수준: 국내 SCOPUS 등재 학술지
- 현재 단계: 표현 형식 차이에 대한 초기 3-seed 증거 확보

## 1. 가제

### 권장 영문 제목

**From Natural-Language Constraints to Executable Guards: Evaluating Specification Representations for Vision-Language Control**

### 대안 제목

**The Specification Alignment Gap in AI-Based Control: Natural Language, Structured Guards, and Executable Formal Contracts**

### 한국어 제목

**인공지능 제어 모델의 명세 정렬 격차: 자연어 제약, 구조화 Guard 및 실행 가능한 정형 계약의 실증 비교**

## 2. 피해야 할 과도한 주장

다음 문장을 논문의 최종 주장으로 사용하지 않는다.

> 인공지능은 정형 명세 언어보다 자연어 제약사항에 더 잘 순응한다.

현재 실험의 Logic Guard는 parser나 solver로 실행된 것이 아니라, 정형 문법과 유사한 문자열을 VLM prompt로 입력한 조건이다. 정형 명세는 원래 VLM이 자연어처럼 읽도록 만든 것이 아니라 도구가 결정적으로 실행하도록 만든 언어다.

따라서 정확한 출발 주장은 다음과 같다.

> 자연어 중심으로 사전학습된 VLM은 제한된 adaptation에서 semantically equivalent raw formal text보다 자연어 제약을 더 쉽게 행동 선택에 반영할 수 있다. 반면 실행 가능한 정형 명세는 모델 해석과 독립적으로 결정적 검증을 제공할 수 있다.

## 3. 한 문장 연구 주장

> AI 제어 모델의 명세 준수는 의미 내용뿐 아니라 표현 형식, 정보 위치, 학습량 및 명세 실행 방식에 의존하며, 자연어 기반 의미 정렬과 실행 가능한 정형 검증을 결합한 hybrid architecture가 필요하다.

## 4. 연구 간극

AI 시스템 요구사항은 자연어 prompt, JSON schema, DSL, temporal logic 및 runtime monitor 등 여러 형태로 주어진다. 그러나 같은 의미를 갖는 명세라도 신경 모델이 직접 해석하는 경우의 순응과 외부 도구가 실행하는 경우의 보장은 다르다.

기존 비교에서 흔히 섞이는 요소는 다음과 같다.

- 의미 정보량
- 명세 위치와 delimiter
- token 길이
- 기반 모델의 사전학습 친숙도
- adaptation data와 optimizer update
- raw prompt interpretation과 executable verification

본 논문은 이 요소를 통제해 **specification alignment gap**을 측정한다.

## 5. 연구 질문

- **RQ1 표현:** 의미적으로 같은 제약을 자연어, 구조화 형식 및 논리식으로 제시할 때 VLM의 준수율은 어떻게 달라지는가?
- **RQ2 위치:** Inline 지시문과 별도 Guard field의 차이는 의미가 아니라 정보 위치만으로도 발생하는가?
- **RQ3 학습 효율:** 표현별로 같은 성능에 도달하는 데 필요한 데이터와 optimizer update는 얼마인가?
- **RQ4 일반화:** 표현별 성능은 unseen phrase, numeric value, field order 및 Guard composition에 어떻게 일반화되는가?
- **RQ5 실행:** Raw formal text를 VLM이 직접 읽는 방식과 formal verifier가 실행하는 방식의 오류ㆍ비용 trade-off는 무엇인가?
- **RQ6 Hybrid:** 자연어 conditioning과 executable formal Guard를 결합하면 목표 완료와 결정적 제약 검사를 동시에 달성하는가?

## 6. 현재 초기 증거

STOP–HOLD–RELEASE–GO 합성 과제의 3-seed 결과:

| 표현 | 정확도 | Guard 위반 ↓ | 안전+목표 완료 ↑ | 계약 전환 pair ↑ |
|---|---:|---:|---:|---:|
| Requirement-only | 0.500 ± 0.000 | 0.319 ± 0.052 | 0.681 ± 0.052 | 0.000 ± 0.000 |
| Inline natural language | 1.000 ± 0.000 | 0.000 ± 0.000 | 1.000 ± 0.000 | 1.000 ± 0.000 |
| Separate natural language | 0.698 ± 0.094 | 0.191 ± 0.136 | 0.809 ± 0.136 | 0.396 ± 0.187 |
| Raw logic text | 0.538 ± 0.027 | 0.274 ± 0.108 | 0.726 ± 0.108 | 0.076 ± 0.055 |
| Shuffled guard | 0.510 ± 0.015 | 0.333 ± 0.023 | 0.667 ± 0.023 | 0.021 ± 0.029 |

이 결과는 다음 가설을 만든다.

1. 기반 VLM은 자연스러운 지시문 위치의 제약을 가장 쉽게 학습한다.
2. 별도 Guard field는 의미 신호가 있지만 adaptation 안정성이 낮다.
3. 임의 Logic Guard 문자열은 형식 적응 없이 직접 실행되기 어렵다.
4. 성능 차이는 정형 명세의 표현력보다 모델–명세 인터페이스 정렬 문제일 수 있다.

Unseen-time에서는 Inline의 안전 목표 완료도 0.649로 하락했고 별도 자연어 Guard는 0.573이었다. 따라서 ID 성능과 수치 규칙 일반화를 구분해야 한다.

## 7. 제안하는 명세 표현 조건

모든 조건은 동일한 의미 predicate와 threshold를 사용한다.

### R0. Requirement-only

현재 제약 정보를 생략한 하한 baseline이다.

### R1. Inline free-form natural language

```text
Proceed after the conflict zone has remained clear for at least 1.5 seconds.
```

### R2. Separate natural-language field

```text
<requirement>Proceed through the intersection.</requirement>
<guard>Remain stopped until clear_duration >= 1.5 seconds.</guard>
```

### R3. Controlled Natural Language

```text
IF conflict_zone is occupied THEN ego SHALL HOLD.
Ego MAY ENTER ONLY IF clear_duration is at least 1.5 seconds.
```

### R4. JSON schema

```json
{
  "invariant": "ego_before_stop_line",
  "release": {"clear_duration_s": {"gte": 1.5}},
  "fallback": "hold"
}
```

### R5. Compact DSL

```text
HOLD WHILE occupied(conflict_zone)
RELEASE IF clear_duration_s >= 1.5
FALLBACK HOLD
```

### R6. STL/temporal logic as raw text

```text
G(occupied -> before_stop_line)
G(enter -> clear_duration >= 1.5)
```

### R7. Executable formal verifier

VLM은 trajectory 후보를 생성하거나 ranking하고, parser/monitor가 R6 명세를 실제로 실행해 violating candidate를 거부한다.

### R8. Hybrid

R1 또는 R3로 VLM을 condition하고, R7 verifier로 최종 허용성을 검사한다.

## 8. 공정 비교 통제

1. 모든 조건의 predicate, threshold, scene, candidate 및 target을 동일하게 유지한다.
2. 자연어와 구조화 표현의 정보량이 같은지 자동 검사를 둔다.
3. Prompt 내 위치와 field order를 교차 배치한다.
4. Token 길이 차이를 기록하고 필요 시 length-matched control을 둔다.
5. 각 표현에 같은 training example 수와 optimizer update를 제공한다.
6. Seed를 최소 3–5개 사용한다.
7. Shuffled semantics, irrelevant text 및 missing-field control을 포함한다.
8. Raw formal text와 executable verifier를 별도 조건으로 보고한다.

## 9. 추가 실험

### E1. Learning curve

- 24, 72, 144, 288 optimizer updates
- 정확도보다 contract-swap 및 safe-goal의 수렴 속도를 비교
- 목적: 표현 친숙도와 최종 표현 능력을 분리

### E2. Field-position ablation

- CoC 앞, CoC 뒤, system field, 별도 delimiter
- Guard field 이름 변경
- 목적: 정보 위치 prior 측정

### E3. Format adaptation

- format instruction pretraining
- Guard special token
- schema-to-action auxiliary task
- 자연어–DSL 의미 대응 학습

### E4. Generalization

- unseen threshold interpolation/extrapolation
- unseen field order
- unseen natural paraphrase
- unseen Guard conjunction
- 일부 predicate 누락과 contradiction

### E5. Executable verifier

- Candidate별 predicate trace 생성
- STL 또는 직접 monitor로 만족 여부 계산
- VLM 선택 전후 위반률과 false rejection 비교
- Verifier latency와 intervention rate 보고

### E6. Model generality

최소 두 모델 family에서 반복한다.

- Qwen3-VL-2B
- 다른 소형 공개 VLM 1종

동일 tokenizer family만 사용하면 자연어 친숙도 결론의 일반성이 약해질 수 있다.

## 10. 주요 지표

- Specification compliance rate
- Safe goal completion
- Contract-swap pair accuracy
- Sample efficiency: 목표 성능까지 필요한 update 수
- Format robustness: field order와 delimiter 변화 민감도
- Semantic robustness: paraphrase와 equivalent formula 민감도
- Numeric generalization
- False rejection / false acceptance
- Executable verifier intervention rate
- Inference 및 verification latency

## 11. 예상 결과와 해석 규칙

### 시나리오 A: 자연어가 적은 update에서만 우세

해석: 기반 모델의 pretraining prior에 따른 sample-efficiency 차이이며 표현력의 본질적 우위가 아니다.

### 시나리오 B: 충분한 adaptation 후 모든 prompt 형식이 수렴

해석: 명세 형식 차이는 학습 가능한 interface alignment 문제다.

### 시나리오 C: Raw logic text는 약하지만 executable verifier는 정확

해석: 자연어와 정형 명세는 경쟁 관계가 아니라 각각 semantic conditioning과 deterministic enforcement 역할을 가진다.

### 시나리오 D: Hybrid가 가장 높은 safe-goal과 낮은 위반 달성

해석: AI-enabled system의 요구사항 전달과 runtime assurance를 분리한 architecture가 타당하다.

## 12. 논문의 핵심 기여

1. AI 제어에서 동일 의미 명세가 표현ㆍ위치ㆍ실행 방식에 따라 다른 행동을 만드는 specification alignment gap을 정의한다.
2. 의미를 고정하고 표현만 바꾸는 controlled benchmark를 제안한다.
3. 명세 표현별 sample efficiency와 일반화를 정량화한다.
4. Prompt-interpreted formal text와 executable formal specification을 명확히 구분한다.
5. 자연어 conditioning과 deterministic verifier를 결합한 hybrid architecture를 평가한다.
6. 동일 명세 변환에 대한 metamorphic testing 방법을 제안한다.

## 13. 논문 구성

1. **Introduction**
   - AI 시스템에서 명세 표현 문제
   - Natural language와 formal specification의 역할 차이
2. **Background and Related Work**
   - Requirements engineering for AI
   - Natural-language constraints and prompt conditioning
   - Formal specification, runtime verification, STL
   - Neuro-symbolic and hybrid assurance
3. **Specification Alignment Gap**
   - 의미, 표현, 위치, 실행의 분해
   - 연구 질문과 formal definitions
4. **Controlled Benchmark**
   - Semantics-fixed representation transforms
   - Temporal driving micro-world
   - Metamorphic contract swaps
5. **Approaches**
   - Raw prompt representations
   - Format adaptation
   - Executable verifier
   - Hybrid architecture
6. **Experimental Design**
   - Models, budgets, seeds, splits, metrics
7. **Results**
   - Representation, sample efficiency, generalization
   - Verifier와 hybrid 결과
8. **Discussion for Software Engineering**
   - Requirements authoring과 runtime assurance implications
9. **Threats to Validity**
10. **Conclusion**

## 14. 표와 그림 계획

### 그림

1. Specification alignment gap 개념도
2. 의미 고정ㆍ표현 변환 pipeline
3. Prompt interpretation 대 executable verification
4. Hybrid natural-language + formal verifier architecture
5. 표현별 learning curve
6. Generalization heatmap

### 표

1. 명세 표현 taxonomy
2. 관련 연구 비교
3. 의미 동등성 및 token 통계
4. 표현별 ID 준수 결과
5. 학습량별 sample efficiency
6. 일반화 결과
7. Raw logic, executable logic, hybrid 비교
8. 오류 유형 및 metamorphic test 결과

## 15. 주장 경계

### 주장 가능 조건

- 의미와 학습량을 통제한 뒤 표현에 따른 차이가 재현됨
- 최소 두 모델 family에서 방향성이 유지됨
- Raw logic과 executable logic을 분리해 보고함

### 주장 불가

- “자연어가 정형 명세보다 본질적으로 우수하다”
- “정형기법은 AI에 부적합하다”
- “합성 micro-world 결과가 모든 AI 소프트웨어에 일반화된다”
- “VLM의 자연어 준수가 실제 안전을 보장한다”

## 16. 완료 기준

- [x] 초기 Inline/Separate/Logic 3-seed 결과
- [x] Specification alignment gap 가설 정립
- [ ] CNL, JSON, DSL 조건 구현
- [ ] Learning curve 실험
- [ ] Field-position ablation
- [ ] Executable verifier 조건
- [ ] Hybrid 조건
- [ ] 두 번째 VLM family 재현
- [ ] 통계 검정 및 effect size
- [ ] 선행연구 체계적 정리
- [ ] 전체 원고 작성
- [ ] Claim audit
- [ ] 목표 저널 형식 적용

## 17. 근거 자료

- `../../docs/reports/TEMPORAL_GUARD_MULTISEED_EXPERIMENT_REPORT_V01.md`
- `../../docs/reports/SAFETY_CONSTRAINED_COC_PROGRESS_REPORT_V01.md`
- `../../artifacts/results/public/small-vlm-guard-v0/temporal-guard-multiseed-v0/`
- `../../projects/01-safety-constrained-coc/experiments/vlm_guard_learning/temporal_guard_world.py`
- `../../projects/01-safety-constrained-coc/experiments/vlm_guard_learning/train_qwen_temporal_guard_lora.py`

