"""Common M15 baseline registry, channel firewall, and deterministic adapters."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from guard_synth_eblc.schema_validation import load_json, validate

from .catalog_retrieval import BM25CatalogRetriever, GraphPredicateRetriever, RetrievalQuery
from .coc_conditioned_frontend import build_constraint_proposals, parse_frontend_request
from .source_catalog import SourceCatalog


PROTOCOL_VERSION = "guardsynth-baseline-protocol-v0.1"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/baseline_result.schema.json"
ALL_BASELINES = ("B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B13")
_CLAIM_SCOPE = "M15_BASELINE_INTERFACE_SMOKE_NOT_COMPARATIVE_EFFECT_OR_VEHICLE_SAFETY"


@dataclass(frozen=True, slots=True)
class BaselineSpec:
    baseline_id: str
    version: str
    adapter_class: str
    channels: tuple[str, ...]


BASELINE_REGISTRY = {
    item.baseline_id: item for item in (
        BaselineSpec("B0", "controlled-template-prior-v0.1", "CONTROLLED_PRIOR", ("SLICE", "CATALOG")),
        BaselineSpec("B1", "coc-only-free-form-provider-v0.1", "EXTERNAL_MODEL_ADAPTER", ("COC",)),
        BaselineSpec("B2", "scene-only-model-provider-v0.1", "EXTERNAL_MODEL_ADAPTER", ("SCENE",)),
        BaselineSpec("B3", "template-retrieval-only-v0.1", "GRAPH_RETRIEVAL", ("SCENE", "CATALOG")),
        BaselineSpec("B4", "coc-scene-template-retrieval-v0.1", "M14_GRAPH_FRONTEND", ("COC", "SCENE", "CATALOG")),
        BaselineSpec("B5", "drivereg-style-bm25-v0.1", "STYLE_ADAPTER_NOT_REPRODUCTION", ("COC", "SCENE", "CATALOG")),
        BaselineSpec("B6", "rtcd-style-scene-filter-v0.1", "STYLE_ADAPTER_NOT_REPRODUCTION", ("SCENE", "CATALOG")),
        BaselineSpec("B7", "physics-only-envelope-v0.1", "DETERMINISTIC_PHYSICS_BINDER", ("PHYSICS", "ASSURANCE")),
        BaselineSpec("B8", "sandra-like-action-filter-v0.1", "STYLE_ADAPTER_NOT_REPRODUCTION", ("RULE", "REACHABILITY")),
        BaselineSpec("B13", "naive-b5-b6-b8-v0.1", "EXPLICIT_SERIAL_COMPOSITION", ("COC", "SCENE", "CATALOG", "REACHABILITY")),
    )
}


def baseline_manifest() -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "baselines": [
            {
                "baseline_id": BASELINE_REGISTRY[key].baseline_id,
                "version": BASELINE_REGISTRY[key].version,
                "adapter_class": BASELINE_REGISTRY[key].adapter_class,
                "declared_channels": list(BASELINE_REGISTRY[key].channels),
            }
            for key in ALL_BASELINES
        ],
        "locked_after_evaluation_start": True,
        "oracle_independence": "BASELINES_DO_NOT_READ_LOCKED_EXPECTED_LABELS",
    }


def _result(
    spec: BaselineSpec,
    *,
    used_channels: tuple[str, ...],
    status: str,
    reasons: list[str],
    candidates: list[dict[str, Any]],
    numeric_parameters: dict[str, Any] | None = None,
    action_set: list[str] | None = None,
) -> dict[str, Any]:
    if not set(used_channels).issubset(spec.channels):
        raise ValueError("BASELINE_CHANNEL_FIREWALL_VIOLATION")
    value = {
        "protocol_version": PROTOCOL_VERSION,
        "baseline_id": spec.baseline_id,
        "baseline_version": spec.version,
        "adapter_class": spec.adapter_class,
        "declared_channels": list(spec.channels),
        "used_channels": list(used_channels),
        "status": status,
        "reason_codes": reasons,
        "candidates": candidates,
        "numeric_parameters": numeric_parameters,
        "action_set": action_set,
        "claim_scope": _CLAIM_SCOPE,
        "oracle_independence": "DOES_NOT_READ_LOCKED_EXPECTED_LABELS",
    }
    validate(value, load_json(SCHEMA_PATH))
    return value


def _claim_sources(catalog: SourceCatalog) -> dict[str, str]:
    return {
        claim["claim_id"]: record["evidence_id"]
        for record in catalog.raw["source_records"]
        for claim in record["claims"]
    }


def _source_refs(rule: dict[str, Any], catalog: SourceCatalog) -> list[str]:
    sources = _claim_sources(catalog)
    return sorted({
        *rule["source_claim_refs"],
        *(sources[claim] for claim in rule["source_claim_refs"]),
    })


def _retrieval_candidates(
    raw: dict[str, Any],
    catalog: SourceCatalog,
    retriever: GraphPredicateRetriever | BM25CatalogRetriever,
) -> list[dict[str, Any]]:
    query = RetrievalQuery(
        slice_hint=raw["slice_hint"],
        scene_predicates=tuple(sorted({item["predicate_id"] for item in raw["scene_facts"]})),
        scene_tags=tuple(sorted(raw["scene_tags"])),
        coc_concepts=(),
    )
    rules = {item["rule_id"]: item for item in catalog.raw["rule_templates"]}
    return [
        {
            "rule_id": item.rule_id,
            "rank": rank,
            "verdict": None,
            "source_refs": _source_refs(rules[item.rule_id], catalog),
            "score": item.score,
        }
        for rank, item in enumerate(retriever.retrieve(catalog, query), start=1)
    ]


def _proposal_candidates(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "rule_id": item["rule_id"],
            "rank": rank,
            "verdict": item["verdict"],
            "source_refs": sorted({
                *item["source_claim_refs"], *item["source_record_refs"]
            }),
            "score": item["retrieval_score"],
        }
        for rank, item in enumerate(proposals, start=1)
    ]


def _neutral_scene_request(raw: dict[str, Any]) -> dict[str, Any]:
    neutral = deepcopy(raw)
    neutral_text = "상황 정보를 검토한다."
    neutral["coc"] = {
        "text": neutral_text,
        "language": "ko",
        "epistemic_kind": "CLAIMED",
        "evidence_ref": "coc-sha256:" + hashlib.sha256(
            neutral_text.encode("utf-8")
        ).hexdigest(),
    }
    return neutral


def _provider_candidates(
    rule_ids: Any,
    raw: dict[str, Any],
    catalog: SourceCatalog,
) -> list[dict[str, Any]]:
    if (
        not isinstance(rule_ids, (list, tuple))
        or any(not isinstance(item, str) or not item for item in rule_ids)
        or len(rule_ids) != len(set(rule_ids))
    ):
        raise ValueError("INVALID_EXTERNAL_MODEL_PROVIDER_OUTPUT")
    rules = {item["rule_id"]: item for item in catalog.raw["rule_templates"]}
    if any(
        rule_id not in rules or rules[rule_id]["slice"] != raw["slice_hint"]
        for rule_id in rule_ids
    ):
        raise ValueError("INVALID_EXTERNAL_MODEL_PROVIDER_OUTPUT")
    return [
        {
            "rule_id": rule_id,
            "rank": rank,
            "verdict": None,
            "source_refs": _source_refs(rules[rule_id], catalog),
            "score": None,
        }
        for rank, rule_id in enumerate(rule_ids, start=1)
    ]


def run_baseline(
    baseline_id: str,
    *,
    request_raw: dict[str, Any],
    catalog: SourceCatalog,
    auxiliary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if baseline_id not in BASELINE_REGISTRY:
        raise ValueError("UNKNOWN_BASELINE_ID")
    spec = BASELINE_REGISTRY[baseline_id]
    raw = deepcopy(request_raw)
    parse_frontend_request(raw)
    auxiliary = dict(auxiliary or {})

    if baseline_id == "B0":
        rules = [
            item for item in catalog.raw["rule_templates"]
            if item["slice"] == raw["slice_hint"]
        ]
        rule = sorted(rules, key=lambda item: item["rule_id"])[0]
        return _result(spec, used_channels=("SLICE", "CATALOG"), status="EXECUTED",
                       reasons=["CONTROLLED_PRIOR_NOT_EMPIRICAL_FREQUENCY"],
                       candidates=[{"rule_id": rule["rule_id"], "rank": 1,
                                    "verdict": None, "source_refs": _source_refs(rule, catalog),
                                    "score": None}])
    if baseline_id == "B1":
        provider = auxiliary.get("coc_model_provider")
        if callable(provider):
            try:
                candidates = _provider_candidates(provider({
                    "slice": raw["slice_hint"],
                    "coc": deepcopy(raw["coc"]),
                }), raw, catalog)
            except (TypeError, ValueError):
                return _result(spec, used_channels=("COC",), status="UNSUPPORTED",
                               reasons=["INVALID_EXTERNAL_MODEL_PROVIDER_OUTPUT"], candidates=[])
            return _result(
                spec,
                used_channels=("COC",),
                status="EXECUTED",
                reasons=[],
                candidates=candidates,
            )
        return _result(spec, used_channels=("COC",), status="UNSUPPORTED",
                       reasons=["EXTERNAL_FREE_FORM_MODEL_PROVIDER_NOT_CONFIGURED"], candidates=[])
    if baseline_id == "B2":
        provider = auxiliary.get("scene_model_provider")
        if callable(provider):
            try:
                candidates = _provider_candidates(provider({
                    "slice": raw["slice_hint"],
                    "scene_tags": deepcopy(raw["scene_tags"]),
                    "scene_facts": deepcopy(raw["scene_facts"]),
                }), raw, catalog)
            except (TypeError, ValueError):
                return _result(spec, used_channels=("SCENE",), status="UNSUPPORTED",
                               reasons=["INVALID_EXTERNAL_MODEL_PROVIDER_OUTPUT"], candidates=[])
            return _result(
                spec,
                used_channels=("SCENE",),
                status="EXECUTED",
                reasons=[],
                candidates=candidates,
            )
        return _result(spec, used_channels=("SCENE",), status="UNSUPPORTED",
                       reasons=["EXTERNAL_SCENE_MODEL_PROVIDER_NOT_CONFIGURED"], candidates=[])
    if baseline_id == "B3":
        return _result(spec, used_channels=("SCENE", "CATALOG"), status="EXECUTED", reasons=[],
                       candidates=_retrieval_candidates(raw, catalog, GraphPredicateRetriever()))
    if baseline_id in {"B4", "B5", "B6"}:
        input_raw = _neutral_scene_request(raw) if baseline_id == "B6" else raw
        retriever = BM25CatalogRetriever() if baseline_id == "B5" else GraphPredicateRetriever()
        proposals = build_constraint_proposals(
            parse_frontend_request(input_raw), catalog, retriever=retriever
        )["proposals"]
        channels = ("SCENE", "CATALOG") if baseline_id == "B6" else ("COC", "SCENE", "CATALOG")
        return _result(spec, used_channels=channels, status="EXECUTED", reasons=[],
                       candidates=_proposal_candidates(proposals))
    if baseline_id == "B7":
        required = {
            "ego_speed_mps", "distance_to_boundary_m", "deceleration_mps2",
            "response_time_s", "physics_evidence_refs",
        }
        if not required.issubset(auxiliary):
            return _result(spec, used_channels=(), status="UNSUPPORTED",
                           reasons=["MISSING_PHYSICS_OR_ASSURANCE_INPUT"], candidates=[])
        speed = float(auxiliary["ego_speed_mps"])
        delay = float(auxiliary["response_time_s"])
        deceleration = float(auxiliary["deceleration_mps2"])
        distance = float(auxiliary["distance_to_boundary_m"])
        if speed < 0 or delay < 0 or deceleration <= 0 or distance < 0:
            return _result(spec, used_channels=("PHYSICS", "ASSURANCE"), status="UNSUPPORTED",
                           reasons=["INVALID_PHYSICS_OR_ASSURANCE_INPUT"], candidates=[])
        stopping_distance = speed * delay + speed * speed / (2.0 * deceleration)
        return _result(spec, used_channels=("PHYSICS", "ASSURANCE"), status="EXECUTED",
                       reasons=[], candidates=[], numeric_parameters={
                           "stopping_distance_m": stopping_distance,
                           "within_boundary": stopping_distance <= distance,
                           "evidence_refs": list(auxiliary["physics_evidence_refs"]),
                       })
    if baseline_id == "B8":
        actions = auxiliary.get("reachable_actions")
        permitted = auxiliary.get("rule_permitted_actions")
        if (
            not isinstance(actions, list)
            or not isinstance(permitted, list)
            or not auxiliary.get("reachability_evidence_ref")
        ):
            return _result(spec, used_channels=(), status="UNSUPPORTED",
                           reasons=["MISSING_REACHABILITY_OR_RULE_ACTION_SET"], candidates=[])
        action_set = sorted(set(actions).intersection(permitted))
        return _result(spec, used_channels=("RULE", "REACHABILITY"),
                       status="EXECUTED" if action_set else "CONFLICT",
                       reasons=[] if action_set else ["EMPTY_REACHABLE_RULE_ACTION_SET"],
                       candidates=[], action_set=action_set)

    b5 = run_baseline("B5", request_raw=raw, catalog=catalog, auxiliary=auxiliary)
    b6 = run_baseline("B6", request_raw=raw, catalog=catalog, auxiliary=auxiliary)
    b8 = run_baseline("B8", request_raw=raw, catalog=catalog, auxiliary=auxiliary)
    b6_by_id = {item["rule_id"]: item for item in b6["candidates"]}
    candidates = [item for item in b5["candidates"] if (
        item["rule_id"] in b6_by_id
        and b6_by_id[item["rule_id"]]["verdict"] != "NOT_APPLICABLE"
    )]
    if b8["status"] != "EXECUTED":
        return _result(spec, used_channels=("COC", "SCENE", "CATALOG"),
                       status="UNSUPPORTED",
                       reasons=["NAIVE_COMPOSITION_DOWNSTREAM_B8_UNSUPPORTED", *b8["reason_codes"]],
                       candidates=candidates)
    return _result(spec, used_channels=("COC", "SCENE", "CATALOG", "REACHABILITY"),
                   status=b8["status"], reasons=b8["reason_codes"], candidates=candidates,
                   action_set=b8["action_set"])
