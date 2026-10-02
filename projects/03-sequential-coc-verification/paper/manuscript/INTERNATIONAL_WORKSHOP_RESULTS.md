# 국제 워크숍 보강 실험 결과

대상 계획: `INTERNATIONAL_WORKSHOP_PLAN.md`

실험 산출물 위치: `artifacts/results/public/workshop-boost/`

본 문서는 국제 워크숍 투고 수준으로 논문을 보강하기 위해 추가로 실행하거나 재정리한 실험 결과를 요약한다. 핵심 결론은 다음과 같다. 현재 결과는 물리적 안전성 증명이 아니라 reasoning-augmented driving annotation을 학습 데이터로 사용하기 전에 수행하는 protocol-level consistency audit의 실효성을 보인다.

## 1. 실행 요약

| Experiment | Status | Output |
|---|---|---|
| Local scene negative-control audit | Done | `local-scene-continuity-negative-control.json` |
| Dedicated UPPAAL boundary-carryover negative control | Done | `boundary-negative-control-result.json` |
| Trainval metadata mirror continuity audit | Done | `workshop-experiment-results.json` |
| Weak kinematic cohort rerun | Done | `weak-kinematic-chunk0.json` |
| UPPAAL cohort verification rerun | Done | `uppaal-cohort-verification-result.json` |
| Detector sensitivity aggregation | Done | `workshop-experiment-results.json` |
| Multi-scene loop verification | Done | `uppaal-loop-verification-result.json` |
| Multi-scene pattern analysis | Done | `uppaal-loop-pattern-analysis.json` |
| Script checker baseline comparison | Done | `workshop-experiment-results.json` |
| Video spot-check summary | Done as contact-sheet triage, not human gold | `video-review-result.json` |
| Official nuScenes full trainval validation | Not done | official full trainval download is not locally available |

## 2. Experiment A: Local Scene Negative-Control

목적은 CoC-Nusc 단독 공개 데이터만 사용했을 때 scene 간 연결을 근거 없이 허용하지 않는지 확인하는 것이다.

실행:

```bash
python projects/03-sequential-coc-verification/experiments/feasibility/audit_scene_continuity.py \
  --output artifacts/results/public/workshop-boost/local-scene-continuity-negative-control.json
```

결과:

| Item | Result |
|---|---|
| CoC-Nusc egomotion files | 98 |
| All local timestamps start at zero | true |
| All local start poses near zero | true |
| Local metadata supports inter-scene connection | false |
| Safe policy | treat scenes as independent episodes unless continuity metadata is provided |

해석:

CoC-Nusc의 local egomotion은 scene마다 timestamp와 pose가 초기화된다. 따라서 CoC-Nusc 단독 데이터에서는 `scene-0027` 다음에 `scene-0028`이 온다는 식의 장기 episode 연결을 주장할 수 없다. 이 실험은 negative-control로 사용된다. 올바른 데이터 gate는 scene boundary에서 pending obligation을 다음 scene으로 넘기지 않아야 하며, 연결 근거가 없으면 각 scene을 독립 clip/window 학습 샘플로만 사용해야 한다.

## 3. Experiment B: Dedicated Boundary-Carryover Negative Control

목적은 검증되지 않은 scene boundary에서 열린 obligation이 다음 scene의 response witness로 부당하게 완료되는지 확인하는 것이다. 이 실험은 CoC-Nusc 단독 데이터에서 모든 scene을 독립 episode로 닫아야 한다는 정책을 실제 UPPAAL mutation oracle로 확인한다.

실행:

```bash
python projects/03-sequential-coc-verification/experiments/uppaal/run_boundary_negative_control.py \
  --output artifacts/results/public/workshop-boost/boundary-negative-control-result.json
```

Negative-control timeline:

| Event | Time |
|---|---:|
| trusted request in scene A | 0 ms |
| unverified scene boundary | 1000 ms |
| response witness in scene B | 1500 ms |
| deadline | 3000 ms |

결과:

| Variant | `E<> Source.Done` | `E<> Monitor.Discarded` | `A[] not cross_boundary_completion` | `A[] not boundary_carryover` | Overall |
|---|---|---|---|---|---|
| `correct_discard` | true | true | true | true | PASS |
| `buggy_carryover` | true | false | false | false | expected failure |

해석:

올바른 모델은 unverified boundary에서 active obligation을 `Discarded` 상태로 닫고, 다음 scene의 response witness가 이전 obligation을 완료하지 못하게 한다. 반대로 buggy mutation은 obligation을 boundary 너머로 carry-over하여 다음 scene의 response로 완료하므로 `cross_boundary_completion`과 `boundary_carryover` query를 위반한다. 두 variant 모두 oracle이 기대 verdict와 일치했다. 따라서 scene 연결 근거가 없는 경우 pending obligation을 닫거나 discard해야 한다는 정책이 단순 설명이 아니라 검사 가능한 formal property가 되었다.

