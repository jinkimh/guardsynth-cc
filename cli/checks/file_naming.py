"""Audit maintained paths against the File Naming Codex."""

from __future__ import annotations

import argparse
from fnmatch import fnmatch
import json
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cli.project_paths import project_root


ROOT = project_root(__file__)
MAINTAINED_ROOTS = (
    "projects", "platforms", "apps", "governance", "docs", "cli", "shared",
    "tests", "src", "experiments",
)
NEW_ARTIFACT_ROOTS = ("artifacts/projects", "artifacts/platforms")
EXCLUDED_PARTS = {
    ".git", ".pytest_cache", ".ruff_cache", ".matplotlib-cache", ".texlive-cache",
    ".texlive-local", "__pycache__", "node_modules",
}
ROOT_FILES = {
    ".gitignore", "AGENTS.md", "MANIFEST.sha256", "PROJECTS.md",
    "PROJECT_REGISTRY.json", "PROJECT_STRUCTURE.md", "README.md",
    "requirements-local.txt",
}
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")
SAFE_DIRECTORY = re.compile(r"^[a-z0-9._-]+$")
PROJECT_DIRECTORY = re.compile(r"^\d{2}-[a-z][a-z0-9-]*$")
PYTHON_FILE = re.compile(r"^(?:__init__|[a-z][a-z0-9_]*)\.py$")
UPPER_DOCUMENT = re.compile(r"^[A-Z0-9]+(?:_[A-Z0-9]+)*\.md$")
DATED_DOCUMENT = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
HIERARCHICAL_DOCUMENT = re.compile(
    r"^(?P<hierarchy>\d{2})_[A-Z0-9]+(?:_[A-Z0-9]+)*\.md$"
)
HTML_FILE = re.compile(r"^[a-z][a-z0-9_]*\.html$")
JSON_FILE = re.compile(
    r"^(?:[a-z][a-z0-9_]*(?:\.schema)?|[A-Z][A-Z0-9_]*|fontlist-v\d+)\.json$"
)
LOWER_GENERIC_FILE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
GENERIC_RESERVED_FILES = {".gitkeep", "Makefile", "PROJECT.yaml", "PLATFORM.yaml"}
PROJECT_PLAN_DOCUMENTS = {
    "01_RESEARCH_PLAN_VNN.md": re.compile(r"^01_RESEARCH_PLAN_V\d{2}\.md$"),
    "02_PROJECT_MILESTONES.md": re.compile(r"^02_PROJECT_MILESTONES\.md$"),
    "03_PROJECT_EXECUTION_TRACKER.md": re.compile(
        r"^03_PROJECT_EXECUTION_TRACKER\.md$"
    ),
}
PROJECT_DOCUMENT_ROLES = {
    "requirements": "REQUIREMENTS",
    "designs": "DESIGN",
    "decisions": "DECISION",
    "reports": "REPORT",
}
FORBIDDEN_DOCUMENT_TOKENS = {"FINAL", "LATEST", "NEW", "COPY"}
SURVEY_METADATA_FIELDS = (
    "기준 연구계획:",
    "조사 기준일:",
    "검색 데이터베이스:",
    "검색 범위:",
    "포함 기준:",
    "제외 기준:",
    "현재 권위 상태:",
    "직접 지원하는 연구 질문:",
    "직접 지원하는 baseline 또는 방법 결정:",
    "후속 문서:",
)


def _exception_patterns() -> tuple[str, ...]:
    payload = json.loads(
        (ROOT / "docs/architecture/NAMING_EXCEPTIONS.json").read_text(encoding="utf-8")
    )
    return tuple(item["pattern"] for item in payload["exceptions"])


def _controlled_document_sets() -> dict[str, dict[str, re.Pattern[str]]]:
    registry = json.loads((ROOT / "PROJECT_REGISTRY.json").read_text(encoding="utf-8"))
    return {
        f"{item['path']}/docs/plans": PROJECT_PLAN_DOCUMENTS
        for item in registry["projects"]
    }


def _registered_projects() -> tuple[Path, ...]:
    registry = json.loads((ROOT / "PROJECT_REGISTRY.json").read_text(encoding="utf-8"))
    return tuple(ROOT / item["path"] for item in registry["projects"])


