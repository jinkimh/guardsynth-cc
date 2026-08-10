# scene-0001 UPPAAL feasibility

## 범위

이 모델은 scene-0001에서 현재 실제 증거가 있는 연속 시간 의무만 표현한다.

- 최초 trusted truck-related `DECELERATE`: 상대시간 `0ms`
- 반복 trusted trigger: `1000ms`, `2300ms`
- speed-trace heuristic response: `2160ms`
- 이후 low-quality event: `6800ms`

장애물 gap, 상대속도, raw brake command와 차량 제동 envelope가 없으므로 collision 또는 safe-distance 물리 속성은 포함하지 않는다. `2160ms`는 active braking 측정값이 아니라 특정 speed 감소 heuristic을 모델 재생하기 위한 값이다.

## 설치

UPPAAL 5.0.0 배포본은 `runtime/solvers/uppaal-5.0.0-linux64/`에 설치했다.

```bash
runtime/solvers/uppaal-5.0.0-linux64/bin/verifyta --version
```

확인 버전은 `UPPAAL 5.0.0 (rev. 714BA9DB36F49691)`이다. 이 배포본의 README는 학위 수여 학술기관의 비상업 연구 용도로 무료 사용 가능하다고 명시한다. 그 밖의 사용에는 별도 라이선스가 필요하다.

```text
archive SHA-256   86d66d8cd25c00f6f45156617f3a7566f1f4fe7aed74dd171bfc9ef27a2c61ce
verifyta SHA-256  6801bf6f55aa74c201ea2524f7a9a6bc59bec428dcb47843186ea808d5beee4c
```

