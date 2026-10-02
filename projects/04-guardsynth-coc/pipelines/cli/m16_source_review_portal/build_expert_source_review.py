#!/usr/bin/env python3
"""Build the machine-assisted M16 60-scene expert source-review package."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


if __package__ in {None, ""}:
    ROOT_BOOTSTRAP = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "PROJECT_REGISTRY.json").is_file()
    )
    sys.path.insert(0, str(ROOT_BOOTSTRAP))

from cli.project_paths import project_root


ROOT = project_root(__file__)
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "expert_source_review_workbench.html"
ACQUISITION_RUN = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-source-acquisition-2026-08-14-v18"
)
SOURCE_REVIEW_UI_RUN = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-source-review-001/m16-source-review-2026-08-15-v5"
)
OBSERVATION_RUN = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-source-review-001/m16-source-review-2026-09-04-v1"
)
GEOMETRY_RUN = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-geometry-candidate-2026-09-05-v1"
)
CASCADE_AUDIT_RUN = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-cascade-structured-link-audit-2026-09-05-v1"
)
CASCADE_DATA = ROOT / "data/restricted/nvidia_cascade/data"
OUTPUT_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-expert-source-review-001"
)
WORKBENCH_NAME = "expert_source_review_workbench.html"
EXPERIMENT_ID = "GUARDSYNTH-M16-EXPERT-SOURCE-REVIEW-001"
CLAIM_SCOPE = (
    "MACHINE_ASSISTED_EXPERT_SOURCE_REVIEW_INPUT_NOT_GROUND_TRUTH_"
    "SOURCE_COMPLETE_FORMAL_PILOT_OR_VEHICLE_SAFETY"
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)


def _data_url_bytes(value: str) -> bytes:
    prefix = "data:image/jpeg;base64,"
    if not value.startswith(prefix):
        raise ValueError("M16_EXPERT_REVIEW_IMAGE_DATA_URL_INVALID")
    return base64.b64decode(value[len(prefix):], validate=True)


def _verified_image_data_url(root: Path, relative: str, expected_hash: str) -> str:
    path = root / relative
    if not path.is_file() or _sha256(path) != expected_hash:
        raise ValueError("M16_EXPERT_REVIEW_GEOMETRY_IMAGE_HASH_CHANGED")
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _extract_embedded_review_records() -> tuple[list[dict[str, Any]], str]:
    html_path = SOURCE_REVIEW_UI_RUN / "source_review_with_images.html"
    manifest_path = SOURCE_REVIEW_UI_RUN / "RUN_MANIFEST.json"
    manifest = _load(manifest_path)
    if _sha256(html_path) != manifest.get("html_sha256"):
        raise ValueError("M16_EXPERT_REVIEW_CONTACT_SHEET_HTML_HASH_CHANGED")
    html = html_path.read_text(encoding="utf-8")
    start_marker = '<script id="reviewData" type="application/json">'
    start = html.find(start_marker)
    end = html.find("</script>", start + len(start_marker))
    if start < 0 or end < 0:
        raise ValueError("M16_EXPERT_REVIEW_EMBEDDED_DATA_MISSING")
    payload = json.loads(html[start + len(start_marker):end])
    records = payload.get("records", [])
    images = manifest.get("images", [])
    if len(records) != 60 or len(images) != 60:
        raise ValueError("M16_EXPERT_REVIEW_CONTACT_SHEET_COUNT_INVALID")
    for record, image_record in zip(records, images):
        image_bytes = _data_url_bytes(record["image_data_url"])
        if (
            _sha256_bytes(image_bytes) != record["image_sha256"]
            or record["image_sha256"] != image_record["image_sha256"]
            or record["review_index"] != image_record["review_index"]
        ):
            raise ValueError("M16_EXPERT_REVIEW_CONTACT_SHEET_HASH_CHANGED")
    return records, _sha256(manifest_path)


def _geometry_records() -> tuple[dict[str, dict[str, Any]], str]:
    candidate_path = GEOMETRY_RUN / "GEOMETRY_CANDIDATE_MANIFEST.json"
    run_manifest = _load(GEOMETRY_RUN / "RUN_MANIFEST.json")
    candidate_hash = _sha256(candidate_path)
    if run_manifest.get("output_hashes", {}).get("geometry_candidate_manifest") != candidate_hash:
        raise ValueError("M16_EXPERT_REVIEW_GEOMETRY_MANIFEST_HASH_CHANGED")
    records = _load(candidate_path).get("records", [])
    if len(records) != 98:
        raise ValueError("M16_EXPERT_REVIEW_GEOMETRY_COUNT_INVALID")
    return {record["candidate_digest"]: record for record in records}, candidate_hash


def _prior_observations() -> tuple[dict[str, dict[str, Any]], str]:
    path = OBSERVATION_RUN / "m16_video_observation_review.json"
    manifest = _load(OBSERVATION_RUN / "RUN_MANIFEST.json")
    if _sha256(path) != manifest.get("source_hashes", {}).get("review_json"):
        raise ValueError("M16_EXPERT_REVIEW_PRIOR_OBSERVATION_HASH_CHANGED")
    records = _load(path).get("records", [])
    if len(records) != 60:
        raise ValueError("M16_EXPERT_REVIEW_PRIOR_OBSERVATION_COUNT_INVALID")
    return {record["candidate_digest"]: record for record in records}, _sha256(path)


def _event_sources() -> dict[str, dict[str, Any]]:
    primary = _load(ACQUISITION_RUN / "SENSOR_MATERIALIZATION_SHORTLIST.json")["records"]
    reserve = _load(ACQUISITION_RUN / "ATTRITION_RESERVE_COHORT.json")["records"]
    return {record["candidate_digest"]: record for record in primary + reserve}


def _cascade_paths() -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in CASCADE_DATA.rglob("*.json"):
        parts = path.stem.split("__", 1)
        if len(parts) != 2 or parts[1] in result:
            raise ValueError("M16_EXPERT_REVIEW_CASCADE_FILENAME_INVALID")
        result[parts[1]] = path
    return result


def _timestamp_seconds(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    if ":" in text:
        minutes, seconds = text.split(":", 1)
        return float(minutes) * 60.0 + float(seconds)
    return float(text)


def _source_target_anchors(
    *, source: dict[str, Any], target_records: list[dict[str, Any]], cascade_path: Path
) -> tuple[list[dict[str, Any]], int]:
    if _sha256(cascade_path) != source["annotation_sha256"]:
        raise ValueError("M16_EXPERT_REVIEW_CASCADE_HASH_CHANGED")
    payload = _load(cascade_path)
    if (
        payload.get("status") != "approved"
        or payload.get("schema_version") != "2.0.0"
        or payload.get("provenance", {}).get("generated_by") != "human"
    ):
        raise ValueError("M16_EXPERT_REVIEW_CASCADE_SOURCE_INVALID")
    annotation = payload["annotation"]
    entities: dict[str, dict[str, Any]] = {}
    for category in ("agents", "traffic_objects", "traffic_lights", "environments"):
        for entity in annotation.get(category, []):
            entities[entity["id"]] = entity
    event_seconds = int(source["event_timestamp_us"]) / 1_000_000.0
    anchors = []
    missing = 0
    for target in target_records:
        entity = entities.get(target["parent_entity_id"], {})
        keypoints = entity.get("keypoints") or []
        if not keypoints:
            missing += 1
            continue
        point = min(
            keypoints,
            key=lambda item: abs(_timestamp_seconds(item["timestamp"]) - event_seconds),
        )
        x, y = float(point["x"]), float(point["y"])
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            missing += 1
            continue
        delta = abs(_timestamp_seconds(point["timestamp"]) - event_seconds)
        temporal_fit = "AT_EVENT" if delta <= 0.5 else "NEAR_EVENT" if delta <= 2.0 else "CONTEXT_ONLY"
        anchors.append({
            "x": round(x, 6),
            "y": round(y, 6),
            "source_category": target["source_category"],
            "entity_type": entity.get("type") or "UNSPECIFIED",
            "temporal_distance_s": round(delta, 3),
            "temporal_fit": temporal_fit,
        })
    return anchors, missing


def _bounded(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)


def machine_visual_proposal(
    *, scene_slice: str, anchors: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return visible low-confidence candidates, never promoted to ground truth."""
    polygons: dict[str, list[list[list[float]]]] = {
        "EGO_LANE_ZONE": [[
            [0.455, 0.48], [0.545, 0.48], [0.735, 0.98], [0.265, 0.98]
        ]]
    }
    event_points = [
        point for point in anchors
        if point.get("temporal_fit") in {"AT_EVENT", "NEAR_EVENT"}
    ]
    if scene_slice == "PEDESTRIAN_CYCLIST_YIELD" and event_points:
        left = min(point["x"] for point in event_points) - 0.04
        right = max(point["x"] for point in event_points) + 0.04
        top = min(point["y"] for point in event_points) - 0.055
        bottom = max(point["y"] for point in event_points) + 0.055
        polygons["CROSSING_CONFLICT_ZONE"] = [[
            [_bounded(left), _bounded(top)],
            [_bounded(right), _bounded(top)],
            [_bounded(right), _bounded(bottom)],
            [_bounded(left), _bounded(bottom)],
        ]]
    return {
        "proposal_version": "guardsynth-m16-machine-visual-proposal-v0.1",
        "proposal_authority": "EXPERT_CONFIRMATION_REQUIRED",
        "confidence": "LOW",
        "polygons": polygons,
        "basis": [
            "PINNED_MODEL_DRIVABLE_AND_LANE_OVERLAY",
            "CENTRAL_EGO_CORRIDOR_HEURISTIC",
            "CASCADE_SOURCE_TARGET_ANCHOR_WHERE_AVAILABLE",
        ],
    }


