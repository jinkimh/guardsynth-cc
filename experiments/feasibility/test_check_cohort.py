import unittest
from pathlib import Path

import pandas as pd

from check_cohort import (
    DEFAULT_SCENES,
    analyze_cohort,
    detect_directional_response,
    expected_longitudinal_direction,
    extract_intents,
    scenes_for_chunk,
)


class CohortCheckerTest(unittest.TestCase):
    def test_extracts_ordered_compound_intents(self) -> None:
        intents = extract_intents("Stop behind the vehicle, then accelerate through the gate.")
        self.assertEqual(intents, ["STOP", "ACCELERATE"])
        self.assertIsNone(expected_longitudinal_direction(intents))

    def test_detects_directional_response(self) -> None:
        frame = pd.DataFrame(
            {
                "timestamp": [0, 250_000, 500_000],
                "speed_mps": [3.0, 2.9, 2.7],
            }
        )
        self.assertEqual(detect_directional_response(frame, 0, 500_000, "DECREASE"), 0)
        self.assertIsNone(detect_directional_response(frame, 0, 500_000, "INCREASE"))

    def test_default_cohort_has_complete_source_files(self) -> None:
        result = analyze_cohort()
        self.assertEqual(result["cohort"]["scene_count"], len(DEFAULT_SCENES))
        self.assertTrue(
            all(
                episode["timestamps_strictly_increasing"]
                for episode in result["episodes"]
            )
        )
        self.assertEqual(result["scene_concatenation_claim"], "FORBIDDEN")

    def test_chunk_zero_selects_all_labeled_scenes(self) -> None:
        self.assertEqual(
            len(scenes_for_chunk(Path("data/baseline/coc_nusc"), 0)), 94
        )

    def test_already_stopped_events_do_not_require_new_deceleration(self) -> None:
        result = analyze_cohort(scenes=("scene-0046",))
        event = next(
            event
            for event in result["episodes"][0]["events"]
            if event["event_id"] == "scene-0046@10000000"
        )
        self.assertEqual(
            event["weak_kinematic_contract"], "PASS_ALREADY_SATISFIED"
        )


if __name__ == "__main__":
    unittest.main()
