#!/usr/bin/env python3

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from analyze_phase_aware_alignment import classify_action  # noqa: E402


class PhaseAwareAlignmentTests(unittest.TestCase):
    def test_decelerate_then_accelerate_is_supported_response(self) -> None:
        speeds = np.concatenate(
            [np.linspace(10.0, 7.0, 25), np.linspace(7.0, 12.0, 39)]
        )
        points = np.zeros((64, 3))
        result = classify_action("DECELERATE", "slow down", points, speeds, 10.0)
        self.assertEqual(result["verdict"], "SUPPORTED_RESPONSE_PHASE")

    def test_stop_without_near_zero_speed_is_contradicted(self) -> None:
        speeds = np.linspace(5.0, 7.0, 64)
        points = np.zeros((64, 3))
        result = classify_action("STOP", "stop", points, speeds, 5.0)
        self.assertEqual(result["verdict"], "CONTRADICTED_WITHIN_HORIZON")

    def test_small_nudge_is_threshold_sensitive_not_contradicted(self) -> None:
        speeds = np.ones(64)
        points = np.zeros((64, 3))
        points[:, 1] = np.concatenate(
            [np.linspace(0.0, 0.23, 32), np.linspace(0.23, -0.4, 32)]
        )
        result = classify_action("LEFT", "nudge left", points, speeds, 1.0)
        self.assertEqual(result["verdict"], "THRESHOLD_SENSITIVE_SMALL_MANEUVER")

    def test_yield_with_deceleration_keeps_release_unresolved(self) -> None:
        speeds = np.concatenate([np.linspace(8.0, 5.0, 30), np.linspace(5.0, 9.0, 34)])
        points = np.zeros((64, 3))
        result = classify_action("YIELD", "yield", points, speeds, 8.0)
        self.assertEqual(
            result["verdict"], "KINEMATIC_RESPONSE_PRESENT_RELEASE_UNRESOLVED"
        )


if __name__ == "__main__":
    unittest.main()
