import unittest

import numpy as np

from experiments.contract_micro_world.micro_world import (
    CONTRACT_DIM,
    COC_DIM,
    STATE_DIM,
    Scenario,
    apply_contract_shield,
    collect_expert_transitions,
    contract_status,
    featurize,
    initial_state,
    rollout_expert,
    rollout_policy,
    sample_scenario,
)


class ContractMicroWorldTest(unittest.TestCase):
    def test_feature_dimensions(self):
        state = initial_state(Scenario("crosswalk", 20.0, 6.0, hazard_clear_time=4.0))
        self.assertEqual(featurize(state, "A_STATE").shape, (STATE_DIM,))
        self.assertEqual(featurize(state, "B_COC").shape, (STATE_DIM + COC_DIM,))
        self.assertEqual(featurize(state, "C_CONTRACT").shape, (STATE_DIM + COC_DIM + CONTRACT_DIM,))

    def test_occlusion_requires_hold(self):
        scenario = Scenario("crosswalk", 20.0, 6.0, hazard_clear_time=0.0, occlusion_start=0.0, occlusion_end=2.0)
        status = contract_status(initial_state(scenario))
        self.assertTrue(status.hold_required)
        self.assertTrue(status.uncertainty_requires_stop)
        self.assertFalse(status.release_allowed)

    def test_shield_reduces_unsafe_acceleration(self):
        state = initial_state(Scenario("crosswalk", 5.0, 7.0, hazard_clear_time=5.0))
        shielded, intervened = apply_contract_shield(state, 1.5)
        self.assertTrue(intervened)
        self.assertLess(shielded, 0.0)

    def test_expert_is_safe_on_sampled_ood_scenarios(self):
        rng = np.random.default_rng(7)
        scenarios = [sample_scenario(kind, rng, "ood") for kind in ("crosswalk", "stop_intersection", "lead_brake") for _ in range(20)]
        for scenario in scenarios:
            metrics = rollout_expert(scenario)
            self.assertFalse(metrics.unsafe, scenario)
            self.assertTrue(metrics.completed, scenario)


if __name__ == "__main__":
    unittest.main()
