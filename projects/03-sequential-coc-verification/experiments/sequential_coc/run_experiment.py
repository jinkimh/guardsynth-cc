#!/usr/bin/env python3
"""Reproduce the separated sequential-CoC experiment without paper writes."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Callable, Iterable, Mapping, Sequence

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())))

from experiments.sequential_coc import build_review_app, contract_review, panel_review
from experiments.sequential_coc.contract_compiler import build_summary, compile_window
from experiments.sequential_coc.cross_scene_boundary import (
    build_secondary_result,
    write_secondary_result,
)
from experiments.sequential_coc.evaluate import (
    UppaalEvidence,
    collect_uppaal_evidence,
    evaluate_all,
    load_production_inputs,
)
from experiments.sequential_coc.event_local_checker import check_event_local
from experiments.sequential_coc.extract_windows import (
    build_inventory,
    build_raw_event_windows,
    load_local_trajectory_raw_events,
    load_reasoning_events,
    local_egomotion_scene_ids,
    read_natural_windows,
    screen_transition_candidates,
    write_inventory,
    write_natural_windows,
)
from experiments.sequential_coc.mutation_generator import (
    generate_mutation_pairs,
    summarize_pairs,
    write_mutation_pairs,
)
from experiments.sequential_coc.stateful_checker import check_stateful
from experiments.sequential_coc.trajectory_contracts import (
    build_trajectory_records,
    write_trajectory_records,
)


STAGE_ORDER = (
    "inventory",
    "extract",
    "compile",
    "check",
    "uppaal",
    "mutate",
    "review",
    "trajectory",
    "evaluate",
    "secondary",
)

EXPECTED_PROTECTED_CHECKPOINTS: Mapping[str, object] = {
    "reasoning_parquet_sha256": "79859a0a93dbb71426cd6d6e54bc1250baa14ec0c45404a112ed87f6334b5ddf",
    "local_egomotion_parquet": {
        "file_count": 98,
        "aggregate_sha256": "5b61b9af6aa1efe7021ca6d044a9aae9b4dcab6e40d9f2378ecda12b1626acca",
    },
    "existing_results_tree": {
        "file_count": 1610,
        "aggregate_sha256": "135b5a136db44de2fab98721a50b4b0480e104f91b820971c7413a718f4d0585",
    },
    "kiee_paper_tree": {
        "file_count": 541,
        "aggregate_sha256": "473fcb6aea5a6b52e2ddc2b316b890a1a6652e83b6d523f9e4493e5302c1d988",
    },
}

@dataclass(frozen=True, slots=True)
class StageResult:
    stage: str
    status: str
    details: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RunResult:
    status: str
    paper_modified: bool
    stages: tuple[StageResult, ...]


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    root: Path
    output_dir: Path
    paper_root: Path
    expected_protected_checkpoints: Mapping[str, object] | None
    checkpoint_provider: Callable[[], Mapping[str, object]] | None = None
    stage_overrides: Mapping[str, Callable[[], StageResult]] = field(default_factory=dict)
    verifyta: Path | None = None
    external_rerun_command: str = (
        "runtime/alpamayo/ar1_venv/bin/python "
        "projects/03-sequential-coc-verification/experiments/sequential_coc/run_experiment.py --stage all"
    )


def _tree_snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    if not root.exists():
        return ()
    return tuple(
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _aggregate_checkpoint(root: Path, files: Iterable[Path]) -> dict[str, object]:
    selected = sorted(
        (path for path in files if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    digest = hashlib.sha256()
    for path in selected:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return {"file_count": len(selected), "aggregate_sha256": digest.hexdigest()}


def protected_input_checkpoints(root: Path, output_dir: Path) -> dict[str, object]:
    """Recompute Task-1 checkpoints with its exact relative-path/hash algorithm."""
    reasoning = root / "data/baseline/coc_nusc/reasoning/ood_reasoning.parquet"
    egomotion = root / "data/baseline/coc_nusc/labels/egomotion"
    results = root / "artifacts/results"
    paper = root / "projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit"
    result_files = (
        path
        for path in results.rglob("*")
        if path.is_file() and output_dir not in path.parents
    )
    return {
        "reasoning_parquet_sha256": _sha256_file(reasoning),
        "local_egomotion_parquet": _aggregate_checkpoint(
            egomotion, egomotion.glob("*.parquet")
        ),
        "existing_results_tree": _aggregate_checkpoint(results, result_files),
        "kiee_paper_tree": _aggregate_checkpoint(paper, paper.rglob("*")),
    }


def _atomic_write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_review_packet(
    expected_mapping: object,
    expected_counts: Mapping[str, object],
    review_dir: Path,
    expected_artifacts: Mapping[str, bytes] | None = None,
) -> None:
    """Bind the review packet to current selection and its declared file hashes."""
    mapping_path = review_dir / "adjudication-mapping.json"
    actual_mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if actual_mapping != expected_mapping:
        raise ValueError("review packet mapping does not match current selection")
    packet = json.loads(
        (review_dir / "packet-manifest.json").read_text(encoding="utf-8")
    )
    if packet.get("packet_status") != "WAITING_FOR_CONTRACT_REVIEW":
        raise ValueError("review packet status is invalid")
    if packet.get("counts") != dict(expected_counts):
        raise ValueError("review packet counts do not match current natural windows")
    artifacts = packet.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("review packet artifacts are missing")
    for name, metadata in artifacts.items():
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("review packet artifact name is invalid")
        if not isinstance(metadata, dict):
            raise ValueError("review packet artifact metadata is invalid")
        path = review_dir / name
        payload = path.read_bytes()
        if metadata.get("bytes") != len(payload) or metadata.get("sha256") != hashlib.sha256(
            payload
        ).hexdigest():
            raise ValueError(f"review packet artifact hash mismatch: {name}")
    for name, expected_payload in (expected_artifacts or {}).items():
        if (review_dir / name).read_bytes() != expected_payload:
            raise ValueError(f"review packet artifact content mismatch: {name}")


class _ProductionStages:
    def __init__(self, root: Path, output_dir: Path, verifyta: Path, external_command: str):
        self.root = root
        self.output_dir = output_dir
        self.verifyta = verifyta
        self.external_command = external_command
        self.uppaal_evidence: UppaalEvidence | None = None

    @property
    def reasoning_path(self) -> Path:
        return self.root / "data/baseline/coc_nusc/reasoning/ood_reasoning.parquet"

    @property
    def egomotion_dir(self) -> Path:
        return self.root / "data/baseline/coc_nusc/labels/egomotion"

    def inventory(self) -> StageResult:
        events = load_reasoning_events(self.reasoning_path)
        inventory = build_inventory(events, local_egomotion_scene_ids(self.egomotion_dir))
        write_inventory(inventory, self.output_dir / "inventory.json")
        return StageResult("inventory", "PASS", inventory)

    def extract(self) -> StageResult:
        raw_scenes = load_local_trajectory_raw_events(self.reasoning_path, self.egomotion_dir)
        windows = build_raw_event_windows(raw_scenes)
        candidates = screen_transition_candidates(windows)
        write_natural_windows(windows, self.output_dir / "natural-windows.jsonl")
        return StageResult(
            "extract",
            "PASS",
            {
                "window_count": len(windows),
                "scene_cluster_count": len({window.cluster_id for window in windows}),
                "candidate_window_count": len(candidates["candidate_window_ids"]),
                "candidate_scene_count": len(candidates["candidate_cluster_ids"]),
            },
        )

    def compile(self) -> StageResult:
        windows = read_natural_windows(self.output_dir / "natural-windows.jsonl")
        return StageResult("compile", "PASS", build_summary(windows))

    def check(self) -> StageResult:
        windows = read_natural_windows(self.output_dir / "natural-windows.jsonl")
        local_counts: Counter[str] = Counter()
        stateful_counts: Counter[str] = Counter()
        compiled_phase_count = 0
        for window in windows:
            events = compile_window(window)
            compiled_phase_count += len(events)
            local_counts[check_event_local(events).verdict] += 1
            stateful_counts[check_stateful(events).verdict] += 1
        return StageResult(
            "check",
            "PASS",
            {
                "window_count": len(windows),
                "compiled_phase_count": compiled_phase_count,
                "event_local_verdicts": dict(sorted(local_counts.items())),
                "stateful_verdicts": dict(sorted(stateful_counts.items())),
            },
        )

    def uppaal(self) -> StageResult:
        self.uppaal_evidence = collect_uppaal_evidence(self.verifyta)
        evidence = self.uppaal_evidence
        details = {
            "actual_verifyta_ran": evidence.actual_verifyta_ran,
            "evaluated_count": evidence.evaluated_count,
            "mismatch_count": evidence.mismatch_count,
            "verifyta": str(self.verifyta),
        }
        if not evidence.actual_verifyta_ran:
            return StageResult(
                "uppaal",
                "NOT_RUN",
                {**details, "external_rerun_command": self.external_command},
            )
        if evidence.evaluated_count != 7 or evidence.mismatch_count != 0:
            return StageResult("uppaal", "UPPAAL_MISMATCH", details)
        return StageResult("uppaal", "PASS", details)

    def mutate(self) -> StageResult:
        path = self.output_dir / "mutations.jsonl"
        pairs = generate_mutation_pairs(10, 20260806)
        write_mutation_pairs(pairs, path)
        return StageResult("mutate", "PASS", summarize_pairs(pairs, path))

    def review(self) -> StageResult:
        review_dir = self.output_dir / "review"
        windows = read_natural_windows(self.output_dir / "natural-windows.jsonl")
        items, expected_mapping, expected_counts = build_review_app.select_review_items(
            windows
        )
        expected_artifacts = {
            f"REVIEW_{reviewer}.html": build_review_app.build_contract_review_page(
                reviewer, build_review_app.order_for_reviewer(reviewer, items)
            ).encode("utf-8")
            for reviewer in ("A", "B")
        }
        validate_review_packet(
            expected_mapping, expected_counts, review_dir, expected_artifacts
        )
        output: list[str] = []
        if len(panel_review.discover_panel_csvs(review_dir)) >= 2:
            code = panel_review.main(
                ["--review-dir", str(review_dir)], output.append, review_items=items
            )
        else:
            code = contract_review.main(["--review-dir", str(review_dir)], output.append)
        if code != 0 or not output:
            return StageResult(
                "review", "CONTRACT_REVIEW_INVALID", {"returncode": code}
            )
        payload = json.loads(output[-1])
        return StageResult("review", str(payload["status"]), payload)

    def trajectory(self) -> StageResult:
        raw_scenes = load_local_trajectory_raw_events(self.reasoning_path, self.egomotion_dir)
        records = build_trajectory_records(raw_scenes, self.egomotion_dir)
        write_trajectory_records(records, self.output_dir / "trajectory-results.jsonl")
        return StageResult("trajectory", "PASS", records[0])

    def evaluate(self) -> StageResult:
        evidence = self.uppaal_evidence
        if evidence is None:
            evidence = collect_uppaal_evidence(self.verifyta)
            self.uppaal_evidence = evidence
        inputs = load_production_inputs(self.output_dir, None)
        inputs = replace(
            inputs,
            uppaal_mismatch_count=evidence.mismatch_count,
            actual_verifyta_ran=evidence.actual_verifyta_ran,
            uppaal_evaluated_count=evidence.evaluated_count,
        )
        result = evaluate_all(inputs)
        if not evidence.actual_verifyta_ran:
            return StageResult(
                "evaluate",
                "NOT_RUN",
                {
                    "reason": "UPPAAL_ACTUAL_VERIFYTA_NOT_RUN",
                    "evaluation_status": result["status"],
                    "metrics_preserved": True,
                    "external_rerun_command": self.external_command,
                },
            )
        _atomic_write_json(self.output_dir / "metrics.json", result)
        return StageResult("evaluate", "PASS", {"evaluation_status": result["status"]})

    def secondary(self) -> StageResult:
        official = self.root / "data/baseline/nuscenes_metadata/interp_12Hz_trainval"
        path = self.output_dir / "cross-scene-secondary.json"
        payload = build_secondary_result(official)
        write_secondary_result(path, payload)
        return StageResult(
            "secondary",
            "PASS",
            {
                "secondary_status": payload["input_inventory"]["status"],
                "evidence_level": payload["evidence_level"],
                "global_model_claim": payload["global_model_claim"],
            },
        )


def production_config(
    root: Path | None = None, *, verifyta: Path | None = None
) -> ExperimentConfig:
    project_root = (root or next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())).resolve()
    output_dir = project_root / "artifacts/results/restricted/sequential-coc-consistency-v1"
    paper_root = project_root / "projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit"
    verifyta_path = verifyta or project_root / "runtime/solvers/uppaal-5.0.0-linux64/bin/verifyta"
    external_command = (
        "runtime/alpamayo/ar1_venv/bin/python "
        "projects/03-sequential-coc-verification/experiments/sequential_coc/run_experiment.py --stage all"
    )
    operations = _ProductionStages(project_root, output_dir, verifyta_path, external_command)
    overrides = {name: getattr(operations, name) for name in STAGE_ORDER}
    return ExperimentConfig(
        root=project_root,
        output_dir=output_dir,
        paper_root=paper_root,
        expected_protected_checkpoints=EXPECTED_PROTECTED_CHECKPOINTS,
        checkpoint_provider=lambda: protected_input_checkpoints(project_root, output_dir),
        stage_overrides=overrides,
        verifyta=verifyta_path,
        external_rerun_command=external_command,
    )


def _protected_inputs_match(config: ExperimentConfig) -> bool:
    expected = config.expected_protected_checkpoints
    if expected is None:
        return True
    if config.checkpoint_provider is None:
        return False
    try:
        return dict(config.checkpoint_provider()) == dict(expected)
    except (OSError, TypeError, ValueError):
        return False


def run_stage(stage: str, config: ExperimentConfig) -> StageResult:
    """Execute one stage and convert operational errors to finite statuses."""
    if stage not in STAGE_ORDER:
        raise ValueError(f"unknown stage: {stage}")
    operation = config.stage_overrides.get(stage)
    if operation is None:
        return StageResult(stage, "NOT_IMPLEMENTED")
    try:
        result = operation()
    except FileNotFoundError as exc:
        return StageResult(stage, "MISSING_ARTIFACT", {"reason": str(exc)})
    except PermissionError as exc:
        return StageResult(stage, "NOT_RUN", {"reason": str(exc)})
    except subprocess.SubprocessError as exc:
        return StageResult(stage, "SUBPROCESS_FAILED", {"reason": str(exc)})
    except OSError as exc:
        return StageResult(stage, "SUBPROCESS_FAILED", {"reason": str(exc)})
    except (TypeError, ValueError) as exc:
        return StageResult(stage, "INVALID_ARTIFACT", {"reason": str(exc)})
    if not isinstance(result, StageResult) or result.stage != stage:
        return StageResult(stage, "INVALID_STAGE_OUTPUT")
    return result


def run_all(config: ExperimentConfig) -> RunResult:
    """Run every automatic stage and wait honestly for absent human review."""
    paper_before = _tree_snapshot(config.paper_root)
    if not _protected_inputs_match(config):
        return RunResult("PROTECTED_INPUT_CHANGED", False, ())
    completed: list[StageResult] = []
    for name in STAGE_ORDER:
        result = run_stage(name, config)
        completed.append(result)
        paper_modified = _tree_snapshot(config.paper_root) != paper_before
        if paper_modified or not _protected_inputs_match(config):
            return RunResult(
                "PROTECTED_INPUT_CHANGED", paper_modified, tuple(completed)
            )
        if result.status not in {
            "PASS",
            "WAITING_FOR_CONTRACT_REVIEW",
            "WAITING_FOR_CONSENSUS",
            "WAITING_FOR_PANEL_ADJUDICATION",
            "CONTRACT_REVIEW_COMPLETE",
            "PANEL_REVIEW_COMPLETE",
            "NOT_RUN",
        }:
            return RunResult(
                result.status,
                paper_modified,
                tuple(completed),
            )
    stages = tuple(completed)
    review = next(stage for stage in stages if stage.stage == "review")
    paper_modified = _tree_snapshot(config.paper_root) != paper_before
    if paper_modified or not _protected_inputs_match(config):
        return RunResult("PROTECTED_INPUT_CHANGED", paper_modified, stages)
    not_run = next(
        (
            stage
            for stage in stages
            if stage.stage != "review" and stage.status == "NOT_RUN"
        ),
        None,
    )
    status = f"{not_run.stage.upper()}_NOT_RUN" if not_run else review.status
    return RunResult(status, paper_modified, stages)


def _stage_payload(result: StageResult) -> dict[str, object]:
    return {
        "stage": result.stage,
        "status": result.status,
        "details": dict(result.details),
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    config: ExperimentConfig | None = None,
    printer: Callable[[str], None] = print,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=(*STAGE_ORDER, "all"))
    args = parser.parse_args(argv)
    active_config = config or production_config()
    if args.stage == "all":
        result = run_all(active_config)
        payload = {
            "status": result.status,
            "paper_modified": result.paper_modified,
            "stages": [_stage_payload(stage) for stage in result.stages],
        }
        printer(json.dumps(payload, sort_keys=True))
        return 0 if result.status in {
            "WAITING_FOR_CONTRACT_REVIEW",
            "WAITING_FOR_CONSENSUS",
            "WAITING_FOR_PANEL_ADJUDICATION",
            "CONTRACT_REVIEW_COMPLETE",
            "PANEL_REVIEW_COMPLETE",
        } else 2

    paper_before = _tree_snapshot(active_config.paper_root)
    if not _protected_inputs_match(active_config):
        result = StageResult(args.stage, "PROTECTED_INPUT_CHANGED")
    else:
        result = run_stage(args.stage, active_config)
        if (
            _tree_snapshot(active_config.paper_root) != paper_before
            or not _protected_inputs_match(active_config)
        ):
            result = StageResult(args.stage, "PROTECTED_INPUT_CHANGED")
    printer(json.dumps(_stage_payload(result), sort_keys=True))
    if result.status in {
        "PASS",
        "WAITING_FOR_CONTRACT_REVIEW",
        "WAITING_FOR_CONSENSUS",
        "WAITING_FOR_PANEL_ADJUDICATION",
        "CONTRACT_REVIEW_COMPLETE",
        "PANEL_REVIEW_COMPLETE",
    }:
        return 0
    return 3 if result.status == "NOT_RUN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
