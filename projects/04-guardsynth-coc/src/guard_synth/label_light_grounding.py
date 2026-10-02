"""Label-light association proposal, triage, and minimal human confirmation.

The module consumes existing perception/map/trajectory evidence.  It does not
train a detector or treat confidence as truth.  Automatic confirmation is
allowed only for a unique pair whose lower confidence bound is calibrated by
an explicitly approved evidence record.  All other cases remain reviewable,
unsupported, or conflicting.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from math import isfinite
from pathlib import Path
import re
from typing import Any, Iterable

from guard_synth_eblc.schema_validation import load_json, validate
from .dry_run_readiness import REQUIRED_SCENE_FIELDS


PACKET_VERSION = "guardsynth-label-light-grounding-v0.1"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/label_light_grounding_packet.schema.json"
IMAGE_REVIEW_EXPORT_SCHEMA_PATH = (
    Path(__file__).resolve().parent / "schemas/image_only_review_export.schema.json"
)
IMAGE_REVIEW_PARTIAL_PACKET_SCHEMA_PATH = (
    Path(__file__).resolve().parent / "schemas/image_review_partial_scene_packet.schema.json"
)
IMAGE_REVIEW_PARTIAL_PACKET_VERSION = "guardsynth-image-review-partial-scene-v0.1"
CALIBRATION_AUDIT_QUEUE_VERSION = "guardsynth-image-review-calibration-audit-v0.1"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_MISSING_REASON_BY_FIELD = {
    "timestamps": "MISSING_TIMESTAMPS",
    "ego_pose_and_speed": "MISSING_TIME_ALIGNED_EGO_POSE_AND_SPEED",
    "relevant_actor_tracks": "MISSING_RELEVANT_ACTOR_TRACKS",
    "target_zone_or_lane_association": "MISSING_OR_AMBIGUOUS_TARGET_ZONE_ASSOCIATION",
    "conflict_or_stop_geometry": "MISSING_CONFLICT_OR_STOP_GEOMETRY",
    "verified_coordinate_transform": "UNVERIFIED_COORDINATE_TRANSFORM",
    "applicable_rule_source_refs": "MISSING_APPLICABLE_RULE_SOURCE_REFS",
    "exact_vehicle_binding": "MISSING_EXACT_VEHICLE_BINDING",
    "source_bearing_vehicle_assurance_profile": "MISSING_VEHICLE_ASSURANCE_PROFILE",
}


class LabelLightValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LabelLightPacket:
    raw: dict[str, Any]
    packet_id: str


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    decision: str
    selected_target_entity_id: str | None
    selected_zone_id: str | None
    reviewer_evidence_ref: str


@dataclass(frozen=True, slots=True)
class LabelLightResult:
    packet_id: str
    association_status: str
    contract_readiness: str
    reason_codes: tuple[str, ...]
    grounded_scene: dict[str, Any] | None
    review_task: dict[str, Any] | None
    proposed_pair: tuple[str, str] | None
    human_correction: bool = False


def _candidate_slices(record: dict[str, Any]) -> list[str]:
    tags = set(record["scene_tags"])
    situation = record["primary_situation"]
    candidates: list[str] = []
    if tags & {"PEDESTRIAN", "CYCLIST_MICROMOBILITY", "CROSSWALK"} or situation in {
        "ROAD_USER_IN_EGO_PATH", "ROAD_USER_APPROACHING_CONFLICT_AREA",
    }:
        candidates.append("PEDESTRIAN_CYCLIST_YIELD")
    if tags & {"TRAFFIC_SIGNAL", "STOP_YIELD_SIGN"} or situation == "TRAFFIC_CONTROL_REQUIRES_ATTENTION":
        candidates.append("STOP_SIGNALS")
    if tags & {"FOLLOWING", "CUT_IN_MERGE"} or situation in {
        "VEHICLE_CUT_IN_OR_MERGE", "FOLLOWING_DISTANCE_CONCERN",
    }:
        candidates.append("FOLLOWING_CUT_IN")
    return candidates


def _candidate_strata(record: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    if record["visual_hazard"] == "TRUE":
        candidates.append("HAZARD_VISIBLE")
    if (
        "OCCLUSION" in record["scene_tags"]
        or record["occlusion"] in {"PARTIAL", "SEVERE"}
        or record["visual_hazard"] == "CONFLICT_ACROSS_FRAMES"
    ):
        candidates.append("HAZARD_OCCLUDED_OR_REAPPEARING")
    if record["visual_hazard"] == "FALSE" and record["primary_situation"] == "NO_VISIBLE_HAZARD":
        candidates.append("NOMINAL_CLEAR")
    if record["temporal_change"] == "LEAVING":
        candidates.append("RELEASE_OR_REACTIVATION")
    return candidates


def _partial_packet_id(scene_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]", "_", scene_id)
    return f"image_review_{normalized}"


def convert_image_review_export(
    raw: dict[str, Any], source_document_sha256: str
) -> list[dict[str, Any]]:
    """Convert completed image claims without inventing M13 grounding values."""
    validate(raw, load_json(IMAGE_REVIEW_EXPORT_SCHEMA_PATH))
    if not _SHA256.fullmatch(source_document_sha256):
        raise LabelLightValidationError("invalid source document sha256")
    review_ids = [record["review_id"] for record in raw["records"]]
    scene_ids = [record["scene_id"] for record in raw["records"]]
    if _duplicates(review_ids) or _duplicates(scene_ids):
        raise LabelLightValidationError("duplicate image review or scene id")

    missing_fields = list(REQUIRED_SCENE_FIELDS)
    missing_reasons = [_MISSING_REASON_BY_FIELD[field] for field in missing_fields]
    packets: list[dict[str, Any]] = []
    packet_schema = load_json(IMAGE_REVIEW_PARTIAL_PACKET_SCHEMA_PATH)
    for record in raw["records"]:
        if (
            record["review_complete"] is not True
            or not record["review_completed_at"].strip()
            or (
                record["human_disposition"] != record["recommended_disposition"]
                and not record["override_reason"].strip()
            )
        ):
            raise LabelLightValidationError(
                f"incomplete image review: {record['review_id']}"
            )
        input_reasons = [
            item for item in record["reason_codes"]
            if isinstance(item, str) and item.strip()
        ]
        reason_codes = list(dict.fromkeys([
            *input_reasons,
            "HUMAN_IMAGE_REVIEW_NOT_ADJUDICATED_GROUND_TRUTH",
            *missing_reasons,
        ]))
        packet = {
            "packet_version": IMAGE_REVIEW_PARTIAL_PACKET_VERSION,
            "packet_id": _partial_packet_id(record["scene_id"]),
            "scene_ref": record["scene_id"],
            "input_class": "LICENSE_RESTRICTED_IMAGE_REVIEW",
            "source_review": {
                "document_sha256": source_document_sha256,
                "exported_at": raw["exported_at"],
                "review_version": raw["review_version"],
                "image_filename": record["image_filename"],
            },
            "review_evidence": {
                "evidence_ref": f"image-review:{source_document_sha256[:12]}:{record['review_id']}",
                "evidence_kind": "HUMAN_REVIEWED_IMAGE_CLAIM",
                "review_id": record["review_id"],
                "reviewer_id": record["reviewer_id"],
                "review_completed_at": record["review_completed_at"],
            },
            "observations": {
                "scene_tags": list(record["scene_tags"]),
                "image_usability": record["image_usability"],
                "primary_situation": record["primary_situation"],
                "visual_hazard": record["visual_hazard"],
                "subject_description": record["subject_description"],
                "candidate_region": record["conflict_region"],
                "subject_region_relation": record["subject_position"],
                "occlusion": record["occlusion"],
                "traffic_control": record["traffic_control"],
                "ego_motion_impression": record["ego_motion"],
                "temporal_change": record["temporal_change"],
                "human_disposition": record["human_disposition"],
                "recommended_disposition": record["recommended_disposition"],
                "review_confidence": record["review_confidence"],
                "override_reason": record["override_reason"],
                "notes": record["notes"],
            },
            "selection_hints": {
                "candidate_slices": _candidate_slices(record),
                "candidate_strata": _candidate_strata(record),
                "slot_assignment_status": "UNASSIGNED_REVIEW_REQUIRED",
            },
            "source_closure": {
                "status": "REVIEW_REQUIRED",
                "source_complete": False,
                "contract_generation_allowed": False,
                "missing_fields": missing_fields,
                "reason_codes": reason_codes,
                "synthesized_required_values": [],
            },
        }
        validate(packet, packet_schema)
        packets.append(packet)
    return packets


def build_blinded_calibration_audit_queue(
    packets: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Select one deterministic item per disposition without exposing its label."""
    packet_list = tuple(packets)
    if not packet_list:
        raise LabelLightValidationError("calibration audit requires at least one packet")

    by_disposition: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for packet in packet_list:
        try:
            disposition = packet["observations"]["human_disposition"]
            packet_id = packet["packet_id"]
            source_sha = packet["source_review"]["document_sha256"]
        except (KeyError, TypeError) as exc:
            raise LabelLightValidationError("invalid partial packet for calibration audit") from exc
        digest = hashlib.sha256(f"{source_sha}:{packet_id}".encode("utf-8")).hexdigest()
        by_disposition.setdefault(disposition, []).append((digest, packet))

    selected = [min(group, key=lambda item: item[0]) for group in by_disposition.values()]
    selected.sort(key=lambda item: item[0])
    items = []
    for index, (_, packet) in enumerate(selected, start=1):
        items.append({
            "audit_id": f"CAL-{index:03d}",
            "source_packet_id": packet["packet_id"],
            "scene_ref": packet["scene_ref"],
            "image_filename": packet["source_review"]["image_filename"],
            "status": "PENDING_INDEPENDENT_REVIEW",
        })
    return {
        "queue_version": CALIBRATION_AUDIT_QUEUE_VERSION,
        "selection_method": "ONE_DETERMINISTIC_HASHED_ITEM_PER_ORIGINAL_DISPOSITION",
        "input_packet_count": len(packet_list),
        "sample_count": len(items),
        "original_labels_embedded": False,
        "claim_scope": "PRELIMINARY_BLINDED_REVIEW_QUEUE_NOT_ACCURACY_OR_GROUND_TRUTH",
        "items": items,
    }


