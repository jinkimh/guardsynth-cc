"""Elaborate a high-level EBLC bundle through Core IR to bounded SMT inputs."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

from .composition import EBLCBundle, LIVE_STATES, dominance_map
from .core_ir import CoreModel, parse_core_model
from .elaborator import ElaborationResult, elaborate_program


BUNDLE_ELABORATOR_VERSION = "eblc-bundle-elaborator-v0.2"
LIFECYCLE = ("INACTIVE", "CANDIDATE", "ACTIVE", "MAINTAINED", "RELEASED", "REACTIVATED", "EXPIRED")
VERDICT = ("VALIDATED", "REVIEW_REQUIRED", "UNSUPPORTED", "CONFLICT")


@dataclass(frozen=True, slots=True)
class BundleElaborationResult:
    core_model: CoreModel
    core_document: dict[str, Any]
    elaboration_map: dict[str, Any]
    component_elaborations: tuple[ElaborationResult, ...]


def _literal(
    sort: str,
    value: Any,
    *,
    enum_name: str | None = None,
    unit: str | None = None,
    frame: str | None = None,
) -> dict[str, Any]:
    return {
        "op": "literal", "sort": sort, "value": value,
        "enum_name": enum_name, "unit": unit, "frame": frame,
    }


def _var(name: str, offset: int = 0) -> dict[str, Any]:
    return {"op": "var", "name": name, "offset": offset}


def _not(argument: dict[str, Any]) -> dict[str, Any]:
    return {"op": "not", "arg": argument}


def _and(*arguments: dict[str, Any]) -> dict[str, Any]:
    if not arguments:
        return _literal("BOOL", True)
    return {"op": "and", "args": list(arguments)}


def _or(*arguments: dict[str, Any]) -> dict[str, Any]:
    if not arguments:
        return _literal("BOOL", False)
    return {"op": "or", "args": list(arguments)}


def _eq(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {"op": "eq", "left": left, "right": right}


def _enum(domain: str, value: str) -> dict[str, Any]:
    return _literal("ENUM", value, enum_name=domain)


def _ite(
    condition: dict[str, Any],
    then: dict[str, Any],
    otherwise: dict[str, Any],
) -> dict[str, Any]:
    return {"op": "ite", "condition": condition, "then": then, "else": otherwise}


def _namespace_expression(expression: dict[str, Any], prefix: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in expression.items():
        if key == "name" and expression.get("op") == "var":
            result[key] = f"{prefix}{value}"
        elif isinstance(value, dict):
            result[key] = _namespace_expression(value, prefix)
        elif isinstance(value, list):
            result[key] = [
                _namespace_expression(item, prefix) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def _live_state(state_expression: dict[str, Any]) -> dict[str, Any]:
    return _or(*(
        _eq(state_expression, _enum("Lifecycle", state))
        for state in ("ACTIVE", "MAINTAINED", "REACTIVATED")
    ))


def _declaration(
    name: str,
    sort: str,
    refs: list[str],
    *,
    enum_name: str | None = None,
    enum_values: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "name": name,
        "sort": sort,
        "time_varying": True,
        "enum_name": enum_name,
        "enum_values": list(enum_values),
        "unit": None,
        "frame": None,
        "source_refs": refs,
    }


def _clause(
    clause_id: str,
    kind: str,
    formula: dict[str, Any],
    refs: list[str],
    description: str,
) -> dict[str, Any]:
    return {
        "id": clause_id,
        "kind": kind,
        "enforcement": "EACH_TRANSITION",
        "formula": formula,
        "source_refs": refs,
        "description": description,
    }


def elaborate_bundle(bundle: EBLCBundle) -> BundleElaborationResult:
    """Compile every high-level contract and its composition into one Core model."""

    component_results = tuple(
        elaborate_program(component.program) for component in bundle.contracts
    )
    declarations: list[dict[str, Any]] = []
    clauses: list[dict[str, Any]] = []
    prefix_by_contract: dict[str, str] = {}
    for index, (component, result) in enumerate(zip(bundle.contracts, component_results)):
        prefix = f"c{index}__"
        prefix_by_contract[component.contract_id] = prefix
        for declaration in result.core_document["declarations"]:
            namespaced = dict(declaration)
            namespaced["name"] = f"{prefix}{declaration['name']}"
            declarations.append(namespaced)
        for clause in result.core_document["clauses"]:
            namespaced = dict(clause)
            namespaced["id"] = f"{prefix}{clause['id']}"
            namespaced["formula"] = _namespace_expression(clause["formula"], prefix)
            clauses.append(namespaced)

    composition_refs = list(bundle.composition_evidence_refs)
    selected_name = {
        item.contract_id: f"selected__{item.contract_id}" for item in bundle.contracts
    }
    admissible_name = {
        action: f"admissible__{action}" for action in bundle.action_domain
    }
    for item in bundle.contracts:
        declarations.append(_declaration(selected_name[item.contract_id], "BOOL", composition_refs))
    for action in bundle.action_domain:
        declarations.append(_declaration(admissible_name[action], "BOOL", composition_refs))
    declarations.extend([
        _declaration("safe_progress_action_exists", "BOOL", composition_refs),
        _declaration("composition_conflict", "BOOL", composition_refs),
        _declaration("composition_review_required", "BOOL", composition_refs),
        _declaration("composition_false_deadlock", "BOOL", composition_refs),
        _declaration(
            "composition_verdict", "ENUM", composition_refs,
            enum_name="Verdict", enum_values=VERDICT,
        ),
    ])

    live_expression = {
        item.contract_id: _live_state(_var(f"{prefix_by_contract[item.contract_id]}state", 1))
        for item in bundle.contracts
    }
    dominated = dominance_map(bundle)
    dominators = {
        item.contract_id: tuple(
            other.contract_id
            for other in bundle.contracts
            if item.contract_id in dominated[other.contract_id]
        )
        for item in bundle.contracts
    }
    for item in bundle.contracts:
        selected_formula = _and(
            live_expression[item.contract_id],
            *(_not(live_expression[other]) for other in dominators[item.contract_id]),
        )
        clauses.append(_clause(
            f"compose_select__{item.contract_id}",
            "FALLBACK",
            _eq(_var(selected_name[item.contract_id]), selected_formula),
            composition_refs,
            "Select a live contract only when no live higher/explicit dominator exists.",
        ))

    for action in bundle.action_domain:
        permitted_by_selected = []
        for item in bundle.contracts:
            permits = action in item.allowed_actions
            permitted_by_selected.append(_or(
                _not(_var(selected_name[item.contract_id])),
                _literal("BOOL", permits),
            ))
        clauses.append(_clause(
            f"compose_action__{action}",
            "FALLBACK",
            _eq(_var(admissible_name[action]), _and(*permitted_by_selected)),
            composition_refs,
            "An action is admissible exactly when every selected contract permits it.",
        ))

    no_action = _and(*(_not(_var(name)) for name in admissible_name.values()))
    hard_ids = [
        item.contract_id for item in bundle.contracts if item.priority_tier == "HARD"
    ]
    hard_pair_selected = _or(*(
        _and(_var(selected_name[left]), _var(selected_name[right]))
        for left, right in combinations(hard_ids, 2)
    ))
    conflict = _and(no_action, hard_pair_selected)
    review = _and(no_action, _not(conflict))
    false_deadlock = _and(_var("safe_progress_action_exists"), no_action)
    clauses.extend([
        _clause(
            "compose_hard_conflict", "FALLBACK",
            _eq(_var("composition_conflict"), conflict), composition_refs,
            "Empty action intersection from at least two selected hard contracts is a conflict.",
        ),
        _clause(
            "compose_review_required", "FALLBACK",
            _eq(_var("composition_review_required"), review), composition_refs,
            "Other empty action intersections require review and are not silently scalarized.",
        ),
        _clause(
            "compose_false_deadlock", "PROGRESS",
            _eq(_var("composition_false_deadlock"), false_deadlock), composition_refs,
            "Flag an empty admissible set when an independently supplied safe-progress action exists.",
        ),
    ])

    child_verdict = {
        value: _or(*(
            _eq(_var(f"{prefix_by_contract[item.contract_id]}verdict"), _enum("Verdict", value))
            for item in bundle.contracts
        ))
        for value in VERDICT
    }
    verdict_formula = _ite(
        _or(_var("composition_conflict"), child_verdict["CONFLICT"]),
        _enum("Verdict", "CONFLICT"),
        _ite(
            child_verdict["UNSUPPORTED"],
            _enum("Verdict", "UNSUPPORTED"),
            _ite(
                _or(_var("composition_review_required"), child_verdict["REVIEW_REQUIRED"]),
                _enum("Verdict", "REVIEW_REQUIRED"),
                _enum("Verdict", "VALIDATED"),
            ),
        ),
    )
    clauses.append(_clause(
        "compose_verdict", "FALLBACK",
        _eq(_var("composition_verdict"), verdict_formula), composition_refs,
        "Conflict, unsupported, review, then validated precedence across selected-action and child verdicts.",
    ))

    core_document = {
        "grammar_version": "eblc-core-v0.1",
        "model_id": f"{bundle.bundle_id}_core",
        "horizon": bundle.frames + 1,
        "declarations": declarations,
        "clauses": clauses,
        "queries": [{
            "id": "composed_model_satisfiable",
            "formula": _literal("BOOL", True),
            "expected": "SAT",
            "classification": "CONSISTENCY",
            "source_refs": composition_refs,
            "description": "The high-level bundle, generated Core, and composition constraints admit a bounded execution.",
        }],
        "source_refs": list(bundle.source_refs),
        "claim_scope": bundle.claim_scope,
    }
    core_model = parse_core_model(core_document)
    program_versions = {
        item.contract_id: item.program.raw["program_version"] for item in bundle.contracts
    }
    derived_outputs = {
        item.contract_id: (
            [output.output_id for output in item.program.typed_derivation.outputs]
            if item.program.typed_derivation is not None else []
        )
        for item in bundle.contracts
    }
    limitations = [
        "BOUNDED_DISCRETE_TIME",
        "FINITE_ENUMERATED_ACTION_DOMAIN",
    ]
    if any(item.program.typed_derivation is None for item in bundle.contracts):
        limitations.append("DERIVATION_PROVENANCE_PRESERVED_NOT_SYMBOLICALLY_REPLAYED")
    limitations.append("NOT_A_VEHICLE_SAFETY_PROOF")
    elaboration_map = {
        "bundle_id": bundle.bundle_id,
        "bundle_version": bundle.raw["bundle_version"],
        "bundle_elaborator_version": BUNDLE_ELABORATOR_VERSION,
        "core_model_id": core_model.model_id,
        "frames": bundle.frames,
        "core_horizon": core_model.horizon,
        "component_prefixes": prefix_by_contract,
        "component_programs": {
            item.contract_id: item.program.program_id for item in bundle.contracts
        },
        "component_program_versions": program_versions,
        "component_typed_derivations": {
            item.contract_id: (
                item.program.typed_derivation.derivation_id
                if item.program.typed_derivation is not None else None
            )
            for item in bundle.contracts
        },
        "component_derived_outputs": derived_outputs,
        "priority": {
            "tiers": ["HARD", "SERVICE", "PREFERENCE"],
            "dominance": {key: sorted(value) for key, value in dominated.items()},
            "compiled_as_scalar_weight": False,
        },
        "generated_composition_clauses": [
            clause["id"] for clause in clauses if clause["id"].startswith("compose_")
        ],
        "limitations": limitations,
    }
    return BundleElaborationResult(
        core_model=core_model,
        core_document=core_document,
        elaboration_map=elaboration_map,
        component_elaborations=component_results,
    )
