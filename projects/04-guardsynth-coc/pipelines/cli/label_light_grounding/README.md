# GuardSynth label-light grounding

기존 detector, tracker, map/trajectory 출력에서 target–conflict-zone 후보를
만들고 다음 세 경로로 분류한다.

1. 승인된 calibration과 유일한 고신뢰 후보: 자동 확인
2. 저신뢰·다중 후보·정책상 자동화 금지: 최소 사람 확인
3. geometry·transform·근거 부족 또는 충돌: 계약을 만들지 않고 중단

이 파이프라인은 새로운 detector를 학습하거나 confidence를 사실로 취급하지
않는다. 공개 fixture는 전부 synthetic이고, 제한 입력은 식별자 없는 집계값만
공개 결과에 포함한다.

```bash
python3 -m cli.pipelines.guardsynth.label_light_grounding.run --run-id <new-run-id>
```

## Image-only 검토를 partial scene packet으로 변환

완료된 restricted image-only 설문은 source-complete grounding packet으로 직접 변환하지
않는다. 다음 변환기는 사람의 이미지 판단만 보존하고 M13 필수 입력 9종을 missing으로
기록하며 계약 생성을 금지한다.

```bash
python3 projects/04-guardsynth-coc/pipelines/cli/label_light_grounding/convert_image_review.py \
  --input artifacts/results/restricted/<review-run>/guardsynth_image_only_review.json \
  --output-dir artifacts/results/restricted/<partial-packet-run>
```

입력과 출력은 모두 `artifacts/results/restricted/` 아래에 있어야 한다. 결과에는 이미지
bytes를 넣지 않으며 timestamp, target/zone ID, geometry, transform 또는 vehicle assurance를
임의 생성하지 않는다. `CALIBRATION_AUDIT_QUEUE.json`은 기존 판정을 넣지 않고 판정 유형별
한 건을 결정적으로 선택하므로, 별도 검토자가 독립적으로 재검토할 때 사용한다.

첫 calibration 항목의 기존 제한 파생 근거를 content hash로 감사하려면 다음을 실행한다.

```bash
python3 projects/04-guardsynth-coc/pipelines/cli/label_light_grounding/audit_calibration_scene.py \
  --packets artifacts/results/restricted/<partial-run>/PARTIAL_SCENE_PACKETS.json \
  --embedded-manifest artifacts/results/restricted/<review-run>/EMBEDDED_REVIEW_MANIFEST.json \
  --adapter-result artifacts/results/restricted/<adapter-run>/ADAPTER_RESULT.json \
  --source-root artifacts/results/restricted/<derived-source-root> \
  --output-dir artifacts/results/restricted/<source-audit-run>
```

10개 중 실제 source-linked field 수가 가장 많은 장면을 고른다. 동일 이미지가 SHA-256으로
유일하게 연결되고 sidecar/adapter 구조가 검증될 때만 timestamp, ego state, geometry를
source-linked로 인정한다. 나머지는 `SOURCE_ACQUISITION_WORK_ORDER.json`에서 열린 상태로
유지되며, 모두 닫힐 때까지 계약 실행은 금지된다.

기존 obstacle 파생물이 `candidate_count`만 남기고 nearest 후보만 저장한 경우
`ACTOR_ASSOCIATION_BLOCKER.json`을 만들고 검토 UI를 생성하지 않는다. 원 obstacle archive가
로컬에서 사용 가능해지면 `projects/03-sequential-coc-verification/experiments/feasibility/analyze_nvidia_obstacle_feasibility.py`를
실행해 별도 `obstacle-feasibility-v2-all-candidates.json`을 만든다. v2는 모든 corridor 후보와
시간순 track sample을 보존하고, adapter는 raw track ID 대신 SHA-256 식별자를 전달한다.

선택 장면의 실제 egomotion, sensor extrinsics, vehicle dimensions와 collection metadata가
사용 가능하면 다음 extractor로 source bundle을 만든다. 출력은 restricted 아래에만 두며
raw clip ID 대신 SHA-256을 기록한다.

```bash
python3 projects/03-sequential-coc-verification/experiments/feasibility/extract_nvidia_scene_source_bundle.py \
  --root data/restricted/nvidia_physicalai \
  --cohort data/restricted/nvidia_physicalai/internal-derived/cohort-10/cohort-conformance.json \
  --obstacles data/restricted/nvidia_physicalai/internal-derived/cohort-10/obstacle-feasibility-v2-all-candidates.json \
  --episode-index <index> --event-index <index> \
  --manifest artifacts/results/restricted/<episode-run>/manifest.json \
  --scene-ref <scene-ref> \
  --output artifacts/results/restricted/<source-bundle-run>/SCENE_SOURCE_BUNDLE.json
```

