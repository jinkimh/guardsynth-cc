"""Read-only adapter for locally available restricted NVIDIA-derived assets.

The module has two levels:

* ``audit_local_candidates`` preserves the original P0b field-readiness audit.
* ``adapt_existing_derived_bundle`` joins already-derived obstacle events,
  recorded ego futures, and event metadata without downloading or copying raw
  video/sensor members.

The join emits hashed identifiers and no CoC text.  A nearest corridor VRU is
not silently promoted to an unambiguous pedestrian association; multiple
candidates remain ``UNKNOWN/REVIEW_REQUIRED``.  Vehicle dimensions are used
only for geometry.  They are not a braking assurance profile.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from math import isfinite
from pathlib import Path
import sys
from typing import Any

from ..catalog import SCHEMA_ROOT
from ..schema_validation import load_json, validate


REQUIRED_FIELDS = (
    "timestamps",
    "conflict_zone_geometry",
    "pedestrian_track_association",
    "pedestrian_to_conflict_zone_association",
    "time_aligned_ego_pose",
    "time_aligned_ego_speed_with_units",
    "coordinate_frame_and_transform",
    "vehicle_assurance_profile",
)

VRU_LABELS = {"person", "rider"}
SNAPSHOT_MAXIMUM_AGE_S = 0.05
TRAJECTORY_SAMPLE_PERIOD_S = 0.1
DEFAULT_RUN_ID = "p0b-data-adapter-2026-08-08-v1"
RUN_DATE = date.today().isoformat()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite_candidate_number(value: Any, reason: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(reason)
    result = float(value)
    if not isfinite(result):
        raise ValueError(reason)
    return result


def _nonnegative_candidate_int(value: Any, reason: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(reason)
    return value


def _association_candidates(
    event: dict[str, Any], candidate_count: int
) -> list[dict[str, Any]]:
    raw = event.get("candidates")
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) != candidate_count:
        raise ValueError("INCOMPLETE_ACTOR_CANDIDATE_SET")
    output = []
    for expected_rank, candidate in enumerate(raw, start=1):
        if not isinstance(candidate, dict):
            raise ValueError("INVALID_ACTOR_CANDIDATE_RECORD")
        track_id = candidate.get("track_id")
        label = candidate.get("label_class")
        rank = candidate.get("rank_by_longitudinal_gap")
        samples = candidate.get("track_samples")
        if (
            not isinstance(track_id, str)
            or not track_id
            or not isinstance(label, str)
            or not label
            or isinstance(rank, bool)
            or not isinstance(rank, int)
            or rank != expected_rank
            or not isinstance(samples, list)
            or not samples
        ):
            raise ValueError("INVALID_ACTOR_CANDIDATE_RECORD")
        safe_samples = []
        previous_timestamp: int | None = None
        for sample in samples:
            if not isinstance(sample, dict):
                raise ValueError("INVALID_ACTOR_CANDIDATE_TRACK_SAMPLES")
            timestamp = sample.get("timestamp_us")
            if (
                isinstance(timestamp, bool)
                or not isinstance(timestamp, int)
                or (previous_timestamp is not None and timestamp <= previous_timestamp)
            ):
                raise ValueError("INVALID_ACTOR_CANDIDATE_TRACK_SAMPLES")
            safe_sample = {
                "timestamp_us": timestamp,
                "center_x_m": _finite_candidate_number(
                    sample.get("center_x_m"), "INVALID_ACTOR_CANDIDATE_TRACK_SAMPLES"
                ),
                "center_y_m": _finite_candidate_number(
                    sample.get("center_y_m"), "INVALID_ACTOR_CANDIDATE_TRACK_SAMPLES"
                ),
            }
            for name in ("half_extent_x_m", "half_extent_y_m"):
                if name in sample:
                    safe_sample[name] = _finite_candidate_number(
                        sample[name], "INVALID_ACTOR_CANDIDATE_TRACK_SAMPLES"
                    )
            safe_samples.append(safe_sample)
            previous_timestamp = timestamp
        safe_candidate = {
            "rank_by_longitudinal_gap": expected_rank,
            "track_id_sha256": _sha256_text(track_id),
            "label_class": label,
            "longitudinal_gap_m": _finite_candidate_number(
                candidate.get("longitudinal_gap_m"), "INVALID_ACTOR_CANDIDATE_RECORD"
            ),
            "lateral_center_m": _finite_candidate_number(
                candidate.get("lateral_center_m"), "INVALID_ACTOR_CANDIDATE_RECORD"
            ),
            "timestamp_error_us": _nonnegative_candidate_int(
                candidate.get("timestamp_error_us"), "INVALID_ACTOR_CANDIDATE_RECORD"
            ),
            "sample_count": _nonnegative_candidate_int(
                candidate.get("sample_count"), "INVALID_ACTOR_CANDIDATE_RECORD"
            ),
            "track_samples": safe_samples,
        }
        for name in ("gap_rate_mps", "closing_speed_mps", "candidate_ttc_s"):
            value = candidate.get(name)
            safe_candidate[name] = (
                None
                if value is None
                else _finite_candidate_number(value, "INVALID_ACTOR_CANDIDATE_RECORD")
            )
        output.append(safe_candidate)
    return output


def _field_paths(value: Any, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else key
            paths.add(child)
            paths.update(_field_paths(item, child))
    elif isinstance(value, list) and value:
        paths.update(_field_paths(value[0], f"{prefix}[]"))
    return paths


def _json_structure_available(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(_field_paths(value))


def audit_local_candidates(project_root: Path) -> dict[str, object]:
    """Coarse P0b audit retained for reproducibility of the first run."""
    candidates = [
        {
            "asset_class": "PHYSICALAI_COHORT_DERIVED_EVENT_CONFORMANCE",
            "relative_path": "data/restricted/nvidia_physicalai/internal-derived/cohort-10/cohort-conformance.json",
            "available_fields": ["timestamps", "event_action_claims", "response_signal"],
        },
        {
            "asset_class": "PHYSICALAI_COHORT_DERIVED_OBSTACLE_FEASIBILITY",
            "relative_path": "data/restricted/nvidia_physicalai/internal-derived/cohort-10/obstacle-feasibility.json",
            "available_fields": ["timestamps", "obstacle_track_candidate", "relative_gap", "relative_closing_speed", "coordinate_convention"],
        },
        {
            "asset_class": "CASCADE_DERIVED_CAUSAL_ANNOTATION",
            "relative_path": "data/restricted/nvidia_cascade/data/batch_00001/014bf197-bbec-4072-8eb7-004507a4859b__ccc47abf-23f1-4abd-9ad3-fa3602099607.json",
            "available_fields": ["timestamps", "agent_semantic_type", "agent_keypoints", "ego_action_claims"],
        },
        {
            "asset_class": "RESTRICTED_MODEL_TRAJECTORY_ARRAYS",
            "relative_path": "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0/episode-02/seed-42/ground_truth_trajectory.npz",
            "available_fields": ["ego_trajectory_array_without_complete_scene_contract"],
        },
    ]
    audited: list[dict[str, object]] = []
    for item in candidates:
        path = project_root / str(item["relative_path"])
        exists = path.is_file()
        readable_structure = _json_structure_available(path) if path.suffix == ".json" else exists
        available = set(item["available_fields"]) if readable_structure else set()
        normalized_available = {field for field in REQUIRED_FIELDS if field in available}
        missing = [field for field in REQUIRED_FIELDS if field not in normalized_available]
        audited.append(
            {
                "asset_class": item["asset_class"],
                "relative_path": item["relative_path"],
                "exists": exists,
                "structure_readable_without_raw_copy": readable_structure,
                "available_field_classes": sorted(available),
                "missing_required_fields": missing,
                "adapter_ready": not missing,
            }
        )
    return {
        "status": "P0B_REAL_ADAPTER_BLOCKED_DATA_GAP",
        "input_class": "LICENSE_RESTRICTED",
        "raw_rows_or_text_included": False,
        "synthetic_fill_performed": False,
        "required_fields": list(REQUIRED_FIELDS),
        "candidates": audited,
        "ready_candidate_count": sum(bool(item["adapter_ready"]) for item in audited),
        "decision": "NO_REAL_SCENE_CONTEXTGRAPH_EMITTED",
        "reason_codes": [
            "MISSING_CONFLICT_ZONE_GEOMETRY",
            "MISSING_PEDESTRIAN_ZONE_ASSOCIATION",
            "MISSING_TIME_ALIGNED_EGO_POSE_SPEED_FRAME_BUNDLE",
            "MISSING_VEHICLE_ASSURANCE_PROFILE",
        ],
        "claim_boundary": "DATA_READINESS_AUDIT_ONLY_NOT_REAL_SCENE_SAFETY_VALIDATION",
    }


def derive_context_candidate(
    *,
    episode_ordinal: int,
    event_ordinal: int,
    clip_id: str,
    event: dict[str, Any],
    vehicle_dimensions: dict[str, Any],
    ego_state: dict[str, Any],
    coc_claim: str | None,
) -> dict[str, Any]:
    """Create one partial ContextGraph record from actual derived fields only."""
    obstacle = event.get("nearest_candidate")
    if not isinstance(obstacle, dict):
        raise ValueError("MISSING_NEAREST_CORRIDOR_OBSTACLE")
    label = str(obstacle.get("label_class", ""))
    if label not in VRU_LABELS:
        raise ValueError("TARGET_IS_NOT_VULNERABLE_ROAD_USER")
    required_numeric = ("longitudinal_gap_m", "lateral_center_m")
    if any(obstacle.get(name) is None for name in required_numeric):
        raise ValueError("MISSING_CONFLICT_ZONE_GEOMETRY_INPUT")
    if any(ego_state.get(name) is None for name in ("speed_mps", "pose_relative_t0_m")):
        raise ValueError("MISSING_TIME_ALIGNED_EGO_STATE")
    front_extent = vehicle_dimensions.get("rear_axle_to_front_extent_m")
    if front_extent is None:
        raise ValueError("MISSING_VEHICLE_FRONT_EXTENT")

    timestamp_us = int(event["timestamp_us"])
    candidate_count = int(event.get("candidate_count", 0))
    association_candidates = _association_candidates(event, candidate_count)
    ambiguous = candidate_count != 1
    clip_hash = _sha256_text(clip_id)
    target_hash = _sha256_text(str(obstacle.get("track_id", "missing-track")))
    zone_hash = _sha256_text(f"{clip_hash}:{timestamp_us}:{target_hash}:near-boundary")
    zone_entry = float(front_extent) + float(obstacle["longitudinal_gap_m"])
    hazard_truth = "UNKNOWN" if ambiguous else "TRUE"
    association_reason = (
        "MULTIPLE_FORWARD_CORRIDOR_CANDIDATES"
        if ambiguous
        else "SINGLE_VRU_FORWARD_CORRIDOR_CANDIDATE"
    )
    context = {
        "timestamp_s": timestamp_us / 1e6,
        "hazard_fact": {
            "truth": hazard_truth,
            "epistemic_kind": "DERIVED",
            "source": "OFFICIAL_DERIVED_OBSTACLE_CORRIDOR_GEOMETRY",
            "timestamp_s": timestamp_us / 1e6,
            "maximum_age_s": SNAPSHOT_MAXIMUM_AGE_S,
        },
        "ego_front_x_m": float(front_extent),
        "ego_speed_mps": float(ego_state["speed_mps"]),
        "zone_entry_x_m": zone_entry,
        "target_entity_id": f"sha256:{target_hash}",
        "zone_id": f"sha256:{zone_hash}",
        "coordinate_frame": "CURRENT_RIG_X_FORWARD",
        "distance_unit": "m",
    }
    validate(context, load_json(SCHEMA_ROOT / "context_graph.schema.json"))
    reason_codes = [
        "MISSING_VEHICLE_ASSURANCE_PROFILE",
        "RIG_TO_CANONICAL_EGO_PATH_FRAME_NOT_VERIFIED",
    ]
    if ambiguous:
        reason_codes.insert(0, "AMBIGUOUS_TARGET")
    return {
        "candidate_id": f"episode-{episode_ordinal:02d}-event-{event_ordinal:02d}",
        "clip_id_sha256": clip_hash,
        "raw_clip_id_included": False,
        "context_graph": context,
        "context_schema_valid": True,
        "target_binding": {
            "label_class": label,
            "candidate_count": candidate_count,
            "track_id_sha256": target_hash,
            "ambiguity_reason": association_reason if ambiguous else None,
            "verdict": "REVIEW_REQUIRED" if ambiguous else "VALIDATED",
            "all_candidates_preserved": bool(association_candidates),
        },
        "association_candidates": association_candidates,
        "conflict_zone": {
            "kind": "DYNAMIC_VRU_OCCUPANCY_NEAR_BOUNDARY_1D",
            "entry_x_m": zone_entry,
            "lateral_center_m": float(obstacle["lateral_center_m"]),
            "source_fields": [
                "vehicle_dimensions.rear_axle_to_front_extent_m",
                "nearest_candidate.longitudinal_gap_m",
                "nearest_candidate.lateral_center_m",
            ],
            "crosswalk_or_legal_zone_claimed": False,
        },
        "ego_state": {
            "pose_relative_t0_m": [float(item) for item in ego_state["pose_relative_t0_m"]],
            "speed_mps": float(ego_state["speed_mps"]),
            "relative_time_s": float(ego_state["relative_time_s"]),
            "derivation": "RECORDED_FUTURE_LINEAR_INTERPOLATION_AND_FINITE_DIFFERENCE",
        },
        "coc_claim": {
            "present": coc_claim is not None,
            "epistemic_kind": "CLAIMED",
            "text_included": False,
            "text_sha256": _sha256_text(coc_claim) if coc_claim is not None else None,
        },
        "contract_binding": {
            "verdict": "UNSUPPORTED",
            "reason_codes": reason_codes,
            "numeric_value_synthesized": False,
            "legal_rule_claimed": False,
        },
    }


def _ego_state_from_recorded_future(points: Any, relative_time_s: float) -> dict[str, Any]:
    """Interpolate a recorded local future; numpy is imported only at execution."""
    import numpy as np

    trajectory = np.asarray(points, dtype=float).reshape(-1, 3)
    sample_times = np.arange(1, len(trajectory) + 1, dtype=float) * TRAJECTORY_SAMPLE_PERIOD_S
    times = np.concatenate(([0.0], sample_times))
    positions = np.vstack((np.zeros((1, 3), dtype=float), trajectory))
    if relative_time_s < 0 or relative_time_s > float(times[-1]) + 1e-9:
        raise ValueError("EVENT_OUTSIDE_RECORDED_FUTURE_HORIZON")
    pose = np.array([
        np.interp(relative_time_s, times, positions[:, dimension])
        for dimension in range(3)
    ])
    interval = min(max(1, int(np.ceil(relative_time_s / TRAJECTORY_SAMPLE_PERIOD_S))), len(trajectory))
    speed = float(
        np.linalg.norm(positions[interval] - positions[interval - 1])
        / TRAJECTORY_SAMPLE_PERIOD_S
    )
    return {
        "pose_relative_t0_m": pose.tolist(),
        "speed_mps": speed,
        "relative_time_s": relative_time_s,
    }


def adapt_existing_derived_bundle(project_root: Path) -> dict[str, Any]:
    """Join local derived files only; this function performs no network access."""
    try:
        import numpy as np
    except ModuleNotFoundError as exc:
        raise RuntimeError("NUMPY_REQUIRED_USE_EXISTING_ALPAMAYO_ENVIRONMENT") from exc

    obstacle_v2_path = project_root / (
        "data/restricted/nvidia_physicalai/internal-derived/cohort-10/"
        "obstacle-feasibility-v2-all-candidates.json"
    )
    obstacle_path = (
        obstacle_v2_path
        if obstacle_v2_path.is_file()
        else project_root
        / "data/restricted/nvidia_physicalai/internal-derived/cohort-10/obstacle-feasibility.json"
    )
    cohort_path = project_root / "data/restricted/nvidia_physicalai/internal-derived/cohort-10/cohort-conformance.json"
    batch_root = project_root / "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0"
    obstacles = json.loads(obstacle_path.read_text(encoding="utf-8"))
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    candidates: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    vru_event_count = 0

    for episode_index, (obstacle_episode, cohort_episode) in enumerate(
        zip(obstacles["episodes"], cohort["episodes"], strict=True)
    ):
        if obstacle_episode["clip_id"] != cohort_episode["clip_id"]:
            raise RuntimeError("COHORT_OBSTACLE_EPISODE_ID_MISMATCH")
        manifest_path = batch_root / f"episode-{episode_index:02d}/seed-42/manifest.json"
        trajectory_path = batch_root / f"episode-{episode_index:02d}/seed-42/ground_truth_trajectory.npz"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None
        trajectory = None
        if trajectory_path.is_file():
            with np.load(trajectory_path) as archive:
                trajectory = archive["gt_xyz"].reshape(-1, 3).copy()
        cohort_by_source = {
            int(event["source_index"]): event for event in cohort_episode["events"]
        }
        for event_index, event in enumerate(obstacle_episode["events"]):
            nearest = event.get("nearest_candidate")
            if not isinstance(nearest, dict) or str(nearest.get("label_class")) not in VRU_LABELS:
                continue
            vru_event_count += 1
            gap_id = f"episode-{episode_index:02d}-event-{event_index:02d}"
            if manifest is None or trajectory is None:
                gaps.append({"candidate_id": gap_id, "reason_code": "MISSING_RECORDED_EGO_FUTURE"})
                continue
            if manifest["clip_id"] != obstacle_episode["clip_id"]:
                gaps.append({"candidate_id": gap_id, "reason_code": "TRAJECTORY_CLIP_ID_MISMATCH"})
                continue
            relative_time_s = (
                int(event["timestamp_us"]) - int(manifest["t0_us"])
            ) / 1e6
            try:
                ego_state = _ego_state_from_recorded_future(trajectory, relative_time_s)
            except ValueError as exc:
                gaps.append({"candidate_id": gap_id, "reason_code": str(exc)})
                continue
            source_event = cohort_by_source.get(int(event["source_index"]))
            coc_claim = str(source_event["coc"]) if source_event and source_event.get("coc") else None
            candidates.append(
                derive_context_candidate(
                    episode_ordinal=episode_index,
                    event_ordinal=event_index,
                    clip_id=str(obstacle_episode["clip_id"]),
                    event=event,
                    vehicle_dimensions=obstacle_episode["vehicle_dimensions"],
                    ego_state=ego_state,
                    coc_claim=coc_claim,
                )
            )

    return {
        "experiment_id": "EBLC-P0B-001",
        "phase": "DATA_GAP_PIVOT_REAL_DERIVED_ADAPTER",
        "status": "PARTIAL_REAL_SCENE_CONTEXT_ADAPTER_EXECUTED",
        "input_class": "LICENSE_RESTRICTED",
        "network_access_performed": False,
        "raw_sensor_or_video_copied": False,
        "raw_coc_text_included": False,
        "synthetic_value_fill_performed": False,
        "vru_event_count": vru_event_count,
        "adapted_context_count": len(candidates),
        "context_schema_valid_count": sum(bool(item["context_schema_valid"]) for item in candidates),
        "unambiguous_target_count": sum(item["target_binding"]["ambiguity_reason"] is None for item in candidates),
        "validated_contract_count": 0,
        "unsupported_contract_count": len(candidates),
        "candidates": candidates,
        "data_gaps": gaps,
        "remaining_reason_codes": [
            "AMBIGUOUS_TARGET",
            "MISSING_VEHICLE_ASSURANCE_PROFILE",
            "RIG_TO_CANONICAL_EGO_PATH_FRAME_NOT_VERIFIED",
        ],
        "decision": "24_SCENE_DRY_RUN_NOT_READY",
        "claim_scope": "PARTIAL_REAL_DERIVED_CONTEXT_ADAPTATION_NOT_CONTRACT_VALIDATION_OR_VEHICLE_SAFETY",
        "source_hashes": {
            "obstacle_feasibility": _sha256_file(obstacle_path),
            "cohort_conformance": _sha256_file(cohort_path),
        },
    }


def _report(result: dict[str, Any], run_id: str) -> str:
    return f"""# P0b data-gap adapter 실행 보고서

