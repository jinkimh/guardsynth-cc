import unittest

from experiments.eblc_pilot.pilot import (
    Lifecycle,
    PILOT_PROFILE,
    SceneFrame,
    Truth,
    Verdict,
    run_bcv_mutation_pilot,
    run_trace,
    safe_release_reactivation_trace,
    synthesize_contract,
    unknown_fallback_trace,
    unsafe_entry_trace,
)


class EBLCPilotTest(unittest.TestCase):
    def setUp(self):
        self.initial = SceneFrame(0.0, -12.0, 6.0, 0.0, Truth.TRUE)
        self.synthesis = synthesize_contract(
            "횡단보도 보행자에게 양보한 뒤 진행한다.",
            self.initial,
            PILOT_PROFILE,
        )
        self.assertIsNotNone(self.synthesis.contract)
        self.contract = self.synthesis.contract

    def test_synthesis_binds_source_target_and_numeric_boundary(self):
        self.assertEqual(self.synthesis.verdict, Verdict.VALIDATED)
        self.assertEqual(self.contract.stop_position_x_m, -1.5)
        self.assertEqual(len(self.contract.evidence_refs), 2)
        self.assertIn("pedestrian-track:P17", self.contract.target)
        self.assertGreater(
            self.contract.maximum_safe_speed_mps(self.initial),
            self.initial.ego_speed_mps,
        )

    def test_release_and_reactivation_execute(self):
        result = run_trace(self.contract, safe_release_reactivation_trace())
        states = [step.lifecycle for step in result.steps]
        self.assertTrue(result.accepted)
        self.assertIn(Lifecycle.RELEASED, states)
        self.assertIn(Lifecycle.REACTIVATED, states)
        self.assertEqual(states[-1], Lifecycle.RELEASED)

    def test_unsafe_entry_is_rejected(self):
        result = run_trace(self.contract, unsafe_entry_trace())
        self.assertFalse(result.accepted)
        self.assertIn(
            "CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE", result.violations
        )

    def test_unknown_observation_uses_approved_hold_fallback(self):
        result = run_trace(self.contract, unknown_fallback_trace())
        diagnostics = [item for step in result.steps for item in step.diagnostics]
        self.assertTrue(result.accepted)
        self.assertIn("UNKNOWN_HOLD_FALLBACK", diagnostics)

    def test_missing_profile_abstains(self):
        result = synthesize_contract("보행자에게 양보한다.", self.initial, None)
        self.assertEqual(result.verdict, Verdict.UNSUPPORTED)
        self.assertIsNone(result.contract)

    def test_coc_claim_is_not_promoted_to_observation(self):
        result = synthesize_contract(
            "보행자에게 양보한다.",
            SceneFrame(0.0, -12.0, 6.0, 0.0, Truth.UNKNOWN),
            PILOT_PROFILE,
        )
        self.assertEqual(result.verdict, Verdict.REVIEW_REQUIRED)
        self.assertIsNone(result.contract)

    def test_bcv_finds_under_and_overconstraint_mutations(self):
        result = run_bcv_mutation_pilot(self.contract)
        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()

