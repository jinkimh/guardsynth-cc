"""Build the public, self-contained GuardSynth scene-evidence review kit."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from cli.project_paths import project_root


ROOT = project_root(__file__)
HERE = Path(__file__).resolve().parent
EXPERIMENT_ID = "GUARDSYNTH-SCENE-EVIDENCE-REVIEW-001"
DEFAULT_RUN_ID = "scene-evidence-review-2026-08-10-v1"
CLAIM_SCOPE = "REVIEW_WORKFLOW_AND_EVIDENCE_TRIAGE_NOT_SOURCE_CREATION_OR_VEHICLE_SAFETY"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _test(module: str) -> dict[str, Any]:
    command = [sys.executable, "-m", "unittest", module, "-v"]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT)
    completed = subprocess.run(
        command, cwd=ROOT, env=environment, text=True, capture_output=True, check=False
    )
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
    }


def execute(run_id: str) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/guardsynth-scene-evidence-review-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")
    output.mkdir(parents=True)

    sources = {
        "scene_evidence_review.html": HERE / "scene_evidence_review.html",
        "REVIEW_METHOD.md": ROOT / "projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_SCENE_EVIDENCE_REVIEW_UI_DESIGN_V01.md",
        "REVIEW_OUTPUT_SCHEMA.json": ROOT / "projects/04-guardsynth-coc/src/guard_synth/schemas/scene_evidence_review.schema.json",
    }
    for name, source in sources.items():
        shutil.copy2(source, output / name)

    tests = {
        "review_ui": _test("projects/04-guardsynth-coc/tests/integration/test_scene_evidence_review_ui.py"),
        "project_layout": _test("tests.structure.test_project_layout"),
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "status": "EXECUTED" if all(item["passed"] for item in tests.values()) else "FAILED",
        "self_contained_html": True,
        "network_access_blocked_by_csp": True,
        "inline_synthetic_diagram_count": 3,
        "review_example_count": 4,
        "batch_image_and_folder_import": True,
        "restricted_embedded_builder_available": True,
        "image_bytes_exported": False,
        "auto_triage_precedence": ["CONFLICT", "UNSUPPORTED", "REVIEW_REQUIRED", "SOURCE_COMPLETE"],
        "source_complete_upward_override_allowed": False,
        "tests": tests,
        "claim_scope": CLAIM_SCOPE,
    }
    _write_json(output / "RESULT.json", result)

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "input_class": "SYNTHETIC_PUBLIC_REVIEW_ASSETS",
        "deterministic": True,
        "claim_scope": CLAIM_SCOPE,
        "files": {path.name: _sha256(path) for path in sorted(output.iterdir())},
        "tests": tests,
    }
    _write_json(output / "RUN_MANIFEST.json", manifest)
    (output / "REPORT_KO.md").write_text(
        f"""# GuardSynth 장면 근거 검토 패키지

- 상태: **{result['status']}**
- HTML: `scene_evidence_review.html`
- 합성 도식: 3개
- 판정 예제: 4개
- 자동 판정: CONFLICT → UNSUPPORTED → REVIEW_REQUIRED → SOURCE_COMPLETE
- 이미지 처리: 로컬 preview만 허용, JSON/CSV에 bytes 미포함
- 주장 범위: `{CLAIM_SCOPE}`

이 패키지는 누락 근거를 만들어 주지 않는다. 검토 결과가 `SOURCE_COMPLETE`가 되려면
장면 association, geometry/transform/time, 적용 규칙과 필요한 차량 assurance가 실제
reference로 닫혀야 한다. 자동 권고보다 높은 `SOURCE_COMPLETE` 판정으로 우회할 수 없다.
""",
        encoding="utf-8",
    )
    return output, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    args = parser.parse_args()
    output, result = execute(args.run_id)
    print(json.dumps({"output": str(output), "status": result["status"]}, ensure_ascii=False))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
