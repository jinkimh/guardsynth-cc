"""Semantic validation for opaque, owner-scoped review sample manifests."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import re


class SampleManifestError(ValueError):
    pass


M16_SLICES = (
    "PEDESTRIAN_CYCLIST_YIELD",
    "STOP_SIGNALS",
    "FOLLOWING_CUT_IN",
)
M16_OUTCOMES = (
    "NOMINAL",
    "HAZARD_TRUE_ACTIVE",
    "UNKNOWN",
    "CONFLICT",
    "RELEASE",
    "REACTIVATION",
)
REQUIRED_SOURCE_FIELDS = (
    "timestamps",
    "ego_pose_speed",
    "actor_control_state",
    "lane_zone_association",
    "conflict_geometry",
    "coordinate_transform",
    "applicable_rule",
    "recorded_rig_binding",
)
SOURCE_CLOSURES = {"SOURCE_COMPLETE", "REVIEW_REQUIRED", "UNSUPPORTED", "CONFLICT"}
REVIEW_TYPES = {
    "M16_SOURCE_REVIEW",
    "M16_EXPERT_PILOT",
    "IMAGE_ONLY_SCENE_REVIEW",
    "ASSOCIATION_LIFECYCLE_REVIEW",
    "SPECIFICATION_INTERFACE_REVIEW",
    "EBLC_LANGUAGE_EVALUATION",
    "PAPER_INTERNAL_CLAIM_REVIEW",
}
_OPAQUE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _manifest_hash(manifest: dict) -> str:
    encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _validate_source_binding(sample_id: str, field: str, value: object) -> None:
    if not isinstance(value, dict) or set(value) != {"source_id", "sha256"}:
        raise SampleManifestError(f"{sample_id}: invalid source binding for {field}")
    source_id = value["source_id"]
    digest = value["sha256"]
    if not isinstance(source_id, str) or not _OPAQUE_ID.fullmatch(source_id):
        raise SampleManifestError(f"{sample_id}: source_id must be opaque for {field}")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise SampleManifestError(f"{sample_id}: invalid source hash for {field}")


def _expected_joint_counts() -> dict[tuple[str, str], int]:
    expected = {}
    for slice_index, slice_name in enumerate(M16_SLICES):
        extra = {2 * slice_index, 2 * slice_index + 1}
        for outcome_index, outcome in enumerate(M16_OUTCOMES):
            expected[(slice_name, outcome)] = 4 if outcome_index in extra else 3
    return expected


def validate_sample_manifest(manifest: dict) -> dict:
    if not isinstance(manifest, dict):
        raise SampleManifestError("sample manifest must be an object")
    required_top = {"schema_version", "project_id", "review_round_id", "review_type", "classification", "samples"}
    if set(manifest) != required_top:
        raise SampleManifestError("sample manifest fields do not match the v1 contract")
    if manifest["schema_version"] != 1:
        raise SampleManifestError("unsupported sample manifest version")
    for key in ("project_id", "review_round_id"):
        if not isinstance(manifest[key], str) or not _OPAQUE_ID.fullmatch(manifest[key]):
            raise SampleManifestError(f"{key} must be an opaque kebab-case id")
    review_type = manifest["review_type"]
    if review_type not in REVIEW_TYPES:
        raise SampleManifestError("unsupported review type")
    if manifest["classification"] not in {"RESTRICTED", "PUBLIC", "INTERMEDIATE"}:
        raise SampleManifestError("unsupported sample classification")
    samples = manifest["samples"]
    if not isinstance(samples, list) or not samples:
        raise SampleManifestError("sample manifest must contain samples")

    allowed_sample = {"sample_id", "slice", "outcome", "source_closure", "required_sources", "reason_codes"}
    preflight_ids = [sample.get("sample_id") for sample in samples if isinstance(sample, dict)]
    duplicate_ids = sorted({item for item in preflight_ids if preflight_ids.count(item) > 1 and isinstance(item, str)})
    if duplicate_ids:
        raise SampleManifestError(f"duplicate sample_id: {duplicate_ids[0]}")
    sample_ids: set[str] = set()
    slice_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    joint_counts: Counter[tuple[str, str]] = Counter()
    source_complete = 0
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != allowed_sample:
            raise SampleManifestError("sample fields do not match the v1 contract")
        sample_id = sample["sample_id"]
        if not isinstance(sample_id, str) or not _OPAQUE_ID.fullmatch(sample_id):
            raise SampleManifestError("sample_id must be opaque kebab-case")
        if sample_id in sample_ids:
            raise SampleManifestError(f"duplicate sample_id: {sample_id}")
        sample_ids.add(sample_id)
        closure = sample["source_closure"]
        if closure not in SOURCE_CLOSURES:
            raise SampleManifestError(f"{sample_id}: invalid source closure")
        reason_codes = sample["reason_codes"]
        if not isinstance(reason_codes, list) or any(not isinstance(item, str) for item in reason_codes):
            raise SampleManifestError(f"{sample_id}: invalid reason codes")
        if review_type == "IMAGE_ONLY_SCENE_REVIEW":
            if closure != "REVIEW_REQUIRED" or "IMAGE_ONLY_CANNOT_ESTABLISH_SOURCE_CLOSURE" not in reason_codes:
                raise SampleManifestError("IMAGE_ONLY_CANNOT_ESTABLISH_SOURCE_CLOSURE")
        bindings = sample["required_sources"]
        if not isinstance(bindings, dict):
            raise SampleManifestError(f"{sample_id}: required_sources must be an object")
        if closure == "SOURCE_COMPLETE":
            if set(bindings) != set(REQUIRED_SOURCE_FIELDS):
                missing = sorted(set(REQUIRED_SOURCE_FIELDS) - set(bindings))
                raise SampleManifestError(f"{sample_id}: missing required source fields: {missing}")
            source_complete += 1
        for field, binding in bindings.items():
            if field not in REQUIRED_SOURCE_FIELDS:
                raise SampleManifestError(f"{sample_id}: unknown required source field: {field}")
            _validate_source_binding(sample_id, field, binding)

        slice_name = sample["slice"]
        outcome = sample["outcome"]
        if not isinstance(slice_name, str) or not isinstance(outcome, str):
            raise SampleManifestError(f"{sample_id}: slice and outcome must be strings")
        if closure == "SOURCE_COMPLETE":
            slice_counts[slice_name] += 1
            outcome_counts[outcome] += 1
            joint_counts[(slice_name, outcome)] += 1

    slice_ready = set(slice_counts) == set(M16_SLICES) and all(slice_counts[item] == 20 for item in M16_SLICES)
    outcome_ready = set(outcome_counts) == set(M16_OUTCOMES) and all(outcome_counts[item] == 10 for item in M16_OUTCOMES)
    joint_ready = dict(joint_counts) == _expected_joint_counts()
    is_m16_empirical = review_type == "M16_EXPERT_PILOT"
    source_cohort_ready = (
        len(samples) == 60 and source_complete == 60 and slice_ready and outcome_ready and joint_ready
    ) if is_m16_empirical else False
    return {
        "manifest_hash": _manifest_hash(manifest),
        "distinct_samples": len(sample_ids),
        "source_complete": source_complete,
        "slice_counts": dict(sorted(slice_counts.items())),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "joint_counts": {f"{key[0]}::{key[1]}": value for key, value in sorted(joint_counts.items())},
        "slice_quota_ready": slice_ready,
        "outcome_quota_ready": outcome_ready,
        "joint_cells_ready": joint_ready,
        "source_cohort_ready": source_cohort_ready,
    }