def _duplicates(values: Iterable[str]) -> bool:
    items = tuple(values)
    return len(items) != len(set(items))


def _evidence_refs(raw: dict[str, Any]) -> tuple[str, ...]:
    refs = [
        raw["policy"]["policy_evidence_ref"], raw["hazard"]["evidence_ref"],
        *raw["policy"]["approved_calibration_evidence_refs"],
    ]
    refs.extend(item["track_evidence_ref"] for item in raw["targets"])
    for zone in raw["zones"]:
        refs.extend((zone["geometry_evidence_ref"], zone["transform_evidence_ref"]))
    for pair in raw["pair_candidates"]:
        refs.extend((pair["association_evidence_ref"], pair["calibration_evidence_ref"]))
    return tuple(ref for ref in refs if ref)


def parse_label_light_packet(raw: dict[str, Any]) -> LabelLightPacket:
    validate(raw, load_json(SCHEMA_PATH))
    if raw["packet_version"] != PACKET_VERSION:
        raise LabelLightValidationError("unsupported packet version")
    if not _IDENTIFIER.fullmatch(raw["packet_id"]):
        raise LabelLightValidationError("invalid packet id")
    if not 0.0 <= float(raw["policy"]["minimum_confidence_lower_bound"]) <= 1.0:
        raise LabelLightValidationError("invalid auto-confirm confidence threshold")
    known = tuple(raw["source_refs"])
    if _duplicates(known):
        raise LabelLightValidationError("duplicate source refs")
    unknown = sorted(set(_evidence_refs(raw)) - set(known))
    if unknown:
        raise LabelLightValidationError(f"unknown evidence references: {unknown}")

    target_ids = tuple(item["target_entity_id"] for item in raw["targets"])
    zone_ids = tuple(item["zone_id"] for item in raw["zones"])
    if _duplicates(target_ids) or _duplicates(zone_ids):
        raise LabelLightValidationError("duplicate target or zone id")
    pairs: set[tuple[str, str]] = set()
    for item in raw["pair_candidates"]:
        key = (item["target_entity_id"], item["zone_id"])
        if key in pairs:
            raise LabelLightValidationError("duplicate target-zone candidate pair")
        pairs.add(key)
        if key[0] not in target_ids or key[1] not in zone_ids:
            raise LabelLightValidationError("candidate pair refers to unknown target or zone")
        lower = float(item["confidence_lower_bound"])
        upper = float(item["confidence_upper_bound"])
        if not all(isfinite(value) and 0.0 <= value <= 1.0 for value in (lower, upper)) or lower > upper:
            raise LabelLightValidationError("invalid confidence interval")
    return LabelLightPacket(raw, raw["packet_id"])


