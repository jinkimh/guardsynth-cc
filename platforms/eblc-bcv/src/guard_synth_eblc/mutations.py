"""Public controlled BCV under/overconstraint mutation suite."""

from __future__ import annotations

from dataclasses import replace

from .adapters.synthetic_pedestrian import frame
from .runtime_monitor import run_runtime
from .semantics import run_canonical
from .translation_validator import normalized
from .types import BoundContract, ContextFrame, Truth
from .z3_bounded_checker import ENGINE, run_bounded_target


def _witnesses() -> dict[str, tuple[ContextFrame, ...]]:
    return {
        "MISSING_INVARIANT": (frame(0.0, Truth.TRUE, x=-1.0, speed=0.0),),
        "WEAK_STOP_BOUND": (frame(0.0, Truth.TRUE, x=-1.0, speed=0.0),),
        "WRONG_TARGET": (frame(0.0, Truth.TRUE, x=-1.0, speed=0.0),),
        "MISSING_REACTIVATION": (
            frame(0.0, Truth.TRUE), frame(0.1, Truth.FALSE),
            frame(0.2, Truth.FALSE), frame(0.3, Truth.TRUE),
            frame(0.4, Truth.TRUE, x=-1.49, speed=0.0),
        ),
        "UNKNOWN_AS_FALSE": (
            frame(0.0, Truth.TRUE), frame(0.1, Truth.UNKNOWN),
            frame(0.2, Truth.UNKNOWN), frame(0.3, Truth.FALSE, x=-1.49, speed=0.0),
        ),
        "MISSING_RELEASE": (
            frame(0.0, Truth.TRUE), frame(0.1, Truth.FALSE),
            frame(0.2, Truth.FALSE), frame(0.3, Truth.FALSE, x=1.0, speed=0.0, safe_progress=True),
        ),
        "OVER_TIGHT_BOUND": (frame(0.0, Truth.TRUE, x=-1.75, speed=0.0),),
        "EXTRA_ALWAYS_ACTIVE_CLAUSE": (frame(0.0, Truth.FALSE, x=1.0, speed=0.0, safe_progress=True),),
        "UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK": (frame(0.0, Truth.UNKNOWN, x=-1.0, speed=0.0, safe_progress=True),),
        "FALSE_DEADLOCK": (frame(0.0, Truth.FALSE, x=1.0, speed=1.0, safe_progress=True),),
    }


MUTATION_METADATA: dict[str, dict[str, str]] = {
    "MISSING_INVARIANT": {"class": "underconstraint", "field": "enforce_invariant", "reason": "MISSING_CLAUSE_WITNESS"},
    "WEAK_STOP_BOUND": {"class": "underconstraint", "field": "stop_position_x_m += 1.0", "reason": "WEAK_BOUND_WITNESS"},
    "WRONG_TARGET": {"class": "underconstraint", "field": "target_entity_id", "reason": "WRONG_TARGET_WITNESS"},
    "MISSING_REACTIVATION": {"class": "underconstraint", "field": "reactivation_enabled", "reason": "MISSED_REACTIVATION_WITNESS"},
    "UNKNOWN_AS_FALSE": {"class": "underconstraint", "field": "unknown_policy=AS_FALSE", "reason": "UNKNOWN_CLOSED_FALSE_WITNESS"},
    "MISSING_RELEASE": {"class": "overconstraint", "field": "release_enabled", "reason": "STALE_OBLIGATION_WITNESS"},
    "OVER_TIGHT_BOUND": {"class": "overconstraint", "field": "stop_position_x_m -= 0.5", "reason": "OVER_TIGHT_BOUND_WITNESS"},
    "EXTRA_ALWAYS_ACTIVE_CLAUSE": {"class": "overconstraint", "field": "always_active", "reason": "EXTRA_CLAUSE_WITNESS"},
    "UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK": {"class": "overconstraint", "field": "unknown_policy=AS_TRUE; fallback_approved=false", "reason": "UNAPPROVED_UNKNOWN_TRUE_WITNESS"},
    "FALSE_DEADLOCK": {"class": "overconstraint", "field": "force_deadlock", "reason": "FALSE_DEADLOCK_WITNESS"},
}


