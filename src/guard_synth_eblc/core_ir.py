"""Typed EBLC bounded discrete-time Core IR v0.1.

The Core IR is intentionally domain-neutral.  It represents declarations,
source-bearing lifecycle/guard clauses, bounded temporal expressions, and
counterexample queries.  Operational lowering lives in ``smt_compiler.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import re
from typing import Any

from .schema_validation import load_json, validate


GRAMMAR_VERSION = "eblc-core-v0.1"
CORE_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/eblc_core_ir.schema.json"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_NUMERIC_SORTS = {"INT", "REAL"}
_UNIT_DIMENSIONS = {
    None: (0, 0),
    "1": (0, 0),
    "m": (1, 0),
    "s": (0, 1),
    "m/s": (1, -1),
    "m/s^2": (1, -2),
}


class CoreIRValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Declaration:
    name: str
    sort: str
    time_varying: bool
    enum_name: str | None
    enum_values: tuple[str, ...]
    unit: str | None
    frame: str | None
    source_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Expression:
    op: str
    args: tuple["Expression", ...] = ()
    name: str | None = None
    offset: int = 0
    value: bool | int | float | str | None = None
    literal_sort: str | None = None
    enum_name: str | None = None
    unit: str | None = None
    frame: str | None = None
    start: int = 0
    end: int = 0


@dataclass(frozen=True, slots=True)
class Clause:
    clause_id: str
    kind: str
    enforcement: str
    formula: Expression
    source_refs: tuple[str, ...]
    description: str


@dataclass(frozen=True, slots=True)
class Query:
    query_id: str
    formula: Expression
    expected: str
    classification: str
    source_refs: tuple[str, ...]
    description: str


@dataclass(frozen=True, slots=True)
class CoreModel:
    grammar_version: str
    model_id: str
    horizon: int
    declarations: tuple[Declaration, ...]
    clauses: tuple[Clause, ...]
    queries: tuple[Query, ...]
    source_refs: tuple[str, ...]
    claim_scope: str


@dataclass(frozen=True, slots=True)
class TypeInfo:
    sort: str
    dimensions: tuple[int, int] = (0, 0)
    frame: str | None = None
    enum_name: str | None = None


def _parse_expression(raw: dict[str, Any]) -> Expression:
    op = raw["op"]
    if op == "literal":
        return Expression(
            op,
            value=raw["value"],
            literal_sort=raw["sort"],
            enum_name=raw["enum_name"],
            unit=raw["unit"],
            frame=raw["frame"],
        )
    if op == "var":
        return Expression(op, name=raw["name"], offset=raw["offset"])
    if op in {"not", "neg"}:
        return Expression(op, (_parse_expression(raw["arg"]),))
    if op in {"and", "or"}:
        return Expression(op, tuple(_parse_expression(item) for item in raw["args"]))
    if op in {"implies", "eq", "ne", "lt", "le", "gt", "ge", "add", "sub", "mul", "div"}:
        return Expression(op, (_parse_expression(raw["left"]), _parse_expression(raw["right"])))
    if op == "ite":
        return Expression(
            op,
            (
                _parse_expression(raw["condition"]),
                _parse_expression(raw["then"]),
                _parse_expression(raw["else"]),
            ),
        )
    if op in {"always", "eventually"}:
        return Expression(
            op,
            (_parse_expression(raw["arg"]),),
            start=raw["start"],
            end=raw["end"],
        )
    if op == "until":
        return Expression(
            op,
            (_parse_expression(raw["left"]), _parse_expression(raw["right"])),
            start=raw["start"],
            end=raw["end"],
        )
    raise CoreIRValidationError(f"unsupported expression op: {op}")


def parse_core_model(raw: dict[str, Any]) -> CoreModel:
    validate(raw, load_json(CORE_SCHEMA_PATH))
    model = CoreModel(
        grammar_version=raw["grammar_version"],
        model_id=raw["model_id"],
        horizon=raw["horizon"],
        declarations=tuple(
            Declaration(
                item["name"],
                item["sort"],
                item["time_varying"],
                item["enum_name"],
                tuple(item["enum_values"]),
                item["unit"],
                item["frame"],
                tuple(item["source_refs"]),
            )
            for item in raw["declarations"]
        ),
        clauses=tuple(
            Clause(
                item["id"],
                item["kind"],
                item["enforcement"],
                _parse_expression(item["formula"]),
                tuple(item["source_refs"]),
                item["description"],
            )
            for item in raw["clauses"]
        ),
        queries=tuple(
            Query(
                item["id"],
                _parse_expression(item["formula"]),
                item["expected"],
                item["classification"],
                tuple(item["source_refs"]),
                item["description"],
            )
            for item in raw["queries"]
        ),
        source_refs=tuple(raw["source_refs"]),
        claim_scope=raw["claim_scope"],
    )
    type_check_model(model)
    return model


def load_core_model(path: Path) -> CoreModel:
    return parse_core_model(load_json(path))


def _unit_dimensions(unit: str | None) -> tuple[int, int]:
    if unit not in _UNIT_DIMENSIONS:
        raise CoreIRValidationError(f"unsupported Core v0 unit: {unit}")
    return _UNIT_DIMENSIONS[unit]


def _compatible_numeric(left: TypeInfo, right: TypeInfo, operation: str) -> None:
    if left.sort not in _NUMERIC_SORTS or right.sort not in _NUMERIC_SORTS:
        raise CoreIRValidationError(f"{operation} requires numeric operands")
    if left.dimensions != right.dimensions:
        raise CoreIRValidationError(
            f"{operation} unit mismatch: {left.dimensions} vs {right.dimensions}"
        )
    if left.frame and right.frame and left.frame != right.frame:
        raise CoreIRValidationError(f"{operation} frame mismatch: {left.frame} vs {right.frame}")


def _same_value_type(left: TypeInfo, right: TypeInfo, operation: str) -> None:
    if left.sort in _NUMERIC_SORTS and right.sort in _NUMERIC_SORTS:
        _compatible_numeric(left, right, operation)
        return
    if left.sort != right.sort:
        raise CoreIRValidationError(f"{operation} sort mismatch: {left.sort} vs {right.sort}")
    if left.sort == "ENUM" and left.enum_name != right.enum_name:
        raise CoreIRValidationError(
            f"{operation} enum mismatch: {left.enum_name} vs {right.enum_name}"
        )


def _expression_type(
    expression: Expression,
    declarations: dict[str, Declaration],
    *,
    horizon: int,
    base_time: int = 0,
) -> TypeInfo:
    op = expression.op
    if op == "literal":
        sort = expression.literal_sort or ""
        value = expression.value
        if sort == "BOOL" and not isinstance(value, bool):
            raise CoreIRValidationError("BOOL literal must contain a boolean")
        if sort == "INT" and (not isinstance(value, int) or isinstance(value, bool)):
            raise CoreIRValidationError("INT literal must contain an integer")
        if sort == "REAL" and (
            not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value)
        ):
            raise CoreIRValidationError("REAL literal must contain a finite number")
        if sort == "ENUM" and (not isinstance(value, str) or not expression.enum_name):
            raise CoreIRValidationError("ENUM literal requires a string value and enum_name")
        if sort in {"BOOL", "ENUM"} and (expression.unit is not None or expression.frame is not None):
            raise CoreIRValidationError(f"{sort} literal cannot carry unit/frame")
        if sort in _NUMERIC_SORTS:
            return TypeInfo(sort, _unit_dimensions(expression.unit), expression.frame)
        return TypeInfo(sort, enum_name=expression.enum_name)

    if op == "var":
        if expression.name not in declarations:
            raise CoreIRValidationError(f"unknown variable: {expression.name}")
        declaration = declarations[expression.name]
        if not declaration.time_varying and expression.offset != 0:
            raise CoreIRValidationError(f"constant variable cannot use offset: {expression.name}")
        time = base_time + expression.offset
        if declaration.time_varying and not 0 <= time < horizon:
            raise CoreIRValidationError(
                f"variable reference outside horizon: {expression.name}@{time}"
            )
        return TypeInfo(
            declaration.sort,
            _unit_dimensions(declaration.unit),
            declaration.frame,
            declaration.enum_name,
        )

    if op in {"always", "eventually", "until"}:
        if expression.start > expression.end:
            raise CoreIRValidationError(f"{op} start must be <= end")
        if base_time + expression.end >= horizon:
            raise CoreIRValidationError(f"{op} window exceeds horizon")
        temporal_args = expression.args
        for arg_index, temporal_arg in enumerate(temporal_args):
            first_time = base_time + expression.start
            if op == "until" and arg_index == 0:
                # Bounded-until requires its left operand from the current
                # instant until the instant before the right operand holds.
                first_time = base_time
            for time in range(first_time, base_time + expression.end + 1):
                result = _expression_type(temporal_arg, declarations, horizon=horizon, base_time=time)
                if result.sort != "BOOL":
                    raise CoreIRValidationError(f"{op} requires boolean operands")
        return TypeInfo("BOOL")

    child_types = tuple(
        _expression_type(item, declarations, horizon=horizon, base_time=base_time)
        for item in expression.args
    )
    if op == "not":
        if child_types[0].sort != "BOOL":
            raise CoreIRValidationError("not requires BOOL")
        return TypeInfo("BOOL")
    if op == "neg":
        if child_types[0].sort not in _NUMERIC_SORTS:
            raise CoreIRValidationError("neg requires numeric input")
        return child_types[0]
    if op in {"and", "or"}:
        if any(item.sort != "BOOL" for item in child_types):
            raise CoreIRValidationError(f"{op} requires BOOL arguments")
        return TypeInfo("BOOL")
    if op == "implies":
        if child_types[0].sort != "BOOL" or child_types[1].sort != "BOOL":
            raise CoreIRValidationError("implies requires BOOL operands")
        return TypeInfo("BOOL")
    if op in {"eq", "ne"}:
        _same_value_type(child_types[0], child_types[1], op)
        return TypeInfo("BOOL")
    if op in {"lt", "le", "gt", "ge"}:
        _compatible_numeric(child_types[0], child_types[1], op)
        return TypeInfo("BOOL")
    if op in {"add", "sub"}:
        _compatible_numeric(child_types[0], child_types[1], op)
        return TypeInfo(
            "REAL" if "REAL" in {child_types[0].sort, child_types[1].sort} else "INT",
            child_types[0].dimensions,
            child_types[0].frame or child_types[1].frame,
        )
    if op in {"mul", "div"}:
        if any(item.sort not in _NUMERIC_SORTS for item in child_types):
            raise CoreIRValidationError(f"{op} requires numeric operands")
        if child_types[0].frame and child_types[1].frame and child_types[0].frame != child_types[1].frame:
            raise CoreIRValidationError(f"{op} frame mismatch")
        dimensions = (
            child_types[0].dimensions[0] + (1 if op == "mul" else -1) * child_types[1].dimensions[0],
            child_types[0].dimensions[1] + (1 if op == "mul" else -1) * child_types[1].dimensions[1],
        )
        return TypeInfo(
            "REAL" if op == "div" or "REAL" in {child_types[0].sort, child_types[1].sort} else "INT",
            dimensions,
            child_types[0].frame or child_types[1].frame,
        )
    if op == "ite":
        if child_types[0].sort != "BOOL":
            raise CoreIRValidationError("ite condition must be BOOL")
        _same_value_type(child_types[1], child_types[2], "ite")
        if child_types[1].sort in _NUMERIC_SORTS:
            return TypeInfo(
                "REAL" if "REAL" in {child_types[1].sort, child_types[2].sort} else "INT",
                child_types[1].dimensions,
                child_types[1].frame or child_types[2].frame,
            )
        return child_types[1]
    raise CoreIRValidationError(f"unsupported expression op: {op}")


def type_check_model(model: CoreModel) -> None:
    if model.grammar_version != GRAMMAR_VERSION:
        raise CoreIRValidationError(f"unsupported grammar version: {model.grammar_version}")
    if not _IDENTIFIER.fullmatch(model.model_id):
        raise CoreIRValidationError(f"invalid model identifier: {model.model_id}")
    source_set = set(model.source_refs)
    if len(source_set) != len(model.source_refs):
        raise CoreIRValidationError("duplicate model source_refs")

    declarations: dict[str, Declaration] = {}
    enum_domains: dict[str, tuple[str, ...]] = {}
    for declaration in model.declarations:
        if not _IDENTIFIER.fullmatch(declaration.name):
            raise CoreIRValidationError(f"invalid declaration name: {declaration.name}")
        if declaration.name in declarations:
            raise CoreIRValidationError(f"duplicate declaration: {declaration.name}")
        if not declaration.source_refs:
            raise CoreIRValidationError(f"declaration has no source refs: {declaration.name}")
        if not set(declaration.source_refs).issubset(source_set):
            raise CoreIRValidationError(f"unknown source ref on declaration: {declaration.name}")
        _unit_dimensions(declaration.unit)
        if declaration.sort == "ENUM":
            if not declaration.enum_name or not declaration.enum_values:
                raise CoreIRValidationError(f"ENUM declaration requires enum_name/values: {declaration.name}")
            if len(set(declaration.enum_values)) != len(declaration.enum_values):
                raise CoreIRValidationError(f"duplicate ENUM values: {declaration.name}")
            previous = enum_domains.setdefault(declaration.enum_name, declaration.enum_values)
            if previous != declaration.enum_values:
                raise CoreIRValidationError(f"inconsistent ENUM domain: {declaration.enum_name}")
            if declaration.unit is not None or declaration.frame is not None:
                raise CoreIRValidationError(f"ENUM declaration cannot carry unit/frame: {declaration.name}")
        elif declaration.enum_name is not None or declaration.enum_values:
            raise CoreIRValidationError(f"non-ENUM declaration has enum metadata: {declaration.name}")
        if declaration.sort == "BOOL" and (declaration.unit is not None or declaration.frame is not None):
            raise CoreIRValidationError(f"BOOL declaration cannot carry unit/frame: {declaration.name}")
        declarations[declaration.name] = declaration

    def check_enum_literals(expression: Expression) -> None:
        if expression.op == "literal" and expression.literal_sort == "ENUM":
            domain = enum_domains.get(expression.enum_name or "")
            if domain is None:
                raise CoreIRValidationError(
                    f"ENUM literal references unknown domain: {expression.enum_name}"
                )
            if expression.value not in domain:
                raise CoreIRValidationError(
                    f"ENUM literal {expression.value!r} is outside {expression.enum_name}"
                )
        for child in expression.args:
            check_enum_literals(child)

    identifiers: set[str] = set()
    for clause in model.clauses:
        if not _IDENTIFIER.fullmatch(clause.clause_id) or clause.clause_id in identifiers:
            raise CoreIRValidationError(f"invalid or duplicate clause id: {clause.clause_id}")
        identifiers.add(clause.clause_id)
        if not set(clause.source_refs).issubset(source_set):
            raise CoreIRValidationError(f"unknown source ref on clause: {clause.clause_id}")
        check_enum_literals(clause.formula)
        times = {
            "INITIAL": (0,),
            "EACH_FRAME": tuple(range(model.horizon)),
            "EACH_TRANSITION": tuple(range(model.horizon - 1)),
            "TRACE": (0,),
            "DECLARATIVE": (0,),
        }[clause.enforcement]
        for time in times:
            result = _expression_type(clause.formula, declarations, horizon=model.horizon, base_time=time)
            if result.sort != "BOOL":
                raise CoreIRValidationError(f"clause must be BOOL: {clause.clause_id}")

    for query in model.queries:
        if not _IDENTIFIER.fullmatch(query.query_id) or query.query_id in identifiers:
            raise CoreIRValidationError(f"invalid or duplicate query id: {query.query_id}")
        identifiers.add(query.query_id)
        if not set(query.source_refs).issubset(source_set):
            raise CoreIRValidationError(f"unknown source ref on query: {query.query_id}")
        check_enum_literals(query.formula)
        result = _expression_type(query.formula, declarations, horizon=model.horizon)
        if result.sort != "BOOL":
            raise CoreIRValidationError(f"query must be BOOL: {query.query_id}")


def declaration_map(model: CoreModel) -> dict[str, Declaration]:
    return {item.name: item for item in model.declarations}
