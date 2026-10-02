"""Build and optionally serve the local GuardSynth research portal."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
from http.cookies import SimpleCookie
from datetime import date
from functools import partial
import hashlib
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any
from urllib.parse import urlsplit

from apps.research_portal.artifact_registry import ArtifactRegistry, ArtifactRegistryError
from apps.research_portal.paper_registry import load_paper_registry
from apps.research_portal.projection import load_portfolio
from apps.research_portal.review_backend import BackendError, ReviewBackend
from apps.research_portal.review_store import ReviewStore
from apps.research_portal.security import (
    SecurityError,
    LoginRateLimiter,
    SessionStore,
    security_headers,
    validate_auth_config,
    validate_loopback_request,
    validate_route_segment,
    verify_secret,
)
from cli.project_paths import project_root


ROOT = project_root(__file__)
SITE = Path(__file__).resolve().parent / "site"
MILESTONES = ROOT / "projects/04-guardsynth-coc/docs/plans/02_PROJECT_MILESTONES.md"
TRACKER = ROOT / "projects/04-guardsynth-coc/docs/plans/03_PROJECT_EXECUTION_TRACKER.md"
PROJECT_REGISTRY = ROOT / "PROJECT_REGISTRY.json"
STRUCTURE_CODEX = ROOT / "docs/architecture/PROJECT_STRUCTURE_CODEX.md"
M16_REQUIREMENTS = ROOT / (
    "projects/04-guardsynth-coc/docs/requirements/M16_EXPERT_PILOT_REQUIREMENTS.md"
)
M16_ACQUISITION_REQUIREMENTS = ROOT / (
    "projects/04-guardsynth-coc/docs/requirements/"
    "M16_SOURCE_COMPLETE_SCENE_ACQUISITION_REQUIREMENTS_V01.md"
)
M13_RESULT = ROOT / (
    "artifacts/results/restricted/guardsynth-sim24-batch-001/"
    "alpamayo-terminal-batch-2026-08-12-v1/BATCH_RESULT.json"
)
M16_PREFLIGHT = ROOT / (
    "artifacts/results/restricted/guardsynth-expert-pilot-preflight-001/"
    "m16-preflight-2026-08-12-v4/PILOT_PREFLIGHT.json"
)
REVIEW_ASSET_REGISTRY = Path(__file__).resolve().parent / "review_asset_registry.json"
PROJECT_DOCUMENT_OVERRIDES: dict[str, dict[str, Path]] = {}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _project_paths(registry_item: dict[str, Any]) -> dict[str, Path]:
    project_root = ROOT / registry_item["path"]
    defaults = {
        "root": project_root,
        "metadata": project_root / "PROJECT.yaml",
        "readme": project_root / "README.md",
        "status": project_root / "STATUS.md",
        "plan": next((project_root / "docs/plans").glob("01_RESEARCH_PLAN_V*.md")),
        "milestones": project_root / "docs/plans/02_PROJECT_MILESTONES.md",
        "tracker": project_root / "docs/plans/03_PROJECT_EXECUTION_TRACKER.md",
    }
    defaults.update(PROJECT_DOCUMENT_OVERRIDES.get(registry_item["id"], {}))
    return defaults


def _simple_yaml(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([a-z_]+):\s*(.+)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"')
    return values


def _clean_markdown(text: str) -> str:
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[`*_#]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _readme_overview(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    body = re.split(r"^# .+$", text, maxsplit=1, flags=re.MULTILINE)[-1]
    paragraphs = []
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block or block.startswith(("- ", "#")):
            continue
        paragraphs.append(_clean_markdown(block))
        if len(paragraphs) == 2:
            break
    if not paragraphs:
        raise ValueError(f"project overview missing: {path}")
    return " ".join(paragraphs)


def _status_data(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for label, key in (
        ("State", "state"),
        ("Evidence", "evidence"),
        ("Boundary", "boundary"),
        ("Blocker", "blocker"),
        ("Next", "next"),
        ("Current gate", "current_gate"),
    ):
        match = re.search(
            rf"^- {re.escape(label)}:\s*(.+?)(?=\n- [A-Z][^:]*:|\n\n|\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if match:
            value = match.group(1)
            if key == "state":
                value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
                result[key] = re.sub(r"\s+", " ", value.strip(" `*#\n"))
            else:
                result[key] = _clean_markdown(value)
    for required in ("state", "evidence", "boundary"):
        if required not in result:
            raise ValueError(f"project status field missing ({required}): {path}")
    result.setdefault("blocker", "기록된 blocker 없음")
    result.setdefault("next", result.get("current_gate", "tracker에서 다음 작업 확인"))
    return result


def _plan_focus(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^##\s+(.+)$", text, re.MULTILINE))
    selected = None
    for index, heading in enumerate(headings):
        if any(label in heading.group(1) for label in ("연구 목적", "연구 질문", "연구 개요")):
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            selected = text[heading.end():end]
            break
    if selected is None:
        return "상세 목표는 권위 연구계획에서 관리합니다."
    cleaned = _clean_markdown(selected)
    return cleaned[:1200] + ("…" if len(cleaned) > 1200 else "")


def _generic_milestones(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or not re.fullmatch(r"(?:[A-Z]{1,3}-)?M\d{2}", cells[0]):
            continue
        if len(cells) == 4:
            milestone_id, title, status, summary = cells
            phase = ""
        elif len(cells) >= 5:
            milestone_id, title, phase, status, summary = cells[:5]
        else:
            continue
        rows.append({
            "id": milestone_id,
            "title": _clean_markdown(title),
            "phase": _clean_markdown(phase),
            "status": _clean_markdown(status),
            "summary": _clean_markdown(summary),
            "tasks": [],
            "done_tasks": 0,
            "task_count": 0,
        })
    by_id = {item["id"]: item for item in rows}
    headings = list(re.finditer(r"^###\s+((?:[A-Z]{1,3}-)?M\d{2})\.\s+(.+)$", text, re.MULTILINE))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section = text[heading.end():end]
        milestone = by_id.get(heading.group(1))
        if not milestone:
            continue
        tasks = [
            {"done": mark.lower() == "x", "text": _clean_markdown(label)}
            for mark, label in re.findall(r"^- \[([ xX])\] (.+)$", section, re.MULTILINE)
        ]
        milestone["tasks"] = tasks
        milestone["done_tasks"] = sum(task["done"] for task in tasks)
        milestone["task_count"] = len(tasks)
    if not rows:
        raise ValueError(f"project milestone ledger has no rows: {path}")
    return rows


def _tracker_task(path: Path, milestones_path: Path, milestones: list[dict[str, Any]]) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    task_section = re.search(
        r"^## 1\. 현재 단일 작업\s*$([\s\S]*?)(?=^## )", text, re.MULTILINE
    )
    task = _clean_markdown(task_section.group(1)) if task_section else ""
    task_id = re.search(r"`((?:[A-Z]{1,3}-)?M\d{2})`", task_section.group(1)) if task_section else None
    active_id = task_id.group(1) if task_id else ""
    if not active_id:
        ledger_text = milestones_path.read_text(encoding="utf-8")
        active = re.search(r"^- 현재 활성 마일스톤: `([^`]+)`", ledger_text, re.MULTILINE)
        active_id = active.group(1) if active else ""
    if not active_id:
        candidate = next(
            (item for item in milestones if _status_class(item["status"]) in ("active", "ready", "blocked", "partial")),
            milestones[-1],
        )
        active_id = candidate["id"]
    if not task:
        status = _status_data(path.parents[2] / "STATUS.md")
        task = status["next"]
    return active_id, task


def _status_class(status: str) -> str:
    value = status.lower()
    for label in ("complete", "blocked", "active", "ready", "partial", "queued"):
        if label in value:
            return label
    return "queued"


def _project_tracking_sync(
    mode: str, paths: dict[str, Path], project_root: Path
) -> dict[str, Any]:
    return {
        "authority": "CANONICAL_DOCUMENTS",
        "mode": mode,
        "sources": [
            paths[key].relative_to(ROOT).as_posix()
            if paths[key].is_relative_to(ROOT) else paths[key].as_posix()
            for key in ("metadata", "readme", "status", "plan", "milestones", "tracker")
        ],
        "project_root": project_root.relative_to(ROOT).as_posix(),
    }


def _research_project_data(
    registry_item: dict[str, Any], review_pages: list[dict[str, Any]], mode: str
) -> dict[str, Any]:
    paths = _project_paths(registry_item)
    metadata = _simple_yaml(paths["metadata"])
    status = _status_data(paths["status"])
    milestones = _generic_milestones(paths["milestones"])
    active_id, current_task = _tracker_task(paths["tracker"], paths["milestones"], milestones)
    active = next((item for item in milestones if item["id"] == active_id), None)
    if active is None:
        raise ValueError(
            f"project tracker active milestone is not in ledger: {registry_item['id']} {active_id}"
        )
    order = int(registry_item["order"])
    return {
        "id": registry_item["id"],
        "order": order,
        "title": metadata.get("title", registry_item["id"]),
        "path": registry_item["path"],
        "overview": _readme_overview(paths["readme"]),
        "goal": metadata.get("research_question", "연구 질문 미기록"),
        "plan_focus": _plan_focus(paths["plan"]),
        "state": status["state"],
        "evidence": status["evidence"],
        "boundary": status["boundary"],
        "blocker": status["blocker"],
        "next": status["next"],
        "current_task": current_task,
        "active_milestone_id": active_id,
        "active_milestone": active,
        "milestones": milestones,
        "review_pages": review_pages,
        "page": f"project_{order:02d}.html",
        "review_page": f"review_{order:02d}.html",
        "paper_status": registry_item.get("paper_status", "UNRECORDED"),
        "artifact_root": registry_item["artifact_root"],
        "tracking_sync": _project_tracking_sync(mode, paths, paths["root"]),
    }


def _research_projects(
    review_pages_by_project: dict[str, list[dict[str, Any]]], mode: str
) -> list[dict[str, Any]]:
    registry = _load(PROJECT_REGISTRY)
    return [
        _research_project_data(
            item, review_pages_by_project.get(item["id"], []), mode
        )
        for item in sorted(registry["projects"], key=lambda value: value["order"])
    ]


def _milestone_data(path: Path | None = None) -> list[dict[str, Any]]:
    text = (path or MILESTONES).read_text(encoding="utf-8")
    summary_rows = {
        item[0]: {
            "id": item[0], "title": item[1].strip(), "phase": item[2].strip(),
            "status": item[3].strip(), "summary": item[4].strip(),
        }
        for item in re.findall(
            r"^\| (M\d{2}) \| ([^|]+?) \| ([^|]+?) \| `([^`]+)`(?:\([^)]*\))? \| ([^|]+?) \|$",
            text,
            re.MULTILINE,
        )
    }
    headings = list(re.finditer(r"^### (M\d{2})\. (.+)$", text, re.MULTILINE))
    for index, heading in enumerate(headings):
        milestone_id = heading.group(1)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section = text[heading.end():end]
        tasks = [
            {"done": mark.lower() == "x", "text": label.strip()}
            for mark, label in re.findall(r"^- \[([ xX])\] (.+)$", section, re.MULTILINE)
        ]
        if milestone_id in summary_rows:
            summary_rows[milestone_id]["tasks"] = tasks
            summary_rows[milestone_id]["done_tasks"] = sum(item["done"] for item in tasks)
            work_package = re.search(r"^- work package: `([^`]+)`", section, re.MULTILINE)
            summary_rows[milestone_id]["work_package"] = (
                work_package.group(1) if work_package else None
            )
    result = [summary_rows[f"M{index:02d}"] for index in range(22)]
    for item in result:
        item.setdefault("tasks", [])
        item.setdefault("done_tasks", 0)
        item["task_count"] = len(item["tasks"])
    return result


def _tracker_metadata(path: Path | None = None) -> dict[str, str]:
    tracker_path = path or TRACKER
    text = tracker_path.read_text(encoding="utf-8")
    fields = {}
    for label, key in (
        ("현재 연구 위치", "research_position"),
        ("현재 활성 작업 ID", "active_work_package"),
        ("현재 전체 판단", "overall_decision"),
    ):
        match = re.search(rf"^- {label}: `([^`]+)`", text, re.MULTILINE)
        if not match:
            raise ValueError(f"tracker field missing: {label}")
        fields[key] = match.group(1)
    regression = re.search(r"maintained (\d+)/(\d+)", text)
    if not regression:
        raise ValueError("tracker regression count is missing")
    fields["maintained_tests_passed"] = regression.group(1)
    fields["maintained_tests_total"] = regression.group(2)
    sub_work = re.search(
        r"^- 현재 하위 work package: \[[^]]+\]\(([^)]+)\)", text, re.MULTILINE
    )
    if not sub_work:
        raise ValueError("tracker current sub work package is missing")
    sub_work_path = (tracker_path.parent / sub_work.group(1)).resolve()
    try:
        fields["current_sub_work_package"] = sub_work_path.relative_to(ROOT).as_posix()
    except ValueError as error:
        raise ValueError("tracker sub work package must remain inside repository") from error
    updated = re.search(r"^- 마지막 갱신일: (\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
    if not updated:
        raise ValueError("tracker last update is missing")
    fields["last_updated"] = updated.group(1)
    return fields


def _repository_structure_data() -> dict[str, Any]:
    registry = _load(PROJECT_REGISTRY)
    presentation = {
        "safety-constrained-coc": (
            "Safety-Constrained CoC",
            "주어진 실행 제약이 목표를 유지하면서 VLM 행동을 개선하는지 평가",
        ),
        "specification-alignment": (
            "Specification Alignment",
            "자연어·구조화·실행 가능 명세 인터페이스의 차이와 정렬을 연구",
        ),
        "sequential-coc-verification": (
            "Sequential CoC Verification",
            "연속 CoC annotation의 상태·시간 일관성을 검증",
        ),
        "guardsynth-coc": (
            "GuardSynth-CoC",
            "CoC·장면·규칙·근거·assurance에서 적용 가능한 제약을 합성",
        ),
        "eblc-language-verification": (
            "EBLC Language Verification",
            "EBLC 언어의 lifecycle 의미와 multi-target lowering을 독립 평가",
        ),
    }
    projects = []
    for item in sorted(registry["projects"], key=lambda value: value["order"]):
        title, responsibility = presentation[item["id"]]
        projects.append({
            **item,
            "title": title,
            "responsibility": responsibility,
            "current": item["id"] == "guardsynth-coc",
        })
    platforms = [
        {
            **item,
            "title": "EBLC/BCV verification platform",
            "responsibility": (
                "재사용 가능한 EBLC representation·Core lowering·runtime·BCV·SMT/Z3 구현"
            ),
        }
        for item in registry["platforms"]
    ]
    return {
        "codex_version": registry["codex_version"],
        "projects": projects,
        "platforms": platforms,
        "applications": registry["applications"],
        "repository_namespaces": registry["repository_namespaces"],
        "rules": [
            "연구 질문별 문서·코드·테스트는 정확히 하나의 numbered project가 소유합니다.",
            "공용 EBLC/BCV/Core/SMT 구현은 projects가 아니라 platforms/eblc-bcv가 소유합니다.",
            "웹 애플리케이션은 apps/, 생성 결과는 owner별 artifacts/ 아래에 둡니다.",
            "legacy root src/tests/experiments는 compatibility shim만 허용합니다.",
        ],
    }


def _numbered_section(text: str, heading: str, next_heading: str) -> list[str]:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## {re.escape(next_heading)}\s*$)",
        text,
        re.MULTILINE,
    )
    if not match:
        raise ValueError(f"document section missing: {heading}")
    return [
        value.strip()
        for value in re.findall(r"^\d+\. (.+)$", match.group(1), re.MULTILINE)
    ]


def _current_work_data(
    milestones: list[dict[str, Any]], tracker: dict[str, str], m16: dict[str, Any]
) -> dict[str, Any]:
    active = next(
        (
            item for item in milestones
            if item.get("work_package") == tracker["active_work_package"]
        ),
        None,
    )
    if active is None:
        raise ValueError(
            "tracker active work package does not map to exactly one milestone section"
        )
    requirements_path = tracker["current_sub_work_package"]
    requirements_file = ROOT / requirements_path
    acquisition_text = requirements_file.read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", acquisition_text, re.MULTILINE)
    if not title:
        raise ValueError("current work requirement title is missing")
    try:
        immediate_tasks = _numbered_section(
            acquisition_text, "다음 태스크 판정", "Prompt"
        )
    except ValueError:
        immediate_tasks = [task["text"] for task in active["tasks"] if not task["done"]]
    if len(immediate_tasks) < 1:
        immediate_tasks = [title.group(1)]
    start_gate: list[str] = []
    after_gate = [task["text"] for task in active["tasks"] if not task["done"]]
    if active["id"] == "M16":
        requirement_text = M16_REQUIREMENTS.read_text(encoding="utf-8")
        start_gate = _numbered_section(requirement_text, "start gate", "성공 gate")
        if len(start_gate) < 5:
            raise ValueError("M16 start gate contract is incomplete")
        after_gate = [
            "reviewer training·calibration",
            "2인 독립 annotation",
            "별도 adjudicator의 불일치 판정",
            "합의도·수정률·작업시간 측정과 main-study power analysis",
        ]
    progress = re.search(r"(\d+)/(\d+)", active["summary"])
    eligible = int(progress.group(1)) if progress else None
    target = int(progress.group(2)) if progress else None
    if active["id"] == "M16":
        eligible = int(m16["eligible_scene_count"])
        target = int(m16["target_scene_count"])
    shortfall = target - eligible if eligible is not None and target is not None else None
    return {
        "milestone_id": active["id"],
        "milestone_title": active["title"],
        "milestone_status": active["status"],
        "work_package": tracker["active_work_package"],
        "immediate_task": title.group(1).removesuffix(" 요구사항"),
        "immediate_tasks": immediate_tasks,
        "relationship": (
            f"{active['id']} {active['title']}이 현재 상위 마일스톤입니다. "
            f"현재 하위 요구사항은 {title.group(1)}이며, 상위 마일스톤을 "
            "시작·완료하기 위해 먼저 닫아야 하는 실행 단위입니다."
        ),
        "eligible_scene_count": eligible,
        "target_scene_count": target,
        "scene_shortfall": shortfall,
        "formal_annotation_allowed": (
            bool(m16["annotation_start_allowed"]) if active["id"] == "M16" else None
        ),
        "start_gate": start_gate,
        "after_scene_gate": after_gate,
        "requirements_path": requirements_path,
    }


def _tracking_sync(mode: str, tracker: dict[str, str]) -> dict[str, Any]:
    def display(path: Path) -> str:
        try:
            return path.relative_to(ROOT).as_posix()
        except ValueError:
            return path.as_posix()

    return {
        "authority": "CANONICAL_DOCUMENTS",
        "mode": mode,
        "last_tracker_update": tracker["last_updated"],
        "sources": [
            display(MILESTONES),
            display(TRACKER),
            tracker["current_sub_work_package"],
            display(PROJECT_REGISTRY),
        ],
    }


def _tracking_snapshot(base_data: dict[str, Any]) -> dict[str, Any]:
    """Reload canonical project-control documents without mutating a run artifact."""
    data = copy.deepcopy(base_data)
    milestones = _milestone_data()
    tracker = _tracker_metadata()
    m16 = _load(M16_PREFLIGHT)
    data["generated_date"] = date.today().isoformat()
    data["tracker"] = tracker
    data["milestones"] = milestones
    data["milestone_status_counts"] = dict(
        Counter(item["status"].split("(", 1)[0] for item in milestones)
    )
    data["repository_structure"] = _repository_structure_data()
    data["current_work"] = _current_work_data(milestones, tracker, m16)
    data["tracking_sync"] = _tracking_sync("LIVE_ON_PAGE_LOAD", tracker)
    return data


def _portfolio_snapshot(base_data: dict[str, Any]) -> dict[str, Any]:
    """Reload every research project's canonical management documents."""
    data = copy.deepcopy(base_data)
    review_pages = {
        project["id"]: project.get("review_pages", [])
        for project in data.get("research_projects", [])
    }
    data["generated_date"] = date.today().isoformat()
    data["research_projects"] = _research_projects(
        review_pages, "LIVE_ON_PAGE_LOAD"
    )
    data["portfolio"] = {
        "project_count": len(data["research_projects"]),
        "milestone_count": sum(
            len(project["milestones"]) for project in data["research_projects"]
        ),
        "review_package_count": sum(
            len(project["review_pages"]) for project in data["research_projects"]
        ),
    }
    data["projection"] = load_portfolio(ROOT)
    data["platforms"] = data["projection"]["platforms"]
    data["paper_registry"] = load_paper_registry(ROOT)
    data["artifact_registry"] = ArtifactRegistry(ROOT).records(include_restricted=False)
    return data


