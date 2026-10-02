#!/usr/bin/env python3
"""Run the synthetic EBLC/BCV execution pilot and print a JSON report."""

from __future__ import annotations

import json

from .pilot import (
    PILOT_PROFILE,
    SceneFrame,
    Truth,
    run_bcv_mutation_pilot,
    run_trace,
    safe_release_reactivation_trace,
    synthesize_contract,
    unknown_fallback_trace,
    unsafe_entry_trace,
)


def _trace_summary(result):
    return {
        "accepted": result.accepted,
        "violations": list(result.violations),
        "lifecycle": [step.lifecycle.value for step in result.steps],
        "diagnostics": [
            diagnostic for step in result.steps for diagnostic in step.diagnostics
        ],
        "max_safe_speed_mps": [
            None
            if step.max_safe_speed_mps is None
            else round(step.max_safe_speed_mps, 3)
            for step in result.steps
        ],
    }


def main() -> None:
    initial = SceneFrame(0.0, -12.0, 6.0, 0.0, Truth.TRUE)
    synthesis = synthesize_contract(
        "횡단보도 보행자에게 양보한 뒤 진행한다.",
        initial,
        PILOT_PROFILE,
    )
    if synthesis.contract is None:
        raise RuntimeError(f"pilot synthesis failed: {synthesis.reason}")
    contract = synthesis.contract

    safe = run_trace(contract, safe_release_reactivation_trace())
    unsafe = run_trace(contract, unsafe_entry_trace())
    unknown = run_trace(contract, unknown_fallback_trace())
    bcv = run_bcv_mutation_pilot(contract)
    missing_profile = synthesize_contract(
        "횡단보도 보행자에게 양보한다.", initial, None
    )
    coc_only = synthesize_contract(
        "보행자에게 양보한다.",
        SceneFrame(0.0, -12.0, 6.0, 0.0, Truth.UNKNOWN),
        PILOT_PROFILE,
    )

    report = {
        "scope": "SYNTHETIC_MECHANISM_PILOT_NOT_REAL_VEHICLE_SAFETY",
        "synthesis": {
            "verdict": synthesis.verdict.value,
            "reason": synthesis.reason,
            "candidates": list(synthesis.candidates),
            "contract_id": contract.contract_id,
            "rule_id": contract.rule_id,
            "target": contract.target,
            "stop_position_x_m": contract.stop_position_x_m,
            "evidence_refs": list(contract.evidence_refs),
            "derivation": contract.derivation,
        },
        "execution": {
            "safe_release_reactivation": _trace_summary(safe),
            "unsafe_entry": _trace_summary(unsafe),
            "unknown_fallback": _trace_summary(unknown),
        },
        "selective_status": {
            "missing_vehicle_profile": missing_profile.verdict.value,
            "coc_claim_without_observation": coc_only.verdict.value,
        },
        "bcv_mutation": {
            "correct_accepts_safe_trace": bcv.correct_accepts_safe_trace,
            "correct_rejects_unsafe_trace": bcv.correct_rejects_unsafe_trace,
            "underconstraint_witness_found": bcv.underconstraint_witness_found,
            "overconstraint_witness_found": bcv.overconstraint_witness_found,
            "passed": bcv.passed,
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