## 4. Experiment C: Trainval Metadata Mirror Continuity Audit

목적은 nuScenes 호환 trainval metadata mirror를 사용했을 때 실제로 연결 가능한 scene 후보가 어느 정도 나오는지 확인하는 것이다.

사용한 metadata:

- `data/baseline/nuscenes_metadata/interp_12Hz_trainval/scene.json`
- `sample.json`
- `log.json`
- `ego_pose.json`
- 출처 표기: local symlinked `flymin/MagicDriveDiT-nuScenes-metadata` mirror
- 주의: official nuScenes trainval 직접 다운로드가 아니라 metadata mirror이다.

결과:

| Metric | Value |
|---|---:|
| Scenes in mirror | 850 |
| Samples in mirror | 200,644 |
| Logs | 68 |
| Adjacent same-log scene pairs | 782 |
| Adjacent pairs with gap <= 1 s | 391 |
| Local CoC-overlapping strict pairs | 384 |
| Strict pairs with local reasoning and egomotion | 16 |
| Derived chains | 13 |

Chain length:

| Chain length | Count |
|---|---:|
| 2 scenes | 11 |
| 3 scenes | 1 |
| 4 scenes | 1 |

Longest available local chains:

| Chain | Length |
|---|---:|
| `scene-0130 -> scene-0131 -> scene-0132 -> scene-0133` | 4 |
| `scene-0007 -> scene-0008 -> scene-0009` | 3 |
| `scene-0025 -> scene-0026` | 2 |
| `scene-0027 -> scene-0028` | 2 |
| `scene-0031 -> scene-0032` | 2 |
| `scene-0048 -> scene-0049` | 2 |
| `scene-0051 -> scene-0052` | 2 |
| `scene-0056 -> scene-0057` | 2 |
| `scene-0063 -> scene-0064` | 2 |
| `scene-0124 -> scene-0125` | 2 |

해석:

metadata mirror를 사용하면 scene 간 시간 연속성 후보를 찾을 수 있다. 그러나 이 결과는 official full trainval metadata로 직접 재확인된 것은 아니다. 따라서 논문에서는 “official mini는 schema-level evidence, trainval mirror는 pilot-level continuity evidence”로 구분해서 서술해야 한다.

## 5. Experiment D: Weak Kinematic Cohort Audit

목적은 reasoning event를 timed obligation으로 변환하고, ego speed/trajectory 기반 약한 response witness와 매칭하는 절차가 94개 scene 규모에서 동작하는지 확인하는 것이다.

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
| Contract fail | 5 |
| Camera available scenes | 11 |

해석:

5개 fail은 unsafe control의 증거가 아니라, 3초 후보 deadline과 ego-speed witness 기준에서 response 확인이 불충분한 review candidate이다. 즉 이 실험의 산출물은 “위험 장면 판정”이 아니라 “검토 우선순위화”이다.

## 6. Experiment E: Detector Sensitivity

목적은 ego-speed 기반 response witness가 detector parameter에 얼마나 민감한지 정량화하는 것이다. 각 event는 27개 detector profile에 대해 평가되었다.

결과:

| Detection profiles agreeing | Event count |
|---|---:|
| 27/27 | 72 |
| 18-26/27 | 51 |
| 9-17/27 | 2 |
| 1-8/27 | 4 |
| 0/27 | 1 |

Review priority:

| Priority | Event count |
|---|---:|
| No special review flag | 72 |
| Threshold-sensitive camera review | 53 |
| Camera and raw actuator confirmation required | 5 |

해석:

단일 detector 설정에서의 fail을 곧바로 protocol violation으로 확정하면 과장이다. 대신 detector sensitivity는 다음과 같이 사용해야 한다.

- 27/27 stable pass: weak positive training candidate
- 18-26/27 pass: threshold-sensitive candidate
- 1-8/27 또는 0/27: high-priority review candidate
- fail 5건: camera 및 raw actuator 확인 필요

## 7. Experiment F: UPPAAL Cohort Verification and Mutation Oracle

목적은 생성된 UPPAAL 모델이 baseline, provenance mutation, response mutation에 대해 기대한 verdict를 내는지 확인하는 것이다.

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

이 결과는 checker가 단지 baseline trace를 통과시키는지 보는 것이 아니다. 출처를 훼손한 provenance mutation과 response witness를 훼손한 response mutation이 기대한 질의를 깨뜨리는지 확인한다. 따라서 mutation oracle은 checker 자체가 오류를 감지할 수 있는지를 보이는 sanity check로 기능한다.

## 8. Experiment G: Multi-Scene Loop Verification

