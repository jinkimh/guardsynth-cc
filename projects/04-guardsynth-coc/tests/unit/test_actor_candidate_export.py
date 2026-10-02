from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.actor_candidate_export import (
    ActorCandidateExportError,
    serialize_actor_candidate,
)


class ActorCandidateExportTest(unittest.TestCase):
    def test_candidate_preserves_rank_geometry_rate_and_track_samples(self) -> None:
        record = serialize_actor_candidate(
            row={
                "track_id": "track-1",
                "label_class": "person",
                "longitudinal_gap_m": 4.0,
                "center_y": 0.2,
                "timestamp_error_us": 1000,
            },
            rates={"sample_count": 3, "gap_rate_mps": -1.0, "closing_speed_mps": 1.0},
            rank=2,
            track_samples=[
                {"timestamp_us": 900000, "center_x_m": 5.2, "center_y_m": 0.2},
                {"timestamp_us": 1000000, "center_x_m": 5.1, "center_y_m": 0.2},
            ],
        )
        self.assertEqual(record["rank_by_longitudinal_gap"], 2)
        self.assertEqual(record["track_id"], "track-1")
        self.assertEqual(record["candidate_ttc_s"], 4.0)
        self.assertEqual(len(record["track_samples"]), 2)

    def test_missing_or_nonfinite_required_values_fail_closed(self) -> None:
        base = {
            "track_id": "track-1",
            "label_class": "person",
            "longitudinal_gap_m": 4.0,
            "center_y": 0.2,
            "timestamp_error_us": 1000,
        }
        with self.assertRaisesRegex(ActorCandidateExportError, "missing label_class"):
            serialize_actor_candidate(
                row={**base, "label_class": ""}, rates={}, rank=1, track_samples=[]
            )
        with self.assertRaisesRegex(ActorCandidateExportError, "invalid longitudinal_gap_m"):
            serialize_actor_candidate(
                row={**base, "longitudinal_gap_m": float("nan")},
                rates={},
                rank=1,
                track_samples=[],
            )

    def test_track_samples_must_be_time_ordered_and_nonempty(self) -> None:
        row = {
            "track_id": "track-1",
            "label_class": "person",
            "longitudinal_gap_m": 4.0,
            "center_y": 0.2,
            "timestamp_error_us": 1000,
        }
        with self.assertRaisesRegex(ActorCandidateExportError, "track_samples"):
            serialize_actor_candidate(row=row, rates={}, rank=1, track_samples=[])
        with self.assertRaisesRegex(ActorCandidateExportError, "strictly ordered"):
            serialize_actor_candidate(
                row=row,
                rates={},
                rank=1,
                track_samples=[
                    {"timestamp_us": 2, "center_x_m": 1.0, "center_y_m": 0.0},
                    {"timestamp_us": 1, "center_x_m": 1.0, "center_y_m": 0.0},
                ],
            )


if __name__ == "__main__":
    unittest.main()
