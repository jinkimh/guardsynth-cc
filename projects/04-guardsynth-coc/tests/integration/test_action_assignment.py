"""Nomination must not silently create independence, acceptance, or gold."""

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
MODULE = ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning/prepare_action_assignment.py"
spec = importlib.util.spec_from_file_location("prepare_action_assignment", MODULE)
assignment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assignment)
SOURCE = ROOT / "artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001/m17-machine-preflight-2026-09-28-002"


class ActionAssignmentTest(unittest.TestCase):
    def test_answer_form_round_trip_and_individual_validator_compatibility(self):
        sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/src"))
        from guard_synth.independent_development_review import validate_independent_review
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "review"
            result = assignment.prepare(SOURCE, output, "Jonh", answer_form=True)
            self.assertTrue(result["answer_form_prepared"])
            self.assertFalse(result["dispatch_authorized"])
            html = (output / "action_review.html").read_text()
            self.assertTrue('<form id="reviewForm">' in html)
            self.assertFalse('여기서는 행동 정답을 작성하지 않습니다' in html)
            packets = json.loads(re.search(r'<script id="packets" type="application/json">(.*?)</script>', html, re.S).group(1))
            scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
            self.assertEqual(len(scripts), 2)
            for packet in packets:
                self.assertEqual(set(packet), assignment.PACKET_KEYS | {"packet_sha256", "images"})
                packet["images"] = ["test-image"] * len(packet["frames"])
            check = subprocess.run(
                ["node", str(Path(__file__).with_name("test_action_review_form.js"))],
                input=json.dumps({"packets": packets, "scripts": scripts}),
                text=True, capture_output=True,
            )
            self.assertEqual(check.returncode, 0, check.stderr)
            exported = json.loads(check.stdout)
            self.assertEqual(exported["bundle_sha256"], result["bundle_sha256"])
            for record, packet in zip(exported["reviews"], packets):
                checked = validate_independent_review(record, packet, packet["packet_sha256"])
                self.assertTrue(checked["review_completed"])
                self.assertFalse(checked["learning_export_allowed"])
            self.assertEqual(result["action_responses"], 0)

    def test_nomination_and_preview_preserve_gates_and_packets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preview"
            result = assignment.prepare(SOURCE, output, "Jonh")
            self.assertEqual(result["reviewer_id"], "Jonh")
            self.assertEqual(len(result["sample_ids"]), 16)
            self.assertIsNone(result["reviewer_self_declaration"])
            self.assertIsNone(result["coordinator_acceptance"])
            self.assertFalse(result["dispatch_authorized"])
            self.assertFalse(result["formal_gate_changed"])
            self.assertEqual(result["formal_required_action_reviewers"], 2)
            self.assertEqual(result["action_responses"], 0)
            html = (output / "action_assignment_preview.html").read_text()
            packets = json.loads(re.search(r'<script id="packets" type="application/json">(.*?)</script>', html, re.S).group(1))
            self.assertEqual(len(packets), 16)
            self.assertFalse("<form" in html)
            for packet in packets:
                self.assertEqual(set(packet), assignment.PACKET_KEYS | {"packet_sha256", "images"})
                self.assertEqual(packet["kind"], "ACTION")
            script = re.findall(r'<script>(.*?)</script>', html, re.S)[0]
            check = subprocess.run(["node", "--check"], input=script, text=True, capture_output=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            with self.assertRaises(FileExistsError):
                assignment.prepare(SOURCE, output, "Jonh")
            manifest = json.loads((output / "RUN_MANIFEST.json").read_text())
            for name, expected in manifest["output_hashes"].items():
                self.assertEqual(assignment.sha((output / name).read_bytes()), expected)

    def test_modified_packet_is_rejected(self):
        records = json.loads((SOURCE / "review_coordination.json").read_text())["records"]
        hashes = json.loads((SOURCE / "RUN_MANIFEST.json").read_text())["output_hashes"]
        hashes[records[0]["action_packet"]] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            assignment.load_action(SOURCE, records[0], hashes)


if __name__ == "__main__":
    unittest.main()
