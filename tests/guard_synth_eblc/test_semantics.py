import unittest

from experiments.eblc_p0b.adapters.pilot_adapter import PILOT_PROFILE, frame, initial_frame, safe_release_reactivation_trace
from experiments.eblc_p0b.binders import bind_pedestrian_contract
from experiments.eblc_p0b.catalog import load_pilot_rule, load_predicate_spec
from experiments.eblc_p0b.semantics import run_canonical
from experiments.eblc_p0b.types import EpistemicKind, Lifecycle, Truth, Verdict


class CanonicalSemanticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        outcome = bind_pedestrian_contract(load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE)
        cls.contract = outcome.contract

    def test_hazard_true_activates_and_one_false_does_not_release(self):
        result = run_canonical(self.contract, (frame(0.0, Truth.TRUE), frame(0.1, Truth.FALSE)))
        self.assertEqual(result.steps[0].lifecycle, Lifecycle.ACTIVE)
        self.assertEqual(result.steps[1].lifecycle, Lifecycle.MAINTAINED)

    def test_consecutive_clear_releases_then_hazard_reactivates(self):
        result = run_canonical(self.contract, safe_release_reactivation_trace())
        states = [step.lifecycle for step in result.steps]
        self.assertIn(Lifecycle.RELEASED, states)
        self.assertIn(Lifecycle.REACTIVATED, states)
        self.assertTrue(result.accepted)

    def test_active_unknown_uses_only_approved_hold_fallback(self):
        result = run_canonical(self.contract, (frame(0.0, Truth.TRUE), frame(0.1, Truth.UNKNOWN)))
        self.assertEqual(result.steps[-1].lifecycle, Lifecycle.MAINTAINED)
        self.assertIn("APPROVED_UNKNOWN_HOLD_FALLBACK", result.diagnostics)

    def test_conflicting_evidence_returns_conflict(self):
        result = run_canonical(self.contract, (frame(0.0, Truth.CONFLICT),))
        self.assertEqual(result.verdict, Verdict.CONFLICT)
        self.assertFalse(result.accepted)

    def test_active_conflict_zone_entry_is_violation(self):
        result = run_canonical(self.contract, (frame(0.0, Truth.TRUE, x=-1.49, speed=0.0),))
        self.assertIn("CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE", result.violations)

    def test_dynamic_stopping_speed_bound_is_violation(self):
        result = run_canonical(self.contract, (frame(0.0, Truth.TRUE, x=-12.0, speed=20.0),))
        self.assertIn("DYNAMIC_STOPPING_SPEED_BOUND_EXCEEDED", result.violations)

    def test_stale_timestamp_fails_to_unknown(self):
        result = run_canonical(self.contract, (frame(0.5, Truth.TRUE, fact_timestamp_s=0.0),))
        self.assertEqual(result.steps[0].lifecycle, Lifecycle.CANDIDATE)
        self.assertEqual(result.verdict, Verdict.REVIEW_REQUIRED)
        self.assertIn("STALE_PREDICATE_FAILURE_TO_UNKNOWN", result.diagnostics)

    def test_safe_progress_is_allowed_without_hazard(self):
        result = run_canonical(self.contract, (frame(0.0, Truth.FALSE, x=1.0, speed=2.0, safe_progress=True),))
        self.assertTrue(result.accepted)
        self.assertTrue(result.steps[0].progress_allowed)

    def test_boundary_equality_and_adjacent_values(self):
        equality = run_canonical(self.contract, (frame(0.0, Truth.TRUE, x=-1.5, speed=0.0),))
        before = run_canonical(self.contract, (frame(0.0, Truth.TRUE, x=-1.500001, speed=0.0),))
        after = run_canonical(self.contract, (frame(0.0, Truth.TRUE, x=-1.499999, speed=0.0),))
        self.assertTrue(equality.accepted)
        self.assertTrue(before.accepted)
        self.assertFalse(after.accepted)

    def test_claimed_runtime_fact_remains_review_only(self):
        result = run_canonical(self.contract, (frame(0.0, Truth.TRUE, epistemic=EpistemicKind.CLAIMED),))
        self.assertEqual(result.steps[0].lifecycle, Lifecycle.CANDIDATE)
        self.assertEqual(result.verdict, Verdict.REVIEW_REQUIRED)

    def test_expiry_is_distinct_from_release(self):
        result = run_canonical(self.contract, (frame(0.0, Truth.TRUE, scope_valid=False),))
        self.assertEqual(result.steps[0].lifecycle, Lifecycle.EXPIRED)


if __name__ == "__main__":
    unittest.main()

