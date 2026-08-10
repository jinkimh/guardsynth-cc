# Alpamayo 생태계 공식 데이터 기반 시간계약·모델체킹 실험 보고서

> 문서 등급: `LICENSE_RESTRICTED_INTERNAL_RESULT`  
> 실험 ID: `ALP-EXP-001`  
> 기준일: 2026-08-01  
> 외부 공개: NVIDIA Autonomous Vehicle Dataset License 검토 및 별도 승인 전 금지

## 1. 문서 목적

이 문서는 논문 원고가 아니다. NVIDIA Alpamayo 생태계에서 제공되는 공식 reasoning annotation,
egomotion과 obstacle track을 이용하여 다음 질문의 기술적 feasibility를 확인한 내부 실험 기록이다.

1. 공식 reasoning event를 실제 주행 궤적과 `clip_id` 및 timestamp로 연결할 수 있는가?
2. 단일 event가 아니라 연속 event episode를 시간계약으로 변환할 수 있는가?
3. 관측 궤적이 annotation의 제어 방향과 일치하는지 자동 검사할 수 있는가?
4. UPPAAL이 지연, 응답 삭제, 순서 변경과 provenance 변조를 반례로 검출하는가?
5. obstacle track으로 안전거리 모델의 입력인 gap과 gap-rate를 구성할 수 있는가?
6. 현재 증거로 무엇을 주장할 수 있고, 무엇을 주장해서는 안 되는가?

## 2. 가장 중요한 범위 구분

### 2.1 이번 실험에서 사용한 것

- 공식 데이터셋: `nvidia/PhysicalAI-Autonomous-Vehicles`
- 공식 reasoning 파일: `reasoning/ood_reasoning.parquet`
- 공식 clip index와 feature-presence metadata
- 공식 SDK `physical_ai_av`를 통한 egomotion 및 obstacle member 선택 스트리밍
- UPPAAL 5.0.0을 이용한 timed episode 및 mutation 검증

### 2.2 이번 실험에서 사용하지 않은 것

- `nvidia/Alpamayo-R1-10B` 모델 가중치 추론
- Alpamayo가 새로 생성한 Chain-of-Causation reasoning trace
- Alpamayo fine-tuning 또는 RL post-training
- closed-loop simulator 또는 실차 제어
- raw brake, throttle, steering actuator command

따라서 이번 결과는 **Alpamayo 신경망 자체의 안전성 검증이 아니다.** 정확한 표현은 다음과 같다.

> Alpamayo 생태계의 공식 human-refined reasoning annotation과 대응 주행 데이터로
> provenance-aware timed episode model checking을 구성할 수 있음을 확인했다.

## 3. 데이터와 provenance

### 3.1 공식 출처

| 구분 | 위치 | 역할 |
|---|---|---|
| Alpamayo 모델 | <https://huggingface.co/nvidia/Alpamayo-R1-10B> | 향후 모델 출력 검증 대상 |
| 추론 코드 | <https://github.com/NVlabs/alpamayo> | 모델 입력 및 추론 절차 |
| 공식 AV 데이터 | <https://huggingface.co/datasets/nvidia/PhysicalAI-Autonomous-Vehicles> | reasoning, 영상, 궤적, obstacle |
| 공식 SDK | <https://github.com/NVlabs/physical_ai_av> | clip 및 feature 선택 접근 |

확인한 데이터셋 revision은 다음과 같다.

```text
b719eea7f0a63619ef51ec7f54178af0937ef050
```

사본 위치와 SHA-256은 같은 디렉터리의 `COPY_MANIFEST.md`에서 관리한다.

### 3.2 reasoning 파일 구조

`ood_reasoning.parquet`의 `clip_id`는 일반 열이 아니라 Parquet index다. 각 행은 다음 필드를 가진다.

```text
index: clip_id
feature: camera_front_wide_120fov
event_cluster: long-tail category
split: train | val
events: JSON string
  - event_start_frame
  - event_start_timestamp
  - coc
```

