"""M16 event-anchor coordinate-transform contracts."""

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

from guard_synth.m16_event_anchor_transform import (
    apply_verified_event_anchor_transforms,
    public_event_anchor_transform_summary,
    verify_event_anchor_transform,
)


class M16EventAnchorTransformTest(unittest.TestCase):
    def test_event_timestamp_is_bound_as_m16_scene_anchor(self) -> None:
        result = verify_event_anchor_transform(
            egomotion_rows=[
                {"timestamp": 0, "qx": 0.0, "qy": 0.0, "qz": 0.0, "qw": 1.0,
                 "x": 0.0, "y": 0.0, "z": 0.0},
                {"timestamp": 100_000, "qx": 0.0, "qy": 0.0, "qz": 0.1,
                 "qw": 0.9949874371, "x": 1.0, "y": 0.2, "z": 0.0},
            ],
            event_timestamp_us=50_000,
            egomotion_sha256="a" * 64,
            offline_extrinsics_sha256="b" * 64,
        )
        self.assertEqual(result["status"], "AVAILABLE_SOURCE_LINKED")
        self.assertEqual(result["t0_binding"], "M16_REVIEW_EVENT_TIMESTAMP")
        self.assertEqual(result["event_timestamp_us"], 50_000)
        self.assertEqual(result["t0_us"], 50_000)
        self.assertEqual(result["bracketing_timestamp_us"], [0, 100_000])
        self.assertLessEqual(result["inverse_closure_max_abs_error"], 1e-12)
        self.assertLessEqual(result["event_to_t0_identity_max_abs_error"], 1e-12)

    def test_event_outside_offline_egomotion_range_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "EVENT_NOT_BRACKETED_BY_OFFLINE_EGOMOTION"):
            verify_event_anchor_transform(
                egomotion_rows=[
                    {"timestamp": 10, "qx": 0.0, "qy": 0.0, "qz": 0.0,
                     "qw": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
                    {"timestamp": 20, "qx": 0.0, "qy": 0.0, "qz": 0.0,
                     "qw": 1.0, "x": 1.0, "y": 0.0, "z": 0.0},
                ],
                event_timestamp_us=30,
                egomotion_sha256="a" * 64,
                offline_extrinsics_sha256="b" * 64,
            )

    def test_verified_transforms_close_only_the_transform_field(self) -> None:
        digest = "candidate-sha256:" + "c" * 64
        audit = {
            "classified_event_count": 1,
            "verified_coordinate_transform_count": 0,
            "source_complete_8_of_8_count": 0,
            "newly_eligible_scene_count": 0,
            "remaining_field_event_counts": {
                "relevant_actor_or_control_state": 1,
                "target_zone_or_lane_association": 1,
                "conflict_stop_or_following_geometry": 1,
                "verified_coordinate_transform": 1,
                "applicable_rule_scope": 1,
                "outcome_lifecycle_witness": 1,
            },
            "records": [{
                "candidate_digest": digest,
                "coordinate_transform_status": "REVIEW_REQUIRED_MODEL_T0_BINDING_AND_NUMERIC_CLOSURE",
                "field_status": {
                    "verified_coordinate_transform": "REVIEW_REQUIRED_MODEL_T0_BINDING_AND_NUMERIC_CLOSURE",
                    "target_zone_or_lane_association": "REVIEW_REQUIRED_SOURCE_GEOMETRY",
                },
                "source_complete": False,
                "eligible": False,
            }],
        }
        transformed = apply_verified_event_anchor_transforms(
            audit,
            {digest: {
                "status": "AVAILABLE_SOURCE_LINKED",
                "event_timestamp_us": 50_000,
                "t0_us": 50_000,
                "inverse_closure_max_abs_error": 0.0,
            }},
        )
        self.assertEqual(transformed["verified_coordinate_transform_count"], 1)
        self.assertNotIn(
            "verified_coordinate_transform",
            transformed["remaining_field_event_counts"],
        )
        record = transformed["records"][0]
        self.assertEqual(
            record["field_status"]["verified_coordinate_transform"],
            "AVAILABLE_SOURCE_LINKED",
        )
        self.assertFalse(record["source_complete"])
        self.assertFalse(record["eligible"])

    def test_public_summary_removes_per_event_records(self) -> None:
        public = public_event_anchor_transform_summary({
            "verified_coordinate_transform_count": 1,
            "records": [{"candidate_digest": "candidate-sha256:" + "d" * 64}],
        })
        self.assertNotIn("records", public)
        self.assertNotIn("candidate-sha256", str(public))


if __name__ == "__main__":
    unittest.main()
