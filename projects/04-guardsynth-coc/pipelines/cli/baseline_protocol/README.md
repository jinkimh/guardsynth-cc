# GuardSynth baseline protocol

B0–B8/B13을 M14의 24-case locked software matrix에서 공통 schema로 실행한다.

```bash
python3 -m cli.pipelines.guardsynth.baseline_protocol.run \
  --output-dir artifacts/results/public/guardsynth-baseline-protocol-001/<run-id>
```

외부 model provider나 reachability 입력이 없으면 해당 baseline은 `UNSUPPORTED`를 반환한다.
이 smoke run은 성능 순위나 실제 장면 효과 평가가 아니다.
