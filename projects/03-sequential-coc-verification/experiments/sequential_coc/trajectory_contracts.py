#!/usr/bin/env python3
"""Exploratory longitudinal-action consistency over recorded ego trajectories.

The thresholds in this module parameterize a behavioral abstraction.  They are
not normative safety limits, and the recorded trajectory is not ground truth.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Iterable, Mapping, Sequence

import pandas as pd

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())))

from experiments.sequential_coc.contract_compiler import compile_text
from experiments.sequential_coc.contract_ir import Action, ContractEvent
from experiments.sequential_coc.extract_windows import (
    EGOMOTION_DIR,
    OUTPUT_DIR,
    RawEvent,
    load_local_trajectory_raw_events,
)


TRAJECTORY_RESULTS_PATH = OUTPUT_DIR / "trajectory-results.jsonl"


class ObservedAction(str, Enum):
    STOP_OR_HOLD = "STOP_OR_HOLD"
    YIELD_OR_DECELERATE = "YIELD_OR_DECELERATE"
    MAINTAIN_SPEED = "MAINTAIN_SPEED"
    ACCELERATE_OR_PROCEED = "ACCELERATE_OR_PROCEED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ActionThresholds:
    name: str
    response_deadline_s: float
    window_s: float
    minimum_speed_delta_mps: float
    minimum_direction_fraction: float
    stopped_speed_threshold_mps: float

    def __post_init__(self) -> None:
        if self.name not in {"baseline", "strict", "lenient"}:
            raise ValueError("threshold name must be baseline, strict, or lenient")
        for name in (
            "response_deadline_s",
            "window_s",
            "minimum_speed_delta_mps",
            "stopped_speed_threshold_mps",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not math.isfinite(float(value)) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not 0 < self.minimum_direction_fraction <= 1:
            raise ValueError("minimum_direction_fraction must be in (0, 1]")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "response_deadline_s": self.response_deadline_s,
            "window_s": self.window_s,
            "minimum_speed_delta_mps": self.minimum_speed_delta_mps,
            "minimum_direction_fraction": self.minimum_direction_fraction,
            "stopped_speed_threshold_mps": self.stopped_speed_threshold_mps,
        }


# Existing defaults: projects/03-sequential-coc-verification/experiments/feasibility/check_cohort.py and KIEE block B.
# Strict/lenient use the endpoints of that implementation's 27-profile grid.
# The post-hoc 0.5 m/s stop helper is held fixed instead of generalized.
BASELINE_THRESHOLDS = ActionThresholds("baseline", 3.0, 0.5, 0.1, 0.7, 0.5)
STRICT_THRESHOLDS = ActionThresholds("strict", 3.0, 0.25, 0.2, 0.9, 0.5)
LENIENT_THRESHOLDS = ActionThresholds("lenient", 3.0, 1.0, 0.05, 0.5, 0.5)
THRESHOLD_SETS = (BASELINE_THRESHOLDS, STRICT_THRESHOLDS, LENIENT_THRESHOLDS)
THRESHOLD_PROVENANCE = {
    "baseline_code": "projects/03-sequential-coc-verification/experiments/feasibility/check_cohort.py",
    "baseline_paper": (
        "projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/"
        "sections/06-experiments.tex"
    ),
    "parameter_semantics": "BEHAVIORAL_ABSTRACTION_NOT_NORMATIVE_SAFETY_CRITERIA",
    "sensitivity_selection": "ENDPOINTS_OF_EXISTING_27_PROFILE_GRID",
    "excluded_separate_default": (
        "13-chain W=1.0s/delta=0.7mps implementation is explicitly excluded "
        "from the shared quantitative condition in KIEE block C"
    ),
}


@dataclass(frozen=True, slots=True)
class _EgoSample:
    timestamp_us: int
    signed_longitudinal_speed_mps: float


@dataclass(frozen=True, slots=True)
class TrajectoryResult:
    verdict: str
    reason: str
    observed_action: ObservedAction

    def __post_init__(self) -> None:
        if self.verdict not in {"ALIGNED", "NOT_ALIGNED", "UNKNOWN"}:
            raise ValueError("verdict must be ALIGNED, NOT_ALIGNED, or UNKNOWN")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string")
        if not isinstance(self.observed_action, ObservedAction):
            object.__setattr__(self, "observed_action", ObservedAction(self.observed_action))

    def to_dict(self) -> dict[str, str]:
        return {
            "verdict": self.verdict,
            "reason": self.reason,
            "observed_action": self.observed_action.value,
        }


def _normalize_trace(ego_trace: Iterable[Mapping[str, object] | _EgoSample]) -> tuple[_EgoSample, ...]:
    samples: list[_EgoSample] = []
    for value in ego_trace:
        if isinstance(value, _EgoSample):
            sample = value
        elif isinstance(value, Mapping):
            if "timestamp_us" not in value or "signed_longitudinal_speed_mps" not in value:
                raise ValueError("SIGNED_LONGITUDINAL_TRACE_REQUIRED")
            timestamp = value["timestamp_us"]
            speed = value["signed_longitudinal_speed_mps"]
            if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
                raise ValueError("SIGNED_LONGITUDINAL_TRACE_REQUIRED")
            if isinstance(speed, bool) or not isinstance(speed, (int, float)):
                raise ValueError("SIGNED_LONGITUDINAL_TRACE_REQUIRED")
            if not math.isfinite(float(timestamp)) or not math.isfinite(float(speed)):
                raise ValueError("SIGNED_LONGITUDINAL_TRACE_REQUIRED")
            sample = _EgoSample(round(float(timestamp)), float(speed))
        else:
            raise ValueError("SIGNED_LONGITUDINAL_TRACE_REQUIRED")
        samples.append(sample)
    if len(samples) < 2:
        raise ValueError("SIGNED_LONGITUDINAL_TRACE_REQUIRED")
    timestamps = [sample.timestamp_us for sample in samples]
    if any(left >= right for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("TRACE_TIMESTAMPS_NOT_STRICTLY_INCREASING")
    return tuple(samples)


def _directional_onset(
    samples: Sequence[_EgoSample], thresholds: ActionThresholds, sign: int
) -> int | None:
    trace_start = samples[0].timestamp_us
    latest_onset = trace_start + round(thresholds.response_deadline_s * 1_000_000)
    window_us = round(thresholds.window_s * 1_000_000)
    for index, candidate in enumerate(samples):
        if candidate.timestamp_us > latest_onset:
            break
        window = [
            sample
            for sample in samples[index:]
            if sample.timestamp_us <= candidate.timestamp_us + window_us
        ]
        if len(window) < 2:
            continue
        signed_delta = sign * (
            window[-1].signed_longitudinal_speed_mps
            - window[0].signed_longitudinal_speed_mps
        )
        signed_steps = [
            sign
            * (
                right.signed_longitudinal_speed_mps
                - left.signed_longitudinal_speed_mps
            )
            for left, right in zip(window, window[1:])
        ]
        fraction = sum(step > 0 for step in signed_steps) / len(signed_steps)
        if (
            signed_delta + 1e-12 >= thresholds.minimum_speed_delta_mps
            and fraction + 1e-12 >= thresholds.minimum_direction_fraction
        ):
            return candidate.timestamp_us
    return None


def _classify_normalized(
    samples: Sequence[_EgoSample], thresholds: ActionThresholds
) -> ObservedAction:
    decelerate_onset = _directional_onset(samples, thresholds, -1)
    accelerate_onset = _directional_onset(samples, thresholds, 1)
    if decelerate_onset is not None or accelerate_onset is not None:
        if decelerate_onset == accelerate_onset:
            return ObservedAction.UNKNOWN
        if accelerate_onset is None or (
            decelerate_onset is not None and decelerate_onset < accelerate_onset
        ):
            return ObservedAction.YIELD_OR_DECELERATE
        return ObservedAction.ACCELERATE_OR_PROCEED

    speeds = [sample.signed_longitudinal_speed_mps for sample in samples]
    if max(abs(speed) for speed in speeds) <= thresholds.stopped_speed_threshold_mps:
        return ObservedAction.STOP_OR_HOLD
    if max(speeds) - min(speeds) + 1e-12 < thresholds.minimum_speed_delta_mps:
        return ObservedAction.MAINTAIN_SPEED
    return ObservedAction.UNKNOWN


def classify_observed_action(
    ego_trace: Iterable[Mapping[str, object] | _EgoSample],
    thresholds: ActionThresholds,
) -> ObservedAction:
    """Classify recorded behavior using signed longitudinal speed and nothing else."""
    if not isinstance(thresholds, ActionThresholds):
        raise TypeError("thresholds must be ActionThresholds")
    try:
        samples = _normalize_trace(ego_trace)
    except ValueError:
        return ObservedAction.UNKNOWN
    return _classify_normalized(samples, thresholds)


def _trace_for_event(
    samples: Sequence[_EgoSample], event_timestamp_us: int, thresholds: ActionThresholds
) -> tuple[_EgoSample, ...]:
    end_us = event_timestamp_us + round(
        (thresholds.response_deadline_s + thresholds.window_s) * 1_000_000
    )
    return tuple(
        sample
        for sample in samples
        if event_timestamp_us <= sample.timestamp_us <= end_us
    )


def _unknown(reason: str) -> TrajectoryResult:
    return TrajectoryResult("UNKNOWN", reason, ObservedAction.UNKNOWN)


def evaluate_trajectory_contract(
    events: Sequence[ContractEvent],
    ego_trace: Iterable[Mapping[str, object] | _EgoSample],
    thresholds: ActionThresholds,
) -> TrajectoryResult:
    """Compare one explicit source-event contract with recorded longitudinal behavior."""
    if not events:
        return _unknown("NO_SUPPORTED_LONGITUDINAL_ACTION")
    if any(not isinstance(event, ContractEvent) for event in events):
        raise TypeError("events must contain ContractEvent values")
    if len({event.scene_id for event in events}) != 1:
        return _unknown("SCENE_IDENTITY_MISMATCH")
    if any(event.parse_status != "PARSED" for event in events):
        return _unknown("CONTRACT_PARSE_UNKNOWN")
    if len(events) != 1:
        return _unknown("PHASE_TIMING_EVIDENCE_REQUIRED")

    try:
        normalized = _normalize_trace(ego_trace)
    except ValueError as exc:
        return _unknown(str(exc))
    selected = _trace_for_event(normalized, events[0].timestamp_us, thresholds)
    if len(selected) < 2:
        return _unknown("EGOMOTION_WINDOW_UNAVAILABLE")
    observed = _classify_normalized(selected, thresholds)
    if observed is ObservedAction.UNKNOWN:
        return TrajectoryResult("UNKNOWN", "OBSERVED_ACTION_UNKNOWN", observed)

    expected = events[0].action
    if (
        expected in {Action.STOP_OR_HOLD, Action.YIELD_OR_DECELERATE}
        and observed is ObservedAction.ACCELERATE_OR_PROCEED
    ):
        if not events[0].release_known:
            return TrajectoryResult("UNKNOWN", "RELEASE_EVIDENCE_REQUIRED", observed)
        if not events[0].release_value:
            return TrajectoryResult(
                "NOT_ALIGNED", "LONGITUDINAL_ACTION_MISMATCH", observed
            )
        if events[0].permitted_next_action is Action.ACCELERATE_OR_PROCEED:
            return TrajectoryResult("ALIGNED", "RELEASE_CONFIRMED", observed)
        return TrajectoryResult("UNKNOWN", "PERMITTED_NEXT_ACTION_REQUIRED", observed)

    negative_actions = {
        ObservedAction.STOP_OR_HOLD,
        ObservedAction.YIELD_OR_DECELERATE,
    }
    if expected in {Action.STOP_OR_HOLD, Action.YIELD_OR_DECELERATE}:
        aligned = observed in negative_actions
    else:
        aligned = expected.value == observed.value
    return TrajectoryResult(
        "ALIGNED" if aligned else "NOT_ALIGNED",
        "ACTION_MATCH" if aligned else "LONGITUDINAL_ACTION_MISMATCH",
        observed,
    )


def _source_event_id(scene_id: str, event: RawEvent) -> str:
    canonical = json.dumps(
        {
            "scene_id": scene_id,
            "timestamp_us": event.timestamp_us,
            "original_position": event.original_position,
            "source_text_sha256": event.source_text_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_scene_trace(scene_id: str, directory: Path) -> tuple[_EgoSample, ...]:
    path = directory / f"{scene_id}.egomotion.parquet"
    if not path.is_file():
        raise FileNotFoundError("EGOMOTION_FILE_NOT_FOUND")
    frame = pd.read_parquet(path, columns=["timestamp", "vx"]).sort_values("timestamp")
    return tuple(
        _EgoSample(int(row.timestamp), float(row.vx))
        for row in frame.itertuples(index=False)
    )


def _aggregate_scene_verdict(event_verdicts: Sequence[str]) -> tuple[str, str]:
    if "NOT_ALIGNED" in event_verdicts:
        return "NOT_ALIGNED", "EVENT_NOT_ALIGNED_PRESENT"
    if "UNKNOWN" in event_verdicts:
        return "UNKNOWN", "EVENT_UNKNOWN_PRESENT"
    return "ALIGNED", "ALL_EVENT_ACTIONS_ALIGNED"


def build_trajectory_records(
    scene_events: Mapping[str, Sequence[RawEvent]],
    egomotion_dir: Path = EGOMOTION_DIR,
) -> list[dict[str, object]]:
    """Build text-free event and scene-cluster records with identity deduplication."""
    event_records: list[dict[str, object]] = []
    scene_records: list[dict[str, object]] = []
    seen: set[tuple[str, int, int, str]] = set()
    link_failures: Counter[str] = Counter()

    for scene_id in sorted(scene_events):
        try:
            ego_trace = _load_scene_trace(scene_id, egomotion_dir)
            trace_error = None
        except (FileNotFoundError, KeyError, ValueError, TypeError):
            ego_trace = ()
            trace_error = "EGOMOTION_FILE_OR_SCHEMA_UNAVAILABLE"

        current_scene_records: list[dict[str, object]] = []
        for source in sorted(
            scene_events[scene_id], key=lambda item: (item.timestamp_us, item.original_position)
        ):
            identity = (
                scene_id,
                source.timestamp_us,
                source.original_position,
                source.source_text_sha256,
            )
            if identity in seen:
                continue
            seen.add(identity)
            source_id = _source_event_id(scene_id, source)
            link_reason = trace_error
            if link_reason is None and (
                not ego_trace
                or source.timestamp_us < ego_trace[0].timestamp_us
                or source.timestamp_us > ego_trace[-1].timestamp_us
            ):
                link_reason = "EVENT_TIMESTAMP_OUTSIDE_EGOMOTION"

            if link_reason is None:
                compiled = compile_text(
                    source.source_text, source_id, scene_id, source.timestamp_us
                )
                threshold_results = {
                    threshold.name: evaluate_trajectory_contract(
                        compiled, ego_trace, threshold
                    ).to_dict()
                    for threshold in THRESHOLD_SETS
                }
                link_status = "LINKED"
            else:
                link_failures[link_reason] += 1
                threshold_results = {
                    threshold.name: _unknown(link_reason).to_dict()
                    for threshold in THRESHOLD_SETS
                }
                link_status = "NOT_LINKED"

            baseline_verdict = threshold_results["baseline"]["verdict"]
            changed_profiles = [
                threshold.name
                for threshold in THRESHOLD_SETS
                if threshold_results[threshold.name]["verdict"] != baseline_verdict
            ]
            record: dict[str, object] = {
                "record_type": "sample",
                "sample_unit": "event",
                "scene_cluster_id": scene_id,
                "event_id": source_id,
                "timestamp_us": source.timestamp_us,
                "link_status": link_status,
                "link_failure_reason": link_reason,
                "threshold_results": threshold_results,
                "verdict_changed_from_baseline": changed_profiles,
            }
            event_records.append(record)
            current_scene_records.append(record)

        if not current_scene_records:
            continue
        scene_threshold_results: dict[str, dict[str, str]] = {}
        for threshold in THRESHOLD_SETS:
            verdict, reason = _aggregate_scene_verdict(
                [
                    str(record["threshold_results"][threshold.name]["verdict"])  # type: ignore[index]
                    for record in current_scene_records
                ]
            )
            scene_threshold_results[threshold.name] = {
                "verdict": verdict,
                "reason": reason,
            }
        baseline_verdict = scene_threshold_results["baseline"]["verdict"]
        scene_records.append(
            {
                "record_type": "sample",
                "sample_unit": "scene_cluster",
                "scene_cluster_id": scene_id,
                "event_count": len(current_scene_records),
                "link_failure_reasons": dict(
                    sorted(
                        Counter(
                            str(record["link_failure_reason"])
                            for record in current_scene_records
                            if record["link_failure_reason"] is not None
                        ).items()
                    )
                ),
                "threshold_results": scene_threshold_results,
                "verdict_changed_from_baseline": [
                    threshold.name
                    for threshold in THRESHOLD_SETS
                    if scene_threshold_results[threshold.name]["verdict"]
                    != baseline_verdict
                ],
            }
        )

    event_verdict_counts = {
        threshold.name: dict(
            sorted(
                Counter(
                    str(record["threshold_results"][threshold.name]["verdict"])  # type: ignore[index]
                    for record in event_records
                ).items()
            )
        )
        for threshold in THRESHOLD_SETS
    }
    scene_verdict_counts = {
        threshold.name: dict(
            sorted(
                Counter(
                    str(record["threshold_results"][threshold.name]["verdict"])  # type: ignore[index]
                    for record in scene_records
                ).items()
            )
        )
        for threshold in THRESHOLD_SETS
    }
    summary: dict[str, object] = {
        "sample_units": {
            "event": len(event_records),
            "scene_cluster": len(scene_records),
        },
        "linked_event_count": sum(record["link_status"] == "LINKED" for record in event_records),
        "link_failure_reasons": dict(sorted(link_failures.items())),
        "verdict_counts": {
            "event": event_verdict_counts,
            "scene_cluster": scene_verdict_counts,
        },
        "verdict_change_counts": {
            "event": sum(bool(record["verdict_changed_from_baseline"]) for record in event_records),
            "scene_cluster": sum(
                bool(record["verdict_changed_from_baseline"]) for record in scene_records
            ),
        },
        # Text-free, restricted scene records permit an auditable join with
        # the independently reviewed scene-cluster sample.  They are not
        # public data and contain neither CoC text nor trajectory samples.
        "scene_records": [
            {
                "scene_cluster_id": record["scene_cluster_id"],
                "event_count": record["event_count"],
                "threshold_results": record["threshold_results"],
                "verdict_changed_from_baseline": record[
                    "verdict_changed_from_baseline"
                ],
            }
            for record in scene_records
        ],
    }
    return [summary]


def write_trajectory_records(
    records: Sequence[Mapping[str, object]], path: Path = TRAJECTORY_RESULTS_PATH
) -> None:
    """Atomically publish text-free JSONL under restricted modes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    payload = "".join(
        json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
        for record in records
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, path)
        path.chmod(0o600)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-results", action="store_true", required=True)
    parser.parse_args()
    records = build_trajectory_records(load_local_trajectory_raw_events())
    write_trajectory_records(records)
    print(json.dumps(records[0], sort_keys=True))


if __name__ == "__main__":
    main()
