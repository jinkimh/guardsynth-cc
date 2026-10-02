"""Contracts for source-bound M16 machine geometry candidates."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
SRC = ROOT / "projects/04-guardsynth-coc/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.m16_geometry_candidate import (
    build_geometry_candidate_record,
    public_geometry_candidate_summary,
    summarize_geometry_candidates,
)


def _sha(character: str) -> str:
    return character * 64


def _frames() -> list[dict]:
    return [
        {
            "offset_s": offset,
            "frame_index": 100 + index,
            "timestamp_us": 1_000_000 + round(offset * 1_000_000),
            "source_pixel_sha256": _sha("a"),
            "drivable_mask_sha256": _sha("b"),
            "lane_mask_sha256": _sha("c"),
            "overlay_sha256": _sha("d"),
            "width_px": 1920,
            "height_px": 1080,
        }
        for index, offset in enumerate((-1.0, -0.5, 0.0, 0.5, 1.0))
    ]


class M16GeometryCandidateTest(unittest.TestCase):
    def test_machine_candidate_is_bound_but_does_not_close_scene_fields(self) -> None:
        record = build_geometry_candidate_record(
            candidate_digest="candidate-sha256:" + _sha("e"),
            asset_candidate_digest="candidate-sha256:" + _sha("f"),
            scene_slice="FOLLOWING_CUT_IN",
            event_timestamp_us=1_000_000,
            source_video_sha256=_sha("1"),
            model_source_revision=_sha("2")[:40],
            model_weight_sha256=_sha("3"),
            frame_records=_frames(),
        )
        self.assertEqual(record["machine_geometry_status"], "SOURCE_BOUND_CANDIDATE")
        self.assertEqual(record["curator_status"], "PENDING")
        self.assertFalse(record["source_complete"])
        self.assertFalse(record["eligible"])
        self.assertEqual(record["source_field_updates"], {})

    def test_missing_five_frame_contract_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "FIVE_FRAME"):
            build_geometry_candidate_record(
                candidate_digest="candidate-sha256:" + _sha("e"),
                asset_candidate_digest="candidate-sha256:" + _sha("f"),
                scene_slice="STOP_SIGNALS",
                event_timestamp_us=1_000_000,
                source_video_sha256=_sha("1"),
                model_source_revision=_sha("2")[:40],
                model_weight_sha256=_sha("3"),
                frame_records=_frames()[:-1],
            )

    def test_summary_preserves_fail_closed_counts(self) -> None:
        record = build_geometry_candidate_record(
            candidate_digest="candidate-sha256:" + _sha("e"),
            asset_candidate_digest="candidate-sha256:" + _sha("f"),
            scene_slice="PEDESTRIAN_CYCLIST_YIELD",
            event_timestamp_us=1_000_000,
            source_video_sha256=_sha("1"),
            model_source_revision=_sha("2")[:40],
            model_weight_sha256=_sha("3"),
            frame_records=_frames(),
        )
        summary = summarize_geometry_candidates([record])
        self.assertEqual(summary["source_bound_machine_candidate_count"], 1)
        self.assertEqual(summary["curator_pending_count"], 1)
        self.assertEqual(summary["new_source_complete_count"], 0)
        self.assertEqual(summary["new_eligible_count"], 0)

        public = public_geometry_candidate_summary({**summary, "records": [record]})
        self.assertNotIn("records", public)
        self.assertNotIn("candidate-sha256", str(public))


if __name__ == "__main__":
    unittest.main()
