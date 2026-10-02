#!/usr/bin/env python3
"""Build the deterministic, paired synthetic benchmark for sequential CoC checks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile
from typing import Any, Iterable, Mapping

if __package__ in (None, ""):
    sys.path.insert(0, str(next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())))

from experiments.sequential_coc.contract_ir import (
    Action,
    CheckResult,
    ContractEvent,
    ContradictionType,
    EventWindow,
)
from experiments.sequential_coc.event_local_checker import check_event_local
from experiments.sequential_coc.stateful_checker import check_stateful


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
DEFAULT_OUTPUT = (
    ROOT
    / "artifacts/results/restricted/sequential-coc-consistency-v1/mutations.jsonl"
)
SCHEMA_VERSION = "sequential-coc-mutation-pair-v1"
PRIMARY_TYPES = (
    ContradictionType.HOLD_GO_CONFLICT,
    ContradictionType.PREMATURE_RELEASE,
    ContradictionType.ORDER_VIOLATION,
    ContradictionType.STALE_OBLIGATION,
)
_PAIR_KEYS = frozenset(
    {
        "schema_version",
        "pair_id",
        "cluster_id",
        "original",
        "mutated",
        "changed_fields",
        "oracle",
        "checker_results",
    }
)
_CHECKER_RESULT_KEYS = frozenset({"event_local", "stateful"})
_SIDES = frozenset({"original", "mutated"})
_WINDOW_KEYS = frozenset({"window_id", "cluster_id", "events", "content_hash"})
_EVENT_KEYS = frozenset(
    {
        "scene_id", "event_id", "timestamp_us", "action", "trigger", "target",
        "satisfaction_known", "satisfaction_value", "release_known", "release_value",
        "permitted_next_action", "phase_index", "provenance", "parse_status",
        "satisfaction_condition", "release_condition",
    }
)
_RESULT_KEYS = frozenset(
    {"verdict", "contradiction_types", "first_event_id", "state_trace", "unknown_reasons"}
)


class MutationEligibilityError(ValueError):
    """A finite, machine-readable controlled-generation failure."""


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _pair_identity(
    cluster_id: str,
    oracle: ContradictionType,
    original: EventWindow,
    mutated: EventWindow,
) -> str:
    return _digest(
        {
            "cluster_id": cluster_id,
            "oracle": oracle.value,
            "original_content_hash": original.content_hash,
            "mutated_content_hash": mutated.content_hash,
        }
    )


def _flatten(value: object, prefix: str = "") -> dict[str, object]:
    flattened: dict[str, object] = {}
    if isinstance(value, Mapping):
        for key in sorted(value):
            if key == "content_hash":
                continue
            child = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten(value[key], child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            flattened.update(_flatten(item, f"{prefix}[{index}]"))
    else:
        flattened[prefix] = value
    return flattened


def validate_pair_diff(pair: "MutationPair") -> tuple[tuple[str, object, object], ...]:
    """Independently enumerate serialized IR changes and enforce the declaration."""
    before = _flatten(pair.original.to_dict(include_text=False))
    after = _flatten(pair.mutated.to_dict(include_text=False))
    if set(before) != set(after):
        raise ValueError("SERIALIZED_IR_SHAPE_CHANGED")
    differences = tuple(
        (path, before[path], after[path])
        for path in sorted(before)
        if before[path] != after[path]
    )
    if tuple(path for path, _, _ in differences) != pair.changed_fields:
        raise ValueError("DECLARED_DIFF_MISMATCH")
    if len(differences) != 1:
        raise ValueError("ONE_FACTOR_DIFF_REQUIRED")
    return differences


@dataclass(frozen=True, slots=True)
class MutationPair:
    pair_id: str
    cluster_id: str
    original: EventWindow
    mutated: EventWindow
    changed_fields: tuple[str, ...]
    oracle: ContradictionType
    original_event_local: CheckResult
    original_stateful: CheckResult
    mutated_event_local: CheckResult
    mutated_stateful: CheckResult

    def __post_init__(self) -> None:
        if not isinstance(self.pair_id, str) or len(self.pair_id) != 64:
            raise ValueError("PAIR_ID_INVALID")
        try:
            int(self.pair_id, 16)
        except ValueError as exc:
            raise ValueError("PAIR_ID_INVALID") from exc
        if not isinstance(self.cluster_id, str) or not self.cluster_id:
            raise ValueError("CLUSTER_ID_INVALID")
        if not isinstance(self.original, EventWindow) or not isinstance(
            self.mutated, EventWindow
        ):
            raise TypeError("PAIR_WINDOWS_INVALID")
        changed_fields = tuple(self.changed_fields)
        if any(not isinstance(item, str) or not item for item in changed_fields):
            raise TypeError("CHANGED_FIELDS_INVALID")
        object.__setattr__(self, "changed_fields", changed_fields)
        try:
            oracle = (
                self.oracle
                if isinstance(self.oracle, ContradictionType)
                else ContradictionType(self.oracle)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("ORACLE_INVALID") from exc
        if oracle not in PRIMARY_TYPES:
            raise ValueError("ORACLE_INVALID")
        object.__setattr__(self, "oracle", oracle)
        if not (
            self.original.cluster_id
            == self.cluster_id
            == self.mutated.cluster_id
        ):
            raise ValueError("PAIR_CLUSTER_MISMATCH")
        if self.original.window_id != self.mutated.window_id:
            raise ValueError("PAIR_WINDOW_ID_MISMATCH")
        if self.original.content_hash == self.mutated.content_hash:
            raise ValueError("PAIR_CONTENT_IDENTICAL")
        validate_pair_diff(self)
        expected_id = _pair_identity(
            self.cluster_id, self.oracle, self.original, self.mutated
        )
        if self.pair_id != expected_id:
            raise ValueError("PAIR_ID_MISMATCH")
        expected_results = (
            check_event_local(list(self.original.events)),
            check_stateful(list(self.original.events)),
            check_event_local(list(self.mutated.events)),
            check_stateful(list(self.mutated.events)),
        )
        actual_results = (
            self.original_event_local,
            self.original_stateful,
            self.mutated_event_local,
            self.mutated_stateful,
        )
        if actual_results != expected_results:
            raise ValueError("CHECKER_RESULT_MISMATCH")
        if self.original_stateful.verdict != "CONSISTENT":
            raise ValueError("ORIGINAL_NOT_CONSISTENT")
        if (
            self.mutated_stateful.verdict != "CONTRADICTION"
            or self.mutated_stateful.contradiction_types != (self.oracle,)
        ):
            raise ValueError("MUTATION_ORACLE_MISMATCH")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "pair_id": self.pair_id,
            "cluster_id": self.cluster_id,
            "original": self.original.to_dict(include_text=False),
            "mutated": self.mutated.to_dict(include_text=False),
            "changed_fields": list(self.changed_fields),
            "oracle": self.oracle.value,
            "checker_results": {
                "original": {
                    "event_local": self.original_event_local.to_dict(),
                    "stateful": self.original_stateful.to_dict(),
                },
                "mutated": {
                    "event_local": self.mutated_event_local.to_dict(),
                    "stateful": self.mutated_stateful.to_dict(),
                },
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MutationPair":
        if not isinstance(value, Mapping) or set(value) != _PAIR_KEYS:
            raise ValueError("PAIR_SCHEMA_MISMATCH")
        if value["schema_version"] != SCHEMA_VERSION:
            raise ValueError("PAIR_SCHEMA_VERSION_MISMATCH")
        checker_results = value["checker_results"]
        if not isinstance(checker_results, Mapping) or set(checker_results) != _SIDES:
            raise ValueError("CHECKER_RESULTS_SCHEMA_MISMATCH")
        for side in _SIDES:
            if not isinstance(checker_results[side], Mapping) or set(
                checker_results[side]
            ) != _CHECKER_RESULT_KEYS:
                raise ValueError("CHECKER_RESULTS_SCHEMA_MISMATCH")
            for checker_name in _CHECKER_RESULT_KEYS:
                result = checker_results[side][checker_name]
                if not isinstance(result, Mapping) or set(result) != _RESULT_KEYS:
                    raise ValueError("CHECKER_RESULT_SCHEMA_MISMATCH")
        for name in ("original", "mutated"):
            window = value[name]
            if not isinstance(window, Mapping) or set(window) != _WINDOW_KEYS:
                raise ValueError("WINDOW_SCHEMA_MISMATCH")
            events = window["events"]
            if not isinstance(events, list) or not events:
                raise ValueError("EVENT_SCHEMA_MISMATCH")
            if any(not isinstance(event, Mapping) or set(event) != _EVENT_KEYS for event in events):
                raise ValueError("EVENT_SCHEMA_MISMATCH")
        changed_fields = value["changed_fields"]
        if not isinstance(changed_fields, list):
            raise TypeError("CHANGED_FIELDS_INVALID")
        return cls(
            pair_id=value["pair_id"],
            cluster_id=value["cluster_id"],
            original=EventWindow.from_dict(value["original"]),
            mutated=EventWindow.from_dict(value["mutated"]),
            changed_fields=tuple(changed_fields),
            oracle=value["oracle"],
            original_event_local=CheckResult.from_dict(
                checker_results["original"]["event_local"]
            ),
            original_stateful=CheckResult.from_dict(
                checker_results["original"]["stateful"]
            ),
            mutated_event_local=CheckResult.from_dict(
                checker_results["mutated"]["event_local"]
            ),
            mutated_stateful=CheckResult.from_dict(
                checker_results["mutated"]["stateful"]
            ),
        )


def _eligible_change(
    window: EventWindow, kind: ContradictionType
) -> tuple[int, str, object]:
    events = window.events
    if kind is ContradictionType.HOLD_GO_CONFLICT:
        if not (
            len(events) == 2
            and events[0].action
            in (Action.STOP_OR_HOLD, Action.YIELD_OR_DECELERATE)
            and events[0].release_known
            and not events[0].release_value
            and events[0].satisfaction_known
            and events[0].satisfaction_value
            and events[1].action is Action.MAINTAIN_SPEED
        ):
            raise MutationEligibilityError("INELIGIBLE_HOLD_GO_CONFLICT")
        return 1, "action", Action.ACCELERATE_OR_PROCEED
    if kind is ContradictionType.PREMATURE_RELEASE:
        if not (
            len(events) == 1
            and events[0].action is Action.ACCELERATE_OR_PROCEED
            and events[0].release_known
            and events[0].release_value
        ):
            raise MutationEligibilityError("INELIGIBLE_PREMATURE_RELEASE")
        return 0, "release_value", False
    if kind is ContradictionType.ORDER_VIOLATION:
        if not (
            len(events) == 1
            and events[0].action is Action.ACCELERATE_OR_PROCEED
            and events[0].satisfaction_known
            and events[0].satisfaction_value
        ):
            raise MutationEligibilityError("INELIGIBLE_ORDER_VIOLATION")
        return 0, "satisfaction_value", False
    if kind is ContradictionType.STALE_OBLIGATION:
        if not (
            len(events) == 2
            and events[0].action
            in (Action.STOP_OR_HOLD, Action.YIELD_OR_DECELERATE)
            and events[1].action is events[0].action
            and events[1].target == events[0].target
            and events[1].release_known
            and not events[1].release_value
        ):
            raise MutationEligibilityError("INELIGIBLE_STALE_OBLIGATION")
        return 1, "release_value", True
    raise MutationEligibilityError("UNSUPPORTED_KIND")


def mutate_window(
    window: EventWindow, kind: ContradictionType
) -> MutationPair:
    """Apply exactly one predeclared field mutation and assert its oracle."""
    if not isinstance(window, EventWindow):
        raise TypeError("WINDOW_INVALID")
    try:
        normalized_kind = (
            kind if isinstance(kind, ContradictionType) else ContradictionType(kind)
        )
    except (TypeError, ValueError) as exc:
        raise MutationEligibilityError("UNSUPPORTED_KIND") from exc
    if normalized_kind not in PRIMARY_TYPES:
        raise MutationEligibilityError("UNSUPPORTED_KIND")

    base_stateful = check_stateful(list(window.events))
    if base_stateful.verdict == "CONTRADICTION":
        raise MutationEligibilityError("BASE_ALREADY_CONTRADICTORY")
    if base_stateful.verdict == "UNKNOWN":
        raise MutationEligibilityError("BASE_UNKNOWN")

    event_index, field, changed_value = _eligible_change(window, normalized_kind)
    events = list(window.events)
    events[event_index] = replace(events[event_index], **{field: changed_value})
    mutated = EventWindow(window.window_id, window.cluster_id, tuple(events))
    changed_fields = (f"events[{event_index}].{field}",)
    mutated_stateful = check_stateful(list(mutated.events))
    if (
        mutated_stateful.verdict != "CONTRADICTION"
        or mutated_stateful.contradiction_types != (normalized_kind,)
    ):
        raise MutationEligibilityError("MUTATION_POSTCONDITION_FAILED")
    pair_id = _pair_identity(
        window.cluster_id, normalized_kind, window, mutated
    )
    return MutationPair(
        pair_id=pair_id,
        cluster_id=window.cluster_id,
        original=window,
        mutated=mutated,
        changed_fields=changed_fields,
        oracle=normalized_kind,
        original_event_local=check_event_local(list(window.events)),
        original_stateful=base_stateful,
        mutated_event_local=check_event_local(list(mutated.events)),
        mutated_stateful=mutated_stateful,
    )


def _synthetic_base(
    kind: ContradictionType, ordinal: int, seed: int
) -> EventWindow:
    identity = {"seed": seed, "kind": kind.value, "ordinal": ordinal}
    cluster_id = _digest({"domain": "controlled-cluster", **identity})
    window_id = _digest({"domain": "controlled-window", **identity})
    target = f"controlled-target-{ordinal % 3}"

    def event_id(position: int) -> str:
        return _digest({"domain": "controlled-event", "position": position, **identity})

    common: dict[str, object] = {
        "scene_id": cluster_id,
        "provenance": "CONTROLLED_SYNTHETIC_IR",
        "parse_status": "PARSED",
        "source_text": None,
    }
    if kind is ContradictionType.HOLD_GO_CONFLICT:
        hold_action = (
            Action.STOP_OR_HOLD
            if ordinal % 2 == 0
            else Action.YIELD_OR_DECELERATE
        )
        events = (
            ContractEvent(
                event_id=event_id(0), timestamp_us=ordinal * 10 + 1,
                action=hold_action, target=target,
                satisfaction_known=True, satisfaction_value=True,
                release_known=True, release_value=False, **common,
            ),
            ContractEvent(
                event_id=event_id(1), timestamp_us=ordinal * 10 + 2,
                action=Action.MAINTAIN_SPEED, **common,
            ),
        )
    elif kind is ContradictionType.PREMATURE_RELEASE:
        events = (
            ContractEvent(
                event_id=event_id(0), timestamp_us=ordinal * 10 + 1,
                action=Action.ACCELERATE_OR_PROCEED,
                satisfaction_known=True, satisfaction_value=True,
                release_known=True, release_value=True, **common,
            ),
        )
    elif kind is ContradictionType.ORDER_VIOLATION:
        events = (
            ContractEvent(
                event_id=event_id(0), timestamp_us=ordinal * 10 + 1,
                action=Action.ACCELERATE_OR_PROCEED,
                satisfaction_known=True, satisfaction_value=True,
                release_known=True, release_value=True, **common,
            ),
        )
    elif kind is ContradictionType.STALE_OBLIGATION:
        hold_action = (
            Action.STOP_OR_HOLD
            if ordinal % 2 == 0
            else Action.YIELD_OR_DECELERATE
        )
        events = tuple(
            ContractEvent(
                event_id=event_id(position),
                timestamp_us=ordinal * 10 + position + 1,
                action=hold_action, target=target,
                satisfaction_known=True, satisfaction_value=True,
                release_known=True, release_value=False, **common,
            )
            for position in range(2)
        )
    else:  # guarded by the finite caller loop
        raise MutationEligibilityError("UNSUPPORTED_KIND")
    return EventWindow(window_id, cluster_id, events)


def _validate_collection(pairs: Iterable[MutationPair]) -> tuple[MutationPair, ...]:
    materialized = tuple(pairs)
    if any(not isinstance(pair, MutationPair) for pair in materialized):
        raise TypeError("PAIR_COLLECTION_INVALID")
    pair_ids = [pair.pair_id for pair in materialized]
    if len(pair_ids) != len(set(pair_ids)):
        raise ValueError("DUPLICATE_PAIR_ID")
    clusters = [pair.cluster_id for pair in materialized]
    if len(clusters) != len(set(clusters)):
        raise ValueError("DUPLICATE_CLUSTER_ID")
    originals = [pair.original.content_hash for pair in materialized]
    mutations = [pair.mutated.content_hash for pair in materialized]
    if len(originals) != len(set(originals)):
        raise ValueError("DUPLICATE_ORIGINAL_CONTENT")
    if len(mutations) != len(set(mutations)):
        raise ValueError("DUPLICATE_MUTATED_CONTENT")
    if set(originals) & set(mutations):
        raise ValueError("ORIGINAL_MUTATION_REVERSAL_LEAKAGE")
    return materialized


def generate_mutation_pairs(
    pairs_per_type: int = 10, seed: int = 20260806
) -> tuple[MutationPair, ...]:
    """Generate quotas directly; checker postconditions may fail but never filter."""
    if isinstance(pairs_per_type, bool) or not isinstance(pairs_per_type, int) or pairs_per_type < 1:
        raise ValueError("PAIRS_PER_TYPE_INVALID")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("SEED_INVALID")
    pairs = [
        mutate_window(_synthetic_base(kind, ordinal, seed), kind)
        for kind in PRIMARY_TYPES
        for ordinal in range(pairs_per_type)
    ]
    random.Random(seed).shuffle(pairs)
    validated = _validate_collection(pairs)
    counts = {
        kind: sum(pair.oracle is kind for pair in validated) for kind in PRIMARY_TYPES
    }
    if counts != {kind: pairs_per_type for kind in PRIMARY_TYPES}:
        raise RuntimeError("GENERATION_QUOTA_FAILURE")
    return validated


def jsonl_bytes(pairs: Iterable[MutationPair]) -> bytes:
    validated = _validate_collection(pairs)
    return b"".join(_canonical(pair.to_dict()) + b"\n" for pair in validated)


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def read_mutation_pairs(path: Path) -> tuple[MutationPair, ...]:
    path = Path(path)
    rows = path.read_text(encoding="utf-8").splitlines()
    if any(not row for row in rows):
        raise ValueError("BLANK_JSONL_ROW")
    pairs: list[MutationPair] = []
    for row in rows:
        value = json.loads(row, object_pairs_hook=_strict_json_object)
        if not isinstance(value, Mapping):
            raise ValueError("PAIR_SCHEMA_MISMATCH")
        pairs.append(MutationPair.from_dict(value))
    return _validate_collection(pairs)


def write_mutation_pairs(pairs: Iterable[MutationPair], path: Path) -> None:
    """Validate complete bytes in a restricted temp file, then publish atomically."""
    path = Path(path)
    payload = jsonl_bytes(pairs)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        restored = read_mutation_pairs(temporary_path)
        if jsonl_bytes(restored) != payload:
            raise ValueError("ATOMIC_ROUND_TRIP_MISMATCH")
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise


def summarize_pairs(pairs: Iterable[MutationPair], path: Path) -> dict[str, object]:
    values = _validate_collection(pairs)
    return {
        "status": "COMPLETE",
        "sample_unit": "PAIR",
        "pair_count": len(values),
        "cluster_count": len({pair.cluster_id for pair in values}),
        "type_counts": {
            kind.value: sum(pair.oracle is kind for pair in values)
            for kind in PRIMARY_TYPES
        },
        "original_stateful_counts": {
            "CONSISTENT": sum(pair.original_stateful.verdict == "CONSISTENT" for pair in values),
            "CONTRADICTION": sum(pair.original_stateful.verdict == "CONTRADICTION" for pair in values),
            "UNKNOWN": sum(pair.original_stateful.verdict == "UNKNOWN" for pair in values),
        },
        "mutated_stateful_counts": {
            "CONSISTENT": sum(pair.mutated_stateful.verdict == "CONSISTENT" for pair in values),
            "CONTRADICTION": sum(pair.mutated_stateful.verdict == "CONTRADICTION" for pair in values),
            "UNKNOWN": sum(pair.mutated_stateful.verdict == "UNKNOWN" for pair in values),
        },
        "original_event_local_counts": {
            verdict: sum(pair.original_event_local.verdict == verdict for pair in values)
            for verdict in ("CONSISTENT", "CONTRADICTION", "UNKNOWN")
        },
        "mutated_event_local_counts": {
            verdict: sum(pair.mutated_event_local.verdict == verdict for pair in values)
            for verdict in ("CONSISTENT", "CONTRADICTION", "UNKNOWN")
        },
        "exclusion_count": 0,
        "failure_count": 0,
        "human_review_required": False,
        "output": str(path),
        "sha256": hashlib.sha256(jsonl_bytes(values)).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs-per-type", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        pairs = generate_mutation_pairs(args.pairs_per_type, args.seed)
        write_mutation_pairs(pairs, args.output)
    except (MutationEligibilityError, RuntimeError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {"status": "GENERATION_FAILURE", "reason": str(exc)},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(summarize_pairs(pairs, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
