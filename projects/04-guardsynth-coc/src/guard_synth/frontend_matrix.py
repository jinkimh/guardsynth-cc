"""Locked 24-case software matrix for the scoped M14 front-end protocol."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from .coc_conditioned_frontend import (
    COC_FRONTEND_VERSION,
    build_constraint_proposals,
    parse_frontend_request,
)
from .frontend_materialization import (
    SUPPORTED_OPERATIONAL_POLICY_BINDINGS,
    materialize_simulated_proposal,
)
from .source_catalog import SourceCatalog
from guard_synth_eblc.bundle_elaborator import elaborate_bundle
from guard_synth_eblc.indexed_collection import expand_indexed_collection


MATRIX_VERSION = "guardsynth-coc-frontend-matrix-v0.1"
_VARIANTS = (
    ("VALID", "PROPOSED"),
    ("PARAPHRASE_SHUFFLE", "PROPOSED"),
    ("MISSING_PREDICATE", "REVIEW_REQUIRED"),
    ("UNKNOWN", "REVIEW_REQUIRED"),
    ("CONFLICT", "CONFLICT"),
    ("FALSE", "NOT_APPLICABLE"),
    ("CLAIMED_ONLY", "REVIEW_REQUIRED"),
    ("AMBIGUOUS_BINDING", "REVIEW_REQUIRED"),
)
_SLICES = (
    {
        "slice": "PEDESTRIAN_CYCLIST_YIELD",
        "rule_id": "KR-RTA-27-1-CROSSWALK-STOP",
        "tags": ["MARKED_CROSSWALK", "PEDESTRIAN_ACTOR", "PEDESTRIAN_CROSSING"],
        "predicates": [
            "pedestrian_crossing_state", "stop_boundary_geometry",
            "ego_boundary_relation",
        ],
        "target": "pedestrian-1",
        "zone": "crosswalk-1",
        "coc": "횡단보도의 보행자 때문에 정지하려고 한다.",
        "paraphrase": "보행자가 횡단 중이라 차를 멈출 계획이다.",
    },
    {
        "slice": "STOP_SIGNALS",
        "rule_id": "KR-RULES-A2-RED-STOP",
        "tags": ["APPLICABLE_TRAFFIC_CONTROL", "RED_SIGNAL"],
        "predicates": [
            "traffic_control_state", "stop_boundary_geometry",
            "ego_boundary_relation",
        ],
        "target": "signal-1",
        "zone": "lane-1",
        "coc": "적색 신호 때문에 정지하려고 한다.",
        "paraphrase": "빨간 신호라 멈출 계획이다.",
    },
    {
        "slice": "FOLLOWING_CUT_IN",
        "rule_id": "KR-RTA-19-3-NO-OBSTRUCTIVE-LANE-CHANGE",
        "tags": ["EGO_LANE_CHANGE", "TARGET_LANE_TRAFFIC"],
        "predicates": ["adjacent_actor_state"],
        "target": "adjacent-vehicle-1",
        "zone": "target-lane-1",
        "coc": "차선 변경 차량 때문에 감속하려고 한다.",
        "paraphrase": "옆 차량을 보고 lane change를 계획한다.",
    },
)


def _fact(predicate: str, target: str, zone: str, case_id: str) -> dict[str, Any]:
    return {
        "predicate_id": predicate,
        "truth": "TRUE",
        "epistemic_kind": "DERIVED",
        "source_ref": f"public-synthetic:{case_id}:{predicate}",
        "freshness_status": "FRESH",
        "target_ids": [target],
        "zone_ids": [zone],
    }


def build_locked_frontend_cases() -> tuple[dict[str, Any], ...]:
    cases: list[dict[str, Any]] = []
    for slice_spec in _SLICES:
        for index, (variant, expected) in enumerate(_VARIANTS):
            case_id = f"{slice_spec['slice'].lower()}_{index:02d}_{variant.lower()}"
            facts = [
                _fact(predicate, slice_spec["target"], slice_spec["zone"], case_id)
                for predicate in slice_spec["predicates"]
            ]
            coc = slice_spec["coc"]
            if variant == "PARAPHRASE_SHUFFLE":
                coc = slice_spec["paraphrase"]
                facts.reverse()
            elif variant == "MISSING_PREDICATE":
                facts.pop(0)
            elif variant in {"UNKNOWN", "CONFLICT", "FALSE"}:
                facts[0]["truth"] = variant
            elif variant == "CLAIMED_ONLY":
                facts[0]["epistemic_kind"] = "CLAIMED"
            elif variant == "AMBIGUOUS_BINDING":
                facts[0]["target_ids"].append(slice_spec["target"] + "-alternate")
            evidence_hash = hashlib.sha256(case_id.encode("utf-8")).hexdigest()
            request = {
                "frontend_version": COC_FRONTEND_VERSION,
                "request_id": case_id,
                "jurisdiction": "KR",
                "catalog_id": "guardsynth-kr-structured-road-v0.1",
                "catalog_version": "guardsynth-source-catalog-v0.1",
                "catalog_as_of_date": "2026-08-10",
                "odd_tags": ["urban_or_suburban_structured_public_road"],
                "slice_hint": slice_spec["slice"],
                "scene_tags": list(slice_spec["tags"]),
                "coc": {
                    "text": coc,
                    "language": "ko",
                    "epistemic_kind": "CLAIMED",
                    "evidence_ref": f"coc-sha256:{evidence_hash}",
                },
                "scene_facts": facts,
                "policy_evidence_ref": "GS-COC-FRONTEND-POLICY-v0.1",
            }
            cases.append({
                "case_id": case_id,
                "slice": slice_spec["slice"],
                "primary_rule_id": slice_spec["rule_id"],
                "variant": variant,
                "expected_primary_verdict": expected,
                "request": request,
                "baseline_auxiliary": {
                    "ego_speed_mps": 6.0,
                    "distance_to_boundary_m": 10.0,
                    "deceleration_mps2": 3.0,
                    "response_time_s": 0.5,
                    "physics_evidence_refs": [
                        "M15-PUBLIC-SYNTHETIC-PHYSICS-STATE-v0.1",
                        "M15-PUBLIC-SYNTHETIC-ASSURANCE-v0.1"
                    ],
                    "reachable_actions": ["STOP", "CREEP", "PROCEED"],
                    "rule_permitted_actions": ["STOP", "CREEP"],
                    "reachability_evidence_ref": (
                        "M15-PUBLIC-SYNTHETIC-REACHABILITY-ACTION-SET-v0.1"
                    ),
                },
            })
    return tuple(cases)


def evaluate_locked_frontend_matrix(
    *,
    catalog: SourceCatalog,
    model_source: Path | dict[str, Any],
    base_request: dict[str, Any],
) -> dict[str, Any]:
    # Solver selection is a CLI/test harness responsibility.  Import only at
    # execution time so merely loading the case matrix cannot cache a missing
    # optional Z3 runtime before project-local configuration.
    from guard_synth_eblc.smt_compiler import check_queries, compile_core_model

    records = []
    for case in build_locked_frontend_cases():
        proposal_bundle = build_constraint_proposals(
            parse_frontend_request(deepcopy(case["request"])), catalog
        )
        primary = next(
            item for item in proposal_bundle["proposals"]
            if item["rule_id"] == case["primary_rule_id"]
        )
        compiler = {
            "attempted": False,
            "status": "NOT_APPLICABLE_TO_CASE",
            "reason_code": None,
            "query_statuses": {},
            "source_separation": None,
        }
        if primary["verdict"] == "PROPOSED":
            if primary["rule_id"] not in SUPPORTED_OPERATIONAL_POLICY_BINDINGS:
                compiler.update({
                    "status": "UNSUPPORTED",
                    "reason_code": "NO_OPERATIONAL_POLICY_BINDING_FOR_PROPOSAL",
                })
            else:
                compiler["attempted"] = True
                context = {
                    "scene_ref": case["case_id"],
                    "timestamp_s": 1.0,
                    "hazard_evidence_ref": f"public-synthetic:{case['case_id']}:hazard",
                    "target_entity_id": primary["target_id"],
                    "zone_id": primary["zone_id"],
                    "zone_entry_x_m": 15.0,
                    "coordinate_frame": "dataset_rig",
                    "distance_unit": "m",
                    "geometry_evidence_ref": f"public-synthetic:{case['case_id']}:geometry",
                    "association_evidence_refs": [
                        f"public-synthetic:{case['case_id']}:association"
                    ],
                    "transform_verified": True,
                    "transform_evidence_ref": f"public-synthetic:{case['case_id']}:transform",
                    "recorded_vehicle_binding_key": f"recorded-rig:{case['case_id']}",
                }
                materialized = materialize_simulated_proposal(
                    proposal_bundle=proposal_bundle,
                    proposal_rule_id=primary["rule_id"],
                    scene_context=context,
                    model_source=model_source,
                    base_request=deepcopy(base_request),
                    request_id=f"{case['case_id']}__materialized",
                )
                expansion = expand_indexed_collection(materialized.generated.collection)
                compiled = compile_core_model(
                    elaborate_bundle(expansion.bundle).core_model
                )
                query_results = check_queries(compiled)
                compiler.update({
                    "status": "VALIDATED",
                    "reason_code": None,
                    "query_statuses": {
                        item["query_id"]: item["status"]
                        for item in query_results["results"]
                    },
                    "source_separation": not set(
                        materialized.legal_proposal_refs
                    ).intersection(materialized.numeric_evidence_refs),
                })
        records.append({
            "case_id": case["case_id"],
            "slice": case["slice"],
            "variant": case["variant"],
            "primary_rule_id": case["primary_rule_id"],
            "expected_primary_verdict": case["expected_primary_verdict"],
            "actual_primary_verdict": primary["verdict"],
            "matches": primary["verdict"] == case["expected_primary_verdict"],
            "reason_codes": primary["reason_codes"],
            "coc_text_in_output": proposal_bundle["coc_parse"]["text_included"],
            "claim_promoted": proposal_bundle["claim_promoted_to_scene_or_legal_authority"],
            "compiler": compiler,
        })
    compile_attempts = [item for item in records if item["compiler"]["attempted"]]
    return {
        "matrix_version": MATRIX_VERSION,
        "case_count": len(records),
        "schema_parse_count": len(records),
        "expected_verdict_matches": sum(item["matches"] for item in records),
        "claim_promotions": sum(item["claim_promoted"] for item in records),
        "coc_text_outputs": sum(item["coc_text_in_output"] for item in records),
        "compiler_attempt_count": len(compile_attempts),
        "compiler_success_count": sum(
            item["compiler"]["status"] == "VALIDATED" for item in compile_attempts
        ),
        "supported_operational_policy_rule_count": len(
            SUPPORTED_OPERATIONAL_POLICY_BINDINGS
        ),
        "primary_rule_count": len(_SLICES),
        "records": records,
    }
