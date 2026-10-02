"""Finite-trace agreement for canonical bundle composition and generated SMT."""

from __future__ import annotations

from typing import Mapping

from .bundle_elaborator import BundleElaborationResult, elaborate_bundle
from .composition import ContractEvaluation, EBLCBundle, resolve_composition
from .conformance import assign_trace_inputs
from .semantics import CanonicalInterpreter
from .smt_compiler import compile_core_model, solve_assignment
from .types import BoundContract, ContextFrame


BUNDLE_CONFORMANCE_VERSION = "eblc-bundle-conformance-v0.2"


def compare_bundle_trace(
    bundle: EBLCBundle,
    contracts: Mapping[str, BoundContract],
    traces: Mapping[str, tuple[ContextFrame, ...]],
    *,
    safe_progress_action_exists: tuple[bool, ...] | None = None,
) -> dict[str, object]:
    expected_ids = {item.contract_id for item in bundle.contracts}
    if set(contracts) != expected_ids or set(traces) != expected_ids:
        raise ValueError("bundle contract/trace coverage mismatch")
    lengths = {len(traces[item]) for item in expected_ids}
    if len(lengths) != 1 or not lengths or 0 in lengths:
        raise ValueError("all bundle traces must have the same nonzero length")
    frame_count = next(iter(lengths))
    if frame_count > bundle.frames:
        raise ValueError("bundle trace exceeds configured frame bound")
    safe = safe_progress_action_exists or tuple(False for _ in range(frame_count))
    if len(safe) != frame_count:
        raise ValueError("safe-progress sequence length mismatch")

    elaborated: BundleElaborationResult = elaborate_bundle(bundle)
    compiled = compile_core_model(elaborated.core_model)
    assignments: dict[tuple[str, int | None], bool | int | float | str] = {}
    interpreters: dict[str, CanonicalInterpreter] = {}
    for component in bundle.contracts:
        contract_id = component.contract_id
        interpreters[contract_id] = CanonicalInterpreter(contracts[contract_id])
        child_assignments = assign_trace_inputs(
            contracts[contract_id], component.program, traces[contract_id]
        )
        prefix = elaborated.elaboration_map["component_prefixes"][contract_id]
        assignments.update({(f"{prefix}{name}", time): value for (name, time), value in child_assignments.items()})
    for index in range(bundle.frames):
        assignments[("safe_progress_action_exists", index)] = (
            safe[index] if index < frame_count else False
        )

    canonical: list[dict[str, object]] = []
    for index in range(frame_count):
        evaluations: list[ContractEvaluation] = []
        for component in bundle.contracts:
            contract_id = component.contract_id
            step = interpreters[contract_id].step(traces[contract_id][index])
            evaluations.append(ContractEvaluation(
                contract_id=contract_id,
                lifecycle=step.lifecycle.value,
                verdict=step.verdict.value,
            ))
        result = resolve_composition(
            bundle, evaluations,
            safe_progress_action_exists=safe[index],
        )
        canonical.append({
            "selected_contracts": list(result.selected_contracts),
            "admissible_actions": list(result.admissible_actions),
            "verdict": result.verdict,
            "false_deadlock": result.false_deadlock,
        })

    solved = solve_assignment(compiled, assignments)
    names = {
        (item["declaration"], item["time"]): item["smt_symbol"]
        for item in compiled.symbol_table["symbols"]
    }
    witness = solved["witness"] or {}
    core_smt: list[dict[str, object]] = []
    mismatches: list[dict[str, object]] = []
    if solved["status"] == "SAT":
        for index, expected in enumerate(canonical):
            selected = [
                item.contract_id for item in bundle.contracts
                if witness[names[(f"selected__{item.contract_id}", index)]]
            ]
            allowed = [
                action for action in bundle.action_domain
                if witness[names[(f"admissible__{action}", index)]]
            ]
            actual = {
                "selected_contracts": selected,
                "admissible_actions": allowed,
                "verdict": witness[names[("composition_verdict", index)]],
                "false_deadlock": witness[names[("composition_false_deadlock", index)]],
            }
            core_smt.append(actual)
            for field, expected_value in expected.items():
                if actual[field] != expected_value:
                    mismatches.append({
                        "frame": index,
                        "field": field,
                        "canonical": expected_value,
                        "core_smt": actual[field],
                    })
    else:
        mismatches.append({
            "frame": None,
            "field": "solver_status",
            "canonical": "EXECUTABLE",
            "core_smt": solved["status"],
        })
    return {
        "version": BUNDLE_CONFORMANCE_VERSION,
        "bundle_id": bundle.bundle_id,
        "frame_count": frame_count,
        "solver_status": solved["status"],
        "matches": not mismatches,
        "mismatches": mismatches,
        "canonical": canonical,
        "core_smt": core_smt,
        "limitations": [
            "GENERATED_FINITE_TRACE_CONFORMANCE",
            "NOT_AN_INDEPENDENT_SAFETY_ORACLE",
            "NOT_A_VEHICLE_SAFETY_PROOF",
        ],
    }
