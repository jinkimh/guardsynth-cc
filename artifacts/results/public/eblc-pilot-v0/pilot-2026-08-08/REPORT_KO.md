# EBLC 실행 파일럿 v0 결과

- 실행일: 2026-08-08
- Python: 3.11.2
- 데이터: 공개 가능한 synthetic 1D trace
- 규칙: `PILOT-SYSTEM-REQUIREMENT-PED-YIELD-v0`
- 결과 JSON: [RESULT.json](RESULT.json)
- 코드: [experiments/eblc_pilot](../../../../eblc_pilot/README.md)

## 질문

보행자 conflict-zone 양보 규칙을 장면별 수치와 lifecycle을 가진 EBLC로 인스턴스화했을 때 실제 runtime monitor에서 실행되는가?

## 실행 결과

```text
단위 테스트                         7/7 PASS
rule/target/numeric binding         PASS
안전 release/reactivation trace     ACCEPT
활성 중 conflict-zone 진입 trace    REJECT
UNKNOWN 관측 hold fallback          ACTIVE/ACCEPT
차량 profile 누락                   UNSUPPORTED
CoC 주장만 있고 관측 없음           REVIEW_REQUIRED
BCV missing-invariant mutation      UNDERCONSTRAINT WITNESS FOUND
BCV missing-release mutation        OVERCONSTRAINT WITNESS FOUND
```

안전 trace의 실제 상태 전이는 다음과 같았다.

```text
ACTIVE
-> MAINTAINED
-> RELEASED
-> REACTIVATED
-> MAINTAINED
-> RELEASED
```

위험 trace는 다음 두 이유로 거부됐다.

```text
CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE
ROBUST_STOPPING_SPEED_BOUND_EXCEEDED
```

계약의 정지 위치는 conflict-zone entry `0.0 m`에서 synthetic requirement의 margin `1.5 m`를 빼 `-1.5 m`로 결합했다. 매 frame의 최대 허용 속도는 차량 profile의 response time `0.5 s`, service deceleration `3.0 m/s²`, position uncertainty `0.5 m`를 사용해 다시 계산했다. 이 값들은 실제 차량 보장값이나 법적 수치가 아니다.

## 무엇을 확인했는가

이번 결과는 다음 software mechanism이 연결될 수 있음을 확인한다.

```text
CoC clue + observed scene fact
-> source-bearing rule candidate
-> target and numeric binding
-> lifecycle contract
-> runtime enforcement
-> controlled BCV mutation check
```

특히 CoC 문장만 있을 때는 hard contract로 승격하지 않았고, 차량 profile이 없을 때는 임의 수치를 생성하지 않았다. release가 두 frame 연속 확인된 뒤에만 진행을 허용했으며, 이후 위험이 재등장하면 같은 계약을 재활성화했다.

## 아직 확인하지 못한 것

- 실제 관할 법규의 정확한 formalization
- 실제 카메라ㆍLiDAR에서 보행자와 conflict zone을 찾는 grounding
- 실제 차량의 보장 제동성능과 마찰 불확실성
- 독립적으로 구현된 법규ㆍ물리 oracle
- 여러 규칙의 동시 composition과 priority
- 실제 planner/reachability backend와의 연결
- real-world 또는 simulator closed-loop safety improvement

따라서 이 결과는 E-1/E0 통과나 차량 안전성 근거가 아니라, 다음 파일럿으로 진행할 수 있다는 **P0a mechanism feasibility** 결과다.

## 재현 명령

프로젝트 루트에서 실행한다.

```bash
python3 -m unittest experiments.eblc_pilot.test_pilot -v
python3 -m experiments.eblc_pilot.run_pilot
```
