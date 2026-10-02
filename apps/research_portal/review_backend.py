"""Small explicit router for authenticated review operations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import threading
from typing import Any

from apps.research_portal.review_store import ReviewStore, ReviewStoreError
from apps.research_portal.security import SecurityError, validate_route_segment


class BackendError(ValueError):
    def __init__(self, status: int, message: str, data: dict | None = None):
        super().__init__(message)
        self.status = status
        self.data = data or {"error": message}


@dataclass(frozen=True)
class BackendResponse:
    status: int
    data: dict[str, Any]


_FORBIDDEN_EXPORT_KEYS = {
    "canonical_path", "raw_path", "source_path", "sample_id", "scene_id",
    "raw_identifier", "image_bytes", "coc_text", "seed", "seed_ciphertext",
}


def _assert_public_value(value: Any, key: str = "") -> None:
    if key.lower() in _FORBIDDEN_EXPORT_KEYS:
        raise BackendError(400, f"public export contains forbidden field: {key}")
    if isinstance(value, bytes):
        raise BackendError(400, "public export cannot contain binary data")
    if isinstance(value, str) and (value.startswith(("/", "file:")) or "\\" in value or "data:image" in value):
        raise BackendError(400, "public export contains a path or image payload")
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            _assert_public_value(child_value, str(child_key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            _assert_public_value(child)


def build_public_export(
    *,
    project_id: str,
    review_round_id: str,
    progress: dict,
    agreement: dict,
    claim_limitations: list[str],
) -> dict:
    """Build a new deidentified aggregate object, never a DB/file projection."""
    exported = {
        "project_id": project_id,
        "review_round_id": review_round_id,
        "agreement_contract_version": "nominal-krippendorff-alpha-v1",
        "progress": progress,
        "agreement": agreement,
        "claim_limitations": claim_limitations,
    }
    _assert_public_value(exported)
    return exported


def write_public_export_run(
    output_dir: Path,
    exported: dict,
    *,
    experiment_id: str,
    run_id: str,
) -> dict:
    """Materialize a new immutable, aggregate-only public export run."""
    _assert_public_value(exported)
    if "public" not in output_dir.parts:
        raise BackendError(400, "review aggregate export must use a public artifact root")
    if output_dir.exists():
        raise BackendError(409, "refusing to overwrite a public export run")
    output_dir.mkdir(parents=True)
    export_text = json.dumps(exported, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    export_hash = hashlib.sha256(export_text.encode()).hexdigest()
    result = {
        "experiment_id": experiment_id,
        "run_id": run_id,
        "status": "EXPORTED",
        "classification": "PUBLIC_DEIDENTIFIED_AGGREGATE",
        "export_sha256": export_hash,
        "claim_scope": "DEIDENTIFIED_REVIEW_AGGREGATE_NOT_RAW_REVIEW_OR_VEHICLE_SAFETY",
    }
    manifest = {
        "experiment_id": experiment_id,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "input_class": "RESTRICTED_REVIEW_AGGREGATE",
        "output_class": "PUBLIC_DEIDENTIFIED_AGGREGATE",
        "review_export_sha256": export_hash,
        "restricted_payload_copied": False,
        "claim_scope": result["claim_scope"],
    }
    files = {
        "REVIEW_EXPORT.json": export_text,
        "RESULT.json": json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        "RUN_MANIFEST.json": json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    }
    for name, text in files.items():
        path = output_dir / name
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text)
        path.chmod(0o444)
    return result


class ReviewBackend:
    """Route review calls after the HTTP layer has authenticated an actor."""

    def __init__(
        self,
        store: ReviewStore,
        *,
        lead_actor_ids: set[str] | None = None,
        public_export_root: Path | None = None,
    ):
        self.store = store
        self.lead_actor_ids = set(lead_actor_ids or ())
        self.public_export_root = public_export_root
        self._dispatch_lock = threading.RLock()

    @staticmethod
    def _body(body: dict | None) -> dict:
        if not isinstance(body, dict):
            raise BackendError(400, "JSON object body is required")
        return body

    def _require_lead(self, actor_id: str, round_id: str | None = None) -> None:
        if actor_id in self.lead_actor_ids:
            return
        if round_id and self.store.has_capability(round_id, actor_id, "LEAD"):
            return
        raise BackendError(403, "research lead capability is required")

    def dispatch(self, method: str, path: str, *, actor_id: str, body: dict | None) -> BackendResponse:
        with self._dispatch_lock:
            return self._dispatch(method, path, actor_id=actor_id, body=body)

    def _dispatch(self, method: str, path: str, *, actor_id: str, body: dict | None) -> BackendResponse:
        if not actor_id or len(actor_id) > 128:
            raise BackendError(401, "authentication is required")

        assignment_match = re.fullmatch(r"/api/assignments/([^/]+)/reviews", path)
        activity_start = re.fullmatch(r"/api/assignments/([^/]+)/activity/start", path)
        activity_heartbeat = re.fullmatch(r"/api/assignments/([^/]+)/activity/heartbeat", path)
        round_assignments = re.fullmatch(r"/api/rounds/([^/]+)/assignments", path)
        membership_add = re.fullmatch(r"/api/rounds/([^/]+)/memberships", path)
        manifest_freeze = re.fullmatch(r"/api/rounds/([^/]+)/manifest", path)
        guideline_add = re.fullmatch(r"/api/rounds/([^/]+)/guidelines", path)
        round_metrics_route = re.fullmatch(r"/api/rounds/([^/]+)/metrics", path)
        round_finalize = re.fullmatch(r"/api/rounds/([^/]+)/finalize", path)
        public_export = re.fullmatch(r"/api/rounds/([^/]+)/public-export", path)
        empirical_start = re.fullmatch(r"/api/rounds/([^/]+)/empirical/start", path)
        calibration_start = re.fullmatch(r"/api/rounds/([^/]+)/calibration/start", path)
        calibration_complete = re.fullmatch(r"/api/rounds/([^/]+)/calibration/complete", path)
        adjudication_queue = re.fullmatch(r"/api/rounds/([^/]+)/adjudications", path)
        adjudication_submit = re.fullmatch(r"/api/rounds/([^/]+)/samples/([^/]+)/adjudication", path)
        try:
            if method == "GET" and path == "/api/rounds":
                return BackendResponse(200, {"rounds": self.store.rounds_for(actor_id)})

            if method == "POST" and path == "/api/rounds":
                self._require_lead(actor_id)
                payload = self._body(body)
                if set(payload) != {"review_round_id", "review_type", "purpose"}:
                    raise BackendError(400, "round create fields do not match the contract")
                round_id = validate_route_segment(payload["review_round_id"])
                purpose = payload["purpose"]
                if not isinstance(purpose, str) or not 1 <= len(purpose) <= 2000:
                    raise BackendError(400, "round purpose length is invalid")
                self.store.create_round(
                    round_id, review_type=payload["review_type"], purpose=purpose, created_by=actor_id
                )
                self.store.add_membership(round_id, actor_id, "LEAD")
                return BackendResponse(201, {"review_round_id": round_id, "state": "DRAFT"})

            if method == "GET" and round_assignments:
                round_id = validate_route_segment(round_assignments.group(1))
                return BackendResponse(200, {"assignments": self.store.assignments_for(round_id, actor_id)})

            if method == "GET" and adjudication_queue:
                round_id = validate_route_segment(adjudication_queue.group(1))
                return BackendResponse(200, {"queue": self.store.adjudication_queue(round_id, actor_id)})

            if method == "GET" and round_metrics_route:
                round_id = validate_route_segment(round_metrics_route.group(1))
                self._require_lead(actor_id, round_id)
                return BackendResponse(200, self.store.round_metrics(round_id))

            if method == "POST" and membership_add:
                round_id = validate_route_segment(membership_add.group(1))
                self._require_lead(actor_id, round_id)
                payload = self._body(body)
                if set(payload) != {"actor_id", "capability"}:
                    raise BackendError(400, "membership fields do not match the contract")
                member_id = validate_route_segment(payload["actor_id"])
                self.store.add_membership(round_id, member_id, payload["capability"])
                return BackendResponse(201, {"actor_id": member_id, "capability": payload["capability"]})

            if method == "POST" and manifest_freeze:
                round_id = validate_route_segment(manifest_freeze.group(1))
                self._require_lead(actor_id, round_id)
                report = self.store.freeze_sample_manifest(round_id, self._body(body), actor_id=actor_id)
                return BackendResponse(201, report)

            if method == "POST" and round_assignments:
                round_id = validate_route_segment(round_assignments.group(1))
                self._require_lead(actor_id, round_id)
                payload = self._body(body)
                if set(payload) != {"reviewers_per_sample", "seed"}:
                    raise BackendError(400, "assignment fields do not match the contract")
                seed = payload["seed"]
                reviewers_per_sample = payload["reviewers_per_sample"]
                if not isinstance(seed, str) or not 32 <= len(seed) <= 256:
                    raise BackendError(400, "assignment seed length is invalid")
                if isinstance(reviewers_per_sample, bool) or not isinstance(reviewers_per_sample, int):
                    raise BackendError(400, "reviewers_per_sample must be an integer")
                assignments = self.store.assign(
                    round_id, reviewers_per_sample=reviewers_per_sample, seed=seed.encode()
                )
                return BackendResponse(201, {"assignment_count": len(assignments)})

            if method == "POST" and guideline_add:
                round_id = validate_route_segment(guideline_add.group(1))
                self._require_lead(actor_id, round_id)
                payload = self._body(body)
                digest = payload.get("content_hash")
                if set(payload) != {"content_hash"} or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                    raise BackendError(400, "guideline content_hash is invalid")
                revision = self.store.add_guideline_revision(round_id, digest, actor_id=actor_id)
                return BackendResponse(201, {"revision": revision, "content_hash": digest})

            if method == "POST" and round_finalize:
                round_id = validate_route_segment(round_finalize.group(1))
                self._require_lead(actor_id, round_id)
                payload = self._body(body)
                if set(payload) != {"terminal_shortfall"} or not isinstance(payload["terminal_shortfall"], bool):
                    raise BackendError(400, "finalize requires terminal_shortfall boolean")
                result = self.store.finalize_round(
                    round_id,
                    actor_id=actor_id,
                    terminal_shortfall=payload["terminal_shortfall"],
                    backup_dir=self.store.path.parent / "backups",
                    export_path=self.store.path.parent / "ROUND_EXPORT.json",
                )
                return BackendResponse(200, {
                    "review_round_id": result["review_round_id"],
                    "round_state": result["round_state"],
                    "export_sha256": result["export_sha256"],
                    "backup_sha256": result["backup_sha256"],
                })

            if method == "POST" and public_export:
                round_id = validate_route_segment(public_export.group(1))
                self._require_lead(actor_id, round_id)
                if self.public_export_root is None:
                    raise BackendError(404, "public review export is not configured")
                payload = self._body(body)
                if set(payload) != {"run_id", "claim_limitations"}:
                    raise BackendError(400, "public export fields do not match the contract")
                run_id = validate_route_segment(payload["run_id"])
                limitations = payload["claim_limitations"]
                if not isinstance(limitations, list) or not limitations or any(
                    not isinstance(item, str) or not 1 <= len(item) <= 500 for item in limitations
                ):
                    raise BackendError(400, "public export claim_limitations are invalid")
                round_record = self.store.round_record(round_id)
                if round_record["state"] not in {"COMPLETE", "TERMINAL_SHORTFALL"}:
                    raise BackendError(409, "public export requires a closed review round")
                metrics = self.store.round_metrics(round_id)
                exported = build_public_export(
                    project_id=self.store.owner_project_id(),
                    review_round_id=round_id,
                    progress=metrics["progress"],
                    agreement={key: value for key, value in metrics.items() if key not in {"progress", "reviewer_time"}},
                    claim_limitations=limitations,
                )
                result = write_public_export_run(
                    self.public_export_root / run_id,
                    exported,
                    experiment_id="RESEARCH-REVIEW-EXPORT-001",
                    run_id=run_id,
                )
                return BackendResponse(201, {
                    "review_round_id": round_id,
                    "run_id": run_id,
                    "export_sha256": result["export_sha256"],
                })

            if method == "POST" and assignment_match:
                assignment_id = validate_route_segment(assignment_match.group(1))
                if self.store.assignment_owner(assignment_id) != actor_id:
                    raise BackendError(403, "assignment is not owned by this reviewer")
                payload = self._body(body)
                allowed = {"verdict", "revision", "finalize", "rationale", "payload"}
                if set(payload) - allowed or not {"verdict", "revision", "finalize"}.issubset(payload):
                    raise BackendError(400, "review request fields do not match the contract")
                if isinstance(payload["revision"], bool) or not isinstance(payload["revision"], int):
                    raise BackendError(400, "review revision must be an integer")
                if not isinstance(payload["finalize"], bool):
                    raise BackendError(400, "review finalize must be boolean")
                if "rationale" in payload and not isinstance(payload["rationale"], str):
                    raise BackendError(400, "review rationale must be a string")
                self.store.submit_review(
                    assignment_id,
                    payload.get("verdict"),
                    revision=payload.get("revision"),
                    finalize=payload.get("finalize"),
                    rationale=payload.get("rationale", ""),
                    payload=payload.get("payload"),
                )
                return BackendResponse(201, {"assignment_id": assignment_id, "saved": True})

            if method == "POST" and activity_start:
                assignment_id = validate_route_segment(activity_start.group(1))
                if self._body(body):
                    raise BackendError(400, "activity start body must be empty")
                self.store.start_assignment(assignment_id, actor_id=actor_id)
                return BackendResponse(200, {"assignment_id": assignment_id, "activity": "STARTED"})

            if method == "POST" and activity_heartbeat:
                assignment_id = validate_route_segment(activity_heartbeat.group(1))
                if self._body(body):
                    raise BackendError(400, "activity heartbeat body must be empty")
                active = self.store.touch_assignment(assignment_id, actor_id=actor_id)
                return BackendResponse(200, {"assignment_id": assignment_id, "active_seconds": active})

            if method == "POST" and adjudication_submit:
                round_id = validate_route_segment(adjudication_submit.group(1))
                sample_id = validate_route_segment(adjudication_submit.group(2))
                payload = self._body(body)
                if set(payload) - {"verdict", "rationale", "payload"}:
                    raise BackendError(400, "adjudication request contains unknown fields")
                self.store.adjudicate(
                    round_id,
                    sample_id,
                    adjudicator_id=actor_id,
                    verdict=payload.get("verdict"),
                    rationale=payload.get("rationale", ""),
                    payload=payload.get("payload"),
                )
                return BackendResponse(201, {"sample_id": sample_id, "adjudicated": True})

            if method == "POST" and calibration_start:
                round_id = validate_route_segment(calibration_start.group(1))
                self._require_lead(actor_id, round_id)
                payload = self._body(body)
                if set(payload) != {"schema_ui_export_validated"} or not isinstance(payload["schema_ui_export_validated"], bool):
                    raise BackendError(400, "calibration start evidence is invalid")
                self.store.set_gate_evidence(
                    round_id,
                    actor_id=actor_id,
                    schema_ui_export_validated=payload["schema_ui_export_validated"],
                )
                gate = self.store.m16_gate(round_id)
                if not gate["calibration_start_allowed"]:
                    if self.store.round_record(round_id)["state"] == "DRAFT":
                        self.store.transition_round(round_id, "ELIGIBILITY_BLOCKED", actor_id=actor_id)
                    raise BackendError(403, "calibration gate is closed", gate)
                state = self.store.round_record(round_id)["state"]
                if state in {"DRAFT", "ELIGIBILITY_BLOCKED"}:
                    self.store.transition_round(round_id, "READY_CALIBRATION", actor_id=actor_id)
                self.store.transition_round(round_id, "CALIBRATION_ACTIVE", actor_id=actor_id)
                return BackendResponse(200, gate)

            if method == "POST" and calibration_complete:
                round_id = validate_route_segment(calibration_complete.group(1))
                self._require_lead(actor_id, round_id)
                payload = self._body(body)
                expected = {"calibration_complete", "reviewer_training_complete", "baseline_model_split_manifest_frozen"}
                if set(payload) != expected or any(not isinstance(payload[key], bool) for key in expected):
                    raise BackendError(400, "calibration completion evidence is invalid")
                self.store.set_gate_evidence(
                    round_id,
                    actor_id=actor_id,
                    calibration_complete=payload["calibration_complete"],
                    reviewer_training_complete=payload["reviewer_training_complete"],
                    baseline_split_frozen=payload["baseline_model_split_manifest_frozen"],
                )
                gate = self.store.m16_gate(round_id)
                if not gate["empirical_annotation_start_allowed"]:
                    raise BackendError(403, "empirical annotation gate is closed", gate)
                if self.store.round_record(round_id)["state"] != "CALIBRATION_ACTIVE":
                    raise BackendError(409, "round is not in calibration")
                self.store.transition_round(round_id, "READY_EMPIRICAL", actor_id=actor_id)
                return BackendResponse(200, gate)

            if method == "POST" and empirical_start:
                round_id = validate_route_segment(empirical_start.group(1))
                self._require_lead(actor_id, round_id)
                payload = self._body(body)
                if payload:
                    raise BackendError(400, "empirical start derives all gate evidence server-side")
                gate = self.store.m16_gate(round_id)
                if not gate["empirical_annotation_start_allowed"]:
                    raise BackendError(403, "empirical annotation gate is closed", gate)
                if self.store.round_record(round_id)["state"] != "READY_EMPIRICAL":
                    raise BackendError(409, "round is not ready for empirical annotation")
                self.store.transition_round(round_id, "EMPIRICAL_ACTIVE", actor_id=actor_id)
                return BackendResponse(200, gate)
        except (ReviewStoreError, SecurityError) as exc:
            raise BackendError(400, str(exc)) from exc
        raise BackendError(404, "route not found")
