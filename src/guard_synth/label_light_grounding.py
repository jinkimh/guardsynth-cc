"""Label-light association proposal, triage, and minimal human confirmation.

The module consumes existing perception/map/trajectory evidence.  It does not
train a detector or treat confidence as truth.  Automatic confirmation is
allowed only for a unique pair whose lower confidence bound is calibrated by
an explicitly approved evidence record.  All other cases remain reviewable,
unsupported, or conflicting.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import re
from typing import Any, Iterable

from guard_synth_eblc.schema_validation import load_json, validate


PACKET_VERSION = "guardsynth-label-light-grounding-v0.1"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/label_light_grounding_packet.schema.json"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


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