def _pair_sort_key(pair: dict[str, Any]) -> tuple[float, float, str, str]:
    return (
        -float(pair["confidence_lower_bound"]),
        -float(pair["confidence_upper_bound"]),
        pair["target_entity_id"], pair["zone_id"],
    )


def _zone(packet: LabelLightPacket, zone_id: str) -> dict[str, Any]:
    return next(item for item in packet.raw["zones"] if item["zone_id"] == zone_id)


def _target(packet: LabelLightPacket, target_id: str) -> dict[str, Any]:
    return next(item for item in packet.raw["targets"] if item["target_entity_id"] == target_id)


def _hazard_review_reasons(raw: dict[str, Any]) -> tuple[str, ...]:
    hazard = raw["hazard"]
    reasons: list[str] = []
    if hazard["epistemic_kind"] == "CLAIMED":
        reasons.append("COC_CLAIM_NOT_OBSERVED_FACT")
    if hazard["truth"] == "UNKNOWN":
        reasons.append("UNKNOWN_HAZARD_EVIDENCE")
    elif hazard["truth"] == "FALSE":
        reasons.append("HAZARD_NOT_ACTIVE")
    if raw["timestamp_s"] < hazard["timestamp_s"]:
        reasons.append("FUTURE_HAZARD_EVIDENCE")
    elif raw["timestamp_s"] - hazard["timestamp_s"] > hazard["maximum_age_s"]:
        reasons.append("STALE_HAZARD_EVIDENCE")
    return tuple(reasons)


