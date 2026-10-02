# Safety-Constrained CoC 논문 포트폴리오 계획

- 작성일: 2026-08-04
- 목표: 국내 SCOPUS 등재 학술지 논문 2편
- 공통 기반: Alpamayo-R1 CoC 분석, Qwen3-VL-2B Guard 학습 실험, 합성 micro-world

## 1. 논문 구성

| 구분 | 논문 1 | 논문 2 |
|---|---|---|
| 가제 | Safety-Constrained CoC | Specification Alignment Gap |
| 중심 분야 | 자율주행 AI, VLM, AI safety | 소프트웨어공학, 요구공학, 정형기법 |
| 중심 질문 | CoC에 안전 제약을 추가하면 목표를 유지하며 위반을 줄이는가? | 동일 제약의 표현ㆍ실행 방식에 따라 AI 순응이 어떻게 달라지는가? |
| 핵심 독립변수 | Guard 유무, maneuver 유형 | Inline NL, separate NL, CNL/JSON/DSL, raw logic, executable logic |
| 핵심 지표 | Guard 위반, safe-goal, deadlock, progress | 준수율, sample efficiency, 표현/수치 일반화, verifier 보장 |
| 핵심 메시지 | Safety-Constrained CoC는 목표 보존형 제약 준수를 향상시킨다 | 자연어는 모델 정렬에, 정형 명세는 결정적 실행에 유리하며 hybrid가 필요하다 |

## 2. 중복 방지 원칙

1. 논문 1은 Guard 표현 형식 비교를 주요 기여로 삼지 않는다. 검증된 최선의 표현을 사용해 maneuver coverage와 안전 목표 완료 효과를 평가한다.
2. 논문 2는 자율주행 maneuver 성능 자체보다 의미적으로 동일한 명세의 표현 통제 실험을 중심으로 한다.
3. 공통 micro-world와 일부 baseline은 사용할 수 있지만, 주표ㆍ주그림ㆍ연구 질문과 결론은 분리한다.
4. 동일 수치를 양 논문의 주된 신규 결과로 중복 제시하지 않는다. 한 논문에서는 배경 또는 사전 연구로 인용한다.
5. 논문 1의 데이터는 `maneuver × guard presence`, 논문 2의 데이터는 `semantics-fixed × representation × training budget` 구조로 관리한다.

## 3. 작성 순서

1. 논문 1을 우선 완성한다.
   - 현재 정적ㆍ시간적 결과가 가장 강하다.
   - `CRUISE → STOP`과 `LANE CHANGE → COMPLETE/ABORT`를 추가한다.
   - 국내 저널 투고 후 `paper1-safety-constrained-coc/INTERNATIONAL_JOURNAL_EXPANSION_PLAN.md`에 따라 폐루프 국제 저널 연구로 확장한다.
2. 논문 2의 공정한 형식 비교를 수행한다.
   - raw logic text와 executable formal verifier를 반드시 구분한다.
   - 학습량 곡선과 최소 2개 모델을 추가한다.
3. 각 논문의 실험 revision과 source table을 별도로 고정한다.

## 4. 공통 주장 제한

- 실제 차량 안전이나 충돌률 감소를 주장하지 않는다.
- 합성 후보 선택을 연속 제어 안전 보장으로 표현하지 않는다.
- 자연어 Guard가 완전한 안전 명세라고 주장하지 않는다.
- raw formal text에 대한 VLM의 낮은 순응을 정형기법 자체의 실패로 해석하지 않는다.
- Alpamayo-R1 zero-shot 결과는 반응성 진단으로만 사용한다.

## 5. 계획 문서

- 논문 1: `paper1-safety-constrained-coc/WRITING_PLAN.md`
- 논문 1 국제 확장: `paper1-safety-constrained-coc/INTERNATIONAL_JOURNAL_EXPANSION_PLAN.md`
- 논문 2: `paper2-specification-alignment/WRITING_PLAN.md`
