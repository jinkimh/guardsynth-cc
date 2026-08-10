"""Read-only checks for canonical project paths and local Markdown links."""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import unquote


_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def documentation_files(root: Path) -> tuple[Path, ...]:
    files = [root / "README.md", root / "PROJECT_STRUCTURE.md"]
    for base in ("docs", "src", "cli", "experiments", "artifacts"):
        for path in (root / base).rglob("*.md"):
            relative = path.relative_to(root).as_posix()
            if "docs/internal" in relative or "docs/notes" in relative:
                continue
            if base in {"src", "cli", "experiments", "artifacts"} and path.name != "README.md":
                continue
            files.append(path)
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
