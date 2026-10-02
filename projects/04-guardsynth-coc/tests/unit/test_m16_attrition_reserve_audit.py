"""Unit contract for event-level M16 attrition reserve summaries."""

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

from guard_synth.m16_attrition_reserve_audit import (
    public_attrition_reserve_summary,
)


class M16AttritionReserveAuditTest(unittest.TestCase):
    def test_summary_keeps_event_evidence_separate_from_scene_eligibility(self) -> None:
        records = [
            {
                "reserve_tier": tier,
                "temporal_closure": True,
                "calibration_closure": "5_OF_5",
                "recorded_rig_binding_status": "AVAILABLE_SOURCE_LINKED",
                "coordinate_transform_status": (
                    "REVIEW_REQUIRED_ONLINE_OFFLINE_VARIANT_SELECTION"
                ),
                "association_review_status": association,
                "clip_id": f"private-{index}",
            }
            for index, (tier, association) in enumerate(
                (
                    ("NEW_CLIP_PRIMARY", "REVIEWABLE_ACTOR_ASSOCIATION_LANE_MISSING"),
                    ("NEW_CLIP_SECONDARY_EVENT", "INSUFFICIENT_SOURCE_GEOMETRY_FOR_ASSOCIATION"),
                    ("MATERIALIZED_CLIP_SECONDARY_EVENT", "REVIEWABLE_CONTROL_ASSOCIATION_LANE_MISSING"),
                )
            )
        ]

        summary = public_attrition_reserve_summary(records)

        self.assertEqual(summary["audited_reserve_event_count"], 3)
        self.assertEqual(summary["temporal_closure_event_count"], 3)
        self.assertEqual(summary["verified_coordinate_transform_event_count"], 0)
        self.assertEqual(summary["source_complete_8_of_8_event_count"], 0)
        self.assertEqual(summary["final_outcome_assigned_count"], 0)
        self.assertNotIn("private-", repr(summary))


if __name__ == "__main__":
    unittest.main()
