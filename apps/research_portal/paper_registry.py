"""Owner-scoped paper manifest loader for the research portal."""

from __future__ import annotations

import json
from pathlib import Path


class PaperRegistryError(ValueError):
    pass


def _owned_source(root: Path, owner: Path, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise PaperRegistryError("paper source_path must be a non-empty string")
    source = (owner / value).resolve()
    try:
        source.relative_to(owner.resolve())
    except ValueError as exc:
        raise PaperRegistryError(f"paper source leaves project owner: {value}") from exc
    if not source.is_file():
        raise PaperRegistryError(f"paper source does not exist: {value}")
    return source.relative_to(root).as_posix()


def load_paper_registry(root: Path) -> dict:
    root = root.resolve()
    registry = json.loads((root / "PROJECT_REGISTRY.json").read_text(encoding="utf-8"))
    projects: list[dict] = []
    papers: list[dict] = []
    seen: set[str] = set()
    for entry in sorted(registry.get("projects", []), key=lambda item: item["order"]):
        owner = (root / entry["path"]).resolve()
        manifest_path = owner / "paper/PAPER_MANIFEST.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PaperRegistryError(f"cannot load {manifest_path}") from exc
        if manifest.get("project_id") != entry["id"]:
            raise PaperRegistryError(f"paper manifest owner mismatch: {manifest_path}")
        project_record = {
            "project_id": entry["id"],
            "paper_status": entry.get("paper_status", "UNKNOWN"),
            "manifest_path": manifest_path.relative_to(root).as_posix(),
        }
        projects.append(project_record)
        for raw in manifest.get("papers", []):
            paper_id = raw.get("paper_id")
            if not isinstance(paper_id, str) or paper_id in seen:
                raise PaperRegistryError(f"missing or duplicate paper_id: {paper_id}")
            seen.add(paper_id)
            papers.append(
                {
                    "paper_id": paper_id,
                    "project_id": entry["id"],
                    "title": str(raw.get("title", paper_id)),
                    "status": str(raw.get("status", entry.get("paper_status", "UNKNOWN"))),
                    "media_type": str(raw.get("media_type", "application/pdf")),
                    "source_path": _owned_source(root, owner, raw.get("source_path")),
                }
            )
    return {"projects": projects, "papers": papers}