이 bundle을 `audit_calibration_scene.py --scene-source-bundle <path>`에 전달하면 수치적 역변환
closure와 근거를 확인한 뒤 coordinate transform 및 clip-specific rig configuration binding만
source-linked로 인정한다. 이 binding은 VIN 또는 vehicle assurance profile을 대신하지 않는다.

전체 actor track이 준비된 장면은 다음 명령으로 기하학적 set association을 만든다.

```bash
python3 projects/04-guardsynth-coc/pipelines/cli/label_light_grounding/build_geometric_association.py \
  --obstacles data/restricted/<all-candidates.json> \
  --adapter-result artifacts/results/restricted/<adapter-run>/ADAPTER_RESULT.json \
  --scene-ref <scene-ref> --episode-index <n> --event-index <n> \
  --adapter-candidate-index <n> \
  --output-dir artifacts/results/restricted/<association-run>
```

이 단계는 가장 가까운 actor 하나를 고르지 않는다. source-linked oriented box가 ego corridor와
겹치는 모든 track의 `SET`을 만들고 검토용 평면도를 함께 저장한다. 결과를
`audit_calibration_scene.py --association-evidence <ASSOCIATION_EVIDENCE.json>`로 전달할 수 있다.
이는 geometric association이며 CoC referent, 횡단보도, 충돌 예측 또는 안전 판정이 아니다.

공식 규칙 원문과 장면 조건을 연결할 때는 다음 builder를 사용한다. 위치가 데이터셋 GPS로
확인되지 않은 경우 `INFERRED_HIGH_CONFIDENCE_NOT_DATASET_GPS`를 보존하며, CoC를 법적 authority나
관측 사실로 사용하지 않는다.

```bash
python3 projects/04-guardsynth-coc/pipelines/cli/label_light_grounding/build_rule_applicability.py \
  --packets artifacts/results/restricted/<partial-run>/PARTIAL_SCENE_PACKETS.json \
  --association-evidence artifacts/results/restricted/<association-run>/ASSOCIATION_EVIDENCE.json \
  --source-audit artifacts/results/restricted/<audit-run>/CALIBRATION_SOURCE_AUDIT.json \
  --ca-21950-snapshot <downloaded-official-21950.html> \
  --ca-21954-snapshot <downloaded-official-21954.html> \
  --sfmta-route-snapshot <downloaded-official-route.html> \
  --sfcta-report-snapshot <downloaded-official-report.pdf> \
  --scene-ref <scene-ref> --dataset-country 'United States' \
  --output-dir artifacts/results/restricted/<rule-applicability-run>
```

출력은 공식 URL과 snapshot SHA-256, 사람 검토 조건, association 및 위치 추론의 한계를 함께
기록한다. 이를 source audit의 `--rule-applicability-evidence`로 전달할 수 있다. 규칙 연결만으로
차량 assurance profile이나 수치 제동 한계를 만들지 않는다.

마지막 vehicle assurance field는 다음 감사기로 확인한다. 관측 egomotion, CoC 응답시간,
플랫폼/API 문서를 차량별 제동 보장으로 승격하지 않고, 동일 binding의 OEM/control-stack 검증
profile만 허용한다.

```bash
python3 projects/04-guardsynth-coc/pipelines/cli/label_light_grounding/audit_vehicle_assurance.py \
  --scene-source-bundle artifacts/results/restricted/<bundle-run>/SCENE_SOURCE_BUNDLE.json \
  --cohort-conformance data/restricted/<cohort-conformance.json> \
  --experiment-report data/restricted/<experiment-report.md> \
  --dataset-card-snapshot <official-dataset-card.html> \
  --drive-agx-snapshot <official-drive-agx.html> \
  --vehicleio-workflow-snapshot <official-vehicleio-workflow.html> \
  --vehicleio-actuators-snapshot <official-vehicleio-actuators.html> \
  --output-dir artifacts/results/restricted/<assurance-audit-run>
```

통과하려면 vehicle/DBW identity와 정확히 일치하는 감속·command-to-deceleration latency·jerk,
운용조건, 불확실성 및 검증 source가 모두 필요하다. 일부라도 없으면 `REVIEW_REQUIRED`이며
실제 장면 계약 생성을 허용하지 않는다.
