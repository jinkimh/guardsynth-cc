#!/usr/bin/env python3
"""Regenerate the integrity manifest for access-controlled experiment results."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
RESTRICTED_RESULTS = ROOT / "artifacts/results/restricted"
MANIFEST = RESTRICTED_RESULTS / "MANIFEST.sha256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    files = sorted(
        path
        for path in RESTRICTED_RESULTS.rglob("*")
        if path.is_file() and path != MANIFEST
    )
    lines = [
        f"{sha256(path)}  ./{path.relative_to(RESTRICTED_RESULTS).as_posix()}"
        for path in files
    ]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    MANIFEST.chmod(0o600)
    print(f"updated {MANIFEST.relative_to(ROOT)} with {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
