from __future__ import annotations

import json
from pathlib import Path
import unittest

from cli.checks.project_integrity import broken_markdown_links


ROOT = Path(__file__).resolve().parents[2]


class ProjectLayoutV2Test(unittest.TestCase):
    def test_canonical_roots_exist(self) -> None:
        for relative in (
            "docs/requirements", "docs/plans", "docs/designs", "docs/reports",
            "src", "cli/pipelines", "tests", "experiments",
            "artifacts/intermediate", "artifacts/results/public",
            "artifacts/results/restricted", "data", "papers", "runtime",
            "third_party", "archive",
        ):
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_dir(), relative)

    def test_deprecated_mixed_roots_are_absent(self) -> None:
        self.assertFalse((ROOT / "research").exists())
        self.assertFalse((ROOT / "experiments/results").exists())

    def test_tools_installers_and_generated_models_are_segregated(self) -> None:
        self.assertTrue(
            (ROOT / "runtime/solvers/uppaal-5.0.0-linux64/bin/verifyta").is_file()
        )
        for name in (
            "uppaal-5.0.0-linux64.zip",
            "z3-5.0.0-x64-glibc-2.39.zip",
            "z3-z3-5.0.0.tar.gz",
        ):
            self.assertTrue((ROOT / "archive/installers" / name).is_file())
            self.assertFalse((ROOT / name).exists())
        self.assertTrue((ROOT / "artifacts/intermediate/uppaal-models").is_dir())
        self.assertFalse((ROOT / "experiments/uppaal/models").exists())

    def test_eblc_pipelines_are_domain_grouped(self) -> None:
        expected = {
            "composition_compile", "core_smt_compile", "derivation_compile", "indexed_collection_compile", "p0b_schema_bcv", "program_conformance", "release_candidate",
            "restricted_scene_grounding", "robustness_audit", "scenario_validation",
        }
        actual = {
            path.name for path in (ROOT / "cli/pipelines/eblc").iterdir()
            if path.is_dir() and not path.name.startswith("__")
        }
        self.assertEqual(actual, expected)
        for name in expected:
            runner = ROOT / "cli/pipelines/eblc" / name / "run.py"
            self.assertTrue(runner.is_file())
            self.assertIn("project_root(__file__)", runner.read_text(encoding="utf-8"))

    def test_guardsynth_generator_is_separate_from_eblc_language_pipelines(self) -> None:
        runner = ROOT / "cli/pipelines/guardsynth/source_aware_generate/run.py"
        label_light_runner = ROOT / "cli/pipelines/guardsynth/label_light_grounding/run.py"
        review_runner = ROOT / "cli/pipelines/guardsynth/scene_evidence_review/run.py"
        review_html = ROOT / "cli/pipelines/guardsynth/scene_evidence_review/SCENE_EVIDENCE_REVIEW.html"
        self.assertTrue((ROOT / "src/guard_synth/source_aware_generator.py").is_file())
        self.assertTrue((ROOT / "src/guard_synth/label_light_grounding.py").is_file())
        self.assertTrue(runner.is_file())
        self.assertTrue(label_light_runner.is_file())
        self.assertTrue(review_runner.is_file())
        self.assertTrue(review_html.is_file())
        self.assertIn("project_root(__file__)", runner.read_text(encoding="utf-8"))
        self.assertIn("project_root(__file__)", label_light_runner.read_text(encoding="utf-8"))
        self.assertIn("project_root(__file__)", review_runner.read_text(encoding="utf-8"))
        self.assertFalse((ROOT / "src/guard_synth_eblc/source_aware_generator.py").exists())

    def test_maintained_eblc_tests_have_single_owner(self) -> None:
        maintained = sorted((ROOT / "tests/guard_synth_eblc").glob("test_*.py"))
        compatibility = sorted((ROOT / "experiments/eblc_p0b").glob("test_*.py"))
        self.assertEqual(len(maintained), 22)
        self.assertEqual(compatibility, [])

    def test_migration_map_is_machine_readable(self) -> None:
        mapping = json.loads(
            (ROOT / "docs/architecture/MIGRATION_MAP.json").read_text(encoding="utf-8")
        )
        self.assertEqual(mapping["migration_id"], "PROJECT-LAYOUT-V2-2026-08-09")
        self.assertEqual(
            mapping["mappings"]["experiments/results/baseline"],
            "artifacts/results/public",
        )

    def test_guardsynth_has_one_canonical_living_execution_tracker(self) -> None:
        tracker = ROOT / "docs/plans/guard-synth-coc/PROJECT_EXECUTION_TRACKER.md"
        milestones = ROOT / "docs/plans/guard-synth-coc/PROJECT_MILESTONES.md"
        master_plan = ROOT / "docs/plans/guard-synth-coc/RESEARCH_PLAN_V1.md"
        docs_index = ROOT / "docs/README.md"
        self.assertTrue(tracker.is_file())
        self.assertTrue(milestones.is_file())
        text = tracker.read_text(encoding="utf-8")
        self.assertIn("현재 활성 작업 ID: `GS-P1-DRYRUN-001`", text)
        self.assertIn("## 7. 매 작업 세션의 운영 규칙", text)
        milestone_text = milestones.read_text(encoding="utf-8")
        for milestone in range(21):
            self.assertIn(f"M{milestone:02d}", milestone_text)
        self.assertIn("M11. 관할·ODD·vertical slice·source hierarchy 결정", milestone_text)
        self.assertIn("PROJECT_MILESTONES.md", text)
        for phase in range(7):
            self.assertIn(f"| P{phase} |", text)
        self.assertIn("PROJECT_EXECUTION_TRACKER.md", master_plan.read_text(encoding="utf-8"))
        self.assertIn("PROJECT_MILESTONES.md", master_plan.read_text(encoding="utf-8"))
        self.assertIn("PROJECT_EXECUTION_TRACKER.md", docs_index.read_text(encoding="utf-8"))
        self.assertIn("PROJECT_MILESTONES.md", docs_index.read_text(encoding="utf-8"))

    def test_canonical_documentation_links_resolve(self) -> None:
        self.assertEqual(broken_markdown_links(ROOT), ())

    def test_public_manifest_has_only_existing_canonical_paths(self) -> None:
        entries = (ROOT / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
        paths = [line.split("  ./", 1)[1] for line in entries if "  ./" in line]
        self.assertTrue(paths)
        self.assertTrue(all((ROOT / path).is_file() for path in paths))
        self.assertFalse(any(path.startswith("research/") for path in paths))
        self.assertFalse(any(path.startswith("experiments/results/") for path in paths))


if __name__ == "__main__":
    unittest.main()
