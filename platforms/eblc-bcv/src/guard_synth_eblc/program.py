"""High-level, evidence-bearing EBLC program representation."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import re
from typing import Any

from .derivation import DerivationSpec, DerivationValidationError, parse_derivation_spec
from .schema_validation import load_json, validate


PROGRAM_VERSION = "eblc-program-v0.1"
PROGRAM_VERSION_V02 = "eblc-program-v0.2"
SUPPORTED_PROGRAM_VERSIONS = (PROGRAM_VERSION, PROGRAM_VERSION_V02)
PROGRAM_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/eblc_program.schema.json"
PROGRAM_V02_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/eblc_program_v0_2.schema.json"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


class EBLCProgramValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SourcedQuantity:
    value: float
    unit: str | None
    frame: str | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EBLCProgram:
    raw: dict[str, Any]
    program_id: str
    frames: int
    claim_scope: str
    source_refs: tuple[str, ...]
    typed_derivation: DerivationSpec | None


def _refs(raw: dict[str, Any], field: str = "evidence_refs") -> tuple[str, ...]:
    return tuple(raw[field])


def _quantity(raw: dict[str, Any]) -> SourcedQuantity:
    return SourcedQuantity(float(raw["value"]), raw["unit"], raw["frame"], _refs(raw))


def _validate_v02_derivation(
    raw: dict[str, Any],
    *,
    source_refs: tuple[str, ...],
) -> DerivationSpec:
    try:
        spec = parse_derivation_spec(raw["typed_derivation"])
    except (DerivationValidationError, ValueError) as exc:
        raise EBLCProgramValidationError(f"invalid embedded typed derivation: {exc}") from exc
    if spec.horizon != int(raw["frames"]) + 1:
        raise EBLCProgramValidationError(
            f"embedded derivation horizon mismatch: {spec.horizon} != {int(raw['frames']) + 1}"
        )
    if not set(spec.source_refs).issubset(source_refs):
        raise EBLCProgramValidationError("embedded derivation source refs are outside program source refs")
    if spec.claim_scope != raw["claim_scope"]:
        raise EBLCProgramValidationError("embedded derivation claim scope mismatch")

    frame = raw["binding"]["coordinate_frame"]
    expected_outputs = {
        "stop_position": ("stop_position", "REAL", False, "m", frame),
        "stopping_distance": ("stopping_distance", "REAL", True, "m", frame),
    }
    actual_outputs = {item.output_id: item for item in spec.outputs}
    if set(actual_outputs) != set(expected_outputs):
        raise EBLCProgramValidationError("embedded derivation output interface mismatch")
    for output_id, expected in expected_outputs.items():
        output = actual_outputs[output_id]
        actual = (
            output.target_declaration, output.sort, output.time_varying,
            output.unit, output.frame,
        )
        if actual != expected:
            raise EBLCProgramValidationError(
                f"embedded derivation output interface mismatch: {output_id}"
            )
        if output.replace_clause_ids:
            raise EBLCProgramValidationError(
                f"embedded derivation cannot replace semantic clauses: {output_id}"
            )

    allowed_core_variables = {
        "ego_speed": ("REAL", True, "m/s", frame),
        "speed_epsilon": ("REAL", False, "m/s", frame),
        "response_time": ("REAL", False, "s", None),
        "deceleration": ("REAL", False, "m/s^2", frame),
    }
    embedded_core_names: set[str] = set()
    for symbol in spec.symbols:
        if symbol.kind != "CORE_VARIABLE":
            continue
        embedded_core_names.add(symbol.core_name or "")
        expected = allowed_core_variables.get(symbol.core_name or "")
        actual = (symbol.sort, symbol.time_varying, symbol.unit, symbol.frame)
        if expected is None or actual != expected:
            raise EBLCProgramValidationError(
                f"embedded derivation CORE_VARIABLE interface mismatch: {symbol.symbol_id}"
            )
    if embedded_core_names != set(allowed_core_variables):
        raise EBLCProgramValidationError(
            "embedded derivation CORE_VARIABLE interface is incomplete"
        )
    return spec


def parse_program(raw: dict[str, Any]) -> EBLCProgram:
    version = raw.get("program_version")
    if version == PROGRAM_VERSION:
        validate(raw, load_json(PROGRAM_SCHEMA_PATH))
    elif version == PROGRAM_VERSION_V02:
        validate(raw, load_json(PROGRAM_V02_SCHEMA_PATH))
    else:
        raise EBLCProgramValidationError(f"unsupported program version: {version}")
    if not _IDENTIFIER.fullmatch(raw["program_id"]):
        raise EBLCProgramValidationError(f"invalid program id: {raw['program_id']}")
    source_refs = tuple(raw["source_refs"])
    if len(source_refs) != len(set(source_refs)):
        raise EBLCProgramValidationError("duplicate source_refs")
    known = set(source_refs)
    referenced: list[tuple[str, tuple[str, ...]]] = [
        ("binding", _refs(raw["binding"])),
        ("predicate", _refs(raw["predicate"])),
        ("lifecycle", _refs(raw["lifecycle"])),
        ("priority", _refs(raw["priority"])),
    ]
    referenced.extend(
        (f"constraints.{name}", _quantity(value).evidence_refs)
        for name, value in raw["constraints"].items()
        if isinstance(value, dict)
    )
    if version == PROGRAM_VERSION:
        referenced.extend(
            (f"derivation_dag.{node['node_id']}", _refs(node, "source_refs"))
            for node in raw["derivation_dag"]
        )
    for owner, refs in referenced:
        if not refs or not set(refs).issubset(known):
            raise EBLCProgramValidationError(f"invalid or unknown evidence refs on {owner}")

    predicate = raw["predicate"]
    allowed = tuple(predicate["allowed_epistemic"])
    if len(allowed) != len(set(allowed)):
        raise EBLCProgramValidationError("duplicate allowed_epistemic values")
    if "CLAIMED" in allowed:
        raise EBLCProgramValidationError("CLAIMED cannot be an activation evidence source")

    lifecycle = raw["lifecycle"]
    quantities = {name: _quantity(value) for name, value in raw["constraints"].items() if isinstance(value, dict)}
    if any(not isfinite(value.value) for value in quantities.values()):
        raise EBLCProgramValidationError("non-finite sourced quantity")
    if quantities["position_uncertainty"].value < 0:
        raise EBLCProgramValidationError("position uncertainty must be nonnegative")
    if quantities["response_time"].value < 0:
        raise EBLCProgramValidationError("response time must be nonnegative")
    if quantities["deceleration"].value <= 0:
        raise EBLCProgramValidationError("deceleration must be positive")
    if any(quantities[name].value < 0 for name in ("position_epsilon", "speed_epsilon", "time_epsilon")):
        raise EBLCProgramValidationError("epsilon values must be nonnegative")

    typed_derivation = None
    if version == PROGRAM_VERSION:
        node_ids = [node["node_id"] for node in raw["derivation_dag"]]
        if len(node_ids) != len(set(node_ids)):
            raise EBLCProgramValidationError("duplicate derivation node id")
    else:
        typed_derivation = _validate_v02_derivation(raw, source_refs=source_refs)
    return EBLCProgram(
        raw=raw,
        program_id=raw["program_id"],
        frames=int(raw["frames"]),
        claim_scope=raw["claim_scope"],
        source_refs=source_refs,
        typed_derivation=typed_derivation,
    )


def load_program(path: Path) -> EBLCProgram:
    return parse_program(load_json(path))
