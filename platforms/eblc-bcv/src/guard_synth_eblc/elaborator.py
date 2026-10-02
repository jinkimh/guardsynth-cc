"""Elaborate a high-level EBLC program into the typed bounded Core IR.

Unlike the earlier hand-authored Core fixture, this module owns the reusable
expansion of freshness, epistemic failure, lifecycle, verdict, invariant,
dynamic stopping-bound, and progress semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .core_ir import CoreModel, parse_core_model
from .derivation import elaborate_derivation
from .program import EBLCProgram


ELABORATOR_VERSION = "eblc-program-elaborator-v0.2"
LIFECYCLE = ("INACTIVE", "CANDIDATE", "ACTIVE", "MAINTAINED", "RELEASED", "REACTIVATED", "EXPIRED")
TRUTH = ("TRUE", "FALSE", "UNKNOWN", "CONFLICT")
EPISTEMIC = ("OBSERVED", "PREDICTED", "DERIVED", "CLAIMED")
VERDICT = ("VALIDATED", "REVIEW_REQUIRED", "UNSUPPORTED", "CONFLICT")


@dataclass(frozen=True, slots=True)
class ElaborationResult:
    core_model: CoreModel
    core_document: dict[str, Any]
    elaboration_map: dict[str, Any]


def _lit(sort: str, value: Any, *, enum: str | None = None, unit: str | None = None, frame: str | None = None) -> dict[str, Any]:
    return {"op": "literal", "sort": sort, "value": value, "enum_name": enum, "unit": unit, "frame": frame}


def _var(name: str, offset: int = 0) -> dict[str, Any]:
    return {"op": "var", "name": name, "offset": offset}


def _unary(op: str, arg: dict[str, Any]) -> dict[str, Any]:
    return {"op": op, "arg": arg}


def _nary(op: str, *args: dict[str, Any]) -> dict[str, Any]:
    return {"op": op, "args": list(args)}


def _binary(op: str, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {"op": op, "left": left, "right": right}


def _ite(condition: dict[str, Any], then: dict[str, Any], otherwise: dict[str, Any]) -> dict[str, Any]:
    return {"op": "ite", "condition": condition, "then": then, "else": otherwise}


def _enum(domain: str, value: str) -> dict[str, Any]:
    return _lit("ENUM", value, enum=domain)


def _eq(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return _binary("eq", left, right)


def _state(value: str, offset: int = 0) -> dict[str, Any]:
    return _eq(_var("state", offset), _enum("Lifecycle", value))


def _truth(value: str, *, effective: bool = True) -> dict[str, Any]:
    return _eq(_var("effective_truth" if effective else "raw_truth"), _enum("Truth", value))


def _live(expression: dict[str, Any]) -> dict[str, Any]:
    return _nary("or", *(_eq(expression, _enum("Lifecycle", value)) for value in ("ACTIVE", "MAINTAINED", "REACTIVATED")))


def _declaration(
    name: str,
    sort: str,
    refs: list[str],
    *,
    time_varying: bool = True,
    enum_name: str | None = None,
    enum_values: tuple[str, ...] = (),
    unit: str | None = None,
    frame: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name, "sort": sort, "time_varying": time_varying,
        "enum_name": enum_name, "enum_values": list(enum_values),
        "unit": unit, "frame": frame, "source_refs": refs,
    }


def _clause(
    clause_id: str,
    kind: str,
    enforcement: str,
    formula: dict[str, Any],
    refs: list[str],
    description: str,
) -> dict[str, Any]:
    return {
        "id": clause_id, "kind": kind, "enforcement": enforcement,
        "formula": formula, "source_refs": refs, "description": description,
    }


def elaborate_program(program: EBLCProgram) -> ElaborationResult:
    raw = program.raw
    binding = raw["binding"]
    predicate = raw["predicate"]
    lifecycle = raw["lifecycle"]
    constraints = raw["constraints"]
    rule_refs = list(lifecycle["evidence_refs"])
    predicate_refs = list(predicate["evidence_refs"])
    oracle_refs = [
        ref for ref in program.source_refs
        if "CONFORMANCE-ORACLE" in ref or "QUERY-ORACLE" in ref
    ] or rule_refs
    combined_refs = list(dict.fromkeys(rule_refs + predicate_refs))
    frames = program.frames
    horizon = frames + 1
    frame = binding["coordinate_frame"]
    typed_derivation = program.typed_derivation

    declarations = [
        _declaration("state", "ENUM", rule_refs, enum_name="Lifecycle", enum_values=LIFECYCLE),
        _declaration("clear_count", "INT", rule_refs, unit="1"),
        _declaration("raw_truth", "ENUM", predicate_refs, enum_name="Truth", enum_values=TRUTH),
        _declaration("epistemic", "ENUM", predicate_refs, enum_name="Epistemic", enum_values=EPISTEMIC),
        _declaration("timestamp", "REAL", predicate_refs, unit="s"),
        _declaration("fact_timestamp", "REAL", predicate_refs, unit="s"),
        _declaration("fact_maximum_age", "REAL", predicate_refs, unit="s"),
        _declaration("scope_valid", "BOOL", rule_refs),
        _declaration("unit_ok", "BOOL", list(binding["evidence_refs"])),
        _declaration("coordinate_ok", "BOOL", list(binding["evidence_refs"])),
        _declaration("target_ok", "BOOL", list(binding["evidence_refs"])),
        _declaration("ego_front_x", "REAL", oracle_refs, unit="m", frame=frame),
        _declaration("ego_speed", "REAL", oracle_refs, unit="m/s", frame=frame),
        _declaration("safe_progress", "BOOL", oracle_refs),
        _declaration("effective_truth", "ENUM", combined_refs, enum_name="Truth", enum_values=TRUTH),
        _declaration("verdict", "ENUM", combined_refs, enum_name="Verdict", enum_values=VERDICT),
        _declaration("entry_violation", "BOOL", combined_refs),
        _declaration("speed_violation", "BOOL", combined_refs),
        _declaration("deadlock_violation", "BOOL", combined_refs),
        _declaration("progress_allowed", "BOOL", combined_refs),
    ]

    quantity_names = (
        ("stop_position",) if typed_derivation is None else ()
    ) + (
        "position_uncertainty", "response_time", "deceleration",
        "position_epsilon", "speed_epsilon", "time_epsilon",
    )
    for name in quantity_names:
        quantity = constraints[name]
        declarations.append(_declaration(
            name, "REAL", list(quantity["evidence_refs"]), time_varying=False,
            unit=quantity["unit"], frame=quantity["frame"],
        ))
    if typed_derivation is not None:
        for output in typed_derivation.outputs:
            declarations.append(_declaration(
                output.target_declaration,
                output.sort,
                list(output.evidence_refs),
                time_varying=output.time_varying,
                unit=output.unit,
                frame=output.frame,
            ))
    declarations.extend([
        _declaration("predicate_maximum_age", "REAL", predicate_refs, time_varying=False, unit="s"),
        _declaration("release_threshold", "INT", rule_refs, time_varying=False, unit="1"),
    ])

    clauses: list[dict[str, Any]] = [
        _clause("initial_state", "LIFECYCLE", "INITIAL", _eq(_var("state"), _enum("Lifecycle", lifecycle["initial_state"])), rule_refs, "Initial lifecycle state from the high-level policy."),
        _clause("initial_clear_count", "LIFECYCLE", "INITIAL", _eq(_var("clear_count"), _lit("INT", 0, unit="1")), rule_refs, "Initial consecutive-clear counter."),
    ]
    for name in quantity_names:
        quantity = constraints[name]
        clauses.append(_clause(
            f"bind_{name}", "BOUND", "INITIAL",
            _eq(_var(name), _lit("REAL", quantity["value"], unit=quantity["unit"], frame=quantity["frame"])),
            list(quantity["evidence_refs"]), f"Evidence-bound high-level quantity: {name}.",
        ))
    clauses.extend([
        _clause("bind_predicate_maximum_age", "BOUND", "INITIAL", _eq(_var("predicate_maximum_age"), _lit("REAL", predicate["maximum_age_s"], unit="s")), predicate_refs, "Predicate freshness contract."),
        _clause("bind_release_threshold", "RELEASE", "INITIAL", _eq(_var("release_threshold"), _lit("INT", lifecycle["release_clear_frames"], unit="1")), rule_refs, "Consecutive clear frames required for release."),
        _clause("input_timestamp_nonnegative", "ASSUMPTION", "EACH_FRAME", _binary("ge", _var("timestamp"), _lit("REAL", 0.0, unit="s")), oracle_refs, "Finite-trace conformance input domain."),
        _clause("input_fact_timestamp_nonnegative", "ASSUMPTION", "EACH_FRAME", _binary("ge", _var("fact_timestamp"), _lit("REAL", 0.0, unit="s")), oracle_refs, "Finite-trace conformance input domain."),
        _clause("input_fact_age_nonnegative", "ASSUMPTION", "EACH_FRAME", _binary("ge", _var("fact_maximum_age"), _lit("REAL", 0.0, unit="s")), oracle_refs, "Finite-trace conformance input domain."),
        _clause("input_speed_nonnegative", "ASSUMPTION", "EACH_FRAME", _binary("ge", _var("ego_speed"), _lit("REAL", 0.0, unit="m/s", frame=frame)), oracle_refs, "Finite-trace conformance input domain."),
    ])

    age = _binary("sub", _var("timestamp"), _var("fact_timestamp"))
    freshness_limit = _ite(
        _binary("le", _var("fact_maximum_age"), _var("predicate_maximum_age")),
        _var("fact_maximum_age"), _var("predicate_maximum_age"),
    )
    future = _binary("lt", age, _unary("neg", _var("time_epsilon")))
    stale = _binary("gt", age, _binary("add", freshness_limit, _var("time_epsilon")))
    disallowed_epistemic = _nary(
        "or", *(
            _eq(_var("epistemic"), _enum("Epistemic", value))
            for value in EPISTEMIC
            if value not in predicate["allowed_epistemic"]
        ),
    )
    epistemic_failure = _nary("or", future, stale, disallowed_epistemic)
    effective_formula = _eq(
        _var("effective_truth"),
        _ite(epistemic_failure, _enum("Truth", predicate["failure_value"]), _var("raw_truth")),
    )
    clauses.append(_clause(
        "effective_truth_from_freshness_and_epistemic", "ACTIVATION", "EACH_FRAME",
        effective_formula, combined_refs,
        "Future, stale, or policy-disallowed epistemic evidence fails to UNKNOWN; otherwise raw truth is preserved.",
    ))

    expiry_terms = [_unary("not", _var("scope_valid"))]
    if lifecycle["expiry_timestamp_s"] is not None:
        expiry_terms.append(_binary(
            "ge", _var("timestamp"),
            _lit("REAL", lifecycle["expiry_timestamp_s"], unit="s"),
        ))
    expiry = _nary("or", *expiry_terms)
    supported = _nary("and", _var("unit_ok"), _var("coordinate_ok"))
    scoped_state = _ite(expiry, _enum("Lifecycle", "EXPIRED"), _var("state"))
    scoped_clear = _ite(expiry, _lit("INT", 0, unit="1"), _var("clear_count"))
    always_activation = _nary(
        "and", _lit("BOOL", bool(lifecycle["always_active"])),
        _unary("not", _live(scoped_state)),
    )
    base_state = _ite(always_activation, _enum("Lifecycle", "ACTIVE"), scoped_state)
    base_clear = _ite(always_activation, _lit("INT", 0, unit="1"), scoped_clear)

    policy_truth = _var("effective_truth")
    if lifecycle["unknown_policy"] == "AS_FALSE":
        policy_truth = _ite(_truth("UNKNOWN"), _enum("Truth", "FALSE"), _var("effective_truth"))
    elif lifecycle["unknown_policy"] == "AS_TRUE":
        policy_truth = _ite(_truth("UNKNOWN"), _enum("Truth", "TRUE"), _var("effective_truth"))

    policy_is = lambda value: _eq(policy_truth, _enum("Truth", value))
    inactive = _nary("or", _eq(base_state, _enum("Lifecycle", "INACTIVE")), _eq(base_state, _enum("Lifecycle", "CANDIDATE")))
    released = _eq(base_state, _enum("Lifecycle", "RELEASED"))
    live = _live(base_state)
    incremented = _binary("add", base_clear, _lit("INT", 1, unit="1"))
    release_now = _nary(
        "and", _lit("BOOL", bool(lifecycle["release_enabled"])),
        _binary("ge", incremented, _var("release_threshold")),
    )
    inactive_next = _ite(policy_is("TRUE"), _enum("Lifecycle", "ACTIVE"), _ite(policy_is("FALSE"), _enum("Lifecycle", "INACTIVE"), _enum("Lifecycle", "CANDIDATE")))
    released_next = _ite(
        _nary("and", policy_is("TRUE"), _lit("BOOL", bool(lifecycle["reactivation_enabled"]))),
        _enum("Lifecycle", "REACTIVATED"), base_state,
    )
    live_unknown_next = _enum("Lifecycle", "MAINTAINED") if lifecycle["fallback_approved"] else base_state
    live_next = _ite(
        policy_is("TRUE"), _enum("Lifecycle", "MAINTAINED"),
        _ite(policy_is("FALSE"), _ite(release_now, _enum("Lifecycle", "RELEASED"), _enum("Lifecycle", "MAINTAINED")), live_unknown_next),
    )
    transitioned_state = _ite(inactive, inactive_next, _ite(released, released_next, _ite(live, live_next, base_state)))
    next_state = _ite(
        supported,
        _ite(_eq(scoped_state, _enum("Lifecycle", "EXPIRED")), scoped_state, _ite(_truth("CONFLICT"), base_state, transitioned_state)),
        scoped_state,
    )

    inactive_clear = _ite(_nary("or", policy_is("TRUE"), policy_is("FALSE")), _lit("INT", 0, unit="1"), base_clear)
    released_clear = _ite(
        _nary("and", policy_is("TRUE"), _lit("BOOL", bool(lifecycle["reactivation_enabled"]))),
        _lit("INT", 0, unit="1"), base_clear,
    )
    live_clear = _ite(policy_is("TRUE"), _lit("INT", 0, unit="1"), _ite(policy_is("FALSE"), incremented, _lit("INT", 0, unit="1")))
    transitioned_clear = _ite(inactive, inactive_clear, _ite(released, released_clear, _ite(live, live_clear, base_clear)))
    next_clear = _ite(
        supported,
        _ite(_eq(scoped_state, _enum("Lifecycle", "EXPIRED")), scoped_clear, _ite(_truth("CONFLICT"), base_clear, transitioned_clear)),
        scoped_clear,
    )
    clauses.extend([
        _clause("generated_lifecycle_transition", "LIFECYCLE", "EACH_TRANSITION", _eq(_var("state", 1), next_state), rule_refs, "Generated activation, maintenance, release, reactivation, expiry, and fallback transition."),
        _clause("generated_clear_counter_transition", "RELEASE", "EACH_TRANSITION", _eq(_var("clear_count", 1), next_clear), rule_refs, "Generated consecutive-clear counter transition."),
    ])

    post_live = _live(_var("state", 1))
    unknown_after_policy = _eq(policy_truth, _enum("Truth", "UNKNOWN"))
    unknown_precondition = _nary("and", inactive, unknown_after_policy)
    unknown_live_without_fallback = _nary(
        "and", live, unknown_after_policy,
        _lit("BOOL", not bool(lifecycle["fallback_approved"])),
    )
    as_true_review = _nary(
        "and", _truth("UNKNOWN"),
        _lit("BOOL", lifecycle["unknown_policy"] == "AS_TRUE"),
    )
    review = _nary(
        "or", epistemic_failure, _unary("not", _var("target_ok")),
        unknown_precondition, unknown_live_without_fallback, as_true_review,
    )
    verdict_value = _ite(
        _unary("not", supported), _enum("Verdict", "UNSUPPORTED"),
        _ite(_truth("CONFLICT"), _enum("Verdict", "CONFLICT"), _ite(review, _enum("Verdict", "REVIEW_REQUIRED"), _enum("Verdict", "VALIDATED"))),
    )
    clauses.append(_clause(
        "generated_verdict", "FALLBACK", "EACH_TRANSITION",
        _eq(_var("verdict"), verdict_value), combined_refs,
        "Generated fail-closed per-frame verdict with conflict and review precedence.",
    ))

    entry_condition = _nary(
        "and", supported, _lit("BOOL", bool(constraints["enforce_invariant"])), post_live,
        _var("target_ok"),
        _binary("gt", _var("ego_front_x"), _binary("add", _var("stop_position"), _var("position_epsilon"))),
    )
    available = _binary("sub", _binary("sub", _var("stop_position"), _var("ego_front_x")), _var("position_uncertainty"))
    adjusted_speed = _binary("sub", _var("ego_speed"), _var("speed_epsilon"))
    stop_distance = (
        _var("stopping_distance")
        if typed_derivation is not None
        else _binary(
            "add", _binary("mul", adjusted_speed, _var("response_time")),
            _binary("div", _binary("mul", adjusted_speed, adjusted_speed), _binary("mul", _lit("REAL", 2.0, unit="1"), _var("deceleration"))),
        )
    )
    zero_distance = _lit("REAL", 0.0, unit="m", frame=frame)
    zero_speed = _lit("REAL", 0.0, unit="m/s", frame=frame)
    speed_condition = _nary(
        "and", supported, _var("target_ok"),
        _lit("BOOL", bool(constraints["enforce_invariant"])), post_live,
        _nary("or",
            _nary("and", _binary("le", available, zero_distance), _binary("gt", _var("ego_speed"), _var("speed_epsilon"))),
            _nary("and", _binary("gt", available, zero_distance), _binary("gt", adjusted_speed, zero_speed), _binary("gt", stop_distance, available)),
        ),
    )
    progress_value = _unary("not", post_live)
    if constraints["force_deadlock"]:
        progress_value = _ite(_var("safe_progress"), _lit("BOOL", False), progress_value)
    progress_value = _ite(supported, progress_value, _lit("BOOL", False))
    deadlock_condition = _nary(
        "and", supported, _lit("BOOL", bool(constraints["force_deadlock"])),
        _var("safe_progress"),
    )
    clauses.extend([
        _clause("generated_entry_violation", "INVARIANT", "EACH_TRANSITION", _eq(_var("entry_violation"), entry_condition), combined_refs, "Generated stop-position violation predicate."),
        _clause("generated_speed_violation", "BOUND", "EACH_TRANSITION", _eq(_var("speed_violation"), speed_condition), combined_refs, "Generated dynamic stopping-bound violation predicate."),
        _clause("generated_deadlock_violation", "PROGRESS", "EACH_TRANSITION", _eq(_var("deadlock_violation"), deadlock_condition), combined_refs, "Generated false-deadlock violation predicate."),
        _clause("generated_progress_permission", "PROGRESS", "EACH_TRANSITION", _eq(_var("progress_allowed"), progress_value), combined_refs, "Generated progress permission from post-step lifecycle."),
    ])

    core_document = {
        "grammar_version": "eblc-core-v0.1",
        "model_id": f"{program.program_id}_core",
        "horizon": horizon,
        "declarations": declarations,
        "clauses": clauses,
        "queries": [{
            "id": "generated_model_satisfiable",
            "formula": _lit("BOOL", True),
            "expected": "SAT",
            "classification": "CONSISTENCY",
            "source_refs": oracle_refs,
            "description": "The elaborated model has at least one bounded execution.",
        }],
        "source_refs": list(program.source_refs),
        "claim_scope": program.claim_scope,
    }
    derivation_map = None
    if typed_derivation is None:
        core_model = parse_core_model(core_document)
    else:
        derived = elaborate_derivation(
            typed_derivation,
            base_core_document=core_document,
        )
        core_model = derived.core_model
        core_document = derived.core_document
        derivation_map = derived.derivation_map
    elaboration_map = {
        "program_id": program.program_id,
        "program_version": raw["program_version"],
        "elaborator_version": ELABORATOR_VERSION,
        "core_model_id": core_model.model_id,
        "frames": frames,
        "core_horizon": horizon,
        "generated_from": {
            "binding": ["unit_ok", "coordinate_ok", "target_ok"],
            "predicate": ["effective_truth_from_freshness_and_epistemic"],
            "lifecycle": ["generated_lifecycle_transition", "generated_clear_counter_transition"],
            "constraints": ["generated_entry_violation", "generated_speed_violation", "generated_deadlock_violation", "generated_progress_permission"],
            "verdict": ["generated_verdict"],
            "derivation_nodes": (
                [node.node_id for node in typed_derivation.nodes]
                if typed_derivation is not None
                else [node["node_id"] for node in raw["derivation_dag"]]
            ),
            "priority": {"class": raw["priority"]["class"], "overrides": raw["priority"]["overrides"], "compiled_as_scalar_weight": False},
        },
        "typed_derivation": derivation_map,
        "limitations": [
            "SINGLE_BOUND_CONTRACT",
            "BOUNDED_DISCRETE_TIME",
            "PRIORITY_PRESERVED_NOT_COMPOSED",
        ] + (
            [] if typed_derivation is not None
            else ["DERIVATION_PROVENANCE_PRESERVED_NOT_SYMBOLICALLY_REPLAYED"]
        ),
    }
    return ElaborationResult(core_model, core_document, elaboration_map)
