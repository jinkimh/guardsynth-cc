import math
import unittest

import numpy as np
import pandas as pd

from analyze_nvidia_obstacle_feasibility import add_oriented_extents, corridor_snapshot
from analyze_nvidia_official_cohort import is_compound
from analyze_nvidia_official_episode import detect_response, event_contract


class OfficialNvidiaAnalysisTests(unittest.TestCase):
    def test_normalizes_extended_longitudinal_phrases(self):
        self.assertEqual(event_contract("Strong deceleration for a cut-in")[3], "DECREASE_SPEED")
        self.assertEqual(event_contract("Gentle acceleration after yielding")[3], "INCREASE_SPEED")

    def test_flags_compound_longitudinal_command(self):
        self.assertTrue(is_compound("Decelerate for the worker, then slowly accelerate."))
        self.assertFalse(is_compound("Decelerate for the lead vehicle."))

    def test_detects_sustained_candidate_response(self):
        timestamps = np.arange(0, 1_500_000, 10_000)
        frame = pd.DataFrame(
            {"timestamp": timestamps, "speed_mps": 10.0 - timestamps / 1_000_000}
        )
        result = detect_response(frame, 200_000, "speed_mps", -1, 0.1)
        self.assertEqual(result["verdict"], "PASS_CANDIDATE_CONFORMANCE")
        self.assertLessEqual(result["response_latency_s"], 0.01)

    def test_oriented_box_corridor_gap(self):
        frame = pd.DataFrame(
            {
                "timestamp_us": [1_000_000],
                "track_id": ["target"],
                "center_x": [10.0],
                "center_y": [0.5],
                "size_x": [4.0],
                "size_y": [2.0],
                "orientation_x": [0.0],
                "orientation_y": [0.0],
                "orientation_z": [0.0],
                "orientation_w": [1.0],
            }
        )
        snapshot = corridor_snapshot(
            add_oriented_extents(frame), 1_000_000, ego_front_extent=4.0, ego_half_width=1.0
        )
        self.assertEqual(len(snapshot), 1)
        self.assertTrue(math.isclose(snapshot.iloc[0]["longitudinal_gap_m"], 4.0))


if __name__ == "__main__":
    unittest.main()
