"""Validated, read-only projection of canonical repository research state."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Mapping


class ProjectionError(ValueError):
    """Raised when canonical project metadata and documents disagree."""


_MILESTONE_ID = re.compile(r"(?:[A-Z]{2}-)?M\d{2}")
_STATUS_LINE = re.compile(r"^- ([^:]+):\s*(.*)$")


def _read(path: Path, overrides: Mapping[Path, str]) -> str:
    resolved = path.resolve()
    for candidate, value in overrides.items():
        if candidate.resolve() == resolved:
            return value
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectionError(f"cannot read canonical source: {path}") from exc


def _simple_yaml(text: str) -> dict:
    values: dict[str, object] = {}
    current_list: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list:
            cast = values.setdefault(current_list, [])
            if isinstance(cast, list):
                cast.append(line[4:].strip())
            continue
        if line.startswith(" ") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip()
        current_list = key if not value else None
        if not value:
            values[key] = []
        elif value == "[]":
            values[key] = []
        elif re.fullmatch(r"\d+", value):
            values[key] = int(value)
        else:
            values[key] = value.strip("'\"")
    return values


def _owned_path(root: Path, owner: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ProjectionError(f"missing {label}")
    candidate = (owner / relative).resolve()
    try:
        candidate.relative_to(owner.resolve())
    except ValueError as exc:
        raise ProjectionError(f"{label} leaves its owner: {relative}") from exc
    if not candidate.is_file():
        raise ProjectionError(f"missing {label}: {relative}")
    return candidate


def _status_data(text: str) -> dict:
    fields: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = _STATUS_LINE.match(line)
        if match:
            key = match.group(1).strip().lower().replace(" ", "_")
            fields.setdefault(key, []).append(match.group(2).strip())
    state_values = fields.get("state", [])
    raw_state = state_values[0].strip("`") if state_values else "UNKNOWN"
    return {"fields": fields, "raw_state": raw_state, "evidence": fields.get("evidence", []), "next": fields.get("next", [])}


def _milestone_ledger(text: str) -> dict[str, dict[str, str]]:
    milestones: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or not _MILESTONE_ID.fullmatch(cells[0]):
            continue
        status_cell = next((cell for cell in cells[1:] if "`" in cell), "")
        match = re.search(r"`([A-Z_]+)`(?:\(([^)]+)\))?", status_cell)
        if not match:
            raise ProjectionError(f"milestone {cells[0]} has no exact status token")
        milestones[cells[0]] = {
            "state": match.group(1),
            "qualifier": (match.group(2) or "").strip(),
        }
    return milestones


def _active_milestone(tracker: str) -> str:
    explicit = re.search(r"현재 마일스톤 완료 상태:\s*`((?:[A-Z]{2}-)?M\d{2})\s+[A-Z_]+`", tracker)
    if explicit:
        return explicit.group(1)
    section = re.search(r"## 1\. 현재 단일 작업\s+(.*?)(?=\n## |\Z)", tracker, re.DOTALL)
    if section:
        match = re.search(r"`((?:[A-Z]{2}-)?M\d{2})`", section.group(1))
        if match:
            return match.group(1)
    raise ProjectionError("execution tracker does not declare one active milestone")


def _decision_records(owner: Path, overrides: Mapping[Path, str]) -> list[dict]:
    records = []
    decision_root = owner / "docs/decisions"
    if not decision_root.is_dir():
        return records
    for path in sorted(decision_root.glob("*.md")):
        text = _read(path, overrides)
        title = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        status = re.search(r"^-\s*(?:상태|Status):\s*`?([^`\n]+)", text, re.MULTILINE | re.IGNORECASE)
        decision_id = re.search(r"^-\s*(?:결정 ID|Decision ID):\s*`?([^`\n]+)", text, re.MULTILINE | re.IGNORECASE)
        records.append({
            "decision_id": decision_id.group(1).strip() if decision_id else path.stem,
            "title": title.group(1).strip() if title else path.stem,
            "status": status.group(1).strip() if status else "UNRECORDED",
            "content_hash": hashlib.sha256(text.encode()).hexdigest(),
        })
    return records


def _project(root: Path, registry_entry: dict, overrides: Mapping[Path, str]) -> dict:
    owner = (root / registry_entry["path"]).resolve()
    metadata_path = owner / "PROJECT.yaml"
    metadata = _simple_yaml(_read(metadata_path, overrides))
    if metadata.get("project_id") != registry_entry["id"]:
        raise ProjectionError(f"project id mismatch at {metadata_path}")
    if metadata.get("project_order") != registry_entry["order"]:
        raise ProjectionError(f"project order mismatch at {metadata_path}")

    plan_candidates = list((owner / "docs/plans").glob("01_RESEARCH_PLAN_V[0-9][0-9].md"))
    if len(plan_candidates) != 1:
        raise ProjectionError(f"expected exactly one research plan under {owner}")

    status_path = _owned_path(root, owner, metadata.get("canonical_status"), "canonical_status")
    plan_path = _owned_path(root, owner, metadata.get("canonical_research_plan"), "canonical_research_plan")
    milestones_path = _owned_path(root, owner, metadata.get("canonical_milestones"), "canonical_milestones")
    tracker_path = _owned_path(root, owner, metadata.get("canonical_execution_tracker"), "canonical_execution_tracker")
    survey_path = _owned_path(root, owner, metadata.get("survey_index"), "survey_index")
    paper_root = (owner / str(metadata.get("paper_root", "paper"))).resolve()
    if not paper_root.is_dir() or owner not in paper_root.parents:
        raise ProjectionError(f"invalid paper root for {registry_entry['id']}")
    readme_path = owner / "README.md"
    result_index_path = owner / "results/RESULT_INDEX.md"
    for source in (readme_path, result_index_path):
        if not source.is_file():
            raise ProjectionError(f"missing canonical source: {source}")

    source_paths = {
        "metadata": metadata_path,
        "readme": readme_path,
        "status": status_path,
        "research_plan": plan_path,
        "milestones": milestones_path,
        "execution_tracker": tracker_path,
        "survey_index": survey_path,
        "result_index": result_index_path,
    }
    source_text = {key: _read(path, overrides) for key, path in source_paths.items()}
    status = _status_data(source_text["status"])
    milestones = _milestone_ledger(source_text["milestones"])
    active = _active_milestone(source_text["execution_tracker"])
    if active not in milestones:
        raise ProjectionError(f"active milestone {active} is absent from the milestone ledger")

    sources = {key: path.relative_to(root).as_posix() for key, path in source_paths.items()}
    source_hashes = {
        key: hashlib.sha256(text.encode()).hexdigest() for key, text in source_text.items()
    }
    gate = milestones[active]
    return {
        "project_id": registry_entry["id"],
        "order": registry_entry["order"],
        "title": metadata.get("title", registry_entry["id"]),
        "research_question": metadata.get("research_question", ""),
        "raw_state": status["raw_state"],
        "active_milestone_id": active,
        "gate_state": gate["state"],
        "gate_qualifier": gate["qualifier"],
        "status": status,
        "dependencies": metadata.get("dependencies", []),
        "decisions": _decision_records(owner, overrides),
        "canonical_sources": sources,
        "canonical_source_hashes": source_hashes,
    }


def _platform(root: Path, entry: dict, overrides: Mapping[Path, str]) -> dict:
    owner = (root / entry["path"]).resolve()
    metadata_path = owner / "PLATFORM.yaml"
    metadata = _simple_yaml(_read(metadata_path, overrides))
    if metadata.get("platform_id") != entry["id"]:
        raise ProjectionError(f"platform id mismatch at {metadata_path}")
    status_path = _owned_path(root, owner, metadata.get("canonical_status"), "canonical_status")
    return {
        "platform_id": entry["id"],
        "title": metadata.get("title", entry["id"]),
        "raw_state": metadata.get("status", "unknown"),
        "consumers": metadata.get("consumers", []),
        "canonical_sources": {
            "metadata": metadata_path.relative_to(root).as_posix(),
            "readme": (owner / "README.md").relative_to(root).as_posix(),
            "status": status_path.relative_to(root).as_posix(),
        },
    }


def load_portfolio(
    root: Path,
    *,
    document_overrides: Mapping[Path, str] | None = None,
) -> dict:
    """Load registry-ordered projects and platforms from canonical documents."""
    root = root.resolve()
    overrides = document_overrides or {}
    try:
        registry = json.loads((root / "PROJECT_REGISTRY.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectionError("cannot load PROJECT_REGISTRY.json") from exc
    projects = sorted(registry.get("projects", []), key=lambda item: item["order"])
    return {
        "projects": [_project(root, entry, overrides) for entry in projects],
        "platforms": [_platform(root, entry, overrides) for entry in registry.get("platforms", [])],
    }
