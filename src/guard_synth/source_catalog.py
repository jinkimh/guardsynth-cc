"""Validated source-bearing catalog boundary for GuardSynth.

The catalog records authoritative claims and explicit operationalization gaps.
It does not interpret free-form CoC, infer scene facts, or invent numeric bounds.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from guard_synth_eblc.schema_validation import load_json, validate


SOURCE_CATALOG_VERSION = "guardsynth-source-catalog-v0.1"
PACKAGE_ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = PACKAGE_ROOT / "schemas/source_catalog.schema.json"
KR_FIXTURE_PATH = PACKAGE_ROOT / "fixtures/source_catalog_kr_v0_1.json"
EXPECTED_SLICES = {
    "PEDESTRIAN_CYCLIST_YIELD",
    "STOP_SIGNALS",
    "FOLLOWING_CUT_IN",
}
EXPECTED_FAMILIES = {
    "PEDESTRIAN_YIELD",
    "CYCLIST_YIELD",
    "SIGNAL_STOP",
    "SIGNAL_CAUTION_PROCEED",
    "LONGITUDINAL_FOLLOWING",
    "CUT_IN_LANE_CHANGE",
}


class SourceCatalogValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SourceCatalog:
    raw: dict[str, Any]

    @property
    def rule_templates(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.raw["rule_templates"])

    @property
    def source_records(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.raw["source_records"])


def _ids(items: Iterable[dict[str, Any]], key: str) -> tuple[str, ...]:
    return tuple(item[key] for item in items)


def _require_unique(items: Iterable[str], label: str) -> set[str]:
    values = tuple(items)
    if len(values) != len(set(values)):
        raise SourceCatalogValidationError(f"duplicate {label}")
    return set(values)


def source_record_hash(record: dict[str, Any]) -> str:
    """Hash the canonical source record, not downloaded document bytes."""

    material = {key: value for key, value in record.items() if key != "record_hash"}
    encoded = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _claim_index(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        for claim in record["claims"]:
            claim_id = claim["claim_id"]
            if claim_id in result:
                raise SourceCatalogValidationError(f"duplicate source claim: {claim_id}")
            result[claim_id] = {"record": record, "claim": claim}
    return result


def _has_numeric_literal(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, list):
        return any(_has_numeric_literal(item) for item in value)
    if isinstance(value, dict):
        return any(_has_numeric_literal(item) for item in value.values())
    return False


def parse_source_catalog(raw: dict[str, Any]) -> SourceCatalog:
    validate(raw, load_json(SCHEMA_PATH))
    if raw["catalog_version"] != SOURCE_CATALOG_VERSION:
        raise SourceCatalogValidationError("unsupported source catalog version")

    source_ids = _require_unique(_ids(raw["source_records"], "evidence_id"), "source record")
    predicate_ids = _require_unique(_ids(raw["predicate_specs"], "predicate_id"), "predicate")
    binder_ids = _require_unique(_ids(raw["binder_specs"], "binder_id"), "binder")
    lifecycle_ids = _require_unique(
        _ids(raw["lifecycle_profiles"], "lifecycle_profile_id"), "lifecycle profile"
    )
    rule_ids = _require_unique(_ids(raw["rule_templates"], "rule_id"), "rule template")
    family_ids = _require_unique(_ids(raw["family_coverage"], "family_id"), "family")
    claims = _claim_index(raw["source_records"])

    for record in raw["source_records"]:
        if record["source_class"] == "LEGAL" and "law.go.kr" not in record["uri"]:
            raise SourceCatalogValidationError("LEGAL source is not an official law.go.kr record")
        if record["record_hash"] != source_record_hash(record):
            raise SourceCatalogValidationError(
                f"source record hash mismatch: {record['evidence_id']}"
            )

    for predicate in raw["predicate_specs"]:
        if "CLAIMED" in predicate["allowed_epistemic"]:
            raise SourceCatalogValidationError("CoC/CLAIMED evidence cannot satisfy a predicate")
        if predicate["failure_value"] != "UNKNOWN":
            raise SourceCatalogValidationError("predicate must fail to UNKNOWN")

    for binder in raw["binder_specs"]:
        for output in binder["outputs"]:
            unknown = set(output["source_claim_refs"]) - set(claims)
            if unknown:
                raise SourceCatalogValidationError(
                    f"unknown binder source claim refs: {sorted(unknown)}"
                )
            if output["kind"] == "UNSUPPORTED" and not output["reason_code"]:
                raise SourceCatalogValidationError("UNSUPPORTED output needs a reason code")

    slices: dict[str, int] = {name: 0 for name in EXPECTED_SLICES}
    for rule in raw["rule_templates"]:
        if rule["slice"] not in slices:
            raise SourceCatalogValidationError(f"unknown slice: {rule['slice']}")
        slices[rule["slice"]] += 1
        unknown_claims = set(rule["source_claim_refs"]) - set(claims)
        unknown_predicates = set(rule["required_predicate_refs"]) - predicate_ids
        if unknown_claims or unknown_predicates:
            raise SourceCatalogValidationError(
                f"open rule references: claims={sorted(unknown_claims)}, "
                f"predicates={sorted(unknown_predicates)}"
            )
        if rule["binder_ref"] not in binder_ids:
            raise SourceCatalogValidationError(f"unknown binder ref: {rule['binder_ref']}")
        if rule["lifecycle_profile_ref"] not in lifecycle_ids:
            raise SourceCatalogValidationError(
                f"unknown lifecycle ref: {rule['lifecycle_profile_ref']}"
            )
        for claim_ref in rule["source_claim_refs"]:
            if not claims[claim_ref]["claim"]["normative"]:
                raise SourceCatalogValidationError(
                    f"rule uses non-normative claim as authority: {claim_ref}"
                )

    if any(count < 4 for count in slices.values()):
        raise SourceCatalogValidationError(f"slice has fewer than four rules: {slices}")
    if family_ids != EXPECTED_FAMILIES:
        raise SourceCatalogValidationError(
            f"family coverage mismatch: {sorted(family_ids)}"
        )
    for family in raw["family_coverage"]:
        if not set(family["rule_refs"]).issubset(rule_ids):
            raise SourceCatalogValidationError(f"family contains unknown rule: {family['family_id']}")

    for section in (raw["rule_templates"], raw["binder_specs"], raw["lifecycle_profiles"]):
        if _has_numeric_literal(section):
            raise SourceCatalogValidationError("unsourced executable numeric literal in catalog")

    if not source_ids:
        raise SourceCatalogValidationError("source catalog is empty")
    return SourceCatalog(raw)


def load_source_catalog(path: Path = KR_FIXTURE_PATH) -> SourceCatalog:
    return parse_source_catalog(load_json(path))


def audit_source_catalog(catalog: SourceCatalog) -> dict[str, Any]:
    raw = catalog.raw
    slice_counts = {
        name: sum(rule["slice"] == name for rule in raw["rule_templates"])
        for name in sorted(EXPECTED_SLICES)
    }
    unsupported_outputs = [
        output
        for binder in raw["binder_specs"]
        for output in binder["outputs"]
        if output["kind"] == "UNSUPPORTED"
    ]
    return {
        "catalog_id": raw["catalog_id"],
        "catalog_version": raw["catalog_version"],
        "jurisdiction": raw["jurisdiction"],
        "source_record_count": len(raw["source_records"]),
        "source_claim_count": sum(len(item["claims"]) for item in raw["source_records"]),
        "predicate_count": len(raw["predicate_specs"]),
        "binder_count": len(raw["binder_specs"]),
        "lifecycle_profile_count": len(raw["lifecycle_profiles"]),
        "rule_template_count": len(raw["rule_templates"]),
        "slice_counts": slice_counts,
        "family_coverage": sorted(item["family_id"] for item in raw["family_coverage"]),
        "family_coverage_count": len(raw["family_coverage"]),
        "unsupported_numeric_output_count": len(unsupported_outputs),
        "unsourced_normative_or_numeric_value_count": 0,
        "reference_closure": True,
        "failure_to_unknown_coverage": {
            "numerator": sum(
                item["failure_value"] == "UNKNOWN" for item in raw["predicate_specs"]
            ),
            "denominator": len(raw["predicate_specs"]),
        },
        "claim_scope": raw["claim_scope"],
    }

