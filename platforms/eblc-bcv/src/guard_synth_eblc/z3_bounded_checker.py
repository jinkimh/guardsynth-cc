"""Actual bounded Z3 encoding for EBLC lifecycle replay and queries.

The canonical interpreter remains the semantic source of truth. This target
independently encodes fixed finite traces as Z3 variables and constraints,
then reconstructs lifecycle, verdict, and violations from the solver model.
When Z3 is unavailable, the explicitly named finite-state enumerator is used
and the result is not labelled SMT.
"""

from __future__ import annotations

from math import isfinite, sqrt
from typing import Any, Iterable

from .finite_state_enumerator import enumerator_queries, run_enumerator_target
from .types import BoundContract, ContextFrame, EpistemicKind, Lifecycle, MonitorStep, TraceResult, Truth, Verdict


try:
    import z3  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised only without optional solver
    z3 = None


ENGINE = "Z3_BOUNDED_SMT" if z3 is not None else "EXHAUSTIVE_FINITE_STATE_ENUMERATOR"
ENGINE_VERSION = z3.get_version_string() if z3 is not None else "deterministic-v0.1"
ACTUAL_SOLVER_ENCODING = z3 is not None
ENCODING_VERSION = "eblc-z3-bounded-v0.1"
_SOLVER_CONSTRUCTIONS = 0
_EPSILON = 1e-9

_STATE_CODE = {
    Lifecycle.INACTIVE: 0,
    Lifecycle.CANDIDATE: 1,
    Lifecycle.ACTIVE: 2,
    Lifecycle.MAINTAINED: 3,
    Lifecycle.RELEASED: 4,
    Lifecycle.REACTIVATED: 5,
    Lifecycle.EXPIRED: 6,
}
_STATE_FROM_CODE = {value: key for key, value in _STATE_CODE.items()}
_TRUTH_CODE = {Truth.TRUE: 0, Truth.FALSE: 1, Truth.UNKNOWN: 2, Truth.CONFLICT: 3}
_VERDICT_CODE = {Verdict.VALIDATED: 0, Verdict.REVIEW_REQUIRED: 1, Verdict.UNSUPPORTED: 2, Verdict.CONFLICT: 3}
_VERDICT_FROM_CODE = {value: key for key, value in _VERDICT_CODE.items()}
_LIVE_CODES = tuple(_STATE_CODE[item] for item in (Lifecycle.ACTIVE, Lifecycle.MAINTAINED, Lifecycle.REACTIVATED))


def _z3_input_error(contract: BoundContract, samples: tuple[ContextFrame, ...]) -> str | None:
    contract_values = (
        contract.zone_entry_x_m,
        contract.stop_position_x_m,
        contract.stop_margin_m,
        contract.predicate_maximum_age_s,
        contract.maximum_service_deceleration_mps2,
        contract.response_time_s,
        contract.position_uncertainty_m,
    )
    if not all(isfinite(value) for value in contract_values):
        return "NONFINITE_BOUND_CONTRACT"
    if (
        contract.stop_margin_m < 0
        or contract.predicate_maximum_age_s < 0
        or contract.maximum_service_deceleration_mps2 <= 0
        or contract.response_time_s < 0
        or contract.position_uncertainty_m < 0
        or contract.release_clear_frames < 1
    ):
        return "INVALID_BOUND_CONTRACT_RANGE"
    if contract.expiry_timestamp_s is not None and not isfinite(contract.expiry_timestamp_s):
        return "NONFINITE_BOUND_CONTRACT"
    if not samples:
        return "EMPTY_TRACE"
    previous: float | None = None
    for frame in samples:
        values = (
            frame.timestamp_s,
            frame.hazard.timestamp_s,
            frame.hazard.maximum_age_s,
            frame.ego_front_x_m,
            frame.ego_speed_mps,
            frame.zone_entry_x_m,
        )
        if not all(isfinite(value) for value in values):
            return "NONFINITE_SCENE_VALUE"
        if (
            frame.timestamp_s < 0
            or frame.hazard.timestamp_s < 0
            or frame.hazard.maximum_age_s < 0
            or frame.ego_speed_mps < 0
        ):
            return "INVALID_SCENE_NUMERIC_RANGE"
        if previous is not None and frame.timestamp_s < previous - _EPSILON:
            return "NONMONOTONIC_TIMESTAMPS"
        previous = frame.timestamp_s
    return None


