#!/usr/bin/env python3
"""Inventory sequential CoC events without exporting source reasoning text."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())))

from experiments.sequential_coc.contract_ir import ContractEvent, EventWindow


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
REASONING_PATH = ROOT / "data/baseline/coc_nusc/reasoning/ood_reasoning.parquet"
EGOMOTION_DIR = ROOT / "data/baseline/coc_nusc/labels/egomotion"
RESULTS_ROOT = ROOT / "artifacts/results"
PAPER_ROOT = ROOT / "projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit"
OUTPUT_DIR = RESULTS_ROOT / "restricted/sequential-coc-consistency-v1"
INVENTORY_PATH = OUTPUT_DIR / "inventory.json"
NATURAL_WINDOWS_PATH = OUTPUT_DIR / "natural-windows.jsonl"

LEXICAL_PATTERNS = {
    "stop": r"\bstop\b",
    "yield": r"\byield\w*\b",
    "accelerate": r"\baccelerat\w*\b",
    "decelerate": r"\bdecelerat\w*\b",
    "pedestrian_or_crosswalk": r"\b(?:pedestrian|crosswalk)\b",
}
TRANSITION_SOURCE_PATTERN = r"\b(?:stop|yield\w*)\b"
TRANSITION_TARGET_PATTERN = r"\b(?:accelerat\w*|proceed\w*)\b"
AUTOMATED_CANDIDATE_STATUS = "AUTOMATED_CANDIDATE_NOT_GROUND_TRUTH"
RAW_EVENT_KEYS = frozenset(
    {
        "scene_id",
        "timestamp_us",
        "source_text",
        "source_text_sha256",
        "original_position",
        "duplicate_occurrence",
    }
)
RAW_WINDOW_KEYS = frozenset({"window_id", "cluster_id", "events"})
SHA256_HEX_PATTERN = re.compile(r"[0-9a-f]{64}")


def _require_scene_id(scene_id: str) -> str:
    if not isinstance(scene_id, str) or not scene_id:
        raise ValueError("scene_id must be a non-empty string")
    return scene_id


def _source_text_hash(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def _require_exact_keys(value: Mapping[str, object], expected: frozenset[str], name: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValueError(f"{name} must contain exactly {sorted(expected)!r}")


def _require_nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


@dataclass(frozen=True, slots=True)
class RawEvent:
    """Private source-text event retained only for restricted extraction outputs."""

    scene_id: str
    timestamp_us: int
    source_text: str
    original_position: int = 0
    duplicate_occurrence: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "scene_id", _require_scene_id(self.scene_id))
        object.__setattr__(self, "timestamp_us", _require_nonnegative_int("timestamp_us", self.timestamp_us))
        if not isinstance(self.source_text, str):
            raise TypeError("source_text must be a string")
        object.__setattr__(
            self, "original_position", _require_nonnegative_int("original_position", self.original_position)
        )
        object.__setattr__(
            self,
            "duplicate_occurrence",
            _require_nonnegative_int("duplicate_occurrence", self.duplicate_occurrence),
        )

    @property
    def source_text_sha256(self) -> str:
        return _source_text_hash(self.source_text)

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_id": self.scene_id,
            "timestamp_us": self.timestamp_us,
            "source_text": self.source_text,
            "source_text_sha256": self.source_text_sha256,
            "original_position": self.original_position,
            "duplicate_occurrence": self.duplicate_occurrence,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "RawEvent":
        if not isinstance(value, Mapping):
            raise TypeError("RawEvent input must be a mapping")
        _require_exact_keys(value, RAW_EVENT_KEYS, "RawEvent")
        source_text_hash = value["source_text_sha256"]
        if not isinstance(source_text_hash, str) or SHA256_HEX_PATTERN.fullmatch(source_text_hash) is None:
            raise ValueError("source_text_sha256 must be a lowercase SHA-256 hex digest")
        event = cls(
            scene_id=value["scene_id"],  # type: ignore[arg-type]
            timestamp_us=value["timestamp_us"],  # type: ignore[arg-type]
            source_text=value["source_text"],  # type: ignore[arg-type]
            original_position=value["original_position"],  # type: ignore[arg-type]
            duplicate_occurrence=value["duplicate_occurrence"],  # type: ignore[arg-type]
        )
        if source_text_hash != event.source_text_sha256:
            raise ValueError("source_text_sha256 does not match source_text")
        return event


@dataclass(frozen=True, slots=True)
class RawEventWindow:
    """Private window representation; never convert source text into an Action here."""

    window_id: str
    cluster_id: str
    events: tuple[RawEvent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.window_id, str) or SHA256_HEX_PATTERN.fullmatch(self.window_id) is None:
            raise ValueError("window_id must be a lowercase SHA-256 hex digest")
        object.__setattr__(self, "cluster_id", _require_scene_id(self.cluster_id))
        events = tuple(self.events)
        if not 2 <= len(events) <= 4:
            raise ValueError("raw windows must contain two through four events")
        if any(not isinstance(event, RawEvent) for event in events):
            raise TypeError("events must contain RawEvent values")
        if any(event.scene_id != self.cluster_id for event in events):
            raise ValueError("raw window events must match cluster_id")
        ordering = [(event.timestamp_us, event.original_position) for event in events]
        if ordering != sorted(ordering):
            raise ValueError("raw events must be timestamp/original-position sorted")
        expected_id = _anonymous_window_id(
            self.cluster_id, [(event.original_position, event) for event in events]
        )
        if self.window_id != expected_id:
            raise ValueError("window_id does not match raw window content")
        object.__setattr__(self, "events", events)

    def to_dict(self) -> dict[str, object]:
        return {
            "window_id": self.window_id,
            "cluster_id": self.cluster_id,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "RawEventWindow":
        if not isinstance(value, Mapping):
            raise TypeError("RawEventWindow input must be a mapping")
        _require_exact_keys(value, RAW_WINDOW_KEYS, "RawEventWindow")
        raw_events = value["events"]
        if not isinstance(raw_events, list):
            raise TypeError("events must be a list")
        return cls(
            window_id=value["window_id"],  # type: ignore[arg-type]
            cluster_id=value["cluster_id"],  # type: ignore[arg-type]
            events=tuple(RawEvent.from_dict(item) for item in raw_events),  # type: ignore[arg-type]
        )


def _anonymous_window_id(
    scene_id: str,
    ordered_entries: Sequence[tuple[int, ContractEvent | RawEvent]],
) -> str:
    """Hash scene identity and ordered source identities without exposing either."""
    duplicate_counts: dict[tuple[int, str], int] = {}
    payload_events: list[dict[str, object]] = []
    for original_position, event in ordered_entries:
        if isinstance(event, RawEvent):
            source_hash = event.source_text_sha256
            phase_index = 0
            occurrence = event.duplicate_occurrence
        else:
            source_hash = _source_text_hash(
                event.source_text
                if event.source_text is not None
                else json.dumps(event.to_dict(include_text=False), sort_keys=True, separators=(",", ":"))
            )
            phase_index = event.phase_index
            duplicate_key = (event.timestamp_us, source_hash)
            occurrence = duplicate_counts.get(duplicate_key, 0)
            duplicate_counts[duplicate_key] = occurrence + 1
        payload_events.append(
            {
                "timestamp_us": event.timestamp_us,
                "phase_index": phase_index,
                "source_text_sha256": source_hash,
                "duplicate_occurrence": occurrence,
                "original_position": original_position,
            }
        )
    canonical = json.dumps(
        {"scene_id": scene_id, "events": payload_events},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_event_windows(
    scene_id: str, events: list[ContractEvent], max_followups: int = 3
) -> list[EventWindow]:
    """Build overlapping, within-scene windows from compiled contract events."""
    if max_followups < 1:
        raise ValueError("max_followups must be at least one")
    _require_scene_id(scene_id)
    ordered = sorted(
        enumerate(events),
        key=lambda item: (item[1].timestamp_us, item[1].phase_index, item[0]),
    )
    ordered_events = [event for _, event in ordered]
    if any(event.scene_id != scene_id for event in ordered_events):
        raise ValueError("events must belong to scene_id")
    windows: list[EventWindow] = []
    for start in range(len(ordered_events) - 1):
        window_events = tuple(ordered_events[start : start + max_followups + 1])
        window_id = _anonymous_window_id(scene_id, ordered[start : start + max_followups + 1])
        windows.append(EventWindow(window_id, scene_id, window_events))
    return windows


def load_local_trajectory_raw_events(
    path: Path = REASONING_PATH, egomotion_dir: Path = EGOMOTION_DIR
) -> dict[str, list[RawEvent]]:
    """Load private source events for the local trajectory scene subset only."""
    frame = pd.read_parquet(path, columns=["events"])
    selected_scene_ids = local_egomotion_scene_ids(egomotion_dir)
    raw_scenes: dict[str, list[RawEvent]] = {}
    for scene_id, raw_events in frame["events"].items():
        scene_id = str(scene_id)
        if scene_id not in selected_scene_ids:
            continue
        raw_scenes[scene_id] = [
            RawEvent(
                scene_id=scene_id,
                timestamp_us=int(raw_event["event_start_timestamp"]),
                source_text=_event_text(raw_event),
                original_position=position,
            )
            for position, raw_event in enumerate(json.loads(raw_events))
        ]
    return raw_scenes


def build_raw_event_windows(
    scene_events: Mapping[str, Sequence[RawEvent]], max_followups: int = 3
) -> list[RawEventWindow]:
    """Build restricted windows using the same within-scene boundaries as the public IR."""
    if max_followups < 1:
        raise ValueError("max_followups must be at least one")
    windows: list[RawEventWindow] = []
    for scene_id in sorted(scene_events):
        _require_scene_id(scene_id)
        events = scene_events[scene_id]
        if any(event.scene_id != scene_id for event in events):
            raise ValueError("raw events must belong to their scene mapping key")
        ordered = sorted(
            events, key=lambda event: (event.timestamp_us, event.original_position)
        )
        duplicate_counts: dict[tuple[int, str], int] = {}
        normalized_events: list[RawEvent] = []
        for event in ordered:
            duplicate_key = (event.timestamp_us, event.source_text_sha256)
            occurrence = duplicate_counts.get(duplicate_key, 0)
            duplicate_counts[duplicate_key] = occurrence + 1
            normalized_events.append(replace(event, duplicate_occurrence=occurrence))
        for start in range(len(ordered) - 1):
            selected = normalized_events[start : start + max_followups + 1]
            windows.append(
                RawEventWindow(
                    window_id=_anonymous_window_id(
                        scene_id, [(event.original_position, event) for event in selected]
                    ),
                    cluster_id=scene_id,
                    events=tuple(selected),
                )
            )
    return windows


def _window_source_text(event: ContractEvent | RawEvent) -> str:
    return event.source_text or ""


def screen_transition_candidates(
    windows: Iterable[EventWindow | RawEventWindow],
) -> dict[str, list[str]]:
    """Screen immediate source/target text pairs; this is not a ground-truth label."""
    source = re.compile(TRANSITION_SOURCE_PATTERN, re.IGNORECASE)
    target = re.compile(TRANSITION_TARGET_PATTERN, re.IGNORECASE)
    candidate_window_ids: list[str] = []
    candidate_cluster_ids: list[str] = []
    for window in windows:
        left, right = window.events[:2]
        if source.search(_window_source_text(left)) and target.search(_window_source_text(right)):
            candidate_window_ids.append(window.window_id)
            if window.cluster_id not in candidate_cluster_ids:
                candidate_cluster_ids.append(window.cluster_id)
    return {
        "candidate_window_ids": candidate_window_ids,
        "candidate_cluster_ids": candidate_cluster_ids,
    }


def write_natural_windows(
    windows: Iterable[RawEventWindow], path: Path = NATURAL_WINDOWS_PATH
) -> None:
    """Write private raw source windows in a restricted JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    with path.open("w", encoding="utf-8") as output:
        for window in windows:
            output.write(json.dumps(window.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    path.chmod(0o600)


def read_natural_windows(path: Path = NATURAL_WINDOWS_PATH) -> list[RawEventWindow]:
    """Read restricted raw windows for private downstream compilation only."""
    return [
        RawEventWindow.from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def load_reasoning_events(path: Path) -> dict[str, list[dict]]:
    """Load and timestamp-sort event dictionaries by scene ID."""
    frame = pd.read_parquet(path, columns=["events"])
    return {
        str(scene_id): sorted(
            json.loads(raw_events),
            key=lambda event: int(event["event_start_timestamp"]),
        )
        for scene_id, raw_events in frame["events"].items()
    }


def local_egomotion_scene_ids(directory: Path) -> set[str]:
    """Return scene IDs backed by local egomotion parquet files."""
    suffix = ".egomotion.parquet"
    return {
        path.name.removesuffix(suffix)
        for path in directory.glob(f"*{suffix}")
        if path.is_file()
    }


def _counts(scene_events: Iterable[list[dict]]) -> dict[str, int]:
    groups = list(scene_events)
    event_count = sum(len(events) for events in groups)
    return {
        "scene_count": len(groups),
        "event_count": event_count,
        "scenes_with_two_or_more": sum(len(events) >= 2 for events in groups),
        "adjacent_pair_count": sum(max(0, len(events) - 1) for events in groups),
    }


def _event_text(event: dict) -> str:
    return str(event.get("cot", ""))


def _lexical_counts(scene_events: Iterable[list[dict]]) -> dict[str, int]:
    events = [event for group in scene_events for event in group]
    return {
        name: sum(re.search(pattern, _event_text(event), re.IGNORECASE) is not None for event in events)
        for name, pattern in LEXICAL_PATTERNS.items()
    }


def _transition_counts(scene_events: dict[str, list[dict]]) -> dict[str, object]:
    source = re.compile(TRANSITION_SOURCE_PATTERN, re.IGNORECASE)
    target = re.compile(TRANSITION_TARGET_PATTERN, re.IGNORECASE)
    pair_count = 0
    scene_count = 0
    for group in scene_events.values():
        matches = sum(
            source.search(_event_text(left)) is not None
            and target.search(_event_text(right)) is not None
            for left, right in zip(group, group[1:])
        )
        pair_count += matches
        scene_count += matches > 0
    return {
        "source_pattern": TRANSITION_SOURCE_PATTERN,
        "target_pattern": TRANSITION_TARGET_PATTERN,
        "pair_count": pair_count,
        "scene_count": scene_count,
        "candidate_status": AUTOMATED_CANDIDATE_STATUS,
        "prior_count_status": "PRIOR_COUNT_NOT_REPRODUCIBLE",
        "prior_pair_count": 21,
        "prior_scene_count": 16,
    }


def build_inventory(events: dict[str, list[dict]], ego_scene_ids: set[str]) -> dict:
    """Return count-only inventories for all labels and the local trajectory subset."""
    trajectory_subset = {
        scene_id: events[scene_id]
        for scene_id in sorted(set(events).intersection(ego_scene_ids))
    }
    return {
        "all_reasoning": _counts(events.values()),
        "trajectory_subset": _counts(trajectory_subset.values()),
        "trajectory_subset_lexical": _lexical_counts(trajectory_subset.values()),
        "trajectory_subset_transition_selector": _transition_counts(trajectory_subset),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _aggregate_checkpoint(root: Path, files: Iterable[Path]) -> dict[str, object]:
    selected = sorted(
        (path for path in files if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    digest = hashlib.sha256()
    for path in selected:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return {"file_count": len(selected), "aggregate_sha256": digest.hexdigest()}


def _checkpoint_inventory() -> dict[str, object]:
    results_files = (
        path
        for path in RESULTS_ROOT.rglob("*")
        if path.is_file() and OUTPUT_DIR not in path.parents
    )
    return {
        "reasoning_parquet_sha256": _sha256_file(REASONING_PATH),
        "local_egomotion_parquet": _aggregate_checkpoint(
            EGOMOTION_DIR, EGOMOTION_DIR.glob("*.parquet")
        ),
        "existing_results_tree": _aggregate_checkpoint(RESULTS_ROOT, results_files),
        "kiee_paper_tree": _aggregate_checkpoint(PAPER_ROOT, PAPER_ROOT.rglob("*")),
    }


def write_inventory(inventory: dict, path: Path = INVENTORY_PATH) -> None:
    """Write a count-and-hash-only inventory with restricted permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    payload = {"protected_input_checkpoints": _checkpoint_inventory(), **inventory}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> None:
    parser = argparse.ArgumentParser()
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--inventory-only", action="store_true")
    command.add_argument("--write-windows", action="store_true")
    args = parser.parse_args()
    if args.inventory_only:
        events = load_reasoning_events(REASONING_PATH)
        inventory = build_inventory(events, local_egomotion_scene_ids(EGOMOTION_DIR))
        write_inventory(inventory)
        print(json.dumps(inventory, indent=2, sort_keys=True))
        return

    raw_scenes = load_local_trajectory_raw_events()
    windows = build_raw_event_windows(raw_scenes)
    candidates = screen_transition_candidates(windows)
    write_natural_windows(windows)
    events = load_reasoning_events(REASONING_PATH)
    inventory = build_inventory(events, local_egomotion_scene_ids(EGOMOTION_DIR))
    write_inventory(inventory)
    print(
        json.dumps(
            {
                "window_count": len(windows),
                "multi_event_scene_count": len({window.cluster_id for window in windows}),
                "adjacent_relationship_count": sum(max(0, len(events) - 1) for events in raw_scenes.values()),
                "candidate_window_count": len(candidates["candidate_window_ids"]),
                "candidate_scene_count": len(candidates["candidate_cluster_ids"]),
                "candidate_status": AUTOMATED_CANDIDATE_STATUS,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
