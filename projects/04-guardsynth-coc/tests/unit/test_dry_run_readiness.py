from __future__ import annotations

import unittest

from guard_synth.dry_run_readiness import (
    REQUIRED_SCENE_FIELDS,
    STRATA,
    assess_dry_run_readiness,
    build_twenty_four_slot_plan,
)
from guard_synth.source_catalog import KR_FIXTURE_PATH, load_source_catalog


class DryRunReadinessTest(unittest.TestCase):
    def test_plan_has_eight_slots_per_slice(self) -> None:
        slots = build_twenty_four_slot_plan()
        self.assertEqual(len(slots), 24)
        counts = {}
        for slot in slots:
            counts[slot["slice"]] = counts.get(slot["slice"], 0) + 1
        self.assertEqual(set(counts.values()), {8})

    def test_each_slice_has_all_locked_strata(self) -> None:
        slots = build_twenty_four_slot_plan()
        for slice_name in {item["slice"] for item in slots}:
            self.assertEqual(
                {item["stratum"] for item in slots if item["slice"] == slice_name},
                set(STRATA),
            )

    def test_unassigned_slots_are_not_synthetic_filled(self) -> None:
        for slot in build_twenty_four_slot_plan():
            self.assertIsNone(slot["real_scene_ref"])
            self.assertFalse(slot["source_complete"])
            self.assertFalse(slot["synthetic_fill"])

    def test_required_fields_include_association_transform_and_assurance(self) -> None:
        required = set(REQUIRED_SCENE_FIELDS)
        self.assertIn("target_zone_or_lane_association", required)
        self.assertIn("verified_coordinate_transform", required)
        self.assertIn("source_bearing_vehicle_assurance_profile", required)

    def test_zero_source_complete_inputs_block_execution(self) -> None:
        aggregate = {"readiness_summary": {
            "actual_candidate_event_count": 5,
            "adapted_candidate_count": 4,
            "source_complete_scene_count": 0,
            "missing_scene_input_slot_count": 19,
            "reason_code_counts": {
                "MISSING_OR_AMBIGUOUS_TARGET_ZONE_ASSOCIATION": 4,
                "UNVERIFIED_COORDINATE_TRANSFORM": 4,
                "MISSING_VEHICLE_ASSURANCE_PROFILE": 4,
            },
        }}
        result = assess_dry_run_readiness(load_source_catalog(KR_FIXTURE_PATH), aggregate)
        self.assertEqual(result["status"], "BLOCKED_INPUT")
        self.assertEqual(result["decision"], "M13_BLOCKED_SOURCE_COMPLETE_SCENES")
        self.assertEqual(result["execution"]["guardsynth_eblc_core_z3_scene_runs"], 0)
        self.assertTrue(result["catalog_gate"]["ready"])
        self.assertFalse(result["input_readiness"]["synthetic_scene_fill_performed"])


if __name__ == "__main__":
    unittest.main()
