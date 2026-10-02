# EBLC 언어 및 양방향 검증 독립 연구계획 v1

- 프로젝트: `eblc-language-verification`
- 문서 계층: `01` 최상위 연구계획
- 상태: `RESEARCH_PLANNING`
- 하위 마일스톤: [02_PROJECT_MILESTONES.md](02_PROJECT_MILESTONES.md)
- 실행 관리: [03_PROJECT_EXECUTION_TRACKER.md](03_PROJECT_EXECUTION_TRACKER.md)
- 관련연구: [RELATED_WORK_SURVEY_V01.md](../surveys/RELATED_WORK_SURVEY_V01.md)
- 연구 헌장: [RESEARCH_CHARTER.md](../charter/RESEARCH_CHARTER.md)
- 평가 요구사항: [INDEPENDENT_EVALUATION_REQUIREMENTS.md](../requirements/INDEPENDENT_EVALUATION_REQUIREMENTS.md)
- 재사용 구현: [`platforms/eblc-bcv/`](../../../../platforms/eblc-bcv/)

## 1. 연구 목적

EBLC(Evidence-Bound Lifecycle Contract)를 GuardSynth의 내부 구현 요소가 아니라 독립적인
계약 표현과 검증 workflow로 평가한다. 핵심은 개별 기능의 존재가 아니라 evidence binding,
typed derivation, lifecycle, composition, multi-target lowering과 bidirectional mutation
검증이 하나의 추적 가능한 의미 체계를 구성하는지 확인하는 것이다.

## 2. 연구 질문

- RQ1 Representation: EBLC는 단순 schema, flat guard set 또는 비교 계약 표현보다 evidence,
  derivation, lifecycle, conflict와 fallback을 더 명시적으로 표현하는가?
- RQ2 Traceability: source에서 clause와 compiled assertion까지 provenance를 손실 없이
  추적할 수 있는가?
- RQ3 Semantic preservation: canonical evaluator, runtime monitor, Core와 SMT target의 판정이
  명시된 finite scope에서 일치하는가?
- RQ4 Bidirectional verification: BCV는 의도적으로 주입한 과소제약, 과잉제약 및 번역 오류를
  각각 검출하는가?
- RQ5 Cost and limits: 표현력과 검증 가능성의 대가로 발생하는 authoring, compilation 및
  solver 비용과 실패 유형은 무엇인가?

## 3. 조건부 중심 주장

다음 주장은 선행연구 감사와 locked evaluation gate를 모두 통과할 때만 사용한다.

> EBLC는 evidence와 lifecycle을 보존하는 typed contract representation과 다중 실행 target의
> 추적 가능한 lowering을 제공하며, BCV는 제한된 범위에서 과소·과잉제약과 번역 불일치를
> 대칭적으로 드러낸다.

“최초”, “완전 검증”, “차량 안전 보장” 또는 “모든 계약 언어보다 우수”는 현재 주장이 아니다.

## 4. 연구 대상과 코드 경계

평가 대상 구현은 [`platforms/eblc-bcv/`](../../../../platforms/eblc-bcv/)의 versioned release다.
플랫폼 코드를 이 프로젝트로 복사하지 않는다. 이 프로젝트는 다음만 소유한다.

- 독립 비교 protocol과 benchmark manifest
- paper-specific baseline adapter와 분석
- locked evaluation 설정 및 project-owned run
- 표, 그림, 통계, 한계 분석과 원고

플랫폼 자체 conformance run은 `artifacts/platforms/eblc-bcv/`에, 독립 논문 실험은
`artifacts/projects/eblc-language-verification/`에 기록한다.

### 4.1 기존 플랫폼 자산의 역할

- [EBLC language specification v0.2](../../../../platforms/eblc-bcv/docs/specifications/EBLC_LANGUAGE_SPEC_V02.md)
- [requirement traceability](../../../../platforms/eblc-bcv/docs/reports/EBLC_REQUIREMENT_TRACEABILITY_V02.md)
- [P0b verification report](../../../../platforms/eblc-bcv/docs/reports/EBLC_P0B_COC_CONSTRAINT_SMT_VERIFICATION_REPORT_V01.md)
- [release notes v0.2](../../../../platforms/eblc-bcv/docs/releases/EBLC_RELEASE_NOTES_V02.md)

이 자산들은 구현 출발점과 development evidence다. Project 05의 독립 baseline 비교,
locked oracle 또는 논문 주 결과를 대신하지 않는다.

## 5. 평가 설계

### 5.1 비교 조건

최종 baseline은 systematic survey 후 동결한다. 최소한 다음 역할을 분리해 비교한다.

- untyped 또는 flat structured guard representation
- temporal/lifecycle 표현이 가능한 비교 형식
- provenance를 별도 metadata로만 보유한 표현
- EBLC without evidence binding, lifecycle, composition 또는 BCV ablation
- full EBLC + BCV

### 5.2 Benchmark unit

하나의 unit은 source/evidence, typed inputs, contract, finite trace 또는 state set, expected
verdict, target outputs와 provenance expectation을 포함한다. development case와 locked test를
분리하고, 수정에 사용한 반례를 locked 결과로 재사용하지 않는다.

### 5.3 주요 지표

- feature/construct coverage와 unsupported rate
- source-to-assertion provenance recovery
- target 간 verdict 및 witness agreement
- mutation class별 precision, recall과 false alarm
- compile/solver time, artifact size와 authoring burden
- ambiguity, missing input, conflict 및 numeric boundary 실패 유형

## 6. 독립성 및 타당성

동일 구현 계통의 evaluator끼리 일치한 사실만으로 의미보존을 결론 내리지 않는다. hand-authored
oracle, direct solver replay 또는 별도 reference evaluator를 locked subset에 사용한다. 비교
언어는 가능한 범위와 불가능한 범위를 함께 기록하고, 더 많은 syntax를 지원한다는 사실만으로
우월성을 주장하지 않는다.

GuardSynth 결과는 application case study로만 사용한다. GuardSynth의 scene grounding이나
constraint synthesis 성능을 EBLC의 언어 기여와 분리한다.

## 7. 성공·피벗 기준

- GO: 선행연구 대비 명확한 차별점, 독립 oracle이 포함된 locked benchmark, target agreement,
  양방향 mutation 검출 및 비용 분석이 모두 확보된다.
- NARROW: 신규성은 제한적이지만 provenance-preserving lowering 또는 BCV 중 하나가 독립적으로
  유효하면 해당 기여로 범위를 축소한다.
- NO-GO: 기존 표현과 실질적 차이가 없거나 독립 평가에서 의미보존·mutation gate를 통과하지
  못하면 독립 논문 주장을 중단하고 플랫폼 engineering report로 유지한다.

## 8. 논문 산출물

논문 구조와 작성 개시 gate는 [paper/README.md](../../paper/README.md)에 둔다. 연구 범위나
성공 기준 변경은 이 문서를 먼저 개정하고 마일스톤과 실행 추적표를 동기화한다.