def _review_sources(output_reviews: Path) -> list[dict[str, Any]]:
    config = _load(REVIEW_ASSET_REGISTRY)
    if not isinstance(config, dict) or set(config) != {"schema_version", "entries"} or config["schema_version"] != 1:
        raise ValueError("review asset registry contract is invalid")
    service = ArtifactRegistry(ROOT)
    records = service.records(include_restricted=True)
    pages: list[dict[str, Any]] = []
    entry_fields = {
        "id", "title", "description", "display_classification", "owner_id",
        "artifact_classification", "selector", "asset_label", "output_name",
    }
    for entry in config["entries"]:
        if not isinstance(entry, dict) or set(entry) != entry_fields:
            raise ValueError("review asset registry entry fields are invalid")
        selector = entry["selector"]
        if not isinstance(selector, dict) or len(selector) != 1 or next(iter(selector)) not in {"run_label", "experiment_id"}:
            raise ValueError("review asset registry selector is invalid")
        key, expected = next(iter(selector.items()))
        matches = [
            record for record in records
            if record["owner_id"] == entry["owner_id"]
            and record["classification"] == entry["artifact_classification"]
            and record.get(key) == expected
            and any(asset["label"] == entry["asset_label"] for asset in record["assets"])
        ]
        if not matches:
            raise ValueError(f"registered review asset is missing: {entry['id']}")
        for index, record in enumerate(sorted(matches, key=lambda item: item["run_label"]), start=1):
            asset = next(item for item in record["assets"] if item["label"] == entry["asset_label"])
            source, _ = service.resolve_asset(
                record["artifact_id"], asset["asset_id"], include_restricted=True
            )
            if "{index}" in entry["output_name"]:
                output_name = entry["output_name"].format(index=f"{index:02d}")
                page_id = f"{entry['id']}-{index:02d}"
                title = entry["title"].format(index=index)
            else:
                if len(matches) != 1:
                    raise ValueError(f"review asset selector is not unique: {entry['id']}")
                output_name = entry["output_name"]
                page_id = entry["id"]
                title = entry["title"]
            if not re.fullmatch(r"[a-z][a-z0-9_]*\.html", output_name):
                raise ValueError("review output name is invalid")
            target = output_reviews / output_name
            shutil.copyfile(source, target)
            pages.append({
                "id": page_id,
                "title": title,
                "description": entry["description"],
                "classification": entry["display_classification"],
                "href": f"reviews/{target.name}",
                "project_id": entry["owner_id"],
                "artifact_id": record["artifact_id"],
                "source_manifest_hash": record["manifest_hash"],
                "review_time": record.get("created_at", record["run_label"]),
            })
    return sorted(
        pages,
        key=lambda page: (page["review_time"], page["id"]),
        reverse=True,
    )


