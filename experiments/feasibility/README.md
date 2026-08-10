# 최소 증거 기반 feasibility check

Alpamayo 생태계 공식 데이터만을 대상으로 한 내부 실험 보고서와 후속 실험 목록은
[Alpamayo 전용 실험 인덱스](../alpamayo/README.md)에서 관리한다.

## 결론

현재 확보한 증거로는 다음의 제한된 주장을 재현할 수 있다.

> PhysicalAI-AV 호환 데이터의 `clip_id`와 `event_start_timestamp`를 이용하면 CoC 문장, 과거 카메라 프레임, egomotion history와 future trajectory를 시간 정렬할 수 있다. CoC 결정을 closed-set action으로 정규화한 뒤 기록 궤적이 그 행동 방향과 일치하는지 검사하는 최소 파이프라인은 구현 가능하다.

이 결과는 공식 NVIDIA CoC label에 대한 최종 검증이 아니다. 사용한 CoC-nuScenes는 NVIDIA의 공개 autolabeler로 생성된 호환 데이터이며 NVIDIA가 배포한 human-refined OOD CoC와 구분한다.

## 확보한 실제 증거

### 공식 NVIDIA 근거

- [NVIDIA Physical AI AV 데이터 카드](https://huggingface.co/datasets/nvidia/PhysicalAI-Autonomous-Vehicles)에는 `reasoning/ood_reasoning.parquet`가 공개 목록에 있으며 train 1,728개, validation 349개의 human-refined CoC label을 포함한다고 명시되어 있다.
- [공식 Alpamayo loader](../../third_party/alpamayo/src/alpamayo_r1/load_physical_aiavdataset.py)는 `clip_id`와 `t0_us`를 받아 과거 egomotion 16개, 미래 waypoint 64개, 4개 카메라의 프레임과 timestamp를 반환한다. 확인 revision은 `7da704aaaa56b2a0bbce9b7c404ca40b16ed2c93`이다.
- [공식 CoC autolabeler](../../third_party/alpamayo-coc-autolabeler)는 `clip_id`, `event_start_timestamp`, `effect_on_ego_behavior`를 출력하고 2초 history와 6초 future window를 사용한다. 확인 revision은 `4dda80943b8a88b186f0fe8b0340789380c0ce39`이다.
- [공식 Physical AI AV SDK](../../third_party/physical_ai_av)는 timestamp 기반 frame 및 egomotion 접근을 제공한다. 확인 revision은 `2c674fa990a2d779cdc26aba48bd2dd988aa4f79`이다.
- 2026-08-01에 라이선스 동의 및 계정 접근 승인을 확인하고 공식 `reasoning/ood_reasoning.parquet`, `clip_index.parquet`, `features.csv`, `LICENSE.pdf`를 내려받았다. 공식 reasoning의 1,740개 clip index가 전체 clip index와 모두 결합되는 것까지 내부 확인했다.
- NVIDIA AV Dataset License 3절은 Dataset 관련 benchmark/performance 결과를 Confidential Information으로 정의하고, 4.6절은 Dataset 및 파생물 재배포를 제한한다. 따라서 공식 CoC 원문, clip별 측정치와 model-checking 결과는 라이선스 검토 전 공개 산출물에 포함하지 않는다.

### 내려받은 공개 호환 샘플

- 데이터셋: `YSHRobotics/CoC-Nusc`, revision `994bdd94fcf696b6289e2b2bac7fcbded47eed0a`
- 성격: nuScenes를 PhysicalAI-AV layout으로 변환하고 NVIDIA `alpamayo-coc-autolabeler`와 Qwen3.5-35B-A3B로 CoC를 생성한 비공식 호환 데이터
- 라이선스: CC BY-NC-SA 4.0
- 로컬 범위: reasoning 3,218 events/743 clips, metadata, `scene-0001` front-wide video와 timestamp, egomotion
- 원본 설명: [UPSTREAM_README.md](../../data/baseline/coc_nusc/UPSTREAM_README.md)

## 재현 샘플

- `clip_id`: `scene-0001`
- `event_start_timestamp`: `4,800,000 us`
- CoC: `Decelerate to maintain a safe distance from the stopped truck ahead while navigating through the construction zone.`
- 영상 증거: 과거 구간부터 전방 트럭과 공사 구간이 보이며, 시간 진행에 따라 트럭과의 간격이 감소한다.
- 궤적 증거: 속도는 `t0`에서 약 `5.8646 m/s`, 4초 후 `4.0798 m/s`, 6초 후 `4.5531 m/s`다. 6초 전체 변화는 `-1.3115 m/s`이고, 미래 구간의 인접 샘플 속도 차분 중 약 74%가 음수다.
- 시각 자료: [timeline_contact_sheet.jpg](../../artifacts/results/public/scene-0001/timeline_contact_sheet.jpg)

실행:

```bash
python experiments/feasibility/check_sample.py
```

예상 핵심 판정:

```text
schema_and_temporal_join              PASS
closed_set_decision_parse             PASS_DECELERATE
directional_trajectory_conformance    PASS
semantic_grounding                    MANUAL_REVIEW_REQUIRED
safe_distance_property                UNKNOWN_MISSING_OBSTACLE_DISTANCE
formal_model_checking                 NOT_RUN
official_alpamayo_label_replication   SEPARATE_LICENSED_EXPERIMENT_REQUIRED
```

## 주장 가능한 범위

1. CoC와 trajectory의 키 기반 결합 및 시간 정렬이 가능하다.
2. `Decelerate` 같은 CoC 결정을 closed-set action으로 추출할 수 있다.
3. 기록 궤적에서 해당 행동의 방향적 conformance를 계산할 수 있다.
4. 원본 프레임, CoC, trajectory metric 사이의 provenance chain을 만들 수 있다.

## 연속 episode feasibility

`check_episode.py`는 `scene-0001`의 CoC 6개를 하나의 episode로 합성한다. 첫 truck-related `DECELERATE`가 나타난 2.5초에 `SAFE_DISTANCE_TRUCK` 의무와 reaction clock을 생성하고, 3.5초와 4.8초의 반복 CoC에서는 clock을 초기화하지 않는다. 품질 판정이 FAIL인 9.3초와 10.4초 event는 신뢰 상태를 덮어쓰지 못한다.

실행:

```bash
python experiments/feasibility/check_episode.py
```

기본 sustained-deceleration 판정은 0.5초 구간에서 속도가 0.1 m/s 이상 감소하고, 인접 속도 차분 중 70% 이상이 음수인 최초 시점을 사용한다. 이 정의에서 최초 감속 의무는 2.5초, 지속 감속 시작은 약 4.6597초, heuristic 반응 지연은 약 2.1597초다. 이는 raw brake signal이 아니므로 active braking과 coast-down을 구분하지 못한다.

```text
SAFE_DISTANCE_TRUCK triggered                 2.5000s
repeated CoC without clock reset              3.5000s, 4.8000s
sustained deceleration onset                  4.6597s
response latency                              2.1597s

bounded response, deadline 1s                 FAIL
bounded response, deadline 2s                 FAIL
bounded response, deadline 3s                 PASS
longitudinal episode conformance              CONTRACT_DEPENDENT
```

이 결과는 안전 위반을 곧바로 뜻하지 않는다. 어떤 deadline이 안전 한계인지 또는 서비스 목표인지는 차량 동역학, 상대거리와 상대속도, 규칙 계약에서 정해야 한다. 여기서 입증된 것은 반복 CoC마다 독립 검사를 시작하면 최초 의무로부터 약 2.16초의 지연을 놓칠 수 있다는 점과, stateful episode 검사가 그 차이를 검출할 수 있다는 점이다.

감속 검출의 construct validity를 확인하기 위해 window `0.25/0.5/1초`, 최소 속도감소 `0.05/0.1/0.2/0.5m/s`, 음의 미분 비율 `0.5/0.7/0.9`의 36개 조합을 검사했다. 9개 profile은 응답을 검출하지 못했고, 검출된 heuristic latency는 `1.7790~4.0197초`였다. 따라서 `2.1597초`를 실제 제동 또는 actuator latency로 사용하지 않으며 sensitivity anchor로만 보고한다.

## 13-scene cohort 재현

단일 scene 결과의 반복 가능성을 확인하기 위해 reasoning 전체 743개 scene 중 chunk 0에서
trusted CoC 수와 제어 전환 다양성이 높은 12개 scene을 선정하고 `scene-0001`과 함께
13개 독립 episode로 검사했다. scene 번호는 연속 주행을 뜻하지 않으므로 서로 하나의
시간축으로 이어 붙이지 않는다.

```bash
python experiments/feasibility/check_cohort.py \
  --output artifacts/results/public/cohort-13/weak-kinematic-cohort-result.json
python experiments/uppaal/run_cohort_verification.py \
  --output artifacts/results/public/cohort-13/uppaal-cohort-verification-result.json
```

| 항목 | 결과 |
|---|---:|
| 독립 scene | 13 |
| CoC event | 85 |
| trusted event | 78 |
| 단일 종방향 계약 평가 가능 | 30 |
| weak kinematic PASS | 29 |
| weak kinematic FAIL 후보 | 1 |
| camera 확보 scene | 1 |
| UPPAAL 모델 | 39 |
| symbolic query 판정 | 156 |
| mutation oracle 일치 | 39/39 |

FAIL 후보는 `scene-0028@6500000us`의 “red traffic light에서 정지하기 위해
감속” CoC다. 이벤트 시점 속도는 약 `4.8784m/s`였고 기본 검출 설정에서는 3초
이내 sustained decrease를 찾지 못했다. 같은 구간에서 표본 속도는 약
`4.88 -> 5.43m/s`로 증가했다. UPPAAL baseline도 이 episode의
`A[] not weak_response_violation` 반례를 반환했다.

그러나 이 후보는 threshold에 완전히 불변하지 않다. `D=3s`에서 window, 최소
속도변화와 방향비율을 바꾼 27개 profile 중 5개가 `2.8396~2.9589s`의 반응을
검출했고 22개는 검출하지 못했다. 또한 scene-0028 영상과 raw actuator가 현재 없어
CoC timestamp가 anticipatory label인지, 실제 제동 지연인지, label 오류인지 구분할
수 없다. 따라서 판정은 `CAMERA_AND_RAW_ACTUATOR_CONFIRMATION_REQUIRED`이며 실제
안전 위반 증거로 승격하지 않는다.

각 event는 reasoning parquet의 원본 index를 보존한 JSON pointer, reasoning/egomotion
SHA-256과 연결된다. 복합 명령(`STOP then ACCELERATE`), 비방향 명령과 low-quality
CoC는 단일 방향 계약에서 제외한다. 합성 mutation은 provenance 및 response query가
실제로 결함을 검출하는지 시험하는 hard negative 역할만 한다.

## chunk 0 전체 94-scene 확장

선별 cohort의 selection bias를 줄이기 위해 `clip_index.chunk == 0`이면서 reasoning
label이 존재하고 egomotion archive에 포함된 scene 전체를 자동 선택했다.

```bash
python experiments/feasibility/check_cohort.py --chunk 0 \
  --output artifacts/results/public/chunk-0000-94/weak-kinematic-cohort-result.json
python experiments/uppaal/run_cohort_verification.py \
  --cohort-result artifacts/results/public/chunk-0000-94/weak-kinematic-cohort-result.json \
  --model-dir artifacts/intermediate/uppaal-models/chunk-0000-94 \
  --output artifacts/results/public/chunk-0000-94/uppaal-cohort-verification-result.json
```

| 항목 | 결과 |
|---|---:|
| 독립 scene | 94 |
| CoC / trusted CoC | 403 / 290 |
| 단일 종방향 계약 평가 가능 | 134 |
| PASS / FAIL 후보 | 129 / 5 |
| camera+timestamp 확보 | 11 scene |
| UPPAAL baseline+mutation 모델 | 282 |
| symbolic query 판정 | 1,128 |
| mutation oracle 일치 | 282/282 |

최초 실행에서는 8개 FAIL이 나왔으나 영상과 event 시점 속도를 함께 검토한 결과,
`scene-0046`의 STOP은 이미 `0.0001m/s`, `scene-0159`의 두 YIELD는 각각
`0.2179/0.3999m/s`였다. 이미 의무를 만족한 상태에 추가 감속을 요구한 checker
오류이므로 `STOP/YIELD && speed <= 0.5m/s`를 `PASS_ALREADY_SATISFIED`로
명세하고 전체 모델을 재생성했다.

남은 검토 후보는 `scene-0019`, `0028`, `0042`, `0065`, `0074`다. 영상상
보행자·신호·선행차 등 일부 원인은 관측되지만, 반복/stale CoC, anticipatory label,
semantic grounding 오류와 실제 response delay를 현재 신호만으로 구분할 수 없다.
따라서 5건 모두 safety violation이 아니라 `UNKNOWN_REVIEW_REQUIRED`다. contact sheet와
triage는 `artifacts/results/public/chunk-0000-94/video-review-result.json`에 기록한다.

이 확장은 한 scene의 결과를 일반화한 것이 아니라 동일 checker가 더 다양한 episode에서
어디서 실패하고, 영상 검토가 명세를 어떻게 수정하는지 보여주는 반복성 증거다. UPPAAL
PASS 역시 offline 판정을 재생한 trace-model mutation oracle의 일치이며, 비결정적 환경의
정책 안전 증명은 아니다.

## 아직 주장할 수 없는 범위

1. 전방 트럭까지의 거리와 상대속도가 없으므로 안전거리 유지 여부를 증명할 수 없다.
2. 영상 육안 확인은 scalable하거나 독립적인 semantic grounding 평가가 아니다.
3. source quality score는 같은 계열 VLM의 self-evaluation이므로 독립 gold evidence로 사용하지 않는다.
4. 한 기록 궤적의 conformance는 가능한 환경 분기 전체에 대한 symbolic safety proof가 아니다.
5. 비공식 호환 CoC 결과를 NVIDIA human-refined CoC의 품질 근거로 일반화할 수 없다.
6. 현재 episode checker는 기록된 하나의 egomotion을 검사하며 비결정적 환경 분기를 탐색하지 않는다.

## 공식 NVIDIA 데이터 내부 feasibility

라이선스 제한 영역에서 validation split의 3-event episode 하나를 선정하고 공식 SDK로 해당 clip의 egomotion만 스트리밍했다. `experiments/feasibility/analyze_nvidia_official_episode.py`는 reasoning index, 전체 clip index, archive member와 egomotion을 연결하고 감속, 좌측 조향, 속도 회복의 후보 방향 계약을 계산한다. `experiments/uppaal/run_nvidia_official_episode.py`는 이 연속 episode와 지연/삭제 mutation을 timed automata로 변환하여 내부 검증한다.

상세 결과와 모델은 `data/restricted/nvidia_physicalai/internal-derived/`에 두며 공개 또는 재배포하지 않는다. 후보 `D=1s`는 mutation 검출용 feasibility parameter일 뿐 물리적 안전 deadline으로 정당화되지 않았다. 현재 결과는 공식 데이터로 provenance-aware episode model checking 파이프라인을 실행할 수 있다는 내부 기술 검증이며, 안전거리 또는 충돌 안전성 증명이 아니다.

### validation 다중-event 내부 cohort

validation의 다중-event clip 55개 중 event cluster 다양성과 필요한 feature 존재 여부를 기준으로 10개를 목적 표집했다. 공사구간뿐 아니라 보행자, 특수차량, 복합교차로, 자전거, 긴급상황과 기타 long-tail cluster를 포함한다. 통계적 대표 표본은 아니다.

```bash
python experiments/feasibility/analyze_nvidia_official_cohort.py
python experiments/feasibility/analyze_nvidia_obstacle_feasibility.py
python experiments/uppaal/run_nvidia_official_cohort.py
```

내부 결과는 10 episode, 23 event다. 복합 종방향 명령 1개는 단일 계약에서 제외했다. 나머지 22개 중 후보 `D=1s` 방향 계약에서 18개는 반응을 검출했고 1개는 이미 만족된 상태였으며 3개는 반응을 검출하지 못했다. 이 3개는 safety violation이 아니라 threshold, anticipatory annotation, semantic mismatch와 실제 지연을 구분해야 하는 검토 후보다.

`obstacle.offline`의 4D track, oriented box와 `vehicle_dimensions`를 결합해 event 23개 중 18개에서 전방 corridor의 기하 후보, 종방향 gap, gap-rate와 후보 TTC를 구성했다. 다만 nearest corridor track이 CoC 원인 객체라는 semantic association은 아직 증명되지 않았으므로 `UnsafeDistance` 판정은 생성하지 않는다.

UPPAAL에서는 episode별 baseline, provenance mutation, response deletion mutation, request-order mutation의 40개 모델과 200개 query를 실행했다. mutation oracle은 40/40 일치했다. 이 수치와 clip별 결과는 `LICENSE_RESTRICTED_INTERNAL_RESULT`이며 외부 공개 전 별도 승인이 필요하다.

## 다음 증거 게이트

라이선스 허용 범위에서 연속 CoC가 있는 5~10개 episode로 내부 반복 실험을 확대한다. 각 `clip_id`에 대해 `egomotion`, front-wide camera timestamp, 가능하면 `obstacle.offline`을 선택 접근한다. obstacle track의 거리·상대속도를 확보하면 `Decelerate -> bounded response`와 `A[] not UnsafeDistance`의 입력 계약을 실제 필드로 구성할 수 있다. 그다음 환경 반응과 sensor delay를 bounded nondeterministic branch로 추가한다. 외부 논문에 공식 데이터 기반 수치, 원문 또는 그림을 싣기 전에는 NVIDIA의 서면 허가나 적절한 법률 검토를 별도 gate로 둔다.

## 종방향 parameter-grid falsification feasibility

`check_longitudinal_falsification.py`는 scene의 최초 truck-related 감속 의무 시점에서 실제 ego 속도를 seed로 읽고, 누락된 gap과 제동 물리를 명시적인 합성 grid로 열거한다. 이 도구는 reachable state graph 또는 SAT/SMT encoding을 탐색하는 model checker가 아니라 deterministic scenario sweep이다.

```bash
python experiments/feasibility/check_longitudinal_falsification.py \
  > artifacts/results/public/scene-0001/longitudinal-falsification-result.json
```

기본 grid에서 응답지연 `0.5/1/2/2.1597초`의 collision scenario 수는 각각 `3/6/12/13`, 모든 열거 제동조건에서 collision witness가 없었던 최소 시험 gap은 `10/10/15/20m`였다. 마지막 delay는 위의 불안정한 speed-trace heuristic을 sensitivity anchor로 다시 사용한 것이다. 이는 지연과 차량 물리를 합성한 counterexample 탐색의 feasibility다. 실제 gap과 차량 calibration이 없으므로 scene 안전 판정은 계속 `UNKNOWN`이며, finite grid의 no-witness는 연속 상태공간의 안전 proof가 아니다.

방법 서베이, fine-tuning 연결 구조와 단계별 검증 계획은 [E2E fine-tuning과 모델체킹 서베이](../../docs/surveys/system/2026-08-01-e2e-finetuning-model-checking-survey.md)에 정리한다.

## UPPAAL timed-episode 모델

사용자가 제공한 배포본은 `runtime/solvers/uppaal-5.0.0-linux64/`에 설치했고 원본
archive는 `archive/installers/uppaal-5.0.0-linux64.zip`에 보존했다. `verifyta --version`은
`UPPAAL 5.0.0 (rev. 714BA9DB36F49691)`을 반환한다.

현재 실제 증거로 모델링 가능한 범위는 collision dynamics가 아니라 다음 timed protocol이다.

```text
first trusted DECELERATE  0ms
repeated triggers         1000ms, 2300ms
heuristic response        2160ms
low-quality event         6800ms
```

`experiments/uppaal/generate_models.py`가 baseline과 네 mutation을 생성한다.

- `normal`: 3초 candidate deadline
- `deadline_2s`: 2초 candidate deadline
- `clock_reset`: 반복 trigger가 response clock을 reset
- `no_response`: response event 제거
- `untrusted_overwrite`: low-quality event가 trusted state를 overwrite

여섯 query는 obligation 활성화·응답 도달성, deadline miss, clock reset, untrusted overwrite와 deadlock을 검사한다. XML 구조, variant completeness와 runner output parser에 대한 단위 테스트는 통과했다.

학술용 verifier license 활성화 후 다섯 variant와 여섯 query, 총 30개 symbolic 판정을 실행했다. `normal`은 모두 PASS했고 `deadline_2s`의 deadline query, `clock_reset`의 clock-reset query, `no_response`의 response reachability와 deadline query, `untrusted_overwrite`의 trust-policy query가 각각 FAIL했다. 모든 결과가 사전 작성한 mutation oracle과 일치해 [UPPAAL 실행 결과](../../artifacts/results/public/scene-0001/uppaal-verification-result.json)의 overall은 `PASS`다.

첫 symbolic 실행에서는 의도적인 episode terminal state도 UPPAAL deadlock으로 판정되었다. diagnostic trace로 원인을 확인하고 `CoC.Done`에 terminal stutter를 명시한 뒤 모든 variant의 `A[] not deadlock`이 PASS했다. 전체 trace는 [uppaal-traces](../../artifacts/results/public/scene-0001/uppaal-traces/)에 보존한다. 이 PASS는 timed-protocol mutation 검출 feasibility이며 collision 또는 실제 차량 안전 증명이 아니다. 설치·생성·실행 절차는 [experiments/uppaal/README.md](../uppaal/README.md)에 기록한다.
