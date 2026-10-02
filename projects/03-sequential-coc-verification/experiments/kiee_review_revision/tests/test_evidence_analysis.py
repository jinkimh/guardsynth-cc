import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "analyze_existing_evidence.py"

class EvidenceAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), "Reanalysis implementation is not present yet")
        spec = importlib.util.spec_from_file_location("evidence_analysis", MODULE)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)

    def test_perfect_agreement_non_degenerate(self):
        result = self.api.agreement([["A", "A"], ["B", "B"]])
        self.assertEqual(result["raw_agreement"], 1)
        self.assertEqual(result["kappa"], 1)

    def test_identical_single_category_kappa_undefined(self):
        self.assertIsNone(self.api.agreement([["A", "A"], ["A", "A"]])["kappa"])

    def test_disagreement_is_not_consensus(self):
        result = self.api.agreement([["A", "B"], ["A", "B"]])
        self.assertEqual(result["raw_agreement"], 0)
        self.assertEqual(result["kappa"], -1)

    def test_incomplete_panel_rejected(self):
        with self.assertRaises(ValueError):
            self.api.agreement([["A", "B"], ["A"]])

    def test_never_detected_is_not_threshold_sensitive(self):
        result = self.api.sensitivity_counts([{"detected_profile_count": n, "profile_count": 27} for n in [0, 1, 26, 27]])
        self.assertEqual(result, {"total": 4, "always_detected": 1, "setting_sensitive": 2, "never_detected": 1})

    def test_invalid_detection_count_rejected(self):
        with self.assertRaises(ValueError):
            self.api.sensitivity_counts([{"detected_profile_count": 28, "profile_count": 27}])

    def test_duplicate_review_ids_rejected(self):
        with self.assertRaises(ValueError):
            self.api.index_reviews([{"review_id": "one"}, {"review_id": "one"}])

    def test_unequal_panel_ids_rejected(self):
        with self.assertRaises(ValueError):
            self.api.align_panel({"A": [{"review_id": "one"}], "B": [{"review_id": "two"}]})

if __name__ == "__main__":
    unittest.main()