def _paper_data(output_downloads: Path, paper_registry: dict[str, Any]) -> list[dict[str, Any]]:
    output_downloads.mkdir()
    registered = {paper["project_id"]: paper for paper in paper_registry["papers"]}
    try:
        paper1 = registered["safety-constrained-coc"]
        paper3 = registered["sequential-coc-verification"]
    except KeyError as exc:
        raise ValueError("the two compatibility papers must be present in project manifests") from exc
    assets = (
        (ROOT / paper1["source_path"], "paper1-safety-constrained-coc.pdf"),
        (ROOT / paper3["source_path"], "paper3-sequential-coc-uppaal-10pages.pdf"),
    )
    for source, name in assets:
        shutil.copyfile(source, output_downloads / name)
    return [
        {
            "id": "paper1",
            "number": "Paper 1",
            "status": "MANUSCRIPT_READY",
            "status_label": "완성 원고 · 익명 심사본",
            "title_ko": "비전-언어 자율주행 모델의 실행 가드 기반 궤적 후보 선택",
            "title_en": (
                "Guard-Aware Trajectory Candidate Selection for Vision-Language "
                "Autonomous Driving: Safety-Constrained Chain-of-Causation"
            ),
            "summary": (
                "행동 목표만 설명하는 CoC에 실행 가드를 결합하고, 동일한 장면·목표·후보에서 "
                "가드만 바꾸는 paired-contract 평가로 VLM이 제약을 실제 선택에 반영하는지 "
                "검토합니다."
            ),
            "contributions": [
                "CoC를 요구사항과 실행 가드를 함께 갖는 Safety-Constrained CoC로 확장",
                "가드 준수 여부만 달라지는 paired-contract benchmark 설계",
                "가드 위반 감소와 안전한 목표 완료·계약 전환을 함께 평가",
            ],
            "highlights": [
                "표준 3-seed 시간 계약 실험에서 requirement-only의 가드 위반 31.9%를 0%로 줄였습니다.",
                "미학습 시간값에서는 성능이 크게 하락해 수치 일반화의 한계를 함께 확인했습니다.",
                "결과는 합성 후보 선택의 학습 가능성을 지지하며 실도로 grounding이나 차량 안전을 입증하지 않습니다.",
            ],
            "download": {
                "label": "논문 PDF 다운로드",
                "href": "downloads/paper1-safety-constrained-coc.pdf",
                "filename": "paper1-safety-constrained-coc.pdf",
                "source": paper1["source_path"],
            },
            "supporting_document": None,
        },
        {
            "id": "paper3",
            "number": "Paper 3",
            "status": "MANUSCRIPT_READY",
            "status_label": "완성 원고 · 익명 심사본",
            "title_ko": "E2E 자율주행 연속 CoC 주석의 상태 일관성 검증",
            "title_en": (
                "Stateful Consistency Verification of Sequential CoC Annotations for "
                "E2E Autonomous Driving: A CoC-Nusc and UPPAAL Study"
            ),
            "summary": (
                "개별 CoC만 검사하면 놓치는 지속 의무, 해제 조건과 행동 순서를 순차 계약으로 "
                "컴파일하고, 상태 기반 Python monitor와 UPPAAL 모델로 일관성을 검사합니다."
            ),
            "contributions": [
                "연속 CoC를 지속 의무·해제·행동 순서를 가진 상태 계약으로 변환",
                "UNKNOWN을 보존하는 3값 근거와 상태 기반 일관성 검사 도입",
                "Python monitor와 UPPAAL의 제한된 변환 일치 및 witness 제시",
            ],
            "highlights": [
                "90개 trajectory-linked multi-CoC 장면에서 309개 인접 window를 추출했습니다.",
                "합성 40개 mutation은 stateful checker가 모두 검출했지만 이는 규칙 fixture coverage입니다.",
                "UPPAAL 7개 canonical fixture의 불일치는 0개였으나 독립적인 의미 검증이나 자연 오류율은 아닙니다.",
            ],
            "download": {
                "label": "논문 PDF 다운로드",
                "href": "downloads/paper3-sequential-coc-uppaal-10pages.pdf",
                "filename": "paper3-sequential-coc-uppaal-10pages.pdf",
                "source": paper3["source_path"],
            },
            "supporting_document": None,
        },
    ]


