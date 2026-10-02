"""Source-bearing transform and rig binding records for NVIDIA derived scenes."""

from __future__ import annotations

import hashlib
import json
from math import isfinite
from typing import Any, Mapping, Sequence


SOURCE_BUNDLE_VERSION = "guardsynth-nvidia-scene-source-bundle-v0.1"


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_coordinate_transform(
    *,
    transform: Any,
    source_frame: str,
    target_frame: str,
    event_timestamp_us: int,
    t0_us: int,
    evidence_refs: Sequence[str],
) -> dict[str, Any]:
    """Serialize and numerically validate a scipy-compatible rigid transform."""
    matrix = transform.as_matrix()
    inverse = transform.inv().as_matrix()
    product = matrix @ inverse
    closure_error = max(
        abs(float(product[row, column]) - float(row == column))
        for row in range(4)
        for column in range(4)
    )
    values = [float(value) for value in matrix.reshape(-1)]
    if (
        not source_frame
        or not target_frame
        or not evidence_refs
        or any(not isinstance(ref, str) or not ref for ref in evidence_refs)
        or any(not isfinite(value) for value in values)
        or closure_error > 1e-9
    ):
        raise ValueError("INVALID_SOURCE_BEARING_COORDINATE_TRANSFORM")
    return {
        "status": "AVAILABLE_SOURCE_LINKED",
        "source_frame": source_frame,
        "target_frame": target_frame,
        "event_timestamp_us": event_timestamp_us,
        "t0_us": t0_us,
        "matrix_4x4": [[float(value) for value in row] for row in matrix],
        "inverse_closure_max_abs_error": closure_error,
        "evidence_refs": list(evidence_refs),
        "derivation": "INVERSE_T0_EGOMOTION_COMPOSED_WITH_EVENT_EGOMOTION",
    }


def build_vehicle_binding(
    *,
    clip_id_sha256: str,
    dataset_revision: str,
    platform_class: str,
    radar_config: str,
    vehicle_dimensions: Mapping[str, float],
    calibration_digest: str,
    evidence_refs: Sequence[str],
) -> dict[str, Any]:
    """Bind one dataset clip to its recorded rig configuration, never to a VIN."""
    values = {
        "clip_id_sha256": clip_id_sha256,
        "dataset_revision": dataset_revision,
        "platform_class": platform_class,
        "radar_config": radar_config,
        "vehicle_dimensions": dict(vehicle_dimensions),
        "calibration_digest": calibration_digest,
    }
    if (
        any(not isinstance(value, str) or not value for value in (
            clip_id_sha256, dataset_revision, platform_class, radar_config,
            calibration_digest,
        ))
        or any(not isinstance(ref, str) or not ref for ref in evidence_refs)
        or any(not isfinite(float(value)) for value in vehicle_dimensions.values())
    ):
        raise ValueError("INVALID_DATASET_RIG_CONFIGURATION_BINDING")
    return {
        "status": "AVAILABLE_SOURCE_LINKED",
        "vehicle_binding_key": f"nvidia-rig-config-sha256:{_digest(values)}",
        "binding_scope": "DATASET_CLIP_RIG_CONFIGURATION_NOT_VIN",
        "components": values,
        "evidence_refs": list(evidence_refs),
    }

