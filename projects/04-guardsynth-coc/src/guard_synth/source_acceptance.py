"""Fail-closed development source review; never independent action gold."""

from datetime import datetime
import math

VERSION = "paper1-source-acceptance-v0.1"
TRUTHS = {"TRUE", "FALSE", "UNKNOWN", "CONFLICT"}


def point(value):
    if (not isinstance(value, list) or len(value) != 2
        or any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1 for x in value)):
        raise ValueError("invalid normalized point")
    return value


def polygon(value):
    if not isinstance(value, list) or not 3 <= len(value) <= 64:
        raise ValueError("polygon requires 3..64 vertices")
    for p in value:
        point(p)
    if len({tuple(p) for p in value}) != len(value):
        raise ValueError("duplicate polygon vertex")
    area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(value, value[1:]+value[:1]))
    if abs(area) <= 1e-8:
        raise ValueError("degenerate polygon")
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def on(a,b,c):
        return abs(cross(a,b,c)) < 1e-12 and min(a[0],b[0]) <= c[0] <= max(a[0],b[0]) and min(a[1],b[1]) <= c[1] <= max(a[1],b[1])
    edges = list(zip(value, value[1:]+value[:1]))
    for i,(a,b) in enumerate(edges):
        for j,(c,d) in enumerate(edges):
            if j <= i or j == i+1 or (i == 0 and j == len(edges)-1):
                continue
            if (cross(a,b,c)*cross(a,b,d) < 0 and cross(c,d,a)*cross(c,d,b) < 0) or any((on(a,b,c),on(a,b,d),on(c,d,a),on(c,d,b))):
                raise ValueError("self-intersecting polygon")
    return value


def validate_review(review, packet, packet_sha256):
    required = {"review_version", "packet_sha256", "candidate_digest", "event_timestamp_us", "reviewer_id",
        "reviewed_at", "target_identity", "target_point", "zone_status", "zone_polygon", "road_context",
        "ped_truth", "road_truth", "ped_reason", "road_reason"}
    if not isinstance(review, dict) or set(review) != required:
        raise ValueError("review fields mismatch")
    for key, expected in (("review_version", VERSION), ("packet_sha256", packet_sha256),
                           ("candidate_digest", packet["candidate_digest"]), ("event_timestamp_us", packet["event_timestamp_us"])):
        if review[key] != expected or type(review[key]) is not type(expected):
            raise ValueError("review packet binding mismatch: " + key)
    for key in ("reviewer_id", "ped_reason", "road_reason", "reviewed_at"):
        if not isinstance(review[key], str) or not review[key].strip() or len(review[key]) > 4000:
            raise ValueError("review text missing/invalid: " + key)
    if datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("review time requires timezone")
    for key, choices in (("target_identity", {"CONFIRMED_AGENT3", "UNCERTAIN"}),
                          ("zone_status", {"CONFIRMED", "UNCERTAIN"}),
                          ("road_context", {"CONFIRMED", "UNCERTAIN"}),
                          ("ped_truth", TRUTHS), ("road_truth", TRUTHS)):
        if not isinstance(review[key], str) or review[key] not in choices:
            raise ValueError("invalid review choice: " + key)
    if review["target_point"] is not None:
        point(review["target_point"])
    if review["zone_polygon"]:
        polygon(review["zone_polygon"])
    elif review["zone_polygon"] != []:
        raise ValueError("invalid empty polygon")
    if review["target_identity"] == "CONFIRMED_AGENT3" and review["target_point"] is None:
        raise ValueError("confirmed identity needs a t0 point")
    if review["zone_status"] == "CONFIRMED" and not review["zone_polygon"]:
        raise ValueError("confirmed zone needs polygon")
    common = review["zone_status"] == "CONFIRMED"
    valid = {"ped": common and review["target_identity"] == "CONFIRMED_AGENT3" and review["ped_truth"] in {"TRUE", "FALSE"},
             "road": common and review["road_context"] == "CONFIRMED" and review["road_truth"] in {"TRUE", "FALSE"}}
    accepted = all(valid.values())
    return {"status": "HUMAN_REVIEWED_DEVELOPMENT_SOURCE" if accepted else "REVIEW_RECORDED_SOURCE_UNRESOLVED",
        "review_completed": True, "source_accepted_for_development": accepted,
        "event_predicates": {oid: {"truth": review[oid+"_truth"], "evidence_valid": valid[oid]} for oid in valid},
        "reviewer_id": review["reviewer_id"], "identity_assurance": "SUBMITTER_DECLARED_NOT_AUTHENTICATED",
        "independent_action_gold": None, "independent_cnl_audit": "PENDING", "learning_export_allowed": False,
        "claim_scope": "HUMAN_DECLARED_SINGLE_EVENT_DEVELOPMENT_SOURCE_NOT_TEST_GOLD_OR_VEHICLE_SAFETY"}