공개된 `coc`는 event별 행동 문장이다. Alpamayo 모델이 출력하는 긴 구조적 reasoning trace 전체와
동일한 데이터 구조가 아니다. 이 차이 때문에 본 실험은 annotation-to-trajectory conformance로
분류한다.

### 3.3 전체 구조 검사

| 항목 | 확인 결과 |
|---|---:|
| reasoning clip 행 | 1,740 |
| reasoning event | 2,077 |
| train | 1,450 clip / 1,728 event |
| validation | 290 clip / 349 event |
| 전체 clip index 결합 | 1,740 / 1,740 |
| JSON parse 오류 | 0 |
| 다중-event episode | 308 |
| 최대 event 수 | 4 |
| episode 내부 timestamp 역전 | 0 |

같은 episode에서 event frame 차이와 timestamp 차이는 10 Hz 관계를 보존했다. 따라서 event 순서를
하나의 시간축으로 옮길 수 있다.

## 4. 실험 파이프라인

```text
Official reasoning parquet
       │ clip_id + event timestamp
       ▼
Official clip index / feature presence
       │ chunk + archive member
       ▼
egomotion ───────────── obstacle.offline
       │                       │
       │ speed/yaw response    │ box/gap/gap-rate/TTC candidate
       └───────────┬───────────┘
                   ▼
        Candidate timed contracts
                   │
          provenance-preserving transform
                   ▼
             UPPAAL automata
                   │
        baseline + controlled mutations
                   ▼
       property verdicts and counterexamples
```

모든 변환은 원본 `clip_id`, event source index, timestamp, 원본 파일 hash와 archive member를 보존한다.

## 5. 후보 시간계약

### 5.1 행동 정규화

event 문장의 첫 행동을 다음 후보 계약으로 정규화했다.

| 자연어 행동 계열 | 후보 intent | 관측 signal |
|---|---|---|
| decelerate, strong/gentle deceleration, yield, stop | `DECREASE_SPEED` | speed |
| resume speed, accelerate, gentle acceleration | `INCREASE_SPEED` | speed |
| steer/adjust left | `TURN_LEFT` | yaw |
| steer/adjust right | `TURN_RIGHT` | yaw |

한 문장에 감속 후 가속처럼 상반된 행동이 함께 있으면 `EXCLUDED_COMPOUND`로 분리한다. 내부 전환
timestamp가 없으므로 임의 분해하지 않는다.

### 5.2 응답 검출 heuristic

기본 후보 검출 조건은 다음과 같다.

```text
candidate deadline       1.0 s
response window          0.5 s
minimum speed delta      0.1 m/s
minimum yaw delta        1 degree
direction fraction       0.6
```

이 값들은 안전 규격이 아니다. mutation 검출 및 model-checking feasibility를 위한 candidate parameter다.
`D=1s`를 물리적으로 정당화하려면 gap, 상대속도, 최대 제동력, jerk, 노면과 actuator delay가 필요하다.

## 6. 공식 validation cohort

### 6.1 선정 원칙

validation의 다중-event episode 55개 중 10개를 목적 표집했다.

- 다중 event 보유
- egomotion, front-wide camera와 obstacle feature 존재
- event cluster 다양성
- 종방향 및 횡방향 전환 포함
- 공사구간에만 편중되지 않도록 구성

포함 cluster는 보행자, 특수·비정상 차량 행동, 복합교차로, 자전거·마이크로모빌리티,
긴급상황, 기타 long-tail, 공사구간의 7종이다. 이는 통계적 대표 표본이 아니다.

### 6.2 방향 conformance 결과

| 항목 | 결과 |
|---|---:|
| episode | 10 |
| event | 23 |
| 단일 후보 계약 적용 가능 | 22 |
| 후보 반응 검출 | 18 |
| event 시점에 이미 만족 | 1 |
| 후보 1초 내 반응 미검출 | 3 |
| 복합 명령 제외 | 1 |

