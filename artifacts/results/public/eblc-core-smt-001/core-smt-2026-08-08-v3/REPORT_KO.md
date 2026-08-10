# EBLC Core → SMT 컴파일 실행 보고서

- 상태: **EXECUTED**
- 실행 ID: `core-smt-2026-08-08-v3`
- 문법/컴파일러: `eblc-core-v0.1` / `eblc-core-smt-compiler-v0.1`
- 솔버: project-local Z3 `5.0.0`
- bounded horizon: `5`
- 주장 범위: `BOUNDED_CORE_GRAMMAR_AND_COMPILER_NOT_VEHICLE_SAFETY`

## 구현 및 검사 결과

EBLC Core JSON을 스키마 검사한 뒤 typed AST로 읽고, 변수 sort·단위·좌표계·시간 offset·enum domain을 fail-closed 방식으로 검사했다. 논리식, 산술식, `ite`, `always`, `eventually`, `until`과 lifecycle clause를 horizon 안에서 Z3 식으로 변환했다. 나눗셈에는 분모가 0이 아니라는 definedness 조건을 자동 추가했다.

`DECLARATIVE` invariant/bound는 모델의 가정으로 넣지 않았다. 대신 그 위반식을 query로 풀어 circular validation을 피했다. 각 query는 동일 base model 위의 독립 solver instance에서 실행됐다.

| query | 분류 | 기대 | 실제 | 일치 |
|---|---|---:|---:|---:|
| `lifecycle_transition_inconsistency` | CONSISTENCY | UNSAT | UNSAT | True |
| `active_stop_position_violation` | UNDERCONSTRAINT | SAT | SAT | True |
| `missing_reactivation` | UNDERCONSTRAINT | UNSAT | UNSAT | True |
| `safe_progress_false_deadlock` | OVERCONSTRAINT | UNSAT | UNSAT | True |
| `dynamic_stopping_bound_violation` | UNDERCONSTRAINT | SAT | SAT | True |
| `clear_counter_always_nonnegative` | BOUNDARY | SAT | SAT | True |
| `inactive_until_activation` | EXAMPLE | SAT | SAT | True |

- query agreement: `7/7` (`1.000`)
- exported SMT-LIB direct replay: `8/8` (`1.000`)
- Core compiler tests: `12/12`
- 전체 P0b regression: `55/55`

## 산출물

`MODEL.smt2`는 공통 제약, `QUERY_*.smt2`는 query별 재실행 가능한 SMT-LIB이다. `SYMBOL_TABLE.json`은 EBLC 이름·시간·단위·좌표계와 SMT symbol의 대응을, `SOURCE_MAP.json`은 clause/query와 근거의 대응을, `QUERY_MANIFEST.json`은 SAT/UNSAT와 witness를 보존한다.

## 해석 한계

이 실행은 Core v0.1의 bounded discrete-time 문법과 변환기가 synthetic P0b 모델에서 의도한 query 결과를 낸다는 소프트웨어 증거다. 무한시간 의미, 연속 동역학, 실제 법규의 타당성, 실제 차량 보장값, 실제 차량 안전성은 입증하지 않는다. P0b 전용 canonical interpreter와 이 Core compiler의 완전한 모든-input 의미 동등성도 아직 입증 범위 밖이다.
