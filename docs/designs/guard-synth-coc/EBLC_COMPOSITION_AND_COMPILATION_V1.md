# EBLC 다중 계약 composition 및 고수준→Core→SMT 설계 V1

## 1. 목적과 고정 기준선

이 설계는 단일 보행자 계약용 `eblc-program-v0.1`을 변경하지 않고 그 위에
`eblc-bundle-v0.1`을 추가한다. 이후 program v0.2 typed derivation 전파는
[별도 확장 설계](EBLC_BUNDLE_V02_DERIVATION_PROPAGATION.md)로 고정했다. 구현 전 유지 회귀 기준선은 다음과 같다.

- 구현 전 명령: `python3 -m unittest discover -s tests/guard_synth_eblc -p 'test_*.py'`
- 결과: **77/77 통과**
- P0a 회귀: **7/7 통과**
- 기준선 의미: 기존 단일 계약 EBLC 동작과 공개 인터페이스의 회귀 기준

확장 후에는 신규 테스트가 함께 discover되므로 77개 기준선만 재실행하는 정확한
module 목록과 결과는 최신 `RUN_MANIFEST.json`의 `legacy_baseline` 항목에 고정한다.

Git 메타데이터가 없는 작업공간이므로 최종 실행 manifest는 관련 파일의 SHA-256과
`WORKSPACE_WITHOUT_GIT_METADATA`를 기록한다.

## 2. 언어 계층

```text
eblc-program-v0.1 (단일 evidence-bound lifecycle contract)
              × 2 이상
                    ↓ eblc-bundle-v0.1
계약별 lifecycle/verdict + priority tier + allowed action set
                    ↓ bundle elaborator
namespaced EBLC Core v0.1 + composition clauses
                    ↓ generic Core SMT compiler
bounded SMT-LIB / Z3 model / witness / source map
```

JSON Schema는 입력 문법을 검사하고 Python parser는 중복, 출처, 참조, 순환,
우선순위 역전 같은 의미 전제조건을 fail-closed로 검사한다. 실제 실행 의미의 기준은
`composition.resolve_composition`이며, Core와 SMT는 그 의미의 생성 target이다.

## 3. 입력 인터페이스

Bundle은 다음을 요구한다.

- `source_refs`: bundle 및 모든 내장 program의 근거 식별자
- `action_domain`: 유한한 action 이름 집합
- `contracts`: 둘 이상의 기존 고수준 EBLC program
- 계약별 `priority_tier`: `HARD`, `SERVICE`, `PREFERENCE`
- 계약별 `allowed_actions`: 계약이 선택됐을 때 허용하는 action 집합
- 계약별 `overrides_contracts`: 명시적이고 비순환인 override edge
- `composition_evidence_refs`: composition 정책 자체의 근거

실제 법규 source나 실제 차량 보장값은 이 문법이 자동으로 만들어 주지 않는다.
누락되거나 확인되지 않은 값은 별도 authoring/binding 단계에서
`UNSUPPORTED` 또는 `REVIEW_REQUIRED`로 남아야 한다.

## 4. priority와 충돌 의미론

priority는 scalar weight가 아니다. 따라서 편의성 점수가 hard 제약을 상쇄할 수 없다.

1. live state는 `ACTIVE`, `MAINTAINED`, `REACTIVATED`다.
2. 기본 tier 순서는 `HARD > SERVICE > PREFERENCE`다.
3. 높은 tier의 live 계약은 낮은 tier의 live 계약을 suppress한다.
4. 동일 tier 계약은 서로 비교 불가능하며, 명시적 override가 있을 때만 suppress된다.
5. 낮은 tier가 높은 tier를 override하려는 입력과 override cycle은 거부한다.
6. 선택된 모든 계약의 `allowed_actions`를 교집합한다.
7. 둘 이상의 선택된 HARD 계약 때문에 교집합이 비면 `CONFLICT`다.
8. 그 밖의 빈 교집합은 `REVIEW_REQUIRED`다.
9. 독립적으로 safe-progress action이 존재한다고 주어졌는데 교집합이 비면
   `FALSE_DEADLOCK_SAFE_PROGRESS_EXISTS`를 기록한다.

개별 계약 verdict의 전체 우선순위는
`CONFLICT > UNSUPPORTED > REVIEW_REQUIRED > VALIDATED`다. 이는 가중치 합이 아니라
fail-closed 상태 우선순위다.

## 5. Core 생성 규칙

각 내장 program을 기존 elaborator로 Core로 만든 뒤 `c0__`, `c1__`처럼 모든 선언,
절, 변수 참조를 namespace한다. 이어 다음 시간가변 출력을 생성한다.

- `selected__<contract>`
- `admissible__<action>`
- `composition_conflict`
- `composition_review_required`
- `composition_false_deadlock`
- `composition_verdict`

전이 프레임 `t`에서 선택 여부는 각 계약의 post-state `state[t+1]`로 판단한다.
admissible action은 선택 계약 모두가 허용할 때만 참이다. 이 식들은 기존 Core v0.1의
Boolean, enum, `ite`, `EACH_TRANSITION`만 사용하므로 generic Core→Z3 compiler를
그대로 통과한다.

## 6. 검증 구조와 주장 경계

canonical path는 각 계약의 `CanonicalInterpreter` 결과를 composition resolver에 넣는다.
translation path는 같은 고수준 bundle을 Core와 Z3로 변환한다. 같은 finite trace에서
선택 계약, 허용 action, composition verdict, false-deadlock을 비교한다.

이는 bounded translation agreement이며 독립 safety oracle 또는 차량 안전 증명이
아니다. 생성기, resolver, compiler는 실제 규칙 source의 타당성이나 센서·차량 성능을
입증하지 않는다. 다음 범위도 남아 있다.

- 현재 typed arithmetic DAG 밖의 arbitrary/user-defined derivation
- 무한시간 및 연속/hybrid dynamics
- 동적 action 생성과 planner reachability 통합
- 자연어 CoC에서 완전 자동으로 근거 있는 EBLC를 생성하는 기능