세 미검출 event는 모두 좌측 조향 계열이었다. 따라서 이를 일반적인 제어 실패나 안전 위반으로
해석하지 않는다. yaw 기반 lateral checker, anticipatory annotation, 이미 진행 중인 maneuver,
곡선 도로, 안전상 감속에 의한 조향 선점 가능성을 우선 검토해야 한다.

## 7. Obstacle 기반 안전계약 입력 feasibility

### 7.1 사용 필드

`obstacle.offline`에서 다음 필드를 확인했다.

```text
timestamp_us, track_id
center_x, center_y, center_z
size_x, size_y, size_z
orientation quaternion
label_class
reference_frame = rig
```

공식 좌표계의 `x=전방`, `y=좌측`, `z=상방`을 사용했다. `vehicle_dimensions`의 차체 길이,
폭과 rear-axle-to-center를 결합했다.

### 7.2 계산

각 event에서 다음 값을 계산했다.

1. quaternion yaw를 이용한 obstacle oriented-box의 x/y projected half extent
2. ego와 obstacle의 횡방향 box overlap
3. 전방 corridor 후보의 종방향 gap
4. 동일 track의 event 전후 0.5초 gap 선형 변화율
5. closing speed가 양수일 때의 후보 TTC

### 7.3 결과와 제한

| 항목 | 결과 |
|---|---:|
| 검사 event | 23 |
| 전방 corridor 기하 후보 존재 | 18 |
| gap-rate 계산 가능 | 18 |
| 기하 입력 구성 | `PASS` |
| CoC 원인 객체와 track 연결 | `UNRESOLVED` |
| 안전거리 계약 | `NOT_JUSTIFIED` |
| 물리적 안전성 | `UNKNOWN` |

최근접 corridor track은 CoC가 언급한 객체와 다를 수 있다. 그러므로 후보 TTC가 작더라도 충돌 위험
증거로 사용하지 않는다. 영상, class, track continuity와 CoC noun phrase를 결합한 semantic association
gate가 필요하다.

## 8. UPPAAL 모델

### 8.1 구성

episode별로 다음 automata를 생성했다.

```text
EpisodeSource
  └─ 관측 request와 response를 timestamp 순서로 broadcast

ResponseMonitor[i]
  ├─ WaitRequest
  ├─ WaitResponse, clock <= D
  ├─ Done
  └─ Miss

OrderMonitor
  ├─ ExpectRequest[i]
  ├─ Done
  └─ OrderViolation
```

응답 의무는 event별 독립 clock으로 관리한다. 이는 앞 event의 응답이 끝나기 전에 다음 event가
도착할 수 있는 실제 연속 제어를 표현하기 위한 것이다.

### 8.2 모델 variant

각 episode에 네 variant를 만들었다.

| Variant | 의미 | 기대 검출 |
|---|---|---|
| `baseline` | 관측 request/response | 원본 후보 판정 보존 |
| `provenance_mutation` | 출처 신뢰 상태 변조 | provenance 위반 |
| `response_mutation` | 관측 응답 하나 삭제 | candidate response 위반 |
| `order_mutation` | 앞의 두 request 순서 교환 | order 및 pairing 위반 |

### 8.3 query

```text
E<> Source.Done
A[] not candidate_response_violation
A[] not order_violation
A[] not provenance_violation
A[] not deadlock
```

### 8.4 검증 결과

| 항목 | 결과 |
|---|---:|
| episode | 10 |
| variant / episode | 4 |
| UPPAAL 모델 | 40 |
| query 판정 | 200 |
| mutation oracle 일치 | 40 / 40 |
| overall | `PASS` |
| physical safety | `UNKNOWN` |