def _grounded_scene(
    packet: LabelLightPacket,
    pair: dict[str, Any],
    *,
    review_evidence_ref: str | None = None,
) -> dict[str, Any]:
    raw = packet.raw
    zone = _zone(packet, pair["zone_id"])
    target = _target(packet, pair["target_entity_id"])
    association_refs = list(dict.fromkeys((
        pair["association_evidence_ref"], pair["calibration_evidence_ref"],
        target["track_evidence_ref"], review_evidence_ref,
    )))
    association_refs = [item for item in association_refs if item]
    return {
        "scene_ref": raw["scene_ref"],
        "instance_id": f"{packet.packet_id}_instance",
        "contract_id": f"{packet.packet_id}_contract",
        "timestamp_s": raw["timestamp_s"],
        "hazard": dict(raw["hazard"]),
        "association": {
            "target_entity_id": pair["target_entity_id"],
            "zone_id": pair["zone_id"],
            "evidence_ref": pair["association_evidence_ref"],
            "evidence_refs": association_refs,
        },
        "zone_geometry": {
            "entry_x_m": zone["entry_x_m"], "frame": zone["frame"],
            "evidence_ref": zone["geometry_evidence_ref"],
        },
        "coordinate_transform": {
            "verified": zone["transform_verified"],
            "evidence_ref": zone["transform_evidence_ref"],
        },
        "vehicle_binding_key": raw["vehicle_binding_key"],
        "assurance_scope": raw["assurance_scope"],
        "reason_codes": [],
    }