목적은 연결 가능한 scene 후보를 하나의 긴 episode로 구성했을 때, scene boundary와 timed obligation을 함께 검사할 수 있는지 확인하는 것이다.

실행:

```bash
python projects/03-sequential-coc-verification/experiments/uppaal/run_multiscene_loop_verification.py \
  --output artifacts/results/public/workshop-boost/uppaal-loop-verification-result.json
```

대상 chain:

`scene-0130 -> scene-0131 -> scene-0132 -> scene-0133`

| Item | Value |
|---|---:|
| Duration | 72.301 s |
| Event count | 16 |
| Scene boundaries | 3 |
| Slow requests | 9 |
| Acceleration requests | 1 |
| Slow response witnesses | 3 |
| Deadline | 3 s |
| Max boundary gap | 1 s |

UPPAAL query 결과:

| Query | Satisfied |
|---|---|
| `E<> Source.Done` | true |
| `E<> MonitorProc.Responded` | false |
| `A[] not deadline_miss` | false |
| `A[] not contradiction` | true |
| `A[] not boundary_violation` | true |
| `A[] not deadlock` | true |

해석:

이 결과는 중요한 구분을 보여준다. 해당 chain은 boundary gap 기준으로는 연결 가능하고 deadlock도 없지만, 3초 deadline property는 실패한다. 즉 scene continuity audit은 “붙일 수 있는가”를 답하고, UPPAAL timed observer는 “붙인 뒤 판단-반응 계약이 유지되는가”를 답한다.

## 9. Experiment H: Multi-Scene Pattern Analysis

목적은 13개 strict chain 전체에서 boundary failure와 deadline failure가 어떻게 분리되는지 확인하는 것이다.

결과:

| Metric | Value |
|---|---:|
| Chains | 13 |
| Pass chains | 4 |
| Fail chains | 9 |
| Boundary failures | 0 |
| Deadline failures | 8 |
| Responded failures | 7 |

핵심 관찰:

- 13개 chain 모두 `A[] not boundary_violation`을 만족했다.
- 그러나 8개 chain은 3초 deadline property를 만족하지 않았다.
- 따라서 “연속 scene으로 묶을 수 있음”과 “긴 episode에서 판단-반응 계약이 만족됨”은 별개의 문제이다.
- PASS와 FAIL chain은 lead vehicle, intersection, speed bump 같은 표면 단어를 공유하므로 keyword heuristic만으로는 충분하지 않다.

## 10. Experiment I: Script Checker Baseline Comparison

목적은 같은 timeline을 단순 timestamp script로 검사했을 때 UPPAAL과 어떤 관계가 있는지 확인하는 것이다.

결과:

| Metric | Value |
|---|---:|
| Compared loop-batch items | 13 |
| Comparable verdicts matching UPPAAL | 13 |
| Non-matching items | 0 |

해석:

UPPAAL terminal-miss semantics를 동일하게 구현하면, deterministic trace의 일부 Boolean verdict는 timestamp script로도 재현된다. 따라서 논문에서 “UPPAAL이 아니면 불가능하다”고 주장하면 안 된다.

대신 다음과 같이 주장해야 한다.

> 단순 timestamp script는 고정 trace의 일부 verdict를 재현할 수 있다. 그러나 UPPAAL 모델은 CoCSource, EgoTrace, ObligationManager, ReactionObserver, DecisionValidator를 동기화된 timed observer network로 명시하며, deadlock query, mutation oracle, 반복 의미론 변경, boundary policy를 동일한 formal artifact 안에서 다룰 수 있다.

이 결과는 오히려 논문을 더 정직하게 만든다. 즉 UPPAAL은 숫자 계산을 대신하는 도구가 아니라, 계산 가능한 검사 절차를 명세 수준에서 재현 가능하게 만드는 도구로 위치시켜야 한다.

## 11. Experiment J: Video Spot-Check Summary

목적은 high-priority fail candidate가 실제 영상 문맥과 어떻게 연결되는지 확인하는 것이다. 기존 contact-sheet 기반 triage 결과를 워크숍 실험 결과로 정리하였다.

초기 fail 후보 8개 중 3개는 STOP/YIELD event가 이미 near-zero speed 상태였기 때문에 “추가 감속 없음”을 fail로 본 false positive였다. 이를 반영하여 contract를 수정했고, 최종 후보는 5개로 줄었다.

Resolved false positives:

| Event | Reason |
|---|---|
| `scene-0046@10000000` | STOP/YIELD near-zero speed case |
| `scene-0159@4500000` | STOP/YIELD near-zero speed case |
| `scene-0159@4900000` | STOP/YIELD near-zero speed case |

Remaining candidates:

| Event | Visual grounding | Triage |
|---|---|---|
| `scene-0019@10600000` | pedestrian and speed bump visible | likely repeated or stale CoC after prior yield |
| `scene-0028@6500000` | partial intersection and signal visible later | anticipatory or delayed response candidate |
| `scene-0042@6500000` | lead vehicle visible | delayed response or anticipatory label candidate |
| `scene-0065@13200000` | bus visible but causal direction inconclusive | semantic grounding and response review |
| `scene-0074@3400000` | generic route context only | action-trajectory mismatch candidate |

해석:

Video spot-check는 독립 gold label이 아니다. 네 개의 sampled front-camera frame과 ego speed를 기반으로 한 triage이다. 따라서 최종 safety verdict는 모두 `UNKNOWN`으로 유지해야 한다. 그럼에도 이 결과는 checker가 만든 후보가 완전히 무의미한 noise가 아니라, 실제 영상 문맥 검토가 필요한 후보로 이어진다는 점을 보여준다.

## 12. Official Mini Sanity Check

official nuScenes mini metadata도 별도로 확인하였다.

| Item | Value |
|---|---:|
| Scenes | 10 |
| Samples | 404 |
| Sample data | 31,206 |
| Ego poses | 31,206 |
| Logs | 8 |

결론:

- official mini는 scene, sample, log, sample_data, ego_pose를 포함하므로 continuity schema를 확인하는 데 충분하다.
- local CoC scene과 10개 scene 이름이 겹친다.
- 그러나 mini는 부분집합이므로 trainval candidate chain을 검증할 수 없다.

따라서 논문에서는 official mini를 “nuScenes continuity schema 확인”에만 사용하고, trainval mirror 결과는 “pilot continuity audit”으로 분리해야 한다.

## 13. Remaining Experiment Feasibility Audit

남은 실험의 수행 가능성도 별도 JSON으로 기록했다.

Output:

`artifacts/results/public/workshop-boost/remaining-experiments-feasibility.json`

결론:

| Experiment | Status | Reason |
|---|---|---|
| Official full trainval validation | not completed | official full trainval archive is not locally available |
| Independent human visual review | not completed | current review is contact-sheet based triage, not human gold review |
| Raw actuator/CAN validation | not completed | no brake/throttle/steering/CAN trace exists locally |
| Object/hazard continuity | not completed for trainval chains | trainval mirror lacks `sample_annotation` and `instance`; official mini is only a subset |
| Learning-use ablation | not completed | no downstream policy/trajectory training pipeline is present |

이 audit은 “미완료”를 단순한 약점으로 남기지 않고, 어떤 evidence가 부족해서 어떤 주장을 할 수 없는지 명확히 분리한다.

## 14. 논문에 반영할 결론

국제 워크숍 버전에서 가장 강하게 밀 수 있는 결론은 다음 다섯 가지다.

1. Reasoning annotation은 학습 가능한 의미 신호를 제공하지만, timed obligation과 반복 의미론 없이는 response deadline 판정이 불안정하다.
2. CoC-Nusc chunk 0의 94개 scene에서 5개 high-priority review candidate를 자동 선별했고, detector sensitivity를 통해 53개 threshold-sensitive case를 추가로 구분했다.
3. UPPAAL mutation oracle은 provenance corruption과 response corruption을 기대대로 감지했으며, 282개 모델과 1,128개 query에서 oracle mismatch가 없었다.
4. Dedicated boundary negative-control은 unverified scene boundary에서 obligation carry-over가 발생하면 `cross_boundary_completion`과 `boundary_carryover` query가 실패함을 보였다.
5. Scene continuity가 확인된 pilot chain에서도 boundary property와 deadline property는 분리된다. 13개 strict chain은 boundary violation이 0개였지만, deadline failure는 8개였다.

## 15. 남은 보강 과제

국제 워크숍 제출 전 가능하면 다음을 추가하는 것이 좋다.

1. Official nuScenes full trainval metadata 직접 다운로드 후 mirror audit 결과 재확인
2. 5개 remaining candidate에 대한 독립 human visual review
3. object track 또는 hazard continuity 기반 multi-scene 연결 검증
4. raw actuator, CAN, brake/throttle signal을 사용할 수 있는 데이터셋으로 response witness 강화
5. 감사 전후 데이터로 작은 learning-use ablation 수행

현재 단계에서 논문 주장은 다음 표현이 가장 안전하고 설득력 있다.

> 본 연구는 reasoning-augmented driving annotation의 물리적 안전성을 증명하지 않는다. 대신, 자연어 판단 event가 학습 데이터로 사용되기 전에 timed obligation, response witness, provenance, 반복 의미론, scene boundary 정책과 일관되는지 검사하는 재현 가능한 formal audit 절차를 제시한다.