`PASS`는 checker가 정의한 candidate contract와 mutation oracle을 일관되게 실행했다는 뜻이다.
Alpamayo 모델, 실제 차량 또는 가능한 모든 환경 분기의 안전성을 증명했다는 뜻이 아니다.

## 9. 모델체킹에서 드러난 연구 문제

### 9.1 병렬 obligation과 safety preemption

실제 episode에는 0.3초와 0.8초 간격의 request가 존재했다. 이전 응답 의무가 끝나기 전에 다음
명령이 들어올 수 있다.

```text
TURN_LEFT obligation
       │ 0.3 s
       ├────────── DECREASE_SPEED obligation
       │
       └─ preserve, suspend, cancel, or preempt?
```

가능한 의미론은 다음과 같다.

- `preserve-all`: 모든 미완료 의무를 유지한다.
- `latest-command`: 최신 명령이 이전 명령을 대체한다.
- `axis-independent`: 종방향과 횡방향 의무를 병렬 유지한다.
- `braking-priority`: 위험 감속이 조향 의무를 일시 중지하거나 취소한다.

동일 trace도 의미론에 따라 PASS와 FAIL이 바뀔 수 있다. 다음 UPPAAL 모델의 핵심 비교 대상이다.

### 9.2 복합 자연어 명령의 시간 정보 부족

한 event 문장에 감속과 후속 가속이 함께 포함된 사례가 있었다. sub-action timestamp가 없으므로
timed automata로 유일하게 변환할 수 없다. 자연어 annotation과 제어 계약 사이에 구조화 단계가
반드시 필요하다는 직접적인 예다.

### 9.3 객체 association의 비결정성

CoC hazard가 여러 obstacle track 중 무엇을 가리키는지 확정되지 않는다. 다음 모델에서는 plausible
track 집합을 비결정적으로 선택하고 속성을 구별해야 한다.

```text
A[] all plausible associations are safe
E<> at least one plausible association violates the distance contract
```

### 9.4 property coupling

request 순서를 교환하면 order 위반뿐 아니라 request-response pairing도 깨져 response 위반이 함께
발생했다. 위반 query 수만 세면 root cause를 잘못 설명할 수 있다. provenance, ordering, pairing,
deadline, physical safety 순서의 진단 계층이 필요하다.

### 9.5 deadline 정당화

현재 `D=1s`는 candidate다. 향후 deadline은 다음과 같이 상태 의존적으로 구성해야 한다.

```text
D_safe = f(gap, relative_speed, ego_speed,
           max_deceleration, jerk_limit,
           actuator_delay, road_friction,
           object uncertainty)
```

고정 deadline보다 parameterized 또는 state-dependent contract가 적절하다.

## 10. 주장 가능 범위

### 10.1 현재 증거가 지지하는 주장

1. 공식 reasoning event 2,077개를 1,740개 clip 및 전체 index와 추적 가능하게 결합할 수 있다.
2. 공식 validation 다중-event episode를 egomotion과 시간 정렬할 수 있다.
3. 행동 문장을 후보 종·횡방향 계약으로 정규화하고 관측 방향 conformance를 검사할 수 있다.
4. obstacle track으로 전방 gap, gap-rate와 후보 TTC 입력을 구성할 수 있다.
5. UPPAAL이 통제된 provenance, response, order mutation을 예상대로 검출한다.
6. 연속 제어에는 병렬 obligation, preemption과 compound-command semantics가 필요하다.

### 10.2 현재 증거가 지지하지 않는 주장

1. Alpamayo 모델이 안전하다 또는 위험하다.
2. 후보 미응답 3건이 실제 제어 실패다.
3. 후보 TTC가 실제 CoC hazard의 TTC다.
4. `D=1s`가 안전 deadline이다.
5. baseline UPPAAL PASS가 충돌 부재를 증명한다.
6. 10개 목적 표본 결과가 전체 데이터 또는 실제 도로 분포를 대표한다.
7. 공식 annotation이 모델 학습의 완전한 ground truth다.

## 11. 재현 절차

