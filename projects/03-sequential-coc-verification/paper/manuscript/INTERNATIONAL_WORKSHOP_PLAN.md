# 국제 워크숍 수준 보강 계획 및 수행 상태

대상 원고: `paper/demestic-journal/main.tex`

관련 결과 문서: `INTERNATIONAL_WORKSHOP_RESULTS.md`

실험 산출물 위치: `artifacts/results/public/workshop-boost/`

본 문서는 국내 학술지형 원고를 국제 워크숍 투고 후보 수준으로 끌어올리기 위해 세운 계획과 현재 수행 상태를 정리한다. 이전 버전의 계획서에는 일부 항목이 아직 제안 단계로 남아 있었으나, 현재 문서는 확장 실험 이후의 상태를 기준으로 정리한다.

## 1. 현재 논문의 중심 주장

본 논문의 주장은 reasoning-augmented driving annotation의 물리적 안전성 증명이 아니다. 현재 가장 방어 가능한 중심 주장은 다음과 같다.

> Reasoning-augmented driving annotation은 E2E/VLA 주행 학습에 유용한 의미 신호를 제공하지만, 자연어 판단 event, 반복 판단, ego-motion response, provenance, scene boundary 사이의 시간적 의미론이 닫혀 있지 않으면 학습 샘플과 검증 verdict가 서로 모순될 수 있다. 본 연구는 이러한 annotation을 timed obligation으로 변환하고, UPPAAL timed observer network와 mutation oracle을 사용하여 protocol-level consistency를 감사한다.

이 포지셔닝은 세 가지 이유로 국제 워크숍에 적합하다.

1. 안전성 인증이라고 과장하지 않는다.
2. reasoning annotation을 학습 데이터로 사용하는 최신 E2E/VLA driving 흐름과 직접 연결된다.
3. review candidate, semantic flip, mutation oracle, scene-boundary gate라는 구체적 산출물을 제공한다.

## 2. 연구 질문 정리

현재 원고는 다음 네 가지 연구 질문으로 정리하는 것이 가장 일관적이다.

- RQ1: 자연어 CoC reasoning event를 timed obligation으로 변환할 수 있는가?
- RQ2: 반복 reasoning event의 의미론이 response deadline verdict를 바꾸는가?
- RQ3: UPPAAL observer network와 mutation oracle이 annotation 처리 오류를 감지하는가?
- RQ4: scene continuity 증거가 없을 때 obligation carry-over를 차단하고, 증거가 있을 때 긴 episode 검증으로 확장할 수 있는가?

## 3. 실험 수행 상태

| Experiment | Status | Output / Evidence | Claim strengthened |
|---|---|---|---|
| Single-scene feasibility | Done | `artifacts/results/public/scene-0001/*` | timed obligation 변환 가능성 |
| Weak kinematic cohort | Done | `weak-kinematic-chunk0.json` | 94 scene batch screening 가능성 |
| Detector sensitivity | Done | `workshop-experiment-results.json` | weak witness 불확실성 정량화 |
| UPPAAL cohort verification | Done | `uppaal-cohort-verification-result.json` | 282 models, 1,128 queries, oracle match |
| Local scene negative-control audit | Done | `local-scene-continuity-negative-control.json` | CoC-Nusc 단독 scene 연결 금지 근거 |
| Dedicated boundary-carryover negative control | Done | `boundary-negative-control-result.json` | boundary carry-over 금지를 formal property로 검증 |
| Trainval metadata mirror audit | Done as pilot | `workshop-experiment-results.json` | 연결 가능한 scene 후보 탐색 |
| Multi-scene loop verification | Done | `uppaal-loop-verification-result.json` | 연결 후 deadline property 별도 검증 |
| Multi-scene pattern analysis | Done | `uppaal-loop-pattern-analysis.json` | boundary failure와 deadline failure 분리 |
| Script checker baseline | Done | `workshop-experiment-results.json` | UPPAAL의 역할을 정직하게 한정 |
| Official nuScenes mini sanity check | Done | `nuscenes-official-mini-continuity-audit.json` | official schema-level continuity evidence |
| Camera/video spot-check | Partially done | `video-review-result.json`, contact sheets | review candidate가 영상 검토 후보로 이어짐 |
| Remaining feasibility audit | Done | `remaining-experiments-feasibility.json` | 미완료 실험의 근거와 한계 명시 |

