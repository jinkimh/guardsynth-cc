# GuardSynth 24-scene dry-run readiness

세 slice별 8개, 총 24개 실장면 slot과 필요한 source-complete 입력을 고정하고 현재 공개
비식별 readiness 집계에 대해 실행 가능 여부를 fail-closed 판정한다.

```bash
/usr/bin/python3 projects/04-guardsynth-coc/pipelines/cli/twenty_four_scene_readiness/run.py \
  --run-id kr-dry-run-readiness-2026-08-10-v1
```

실제 scene field가 없으면 EBLC/Z3 scene run을 만들지 않고 data-gap을 출력한다.