def _review_cards(projects: list[dict[str, Any]]) -> str:
    """Keep registered questionnaires reachable without client-side rendering."""
    cards = []
    for project in projects:
        for page in project["review_pages"]:
            cards.append(
                '<article class="card">'
                f'<p class="eyebrow">{escape(project["title"])}</p>'
                f'<h2>{escape(page["title"])}</h2>'
                f'<p>{escape(page["description"])}</p>'
                f'<a class="button" href="{escape(page["href"], quote=True)}">'
                '검토 화면 열기</a></article>'
            )
    return "\n".join(cards) or '<p>등록된 검토 화면이 없습니다.</p>'


def build_portal(output_dir: Path) -> dict[str, Any]:
    registry = _load(PROJECT_REGISTRY)
    projection = load_portfolio(ROOT)
    paper_registry = load_paper_registry(ROOT)
    artifact_registry = ArtifactRegistry(ROOT).records(include_restricted=False)
    project_inputs = [
        path
        for item in registry["projects"]
        for path in _project_paths(item).values()
        if path.is_file()
    ]
    required = (
        SITE, PROJECT_REGISTRY, STRUCTURE_CODEX,
        *(ROOT / paper["source_path"] for paper in paper_registry["papers"]),
        *project_inputs,
    )
    if any(not item.exists() for item in required):
        raise FileNotFoundError("project portal input is missing")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    output_dir.mkdir(parents=True)
    for source in SITE.iterdir():
        if source.is_file() and source.name not in (
            "structure.html", "project.html", "project_review.html"
        ):
            shutil.copyfile(source, output_dir / source.name)
    reviews_dir = output_dir / "reviews"
    reviews_dir.mkdir()
    review_pages = _review_sources(reviews_dir)
    papers = _paper_data(output_dir / "downloads", paper_registry)
    review_pages_by_project = {
        item["id"]: [
            page for page in review_pages if page["project_id"] == item["id"]
        ]
        for item in registry["projects"]
    }
    research_projects = _research_projects(
        review_pages_by_project, "BUILD_SNAPSHOT"
    )
    (output_dir / "reviews.html").write_text(
        (SITE / "reviews.html").read_text(encoding="utf-8").replace(
            "{{REVIEW_CARDS}}", _review_cards(research_projects)
        ),
        encoding="utf-8",
    )
    project_template = (SITE / "project.html").read_text(encoding="utf-8")
    review_template = (SITE / "project_review.html").read_text(encoding="utf-8")
    for project in research_projects:
        order = f"{project['order']:02d}"
        (output_dir / project["page"]).write_text(
            project_template.replace("{{PROJECT_ORDER}}", order), encoding="utf-8"
        )
        (output_dir / project["review_page"]).write_text(
            review_template.replace("{{PROJECT_ORDER}}", order), encoding="utf-8"
        )
    data = {
        "portal_version": "guardsynth-project-portal-v0.3",
        "generated_date": date.today().isoformat(),
        "classification": "LICENSE_RESTRICTED_LOCAL_ONLY",
        "papers": papers,
        "paper_registry": paper_registry,
        "artifact_registry": artifact_registry,
        "projection": projection,
        "platforms": projection["platforms"],
        "research_projects": research_projects,
        "portfolio": {
            "project_count": len(research_projects),
            "milestone_count": sum(len(project["milestones"]) for project in research_projects),
            "review_package_count": sum(len(project["review_pages"]) for project in research_projects),
        },
        "source_documents": sorted({
            path.relative_to(ROOT).as_posix()
            for item in registry["projects"]
            for path in _project_paths(item).values()
            if path.is_file() and path.is_relative_to(ROOT)
        }),
    }
    data_text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    (output_dir / "portal-data.js").write_text(
        "window.GUARDSYNTH_PORTAL_DATA = " + data_text + ";\n", encoding="utf-8"
    )
    (output_dir / "PORTAL_DATA.json").write_text(data_text + "\n", encoding="utf-8")
    result = {
        "experiment_id": "GUARDSYNTH-PROJECT-PORTAL-001",
        "run_id": output_dir.name,
        "status": "BUILT",
        "classification": "LICENSE_RESTRICTED_LOCAL_ONLY",
        "project_count": len(research_projects),
        "milestone_count": data["portfolio"]["milestone_count"],
        "review_page_count": len(review_pages),
        "paper_count": len(papers),
        "artifact_run_count": len(artifact_registry),
        "platform_count": len(projection["platforms"]),
        "served_host_policy": "LOOPBACK_ONLY_127.0.0.1",
        "claim_scope": "PROJECT_TRACKING_AND_LOCAL_REVIEW_NOT_RESEARCH_RESULT_OR_VEHICLE_SAFETY",
    }
    (output_dir / "RESULT.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": "GUARDSYNTH-PROJECT-PORTAL-001",
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "input_class": "LICENSE_RESTRICTED_LOCAL_ONLY",
        "served_host_policy": "LOOPBACK_ONLY_127.0.0.1",
        "milestone_count": data["portfolio"]["milestone_count"],
        "review_page_count": len(review_pages),
        "review_assets": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(reviews_dir.iterdir())
            if path.is_file()
        },
        "paper_count": len(papers),
        "paper_download_count": sum(paper["download"] is not None for paper in papers),
        "project_count": len(research_projects),
        "platform_count": len(registry.get("platforms", [])),
        "project_management_sha256": hashlib.sha256(
            "".join(
                hashlib.sha256(path.read_bytes()).hexdigest()
                for item in registry["projects"]
                for path in _project_paths(item).values()
                if path.is_file()
            ).encode()
        ).hexdigest(),
        "project_registry_sha256": hashlib.sha256(PROJECT_REGISTRY.read_bytes()).hexdigest(),
        "claim_scope": "PROJECT_TRACKING_AND_LOCAL_REVIEW_NOT_RESEARCH_RESULT_OR_VEHICLE_SAFETY",
    }
    (output_dir / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "REPORT_KO.md").write_text(
        f"""# GuardSynth-CC 연구 포트폴리오

- 상태: **BUILT**
- 분류: **LICENSE_RESTRICTED_LOCAL_ONLY**
- 연구 포트폴리오: `index.html`
- 우리의 논문: `papers.html`
- 연구영역별 현황: `project_01.html`~`project_05.html`
- 전체 마일스톤 요약: `milestones.html`
- 연구영역별 검토 선택: `review.html`
- 독립 검토 워크스페이스: `review_01.html`~`review_05.html`
- 검토 가이드: `guide.html`
- 연구영역: **{len(research_projects)}개**
- 전체 마일스톤: **{data['portfolio']['milestone_count']}개**
- 통합 검토 화면: **{len(review_pages)}개**
- 논문 포트폴리오: **{len(papers)}편**, PDF **{sum(paper['download'] is not None for paper in papers)}편**
- 관리 원장: 각 project의 `PROJECT.yaml`, `README.md`, `STATUS.md`, 연구계획,
  milestone ledger, execution tracker

## 실행

```bash
python3 -m apps.research_portal.run \\
  --output-dir {output_dir.as_posix()} --serve --port 8765
```

브라우저에서 `http://127.0.0.1:8765/`를 연다. 서버는 저장소 전체가 아니라 선택한 포털
복사본만 loopback에 제공한다. 제한 장면을 공개 네트워크에 배포하지 않는다.

이 포털은 프로젝트 추적과 로컬 검토 인터페이스이며 연구 효과 또는 차량 안전 결과가 아니다.
""",
        encoding="utf-8",
    )
    return manifest


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def end_headers(self) -> None:
        legacy_review = urlsplit(self.path).path.startswith("/reviews/") or getattr(self, "_legacy_asset_response", False)
        for key, value in security_headers(legacy_review=legacy_review).items():
            self.send_header(key, value)
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        super().end_headers()


