"""Typed, evidence-bearing numeric derivation DAG to EBLC Core compiler."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import re
from typing import Any, Iterable

from .core_ir import CoreModel, parse_core_model
from .schema_validation import load_json, validate


DERIVATION_VERSION = "eblc-derivation-v0.1"
DERIVATION_COMPILER_VERSION = "eblc-derivation-core-compiler-v0.1"
DERIVATION_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/derivation_spec.schema.json"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_BINARY_OPERATIONS = frozenset({"ADD", "SUB", "MUL", "DIV", "MIN", "MAX"})
_UNARY_OPERATIONS = frozenset({"NEG"})


class DerivationValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DerivationSymbol:
    symbol_id: str
    kind: str
    sort: str
    time_varying: bool
    value: int | float | None
    core_name: str | None
    unit: str | None
    frame: str | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DerivationNode:
    node_id: str
    operation: str
    inputs: tuple[str, ...]
    source_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DerivationOutput:
    output_id: str
    node_ref: str
    target_declaration: str
    sort: str
    time_varying: bool
    unit: str | None
    frame: str | None
    replace_clause_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DerivationSpec:
    raw: dict[str, Any]
    derivation_id: str
    horizon: int
    claim_scope: str
    source_refs: tuple[str, ...]
    symbols: tuple[DerivationSymbol, ...]
    nodes: tuple[DerivationNode, ...]
    outputs: tuple[DerivationOutput, ...]


@dataclass(frozen=True, slots=True)
class DerivationElaborationResult:
    core_model: CoreModel
    core_document: dict[str, Any]
    derivation_map: dict[str, Any]


def _duplicates(values: Iterable[str]) -> bool:
    items = tuple(values)
    return len(items) != len(set(items))


def _check_refs(owner: str, refs: tuple[str, ...], known: set[str]) -> None:
    if not refs or not set(refs).issubset(known):
        raise DerivationValidationError(f"unknown evidence reference on {owner}")


def parse_derivation_spec(raw: dict[str, Any]) -> DerivationSpec:
    validate(raw, load_json(DERIVATION_SCHEMA_PATH))
    if raw["derivation_version"] != DERIVATION_VERSION:
        raise DerivationValidationError(
            f"unsupported derivation version: {raw['derivation_version']}"
        )
    if not _IDENTIFIER.fullmatch(raw["derivation_id"]):
        raise DerivationValidationError(f"invalid derivation id: {raw['derivation_id']}")
    source_refs = tuple(raw["source_refs"])
    if _duplicates(source_refs):
        raise DerivationValidationError("duplicate derivation source_refs")
    known_sources = set(source_refs)

    symbols: list[DerivationSymbol] = []
    symbol_ids = [item["symbol_id"] for item in raw["symbols"]]
    if _duplicates(symbol_ids):
        raise DerivationValidationError("duplicate derivation symbol id")
    for item in raw["symbols"]:
        symbol_id = item["symbol_id"]
        if not _IDENTIFIER.fullmatch(symbol_id):
            raise DerivationValidationError(f"invalid derivation symbol id: {symbol_id}")
        refs = tuple(item["evidence_refs"])
        _check_refs(f"symbol:{symbol_id}", refs, known_sources)
        kind = item["kind"]
        value = item["value"]
        core_name = item["core_name"]
        if kind == "SOURCED_VALUE":
            if value is None or core_name is not None or item["time_varying"]:
                raise DerivationValidationError(
                    f"SOURCED_VALUE requires finite constant value and null core_name: {symbol_id}"
                )
            if not isfinite(value):
                raise DerivationValidationError(f"non-finite derivation value: {symbol_id}")
            if item["sort"] == "INT" and (not isinstance(value, int) or isinstance(value, bool)):
                raise DerivationValidationError(f"INT sourced value requires integer: {symbol_id}")
        elif value is not None or not isinstance(core_name, str) or not _IDENTIFIER.fullmatch(core_name):
            raise DerivationValidationError(
                f"CORE_VARIABLE requires null value and valid core_name: {symbol_id}"
            )
        symbols.append(DerivationSymbol(
            symbol_id=symbol_id,
            kind=kind,
            sort=item["sort"],
            time_varying=bool(item["time_varying"]),
            value=value,
            core_name=core_name,
            unit=item["unit"],
            frame=item["frame"],
            evidence_refs=refs,
        ))

    nodes: list[DerivationNode] = []
    node_ids = [item["node_id"] for item in raw["nodes"]]
    if _duplicates(node_ids):
        raise DerivationValidationError("duplicate derivation node id")
    known_symbol_refs = {f"symbol:{item}" for item in symbol_ids}
    known_node_refs = {f"node:{item}" for item in node_ids}
    known_refs = known_symbol_refs | known_node_refs
    for item in raw["nodes"]:
        node_id = item["node_id"]
        if not _IDENTIFIER.fullmatch(node_id):
            raise DerivationValidationError(f"invalid derivation node id: {node_id}")
        refs = tuple(item["source_refs"])
        _check_refs(f"node:{node_id}", refs, known_sources)
        inputs = tuple(item["inputs"])
        expected_arity = 1 if item["operation"] in _UNARY_OPERATIONS else 2
        if len(inputs) != expected_arity:
            raise DerivationValidationError(
                f"operation arity mismatch on {node_id}: expected {expected_arity}, got {len(inputs)}"
            )
        for reference in inputs:
            if reference not in known_refs:
                raise DerivationValidationError(
                    f"unknown derivation reference on {node_id}: {reference}"
                )
        nodes.append(DerivationNode(node_id, item["operation"], inputs, refs))

    by_node = {item.node_id: item for item in nodes}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise DerivationValidationError("derivation DAG cycle")
        if node_id in visited:
            return
        visiting.add(node_id)
        for reference in by_node[node_id].inputs:
            if reference.startswith("node:"):
                visit(reference.split(":", 1)[1])
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in by_node:
        visit(node_id)

    outputs: list[DerivationOutput] = []
    output_ids = [item["output_id"] for item in raw["outputs"]]
    target_ids = [item["target_declaration"] for item in raw["outputs"]]
    if _duplicates(output_ids) or _duplicates(target_ids):
        raise DerivationValidationError("duplicate derivation output or target")
    for item in raw["outputs"]:
        output_id = item["output_id"]
        target = item["target_declaration"]
        if not _IDENTIFIER.fullmatch(output_id) or not _IDENTIFIER.fullmatch(target):
            raise DerivationValidationError(f"invalid derivation output identifier: {output_id}")
        node_ref = item["node_ref"]
        if node_ref not in known_node_refs:
            raise DerivationValidationError(
                f"unknown derivation reference on output {output_id}: {node_ref}"
            )
        refs = tuple(item["evidence_refs"])
        _check_refs(f"output:{output_id}", refs, known_sources)
        replacements = tuple(item["replace_clause_ids"])
        if _duplicates(replacements):
            raise DerivationValidationError(f"duplicate replacement clause on {output_id}")
        outputs.append(DerivationOutput(
            output_id=output_id,
            node_ref=node_ref,
            target_declaration=target,
            sort=item["sort"],
            time_varying=bool(item["time_varying"]),
            unit=item["unit"],
            frame=item["frame"],
            replace_clause_ids=replacements,
            evidence_refs=refs,
        ))
    return DerivationSpec(
        raw=raw,
        derivation_id=raw["derivation_id"],
        horizon=int(raw["horizon"]),
        claim_scope=raw["claim_scope"],
        source_refs=source_refs,
        symbols=tuple(symbols),
        nodes=tuple(nodes),
        outputs=tuple(outputs),
    )


def load_derivation_spec(path: Path) -> DerivationSpec:
    return parse_derivation_spec(load_json(path))


def _literal(sort: str, value: int | float, unit: str | None, frame: str | None) -> dict[str, Any]:
    return {
        "op": "literal", "sort": sort, "value": value,
        "enum_name": None, "unit": unit, "frame": frame,
    }


def _var(name: str) -> dict[str, Any]:
    return {"op": "var", "name": name, "offset": 0}


def _binary(op: str, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {"op": op, "left": left, "right": right}


def _declaration(
    name: str,
    sort: str,
    time_varying: bool,
    unit: str | None,
    frame: str | None,
    refs: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "name": name, "sort": sort, "time_varying": time_varying,
        "enum_name": None, "enum_values": [], "unit": unit, "frame": frame,
        "source_refs": list(refs),
    }


def _clause(
    clause_id: str,
    formula: dict[str, Any],
    refs: tuple[str, ...],
    description: str,
    enforcement: str,
) -> dict[str, Any]:
    return {
        "id": clause_id, "kind": "BOUND", "enforcement": enforcement,
        "formula": formula, "source_refs": list(refs), "description": description,
    }


def elaborate_derivation(
    spec: DerivationSpec,
    *,
    base_core_document: dict[str, Any] | None = None,
) -> DerivationElaborationResult:
    """Generate a standalone Core model or augment an existing Core document."""

    if base_core_document is None:
        document: dict[str, Any] = {
            "grammar_version": "eblc-core-v0.1",
            "model_id": f"{spec.derivation_id}_core",
            "horizon": spec.horizon,
            "declarations": [],
            "clauses": [],
            "queries": [],
            "source_refs": list(spec.source_refs),
            "claim_scope": spec.claim_scope,
        }
    else:
        document = {
            **base_core_document,
            "model_id": f"{base_core_document['model_id']}_typed_derivation",
            "declarations": [dict(item) for item in base_core_document["declarations"]],
            "clauses": [dict(item) for item in base_core_document["clauses"]],
            "queries": [dict(item) for item in base_core_document["queries"]],
            "source_refs": list(dict.fromkeys(base_core_document["source_refs"] + list(spec.source_refs))),
        }
        if document["horizon"] != spec.horizon:
            raise DerivationValidationError(
                f"derivation/base horizon mismatch: {spec.horizon} != {document['horizon']}"
            )

    declarations = {item["name"]: item for item in document["declarations"]}
    symbol_core_name: dict[str, str] = {}
    for symbol in spec.symbols:
        if symbol.kind == "SOURCED_VALUE":
            name = f"derive__symbol__{symbol.symbol_id}"
            if name in declarations:
                raise DerivationValidationError(f"derivation declaration collision: {name}")
            declaration = _declaration(
                name, symbol.sort, False, symbol.unit, symbol.frame, symbol.evidence_refs
            )
            document["declarations"].append(declaration)
            declarations[name] = declaration
            document["clauses"].append(_clause(
                f"derive__bind__{symbol.symbol_id}",
                _binary(
                    "eq", _var(name),
                    _literal(symbol.sort, symbol.value, symbol.unit, symbol.frame),
                ),
                symbol.evidence_refs,
                f"Bind sourced derivation input {symbol.symbol_id}.",
                "INITIAL",
            ))
        else:
            name = symbol.core_name or ""
            existing = declarations.get(name)
            if existing is None:
                declaration = _declaration(
                    name, symbol.sort, symbol.time_varying,
                    symbol.unit, symbol.frame, symbol.evidence_refs,
                )
                document["declarations"].append(declaration)
                declarations[name] = declaration
            elif (
                existing["sort"] != symbol.sort
                or existing["time_varying"] != symbol.time_varying
                or existing["unit"] != symbol.unit
                or existing["frame"] != symbol.frame
            ):
                raise DerivationValidationError(
                    f"CORE_VARIABLE type mismatch for {symbol.symbol_id}: {name}"
                )
        symbol_core_name[symbol.symbol_id] = name

    nodes = {item.node_id: item for item in spec.nodes}
    symbols = {item.symbol_id: item for item in spec.symbols}
    expression_cache: dict[str, dict[str, Any]] = {}
    time_varying_cache: dict[str, bool] = {}

    def reference_expression(reference: str) -> tuple[dict[str, Any], bool]:
        kind, identifier = reference.split(":", 1)
        if kind == "symbol":
            return _var(symbol_core_name[identifier]), symbols[identifier].time_varying
        return node_expression(identifier)

    def node_expression(node_id: str) -> tuple[dict[str, Any], bool]:
        if node_id in expression_cache:
            return expression_cache[node_id], time_varying_cache[node_id]
        node = nodes[node_id]
        values = tuple(reference_expression(reference) for reference in node.inputs)
        expressions = tuple(item[0] for item in values)
        varying = any(item[1] for item in values)
        if node.operation == "NEG":
            expression = {"op": "neg", "arg": expressions[0]}
        elif node.operation in {"ADD", "SUB", "MUL", "DIV"}:
            expression = _binary(node.operation.lower(), expressions[0], expressions[1])
        elif node.operation == "MIN":
            expression = {
                "op": "ite",
                "condition": _binary("le", expressions[0], expressions[1]),
                "then": expressions[0],
                "else": expressions[1],
            }
        elif node.operation == "MAX":
            expression = {
                "op": "ite",
                "condition": _binary("ge", expressions[0], expressions[1]),
                "then": expressions[0],
                "else": expressions[1],
            }
        else:  # schema/parser prevent this branch
            raise DerivationValidationError(f"unsupported derivation operation: {node.operation}")
        expression_cache[node_id] = expression
        time_varying_cache[node_id] = varying
        return expression, varying

    replacements = {
        clause_id for output in spec.outputs for clause_id in output.replace_clause_ids
    }
    existing_clause_ids = {item["id"] for item in document["clauses"]}
    missing_replacements = replacements - existing_clause_ids
    if missing_replacements:
        raise DerivationValidationError(
            f"unknown replacement clause ids: {sorted(missing_replacements)}"
        )
    document["clauses"] = [
        item for item in document["clauses"] if item["id"] not in replacements
    ]

    for output in spec.outputs:
        expression, depends_on_time = reference_expression(output.node_ref)
        if depends_on_time and not output.time_varying:
            raise DerivationValidationError(
                f"time-varying derivation requires time-varying output: {output.output_id}"
            )
        target = declarations.get(output.target_declaration)
        if target is None:
            target = _declaration(
                output.target_declaration, output.sort, output.time_varying,
                output.unit, output.frame, output.evidence_refs,
            )
            document["declarations"].append(target)
            declarations[output.target_declaration] = target
        elif (
            target["sort"] != output.sort
            or target["time_varying"] != output.time_varying
            or target["unit"] != output.unit
            or target["frame"] != output.frame
        ):
            raise DerivationValidationError(
                f"derivation output type mismatch: {output.target_declaration}"
            )
        refs = tuple(dict.fromkeys(
            output.evidence_refs
            + tuple(ref for node in spec.nodes for ref in node.source_refs)
            + tuple(ref for symbol in spec.symbols for ref in symbol.evidence_refs)
        ))
        document["clauses"].append(_clause(
            f"derive__output__{output.output_id}",
            _binary("eq", _var(output.target_declaration), expression),
            refs,
            f"Symbolically replay typed derivation output {output.output_id}.",
            "EACH_FRAME" if output.time_varying else "INITIAL",
        ))

    if not document["queries"]:
        document["queries"] = [{
            "id": "typed_derivation_satisfiable",
            "formula": {
                "op": "literal", "sort": "BOOL", "value": True,
                "enum_name": None, "unit": None, "frame": None,
            },
            "expected": "SAT",
            "classification": "CONSISTENCY",
            "source_refs": list(spec.source_refs),
            "description": "The typed derivation admits a bounded Core execution.",
        }]
    core_model = parse_core_model(document)
    derivation_map = {
        "derivation_id": spec.derivation_id,
        "derivation_version": DERIVATION_VERSION,
        "compiler_version": DERIVATION_COMPILER_VERSION,
        "core_model_id": core_model.model_id,
        "symbol_bindings": symbol_core_name,
        "node_operations": {item.node_id: item.operation for item in spec.nodes},
        "outputs": {
            item.output_id: {
                "target_declaration": item.target_declaration,
                "replaced_clauses": list(item.replace_clause_ids),
            }
            for item in spec.outputs
        },
        "limitations": [
            "FINITE_TYPED_ARITHMETIC_DAG",
            "NO_AUTOMATIC_PARSING_OF_FREE_FORM_OPERATION_STRINGS",
            "BOUNDED_CORE_EXECUTION",
            "NOT_A_VEHICLE_SAFETY_PROOF",
        ],
    }
    return DerivationElaborationResult(core_model, document, derivation_map)
