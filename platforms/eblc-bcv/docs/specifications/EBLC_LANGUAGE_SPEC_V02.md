# EBLC language specification v0.2

Status: **scoped release candidate** (`EBLC-v0.2-rc1`)

EBLC(Evidence-Bound Lifecycle Contract)는 장면에 적용되는 의무를 근거, 관측성,
수치 유도, lifecycle 및 실행 대상과 함께 표현하는 bounded contract 언어다. 이 문서는
v0.2의 공개 문법과 의미 경계를 동결한다. Python type은 표현, JSON Schema는 구문,
[`semantics.py`](../../../platforms/eblc-bcv/src/guard_synth_eblc/semantics.py)는 단일 계약의 canonical
operational semantics를 담당한다.

## 1. 언어 계층

```text
RuleTemplate + grounded inputs
              ↓ (별도 GuardSynth/binder 계층)
EBLC program v0.2
              ↓ deterministic elaboration
typed EBLC Core v0.1
              ↓ bounded lowering
SMT-LIB / Z3

EBLC program or bundle
              ↓ one-way projection
EBLC-CNL-EN-v0.1 (model prompt; 실행 권위 아님)
```

구조화 EBLC program/bundle과 canonical interpreter가 실행 권위다. Core와 SMT는
bounded compiler target이며 CNL은 사람이 읽거나 모델 prompt에 넣기 위한 결정론적
투영이다. CNL을 다시 파싱해 실행 계약으로 승격하는 의미는 정의하지 않는다.

## 2. 최상위 program

`eblc-program-v0.2`의 필수 필드는 다음과 같다.

| 필드 | 의미 |
|---|---|
| `program_id`, `program_version`, `frames` | 식별자, 문법 버전, bounded trace 길이 |
| `claim_scope`, `source_refs` | 주장 범위와 허용 근거 ID 집합 |
| `binding` | contract/rule/subject/target/zone, 단위와 좌표계 |
| `predicate` | activation predicate, 허용 epistemic kind, freshness, failure value |
| `lifecycle` | 초기 상태, 해제, 재활성, UNKNOWN fallback, expiry |
| `constraints` | 근거가 붙은 차량/수치 입력과 invariant/deadlock flag |
| `typed_derivation` | 수치 입력에서 Core output으로 가는 typed DAG |
| `priority` | scalar가 아닌 priority class와 override 관계 |

실행에 필요한 값이나 source가 없으면 schema/parser/binder가 실패하거나
`REVIEW_REQUIRED`/`UNSUPPORTED`를 반환한다. 임의 기본값은 허용하지 않는다.

## 3. 사실, 근거와 판정

- truth: `TRUE | FALSE | UNKNOWN | CONFLICT`
- epistemic kind: `OBSERVED | PREDICTED | DERIVED | CLAIMED`
- verdict: `VALIDATED | REVIEW_REQUIRED | UNSUPPORTED | CONFLICT`
- lifecycle: `INACTIVE | CANDIDATE | ACTIVE | MAINTAINED | RELEASED |
  REACTIVATED | EXPIRED`

`CLAIMED`는 CoC나 외부 주장을 보존하지만 activation을 위한 관측 사실로 승격하지
않는다. stale, future-dated 또는 허용되지 않은 epistemic 입력은 predicate 계약에 따라
`UNKNOWN`으로 처리한다. 모순된 입력은 `CONFLICT`다.

## 4. Canonical lifecycle

1. 유효한 hazard `TRUE`가 들어오면 의무가 `ACTIVE`가 된다.
2. live obligation 중 hazard가 계속 `TRUE`이면 `MAINTAINED`가 된다.
3. 한 frame의 `FALSE`는 즉시 해제하지 않는다. `release_clear_frames`의 연속 clear
   evidence가 있어야 `RELEASED`가 된다.
4. 해제 후 hazard가 다시 `TRUE`이고 재활성이 허용되면 `REACTIVATED`가 된다.
5. live state에서 fresh `UNKNOWN`은 승인된 fallback이 있을 때만 prior live obligation을
   유지한다. 승인되지 않으면 `REVIEW_REQUIRED`다.
6. `CONFLICT`, binding/unit/frame 오류 및 필수 입력 부재는 fail closed 판정을 만든다.
7. 명시된 expiry 시각 이후에는 `EXPIRED`가 된다.

