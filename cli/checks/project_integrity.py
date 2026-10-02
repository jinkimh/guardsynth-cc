"""Read-only checks for canonical project paths and local Markdown links."""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import unquote


_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def documentation_files(root: Path) -> tuple[Path, ...]:
    files = [
        root / "README.md",
        root / "PROJECT_STRUCTURE.md",
        root / "PROJECTS.md",
        root / "AGENTS.md",
    ]
    files.extend((root / "docs/architecture").glob("*.md"))
    files.extend((root / "governance").glob("*/README.md"))
    files.extend((root / "projects").glob("*/README.md"))
    files.extend((root / "projects").glob("*/STATUS.md"))
    files.extend((root / "projects").glob("*/results/RESULT_INDEX.md"))
    files.extend((root / "platforms").glob("*/README.md"))
    files.extend((root / "platforms").glob("*/STATUS.md"))
    files.extend((root / "platforms").glob("*/results/RESULT_INDEX.md"))
    for relative in (
        "apps/research_portal/README.md",
        "archive/README.md",
        "cli/README.md",
        "data/README.md",
        "experiments/README.md",
        "platforms/README.md",
        "projects/README.md",
        "runtime/README.md",
        "src/README.md",
        "tests/README.md",
        "third_party/README.md",
    ):
        files.append(root / relative)
    return tuple(sorted(set(path for path in files if path.is_file())))


def broken_markdown_links(root: Path) -> tuple[dict[str, str], ...]:
    broken: list[dict[str, str]] = []
    for source in documentation_files(root):
        text = source.read_text(encoding="utf-8")
        for raw in _LINK.findall(text):
            original = raw.strip()
            if " " in original and not original.startswith("<"):
                continue
            target = original.strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "urn:")):
                continue
            if "/" not in target and "." not in target:
                continue
            target = unquote(target)
            target = re.sub(r":\d+$", "", target)
            resolved = Path(target) if Path(target).is_absolute() else (source.parent / target)
            if not resolved.resolve().exists():
                broken.append({
                    "source": source.relative_to(root).as_posix(),
                    "target": raw,
                    "resolved": resolved.resolve().as_posix(),
                })
    return tuple(broken)
