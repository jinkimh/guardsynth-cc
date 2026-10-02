"""Fail-closed UN-treaty normative authority binding for the M16 cohort."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Iterable
from urllib.parse import urlparse


CATALOG_VERSION = "guardsynth-m16-treaty-authority-v0.1"
CATALOG_PATH = (
    Path(__file__).resolve().parent
    / "fixtures/m16_treaty_authority_catalog_v0_1.json"
)
SLICES = {
    "PEDESTRIAN_CYCLIST_YIELD",
    "STOP_SIGNALS",
    "FOLLOWING_CUT_IN",
}
RULE_STRENGTHS = {"DIRECT_TREATY_RULE", "GENERAL_DUE_CARE_FALLBACK"}
OFFICIAL_HOSTS = {"treaties.un.org", "unece.org"}


def _unique(items: Iterable[str], label: str) -> set[str]:
    values = tuple(items)
    if len(values) != len(set(values)):
        raise ValueError(f"M16_TREATY_DUPLICATE_{label}")
    return set(values)


def load_treaty_authority_catalog(source: Path | dict[str, Any]) -> dict[str, Any]:
    """Load and structurally audit the deliberately small M16 treaty catalog."""

    raw = (
        json.loads(source.read_text(encoding="utf-8"))
        if isinstance(source, Path)
        else deepcopy(source)
    )
    required = {
        "catalog_id",
        "catalog_version",
        "authority_class",
        "status_checked_on",
        "source_records",
        "frameworks",
        "country_bindings",
        "slice_mappings",
        "legal_compliance_claim",
        "claim_scope",
    }
    if not isinstance(raw, dict) or not required.issubset(raw):
        raise ValueError("M16_TREATY_CATALOG_STRUCTURE_INVALID")
    if raw["catalog_version"] != CATALOG_VERSION:
        raise ValueError("M16_TREATY_CATALOG_VERSION_INVALID")
    if raw["authority_class"] != "INTERNATIONAL_TREATY_NORMATIVE_BASELINE":
        raise ValueError("M16_TREATY_AUTHORITY_CLASS_INVALID")
    if raw["legal_compliance_claim"] != "NOT_PERMITTED":
        raise ValueError("M16_TREATY_LEGAL_COMPLIANCE_BOUNDARY_INVALID")

    source_ids = _unique(
        (record.get("source_id") for record in raw["source_records"]), "SOURCE_ID"
    )
    for record in raw["source_records"]:
        parsed = urlparse(str(record.get("uri", "")))
        if (
            parsed.scheme != "https"
            or parsed.hostname not in OFFICIAL_HOSTS
            or record.get("official_host") != parsed.hostname
        ):
            raise ValueError("M16_TREATY_NON_OFFICIAL_SOURCE")

    framework_ids = _unique(
        (item.get("framework_id") for item in raw["frameworks"]), "FRAMEWORK_ID"
    )
    for framework in raw["frameworks"]:
        refs = set(framework.get("party_status_source_refs", ())) | set(
            framework.get("normative_text_source_refs", ())
        )
        if not refs or not refs.issubset(source_ids):
            raise ValueError("M16_TREATY_FRAMEWORK_SOURCE_REF_INVALID")

    countries = _unique(
        (item.get("country") for item in raw["country_bindings"]), "COUNTRY"
    )
    country_codes = _unique(
        (item.get("country_code") for item in raw["country_bindings"]), "COUNTRY_CODE"
    )
    if len(countries) != len(country_codes):
        raise ValueError("M16_TREATY_COUNTRY_BINDING_INVALID")
    for item in raw["country_bindings"]:
        if (
            not isinstance(item.get("country_code"), str)
            or re.fullmatch(r"[A-Z]{2}", item["country_code"]) is None
            or item.get("framework_ref") not in framework_ids
            or item.get("participant_status") != "PARTY"
        ):
            raise ValueError("M16_TREATY_COUNTRY_BINDING_INVALID")

    mapping_keys: set[tuple[str, str]] = set()
    for mapping in raw["slice_mappings"]:
        key = (mapping.get("framework_ref"), mapping.get("slice"))
        if key in mapping_keys:
            raise ValueError("M16_TREATY_DUPLICATE_SLICE_MAPPING")
        mapping_keys.add(key)
        if (
            key[0] not in framework_ids
            or key[1] not in SLICES
            or mapping.get("rule_strength") not in RULE_STRENGTHS
            or not isinstance(mapping.get("domestic_detail_required"), bool)
            or not mapping.get("article_refs")
            or not set(mapping.get("source_refs", ())).issubset(source_ids)
        ):
            raise ValueError("M16_TREATY_SLICE_MAPPING_INVALID")
    expected = {(framework_id, slice_name) for framework_id in framework_ids for slice_name in SLICES}
    if mapping_keys != expected:
        raise ValueError("M16_TREATY_SLICE_MAPPING_INCOMPLETE")
    return raw


def bind_treaty_authority(
    records: Iterable[dict[str, Any]], catalog: dict[str, Any]
) -> dict[str, Any]:
    """Bind country and slice to a treaty baseline without asserting local compliance."""

    catalog = load_treaty_authority_catalog(catalog)
    countries = {item["country"]: item for item in catalog["country_bindings"]}
    mappings = {
        (item["framework_ref"], item["slice"]): item
        for item in catalog["slice_mappings"]
    }
    bound: list[dict[str, Any]] = []
    for supplied in records:
        record = deepcopy(supplied)
        country = countries.get(record.get("country"))
        mapping = mappings.get(
            (country["framework_ref"], record.get("slice"))
        ) if country else None
        if country is None or mapping is None:
            record.update({
                "authority_status": "REVIEW_REQUIRED_NO_TREATY_BINDING",
                "legal_compliance_claim": "NOT_PERMITTED",
            })
        else:
            tasks = [
                task for task in record.get("next_source_tasks", [])
                if task != "BIND_JURISDICTION_MATCHED_AUTHORITY"
            ]
            record.update({
                "authority_status": "AVAILABLE_TREATY_NORMATIVE_BASELINE",
                "scope_compatibility": "TREATY_NORMATIVE_BASELINE_COMPATIBLE",
                "authority_class": catalog["authority_class"],
                "authority_catalog_id": catalog["catalog_id"],
                "authority_catalog_version": catalog["catalog_version"],
                "country_code": country["country_code"],
                "participant_status": country["participant_status"],
                "framework_ref": country["framework_ref"],
                "rule_strength": mapping["rule_strength"],
                "article_refs": deepcopy(mapping["article_refs"]),
                "source_refs": deepcopy(mapping["source_refs"]),
                "rule_summary": mapping["rule_summary"],
                "domestic_detail_required": mapping["domestic_detail_required"],
                "legal_compliance_claim": "NOT_PERMITTED",
                "next_source_tasks": tasks,
            })
        bound.append(record)

    authority_bound_count = sum(
        item.get("authority_status") == "AVAILABLE_TREATY_NORMATIVE_BASELINE"
        for item in bound
    )
    return {
        "audit_version": "guardsynth-m16-treaty-authority-binding-v0.1",
        "catalog_id": catalog["catalog_id"],
        "catalog_version": catalog["catalog_version"],
        "status_checked_on": catalog["status_checked_on"],
        "record_count": len(bound),
        "authority_bound_count": authority_bound_count,
        "unbound_count": len(bound) - authority_bound_count,
        "direct_treaty_rule_count": sum(
            item.get("rule_strength") == "DIRECT_TREATY_RULE" for item in bound
        ),
        "general_due_care_fallback_count": sum(
            item.get("rule_strength") == "GENERAL_DUE_CARE_FALLBACK" for item in bound
        ),
        "domestic_detail_required_count": sum(
            item.get("domestic_detail_required") is True for item in bound
        ),
        "domestic_legal_compliance_closed_count": 0,
        "records": bound,
        "claim_scope": catalog["claim_scope"],
    }
