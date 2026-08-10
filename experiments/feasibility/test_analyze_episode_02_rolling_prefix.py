#!/usr/bin/env python3
"""Unit tests for episode-02 rolling-prefix analysis helpers."""

from __future__ import annotations

import types
import unittest

import numpy as np
from scipy.spatial.transform import RigidTransform

from analyze_episode_02_rolling_prefix import actor_phase, classify_coc, speed_metrics


class RollingPrefixAnalysisTest(unittest.TestCase):
    def actor(self, y: float) -> object:
        return types.SimpleNamespace(
            center=np.array([[10.0, y]]),
            width=np.array([0.6]),
        )

    def test_entry_side_aware_phase_order(self) -> None:
        pose = RigidTransform.identity()
        dimensions = types.SimpleNamespace(width=2.0)
        self.assertEqual(actor_phase(self.actor(-2.0), pose, dimensions, -1.0)[0], "APPROACHING_EGO_CORRIDOR")
        self.assertEqual(actor_phase(self.actor(0.0), pose, dimensions, -1.0)[0], "OCCUPYING_EGO_CORRIDOR")
        self.assertEqual(actor_phase(self.actor(2.0), pose, dimensions, -1.0)[0], "CLEARED_EGO_CORRIDOR")

    def test_coc_semantic_classes(self) -> None:
        self.assertEqual(classify_coc("Yield to the pedestrian"), "HOLD_OR_YIELD")
        self.assertEqual(classify_coc("Resume speed after clearance"), "RELEASE_OR_PROCEED")
        self.assertEqual(classify_coc("Maintain lane"), "UNSPECIFIED")

    def test_speed_metrics_use_origin_to_first_waypoint(self) -> None:
        local_xy = np.array([[0.1, 0.0], [0.2, 0.0], [0.3, 0.0], [0.4, 0.0], [0.5, 0.0]])
        result = speed_metrics(local_xy, current_speed=1.0)
        self.assertAlmostEqual(result["mean_executable_speed_mps"], 1.0)
        self.assertAlmostEqual(result["end_minus_current_speed_mps"], 0.0)


if __name__ == "__main__":
    unittest.main()
