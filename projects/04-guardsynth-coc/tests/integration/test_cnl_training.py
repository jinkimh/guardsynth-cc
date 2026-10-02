"""Software fixtures only: these tests are not a human annotation or effect study."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/src"))
sys.path.insert(0, str(ROOT / "platforms/eblc-bcv/src"))
from cli.solver_runtime import configure_project_z3
configure_project_z3(ROOT)

from guard_synth.cnl_training import (
    ARMS, audit_matched_examples, build_example, candidate_cnl, checked_cnl,
    digest_file, direct_nl,
)
from guard_synth.source_aware_generator import generate_from_request, load_generation_request
from guard_synth_eblc.indexed_collection import expand_indexed_collection

FIXTURE = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"


class CNLTrainingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = generate_from_request(load_generation_request(FIXTURE))
        cls.bundle = expand_indexed_collection(cls.generated.collection).bundle
        cls.checked = checked_cnl(cls.generated)

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / "fixture.ppm"
        self.image.write_bytes(b"P6\n1 1\n255\n\x00\x00\x00")

    def example(self, arm="L3", **overrides):
        constraints = {
            "L0": None,
            "L1": direct_nl("Fixture: yield.", source_refs=("fixture:rule",), provider="fixture-only"),
            "L2": candidate_cnl(self.bundle), "L3": self.checked,
        }
        args = dict(scene_id="s1", group_id="clip1", split="software_smoke",
                    image=self.image, image_sha256=digest_file(self.image), coc="private CoC text",
                    coc_source_ref="fixture:coc", choices={"STOP": "Stop", "PROCEED": "Proceed"},
                    action="STOP", action_source_ref="fixture:label", arm=arm, constraint=constraints[arm])
        args.update(overrides)
        return build_example(**args)

    def test_four_arms_have_identical_inputs_and_action_labels(self):
        examples = [self.example(arm) for arm in ARMS]
        self.assertEqual(audit_matched_examples(examples)["base_scene_count"], 1)
        self.assertTrue(all(e["input"] == examples[0]["input"] for e in examples))
        self.assertTrue(all(e["target"].endswith("ACTION: STOP") for e in examples))
        self.assertNotIn("CONSTRAINTS:", examples[0]["target"])
        self.assertIn(self.checked.text.rstrip(), examples[3]["target"])

    def test_coc_and_gold_constraints_never_enter_user_prompt(self):
        example = self.example()
        self.assertNotIn("private CoC text", example["input"]["text"])
        self.assertNotIn("SOURCE BUNDLE:", example["input"]["text"])
        self.assertNotIn("P0B-SYNTHETIC", example["input"]["text"])

    def test_l2_does_not_call_semantic_compiler(self):
        with patch("guard_synth.cnl_training.compile_core_model", side_effect=AssertionError):
            candidate = candidate_cnl(self.bundle)
        self.assertEqual(candidate.text, self.checked.text)
        self.assertEqual(candidate.provenance["semantic_verification"], "BYPASSED")

    def test_l3_keeps_smt_and_human_claim_boundaries(self):
        provenance = self.checked.provenance
        self.assertEqual(provenance["base_satisfiability"], "SAT")
        self.assertTrue(provenance["queries"])
        self.assertEqual(provenance["independent_semantic_audit"], "PENDING")
        self.assertEqual(provenance["paper_cohort_eligibility"], "NOT_EVALUATED")

    def test_source_failure_is_not_rendered_as_l3(self):
        with self.assertRaisesRegex(ValueError, "abstention"):
            checked_cnl(replace(self.generated, verdict="REVIEW_REQUIRED"))

    def test_unsat_cannot_pass_on_matching_unsat_query_alone(self):
        with patch("guard_synth.cnl_training.solve_assignment", return_value={"status": "UNSAT"}):
            with self.assertRaisesRegex(ValueError, "consistency"):
                checked_cnl(self.generated)

    def test_target_zone_and_lifecycle_survive_cnl_insertion(self):
        text = self.example()["target"]
        for value in ("synthetic-pedestrian:P17", "synthetic-zone:CZ4", "synthetic-pedestrian:P18",
                      "ego_path_s", "2 consecutive clear frames", "reactivation is enabled", "UNKNOWN"):
            self.assertIn(value, text)

    def test_image_hash_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "visual input"):
            self.example(image_sha256="0" * 64)

    def test_mutated_cnl_rejected(self):
        with self.assertRaisesRegex(ValueError, "constraint content"):
            self.example(constraint=replace(self.checked, text="different constraint"))

    def test_test_supervision_rejected(self):
        with self.assertRaisesRegex(ValueError, "test examples"):
            self.example(split="test")

    def test_label_outside_candidates_rejected(self):
        with self.assertRaisesRegex(ValueError, "action must"):
            self.example(action="OTHER")

    def test_arm_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "different arm"):
            self.example(constraint=candidate_cnl(self.bundle))

    def test_empty_direct_nl_provider_rejected(self):
        with self.assertRaises(ValueError):
            direct_nl("", source_refs=(), provider="")

    def test_clip_leakage_rejected(self):
        examples = [self.example(arm) for arm in ARMS]
        leaking = deepcopy(examples[0]); leaking.update(scene_id="s2", split="dev")
        with self.assertRaisesRegex(ValueError, "group crosses"):
            audit_matched_examples(examples + [leaking])

    def test_missing_arm_and_different_action_rejected(self):
        examples = [self.example(arm) for arm in ARMS]
        with self.assertRaisesRegex(ValueError, "missing arm"):
            audit_matched_examples(examples[:-1])
        examples[-1] = self.example(action="PROCEED")
        with self.assertRaisesRegex(ValueError, "unmatched"):
            audit_matched_examples(examples)


if __name__ == "__main__":
    unittest.main()
