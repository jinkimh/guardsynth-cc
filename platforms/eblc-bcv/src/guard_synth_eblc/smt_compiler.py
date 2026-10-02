"""Generic EBLC Core IR to bounded SMT compiler.

This module lowers the typed, domain-neutral Core IR.  It does not import the
pedestrian P0b interpreter or its hand-written Z3 encoding.  Temporal operators
are expanded over the model's finite horizon and every query is checked in an
isolated solver against the same compiled base assertions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any, Mapping

from .core_ir import CoreModel, Declaration, Expression, declaration_map, type_check_model


try:
    import z3  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - CLI configures project-local Z3
    z3 = None


COMPILER_VERSION = "eblc-core-smt-compiler-v0.1"
_SAFE = re.compile(r"[^A-Za-z0-9_]" )


class SMTCompilationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LoweredExpression:
    term: Any
    side_constraints: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class AssertionRecord:
    assertion_id: str
    expression: Any
    clause_id: str
    kind: str
    enforcement: str
    base_time: int
    source_refs: tuple[str, ...]
    role: str = "FORMULA"


@dataclass(slots=True)
class CompiledCoreModel:
    model: CoreModel
    symbols: dict[tuple[str, int | None], Any]
    enum_codes: dict[str, dict[str, int]]
    assertions: tuple[AssertionRecord, ...]
    symbol_table: dict[str, Any]
    source_map: dict[str, Any]


def _require_z3() -> None:
    if z3 is None:
        raise SMTCompilationError("Z3 is unavailable; configure the project-local solver first")


def _safe_name(value: str) -> str:
    return _SAFE.sub("_", value)


def _symbol_name(model_id: str, declaration: Declaration, time: int | None) -> str:
    suffix = "const" if time is None else f"t{time}"
    return f"{_safe_name(model_id)}__{_safe_name(declaration.name)}__{suffix}"


def _make_symbol(name: str, sort: str):
    if sort == "BOOL":
        return z3.Bool(name)
    if sort in {"INT", "ENUM"}:
        return z3.Int(name)
    if sort == "REAL":
        return z3.Real(name)
    raise SMTCompilationError(f"unsupported declaration sort: {sort}")


def _literal(expression: Expression, enum_codes: dict[str, dict[str, int]]):
    sort = expression.literal_sort
    if sort == "BOOL":
        return z3.BoolVal(bool(expression.value))
    if sort == "INT":
        return z3.IntVal(int(expression.value))
    if sort == "REAL":
        return z3.RealVal(str(expression.value))
    if sort == "ENUM":
        domain = enum_codes.get(expression.enum_name or "")
        if domain is None or expression.value not in domain:
            raise SMTCompilationError(
                f"unknown enum literal {expression.enum_name}.{expression.value}"
            )
        return z3.IntVal(domain[str(expression.value)])
    raise SMTCompilationError(f"unsupported literal sort: {sort}")


def _combine(*items: LoweredExpression) -> tuple[Any, ...]:
    return tuple(constraint for item in items for constraint in item.side_constraints)


def _and(items: list[Any]):
    return z3.BoolVal(True) if not items else z3.And(*items)


def _or(items: list[Any]):
    return z3.BoolVal(False) if not items else z3.Or(*items)


def _lower(
    expression: Expression,
    *,
    base_time: int,
    model: CoreModel,
    declarations: dict[str, Declaration],
    symbols: dict[tuple[str, int | None], Any],
    enum_codes: dict[str, dict[str, int]],
) -> LoweredExpression:
    op = expression.op
    if op == "literal":
        return LoweredExpression(_literal(expression, enum_codes))
    if op == "var":
        declaration = declarations[expression.name or ""]
        time = base_time + expression.offset if declaration.time_varying else None
        try:
            return LoweredExpression(symbols[(declaration.name, time)])
        except KeyError as exc:  # defensive: type checker should catch this
            raise SMTCompilationError(f"variable outside compiled horizon: {declaration.name}@{time}") from exc

    if op in {"always", "eventually"}:
        lowered = [
            _lower(
                expression.args[0], base_time=base_time + offset, model=model,
                declarations=declarations, symbols=symbols, enum_codes=enum_codes,
            )
            for offset in range(expression.start, expression.end + 1)
        ]
        terms = [item.term for item in lowered]
        return LoweredExpression(
            _and(terms) if op == "always" else _or(terms),
            _combine(*lowered),
        )

    if op == "until":
        disjuncts: list[Any] = []
        constraints: list[Any] = []
        left, right = expression.args
        for witness_offset in range(expression.start, expression.end + 1):
            right_value = _lower(
                right, base_time=base_time + witness_offset, model=model,
                declarations=declarations, symbols=symbols, enum_codes=enum_codes,
            )
            prefix = [
                _lower(
                    left, base_time=base_time + offset, model=model,
                    declarations=declarations, symbols=symbols, enum_codes=enum_codes,
                )
                for offset in range(0, witness_offset)
            ]
            disjuncts.append(_and([item.term for item in prefix] + [right_value.term]))
            constraints.extend(right_value.side_constraints)
            constraints.extend(_combine(*prefix))
        return LoweredExpression(_or(disjuncts), tuple(constraints))

    lowered = tuple(
        _lower(
            child, base_time=base_time, model=model,
            declarations=declarations, symbols=symbols, enum_codes=enum_codes,
        )
        for child in expression.args
    )
    terms = tuple(item.term for item in lowered)
    constraints = _combine(*lowered)

    if op == "not":
        term = z3.Not(terms[0])
    elif op == "neg":
        term = -terms[0]
    elif op == "and":
        term = z3.And(*terms)
    elif op == "or":
        term = z3.Or(*terms)
    elif op == "implies":
        term = z3.Implies(terms[0], terms[1])
    elif op == "eq":
        term = terms[0] == terms[1]
    elif op == "ne":
        term = terms[0] != terms[1]
    elif op == "lt":
        term = terms[0] < terms[1]
    elif op == "le":
        term = terms[0] <= terms[1]
    elif op == "gt":
        term = terms[0] > terms[1]
    elif op == "ge":
        term = terms[0] >= terms[1]
    elif op == "add":
        term = terms[0] + terms[1]
    elif op == "sub":
        term = terms[0] - terms[1]
    elif op == "mul":
        term = terms[0] * terms[1]
    elif op == "div":
        term = terms[0] / terms[1]
        constraints = constraints + (terms[1] != 0,)
    elif op == "ite":
        term = z3.If(terms[0], terms[1], terms[2])
    else:
        raise SMTCompilationError(f"unsupported lowering op: {op}")
    return LoweredExpression(term, constraints)


def _enforcement_times(model: CoreModel, enforcement: str) -> tuple[int, ...]:
    if enforcement in {"INITIAL", "TRACE", "DECLARATIVE"}:
        return (0,)
    if enforcement == "EACH_FRAME":
        return tuple(range(model.horizon))
    if enforcement == "EACH_TRANSITION":
        return tuple(range(model.horizon - 1))
    raise SMTCompilationError(f"unknown enforcement mode: {enforcement}")


def compile_core_model(model: CoreModel) -> CompiledCoreModel:
    _require_z3()
    type_check_model(model)
    declarations = declaration_map(model)
    enum_codes: dict[str, dict[str, int]] = {}
    symbols: dict[tuple[str, int | None], Any] = {}
    symbol_records: list[dict[str, Any]] = []
    assertion_records: list[AssertionRecord] = []

    for declaration in model.declarations:
        if declaration.sort == "ENUM":
            enum_codes.setdefault(
                declaration.enum_name or "",
                {value: index for index, value in enumerate(declaration.enum_values)},
            )
        times: tuple[int | None, ...] = (
            tuple(range(model.horizon)) if declaration.time_varying else (None,)
        )
        for time in times:
            name = _symbol_name(model.model_id, declaration, time)
            symbol = _make_symbol(name, declaration.sort)
            symbols[(declaration.name, time)] = symbol
            symbol_records.append({
                "smt_symbol": name,
                "declaration": declaration.name,
                "time": time,
                "sort": declaration.sort,
                "enum_name": declaration.enum_name,
                "unit": declaration.unit,
                "frame": declaration.frame,
                "source_refs": list(declaration.source_refs),
            })
            if declaration.sort == "ENUM":
                codes = enum_codes[declaration.enum_name or ""]
                expression = z3.And(symbol >= min(codes.values()), symbol <= max(codes.values()))
                assertion_records.append(AssertionRecord(
                    f"domain__{declaration.name}__{time}", expression,
                    declaration.name, "DOMAIN", "DECLARATION", -1 if time is None else time,
                    declaration.source_refs, "ENUM_DOMAIN",
                ))

    for clause in model.clauses:
        if clause.enforcement == "DECLARATIVE":
            continue
        for base_time in _enforcement_times(model, clause.enforcement):
            lowered = _lower(
                clause.formula, base_time=base_time, model=model,
                declarations=declarations, symbols=symbols, enum_codes=enum_codes,
            )
            assertion_records.append(AssertionRecord(
                f"clause__{clause.clause_id}__t{base_time}", lowered.term,
                clause.clause_id, clause.kind, clause.enforcement, base_time,
                clause.source_refs,
            ))
            for index, side_constraint in enumerate(lowered.side_constraints):
                assertion_records.append(AssertionRecord(
                    f"side__{clause.clause_id}__t{base_time}__{index}", side_constraint,
                    clause.clause_id, clause.kind, clause.enforcement, base_time,
                    clause.source_refs, "DEFINEDNESS",
                ))

    indexed_assertions = tuple(enumerate(assertion_records))
    clause_source_map: dict[str, Any] = {}
    for clause in model.clauses:
        records = [
            (index, record)
            for index, record in indexed_assertions
            if record.clause_id == clause.clause_id
        ]
        clause_source_map[clause.clause_id] = {
            "kind": clause.kind,
            "enforcement": clause.enforcement,
            "description": clause.description,
            "source_refs": list(clause.source_refs),
            "assertion_indices": [index for index, _ in records],
            "assertion_ids": [record.assertion_id for _, record in records],
            "compiled": clause.enforcement != "DECLARATIVE",
        }

    source_map = {
        "model_id": model.model_id,
        "grammar_version": model.grammar_version,
        "compiler_version": COMPILER_VERSION,
        "assertions": [
            {
                "index": index,
                "assertion_id": record.assertion_id,
                "clause_id": record.clause_id,
                "role": record.role,
                "base_time": record.base_time,
                "source_refs": list(record.source_refs),
            }
            for index, record in indexed_assertions
        ],
        "clauses": clause_source_map,
        "queries": {
            query.query_id: {
                "classification": query.classification,
                "description": query.description,
                "source_refs": list(query.source_refs),
                "smt_file": f"QUERY_{query.query_id}.smt2",
                "base_assertion_count": len(assertion_records),
            }
            for query in model.queries
        },
    }
    symbol_table = {
        "model_id": model.model_id,
        "horizon": model.horizon,
        "symbols": symbol_records,
        "enum_codes": enum_codes,
    }
    return CompiledCoreModel(
        model, symbols, enum_codes, tuple(assertion_records), symbol_table, source_map
    )


def _new_base_solver(compiled: CompiledCoreModel):
    solver = z3.Solver()
    for record in compiled.assertions:
        solver.add(record.expression)
    return solver


def _z3_value(value: Any) -> bool | int | str:
    if z3.is_true(value):
        return True
    if z3.is_false(value):
        return False
    if z3.is_int_value(value):
        return value.as_long()
    if z3.is_rational_value(value):
        numerator = value.numerator_as_long()
        denominator = value.denominator_as_long()
        return str(numerator) if denominator == 1 else f"{numerator}/{denominator}"
    return str(value)


def _witness(compiled: CompiledCoreModel, solver_model: Any) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for record in compiled.symbol_table["symbols"]:
        name = record["smt_symbol"]
        declaration = record["declaration"]
        time = record["time"]
        symbol = compiled.symbols[(declaration, time)]
        value: Any = _z3_value(solver_model.eval(symbol, model_completion=True))
        enum_name = record["enum_name"]
        if enum_name is not None and isinstance(value, int):
            reverse = {code: label for label, code in compiled.enum_codes[enum_name].items()}
            value = reverse.get(value, f"INVALID_ENUM_CODE_{value}")
        values[name] = value
    return values


def check_queries(compiled: CompiledCoreModel) -> dict[str, Any]:
    declarations = declaration_map(compiled.model)
    results: list[dict[str, Any]] = []
    matches = 0
    for query in compiled.model.queries:
        lowered = _lower(
            query.formula, base_time=0, model=compiled.model,
            declarations=declarations, symbols=compiled.symbols,
            enum_codes=compiled.enum_codes,
        )
        solver = _new_base_solver(compiled)
        solver.add(*lowered.side_constraints)
        solver.add(lowered.term)
        checked = solver.check()
        status = "SAT" if checked == z3.sat else "UNSAT" if checked == z3.unsat else "UNKNOWN"
        matched = status == query.expected
        matches += int(matched)
        results.append({
            "query_id": query.query_id,
            "classification": query.classification,
            "expected": query.expected,
            "status": status,
            "matches_expected": matched,
            "description": query.description,
            "source_refs": list(query.source_refs),
            "definedness_constraint_count": len(lowered.side_constraints),
            "witness": _witness(compiled, solver.model()) if checked == z3.sat else None,
            "reason_unknown": solver.reason_unknown() if checked == z3.unknown else None,
            "smt2": solver.to_smt2(),
        })
    return {
        "model_id": compiled.model.model_id,
        "engine": "Z3_BOUNDED_SMT",
        "z3_version": z3.get_version_string(),
        "grammar_version": compiled.model.grammar_version,
        "compiler_version": COMPILER_VERSION,
        "query_count": len(results),
        "matches_expected": matches,
        "agreement": matches / len(results) if results else 0.0,
        "results": results,
    }


def solve_assignment(
    compiled: CompiledCoreModel,
    assignments: Mapping[tuple[str, int | None], bool | int | float | str],
) -> dict[str, Any]:
    """Solve one concrete/partial input assignment against a compiled model.

    Enum assignments use their public string labels.  The returned witness uses
    the same labels, which lets conformance code compare outputs without relying
    on private integer codes.
    """

    declarations = declaration_map(compiled.model)
    solver = _new_base_solver(compiled)
    for key, value in assignments.items():
        if key not in compiled.symbols:
            raise SMTCompilationError(f"assignment references unknown symbol/time: {key}")
        name, _ = key
        declaration = declarations[name]
        symbol = compiled.symbols[key]
        if declaration.sort == "BOOL":
            if not isinstance(value, bool):
                raise SMTCompilationError(f"BOOL assignment requires bool: {key}")
            encoded = z3.BoolVal(value)
        elif declaration.sort == "INT":
            if not isinstance(value, int) or isinstance(value, bool):
                raise SMTCompilationError(f"INT assignment requires int: {key}")
            encoded = z3.IntVal(value)
        elif declaration.sort == "REAL":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise SMTCompilationError(f"REAL assignment requires number: {key}")
            encoded = z3.RealVal(str(value))
        elif declaration.sort == "ENUM":
            codes = compiled.enum_codes[declaration.enum_name or ""]
            if not isinstance(value, str) or value not in codes:
                raise SMTCompilationError(f"invalid ENUM assignment {value!r} for {key}")
            encoded = z3.IntVal(codes[value])
        else:  # defensive: Core type checking already restricts sorts
            raise SMTCompilationError(f"unsupported assignment sort: {declaration.sort}")
        solver.add(symbol == encoded)
    checked = solver.check()
    status = "SAT" if checked == z3.sat else "UNSAT" if checked == z3.unsat else "UNKNOWN"
    return {
        "status": status,
        "assignment_count": len(assignments),
        "witness": _witness(compiled, solver.model()) if checked == z3.sat else None,
        "reason_unknown": solver.reason_unknown() if checked == z3.unknown else None,
    }


def export_compilation(compiled: CompiledCoreModel, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    base_solver = _new_base_solver(compiled)
    (output_dir / "MODEL.smt2").write_text(base_solver.to_smt2(), encoding="utf-8")
    (output_dir / "SYMBOL_TABLE.json").write_text(
        json.dumps(compiled.symbol_table, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "SOURCE_MAP.json").write_text(
        json.dumps(compiled.source_map, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    checked = check_queries(compiled)
    manifest_results: list[dict[str, Any]] = []
    for result in checked["results"]:
        query_path = output_dir / f"QUERY_{result['query_id']}.smt2"
        query_path.write_text(result.pop("smt2"), encoding="utf-8")
        manifest_results.append(result)
    checked["results"] = manifest_results
    (output_dir / "QUERY_MANIFEST.json").write_text(
        json.dumps(checked, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return checked
