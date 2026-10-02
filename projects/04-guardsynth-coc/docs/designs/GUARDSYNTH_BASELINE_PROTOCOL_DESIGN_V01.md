# GuardSynth 비교 baseline protocol v0.1 설계

## 1. 공통 envelope

모든 adapter는 M14 `FrontendRequest`의 immutable copy와 source catalog를 받고, registry에
선언된 channel만 읽는다. 결과는 baseline ID, 사용 channel, 후보, 상태와 reason code를
갖는 공통 record로 정규화한다.

```text
locked request + catalog
          │
          ├─ channel firewall ─> B0 ... B8
          │                         │
          └─────────────────────────┴─> common result record
                                      └─> B13 explicit serial composition
```

## 2. channel firewall

CoC-only는 scene facts/tags를, scene-only는 CoC concepts를 읽을 수 없다. v0.1은 adapter에
전체 request를 넘긴 뒤 관례로 지키지 않고, dispatcher가 허용 channel만 담은 view를 만든다.
각 결과에 `used_channels`를 기록해 registry 선언과 기계적으로 비교한다.

## 3. 실행 불가능 baseline

외부 model provider, numeric ego/geometry/assurance 또는 reachability action set이 없는 경우
adapter는 고정 reason code로 `UNSUPPORTED`를 반환한다. dummy model output, 임의 제동값,
항상-stop action을 넣지 않는다. 이것은 baseline 누락을 숨기는 성공이 아니라 protocol-level
abstention이다.

## 4. component-style adapter

- B5는 source catalog에 대한 deterministic BM25 retrieval만 DriveReg-style component로 쓴다.
- B6는 CoC concept를 제거한 scene predicate/tag applicability filter다.
- B8은 reachability/action 입력이 제공될 때만 action filter가 되며 v0.1 matrix에는 입력이 없다.
- B13은 B5/B6/B8의 출력을 직렬 결합하고 B8 abstention을 최종 결과에 보존한다.

원 시스템과 동일 구현·성능이라는 표현은 사용하지 않는다.

## 5. oracle 독립성

locked matrix의 기대 primary verdict는 adapter 내부에서 조회하지 않는다. M15는 schema,
determinism, channel use와 abstention을 검사하며 정확도 평가는 M16의 독립 expert gold부터
수행한다.