학술용 verifier license를 활성화했으며 key 자체는 문서나 결과 파일에 저장하지 않았다. 공식 설치 안내와 갱신 절차는 [UPPAAL 다운로드 페이지](https://uppaal.org/downloads/)를 따른다.

```bash
runtime/solvers/uppaal-5.0.0-linux64/bin/verifyta --lease 168 --key "$UPPAAL_LICENSE_KEY"
```

## 모델 생성

```bash
python experiments/uppaal/generate_models.py
```

시간 상수는 코드에 독립적으로 복사하지 않고 `artifacts/results/public/scene-0001/episode-check-result.json`에서 읽어 millisecond 단위로 양자화한다. 생성된 `scene-profile.json`이 source, trigger와 양자화 규칙을 기록한다.

생성되는 모델:

| variant | 변화 | 검출 대상 |
|---|---|---|
| `normal` | `D=3000ms`, response 발생 | baseline |
| `deadline_2s` | `D=2000ms` | heuristic response의 deadline miss |
| `clock_reset` | 반복 trigger에서 reaction clock reset | clock-reset violation |
| `no_response` | response event 제거 | non-vacuity 및 deadline miss |
| `untrusted_overwrite` | low-quality event가 trusted state overwrite | trust-policy violation |

템플릿 네트워크:

```text
CoCSource
  -> first_trigger / repeat_trigger / untrusted_event

EgoTrace
  -> response

ObligationManager
  Idle -> Active -> Responded

ReactionObserver
  Idle -> Armed -> Done | DeadlineMiss

DecisionValidator
  -> untrusted overwrite 감시
```

Query 순서:

```text
E<> Obligation.Active
E<> Obligation.Responded
A[] not Reaction.DeadlineMiss
A[] not clock_reset_violation
A[] not untrusted_overwrite
A[] not deadlock
```

## 실행

```bash
python experiments/uppaal/run_verification.py \
  --output artifacts/results/public/scene-0001/uppaal-verification-result.json
```

Runner는 각 query의 실제 판정과 `expected-results.json`의 mutation oracle을 비교한다. `normal`만 실행하는 것으로는 query vacuity를 배제할 수 없으므로 다섯 variant가 모두 예상 matrix와 일치해야 feasibility를 PASS로 판정한다.

실제 UPPAAL 5.0.0 symbolic 결과는 다음과 같이 mutation oracle과 모두 일치했다.

| variant | Active | Responded | no DeadlineMiss | no clock reset | no overwrite | no deadlock |
|---|---:|---:|---:|---:|---:|---:|
| `normal` | PASS | PASS | PASS | PASS | PASS | PASS |
| `deadline_2s` | PASS | PASS | FAIL | PASS | PASS | PASS |
| `clock_reset` | PASS | PASS | PASS | FAIL | PASS | PASS |
| `no_response` | PASS | FAIL | FAIL | PASS | PASS | PASS |
| `untrusted_overwrite` | PASS | PASS | PASS | PASS | FAIL | PASS |

첫 실행에서는 모든 모델의 `A[] not deadlock`이 실패했다. diagnostic trace를 통해 `6800ms` 이후 의도적인 terminal state에 outgoing transition이 없는 것이 원인임을 확인했다. `CoC.Done`에 terminal stutter를 명시한 뒤 정상 종료와 중간 protocol deadlock을 분리했고 위 matrix를 얻었다. 각 variant의 전체 verifyta 출력은 evidence의 `uppaal-traces/`에 저장한다.

## 연속 4국면 시나리오

단일 의무를 넘어 국면 전환 검증이 가능한지 확인하기 위해 별도의
`scene-0001-chained` 모델을 추가했다.

```text
FOLLOW -> DECELERATE -> STOP/HOLD -> RECOVER
```

`DECELERATE` 요청 `0ms`와 speed-trace 반응 `2160ms`는 scene-0001
episode evidence에서 가져온 값이다. 이후 `STOP` 요청 `5000ms`, 정지 확인
`6400ms`, clearance `8000ms`, 회복 요청 `8100ms`, 회복 확인 `9000ms`는
연속 프로토콜의 모델링 가능성만 검사하기 위한 합성 값이다. 각 값과 출처 구분은
`models/scene-0001-chained-profile.json`에 기록한다.

검증 속성은 세 국면의 도달 가능성, 국면별 deadline, 순서 위반, clearance 이전
회복, deadlock 부재이다. 실행 명령은 다음과 같다.

```bash
python experiments/uppaal/run_chained_verification.py \
  --output artifacts/results/public/scene-0001/uppaal-chained-verification-result.json
```

| variant | Decel | Hold | Recovered | deadline | order | clearance | deadlock |
|---|---:|---:|---:|---:|---:|---:|---:|
| `normal` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `late_stop` | PASS | PASS | PASS | FAIL | PASS | PASS | PASS |
| `skip_hold` | PASS | FAIL | FAIL | FAIL | FAIL | PASS | PASS |
| `premature_recovery` | PASS | PASS | PASS | PASS | PASS | FAIL | PASS |
| `no_recovery` | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS |

다섯 모델의 실제 UPPAAL 판정이 mutation oracle과 모두 일치했다. 따라서
연속 제어 국면과 국면 간 계약을 timed automata로 표현하고 결함 반례를 분리해
검출할 수 있다는 feasibility는 확인했다. 다만 합성된 `STOP/HOLD/RECOVER` 구간은
데이터셋에서 관측된 차량 거동이 아니며, 이 결과는 충돌 안전성이나 실제 제동 성능의
증거가 아니다.

## Provenance 재실험

각 정상 경로 전이와 mutation에 다음 provenance class를 부여했다.

| class | 의미 | 학습 사용 정책 |
|---|---|---|
| `OBSERVED` | 원본 CoC event에 직접 연결 | sequence label 허용 |
| `DERIVED` | 원본 데이터와 명시된 규칙으로 계산 | quality weight가 있는 weak label만 허용 |
| `SYNTHETIC_ASSUMPTION` | feasibility용 가정 | positive label 금지 |
| `SYNTHETIC_MUTATION` | 속성 위반을 위해 주입한 결함 | hard negative만 허용 |

각 `OBSERVED`/`DERIVED` 전이는 source artifact SHA-256, JSON pointer, 원본
timestamp 또는 derivation을 가진다. 전체 lineage는
`models/scene-0001-chained-profile.json`, 학습 routing 결과는
`models/scene-0001-training-manifest.json`에 저장한다.

재실험 결과:

| 모델/episode | source-backed | synthetic | 모델체킹/mutation | positive sequence 학습 | raw-control 학습 |
|---|---:|---:|---|---|---|
| 합성 4국면 | 2/7 (28.6%) | 5 | PASS | **FAIL** | FAIL |
| 원본 trace episode | 7/7 (100%) | 0 | 아직 별도 모델 미실행 | **PASS_WITH_WEAK_RESPONSE_LABEL** | FAIL |

합성 4국면의 UPPAAL mutation 결과는 다시 실행해 모두 oracle과 일치했다. 하지만
provenance gate는 이 시나리오를 positive 학습 정답에서 제외한다. 원본 trace
episode는 CoC sequence/order 학습 후보로 사용할 수 있지만, `2160ms` 반응은
speed-trace heuristic이므로 가중치를 낮춘 weak label이어야 한다. raw brake 또는
actuator supervision에는 두 episode 모두 사용할 수 없다.

## 13-scene cohort 검증

`generate_cohort_models.py`는 13개 독립 scene의 traceable CoC episode에서 scene별
baseline, provenance mutation, response mutation을 생성한다. 총 39개 XML에 다음
query 네 개를 적용한다.

```text
E<> Source.Done
A[] not provenance_violation
A[] not weak_response_violation
A[] not deadlock
```

UPPAAL은 39개 모델의 156개 query를 모두 실행했으며 oracle과 전부 일치했다.
12개 baseline은 모든 속성을 만족했고, `scene-0028` baseline만 관측된 weak
kinematic FAIL을 반영해 `A[] not weak_response_violation`이 실패했다. 모든
provenance/response mutation도 대응 query에서 검출됐다.

이 실험은 여러 scene에서 trace replay와 mutation 검출을 반복할 수 있음을 보인다.
다만 UPPAAL 모델은 offline checker가 추출한 관측 판정을 재생하므로 정책의 가능한
환경 분기 전체를 탐색하지 않는다. 특히 `scene-0028`은 영상과 actuator 확인 전까지
안전 반례가 아니라 후속 검토 후보이다.

## chunk 0 전체 실행

cohort generator/runner를 입력 결과와 model directory를 받도록 일반화하고 chunk 0의
라벨 보유 94개 scene 전체를 실행했다. scene별 baseline, provenance mutation,
response mutation으로 282개 모델과 1,128개 query를 검증했다. 모든 실제 verdict가
oracle과 일치했다.

최종 baseline의 weak-response violation scene은 `scene-0019`, `scene-0028`,
`scene-0042`, `scene-0065`, `scene-0074`다. 초기 8건 중 이미 정지한 STOP/YIELD
3건은 영상 검토 후 계약을 수정하여 제거했다. 남은 5건은 UPPAAL이 offline weak
contract 판정을 정확히 재생한 것이며, 아직 actuator-level 반례가 아니다.

## scene-0074 반복 의무 의미론 실험

남은 후보 중 `scene-0074@3400000`을 전용 timed trace로 확장했다. 관측된 네 가속
CoC는 scene 시각 `3.4/5.9/7.2/11.6초`이고, 기본 속도-response profile에서 검출된
반응은 첫 CoC 기준 상대 시각 `3.360/3.820/8.201초`다. 다음 명령으로 두 반복 처리
규칙을 같은 모델에서 검증한다.

```bash
python experiments/uppaal/run_scene0074_protocol.py
```

| 반복 CoC 의미론 | D=3s 결과 | 해석 |
|---|---|---|
| `preserve-first` | **FAIL** | 최초 의무는 3초 안에 응답하지 않음 |
| `reset-on-repeat` | **PASS** | 2.5초의 반복 지시가 deadline을 갱신하고 0.86초 뒤 응답 |

7개 query가 모두 예상 oracle과 일치했고 deadlock도 없었다. 따라서 이 trace는
`preserve-first` 계약에 대한 프로토콜 수준 반례인 동시에, 반복 CoC의 갱신 규칙을
명세하지 않으면 검증 판정이 유일하지 않음을 보여주는 witness다. 충돌 위험, 실제
가속 페달/토크 반응 또는 차량의 물리 안전성을 입증하는 반례는 아니다. 결과와
추적성은 `artifacts/results/public/scene-0074/uppaal-repeated-obligation-semantics-result.json`
에 저장한다.

## 나머지 4개 후보 다중 속성 검증

`scene-0019/0028/0042/0065`에는 세 가지 반복 규칙과 `D=1~5초`를 조합한 60개
모델을 생성했다. 모델마다 episode 도달성, deadline 준수, target response 존재,
orphan response 부재, provenance, command-response 수 순서, deadlock 부재의 7개
속성을 검사했다. 총 420개 query가 oracle과 모두 일치했다.

```bash
python experiments/uppaal/run_remaining_candidate_verification.py
```

| scene | `preserve` 통과 D | `reset` 통과 D | 핵심 판정 |
|---|---|---|---|
| `0019` | 없음 | 없음 | 1초 이내 중복으로 제거할 때만 통과; target response는 기본 profile에서 없음 |
| `0028` | 4, 5 | 3, 4, 5 | D=3 판정이 반복 타이머 규칙에 따라 바뀜 |
| `0042` | 4, 5 | 4, 5 | 반복 규칙과 무관하게 D=3 실패, D=4 통과 |
| `0065` | 4, 5 | 4, 5 | 반복 없음; D=3 실패, D=4 통과 |

`deduplicate-1s`는 source contract가 아니라 민감도 가정이다. 이 규칙은 `0019`의
짧은 반복 CoC를 제거해 deadline 위반을 없애지만, `0028`에서는 마지막 STOP CoC만
제거하고 대응 반응을 남겨 orphan response 위반을 만든다. 따라서 중복 제거는 CoC와
그 반응의 lineage를 함께 병합해야 한다.

학습 사용도 조건부다. `0028`은 `preserve + D=3`에서만 protocol hard-negative로,
`0042`는 threshold-sensitive low-confidence hard-negative로 사용할 수 있다. `0019`는
중복 정책 확정 전까지, `0065`는 영상의 causal grounding 확인 전까지 review-only다.
네 장면 모두 raw actuator와 객체 거리 자료가 없어 물리 안전 상태는 `UNKNOWN`이다.
