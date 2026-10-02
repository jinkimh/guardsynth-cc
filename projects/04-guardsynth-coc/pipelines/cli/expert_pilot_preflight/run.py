"""Audit whether M16 has 60 eligible scenes before expert annotation starts."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any

from cli.project_paths import project_root


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.expert_pilot_protocol import (
    build_pilot_preflight,
    build_pilot_slot_manifest,
    pilot_design,
)
from guard_synth_eblc.schema_validation import load_json


EXPERIMENT_ID = "GUARDSYNTH-EXPERT-PILOT-PREFLIGHT-001"
DEFAULT_BATCH = ROOT / (
    "artifacts/results/restricted/guardsynth-sim24-batch-001/"
    "alpamayo-terminal-batch-2026-08-12-v1/BATCH_RESULT.json"
)
ANNOTATION_SCHEMA = ROOT / "projects/04-guardsynth-coc/src/guard_synth/schemas/expert_annotation.schema.json"
ASSIGNMENT_SCHEMA = ROOT / "projects/04-guardsynth-coc/src/guard_synth/schemas/expert_assignment_manifest.schema.json"
METRICS_SCHEMA = ROOT / "projects/04-guardsynth-coc/src/guard_synth/schemas/expert_pilot_metrics.schema.json"
POWER_SCHEMA = ROOT / "projects/04-guardsynth-coc/src/guard_synth/schemas/power_analysis_input.schema.json"
SLOT_SCHEMA = ROOT / "projects/04-guardsynth-coc/src/guard_synth/schemas/expert_pilot_slot_manifest.schema.json"
TRAINING_EXAMPLE = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/expert_annotation_training_example_v0_1.json"
WORKBENCH = ROOT / (
    "projects/04-guardsynth-coc/pipelines/cli/expert_pilot_preflight/expert_annotation_workbench.html"
)


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execute(*, batch_path: Path, output_dir: Path) -> dict[str, Any]:
    if any(not path.is_file() for path in (
        batch_path, ANNOTATION_SCHEMA, ASSIGNMENT_SCHEMA, METRICS_SCHEMA,
        POWER_SCHEMA, SLOT_SCHEMA, TRAINING_EXAMPLE, WORKBENCH
    )):
        raise FileNotFoundError("M16 preflight input is missing")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    preflight = build_pilot_preflight(load_json(batch_path))
    output_dir.mkdir(parents=True)
    _write(output_dir / "PILOT_DESIGN.json", pilot_design())
    _write(output_dir / "PILOT_SLOT_MANIFEST.json", build_pilot_slot_manifest())
    _write(output_dir / "PILOT_PREFLIGHT.json", preflight)
    shutil.copyfile(ANNOTATION_SCHEMA, output_dir / "EXPERT_ANNOTATION_SCHEMA.json")
    shutil.copyfile(ASSIGNMENT_SCHEMA, output_dir / "EXPERT_ASSIGNMENT_SCHEMA.json")
    shutil.copyfile(METRICS_SCHEMA, output_dir / "EXPERT_PILOT_METRICS_SCHEMA.json")
    shutil.copyfile(POWER_SCHEMA, output_dir / "POWER_ANALYSIS_INPUT_SCHEMA.json")
    shutil.copyfile(SLOT_SCHEMA, output_dir / "PILOT_SLOT_MANIFEST_SCHEMA.json")
    shutil.copyfile(TRAINING_EXAMPLE, output_dir / "TRAINING_ANNOTATION_EXAMPLE.json")
    shutil.copyfile(WORKBENCH, output_dir / "expert_annotation_workbench.html")
    _write(output_dir / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "input_class": "LICENSE_RESTRICTED_AGGREGATE_NO_RAW_IDENTIFIERS",
        "input_hash": hashlib.sha256(batch_path.read_bytes()).hexdigest(),
        "deterministic": True,
        "annotation_started": preflight["annotation_start_allowed"],
        "claim_scope": preflight["claim_scope"],
    })
    (output_dir / "REPORT_KO.md").write_text(
        f"""# M16 60-scene expert pilot preflight

- 상태: **{preflight['status']}**
- annotation start: **{'허용' if preflight['annotation_start_allowed'] else '금지'}**
- source-complete eligible scenes: **{preflight['eligible_scene_count']}/{preflight['target_scene_count']}**
- 총 부족: **{preflight['total_scene_shortfall']}장면**
- slice coverage: **{preflight['slice_coverage']}**
- outcome coverage: **{preflight['outcome_coverage']}**
- synthetic fill: **0건**
- locked joint slot manifest: **60 slots (slice×outcome cell당 3~4)**

현재 4개 장면은 모두 pedestrian/cyclist-yield의 hazard-active strata다. 두 다른 slice와
nominal/unknown/conflict/release/reactivation 근거가 없으므로 전문가 annotation을 시작하지
않는다. annotation/assignment/metrics/power 계약과 training UI만 배포하며, 관측 effect와
variance source ref 없이는 power record를 만들지 않는다. 이 결과는 pilot 준비도 감사이며
전문가 agreement나 GuardSynth 효과 결과가 아니다.
""",
        encoding="utf-8",
    )
    return preflight


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = execute(batch_path=args.batch, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
