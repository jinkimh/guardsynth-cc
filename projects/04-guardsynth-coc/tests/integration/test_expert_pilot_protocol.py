"""TDD contract for M16 stratified design and fail-closed preflight."""

from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.expert_pilot_protocol import (
    annotation_disagreement_reasons,
    build_blinded_assignment_manifest,
    build_expert_pilot_metrics,
    build_pilot_preflight,
    build_pilot_slot_manifest,
    build_power_planning_record,
    pilot_design,
    validate_expert_annotation,
)
from guard_synth_eblc.schema_validation import load_json
from cli.pipelines.guardsynth.expert_pilot_preflight.run import execute


BATCH = ROOT / (
    "artifacts/results/restricted/guardsynth-sim24-batch-001/"
    "alpamayo-terminal-batch-2026-08-12-v1/BATCH_RESULT.json"
)
TRAINING = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/expert_annotation_training_example_v0_1.json"
WORKBENCH = ROOT / (
    "projects/04-guardsynth-coc/pipelines/cli/expert_pilot_preflight/"
    "expert_annotation_workbench.html"
)


class ExpertPilotProtocolTest(unittest.TestCase):
    @staticmethod
    def annotation(reviewer: str, *, applicability: str = "UNSUPPORTED") -> dict:
        return {
            "annotation_version": "guardsynth-expert-annotation-v0.1",
            "assignment_id": f"assignment-{reviewer}",
            "reviewer_pseudonym": reviewer,
            "scene_ref_hash": "sha256:" + "a" * 64,
            "interface_mode": "COMPLETE_AUTHORING",
            "applicability": applicability,
            "guard_fields": {
                "guard_type": None, "target_id": None, "zone_id": None,
                "operator": None, "range": None, "unit": None,
                "coordinate_frame": None,
            },
            "source_sufficiency": {
                "verdict": "INSUFFICIENT", "source_refs": [],
                "reason_codes": ["MISSING_SOURCE"],
            },
            "lifecycle": {
                "activation": None, "maintain": None, "release": None,
                "reactivation": None, "expiry": None, "fallback": None,
            },
            "confidence": 1.0,
            "corrections": [],
            "started_at": "2026-08-12T00:00:00Z",
            "completed_at": "2026-08-12T00:01:00Z",
        }

    def test_design_has_60_scenes_balanced_slices_and_outcomes(self) -> None:
        design = pilot_design()
        self.assertEqual(sum(design["slice_quota"].values()), 60)
        self.assertEqual(sum(design["outcome_quota"].values()), 60)
        self.assertEqual(design["independent_reviewers_per_scene"], 2)
        self.assertFalse(design["synthetic_required_field_fill_allowed"])
        manifest = build_pilot_slot_manifest()
        self.assertEqual(manifest["slot_count"], 60)
        slice_counts = {}
        outcome_counts = {}
        joint_counts = {}
        for slot in manifest["slots"]:
            slice_counts[slot["slice"]] = slice_counts.get(slot["slice"], 0) + 1
            outcome_counts[slot["outcome"]] = outcome_counts.get(slot["outcome"], 0) + 1
            key = (slot["slice"], slot["outcome"])
            joint_counts[key] = joint_counts.get(key, 0) + 1
        self.assertEqual(slice_counts, design["slice_quota"])
        self.assertEqual(outcome_counts, design["outcome_quota"])
        self.assertEqual(set(joint_counts.values()), {3, 4})

    def test_current_m13_batch_blocks_annotation_with_exact_shortfall(self) -> None:
        result = build_pilot_preflight(load_json(BATCH))
        self.assertEqual(result["status"], "BLOCKED_DATA_SHORTFALL")
        self.assertFalse(result["annotation_start_allowed"])
        self.assertEqual(result["eligible_scene_count"], 4)
        self.assertEqual(result["total_scene_shortfall"], 56)
        self.assertEqual(result["slice_shortfall"]["PEDESTRIAN_CYCLIST_YIELD"], 16)
        self.assertEqual(result["slice_shortfall"]["STOP_SIGNALS"], 20)
        self.assertEqual(result["outcome_shortfall"]["HAZARD_TRUE_ACTIVE"], 6)
        self.assertFalse(result["synthetic_scene_fill_performed"])

    def test_annotation_schema_accepts_complete_abstention_record(self) -> None:
        annotation = self.annotation("reviewer-A")
        validate_expert_annotation(annotation)
        annotation["confidence"] = 1.1
        with self.assertRaisesRegex(ValueError, "CONFIDENCE_OUT_OF_RANGE"):
            validate_expert_annotation(annotation)

    def test_blinded_assignment_is_balanced_deterministic_and_independent(self) -> None:
        scenes = [f"sha256:{index:064x}" for index in range(60)]
        kwargs = {
            "scene_ref_hashes": scenes,
            "reviewer_pseudonyms": ["R1", "R2", "R3", "R4"],
            "adjudicator_pseudonym": "ADJ",
            "calibration_scene_hashes": set(scenes[:4]),
        }
        first = build_blinded_assignment_manifest(**kwargs)
        second = build_blinded_assignment_manifest(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(len(first["assignments"]), 120)
        self.assertEqual(first["interface_mode_counts"], {
            "MINIMAL_CONFIRMATION": 60,
            "COMPLETE_AUTHORING": 60,
        })
        by_scene = {}
        for item in first["assignments"]:
            by_scene.setdefault(item["scene_ref_hash"], []).append(item)
        self.assertTrue(all(len(items) == 2 for items in by_scene.values()))
        self.assertTrue(all(
            len({item["reviewer_pseudonym"] for item in items}) == 2
            and len({item["interface_mode"] for item in items}) == 2
            for items in by_scene.values()
        ))
        self.assertFalse(first["model_identity_exposed"])
        self.assertFalse(first["raw_scene_identifier_exposed"])

    def test_disagreement_queue_requires_independent_same_scene_reviews(self) -> None:
        left = self.annotation("R1", applicability="APPLICABLE")
        right = self.annotation("R2", applicability="UNSUPPORTED")
        reasons = annotation_disagreement_reasons(left, right)
        self.assertIn("APPLICABILITY_DISAGREEMENT", reasons)
        right["reviewer_pseudonym"] = "R1"
        with self.assertRaisesRegex(ValueError, "NOT_INDEPENDENT"):
            annotation_disagreement_reasons(left, right)

    def test_training_workbench_is_self_contained_and_fixture_is_valid(self) -> None:
        validate_expert_annotation(load_json(TRAINING))
        html = WORKBENCH.read_text(encoding="utf-8")
        self.assertIn("TRAINING ONLY", html)
        self.assertIn("MINIMAL_CONFIRMATION", html)
        self.assertIn("COMPLETE_AUTHORING", html)
        self.assertIn("function buildRecord()", html)
        self.assertIn("new Blob", html)
        self.assertIn("<svg class=\"scene\"", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

    def test_metrics_require_complete_independent_assignments_and_measure_modes(self) -> None:
        scenes = [f"sha256:{index:064x}" for index in range(4)]
        manifest = build_blinded_assignment_manifest(
            scene_ref_hashes=scenes,
            reviewer_pseudonyms=["R1", "R2", "R3", "R4"],
            adjudicator_pseudonym="ADJ",
        )
        annotations = []
        for assignment in manifest["assignments"]:
            annotation = self.annotation(
                assignment["reviewer_pseudonym"],
                applicability=(
                    "APPLICABLE"
                    if int(assignment["scene_ref_hash"].split(":", 1)[1], 16) % 2 == 0
                    else "NOT_APPLICABLE"
                ),
            )
            annotation.update({
                "assignment_id": assignment["assignment_id"],
                "scene_ref_hash": assignment["scene_ref_hash"],
                "interface_mode": assignment["interface_mode"],
                "completed_at": (
                    "2026-08-12T00:01:00Z"
                    if assignment["interface_mode"] == "MINIMAL_CONFIRMATION"
                    else "2026-08-12T00:02:00Z"
                ),
            })
            annotations.append(annotation)
        metrics = build_expert_pilot_metrics(
            assignment_manifest=manifest,
            annotations=annotations,
            expected_scene_count=4,
            guideline_revision_count=1,
        )
        self.assertEqual(metrics["applicability_alpha"], 1.0)
        self.assertEqual(
            metrics["timing_by_interface_mode"]["MINIMAL_CONFIRMATION"]["median_seconds"],
            60.0,
        )
        self.assertEqual(
            metrics["timing_by_interface_mode"]["COMPLETE_AUTHORING"]["median_seconds"],
            120.0,
        )
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_INDEPENDENT"):
            build_expert_pilot_metrics(
                assignment_manifest=manifest,
                annotations=annotations[:-1],
                expected_scene_count=4,
            )

    def test_applicability_alpha_uses_finite_sample_expected_disagreement(self) -> None:
        scenes = [f"sha256:{index:064x}" for index in range(4)]
        manifest = build_blinded_assignment_manifest(
            scene_ref_hashes=scenes,
            reviewer_pseudonyms=["R1", "R2", "R3", "R4"],
            adjudicator_pseudonym="ADJ",
        )
        annotations = []
        for assignment in manifest["assignments"]:
            scene_index = int(assignment["scene_ref_hash"].split(":", 1)[1], 16)
            applicability = "APPLICABLE" if scene_index == 0 else "NOT_APPLICABLE"
            if scene_index >= 2 and assignment["interface_mode"] == "MINIMAL_CONFIRMATION":
                applicability = "APPLICABLE"
            annotation = self.annotation(
                assignment["reviewer_pseudonym"], applicability=applicability,
            )
            annotation.update({
                "assignment_id": assignment["assignment_id"],
                "scene_ref_hash": assignment["scene_ref_hash"],
                "interface_mode": assignment["interface_mode"],
            })
            annotations.append(annotation)
        metrics = build_expert_pilot_metrics(
            assignment_manifest=manifest,
            annotations=annotations,
            expected_scene_count=4,
        )
        self.assertAlmostEqual(metrics["applicability_alpha"], 0.125)

    def test_power_planning_requires_observed_nonzero_effect_and_cluster_inputs(self) -> None:
        record = build_power_planning_record(
            paired_effect_estimate=0.1,
            paired_effect_variance=0.04,
            cluster_size=3,
            intraclass_correlation=0.1,
            effect_source_ref="artifact://m16/paired-effect.json",
            variance_source_ref="artifact://m16/paired-variance.json",
        )
        self.assertGreaterEqual(record["required_scene_count"], 2)
        self.assertEqual(record["design_effect"], 1.2)
        with self.assertRaisesRegex(ValueError, "NONZERO_EFFECT"):
            build_power_planning_record(
                paired_effect_estimate=0.0,
                paired_effect_variance=0.04,
                cluster_size=3,
                intraclass_correlation=0.1,
                effect_source_ref="artifact://m16/paired-effect.json",
                variance_source_ref="artifact://m16/paired-variance.json",
            )

    def test_preflight_package_contains_all_review_and_analysis_contracts(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "preflight"
            result = execute(batch_path=BATCH, output_dir=output)
            self.assertFalse(result["annotation_start_allowed"])
            for name in (
                "EXPERT_ANNOTATION_SCHEMA.json",
                "EXPERT_ASSIGNMENT_SCHEMA.json",
                "EXPERT_PILOT_METRICS_SCHEMA.json",
                "POWER_ANALYSIS_INPUT_SCHEMA.json",
                "PILOT_SLOT_MANIFEST.json",
                "PILOT_SLOT_MANIFEST_SCHEMA.json",
                "TRAINING_ANNOTATION_EXAMPLE.json",
                "expert_annotation_workbench.html",
            ):
                self.assertTrue((output / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
