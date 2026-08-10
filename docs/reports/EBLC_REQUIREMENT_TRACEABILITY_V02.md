# EBLC v0.2 요구사항–구현 추적표

이 표는 EBLC를 무기한 확장하지 않기 위한 release boundary다. `SUPPORTED`는 공개
bounded v0.2 범위에서 구현·테스트됨을 뜻하며 실제 차량 안전성을 뜻하지 않는다.

| ID | 요구사항 | 상태 | 구현/경계 |
|---|---|---|---|
| REQ-TRUTH | 4값 fact truth | SUPPORTED | `types.py`, `semantics.py` |
| REQ-EPISTEMIC | evidence epistemic kind | SUPPORTED | `types.py`, `program.py` |
| REQ-VERDICT | 4개 verdict | SUPPORTED | `types.py`, `semantics.py` |
| REQ-LIFECYCLE | activation/maintain/release/reactivate/expiry | SUPPORTED | `semantics.py`, `elaborator.py` |
| REQ-RULE | source/version/scope/precondition/exception RuleTemplate 표현 | SUPPORTED | `types.py`, rule schema |
| REQ-BINDING | target-zone binding과 ambiguity | SUPPORTED | `binders.py`, `indexed_collection.py` |
| REQ-PARTIAL | Value/Interval/Set/Unsupported 결과 | SUPPORTED | `types.py`, `binders.py` |
| REQ-OBSERVABILITY | freshness/failure-to-UNKNOWN | SUPPORTED | `semantics.py`, `elaborator.py` |
| REQ-EVIDENCE | evidence ref와 typed derivation DAG | SUPPORTED | `derivation.py`, `program.py` |
| REQ-PRIORITY | non-scalar priority/action 합성 | SUPPORTED | `composition.py`, `bundle_elaborator.py` |
| REQ-CORE-SMT | high-level → Core → bounded SMT | SUPPORTED | `elaborator.py`, `smt_compiler.py` |
| REQ-TARGETS | canonical/runtime/Z3 agreement | SUPPORTED | `translation_validator.py`, `conformance.py` |
| REQ-BCV | under/over mutation witness | SUPPORTED | `mutations.py` |
| REQ-MULTI | multi-contract/indexed actor-zone | SUPPORTED | `composition.py`, `indexed_collection.py` |
| REQ-CNL | deterministic EBLC→CNL | SUPPORTED | `cnl_renderer.py`, mapping/hash test |
| REQ-STRUCTURED-GENERATOR | structured source-aware input→indexed collection | SUPPORTED_NEXT_LAYER | `src/guard_synth/source_aware_generator.py` |
| REQ-EXCEPTION-ALGEBRA | 일반 exception 실행 대수 | DEFERRED_V0_3 | field 표현은 지원, 일반 실행은 이관 |
| REQ-QUANTIFIERS | unbounded collection/quantifier | OUT_OF_SCOPE_V0_2 | finite indexed collection 사용 |
| REQ-HYBRID | continuous/hybrid/unbounded time | OUT_OF_SCOPE_V0_2 | bounded discrete semantics |
| REQ-NL-GENERATOR | CoC/NL→source-grounded EBLC | NEXT_LAYER_GUARDSYNTH | EBLC 언어가 아닌 생성 계층 |
| REQ-REAL-ASSURANCE | 실제 association/profile source authoring | DATA_ADAPTER_GAP | 추정/default 금지 |
| REQ-SAFETY-PROOF | 독립 vehicle-safety proof | NOT_CLAIMED | 독립 evaluator와 실제 보장 필요 |

## Release 판정

문법과 compiler의 완료 판정은 **`FEATURE_COMPLETE_SCOPED_RELEASE_CANDIDATE`**다.
즉 v0.2로 선언한 bounded vertical-slice 범위는 닫되, 표의 이관 항목을 완료한 것처럼
주장하지 않는다. `RuleTemplate + ContextGraph + VehicleProfile → indexed collection`
구조화 GuardSynth v0.1은 별도 계층에서 구현되었고 EBLC RC 의미를 변경하지 않는다.
free-form CoC/NL parser와 실제 source authoring은 여전히 후속 범위다.

언어 정의는 [EBLC v0.2 명세](../specifications/eblc/EBLC_LANGUAGE_SPEC_V02.md), 재현 절차는
[사용자 가이드](../guides/eblc/EBLC_USER_GUIDE_V02.md)를 참조한다.
