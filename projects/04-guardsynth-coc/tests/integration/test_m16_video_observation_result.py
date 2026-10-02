"""Contracts for finalizing the M16 human video-observation export."""

from __future__ import annotations

import csv
import importlib.util
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
FINALIZE = ROOT / (
    "projects/04-guardsynth-coc/pipelines/cli/"
    "m16_source_review_portal/finalize_review.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "m16_video_observation_result", FINALIZE
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fixture_records() -> list[dict[str, object]]:
    slices = (
        "PEDESTRIAN_CYCLIST_YIELD",
        "STOP_SIGNALS",
        "FOLLOWING_CUT_IN",
    )
    records = []
    for index in range(1, 61):
        records.append({
            "candidate_digest": "candidate-sha256:" + f"{index:064x}",
            "review_index": index,
            "slice": slices[(index - 1) % len(slices)],
            "image_sha256": f"{index + 100:064x}",
            "reviewer_id": "reviewer-a",
            "visual_association_observation": "CLEAR_VISIBLE",
            "visual_temporal_observation": "NO_HAZARD_VISIBLE",
            "notes": "",
            "image_bytes_included": False,
        })
    records[0]["visual_temporal_observation"] = "STATE_TRANSITION_VISIBLE"
    records[0]["notes"] = "위험 해제"
    return records


def write_fixture(directory: Path) -> tuple[Path, Path, Path, Path]:
    records = fixture_records()
    packet = {
        "record_count": len(records),
        "records": [
            {
                "candidate_digest": item["candidate_digest"],
                "slice": item["slice"],
            }
            for item in records
        ],
    }
    packet_path = directory / "packet.json"
    packet_path.write_text(
        json.dumps(packet, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    import hashlib

    export = {
        "review_version": "guardsynth-m16-video-observation-v0.2",
        "packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
        "exported_at": "2026-09-04T21:35:11.421Z",
        "image_bytes_included": False,
        "records": records,
    }
    json_path = directory / "review.json"
    json_path.write_text(
        json.dumps(export, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    csv_path = directory / "review.csv"
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
    csv_path.write_text(stream.getvalue(), encoding="utf-8")
    embedded = {
        "packet_sha256": export["packet_sha256"],
        "records": [
            {
                "candidate_digest": item["candidate_digest"],
                "review_index": item["review_index"],
                "slice": item["slice"],
                "image_sha256": item["image_sha256"],
            }
            for item in records
        ],
    }
    html_path = directory / "review.html"
    html_path.write_text(
        '<script id="reviewData" type="application/json">'
        + json.dumps(embedded)
        + "</script>",
        encoding="utf-8",
    )
    return json_path, csv_path, packet_path, html_path


class M16VideoObservationResultTest(unittest.TestCase):
    def test_complete_export_is_validated_and_aggregated(self) -> None:
        module = load_module()
        with TemporaryDirectory() as directory:
            paths = write_fixture(Path(directory))
            result = module.validate_review_export(*paths)
        self.assertEqual(result["human_review_completed_count"], 60)
        self.assertEqual(result["reviewer_count"], 1)
        self.assertEqual(result["transition_note_complete_count"], 1)
        self.assertNotIn("candidate_digest", str(result))
        self.assertNotIn("reviewer-a", str(result))

    def test_missing_or_invalid_observation_is_rejected(self) -> None:
        module = load_module()
        with TemporaryDirectory() as directory:
            json_path, csv_path, packet_path, html_path = write_fixture(
                Path(directory)
            )
            export = json.loads(json_path.read_text(encoding="utf-8"))
            export["records"][4]["visual_temporal_observation"] = ""
            json_path.write_text(json.dumps(export), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "OBSERVATION_VALUE_INVALID"):
                module.validate_review_export(
                    json_path, csv_path, packet_path, html_path
                )

    def test_candidate_or_image_reference_mismatch_is_rejected(self) -> None:
        module = load_module()
        with TemporaryDirectory() as directory:
            json_path, csv_path, packet_path, html_path = write_fixture(
                Path(directory)
            )
            export = json.loads(json_path.read_text(encoding="utf-8"))
            export["records"][2]["image_sha256"] = "f" * 64
            json_path.write_text(json.dumps(export), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SOURCE_REFERENCE_MISMATCH"):
                module.validate_review_export(
                    json_path, csv_path, packet_path, html_path
                )

    def test_json_and_csv_must_match(self) -> None:
        module = load_module()
        with TemporaryDirectory() as directory:
            json_path, csv_path, packet_path, html_path = write_fixture(
                Path(directory)
            )
            csv_text = csv_path.read_text(encoding="utf-8")
            csv_path.write_text(
                csv_text.replace("NO_HAZARD_VISIBLE", "HAZARD_VISIBLE", 1),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "JSON_CSV_MISMATCH"):
                module.validate_review_export(
                    json_path, csv_path, packet_path, html_path
                )


if __name__ == "__main__":
    unittest.main()