class _LiveTrackingHandler(_QuietHandler):
    def __init__(
        self,
        *args: object,
        portal_data: dict[str, Any],
        review_backend: ReviewBackend | None = None,
        auth_records: dict[str, str] | None = None,
        auth_roles: dict[str, set[str]] | None = None,
        sessions: SessionStore | None = None,
        login_limiter: LoginRateLimiter | None = None,
        artifact_service: ArtifactRegistry | None = None,
        **kwargs: object,
    ) -> None:
        self.portal_data = portal_data
        self.review_backend = review_backend
        self.auth_records = auth_records or {}
        self.auth_roles = auth_roles or {}
        self.sessions = sessions
        self.login_limiter = login_limiter or LoginRateLimiter()
        self.artifact_service = artifact_service
        super().__init__(*args, **kwargs)

    def _validate_request_boundary(self) -> bool:
        try:
            validate_loopback_request(
                self.headers.get("Host", ""),
                self.headers.get("Origin"),
                self.server.server_port,
            )
            return True
        except SecurityError:
            self.send_error(421, "loopback host/origin required")
            return False

    def _json_response(self, status: int, data: dict[str, Any], *, cookie: str | None = None) -> None:
        body = (json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n").encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self) -> dict[str, Any]:
        if self.headers.get_content_type() != "application/json":
            raise BackendError(415, "application/json is required")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise BackendError(400, "invalid content length") from exc
        if length <= 0 or length > 1_048_576:
            raise BackendError(413, "JSON body size is invalid")
        try:
            value = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as exc:
            raise BackendError(400, "invalid JSON") from exc
        if not isinstance(value, dict):
            raise BackendError(400, "JSON object body is required")
        return value

    def _session(self, *, require_csrf: bool) -> Any:
        if self.sessions is None:
            raise BackendError(404, "review backend is disabled")
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        item = cookie.get("gs_session")
        if item is None:
            raise BackendError(401, "authentication is required")
        try:
            csrf_token = self.headers.get("X-CSRF-Token") if require_csrf else None
            if require_csrf and not csrf_token:
                raise BackendError(403, "csrf token is required")
            return self.sessions.require(
                item.value,
                csrf_token,
            )
        except SecurityError as exc:
            raise BackendError(401, "authentication is required") from exc

    def _artifact_access(self, artifact_id: str) -> tuple[dict[str, Any], bool]:
        if self.artifact_service is None:
            raise BackendError(404, "artifact registry is unavailable")
        try:
            return self.artifact_service.detail(artifact_id, include_restricted=False), False
        except ArtifactRegistryError as public_error:
            if "requires restricted access" not in str(public_error):
                raise BackendError(404, "artifact not found") from public_error
        self._session(require_csrf=False)
        try:
            return self.artifact_service.detail(artifact_id, include_restricted=True), True
        except ArtifactRegistryError as exc:
            raise BackendError(404, "artifact not found") from exc

    def _serve_artifact_asset(self, artifact_id: str, asset_id: str) -> None:
        detail, restricted = self._artifact_access(artifact_id)
        try:
            path, media_type = self.artifact_service.resolve_asset(
                artifact_id, asset_id, include_restricted=restricted
            )
        except ArtifactRegistryError as exc:
            raise BackendError(404, "artifact asset not found") from exc
        body = path.read_bytes()
        self._legacy_asset_response = media_type.startswith("text/html")
        self.send_response(200)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-SHA256", next(item["sha256"] for item in detail["assets"] if item["asset_id"] == asset_id))
        self.send_header("X-Artifact-Classification", detail["classification"])
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._validate_request_boundary():
            return
        resource = urlsplit(self.path).path
        if resource == "/api/artifacts" and self.artifact_service is not None:
            include_restricted = False
            if self.sessions is not None:
                try:
                    self._session(require_csrf=False)
                    include_restricted = True
                except BackendError:
                    pass
            self._json_response(200, {"artifacts": self.artifact_service.records(include_restricted=include_restricted)})
            return
        artifact_match = re.fullmatch(r"/api/artifacts/([^/]+)", resource)
        asset_match = re.fullmatch(r"/assets/([^/]+)/([^/]+)", resource)
        if artifact_match:
            try:
                artifact_id = validate_route_segment(artifact_match.group(1))
                detail, _ = self._artifact_access(artifact_id)
                self._json_response(200, detail)
            except (BackendError, SecurityError) as error:
                status = error.status if isinstance(error, BackendError) else 400
                data = error.data if isinstance(error, BackendError) else {"error": str(error)}
                self._json_response(status, data)
            return
        if asset_match:
            try:
                artifact_id = validate_route_segment(asset_match.group(1))
                asset_id = validate_route_segment(asset_match.group(2))
                self._serve_artifact_asset(artifact_id, asset_id)
            except (BackendError, SecurityError) as error:
                status = error.status if isinstance(error, BackendError) else 400
                data = error.data if isinstance(error, BackendError) else {"error": str(error)}
                self._json_response(status, data)
            return
        if resource.startswith("/api/") and self.review_backend is not None:
            try:
                session = self._session(require_csrf=False)
                result = self.review_backend.dispatch(
                    "GET", resource, actor_id=session.actor_id, body=None
                )
                self._json_response(result.status, result.data)
            except BackendError as error:
                self._json_response(error.status, error.data)
            return
        if resource not in ("/portal-data.js", "/PORTAL_DATA.json"):
            super().do_GET()
            return
        try:
            data = _portfolio_snapshot(self.portal_data)
            text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
            if resource == "/portal-data.js":
                body = ("window.GUARDSYNTH_PORTAL_DATA = " + text + ";\n").encode()
                content_type = "text/javascript; charset=utf-8"
            else:
                body = (text + "\n").encode()
                content_type = "application/json; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as error:
            body = f"canonical tracking document error: {error}\n".encode()
            self.send_response(503)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self) -> None:
        if not self._validate_request_boundary():
            return
        resource = urlsplit(self.path).path
        try:
            payload = self._json_body()
            if resource == "/api/login":
                if self.sessions is None:
                    raise BackendError(404, "review backend is disabled")
                actor_id = payload.get("actor_id")
                secret = payload.get("secret")
                limit_key = self.client_address[0]
                try:
                    self.login_limiter.check(limit_key)
                except SecurityError as exc:
                    raise BackendError(429, "login failed") from exc
                encoded = self.auth_records.get(actor_id, "") if isinstance(actor_id, str) else ""
                if not isinstance(secret, str) or not encoded or not verify_secret(secret, encoded):
                    self.login_limiter.failure(limit_key)
                    raise BackendError(401, "login failed")
                self.login_limiter.success(limit_key)
                session = self.sessions.create(actor_id)
                cookie = f"gs_session={session.session_id}; HttpOnly; SameSite=Strict; Path=/"
                self._json_response(
                    200,
                    {"actor_id": actor_id, "roles": sorted(self.auth_roles.get(actor_id, set())), "csrf_token": session.csrf_token},
                    cookie=cookie,
                )
                return
            if self.review_backend is None:
                raise BackendError(404, "review backend is disabled")
            session = self._session(require_csrf=True)
            result = self.review_backend.dispatch(
                "POST", resource, actor_id=session.actor_id, body=payload
            )
            self._json_response(result.status, result.data)
        except BackendError as error:
            self._json_response(error.status, error.data)


