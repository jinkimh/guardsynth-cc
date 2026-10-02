"""Deterministic, synthetic public examples for EBLC language pipelines."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Iterable

from .composition import EBLCBundle, parse_bundle
from .derivation import DerivationSpec, parse_derivation_spec
from .program import EBLCProgram, load_program
from .schema_validation import load_json


PROGRAM_FIXTURE = Path(__file__).resolve().parent / "fixtures/eblc_program_p0b.json"
PROGRAM_V02_FIXTURE = Path(__file__).resolve().parent / "fixtures/eblc_program_p0b_v0_2.json"
SYNTHETIC_COMPOSITION_REF = "P0B-SYNTHETIC-COMPOSITION-POLICY-v0"


def synthetic_program_v02() -> EBLCProgram:
    """Load the public v0.2 fixture with its embedded full stopping DAG."""

    return load_program(PROGRAM_V02_FIXTURE)


def synthetic_stop_position_derivation(*, horizon: int = 9) -> DerivationSpec:
    """Typed replay of the public synthetic stop-position calculation."""

    rule_ref = "P0B-SYNTHETIC-SYSTEM-REQUIREMENT-PED-YIELD-v0"
    return parse_derivation_spec({
        "derivation_version": "eblc-derivation-v0.1",
        "derivation_id": "p0b_stop_position_derivation",
        "horizon": horizon,
        "claim_scope": "SYNTHETIC_TYPED_DERIVATION_NOT_VEHICLE_SAFETY",
        "source_refs": [rule_ref],
        "symbols": [
            {
                "symbol_id": "zone_entry_x",
                "kind": "SOURCED_VALUE",
                "sort": "REAL",
                "time_varying": False,
                "value": 0.0,
                "core_name": None,
                "unit": "m",
                "frame": "ego_path_s",
                "evidence_refs": [rule_ref],
            },
            {
                "symbol_id": "stop_margin",
                "kind": "SOURCED_VALUE",
                "sort": "REAL",
                "time_varying": False,
                "value": 1.5,
                "core_name": None,
                "unit": "m",
                "frame": "ego_path_s",
                "evidence_refs": [rule_ref],
            },
        ],
        "nodes": [{
            "node_id": "stop_position",
            "operation": "SUB",
            "inputs": ["symbol:zone_entry_x", "symbol:stop_margin"],
            "source_refs": [rule_ref],
        }],
        "outputs": [{
            "output_id": "stop_position",
            "node_ref": "node:stop_position",
            "target_declaration": "stop_position",
            "sort": "REAL",
            "time_varying": False,
            "unit": "m",
            "frame": "ego_path_s",
            "replace_clause_ids": ["bind_stop_position"],
            "evidence_refs": [rule_ref],
        }],
    })


def _synthetic_bundle(
    fixture: Path,
    tiers: Iterable[str] = ("HARD", "SERVICE"),
    allowed_actions: Iterable[Iterable[str]] = (("STOP",), ("PROCEED",)),
    overrides_contracts: Iterable[Iterable[str]] | None = None,
    *,
    bundle_id: str = "p0b_synthetic_composition_bundle",
) -> EBLCBundle:
    """Build a source-complete example without claiming law or vehicle safety."""

    tier_values = tuple(tiers)
    allowed_values = tuple(tuple(actions) for actions in allowed_actions)
    override_values = (
        tuple(tuple(items) for items in overrides_contracts)
        if overrides_contracts is not None
        else tuple(() for _ in tier_values)
    )
    if not (len(tier_values) == len(allowed_values) == len(override_values)):
        raise ValueError("synthetic bundle dimensions must match")
    base = load_json(fixture)
    contracts = []
    for index, (tier, actions, overrides) in enumerate(
        zip(tier_values, allowed_values, override_values)
    ):
        contract_id = f"C{index}"
        program = deepcopy(base)
        program["program_id"] = f"p0b_synthetic_composition_program_{index}"
        program["binding"]["contract_id"] = contract_id
        contracts.append({
            "contract_id": contract_id,
            "program": program,
            "priority_tier": tier,
            "allowed_actions": list(actions),
            "overrides_contracts": list(overrides),
            "evidence_refs": [SYNTHETIC_COMPOSITION_REF],
        })
    source_refs = list(dict.fromkeys(base["source_refs"] + [SYNTHETIC_COMPOSITION_REF]))
    return parse_bundle({
        "bundle_version": "eblc-bundle-v0.1",
        "bundle_id": bundle_id,
        "frames": base["frames"],
        "claim_scope": "SYNTHETIC_COMPOSITION_AND_BOUNDED_TRANSLATION_NOT_VEHICLE_SAFETY",
        "source_refs": source_refs,
        "action_domain": ["STOP", "CREEP", "PROCEED"],
        "contracts": contracts,
        "composition_evidence_refs": [SYNTHETIC_COMPOSITION_REF],
    })


def synthetic_bundle(
    tiers: Iterable[str] = ("HARD", "SERVICE"),
    allowed_actions: Iterable[Iterable[str]] = (("STOP",), ("PROCEED",)),
    overrides_contracts: Iterable[Iterable[str]] | None = None,
    *,
    bundle_id: str = "p0b_synthetic_composition_bundle",
) -> EBLCBundle:
    """Build a legacy v0.1-program bundle for compatibility tests."""

    return _synthetic_bundle(
        PROGRAM_FIXTURE,
        tiers,
        allowed_actions,
        overrides_contracts,
        bundle_id=bundle_id,
    )


def synthetic_bundle_v02(
    tiers: Iterable[str] = ("HARD", "SERVICE"),
    allowed_actions: Iterable[Iterable[str]] = (("STOP",), ("PROCEED",)),
    overrides_contracts: Iterable[Iterable[str]] | None = None,
    *,
    bundle_id: str = "p0b_synthetic_composition_bundle_v02",
) -> EBLCBundle:
    """Build a public bundle whose components embed typed derivation DAGs."""

    return _synthetic_bundle(
        PROGRAM_V02_FIXTURE,
        tiers,
        allowed_actions,
        overrides_contracts,
        bundle_id=bundle_id,
    )
