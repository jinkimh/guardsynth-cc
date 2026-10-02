import unittest

import numpy as np

from analyze_alp_exp_005_feasibility_batch import (
    action_matches,
    parse_actions,
    parse_entities,
    trajectory_features,
)


class FeasibilityBatchAnalysisTest(unittest.TestCase):
    def test_parses_compound_action_and_entities(self) -> None:
        text = "Decelerate and nudge to the left to avoid the pedestrian."
        self.assertEqual(parse_actions(text), {"DECELERATE", "LEFT"})
        self.assertEqual(parse_entities(text), {"PEDESTRIAN"})

    def test_slow_object_is_not_ego_deceleration(self) -> None:
        text = "Maintain lane behind the slow lead truck."
        self.assertEqual(parse_actions(text), {"KEEP_LANE"})

    def test_left_and_deceleration_match(self) -> None:
        x = np.linspace(0.8, 40.0, 64)
        y = np.linspace(0.0, 1.2, 64)
        points = np.column_stack((x, y, np.zeros(64)))
        points[-10:, 0] = np.linspace(points[-11, 0] + 0.4, points[-11, 0] + 2.0, 10)
        features = trajectory_features(points)
        self.assertTrue(action_matches({"DECELERATE", "LEFT"}, features, strict_lateral=True))

    def test_entity_position_does_not_become_lateral_action(self) -> None:
        text = "Decelerate for the vehicle on the right."
        self.assertEqual(parse_actions(text), {"DECELERATE"})

    def test_already_stopped_yield_is_temporally_unevaluable(self) -> None:
        x = np.linspace(0.01, 20.0, 64)
        y = np.zeros(64)
        points = np.column_stack((x, y, np.zeros(64)))
        points[:5, 0] = np.linspace(0.001, 0.02, 5)
        features = trajectory_features(points)
        self.assertIsNone(action_matches({"STOP", "YIELD"}, features, strict_lateral=False))


if __name__ == "__main__":
    unittest.main()