def _project_document_role(path: Path) -> str | None:
    relative = path.relative_to(ROOT)
    if len(relative.parts) < 5 or relative.parts[0] != "projects":
        return None
    if relative.parts[2] != "docs":
        return None
    return PROJECT_DOCUMENT_ROLES.get(relative.parts[3])


def _document_has_role(path: Path, role: str) -> bool:
    if DATED_DOCUMENT.fullmatch(path.name):
        return path.stem.endswith(f"-{role.lower()}")
    return role in path.stem.split("_")


def maintained_files() -> tuple[Path, ...]:
    files = [path for path in ROOT.iterdir() if path.is_file()]
    for root_name in (*MAINTAINED_ROOTS, *NEW_ARTIFACT_ROOTS):
        for path in (ROOT / root_name).rglob("*"):
            if path.is_file() and not any(part in EXCLUDED_PARTS for part in path.parts):
                files.append(path)
    return tuple(sorted(set(files)))


def maintained_directories() -> tuple[Path, ...]:
    directories: list[Path] = []
    for root_name in (*MAINTAINED_ROOTS, *NEW_ARTIFACT_ROOTS):
        for path in (ROOT / root_name).rglob("*"):
            if path.is_dir() and not any(part in EXCLUDED_PARTS for part in path.parts):
                directories.append(path)
    return tuple(sorted(set(directories)))


