import unittest
from pathlib import Path

from apps.research_portal.projection import ProjectionError, load_portfolio


ROOT = Path(__file__).resolve().parents[3]


class ProjectionTest(unittest.TestCase):
    def test_projects_follow_registry_order_and_platforms_are_separate(self):
        portfolio = load_portfolio(ROOT)

        self.assertEqual(
            [project["project_id"] for project in portfolio["projects"]],
            [
                "safety-constrained-coc",
                "specification-alignment",
                "sequential-coc-verification",
                "guardsynth-coc",
                "eblc-language-verification",
            ],
        )
        self.assertEqual(
            [platform["platform_id"] for platform in portfolio["platforms"]],
            ["eblc-bcv"],
        )
        self.assertEqual(
            portfolio["platforms"][0]["consumers"],
            ["guardsynth-coc", "specification-alignment", "eblc-language-verification"],
        )
        guardsynth = next(item for item in portfolio["projects"] if item["project_id"] == "guardsynth-coc")
        self.assertEqual(guardsynth["dependencies"], ["eblc-bcv"])

    def test_gate_state_is_taken_from_the_active_milestone_not_project_state(self):
        status_path = ROOT / "projects/04-guardsynth-coc/STATUS.md"
        status_text = status_path.read_text(encoding="utf-8")
        state_line = next(line for line in status_text.splitlines() if line.startswith("- State:"))
        portfolio = load_portfolio(ROOT, document_overrides={
            status_path: status_text.replace(state_line, "- State: `PROJECTION_TEST_STATE`", 1),
        })
        guardsynth = next(
            project
            for project in portfolio["projects"]
            if project["project_id"] == "guardsynth-coc"
        )

        self.assertEqual(guardsynth["active_milestone_id"], "M16")
        self.assertEqual(guardsynth["gate_state"], "PARTIAL")
        self.assertEqual(
            guardsynth["raw_state"],
            "PROJECTION_TEST_STATE",
        )
        self.assertEqual(len(guardsynth["canonical_sources"]), 8)
        self.assertEqual(len(guardsynth["canonical_source_hashes"]), 8)
        self.assertGreaterEqual(len(guardsynth["status"]["evidence"]), 2)
        self.assertEqual(len(guardsynth["status"]["next"]), 1)
        self.assertIn("next_work-package_requirements", guardsynth["status"]["fields"])
        self.assertTrue(guardsynth["decisions"])
        self.assertTrue(all("content_hash" in item for item in guardsynth["decisions"]))

    def test_tracker_milestone_must_exist_in_ledger(self):
        tracker = ROOT / "projects/04-guardsynth-coc/docs/plans/03_PROJECT_EXECUTION_TRACKER.md"
        broken = tracker.read_text(encoding="utf-8").replace("`M16 PARTIAL`", "`M99 PARTIAL`", 1)

        with self.assertRaises(ProjectionError):
            load_portfolio(ROOT, document_overrides={tracker: broken})

    def test_survey_and_result_indexes_are_live_content_sources(self):
        survey = ROOT / "projects/04-guardsynth-coc/docs/surveys/README.md"
        result = ROOT / "projects/04-guardsynth-coc/results/RESULT_INDEX.md"
        base = load_portfolio(ROOT)
        changed = load_portfolio(ROOT, document_overrides={
            survey: survey.read_text(encoding="utf-8") + "\n<!-- live survey fixture -->\n",
            result: result.read_text(encoding="utf-8") + "\n<!-- live result fixture -->\n",
        })
        base_project = next(item for item in base["projects"] if item["project_id"] == "guardsynth-coc")
        changed_project = next(item for item in changed["projects"] if item["project_id"] == "guardsynth-coc")
        self.assertNotEqual(
            base_project["canonical_source_hashes"]["survey_index"],
            changed_project["canonical_source_hashes"]["survey_index"],
        )
        self.assertNotEqual(
            base_project["canonical_source_hashes"]["result_index"],
            changed_project["canonical_source_hashes"]["result_index"],
        )


if __name__ == "__main__":
    unittest.main()
