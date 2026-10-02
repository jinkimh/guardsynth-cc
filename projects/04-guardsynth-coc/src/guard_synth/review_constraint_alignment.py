"""Reuse window-level observations without inventing event-level EBLC inputs.

Outputs are source-linked development drafts, not validated EBLC, human gold,
or a comparison against an independently generated model prediction.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any


ALIGNMENT_VERSION = "guardsynth-review-constraint-alignment-v0.1"
FAMILY = "PEDESTRIAN_CYCLIST_YIELD"
_TEMPORAL = {"HAZARD_VISIBLE", "NO_HAZARD_VISIBLE", "STATE_TRANSITION_VISIBLE", "NOT_OBSERVABLE"}
_ASSOCIATION = {"CLEAR_VISIBLE", "AMBIGUOUS_VISIBLE", "NOT_OBSERVABLE"}
_CONTEXT = {
    "PEDESTRIAN_OR_PERSON": r"\b(?:pedestrians?|persons?|personnel|driver)\b",
    "WORKER_OR_FLAGGER": r"\b(?:workers?|flaggers?)\b",
    "CROSSING_OR_CROSSWALK": r"\b(?:crossing|crosswalk|cleared the roadway)\b",
    "ROADSIDE_OR_SIDEWALK": r"\b(?:sidewalk|roadside|parking)\b",
    "TRAFFIC_CONTROL": r"\b(?:traffic light|stop sign|guidance)\b",
    "WORK_ZONE_OR_CONES": r"\b(?:construction zone|traffic cones)\b",
}
_DRAFTS = {
    "HAZARD_VISIBLE": (
        "CONDITIONAL_CONFLICT_ENTRY_RESTRICTION",
        "대상과 에고 진행 경로의 충돌 관계가 시점별 근거로 확인되어 유지되는 동안, "
        "해당 충돌 영역 진입을 제한하는 제약 후보. 구체적인 정지·감속·회피 행동과 수치는 미정이다.",
    ),
    "NO_HAZARD_VISIBLE": (
        "AVOID_UNSUPPORTED_ACTIVATION",
        "이 시간창의 관찰만으로 보행자 충돌 제약의 활성화를 확정하지 않는다. "
        "CoC의 예방적 감속이나 사람의 존재만으로 지속 정지 의무를 추가하지 않는다. "
        "이는 진행 허가나 다른 위험·제약의 부재 판정이 아니다.",
    ),
    "STATE_TRANSITION_VISIBLE": (
        "REVIEW_TIME_BOUND_RELEASE_CONDITION",
        "기존 관찰의 상태 전이와 메모를 유지하고, 충돌 관계가 해소된 시점·지속 조건을 "
        "확인한 뒤 해당 제약의 해제를 검토한다. 해제 시각·연속 clear frame 수는 추정하지 않는다.",
    ),
}


def index_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in records:
        key = item["candidate_digest"]
        if not key or key in result:
            raise ValueError("duplicate or missing candidate identity")
        result[key] = item
    return result


def align_reviewed_scene(
    *, scene: dict[str, Any], coc: str, observation: dict[str, Any],
    geometry: dict[str, Any], structured: dict[str, Any], authority: dict[str, Any],
    evidence_refs: dict[str, str],
) -> dict[str, Any]:
    """Align one existing answer with exact-source CoC and non-executable drafts."""
    key = scene["candidate_digest"]
    if scene["slice"] != FAMILY:
        raise ValueError("outside selected development family")
    for item in (observation, geometry, structured, authority):
        if item["candidate_digest"] != key or item["slice"] != FAMILY:
            raise ValueError("cross-scene evidence join")
    for item in (geometry, authority):
        if item["event_timestamp_us"] != scene["event_timestamp_us"]:
            raise ValueError("event timestamp mismatch")
    if geometry["source_video_sha256"] != authority["source_video_sha256"]:
        raise ValueError("source video mismatch")
    if structured["cascade_structured_link_audit"]["event_timestamp_us"] != scene["event_timestamp_us"]:
        raise ValueError("structured event timestamp mismatch")
    if hashlib.sha256(coc.encode()).hexdigest() != scene["coc_sha256"]:
        raise ValueError("CoC content hash mismatch")
    if set(evidence_refs) != {"coc", "observation", "geometry", "structured", "authority"} or not all(evidence_refs.values()):
        raise ValueError("source references incomplete")
    temporal = observation["visual_temporal_observation"]
    association = observation["visual_association_observation"]
    if temporal not in _TEMPORAL or association not in _ASSOCIATION:
        raise ValueError("unsupported observation value")
    if association != "CLEAR_VISIBLE" and temporal != "NOT_OBSERVABLE":
        raise ValueError("inconsistent observation pair")
    if temporal == "STATE_TRANSITION_VISIBLE" and not observation["notes"].strip():
        raise ValueError("transition note missing")

    contexts = [{"context": name, "matched_text": match.group(), "span": list(match.span()),
                 "evidence_ref": evidence_refs["coc"], "epistemic_kind": "CLAIMED"}
                for name, pattern in _CONTEXT.items() for match in re.finditer(pattern, coc, re.I)]
    candidate = _DRAFTS.get(temporal)
    polygons = geometry.get("normalized_pixel_polygons", {})
    polygon_count = sum(len(items) for items in polygons.values())
    labels = [label for label, items in polygons.items() if items]
    assessment = geometry["machine_geometry_assessment"]
    issues = [
        {"code": "EVENT_TIME_PREDICATE_NOT_ESTABLISHED", "owner": "MACHINE_SOURCE_ALIGNMENT",
         "detail": "기존 시간창 판정을 t0 truth/freshness로 변환하지 않음; 시점별 근거 연결 필요"},
        {"code": "TARGET_ZONE_BINDING_NOT_ESTABLISHED", "owner": "MACHINE_SOURCE_ALIGNMENT",
         "detail": "대상이 명확히 보인다는 답변은 CASCADE entity ID와 semantic zone의 수치적 연결과 다름"},
        {"code": "OPERATIONAL_CLAUSE_NOT_FROZEN", "owner": "RESEARCH_PROTOCOL",
         "detail": "기존 국제협약 baseline을 특정 STOP 행동·수치·해제 정책으로 자동 구체화하지 않음"},
        {"code": "NUMERIC_BACKEND_INPUTS_UNAVAILABLE", "owner": "MACHINE_SOURCE_ALIGNMENT",
         "detail": "현재 stopping backend의 metric zone entry·assurance profile 근거 없음; synthetic 값 이식 금지"},
    ]
    if temporal == "STATE_TRANSITION_VISIBLE":
        issues.append({"code": "TRANSITION_TIMING_UNRESOLVED", "owner": "SOURCE_FIRST_THEN_TARGETED_REVIEW",
                       "detail": "기존 전이 메모는 재사용; 정확한 시각과 release 조건만 추가 연결"})
    if temporal == "NOT_OBSERVABLE":
        issues.append({"code": "OBSERVATION_UNRESOLVED", "owner": "SOURCE_FIRST_THEN_TARGETED_REVIEW",
                       "detail": "관측 불가 답변을 보존; 더 나은 근거 확보 전 같은 질문 반복 금지"})
    # These are context flags, not accusations of annotation or CoC error.
    context_names = {item["context"] for item in contexts}
    mixed = bool(context_names & {"WORKER_OR_FLAGGER", "TRAFFIC_CONTROL", "WORK_ZONE_OR_CONES"})
    return {
        "alignment_version": ALIGNMENT_VERSION, "candidate_digest": key,
        "review_index": observation["review_index"], "group_id": scene["group_id"],
        "event_timestamp_us": scene["event_timestamp_us"], "upstream_split": scene["upstream_split"],
        "coc": {"text": coc, "sha256": scene["coc_sha256"], "epistemic_kind": "CLAIMED",
                "context_matches": contexts, "mixed_work_or_control_context": mixed},
        "observation": {k: observation[k] for k in ("visual_association_observation", "visual_temporal_observation", "notes", "image_sha256")},
        "observation_scope": "EXISTING_EVENT_ADJACENT_WINDOW_NOT_EVENT_TIME_GOLD",
        "observation_reused": True, "repeat_existing_survey_requested": False,
        "geometry": {"assessment": assessment, "disposition": geometry["geometry_disposition"],
                     "review_completed": True, "polygon_submission_completed": polygon_count > 0,
                     "polygon_count": polygon_count, "polygon_labels": labels,
                     "normalized_pixel_polygons": polygons,
                     "metric_geometry_inferred": False},
        "structured_target_candidates": structured["cascade_structured_link_audit"]["active_source_targets"],
        "authority": {k: authority[k] for k in ("authority_status", "rule_strength", "article_refs", "rule_summary", "legal_compliance_claim")},
        "draft": None if candidate is None else {
            "kind": candidate[0], "text_ko": candidate[1],
            "status": "REVIEW_DERIVED_CONDITIONAL_PROPOSAL_NOT_VERIFIED_CNL",
            "source_refs": [evidence_refs["observation"], evidence_refs["coc"]],
            "target_entity_id": None, "zone_id": None, "event_activation_truth": "UNKNOWN",
            "numeric_parameters": None, "selected_action": None,
        },
        "field_correspondence": {
            "binding.target_entity_id": "SOURCE_CANDIDATES_ONLY_NOT_SELECTED",
            "binding.zone_id": "UNBOUND_SEMANTIC_ZONE",
            "predicate.event_truth": "UNKNOWN_WINDOW_OBSERVATION_ONLY",
            "lifecycle.release": "TRANSITION_NOTE_ONLY" if temporal == "STATE_TRANSITION_VISIBLE" else "NOT_ESTABLISHED",
            "constraints.numeric_inputs": "NOT_ESTABLISHED",
            "rule.operational_mapping": "NOT_ESTABLISHED",
        },
        "eblc_preflight": {"status": "BLOCKED_MISSING_SOURCE_BINDINGS", "program_generated": False,
                           "sat_status": "NOT_RUN", "cnl_status": "NOT_RENDERED_FROM_EBLC"},
        "comparison_status": "OBSERVATION_REUSE_NOT_INDEPENDENT_ACCURACY_EVALUATION",
        "paper_cohort_eligibility": "NOT_EVALUATED", "learning_export_allowed": False,
        "issues": issues, "evidence_refs": evidence_refs,
    }
