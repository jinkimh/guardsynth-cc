import unittest

import pandas as pd

from check_episode import (
    analyze_deceleration_sensitivity,
    detect_sustained_deceleration,
    normalize_coc,
    parse_deadlines,
    select_obligation_anchor,
)


class EpisodeCheckerTest(unittest.TestCase):
    def test_normalizes_two_axis_decision_and_hazards(self) -> None:
        decision = normalize_coc(
            "Nudge left to create clearance from the stopped truck and construction "
            "zone on the right while adapting speed to maintain a safe distance."
        )
        self.assertEqual(decision.longitudinal, "ADAPT_SPEED")
        self.assertEqual(decision.lateral, "NUDGE_LEFT")
        self.assertEqual(decision.hazards, ("TRUCK", "CONSTRUCTION_ZONE"))

    def test_detects_sustained_deceleration_onset(self) -> None:
        trace = pd.DataFrame(
            {
                "timestamp": [0, 250_000, 500_000, 750_000, 1_000_000],
                "speed_mps": [5.0, 5.1, 5.0, 4.8, 4.6],
            }
        )
        onset = detect_sustained_deceleration(trace, 0, 1_000_000, 500_000, 0.1, 0.5)
        self.assertEqual(onset, 250_000)

    def test_deadlines_are_sorted_and_unique(self) -> None:
        self.assertEqual(parse_deadlines("3,1,2,2"), [1.0, 2.0, 3.0])

    def test_normalizes_acceleration_for_transition_checks(self) -> None:
        decision = normalize_coc("Accelerate through the clear intersection.")
        self.assertEqual(decision.longitudinal, "ACCELERATE")

    def test_repeated_trigger_does_not_change_obligation_anchor(self) -> None:
        self.assertEqual(select_obligation_anchor([4_800_000, 2_500_000, 3_500_000]), 2_500_000)

    def test_reports_threshold_profiles_without_detected_response(self) -> None:
        trace = pd.DataFrame(
            {"timestamp": [0, 500_000, 1_000_000], "speed_mps": [5.0, 5.0, 5.0]}
        )
        result = analyze_deceleration_sensitivity(
            trace, 0, 1_000_000, [0.5], [0.1], [0.7]
        )
        self.assertEqual(result["profile_count"], 1)
        self.assertEqual(result["no_response_profile_count"], 1)


if __name__ == "__main__":
    unittest.main()