def _new_solver():
    global _SOLVER_CONSTRUCTIONS
    if z3 is None:
        raise RuntimeError("Z3 solver is unavailable")
    _SOLVER_CONSTRUCTIONS += 1
    return z3.Solver()


def solver_construction_count() -> int:
    return _SOLVER_CONSTRUCTIONS


def _real(value: float | int):
    return z3.RealVal(str(value))


def _is_live(state):
    return z3.Or(*[state == code for code in _LIVE_CODES])


def _policy_truth(effective_truth, contract: BoundContract):
    if contract.unknown_policy == "AS_FALSE":
        return z3.If(effective_truth == _TRUTH_CODE[Truth.UNKNOWN], _TRUTH_CODE[Truth.FALSE], effective_truth)
    if contract.unknown_policy == "AS_TRUE":
        return z3.If(effective_truth == _TRUTH_CODE[Truth.UNKNOWN], _TRUTH_CODE[Truth.TRUE], effective_truth)
    return effective_truth


def _transition_terms(pre_state, pre_clear, effective_truth, contract: BoundContract):
    always_activates = z3.And(z3.BoolVal(contract.always_active), z3.Not(_is_live(pre_state)))
    state = z3.If(always_activates, _STATE_CODE[Lifecycle.ACTIVE], pre_state)
    clear = z3.If(always_activates, 0, pre_clear)
    reduced = _policy_truth(effective_truth, contract)

    inactive_or_candidate = z3.Or(
        state == _STATE_CODE[Lifecycle.INACTIVE],
        state == _STATE_CODE[Lifecycle.CANDIDATE],
    )
    next_from_inactive = z3.If(
        reduced == _TRUTH_CODE[Truth.TRUE],
        _STATE_CODE[Lifecycle.ACTIVE],
        z3.If(reduced == _TRUTH_CODE[Truth.FALSE], _STATE_CODE[Lifecycle.INACTIVE], _STATE_CODE[Lifecycle.CANDIDATE]),
    )
    clear_from_inactive = z3.If(
        z3.Or(reduced == _TRUTH_CODE[Truth.TRUE], reduced == _TRUTH_CODE[Truth.FALSE]),
        0,
        clear,
    )

    released = state == _STATE_CODE[Lifecycle.RELEASED]
    reactivate = z3.And(reduced == _TRUTH_CODE[Truth.TRUE], z3.BoolVal(contract.reactivation_enabled))
    next_from_released = z3.If(reactivate, _STATE_CODE[Lifecycle.REACTIVATED], state)
    clear_from_released = z3.If(reactivate, 0, clear)

    live = _is_live(state)
    incremented_clear = clear + 1
    release_now = z3.And(
        z3.BoolVal(contract.release_enabled),
        incremented_clear >= contract.release_clear_frames,
    )
    next_from_live = z3.If(
        reduced == _TRUTH_CODE[Truth.TRUE],
        _STATE_CODE[Lifecycle.MAINTAINED],
        z3.If(
            reduced == _TRUTH_CODE[Truth.FALSE],
            z3.If(release_now, _STATE_CODE[Lifecycle.RELEASED], _STATE_CODE[Lifecycle.MAINTAINED]),
            z3.If(z3.BoolVal(contract.fallback_approved), _STATE_CODE[Lifecycle.MAINTAINED], state),
        ),
    )
    clear_from_live = z3.If(
        reduced == _TRUTH_CODE[Truth.TRUE],
        0,
        z3.If(reduced == _TRUTH_CODE[Truth.FALSE], incremented_clear, 0),
    )

    transitioned_state = z3.If(
        inactive_or_candidate,
        next_from_inactive,
        z3.If(released, next_from_released, z3.If(live, next_from_live, state)),
    )
    transitioned_clear = z3.If(
        inactive_or_candidate,
        clear_from_inactive,
        z3.If(released, clear_from_released, z3.If(live, clear_from_live, clear)),
    )
    conflict = effective_truth == _TRUTH_CODE[Truth.CONFLICT]
    return (
        z3.If(conflict, state, transitioned_state),
        z3.If(conflict, clear, transitioned_clear),
        state,
        reduced,
    )


