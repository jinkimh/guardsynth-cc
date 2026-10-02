"""Selected paper-1 task mapping; source candidates never become hazard gold."""

from __future__ import annotations

from guard_synth_eblc.action_contract import parse_action_contract


def prepare_scene18_contract(scene: dict, *, policy_ref: str, source_refs: list[str]):
    """Prepare the pinned worked-example task, not a general CoC extractor.

    The caller revalidates source bytes. This adapter refuses other task contexts
    and never invents source-confirmed bindings or evidence acceptance.
    """
    if (scene["clip_id"] != "a508e4e3-1381-462a-ad65-cf938a438187"
        or scene["event_timestamp_us"] != 9788430 or scene["review_index"] != 18
        or scene["source_linked_person_ids"] != ["Agent3"]):
        raise ValueError("outside pinned scene18 development task")
    if policy_ref not in source_refs:
        raise ValueError("policy source not pinned")
    raw = {"contract_version": "eblc-action-contract-v0.1", "contract_id": "scene18_entry_contract",
        "horizon": 3, "claim_scope": "CONDITIONAL_ACTION_SELECTION_NOT_VEHICLE_SAFETY",
        "subject_id": "ego", "zone_id": None, "policy": "CLEAR_REQUIRED_FOR_ENTRY", "source_refs": source_refs,
        "obligations": [
            {"obligation_id": "ped", "predicate_id": "pedestrian_conflict", "target_entity_id": "Agent3",
             "rule_ref": policy_ref, "source_refs": source_refs},
            {"obligation_id": "road", "predicate_id": "main_road_yield_required", "target_entity_id": None,
             "rule_ref": policy_ref, "source_refs": source_refs},
        ]}
    contract = parse_action_contract(raw)
    gate = {"status": "CONDITIONAL_CONTRACT_SOURCE_REVIEW_REQUIRED", "source_bound": False,
        "candidate_digest": scene["candidate_digest"], "event_timestamp_us": scene["event_timestamp_us"],
        "target_candidate": "Agent3", "target_identity_confirmed": False, "zone_id": None,
        "event_predicates": {p: {"truth": "UNKNOWN", "evidence_valid": False} for p in ("ped", "road")},
        "blockers": ["TARGET_ZONE_BINDING_UNCONFIRMED", "EVENT_CONFLICT_PREDICATE_UNCONFIRMED",
                     "MAIN_ROAD_OBLIGATION_UNCONFIRMED", "EVIDENCE_ACCEPTANCE_CONTRACT_UNINSTANTIATED",
                     "INDEPENDENT_ACTION_GOLD_MISSING", "INDEPENDENT_CNL_AUDIT_PENDING"],
        "action_gold": None, "learning_export_allowed": False,
        "note": "DEFER_ENTRY from incomplete evidence is a policy output, not a real-scene gold label."}
    return contract, gate