def mutate(contract: BoundContract, mutation_id: str) -> BoundContract:
    common = {"mutation_id": mutation_id}
    if mutation_id == "MISSING_INVARIANT":
        return replace(contract, enforce_invariant=False, **common)
    if mutation_id == "WEAK_STOP_BOUND":
        return replace(contract, stop_position_x_m=contract.stop_position_x_m + 1.0, **common)
    if mutation_id == "WRONG_TARGET":
        return replace(contract, target_entity_id="mutated-wrong-target", **common)
    if mutation_id == "MISSING_REACTIVATION":
        return replace(contract, reactivation_enabled=False, **common)
    if mutation_id == "UNKNOWN_AS_FALSE":
        return replace(contract, unknown_policy="AS_FALSE", **common)
    if mutation_id == "MISSING_RELEASE":
        return replace(contract, release_enabled=False, **common)
    if mutation_id == "OVER_TIGHT_BOUND":
        return replace(contract, stop_position_x_m=contract.stop_position_x_m - 0.5, **common)
    if mutation_id == "EXTRA_ALWAYS_ACTIVE_CLAUSE":
        return replace(contract, always_active=True, **common)
    if mutation_id == "UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK":
        return replace(contract, unknown_policy="AS_TRUE", fallback_approved=False, **common)
    if mutation_id == "FALSE_DEADLOCK":
        return replace(contract, force_deadlock=True, **common)
    raise KeyError(mutation_id)


def _frame_summary(item: ContextFrame) -> dict[str, object]:
    return {
        "t": item.timestamp_s,
        "hazard": item.hazard.truth.value,
        "epistemic_kind": item.hazard.epistemic_kind.value,
        "ego_front_x_m": item.ego_front_x_m,
        "ego_speed_mps": item.ego_speed_mps,
        "safe_progress_available": item.safe_progress_available,
    }


def run_mutation_suite(contract: BoundContract) -> dict[str, object]:
    records: list[dict[str, object]] = []
    for mutation_id, metadata in MUTATION_METADATA.items():
        witness = _witnesses()[mutation_id]
        mutant = mutate(contract, mutation_id)
        base = run_canonical(contract, witness)
        canonical = run_canonical(mutant, witness)
        runtime = run_runtime(mutant, witness)
        bounded = run_bounded_target(mutant, witness)
        expected_flip = (
            (not base.accepted and canonical.accepted)
            if metadata["class"] == "underconstraint"
            else (base.accepted and not canonical.accepted)
        )
        target_agreement = normalized(canonical) == normalized(runtime) == normalized(bounded)
        detected = expected_flip and target_agreement
        records.append(
            {
                "mutation_id": mutation_id,
                "classification": metadata["class"],
                "mutated_field_or_edge": metadata["field"],
                "minimal_witness_trace": [_frame_summary(item) for item in witness],
                "base_canonical": normalized(base),
                "canonical": normalized(canonical),
                "runtime_monitor": normalized(runtime),
                "bounded_target": normalized(bounded),
                "detected": detected,
                "reason_code": metadata["reason"] if detected else "MUTATION_NOT_DETECTED",
                "oracle_scope": ["CONTROLLED_MUTATION_ORACLE", "NOT_INDEPENDENT_SAFETY_ORACLE"],
            }
        )
    under = [row for row in records if row["classification"] == "underconstraint"]
    over = [row for row in records if row["classification"] == "overconstraint"]
    under_detected = sum(bool(row["detected"]) for row in under)
    over_detected = sum(bool(row["detected"]) for row in over)
    return {
        "engine": ENGINE,
        "oracle_scope": ["CONTROLLED_MUTATION_ORACLE", "NOT_INDEPENDENT_SAFETY_ORACLE"],
        "underconstraint": {"detected": under_detected, "total": len(under), "recall": under_detected / len(under)},
        "overconstraint": {"detected": over_detected, "total": len(over), "recall": over_detected / len(over)},
        "records": records,
    }