def serve_portal(
    output_dir: Path,
    port: int,
    *,
    review_db: Path | None = None,
    review_owner: str | None = None,
    review_classification: str | None = None,
    auth_file: Path | None = None,
    review_public_export_root: Path | None = None,
) -> None:
    if not output_dir.is_dir() or not (output_dir / "index.html").is_file():
        raise FileNotFoundError("built portal index is missing")
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    portal_data = _load(output_dir / "PORTAL_DATA.json")
    artifact_service = ArtifactRegistry(ROOT)
    store = None
    backend = None
    auth_records: dict[str, str] = {}
    auth_roles: dict[str, set[str]] = {}
    sessions = None
    login_limiter = None
    configured = (review_db, review_owner, review_classification, auth_file)
    if any(configured) and not all(configured):
        raise ValueError("review_db, review_owner, review_classification, and auth_file are required together")
    if review_public_export_root is not None and not all(configured):
        raise ValueError("review public export requires the configured review backend")
    if all(configured):
        store = ReviewStore.open(
            review_db,
            owner_project_id=review_owner,
            classification=review_classification,
        )
        raw_auth = _load(auth_file)
        auth_records, auth_roles = validate_auth_config(raw_auth)
        if review_public_export_root is not None:
            registry = _load(PROJECT_REGISTRY)
            owner = next(
                item for item in registry["projects"] if item["id"] == review_owner
            )
            expected_public_root = (ROOT / owner["artifact_root"] / "public").resolve()
            try:
                review_public_export_root.resolve().relative_to(expected_public_root)
            except ValueError as exc:
                raise ValueError("review public export root must stay under the owner public artifact root") from exc
        backend = ReviewBackend(
            store,
            lead_actor_ids={actor for actor, roles in auth_roles.items() if "RESEARCH_LEAD" in roles},
            public_export_root=review_public_export_root,
        )
        sessions = SessionStore()
        login_limiter = LoginRateLimiter()
    handler = partial(
        _LiveTrackingHandler,
        directory=str(output_dir),
        portal_data=portal_data,
        review_backend=backend,
        auth_records=auth_records,
        auth_roles=auth_roles,
        sessions=sessions,
        login_limiter=login_limiter,
        artifact_service=artifact_service,
    )
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"GuardSynth portal: http://127.0.0.1:{server.server_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if store is not None:
            store.close()


