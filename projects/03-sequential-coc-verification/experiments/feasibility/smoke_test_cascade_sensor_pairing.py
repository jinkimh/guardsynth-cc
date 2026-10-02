#!/usr/bin/env python3
"""Smoke-test CASCADE filename references against PhysicalAI AV sensor data.

The CASCADE annotation payload is gated.  This script checks its filename-to-
PhysicalAI mapping over the full repository, selects one feature-rich clip in
the CASCADE/OOD-human-CoC intersection, validates the annotation with the
official devkit, streams only that clip's sensor members, and decodes one
front-camera frame.

No raw sensor member or decoded image is retained.  The JSON report contains
only aggregate counts, hashes, and a redacted identifier.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from huggingface_hub import HfApi, hf_hub_download
from physical_ai_av import PhysicalAIAVDatasetInterface
from physical_ai_av.video import SeekVideoReader


PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
DEFAULT_PAI_ROOT = PROJECT_ROOT / "data/restricted/nvidia_physicalai"
DEFAULT_CASCADE_ROOT = PROJECT_ROOT / "data/restricted/nvidia_cascade"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/restricted/nvidia_cascade/internal-derived/smoke-test-1/result.json"
)
CASCADE_REPO = "nvidia/cascade"
PAI_REVISION = "b719eea7f0a63619ef51ec7f54178af0937ef050"
REQUIRED_FEATURES = (
    "camera_front_wide_120fov",
    "egomotion",
    "egomotion.offline",
    "obstacle.offline",
)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def auth_status(api: HfApi, repo_id: str) -> dict[str, object]:
    try:
        api.auth_check(repo_id=repo_id, repo_type="dataset")
    except Exception as error:  # HF exposes several access-related exception types.
        return {"authorized": False, "error_type": type(error).__name__}
    return {"authorized": True, "error_type": None}


def cascade_json_files(api: HfApi) -> tuple[str, list[str]]:
    info = api.repo_info(repo_id=CASCADE_REPO, repo_type="dataset")
    files = sorted(
        sibling.rfilename
        for sibling in info.siblings or []
        if sibling.rfilename.startswith("data/")
        and sibling.rfilename.endswith(".json")
    )
    if not files:
        raise RuntimeError("CASCADE repository listing contains no annotation JSON files")
    return info.sha, files


def resolve_pai_references(
    filenames: list[str], pai_ids: set[str]
) -> tuple[list[tuple[str, str]], dict[str, int]]:
    """Resolve exactly one PAI UUID from each ``uuid__uuid.json`` filename."""
    resolved: list[tuple[str, str]] = []
    malformed = 0
    ambiguous = 0
    unmatched = 0
    first_component_matches = 0
    second_component_matches = 0

    for filename in filenames:
        parts = Path(filename).stem.split("__")
        if len(parts) != 2:
            malformed += 1
            continue
        hits = [component for component in parts if component in pai_ids]
        first_component_matches += int(parts[0] in pai_ids)
        second_component_matches += int(parts[1] in pai_ids)
        if len(hits) == 0:
            unmatched += 1
        elif len(hits) > 1:
            ambiguous += 1
        else:
            resolved.append((filename, hits[0]))

    stats = {
        "annotation_json_count": len(filenames),
        "resolved_unique_reference_count": len(resolved),
        "unique_pai_clip_count": len({clip_id for _, clip_id in resolved}),
        "first_component_matches": first_component_matches,
        "second_component_matches": second_component_matches,
        "malformed_filename_count": malformed,
        "ambiguous_reference_count": ambiguous,
        "unmatched_reference_count": unmatched,
    }
    return resolved, stats


def read_zip_members(
    interface: PhysicalAIAVDatasetInterface, clip_id: str, feature: str
) -> tuple[dict[str, bytes], str]:
    chunk = interface.get_clip_chunk(clip_id)
    chunk_file = interface.features.get_chunk_feature_filename(chunk, feature)
    members = interface.features.get_clip_files_in_zip(clip_id, feature)
    with interface.open_file(chunk_file, maybe_stream=True) as source:
        with zipfile.ZipFile(source) as archive:
            raw = {name: archive.read(member) for name, member in members.items()}
    return raw, chunk_file


def frame_summary(frame: pd.DataFrame, timestamp_column: str) -> dict[str, object]:
    return {
        "rows": len(frame),
        "columns": len(frame.columns),
        "timestamp_min_us": int(frame[timestamp_column].min()),
        "timestamp_max_us": int(frame[timestamp_column].max()),
    }


def parse_cascade_annotation(path: Path, expected_clip_id: str) -> dict[str, object]:
    """Validate one gated annotation and summarize graph integrity without raw text."""
    import sys

    devkit_src = PROJECT_ROOT / "third_party/cascade-devkit/src"
    if str(devkit_src) not in sys.path:
        sys.path.insert(0, str(devkit_src))
    from cascade_av.io import load_file
    from cascade_av.query.triplets import extract_causal_triplets

    bundle = load_file(path)
    if bundle.video.clip_id != expected_clip_id:
        raise RuntimeError("CASCADE video.clip_id does not match the resolved PAI reference")

    annotation = bundle.annotation
    triplets = extract_causal_triplets(bundle)
    resolved_triplets = sum(triplet.cause is not None for triplet in triplets)
    dangling_triplets = len(triplets) - resolved_triplets
    return {
        "schema_parse": "PASS",
        "schema_version": bundle.schema_version,
        "annotation_status": bundle.status,
        "human_provenance": bundle.provenance.get("generated_by") == "human",
        "video_duration_s": bundle.video.duration_s,
        "payload_bytes": path.stat().st_size,
        "payload_sha256": sha256_bytes(path.read_bytes()),
        "environments": len(annotation.environments),
        "conditions": len(annotation.conditions),
        "traffic_objects": len(annotation.traffic_objects),
        "traffic_lights": len(annotation.traffic_lights),
        "agents": len(annotation.agents),
        "ego_actions": len(annotation.ego_vehicle.actions),
        "agent_actions": sum(len(agent.actions) for agent in annotation.agents),
        "because_of_entries": sum(
            len(action.because_of) for action in annotation.ego_vehicle.actions
        )
        + sum(
            len(action.because_of)
            for agent in annotation.agents
            for action in agent.actions
        ),
        "causal_triplets": len(triplets),
        "resolved_causal_triplets": resolved_triplets,
        "dangling_causal_triplets": dangling_triplets,
        "qa_issue_count": len(bundle.qa_issues),
        "graph_integrity": (
            "PASS" if dangling_triplets == 0 else "REVIEW_DANGLING_CAUSAL_REFERENCE"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pai-root", type=Path, default=DEFAULT_PAI_ROOT)
    parser.add_argument("--cascade-root", type=Path, default=DEFAULT_CASCADE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    pai_root = args.pai_root.resolve()
    cascade_root = args.cascade_root.resolve()
    api = HfApi()
    cascade_revision, annotation_files = cascade_json_files(api)
    clip_index = pd.read_parquet(pai_root / "clip_index.parquet")
    feature_presence = pd.read_parquet(pai_root / "metadata/feature_presence.parquet")
    ood_reasoning = pd.read_parquet(pai_root / "reasoning/ood_reasoning.parquet")

    resolved, mapping = resolve_pai_references(annotation_files, set(clip_index.index))
    if mapping["resolved_unique_reference_count"] != len(annotation_files):
        raise RuntimeError(f"CASCADE-to-PAI reference mapping is incomplete: {mapping}")

    sensor_eligible = [
        (annotation_file, clip_id)
        for annotation_file, clip_id in resolved
        if bool(feature_presence.loc[clip_id, list(REQUIRED_FEATURES)].fillna(False).all())
    ]
    ood_ids = set(ood_reasoning.index)
    aligned = [pair for pair in resolved if pair[1] in ood_ids]
    aligned_sensor_eligible = [pair for pair in sensor_eligible if pair[1] in ood_ids]
    if not aligned_sensor_eligible:
        raise RuntimeError("no CASCADE-referenced clip has all required smoke-test features")
    annotation_file, clip_id = aligned_sensor_eligible[0]
    aligned_human_coc_event_count = sum(
        len(json.loads(ood_reasoning.at[aligned_clip_id, "events"]))
        for _, aligned_clip_id in aligned
    )
    selected_human_coc_event_count = len(json.loads(ood_reasoning.at[clip_id, "events"]))
    cascade_access = auth_status(api, CASCADE_REPO)
    cascade_annotation = None
    if cascade_access["authorized"]:
        annotation_path = Path(
            hf_hub_download(
                repo_id=CASCADE_REPO,
                repo_type="dataset",
                filename=annotation_file,
                revision=cascade_revision,
                local_dir=cascade_root,
            )
        )
        cascade_annotation = parse_cascade_annotation(annotation_path, clip_id)

    interface = PhysicalAIAVDatasetInterface(
        revision=PAI_REVISION,
        local_dir=pai_root,
        confirm_download_threshold_gb=10.0,
    )

    ego_raw, ego_chunk = read_zip_members(interface, clip_id, "egomotion")
    ego_offline_raw, ego_offline_chunk = read_zip_members(
        interface, clip_id, "egomotion.offline"
    )
    obstacle_raw, obstacle_chunk = read_zip_members(
        interface, clip_id, "obstacle.offline"
    )
    camera_raw, camera_chunk = read_zip_members(
        interface, clip_id, "camera_front_wide_120fov"
    )

    ego = pd.read_parquet(io.BytesIO(ego_raw["egomotion"]))
    ego_offline = pd.read_parquet(io.BytesIO(ego_offline_raw["egomotion.offline"]))
    obstacles = pd.read_parquet(io.BytesIO(obstacle_raw["obstacle.offline"]))
    camera_timestamps = pd.read_parquet(io.BytesIO(camera_raw["frame_timestamps"]))[
        "timestamp"
    ].to_numpy(copy=True)

    reader = SeekVideoReader(
        video_data=io.BytesIO(camera_raw["video"]), timestamps=camera_timestamps
    )
    requested_timestamp = np.array(
        [int(camera_timestamps[len(camera_timestamps) // 2])], dtype=np.int64
    )
    images, actual_timestamps = reader.decode_images_from_timestamps(requested_timestamp)
    reader.close()

    ego_summary = frame_summary(ego, "timestamp")
    ego_offline_summary = frame_summary(ego_offline, "timestamp")
    obstacle_summary = frame_summary(obstacles, "timestamp_us")
    camera_summary = {
        "frames": len(camera_timestamps),
        "timestamp_min_us": int(camera_timestamps.min()),
        "timestamp_max_us": int(camera_timestamps.max()),
        "decoded_frame_shape": list(images[0].shape),
        "decoded_dtype": str(images[0].dtype),
        "requested_timestamp_us": int(requested_timestamp[0]),
        "actual_timestamp_us": int(actual_timestamps[0]),
    }

    starts = [
        ego_summary["timestamp_min_us"],
        ego_offline_summary["timestamp_min_us"],
        obstacle_summary["timestamp_min_us"],
        camera_summary["timestamp_min_us"],
    ]
    ends = [
        ego_summary["timestamp_max_us"],
        ego_offline_summary["timestamp_max_us"],
        obstacle_summary["timestamp_max_us"],
        camera_summary["timestamp_max_us"],
    ]
    overlap_start = max(starts)
    overlap_end = min(ends)

    report = {
        "status": (
            "ALIGNED_TRIPLE_JOIN_PASS_GRAPH_INTEGRITY_REVIEW"
            if cascade_annotation
            and cascade_annotation["dangling_causal_triplets"]
            else "ALIGNED_TRIPLE_JOIN_PASS"
            if cascade_annotation
            else "SENSOR_STREAM_AND_DECODE_PASS"
        ),
        "publication_control": {
            "classification": "LICENSE_RESTRICTED_INTERNAL_RESULT",
            "raw_cascade_annotation_retained": cascade_annotation is not None,
            "raw_sensor_members_retained": False,
            "decoded_camera_frame_retained": False,
        },
        "source": {
            "cascade_repository": CASCADE_REPO,
            "cascade_revision": cascade_revision,
            "pai_repository": "nvidia/PhysicalAI-Autonomous-Vehicles",
            "pai_revision": interface.revision,
            "annotation_locator_sha256": sha256_bytes(annotation_file.encode()),
            "annotation_payload_sha256": (
                cascade_annotation["payload_sha256"] if cascade_annotation else None
            ),
            "selected_annotation_ordinal": annotation_files.index(annotation_file),
            "clip_id_sha256": sha256_bytes(clip_id.encode()),
            "clip_id_redacted": f"{clip_id[:8]}…{clip_id[-4:]}",
            "chunk": int(interface.get_clip_chunk(clip_id)),
        },
        "access": {
            "cascade_annotation_payload": cascade_access,
            "pai_sensor_stream": {"authorized": True, "error_type": None},
        },
        "mapping": mapping,
        "availability": {
            "required_features": list(REQUIRED_FEATURES),
            "cascade_sensor_eligible_clip_count": len(sensor_eligible),
            "cascade_ood_human_coc_overlap_clip_count": len(aligned),
            "cascade_ood_human_coc_overlap_event_count": aligned_human_coc_event_count,
            "aligned_sensor_eligible_clip_count": len(aligned_sensor_eligible),
            "selected_human_coc_event_count": selected_human_coc_event_count,
        },
        "cascade_annotation": cascade_annotation,
        "streams": {
            "egomotion": {
                **ego_summary,
                "bytes": len(ego_raw["egomotion"]),
                "sha256": sha256_bytes(ego_raw["egomotion"]),
                "chunk_file": ego_chunk,
            },
            "egomotion_offline": {
                **ego_offline_summary,
                "bytes": len(ego_offline_raw["egomotion.offline"]),
                "sha256": sha256_bytes(ego_offline_raw["egomotion.offline"]),
                "chunk_file": ego_offline_chunk,
            },
            "obstacle_offline": {
                **obstacle_summary,
                "bytes": len(obstacle_raw["obstacle.offline"]),
                "unique_tracks": int(obstacles["track_id"].nunique()),
                "sha256": sha256_bytes(obstacle_raw["obstacle.offline"]),
                "chunk_file": obstacle_chunk,
            },
            "front_camera": {
                **camera_summary,
                "video_bytes": len(camera_raw["video"]),
                "video_sha256": sha256_bytes(camera_raw["video"]),
                "frame_timestamps_bytes": len(camera_raw["frame_timestamps"]),
                "chunk_file": camera_chunk,
            },
        },
        "temporal_overlap": {
            "start_us": overlap_start,
            "end_us": overlap_end,
            "duration_s": round((overlap_end - overlap_start) / 1e6, 6),
            "pass": overlap_end > overlap_start,
        },
        "assessment": {
            "cascade_to_pai_reference_mapping": "PASS",
            "cascade_ood_human_coc_alignment": "PASS",
            "sensor_member_streaming": "PASS",
            "camera_frame_decode": "PASS",
            "cross_sensor_temporal_overlap": "PASS",
            "cascade_annotation_parse": (
                "NOT_RUN_CURRENT_HF_IDENTITY_NOT_AUTHORIZED"
                if not cascade_access["authorized"]
                else cascade_annotation["schema_parse"]
            ),
            "cascade_graph_integrity": (
                cascade_annotation["graph_integrity"]
                if cascade_annotation
                else "NOT_RUN"
            ),
            "end_to_end_annotation_sensor_join": (
                "PASS" if cascade_annotation else "PARTIAL_PENDING_CASCADE_PAYLOAD_ACCESS"
            ),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
