import unittest
from unittest.mock import patch

from serve_alp_exp_005_blind_review import main, validate_label


class BlindReviewServerTest(unittest.TestCase):
    def test_accepts_partial_autosave(self) -> None:
        label = validate_label({"consistency": "INCONSISTENT", "notes": "check"})
        self.assertEqual(label["consistency"], "INCONSISTENT")
        self.assertEqual(label["stated_lateral"], "")

    def test_rejects_unknown_label(self) -> None:
        with self.assertRaises(ValueError):
            validate_label({"consistency": "MAYBE"})

    def test_rejects_long_notes(self) -> None:
        with self.assertRaises(ValueError):
            validate_label({"notes": "x" * 501})

    def test_refuses_public_basic_auth_without_tls(self) -> None:
        arguments = [
            "server",
            "--reviewer", "A",
            "--host", "0.0.0.0",
            "--allow-non-loopback",
        ]
        with patch("sys.argv", arguments), self.assertRaisesRegex(SystemExit, "without HTTPS"):
            main()


if __name__ == "__main__":
    unittest.main()
