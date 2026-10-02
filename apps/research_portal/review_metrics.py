"""Versioned review progress and agreement calculations."""

from __future__ import annotations

from collections import Counter
from itertools import permutations
from statistics import mean, median
from typing import Iterable, Mapping


AGREEMENT_CONTRACT_VERSION = "nominal-krippendorff-alpha-v1"
M16_PROGRESS_CONTRACT_VERSION = "m16-start-gate-v1"


def nominal_krippendorff_alpha(items: Mapping[str, Iterable[str | None]]) -> dict:
    """Calculate nominal alpha while reporting exclusions and degenerate data."""
    usable: list[list[str]] = []
    missing = 0
    excluded = 0
    for responses in items.values():
        raw = list(responses)
        missing += sum(value is None for value in raw)
        values = [value for value in raw if value is not None]
        if len(values) < 2:
            excluded += 1
            continue
        usable.append(values)

    categories = Counter(value for values in usable for value in values)
    ratings = sum(categories.values())
    if ratings < 2 or len(categories) < 2:
        return {
            "contract_version": AGREEMENT_CONTRACT_VERSION,
            "status": "NOT_ESTIMABLE_NO_CATEGORY_VARIANCE",
            "alpha": None,
            "included_items": len(usable),
            "excluded_items": excluded,
            "missing_responses": missing,
            "category_counts": dict(sorted(categories.items())),
        }

    observed_disagreements = 0.0
    observed_ratings = 0
    for values in usable:
        observed_ratings += len(values)
        for left, right in permutations(values, 2):
            observed_disagreements += (left != right) / (len(values) - 1)
    observed = observed_disagreements / observed_ratings
    expected_disagreements = sum(
        left_count * right_count
        for left, left_count in categories.items()
        for right, right_count in categories.items()
        if left != right
    )
    expected = expected_disagreements / (ratings * (ratings - 1))
    alpha = 1.0 - observed / expected
    return {
        "contract_version": AGREEMENT_CONTRACT_VERSION,
        "status": "ESTIMATED",
        "alpha": alpha,
        "observed_disagreement": observed,
        "expected_disagreement": expected,
        "included_items": len(usable),
        "excluded_items": excluded,
        "missing_responses": missing,
        "category_counts": dict(sorted(categories.items())),
    }


def review_progress(*, assigned: int, finalized: int) -> dict:
    if assigned < 0 or finalized < 0 or finalized > assigned:
        raise ValueError("invalid review progress counts")
    return {
        "assigned": assigned,
        "finalized": finalized,
        "fraction": finalized / assigned if assigned else None,
    }


def categorical_agreement(items: Mapping[str, Iterable[str | None]]) -> dict:
    included = 0
    excluded = 0
    exact = 0
    matrix: dict[str, dict[str, int]] = {}
    for responses in items.values():
        values = list(responses)
        if len(values) < 2 or values[0] is None or values[1] is None:
            excluded += 1
            continue
        left, right = values[0], values[1]
        included += 1
        exact += left == right
        matrix.setdefault(left, {})[right] = matrix.setdefault(left, {}).get(right, 0) + 1
    return {
        "contract_version": "categorical-exact-confusion-v1",
        "included_items": included,
        "excluded_items": excluded,
        "exact_fraction": exact / included if included else None,
        "confusion_matrix": {left: dict(sorted(row.items())) for left, row in sorted(matrix.items())},
    }


