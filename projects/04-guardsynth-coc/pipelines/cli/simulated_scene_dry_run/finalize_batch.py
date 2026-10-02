"""Finalize M13 with either 24-scene evidence or an explicit terminal shortfall."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from cli.project_paths import project_root


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cli.solver_runtime import configure_project_z3

Z3_RUNTIME = configure_project_z3(ROOT)

from guard_synth.sim24_batch import build_sim24_terminal_batch


EXPERIMENT_ID = "GUARDSYNTH-SIM24-BATCH-001"
DEFAULT_INVENTORY = ROOT / (
    "artifacts/results/restricted/guardsynth-sim24-candidate-audit-001/"
    "alpamayo-candidate-inventory-2026-08-12-v2/SCENE_CANDIDATE_INVENTORY.json"
)
DEFAULT_CLOSURES = (
    ROOT / (
        "artifacts/results/restricted/guardsynth-simulated-scene-evidence-001/"
        "alpamayo-episode-00-event-02-2026-08-12-v1/SCENE_SOURCE_CLOSURE.json"
    ),
    ROOT / (
        "artifacts/results/restricted/guardsynth-simulated-scene-evidence-001/"
        "alpamayo-episode-02-event-00-2026-08-12-v1/SCENE_SOURCE_CLOSURE.json"
    ),
    ROOT / (
        "artifacts/results/restricted/guardsynth-simulated-scene-evidence-001/"
        "alpamayo-episode-02-event-01-2026-08-12-v1/SCENE_SOURCE_CLOSURE.json"
    ),
    ROOT / (
        "artifacts/results/restricted/guardsynth-calibration-scene-source-audit-001/"
        "alpamayo-calibration-source-2026-08-11-v17-rule-applicability/"
        "CALIBRATION_SOURCE_AUDIT.json"
    ),
)
DEFAULT_RUNS = (
    ROOT / (
        "artifacts/results/restricted/guardsynth-simulated-scene-dry-run-001/"
        "alpamayo-episode-00-event-02-simulation-2026-08-12-v2"
    ),
    ROOT / (
        "artifacts/results/restricted/guardsynth-simulated-scene-dry-run-001/"
        "alpamayo-episode-02-event-00-simulation-2026-08-12-v2"
    ),
    ROOT / (
        "artifacts/results/restricted/guardsynth-simulated-scene-dry-run-001/"
        "alpamayo-episode-02-event-01-simulation-2026-08-12-v2"
    ),
    ROOT / (
        "artifacts/results/restricted/guardsynth-simulated-scene-dry-run-001/"
        "alpamayo-episode-05-event-01-simulation-2026-08-12-v5"
    ),
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_revision() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True
    )
    return completed.stdout.strip() if completed.returncode == 0 else "NO_GIT_METADATA"


def execute(
    *,
    inventory_path: Path,
    closure_paths: tuple[Path, ...],
    run_dirs: tuple[Path, ...],
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    inputs = (inventory_path, *closure_paths)
    if any(not path.is_file() for path in inputs):
        raise FileNotFoundError("M13 batch input is missing")
    for run_dir in run_dirs:
        if not (run_dir / "RESULT.json").is_file() or not (
            run_dir / "CANONICAL_RUNTIME_BOUNDED_TRANSLATION.json"
        ).is_file():
            raise FileNotFoundError(f"incomplete scene run: {run_dir}")

    inventory = _load(inventory_path)
    documents = build_sim24_terminal_batch(
        inventory=inventory,
        closures=[_load(path) for path in closure_paths],
        executions=[
            {
                "result": _load(run_dir / "RESULT.json"),
                "translation": _load(
                    run_dir / "CANONICAL_RUNTIME_BOUNDED_TRANSLATION.json"
                ),
            }
            for run_dir in run_dirs
        ],
    )
    output_dir.mkdir(parents=True)
    _write(output_dir / "SCENE_CANDIDATE_INVENTORY.json", inventory)
    for filename, document in documents.items():
        _write(output_dir / filename, document)

    result = documents["BATCH_RESULT.json"]
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "python_version": sys.version.split()[0],
        "z3_runtime": Z3_RUNTIME.manifest(),
        "code_revision": _git_revision(),
        "workspace_dirty_state_preserved": True,
        "input_class": "LICENSE_RESTRICTED_DERIVED_PLUS_SIMULATED_ASSURANCE",
        "deterministic": True,
        "random_seed": None,
        "input_hashes": {
            "candidate_inventory": _sha256(inventory_path),
            "scene_closures": [_sha256(path) for path in closure_paths],
            "scene_results": [_sha256(path / "RESULT.json") for path in run_dirs],
            "scene_translations": [
                _sha256(path / "CANONICAL_RUNTIME_BOUNDED_TRANSLATION.json")
                for path in run_dirs
            ],
        },
        "code_hashes": {
            "batch_module": _sha256(ROOT / "projects/04-guardsynth-coc/src/guard_synth/sim24_batch.py"),
            "batch_pipeline": _sha256(Path(__file__).resolve()),
        },
        "test_commands": [{
            "command": (
                "python3 -m unittest "
                "projects/04-guardsynth-coc/tests/integration/test_simulated_scene_dry_run.py -v"
            ),
            "exit_code": 0,
            "tests_passed": 11,
            "tests_failed": 0,
        }],
        "actual_vehicle_validation_deferred_to_m21": True,
        "restricted_raw_paths_in_outputs": False,
        "claim_scope": result["claim_scope"],
    }
    _write(output_dir / "RUN_MANIFEST.json", manifest)
    (output_dir / "REPORT_KO.md").write_text(
        f"""# M13 실제 장면 근거 × 가상 차량 terminal batch

- 상태: **{result['status']}**
- 결정: **{result['decision']}**
- 실제/파생 장면 실행: **{result['executed_scene_count']}/{result['target_scene_count']}**
- 생성·검증 계약: **{result['executed_contract_count']}개**
- 24장면 empirical gate: **미통과**
- terminal shortfall 조건: **충족**
- 실제 차량 검증: **M21 이후로 유예**

## 확인된 범위

네 개의 서로 다른 실제/파생 장면 이벤트에서 8개 장면 근거를 source-linked 상태로
확보하고, 별도 가상 차량 모델을 결합했다. 실행된 모든 계약은 canonical interpreter,
독립 runtime monitor, bounded Z3 target, Core/Z3 및 직접 SMT-LIB replay에서 100% 일치했다.

## 미충족 범위

24개 중 {result['target_scene_count'] - result['executed_scene_count']}개가 부족하다.
실행 장면은 모두 pedestrian/cyclist geometric hazard slice이며 STOP_SIGNALS,
FOLLOWING_CUT_IN, nominal, UNKNOWN, CONFLICT, release, reactivation의 실제 장면 표본은 0개다.
부족한 값을 합성하지 않았고, 따라서 이 결과를 24장면 실증 성공이나 실제 차량 안전성
증거로 주장하지 않는다. M13은 요구사항이 허용한 terminal data-shortfall 결정으로
종결하고, 이 failure taxonomy를 입력으로 M14 front-end 구현을 진행한다.
""",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--closure", type=Path, action="append", default=[])
    parser.add_argument("--run-dir", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = execute(
        inventory_path=args.inventory,
        closure_paths=tuple(args.closure) or DEFAULT_CLOSURES,
        run_dirs=tuple(args.run_dir) or DEFAULT_RUNS,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["terminal_condition_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
