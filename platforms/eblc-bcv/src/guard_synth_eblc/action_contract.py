"""Versioned qualitative EBLC entry contracts lowered to the existing Core IR.

No scene parsing, normative inference, source certification or metric assurance.
Null identities are explicit conditional bindings, never source-complete claims.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re

from .core_ir import parse_core_model
from .schema_validation import load_json, validate

ACTION_CONTRACT_VERSION = "eblc-action-contract-v0.1"
ACTION_SCHEMA = Path(__file__).parent / "schemas/eblc_action_contract.schema.json"
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class ActionContract:
    raw: dict


def parse_action_contract(raw: dict) -> ActionContract:
    validate(raw, load_json(ACTION_SCHEMA))
    if raw["horizon"] > 32:
        raise ValueError("action contract horizon exceeds bounded v0.1 limit")
    if not IDENTIFIER.fullmatch(raw["contract_id"]):
        raise ValueError("invalid contract identifier")
    sources = raw["source_refs"]
    if len(sources) != len(set(sources)):
        raise ValueError("duplicate source reference")
    ids, predicates = set(), set()
    for ob in raw["obligations"]:
        for field, seen in (("obligation_id", ids), ("predicate_id", predicates)):
            if not IDENTIFIER.fullmatch(ob[field]) or ob[field] in seen:
                raise ValueError("invalid or duplicate obligation/predicate identifier")
            seen.add(ob[field])
        if (len(ob["source_refs"]) != len(set(ob["source_refs"]))
            or not set(ob["source_refs"]).issubset(sources) or ob["rule_ref"] not in ob["source_refs"]):
            raise ValueError("unbound obligation source/rule reference")
    return ActionContract(deepcopy(raw))


def var(name, offset=0):
    return {"op": "var", "name": name, "offset": offset}


def literal(value, enum=None):
    return {"op": "literal", "sort": "ENUM" if enum else "BOOL", "value": value,
            "enum_name": enum, "unit": None, "frame": None}


def binary(op, left, right):
    return {"op": op, "left": left, "right": right}


def conjunction(*args):
    return {"op": "and", "args": list(args)}


def neg(arg):
    return {"op": "not", "arg": arg}


def lower_action_contract(contract: ActionContract) -> dict:
    # Revalidate to reject post-parse mutation of the JSON held by the dataclass.
    raw = parse_action_contract(contract.raw).raw
    declarations, clauses = [], []
    refs = raw["source_refs"]

    def declare(name, sources, enum=None, values=(), varying=True):
        declarations.append({"name": name, "sort": "ENUM" if enum else "BOOL", "time_varying": varying,
            "enum_name": enum, "enum_values": list(values), "unit": None, "frame": None, "source_refs": sources})

    def clause(cid, kind, enforcement, formula, sources, description):
        clauses.append({"id": cid, "kind": kind, "enforcement": enforcement, "formula": formula,
                        "source_refs": sources, "description": description})

    clears, unresolved = [], []
    for ob in raw["obligations"]:
        oid, sources = ob["obligation_id"], ob["source_refs"]
        name = lambda suffix: oid + "_" + suffix
        declare(name("truth"), sources, "Truth", ("TRUE", "FALSE", "UNKNOWN", "CONFLICT"))
        for suffix in ("evidence_valid", "on", "clear", "active"):
            declare(name(suffix), sources)
        declare(name("prior_active"), sources, varying=False)
        for suffix, truth in (("on", "TRUE"), ("clear", "FALSE")):
            clause(name(suffix), "ACTIVATION" if suffix == "on" else "RELEASE", "EACH_FRAME",
                binary("eq", var(name(suffix)), conjunction(var(name("evidence_valid")),
                    binary("eq", var(name("truth")), literal(truth, "Truth")))), sources,
                "Confirmation is exactly valid evidence and the specified truth value.")
        def transition(offset, previous):
            return binary("eq", var(name("active"), offset), {"op": "ite",
                "condition": var(name("on"), offset), "then": literal(True),
                "else": {"op": "ite", "condition": var(name("clear"), offset),
                         "then": literal(False), "else": previous}})
        clause(name("initial"), "LIFECYCLE", "INITIAL", transition(0, var(name("prior_active"))), sources,
               "Observe before deciding; initial previous activation is an explicit input.")
        clause(name("transition"), "LIFECYCLE", "EACH_TRANSITION", transition(1, var(name("active"))), sources,
               "Confirm to activate/release; otherwise retain previous activation, including after release.")
        clause(name("no_entry"), "INVARIANT", "EACH_FRAME",
            binary("implies", var(name("active")), binary("ne", var("action"), literal("ENTER_ZONE", "Action"))),
            sources, "An active obligation forbids zone entry.")
        clears.append(var(name("clear")))
        unresolved.append({"op": "or", "args": [neg(var(name("evidence_valid"))),
            binary("eq", var(name("truth")), literal("UNKNOWN", "Truth")),
            binary("eq", var(name("truth")), literal("CONFLICT", "Truth"))]})
    declare("entry_permitted", refs)
    declare("review_required", refs)
    declare("action", refs, "Action", ("DEFER_ENTRY", "ENTER_ZONE"))
    clause("entry_gate", "FALLBACK", "EACH_FRAME", binary("eq", var("entry_permitted"), conjunction(*clears)), refs,
           "Entry permission requires confirmed clearance of every declared obligation.")
    clause("review_gate", "FALLBACK", "EACH_FRAME", binary("eq", var("review_required"), {"op": "or", "args": unresolved}), refs,
           "Any unknown, conflicting or invalid evidence requires review; it is not clearance.")
    clause("action_gate", "INVARIANT", "EACH_FRAME", binary("implies",
        binary("eq", var("action"), literal("ENTER_ZONE", "Action")), var("entry_permitted")), refs,
        "Without entry permission only DEFER_ENTRY is admissible; permission never forces entry.")
    core = {"grammar_version": "eblc-core-v0.1", "model_id": raw["contract_id"], "horizon": raw["horizon"],
        "source_refs": refs, "claim_scope": raw["claim_scope"], "declarations": declarations, "clauses": clauses,
        "queries": [{"id": "base_consistency", "formula": literal(True), "expected": "SAT",
                     "classification": "CONSISTENCY", "source_refs": refs, "description": "Non-vacuous base model."}]}
    parse_core_model(core)
    return core