def _prior_proposal(record: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "HAZARD_VISIBLE": "HAZARD_TRUE_ACTIVE",
        "NO_HAZARD_VISIBLE": "NOMINAL",
        "NOT_OBSERVABLE": "UNKNOWN",
        "STATE_TRANSITION_VISIBLE": "",
    }
    return {
        "association": record["visual_association_observation"],
        "temporal_observation": record["visual_temporal_observation"],
        "outcome": mapping[record["visual_temporal_observation"]],
        "provenance": "PRIOR_HUMAN_VIDEO_OBSERVATION_NOT_MACHINE_PREDICTION",
    }


def build_review_records() -> tuple[list[dict[str, Any]], dict[str, str]]:
    contact_records, contact_manifest_hash = _extract_embedded_review_records()
    geometry_by_digest, geometry_manifest_hash = _geometry_records()
    observation_by_digest, observation_hash = _prior_observations()
    source_by_digest = _event_sources()
    audit_path = CASCADE_AUDIT_RUN / "CASCADE_STRUCTURED_LINK_AUDIT.json"
    audit_by_digest = {
        record["candidate_digest"]: record
        for record in _load(audit_path)["records"]
    }
    cascade_by_reference = _cascade_paths()
    records = []
    for contact in contact_records:
        digest = contact["candidate_digest"]
        geometry = geometry_by_digest[digest]
        source = source_by_digest[digest]
        audit = audit_by_digest[digest]["cascade_structured_link_audit"]
        cascade_path = cascade_by_reference.get(source["clip_id"])
        if cascade_path is None:
            raise ValueError("M16_EXPERT_REVIEW_CASCADE_SOURCE_MISSING")
        anchors, unanchored_count = _source_target_anchors(
            source=source,
            target_records=audit["active_source_targets"],
            cascade_path=cascade_path,
        )
        t0_frames = [frame for frame in geometry["frames"] if float(frame["offset_s"]) == 0.0]
        if len(t0_frames) != 1:
            raise ValueError("M16_EXPERT_REVIEW_T0_FRAME_INVALID")
        t0 = t0_frames[0]
        observation = observation_by_digest[digest]
        if observation["image_sha256"] != contact["image_sha256"]:
            raise ValueError("M16_EXPERT_REVIEW_OBSERVATION_IMAGE_MISMATCH")
        records.append({
            "review_index": contact["review_index"],
            "candidate_digest": digest,
            "slice": contact["slice"],
            "event_timestamp_us": int(source["event_timestamp_us"]),
            "contact_sheet_data_url": contact["image_data_url"],
            "contact_sheet_sha256": contact["image_sha256"],
            "t0_overlay_data_url": _verified_image_data_url(
                GEOMETRY_RUN, t0["overlay_path"], t0["overlay_sha256"]
            ),
            "t0_overlay_sha256": t0["overlay_sha256"],
            "source_target_anchors": anchors,
            "unanchored_source_target_count": unanchored_count,
            "machine_visual_proposal": machine_visual_proposal(
                scene_slice=contact["slice"], anchors=anchors
            ),
            "prior_observation_proposal": _prior_proposal(observation),
        })
    if (
        len(records) != 60
        or len({record["candidate_digest"] for record in records}) != 60
        or [record["review_index"] for record in records] != list(range(1, 61))
    ):
        raise ValueError("M16_EXPERT_REVIEW_RECORD_SET_INVALID")
    return records, {
        "contact_sheet_run_manifest": contact_manifest_hash,
        "geometry_candidate_manifest": geometry_manifest_hash,
        "prior_video_observation": observation_hash,
        "cascade_structured_link_audit": _sha256(audit_path),
    }