## 4. 수행된 핵심 결과

### 4.1 Weak kinematic cohort

실행:

```bash
python projects/03-sequential-coc-verification/experiments/feasibility/check_cohort.py \
  --chunk 0 \
  --output artifacts/results/public/workshop-boost/weak-kinematic-chunk0.json
```

결과:

| Metric | Value |
|---|---:|
| Scenes | 94 |
| CoC annotations | 403 |
| Trusted events | 290 |
| Evaluable directional contracts | 134 |
| Contract pass | 129 |
| Contract fail / high-priority review candidate | 5 |
| Camera available scenes | 11 |

해석:

5개 fail은 unsafe control의 증거가 아니다. 3초 후보 deadline과 ego-speed witness 기준에서 response 확인이 불충분한 high-priority review candidate이다.

### 4.2 Detector sensitivity

각 evaluable event에 대해 27개 detector profile을 평가했다.

| Detection profiles agreeing | Event count |
|---|---:|
| 27/27 | 72 |
| 18--26/27 | 51 |
| 9--17/27 | 2 |
| 1--8/27 | 4 |
| 0/27 | 1 |

Review priority:

| Priority | Event count |
|---|---:|
| No special review flag | 72 |
| Threshold-sensitive camera review | 53 |
| Camera and raw actuator confirmation required | 5 |

이 결과는 단일 detector setting의 fail을 곧바로 violation으로 승격하지 않고, detector profile 민감도를 검토 우선순위와 학습 가중치에 반영해야 함을 보여준다.

### 4.3 UPPAAL cohort verification

실행:

```bash
python projects/03-sequential-coc-verification/experiments/uppaal/run_cohort_verification.py \
  --cohort-result artifacts/results/public/workshop-boost/weak-kinematic-chunk0.json \
  --model-dir artifacts/intermediate/uppaal-models/chunk-0000-94 \
  --output artifacts/results/public/workshop-boost/uppaal-cohort-verification-result.json
```

결과:

| Metric | Value |
|---|---:|
| Scenes | 94 |
| UPPAAL models | 282 |
| Query evaluations | 1,128 |
| All mutation oracles match | true |
| Overall | PASS |

해석:

Baseline, provenance mutation, response mutation이 기대한 verdict와 일치했다. 이는 checker가 출처 훼손과 response 훼손을 무시하지 않고 의도한 query violation으로 감지한다는 sanity evidence이다.

### 4.4 Local negative-control 및 boundary-carryover negative-control

Local metadata audit 결과 CoC-Nusc 단독 데이터는 inter-scene continuity evidence를 제공하지 않는다.

| Item | Result |
|---|---|
| CoC-Nusc egomotion files | 98 |
| All local timestamps start at zero | true |
| All local start poses near zero | true |
| Local metadata supports inter-scene connection | false |

Dedicated UPPAAL boundary negative-control도 수행했다.

실행:

```bash
python projects/03-sequential-coc-verification/experiments/uppaal/run_boundary_negative_control.py \
  --output artifacts/results/public/workshop-boost/boundary-negative-control-result.json
```

결과:

| Variant | Verdict | Interpretation |
|---|---|---|
| `correct_discard` | all queries pass | unverified boundary에서 obligation discard |
| `buggy_carryover` | expected failure | cross-boundary completion 및 carry-over 검출 |

`buggy_carryover`는 다음 query를 기대대로 위반했다.

- `E<> Monitor.Discarded`
- `A[] not cross_boundary_completion`
- `A[] not boundary_carryover`

따라서 scene 연결 근거가 없는 경우 pending obligation을 닫거나 discard해야 한다는 정책은 단순 설명이 아니라 검사 가능한 formal property가 되었다.

### 4.5 Trainval metadata mirror audit

