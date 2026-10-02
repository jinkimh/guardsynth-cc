#!/usr/bin/env python3
"""Synthetic-only provenance policy checks at a scene boundary.

This module deliberately does not infer official trainval provenance, object
continuity, or natural semantic contradictions.  It demonstrates only the
policy distinction between discarding a boundary obligation, carrying it with
confirmed provenance, and attempting unsupported carryover.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

if __package__ in (None, ""):
    sys.path.insert(0, str(next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())))

from experiments.sequential_coc.contract_ir import (
    CheckResult,
    ContradictionType,
    ObligationState,
)


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
OUTPUT_DIR = ROOT / "artifacts/results/restricted/sequential-coc-consistency-v1"
OUTPUT_PATH = OUTPUT_DIR / "cross-scene-secondary.json"
OFFICIAL_TRAINVAL_ROOT = ROOT / "data/baseline/nuscenes_metadata/interp_12Hz_trainval"
EXPECTED_INVENTORY = {
    "chain_count": 13,
    "unique_scene_count": 29,
    "boundary_count": 16,
}


def evaluate_boundary_policy(
    chain: dict, carryover: bool, provenance_supported: bool
) -> CheckResult:
    """Apply only the provenance rule for a proposed boundary carryover.

    ``chain`` is intentionally opaque: the policy must not derive continuity
    or a natural semantic result from its contents.
    """
    if not isinstance(chain, dict):
        raise TypeError("chain must be a dict")
    if not isinstance(carryover, bool) or not isinstance(provenance_supported, bool):
        raise TypeError("carryover and provenance_supported must be bool")

    if carryover and not provenance_supported:
        return CheckResult(
            verdict="POLICY_ERROR",
            contradiction_types=(ContradictionType.UNSUPPORTED_CARRYOVER,),
            state_trace=(ObligationState.INACTIVE,),
        )
    if carryover:
        return CheckResult(verdict="CONSISTENT", state_trace=(ObligationState.ACTIVE,))
    return CheckResult(verdict="CONSISTENT", state_trace=(ObligationState.INACTIVE,))


def _inventory_gate(official_trainval_root: Path) -> dict[str, object]:
    """Fail closed when raw official membership evidence cannot be rechecked."""
    if not official_trainval_root.is_dir():
        reason = "OFFICIAL_TRAINVAL_RAW_SOURCE_UNAVAILABLE"
    else:
        reason = "RAW_CHAIN_MEMBERSHIP_AND_OBJECT_CONTINUITY_NOT_ESTABLISHED"
    return {
        "status": "INPUT_INVENTORY_MISMATCH",
        "expected": dict(EXPECTED_INVENTORY),
        "observed": None,
        "failure_reasons": [reason],
    }


def _synthetic_chain() -> dict[str, object]:
    return {"fixture_kind": "SYNTHETIC_BOUNDARY", "boundary_count": 1}


def build_secondary_result(official_trainval_root: Path = OFFICIAL_TRAINVAL_ROOT) -> dict[str, object]:
    """Build aggregate-only provenance-policy evidence from synthetic fixtures."""
    cases = (
        ("DISCARD", False, False),
        ("SUPPORTED_CARRYOVER", True, True),
        ("UNSUPPORTED_CARRYOVER", True, False),
    )
    aggregate: dict[str, dict[str, int]] = {}
    for policy, carryover, provenance_supported in cases:
        result = evaluate_boundary_policy(
            _synthetic_chain(), carryover, provenance_supported
        )
        aggregate[policy] = {
            "policy_error_count": int(result.verdict == "POLICY_ERROR"),
            "natural_semantic_conflict_count": 0,
        }

    inventory = _inventory_gate(official_trainval_root)
    return {
        "schema_version": "sequential-coc-cross-scene-secondary-v1",
        "evidence_level": "PROVENANCE_POLICY_EXAMPLE",
        "global_model_claim": False,
        "input_inventory": inventory,
        "policy_aggregate": aggregate,
        "natural_semantic_conflict_count": 0,
        "unknown_status": "NOT_RUN",
        "not_run_reasons": [
            "OFFICIAL_TRAINVAL_PROVENANCE_NOT_REVERIFIED",
            "OBJECT_CONTINUITY_NOT_ESTABLISHED",
        ],
        "failure_reasons": ["INPUT_INVENTORY_MISMATCH"],
        "excluded_claims": [
            "GLOBAL_COC_MODEL",
            "SAFETY_OR_CONTROL_ROBUSTNESS",
            "OFFICIAL_TRAINVAL_PROVENANCE",
            "OBJECT_CONTINUITY",
        ],
    }


def write_secondary_result(output_path: Path, payload: dict[str, object]) -> None:
    """Atomically publish an aggregate-only restricted result with fixed modes."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(output_path.parent, 0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", dir=output_path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, output_path)
        os.chmod(output_path, 0o600)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-trainval-root", type=Path, default=OFFICIAL_TRAINVAL_ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    payload = build_secondary_result(args.official_trainval_root)
    write_secondary_result(args.output, payload)
    print(
        json.dumps(
            {
                "evidence_level": payload["evidence_level"],
                "global_model_claim": payload["global_model_claim"],
                "input_inventory_status": payload["input_inventory"]["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
