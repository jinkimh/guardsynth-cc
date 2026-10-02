# EBLC executable pilot

## 목적

이 파일럿은 보행자 conflict-zone 양보 요구사항 하나를 사용해 다음 연결이 실제 코드로 실행되는지 확인한다.

```text
CoC clue + scene fact
  -> audited pilot rule retrieval
  -> entity/numeric binding
  -> EBLC lifecycle contract
  -> runtime monitor
  -> BCV under/overconstraint mutation check
```

검증 범위는 합성된 1차원 synthetic trace의 mechanism feasibility다. 실제 법규의 정확성, 카메라 perception, 실제 보행자 prediction, 실제 차량 안전성은 검증하지 않는다. 규칙 source는 법규가 아니라 `PILOT-SYSTEM-REQUIREMENT-PED-YIELD-v0`이라는 명시적 synthetic system requirement다.

## 실행

프로젝트 루트에서 추가 패키지 없이 실행한다.

```bash
python3 -m unittest experiments.eblc_pilot.test_pilot -v
python3 -m experiments.eblc_pilot.run_pilot
```

## 포함된 확인

- rule candidate와 source ID가 보존되는가
- conflict-zone 위치와 차량 profile로 stop position/speed bound가 계산되는가
- `ACTIVE -> MAINTAINED -> RELEASED -> REACTIVATED -> RELEASED`가 실행되는가
- 의무 활성 중 conflict zone에 진입한 trace가 거부되는가
- 관측 `UNKNOWN`에서 승인된 hold fallback이 작동하는가
- 차량 profile이 없으면 수치를 만들지 않고 `UNSUPPORTED`를 반환하는가
- CoC 주장만 있고 장면 관측이 없으면 `REVIEW_REQUIRED`가 되는가
- invariant 누락 mutant에서 과소제약 반례를, release 누락 mutant에서 과잉제약 반례를 찾는가