사용한 metadata는 official nuScenes trainval 직접 다운로드가 아니라 local symlink로 보관된 nuScenes 호환 trainval metadata mirror이다.

| Metric | Value |
|---|---:|
| Scenes in mirror | 850 |
| Samples in mirror | 200,644 |
| Logs | 68 |
| Adjacent same-log scene pairs | 782 |
| Gap <= 1 s pairs | 391 |
| Local CoC-overlapping strict pairs | 384 |
| Strict pairs with local reasoning and egomotion | 16 |
| Derived chains | 13 |

Chain length:

| Chain length | Count |
|---|---:|
| 2 scenes | 11 |
| 3 scenes | 1 |
| 4 scenes | 1 |

이 결과는 inter-scene 검증 가능성을 보이는 pilot evidence이다. official full trainval archive로 직접 재검증한 것은 아니므로 dataset-level 일반화 주장은 피해야 한다.

### 4.6 Multi-scene loop verification

대표 chain:

`scene-0130 -> scene-0131 -> scene-0132 -> scene-0133`

| Item | Value |
|---|---:|
| Event horizon | 72.301 s |
| Event count | 16 |
| Scene boundaries | 3 |
| Slow requests | 9 |
| Acceleration requests | 1 |
| Slow response witnesses | 3 |
| Deadline | 3 s |
| Max boundary gap | 1 s |

Query 결과:

| Query | Result |
|---|---|
| `E<> Source.Done` | true |
| `E<> MonitorProc.Responded` | false |
| `A[] not deadline_miss` | false |
| `A[] not contradiction` | true |
| `A[] not boundary_violation` | true |
| `A[] not deadlock` | true |

해석:

해당 chain은 boundary gap 기준으로는 연결 가능하고 deadlock도 없지만, 3초 deadline property는 실패한다. 즉 continuity audit은 “붙일 수 있는가”를 답하고, timed observer model checking은 “붙인 뒤 판단-반응 계약이 유지되는가”를 답한다.

### 4.7 Multi-scene pattern analysis

| Metric | Value |
|---|---:|
| Chains | 13 |
| Pass chains | 4 |
| Fail chains | 9 |
| Boundary failures | 0 |
| Deadline failures | 8 |
| Responded failures | 7 |

핵심 관찰:

- 13개 chain 모두 boundary property는 통과했다.
- 그러나 8개 chain은 3초 deadline property에서 실패했다.
- PASS와 FAIL chain은 lead vehicle, intersection, speed bump 같은 표면 단어를 공유하므로 keyword heuristic만으로는 충분하지 않다.

### 4.8 Script checker baseline

동일한 multi-scene loop item에 대해 timestamp script baseline을 실행했다.

| Metric | Value |
|---|---:|
| Compared loop-batch items | 13 |
| Comparable verdicts matching UPPAAL | 13 |
| Non-matching items | 0 |

해석:

UPPAAL terminal-miss semantics를 동일하게 구현하면 deterministic trace의 일부 Boolean verdict는 script로도 재현된다. 따라서 논문에서 “UPPAAL이 아니면 불가능하다”고 주장하면 안 된다. UPPAAL의 기여는 수치 계산 자체가 아니라 timed observer composition, deadlock query, mutation oracle, 반복 의미론, boundary policy를 하나의 formal artifact로 묶는 데 있다.

### 4.9 Camera/video spot-check

5개 high-priority candidate에 대해 contact-sheet 기반 visual triage를 정리했다. 이는 독립 human gold label이 아니다.

| Event | Triage |
|---|---|
| `scene-0019@10600000` | likely repeated or stale CoC after prior yield |
| `scene-0028@6500000` | anticipatory or delayed response candidate |
| `scene-0042@6500000` | delayed response or anticipatory label candidate |
| `scene-0065@13200000` | semantic grounding and response review |
| `scene-0074@3400000` | action-trajectory mismatch candidate |

해석:

Checker가 만든 후보가 완전히 무의미한 noise가 아니라 영상 문맥 검토가 필요한 후보로 이어짐을 보인다. 그러나 독립 human review가 아니므로 safety status는 `UNKNOWN`으로 유지해야 한다.

