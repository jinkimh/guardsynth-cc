#!/usr/bin/env python3
"""Analyze one licensed NVIDIA OOD reasoning episode against egomotion."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from physical_ai_av import PhysicalAIAVDatasetInterface


ROOT = Path("data/restricted/nvidia_physicalai")
DEFAULT_CLIP_ID = "caf6ea10-fc2b-47d1-814c-67c73b6cea9f"
WINDOW_US = 500_000
DEADLINE_US = 1_000_000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_egomotion(
    clip_id: str, root: Path
) -> tuple[pd.DataFrame, dict[str, object]]:
    interface = PhysicalAIAVDatasetInterface(
        local_dir=root.resolve(), confirm_download_threshold_gb=float("inf")
    )
    feature = interface.features.LABELS.EGOMOTION
    chunk = int(interface.get_clip_chunk(clip_id))
    chunk_file = interface.features.get_chunk_feature_filename(chunk, feature)
    member = interface.features.get_clip_files_in_zip(clip_id, feature)["egomotion"]
    with interface.open_file(chunk_file, maybe_stream=True) as source:
        with zipfile.ZipFile(source) as archive:
            raw = archive.read(member)
    frame = pd.read_parquet(io.BytesIO(raw)).sort_values("timestamp").copy()
    return frame, {
        "chunk": chunk,
        "chunk_file": chunk_file,
        "archive_member": member,
        "extracted_bytes": len(raw),
    }


def add_motion_signals(frame: pd.DataFrame) -> pd.DataFrame:
    frame["speed_mps"] = np.hypot(frame["vx"], frame["vy"])
    qx, qy, qz, qw = (frame[column].to_numpy() for column in ("qx", "qy", "qz", "qw"))
    frame["yaw_rad"] = np.unwrap(
        np.arctan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
    )
    return frame


def nearest_value(frame: pd.DataFrame, timestamp_us: int, column: str) -> float:
    position = int(np.argmin(np.abs(frame["timestamp"].to_numpy() - timestamp_us)))
    return float(frame.iloc[position][column])


def detect_response(
    frame: pd.DataFrame,
    timestamp_us: int,
    signal: str,
    sign: int,
    minimum_delta: float,
) -> dict[str, object]:
    candidates = frame[
        (frame["timestamp"] >= timestamp_us)
        & (frame["timestamp"] <= timestamp_us + DEADLINE_US)
    ]
    for onset_us in candidates["timestamp"]:
        window = frame[
            (frame["timestamp"] >= onset_us)
            & (frame["timestamp"] <= onset_us + WINDOW_US)
        ]
        if len(window) < 20:
            continue
        values = window[signal].to_numpy()
        signed_delta = float(sign * (values[-1] - values[0]))
        direction_fraction = float(np.mean(sign * np.diff(values) > 0))
        if signed_delta >= minimum_delta and direction_fraction >= 0.6:
            return {
                "verdict": "PASS_CANDIDATE_CONFORMANCE",
                "response_onset_us": int(onset_us),
                "response_latency_s": round((int(onset_us) - timestamp_us) / 1e6, 6),
                "window_s": WINDOW_US / 1e6,
                "signed_delta": round(signed_delta, 6),
                "direction_fraction": round(direction_fraction, 6),
            }
    return {
        "verdict": "NO_RESPONSE_UNDER_CANDIDATE_HEURISTIC",
        "response_onset_us": None,
        "response_latency_s": None,
        "window_s": WINDOW_US / 1e6,
    }


def event_contract(text: str) -> tuple[str, int, float, str]:
    lowered = text.lower()
    if lowered.startswith(("decelerate", "slow down", "strong deceleration", "gentle deceleration", "yield", "stop")):
        return "speed_mps", -1, 0.1, "DECREASE_SPEED"
    if lowered.startswith(("resume speed", "accelerate", "gentle acceleration")):
        return "speed_mps", 1, 0.1, "INCREASE_SPEED"
    if lowered.startswith(("steer left", "slightly adjust left")):
        return "yaw_rad", 1, math.radians(1), "TURN_LEFT"
    if lowered.startswith(("steer right", "slightly adjust right")):
        return "yaw_rad", -1, math.radians(1), "TURN_RIGHT"
    raise ValueError(f"unsupported event for the candidate checker: {text}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--clip-id", default=DEFAULT_CLIP_ID)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    reasoning_path = args.root / "reasoning/ood_reasoning.parquet"
    index_path = args.root / "clip_index.parquet"
    license_path = args.root / "LICENSE.pdf"
    reasoning = pd.read_parquet(reasoning_path)
    clip_index = pd.read_parquet(index_path)
    if args.clip_id not in reasoning.index or args.clip_id not in clip_index.index:
        raise SystemExit(f"clip is not traceable in both official indexes: {args.clip_id}")

    raw_events = json.loads(reasoning.at[args.clip_id, "events"])
    egomotion, archive = load_egomotion(args.clip_id, args.root)
    egomotion = add_motion_signals(egomotion)
    events = []
    for source_index, event in enumerate(raw_events):
        timestamp_us = int(event["event_start_timestamp"])
        signal, sign, threshold, intent = event_contract(event["coc"])
        response = detect_response(egomotion, timestamp_us, signal, sign, threshold)
        events.append(
            {
                "source_index": source_index,
                "source_json_pointer": f"/{args.clip_id}/events/{source_index}",
                "timestamp_us": timestamp_us,
                "event_start_frame": int(event["event_start_frame"]),
                "coc": event["coc"],
                "intent": intent,
                "signal": signal,
                "signal_at_event": round(nearest_value(egomotion, timestamp_us, signal), 6),
                "candidate_contract": {
                    "deadline_s": DEADLINE_US / 1e6,
                    "minimum_signed_delta": threshold,
                    "status": "FEASIBILITY_PARAMETER_NOT_SAFETY_JUSTIFIED",
                },
                "response": response,
            }
        )

    report = {
        "checker": "OFFICIAL_NVIDIA_OOD_EPISODE_CANDIDATE_CONFORMANCE",
        "publication_control": {
            "classification": "LICENSE_RESTRICTED_INTERNAL_RESULT",
            "reason": "NVIDIA AV Dataset License sections 3 and 4.6",
        },
        "source": {
            "repository": "nvidia/PhysicalAI-Autonomous-Vehicles",
            "clip_id": args.clip_id,
            "split": reasoning.at[args.clip_id, "split"],
            "event_cluster": reasoning.at[args.clip_id, "event_cluster"],
            "reasoning_sha256": sha256_file(reasoning_path),
            "clip_index_sha256": sha256_file(index_path),
            "license_sha256": sha256_file(license_path),
            "archive": archive,
        },
        "traceability": {
            "reasoning_index_match": True,
            "clip_index_match": True,
            "event_count": len(events),
            "egomotion_rows": len(egomotion),
            "egomotion_timestamp_range_us": [
                int(egomotion["timestamp"].min()),
                int(egomotion["timestamp"].max()),
            ],
        },
        "events": events,
        "assessment": {
            "candidate_contract_pass_count": sum(
                event["response"]["verdict"] == "PASS_CANDIDATE_CONFORMANCE"
                for event in events
            ),
            "episode_model_checking_ready": all(
                event["response"]["response_onset_us"] is not None for event in events
            ),
            "physical_safety": "UNKNOWN_MISSING_OBJECT_DISTANCE_AND_RELATIVE_SPEED",
            "normative_deadline": "NOT_ESTABLISHED",
        },
    }
    rendered = json.dumps(report, indent=2) + "\n"
    output = args.output or (
        args.root / "internal-derived" / args.clip_id / "episode-conformance.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
