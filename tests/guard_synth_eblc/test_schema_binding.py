from dataclasses import replace
import unittest

from experiments.eblc_p0b.adapters.pilot_adapter import PILOT_PROFILE, initial_frame
from experiments.eblc_p0b.binders import bind_pedestrian_contract
from experiments.eblc_p0b.catalog import load_pilot_rule, load_predicate_spec, valid_fixture_pairs
from experiments.eblc_p0b.schema_validation import validate_file
from experiments.eblc_p0b.types import EpistemicKind, Fact, Truth, Verdict


class SchemaAndBindingTest(unittest.TestCase):
    def setUp(self):
        self.rule = load_pilot_rule()
        self.predicate = load_predicate_spec()
        self.frame = initial_frame()

    def test_all_schema_fixtures_validate(self):
        pairs = valid_fixture_pairs()
        for fixture, schema in pairs:
            validate_file(fixture, schema)
        self.assertEqual(len(pairs), 4)

    def test_valid_binding_preserves_source_target_derivation_and_priority(self):
        result = bind_pedestrian_contract(self.rule, self.predicate, self.frame, PILOT_PROFILE)
        self.assertEqual(result.verdict, Verdict.VALIDATED)
        self.assertEqual(result.contract.stop_position_x_m, -1.5)
        self.assertEqual(len(result.contract.evidence_refs), 2)
        self.assertEqual(len(result.contract.derivation_dag), 2)
        self.assertNotIn("weight", self.rule.priority.__slots__)

    def test_missing_vehicle_profile_is_unsupported(self):
        result = bind_pedestrian_contract(self.rule, self.predicate, self.frame, None)
        self.assertEqual(result.verdict, Verdict.UNSUPPORTED)
        self.assertIn("MISSING_VEHICLE_PROFILE_FOR_NUMERIC_BINDING", result.reason_codes)

    def test_coc_claim_is_not_promoted_to_observed_fact(self):
        claimed = replace(
            self.frame,
            hazard=Fact(Truth.TRUE, EpistemicKind.CLAIMED, "SYNTHETIC-COC", 0.0, 0.2),
        )
        result = bind_pedestrian_contract(self.rule, self.predicate, claimed, PILOT_PROFILE)
        self.assertEqual(result.verdict, Verdict.REVIEW_REQUIRED)
        self.assertIsNone(result.contract)

    def test_unit_or_coordinate_mismatch_is_unsupported(self):
        wrong_unit = replace(self.frame, distance_unit="cm")
        wrong_frame = replace(self.frame, coordinate_frame="world")
        for bad in (wrong_unit, wrong_frame):
            result = bind_pedestrian_contract(self.rule, self.predicate, bad, PILOT_PROFILE)
            self.assertEqual(result.verdict, Verdict.UNSUPPORTED)
            self.assertIn("UNIT_OR_FRAME_ERROR", result.reason_codes)

    def test_ambiguous_target_requires_review(self):
        result = bind_pedestrian_contract(
            self.rule, self.predicate, self.frame, PILOT_PROFILE,
            target_ambiguity_reason="TWO_EQUAL_TRACK_CANDIDATES",
        )
        self.assertEqual(result.verdict, Verdict.REVIEW_REQUIRED)
        self.assertIn("AMBIGUOUS_TARGET", result.reason_codes)


if __name__ == "__main__":
    unittest.main()