def interval_agreement(pairs: Iterable[tuple[Mapping[str, object], Mapping[str, object]]]) -> dict:
    ious: list[float] = []
    mismatches = 0
    non_overlaps = 0
    for left, right in pairs:
        if left.get("unit") != right.get("unit") or left.get("frame") != right.get("frame"):
            mismatches += 1
            continue
        try:
            left_low, left_high = float(left["low"]), float(left["high"])
            right_low, right_high = float(right["low"]), float(right["high"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("interval requires numeric low/high") from exc
        if left_low > left_high or right_low > right_high:
            raise ValueError("interval low cannot exceed high")
        intersection = max(0.0, min(left_high, right_high) - max(left_low, right_low))
        union = max(left_high, right_high) - min(left_low, right_low)
        iou = 1.0 if union == 0 and left_low == right_low else intersection / union if union else 0.0
        ious.append(iou)
        non_overlaps += intersection == 0 and not (union == 0 and left_low == right_low)
    return {
        "contract_version": "numeric-interval-iou-v1",
        "included_items": len(ious),
        "unit_or_frame_mismatch": mismatches,
        "overlap_fraction": (len(ious) - non_overlaps) / len(ious) if ious else None,
        "mean_iou": mean(ious) if ious else None,
    }


def source_set_agreement(pairs: Iterable[tuple[set[str], set[str]]]) -> dict:
    exact = 0
    jaccards: list[float] = []
    count = 0
    for left, right in pairs:
        if any("/" in item or "\\" in item for item in left | right):
            raise ValueError("source agreement accepts normalized source ids, not paths")
        count += 1
        exact += left == right
        union = left | right
        jaccards.append(len(left & right) / len(union) if union else 1.0)
    return {
        "contract_version": "source-id-set-agreement-v1",
        "included_items": count,
        "exact_fraction": exact / count if count else None,
        "mean_jaccard": mean(jaccards) if jaccards else None,
    }


def correction_rates(pairs: Iterable[tuple[Mapping[str, object], Mapping[str, object]]]) -> dict:
    scenes = 0
    corrected_scenes = 0
    comparable_fields = 0
    corrected_fields = 0
    for original, final in pairs:
        scenes += 1
        scene_changed = False
        for field in sorted(set(original) & set(final)):
            comparable_fields += 1
            if original[field] != final[field]:
                corrected_fields += 1
                scene_changed = True
        corrected_scenes += scene_changed
    return {
        "contract_version": "adjudicated-correction-rate-v1",
        "adjudicated_scenes": scenes,
        "comparable_fields": comparable_fields,
        "scene_correction_rate": corrected_scenes / scenes if scenes else None,
        "field_correction_rate": corrected_fields / comparable_fields if comparable_fields else None,
    }


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def reviewer_time_summary(records: Iterable[Mapping[str, object]], *, idle_timeout_seconds: float) -> dict:
    if idle_timeout_seconds <= 0:
        raise ValueError("idle timeout must be positive")
    groups = {"calibration": [], "empirical": []}
    excluded = {"calibration": 0, "empirical": 0}
    for record in records:
        seconds = record.get("active_seconds")
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or seconds < 0:
            raise ValueError("active_seconds must be non-negative")
        group = "calibration" if record.get("calibration") is True else "empirical"
        if seconds > idle_timeout_seconds and record.get("server_idle_filtered") is not True:
            excluded[group] += 1
        else:
            groups[group].append(float(seconds))
    result = {"contract_version": "server-active-time-v1", "idle_timeout_seconds": idle_timeout_seconds}
    for group, values in groups.items():
        result[group] = {
            "included": len(values),
            "idle_excluded": excluded[group],
            "median": median(values) if values else None,
            "q1": _percentile(values, 0.25),
            "q3": _percentile(values, 0.75),
            "p90": _percentile(values, 0.90),
        }
    return result


def round_progress(
    *,
    assigned: int,
    finalized: int,
    total_samples: int,
    samples_with_required_reviews: int,
    disagreement_samples_ready: int,
    adjudicated_disagreements: int,
) -> dict:
    return {
        "contract_version": "separate-round-progress-v1",
        "reviewer_progress": review_progress(assigned=assigned, finalized=finalized),
        "independent_scene_progress": review_progress(
            assigned=total_samples, finalized=samples_with_required_reviews
        ),
        "adjudication_progress": review_progress(
            assigned=disagreement_samples_ready, finalized=adjudicated_disagreements
        ),
    }


def m16_start_gate(
    *,
    distinct_eligible: int,
    slice_counts: Mapping[str, int],
    outcome_counts: Mapping[str, int],
    joint_cells_ready: bool,
    source_complete: int,
    schema_ui_export_validated: bool,
    assignments_valid: bool,
    calibration_complete: bool,
    reviewer_training_complete: bool,
    baseline_model_split_manifest_frozen: bool,
    guideline_revision_count: int,
) -> dict:
    slice_quota_ready = len(slice_counts) == 3 and all(value == 20 for value in slice_counts.values())
    outcome_quota_ready = bool(outcome_counts) and all(value == 10 for value in outcome_counts.values())
    source_cohort_ready = (
        distinct_eligible == 60
        and slice_quota_ready
        and outcome_quota_ready
        and joint_cells_ready
        and source_complete == 60
    )
    calibration_start = source_cohort_ready and schema_ui_export_validated and assignments_valid
    empirical_start = (
        calibration_start
        and calibration_complete
        and reviewer_training_complete
        and baseline_model_split_manifest_frozen
        and guideline_revision_count <= 2
    )
    return {
        "contract_version": M16_PROGRESS_CONTRACT_VERSION,
        "source_cohort_ready": source_cohort_ready,
        "calibration_start_allowed": calibration_start,
        "empirical_annotation_start_allowed": empirical_start,
        "eligible_shortfall": max(0, 60 - distinct_eligible),
        "source_complete_shortfall": max(0, 60 - source_complete),
        "slice_quota_ready": slice_quota_ready,
        "outcome_quota_ready": outcome_quota_ready,
        "joint_cells_ready": joint_cells_ready,
    }
