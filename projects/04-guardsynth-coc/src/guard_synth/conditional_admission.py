"""Conditional development admission is distinct from full-source/main-study approval."""

from guard_synth.source_acceptance import point, polygon

POLICY_VERSION = "paper1-conditional-admission-v0.1"


def assess_conditional_candidate(row, *, english_meaning_recorded=False,
                                 supported_scope=False, solver_checks_passed=False,
                                 permitted_actions=()):
    reasons = []
    for field in ("assets_verified", "contract_cnl_linked", "independent_action_available", "cnl_review_available"):
        if row.get(field) is not True:
            reasons.append(field.upper() + "_REQUIRED")
    try:
        point(row.get("reviewed_event_target"))
        polygon(row.get("reviewed_event_zone"))
    except ValueError:
        reasons.append("CONFIRMED_TARGET_ZONE_REQUIRED")
    predicates = row.get("event_predicates")
    valid_predicates = isinstance(predicates, dict) and set(predicates) == {"ped", "road"} and all(
        isinstance(v, dict) and set(v) == {"truth", "evidence_valid"}
        and isinstance(v["truth"], str) and v["truth"] in {"TRUE", "FALSE", "UNKNOWN", "CONFLICT"}
        and type(v["evidence_valid"]) is bool for v in predicates.values())
    known = [v for v in predicates.values() if v["evidence_valid"] and v["truth"] in {"TRUE", "FALSE"}] if valid_predicates else []
    if not known:
        reasons.append("CONFIRMED_EVENT_EVIDENCE_REQUIRED")
    for flag, reason in ((english_meaning_recorded, "ENGLISH_MEANING_RECORD_REQUIRED"),
                         (supported_scope, "SUPPORTED_CONDITION_SCOPE_REQUIRED"),
                         (solver_checks_passed, "PASSING_BOUNDED_CHECKS_REQUIRED")):
        if flag is not True:
            reasons.append(reason)
    action = row.get("independent_development_action")
    if not isinstance(action, str) or action not in {"DEFER_ENTRY", "ENTER_ZONE"}:
        reasons.append("INDEPENDENT_ACTION_LABEL_REQUIRED")
    elif action not in permitted_actions:
        reasons.append("ACTION_SPEC_ADJUDICATION_REQUIRED")
    if row.get("prior_observation") == "NOT_OBSERVABLE":
        reasons.append("PRIOR_UNOBSERVABLE_NOT_RESOLVED")
    admitted = not reasons
    return {"policy_version": POLICY_VERSION,
        "conditional_development_admissible": admitted,
        "status": "CONDITIONAL_DEVELOPMENT_ADMITTED" if admitted else "CONDITIONAL_DEVELOPMENT_PENDING",
        "reasons": reasons, "all_predicates_resolved": len(known) == 2,
        "source_accepted_unchanged": row.get("source_accepted") is True,
        "nominal_entry_label_available": admitted and action == "ENTER_ZONE" and all(v["truth"] == "FALSE" for v in known) and len(known) == 2,
        "main_study_admissible": False, "learning_export_allowed": False,
        "claim_scope": "CONDITIONAL_DEVELOPMENT_CANDIDATE_NOT_MAIN_GOLD_OR_EFFECT"}
