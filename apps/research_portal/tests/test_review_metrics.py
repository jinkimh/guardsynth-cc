import unittest

from apps.research_portal.review_metrics import (
    categorical_agreement,
    correction_rates,
    interval_agreement,
    m16_start_gate,
    nominal_krippendorff_alpha,
    reviewer_time_summary,
    round_progress,
    source_set_agreement,
)


class ReviewMetricsTest(unittest.TestCase):
    def test_nominal_alpha_matches_known_two_reviewer_fixture(self):
        result = nominal_krippendorff_alpha(
            {"s1": ["A", "A"], "s2": ["A", "B"], "s3": ["B", "B"]}
        )

        self.assertEqual(result["status"], "ESTIMATED")
        self.assertAlmostEqual(result["alpha"], 4 / 9)
        self.assertEqual(result["included_items"], 3)

    def test_zero_category_variance_is_not_reported_as_perfect_agreement(self):
        result = nominal_krippendorff_alpha({"s1": ["A", "A"], "s2": ["A", None]})

        self.assertEqual(result["status"], "NOT_ESTIMABLE_NO_CATEGORY_VARIANCE")
        self.assertIsNone(result["alpha"])
        self.assertEqual(result["excluded_items"], 1)

    def test_current_m16_counts_fail_both_start_gates(self):
        gate = m16_start_gate(
            distinct_eligible=1,
            slice_counts={"s1": 1, "s2": 0, "s3": 0},
            outcome_counts={"o1": 1},
            joint_cells_ready=False,
            source_complete=1,
            schema_ui_export_validated=True,
            assignments_valid=False,
            calibration_complete=False,
            reviewer_training_complete=False,
            baseline_model_split_manifest_frozen=False,
            guideline_revision_count=0,
        )

        self.assertFalse(gate["calibration_start_allowed"])
        self.assertFalse(gate["empirical_annotation_start_allowed"])
        self.assertEqual(gate["eligible_shortfall"], 59)

    def test_field_interval_source_correction_and_time_contracts(self):
        categorical = categorical_agreement({"s1": ["A", "A"], "s2": ["A", "B"], "s3": ["B", None]})
        self.assertEqual(categorical["exact_fraction"], 0.5)
        self.assertEqual(categorical["excluded_items"], 1)
        self.assertEqual(categorical["confusion_matrix"]["A"]["B"], 1)

        intervals = interval_agreement([
            ({"low": 0, "high": 10, "unit": "m", "frame": "map"}, {"low": 5, "high": 15, "unit": "m", "frame": "map"}),
            ({"low": 0, "high": 1, "unit": "m", "frame": "map"}, {"low": 0, "high": 1, "unit": "s", "frame": "map"}),
        ])
        self.assertAlmostEqual(intervals["mean_iou"], 1 / 3)
        self.assertEqual(intervals["unit_or_frame_mismatch"], 1)

        sources = source_set_agreement([({"s1", "s2"}, {"s2", "s3"}), ({"s1"}, {"s1"})])
        self.assertEqual(sources["exact_fraction"], 0.5)
        self.assertAlmostEqual(sources["mean_jaccard"], 2 / 3)

        corrections = correction_rates([
            ({"a": 1, "b": 2}, {"a": 1, "b": 3}),
            ({"a": 1}, {"a": 1}),
        ])
        self.assertEqual(corrections["scene_correction_rate"], 0.5)
        self.assertEqual(corrections["field_correction_rate"], 1 / 3)

        timing = reviewer_time_summary([
            {"active_seconds": 10, "calibration": False},
            {"active_seconds": 20, "calibration": False},
            {"active_seconds": 900, "calibration": False},
            {"active_seconds": 30, "calibration": True},
        ], idle_timeout_seconds=600)
        self.assertEqual(timing["empirical"]["median"], 15)
        self.assertEqual(timing["empirical"]["idle_excluded"], 1)
        self.assertEqual(timing["calibration"]["median"], 30)

    def test_round_progress_keeps_three_denominators_separate(self):
        result = round_progress(
            assigned=10, finalized=6, total_samples=5, samples_with_required_reviews=2,
            disagreement_samples_ready=2, adjudicated_disagreements=1,
        )
        self.assertEqual(result["reviewer_progress"]["fraction"], 0.6)
        self.assertEqual(result["independent_scene_progress"]["fraction"], 0.4)
        self.assertEqual(result["adjudication_progress"]["fraction"], 0.5)
        self.assertNotIn("average", result)


if __name__ == "__main__":
    unittest.main()
