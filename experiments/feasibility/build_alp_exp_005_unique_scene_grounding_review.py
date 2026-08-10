#!/usr/bin/env python3
"""Build the primary grounding review with one fixed-seed run per unique scene."""

from __future__ import annotations

import json
import random
from pathlib import Path

from build_alp_exp_005_grounding_labeler import build_page


ROOT = Path(__file__).resolve().parents[2]
BATCH_ROOT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0"
)
OLD_REVIEW_ROOT = BATCH_ROOT / "blind-review-v0"
OUTPUT_ROOT = BATCH_ROOT / "unique-scene-grounding-v1"
SEED = 42
RANDOMIZATION_SEED = 20260803


def main() -> int:
    candidates = []
    for episode_index in range(10):
        episode = f"episode-{episode_index:02d}"
        run_root = BATCH_ROOT / episode / f"seed-{SEED}"
        manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("status") != "EXECUTED":
            raise ValueError(f"Missing executed run for {episode} seed {SEED}")
        candidates.append(
            {
                "episode": episode,
                "seed": SEED,
                "coc": (run_root / "generated_coc.txt").read_text(encoding="utf-8").strip(),
                "scene": OLD_REVIEW_ROOT / "scene-inputs" / f"{episode}-model-input.jpg",
            }
        )

    random.Random(RANDOMIZATION_SEED).shuffle(candidates)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    OUTPUT_ROOT.chmod(0o700)
    adjudication = OUTPUT_ROOT / "adjudication-only"
    adjudication.mkdir(parents=True, exist_ok=True, mode=0o700)
    adjudication.chmod(0o700)

    items = []
    mapping = []
    import base64

    for index, candidate in enumerate(candidates, start=1):
        review_id = f"UGR-{index:03d}"
        scene_data = base64.b64encode(candidate["scene"].read_bytes()).decode("ascii")
        items.append(
            {
                "review_id": review_id,
                "coc": candidate["coc"],
                "scene": f"data:image/jpeg;base64,{scene_data}",
            }
        )
        mapping.append(
            {
                "review_id": review_id,
                "episode": candidate["episode"],
                "seed": candidate["seed"],
            }
        )

    for reviewer in ("A", "B"):
        output = OUTPUT_ROOT / f"GROUNDING_APP_{reviewer}_UNIQUE_SCENES.html"
        output.write_text(build_page(reviewer, items), encoding="utf-8")
        output.chmod(0o600)
        print(f"wrote {output.relative_to(ROOT)} ({output.stat().st_size:,} bytes)")

    mapping_path = adjudication / "blind-mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mapping_path.chmod(0o600)
    manifest = {
        "experiment_id": "ALP-EXP-005-UNIQUE-SCENE-GROUNDING-V1",
        "review_unit": "unique_scene_fixed_seed",
        "unique_scene_count": len(items),
        "runs_per_scene": 1,
        "fixed_seed": SEED,
        "randomization_seed": RANDOMIZATION_SEED,
        "primary_use": "scene grounding feasibility",
        "excluded_use": "multi-seed stability; evaluate separately",
        "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
    }
    manifest_path = OUTPUT_ROOT / "packet-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)
    print(f"primary review contains {len(items)} unique scenes and zero repeated scene slots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