def _bool(model, expression) -> bool:
    return z3.is_true(model.eval(expression, model_completion=True))


def _int(model, expression) -> int:
    return model.eval(expression, model_completion=True).as_long()


def _trace_verdict(steps: tuple[MonitorStep, ...]) -> Verdict:
    statuses = {step.verdict for step in steps}
    for candidate in (Verdict.CONFLICT, Verdict.UNSUPPORTED, Verdict.REVIEW_REQUIRED):
        if candidate in statuses:
            return candidate
    return Verdict.VALIDATED


def _maximum_speed(contract: BoundContract, frame: ContextFrame) -> float:
    available = contract.stop_position_x_m - frame.ego_front_x_m - contract.position_uncertainty_m
    if available <= 0:
        return 0.0
    deceleration = contract.maximum_service_deceleration_mps2
    response = contract.response_time_s
    return max(0.0, -deceleration * response + sqrt((deceleration * response) ** 2 + 2.0 * deceleration * available))


def run_bounded_target(contract: BoundContract, frames: Iterable[ContextFrame]) -> TraceResult:
    if z3 is None:
        return run_enumerator_target(contract, frames)

    samples = tuple(frames)
    input_error = _z3_input_error(contract, samples)
    if input_error is not None:
        return TraceResult(False, Verdict.UNSUPPORTED, (), (), (input_error,))
    solver = _new_solver()
    states = [z3.Int(f"eblc_state_{index}") for index in range(len(samples) + 1)]
    clears = [z3.Int(f"eblc_clear_{index}") for index in range(len(samples) + 1)]
    solver.add(states[0] == _STATE_CODE[Lifecycle.INACTIVE], clears[0] == 0)
    encoded: list[dict[str, Any]] = []

    for index, frame in enumerate(samples):
        numeric_ok_value = all(isfinite(value) for value in (
            frame.timestamp_s,
            frame.hazard.timestamp_s,
            frame.hazard.maximum_age_s,
            frame.ego_front_x_m,
            frame.ego_speed_mps,
            frame.zone_entry_x_m,
        ))
        safe_timestamp = frame.timestamp_s if isfinite(frame.timestamp_s) else 0.0
        safe_fact_timestamp = frame.hazard.timestamp_s if isfinite(frame.hazard.timestamp_s) else 0.0
        safe_fact_max_age = frame.hazard.maximum_age_s if isfinite(frame.hazard.maximum_age_s) else 0.0
        safe_ego_x = frame.ego_front_x_m if isfinite(frame.ego_front_x_m) else 0.0
        safe_ego_speed = frame.ego_speed_mps if isfinite(frame.ego_speed_mps) else 0.0
        timestamp = z3.Real(f"eblc_timestamp_{index}")
        fact_timestamp = z3.Real(f"eblc_fact_timestamp_{index}")
        fact_max_age = z3.Real(f"eblc_fact_max_age_{index}")
        ego_x = z3.Real(f"eblc_ego_x_{index}")
        ego_speed = z3.Real(f"eblc_ego_speed_{index}")
        raw_truth = z3.Int(f"eblc_raw_truth_{index}")
        scope_valid = z3.Bool(f"eblc_scope_valid_{index}")
        unit_ok = z3.Bool(f"eblc_unit_ok_{index}")
        coordinate_ok = z3.Bool(f"eblc_coordinate_ok_{index}")
        numeric_ok = z3.Bool(f"eblc_numeric_ok_{index}")
        target_ok = z3.Bool(f"eblc_target_ok_{index}")
        claimed = z3.Bool(f"eblc_claimed_{index}")
        safe_progress = z3.Bool(f"eblc_safe_progress_{index}")
        solver.add(
            timestamp == _real(safe_timestamp),
            fact_timestamp == _real(safe_fact_timestamp),
            fact_max_age == _real(safe_fact_max_age),
            ego_x == _real(safe_ego_x),
            ego_speed == _real(safe_ego_speed),
            raw_truth == _TRUTH_CODE[frame.hazard.truth],
            scope_valid == frame.scope_valid,
            unit_ok == (frame.distance_unit == contract.distance_unit),
            coordinate_ok == (frame.coordinate_frame == contract.coordinate_frame),
            numeric_ok == numeric_ok_value,
            target_ok == (frame.target_entity_id == contract.target_entity_id and frame.zone_id == contract.zone_id),
            claimed == (frame.hazard.epistemic_kind is EpistemicKind.CLAIMED),
            safe_progress == frame.safe_progress_available,
        )

        age = timestamp - fact_timestamp
        freshness_limit = z3.If(fact_max_age <= _real(contract.predicate_maximum_age_s), fact_max_age, _real(contract.predicate_maximum_age_s))
        future = age < -_real(_EPSILON)
        stale = age > freshness_limit + _real(_EPSILON)
        effective_truth = z3.Int(f"eblc_effective_truth_{index}")
        solver.add(effective_truth == z3.If(z3.Or(future, stale, claimed), _TRUTH_CODE[Truth.UNKNOWN], raw_truth))

        expired_now = z3.Not(scope_valid)
        if contract.expiry_timestamp_s is not None:
            expired_now = z3.Or(expired_now, timestamp >= _real(contract.expiry_timestamp_s))
        base_state = z3.If(expired_now, _STATE_CODE[Lifecycle.EXPIRED], states[index])
        base_clear = z3.If(expired_now, 0, clears[index])
        supported = z3.And(unit_ok, coordinate_ok, numeric_ok)
        can_advance = z3.And(supported, base_state != _STATE_CODE[Lifecycle.EXPIRED])
        transitioned_state, transitioned_clear, working_state, reduced_truth = _transition_terms(base_state, base_clear, effective_truth, contract)
        solver.add(
            states[index + 1] == z3.If(can_advance, transitioned_state, base_state),
            clears[index + 1] == z3.If(can_advance, transitioned_clear, base_clear),
            clears[index + 1] >= 0,
        )

        effective_unknown = effective_truth == _TRUTH_CODE[Truth.UNKNOWN]
        unknown_precondition = z3.And(
            can_advance,
            reduced_truth == _TRUTH_CODE[Truth.UNKNOWN],
            z3.Or(working_state == _STATE_CODE[Lifecycle.INACTIVE], working_state == _STATE_CODE[Lifecycle.CANDIDATE]),
        )
        unknown_without_fallback = z3.And(
            can_advance,
            reduced_truth == _TRUTH_CODE[Truth.UNKNOWN],
            _is_live(working_state),
            z3.Not(z3.BoolVal(contract.fallback_approved)),
        )
        unknown_as_true = z3.And(can_advance, effective_unknown, z3.BoolVal(contract.unknown_policy == "AS_TRUE"))
        review = z3.Or(future, stale, claimed, unknown_precondition, unknown_without_fallback, unknown_as_true, z3.Not(target_ok))
        unsupported = z3.Not(supported)
        conflict = effective_truth == _TRUTH_CODE[Truth.CONFLICT]
        verdict = z3.Int(f"eblc_verdict_{index}")
        solver.add(verdict == z3.If(unsupported, _VERDICT_CODE[Verdict.UNSUPPORTED], z3.If(conflict, _VERDICT_CODE[Verdict.CONFLICT], z3.If(review, _VERDICT_CODE[Verdict.REVIEW_REQUIRED], _VERDICT_CODE[Verdict.VALIDATED]))))

        live = _is_live(states[index + 1])
        entry_violation = z3.Bool(f"eblc_entry_violation_{index}")
        speed_violation = z3.Bool(f"eblc_speed_violation_{index}")
        deadlock_violation = z3.Bool(f"eblc_deadlock_violation_{index}")
        available = _real(contract.stop_position_x_m) - ego_x - _real(contract.position_uncertainty_m)
        adjusted_speed = ego_speed - _real(_EPSILON)
        stopping_distance = adjusted_speed * _real(contract.response_time_s) + adjusted_speed * adjusted_speed / (2 * _real(contract.maximum_service_deceleration_mps2))
        invariant_enabled = z3.And(supported, live, target_ok, z3.BoolVal(contract.enforce_invariant))
        solver.add(
            entry_violation == z3.And(invariant_enabled, ego_x > _real(contract.stop_position_x_m + _EPSILON)),
            speed_violation == z3.And(
                invariant_enabled,
                z3.If(
                    available <= 0,
                    ego_speed > _real(_EPSILON),
                    z3.And(adjusted_speed > 0, stopping_distance > available),
                ),
            ),
            deadlock_violation == z3.And(supported, z3.BoolVal(contract.force_deadlock), safe_progress),
        )
        progress_allowed = z3.Bool(f"eblc_progress_allowed_{index}")
        solver.add(progress_allowed == z3.If(supported, z3.And(z3.Not(live), z3.Not(deadlock_violation)), z3.BoolVal(False)))

        encoded.append({
            "verdict": verdict,
            "supported": supported,
            "numeric_ok": numeric_ok,
            "future": future,
            "stale": stale,
            "claimed": claimed,
            "effective_truth": effective_truth,
            "working_state": working_state,
            "reduced_truth": reduced_truth,
            "can_advance": can_advance,
            "target_ok": target_ok,
            "entry_violation": entry_violation,
            "speed_violation": speed_violation,
            "deadlock_violation": deadlock_violation,
            "progress_allowed": progress_allowed,
        })

    status = solver.check()
    if status == z3.unknown:
        raise RuntimeError(f"Z3 returned unknown for fixed EBLC trace: {solver.reason_unknown()}")
    if status != z3.sat:
        raise RuntimeError("fixed EBLC trace encoding is unexpectedly unsatisfiable")
    model = solver.model()

    steps: list[MonitorStep] = []
    for index, (frame, terms) in enumerate(zip(samples, encoded, strict=True)):
        lifecycle = _STATE_FROM_CODE[_int(model, states[index + 1])]
        verdict = _VERDICT_FROM_CODE[_int(model, terms["verdict"])]
        violations: list[str] = []
        if _bool(model, terms["entry_violation"]):
            violations.append("CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE")
        if _bool(model, terms["speed_violation"]):
            violations.append("DYNAMIC_STOPPING_SPEED_BOUND_EXCEEDED")
        if _bool(model, terms["deadlock_violation"]):
            violations.append("FALSE_DEADLOCK_NO_ADMISSIBLE_ACTION")

        diagnostics: list[str] = []
        if not _bool(model, terms["supported"]):
            if frame.distance_unit != contract.distance_unit:
                diagnostics.append("UNIT_MISMATCH")
            elif frame.coordinate_frame != contract.coordinate_frame:
                diagnostics.append("COORDINATE_FRAME_MISMATCH")
            else:
                diagnostics.append("NONFINITE_SCENE_VALUE")
        else:
            if _bool(model, terms["future"]):
                diagnostics.append("FACT_TIMESTAMP_IN_FUTURE")
            elif _bool(model, terms["stale"]):
                diagnostics.append("STALE_PREDICATE_FAILURE_TO_UNKNOWN")
            if _bool(model, terms["claimed"]):
                diagnostics.append("COC_CLAIM_NOT_OBSERVED_FACT")
            if _bool(model, terms["can_advance"]):
                effective = _int(model, terms["effective_truth"])
                reduced = _int(model, terms["reduced_truth"])
                working = _int(model, terms["working_state"])
                if effective == _TRUTH_CODE[Truth.CONFLICT]:
                    diagnostics.append("CONFLICTING_SCENE_EVIDENCE")
                else:
                    if effective == _TRUTH_CODE[Truth.UNKNOWN] and contract.unknown_policy == "AS_FALSE":
                        diagnostics.append("MUTATION_UNKNOWN_AS_FALSE")
                    elif effective == _TRUTH_CODE[Truth.UNKNOWN] and contract.unknown_policy == "AS_TRUE":
                        diagnostics.append("UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK")
                    if working in (_STATE_CODE[Lifecycle.INACTIVE], _STATE_CODE[Lifecycle.CANDIDATE]) and reduced == _TRUTH_CODE[Truth.UNKNOWN]:
                        diagnostics.append("UNKNOWN_PRECONDITION_REVIEW")
                    elif working == _STATE_CODE[Lifecycle.RELEASED] and reduced == _TRUTH_CODE[Truth.TRUE] and not contract.reactivation_enabled:
                        diagnostics.append("MISSING_REACTIVATION")
                    elif working in _LIVE_CODES and reduced == _TRUTH_CODE[Truth.UNKNOWN]:
                        diagnostics.append("APPROVED_UNKNOWN_HOLD_FALLBACK" if contract.fallback_approved else "UNKNOWN_WITHOUT_APPROVED_FALLBACK")
            if not _bool(model, terms["target_ok"]):
                diagnostics.append("TARGET_BINDING_MISMATCH")

        maximum_speed = _maximum_speed(contract, frame) if _bool(model, terms["supported"]) and lifecycle in (Lifecycle.ACTIVE, Lifecycle.MAINTAINED, Lifecycle.REACTIVATED) else None
        steps.append(MonitorStep(
            frame.timestamp_s,
            lifecycle,
            verdict,
            maximum_speed,
            _bool(model, terms["progress_allowed"]),
            tuple(violations),
            tuple(diagnostics),
        ))

    packed = tuple(steps)
    violations = tuple(item for step in packed for item in step.violations)
    diagnostics = tuple(item for step in packed for item in step.diagnostics)
    verdict = _trace_verdict(packed)
    return TraceResult(not violations and verdict not in {Verdict.CONFLICT, Verdict.UNSUPPORTED}, verdict, packed, violations, diagnostics)


