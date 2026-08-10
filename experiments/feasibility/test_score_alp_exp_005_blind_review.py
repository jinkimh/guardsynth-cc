import unittest

from score_alp_exp_005_blind_review import cohen_kappa, exact_agreement


class BlindReviewScoringTest(unittest.TestCase):
    def test_exact_agreement(self) -> None:
        self.assertAlmostEqual(exact_agreement(["A", "B", "C"], ["A", "B", "A"]), 2 / 3)

    def test_perfect_kappa(self) -> None:
        self.assertEqual(cohen_kappa(["A", "B", "A"], ["A", "B", "A"]), 1.0)

    def test_kappa_undefined_for_one_constant_class(self) -> None:
        self.assertIsNone(cohen_kappa(["A", "A"], ["A", "A"]))


if __name__ == "__main__":
    unittest.main()
