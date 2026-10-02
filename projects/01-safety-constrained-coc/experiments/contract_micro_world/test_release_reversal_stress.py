import unittest
from dataclasses import replace

from experiments.contract_micro_world.micro_world import (
    EpisodeMetrics,
    Scenario,
    hazard_active,
    initial_state,
    is_visible,
    step,
)
from experiments.contract_micro_world.run_release_reversal_stress import (
    _future_risk_state,
    build_stress_bank,
    independent_stress_oracle,
)


class ReleaseReversalStressTest(unittest.TestCase):
    def test_hazard_and_occlusion_schedules(self):
        scenario = Scenario(
            "crosswalk",
            10.0,
            5.0,
            hazard_intervals=((0.0, 1.0), (2.0, 3.0)),
            occlusion_intervals=((1.5, 2.5),),
        )
        state = initial_state(scenario)
        self.assertTrue(hazard_active(state))
        self.assertTrue(is_visible(state))
        self.assertFalse(hazard_active(replace(state, t=1.2)))
        self.assertFalse(is_visible(replace(state, t=2.0)))
        self.assertTrue(hazard_active(replace(state, t=2.2)))

    def test_oracle_flags_crossing_during_reentry(self):
        scenario = Scenario("crosswalk", 1.0, 5.0, hazard_intervals=((0.0, 5.0),))
        before = replace(initial_state(scenario), ego_x=-0.1, ego_v=1.0)
        after = step(before, 0.0)
        metrics = EpisodeMetrics()
        independent_stress_oracle(before, after, metrics)
        self.assertTrue(metrics.forbidden_entry)
        self.assertTrue(metrics.collision)

    def test_oracle_lookahead_detects_future_reentry(self):
        scenario = Scenario("crosswalk", 10.0, 5.0, hazard_intervals=((1.0, 2.0),))
        state = initial_state(scenario)
        self.assertEqual(_future_risk_state(state, 0.8).t, 0.0)
        self.assertAlmostEqual(_future_risk_state(state, 1.2).t, 1.0)

    def test_small_bank_is_reference_feasible(self):
        cases, attempts = build_stress_bank(2, 11)
        self.assertEqual(len(cases), 8)
        self.assertTrue(all(value >= 2 for value in attempts.values()))


if __name__ == "__main__":
    unittest.main()
