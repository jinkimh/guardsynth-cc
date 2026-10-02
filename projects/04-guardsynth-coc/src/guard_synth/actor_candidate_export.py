"""Fail-closed serialization for obstacle association candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any


class ActorCandidateExportError(ValueError):
    """Raised when a candidate cannot be exported without inventing data."""


def _required_text(values: Mapping[str, Any], name: str) -> str:
    value = values.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ActorCandidateExportError(f"missing {name}")
    return value


def _finite_number(values: Mapping[str, Any], name: str) -> float:
    value = values.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActorCandidateExportError(f"invalid {name}")
    number = float(value)
    if not isfinite(number):
        raise ActorCandidateExportError(f"invalid {name}")
    return number


def _optional_finite_number(values: Mapping[str, Any], name: str) -> float | None:
    value = values.get(name)
    if value is None:
        return None
    return _finite_number(values, name)


def _validated_track_samples(
    track_samples: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not track_samples:
        raise ActorCandidateExportError("track_samples must be nonempty")
    output: list[dict[str, Any]] = []
    previous_timestamp: int | None = None
    for sample in track_samples:
        timestamp = sample.get("timestamp_us")
        if isinstance(timestamp, bool) or not isinstance(timestamp, int):
            raise ActorCandidateExportError("invalid track_samples timestamp_us")
        if previous_timestamp is not None and timestamp <= previous_timestamp:
            raise ActorCandidateExportError("track_samples must be strictly ordered")
        _finite_number(sample, "center_x_m")
        _finite_number(sample, "center_y_m")
        output.append(dict(sample))
        previous_timestamp = timestamp
    return output


def serialize_actor_candidate(
    *,
    row: Mapping[str, Any],
    rates: Mapping[str, Any],
    rank: int,
    track_samples: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Serialize one ranked candidate while retaining its evidence-bearing track."""
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
        raise ActorCandidateExportError("invalid rank")
    track_id = _required_text(row, "track_id")
    label_class = _required_text(row, "label_class")
    gap = _finite_number(row, "longitudinal_gap_m")
    lateral = _finite_number(row, "center_y")
    timestamp_error = row.get("timestamp_error_us")
    if (
        isinstance(timestamp_error, bool)
        or not isinstance(timestamp_error, int)
        or timestamp_error < 0
    ):
        raise ActorCandidateExportError("invalid timestamp_error_us")

    sample_count = rates.get("sample_count", 0)
    if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 0:
        raise ActorCandidateExportError("invalid sample_count")
    gap_rate = _optional_finite_number(rates, "gap_rate_mps")
    closing_speed = _optional_finite_number(rates, "closing_speed_mps")
    if closing_speed is not None and closing_speed < 0:
        raise ActorCandidateExportError("invalid closing_speed_mps")
    ttc = gap / closing_speed if closing_speed is not None and closing_speed > 0 else None

    return {
        "rank_by_longitudinal_gap": rank,
        "track_id": track_id,
        "label_class": label_class,
        "longitudinal_gap_m": round(gap, 6),
        "lateral_center_m": round(lateral, 6),
        "timestamp_error_us": timestamp_error,
        "sample_count": sample_count,
        "gap_rate_mps": None if gap_rate is None else round(gap_rate, 6),
        "closing_speed_mps": (
            None if closing_speed is None else round(closing_speed, 6)
        ),
        "candidate_ttc_s": None if ttc is None else round(ttc, 6),
        "track_samples": _validated_track_samples(track_samples),
    }
