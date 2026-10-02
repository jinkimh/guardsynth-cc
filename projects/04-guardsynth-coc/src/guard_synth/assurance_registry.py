"""Source-bearing vehicle assurance registry with exact, fail-closed lookup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from guard_synth_eblc.schema_validation import load_json, validate


REGISTRY_VERSION = "guardsynth-vehicle-assurance-registry-v0.1"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas/vehicle_assurance_registry.schema.json"


class AssuranceRegistryValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AssuranceEvidence:
    evidence_ref: str
    source_class: str
    uri: str
    version: str
    sha256: str
    scope: str


@dataclass(frozen=True, slots=True)
class AssuranceProfile:
    profile_id: str
    vehicle_binding_key: str
    maximum_service_deceleration_mps2: float
    response_time_s: float
    position_uncertainty_m: float
    evidence: AssuranceEvidence


@dataclass(frozen=True, slots=True)
class AssuranceRegistry:
    registry_id: str
    profiles: tuple[AssuranceProfile, ...]

    def resolve(self, vehicle_binding_key: str) -> AssuranceProfile | None:
        """Return only an exact binding; there is deliberately no fallback."""
        return next(
            (item for item in self.profiles if item.vehicle_binding_key == vehicle_binding_key),
            None,
        )


def parse_assurance_registry(raw: dict[str, Any]) -> AssuranceRegistry:
    validate(raw, load_json(SCHEMA_PATH))
    text_fields = [raw["registry_id"]]
    for item in raw["profiles"]:
        text_fields.extend((item["profile_id"], item["vehicle_binding_key"]))
        evidence = item["evidence"]
        text_fields.extend((
            evidence["evidence_ref"], evidence["uri"], evidence["version"], evidence["scope"],
        ))
    if any(not value.strip() for value in text_fields):
        raise AssuranceRegistryValidationError("blank assurance identifier or source field")
    allowed_schemes = {"urn", "file", "https"}
    if any(
        urlparse(item["evidence"]["uri"]).scheme.lower() not in allowed_schemes
        for item in raw["profiles"]
    ):
        raise AssuranceRegistryValidationError("assurance source URI requires urn, file, or https")
    if any(float(item["maximum_service_deceleration_mps2"]) <= 0 for item in raw["profiles"]):
        raise AssuranceRegistryValidationError("deceleration must be positive")
    if any(
        len(item["evidence"]["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in item["evidence"]["sha256"])
        for item in raw["profiles"]
    ):
        raise AssuranceRegistryValidationError("invalid lowercase SHA-256 evidence digest")
    bindings = [item["vehicle_binding_key"] for item in raw["profiles"]]
    profile_ids = [item["profile_id"] for item in raw["profiles"]]
    evidence_refs = [item["evidence"]["evidence_ref"] for item in raw["profiles"]]
    if len(set(bindings)) != len(bindings):
        raise AssuranceRegistryValidationError("duplicate vehicle binding key")
    if len(set(profile_ids)) != len(profile_ids):
        raise AssuranceRegistryValidationError("duplicate profile id")
    if len(set(evidence_refs)) != len(evidence_refs):
        raise AssuranceRegistryValidationError("duplicate assurance evidence ref")
    profiles = tuple(
        AssuranceProfile(
            profile_id=item["profile_id"],
            vehicle_binding_key=item["vehicle_binding_key"],
            maximum_service_deceleration_mps2=float(item["maximum_service_deceleration_mps2"]),
            response_time_s=float(item["response_time_s"]),
            position_uncertainty_m=float(item["position_uncertainty_m"]),
            evidence=AssuranceEvidence(**item["evidence"]),
        )
        for item in raw["profiles"]
    )
    return AssuranceRegistry(raw["registry_id"], profiles)


def load_assurance_registry(path: Path) -> AssuranceRegistry:
    return parse_assurance_registry(load_json(path))
