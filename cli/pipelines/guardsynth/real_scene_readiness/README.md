# GuardSynth real-scene readiness

기존 restricted derived-scene adapter 결과와 source-bearing vehicle
assurance registry를 결합해 24-slot 준비도를 fail-closed 방식으로 점검한다.
입력이 없는 slot을 synthetic scene으로 채우지 않으며, raw identifier나 CoC
본문을 결과에 포함하지 않는다.

```bash
python3 -m cli.pipelines.guardsynth.real_scene_readiness.run --run-id <new-run-id>
```

이 파이프라인의 `DATA_GAP_PIVOT`은 실행 실패가 아니다. 24개의 실제 장면
계약 검증을 시작하기 위한 grounded input이 부족하다는 종료 판정이다.
