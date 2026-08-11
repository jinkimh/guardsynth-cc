# GuardSynth scene-evidence review

M13 실제 장면 후보의 target–zone association, coordinate transform, rule applicability와
vehicle assurance를 검토하는 self-contained HTML이다.

직접 사용:

```text
SCENE_EVIDENCE_REVIEW.html을 로컬 브라우저로 연다.
```

재현 가능한 공개 패키지 생성:

```bash
/usr/bin/python3 cli/pipelines/guardsynth/scene_evidence_review/run.py \
  --run-id <new-run-id>
```

로컬에서 선택한 이미지는 브라우저 메모리에서만 표시되고 CSV/JSON에 포함되지 않는다.
restricted scene ID가 들어간 export는 공개 폴더에 저장하지 않는다.

브라우저에서는 `여러 이미지 한 번에 선택` 또는 `이미지 폴더 한 번에 선택`을 사용하면
파일마다 검토 카드가 자동으로 생성된다.

이미지를 HTML 하나에 미리 내장해야 한다면 제한 결과 전용 builder를 사용한다.

```bash
/usr/bin/python3 cli/pipelines/guardsynth/scene_evidence_review/build_embedded.py \
  --image-dir <restricted-image-directory> \
  --output-dir artifacts/results/restricted/guardsynth-scene-evidence-review-001/<new-run-id> \
  --source-ref <internal-derived-source-ref>
```

이미지 bytes가 들어간 HTML은 `artifacts/results/restricted/` 밖으로 출력할 수 없도록
builder가 거부한다.

## 이미지밖에 없는 검토

검토자가 이미지/contact sheet만 갖고 있다면 evidence-audit 양식을 사용하지 않는다.
`image-only` 모드는 이미지로 판단 가능한 장면 종류, 시각적 위험, 충돌 영역, 가림,
신호와 프레임 변화만 묻는다. target/track ID, timestamp, geometry, frame, transform과
assurance는 자동으로 `NOT_AVAILABLE_FROM_IMAGE`이며 결과는 항상 계약 생성 전
`REVIEW_REQUIRED`다.

```bash
/usr/bin/python3 cli/pipelines/guardsynth/scene_evidence_review/build_embedded.py \
  --review-mode image-only \
  --image-dir <restricted-image-directory> \
  --output-dir artifacts/results/restricted/guardsynth-image-only-scene-review-001/<new-run-id> \
  --source-ref <internal-derived-source-ref>
```
