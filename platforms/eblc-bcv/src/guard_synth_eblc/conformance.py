"""Generated finite-trace conformance between canonical EBLC and Core SMT."""

from __future__ import annotations

from itertools import product
from typing import Iterable

from .adapters.synthetic_pedestrian import TARGET, ZONE, frame, locked_translation_traces
from .elaborator import ElaborationResult, elaborate_program
from .program import EBLCProgram
from .semantics import CanonicalInterpreter
from .smt_compiler import CompiledCoreModel, compile_core_model, solve_assignment
from .types import BoundContract, ContextFrame, EpistemicKind, Fact, Truth


CONFORMANCE_VERSION = "eblc-generated-conformance-v0.1"


def _symbol_names(compiled: CompiledCoreModel) -> dict[tuple[str, int | None], str]:
    return {
        (item["declaration"], item["time"]): item["smt_symbol"]
        for item in compiled.symbol_table["symbols"]
    }


def assign_trace_inputs(
    contract: BoundContract,
    program: EBLCProgram,
    frames: tuple[ContextFrame, ...],
) -> dict[tuple[str, int | None], bool | int | float | str]:
    if not frames:
        raise ValueError("conformance trace must not be empty")
    if len(frames) > program.frames:
        raise ValueError(f"trace length {len(frames)} exceeds program frames {program.frames}")
    assignments: dict[tuple[str, int | None], bool | int | float | str] = {}
    padded = list(frames)
    last_timestamp = frames[-1].timestamp_s
    while len(padded) < program.frames:
        next_timestamp = last_timestamp + 0.1 * (len(padded) - len(frames) + 1)
        padded.append(frame(next_timestamp, Truth.FALSE, x=-2.2, speed=0.0))
    for index, sample in enumerate(padded):
        values: dict[str, bool | int | float | str] = {
            "raw_truth": sample.hazard.truth.value,
            "epistemic": sample.hazard.epistemic_kind.value,
            "timestamp": sample.timestamp_s,
            "fact_timestamp": sample.hazard.timestamp_s,
            "fact_maximum_age": sample.hazard.maximum_age_s,
            "scope_valid": sample.scope_valid,
            "unit_ok": sample.distance_unit == contract.distance_unit,
            "coordinate_ok": sample.coordinate_frame == contract.coordinate_frame,
            "target_ok": sample.target_entity_id == contract.target_entity_id and sample.zone_id == contract.zone_id,
            "ego_front_x": sample.ego_front_x_m,
            "ego_speed": sample.ego_speed_mps,
            "safe_progress": sample.safe_progress_available,
        }
        assignments.update({(name, index): value for name, value in values.items()})
    return assignments


def compare_trace(
    contract: BoundContract,
    program: EBLCProgram,
    compiled: CompiledCoreModel,
    trace_id: str,
    frames: Iterable[ContextFrame],
) -> dict[str, object]:
    samples = tuple(frames)
    interpreter = CanonicalInterpreter(contract)
    canonical: list[dict[str, object]] = []
    for sample in samples:
        step = interpreter.step(sample)
        canonical.append({
            "state": step.lifecycle.value,
            "clear_count": interpreter.clear_frames,
            "verdict": step.verdict.value,
            "entry_violation": "CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE" in step.violations,
            "speed_violation": "DYNAMIC_STOPPING_SPEED_BOUND_EXCEEDED" in step.violations,
            "deadlock_violation": "FALSE_DEADLOCK_NO_ADMISSIBLE_ACTION" in step.violations,
            "progress_allowed": step.progress_allowed,
        })
    solved = solve_assignment(compiled, assign_trace_inputs(contract, program, samples))
    names = _symbol_names(compiled)
    witness = solved["witness"] or {}
    mismatches: list[dict[str, object]] = []
    core_steps: list[dict[str, object]] = []
    if solved["status"] == "SAT":
        for index, expected in enumerate(canonical):
            actual = {
                "state": witness[names[("state", index + 1)]],
                "clear_count": witness[names[("clear_count", index + 1)]],
                "verdict": witness[names[("verdict", index)]],
                "entry_violation": witness[names[("entry_violation", index)]],
                "speed_violation": witness[names[("speed_violation", index)]],
                "deadlock_violation": witness[names[("deadlock_violation", index)]],
                "progress_allowed": witness[names[("progress_allowed", index)]],
            }
            core_steps.append(actual)
            for field, expected_value in expected.items():
                if actual[field] != expected_value:
                    mismatches.append({
                        "frame": index, "field": field,
                        "canonical": expected_value, "core_smt": actual[field],
                    })
    else:
        mismatches.append({
            "frame": None, "field": "solver_status",
            "canonical": "EXECUTABLE", "core_smt": solved["status"],
        })
    return {
        "trace_id": trace_id,
        "frame_count": len(samples),
        "solver_status": solved["status"],
        "matches": not mismatches,
        "mismatches": mismatches,
        "canonical": canonical,
        "core_smt": core_steps,
    }


