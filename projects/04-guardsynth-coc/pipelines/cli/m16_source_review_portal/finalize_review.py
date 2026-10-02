#!/usr/bin/env python3
"""Validate and finalize one restricted M16 human video-observation export."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
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
OUTPUT_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-source-review-001"
)
DEFAULT_PACKET = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-source-acquisition-2026-08-14-v18/"
    "HUMAN_SOURCE_REVIEW_PACKET.json"
)
DEFAULT_SOURCE_HTML = OUTPUT_ROOT / (
    "m16-source-review-2026-08-15-v5/source_review_with_images.html"
)
JSON_NAME = "m16_video_observation_review.json"
CSV_NAME = "m16_video_observation_review.csv"
SUMMARY_NAME = "HUMAN_VIDEO_OBSERVATION_SUMMARY.json"
EXPECTED_REVIEW_VERSION = "guardsynth-m16-video-observation-v0.2"
EXPECTED_RECORD_COUNT = 60
ASSOCIATION_VALUES = {
    "CLEAR_VISIBLE",
    "AMBIGUOUS_VISIBLE",
    "NOT_OBSERVABLE",
}
TEMPORAL_VALUES = {
    "NO_HAZARD_VISIBLE",
    "HAZARD_VISIBLE",
    "STATE_TRANSITION_VISIBLE",
    "NOT_OBSERVABLE",
}
RECORD_FIELDS = {
    "candidate_digest",
    "review_index",
    "slice",
    "image_sha256",
    "reviewer_id",
    "visual_association_observation",
    "visual_temporal_observation",
    "notes",
    "image_bytes_included",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _embedded_review_data(path: Path) -> dict[str, Any]:
    matched = re.search(
        r'<script id="reviewData" type="application/json">(.*?)</script>',
        path.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    if matched is None:
        raise ValueError("SOURCE_REVIEW_DATA_MISSING")
    return json.loads(matched.group(1))


def _normalized_record(record: dict[str, Any]) -> dict[str, str]:
    normalized = {key: str(record.get(key, "")) for key in RECORD_FIELDS}
    normalized["image_bytes_included"] = normalized[
        "image_bytes_included"
    ].lower()
    return normalized


def validate_review_export(
    json_path: Path,
    csv_path: Path,
    packet_path: Path,
    source_html_path: Path,
) -> dict[str, Any]:
    required = (json_path, csv_path, packet_path, source_html_path)
    if any(not path.is_file() for path in required):
        raise FileNotFoundError("M16_VIDEO_OBSERVATION_INPUT_MISSING")
    export = _load(json_path)
    packet = _load(packet_path)
    embedded = _embedded_review_data(source_html_path)
    records = export.get("records")
    if (
        export.get("review_version") != EXPECTED_REVIEW_VERSION
        or export.get("image_bytes_included") is not False
        or not isinstance(records, list)
        or len(records) != EXPECTED_RECORD_COUNT
        or packet.get("record_count") != EXPECTED_RECORD_COUNT
        or len(packet.get("records", ())) != EXPECTED_RECORD_COUNT
        or len(embedded.get("records", ())) != EXPECTED_RECORD_COUNT
    ):
        raise ValueError("REVIEW_EXPORT_CONTRACT_INVALID")
    packet_sha256 = _sha256(packet_path)
    if (
        export.get("packet_sha256") != packet_sha256
        or embedded.get("packet_sha256") != packet_sha256
    ):
        raise ValueError("SOURCE_REFERENCE_MISMATCH")

    reviewer_ids = set()
    candidate_digests = set()
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict) or set(record) != RECORD_FIELDS:
            raise ValueError("REVIEW_RECORD_SCHEMA_INVALID")
        association = record.get("visual_association_observation")
        temporal = record.get("visual_temporal_observation")
        reviewer_id = str(record.get("reviewer_id", "")).strip()
        notes = record.get("notes")
        if (
            association not in ASSOCIATION_VALUES
            or temporal not in TEMPORAL_VALUES
            or not reviewer_id
            or not isinstance(notes, str)
            or record.get("image_bytes_included") is not False
        ):
            raise ValueError("OBSERVATION_VALUE_INVALID")
        if int(record.get("review_index", 0)) != index:
            raise ValueError("REVIEW_INDEX_INVALID")
        if (
            association != "CLEAR_VISIBLE"
            and temporal != "NOT_OBSERVABLE"
        ):
            raise ValueError("OBSERVATION_PAIR_INCONSISTENT")
        if temporal == "STATE_TRANSITION_VISIBLE" and not notes.strip():
            raise ValueError("TRANSITION_NOTE_REQUIRED")
        reviewer_ids.add(reviewer_id)
        candidate_digests.add(record["candidate_digest"])
    if len(candidate_digests) != EXPECTED_RECORD_COUNT:
        raise ValueError("CANDIDATE_DUPLICATE")

    packet_records = packet["records"]
    embedded_records = embedded["records"]
    if any(
        record["candidate_digest"] != packet_record["candidate_digest"]
        or record["slice"] != packet_record["slice"]
        or record["candidate_digest"] != embedded_record["candidate_digest"]
        or int(record["review_index"]) != int(embedded_record["review_index"])
        or record["slice"] != embedded_record["slice"]
        or record["image_sha256"] != embedded_record["image_sha256"]
        for record, packet_record, embedded_record in zip(
            records, packet_records, embedded_records
        )
    ):
        raise ValueError("SOURCE_REFERENCE_MISMATCH")

    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        csv_records = list(reader)
    if (
        set(reader.fieldnames or ()) != RECORD_FIELDS
        or len(csv_records) != EXPECTED_RECORD_COUNT
        or [_normalized_record(item) for item in records]
        != [_normalized_record(item) for item in csv_records]
    ):
        raise ValueError("JSON_CSV_MISMATCH")

    slice_counts = Counter(item["slice"] for item in records)
    association_counts = Counter(
        item["visual_association_observation"] for item in records
    )
    temporal_counts = Counter(
        item["visual_temporal_observation"] for item in records
    )
    slice_observations = {}
    for slice_name in sorted(slice_counts):
        selected = [item for item in records if item["slice"] == slice_name]
        slice_observations[slice_name] = {
            "record_count": len(selected),
            "association_counts": dict(sorted(Counter(
                item["visual_association_observation"] for item in selected
            ).items())),
            "temporal_counts": dict(sorted(Counter(
                item["visual_temporal_observation"] for item in selected
            ).items())),
        }
    transition_records = [
        item
        for item in records
        if item["visual_temporal_observation"] == "STATE_TRANSITION_VISIBLE"
    ]
    return {
        "summary_version": "guardsynth-m16-video-observation-summary-v0.1",
        "status": "HUMAN_VIDEO_OBSERVATION_COMPLETE",
        "review_record_count": len(records),
        "human_review_completed_count": len(records),
        "reviewer_count": len(reviewer_ids),
        "slice_counts": dict(sorted(slice_counts.items())),
        "association_counts": dict(sorted(association_counts.items())),
        "temporal_counts": dict(sorted(temporal_counts.items())),
        "slice_observations": slice_observations,
        "notes_nonempty_count": sum(bool(item["notes"].strip()) for item in records),
        "transition_note_complete_count": sum(
            bool(item["notes"].strip()) for item in transition_records
        ),
        "not_observable_record_count": sum(
            item["visual_association_observation"] == "NOT_OBSERVABLE"
            or item["visual_temporal_observation"] == "NOT_OBSERVABLE"
            for item in records
        ),
        "json_csv_match": True,
        "packet_hash_match": True,
        "candidate_order_match": True,
        "image_hash_match": True,
        "candidate_identifiers_included": False,
        "reviewer_identifiers_included": False,
    }


def _git_revision() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "NO_GIT_METADATA"


def finalize(
    run_dir: Path,
    packet_path: Path = DEFAULT_PACKET,
    source_html_path: Path = DEFAULT_SOURCE_HTML,
) -> dict[str, Any]:
    resolved = run_dir.resolve()
    if not resolved.is_relative_to(OUTPUT_ROOT.resolve()) or resolved == OUTPUT_ROOT.resolve():
        raise ValueError("RESTRICTED_OWNER_SCOPED_RUN_REQUIRED")
    output_files = (
        run_dir / SUMMARY_NAME,
        run_dir / "RESULT.json",
        run_dir / "RUN_MANIFEST.json",
        run_dir / "REPORT_KO.md",
    )
    if any(path.exists() for path in output_files):
        raise FileExistsError("refusing to overwrite finalized review run")
    json_path = run_dir / JSON_NAME
    csv_path = run_dir / CSV_NAME
    summary = validate_review_export(
        json_path, csv_path, packet_path, source_html_path
    )
    result = {
        "experiment_id": "GUARDSYNTH-M16-SOURCE-REVIEW-001",
        "run_id": run_dir.name,
        "status": (
            "HUMAN_VIDEO_OBSERVATION_COMPLETE_"
            "CURATOR_SOURCE_CLOSURE_REQUIRED"
        ),
        "review_record_count": summary["review_record_count"],
        "human_review_completed_count": summary[
            "human_review_completed_count"
        ],
        "reviewer_count": summary["reviewer_count"],
        "slice_counts": summary["slice_counts"],
        "association_counts": summary["association_counts"],
        "temporal_counts": summary["temporal_counts"],
        "json_csv_match": True,
        "packet_hash_match": True,
        "candidate_order_match": True,
        "image_hash_match": True,
        "source_closure_completed": False,
        "annotation_start_allowed": False,
        "eligible_scene_count": 1,
        "claim_scope": "VIDEO_OBSERVATION_ONLY_NOT_SOURCE_CLOSURE_OR_SAFETY",
    }
    manifest = {
        **result,
        "run_date": date.today().isoformat(),
        "input_class": "LICENSE_RESTRICTED_HUMAN_VIDEO_OBSERVATION",
        "code_revision": _git_revision(),
        "workspace_dirty_state_preserved": True,
        "source_hashes": {
            "human_source_review_packet": _sha256(packet_path),
            "source_review_html": _sha256(source_html_path),
            "review_json": _sha256(json_path),
            "review_csv": _sha256(csv_path),
            "finalizer": _sha256(Path(__file__).resolve()),
        },
        "summary_file": SUMMARY_NAME,
        "raw_image_bytes_included": False,
        "candidate_identifiers_in_aggregate_outputs": False,
        "reviewer_identifiers_in_aggregate_outputs": False,
    }
    run_dir.chmod(0o700)
    json_path.chmod(0o600)
    csv_path.chmod(0o600)
    _write_json(run_dir / SUMMARY_NAME, summary)
    _write_json(run_dir / "RESULT.json", result)
    _write_json(run_dir / "RUN_MANIFEST.json", manifest)
    report = (
        "# M16 human video-observation 검토 결과\n\n"
        f"- 상태: **{result['status']}**\n"
        "- 검증된 human video observation: **60/60**\n"
        f"- 검토자 수: **{result['reviewer_count']}명**\n"
        f"- association: `{json.dumps(result['association_counts'], ensure_ascii=False, sort_keys=True)}`\n"
        f"- temporal state: `{json.dumps(result['temporal_counts'], ensure_ascii=False, sort_keys=True)}`\n"
        "- JSON/CSV, packet candidate 순서, slice와 image hash: **모두 일치**\n"
        "- source closure: **미완료**\n"
        "- 현재 eligible scene: **1/60**\n"
        "- formal expert annotation 시작: **금지**\n\n"
        "이 run은 한 명의 검토자가 60개 후보 이벤트에서 영상으로 직접 관찰한 association과 "
        "시간 상태만 확정한다. geometry, coordinate transform, jurisdiction authority, rule "
        "applicability와 lifecycle source witness를 폐쇄하지 않으며 법규 또는 차량 안전성 판정으로 "
        "사용하지 않는다. 다음 작업은 curator source closure와 60개 distinct 8/8 eligible scene "
        "구축이다.\n"
    )
    report_path = run_dir / "REPORT_KO.md"
    report_path.write_text(report, encoding="utf-8")
    report_path.chmod(0o600)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--source-html", type=Path, default=DEFAULT_SOURCE_HTML)
    args = parser.parse_args()
    result = finalize(args.run_dir, args.packet, args.source_html)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
