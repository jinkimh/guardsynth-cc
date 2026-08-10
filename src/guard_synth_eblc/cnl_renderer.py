"""Deterministic EBLC to Controlled Natural Language projection.

The structured EBLC object remains the execution authority.  This module is a
one-way, model-facing projection: it performs no inference, supplies no missing
values, and does not parse its prose back into an executable contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .composition import EBLCBundle
from .program import EBLCProgram


CNL_RENDERER_VERSION = "eblc-cnl-renderer-v0.1"
CNL_LANGUAGE_VERSION = "EBLC-CNL-EN-v0.1"


@dataclass(frozen=True, slots=True)
class CNLClause:
    clause_id: str
    text: str
    field_paths: tuple[str, ...]
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CNLDocument:
    renderer_version: str
    language_version: str
    source_kind: str
    source_id: str
    text: str
    clauses: tuple[CNLClause, ...]
    covered_paths: tuple[str, ...]
    omitted_paths: tuple[str, ...]
    input_sha256: str
    output_sha256: str

    def mapping_record(self) -> dict[str, Any]:
        return {
            "renderer_version": self.renderer_version,
            "language_version": self.language_version,
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "covered_paths": list(self.covered_paths),
            "omitted_paths": list(self.omitted_paths),
            "clauses": [asdict(clause) for clause in self.clauses],
            "authority_boundary": (
                "ONE_WAY_PROJECTION_STRUCTURED_EBLC_REMAINS_EXECUTION_AUTHORITY"
            ),
        }


def _canonical_bytes(raw: dict[str, Any]) -> bytes:
    return json.dumps(
        raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _number(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    return format(float(value), ".15g")


def _quantity(name: str, raw: dict[str, Any]) -> str:
    unit = f" {raw['unit']}" if raw["unit"] else ""
    frame = f" in frame {raw['frame']}" if raw["frame"] else ""
    return f"{name} = {_number(raw['value'])}{unit}{frame}"


def _expression(operation: str, inputs: Iterable[str]) -> str:
    terms = [item.split(":", 1)[1] for item in inputs]
    infix = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/"}
    if operation in infix:
        return f" {infix[operation]} ".join(terms)
    if operation == "NEG":
        return f"-{terms[0]}"
    if operation in {"MIN", "MAX"}:
        return f"{operation.lower()}({', '.join(terms)})"
    return f"{operation.lower()}({', '.join(terms)})"


def _program_clauses(program: EBLCProgram) -> tuple[CNLClause, ...]:
    raw = program.raw
    binding = raw["binding"]
    predicate = raw["predicate"]
    lifecycle = raw["lifecycle"]
    constraints = raw["constraints"]
    priority = raw["priority"]
    base = ""

    clauses: list[CNLClause] = [
        CNLClause(
            "program.identity",
            f"Program {raw['program_id']} uses {raw['program_version']} over {raw['frames']} bounded frames and has claim scope {raw['claim_scope']}.",
            (f"{base}$.program_version", f"{base}$.program_id", f"{base}$.frames", f"{base}$.claim_scope"),
        ),
        CNLClause(
            "program.sources",
            f"Declared evidence references: {', '.join(raw['source_refs'])}.",
            (f"{base}$.source_refs",),
            tuple(raw["source_refs"]),
        ),
        CNLClause(
            "binding.identity",
            (
                f"Contract {binding['contract_id']} applies rule {binding['rule_id']} to subject "
                f"{binding['subject_id']}, target {binding['target_entity_id']}, and conflict zone "
                f"{binding['zone_id']}."
            ),
            (
                f"{base}$.binding", f"{base}$.binding.contract_id", f"{base}$.binding.rule_id",
                f"{base}$.binding.subject_id", f"{base}$.binding.target_entity_id",
                f"{base}$.binding.zone_id",
            ),
            tuple(binding["evidence_refs"]),
        ),
        CNLClause(
            "binding.coordinates",
            f"Distances use unit {binding['distance_unit']} in coordinate frame {binding['coordinate_frame']}.",
            (f"{base}$.binding.distance_unit", f"{base}$.binding.coordinate_frame"),
            tuple(binding["evidence_refs"]),
        ),
        CNLClause(
            "predicate.observability",
            (
                f"Evaluate activation predicate {predicate['predicate_id']} only from "
                f"{', '.join(predicate['allowed_epistemic'])} evidence with maximum age "
                f"{_number(predicate['maximum_age_s'])} s; failed or stale observation becomes "
                f"{predicate['failure_value']}."
            ),
            (f"{base}$.predicate",),
            tuple(predicate["evidence_refs"]),
        ),
        CNLClause(
            "lifecycle.release",
            (
                f"Initial lifecycle state is {lifecycle['initial_state']}; release is "
                f"{'enabled' if lifecycle['release_enabled'] else 'disabled'} after "
                f"{lifecycle['release_clear_frames']} consecutive clear frames."
            ),
            (f"{base}$.lifecycle", f"{base}$.lifecycle.initial_state", f"{base}$.lifecycle.release_enabled", f"{base}$.lifecycle.release_clear_frames"),
            tuple(lifecycle["evidence_refs"]),
        ),
        CNLClause(
            "lifecycle.reactivation",
            f"After release, reactivation is {'enabled' if lifecycle['reactivation_enabled'] else 'disabled'} when the hazard returns.",
            (f"{base}$.lifecycle.reactivation_enabled",),
            tuple(lifecycle["evidence_refs"]),
        ),
        CNLClause(
            "lifecycle.fallback",
            (
                f"UNKNOWN policy is {lifecycle['unknown_policy']}; fallback action is "
                f"{lifecycle['fallback_action']} and approval is "
                f"{'present' if lifecycle['fallback_approved'] else 'absent'}."
            ),
            (f"{base}$.lifecycle.unknown_policy", f"{base}$.lifecycle.fallback_action", f"{base}$.lifecycle.fallback_approved"),
            tuple(lifecycle["evidence_refs"]),
        ),
        CNLClause(
            "lifecycle.activation_expiry",
            (
                f"Always-active mode is {_number(lifecycle['always_active'])}; expiry timestamp is "
                f"{'not set' if lifecycle['expiry_timestamp_s'] is None else _number(lifecycle['expiry_timestamp_s']) + ' s'}."
            ),
            (f"{base}$.lifecycle.always_active", f"{base}$.lifecycle.expiry_timestamp_s"),
            tuple(lifecycle["evidence_refs"]),
        ),
    ]

    quantity_names = (
        "position_uncertainty", "response_time", "deceleration",
        "position_epsilon", "speed_epsilon", "time_epsilon",
    )
    for name in quantity_names:
        item = constraints[name]
        clauses.append(CNLClause(
            f"constraints.{name}",
            f"Supplied constraint input: {_quantity(name, item)}; these are supplied evidence-bound inputs, not inferred guarantees.",
            (f"{base}$.constraints", f"{base}$.constraints.{name}"),
            tuple(item["evidence_refs"]),
        ))
    clauses.append(CNLClause(
        "constraints.flags",
        (
            f"Invariant enforcement is {_number(constraints['enforce_invariant'])}; "
            f"forced deadlock mode is {_number(constraints['force_deadlock'])}."
        ),
        (f"{base}$.constraints.enforce_invariant", f"{base}$.constraints.force_deadlock"),
    ))

    derivation_key = "typed_derivation" if "typed_derivation" in raw else "derivation_dag"
    derivation = raw[derivation_key]
    if derivation_key == "typed_derivation":
        clauses.append(CNLClause(
            "derivation.interface",
            (
                f"Typed derivation {derivation['derivation_id']} uses {derivation['derivation_version']} "
                f"with horizon {derivation['horizon']} and claim scope {derivation['claim_scope']}."
            ),
            (f"{base}$.typed_derivation",),
            tuple(derivation["source_refs"]),
        ))
        for symbol in derivation["symbols"]:
            value = "runtime-bound" if symbol["value"] is None else _number(symbol["value"])
            unit = f" {symbol['unit']}" if symbol["unit"] else ""
            clauses.append(CNLClause(
                f"derivation.symbol.{symbol['symbol_id']}",
                f"Derivation symbol {symbol['symbol_id']} is {symbol['kind']} with value {value}{unit}.",
                (f"{base}$.typed_derivation.symbols",),
                tuple(symbol["evidence_refs"]),
            ))
        for node in derivation["nodes"]:
            clauses.append(CNLClause(
                f"derivation.node.{node['node_id']}",
                f"{node['node_id']} := {_expression(node['operation'], node['inputs'])}.",
                (f"{base}$.typed_derivation.nodes",),
                tuple(node["source_refs"]),
            ))
        for output in derivation["outputs"]:
            clauses.append(CNLClause(
                f"derivation.output.{output['output_id']}",
                f"Output {output['output_id']} maps {output['node_ref']} to declaration {output['target_declaration']} with unit {output['unit']}.",
                (f"{base}$.typed_derivation.outputs",),
                tuple(output["evidence_refs"]),
            ))
    else:
        for node in derivation:
            clauses.append(CNLClause(
                f"derivation.node.{node['node_id']}",
                f"Legacy derivation node {node['node_id']} applies {node['operation']} to {', '.join(node['inputs'])}.",
                (f"{base}$.derivation_dag",),
                tuple(node["source_refs"]),
            ))

    clauses.append(CNLClause(
        "priority.policy",
        f"Priority class is {priority['class']} and it overrides {', '.join(priority['overrides']) or 'no classes'}.",
        (f"{base}$.priority",),
        tuple(priority["evidence_refs"]),
    ))
    return tuple(clauses)


def _program_text(program: EBLCProgram, clauses: tuple[CNLClause, ...]) -> str:
    lines = [
        f"EBLC CONTROLLED NATURAL LANGUAGE [{CNL_LANGUAGE_VERSION}]",
        f"SOURCE PROGRAM: {program.program_id}",
        (
            "AUTHORITY: This rendering is not the execution authority; use the "
            f"structured EBLC program {program.program_id}."
        ),
        "",
    ]
    lines.extend(f"[{clause.clause_id}] {clause.text}" for clause in clauses)
    return "\n".join(lines) + "\n"


def render_program(program: EBLCProgram) -> CNLDocument:
    clauses = _program_clauses(program)
    text = _program_text(program, clauses)
    covered = tuple(dict.fromkeys(
        [f"$.{key}" for key in program.raw]
        + [path for clause in clauses for path in clause.field_paths]
    ))
    return CNLDocument(
        renderer_version=CNL_RENDERER_VERSION,
        language_version=CNL_LANGUAGE_VERSION,
        source_kind="EBLC_PROGRAM",
        source_id=program.program_id,
        text=text,
        clauses=clauses,
        covered_paths=covered,
        omitted_paths=(),
        input_sha256=_digest(_canonical_bytes(program.raw)),
        output_sha256=_digest(text.encode("utf-8")),
    )


def render_bundle(bundle: EBLCBundle) -> CNLDocument:
    clauses: list[CNLClause] = [
        CNLClause(
            "bundle.identity",
            f"Bundle {bundle.bundle_id} uses {bundle.raw['bundle_version']} over {bundle.frames} bounded frames with claim scope {bundle.claim_scope}.",
            ("$.bundle_version", "$.bundle_id", "$.frames", "$.claim_scope"),
        ),
        CNLClause(
            "bundle.sources",
            f"Declared bundle evidence references: {', '.join(bundle.source_refs)}.",
            ("$.source_refs",),
            bundle.source_refs,
        ),
        CNLClause(
            "bundle.actions",
            f"The action domain: {', '.join(bundle.action_domain)}; for selected live contracts, admissible actions are the intersection of their allowed action sets.",
            ("$.action_domain",),
            bundle.composition_evidence_refs,
        ),
        CNLClause(
            "bundle.composition_evidence",
            f"Composition policy evidence references: {', '.join(bundle.composition_evidence_refs)}.",
            ("$.composition_evidence_refs",),
            bundle.composition_evidence_refs,
        ),
    ]
    lines = [
        f"EBLC CONTROLLED NATURAL LANGUAGE [{CNL_LANGUAGE_VERSION}]",
        f"SOURCE BUNDLE: {bundle.bundle_id}",
        (
            "AUTHORITY: This rendering is not the execution authority; use the "
            f"structured EBLC bundle {bundle.bundle_id}."
        ),
        "",
        "BUNDLE COMPOSITION:",
    ]
    lines.extend(f"[{clause.clause_id}] {clause.text}" for clause in clauses)

    for index, component in enumerate(bundle.contracts):
        entry = bundle.raw["contracts"][index]
        entry_clause = CNLClause(
            f"bundle.contract.{component.contract_id}",
            (
                f"CONTRACT {component.contract_id} has priority tier {component.priority_tier}; "
                f"allowed actions are {', '.join(component.allowed_actions)}; explicit override "
                f"targets are {', '.join(component.overrides_contracts) or 'none'}."
            ),
            (
                "$.contracts", f"$.contracts[{index}]", f"$.contracts[{index}].contract_id",
                f"$.contracts[{index}].priority_tier", f"$.contracts[{index}].allowed_actions",
                f"$.contracts[{index}].overrides_contracts", f"$.contracts[{index}].evidence_refs",
                f"$.contracts[{index}].program",
            ),
            tuple(entry["evidence_refs"]),
        )
        clauses.append(entry_clause)
        raw_component_clauses = _program_clauses(component.program)
        component_clauses = tuple(
            CNLClause(
                clause_id=clause.clause_id,
                text=clause.text,
                field_paths=tuple(
                    f"$.contracts[{index}].program{path[1:]}"
                    for path in clause.field_paths
                ),
                source_refs=clause.source_refs,
            )
            for clause in raw_component_clauses
        )
        clauses.extend(component_clauses)
        lines.extend(("", entry_clause.text, "PROGRAM PROJECTION:"))
        lines.extend(f"[{clause.clause_id}] {clause.text}" for clause in component_clauses)

    text = "\n".join(lines) + "\n"
    covered = tuple(dict.fromkeys(
        [f"$.{key}" for key in bundle.raw]
        + [path for clause in clauses for path in clause.field_paths]
    ))
    return CNLDocument(
        renderer_version=CNL_RENDERER_VERSION,
        language_version=CNL_LANGUAGE_VERSION,
        source_kind="EBLC_BUNDLE",
        source_id=bundle.bundle_id,
        text=text,
        clauses=tuple(clauses),
        covered_paths=covered,
        omitted_paths=(),
        input_sha256=_digest(_canonical_bytes(bundle.raw)),
        output_sha256=_digest(text.encode("utf-8")),
    )


def export_cnl(
    document: CNLDocument,
    output_dir: Path,
    *,
    text_name: str = "CONSTRAINTS.txt",
    mapping_name: str = "CNL_MAPPING.json",
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    text_path = output_dir / text_name
    mapping_path = output_dir / mapping_name
    text_path.write_text(document.text, encoding="utf-8")
    mapping_path.write_text(
        json.dumps(document.mapping_record(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return text_path, mapping_path
