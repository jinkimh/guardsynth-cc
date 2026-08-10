#!/usr/bin/env python3
"""Compile explicit longitudinal instructions into conservative CoC contracts."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Iterable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.sequential_coc.contract_ir import Action, ContractEvent, EventWindow
from experiments.sequential_coc.extract_windows import (
    NATURAL_WINDOWS_PATH,
    RawEvent,
    RawEventWindow,
    read_natural_windows,
)


ORDERED_CONNECTOR = re.compile(r"\b(?:and\s+then|then)\b", re.IGNORECASE)
CONDITION_KEYWORD = re.compile(r"\b(?:until|once|after)\b", re.IGNORECASE)
TRAILING_DESCRIPTION = re.compile(r"[\s,;:.]+$")
IMPERATIVE_PREFIX = re.compile(
    r"(?:^|[.!?;,:]|\b(?:and|but)\b)\s*(?:please|kindly)?\s*$", re.IGNORECASE
)
MODAL_OR_INFINITIVE_PREFIX = re.compile(
    r"\b(?:must|should|shall|will|can|could|may|might|would|"
    r"need(?:s)?\s+to|has\s+to|have\s+to)\s+$",
    re.IGNORECASE,
)
AGENT_WITH_AUXILIARY_PREFIX = re.compile(
    r"\b(?:the\s+)?(?:ego(?:\s+vehicle)?|vehicle|driver|car|we|it)\s+"
    r"(?:is|are|was|were|will|must|should|shall|can|could|would|may|might|"
    r"need(?:s)?\s+to|has\s+to|have\s+to|begin(?:s)?\s+to|continue(?:s)?\s+to)\s+$",
    re.IGNORECASE,
)
AGENT_PREFIX = re.compile(
    r"\b(?:the\s+)?(?:ego(?:\s+vehicle)?|vehicle|driver|car|we|it)\s+$",
    re.IGNORECASE,
)

ACTION_PATTERNS: tuple[tuple[Action, re.Pattern[str]], ...] = (
    (
        Action.STOP_OR_HOLD,
        re.compile(
            r"\b(?:stop(?:s|ping)?|halt(?:s|ed|ing)?|hold(?:s|ing)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Action.YIELD_OR_DECELERATE,
        re.compile(
            r"\b(?:yield(?:s|ed|ing)?|decelerate(?:s|d|ing)?|"
            r"slow(?:s|ed|ing)?\s+down)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Action.ACCELERATE_OR_PROCEED,
        re.compile(
            r"\b(?:accelerate(?:s|d|ing)?|proceed(?:s|ed|ing)?|resume(?:s|d|ing)?|"
            r"mov(?:e|es|ed|ing)\s+forward)\b",
            re.IGNORECASE,
        ),
    ),
    (
        Action.MAINTAIN_SPEED,
        re.compile(
            r"\b(?:maintain(?:s|ed|ing)?|keep(?:s|ing)?)\s+"
            r"(?:the\s+)?(?:current\s+)?speed\b",
            re.IGNORECASE,
        ),
    ),
)

TARGET_PATTERN = re.compile(
    r"\b(?:"
    r"stop\s+sign|yield\s+sign|traffic\s+signal|traffic\s+light|red\s+light|"
    r"oncoming\s+traffic|cross\s+traffic|right[- ]of[- ]way|lead\s+vehicle|"
    r"pedestrian|cyclist|bicyclist|crosswalk|vehicle|traffic|intersection|"
    r"junction|signal|light|obstacle|bus|car|position"
    r")\b",
    re.IGNORECASE,
)

TARGET_REQUIRED = frozenset({Action.STOP_OR_HOLD, Action.YIELD_OR_DECELERATE})


@dataclass(frozen=True, slots=True)
class _ActionMatch:
    action: Action
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class _Condition:
    keyword: str
    description: str
    span: tuple[int, int]


def _validate_source_identity(event_id: str, scene_id: str, timestamp_us: int) -> None:
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("event_id must be a non-empty string")
    if not isinstance(scene_id, str) or not scene_id:
        raise ValueError("scene_id must be a non-empty string")
    if isinstance(timestamp_us, bool) or not isinstance(timestamp_us, int):
        raise TypeError("timestamp_us must be an int")
    if timestamp_us < 0:
        raise ValueError("timestamp_us must be non-negative")


def _clean_description(value: str) -> str:
    return TRAILING_DESCRIPTION.sub("", value.strip())


def _conditions(segment: str) -> list[_Condition]:
    """Extract bounded condition descriptions and their non-directive spans."""
    conditions: list[_Condition] = []
    for keyword_match in CONDITION_KEYWORD.finditer(segment):
        description_start = keyword_match.end()
        remainder = segment[description_start:]
        boundary = re.search(r"[,.;]", remainder)
        description_end = description_start + (boundary.start() if boundary else len(remainder))
        description = _clean_description(segment[description_start:description_end])
        if not description:
            continue
        span_end = description_end + (1 if boundary and boundary.group() == "," else 0)
        conditions.append(
            _Condition(
                keyword=keyword_match.group().lower(),
                description=description,
                span=(keyword_match.start(), span_end),
            )
        )
    return conditions


def _inside_span(start: int, spans: Iterable[tuple[int, int]]) -> bool:
    return any(left <= start < right for left, right in spans)


def _has_positive_action_context(segment: str, match: re.Match[str]) -> bool:
    prefix = segment[: match.start()]
    head = match.group().lower().split()[0]
    if IMPERATIVE_PREFIX.search(prefix):
        return True
    if MODAL_OR_INFINITIVE_PREFIX.search(prefix):
        return True
    if AGENT_WITH_AUXILIARY_PREFIX.search(prefix):
        return True
    finite_or_progressive = head.endswith(("s", "ed", "ing"))
    if finite_or_progressive and AGENT_PREFIX.search(prefix):
        return True
    return False


def _action_matches(segment: str, condition_spans: Iterable[tuple[int, int]]) -> list[_ActionMatch]:
    matches: list[_ActionMatch] = []
    for action, pattern in ACTION_PATTERNS:
        for match in pattern.finditer(segment):
            if _inside_span(match.start(), condition_spans):
                continue
            if not _has_positive_action_context(segment, match):
                continue
            matches.append(_ActionMatch(action, match.start(), match.end()))
    matches.sort(key=lambda item: (item.start, item.end, item.action.value))
    return matches


def _target_in(value: str, *, last: bool = False) -> str | None:
    matches = list(TARGET_PATTERN.finditer(value))
    if not matches:
        return None
    match = matches[-1] if last else matches[0]
    return _clean_description(match.group())


def _local_target(segment: str, actions: list[_ActionMatch], action_index: int) -> str | None:
    action = actions[action_index]
    following_start = (
        actions[action_index + 1].start if action_index + 1 < len(actions) else len(segment)
    )
    target = _target_in(segment[action.end : following_start])
    if target is not None:
        return target
    preceding_end = actions[action_index - 1].end if action_index else 0
    return _target_in(segment[preceding_end : action.start], last=True)


def _split_ordered_segments(text: str) -> list[str]:
    """Split explicit phase connectors while retaining idiomatic ``until then``."""
    segments: list[str] = []
    segment_start = 0
    for connector in ORDERED_CONNECTOR.finditer(text):
        if connector.group().lower() == "then" and re.search(
            r"\buntil\s+$", text[: connector.start()], re.IGNORECASE
        ):
            continue
        segment = text[segment_start : connector.start()].strip()
        if segment:
            segments.append(segment)
        segment_start = connector.end()
    final_segment = text[segment_start:].strip()
    if final_segment:
        segments.append(final_segment)
    return segments


def _phase_event_id(
    scene_id: str,
    timestamp_us: int,
    source_event_id: str,
    source_occurrence: int,
    phase_index: int,
    action: Action,
    action_index: int,
) -> str:
    canonical = json.dumps(
        {
            "scene_id": scene_id,
            "timestamp_us": timestamp_us,
            "source_event_id": source_event_id,
            "source_occurrence": source_occurrence,
            "phase_index": phase_index,
            "action": action.value,
            "action_index": action_index,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _compile_text(
    text: str,
    event_id: str,
    scene_id: str,
    timestamp_us: int,
    *,
    provenance: str,
    source_occurrence: int = 0,
) -> list[ContractEvent]:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    _validate_source_identity(event_id, scene_id, timestamp_us)

    segments = _split_ordered_segments(text)
    phases: list[tuple[str, list[_Condition], list[_ActionMatch]]] = []
    pending_conditions: list[_Condition] = []
    for segment in segments:
        conditions = _conditions(segment)
        actions = _action_matches(segment, (item.span for item in conditions))
        if actions:
            phases.append((segment, pending_conditions + conditions, actions))
            pending_conditions = []
        else:
            pending_conditions.extend(
                item for item in conditions if item.keyword in {"once", "after"}
            )

    compiled: list[ContractEvent] = []
    for phase_index, (segment, conditions, actions) in enumerate(phases):
        ambiguous = len(actions) > 1
        for action_index, action_match in enumerate(actions):
            target = _local_target(segment, actions, action_index)
            if ambiguous:
                parse_status = "UNKNOWN_AMBIGUOUS_ORDER"
            elif action_match.action in TARGET_REQUIRED and target is None:
                parse_status = "UNKNOWN_MISSING_TARGET"
            else:
                parse_status = "PARSED"

            until = next((item.description for item in conditions if item.keyword == "until"), None)
            trigger = next(
                (
                    item.description
                    for item in conditions
                    if item.keyword in {"once", "after"}
                ),
                None,
            )
            compiled.append(
                ContractEvent(
                    scene_id=scene_id,
                    event_id=_phase_event_id(
                        scene_id,
                        timestamp_us,
                        event_id,
                        source_occurrence,
                        phase_index,
                        action_match.action,
                        action_index,
                    ),
                    timestamp_us=timestamp_us,
                    action=action_match.action,
                    trigger=trigger,
                    target=target,
                    satisfaction_known=False,
                    satisfaction_value=False,
                    release_known=False,
                    release_value=False,
                    phase_index=phase_index,
                    provenance=provenance,
                    parse_status=parse_status,
                    source_text=text,
                    release_condition=until,
                )
            )

    # Only explicit ordered phases authorize the next action relationship.
    if len(phases) > 1:
        phase_actions = {
            phase_index: [event for event in compiled if event.phase_index == phase_index]
            for phase_index in range(len(phases))
        }
        for phase_index in range(len(phases) - 1):
            current = phase_actions[phase_index]
            following = phase_actions[phase_index + 1]
            if len(current) == 1 and len(following) == 1:
                index = compiled.index(current[0])
                compiled[index] = replace(
                    current[0], permitted_next_action=following[0].action
                )
    return compiled


def compile_text(
    text: str, event_id: str, scene_id: str, timestamp_us: int
) -> list[ContractEvent]:
    """Compile supported explicit actions without inferring observational evidence."""
    return _compile_text(
        text,
        event_id,
        scene_id,
        timestamp_us,
        provenance="CONTRACT_COMPILER",
    )


def _raw_source_id(cluster_id: str, event: RawEvent) -> str:
    canonical = json.dumps(
        {
            "cluster_id": cluster_id,
            "timestamp_us": event.timestamp_us,
            "original_position": event.original_position,
            "duplicate_occurrence": event.duplicate_occurrence,
            "source_text_sha256": event.source_text_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compile_window(window: EventWindow | RawEventWindow) -> list[ContractEvent]:
    """Compile source events and return timestamp/phase ordered contracts."""
    compiled_with_order: list[tuple[int, int, ContractEvent]] = []
    if isinstance(window, RawEventWindow):
        for source_index, source in enumerate(window.events):
            events = _compile_text(
                source.source_text,
                _raw_source_id(window.cluster_id, source),
                source.scene_id,
                source.timestamp_us,
                provenance="RESTRICTED_NATURAL_WINDOW",
                source_occurrence=source.original_position,
            )
            compiled_with_order.extend(
                (source_index, event_index, event)
                for event_index, event in enumerate(events)
            )
    elif isinstance(window, EventWindow):
        for source_index, source in enumerate(window.events):
            if source.source_text is None:
                continue
            events = _compile_text(
                source.source_text,
                source.event_id,
                source.scene_id,
                source.timestamp_us,
                provenance=source.provenance,
                source_occurrence=source_index,
            )
            compiled_with_order.extend(
                (source_index, event_index, event)
                for event_index, event in enumerate(events)
            )
    else:
        raise TypeError("window must be an EventWindow or RawEventWindow")

    compiled_with_order.sort(
        key=lambda item: (
            item[2].timestamp_us,
            item[2].phase_index,
            item[0],
            item[1],
        )
    )
    return [event for _, _, event in compiled_with_order]


def build_summary(windows: Iterable[RawEventWindow]) -> dict[str, object]:
    """Return deduplicated parser-coverage counts without serializing source text."""
    unique: dict[tuple[str, int, int, str], RawEvent] = {}
    for window in windows:
        if not isinstance(window, RawEventWindow):
            raise TypeError("summary windows must contain RawEventWindow values")
        for source in window.events:
            identity = (
                window.cluster_id,
                source.timestamp_us,
                source.original_position,
                source.source_text_sha256,
            )
            unique.setdefault(identity, source)

    status_counts: Counter[str] = Counter()
    no_action_count = 0
    source_events_with_actions = 0
    for identity in sorted(unique):
        cluster_id = identity[0]
        source = unique[identity]
        events = _compile_text(
            source.source_text,
            _raw_source_id(cluster_id, source),
            cluster_id,
            source.timestamp_us,
            provenance="RESTRICTED_NATURAL_WINDOW",
            source_occurrence=source.original_position,
        )
        if not events:
            no_action_count += 1
            continue
        source_events_with_actions += 1
        status_counts.update(event.parse_status for event in events)

    compiled_phase_count = sum(status_counts.values())
    unknown_count = sum(
        count for status, count in status_counts.items() if status.startswith("UNKNOWN")
    )
    return {
        "unique_source_events": len(unique),
        "source_events_with_actions": source_events_with_actions,
        "compiled_phase_count": compiled_phase_count,
        "no_action_count": no_action_count,
        "parsed_status_counts": dict(sorted(status_counts.items())),
        "unknown_rate": (
            unknown_count / compiled_phase_count if compiled_phase_count else 0.0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report count-only conservative contract parser coverage."
    )
    parser.add_argument("--summary", action="store_true", required=True)
    parser.parse_args()
    summary = build_summary(read_natural_windows(NATURAL_WINDOWS_PATH))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
