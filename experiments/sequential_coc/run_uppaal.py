"""Execute verifyta safely and translate its property results to common IR."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

from experiments.sequential_coc.contract_ir import CheckResult, ContradictionType


_PRIMARY_FLAGS = (
    ContradictionType.HOLD_GO_CONFLICT,
    ContradictionType.PREMATURE_RELEASE,
    ContradictionType.ORDER_VIOLATION,
    ContradictionType.STALE_OBLIGATION,
)
_EXPECTED_QUERIES = (
    "A[] not sticky_hold_go_conflict",
    "A[] not sticky_premature_release",
    "A[] not sticky_order_violation",
    "A[] not sticky_stale_obligation",
    "A[] not sticky_unknown",
    "A<> Observer.Done",
)
_EXPECTED_CONTRACT_VERSION = "sequential-coc-transition-v2"
_EXPECTED_CONTRACT_SHA256 = (
    "e3f5e437dab029813dd4d5e515426e1079e29ce385108aea60665d87d130c4f8"
)
_FORMULA_STATUS = re.compile(
    r"Formula\s+is\s+(?:(NOT)\s+)?satisfied", re.IGNORECASE
)
_FIRST_INDEX = re.compile(r"\bfirst_violation_idx\s*=\s*(-?\d+)\b")
_EVENT_LABEL = re.compile(r"^event\[(\d+)\]=(.*)$", re.DOTALL)
_CONTRACT_VERSION = re.compile(
    r"^// transition_contract_version=(\S+)$", re.MULTILINE
)
_CONTRACT_SHA256 = re.compile(
    r"^// transition_contract_sha256=([0-9a-f]{64})$", re.MULTILINE
)
_UNKNOWN_TRACE_FLAGS = (
    ("sticky_parse_status_unknown", "PARSE_STATUS_UNKNOWN"),
    ("sticky_overlapping_obligation", "OVERLAPPING_OBLIGATION"),
    ("sticky_stale_release_unknown", "STALE_RELEASE_UNKNOWN"),
    ("sticky_active_release_unknown", "ACTIVE_RELEASE_UNKNOWN"),
    ("sticky_active_satisfaction_unknown", "ACTIVE_SATISFACTION_UNKNOWN"),
)


@dataclass(frozen=True, slots=True)
class VerifytaRunMetadata:
    """Process provenance retained for audit without changing CheckResult."""

    executable: str
    version: str
    command: tuple[str, ...]
    returncode: int | None


_last_run_metadata: VerifytaRunMetadata | None = None


def last_verifyta_run_metadata() -> VerifytaRunMetadata | None:
    return _last_run_metadata


def _unknown(reason: str) -> CheckResult:
    return CheckResult(verdict="UNKNOWN", unknown_reasons=(reason,))


def _existing_file(path: Path, name: str) -> Path:
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(f"{name} is not a file: {candidate}")
    return candidate.resolve()


def _model_metadata(model: Path) -> tuple[dict[int, str], str | None, str | None]:
    tree = ET.parse(model)
    declaration = tree.findtext("declaration") or ""
    version_match = _CONTRACT_VERSION.search(declaration)
    hash_match = _CONTRACT_SHA256.search(declaration)
    mapping: dict[int, str] = {}
    for label in tree.findall(".//label[@kind='comments']"):
        match = _EVENT_LABEL.fullmatch(label.text or "")
        if match:
            mapping[int(match.group(1))] = match.group(2)
    return (
        mapping,
        version_match.group(1) if version_match else None,
        hash_match.group(1) if hash_match else None,
    )


def _unknown_reasons_from_trace(output: str) -> tuple[str, ...]:
    return tuple(
        reason
        for flag, reason in _UNKNOWN_TRACE_FLAGS
        if re.search(rf"\b{re.escape(flag)}\s*=\s*1\b", output)
    )


def _version(executable: Path) -> str:
    try:
        completed = subprocess.run(
            [str(executable), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "VERSION_UNAVAILABLE"
    text = (completed.stdout or completed.stderr).strip()
    return text.splitlines()[0] if text else "VERSION_UNAVAILABLE"


def run_verifyta(model: Path, queries: Path, verifyta: Path) -> CheckResult:
    """Run the real executable without a shell and parse six ordered properties."""
    global _last_run_metadata
    model_path = _existing_file(model, "model")
    query_path = _existing_file(queries, "queries")
    verifyta_path = _existing_file(verifyta, "verifyta")
    if not os.access(verifyta_path, os.X_OK):
        raise PermissionError(f"verifyta is not executable: {verifyta_path}")

    try:
        event_ids, contract_version, contract_hash = _model_metadata(model_path)
    except (ET.ParseError, OSError, UnicodeError, ValueError):
        _last_run_metadata = VerifytaRunMetadata(
            str(verifyta_path), "NOT_RUN", (), None
        )
        return _unknown("MODEL_METADATA_PARSE_FAILURE")
    if (
        contract_version != _EXPECTED_CONTRACT_VERSION
        or contract_hash != _EXPECTED_CONTRACT_SHA256
    ):
        _last_run_metadata = VerifytaRunMetadata(
            str(verifyta_path), "NOT_RUN", (), None
        )
        return _unknown("MODEL_CONTRACT_MISMATCH")

    try:
        query_text = query_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        _last_run_metadata = VerifytaRunMetadata(
            str(verifyta_path), "NOT_RUN", (), None
        )
        return _unknown("QUERY_READ_FAILURE")
    expected_query_text = "\n".join(_EXPECTED_QUERIES) + "\n"
    if query_text != expected_query_text:
        _last_run_metadata = VerifytaRunMetadata(
            str(verifyta_path), "NOT_RUN", (), None
        )
        return _unknown("QUERY_CONTRACT_MISMATCH")

    version = _version(verifyta_path)
    command = (
        str(verifyta_path),
        "-q",
        "-t1",
        str(model_path),
        str(query_path),
    )
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        _last_run_metadata = VerifytaRunMetadata(
            str(verifyta_path), version, command, None
        )
        return _unknown("VERIFYTA_TIMEOUT")
    except OSError:
        _last_run_metadata = VerifytaRunMetadata(
            str(verifyta_path), version, command, None
        )
        return _unknown("VERIFYTA_EXECUTION_FAILURE")

    _last_run_metadata = VerifytaRunMetadata(
        str(verifyta_path), version, command, completed.returncode
    )
    output = "\n".join((completed.stdout, completed.stderr))
    if completed.returncode != 0:
        lowered = output.lower()
        if "license" in lowered and (
            "not set" in lowered
            or "does not cover" in lowered
            or "failed to retrieve" in lowered
        ):
            return _unknown("VERIFYTA_LICENSE_UNAVAILABLE")
        return _unknown(f"VERIFYTA_EXIT_{completed.returncode}")

    statuses = [match.group(1) is None for match in _FORMULA_STATUS.finditer(output)]
    if len(statuses) != len(_EXPECTED_QUERIES):
        return _unknown("VERIFYTA_PARSE_FAILURE")

    contradictions = tuple(
        kind for kind, satisfied in zip(_PRIMARY_FLAGS, statuses[:4]) if not satisfied
    )
    first_id: str | None = None
    observed_indices = [int(match.group(1)) for match in _FIRST_INDEX.finditer(output)]
    first_known_index = next((index for index in observed_indices if index >= 0), None)
    if first_known_index is not None:
        first_id = event_ids.get(first_known_index)
    if not statuses[5]:
        return _unknown("VERIFYTA_PROGRESS_FAILURE")
    unknown_reasons = (
        _unknown_reasons_from_trace(output) if not statuses[4] else ()
    )
    if not statuses[4] and not unknown_reasons:
        unknown_reasons = ("UPPAAL_SEMANTIC_UNKNOWN",)
    if contradictions:
        return CheckResult(
            verdict="CONTRADICTION",
            contradiction_types=contradictions,
            first_event_id=first_id,
            unknown_reasons=unknown_reasons,
        )
    if not statuses[4]:
        return CheckResult(verdict="UNKNOWN", unknown_reasons=unknown_reasons)
    return CheckResult(verdict="CONSISTENT")
