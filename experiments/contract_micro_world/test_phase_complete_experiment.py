import unittest
from dataclasses import replace

import numpy as np

from experiments.contract_micro_world.micro_world import (
    EpisodeMetrics,
    Scenario,
    initial_state,
    step,
)
from experiments.contract_micro_world.run_phase_complete_experiment import (
    PHASE_DIM,
    independent_evaluate_transition,
    phase_coverage,
    scenario_bank,
    stop_phase,
)
from experiments.contract_micro_world.micro_world import collect_expert_transitions


class PhaseCompleteExperimentTest(unittest.TestCase):
    def test_training_bank_contains_post_stop_hold(self):
        transitions = collect_expert_transitions(scenario_bank(20, "train", 9))
        coverage = phase_coverage(transitions)
        self.assertGreater(coverage["HOLD"], 0)
        self.assertGreater(coverage["RELEASED"], 0)

    def test_stop_phase_separates_dwell_hold_release(self):
        scenario = Scenario("stop_intersection", 10.0, 5.0, hazard_clear_time=5.0)
        state = initial_state(scenario)
        self.assertEqual(stop_phase(state), "APPROACH")
        self.assertEqual(stop_phase(replace(state, stopped_steps=1, ego_v=0.1)), "STOP_DWELL")
        self.assertEqual(stop_phase(replace(state, stopped_steps=2, has_stopped=True, ego_v=0.0)), "HOLD")
        self.assertEqual(
            stop_phase(replace(state, t=6.0, stopped_steps=2, has_stopped=True, ego_v=0.0)),
            "RELEASED",
        )
        self.assertEqual(PHASE_DIM, 5)

    def test_preline_position_is_not_collision(self):
        scenario = Scenario("stop_intersection", 1.0, 1.0, hazard_clear_time=5.0)
        before = replace(initial_state(scenario), ego_x=-0.4, ego_v=0.1, has_stopped=True, stopped_steps=2)
        after = step(before, 0.0)
        metrics = EpisodeMetrics()
        independent_evaluate_transition(before, after, metrics)
        self.assertFalse(metrics.collision)
        self.assertFalse(metrics.forbidden_entry)


if __name__ == "__main__":
    unittest.main()

