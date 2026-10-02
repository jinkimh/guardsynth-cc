"""Real development export and source-review boundaries, with synthetic UI mutations."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").exists())
sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning"))
import prepare_development_dataset as entry

RUN = entry.PARENT.parent / "development-data-2026-09-08-001"


class DevelopmentDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = entry.r.load(RUN / "source_gap_packet.json")

    def answer(self):
        scene = self.packet["scenes"][0]
        return {"candidate_digest": scene["candidate_digest"], "event_timestamp_us": scene["event_timestamp_us"],
            **{field: "UNKNOWN" for field in entry.CHOICES}, **{field: "Synthetic validation only: cannot determine" for field in entry.TEXTS},
            "target_point": None, "zone_polygon": [], "reviewed_at": "2026-09-08T12:00:00+00:00"}

    def test_unknown_is_a_valid_source_response_not_gold(self):
        answer = self.answer()
        self.assertEqual(entry.validate_answer(answer, self.packet["scenes"][0]), answer)
        self.assertNotIn("action", answer)

    def test_not_applicable_allows_empty_notes_but_unknown_does_not(self):
        answer = self.answer()
        answer.update({field: "NOT_APPLICABLE" for field in entry.CHOICES})
        answer.update({field: "" for field in entry.TEXTS})
        self.assertEqual(entry.validate_answer(answer, self.packet["scenes"][0]), answer)
        program = "require(process.argv[1]).validate(JSON.parse(process.argv[2]),JSON.parse(process.argv[3]));"
        subprocess.run(["node", "-e", program, str(entry.SCRIPT), json.dumps(answer), json.dumps({k: self.packet["scenes"][0][k] for k in ("candidate_digest", "event_timestamp_us")})], check=True, capture_output=True)
        for text, choice in (("target_description", "target_status"), ("ped_reason", "ped_truth"), ("road_reason", "road_context"), ("control_reason", "control_context")):
            altered = {**answer, choice: "UNKNOWN"}
            with self.subTest(field=text), self.assertRaises(ValueError):
                entry.validate_answer(altered, self.packet["scenes"][0])

    def test_confirmed_target_and_zone_require_real_coordinates(self):
        for field in ("target_status", "zone_status"):
            with self.assertRaises(ValueError):
                entry.validate_answer({**self.answer(), field: "CONFIRMED"}, self.packet["scenes"][0])
        with self.assertRaises(ValueError):
            entry.validate_answer({**self.answer(), "zone_polygon": [[0, 0], [.5, .5], [1, 1]]}, self.packet["scenes"][0])

    def test_known_ped_relation_requires_target_zone(self):
        with self.assertRaises(ValueError):
            entry.validate_answer({**self.answer(), "ped_truth": "FALSE"}, self.packet["scenes"][0])

    def test_context_is_not_forced_to_scene18_merge(self):
        answer = self.answer()
        answer.update(road_context="NOT_APPLICABLE", road_truth="NOT_APPLICABLE")
        entry.validate_answer(answer, self.packet["scenes"][0])
        answer["road_truth"] = "FALSE"
        with self.assertRaises(ValueError):
            entry.validate_answer(answer, self.packet["scenes"][0])

    def test_wrong_identity_choices_reasons_and_extra_fields_rejected(self):
        for field, value in (("candidate_digest", "other"), ("event_timestamp_us", 0),
                             ("ped_truth", []), ("ped_reason", ""), ("reviewed_at", "2026-09-08"), ("action", "ENTER_ZONE")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                entry.validate_answer({**self.answer(), field: value}, self.packet["scenes"][0])

    def test_causal_selection_no_future_or_duplicate_frames(self):
        times = [{"frame_index": i, "timestamp": i*10} for i in range(31)]
        frames = entry.select_past_frames(times, 299)
        self.assertEqual(len(frames), 7)
        self.assertEqual(frames[-1]["timestamp"], 290)
        self.assertEqual(len(entry.select_past_frames(times[:2], 10)), 2)
        with self.assertRaises(ValueError):
            entry.select_past_frames(times, -1)
        with self.assertRaises(ValueError):
            entry.select_past_frames(times[::-1], 300)

    def test_thirty_scenes_and_four_priority_not_nominal_labels(self):
        scenes = self.packet["scenes"]
        self.assertEqual(len(scenes), 30)
        self.assertEqual(len({s["candidate_digest"] for s in scenes}), 30)
        self.assertTrue(all(s["prior_observation"] == "NO_HAZARD_VISIBLE" for s in scenes[:4]))
        self.assertTrue(all(s["answers"] is None and s["independent_action_gold"] is None for s in scenes))
        disposition = entry.r.load(RUN / "candidate_disposition.json")["records"]
        self.assertEqual(len(disposition), 32)
        self.assertEqual(sum(d["disposition"] == "NO_REPEAT_UNOBSERVABLE" for d in disposition), 1)
        self.assertTrue(all(not d["test_allowed"] for d in disposition))

    def test_display_frames_and_machine_points_are_causal(self):
        import base64
        for scene in self.packet["scenes"]:
            self.assertLessEqual(len(scene["frames"]), 7)
            for frame in scene["frames"]:
                self.assertLessEqual(frame["timestamp_us"], scene["event_timestamp_us"])
                self.assertEqual(hashlib.sha256(base64.b64decode(frame["data_url"].split(",", 1)[1])).hexdigest(), frame["sha256"])
            self.assertTrue(all(p["timestamp_us"] == scene["event_timestamp_us"] for p in scene["machine_points"]))

    def test_actual_export_is_one_scene_two_arms_not_main(self):
        examples = [json.loads((RUN / f"{arm}_development.jsonl").read_text()) for arm in ("l0", "l3")]
        self.assertEqual(len({e["scene_id"] for e in examples}), 1)
        self.assertEqual(examples[0]["input"], examples[1]["input"])
        self.assertEqual(examples[0]["common_example_sha256"], examples[1]["common_example_sha256"])
        self.assertNotIn("CONSTRAINTS:", examples[0]["target"])
        self.assertIn("CONSTRAINTS:", examples[1]["target"])
        for example in examples:
            self.assertTrue(example["development_training_allowed"])
            self.assertFalse(example["main_training_allowed"])
            self.assertFalse(example["main_test_eligibility"])
            self.assertFalse(example["preview_only"])
            self.assertFalse(example["review_input_equivalence"])
            self.assertEqual(example["action"], "DEFER_ENTRY")
            self.assertEqual(example["event_predicates"]["road"]["truth"], "UNKNOWN")
            self.assertNotIn("COC:", example["input"]["text"])
            self.assertNotIn("CONSTRAINTS:", example["input"]["text"])
            self.assertNotIn("ACTION: DEFER_ENTRY", example["input"]["text"])
            self.assertEqual(hashlib.sha256(example["target"].encode()).hexdigest(), example["target_sha256"])
            entry.r.verified(Path(example["image"]), example["image_sha256"])

    def test_processor_checks_and_no_optimizer_steps(self):
        result = entry.r.load(RUN / "RESULT.json")
        self.assertEqual(result["main_training_scenes"], 0)
        self.assertEqual(result["development_training_scenes"], 1)
        self.assertEqual(result["optimizer_steps"], 0)
        self.assertEqual(result["new_human_answers"], 0)
        metrics = result["processor_metrics"]
        self.assertEqual(metrics[0]["prompt_tokens"], metrics[1]["prompt_tokens"])
        self.assertTrue(all(m["supervised_tokens"] > 0 and m["pixel_values_shape"][0] > 0 for m in metrics))

    def test_html_has_usable_review_and_preserves_drafts(self):
        html = entry.TEMPLATE.read_text()
        script = entry.SCRIPT.read_text()
        self.assertIn('id="complete"', html)
        self.assertIn('id="export"', html)
        self.assertIn('id="closeZoom"', html)
        self.assertIn("완료한 장면만", html)
        self.assertIn("localStorage.setItem", script)
        self.assertIn("completed.delete", script)
        self.assertIn("validate(answer(),scene())", script)
        self.assertNotIn("fetch(", script)
        self.assertNotIn("window.open", script)

    def test_javascript_validation_agrees_for_unknown_and_invalid_polygon(self):
        program = "const m=require(process.argv[1]), a=JSON.parse(process.argv[2]), s=JSON.parse(process.argv[3]);m.validate(a,s);if(m.polygonOK([[0,0],[.5,.5],[1,1]]))throw Error('degenerate accepted');a.ped_truth='FALSE';let rejected=false;try{m.validate(a,s)}catch{rejected=true}if(!rejected)throw Error('unknown geometry admitted');"
        subprocess.run(["node", "--check", str(entry.SCRIPT)], check=True, capture_output=True)
        subprocess.run(["node", "-e", program, str(entry.SCRIPT), json.dumps(self.answer()), json.dumps({k: self.packet["scenes"][0][k] for k in ("candidate_digest", "event_timestamp_us")})], check=True, capture_output=True)

    def test_intake_preserves_partial_answers_without_training_promotion(self):
        with TemporaryDirectory() as temp:
            response = Path(temp) / "response.json"
            entry.r.write_json(response, {"review_version": entry.VERSION, "packet_sha256": entry.r.digest(RUN / "source_gap_packet.json"),
                "reviewer_id": "SYNTHETIC TEST ONLY", "records": [self.answer()]})
            output = Path(temp) / "intake"
            result = entry.intake(output, RUN / "source_gap_packet.json", response)
            self.assertEqual(result["source_reviews_received"], 1)
            self.assertEqual(result["remaining_in_this_packet"], 29)
            self.assertEqual(result["training_scenes_added"], 0)
            self.assertEqual(result["independent_action_gold_added"], 0)
            with self.assertRaises(FileExistsError):
                entry.intake(output, RUN / "source_gap_packet.json", response)

    def test_integrity_and_output_immutability(self):
        entry.r.revalidate_run(RUN)
        with self.assertRaises(FileExistsError):
            entry.run(RUN)

    def test_ui_refresh_keeps_packet_draft_identity_and_hides_host_path(self):
        refreshed = RUN.parent / "source-gap-ui-2026-09-08-001"
        entry.r.revalidate_run(refreshed)
        self.assertEqual(entry.r.digest(RUN / "source_gap_packet.json"), entry.r.digest(refreshed / "source_gap_packet.json"))
        html = (refreshed / "source_gap_review.html").read_text()
        self.assertFalse(str(ROOT) in html, "absolute host path leaked")
        self.assertIn(entry.r.digest(RUN / "source_gap_packet.json"), html)
        with self.assertRaises(FileExistsError):
            entry.refresh_review(refreshed, RUN)


if __name__ == "__main__":
    unittest.main()