def triage_label_light_packet(packet: LabelLightPacket) -> LabelLightResult:
    raw = packet.raw
    hazard = raw["hazard"]
    if hazard["truth"] == "CONFLICT":
        return LabelLightResult(
            packet.packet_id, "CONFLICT", "NOT_AUTHORED",
            ("CONFLICTING_HAZARD_EVIDENCE",), None, None, None,
        )
    approved_calibrations = set(raw["policy"]["approved_calibration_evidence_refs"])
    infrastructure_reasons: list[str] = []
    for zone in raw["zones"]:
        if not zone["geometry_evidence_ref"]:
            infrastructure_reasons.append("MISSING_CONFLICT_ZONE_GEOMETRY")
        if not zone["transform_verified"] or not zone["transform_evidence_ref"]:
            infrastructure_reasons.append("UNVERIFIED_COORDINATE_TRANSFORM")
    if any(not item["track_evidence_ref"] for item in raw["targets"]):
        infrastructure_reasons.append("MISSING_TRACK_EVIDENCE")
    if any(
        not item["association_evidence_ref"]
        or not item["calibration_evidence_ref"]
        or item["calibration_evidence_ref"] not in approved_calibrations
        for item in raw["pair_candidates"]
    ):
        infrastructure_reasons.append("MISSING_OR_UNAPPROVED_CONFIDENCE_CALIBRATION")
    if infrastructure_reasons:
        return LabelLightResult(
            packet.packet_id, "UNSUPPORTED", "NOT_AUTHORED",
            tuple(dict.fromkeys(infrastructure_reasons)), None, None, None,
        )

    pairs = sorted(raw["pair_candidates"], key=_pair_sort_key)
    plausible = [item for item in pairs if item["path_intersection"] == "TRUE"]
    proposal = plausible[0] if plausible else pairs[0]
    proposal_key = (proposal["target_entity_id"], proposal["zone_id"])
    threshold = float(raw["policy"]["minimum_confidence_lower_bound"])
    calibrated_high = [
        item for item in plausible
        if float(item["confidence_lower_bound"]) >= threshold
        and item["calibration_evidence_ref"] in approved_calibrations
    ]
    hazard_reasons = _hazard_review_reasons(raw)
    hazard_allows_auto = hazard["truth"] == "TRUE" and not hazard_reasons
    unique_ok = (
        len(plausible) == 1 if raw["policy"]["require_unique_candidate_pair"]
        else len(calibrated_high) == 1
    )
    if raw["policy"]["auto_confirm_enabled"] and hazard_allows_auto and unique_ok and len(calibrated_high) == 1:
        selected = calibrated_high[0]
        return LabelLightResult(
            packet.packet_id, "AUTO_CONFIRMED", "SOURCE_AUTHORED_PENDING_ASSURANCE_LOOKUP",
            ("UNIQUE_CALIBRATED_ASSOCIATION",), _grounded_scene(packet, selected),
            None, (selected["target_entity_id"], selected["zone_id"]),
        )

    review_reasons = ["HUMAN_CONFIRMATION_REQUIRED"]
    review_reasons.extend(hazard_reasons)
    if len(plausible) != 1:
        review_reasons.append("NON_UNIQUE_ASSOCIATION_CANDIDATES")
    if not calibrated_high:
        review_reasons.append("LOW_CONFIDENCE_ASSOCIATION")
    task = {
        "review_task_id": f"{packet.packet_id}_association_review",
        "proposed_pair": {
            "target_entity_id": proposal["target_entity_id"], "zone_id": proposal["zone_id"],
        },
        "candidate_pairs": [
            {"target_entity_id": item["target_entity_id"], "zone_id": item["zone_id"]}
            for item in pairs
        ],
        "allowed_decisions": ["CONFIRM_PROPOSAL", "SELECT_PAIR", "MARK_AMBIGUOUS", "REJECT_SCENE"],
        "estimated_interactions": 1 if proposal else 2,
        "full_geometry_annotation_required": False,
    }
    return LabelLightResult(
        packet.packet_id, "REVIEW_REQUIRED", "NOT_AUTHORED",
        tuple(review_reasons), None, task, proposal_key,
    )


