"""Review linkage must not silently change scene identity or promote training eligibility."""

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").exists())
sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning"))
import link_scene_reviews as entry


class ReviewLinkageTest(unittest.TestCase):
    def test_real_reviews_link_but_remain_development_only(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "linkage-001"
            result = entry.run(output)
            self.assertTrue(result["korean_all_supported"])
            self.assertTrue(result["action_matches_conditioned_instruction"])
            self.assertTrue(result["declared_action_before_cnl"])
            self.assertEqual(result["matches_expected"], 12)
            self.assertEqual(result["event_predicates"]["road"], {"truth": "UNKNOWN", "evidence_valid": False})
            self.assertFalse(result["english_fidelity_review_complete"])
            self.assertFalse(result["learning_export_allowed"])
            self.assertFalse(result["main_test_eligibility"])
            entry.r.revalidate_run(output)
            with self.assertRaises(FileExistsError):
                entry.run(output)

    def test_mismatched_scene_rejected(self):
        packet = entry.r.load(entry.UI / "scene18_scene_cnl_review_packet.json")
        for field, value in (("event_timestamp_us", 0), ("zone_polygon", []), ("frames", [])):
            other = deepcopy(packet)
            other[field] = value
            with self.assertRaisesRegex(ValueError, "review scene mismatch"):
                entry.compare_packets(packet, other)

    def test_future_frame_rejected_even_when_packets_match(self):
        packet = entry.r.load(entry.UI / "scene18_scene_cnl_review_packet.json")
        packet["frames"][0]["timestamp_us"] = packet["event_timestamp_us"] + 1
        with self.assertRaisesRegex(ValueError, "future review frame"):
            entry.compare_packets(packet, packet)


if __name__ == "__main__":
    unittest.main()
