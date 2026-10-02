"""Fail-closed M14 CoC + scene + source-catalog proposal front-end."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from guard_synth_eblc.schema_validation import load_json, validate

from .source_catalog import SourceCatalog
from .catalog_retrieval import CatalogRetriever, GraphPredicateRetriever, RetrievalQuery


COC_FRONTEND_VERSION = "guardsynth-coc-conditioned-frontend-v0.1"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/coc_conditioned_frontend_request.schema.json"
OUTPUT_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/constraint_proposal_bundle.schema.json"

_LEXICON = {
    "intent": {
        "PLANNED": ("plan", "intend", "하려", "계획"),
    },
    "cause": {
        "PEDESTRIAN": ("pedestrian", "보행자"),
        "CROSSING": ("crosswalk", "crossing", "횡단보도", "횡단"),
        "TRAFFIC_CONTROL": ("signal", "red light", "yellow light", "신호", "적색", "황색"),
        "LEAD_OR_ADJACENT_VEHICLE": ("lead vehicle", "cut-in", "lane change", "앞차", "끼어들", "차선 변경"),
    },
    "action": {
        "STOP": ("stop", "yield", "정지", "멈", "양보"),
        "SLOW": ("slow", "deceler", "감속"),
        "TURN": ("turn", "회전", "우회전", "좌회전"),
        "PROCEED": ("proceed", "go", "진행"),
    },
    "uncertainty": {
        "UNCERTAIN": ("maybe", "possibly", "uncertain", "아마", "가능", "보인다"),
    },
}
_STATUS_PRECEDENCE = (
    "CONFLICT",
    "UNSUPPORTED",
    "REVIEW_REQUIRED",
    "NOT_APPLICABLE",
    "PROPOSED",
)
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_COC_REF = re.compile(r"^coc-sha256:[0-9a-f]{64}$")
_RULE_TAGS = {
    "KR-RTA-27-1-CROSSWALK-STOP": ("MARKED_CROSSWALK", "PEDESTRIAN_ACTOR", "PEDESTRIAN_CROSSING"),
    "KR-RTA-27-2-TURN-PEDESTRIAN": ("EGO_TURNING", "PEDESTRIAN_ACTOR", "PEDESTRIAN_CROSSING", "TRAFFIC_CONTROLLED"),
    "KR-RTA-27-3-UNCONTROLLED-PEDESTRIAN": ("PEDESTRIAN_ACTOR", "PEDESTRIAN_CROSSING", "UNCONTROLLED_INTERSECTION"),
    "KR-RTA-27-5-NONCROSSWALK-STOP": ("NO_CROSSWALK", "PEDESTRIAN_ACTOR", "PEDESTRIAN_CROSSING"),
    "KR-RTA-15-2-3-BICYCLE-CROSSING": ("BICYCLE_ACTOR", "BICYCLE_CROSSING_USE"),
    "KR-RTA-5-1-CONTROL-COMPLIANCE": ("APPLICABLE_TRAFFIC_CONTROL",),
    "KR-RTA-5-2-AUTHORIZED-DIRECTION-OVERRIDE": ("AUTHORIZED_DIRECTION_CONFLICT",),
    "KR-RULES-A2-RED-STOP": ("APPLICABLE_TRAFFIC_CONTROL", "RED_SIGNAL"),
    "KR-RULES-A2-YELLOW-TRANSITION": ("APPLICABLE_TRAFFIC_CONTROL", "YELLOW_SIGNAL"),
    "KR-RULES-A2-FLASHING-RED": ("APPLICABLE_TRAFFIC_CONTROL", "FLASHING_RED_SIGNAL"),
    "KR-RULES-A2-FLASHING-YELLOW": ("APPLICABLE_TRAFFIC_CONTROL", "FLASHING_YELLOW_SIGNAL"),
    "KR-RTA-19-1-FOLLOWING-DISTANCE": ("FOLLOWING_LEAD_VEHICLE",),
    "KR-RTA-19-2-PASS-BICYCLE-DISTANCE": ("BICYCLE_ACTOR", "PASSING_BICYCLE"),
    "KR-RTA-19-3-NO-OBSTRUCTIVE-LANE-CHANGE": ("EGO_LANE_CHANGE", "TARGET_LANE_TRAFFIC"),
    "KR-RTA-19-4-NO-UNNECESSARY-HARD-BRAKE": ("EGO_SUDDEN_BRAKE",),
}
_EXCLUSIVE_TAGS = (
    frozenset(("MARKED_CROSSWALK", "NO_CROSSWALK")),
    frozenset(("PEDESTRIAN_ACTOR", "BICYCLE_ACTOR")),
    frozenset(("TRAFFIC_CONTROLLED", "UNCONTROLLED_INTERSECTION")),
    frozenset(("RED_SIGNAL", "YELLOW_SIGNAL", "FLASHING_RED_SIGNAL", "FLASHING_YELLOW_SIGNAL")),
    frozenset(("BICYCLE_CROSSING_USE", "MARKING_ONLY_NO_CROSSING_USE")),
)


@dataclass(frozen=True, slots=True)
class FrontendRequest:
    raw: dict[str, Any]


def parse_frontend_request(raw: dict[str, Any]) -> FrontendRequest:
    validate(raw, load_json(SCHEMA_PATH))
    if raw["frontend_version"] != COC_FRONTEND_VERSION:
        raise ValueError("UNSUPPORTED_FRONTEND_VERSION")
    if not _IDENTIFIER.fullmatch(raw["request_id"]):
        raise ValueError("INVALID_FRONTEND_REQUEST_ID")
    if raw["coc"]["epistemic_kind"] != "CLAIMED":
        raise ValueError("COC_MUST_REMAIN_CLAIMED")
    if not _COC_REF.fullmatch(raw["coc"]["evidence_ref"]):
        raise ValueError("INVALID_COC_EVIDENCE_REF")
    if (
        len(raw["odd_tags"]) != len(set(raw["odd_tags"]))
        or len(raw["scene_tags"]) != len(set(raw["scene_tags"]))
    ):
        raise ValueError("DUPLICATE_CONTEXT_TAG")
    for fact in raw["scene_facts"]:
        if (
            len(fact["target_ids"]) != len(set(fact["target_ids"]))
            or len(fact["zone_ids"]) != len(set(fact["zone_ids"]))
        ):
            raise ValueError("DUPLICATE_FACT_BINDING_ID")
    return FrontendRequest(raw)


def _parse_coc(coc: dict[str, Any]) -> dict[str, Any]:
    normalized = coc["text"].casefold()
    concepts = {
        group: sorted(
            concept
            for concept, forms in entries.items()
            if any(form in normalized for form in forms)
        )
        for group, entries in _LEXICON.items()
    }
    return {
        "parser_version": COC_FRONTEND_VERSION,
        "language": coc["language"],
        "epistemic_kind": "CLAIMED",
        "evidence_ref": coc["evidence_ref"],
        "text_included": False,
        "concepts": concepts,
        "unknown_groups": sorted(group for group, values in concepts.items() if not values),
    }


def _facts_by_predicate(facts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for fact in facts:
        result.setdefault(fact["predicate_id"], []).append(fact)
    return result


def _predicate_value(
    predicate_id: str,
    facts: dict[str, list[dict[str, Any]]],
) -> tuple[str, list[str], list[dict[str, Any]]]:
    candidates = facts.get(predicate_id, [])
    if not candidates:
        return "UNKNOWN", ["MISSING_REQUIRED_PREDICATE"], []
    usable = [
        fact for fact in candidates
        if fact["epistemic_kind"] != "CLAIMED"
        and fact["freshness_status"] == "FRESH"
    ]
    reasons: list[str] = []
    if len(usable) != len(candidates):
        if any(fact["epistemic_kind"] == "CLAIMED" for fact in candidates):
            reasons.append("CLAIMED_FACT_NOT_PREDICATE_AUTHORITY")
        if any(fact["freshness_status"] != "FRESH" for fact in candidates):
            reasons.append("PREDICATE_NOT_FRESH")
    if not usable:
        return "UNKNOWN", reasons or ["MISSING_REQUIRED_PREDICATE"], candidates
    values = {fact["truth"] for fact in usable}
    if "CONFLICT" in values or ("TRUE" in values and "FALSE" in values):
        return "CONFLICT", [*reasons, "CONFLICTING_SCENE_EVIDENCE"], usable
    if "UNKNOWN" in values:
        return "UNKNOWN", [*reasons, "UNKNOWN_REQUIRED_PREDICATE"], usable
    if "FALSE" in values:
        return "FALSE", reasons, usable
    return "TRUE", reasons, usable


def _applicability(
    required: list[str],
    facts: dict[str, list[dict[str, Any]]],
) -> tuple[str, list[str], list[dict[str, Any]]]:
    evaluated = [_predicate_value(predicate, facts) for predicate in required]
    values = [item[0] for item in evaluated]
    reasons = list(dict.fromkeys(reason for item in evaluated for reason in item[1]))
    used = [fact for item in evaluated for fact in item[2]]
    if "CONFLICT" in values:
        return "CONFLICT", reasons, used
    if "UNKNOWN" in values:
        return "UNKNOWN", reasons, used
    if "FALSE" in values:
        return "FALSE", reasons, used
    return "TRUE", reasons, used


def _tag_applicability(rule_id: str, scene_tags: set[str]) -> tuple[str, list[str]]:
    required = set(_RULE_TAGS.get(rule_id, ()))
    missing = required - scene_tags
    if not missing:
        return "TRUE", []
    for tag in missing:
        for group in _EXCLUSIVE_TAGS:
            if tag in group and scene_tags.intersection(group - {tag}):
                return "FALSE", ["RULE_PRECONDITION_TAG_FALSE"]
    return "UNKNOWN", ["RULE_PRECONDITION_TAG_MISSING"]


def _combine_applicability(
    predicate_status: str,
    tag_status: str,
) -> str:
    if "CONFLICT" in (predicate_status, tag_status):
        return "CONFLICT"
    if "FALSE" in (predicate_status, tag_status):
        return "FALSE"
    if "UNKNOWN" in (predicate_status, tag_status):
        return "UNKNOWN"
    return "TRUE"


def _exception_applicability(rule_id: str, scene_tags: set[str]) -> tuple[str, list[str]]:
    if rule_id == "KR-RTA-5-1-CONTROL-COMPLIANCE" and "AUTHORIZED_DIRECTION_CONFLICT" in scene_tags:
        return "FALSE", ["AUTHORIZED_DIRECTION_OVERRIDE_BRANCH"]
    if rule_id == "KR-RTA-5-2-AUTHORIZED-DIRECTION-OVERRIDE" and "CONTROLLER_AUTHORITY_UNVERIFIED" in scene_tags:
        return "UNKNOWN", ["AUTHORIZED_DIRECTION_NOT_MACHINE_VERIFIED"]
    if rule_id == "KR-RULES-A2-RED-STOP" and "RIGHT_TURN" in scene_tags and "NONOBSTRUCTION_VERIFIED" not in scene_tags:
        return "UNKNOWN", ["RIGHT_TURN_NONOBSTRUCTION_NOT_VERIFIED"]
    if rule_id == "KR-RULES-A2-YELLOW-TRANSITION" and "ALREADY_ENTERED_INTERSECTION" in scene_tags:
        return "UNKNOWN", ["ALREADY_ENTERED_BRANCH_NOT_MATERIALIZED"]
    if rule_id == "KR-RTA-19-4-NO-UNNECESSARY-HARD-BRAKE" and scene_tags.intersection({
        "DANGER_PREVENTION", "UNAVOIDABLE_REASON"
    }):
        return "FALSE", ["DANGER_OR_UNAVOIDABLE_EXCEPTION_TRUE"]
    return "TRUE", []


def _binding(used: list[dict[str, Any]]) -> tuple[str, list[str], str | None, str | None]:
    targets = sorted({value for fact in used for value in fact["target_ids"]})
    zones = sorted({value for fact in used for value in fact["zone_ids"]})
    if len(targets) > 1 or len(zones) > 1:
        return "AMBIGUOUS", ["AMBIGUOUS_BINDING"], None, None
    if len(targets) != 1 or len(zones) != 1:
        return "UNSUPPORTED", ["MISSING_TARGET_OR_ZONE_BINDING"], None, None
    return "BOUND", [], targets[0], zones[0]


def _unsupported_binder_reason(binder: dict[str, Any]) -> str | None:
    for output in binder["outputs"]:
        if output["kind"] == "UNSUPPORTED":
            return output["reason_code"]
    return None


def _proposal_verdict(
    applicability: str,
    binding: str,
    unsupported_binder: str | None,
) -> str:
    if applicability == "CONFLICT":
        return "CONFLICT"
    if applicability == "UNKNOWN":
        return "REVIEW_REQUIRED"
    if applicability == "FALSE":
        return "NOT_APPLICABLE"
    if unsupported_binder or binding == "UNSUPPORTED":
        return "UNSUPPORTED"
    if binding == "AMBIGUOUS":
        return "REVIEW_REQUIRED"
    return "PROPOSED"


def build_constraint_proposals(
    request: FrontendRequest,
    catalog: SourceCatalog,
    *,
    retriever: CatalogRetriever | None = None,
) -> dict[str, Any]:
    raw = request.raw
    coc_parse = _parse_coc(raw["coc"])
    jurisdiction = catalog.raw["jurisdiction"]["country_code"]
    base = {
        "frontend_version": COC_FRONTEND_VERSION,
        "request_id": raw["request_id"],
        "coc_parse": coc_parse,
        "claim_promoted_to_scene_or_legal_authority": False,
        "proposals": [],
        "claim_scope": (
            "REVIEWABLE_CONSTRAINT_PROPOSAL_NOT_LEGAL_DECISION_"
            "OR_VEHICLE_SAFETY_VALIDATION"
        ),
    }
    if raw["jurisdiction"] != jurisdiction:
        result = {**base, "status": "UNSUPPORTED", "reason_codes": ["UNSUPPORTED_JURISDICTION"]}
        validate(result, load_json(OUTPUT_SCHEMA_PATH))
        return result
    if (
        raw["catalog_id"] != catalog.raw["catalog_id"]
        or raw["catalog_version"] != catalog.raw["catalog_version"]
        or raw["catalog_as_of_date"] != catalog.raw["jurisdiction"]["as_of_date"]
    ):
        result = {
            **base,
            "status": "UNSUPPORTED",
            "reason_codes": ["CATALOG_VERSION_OR_ID_MISMATCH"],
        }
        validate(result, load_json(OUTPUT_SCHEMA_PATH))
        return result
    included_odd = set(catalog.raw["odd_scope"]["included"])
    if not set(raw["odd_tags"]).issubset(included_odd):
        result = {
            **base,
            "status": "UNSUPPORTED",
            "reason_codes": [catalog.raw["odd_scope"]["outside_odd_reason"]],
        }
        validate(result, load_json(OUTPUT_SCHEMA_PATH))
        return result

    facts = _facts_by_predicate(raw["scene_facts"])
    scene_tags = set(raw["scene_tags"])
    retrieval_query = RetrievalQuery(
        slice_hint=raw["slice_hint"],
        scene_predicates=tuple(sorted(facts)),
        scene_tags=tuple(sorted(scene_tags)),
        coc_concepts=tuple(
            sorted(value for values in coc_parse["concepts"].values() for value in values)
        ),
    )
    retrieval_backend = retriever or GraphPredicateRetriever()
    retrieved = retrieval_backend.retrieve(catalog, retrieval_query)
    retrieved_by_id = {item.rule_id: item for item in retrieved}
    rules_by_id = {item["rule_id"]: item for item in catalog.raw["rule_templates"]}
    binders = {item["binder_id"]: item for item in catalog.raw["binder_specs"]}
    claim_sources = {
        claim["claim_id"]: record["evidence_id"]
        for record in catalog.raw["source_records"]
        for claim in record["claims"]
    }
    proposals = []
    for retrieved_rule in retrieved:
        rule = rules_by_id[retrieved_rule.rule_id]
        predicate_status, reasons, used = _applicability(
            rule["required_predicate_refs"], facts
        )
        tag_status, tag_reasons = _tag_applicability(rule["rule_id"], scene_tags)
        exception_status, exception_reasons = _exception_applicability(
            rule["rule_id"], scene_tags
        )
        applicability = _combine_applicability(
            _combine_applicability(predicate_status, tag_status),
            exception_status,
        )
        reasons = list(dict.fromkeys([
            *reasons, *tag_reasons, *exception_reasons
        ]))
        binding, binding_reasons, target_id, zone_id = _binding(used)
        binder_reason = _unsupported_binder_reason(binders[rule["binder_ref"]])
        verdict = _proposal_verdict(applicability, binding, binder_reason)
        reason_codes = list(dict.fromkeys([
            *reasons,
            *binding_reasons,
            *([binder_reason] if applicability == "TRUE" and binder_reason else []),
        ]))
        predicate_overlap = sum(
            predicate in facts for predicate in rule["required_predicate_refs"]
        )
        proposals.append({
            "rule_id": rule["rule_id"],
            "slice": rule["slice"],
            "source_claim_refs": list(rule["source_claim_refs"]),
            "source_record_refs": sorted({
                claim_sources[claim] for claim in rule["source_claim_refs"]
            }),
            "required_predicate_refs": list(rule["required_predicate_refs"]),
            "retrieval_predicate_overlap": predicate_overlap,
            "retrieval_score": retrieved_rule.score,
            "retrieval_backend": retrieved_rule.backend,
            "applicability": applicability,
            "binding_status": binding,
            "target_id": target_id,
            "zone_id": zone_id,
            "binder_ref": rule["binder_ref"],
            "verdict": verdict,
            "reason_codes": reason_codes,
            "executable_parameters": None,
            "claim_boundary": rule["claim_boundary"],
        })
    proposals.sort(
        key=lambda item: (
            -retrieved_by_id[item["rule_id"]].score,
            item["rule_id"],
        )
    )
    statuses = {item["verdict"] for item in proposals}
    status = (
        "PROPOSED"
        if "PROPOSED" in statuses
        else next(
            (candidate for candidate in _STATUS_PRECEDENCE if candidate in statuses),
            "UNSUPPORTED",
        )
    )
    result = {
        **base,
        "status": status,
        "reason_codes": [],
        "retrieval_query": {
            "jurisdiction": raw["jurisdiction"],
            "catalog_id": raw["catalog_id"],
            "catalog_version": raw["catalog_version"],
            "catalog_as_of_date": raw["catalog_as_of_date"],
            "odd_tags": sorted(raw["odd_tags"]),
            "slice": raw["slice_hint"],
            "coc_concepts": coc_parse["concepts"],
            "scene_predicates": sorted(facts),
            "scene_tags": sorted(scene_tags),
            "policy_evidence_ref": raw["policy_evidence_ref"],
            "retrieval_backend": retrieval_backend.backend_id,
        },
        "proposals": proposals,
    }
    validate(result, load_json(OUTPUT_SCHEMA_PATH))
    return result
