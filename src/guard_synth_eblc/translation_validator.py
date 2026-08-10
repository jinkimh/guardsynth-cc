"""Public comparison of canonical, runtime, and bounded target decisions."""

from __future__ import annotations

from .runtime_monitor import run_runtime
from .semantics import run_canonical
from .types import BoundContract, ContextFrame, TraceResult
from .z3_bounded_checker import ENGINE, ENGINE_VERSION, run_bounded_target


def normalized(result: TraceResult) -> dict[str, object]:
    return {
        "accepted": result.accepted,
        "verdict": result.verdict.value,
        "lifecycle": [step.lifecycle.value for step in result.steps],
        "violations": list(result.violations),
    }


def validate_translation(
    contract: BoundContract,
    traces: dict[str, tuple[ContextFrame, ...]],
) -> dict[str, object]:
    records: list[dict[str, object]] = []
    for trace_id, frames in traces.items():
        canonical = normalized(run_canonical(contract, frames))
        runtime = normalized(run_runtime(contract, frames))
        bounded = normalized(run_bounded_target(contract, frames))
        records.append(
            {
                "trace_id": trace_id,
                "canonical": canonical,
                "runtime_monitor": runtime,
                "bounded_target": bounded,
                "canonical_runtime_agree": canonical == runtime,
                "canonical_bounded_target_agree": canonical == bounded,
            }
        )
    total = len(records)
    runtime_matches = sum(bool(row["canonical_runtime_agree"]) for row in records)
    bounded_matches = sum(bool(row["canonical_bounded_target_agree"]) for row in records)
    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "trace_count": total,
        "canonical_runtime_matches": runtime_matches,
        "canonical_runtime_agreement": runtime_matches / total if total else 1.0,
        "canonical_bounded_target_matches": bounded_matches,
        "canonical_bounded_target_agreement": bounded_matches / total if total else 1.0,
        "records": records,
        "claim_boundary": "BOUNDED_TRANSLATION_AGREEMENT_NOT_INDEPENDENT_VEHICLE_SAFETY_VERIFICATION",
    }
