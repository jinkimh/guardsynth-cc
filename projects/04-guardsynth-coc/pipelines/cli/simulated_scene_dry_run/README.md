# GuardSynth simulated-scene dry run

이 파이프라인은 제한된 실제 장면의 8개 source-linked field를 별도 가상 차량의 종방향
모델에 투영해 `GuardSynth → EBLC → Core → Z3`를 실행한다. 실제 recorded rig의 누락된
vehicle assurance를 채우거나 9/9 source-complete로 바꾸지 않는다.

```bash
python3 -m cli.pipelines.guardsynth.simulated_scene_dry_run.run \
  --output-dir artifacts/results/restricted/guardsynth-simulated-scene-dry-run-001/<run-id>
```

24장면 후보의 실제/파생 근거 보유 상태는 다음 명령으로 중복 제거·비식별 집계한다.

```bash
python3 -m cli.pipelines.guardsynth.simulated_scene_dry_run.audit_candidates \
  --output-dir artifacts/results/restricted/guardsynth-sim24-candidate-audit-001/<run-id>
```

이미 존재하는 derived adapter event에 source bundle과 geometric association을 연결해 8개
scene field를 닫을 때는 다음 명령을 사용한다.

```bash
python3 -m cli.pipelines.guardsynth.simulated_scene_dry_run.prepare_event \
  --scene-ref episode-XX-event-YY \
  --adapter-result artifacts/results/restricted/.../ADAPTER_RESULT.json \
  --adapter-candidate-index N \
  --source-bundle artifacts/results/restricted/.../SCENE_SOURCE_BUNDLE.json \
  --association artifacts/results/restricted/.../ASSOCIATION_EVIDENCE.json \
  --output-dir artifacts/results/restricted/guardsynth-simulated-scene-evidence-001/<run-id>
```

활성 predicate는 충돌 예측이 아니라 source-linked pedestrian track의 oriented box와 ego
corridor의 기하학적 겹침이다. Alpamayo CoC는 `CLAIMED` provenance로만 유지한다. 공식
규칙은 별도의 조건부 applicability provenance로 보존하며 가상 제동 수치의 출처로
사용하지 않는다.
