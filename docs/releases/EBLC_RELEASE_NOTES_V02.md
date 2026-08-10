# EBLC v0.2 release candidate notes

Release: `EBLC-v0.2-rc1`  
Decision: `FEATURE_COMPLETE_SCOPED_RELEASE_CANDIDATE`

## 포함 기능

- evidence-bearing program v0.2와 fail-closed schema/parser
- canonical lifecycle, 별도 runtime target, bounded Z3 checker
- typed Core v0.1 및 일반 Core→SMT compiler
- source-bearing arithmetic derivation DAG와 stopping-distance output
- non-scalar multi-contract priority/action composition
- fail-closed indexed actor-zone collection
- canonical/Core-SMT generated conformance와 BCV mutation suite
- deterministic `EBLC-CNL-EN-v0.1` one-way prompt projection

## 호환성

program v0.1과 bundle v0.1은 계속 지원한다. program v0.2가 현재 권장 단위다.
CNL은 새 실행 문법이 아니므로 interpreter/compiler의 입력 형식은 바뀌지 않는다.

## 동결 규칙

RC 이후 v0.2에는 결함 수정, 설명 보강 및 의미를 바꾸지 않는 호환성 작업만 허용한다.
새 exception algebra, quantifier, hybrid dynamics 또는 자동 NL generator는 v0.2에 조용히
추가하지 않는다. 의미 변경은 별도 버전과 conformance 기준선이 필요하다.

검증 수치와 artifact는 RC 실행 후
`artifacts/results/public/eblc-release-candidate-001/eblc-v0.2-rc1-2026-08-09/`에
고정한다. 이 release는 연구용 bounded software semantics이며 실제 법규나 차량 안전
인증물이 아니다.
