#!/usr/bin/env python3
"""Extract source-bearing calibration and rig binding for one restricted scene."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
from physical_ai_av import PhysicalAIAVDatasetInterface


PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from guard_synth.nvidia_source_bundle import (
    SOURCE_BUNDLE_VERSION,
    build_coordinate_transform,
    build_vehicle_binding,
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _pose_record(pose: object) -> dict[str, object]:
    matrix = pose.as_matrix()
    return {
        "translation_m": [float(value) for value in pose.translation],
        "quaternion_xyzw": [float(value) for value in pose.rotation.as_quat()],
        "matrix_4x4": [[float(value) for value in row] for row in matrix],
    }


def _calibration_record(extrinsics: object) -> dict[str, object]:
    sensors = {
        sensor_id: _pose_record(pose)
        for sensor_id, pose in sorted(extrinsics.sensor_poses.items())
    }
    canonical = json.dumps(sensors, sort_keys=True, separators=(",", ":")).encode()
    return {"sensor_to_ego": sensors, "calibration_digest": _sha256_bytes(canonical)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--obstacles", type=Path, required=True)
    parser.add_argument("--episode-index", type=int, required=True)
    parser.add_argument("--event-index", type=int, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--scene-ref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--use-local-hf-token",
        action="store_true",
        help="Use the locally configured Hugging Face token for the gated dataset.",
    )
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")

    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    obstacles = json.loads(args.obstacles.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    episode = cohort["episodes"][args.episode_index]
    obstacle_episode = obstacles["episodes"][args.episode_index]
    if not episode["clip_id"] == obstacle_episode["clip_id"] == manifest["clip_id"]:
        raise ValueError("SCENE_CLIP_ID_MISMATCH")
    clip_id = episode["clip_id"]
    event = obstacle_episode["events"][args.event_index]
    event_timestamp_us = int(event["timestamp_us"])
    t0_us = int(manifest["t0_us"])
    dataset_revision = manifest.get("dataset_revision")
    if not isinstance(dataset_revision, str) or not dataset_revision:
        raise ValueError("MISSING_PINNED_DATASET_REVISION")

    metadata_path = args.root / "metadata/data_collection.parquet"
    metadata = pd.read_parquet(metadata_path).loc[clip_id]
    interface = PhysicalAIAVDatasetInterface(
        revision=dataset_revision,
        token=None if args.use_local_hf_token else False,
        local_dir=args.root.resolve(),
        confirm_download_threshold_gb=float("inf"),
    )
    extrinsics = interface.get_clip_feature(
        clip_id, interface.features.CALIBRATION.SENSOR_EXTRINSICS, maybe_stream=True
    )
    dimensions = interface.get_clip_feature(
        clip_id, interface.features.CALIBRATION.VEHICLE_DIMENSIONS, maybe_stream=True
    )
    egomotion = interface.get_clip_feature(
        clip_id, interface.features.LABELS.EGOMOTION, maybe_stream=True
    )
    t0_pose = egomotion(t0_us).pose
    event_pose = egomotion(event_timestamp_us).pose
    event_to_t0 = t0_pose.inv() * event_pose

    devkit_dataset = PROJECT_ROOT / "third_party/physical_ai_av/src/physical_ai_av/dataset.py"
    alpamayo_loader = PROJECT_ROOT / "runtime/alpamayo/src/alpamayo_r1/load_physical_aiavdataset.py"
    obstacle_source = str(obstacles["coordinate_convention"].get("source", ""))
    evidence_refs = [
        f"nvidia-dataset:{interface.revision}:egomotion",
        f"nvidia-dataset:{interface.revision}:sensor_extrinsics",
        f"devkit-sha256:{_sha256_file(devkit_dataset)}",
        f"alpamayo-loader-sha256:{_sha256_file(alpamayo_loader)}",
        f"coordinate-convention:{obstacle_source}",
    ]
    calibration = _calibration_record(extrinsics)
    vehicle_dimensions = {
        "length_m": float(dimensions.length),
        "width_m": float(dimensions.width),
        "height_m": float(dimensions.height),
        "rear_axle_to_bbox_center_m": float(dimensions.rear_axle_to_bbox_center),
        "wheelbase_m": float(dimensions.wheelbase),
        "track_width_m": float(dimensions.track_width),
    }
    coordinate_transform = build_coordinate_transform(
        transform=event_to_t0,
        source_frame="dataset_rig_at_event",
        target_frame="ego_at_model_t0",
        event_timestamp_us=event_timestamp_us,
        t0_us=t0_us,
        evidence_refs=evidence_refs,
    )
    vehicle_binding = build_vehicle_binding(
        clip_id_sha256=_sha256_bytes(clip_id.encode()),
        dataset_revision=interface.revision,
        platform_class=str(metadata["platform_class"]),
        radar_config=str(metadata["radar_config"]),
        vehicle_dimensions=vehicle_dimensions,
        calibration_digest=str(calibration["calibration_digest"]),
        evidence_refs=[
            f"restricted-sha256:{_sha256_file(metadata_path)}#/{_sha256_bytes(clip_id.encode())}",
            f"nvidia-dataset:{interface.revision}:vehicle_dimensions",
            f"nvidia-dataset:{interface.revision}:sensor_extrinsics",
        ],
    )
    result = {
        "source_bundle_version": SOURCE_BUNDLE_VERSION,
        "input_class": "LICENSE_RESTRICTED",
        "scene_ref": args.scene_ref,
        "clip_id_sha256": _sha256_bytes(clip_id.encode()),
        "dataset": {
            "repo_id": interface.repo_id,
            "revision": interface.revision,
            "country": str(metadata["country"]),
        },
        "coordinate_transform": coordinate_transform,
        "vehicle_binding": vehicle_binding,
        "calibration": calibration,
        "rule_applicability": {
            "status": "REVIEW_REQUIRED",
            "reason_code": "COUNTRY_ONLY_WITHOUT_STATE_OR_LOCAL_JURISDICTION",
            "available_country": str(metadata["country"]),
            "kr_catalog_applicable": False,
        },
        "assurance_profile": {
            "status": "REVIEW_REQUIRED",
            "reason_code": "MISSING_VEHICLE_ASSURANCE_PROFILE",
        },
        "raw_clip_id_included": False,
        "synthetic_value_fill_performed": False,
        "claim_scope": "SOURCE_LINKED_DATASET_TRANSFORM_AND_RIG_CONFIGURATION_NOT_VIN_RULE_APPLICABILITY_ASSURANCE_OR_VEHICLE_SAFETY",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.output.chmod(0o600)
    print(json.dumps({
        "status": "EXECUTED",
        "scene_ref": args.scene_ref,
        "coordinate_transform": coordinate_transform["status"],
        "vehicle_binding": vehicle_binding["status"],
        "rule_applicability": result["rule_applicability"]["status"],
        "assurance_profile": result["assurance_profile"]["status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
