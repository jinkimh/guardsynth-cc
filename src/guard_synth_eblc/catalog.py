"""Load the public schema-backed EBLC rule and predicate catalog."""

from __future__ import annotations

from pathlib import Path

from .schema_validation import load_json
from .types import (
    EpistemicKind,
    EvidenceRecord,
    PredicateSpec,
    Priority,
    PriorityClass,
    RuleTemplate,
    SourceClass,
    Truth,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
FIXTURE_ROOT = PACKAGE_ROOT / "fixtures"
SCHEMA_ROOT = PACKAGE_ROOT / "schemas"


def load_predicate_spec() -> PredicateSpec:
    raw = load_json(FIXTURE_ROOT / "predicate_spec.json")
    return PredicateSpec(
        predicate_id=raw["predicate_id"],
        argument_types=tuple(raw["argument_types"]),
        measurement_or_derivation_fn=raw["measurement_or_derivation_fn"],
        allowed_sources=tuple(EpistemicKind(item) for item in raw["allowed_sources"]),
        coordinate_frame=raw["coordinate_frame"],
        update_rate_hz=float(raw["update_rate_hz"]),
        maximum_latency_s=float(raw["maximum_latency_s"]),
        maximum_age_s=float(raw["maximum_age_s"]),
        uncertainty_model=raw["uncertainty_model"],
        monitorability=raw["monitorability"],
        calibration_id=raw["calibration_id"],
        failure_value=Truth(raw["failure_value"]),
    )


def load_pilot_rule() -> RuleTemplate:
    raw = load_json(FIXTURE_ROOT / "rule_template.json")
    source = raw["source"]
    priority = raw["priority"]
    lifecycle = raw["lifecycle"]
    fallback = raw["fallback"]
    roles = raw["roles"]
    return RuleTemplate(
        rule_id=raw["rule_id"],
        source=EvidenceRecord(
            evidence_id=source["evidence_id"],
            source_class=SourceClass(source["source_class"]),
            uri=source["uri"],
            version=source["version"],
            scope=source["scope"],
            section=source["section"],
            content_hash=source["content_hash"],
        ),
        scope=raw["scope"],
        precondition=raw["precondition"],
        exception=raw["exception"],
        subject_role=roles["subject"],
        target_role=roles["target"],
        zone_role=roles["zone"],
        binder_id=raw["binder_id"],
        activation=lifecycle["activation"],
        invariant=lifecycle["invariant"],
        bound=lifecycle["bound"],
        release=lifecycle["release"],
        reactivation=lifecycle["reactivation"],
        expiry=lifecycle["expiry"],
        fallback=fallback["action"],
        fallback_approved=bool(fallback["approved"]),
        observability=tuple(raw["observability"]),
        priority=Priority(
            PriorityClass(priority["class"]),
            tuple(PriorityClass(item) for item in priority["overrides"]),
        ),
        stop_margin_m=float(raw["stop_margin_m"]),
        release_clear_frames=int(raw["release_clear_frames"]),
    )


def valid_fixture_pairs() -> tuple[tuple[Path, Path], ...]:
    return (
        (FIXTURE_ROOT / "context_frame.json", SCHEMA_ROOT / "context_graph.schema.json"),
        (FIXTURE_ROOT / "rule_template.json", SCHEMA_ROOT / "rule_template.schema.json"),
        (FIXTURE_ROOT / "eblc_contract.json", SCHEMA_ROOT / "eblc_contract.schema.json"),
        (FIXTURE_ROOT / "predicate_spec.json", SCHEMA_ROOT / "predicate_spec.schema.json"),
    )