def apply_review_decision(
    packet: LabelLightPacket,
    triage: LabelLightResult,
    decision: ReviewDecision,
) -> LabelLightResult:
    if triage.association_status != "REVIEW_REQUIRED" or triage.review_task is None:
        raise LabelLightValidationError("review decision requires a REVIEW_REQUIRED task")
    if not decision.reviewer_evidence_ref.strip():
        raise LabelLightValidationError("review evidence is required")
    if decision.decision in {"MARK_AMBIGUOUS", "REJECT_SCENE"}:
        status = "REVIEW_REQUIRED" if decision.decision == "MARK_AMBIGUOUS" else "UNSUPPORTED"
        return LabelLightResult(
            packet.packet_id, status, "NOT_AUTHORED", (decision.decision,),
            None, triage.review_task if status == "REVIEW_REQUIRED" else None,
            triage.proposed_pair,
        )
    if decision.decision == "CONFIRM_PROPOSAL":
        selected_key = triage.proposed_pair
    elif decision.decision == "SELECT_PAIR":
        selected_key = (decision.selected_target_entity_id, decision.selected_zone_id)
    else:
        raise LabelLightValidationError("unknown review decision")
    candidates = {
        (item["target_entity_id"], item["zone_id"]): item
        for item in packet.raw["pair_candidates"]
    }
    if selected_key not in candidates:
        raise LabelLightValidationError("selected pair is not a candidate")
    pair = candidates[selected_key]
    correction = selected_key != triage.proposed_pair
    hazard_reasons = _hazard_review_reasons(packet.raw)
    if hazard_reasons:
        return LabelLightResult(
            packet.packet_id, "HUMAN_CONFIRMED", "HAZARD_REVIEW_REQUIRED",
            ("MINIMAL_HUMAN_CONFIRMATION", *hazard_reasons),
            None, None, selected_key, correction,
        )
    return LabelLightResult(
        packet.packet_id, "HUMAN_CONFIRMED", "SOURCE_AUTHORED_PENDING_ASSURANCE_LOOKUP",
        ("MINIMAL_HUMAN_CONFIRMATION",),
        _grounded_scene(packet, pair, review_evidence_ref=decision.reviewer_evidence_ref),
        None, selected_key, correction,
    )


def aggregate_label_light_metrics(results: Iterable[LabelLightResult]) -> dict[str, Any]:
    values = tuple(results)
    total = len(values)
    counts = {
        "auto_confirmed": sum(item.association_status == "AUTO_CONFIRMED" for item in values),
        "review_required": sum(item.association_status == "REVIEW_REQUIRED" for item in values),
        "human_confirmed": sum(item.association_status == "HUMAN_CONFIRMED" for item in values),
        "unsupported": sum(item.association_status == "UNSUPPORTED" for item in values),
        "conflict": sum(item.association_status == "CONFLICT" for item in values),
        "human_corrections": sum(item.human_correction for item in values),
    }
    return {
        "total": total,
        **counts,
        "automatic_confirmation_rate": counts["auto_confirmed"] / total if total else 0.0,
        "review_request_rate": counts["review_required"] / total if total else 0.0,
        "unsupported_rate": counts["unsupported"] / total if total else 0.0,
        "claim_scope": "LABEL_LIGHT_WORKFLOW_METRICS_NOT_ASSOCIATION_ACCURACY_OR_VEHICLE_SAFETY",
    }


def assess_legacy_adapter_label_light(
    adapter_result: dict[str, Any], *, target_slots: int = 24
) -> dict[str, Any]:
    candidates = list(adapter_result.get("candidates", ()))
    gaps = list(adapter_result.get("data_gaps", ()))
    declared = adapter_result.get("vru_event_count", len(candidates) + len(gaps))
    if (
        not isinstance(declared, int) or isinstance(declared, bool)
        or declared != len(candidates) + len(gaps) or declared > target_slots
    ):
        raise LabelLightValidationError("legacy adapter event accounting mismatch")
    review = sum(
        item.get("target_binding", {}).get("verdict") != "VALIDATED"
        for item in candidates
    )
    blocked = sum(
        item.get("contract_binding", {}).get("verdict") != "VALIDATED"
        for item in candidates
    )
    return {
        "status": "LABEL_LIGHT_LEGACY_INPUT_AUDIT",
        "slot_count": target_slots,
        "candidate_event_count": declared,
        "adapted_candidate_count": len(candidates),
        "derivation_gap_count": len(gaps),
        "missing_scene_input_count": target_slots - declared,
        "auto_confirmed_count": 0,
        "association_review_required_count": review,
        "contract_blocked_count": blocked,
        "raw_identifiers_included": False,
        "decision": "LABEL_LIGHT_REVIEW_INPUT_REQUIRED",
        "claim_scope": "AGGREGATE_LABEL_LIGHT_READINESS_NOT_ASSOCIATION_ACCURACY_OR_SAFETY",
    }
