"""Stable repository paths for CLI entry points.

Pipeline modules may be regrouped by domain without changing their root
calculation.  A missing marker fails closed instead of silently selecting a
parent directory.
"""

from __future__ import annotations

from pathlib import Path


def project_root(start: str | Path) -> Path:
    candidate = Path(start).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (
            (directory / "PROJECT_STRUCTURE.md").is_file()
            and (directory / "src").is_dir()
            and (directory / "cli").is_dir()
        ):
            return directory
    raise RuntimeError(f"project root markers not found from {start}")
