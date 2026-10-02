# Expert pilot preflight

M13 source-complete 장면 집계를 60-scene M16 quota와 비교한다.

```bash
python3 -m cli.pipelines.guardsynth.expert_pilot_preflight.run \
  --output-dir artifacts/results/restricted/guardsynth-expert-pilot-preflight-001/<run-id>
```

부족한 장면은 합성하지 않으며 start gate 미통과 시 annotation을 시작하지 않는다.

`expert_annotation_workbench.html`은 synthetic diagram과 두 interface mode를 포함한
훈련용 self-contained UI다. 현재 banner가 표시하는 대로 실제 60-scene annotation에는
사용하지 않는다. 출력 JSON은 `expert_annotation.schema.json`과 Python semantic validator로
검사한다.

preflight artifact에는 blinded assignment, annotation, agreement/timing metrics와 power
planning의 JSON 계약도 함께 복사된다. slice×outcome joint cell을 3~4개로 배분한 60-slot
manifest가 slice 20개와 outcome 10개 주변 합계를 동시에 고정한다. power record는 관측된
paired effect와 variance의 source ref가 모두 있을 때만 만들 수 있으며, 현재 preflight는
데이터를 대신 생성하지 않는다.
