# EBLC 독립 평가 요구사항

- 기준 연구계획: [01_RESEARCH_PLAN_V01.md](../plans/01_RESEARCH_PLAN_V01.md)
- 구현 기준선: [`platforms/eblc-bcv/`](../../../../platforms/eblc-bcv/)

## 1. 사전 동결 항목

- 연구 질문과 주장 가능 범위
- 비교 표현 및 baseline 선택 기준
- benchmark unit, train/dev/test 또는 generation/locked-test 분리
- mutation taxonomy와 기대 판정
- 독립 oracle 및 disagreement 처리
- 주요 지표, 통계 방법과 실패·피벗 기준

## 2. 필수 평가 축

| 축 | 최소 요구사항 |
|---|---|
| 표현력 | evidence, derivation, lifecycle, conflict, fallback을 동일 task에서 비교 |
| 추적성 | source-to-clause 및 clause-to-target provenance 회수 가능성 측정 |
| 의미보존 | canonical, runtime, Core 및 SMT target의 locked-case agreement |
| BCV | underconstraint와 overconstraint를 분리한 controlled mutation 평가 |
| 강건성 | malformed, missing, ambiguous 및 boundary input의 fail-closed 동작 |
| 비용 | 모델 크기, compile time, solver time 및 artifact 크기 보고 |

## 3. 독립성 요구사항

1. implementation과 동일한 함수를 oracle로 재사용한 결과만으로 의미보존을 주장하지 않는다.
2. hand-authored expected outcome, direct solver replay 또는 별도 reference evaluator 중 하나
   이상을 locked test에 사용한다.
3. benchmark를 보고 언어 또는 compiler를 수정한 경우 해당 사례는 development set으로
   이동하고 새로운 locked case를 만든다.
4. GuardSynth application outcome은 외적 사례 연구이며 EBLC 언어 자체의 주요 결과와 분리한다.

## 4. 주장 금지

- finite bound 밖의 전역 soundness 또는 completeness
- 실제 교통법규의 정확성이나 차량 안전성
- 비교 대상의 충분한 재구현 없이 얻은 우월성
- controlled mutation recall을 자연 오류 검출 정확도로 대체하는 주장
