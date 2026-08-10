"""Canonical non-scalar composition semantics for EBLC contract bundles.

The resolver in this module is the operational source of truth for composing
already-evaluated contracts.  It deliberately does not assign numeric weights:
hard constraints cannot be bought off by service or preference objectives.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable

from .program import EBLCProgram, parse_program
from .schema_validation import load_json, validate


BUNDLE_VERSION = "eblc-bundle-v0.1"
COMPOSITION_VERSION = "eblc-composition-v0.1-nonscalar"
BUNDLE_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/eblc_bundle.schema.json"
PRIORITY_TIERS = ("HARD", "SERVICE", "PREFERENCE")
PRIORITY_RANK = {"HARD": 2, "SERVICE": 1, "PREFERENCE": 0}
LIVE_STATES = frozenset({"ACTIVE", "MAINTAINED", "REACTIVATED"})
VERDICTS = frozenset({"VALIDATED", "REVIEW_REQUIRED", "UNSUPPORTED", "CONFLICT"})
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


class EBLCBundleValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class BundleContract:
    contract_id: str
    program: EBLCProgram
    priority_tier: str
    allowed_actions: tuple[str, ...]
    overrides_contracts: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EBLCBundle:
    raw: dict[str, Any]
    bundle_id: str
    frames: int
    claim_scope: str
    source_refs: tuple[str, ...]
    action_domain: tuple[str, ...]
    contracts: tuple[BundleContract, ...]
    composition_evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContractEvaluation:
    contract_id: str
    lifecycle: str
    verdict: str


@dataclass(frozen=True, slots=True)
class CompositionResult:
    selected_contracts: tuple[str, ...]
    suppressed_contracts: tuple[str, ...]
    admissible_actions: tuple[str, ...]
    verdict: str
    false_deadlock: bool
    reason_codes: tuple[str, ...]


def _duplicates(values: Iterable[str]) -> bool:
    items = tuple(values)
    return len(items) != len(set(items))


def _assert_acyclic(edges: dict[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise EBLCBundleValidationError("priority override cycle")
        if node in visited:
            return
        visiting.add(node)
        for target in edges[node]:
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in edges:
        visit(node)


def parse_bundle(raw: dict[str, Any]) -> EBLCBundle:
    validate(raw, load_json(BUNDLE_SCHEMA_PATH))
    if raw["bundle_version"] != BUNDLE_VERSION:
        raise EBLCBundleValidationError(
            f"unsupported bundle version: {raw['bundle_version']}"
        )
    if not _IDENTIFIER.fullmatch(raw["bundle_id"]):
        raise EBLCBundleValidationError(f"invalid bundle id: {raw['bundle_id']}")

    source_refs = tuple(raw["source_refs"])
    action_domain = tuple(raw["action_domain"])
    composition_refs = tuple(raw["composition_evidence_refs"])
    if _duplicates(source_refs):
        raise EBLCBundleValidationError("duplicate source_refs")
    if _duplicates(action_domain):
        raise EBLCBundleValidationError("duplicate action_domain values")
    for action in action_domain:
        if not _IDENTIFIER.fullmatch(action):
            raise EBLCBundleValidationError(f"invalid action identifier: {action}")
    if not set(composition_refs).issubset(source_refs):
        raise EBLCBundleValidationError("unknown composition evidence refs")

    components: list[BundleContract] = []
    ids = [item["contract_id"] for item in raw["contracts"]]
    if _duplicates(ids):
        raise EBLCBundleValidationError("duplicate contract id")
    known_ids = set(ids)
    for item in raw["contracts"]:
        contract_id = item["contract_id"]
        if not _IDENTIFIER.fullmatch(contract_id):
            raise EBLCBundleValidationError(f"invalid contract id: {contract_id}")
        program = parse_program(item["program"])
        if program.frames != raw["frames"]:
            raise EBLCBundleValidationError(
                f"frame count mismatch on {contract_id}: {program.frames} != {raw['frames']}"
            )
        if program.raw["binding"]["contract_id"] != contract_id:
            raise EBLCBundleValidationError(
                f"entry/program contract id mismatch on {contract_id}"
            )
        actions = tuple(item["allowed_actions"])
        overrides = tuple(item["overrides_contracts"])
        refs = tuple(item["evidence_refs"])
        if _duplicates(actions):
            raise EBLCBundleValidationError(f"duplicate allowed action on {contract_id}")
        if not set(actions).issubset(action_domain):
            raise EBLCBundleValidationError(f"unknown allowed action on {contract_id}")
        if _duplicates(overrides):
            raise EBLCBundleValidationError(f"duplicate override on {contract_id}")
        if contract_id in overrides:
            raise EBLCBundleValidationError(f"self override on {contract_id}")
        if not set(overrides).issubset(known_ids):
            raise EBLCBundleValidationError(f"unknown override target on {contract_id}")
        if not set(refs).issubset(source_refs):
            raise EBLCBundleValidationError(f"unknown evidence refs on {contract_id}")
        if not set(program.source_refs).issubset(source_refs):
            raise EBLCBundleValidationError(f"program sources missing from bundle on {contract_id}")
        components.append(BundleContract(
            contract_id=contract_id,
            program=program,
            priority_tier=item["priority_tier"],
            allowed_actions=actions,
            overrides_contracts=overrides,
            evidence_refs=refs,
        ))

    by_id = {item.contract_id: item for item in components}
    edges = {item.contract_id: set(item.overrides_contracts) for item in components}
    for source, targets in edges.items():
        for target in targets:
            if PRIORITY_RANK[by_id[source].priority_tier] < PRIORITY_RANK[by_id[target].priority_tier]:
                raise EBLCBundleValidationError(
                    f"lower priority contract cannot override higher priority contract: {source}->{target}"
                )
    _assert_acyclic(edges)
    return EBLCBundle(
        raw=raw,
        bundle_id=raw["bundle_id"],
        frames=int(raw["frames"]),
        claim_scope=raw["claim_scope"],
        source_refs=source_refs,
        action_domain=action_domain,
        contracts=tuple(components),
        composition_evidence_refs=composition_refs,
    )


def load_bundle(path: Path) -> EBLCBundle:
    return parse_bundle(load_json(path))


def dominance_map(bundle: EBLCBundle) -> dict[str, frozenset[str]]:
    """Return the transitive set of contracts dominated by each contract."""

    dominated: dict[str, set[str]] = {item.contract_id: set() for item in bundle.contracts}
    for left in bundle.contracts:
        for right in bundle.contracts:
            if PRIORITY_RANK[left.priority_tier] > PRIORITY_RANK[right.priority_tier]:
                dominated[left.contract_id].add(right.contract_id)
        dominated[left.contract_id].update(left.overrides_contracts)

    changed = True
    while changed:
        changed = False
        for source in dominated:
            expanded = set(dominated[source])
            for target in tuple(dominated[source]):
                expanded.update(dominated[target])
            if expanded != dominated[source]:
                dominated[source] = expanded
                changed = True
    return {key: frozenset(value) for key, value in dominated.items()}


def resolve_composition(
    bundle: EBLCBundle,
    evaluations: Iterable[ContractEvaluation],
    *,
    safe_progress_action_exists: bool = False,
) -> CompositionResult:
    """Resolve one post-step evaluation of every contract in ``bundle``."""

    records = tuple(evaluations)
    if _duplicates(item.contract_id for item in records):
        raise ValueError("duplicate contract evaluation")
    by_evaluation = {item.contract_id: item for item in records}
    expected = {item.contract_id for item in bundle.contracts}
    if set(by_evaluation) != expected:
        missing = sorted(expected - set(by_evaluation))
        extra = sorted(set(by_evaluation) - expected)
        raise ValueError(f"evaluation coverage mismatch: missing={missing}, extra={extra}")
    for item in records:
        if item.lifecycle not in {
            "INACTIVE", "CANDIDATE", "ACTIVE", "MAINTAINED",
            "RELEASED", "REACTIVATED", "EXPIRED",
        }:
            raise ValueError(f"invalid lifecycle for {item.contract_id}: {item.lifecycle}")
        if item.verdict not in VERDICTS:
            raise ValueError(f"invalid verdict for {item.contract_id}: {item.verdict}")

    live = {
        item.contract_id for item in records if item.lifecycle in LIVE_STATES
    }
    domination = dominance_map(bundle)
    selected = tuple(
        item.contract_id
        for item in bundle.contracts
        if item.contract_id in live
        and not any(
            item.contract_id in domination[other]
            for other in live
            if other != item.contract_id
        )
    )
    selected_set = set(selected)
    suppressed = tuple(
        item.contract_id
        for item in bundle.contracts
        if item.contract_id in live and item.contract_id not in selected_set
    )
    allowed = set(bundle.action_domain)
    for item in bundle.contracts:
        if item.contract_id in selected_set:
            allowed.intersection_update(item.allowed_actions)
    admissible = tuple(action for action in bundle.action_domain if action in allowed)

    selected_hard = sum(
        item.contract_id in selected_set and item.priority_tier == "HARD"
        for item in bundle.contracts
    )
    action_conflict = not admissible and selected_hard >= 2
    action_review = not admissible and not action_conflict
    child_verdicts = {item.verdict for item in records}
    if action_conflict or "CONFLICT" in child_verdicts:
        verdict = "CONFLICT"
    elif "UNSUPPORTED" in child_verdicts:
        verdict = "UNSUPPORTED"
    elif action_review or "REVIEW_REQUIRED" in child_verdicts:
        verdict = "REVIEW_REQUIRED"
    else:
        verdict = "VALIDATED"

    false_deadlock = safe_progress_action_exists and not admissible
    reasons: list[str] = []
    if action_conflict:
        reasons.append("INCOMPARABLE_HARD_CONTRACT_ACTION_CONFLICT")
    elif action_review:
        reasons.append("INCOMPARABLE_NONHARD_CONTRACT_ACTION_CONFLICT")
    if false_deadlock:
        reasons.append("FALSE_DEADLOCK_SAFE_PROGRESS_EXISTS")
    if suppressed:
        reasons.append("LOWER_OR_EXPLICITLY_OVERRIDDEN_CONTRACT_SUPPRESSED")
    if not selected:
        reasons.append("NO_LIVE_CONTRACT_FULL_ACTION_DOMAIN")
    return CompositionResult(
        selected_contracts=selected,
        suppressed_contracts=suppressed,
        admissible_actions=admissible,
        verdict=verdict,
        false_deadlock=false_deadlock,
        reason_codes=tuple(reasons),
    )