def render_workbench(records: list[dict[str, Any]], input_set_sha256: str) -> str:
    payload = {
        "workbench_version": "guardsynth-m16-expert-source-review-v0.2",
        "input_set_sha256": input_set_sha256,
        "records": records,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
        "<", "\\u003c"
    )
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("__EXPERT_REVIEW_DATA_JSON__") != 1:
        raise RuntimeError("M16_EXPERT_REVIEW_TEMPLATE_MARKER_INVALID")
    rendered = template.replace("__EXPERT_REVIEW_DATA_JSON__", encoded)
    if any(marker in rendered.lower() for marker in ("/home/", "file://", "clip_id")):
        raise ValueError("M16_EXPERT_REVIEW_HTML_SOURCE_IDENTIFIER_LEAKAGE")
    return rendered


def execute(*, output_dir: Path, run_id: str) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError("refusing to overwrite M16 expert source review run")
    if not output_dir.resolve().is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("M16_EXPERT_REVIEW_RESTRICTED_OWNER_SCOPE_REQUIRED")
    records, input_hashes = build_review_records()
    input_set_sha256 = _sha256_bytes(
        json.dumps(input_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    rendered = render_workbench(records, input_set_sha256)
    output_dir.mkdir(parents=True)
    output_dir.chmod(0o700)
    workbench_path = output_dir / WORKBENCH_NAME
    _write_text(workbench_path, rendered)
    anchor_count = sum(len(record["source_target_anchors"]) for record in records)
    anchored_scene_count = sum(bool(record["source_target_anchors"]) for record in records)
    event_near_anchor_count = sum(
        anchor["temporal_fit"] != "CONTEXT_ONLY"
        for record in records for anchor in record["source_target_anchors"]
    )
    event_near_anchored_scene_count = sum(
        any(anchor["temporal_fit"] != "CONTEXT_ONLY" for anchor in record["source_target_anchors"])
        for record in records
    )
    event_polygon_count = sum(
        len(record["machine_visual_proposal"]["polygons"]) > 1 for record in records
    )
    prior_counts = Counter(
        record["prior_observation_proposal"]["temporal_observation"]
        for record in records
    )
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": "M16_MACHINE_ASSISTED_EXPERT_SOURCE_REVIEW_READY",
        "scene_count": len(records),
        "machine_lane_drivable_overlay_count": len(records),
        "machine_ego_corridor_candidate_count": len(records),
        "source_target_anchor_count": anchor_count,
        "source_target_anchored_scene_count": anchored_scene_count,
        "event_near_source_target_anchor_count": event_near_anchor_count,
        "event_near_source_target_anchored_scene_count": event_near_anchored_scene_count,
        "context_only_source_target_anchor_count": anchor_count - event_near_anchor_count,
        "machine_event_zone_candidate_count": event_polygon_count,
        "prior_observation_proposal_count": len(records),
        "prior_temporal_observation_counts": dict(sorted(prior_counts.items())),
        "expert_review_completed_count": 0,
        "minimum_independent_expert_count": 2,
        "adjudication_required": True,
        "formal_pilot_annotation_started": False,
        "machine_candidate_promoted_to_ground_truth": False,
        "source_complete_scene_count_changed": False,
        "eligible_scene_count": 1,
        "claim_scope": CLAIM_SCOPE,
    }
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip() or "NO_GIT_METADATA"
    manifest = {
        **result,
        "code_revision": revision,
        "input_hashes": input_hashes,
        "input_set_sha256": input_set_sha256,
        "output_hashes": {"expert_source_review_workbench": _sha256(workbench_path)},
        "image_bytes_in_html": True,
        "image_bytes_in_export": False,
        "network_access_blocked_by_csp": True,
        "raw_source_paths_included": False,
        "raw_video_replicated": False,
    }
    report = f"""# M16 기계 보조 전문가 source review 패키지

- 상태: `{result['status']}`
- 검토 장면: **{len(records)}**
- 모델 lane/drivable overlay: **{len(records)}/60**
- source-linked 좌표 anchor: **{anchor_count}개 / {anchored_scene_count}장면**
- 사건 시각 ±2초 target anchor: **{event_near_anchor_count}개 / {event_near_anchored_scene_count}장면**
- context-only anchor: **{anchor_count - event_near_anchor_count}개**
- 저신뢰 에고 통로 후보: **{len(records)}/60**
- 저신뢰 사건 영역 후보: **{event_polygon_count}/60**
- 실제 전문가 검토 완료: **0/60**

기계 표시는 후보이며 ground truth로 승격하지 않았다. 기존 영상 관찰 60건도 provenance를
`PRIOR_HUMAN_VIDEO_OBSERVATION_NOT_MACHINE_PREDICTION`으로 보존해 초안으로만 제시한다.
최소 2인의 독립 전문가 export와 별도 adjudication 전에는 source-complete, outcome, eligible
또는 formal pilot start gate를 변경하지 않는다.
"""
    _write_json(output_dir / "RESULT.json", result)
    _write_json(output_dir / "RUN_MANIFEST.json", manifest)
    _write_text(output_dir / "REPORT_KO.md", report)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    result = execute(output_dir=args.output_dir, run_id=args.run_id)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
