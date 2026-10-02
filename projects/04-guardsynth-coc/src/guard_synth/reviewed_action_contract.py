"""Bind a pinned development source review without inventing unobserved states."""

from copy import deepcopy

from guard_synth.source_acceptance import validate_review
from guard_synth.qualitative_scene_contract import prepare_scene18_contract
from guard_synth_eblc.action_contract import parse_action_contract


def bind_reviewed_scene18(scene, packet, review, *, packet_sha256, review_ref, policy_ref, source_refs):
    if (packet["candidate_digest"] != scene["candidate_digest"]
        or packet["event_timestamp_us"] != scene["event_timestamp_us"]
        or packet["clip_id"] != scene["clip_id"]):
        raise ValueError("review/scene identity mismatch")
    if review_ref not in source_refs:
        raise ValueError("review source not pinned")
    verdict = validate_review(review, packet, packet_sha256)
    initial, _ = prepare_scene18_contract(scene, policy_ref=policy_ref, source_refs=source_refs)
    raw = deepcopy(initial.raw)
    raw["contract_id"] = "scene18_reviewed_entry_contract"
    if review["zone_status"] == "CONFIRMED":
        raw["zone_id"] = "scene18_reviewed_entry_zone"
    if review["target_identity"] != "CONFIRMED_AGENT3":
        raw["obligations"][0]["target_entity_id"] = None
    # Do not manufacture a road actor ID, metric geometry or an extra time observation.
    binding = {"zone_id": raw["zone_id"], "zone_polygon": deepcopy(review["zone_polygon"]),
        "target_point": deepcopy(review["target_point"]), "coordinate_frame": "camera_front_wide_120fov_normalized_pixel",
        "review_ref": review_ref, "event_timestamp_us": packet["event_timestamp_us"],
        "source_frame_timestamp_us": packet["frames"][-1]["timestamp_us"],
        "source_frame_pixel_sha256": packet["frames"][-1]["pixel_sha256"],
        "metric_geometry": None, "event_predicates": verdict["event_predicates"],
        "observed_core_offsets": [0], "unobserved_core_offsets": [1, 2],
        "prior_activation_observed": False, "cross_dataset_clock_independently_verified": False,
        "source_accepted_for_development": verdict["source_accepted_for_development"],
        "learning_export_allowed": False, "independent_action_gold": None,
        "evidence_scope": "SINGLE_REVIEWED_DECISION_PARTIAL_EVIDENCE_NOT_FULL_TRACE_GOLD"}
    return parse_action_contract(raw), binding
