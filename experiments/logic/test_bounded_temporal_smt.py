#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from run_bounded_temporal_smt import (  # noqa: E402
    action_trajectory_checks,
    collision_witness,
    propositional_consistency,
    stable_action_contradiction,
    sustained_stop_smt,
    trajectory_features,
)


class BoundedTemporalSmtTests(unittest.TestCase):
    def test_propositional_action_conflict_has_unsat_core(self) -> None:
        result = propositional_consistency({"STOP", "ACCELERATE"})
        self.assertEqual(result["verdict"], "UNSAT")
        self.assertIn("exclusive_stop_accelerate", result["unsat_core"])

    def test_action_contradiction_uses_full_threshold_sensitivity(self) -> None:
        points = np.zeros((64, 3), dtype=float)
        points[:, 0] = np.arange(1, 65) * 0.5
        features = trajectory_features(points)
        checks = action_trajectory_checks({"DECELERATE"}, features)
        self.assertTrue(stable_action_contradiction(checks))

    def test_collision_witness_respects_lateral_separation(self) -> None:
        obstacle = pd.Series(
            {
                "center_x": 10.0,
                "center_y": 0.0,
                "half_extent_x": 2.0,
                "half_extent_y": 1.0,
            }
        )
        points = np.zeros((64, 3), dtype=float)
        points[:, 0] = np.arange(1, 65) * 0.5
        witness = collision_witness(points, obstacle, 0.0, 3.0, 1.0, 1.0, 0.0)
        self.assertIsNotNone(witness)
        points[:, 1] = 4.0
        no_witness = collision_witness(
            points, obstacle, 0.0, 3.0, 1.0, 1.0, 0.0
        )
        self.assertIsNone(no_witness)

    def test_sustained_stop_is_threshold_sensitive(self) -> None:
        speeds = np.asarray([2.0] * 5 + [0.35] * 6 + [2.0] * 5)
        low = sustained_stop_smt(speeds, 0.3, 0.5)
        high = sustained_stop_smt(speeds, 0.4, 0.5)
        self.assertEqual(low["verdict"], "UNSAT")
        self.assertEqual(high["verdict"], "SAT")


if __name__ == "__main__":
    unittest.main()
