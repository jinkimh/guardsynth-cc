"""Bounded nuScenes vehicle-monitor example; source observations, never labels."""

from bisect import bisect_right
from copy import deepcopy
import math
import re

from .common import StudioError, dumps

SIGNALS = {"vehicle_speed_kmh": (0, 250), "brake_pressure_bar": (0, 126),
           "throttle_permille": (0, 1000), "steering_deg": (-780, 780)}
MAX_AGE_US = 600000  # 2 Hz vehicle_monitor; older observations remain unknown.


def validate(value, video):
    fields = {"schema_version", "dataset", "scene_id", "video_sha256", "source_sha256",
              "clock_origin_utime", "transmission_approved", "samples"}
    if not isinstance(value, dict) or set(value) != fields:
        raise StudioError("VEHICLE_STATE_SCHEMA", "Closed vehicle-monitor schema required")
    if (value["schema_version"] != 1 or value["dataset"] != "nuscenes-can-bus"
            or not isinstance(value["scene_id"], str) or not re.fullmatch(r"scene-\d{4}", value["scene_id"])
            or value["video_sha256"] != video["original_sha256"]
            or value["transmission_approved"] is not True
            or type(value["clock_origin_utime"]) is not int or value["clock_origin_utime"] <= 0
            or not isinstance(value["source_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["source_sha256"])):
        raise StudioError("VEHICLE_STATE_BINDING", "Video, source, clock and transmission approval required")
    rows = value["samples"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2000:
        raise StudioError("VEHICLE_STATE_SIZE", "Bounded vehicle-monitor rows required")
    previous = None
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"timestamp_us", *SIGNALS}
                or type(row["timestamp_us"]) is not int
                or (previous is not None and row["timestamp_us"] <= previous)):
            raise StudioError("VEHICLE_STATE_SCHEMA", "Strictly increasing measured timestamps required")
        previous = row["timestamp_us"]
        for key, (low, high) in SIGNALS.items():
            v = row[key]
            if type(v) not in (int, float) or not math.isfinite(v) or not low <= v <= high:
                raise StudioError("VEHICLE_STATE_SCHEMA", "Finite values in documented units required")
    if len(dumps(value).encode()) > 256 * 1024:
        raise StudioError("VEHICLE_STATE_SIZE", "Bounded vehicle-monitor rows required")


def causal_projection(value, frames):
    rows = value["samples"]
    times = [r["timestamp_us"] for r in rows]
    selected = []
    for frame in frames:
        timestamp = frame["timestamp_us"]
        index = bisect_right(times, timestamp) - 1
        age = timestamp - times[index] if index >= 0 else None
        sample = deepcopy(rows[index]) if age is not None and age <= MAX_AGE_US else None
        selected.append({"frame_timestamp_us": timestamp, "sample": sample,
                         "age_us": age if sample else None})
    return {**{k: value[k] for k in ("dataset", "scene_id", "source_sha256", "clock_origin_utime")},
            "interpretation": "Measured history; not intended action, causal proof, or guaranteed braking performance.",
            "alignment": "Latest measurement at or before each image; no future interpolation; max age 600000 us.",
            "frames": selected}