### 11.1 사전 조건

- Hugging Face 개인 계정의 NVIDIA 데이터셋 접근 승인
- 로컬 `hf auth login`
- `physical_ai_av==0.2.2`
- UPPAAL 5.0.0 및 유효한 academic license
- 공식 데이터 및 결과를 외부로 복사하지 않는 access-controlled 작업환경

### 11.2 공식 metadata 분석

```bash
python3 feasibility/analyze_nvidia_official_episode.py
python3 feasibility/analyze_nvidia_official_cohort.py
```

### 11.3 obstacle 입력 분석

```bash
python3 feasibility/analyze_nvidia_obstacle_feasibility.py
```

### 11.4 UPPAAL 검증

```bash
python3 uppaal/run_nvidia_official_episode.py
python3 uppaal/run_nvidia_official_cohort.py
```

### 11.5 회귀 테스트

```bash
python3 -m unittest discover -s feasibility -p 'test_*.py'
```

예상 결과는 20개 test 성공과 cohort mutation oracle 40/40 일치다.

## 12. 산출물 지도

| 산출물 | 경로 |
|---|---|
| 단일 공식 episode 분석기 | `feasibility/analyze_nvidia_official_episode.py` |
| 공식 cohort 분석기 | `feasibility/analyze_nvidia_official_cohort.py` |
| obstacle 입력 분석기 | `feasibility/analyze_nvidia_obstacle_feasibility.py` |
| 단일 episode UPPAAL 실행기 | `uppaal/run_nvidia_official_episode.py` |
| cohort UPPAAL 실행기 | `uppaal/run_nvidia_official_cohort.py` |
| cohort 내부 결과 | `evidence/data/nvidia_physicalai/internal-derived/cohort-10/` |
| 사본 관리 manifest | `evidence/data/nvidia_physicalai/COPY_MANIFEST.md` |
| 전체 feasibility 문서 | `feasibility/README.md` |

## 13. 다음 실험

### ALP-EXP-002: obligation arbitration

동일 episode에 `preserve-all`, `axis-independent`, `latest-command`, `braking-priority` 의미론을 적용해
판정이 뒤집히는 조건을 비교한다.

### ALP-EXP-003: semantic track association

미응답 후보와 corridor candidate를 우선으로 전방 영상을 확인하고 CoC noun phrase, obstacle class,
track continuity를 결합한다. association uncertainty는 nondeterministic branch로 보존한다.

### ALP-EXP-004: physical safe-distance contract

gap, closing speed, ego speed, 제동 한계와 delay 범위를 이용해 state-dependent deadline과
`UnsafeDistance` 상태를 정의한다.

### ALP-EXP-005: actual Alpamayo inference

선정 clip을 Alpamayo 입력 형식인 4-camera history와 egomotion history로 변환하고 모델이 생성한
reasoning trace 및 6.4초 trajectory를 같은 checker에 넣는다. 이 단계부터 annotation 검증과
Alpamayo model-output 검증을 명확히 비교할 수 있다.

## 14. 최종 내부 판정

```text
official data provenance             PASS
reasoning-to-clip traceability       PASS
multi-event episode construction     PASS
egomotion candidate conformance      FEASIBLE_WITH_REVIEW_CANDIDATES
obstacle geometric inputs            PASS
semantic hazard association          UNRESOLVED
UPPAAL mutation detection            PASS
normative safety deadline            NOT_ESTABLISHED
physical collision safety            UNKNOWN
Alpamayo model safety                NOT_EVALUATED
```

이번 실험의 핵심 성과는 안전을 증명한 것이 아니다. 공식 Alpamayo 관련 데이터에서 자연어 행동
annotation, 관측 궤적, obstacle track과 formal timed model 사이의 추적 가능한 연결을 실제로
구성했고, 연속 제어의 의미론이 단일 event checker보다 본질적으로 어렵다는 것을 확인한 것이다.
