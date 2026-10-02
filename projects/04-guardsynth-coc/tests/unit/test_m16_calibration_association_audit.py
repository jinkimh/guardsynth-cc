"""Fail-closed M16 calibration and association review tests."""

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

from guard_synth.m16_calibration_association_audit import (
    association_review_status,
    extrinsics_variant_delta,
    public_calibration_association_summary,
)


class M16CalibrationAssociationAuditTest(unittest.TestCase):
    def test_extrinsics_variant_delta_detects_translation(self) -> None:
        online = {"qx": 0, "qy": 0, "qz": 0, "qw": 1, "x": 0, "y": 0, "z": 0}
        offline = {**online, "x": 0.1}
        delta = extrinsics_variant_delta(online, offline)
        self.assertAlmostEqual(delta["translation_delta_m"], 0.1)
        self.assertEqual(delta["rotation_delta_rad"], 0.0)

    def test_association_queue_never_converts_missing_lane_to_final_binding(self) -> None:
        status = association_review_status(
            slice_name="FOLLOWING_CUT_IN",
            relevant_agent_keypoints=1,
            zone_keypoints=0,
            control_keypoints=0,
            obstacle_tracks=4,
        )
        self.assertEqual(status, "REVIEWABLE_ACTOR_ASSOCIATION_LANE_MISSING")

    def test_public_summary_keeps_transform_and_outcome_fail_closed(self) -> None:
        calibration = [{
            "calibration_closure": "5_OF_5",
            "recorded_rig_binding_status": "AVAILABLE_SOURCE_LINKED",
            "coordinate_transform_status": (
                "REVIEW_REQUIRED_ONLINE_OFFLINE_VARIANT_SELECTION"
            ),
        }]
        queue = [{"association_review_status": "REVIEWABLE_ACTOR_ZONE_ASSOCIATION"}]
        summary = public_calibration_association_summary(calibration, queue)
        self.assertEqual(summary["recorded_rig_binding_available_count"], 1)
        self.assertEqual(summary["verified_coordinate_transform_count"], 0)
        self.assertEqual(summary["final_outcome_assigned_count"], 0)


if __name__ == "__main__":
    unittest.main()
