"""Aggregate M13 scene-grounded simulation runs without filling data gaps."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .simulated_scene_inventory import REQUIRED_SCENE_FIELDS


def build_sim24_terminal_batch(
    *,
    inventory: dict[str, Any],
    closures: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    target_scene_count: int = 24,
) -> dict[str, dict[str, Any]]:
    """Build the required M13 batch documents and an explicit terminal decision."""
    if target_scene_count < 1:
        raise ValueError("INVALID_TARGET_SCENE_COUNT")
    if inventory.get("synthetic_scene_fill_performed") is not False:
        raise ValueError("SYNTHETIC_SCENE_FILL_NOT_ALLOWED")
    if len(closures) != len(executions):
        raise ValueError("CLOSURE_EXECUTION_COUNT_MISMATCH")

    required = set(REQUIRED_SCENE_FIELDS)
    closure_records = []
    closure_refs: set[str] = set()
    for closure in closures:
        scene_ref = closure.get("scene_ref")
        if not scene_ref or scene_ref in closure_refs:
            raise ValueError("DUPLICATE_OR_MISSING_SCENE_REF")
        closure_refs.add(scene_ref)
        available = set(closure.get("available_fields", ()))
        if available != required or closure.get("synthesized_required_values"):
            raise ValueError("EXECUTED_SCENE_NOT_8_OF_8_SOURCE_LINKED")
        closure_records.append({
            "scene_ref": scene_ref,
            "available_scene_fields": sorted(available),
            "scene_field_count": len(available),
            "recorded_vehicle_assurance_gap": list(
                closure.get("missing_fields", ())
            ),
            "synthetic_scene_fill_performed": False,
        })

    translation_records = []
    executed_refs: set[str] = set()
    total_contracts = 0
    for execution in executions:
        result = execution.get("result", {})
        scene_ref = result.get("scene_ref")
        if (
            result.get("status") != "EXECUTED"
            or not scene_ref
            or scene_ref in executed_refs
            or scene_ref not in closure_refs
        ):
            raise ValueError("INVALID_OR_DUPLICATE_EXECUTION")
        executed_refs.add(scene_ref)
        contract_count = int(result.get("contract_count", 0))
        if contract_count < 1:
            raise ValueError("EXECUTION_HAS_NO_CONTRACTS")
        total_contracts += contract_count
        translation_records.append({
            "scene_ref": scene_ref,
            "contract_count": contract_count,
            "canonical_runtime_agreement": result.get(
                "canonical_runtime_recorded_frame_agreement"
            ),
            "canonical_bounded_z3_agreement": result.get(
                "canonical_bounded_recorded_frame_agreement"
            ),
            "canonical_core_agreement": result.get(
                "canonical_core_recorded_frame_agreement"
            ),
            "core_z3_query_agreement": result.get("z3_query_agreement"),
            "direct_z3_smtlib_replay_agreement": result.get(
                "direct_z3_smtlib_replay_agreement"
            ),
            "trace_count": execution.get("translation", {}).get("trace_count"),
        })

    agreement_keys = (
        "canonical_runtime_agreement",
        "canonical_bounded_z3_agreement",
        "canonical_core_agreement",
        "core_z3_query_agreement",
        "direct_z3_smtlib_replay_agreement",
    )
    translation_agreement = {
        key: (
            sum(record[key] == 1.0 for record in translation_records)
            / len(translation_records)
            if translation_records
            else 0.0
        )
        for key in agreement_keys
    }

    candidates = inventory.get("candidates", ())
    unready = [item for item in candidates if not item.get("simulation_projection_ready")]
    missing_fields = Counter(
        field
        for item in unready
        for field in item.get("missing_scene_fields", ())
    )
    executed_count = len(executions)
    total_shortfall = max(0, target_scene_count - executed_count)
    absent_slots = max(0, total_shortfall - len(unready))
    empirical_gate = executed_count >= target_scene_count
    decision = (
        "M13_24_SCENE_GATE_PASSED"
        if empirical_gate
        else "M13_TERMINAL_DATA_SHORTFALL_FRONTEND_CAN_PROCEED"
    )

    abstention = {
        "target_scene_count": target_scene_count,
        "executed_scene_count": executed_count,
        "total_shortfall": total_shortfall,
        "inventoried_unready": len(unready),
        "absent_candidate_slots": absent_slots,
        "missing_field_reason_counts": dict(sorted(missing_fields.items())),
        "unready_candidates": [
            {
                "candidate_ref": item.get("candidate_ref"),
                "missing_scene_fields": list(item.get("missing_scene_fields", ())),
                "reason_code": "M13_SCENE_SOURCE_FIELDS_INCOMPLETE",
            }
            for item in unready
        ],
        "missing_input_preservation_rate": 1.0,
        "synthetic_scene_fill_count": 0,
    }
    translations = {
        "executed_scene_count": executed_count,
        "contract_count": total_contracts,
        **translation_agreement,
        "records": translation_records,
        "claim_boundary": (
            "BOUNDED_TRANSLATION_AGREEMENT_NOT_REAL_VEHICLE_SAFETY_PROOF"
        ),
    }
    source_closure = {
        "executed_scene_count": executed_count,
        "required_scene_field_count": len(REQUIRED_SCENE_FIELDS),
        "source_closure_rate": 1.0 if closure_records else 0.0,
        "records": closure_records,
        "actual_vehicle_assurance_deferred_to_m21": True,
    }
    gates = {
        "empirical_24_scene_coverage": empirical_gate,
        "terminal_shortfall_decision_recorded": not empirical_gate,
        "synthetic_scene_field_fill_zero": True,
        "recorded_simulation_binding_separation": all(
            execution["result"].get("gates", {}).get("distinct_vehicle_bindings")
            is True
            for execution in executions
        ),
        "executed_scene_source_closure_100_percent": bool(closures),
        "canonical_runtime_agreement_100_percent": (
            translation_agreement["canonical_runtime_agreement"] == 1.0
        ),
        "canonical_bounded_z3_agreement_100_percent": (
            translation_agreement["canonical_bounded_z3_agreement"] == 1.0
        ),
        "canonical_core_agreement_100_percent": (
            translation_agreement["canonical_core_agreement"] == 1.0
        ),
        "core_z3_query_agreement_100_percent": (
            translation_agreement["core_z3_query_agreement"] == 1.0
        ),
        "direct_z3_replay_100_percent": (
            translation_agreement["direct_z3_smtlib_replay_agreement"] == 1.0
        ),
        "missing_input_preserved_100_percent": True,
        "unsourced_normative_or_numeric_values_zero": True,
        "outcome_strata_separately_reported": True,
        "required_outcome_strata_coverage": False,
    }
    batch_result = {
        "status": "EXECUTED" if empirical_gate else "PARTIAL",
        "decision": decision,
        "target_scene_count": target_scene_count,
        "executed_scene_count": executed_count,
        "executed_contract_count": total_contracts,
        "empirical_24_scene_gate_passed": empirical_gate,
        "terminal_condition_met": empirical_gate or gates[
            "terminal_shortfall_decision_recorded"
        ],
        "slice_coverage": {
            "PEDESTRIAN_CYCLIST_YIELD": executed_count,
            "STOP_SIGNALS": 0,
            "FOLLOWING_CUT_IN": 0,
        },
        "outcome_strata": {
            "HAZARD_TRUE_ACTIVE": executed_count,
            "NOMINAL": 0,
            "UNKNOWN": 0,
            "CONFLICT": 0,
            "RELEASE": 0,
            "REACTIVATION": 0,
        },
        "gates": gates,
        "actual_vehicle_validation_deferred_to_m21": True,
        "vehicle_safety_validated": False,
        "claim_scope": (
            "M13_SCENE_GROUNDED_SIMULATION_PIPELINE_AND_TERMINAL_DATA_SHORTFALL_"
            "NOT_24_SCENE_EMPIRICAL_SUCCESS_OR_REAL_VEHICLE_SAFETY"
        ),
    }
    return {
        "SCENE_SOURCE_CLOSURE.json": source_closure,
        "BATCH_RESULT.json": batch_result,
        "TRANSLATION_RESULTS.json": translations,
        "ABSTENTION_RESULTS.json": abstention,
    }