- run ID: `{run_id}`
- 상태: **{result['status']}**
- 입력: 기존 LICENSE_RESTRICTED 파생 JSON/recorded ego future
- 네트워크 접근: 없음
- raw video/sensor 복사: 없음
- synthetic value 보충: 없음

## 결과

- VRU 후보 event: {result['vru_event_count']}
- schema-valid partial ContextGraph: {result['context_schema_valid_count']}/{result['adapted_context_count']}
- 시간 horizon 밖 또는 ego future 누락: {len(result['data_gaps'])}
- unambiguous target association: {result['unambiguous_target_count']}/{result['adapted_context_count']}
- VALIDATED contract: {result['validated_contract_count']}
- UNSUPPORTED contract: {result['unsupported_contract_count']}

기존 파생물의 실제 timestamp, vehicle front extent, VRU track gap/lateral position 및 recorded ego future를 결합해 1차원 dynamic occupancy conflict-zone ContextGraph를 만들었다. 이 zone은 법적 횡단보도나 지도 규제 zone이 아니다. CoC는 내용 없이 hash와 `CLAIMED` provenance만 보존했다.

모든 후보에 복수의 forward-corridor candidate가 있어 target association은 `REVIEW_REQUIRED`다. 또한 실제 차량 보장 제동 profile과 rig→canonical ego-path frame 검증이 없어 numeric EBLC contract는 `UNSUPPORTED`로 유지했다.

