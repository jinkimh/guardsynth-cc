#!/usr/bin/env python3
"""Tests for critical-delay interval extraction and paired classification."""

from __future__ import annotations

import unittest

import numpy as np

from run_confirmed_critical_delay_analysis import classify_scene, overlap_intervals


class CriticalDelayTest(unittest.TestCase):
    def test_multiple_nonmonotonic_intervals(self) -> None:
        delays = np.arange(0, 0.7, 0.1)
        overlap = np.array([False, True, True, False, False, True, False])
        self.assertEqual(overlap_intervals(delays, overlap), [[0.1, 0.2], [0.5, 0.5]])

    def test_model_earlier_than_human_is_excess_fragility(self) -> None:
        records = [
            {"plan": "human_recorded", "margin_m": 0.25, "critical_delay_to_overlap_s": 1.0},
            {"plan": "model_seed_42", "margin_m": 0.25, "critical_delay_to_overlap_s": 0.7},
        ]
        result = classify_scene(records)
        self.assertEqual(result[0]["classification"], "MODEL_EXCESS_FRAGILITY")
        self.assertEqual(result[0]["critical_delay_difference_model_minus_human_s"], -0.3)

    def test_neither_overlap_is_no_overlap(self) -> None:
        records = [
            {"plan": "human_recorded", "margin_m": 0.25, "critical_delay_to_overlap_s": None},
            {"plan": "model_seed_42", "margin_m": 0.25, "critical_delay_to_overlap_s": None},
        ]
        self.assertEqual(
            classify_scene(records)[0]["classification"],
            "NO_OVERLAP_WITHIN_CONFIRMED_RANGE",
        )


if __name__ == "__main__":
    unittest.main()
