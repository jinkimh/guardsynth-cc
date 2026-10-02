import unittest
from pathlib import Path

from apps.research_portal.paper_registry import load_paper_registry


ROOT = Path(__file__).resolve().parents[3]


class PaperRegistryTest(unittest.TestCase):
    def test_every_project_has_an_owner_scoped_manifest(self):
        registry = load_paper_registry(ROOT)

        self.assertEqual(len(registry["projects"]), 5)
        self.assertEqual(
            {entry["project_id"] for entry in registry["projects"]},
            {
                "safety-constrained-coc",
                "specification-alignment",
                "sequential-coc-verification",
                "guardsynth-coc",
                "eblc-language-verification",
            },
        )
        self.assertEqual(
            {paper["paper_id"] for paper in registry["papers"]},
            {"paper-01-safety-constrained-coc", "paper-03-sequential-coc-verification"},
        )

    def test_client_records_do_not_disclose_absolute_paths(self):
        registry = load_paper_registry(ROOT)

        for paper in registry["papers"]:
            self.assertFalse(Path(paper["source_path"]).is_absolute())
            self.assertTrue(paper["source_path"].startswith("projects/"))
            self.assertNotIn("canonical_path", paper)


if __name__ == "__main__":
    unittest.main()
