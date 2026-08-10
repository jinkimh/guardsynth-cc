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
