# GuardSynth 대한민국 P0 source catalog 요구사항

- work package: `GS-P0-CATALOG-001`
- milestone: M12
- 선행 결정: [대한민국 범위 결정](../../decisions/GUARDSYNTH_KR_SCOPE_AND_SOURCE_POLICY_V1.md)
- locked 범위: 15개 template, 세 deep slice, 여섯 broad family

## 1. 산출물

1. `src/guard_synth/schemas/source_catalog.schema.json`
2. `src/guard_synth/fixtures/source_catalog_kr_v0_1.json`
3. `src/guard_synth/source_catalog.py`
4. catalog audit 단위 테스트와 공개 실행 artifact

기존 단일 synthetic P0b catalog와 generator fixture는 회귀 호환성을 위해 유지한다. 새 catalog는
실제 source authoring을 위한 별도 버전 경계이며, 곧바로 기존 pedestrian program으로
컴파일된다고 주장하지 않는다.

## 2. 필수 내용

- 관할·시행일·ODD와 공식 source record
- source claim 단위의 rule trace
- rule의 scope/precondition/exception/roles
- target/zone binding, ambiguity reason과 partial binder
- PredicateSpec의 observability/freshness/failure-to-UNKNOWN
- activation/invariant/bound/release/reactivation/expiry/fallback 및 edge별 authority
- hard legal/system과 service/preference를 분리한 priority tier
- 여섯 family coverage와 세 slice별 rule 수

## 3. fail-closed 규칙

- 법령에 없는 numeric literal을 rule/binder/lifecycle에 삽입하지 않는다.
- 수치 근거가 없으면 `UNSUPPORTED`와 reason code를 기록한다.
- source·predicate·binder·lifecycle reference가 닫히지 않으면 catalog load를 거부한다.
- official source record가 아닌 항목을 `LEGAL`로 표기하면 거부한다.
- CoC를 source claim 또는 observed predicate로 등록하면 거부한다.
- freshness threshold가 근거 없이 없을 때는 `REVIEW_REQUIRED` policy로 보존한다.

## 4. locked gate

| gate | 기대값 |
|---|---:|
| schema-valid fixture | 100% |
| template 수 | 12–20 (locked 15) |
| slice coverage | 각 slice 4개 이상 |
| broad family coverage | 6/6 |
| source/predicate/binder/lifecycle reference closure | 100% |
| source 없는 normative/numeric value | 0 |
| failure-to-UNKNOWN contract | 100% predicates |
| catalog focused tests | 100% pass |

이 gate는 source catalog의 구조와 추적성을 검증한다. 규칙 해석의 법률 자문 적합성, sensor
accuracy, 차량 capability 또는 실제 장면 안전성을 입증하지 않는다.