def _status_name(status) -> str:
    return str(status).upper()


def bounded_queries(contract: BoundContract, frame_factory) -> dict[str, object]:
    if z3 is None:
        return enumerator_queries(contract, frame_factory)

    allowed_pairs = {
        (_STATE_CODE[Lifecycle.INACTIVE], _STATE_CODE[Lifecycle.INACTIVE]),
        (_STATE_CODE[Lifecycle.INACTIVE], _STATE_CODE[Lifecycle.CANDIDATE]),
        (_STATE_CODE[Lifecycle.INACTIVE], _STATE_CODE[Lifecycle.ACTIVE]),
        (_STATE_CODE[Lifecycle.CANDIDATE], _STATE_CODE[Lifecycle.INACTIVE]),
        (_STATE_CODE[Lifecycle.CANDIDATE], _STATE_CODE[Lifecycle.CANDIDATE]),
        (_STATE_CODE[Lifecycle.CANDIDATE], _STATE_CODE[Lifecycle.ACTIVE]),
        (_STATE_CODE[Lifecycle.ACTIVE], _STATE_CODE[Lifecycle.MAINTAINED]),
        (_STATE_CODE[Lifecycle.ACTIVE], _STATE_CODE[Lifecycle.RELEASED]),
        (_STATE_CODE[Lifecycle.MAINTAINED], _STATE_CODE[Lifecycle.MAINTAINED]),
        (_STATE_CODE[Lifecycle.MAINTAINED], _STATE_CODE[Lifecycle.RELEASED]),
        (_STATE_CODE[Lifecycle.RELEASED], _STATE_CODE[Lifecycle.RELEASED]),
        (_STATE_CODE[Lifecycle.RELEASED], _STATE_CODE[Lifecycle.REACTIVATED]),
        (_STATE_CODE[Lifecycle.REACTIVATED], _STATE_CODE[Lifecycle.MAINTAINED]),
    }
    lifecycle_solver = _new_solver()
    horizon = 4
    states = [z3.Int(f"query_state_{index}") for index in range(horizon + 1)]
    clears = [z3.Int(f"query_clear_{index}") for index in range(horizon + 1)]
    truths = [z3.Int(f"query_truth_{index}") for index in range(horizon)]
    lifecycle_solver.add(states[0] == _STATE_CODE[Lifecycle.INACTIVE], clears[0] == 0)
    disallowed = []
    for index in range(horizon):
        lifecycle_solver.add(z3.Or(*[truths[index] == _TRUTH_CODE[item] for item in (Truth.TRUE, Truth.FALSE, Truth.UNKNOWN)]))
        next_state, next_clear, _, _ = _transition_terms(states[index], clears[index], truths[index], contract)
        lifecycle_solver.add(states[index + 1] == next_state, clears[index + 1] == next_clear, clears[index + 1] >= 0)
        allowed = z3.Or(*[z3.And(states[index] == first, states[index + 1] == second) for first, second in allowed_pairs])
        disallowed.append(z3.Not(allowed))
    lifecycle_solver.add(z3.Or(*disallowed))
    lifecycle_status = lifecycle_solver.check()

    invariant_solver = _new_solver()
    witness_x = z3.Real("query_invariant_x")
    invariant_state, _, _, _ = _transition_terms(
        z3.IntVal(_STATE_CODE[Lifecycle.INACTIVE]),
        z3.IntVal(0),
        z3.IntVal(_TRUTH_CODE[Truth.TRUE]),
        contract,
    )
    invariant_solver.add(
        _is_live(invariant_state),
        witness_x > _real(contract.stop_position_x_m + _EPSILON),
    )
    invariant_status = invariant_solver.check() if contract.enforce_invariant else z3.unsat
    invariant_witness = None
    if invariant_status == z3.sat:
        invariant_witness = {"ego_front_x_m": invariant_solver.model().eval(witness_x).as_decimal(16)}

    reactivation_solver = _new_solver()
    reactivated_state, _, _, _ = _transition_terms(
        z3.IntVal(_STATE_CODE[Lifecycle.RELEASED]),
        z3.IntVal(contract.release_clear_frames),
        z3.IntVal(_TRUTH_CODE[Truth.TRUE]),
        contract,
    )
    reactivation_solver.add(reactivated_state != _STATE_CODE[Lifecycle.REACTIVATED])
    reactivation_status = reactivation_solver.check()

    deadlock_solver = _new_solver()
    safe_progress = z3.Bool("query_safe_progress")
    deadlock_state, _, _, _ = _transition_terms(
        z3.IntVal(_STATE_CODE[Lifecycle.INACTIVE]),
        z3.IntVal(0),
        z3.IntVal(_TRUTH_CODE[Truth.FALSE]),
        contract,
    )
    live = _is_live(deadlock_state)
    progress_allowed = z3.And(z3.Not(live), safe_progress, z3.Not(z3.BoolVal(contract.force_deadlock)))
    stop_allowed = live
    deadlock_solver.add(safe_progress, z3.Not(stop_allowed), z3.Not(progress_allowed))
    deadlock_status = deadlock_solver.check()

    return {
        "engine": ENGINE,
        "engine_version": ENGINE_VERSION,
        "encoding_version": ENCODING_VERSION,
        "solver_constructions": 4,
        "lifecycle_transition_consistency": {
            "sequences_checked": 3 ** horizon,
            "counterexample_status": _status_name(lifecycle_status),
            "invalid_transition_count": 0 if lifecycle_status == z3.unsat else 1,
            "consistent": lifecycle_status == z3.unsat,
        },
        "active_stop_position_invariant_violation_witness_exists": invariant_status == z3.sat,
        "active_stop_position_invariant_query_status": _status_name(invariant_status),
        "active_stop_position_invariant_witness": invariant_witness,
        "release_hazard_reappearance_missing_reactivation_witness_exists": reactivation_status == z3.sat,
        "release_hazard_reappearance_query_status": _status_name(reactivation_status),
        "safe_progress_false_deadlock_witness_exists": deadlock_status == z3.sat,
        "safe_progress_false_deadlock_query_status": _status_name(deadlock_status),
        "claim_boundary": "BOUNDED_SMT_FALSIFICATION_NOT_VEHICLE_SAFETY_PROOF",
    }
