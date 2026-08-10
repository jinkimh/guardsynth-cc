"""Deterministic partial entity and numerical binders for public EBLC v0."""

from __future__ import annotations

from math import isfinite

from .types import (
    BindingOutcome,
    BoundContract,
    ContextFrame,
    DerivationNode,
    EpistemicKind,
    PredicateSpec,
    RuleTemplate,
    TargetBinding,
    Truth,
    UnsupportedBinding,
    ValueBinding,
    VehicleProfile,
    Verdict,
)


def bind_pedestrian_contract(
    rule: RuleTemplate,
    predicate: PredicateSpec,
    frame: ContextFrame,
    vehicle_profile: VehicleProfile | None,
    *,
    target_ambiguity_reason: str | None = None,
) -> BindingOutcome:
    """Bind only supported, source-bearing inputs; never synthesize defaults."""
    target = TargetBinding(
        frame.target_entity_id or None,
        frame.zone_id or None,
        target_ambiguity_reason,
    )
    if rule.source.source_class.value == "UNKNOWN" or not rule.source.uri:
        unsupported = UnsupportedBinding("UNSUPPORTED_SOURCE", ("rule.source",))
        return BindingOutcome(Verdict.UNSUPPORTED, (unsupported.reason_code,), target, (unsupported,), None)
    frame_numeric = (
        frame.timestamp_s,
        frame.hazard.timestamp_s,
        frame.hazard.maximum_age_s,
        frame.ego_front_x_m,
        frame.ego_speed_mps,
        frame.zone_entry_x_m,
        rule.stop_margin_m,
        predicate.maximum_age_s,
    )
    if not all(isfinite(value) for value in frame_numeric):
        unsupported = UnsupportedBinding(
            "NONFINITE_BINDING_INPUT",
            ("context_frame", "rule.stop_margin_m", "predicate.maximum_age_s"),
        )
        return BindingOutcome(Verdict.UNSUPPORTED, (unsupported.reason_code,), target, (unsupported,), None)
    if frame.hazard.truth is Truth.CONFLICT:
        return BindingOutcome(Verdict.CONFLICT, ("CONFLICTING_SCENE_EVIDENCE",), target, (), None)
    if frame.hazard.epistemic_kind is EpistemicKind.CLAIMED:
        return BindingOutcome(
            Verdict.REVIEW_REQUIRED,
            ("COC_CLAIM_NOT_OBSERVED_FACT",),
            target,
            (),
            None,
        )
    if frame.hazard.truth is Truth.UNKNOWN:
        return BindingOutcome(
            Verdict.REVIEW_REQUIRED,
            ("UNKNOWN_PRECONDITION",),
            target,
            (),
            None,
        )
    if frame.hazard.truth is Truth.FALSE:
        return BindingOutcome(
            Verdict.REVIEW_REQUIRED,
            ("RULE_PRECONDITION_FALSE",),
            target,
            (),
            None,
        )
    if frame.hazard.epistemic_kind not in predicate.allowed_sources:
        return BindingOutcome(
            Verdict.REVIEW_REQUIRED,
            ("UNAPPROVED_EPISTEMIC_SOURCE",),
            target,
            (),
            None,
        )
    if not target.complete:
        reason = "AMBIGUOUS_TARGET" if target.ambiguity_reason else "UNSUPPORTED_TARGET_BINDING"
        unsupported = UnsupportedBinding(reason, ("target_entity_id", "zone_id"))
        verdict = Verdict.REVIEW_REQUIRED if target.ambiguity_reason else Verdict.UNSUPPORTED
        return BindingOutcome(verdict, (reason,), target, (unsupported,), None)
    if frame.distance_unit != "m" or frame.coordinate_frame != predicate.coordinate_frame:
        unsupported = UnsupportedBinding(
            "UNIT_OR_FRAME_ERROR",
            ("distance_unit", "coordinate_frame"),
        )
        return BindingOutcome(Verdict.UNSUPPORTED, (unsupported.reason_code,), target, (unsupported,), None)
    if vehicle_profile is None:
        unsupported = UnsupportedBinding(
            "MISSING_VEHICLE_PROFILE_FOR_NUMERIC_BINDING",
            ("vehicle_profile",),
        )
        return BindingOutcome(Verdict.UNSUPPORTED, (unsupported.reason_code,), target, (unsupported,), None)
    profile_numeric = (
        vehicle_profile.maximum_service_deceleration_mps2,
        vehicle_profile.response_time_s,
        vehicle_profile.position_uncertainty_m,
    )
    if not all(isfinite(value) for value in profile_numeric):
        unsupported = UnsupportedBinding(
            "NONFINITE_VEHICLE_PROFILE",
            ("vehicle_profile",),
        )
        return BindingOutcome(Verdict.UNSUPPORTED, (unsupported.reason_code,), target, (unsupported,), None)
    if (
        vehicle_profile.maximum_service_deceleration_mps2 <= 0
        or vehicle_profile.response_time_s < 0
        or vehicle_profile.position_uncertainty_m < 0
        or not vehicle_profile.evidence_ref
    ):
        unsupported = UnsupportedBinding("INVALID_VEHICLE_PROFILE", ("vehicle_profile",))
        return BindingOutcome(Verdict.UNSUPPORTED, (unsupported.reason_code,), target, (unsupported,), None)

    stop_position = frame.zone_entry_x_m - rule.stop_margin_m
    stop_binding = ValueBinding(
        stop_position,
        "m",
        (rule.source.evidence_id,),
        "derive-stop-position",
    )
    release_binding = ValueBinding(
        float(rule.release_clear_frames),
        "frame",
        (rule.source.evidence_id,),
        "bind-release-clear-frames",
    )
    dag = (
        DerivationNode(
            "derive-stop-position",
            "zone_entry_x_m - sourced_stop_margin_m",
            ("frame.zone_entry_x_m", "rule.stop_margin_m"),
            "contract.stop_position_x_m",
        ),
        DerivationNode(
            "derive-dynamic-speed-bound",
            "solve d >= v*rho + v^2/(2*b)",
            (
                "contract.stop_position_x_m",
                "frame.ego_front_x_m",
                "profile.response_time_s",
                "profile.maximum_service_deceleration_mps2",
                "profile.position_uncertainty_m",
            ),
            "step.maximum_safe_speed_mps",
        ),
    )
    contract = BoundContract(
        contract_id="EBLC-P0B-PED-CZ-0001",
        rule_id=rule.rule_id,
        subject_id="ego",
        target_entity_id=target.entity_id or "",
        zone_id=target.zone_id or "",
        zone_entry_x_m=frame.zone_entry_x_m,
        stop_position_x_m=stop_position,
        stop_margin_m=rule.stop_margin_m,
        release_clear_frames=rule.release_clear_frames,
        fallback=rule.fallback,
        fallback_approved=rule.fallback_approved,
        evidence_refs=(rule.source.evidence_id, vehicle_profile.evidence_ref),
        derivation_dag=dag,
        coordinate_frame=predicate.coordinate_frame,
        distance_unit="m",
        predicate_maximum_age_s=predicate.maximum_age_s,
        maximum_service_deceleration_mps2=vehicle_profile.maximum_service_deceleration_mps2,
        response_time_s=vehicle_profile.response_time_s,
        position_uncertainty_m=vehicle_profile.position_uncertainty_m,
        priority=rule.priority,
    )
    return BindingOutcome(
        Verdict.VALIDATED,
        ("BOUND_SOURCE_OBSERVABILITY_COMPLETE",),
        target,
        (stop_binding, release_binding),
        contract,
    )
