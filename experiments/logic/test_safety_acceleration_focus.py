import unittest

import numpy as np

from collect_safety_acceleration_focus import classify


class SafetyAccelerationFocusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.time = np.arange(1, 65, dtype=float) * 0.1

    def test_stop_not_reached_then_accelerates(self) -> None:
        speed = np.r_[np.linspace(1.0, 0.5, 20), np.linspace(0.5, 4.0, 44)]
        category, claim, _ = classify({"STOP"}, 1.0, speed, self.time)
        self.assertIn("STOP_NOT_REACHED", category)
        self.assertEqual(claim, "PLAN_LEVEL_MISMATCH_CANDIDATE")

    def test_stop_then_acceleration_requires_release(self) -> None:
        speed = np.r_[np.linspace(1.0, 0.05, 20), np.linspace(0.05, 4.0, 44)]
        category, claim, _ = classify({"STOP"}, 1.0, speed, self.time)
        self.assertIn("STOP_THEN_FORWARD_ACCELERATION", category)
        self.assertEqual(claim, "RELEASE_UNRESOLVED")

    def test_yield_deceleration_then_acceleration_requires_release(self) -> None:
        speed = np.r_[np.linspace(4.0, 2.0, 32), np.linspace(2.0, 4.0, 32)]
        category, claim, _ = classify({"YIELD"}, 4.0, speed, self.time)
        self.assertIn("YIELD_DECELERATE_THEN_ACCELERATE", category)
        self.assertEqual(claim, "RELEASE_UNRESOLVED")

    def test_near_stop_then_reverse_is_collected(self) -> None:
        speed = np.r_[np.linspace(0.2, 0.0, 20), np.linspace(-0.01, -0.2, 44)]
        category, claim, _ = classify({"YIELD"}, 0.2, speed, self.time)
        self.assertEqual(category, "NEAR_STOP_THEN_REVERSE")
        self.assertEqual(claim, "UNEXPLAINED_REVERSE_CANDIDATE")


if __name__ == "__main__":
    unittest.main()
