"""Pinned real inputs, past-only frames, source packet and UI interaction regression."""

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT=next(p for p in Path(__file__).resolve().parents if (p/"PROJECT_REGISTRY.json").is_file())
ENTRY=ROOT/"projects/04-guardsynth-coc/experiments/paper1_cnl_learning/prepare_source_review.py"
spec=importlib.util.spec_from_file_location("source_acceptance_runner",ENTRY)
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


class SourceAcceptanceRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.output=Path(cls.temp.name)/"test-001"
        cls.result=runner.run(cls.output)
        cls.packet=runner.load(cls.output/"source_review_packet.json")

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_counts_source_gaps_and_review_history_preserved(self):
        self.assertEqual((self.result["candidate_count"],self.result["existing_reviews_reused"],self.result["deferred_count"]),(32,19,13))
        self.assertEqual(self.result["geometry_submission_records_with_coordinates"],0)
        audit=runner.load(self.output/"source_acceptance_audit.json")
        self.assertTrue(all(r["geometry_review_completed"] for r in audit["records"]))
        self.assertEqual(self.result["source_review_scenes_requested"],1)
        self.assertEqual(self.result["training_exports"],0)
        self.assertFalse(self.result["repeat_full_survey_requested"])

    def test_frames_no_future_or_misplaced_source_anchor(self):
        frames=self.packet["frames"]
        self.assertTrue(all(f["timestamp_us"]<=self.packet["event_timestamp_us"] for f in frames))
        self.assertEqual((frames[-1]["frame_index"],frames[-1]["timestamp_us"]),(297,9788396))
        self.assertEqual(float(self.packet["source_anchor"]["timestamp"]),0)
        self.assertEqual(self.packet["source_anchor_display"]["display_frame_timestamp_us"],-111570)
        self.assertFalse(self.packet["source_anchor_display"]["exact_time_match"])
        self.assertFalse(self.packet["human_decisions_prefilled"])
        self.assertFalse(self.packet["independent_gold_screen"])
        self.assertTrue((self.output/"event_frame_exact.png").is_file())

    def test_all_hashes_and_immutable_output(self):
        m=runner.load(self.output/"RUN_MANIFEST.json")
        for field,base in (("input_hashes",ROOT),("code_hashes",ROOT),("output_hashes",self.output)):
            for path,sha in m[field].items():self.assertEqual(runner.digest(base/path),sha,path)
        with self.assertRaises(FileExistsError):runner.run(self.output)

    def test_html_contains_only_packet_images_and_no_remote_dependencies(self):
        html=(self.output/"scene18_source_binding_review.html").read_text()
        p=json.loads(re.search(r'<script id="packet" type="application/json">(.*?)</script>',html,re.S)[1])
        self.assertEqual(len(p["frames"]),self.result["past_only_frame_count"])
        self.assertTrue(all(f["data_url"].startswith("data:image/jpeg;base64,") for f in p["frames"]))
        self.assertNotRegex(html,r'<(?:script|img)[^>]+src=["\']https?://')
        self.assertIn("showModal()",html)
        self.assertIn("localStorage.setItem",html)

    def test_client_state_edit_zoom_restore_and_packet_isolation(self):
        subprocess.run(["node",str(ROOT/"projects/04-guardsynth-coc/tests/integration/test_source_acceptance_ui.js"),
                        str(runner.TEMPLATE),str(self.output/"source_review_packet.json"),self.result["packet_sha256"]],check=True,capture_output=True,text=True)

    def test_synthetic_intake_preserves_unresolved_review_without_export(self):
        review={"review_version":runner.VERSION,"packet_sha256":self.result["packet_sha256"],
            "candidate_digest":self.packet["candidate_digest"],"event_timestamp_us":self.packet["event_timestamp_us"],
            "reviewer_id":"SYNTHETIC_INTAKE_TEST_NOT_HUMAN","reviewed_at":"2026-09-08T00:00:00Z",
            "target_identity":"UNCERTAIN","target_point":None,"zone_status":"UNCERTAIN","zone_polygon":[],
            "road_context":"UNCERTAIN","ped_truth":"UNKNOWN","road_truth":"UNKNOWN",
            "ped_reason":"test-only unknown","road_reason":"test-only unknown"}
        path=Path(self.temp.name)/"synthetic_submission.json"
        runner.write_json(path,review)
        result=runner.run(Path(self.temp.name)/"synthetic-intake-001",path,self.output/"source_review_packet.json")
        self.assertEqual(result["status"],"REVIEW_RECORDED_SOURCE_UNRESOLVED")
        self.assertTrue(result["review_completed"])
        self.assertFalse(result["learning_export_allowed"])
        self.assertIsNone(result["independent_action_gold"])

    def test_tampered_packet_rejected_before_intake_output(self):
        damaged=Path(self.temp.name)/"damaged";damaged.mkdir()
        runner.write_json(damaged/"RUN_MANIFEST.json",runner.load(self.output/"RUN_MANIFEST.json"))
        runner.write_json(damaged/"source_review_packet.json",{**self.packet,"event_timestamp_us":0})
        target=Path(self.temp.name)/"invalid-intake-001"
        with self.assertRaises(ValueError):runner.run(target,Path(self.temp.name)/"unused.json",damaged/"source_review_packet.json")
        self.assertFalse(target.exists())


if __name__=="__main__":unittest.main()
