# GuardSynth source-aware generator v0.1 설계

## 1. 목적과 경계

EBLC v0.2는 계약을 표현·실행·검증하는 언어로 동결했다. 이 모듈은 그 앞에서 다음
구조화 입력을 결합해 실행 가능한 EBLC indexed collection을 만드는 첫 GuardSynth
vertical slice다.

```text
RuleTemplate catalog + PredicateSpec catalog
              + grounded ContextGraph
              + VehicleProfile
              + explicit compiler/composition policy
                              ↓
                EBLC program v0.2 template
                              +
                 indexed actor-zone collection
                              ↓
                 bundle → Core → SMT/Z3
```

자연어 CoC parser, 법규 검색기 또는 perception system은 아직 포함하지 않는다. CoC
reference는 `CLAIMED` provenance로만 보존하며 activation predicate의 evidence로 쓰지
않는다.

## 2. 공개 입력 인터페이스

`guard-synth-source-aware-generator-v0.1` request는 다음을 요구한다.

- catalog의 `template_program_ref`, `rule_template_ref`, `predicate_spec_ref`
- 전체 evidence ID registry인 `source_refs`
- lifecycle/compiler epsilon/action domain/composition source를 가진 explicit `policy`
- source와 수치를 가진 `vehicle_profile`
- graph timestamp와 CoC claim refs를 가진 `context_graph`
- instance별 hazard fact, target/zone candidates와 선택 결과
- association, zone geometry, coordinate transform evidence
- source-bearing zone-entry 값, unit과 coordinate frame

기존 runtime `ContextFrame`은 geometry/transform/association provenance를 담지 못하므로
변경하지 않았다. generator 전용 request schema가 이 정보를 추가하고, 성공한 결과만
기존 indexed collection 문법으로 내린다.

## 3. 생성 규칙

1. JSON schema, catalog ref, identifier와 evidence closure를 검증한다.
2. RuleTemplate source가 `UNKNOWN`이면 중단한다.
3. vehicle profile 값의 존재, 유한성, 부호와 evidence를 검증한다.
4. hazard truth/epistemic/freshness와 predicate policy를 검사한다.
5. target/zone 선택이 candidates에 포함되는지 검사한다.
6. geometry와 transform ref가 association evidence에 실제 포함되는지 검사한다.
7. zone entry unit/frame이 predicate coordinate frame과 일치하는지 검사한다.
8. 모든 instance가 완전할 때만 source-bearing program과 collection을 생성한다.

program template의 `zone_entry_x=0`은 실행값이 아니라
`TEMPLATE_PLACEHOLDER_NEVER_EXECUTED`다. compiler-policy evidence에 묶이며 indexed
expansion이 각 instance의 실제 sourced zone entry로 반드시 overwrite한다. 생성
artifact의 `GENERATION_MAP.json`에 이 경계를 기록한다.

## 4. Fail-closed 판정

| 상황 | 판정 | collection |
|---|---|---|
| CoC claim-only hazard | `REVIEW_REQUIRED` | 생성 안 함 |
| ambiguous target/zone | `REVIEW_REQUIRED` | 생성 안 함 |
| missing profile/geometry/transform/value | `UNSUPPORTED` | 생성 안 함 |
| unit/frame mismatch | `UNSUPPORTED` | 생성 안 함 |
| conflicting evidence/duplicate binding | `CONFLICT` | 생성 안 함 |
| 모든 source와 binding 완전 | `VALIDATED` | 생성 |

판정 우선순위는 `CONFLICT > UNSUPPORTED > REVIEW_REQUIRED`다. 일부 instance만 조용히
실행하지 않는다.

## 5. TDD와 실행 근거

신규 12 tests는 정상 생성, source/value propagation, distinct expansion,
Core-SMT exact witness, deterministic output과 여섯 fail-closed 방향을 고정한다.
기존 EBLC RC baseline 138/138, 전체 150/150, P0a 7/7, 구조 9/9 및 SMT-LIB replay
2/2가 통과했다. 정상 fixture의 Z3 witness는 다음과 같다.

```text
C0 stop_position       = -3/2
C1 stop_position       = 21/2
C0 stopping_distance@0 = 9
C1 stopping_distance@0 = 3
division definedness   = 18 assertions
```

실행 artifact는 [보고서](../../../artifacts/results/public/guardsynth-source-aware-generator-001/source-aware-generator-2026-08-09-v3/REPORT_KO.md)에 있다.

## 6. 입증하지 않은 것과 다음 작업

이 결과는 synthetic structured source flow가 EBLC/Core/Z3까지 연결됨을 보인다. 실제
법규 진위, CoC 해석, perception association, 차량 assurance 값 또는 차량 안전성을
입증하지 않는다. 다음 작업은 문법 추가가 아니라 다음 세 source authoring adapter다.

1. 실제/파생 scene → association·geometry·transform evidence bundle
2. 차량 시험/사양 → VehicleProfile assurance record
3. 규칙 source registry → audited RuleTemplate/PredicateSpec catalog

이 입력이 준비된 뒤에만 24-scene dry run을 진행한다.