def validate_conformance(
    contract: BoundContract,
    program: EBLCProgram,
    traces: dict[str, tuple[ContextFrame, ...]],
) -> dict[str, object]:
    elaborated: ElaborationResult = elaborate_program(program)
    compiled = compile_core_model(elaborated.core_model)
    records = [
        compare_trace(contract, program, compiled, trace_id, samples)
        for trace_id, samples in traces.items()
    ]
    matching_traces = sum(bool(item["matches"]) for item in records)
    frame_count = sum(int(item["frame_count"]) for item in records)
    matching_frames = 0
    for item in records:
        item_frames = int(item["frame_count"])
        if item["matches"]:
            matching_frames += item_frames
            continue
        mismatch_frames = {mismatch["frame"] for mismatch in item["mismatches"]}
        if None not in mismatch_frames:
            matching_frames += item_frames - len(mismatch_frames)
    return {
        "version": CONFORMANCE_VERSION,
        "program_id": program.program_id,
        "core_model_id": elaborated.core_model.model_id,
        "trace_count": len(records),
        "matching_traces": matching_traces,
        "trace_agreement": matching_traces / len(records) if records else 0.0,
        "frame_count": frame_count,
        "matching_frames": matching_frames,
        "frame_agreement": matching_frames / frame_count if frame_count else 0.0,
        "records": records,
        "limitations": [
            "GENERATED_FINITE_TRACE_CONFORMANCE",
            "ELABORATOR_DERIVED_FROM_CANONICAL_SPECIFICATION",
            "NOT_AN_INDEPENDENT_SAFETY_ORACLE",
        ],
    }


def generated_p0b_conformance_suite() -> dict[str, tuple[ContextFrame, ...]]:
    traces = dict(locked_translation_traces())
    truths = tuple(Truth)
    for index, sequence in enumerate(product(truths, repeat=3)):
        traces[f"truth_product_3_{index:03d}"] = tuple(
            frame(step * 0.1, truth, x=-2.2, speed=0.0)
            for step, truth in enumerate(sequence)
        )
    freshness_cases = {
        "fresh": (0.1, 0.1),
        "stale": (0.5, 0.0),
        "future": (0.5, 0.6),
    }
    for truth, epistemic, (freshness_id, (timestamp, fact_timestamp)) in product(
        truths, tuple(EpistemicKind), freshness_cases.items()
    ):
        trace_id = f"epistemic_{truth.value}_{epistemic.value}_{freshness_id}"
        traces[trace_id] = (
            frame(
                timestamp, truth, epistemic=epistemic,
                fact_timestamp_s=fact_timestamp, x=-2.2, speed=0.0,
            ),
        )
    traces.update({
        "target_mismatch": (frame(0.0, Truth.TRUE, target="synthetic-pedestrian:OTHER"),),
        "zone_mismatch": (frame(0.0, Truth.TRUE, zone="synthetic-zone:OTHER"),),
        "unit_mismatch": (frame(0.0, Truth.TRUE, distance_unit="cm"),),
        "coordinate_mismatch": (frame(0.0, Truth.TRUE, coordinate_frame="map_xy"),),
        "scope_expiry": (frame(0.0, Truth.TRUE, scope_valid=False),),
        "entry_boundary_equal": (frame(0.0, Truth.TRUE, x=-1.5, speed=0.0),),
        "entry_boundary_above": (frame(0.0, Truth.TRUE, x=-1.5 + 2e-9, speed=0.0),),
        "speed_high": (frame(0.0, Truth.TRUE, x=-12.0, speed=20.0),),
        "safe_progress_available": (frame(0.0, Truth.FALSE, x=1.0, speed=2.0, safe_progress=True),),
    })
    return traces