수치 invariant는 active obligation 중 conflict-zone entry와 동적 stopping-distance를
검사한다. 입력된 deceleration/response/uncertainty는 그 source가 보장하는 범위의 값일
뿐, EBLC 자체가 실제 차량 보장으로 만들어 주지 않는다.

## 5. Typed derivation

`eblc-derivation-v0.1`은 `SOURCED_VALUE`와 `CORE_VARIABLE` symbol, 비순환 node,
명시적 output binding으로 구성한다. 연산은 다음으로 동결한다.

```text
ADD, SUB, MUL, DIV, NEG, MIN, MAX
```

sort, unit, coordinate frame, time variance, source reference와 `DIV` definedness를
solver 전에 검사한다. v0.2 보행자 slice의 대표 식은 다음과 같다.

```text
stop_position       = zone_entry_x - stop_margin
effective_speed     = max(ego_speed - speed_epsilon, 0)
response_distance   = effective_speed * response_time
braking_distance    = effective_speed² / (2 * deceleration)
stopping_distance   = response_distance + braking_distance
```

## 6. Bundle과 indexed collection

`eblc-bundle-v0.1`은 유한 action domain에서 여러 program을 합성한다. priority tier는
`HARD > SERVICE > PREFERENCE`이고 숫자 weight로 상쇄하지 않는다. 선택된 live
contract들의 허용 action을 교집합한다. 둘 이상의 HARD contract가 빈 교집합을 만들면
`CONFLICT`, 그 밖의 빈 교집합은 `REVIEW_REQUIRED`다.

`eblc-indexed-collection-v0.1`은 한 v0.2 template을 근거가 있는 actor-zone instance로
확장한다. `BOUND`에 target, zone, geometry, transform 및 sourced zone-entry가 모두
필요하다. `AMBIGUOUS | UNSUPPORTED | CONFLICT` instance가 하나라도 있으면 부분 bundle을
만들지 않는다.

## 7. Core/SMT 의미

Core v0.1은 `BOOL`, `INT`, `REAL`, finite `ENUM`, bounded temporal expression 및
`INITIAL | EACH_FRAME | EACH_TRANSITION | TRACE | DECLARATIVE` enforcement를 지원한다.
`DECLARATIVE` property는 base assumption으로 조용히 삽입하지 않고 query로 검사한다.
SMT compiler는 time-indexed symbol, enum domain, bounded temporal expansion,
division definedness, source map과 witness manifest를 생성한다.

이 변환은 finite trace에서 canonical 결과와 대조한다. 같은 specification에서 유도된
translation validation이며 독립적인 차량 안전 oracle은 아니다.

## 8. Controlled Natural Language

`EBLC-CNL-EN-v0.1` renderer는 다음 불변조건을 가진다.

- 동일 입력은 byte-identical text와 동일 SHA-256을 만든다.
- program/bundle의 모든 최상위 field는 clause에 매핑되거나 omission으로 명시된다.
- clause마다 원본 field path와 evidence ref를 기록한다.
- 새 수치, source, target, zone 또는 보장 주장을 생성하지 않는다.
- 입력 hash와 출력 hash를 함께 내보낸다.
- CNL은 실행 권위가 아니며 역변환 의미가 없다.

## 9. v0.2 완료 경계

v0.2 완료 범위는 bounded discrete pedestrian conflict-zone vertical slice, typed
derivation, multi-contract composition, indexed expansion, Core/SMT translation,
BCV mutation과 CNL projection이다. 다음은 완료 조건에서 제외하고 명시적으로 이관한다.

- 일반 operational exception algebra: v0.3 후보
- quantifier, 무한 collection/horizon, continuous/hybrid dynamics
- 자연어 CoC에서 source-aware EBLC를 만드는 generator. 구조화 입력 v0.1은 별도
  `projects/04-guardsynth-coc/src/guard_synth` 계층에 구현됐지만 free-form parsing은 포함하지 않음
- 실제 perception association, 법규 source 및 vehicle assurance authoring
- 독립 simulator/physics oracle과 실제 차량 안전 증명

상세 구현 추적은 [요구사항 추적표](../../reports/EBLC_REQUIREMENT_TRACEABILITY_V02.md),
실행 방법은 [사용자 가이드](../../guides/eblc/EBLC_USER_GUIDE_V02.md)를 따른다.
