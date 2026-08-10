import unittest

from experiments.eblc_p0b.adapters.real_scene_adapter import derive_context_candidate


class RealSceneAdapterUnitTest(unittest.TestCase):
    def base_event(self, candidate_count=2):
        return {
            "timestamp_us": 1_000_000,
            "candidate_count": candidate_count,
            "nearest_candidate": {
                "track_id": "restricted-track-not-emitted",
                "label_class": "person",
                "longitudinal_gap_m": 4.0,
                "lateral_center_m": 0.2,
            },
        }

    def adapt(self, event=None):
        return derive_context_candidate(
            episode_ordinal=0,
            event_ordinal=0,
            clip_id="restricted-clip-not-emitted",
            event=event or self.base_event(),
            vehicle_dimensions={"rear_axle_to_front_extent_m": 3.0},
            ego_state={"pose_relative_t0_m": [0.1, 0.0, 0.0], "speed_mps": 1.0, "relative_time_s": 0.1},
            coc_claim="claim content must not be emitted",
        )

    def test_actual_fields_derive_one_dimensional_zone_without_legal_claim(self):
        result = self.adapt()
        self.assertEqual(result["context_graph"]["zone_entry_x_m"], 7.0)
        self.assertFalse(result["conflict_zone"]["crosswalk_or_legal_zone_claimed"])
        self.assertTrue(result["context_schema_valid"])

    def test_multiple_candidates_remain_unknown_and_review_required(self):
        result = self.adapt()
        self.assertEqual(result["context_graph"]["hazard_fact"]["truth"], "UNKNOWN")
        self.assertEqual(result["target_binding"]["verdict"], "REVIEW_REQUIRED")
        self.assertIn("AMBIGUOUS_TARGET", result["contract_binding"]["reason_codes"])

    def test_single_candidate_can_ground_hazard_but_numeric_contract_stays_unsupported(self):
        result = self.adapt(self.base_event(candidate_count=1))
        self.assertEqual(result["context_graph"]["hazard_fact"]["truth"], "TRUE")
        self.assertEqual(result["target_binding"]["verdict"], "VALIDATED")
        self.assertEqual(result["contract_binding"]["verdict"], "UNSUPPORTED")
        self.assertIn("MISSING_VEHICLE_ASSURANCE_PROFILE", result["contract_binding"]["reason_codes"])

    def test_coc_text_is_hashed_and_remains_claimed(self):
        result = self.adapt()
        self.assertTrue(result["coc_claim"]["present"])
        self.assertFalse(result["coc_claim"]["text_included"])
        self.assertEqual(result["coc_claim"]["epistemic_kind"], "CLAIMED")
        self.assertNotIn("claim content", str(result))

    def test_missing_geometry_is_rejected_without_default(self):
        event = self.base_event()
        event["nearest_candidate"]["longitudinal_gap_m"] = None
        with self.assertRaisesRegex(ValueError, "MISSING_CONFLICT_ZONE_GEOMETRY_INPUT"):
            self.adapt(event)


if __name__ == "__main__":
    unittest.main()
