"""Validate declared independent review; no automatic annotation or paper gate."""

from datetime import datetime

VERSION = "paper1-independent-development-review-v0.1"
SCENE_VERSION = "paper1-scene-cnl-review-v0.1"


def validate_independent_review(raw, packet, packet_sha256, *, known_exposed_reviewer_ids=()):
    common = {"review_version", "packet_sha256", "kind", "reviewer_id", "reviewed_at", "independence", "answers", "reason"}
    if not isinstance(raw, dict) or set(raw) != common:
        raise ValueError("review fields mismatch")
    version = SCENE_VERSION if packet["kind"] == "SCENE_CNL" else VERSION
    if raw["review_version"] != version or raw["packet_sha256"] != packet_sha256 or raw["kind"] != packet["kind"]:
        raise ValueError("review packet mismatch")
    for key in ("reviewer_id", "reviewed_at", "reason"):
        if not isinstance(raw[key], str) or not raw[key].strip() or len(raw[key]) > 8000:
            raise ValueError("missing review text: " + key)
    if datetime.fromisoformat(raw["reviewed_at"].replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("timezone required")
    if raw["independence"] not in ("INDEPENDENT", "EXPOSED_OR_INVOLVED", "UNCERTAIN"):
        raise ValueError("invalid independence declaration")
    if packet["kind"] == "ACTION":
        expected = {"action"}
        choices = {"ENTER_ZONE", "DEFER_ENTRY", "UNJUDGEABLE"}
    elif packet["kind"] == "CNL":
        expected = set(packet.get("korean_review", {}).get("review_clause_ids", packet["clause_ids"]))
        choices = {"MATCH", "MISMATCH", "UNJUDGEABLE"}
    elif packet["kind"] == "SCENE_CNL":
        expected = set(packet["clause_ids"])
        choices = {"SUPPORTED", "UNSUPPORTED", "UNJUDGEABLE"}
    else:
        raise ValueError("unsupported review kind")
    if not isinstance(raw["answers"], dict) or set(raw["answers"]) != expected:
        raise ValueError("answer fields mismatch")
    if any(not isinstance(v, str) or v not in choices for v in raw["answers"].values()):
        raise ValueError("invalid review answer")
    normalize = lambda s: " ".join(s.casefold().split())
    known_exposure = normalize(raw["reviewer_id"]) in {normalize(x) for x in known_exposed_reviewer_ids}
    independent = raw["independence"] == "INDEPENDENT" and not known_exposure
    return {"review_completed": True, "independence_eligible": independent,
        "independence_assurance": "DECLARATION_AND_KNOWN_EXPOSURE_CHECK_NOT_AUTHENTICATED_IDENTITY",
        "known_exposure_conflict": known_exposure,
        "judgement_available": independent and "UNJUDGEABLE" not in raw["answers"].values(),
        "answers": dict(raw["answers"]), "learning_export_allowed": False,
        "main_test_eligibility": False, "claim_scope": "SINGLE_DEVELOPMENT_REVIEW_NOT_PAPER_EFFECT_OR_SOURCE_COMPLETION"}
