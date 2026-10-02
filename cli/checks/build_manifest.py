"""Build the public workspace SHA-256 manifest under Structure Codex v3."""

from __future__ import annotations

import argparse
from fnmatch import fnmatch
import hashlib
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cli.project_paths import project_root


ROOT = project_root(__file__)
OUTPUT = ROOT / "MANIFEST.sha256"
EXCLUDED_PREFIXES = (
    ".git/",
    ".agents/",
    ".codex/",
    ".ruff_cache/",
    ".superpowers/",
    ".worktrees/",
    "archive/handoff/packages/",
    "archive/installers/",
    "artifacts/results/restricted/",
    "data/restricted/",
    "projects/01-safety-constrained-coc/experiments/alpamayo/",
    "projects/01-safety-constrained-coc/experiments/vlm_guard_learning/",
    "papers/",
    "runtime/",
    "third_party/",
    "portal_exec.md",
)
EXCLUDED_PATTERNS = (
    "artifacts/projects/*/restricted/*",
    "artifacts/platforms/*/restricted/*",
)
MODEL_ARTIFACT_SUFFIXES = (
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pth",
    ".onnx",
    ".gguf",
)
SMALL_VLM_ROOT = "artifacts/results/public/small-vlm-guard-v0/"
SMALL_VLM_EXCLUDED_PARTS = {"adapter", "processor"}
EXCLUDED_PARTS = {
    ".git", ".cache", "__pycache__", ".pytest_cache", ".matplotlib-cache",
    ".texlive-cache", ".texlive-local", "texlive-cache",
}


def included(path: Path) -> bool:
    relative_path = path.relative_to(ROOT)
    relative = relative_path.as_posix()
    if relative == OUTPUT.name or any(relative.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    if any(fnmatch(relative, pattern) for pattern in EXCLUDED_PATTERNS):
        return False
    if relative.endswith(MODEL_ARTIFACT_SUFFIXES) or (
        path.suffix == ".bin"
        and path.name.startswith(("pytorch_model", "adapter_model"))
    ):
        return False
    if relative.startswith(SMALL_VLM_ROOT) and any(
        part in SMALL_VLM_EXCLUDED_PARTS for part in relative_path.parts
    ):
        return False
    return not any(
        part in EXCLUDED_PARTS or part.startswith(".venv")
        for part in relative_path.parts
    )


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def build() -> list[str]:
    files = sorted(path for path in ROOT.rglob("*") if path.is_file() and included(path))
    return [f"{digest(path)}  ./{path.relative_to(ROOT).as_posix()}" for path in files]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = "\n".join(build()) + "\n"
    if args.check:
        return 0 if OUTPUT.is_file() and OUTPUT.read_text(encoding="utf-8") == generated else 1
    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"wrote {len(generated.splitlines())} entries to {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