### 4.10 Official nuScenes mini sanity check

Official mini metadata는 schema-level sanity check로 사용했다.

| Item | Value |
|---|---:|
| Scenes | 10 |
| Samples | 404 |
| Sample data | 31,206 |
| Ego poses | 31,206 |
| Logs | 8 |

해석:

Official mini는 scene, sample, sample_data, ego_pose, log table을 포함하므로 continuity schema 확인에는 충분하다. 그러나 mini는 부분집합이므로 trainval candidate chain을 검증할 수 없다.

## 5. 현재까지 강하게 주장할 수 있는 것

현재 결과로 강하게 주장할 수 있는 것은 다음이다.

1. CoC reasoning event를 timed obligation으로 변환하고 ego-motion response witness와 매칭하는 절차를 실제 94개 scene batch에 적용했다.
2. 282개 UPPAAL model과 1,128개 query evaluation에서 mutation oracle이 모두 기대 verdict와 일치했다.
3. Repeated reasoning event의 semantics가 deadline verdict를 바꿀 수 있음을 단일 scene 및 focused candidate 분석에서 확인했다.
4. Detector sensitivity를 사용해 weak positive, threshold-sensitive review, high-priority review candidate를 구분했다.
5. CoC-Nusc 단독 데이터에서는 scene continuity evidence가 없으므로 scene boundary를 넘는 obligation carry-over를 금지해야 한다.
6. Dedicated boundary negative-control은 잘못된 carry-over가 query violation으로 검출됨을 보였다.
7. Metadata mirror 기반 connected-scene pilot에서는 boundary property와 deadline property가 분리됨을 확인했다.
8. Script baseline 비교를 통해 UPPAAL의 역할을 과장하지 않고 formal artifact와 observer composition으로 정확히 한정했다.

## 6. 아직 주장하면 안 되는 것

다음 주장은 현재 결과로는 할 수 없다.

1. 물리적으로 안전한 제어를 증명했다.
2. 충돌 회피, TTC, 안전거리, 차량 동역학상 실행 가능성을 보장했다.
3. Ego speed response witness가 brake/throttle/steering actuator command와 동일하다.
4. CoC-Nusc의 모든 scene이 실제 연속 장기 episode이다.
5. Metadata mirror 기반 chain이 official trainval archive로 byte-level 검증되었다.
6. Contact-sheet triage가 독립 human gold review이다.
7. Audit 결과를 사용하면 실제 E2E/VLA policy 학습 성능이 향상된다.

## 7. 남은 보강 과제

남은 항목은 `remaining-experiments-feasibility.json`에 근거와 함께 정리되어 있다.

| Remaining item | Current status | Why not complete |
|---|---|---|
| Official full trainval validation | Not completed | official full trainval archive가 로컬에 없음 |
| Independent human visual review | Not completed | 현재는 contact-sheet triage이며 human gold가 아님 |
| Raw actuator/CAN validation | Not completed | brake/throttle/steering/CAN trace 없음 |
| Object/hazard continuity | Not completed for trainval chains | trainval mirror에 `sample_annotation`/`instance` 없음 |
| Learning-use ablation | Not completed | downstream training pipeline 없음 |

## 8. 원고 반영 상태

현재 본문에는 다음 내용이 반영되어 있다.

- 실험 설계: local negative-control, boundary negative-control, metadata mirror audit, connected chain pilot, script baseline
- 실험 결과: detector sensitivity, UPPAAL cohort, boundary negative-control, scene continuity 결과, script baseline 결과
- 논의: script와 UPPAAL의 역할 구분, 대규모 scenario collection 확장, claim boundary
- 한계: official mini와 metadata mirror 구분, official full trainval 미검증, object/hazard continuity와 actuator signal 부재
- 결론: 5개 high-priority candidate, 282개 model, 1,128개 query, boundary negative-control, 13개 chain pilot 결과

현재 PDF는 15쪽이며, 빌드 결과 LaTeX error, overfull, undefined reference는 없다.
