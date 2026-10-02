from __future__ import annotations

import json
from fnmatch import fnmatch
from pathlib import Path
import re
import subprocess
import unittest

from cli.checks.project_integrity import broken_markdown_links
from cli.checks.file_naming import (
    maintained_directories,
    maintained_files,
    violations as naming_violations,
)


ROOT = Path(__file__).resolve().parents[2]
STANDARD_PROJECT_DIRS = {
    "docs/charter",
    "docs/requirements",
    "docs/plans",
    "docs/designs",
    "docs/decisions",
    "docs/reports",
    "docs/surveys",
    "src",
    "pipelines",
    "tests/unit",
    "tests/integration",
    "tests/acceptance",
    "experiments",
    "paper",
    "results",
}


def metadata_value(path: Path, key: str) -> str:
    prefix = f"{key}:"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    raise AssertionError(f"{key} missing from {path.relative_to(ROOT)}")


class ProjectStructureCodexV3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(
            (ROOT / "PROJECT_REGISTRY.json").read_text(encoding="utf-8")
        )

    def test_codex_and_agent_entry_point_are_canonical(self) -> None:
        codex = ROOT / "docs/architecture/PROJECT_STRUCTURE_CODEX.md"
        agents = ROOT / "AGENTS.md"
        self.assertTrue(codex.is_file())
        self.assertIn("Codex version: `v3.6`", codex.read_text(encoding="utf-8"))
        self.assertIn("PROJECT_STRUCTURE_CODEX.md", agents.read_text(encoding="utf-8"))
        self.assertIn("Superpowers", agents.read_text(encoding="utf-8"))
        self.assertIn("../guardsynth-cc-worktrees/", agents.read_text(encoding="utf-8"))
        self.assertIn("FILE_NAMING_CODEX.md", agents.read_text(encoding="utf-8"))

    def test_registry_exactly_matches_project_directories(self) -> None:
        registered = {item["id"]: item for item in self.registry["projects"]}
        actual = {path.name for path in (ROOT / "projects").iterdir() if path.is_dir()}
        expected_directories = {Path(item["path"]).name for item in registered.values()}
        self.assertEqual(actual, expected_directories)
        self.assertEqual(
            [item["order"] for item in self.registry["projects"]],
            list(range(1, len(registered) + 1)),
        )
        self.assertEqual(
            {path.name for path in (ROOT / "projects").iterdir() if path.is_file()},
            {"README.md"},
        )
        for project_id, entry in registered.items():
            with self.subTest(project=project_id):
                root = ROOT / entry["path"]
                self.assertEqual(root.name, f"{entry['order']:02d}-{project_id}")
                self.assertEqual(
                    metadata_value(root / "PROJECT.yaml", "project_id"), project_id
                )
                self.assertEqual(
                    metadata_value(root / "PROJECT.yaml", "project_order"),
                    str(entry["order"]),
                )
                self.assertEqual(
                    metadata_value(root / "PROJECT.yaml", "artifact_root"),
                    entry["artifact_root"],
                )
                canonical_research_plan = metadata_value(
                    root / "PROJECT.yaml", "canonical_research_plan"
                )
                self.assertRegex(
                    canonical_research_plan,
                    r"^docs/plans/01_RESEARCH_PLAN_V\d{2}\.md$",
                )
                self.assertTrue((root / canonical_research_plan).is_file())
                canonical_documents = {
                    "canonical_status": "STATUS.md",
                    "canonical_milestones": "docs/plans/02_PROJECT_MILESTONES.md",
                    "canonical_execution_tracker": "docs/plans/03_PROJECT_EXECUTION_TRACKER.md",
                    "survey_index": "docs/surveys/README.md",
                }
                for key, relative in canonical_documents.items():
                    self.assertEqual(metadata_value(root / "PROJECT.yaml", key), relative)
                    self.assertTrue((root / relative).is_file())
                self.assertTrue((root / "README.md").is_file())
                self.assertTrue((root / "STATUS.md").is_file())
                readme = (root / "README.md").read_text(encoding="utf-8")
                status = (root / "STATUS.md").read_text(encoding="utf-8")
                self.assertIn(canonical_research_plan, readme)
                self.assertIn("docs/plans/02_PROJECT_MILESTONES.md", readme)
                self.assertIn("docs/plans/03_PROJECT_EXECUTION_TRACKER.md", readme)
                self.assertIn("docs/surveys/README.md", readme)
                self.assertIn(canonical_research_plan, status)
                self.assertIn("docs/plans/03_PROJECT_EXECUTION_TRACKER.md", status)
                for label in ("State:", "Evidence", "Boundary", "Blocker:", "Next:"):
                    self.assertIn(label, status)
                for relative in STANDARD_PROJECT_DIRS:
                    self.assertTrue((root / relative).is_dir(), f"{project_id}/{relative}")

    def test_registry_exactly_matches_platform_directories(self) -> None:
        registered = {item["id"]: item for item in self.registry["platforms"]}
        actual = {path.name for path in (ROOT / "platforms").iterdir() if path.is_dir()}
        self.assertEqual(actual, set(registered))
        self.assertEqual(
            {path.name for path in (ROOT / "platforms").iterdir() if path.is_file()},
            {"README.md"},
        )
        for platform_id, entry in registered.items():
            root = ROOT / entry["path"]
            self.assertEqual(
                metadata_value(root / "PLATFORM.yaml", "platform_id"), platform_id
            )
            self.assertEqual(
                metadata_value(root / "PLATFORM.yaml", "artifact_root"),
                entry["artifact_root"],
            )
            self.assertTrue((root / "README.md").is_file())
            self.assertTrue((root / "STATUS.md").is_file())

    def test_project_document_management_is_uniform(self) -> None:
        for entry in self.registry["projects"]:
            with self.subTest(project=entry["id"]):
                root = ROOT / entry["path"]
                plans = root / "docs/plans"
                plan_names = {path.name for path in plans.glob("*.md")}
                research_plan_names = {
                    name for name in plan_names
                    if re.fullmatch(r"01_RESEARCH_PLAN_V\d{2}\.md", name)
                }
                self.assertEqual(len(research_plan_names), 1)
                self.assertEqual(
                    plan_names,
                    research_plan_names | {
                        "02_PROJECT_MILESTONES.md",
                        "03_PROJECT_EXECUTION_TRACKER.md",
                    },
                )

                research_plan_name = next(iter(research_plan_names))
                research_plan = (plans / research_plan_name).read_text(
                    encoding="utf-8"
                )
                milestones = (plans / "02_PROJECT_MILESTONES.md").read_text(
                    encoding="utf-8"
                )
                tracker = (plans / "03_PROJECT_EXECUTION_TRACKER.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn("02_PROJECT_MILESTONES.md", research_plan)
                self.assertIn("03_PROJECT_EXECUTION_TRACKER.md", research_plan)
                self.assertIn(research_plan_name, milestones)
                self.assertIn("03_PROJECT_EXECUTION_TRACKER.md", milestones)
                self.assertIn(research_plan_name, tracker)
                self.assertIn("02_PROJECT_MILESTONES.md", tracker)

                surveys = root / "docs/surveys"
                survey_index = (surveys / "README.md").read_text(encoding="utf-8")
                for survey in surveys.glob("*.md"):
                    if survey.name != "README.md":
                        self.assertIn(survey.name, survey_index)
                        survey_content = survey.read_text(encoding="utf-8")
                        if "현재 권위 상태: `CURRENT`" in survey_content:
                            self.assertIn(survey.name, research_plan)

    def test_canonical_implementation_and_pipelines_have_one_owner(self) -> None:
        self.assertTrue(
            (ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/semantics.py").is_file()
        )
        self.assertTrue(
            (ROOT / "projects/04-guardsynth-coc/src/guard_synth/source_aware_generator.py").is_file()
        )
        self.assertTrue(
            (ROOT / "platforms/eblc-bcv/pipelines/cli/core_smt_compile/run.py").is_file()
        )
        self.assertTrue(
            (ROOT / "projects/04-guardsynth-coc/pipelines/cli/source_aware_generate/run.py").is_file()
        )
        self.assertFalse(
            (ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/source_aware_generator.py").exists()
        )

    def test_eblc_research_project_does_not_duplicate_platform(self) -> None:
        research = ROOT / "projects/05-eblc-language-verification"
        platform = ROOT / "platforms/eblc-bcv"
        guardsynth = ROOT / "projects/04-guardsynth-coc"

        research_metadata = (research / "PROJECT.yaml").read_text(encoding="utf-8")
        platform_metadata = (platform / "PLATFORM.yaml").read_text(encoding="utf-8")
        guardsynth_metadata = (guardsynth / "PROJECT.yaml").read_text(encoding="utf-8")

        self.assertIn("  - eblc-bcv", research_metadata)
        self.assertIn("  - eblc-language-verification", platform_metadata)
        self.assertIn("  - eblc-language-verification", guardsynth_metadata)
        self.assertFalse((research / "src/guard_synth_eblc").exists())
        self.assertTrue((platform / "src/guard_synth_eblc").is_dir())
        self.assertIn(
            "projects/05-eblc-language-verification/",
            (platform / "README.md").read_text(encoding="utf-8"),
        )

    def test_legacy_roots_contain_only_compatibility_shims(self) -> None:
        allowed = {
            "src/README.md",
            "src/__init__.py",
            "src/guard_synth/__init__.py",
            "src/guard_synth_eblc/__init__.py",
            "cli/pipelines/guardsynth/__init__.py",
            "cli/pipelines/eblc/__init__.py",
            "experiments/sequential_coc/__init__.py",
            "experiments/contract_micro_world/__init__.py",
            "experiments/alpamayo/__init__.py",
            "experiments/eblc_p0b/__init__.py",
            "experiments/eblc_pilot/__init__.py",
            "experiments/README.md",
        }
        actual: set[str] = set()
        for base in ("src", "cli/pipelines/guardsynth", "cli/pipelines/eblc", "experiments"):
            for path in (ROOT / base).rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts:
                    actual.add(path.relative_to(ROOT).as_posix())
        self.assertEqual(actual, allowed)

    def test_every_root_namespace_is_registered_or_tool_owned(self) -> None:
        registered = {item["path"] for item in self.registry["repository_namespaces"]}
        registered.update(item["path"] for item in self.registry["hidden_namespaces"])
        tool_owned = {".git", ".pytest_cache", ".ruff_cache"}
        actual = {path.name for path in ROOT.iterdir() if path.is_dir()}
        self.assertEqual(actual, registered | tool_owned)

    def test_shared_infrastructure_children_have_consumers(self) -> None:
        for namespace in ("data", "runtime", "third_party"):
            catalog = json.loads(
                (ROOT / namespace / "OWNERSHIP.json").read_text(encoding="utf-8")
            )
            entries = catalog["entries"]
            self.assertTrue(entries)
            for entry in entries:
                with self.subTest(namespace=namespace, path=entry["path"]):
                    self.assertTrue((ROOT / namespace / entry["path"]).exists())
                    self.assertTrue(entry["consumers"])

    def test_root_docs_and_tests_are_repository_only(self) -> None:
        docs_files = {
            path.relative_to(ROOT / "docs").as_posix()
            for path in (ROOT / "docs").rglob("*") if path.is_file()
        }
        self.assertTrue(docs_files)
        self.assertTrue(all(path == "README.md" or path.startswith("architecture/") for path in docs_files))
        test_sources = {
            path.relative_to(ROOT / "tests").as_posix()
            for path in (ROOT / "tests").rglob("*.py")
            if "__pycache__" not in path.parts
        }
        self.assertEqual(
            test_sources,
            {"__init__.py", "structure/__init__.py", "structure/test_project_layout.py",
             "structure/test_checkpoint_naming_exception.py"},
        )

    def test_portal_is_owned_by_apps(self) -> None:
        portal = ROOT / "apps/research_portal"
        registered = {item["id"]: item for item in self.registry["applications"]}
        self.assertEqual(set(registered), {"research-portal", "guardsynth-studio"})
        self.assertEqual(registered["guardsynth-studio"]["path"], "apps/guardsynth_studio")
        self.assertEqual(registered["guardsynth-studio"]["owner_project"], "guardsynth-coc")
        self.assertTrue((ROOT / registered["guardsynth-studio"]["path"] / "README.md").is_file())
        self.assertEqual(registered["research-portal"]["path"], "apps/research_portal")
        self.assertEqual(registered["research-portal"]["owner_project"], "guardsynth-coc")
        self.assertTrue((portal / "run.py").is_file())
        self.assertTrue((portal / "README.md").is_file())
        self.assertTrue((portal / "site/papers.html").is_file())
        self.assertFalse((ROOT / "project_portal").exists())

    def test_new_artifact_namespaces_exist(self) -> None:
        for group, entries in (
            ("projects", self.registry["projects"]),
            ("platforms", self.registry["platforms"]),
        ):
            for entry in entries:
                root = ROOT / "artifacts" / group / entry["id"]
                for classification in ("public", "restricted", "intermediate"):
                    self.assertTrue((root / classification).is_dir())

    def test_every_legacy_artifact_family_has_one_owner(self) -> None:
        catalog = json.loads(
            (ROOT / "artifacts/LEGACY_OWNERSHIP.json").read_text(encoding="utf-8")
        )
        self.assertTrue(catalog["immutable"])
        for classification in ("results/public", "results/restricted", "intermediate"):
            for path in (ROOT / "artifacts" / classification).iterdir():
                if not path.is_dir():
                    continue
                matches = [
                    rule for rule in catalog["rules"]
                    if rule["class"] == classification and fnmatch(path.name, rule["pattern"])
                ]
                self.assertEqual(len(matches), 1, f"{classification}/{path.name}")

    def test_superpowers_has_scratch_promotion_and_archive_separation(self) -> None:
        policy = ROOT / "governance/superpowers/README.md"
        self.assertTrue(policy.is_file())
        text = policy.read_text(encoding="utf-8")
        self.assertIn(".superpowers/sdd/<work-id>/", text)
        self.assertIn("Promotion", text)
        self.assertTrue((ROOT / "archive/agent-history/superpowers").is_dir())
        self.assertFalse((ROOT / "docs/internal/superpowers").exists())
        promotions = json.loads(
            (ROOT / "governance/superpowers/PROMOTIONS.json").read_text(encoding="utf-8")
        )
        self.assertIn("promotions", promotions)
        self.assertTrue((ROOT / "governance/superpowers/PROMOTION_CHECKLIST.md").is_file())
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", ".superpowers/sdd/example/task.md"],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(ignored.returncode, 0)

    def test_worktree_directory_is_registry_only(self) -> None:
        local = ROOT / ".worktrees"
        self.assertEqual(
            {path.name for path in local.iterdir()}, {"README.md", "registry.json"}
        )
        registry = json.loads((local / "registry.json").read_text(encoding="utf-8"))
        self.assertIn("worktrees", registry)
        listing = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        self.assertNotIn(f"worktree {local}/", listing)
        self.assertIn("../guardsynth-cc-worktrees/", (ROOT / "governance/worktrees/README.md").read_text(encoding="utf-8"))

    def test_deprecated_mixed_roots_are_absent(self) -> None:
        self.assertFalse((ROOT / "research").exists())
        self.assertFalse((ROOT / "experiments/results").exists())
        self.assertFalse((ROOT / "docs/superpowers").exists())

    def test_canonical_documentation_links_resolve(self) -> None:
        self.assertEqual(broken_markdown_links(ROOT), ())

    def test_maintained_files_follow_naming_codex(self) -> None:
        self.assertGreater(len(maintained_files()), 300)
        self.assertGreater(len(maintained_directories()), 100)
        self.assertEqual(naming_violations(), ())

    def test_completed_portal_naming_exception_is_immutable_and_scoped(self) -> None:
        exceptions = json.loads(
            (ROOT / "docs/architecture/NAMING_EXCEPTIONS.json").read_text(encoding="utf-8")
        )["exceptions"]
        pattern = (
            "artifacts/projects/guardsynth-coc/restricted/"
            "guardsynth-project-portal-001/portal-2026-08-12-v6/reviews/*.html"
        )
        self.assertEqual(
            [item["pattern"] for item in exceptions if item["pattern"] == pattern],
            [pattern],
        )
        matched = {
            path.relative_to(ROOT).as_posix()
            for path in maintained_files()
            if fnmatch(path.relative_to(ROOT).as_posix(), pattern)
        }
        self.assertEqual(
            matched,
            {
                pattern.replace("*.html", "association-01.html"),
                pattern.replace("*.html", "association-02.html"),
                pattern.replace("*.html", "association-03.html"),
                pattern.replace("*.html", "association-04.html"),
                pattern.replace("*.html", "association-05.html"),
                pattern.replace("*.html", "evidence-review.html"),
                pattern.replace("*.html", "expert-training.html"),
                pattern.replace("*.html", "image-review.html"),
            },
        )

    def test_migration_map_points_to_canonical_locations(self) -> None:
        migration = json.loads(
            (ROOT / "docs/architecture/MIGRATION_MAP.json").read_text(encoding="utf-8")
        )
        self.assertEqual(migration["migration_id"], "PROJECT-STRUCTURE-V3-2026-08-12")
        for old_path, new_path in migration["mappings"].items():
            with self.subTest(old_path=old_path):
                if "*" not in new_path:
                    self.assertTrue((ROOT / new_path).exists(), new_path)

    def test_public_manifest_has_only_existing_paths(self) -> None:
        entries = (ROOT / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
        paths = [line.split("  ./", 1)[1] for line in entries if "  ./" in line]
        self.assertTrue(paths)
        self.assertTrue(all((ROOT / path).is_file() for path in paths))
        self.assertFalse(any(path.startswith("research/") for path in paths))
        self.assertFalse(any(path.startswith("experiments/results/") for path in paths))


if __name__ == "__main__":
    unittest.main()