def violations() -> tuple[str, ...]:
    exceptions = _exception_patterns()
    problems: list[str] = []
    for path in maintained_directories():
        relative = path.relative_to(ROOT).as_posix()
        if any(fnmatch(relative, pattern) for pattern in exceptions):
            continue
        if not SAFE_DIRECTORY.fullmatch(path.name):
            problems.append(f"UNSAFE_DIRECTORY_COMPONENT:{relative}")
        elif path.parent == ROOT / "projects" and not PROJECT_DIRECTORY.fullmatch(path.name):
            problems.append(f"PROJECT_DIRECTORY_NOT_ORDERED:{relative}")
    for path in maintained_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.parent == ROOT:
            if path.name not in ROOT_FILES:
                problems.append(f"UNREGISTERED_ROOT_FILE:{relative}")
            continue
        if any(fnmatch(relative, pattern) for pattern in exceptions):
            continue
        if not SAFE_COMPONENT.fullmatch(path.name):
            problems.append(f"UNSAFE_COMPONENT:{relative}")
            continue
        if path.name.endswith((".orig", ".bak", "~")):
            problems.append(f"BACKUP_FILE_IN_MAINTAINED_TREE:{relative}")
            continue
        if path.suffix == ".py" and not PYTHON_FILE.fullmatch(path.name):
            problems.append(f"PYTHON_NOT_SNAKE_CASE:{relative}")
        elif path.suffix == ".md" and not (
            UPPER_DOCUMENT.fullmatch(path.name) or DATED_DOCUMENT.fullmatch(path.name)
        ):
            problems.append(f"DOCUMENT_NOT_CANONICAL:{relative}")
        elif path.suffix == ".md" and re.search(r"_V\d\.md$", path.name):
            problems.append(f"DOCUMENT_VERSION_NOT_TWO_DIGITS:{relative}")
        elif path.suffix == ".md" and re.match(r"^\d+_", path.name):
            match = HIERARCHICAL_DOCUMENT.fullmatch(path.name)
            if match is None or match.group("hierarchy") == "00":
                problems.append(f"DOCUMENT_HIERARCHY_NOT_TWO_DIGITS:{relative}")
        if path.suffix == ".md" and (
            set(path.stem.upper().split("_")) & FORBIDDEN_DOCUMENT_TOKENS
        ):
            problems.append(f"DOCUMENT_FORBIDDEN_STATUS_TOKEN:{relative}")
        role = _project_document_role(path)
        if path.suffix == ".md" and role and not _document_has_role(path, role):
            problems.append(f"PROJECT_DOCUMENT_ROLE_MISSING:{role}:{relative}")
        survey_tokens = path.stem.split("_")
        if path.suffix == ".md" and path.parent.name == "surveys" and (
            ("SURVEY" in survey_tokens and "NOTES" not in survey_tokens)
            or path.stem.endswith("-survey")
        ):
            content = path.read_text(encoding="utf-8")
            missing_fields = tuple(
                field for field in SURVEY_METADATA_FIELDS if field not in content
            )
            if missing_fields:
                problems.append(
                    f"SURVEY_METADATA_MISSING:{relative}:"
                    f"fields={','.join(missing_fields)}"
                )
        elif path.suffix == ".html" and not HTML_FILE.fullmatch(path.name):
            problems.append(f"HTML_NOT_SNAKE_CASE:{relative}")
        elif path.suffix == ".json" and not JSON_FILE.fullmatch(path.name):
            problems.append(f"JSON_NOT_CANONICAL:{relative}")
        elif path.suffix not in {".py", ".md", ".html", ".json"} and not (
            path.name in GENERIC_RESERVED_FILES or LOWER_GENERIC_FILE.fullmatch(path.name)
        ):
            problems.append(f"GENERIC_FILE_NOT_CANONICAL:{relative}")
    for directory, expected_documents in _controlled_document_sets().items():
        actual_names = tuple(sorted(path.name for path in (ROOT / directory).glob("*.md")))
        counts = {
            label: sum(pattern.fullmatch(name) is not None for name in actual_names)
            for label, pattern in expected_documents.items()
        }
        if len(actual_names) != len(expected_documents) or any(
            count != 1 for count in counts.values()
        ):
            problems.append(
                f"CONTROLLED_DOCUMENT_ORDER_MISMATCH:{directory}:"
                f"expected={','.join(expected_documents)}:actual={','.join(actual_names)}"
            )
    for project_root in _registered_projects():
        surveys = project_root / "docs/surveys"
        survey_index = surveys / "README.md"
        if not survey_index.is_file():
            problems.append(
                f"SURVEY_INDEX_MISSING:{survey_index.relative_to(ROOT).as_posix()}"
            )
            continue
        index_content = survey_index.read_text(encoding="utf-8")
        numbered = sorted(
            path for path in surveys.glob("[0-9][0-9]_*.md") if path.is_file()
        )
        prefixes = [int(path.name[:2]) for path in numbered]
        if prefixes and prefixes != list(range(1, len(prefixes) + 1)):
            problems.append(
                f"SURVEY_CONTROL_SEQUENCE_MISMATCH:"
                f"{surveys.relative_to(ROOT).as_posix()}:"
                f"actual={','.join(f'{number:02d}' for number in prefixes)}"
            )
        research_plans = tuple(
            (project_root / "docs/plans").glob("01_RESEARCH_PLAN_V[0-9][0-9].md")
        )
        plan_content = (
            research_plans[0].read_text(encoding="utf-8")
            if len(research_plans) == 1 else ""
        )
        for survey in surveys.glob("*.md"):
            if survey.name == "README.md":
                continue
            relative = survey.relative_to(ROOT).as_posix()
            if survey.name not in index_content:
                problems.append(f"SURVEY_NOT_INDEXED:{relative}")
            content = survey.read_text(encoding="utf-8")
            if "현재 권위 상태: `CURRENT`" in content and survey.name not in plan_content:
                problems.append(f"CURRENT_SURVEY_NOT_IN_RESEARCH_PLAN:{relative}")
            if "현재 권위 상태: `SUPERSEDED`" in content and not re.search(
                r"\[[^]]+\]\([^)]+\.md(?:#[^)]+)?\)", content
            ):
                problems.append(f"SUPERSEDED_SURVEY_WITHOUT_REPLACEMENT:{relative}")
    return tuple(problems)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print a machine-readable result")
    args = parser.parse_args()
    problems = violations()
    if args.json:
        print(json.dumps({
            "checked_files": len(maintained_files()),
            "checked_directories": len(maintained_directories()),
            "violations": problems,
        }, indent=2))
    elif problems:
        print("\n".join(problems))
    else:
        print(
            f"PASS: {len(maintained_files())} files and "
            f"{len(maintained_directories())} directories satisfy naming policy"
        )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
