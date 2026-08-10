"""Fail-closed expansion of grounded actor-zone instances into EBLC bundles."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from .composition import EBLCBundle, parse_bundle
from .program import EBLCProgram, load_program, parse_program
from .schema_validation import load_json, validate


INDEXED_COLLECTION_VERSION = "eblc-indexed-collection-v0.1"
INDEXED_COLLECTION_COMPILER_VERSION = "eblc-indexed-collection-compiler-v0.1"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/eblc_indexed_collection.schema.json"
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


class IndexedCollectionValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class GroundedZoneEntry:
    value: float
    unit: str
    frame: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndexedInstance:
    instance_id: str
    contract_id: str
    association_status: str
    target_entity_id: str | None
    zone_id: str | None
    zone_geometry_ref: str | None
    coordinate_transform_ref: str | None
    candidate_target_entity_ids: tuple[str, ...]
    candidate_zone_ids: tuple[str, ...]
    association_evidence_refs: tuple[str, ...]
    reason_codes: tuple[str, ...]
    zone_entry: GroundedZoneEntry | None
    priority_tier: str
    allowed_actions: tuple[str, ...]
    overrides_contracts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndexedCollection:
    raw: dict[str, Any]
    collection_id: str
    template_program: EBLCProgram
    frames: int
    claim_scope: str
    source_refs: tuple[str, ...]
    action_domain: tuple[str, ...]
    instances: tuple[IndexedInstance, ...]
    composition_evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndexedExpansionResult:
    collection_id: str
    verdict: str
    reason_codes: tuple[str, ...]
    unresolved_instance_ids: tuple[str, ...]
    bundle: EBLCBundle | None


def _duplicates(values: Iterable[str]) -> bool:
    items = tuple(values)
    return len(items) != len(set(items))


def _default_template_catalog() -> dict[str, EBLCProgram]:
    programs = (
        load_program(FIXTURE_ROOT / "eblc_program_p0b.json"),
        load_program(FIXTURE_ROOT / "eblc_program_p0b_v0_2.json"),
    )
    return {item.program_id: item for item in programs}


def _require_identifier(label: str, value: str) -> None:
    if not _IDENTIFIER.fullmatch(value):
        raise IndexedCollectionValidationError(f"invalid {label}: {value}")


def parse_indexed_collection(
    raw: dict[str, Any],
    *,
    template_catalog: Mapping[str, EBLCProgram] | None = None,
) -> IndexedCollection:
    validate(raw, load_json(SCHEMA_PATH))
    if raw["collection_version"] != INDEXED_COLLECTION_VERSION:
        raise IndexedCollectionValidationError(
            f"unsupported indexed collection version: {raw['collection_version']}"
        )
    _require_identifier("collection id", raw["collection_id"])
    source_refs = tuple(raw["source_refs"])
    action_domain = tuple(raw["action_domain"])
    composition_refs = tuple(raw["composition_evidence_refs"])
    if _duplicates(source_refs):
        raise IndexedCollectionValidationError("duplicate collection source_refs")
    if _duplicates(action_domain):
        raise IndexedCollectionValidationError("duplicate action_domain values")
    if not set(composition_refs).issubset(source_refs):
        raise IndexedCollectionValidationError("unknown composition evidence refs")
    for action in action_domain:
        _require_identifier("action", action)

    catalog = dict(template_catalog or _default_template_catalog())
    template_ref = raw["template_program_ref"]
    if template_ref not in catalog:
        raise IndexedCollectionValidationError(f"unknown template program ref: {template_ref}")
    template = catalog[template_ref]
    if template.raw["program_version"] != "eblc-program-v0.2":
        raise IndexedCollectionValidationError("indexed collection requires program v0.2 template")
    if template.frames != raw["frames"]:
        raise IndexedCollectionValidationError("template/collection frame mismatch")
    if template.claim_scope != raw["claim_scope"]:
        raise IndexedCollectionValidationError("template/collection claim scope mismatch")
    if not set(template.source_refs).issubset(source_refs):
        raise IndexedCollectionValidationError("template sources missing from collection")

    raw_instances = raw["instances"]
    instance_ids = tuple(item["instance_id"] for item in raw_instances)
    contract_ids = tuple(item["contract_id"] for item in raw_instances)
    if _duplicates(instance_ids):
        raise IndexedCollectionValidationError("duplicate instance id")
    if _duplicates(contract_ids):
        raise IndexedCollectionValidationError("duplicate contract id")
    known_contracts = set(contract_ids)
    instances: list[IndexedInstance] = []
    bound_pairs: set[tuple[str, str]] = set()
    expected_frame = template.raw["binding"]["coordinate_frame"]
    expected_unit = template.raw["binding"]["distance_unit"]

    for item in raw_instances:
        instance_id = item["instance_id"]
        contract_id = item["contract_id"]
        _require_identifier("instance id", instance_id)
        _require_identifier("contract id", contract_id)
        actions = tuple(item["allowed_actions"])
        overrides = tuple(item["overrides_contracts"])
        if _duplicates(actions) or not set(actions).issubset(action_domain):
            raise IndexedCollectionValidationError(f"invalid allowed actions on {instance_id}")
        if _duplicates(overrides) or contract_id in overrides or not set(overrides).issubset(known_contracts):
            raise IndexedCollectionValidationError(f"invalid overrides on {instance_id}")

        association = item["association"]
        status = association["status"]
        refs = tuple(association["evidence_refs"])
        reasons = tuple(association["reason_codes"])
        targets = tuple(association["candidate_target_entity_ids"])
        zones = tuple(association["candidate_zone_ids"])
        if _duplicates(refs) or not set(refs).issubset(source_refs):
            raise IndexedCollectionValidationError(f"invalid association evidence on {instance_id}")
        if _duplicates(reasons) or _duplicates(targets) or _duplicates(zones):
            raise IndexedCollectionValidationError(f"duplicate association metadata on {instance_id}")

        zone_entry_raw = item["zone_entry"]
        zone_entry = None
        if zone_entry_raw is not None:
            entry_refs = tuple(zone_entry_raw["evidence_refs"])
            if _duplicates(entry_refs) or not set(entry_refs).issubset(source_refs):
                raise IndexedCollectionValidationError(f"invalid zone-entry evidence on {instance_id}")
            zone_entry = GroundedZoneEntry(
                float(zone_entry_raw["value"]), zone_entry_raw["unit"],
                zone_entry_raw["frame"], entry_refs,
            )

        target = association["target_entity_id"]
        zone = association["zone_id"]
        geometry_ref = association["zone_geometry_ref"]
        transform_ref = association["coordinate_transform_ref"]
        if status == "BOUND":
            if not all(isinstance(value, str) and value for value in (target, zone, geometry_ref, transform_ref)) or zone_entry is None:
                raise IndexedCollectionValidationError(f"BOUND association is incomplete on {instance_id}")
            if reasons:
                raise IndexedCollectionValidationError(f"BOUND association cannot contain reason codes on {instance_id}")
            if geometry_ref not in refs or transform_ref not in refs:
                raise IndexedCollectionValidationError(f"BOUND association evidence is incomplete on {instance_id}")
            if zone_entry.unit != expected_unit or zone_entry.frame != expected_frame:
                raise IndexedCollectionValidationError(f"BOUND association zone-entry unit/frame mismatch on {instance_id}")
            pair = (target, zone)
            if pair in bound_pairs:
                raise IndexedCollectionValidationError(f"duplicate bound target-zone pair: {pair}")
            bound_pairs.add(pair)
        else:
            if any(value is not None for value in (target, zone, geometry_ref, transform_ref)) or zone_entry is not None:
                raise IndexedCollectionValidationError(f"unresolved association contains bound fields on {instance_id}")
            if not reasons:
                raise IndexedCollectionValidationError(f"unresolved association requires reason codes on {instance_id}")
            if status == "AMBIGUOUS" and len(targets) + len(zones) < 2:
                raise IndexedCollectionValidationError(f"AMBIGUOUS association requires multiple candidates on {instance_id}")

        instances.append(IndexedInstance(
            instance_id=instance_id,
            contract_id=contract_id,
            association_status=status,
            target_entity_id=target,
            zone_id=zone,
            zone_geometry_ref=geometry_ref,
            coordinate_transform_ref=transform_ref,
            candidate_target_entity_ids=targets,
            candidate_zone_ids=zones,
            association_evidence_refs=refs,
            reason_codes=reasons,
            zone_entry=zone_entry,
            priority_tier=item["priority_tier"],
            allowed_actions=actions,
            overrides_contracts=overrides,
        ))

    return IndexedCollection(
        raw=raw,
        collection_id=raw["collection_id"],
        template_program=template,
        frames=int(raw["frames"]),
        claim_scope=raw["claim_scope"],
        source_refs=source_refs,
        action_domain=action_domain,
        instances=tuple(instances),
        composition_evidence_refs=composition_refs,
    )


def load_indexed_collection(path: Path) -> IndexedCollection:
    return parse_indexed_collection(load_json(path))


def _expanded_program(collection: IndexedCollection, instance: IndexedInstance) -> EBLCProgram:
    if instance.zone_entry is None or instance.target_entity_id is None or instance.zone_id is None:
        raise AssertionError("only BOUND instances may be expanded")
    raw = deepcopy(collection.template_program.raw)
    raw["program_id"] = f"{collection.template_program.program_id}__{instance.instance_id}"
    program_refs = list(dict.fromkeys(
        raw["source_refs"]
        + list(instance.association_evidence_refs)
        + list(instance.zone_entry.evidence_refs)
    ))
    raw["source_refs"] = program_refs
    raw["binding"].update({
        "contract_id": instance.contract_id,
        "target_entity_id": instance.target_entity_id,
        "zone_id": instance.zone_id,
        "evidence_refs": list(instance.association_evidence_refs),
    })
    derivation = raw["typed_derivation"]
    derivation["source_refs"] = list(dict.fromkeys(
        derivation["source_refs"] + list(instance.zone_entry.evidence_refs)
    ))
    for symbol in derivation["symbols"]:
        if symbol["symbol_id"] == "zone_entry_x":
            symbol["value"] = instance.zone_entry.value
            symbol["unit"] = instance.zone_entry.unit
            symbol["frame"] = instance.zone_entry.frame
            symbol["evidence_refs"] = list(instance.zone_entry.evidence_refs)
    for node in derivation["nodes"]:
        if node["node_id"] == "stop_position":
            node["source_refs"] = list(dict.fromkeys(
                node["source_refs"] + list(instance.zone_entry.evidence_refs)
            ))
    for output in derivation["outputs"]:
        if output["output_id"] == "stop_position":
            output["evidence_refs"] = list(dict.fromkeys(
                output["evidence_refs"] + list(instance.zone_entry.evidence_refs)
            ))
    return parse_program(raw)


def expand_indexed_collection(collection: IndexedCollection) -> IndexedExpansionResult:
    unresolved = tuple(
        item for item in collection.instances if item.association_status != "BOUND"
    )
    if unresolved:
        statuses = {item.association_status for item in unresolved}
        verdict = (
            "CONFLICT" if "CONFLICT" in statuses else
            "UNSUPPORTED" if "UNSUPPORTED" in statuses else
            "REVIEW_REQUIRED"
        )
        reasons = list(dict.fromkeys(
            reason for item in unresolved for reason in item.reason_codes
        ))
        reasons.append("INDEXED_COLLECTION_NOT_PARTIALLY_EXPANDED")
        return IndexedExpansionResult(
            collection.collection_id,
            verdict,
            tuple(reasons),
            tuple(item.instance_id for item in unresolved),
            None,
        )

    programs = {
        item.contract_id: _expanded_program(collection, item)
        for item in collection.instances
    }
    contracts = []
    for item in collection.instances:
        program = programs[item.contract_id]
        contracts.append({
            "contract_id": item.contract_id,
            "program": program.raw,
            "priority_tier": item.priority_tier,
            "allowed_actions": list(item.allowed_actions),
            "overrides_contracts": list(item.overrides_contracts),
            "evidence_refs": list(item.association_evidence_refs),
        })
    bundle = parse_bundle({
        "bundle_version": "eblc-bundle-v0.1",
        "bundle_id": f"{collection.collection_id}__bundle",
        "frames": collection.frames,
        "claim_scope": collection.claim_scope,
        "source_refs": list(collection.source_refs),
        "action_domain": list(collection.action_domain),
        "contracts": contracts,
        "composition_evidence_refs": list(collection.composition_evidence_refs),
    })
    return IndexedExpansionResult(
        collection.collection_id,
        "VALIDATED",
        ("ALL_INDEXED_ASSOCIATIONS_BOUND",),
        (),
        bundle,
    )
