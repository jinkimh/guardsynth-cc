# EBLC indexed actor–zone collection v0.1 설계

## 1. 목적

하나의 `eblc-program-v0.2` template을 여러 actor–conflict-zone binding에 적용하되,
모호하거나 근거가 없는 association을 임의로 확정하지 않는다. 확정된 instance만 모두
존재할 때 기존 bundle→Core→SMT 경로로 결정론적으로 확장한다.

## 2. 입력 구조

`eblc-indexed-collection-v0.1`은 다음을 가진다.

- `template_program_ref`: 검증된 program v0.2 catalog ID
- `instances`: 둘 이상의 actor–zone binding
- instance별 target, zone, zone geometry ref, coordinate-transform ref
- 근거가 있는 `zone_entry` 값과 unit/frame
- `BOUND | AMBIGUOUS | UNSUPPORTED | CONFLICT` association 상태
- priority tier, allowed action, explicit override

`BOUND`는 target, zone, geometry, transform, zone-entry 값과 모든 evidence ref가 있어야
한다. 다른 상태에서는 bound field를 허용하지 않고 reason code를 요구한다.

## 3. Fail-closed 확장

모든 instance가 `BOUND`일 때만 template을 복제한다. 각 복제본은 고유 contract/program
ID, target/zone binding과 zone-entry derivation symbol을 가진다. 한 instance라도
미해결이면 일부 contract만 실행하지 않고 collection 전체를 다음 순서로 중단한다.

```text
CONFLICT > UNSUPPORTED > REVIEW_REQUIRED
```

동일 target–zone pair의 중복 계약도 solver 전에 거부한다.

## 4. TDD 고정 범위

- 두 actor와 서로 다른 두 zone이 distinct program binding으로 확장됨
- zone-entry `0 m`, `12 m`가 typed derivation에 반영됨
- Z3 exact stop position `-3/2`, `21/2`
- Z3 exact stopping distance `9`, `3`
- 두 계약×아홉 frame의 division definedness 18개
- ambiguous association에서 `REVIEW_REQUIRED`, bundle 미생성
- unsupported/conflicting evidence의 verdict precedence
- 기존 EBLC 119개와 P0a 7개 회귀 보존

## 5. 주장 경계

이 문법은 제공된 association과 geometry를 보존하고 불완전 입력을 중단한다. 실제
perception association이 맞는지, geometry/transform source가 참인지, 차량 profile이
보장값인지 또는 차량이 안전한지는 입증하지 않는다.

실행 근거는 [결과 보고서](../../../artifacts/results/public/eblc-indexed-collection-001/indexed-collection-2026-08-09-v1/REPORT_KO.md)에 있다.
