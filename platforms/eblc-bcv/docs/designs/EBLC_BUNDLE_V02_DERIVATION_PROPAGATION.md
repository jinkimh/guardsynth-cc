# EBLC program v0.2 bundle composition 전파 설계

## 1. 목적

단일 `eblc-program-v0.2`에서 동작한 typed derivation을 다중 계약
`eblc-bundle-v0.1`의 namespaced Core와 실제 Z3 SMT까지 손실 없이 전달한다.
기존 v0.1 program과 bundle 문법은 호환성을 위해 유지한다.

## 2. 전파 규칙

각 bundle component에 순서 기반 prefix `c0__`, `c1__`, …를 부여하고 다음을 모두
같은 prefix로 바꾼다.

- Core declaration 이름
- semantic/derivation clause ID
- clause 안의 모든 variable reference
- typed derivation의 `stop_position`과 `stopping_distance` output binding

그 뒤 composition의 `selected__*`, `admissible__*`, conflict/review/verdict 및
false-deadlock 절을 별도 전역 이름으로 추가한다. Priority는 기존대로 scalar가 아닌
`HARD > SERVICE > PREFERENCE`와 근거 있는 비순환 override edge를 사용한다.

## 3. SMT definedness

정지거리 DAG의 나눗셈은 다음 식을 포함한다.

```text
braking_distance = effective_speed² / (2 × deceleration)
```

SMT-LIB 실수 나눗셈의 분모 0을 묵시적으로 허용하지 않기 위해 generic compiler는
각 계약과 각 frame에 `(2 × deceleration) != 0` side assertion을 생성한다. 두 계약,
Core horizon 9인 고정 fixture에서는 총 18개 definedness assertion이 있어야 한다.

## 4. TDD acceptance criteria

1. bundle v0.1 container가 v0.2 component를 읽는다.
2. 두 component의 derived declaration/clause/reference가 서로 다른 namespace를 갖는다.
3. speed violation이 각 namespace의 `stopping_distance`를 사용한다.
4. 분모 비영 assertion이 두 계약 × 아홉 frame에 모두 존재한다.
5. Z3가 독립 입력 속도에 대해 정지거리 `9`와 `3`을 exact rational로 계산한다.
6. hard-service와 hard-hard conflict에서 canonical/Core-SMT 결과가 일치한다.
7. 기존 EBLC 111개와 P0a 7개 회귀가 유지된다.

## 5. 결과와 경계

고정 실행은 신규 8/8, 전체 EBLC 119/119, P0a 7/7, composition scenario 5/5와
SMT-LIB replay 2/2를 통과했다. 이는 synthetic bounded translation evidence다.
실제 법규 source, 실제 차량 감속 성능, 센서 정확성, 무한시간/연속 동역학 또는
차량 안전성을 입증하지 않는다.

결과는 [실행 보고서](../../../artifacts/results/public/eblc-composition-compilation-001/composition-v02-typed-derivation-2026-08-09-v2/REPORT_KO.md)에 있다.