## 판단

첫 P0b의 “geometry/ego state 전무” gap은 일부 축소됐다. 그러나 24-scene dry run은 아직 준비되지 않았다. 다음 단일 작업은 full obstacle snapshot 또는 human grounding을 사용해 복수 후보 중 실제 원인 VRU association을 확정하는 것이다.

이 결과는 partial context adaptation evidence이며 법규 타당성, contract validation 또는 차량 안전성 증거가 아니다.
"""


def write_restricted_run(project_root: Path, run_id: str) -> Path:
    output = project_root / "artifacts/results/restricted/eblc-p0b-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing restricted run: {run_id}")
    result = adapt_existing_derived_bundle(project_root)
    output.mkdir(parents=True, mode=0o700)
    result_path = output / "ADAPTER_RESULT.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = output / "REPORT_KO.md"
    report_path.write_text(_report(result, run_id), encoding="utf-8")
    manifest = {
        "experiment_id": "EBLC-P0B-001",
        "phase": "DATA_GAP_PIVOT_REAL_DERIVED_ADAPTER",
        "run_id": run_id,
        "run_date": RUN_DATE,
        "python_version": sys.version.split()[0],
        "input_class": "LICENSE_RESTRICTED",
        "code_revision": "WORKSPACE_WITHOUT_GIT_METADATA",
        "adapter_sha256": _sha256_file(Path(__file__)),
        "context_schema_sha256": _sha256_file(SCHEMA_ROOT / "context_graph.schema.json"),
        "deterministic_join": True,
        "network_access_performed": False,
        "raw_sensor_or_video_copied": False,
        "raw_coc_text_included": False,
        "test_command": "python3 -m unittest projects/04-guardsynth-coc/tests/integration/test_real_scene_adapter.py -v",
        "claim_scope": result["claim_scope"],
    }
    (output / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for path in output.iterdir():
        path.chmod(0o600)
    return output
