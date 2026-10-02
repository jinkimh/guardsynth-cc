# EBLC Language Verification 연구 헌장

## 1. 연구 책임

이 프로젝트는 EBLC의 독립 연구 질문, 비교 평가, 논문별 분석과 원고를 소유한다. 재사용
언어 구현, Core lowering, runtime monitor, BCV 및 SMT/Z3 코드는
[`platforms/eblc-bcv/`](../../../../platforms/eblc-bcv/)가 계속 소유한다.

## 2. 중심 연구 질문

EBLC의 typed evidence binding, lifecycle semantics, composition 및 multi-target lowering은
단순한 계약 표현보다 추적 가능하고 검증 가능한 이점을 제공하는가?

## 3. 포함 범위

- 기존 계약·규칙 표현과의 기능 및 의미론 비교
- evidence와 derivation provenance의 보존 평가
- lifecycle, composition, conflict 및 fallback 표현력 평가
- canonical semantics와 Core/runtime/SMT target 사이의 의미보존 평가
- BCV의 controlled underconstraint·overconstraint·translation mutation 검출 평가
- 복잡도, 실행 비용, 실패 사례 및 적용 한계 분석

## 4. 제외 범위

- GuardSynth의 scene retrieval, rule applicability 또는 제약 합성 성능을 EBLC 자체 기여로 주장
- bounded 검증 결과를 실제 차량 안전성 증명으로 해석
- 플랫폼 구현과 같은 코드에서 파생한 oracle만으로 독립 검증을 주장
- systematic prior-art audit 전에 EBLC 명칭이나 신규성을 확정

## 5. 소유권 경계

플랫폼의 재사용 가능한 변경은 소비 프로젝트의 versioned requirement와 함께
`platforms/eblc-bcv/`에 구현한다. 이 프로젝트는 paper-specific protocol, baseline adapter,
analysis, figure, table 및 manuscript만 소유한다.