def initialize_review_db(
    path: Path,
    *,
    owner_project_id: str,
    classification: str,
    root: Path = ROOT,
) -> dict[str, str]:
    """Create an empty schema-v2 operations DB only in its registered owner/class root."""
    registry = _load(root / "PROJECT_REGISTRY.json")
    owner = next(
        (item for item in registry.get("projects", []) if item.get("id") == owner_project_id),
        None,
    )
    if owner is None:
        raise ValueError("review database owner must be a registered project")
    if classification not in {"RESTRICTED", "PUBLIC", "INTERMEDIATE"}:
        raise ValueError("review database classification is invalid")
    target = path.resolve()
    class_root = (root / owner["artifact_root"] / classification.lower()).resolve()
    try:
        target.relative_to(class_root)
    except ValueError as exc:
        raise ValueError("review database must stay under its registered owner/classification root") from exc
    if target.suffix != ".sqlite3":
        raise ValueError("review database must use the .sqlite3 suffix")
    store = ReviewStore.create(
        target,
        owner_project_id=owner_project_id,
        classification=classification,
    )
    store.close()
    return {
        "review_db": target.as_posix(),
        "owner_project_id": owner_project_id,
        "classification": classification,
        "schema_version": "2",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--init-review-db", type=Path)
    parser.add_argument("--review-db", type=Path)
    parser.add_argument("--review-owner")
    parser.add_argument("--review-classification")
    parser.add_argument("--auth-file", type=Path)
    parser.add_argument("--review-public-export-root", type=Path)
    args = parser.parse_args()
    if args.init_review_db is not None:
        if args.serve or args.output_dir is not None or args.auth_file is not None:
            parser.error("--init-review-db is a separate initialization operation")
        if not args.review_owner or not args.review_classification:
            parser.error("--init-review-db requires --review-owner and --review-classification")
        result = initialize_review_db(
            args.init_review_db,
            owner_project_id=args.review_owner,
            classification=args.review_classification,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required for build or serve")
    if not args.output_dir.exists():
        result = build_portal(args.output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.serve:
        raise FileExistsError(f"refusing to overwrite existing output: {args.output_dir}")
    if args.serve:
        serve_portal(
            args.output_dir,
            args.port,
            review_db=args.review_db,
            review_owner=args.review_owner,
            review_classification=args.review_classification,
            auth_file=args.auth_file,
            review_public_export_root=args.review_public_export_root,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
