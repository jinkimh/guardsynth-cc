"""M16 expert-pilot design and fail-closed source eligibility preflight."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from math import ceil, isfinite
import random
from statistics import mean, median
from typing import Any

from guard_synth_eblc.schema_validation import load_json, validate


PILOT_PROTOCOL_VERSION = "guardsynth-expert-pilot-v0.1"
SLICES = ("PEDESTRIAN_CYCLIST_YIELD", "STOP_SIGNALS", "FOLLOWING_CUT_IN")
OUTCOMES = ("NOMINAL", "HAZARD_TRUE_ACTIVE", "UNKNOWN", "CONFLICT", "RELEASE", "REACTIVATION")
ANNOTATION_SCHEMA = Path(__file__).resolve().parent / "schemas/expert_annotation.schema.json"
ASSIGNMENT_SCHEMA = Path(__file__).resolve().parent / "schemas/expert_assignment_manifest.schema.json"
METRICS_SCHEMA = Path(__file__).resolve().parent / "schemas/expert_pilot_metrics.schema.json"
POWER_SCHEMA = Path(__file__).resolve().parent / "schemas/power_analysis_input.schema.json"
SLOT_SCHEMA = Path(__file__).resolve().parent / "schemas/expert_pilot_slot_manifest.schema.json"


def pilot_design() -> dict[str, Any]:
    return {
        "protocol_version": PILOT_PROTOCOL_VERSION,
        "target_scene_count": 60,
        "slice_quota": {item: 20 for item in SLICES},
        "outcome_quota": {item: 10 for item in OUTCOMES},
        "independent_reviewers_per_scene": 2,
        "adjudicator_separate": True,
        "calibration_excluded_from_evaluation": True,
        "maximum_guideline_revisions": 2,
        "randomization_seed": 16060,
        "primary_agreement_metric": "KRIPPENDORFF_ALPHA_NOMINAL_APPLICABILITY",
        "minimum_primary_alpha": 0.67,
        "source_complete_only": True,
        "synthetic_required_field_fill_allowed": False,
        "actual_vehicle_validation_required": False,
    }


def build_pilot_slot_manifest() -> dict[str, Any]:
    slots = []
    for slice_index, slice_name in enumerate(SLICES):
        extra_outcomes = {2 * slice_index, 2 * slice_index + 1}
        for outcome_index, outcome in enumerate(OUTCOMES):
            cell_size = 4 if outcome_index in extra_outcomes else 3
            for replicate in range(1, cell_size + 1):
                slots.append({
                    "slot_id": f"M16-S{slice_index + 1}-O{outcome_index + 1}-R{replicate}",
                    "slice": slice_name,
                    "outcome": outcome,
                    "joint_cell_size": cell_size,
                })
    manifest = {
        "slot_manifest_version": "guardsynth-expert-pilot-slots-v0.1",
        "randomization_seed": pilot_design()["randomization_seed"],
        "slot_count": len(slots),
        "slots": slots,
        "source_bindings_included": False,
    }
    validate(manifest, load_json(SLOT_SCHEMA))
    if len({item["slot_id"] for item in slots}) != len(slots):
        raise ValueError("DUPLICATE_PILOT_SLOT_ID")
    return manifest


def build_pilot_preflight(m13_batch_result: dict[str, Any]) -> dict[str, Any]:
    design = pilot_design()
    available = int(m13_batch_result.get("executed_scene_count", 0))
    slice_coverage = m13_batch_result.get("slice_coverage", {})
    outcome_coverage = m13_batch_result.get("outcome_strata", {})
    slice_shortfall = {
        key: max(0, quota - int(slice_coverage.get(key, 0)))
        for key, quota in design["slice_quota"].items()
    }
    outcome_shortfall = {
        key: max(0, quota - int(outcome_coverage.get(key, 0)))
        for key, quota in design["outcome_quota"].items()
    }
    start_allowed = (
        available >= design["target_scene_count"]
        and not any(slice_shortfall.values())
        and not any(outcome_shortfall.values())
        and m13_batch_result.get("gates", {}).get("synthetic_scene_field_fill_zero") is True
    )
    return {
        "protocol_version": PILOT_PROTOCOL_VERSION,
        "status": "READY" if start_allowed else "BLOCKED_DATA_SHORTFALL",
        "annotation_start_allowed": start_allowed,
        "eligible_scene_count": available,
        "target_scene_count": design["target_scene_count"],
        "total_scene_shortfall": max(0, design["target_scene_count"] - available),
        "slice_coverage": {key: int(slice_coverage.get(key, 0)) for key in SLICES},
        "slice_shortfall": slice_shortfall,
        "outcome_coverage": {key: int(outcome_coverage.get(key, 0)) for key in OUTCOMES},
        "outcome_shortfall": outcome_shortfall,
        "reason_codes": [] if start_allowed else [
            "M16_REQUIRES_60_SOURCE_COMPLETE_SCENES",
            "M16_SLICE_QUOTA_NOT_MET",
            "M16_OUTCOME_QUOTA_NOT_MET",
        ],
        "synthetic_scene_fill_performed": False,
        "actual_vehicle_validation_deferred_to_m21": True,
        "claim_scope": "M16_PILOT_PREFLIGHT_NOT_EXPERT_RESULT_OR_VEHICLE_SAFETY",
    }


def validate_expert_annotation(annotation: dict[str, Any]) -> None:
    validate(annotation, load_json(ANNOTATION_SCHEMA))
    confidence = annotation["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or confidence > 1:
        raise ValueError("ANNOTATION_CONFIDENCE_OUT_OF_RANGE")


def build_blinded_assignment_manifest(
    *,
    scene_ref_hashes: list[str],
    reviewer_pseudonyms: list[str],
    adjudicator_pseudonym: str,
    randomization_seed: int = 16060,
    calibration_scene_hashes: set[str] | None = None,
) -> dict[str, Any]:
    if (
        not scene_ref_hashes
        or len(scene_ref_hashes) != len(set(scene_ref_hashes))
        or any(not item for item in scene_ref_hashes)
    ):
        raise ValueError("INVALID_OR_DUPLICATE_SCENE_HASH")
    reviewers = list(reviewer_pseudonyms)
    if (
        len(reviewers) < 2
        or len(reviewers) != len(set(reviewers))
        or adjudicator_pseudonym in reviewers
    ):
        raise ValueError("INVALID_REVIEWER_OR_ADJUDICATOR_SEPARATION")
    if not isinstance(randomization_seed, int) or isinstance(randomization_seed, bool) or randomization_seed < 0:
        raise ValueError("INVALID_RANDOMIZATION_SEED")
    calibration = set(calibration_scene_hashes or ())
    if not calibration.issubset(scene_ref_hashes):
        raise ValueError("UNKNOWN_CALIBRATION_SCENE")

    rng = random.Random(randomization_seed)
    scenes = list(scene_ref_hashes)
    rng.shuffle(scenes)
    reviewer_orders = {reviewer: [] for reviewer in reviewers}
    assignments = []
    for scene_index, scene_hash in enumerate(scenes):
        first = reviewers[scene_index % len(reviewers)]
        second = reviewers[(scene_index + 1) % len(reviewers)]
        modes = (
            ("MINIMAL_CONFIRMATION", "COMPLETE_AUTHORING")
            if scene_index % 2 == 0
            else ("COMPLETE_AUTHORING", "MINIMAL_CONFIRMATION")
        )
        for reviewer, mode in zip((first, second), modes):
            reviewer_orders[reviewer].append((scene_hash, mode))
    for reviewer in reviewers:
        rng.shuffle(reviewer_orders[reviewer])
        for order, (scene_hash, mode) in enumerate(reviewer_orders[reviewer], start=1):
            assignments.append({
                "assignment_id": f"A-{reviewer}-{order:03d}",
                "scene_ref_hash": scene_hash,
                "reviewer_pseudonym": reviewer,
                "interface_mode": mode,
                "presentation_order": order,
                "calibration": scene_hash in calibration,
                "method_identity": "BLINDED",
            })
    assignments.sort(key=lambda item: (item["reviewer_pseudonym"], item["presentation_order"]))
    mode_counts = {
        mode: sum(item["interface_mode"] == mode for item in assignments)
        for mode in ("MINIMAL_CONFIRMATION", "COMPLETE_AUTHORING")
    }
    manifest = {
        "assignment_version": "guardsynth-expert-assignment-v0.1",
        "randomization_seed": randomization_seed,
        "scene_count": len(scenes),
        "reviewer_count": len(reviewers),
        "reviews_per_scene": 2,
        "interface_mode_counts": mode_counts,
        "assignments": assignments,
        "adjudicator_pseudonym": adjudicator_pseudonym,
        "model_identity_exposed": False,
        "raw_scene_identifier_exposed": False,
    }
    validate(manifest, load_json(ASSIGNMENT_SCHEMA))
    return manifest


def annotation_disagreement_reasons(
    left: dict[str, Any], right: dict[str, Any]
) -> tuple[str, ...]:
    validate_expert_annotation(left)
    validate_expert_annotation(right)
    if left["scene_ref_hash"] != right["scene_ref_hash"]:
        raise ValueError("ANNOTATION_SCENE_MISMATCH")
    if left["reviewer_pseudonym"] == right["reviewer_pseudonym"]:
        raise ValueError("ANNOTATIONS_NOT_INDEPENDENT")
    reasons = []
    if left["applicability"] != right["applicability"]:
        reasons.append("APPLICABILITY_DISAGREEMENT")
    for field in ("guard_type", "target_id", "zone_id", "operator", "range", "unit", "coordinate_frame"):
        if left["guard_fields"][field] != right["guard_fields"][field]:
            reasons.append(f"GUARD_FIELD_DISAGREEMENT:{field}")
    if left["source_sufficiency"]["verdict"] != right["source_sufficiency"]["verdict"]:
        reasons.append("SOURCE_SUFFICIENCY_DISAGREEMENT")
    for field in ("activation", "maintain", "release", "reactivation", "expiry", "fallback"):
        if left["lifecycle"][field] != right["lifecycle"][field]:
            reasons.append(f"LIFECYCLE_DISAGREEMENT:{field}")
    return tuple(reasons)


def _nominal_alpha(values_by_scene: list[tuple[str, ...]]) -> float:
    total_pairs = 0
    disagreements = 0
    category_counts: dict[str, int] = {}
    for values in values_by_scene:
        if len(values) < 2:
            raise ValueError("ALPHA_REQUIRES_TWO_RATINGS_PER_SCENE")
        for value in values:
            category_counts[value] = category_counts.get(value, 0) + 1
        for left_index in range(len(values)):
            for right_index in range(left_index + 1, len(values)):
                total_pairs += 1
                disagreements += values[left_index] != values[right_index]
    if not total_pairs:
        raise ValueError("ALPHA_REQUIRES_RATINGS")
    observed = disagreements / total_pairs
    rating_count = sum(category_counts.values())
    if rating_count < 2:
        raise ValueError("ALPHA_REQUIRES_RATINGS")
    expected = 1.0 - sum(
        count * (count - 1) for count in category_counts.values()
    ) / (rating_count * (rating_count - 1))
    if expected == 0:
        return 1.0 if observed == 0 else 0.0
    return 1.0 - observed / expected


def _duration_seconds(annotation: dict[str, Any]) -> float:
    def parse(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    duration = (parse(annotation["completed_at"]) - parse(annotation["started_at"])).total_seconds()
    if duration < 0:
        raise ValueError("ANNOTATION_NEGATIVE_DURATION")
    return duration


def build_expert_pilot_metrics(
    *,
    assignment_manifest: dict[str, Any],
    annotations: list[dict[str, Any]],
    expected_scene_count: int = 60,
    guideline_revision_count: int = 0,
) -> dict[str, Any]:
    validate(assignment_manifest, load_json(ASSIGNMENT_SCHEMA))
    if guideline_revision_count not in {0, 1, 2}:
        raise ValueError("GUIDELINE_REVISION_LIMIT_EXCEEDED")
    assignments = {
        item["assignment_id"]: item
        for item in assignment_manifest["assignments"]
        if not item["calibration"]
    }
    annotations_by_scene: dict[str, list[dict[str, Any]]] = {}
    for annotation in annotations:
        validate_expert_annotation(annotation)
        assignment = assignments.get(annotation["assignment_id"])
        if assignment is None:
            raise ValueError("UNKNOWN_OR_CALIBRATION_ASSIGNMENT")
        if any((
            annotation["reviewer_pseudonym"] != assignment["reviewer_pseudonym"],
            annotation["scene_ref_hash"] != assignment["scene_ref_hash"],
            annotation["interface_mode"] != assignment["interface_mode"],
        )):
            raise ValueError("ANNOTATION_ASSIGNMENT_MISMATCH")
        annotations_by_scene.setdefault(annotation["scene_ref_hash"], []).append(annotation)
    if len(annotations_by_scene) != expected_scene_count or any(
        len(items) != 2 or len({item["reviewer_pseudonym"] for item in items}) != 2
        for items in annotations_by_scene.values()
    ):
        raise ValueError("INCOMPLETE_INDEPENDENT_PILOT_ANNOTATIONS")

    pairs = list(annotations_by_scene.values())
    guard_fields = (
        "guard_type", "target_id", "zone_id", "operator", "range", "unit",
        "coordinate_frame",
    )
    exact = {
        field: sum(pair[0]["guard_fields"][field] == pair[1]["guard_fields"][field] for pair in pairs) / len(pairs)
        for field in guard_fields
    }
    timing: dict[str, list[float]] = {
        "MINIMAL_CONFIRMATION": [], "COMPLETE_AUTHORING": [],
    }
    for annotation in annotations:
        timing[annotation["interface_mode"]].append(_duration_seconds(annotation))
    result = {
        "metrics_version": "guardsynth-expert-pilot-metrics-v0.1",
        "scene_count": len(pairs),
        "annotation_count": len(annotations),
        "applicability_alpha": _nominal_alpha([
            tuple(item["applicability"] for item in pair) for pair in pairs
        ]),
        "field_exact_agreement": exact,
        "source_sufficiency_agreement": sum(
            pair[0]["source_sufficiency"]["verdict"] == pair[1]["source_sufficiency"]["verdict"]
            for pair in pairs
        ) / len(pairs),
        "correction_rate": sum(bool(item["corrections"]) for item in annotations) / len(annotations),
        "timing_by_interface_mode": {
            mode: {
                "count": len(values),
                "mean_seconds": mean(values),
                "median_seconds": median(values),
            }
            for mode, values in timing.items()
        },
        "guideline_revision_count": guideline_revision_count,
        "claim_scope": "M16_EXPERT_PILOT_METRICS_NOT_VEHICLE_SAFETY",
    }
    validate(result, load_json(METRICS_SCHEMA))
    return result


def build_power_planning_record(
    *,
    paired_effect_estimate: float,
    paired_effect_variance: float,
    cluster_size: int,
    intraclass_correlation: float,
    effect_source_ref: str,
    variance_source_ref: str,
) -> dict[str, Any]:
    values = (paired_effect_estimate, paired_effect_variance, intraclass_correlation)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) for value in values):
        raise ValueError("INVALID_POWER_PLANNING_VALUE")
    if paired_effect_estimate == 0 or paired_effect_variance < 0:
        raise ValueError("POWER_PLANNING_REQUIRES_NONZERO_EFFECT_AND_NONNEGATIVE_VARIANCE")
    if not isinstance(cluster_size, int) or isinstance(cluster_size, bool) or cluster_size < 1:
        raise ValueError("INVALID_CLUSTER_SIZE")
    if not 0 <= intraclass_correlation <= 1:
        raise ValueError("INVALID_INTRACLASS_CORRELATION")
    if any(
        not isinstance(item, str) or not item.strip()
        for item in (effect_source_ref, variance_source_ref)
    ):
        raise ValueError("POWER_PLANNING_REQUIRES_SOURCE_REFS")
    design_effect = 1.0 + (cluster_size - 1) * intraclass_correlation
    z_alpha = 1.959963984540054
    z_power = 0.8416212335729143
    required = max(2, ceil(
        ((z_alpha + z_power) ** 2 * paired_effect_variance * design_effect)
        / (paired_effect_estimate ** 2)
    ))
    result = {
        "planning_version": "guardsynth-power-planning-v0.1",
        "paired_effect_estimate": float(paired_effect_estimate),
        "paired_effect_variance": float(paired_effect_variance),
        "cluster_size": cluster_size,
        "intraclass_correlation": float(intraclass_correlation),
        "effect_source_ref": effect_source_ref,
        "variance_source_ref": variance_source_ref,
        "design_effect": design_effect,
        "alpha": 0.05,
        "power": 0.8,
        "required_scene_count": required,
        "method": "PAIRED_NORMAL_APPROXIMATION_WITH_CLUSTER_DESIGN_EFFECT",
        "claim_scope": "PLANNING_APPROXIMATION_REQUIRES_M16_OBSERVED_EFFECT_AND_VARIANCE",
    }
    validate(result, load_json(POWER_SCHEMA))
    return result
