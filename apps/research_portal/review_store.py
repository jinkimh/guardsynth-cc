"""Round-scoped SQLite persistence for independent research review."""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from apps.research_portal.review_metrics import (
    categorical_agreement,
    correction_rates,
    interval_agreement,
    m16_start_gate,
    nominal_krippendorff_alpha,
    reviewer_time_summary,
    round_progress,
    source_set_agreement,
)
from apps.research_portal.sample_manifest import SampleManifestError, validate_sample_manifest


class ReviewStoreError(ValueError):
    pass


REVIEW_TYPES = {
    "M16_SOURCE_REVIEW",
    "M16_EXPERT_PILOT",
    "IMAGE_ONLY_SCENE_REVIEW",
    "ASSOCIATION_LIFECYCLE_REVIEW",
    "SPECIFICATION_INTERFACE_REVIEW",
    "EBLC_LANGUAGE_EVALUATION",
    "PAPER_INTERNAL_CLAIM_REVIEW",
}
VERDICTS = {
    "SOURCE_COMPLETE", "REVIEW_REQUIRED", "UNSUPPORTED", "CONFLICT",
    "APPLICABLE", "NOT_APPLICABLE", "ABSTAIN",
    "ACCEPT", "REVISE", "REJECT", "PASS", "FAIL",
}
ROUND_TRANSITIONS = {
    "DRAFT": {"ELIGIBILITY_BLOCKED", "READY_CALIBRATION"},
    "ELIGIBILITY_BLOCKED": {"READY_CALIBRATION", "TERMINAL_SHORTFALL"},
    "READY_CALIBRATION": {"CALIBRATION_ACTIVE"},
    "CALIBRATION_ACTIVE": {"READY_EMPIRICAL", "TERMINAL_SHORTFALL"},
    "READY_EMPIRICAL": {"EMPIRICAL_ACTIVE"},
    "EMPIRICAL_ACTIVE": {"ADJUDICATION_ACTIVE", "COMPLETE", "TERMINAL_SHORTFALL"},
    "ADJUDICATION_ACTIVE": {"COMPLETE", "TERMINAL_SHORTFALL"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewStore:
    def __init__(self, path: Path, connection: sqlite3.Connection):
        self.path = path
        self.connection = connection
        self.connection.row_factory = sqlite3.Row

    @classmethod
    def create(cls, path: Path, *, owner_project_id: str, classification: str) -> "ReviewStore":
        if path.exists():
            raise ReviewStoreError(f"review database already exists: {path}")
        if classification not in {"RESTRICTED", "PUBLIC", "INTERMEDIATE"}:
            raise ReviewStoreError("invalid database classification")
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, check_same_thread=False)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.executescript(
            """
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE rounds (
              review_round_id TEXT PRIMARY KEY, review_type TEXT NOT NULL, purpose TEXT NOT NULL,
              state TEXT NOT NULL DEFAULT 'DRAFT', max_revisions INTEGER NOT NULL DEFAULT 2,
              created_by TEXT NOT NULL, created_at TEXT NOT NULL, closed_at TEXT,
              sample_manifest_hash TEXT, manifest_frozen INTEGER NOT NULL DEFAULT 0,
              assignment_hash TEXT, assignment_seed_hash TEXT,
              assignment_algorithm_version TEXT,
              schema_ui_export_validated INTEGER NOT NULL DEFAULT 0,
              calibration_complete INTEGER NOT NULL DEFAULT 0,
              reviewer_training_complete INTEGER NOT NULL DEFAULT 0,
              baseline_split_frozen INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE memberships (
              review_round_id TEXT NOT NULL REFERENCES rounds(review_round_id), actor_id TEXT NOT NULL,
              capability TEXT NOT NULL CHECK(capability IN ('REVIEW','ADJUDICATE','LEAD')),
              PRIMARY KEY(review_round_id, actor_id, capability)
            );
            CREATE TABLE samples (
              review_round_id TEXT NOT NULL REFERENCES rounds(review_round_id), sample_id TEXT NOT NULL,
              slice_name TEXT, outcome TEXT, source_closure TEXT,
              manifest_json TEXT NOT NULL DEFAULT '{}',
              PRIMARY KEY(review_round_id, sample_id)
            );
            CREATE TABLE assignments (
              assignment_id TEXT PRIMARY KEY, review_round_id TEXT NOT NULL, sample_id TEXT NOT NULL,
              reviewer_id TEXT NOT NULL, slot INTEGER NOT NULL,
              UNIQUE(review_round_id, sample_id, reviewer_id),
              FOREIGN KEY(review_round_id, sample_id) REFERENCES samples(review_round_id, sample_id)
            );
            CREATE TABLE review_revisions (
              assignment_id TEXT NOT NULL REFERENCES assignments(assignment_id), revision INTEGER NOT NULL,
              verdict TEXT NOT NULL, rationale TEXT NOT NULL DEFAULT '', finalized INTEGER NOT NULL,
              payload_json TEXT NOT NULL DEFAULT '{}', active_seconds REAL NOT NULL DEFAULT 0,
              calibration INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
              PRIMARY KEY(assignment_id, revision)
            );
            CREATE TABLE assignment_activity (
              assignment_id TEXT PRIMARY KEY REFERENCES assignments(assignment_id),
              started_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
              active_seconds REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE adjudications (
              review_round_id TEXT NOT NULL, sample_id TEXT NOT NULL, adjudicator_id TEXT NOT NULL,
              verdict TEXT NOT NULL, rationale TEXT NOT NULL,
              payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
              PRIMARY KEY(review_round_id, sample_id)
            );
            CREATE TABLE guideline_revisions (
              review_round_id TEXT NOT NULL REFERENCES rounds(review_round_id), revision INTEGER NOT NULL,
              content_hash TEXT NOT NULL, created_at TEXT NOT NULL,
              PRIMARY KEY(review_round_id, revision)
            );
            CREATE TABLE audit_events (
              event_id INTEGER PRIMARY KEY AUTOINCREMENT, review_round_id TEXT, actor_id TEXT NOT NULL,
              action TEXT NOT NULL, object_id TEXT, result TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            (("schema_version", "2"), ("owner_project_id", owner_project_id), ("classification", classification)),
        )
        connection.commit()
        return cls(path, connection)

    @classmethod
    def open(cls, path: Path, *, owner_project_id: str, classification: str) -> "ReviewStore":
        connection = sqlite3.connect(path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        values = dict(connection.execute("SELECT key, value FROM metadata"))
        if values.get("owner_project_id") != owner_project_id or values.get("classification") != classification:
            connection.close()
            raise ReviewStoreError("review database owner or classification mismatch")
        if values.get("schema_version") != "2":
            connection.close()
            raise ReviewStoreError("unsupported review database schema version")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return cls(path, connection)

    def close(self) -> None:
        self.connection.close()

    def _round_open(self, round_id: str) -> sqlite3.Row:
        row = self.connection.execute("SELECT * FROM rounds WHERE review_round_id = ?", (round_id,)).fetchone()
        if row is None:
            raise ReviewStoreError("unknown review round")
        if row["state"] in {"COMPLETE", "TERMINAL_SHORTFALL"}:
            raise ReviewStoreError("review round is closed")
        return row

    def _audit(self, round_id: str, actor: str, action: str, object_id: str, result: str = "SUCCESS") -> None:
        self.connection.execute(
            "INSERT INTO audit_events(review_round_id, actor_id, action, object_id, result, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (round_id, actor, action, object_id, result, _now()),
        )

    def create_round(self, round_id: str, *, review_type: str, purpose: str, created_by: str) -> None:
        if review_type not in REVIEW_TYPES:
            raise ReviewStoreError("unsupported review type")
        if self.connection.execute("SELECT 1 FROM rounds LIMIT 1").fetchone():
            raise ReviewStoreError("a review database can own exactly one round")
        with self.connection:
            self.connection.execute(
                "INSERT INTO rounds(review_round_id, review_type, purpose, created_by, created_at) VALUES (?, ?, ?, ?, ?)",
                (round_id, review_type, purpose, created_by, _now()),
            )
            self._audit(round_id, created_by, "ROUND_CREATED", round_id)

    def add_sample(self, round_id: str, sample_id: str) -> None:
        self._round_open(round_id)
        with self.connection:
            self.connection.execute(
                "INSERT INTO samples(review_round_id, sample_id) VALUES (?, ?)",
                (round_id, sample_id),
            )

    def _metadata(self) -> dict[str, str]:
        return dict(self.connection.execute("SELECT key, value FROM metadata"))

    def owner_project_id(self) -> str:
        return self._metadata()["owner_project_id"]

    def freeze_sample_manifest(self, round_id: str, manifest: dict, *, actor_id: str) -> dict:
        row = self._round_open(round_id)
        if row["manifest_frozen"]:
            raise ReviewStoreError("sample manifest is already frozen")
        if self.connection.execute(
            "SELECT 1 FROM samples WHERE review_round_id = ? LIMIT 1", (round_id,)
        ).fetchone():
            raise ReviewStoreError("cannot freeze a manifest after samples were added")
        metadata = self._metadata()
        if manifest.get("project_id") != metadata["owner_project_id"]:
            raise ReviewStoreError("sample manifest project owner mismatch")
        if manifest.get("classification") != metadata["classification"]:
            raise ReviewStoreError("sample manifest classification mismatch")
        if manifest.get("review_round_id") != round_id or manifest.get("review_type") != row["review_type"]:
            raise ReviewStoreError("sample manifest round contract mismatch")
        try:
            report = validate_sample_manifest(manifest)
        except SampleManifestError as exc:
            raise ReviewStoreError(str(exc)) from exc
        with self.connection:
            self.connection.executemany(
                """INSERT INTO samples(
                       review_round_id, sample_id, slice_name, outcome, source_closure, manifest_json
                   ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    (
                        round_id,
                        sample["sample_id"],
                        sample["slice"],
                        sample["outcome"],
                        sample["source_closure"],
                        json.dumps(sample, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    )
                    for sample in manifest["samples"]
                ),
            )
            self.connection.execute(
                "UPDATE rounds SET sample_manifest_hash = ?, manifest_frozen = 1 WHERE review_round_id = ?",
                (report["manifest_hash"], round_id),
            )
            self._audit(round_id, actor_id, "SAMPLE_MANIFEST_FROZEN", report["manifest_hash"])
        return report

    def transition_round(self, round_id: str, new_state: str, *, actor_id: str) -> None:
        row = self._round_open(round_id)
        if new_state not in ROUND_TRANSITIONS.get(row["state"], set()):
            raise ReviewStoreError(f"invalid round transition: {row['state']} -> {new_state}")
        with self.connection:
            self.connection.execute(
                "UPDATE rounds SET state = ? WHERE review_round_id = ?", (new_state, round_id)
            )
            self._audit(round_id, actor_id, "ROUND_TRANSITION", new_state)

    def add_membership(self, round_id: str, actor_id: str, capability: str) -> None:
        self._round_open(round_id)
        if capability not in {"REVIEW", "ADJUDICATE", "LEAD"}:
            raise ReviewStoreError("unsupported membership capability")
        with self.connection:
            self.connection.execute("INSERT INTO memberships VALUES (?, ?, ?)", (round_id, actor_id, capability))

    def clear_draft_assignments(self, round_id: str) -> None:
        if self.connection.execute(
            "SELECT 1 FROM review_revisions r JOIN assignments a USING(assignment_id) WHERE a.review_round_id = ? LIMIT 1",
            (round_id,),
        ).fetchone():
            raise ReviewStoreError("assignments with reviews are immutable")
        if self.connection.execute(
            "SELECT 1 FROM assignment_activity x JOIN assignments a USING(assignment_id) WHERE a.review_round_id = ? LIMIT 1",
            (round_id,),
        ).fetchone():
            raise ReviewStoreError("assignments with activity are immutable")
        with self.connection:
            self.connection.execute("DELETE FROM assignments WHERE review_round_id = ?", (round_id,))

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ReviewStoreError("invalid activity timestamp") from exc
        if parsed.tzinfo is None:
            raise ReviewStoreError("activity timestamp must include timezone")
        return parsed

    def start_assignment(self, assignment_id: str, *, actor_id: str, at: str | None = None) -> None:
        assignment = self.connection.execute(
            "SELECT review_round_id, reviewer_id FROM assignments WHERE assignment_id = ?", (assignment_id,)
        ).fetchone()
        if assignment is None or assignment["reviewer_id"] != actor_id:
            raise ReviewStoreError("assignment is not owned by this reviewer")
        self._round_open(assignment["review_round_id"])
        timestamp = at or _now()
        self._parse_timestamp(timestamp)
        with self.connection:
            self.connection.execute(
                """INSERT INTO assignment_activity(assignment_id, started_at, last_seen_at)
                   VALUES (?, ?, ?) ON CONFLICT(assignment_id) DO NOTHING""",
                (assignment_id, timestamp, timestamp),
            )
            self._audit(assignment["review_round_id"], actor_id, "ASSIGNMENT_STARTED", assignment_id)

    def touch_assignment(
        self,
        assignment_id: str,
        *,
        actor_id: str,
        at: str | None = None,
        idle_timeout_seconds: float = 300,
    ) -> float:
        assignment = self.connection.execute(
            "SELECT review_round_id, reviewer_id FROM assignments WHERE assignment_id = ?", (assignment_id,)
        ).fetchone()
        if assignment is None or assignment["reviewer_id"] != actor_id:
            raise ReviewStoreError("assignment is not owned by this reviewer")
        activity = self.connection.execute(
            "SELECT last_seen_at, active_seconds FROM assignment_activity WHERE assignment_id = ?", (assignment_id,)
        ).fetchone()
        if activity is None:
            raise ReviewStoreError("assignment activity was not started")
        timestamp = at or _now()
        current = self._parse_timestamp(timestamp)
        previous = self._parse_timestamp(activity["last_seen_at"])
        delta = (current - previous).total_seconds()
        if delta < 0:
            raise ReviewStoreError("assignment activity time moved backwards")
        active = float(activity["active_seconds"])
        if delta <= idle_timeout_seconds:
            active += delta
        with self.connection:
            self.connection.execute(
                "UPDATE assignment_activity SET last_seen_at = ?, active_seconds = ? WHERE assignment_id = ?",
                (timestamp, active, assignment_id),
            )
        return active

    def assign(self, round_id: str, *, reviewers_per_sample: int, seed: bytes) -> list[dict]:
        self._round_open(round_id)
        reviewers = [row[0] for row in self.connection.execute(
            "SELECT actor_id FROM memberships WHERE review_round_id = ? AND capability = 'REVIEW' ORDER BY actor_id", (round_id,)
        )]
        adjudicators = {row[0] for row in self.connection.execute(
            "SELECT actor_id FROM memberships WHERE review_round_id = ? AND capability = 'ADJUDICATE'", (round_id,)
        )}
        if adjudicators.intersection(reviewers):
            raise ReviewStoreError("adjudicator cannot also be an independent reviewer")
        if reviewers_per_sample < 2 or len(reviewers) < reviewers_per_sample:
            raise ReviewStoreError("at least two distinct reviewers are required")
        if self.connection.execute("SELECT 1 FROM assignments WHERE review_round_id = ? LIMIT 1", (round_id,)).fetchone():
            raise ReviewStoreError("assignments already exist")
        samples = [row[0] for row in self.connection.execute(
            "SELECT sample_id FROM samples WHERE review_round_id = ? ORDER BY sample_id", (round_id,)
        )]
        if not samples:
            raise ReviewStoreError("cannot assign an empty sample manifest")
        sample_order = sorted(samples, key=lambda sample: hmac.new(seed, f"sample\0{sample}".encode(), hashlib.sha256).digest())
        loads = {reviewer: 0 for reviewer in reviewers}
        rows: list[dict] = []
        for sample in sample_order:
            chosen: set[str] = set()
            for slot in range(reviewers_per_sample):
                reviewer = min(
                    (item for item in reviewers if item not in chosen),
                    key=lambda item: (loads[item], hmac.new(seed, f"{sample}\0{item}\0{slot}".encode(), hashlib.sha256).digest(), item),
                )
                chosen.add(reviewer)
                loads[reviewer] += 1
                digest = hashlib.sha256(f"{round_id}\0{sample}\0{reviewer}\0{slot}".encode()).hexdigest()[:20]
                rows.append({"assignment_id": f"asg-{digest}", "sample_id": sample, "reviewer_id": reviewer, "slot": slot})
        if max(loads.values()) - min(loads.values()) > 1:
            raise ReviewStoreError("assignment algorithm did not produce balanced loads")
        assignment_hash = hashlib.sha256(
            json.dumps(sorted(rows, key=lambda row: row["assignment_id"]), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with self.connection:
            self.connection.executemany(
                "INSERT INTO assignments VALUES (?, ?, ?, ?, ?)",
                ((row["assignment_id"], round_id, row["sample_id"], row["reviewer_id"], row["slot"]) for row in rows),
            )
            self.connection.execute(
                """UPDATE rounds SET assignment_hash = ?, assignment_seed_hash = ?,
                          assignment_algorithm_version = ? WHERE review_round_id = ?""",
                (assignment_hash, hashlib.sha256(seed).hexdigest(), "hmac-sha256-balanced-v1", round_id),
            )
            self._audit(round_id, "system", "ASSIGNMENTS_FROZEN", assignment_hash)
        return sorted(rows, key=lambda row: row["assignment_id"])

    def submit_review(
        self,
        assignment_id: str,
        verdict: str,
        *,
        revision: int,
        finalize: bool,
        rationale: str = "",
        payload: dict | None = None,
    ) -> None:
        if verdict not in VERDICTS:
            raise ReviewStoreError("invalid review verdict")
        assignment = self.connection.execute("SELECT * FROM assignments WHERE assignment_id = ?", (assignment_id,)).fetchone()
        if assignment is None:
            raise ReviewStoreError("unknown assignment")
        round_row = self._round_open(assignment["review_round_id"])
        if revision < 0 or revision > round_row["max_revisions"]:
            raise ReviewStoreError("review revision exceeds round limit")
        payload_value = payload or {}
        if not isinstance(payload_value, dict):
            raise ReviewStoreError("review payload must be an object")
        if round_row["review_type"] == "M16_EXPERT_PILOT":
            required = {"applicability", "field_values", "source_ids", "corrections", "confidence", "calibration"}
            if set(payload_value) != required:
                raise ReviewStoreError("M16 expert review payload fields do not match the contract")
            if not isinstance(payload_value["applicability"], str) or not payload_value["applicability"]:
                raise ReviewStoreError("review applicability must be a non-empty category")
            if not isinstance(payload_value["field_values"], dict):
                raise ReviewStoreError("review field_values must be an object")
            if not isinstance(payload_value["corrections"], list):
                raise ReviewStoreError("review corrections must be a list")
            if not isinstance(payload_value["calibration"], bool):
                raise ReviewStoreError("review calibration must be boolean")
            confidence = payload_value["confidence"]
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                raise ReviewStoreError("review confidence must be between zero and one")
            if not isinstance(payload_value["source_ids"], list) or any(
                not isinstance(item, str) or "/" in item or "\\" in item for item in payload_value["source_ids"]
            ):
                raise ReviewStoreError("review source_ids must be normalized ids")
        activity = self.connection.execute(
            "SELECT active_seconds FROM assignment_activity WHERE assignment_id = ?", (assignment_id,)
        ).fetchone()
        active_seconds = float(activity[0]) if activity else 0.0
        calibration = int(payload_value.get("calibration") is True)
        with self.connection:
            try:
                self.connection.execute(
                    """INSERT INTO review_revisions(
                           assignment_id, revision, verdict, rationale, finalized, payload_json,
                           active_seconds, calibration, created_at
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        assignment_id, revision, verdict, rationale, int(finalize),
                        json.dumps(payload_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        active_seconds, calibration,
                        _now(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ReviewStoreError("review revision is immutable") from exc
            self._audit(assignment["review_round_id"], assignment["reviewer_id"], "REVIEW_FINALIZED" if finalize else "REVIEW_SAVED", assignment_id)

    def assignments_for(self, round_id: str, actor_id: str) -> list[dict]:
        membership = self.connection.execute(
            "SELECT 1 FROM memberships WHERE review_round_id = ? AND actor_id = ? AND capability = 'REVIEW'",
            (round_id, actor_id),
        ).fetchone()
        if not membership:
            raise ReviewStoreError("actor is not a reviewer in this round")
        rows = self.connection.execute(
            """SELECT a.assignment_id, a.sample_id, a.reviewer_id, a.slot, rd.review_type,
                      s.slice_name, s.outcome, s.source_closure, s.manifest_json,
                      MAX(r.revision) AS latest_revision,
                      MAX(CASE WHEN r.finalized = 1 THEN 1 ELSE 0 END) AS has_finalized
               FROM assignments a JOIN rounds rd ON rd.review_round_id = a.review_round_id
               JOIN samples s ON s.review_round_id = a.review_round_id AND s.sample_id = a.sample_id
               LEFT JOIN review_revisions r ON r.assignment_id = a.assignment_id
               WHERE a.review_round_id = ? AND a.reviewer_id = ?
               GROUP BY a.assignment_id, a.sample_id, a.reviewer_id, a.slot, rd.review_type,
                        s.slice_name, s.outcome, s.source_closure, s.manifest_json
               ORDER BY a.slot, a.assignment_id""",
            (round_id, actor_id),
        )
        result = []
        for row in rows:
            item = dict(row)
            manifest = json.loads(item.pop("manifest_json"))
            item["sample"] = {
                "slice": item.pop("slice_name"),
                "outcome": item.pop("outcome"),
                "source_closure": item.pop("source_closure"),
                "required_sources": manifest.get("required_sources", {}),
                "reason_codes": manifest.get("reason_codes", []),
            }
            result.append(item)
        return result

    def rounds_for(self, actor_id: str) -> list[dict]:
        rows = self.connection.execute(
            """SELECT r.review_round_id, r.review_type, r.purpose, r.state, m.capability
               FROM rounds r JOIN memberships m ON m.review_round_id = r.review_round_id
               WHERE m.actor_id = ? ORDER BY r.created_at, r.review_round_id, m.capability""",
            (actor_id,),
        )
        return [dict(row) for row in rows]

    def has_capability(self, round_id: str, actor_id: str, capability: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM memberships WHERE review_round_id = ? AND actor_id = ? AND capability = ?",
            (round_id, actor_id, capability),
        ).fetchone() is not None

    def round_record(self, round_id: str) -> dict:
        row = self.connection.execute(
            "SELECT * FROM rounds WHERE review_round_id = ?", (round_id,)
        ).fetchone()
        if row is None:
            raise ReviewStoreError("unknown review round")
        result = dict(row)
        result["guideline_revision_count"] = self.connection.execute(
            "SELECT COALESCE(MAX(revision), 0) FROM guideline_revisions WHERE review_round_id = ?", (round_id,)
        ).fetchone()[0]
        result["assignments_valid"] = self.assignments_valid(round_id)
        return result

    def set_gate_evidence(self, round_id: str, *, actor_id: str, **evidence: bool) -> None:
        allowed = {
            "schema_ui_export_validated",
            "calibration_complete",
            "reviewer_training_complete",
            "baseline_split_frozen",
        }
        if not evidence or set(evidence) - allowed or any(not isinstance(value, bool) for value in evidence.values()):
            raise ReviewStoreError("invalid round gate evidence")
        self._round_open(round_id)
        assignments = ", ".join(f"{key} = ?" for key in sorted(evidence))
        values = [int(evidence[key]) for key in sorted(evidence)]
        with self.connection:
            self.connection.execute(
                f"UPDATE rounds SET {assignments} WHERE review_round_id = ?", [*values, round_id]
            )
            self._audit(round_id, actor_id, "ROUND_GATE_EVIDENCE_UPDATED", ",".join(sorted(evidence)))

    def m16_gate(self, round_id: str) -> dict:
        row = self.round_record(round_id)
        if row["review_type"] != "M16_EXPERT_PILOT":
            raise ReviewStoreError("M16 gate applies only to M16_EXPERT_PILOT rounds")
        report = self.sample_manifest_report(round_id)
        return m16_start_gate(
            distinct_eligible=report["source_complete"],
            slice_counts=report["slice_counts"],
            outcome_counts=report["outcome_counts"],
            joint_cells_ready=report["joint_cells_ready"],
            source_complete=report["source_complete"],
            schema_ui_export_validated=bool(row["schema_ui_export_validated"]),
            assignments_valid=bool(row["assignments_valid"]),
            calibration_complete=bool(row["calibration_complete"]),
            reviewer_training_complete=bool(row["reviewer_training_complete"]),
            baseline_model_split_manifest_frozen=bool(row["baseline_split_frozen"]),
            guideline_revision_count=int(row["guideline_revision_count"]),
        )

    def sample_manifest_report(self, round_id: str) -> dict:
        row = self.connection.execute(
            "SELECT review_type, manifest_frozen FROM rounds WHERE review_round_id = ?", (round_id,)
        ).fetchone()
        if row is None:
            raise ReviewStoreError("unknown review round")
        if not row["manifest_frozen"]:
            return {
                "distinct_samples": 0,
                "source_complete": 0,
                "slice_counts": {},
                "outcome_counts": {},
                "joint_cells_ready": False,
                "source_cohort_ready": False,
            }
        metadata = self._metadata()
        samples = [json.loads(item[0]) for item in self.connection.execute(
            "SELECT manifest_json FROM samples WHERE review_round_id = ? ORDER BY sample_id", (round_id,)
        )]
        return validate_sample_manifest({
            "schema_version": 1,
            "project_id": metadata["owner_project_id"],
            "review_round_id": round_id,
            "review_type": row["review_type"],
            "classification": metadata["classification"],
            "samples": samples,
        })

    def assignments_valid(self, round_id: str) -> bool:
        samples = [row[0] for row in self.connection.execute(
            "SELECT sample_id FROM samples WHERE review_round_id = ?", (round_id,)
        )]
        if not samples:
            return False
        reviewers = {
            row[0] for row in self.connection.execute(
                "SELECT actor_id FROM memberships WHERE review_round_id = ? AND capability = 'REVIEW'",
                (round_id,),
            )
        }
        adjudicators = {
            row[0] for row in self.connection.execute(
                "SELECT actor_id FROM memberships WHERE review_round_id = ? AND capability = 'ADJUDICATE'",
                (round_id,),
            )
        }
        if reviewers & adjudicators:
            return False
        for sample_id in samples:
            assigned = [row[0] for row in self.connection.execute(
                "SELECT reviewer_id FROM assignments WHERE review_round_id = ? AND sample_id = ?",
                (round_id, sample_id),
            )]
            if len(assigned) < 2 or len(assigned) != len(set(assigned)) or not set(assigned).issubset(reviewers):
                return False
        return True

    def assignment_owner(self, assignment_id: str) -> str | None:
        row = self.connection.execute(
            "SELECT reviewer_id FROM assignments WHERE assignment_id = ?", (assignment_id,)
        ).fetchone()
        return row[0] if row else None

    def add_guideline_revision(self, round_id: str, content_hash: str, *, actor_id: str) -> int:
        round_row = self._round_open(round_id)
        current = self.connection.execute(
            "SELECT COALESCE(MAX(revision), -1) FROM guideline_revisions WHERE review_round_id = ?", (round_id,)
        ).fetchone()[0]
        revision = current + 1
        if revision > round_row["max_revisions"]:
            raise ReviewStoreError("guideline revision exceeds round limit")
        with self.connection:
            self.connection.execute("INSERT INTO guideline_revisions VALUES (?, ?, ?, ?)", (round_id, revision, content_hash, _now()))
            self._audit(round_id, actor_id, "GUIDELINE_REVISED", str(revision))
        return revision

    def adjudicate(
        self,
        round_id: str,
        sample_id: str,
        *,
        adjudicator_id: str,
        verdict: str,
        rationale: str,
        payload: dict | None = None,
    ) -> None:
        self._round_open(round_id)
        if verdict not in VERDICTS or not rationale:
            raise ReviewStoreError("adjudication requires a verdict and rationale")
        payload_value = payload or {}
        if not isinstance(payload_value, dict) or set(payload_value) - {"final_fields"}:
            raise ReviewStoreError("adjudication payload fields do not match the contract")
        if "final_fields" in payload_value and not isinstance(payload_value["final_fields"], dict):
            raise ReviewStoreError("adjudication final_fields must be an object")
        capability = self.connection.execute(
            "SELECT 1 FROM memberships WHERE review_round_id = ? AND actor_id = ? AND capability = 'ADJUDICATE'",
            (round_id, adjudicator_id),
        ).fetchone()
        conflict = self.connection.execute(
            "SELECT 1 FROM assignments WHERE review_round_id = ? AND reviewer_id = ? LIMIT 1", (round_id, adjudicator_id)
        ).fetchone()
        if not capability or conflict:
            raise ReviewStoreError("actor is not an independent round adjudicator")
        latest = list(self.connection.execute(
            """SELECT rr.verdict FROM assignments a JOIN review_revisions rr ON rr.assignment_id = a.assignment_id
               WHERE a.review_round_id = ? AND a.sample_id = ? AND rr.finalized = 1
               AND rr.revision = (SELECT MAX(x.revision) FROM review_revisions x WHERE x.assignment_id = a.assignment_id AND x.finalized = 1)""",
            (round_id, sample_id),
        ))
        if len(latest) < 2 or len({row[0] for row in latest}) == 1:
            raise ReviewStoreError("sample is not ready for adjudication")
        with self.connection:
            self.connection.execute(
                "INSERT INTO adjudications VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    round_id, sample_id, adjudicator_id, verdict, rationale,
                    json.dumps(payload_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    _now(),
                ),
            )
            self._audit(round_id, adjudicator_id, "SAMPLE_ADJUDICATED", sample_id)

    def adjudication_queue(self, round_id: str, adjudicator_id: str) -> list[dict]:
        capability = self.connection.execute(
            "SELECT 1 FROM memberships WHERE review_round_id = ? AND actor_id = ? AND capability = 'ADJUDICATE'",
            (round_id, adjudicator_id),
        ).fetchone()
        conflict = self.connection.execute(
            "SELECT 1 FROM assignments WHERE review_round_id = ? AND reviewer_id = ? LIMIT 1",
            (round_id, adjudicator_id),
        ).fetchone()
        if not capability or conflict:
            raise ReviewStoreError("actor is not an independent round adjudicator")
        rows = self.connection.execute(
            """SELECT a.sample_id, a.reviewer_id, rr.verdict
               FROM assignments a JOIN review_revisions rr ON rr.assignment_id = a.assignment_id
               WHERE a.review_round_id = ? AND rr.finalized = 1
               AND rr.revision = (SELECT MAX(x.revision) FROM review_revisions x WHERE x.assignment_id = a.assignment_id AND x.finalized = 1)
               ORDER BY a.sample_id, a.reviewer_id""",
            (round_id,),
        )
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(row["sample_id"], []).append(
                {"reviewer_id": row["reviewer_id"], "verdict": row["verdict"]}
            )
        decided = {row[0] for row in self.connection.execute(
            "SELECT sample_id FROM adjudications WHERE review_round_id = ?", (round_id,)
        )}
        return [
            {"sample_id": sample_id, "original_verdicts": verdicts}
            for sample_id, verdicts in sorted(grouped.items())
            if sample_id not in decided and len(verdicts) >= 2 and len({item["verdict"] for item in verdicts}) > 1
        ]

    def round_metrics(self, round_id: str) -> dict:
        if self.connection.execute(
            "SELECT 1 FROM rounds WHERE review_round_id = ?", (round_id,)
        ).fetchone() is None:
            raise ReviewStoreError("unknown review round")
        assignments = list(self.connection.execute(
            "SELECT assignment_id, sample_id FROM assignments WHERE review_round_id = ? ORDER BY assignment_id",
            (round_id,),
        ))
        latest: dict[str, str] = {}
        latest_rows: dict[str, sqlite3.Row] = {}
        for row in assignments:
            verdict = self.connection.execute(
                """SELECT verdict, payload_json, active_seconds, calibration FROM review_revisions
                   WHERE assignment_id = ? AND finalized = 1 ORDER BY revision DESC LIMIT 1""",
                (row["assignment_id"],),
            ).fetchone()
            if verdict:
                latest[row["assignment_id"]] = verdict[0]
                latest_rows[row["assignment_id"]] = verdict
        by_sample: dict[str, list[str]] = {}
        expected_by_sample: dict[str, int] = {}
        for row in assignments:
            expected_by_sample[row["sample_id"]] = expected_by_sample.get(row["sample_id"], 0) + 1
            if row["assignment_id"] in latest:
                by_sample.setdefault(row["sample_id"], []).append(latest[row["assignment_id"]])
        completed_samples = sum(
            len(by_sample.get(sample_id, [])) == expected
            for sample_id, expected in expected_by_sample.items()
        )
        disagreements = {
            sample_id for sample_id, values in by_sample.items()
            if len(values) == expected_by_sample[sample_id] and len(set(values)) > 1
        }
        adjudicated = {
            row[0] for row in self.connection.execute(
                "SELECT sample_id FROM adjudications WHERE review_round_id = ?", (round_id,)
            )
        }
        sample_count = self.connection.execute(
            "SELECT COUNT(*) FROM samples WHERE review_round_id = ?", (round_id,)
        ).fetchone()[0]
        progress = round_progress(
            assigned=len(assignments),
            finalized=len(latest),
            total_samples=sample_count,
            samples_with_required_reviews=completed_samples,
            disagreement_samples_ready=len(disagreements),
            adjudicated_disagreements=len(disagreements & adjudicated),
        )
        payload_by_sample: dict[str, list[dict]] = {}
        timing_records = []
        for assignment in assignments:
            revision = latest_rows.get(assignment["assignment_id"])
            if revision is None:
                continue
            payload = json.loads(revision["payload_json"])
            payload_by_sample.setdefault(assignment["sample_id"], []).append(payload)
            timing_records.append({
                "active_seconds": revision["active_seconds"],
                "calibration": bool(revision["calibration"]),
                "server_idle_filtered": True,
            })
        applicability = {
            sample_id: [payload.get("applicability") for payload in payloads]
            for sample_id, payloads in payload_by_sample.items()
            if any("applicability" in payload for payload in payloads)
        }
        alpha_values = applicability or by_sample
        alpha = nominal_krippendorff_alpha(alpha_values) if alpha_values else {
            "contract_version": "nominal-krippendorff-alpha-v1",
            "status": "NOT_ESTIMABLE_NO_RATINGS",
            "alpha": None,
            "included_items": 0,
            "excluded_items": sample_count,
            "missing_responses": len(assignments),
            "category_counts": {},
        }
        field_names = sorted({
            field
            for payloads in payload_by_sample.values()
            for payload in payloads
            for field in payload.get("field_values", {})
        })
        field_agreement = {}
        for field in field_names:
            values_by_sample = {
                sample_id: [payload.get("field_values", {}).get(field) for payload in payloads]
                for sample_id, payloads in payload_by_sample.items()
            }
            all_values = [
                value for values in values_by_sample.values() for value in values if value is not None
            ]
            if any(isinstance(value, dict) for value in all_values):
                if not all(
                    isinstance(value, dict) and {"low", "high", "unit", "frame"}.issubset(value)
                    for value in all_values
                ):
                    raise ReviewStoreError("field values cannot mix interval objects and categorical values")
                pairs = [
                    (values[0], values[1]) for values in values_by_sample.values()
                    if len(values) >= 2 and values[0] is not None and values[1] is not None
                ]
                field_agreement[field] = {"kind": "NUMERIC_INTERVAL", **interval_agreement(pairs)}
            else:
                field_agreement[field] = {"kind": "CATEGORICAL", **categorical_agreement(values_by_sample)}
        source_pairs = []
        for payloads in payload_by_sample.values():
            if len(payloads) >= 2 and all("source_ids" in payload for payload in payloads[:2]):
                source_pairs.append((set(payloads[0]["source_ids"]), set(payloads[1]["source_ids"])))
        correction_pairs = []
        for row in self.connection.execute(
            "SELECT sample_id, payload_json FROM adjudications WHERE review_round_id = ? ORDER BY sample_id",
            (round_id,),
        ):
            final_fields = json.loads(row["payload_json"]).get("final_fields")
            originals = [
                payload.get("field_values", {}) for payload in payload_by_sample.get(row["sample_id"], [])
            ]
            if not isinstance(final_fields, dict) or not originals:
                continue
            comparable = {}
            for field, final_value in final_fields.items():
                values = [original[field] for original in originals if field in original]
                if values:
                    comparable[field] = final_value if all(value == final_value for value in values) else object()
            correction_pairs.append((comparable, final_fields))
        return {
            "progress": progress,
            "applicability_agreement": alpha,
            "field_agreement": field_agreement,
            "source_agreement": source_set_agreement(source_pairs),
            "correction_rates": correction_rates(correction_pairs),
            "reviewer_time": reviewer_time_summary(timing_records, idle_timeout_seconds=300),
        }

    def backup(self, backup_dir: Path, *, round_id: str) -> tuple[Path, str]:
        expected = (self.path.parent / "backups").resolve()
        if backup_dir.resolve() != expected:
            raise ReviewStoreError("backup directory must be the operations-run backups sibling")
        backup_dir.mkdir(parents=True, exist_ok=True)
        target = backup_dir / f"{round_id}.sqlite3"
        if target.exists():
            raise ReviewStoreError("refusing to overwrite an existing review backup")
        destination = sqlite3.connect(target)
        try:
            self.connection.backup(destination)
            if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ReviewStoreError("review backup integrity check failed")
        finally:
            destination.close()
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        target.chmod(0o440)
        return target, digest

    def finalize_round(
        self,
        round_id: str,
        *,
        actor_id: str,
        terminal_shortfall: bool,
        backup_dir: Path,
        export_path: Path,
    ) -> dict:
        row = self._round_open(round_id)
        if export_path.parent.resolve() != self.path.parent.resolve():
            raise ReviewStoreError("restricted round export must stay in its operations run")
        if export_path.exists():
            raise ReviewStoreError("refusing to overwrite an existing round export")
        metrics = self.round_metrics(round_id)
        if not terminal_shortfall:
            reviewer = metrics["progress"]["reviewer_progress"]
            adjudication = metrics["progress"]["adjudication_progress"]
            if reviewer["assigned"] == 0 or reviewer["fraction"] != 1:
                raise ReviewStoreError("cannot complete a round with unfinished independent reviews")
            if adjudication["assigned"] and adjudication["fraction"] != 1:
                raise ReviewStoreError("cannot complete a round with unfinished adjudications")
        with self.connection:
            self._audit(round_id, actor_id, "ROUND_FINALIZATION_STARTED", round_id)
        self.close_round(round_id, terminal_shortfall=terminal_shortfall, actor_id=actor_id)
        round_state = "TERMINAL_SHORTFALL" if terminal_shortfall else "COMPLETE"
        export = {
            "schema_version": 1,
            "owner_project_id": self._metadata()["owner_project_id"],
            "classification": self._metadata()["classification"],
            "review_round_id": round_id,
            "review_type": row["review_type"],
            "round_state": round_state,
            "sample_manifest_hash": row["sample_manifest_hash"],
            "assignment_hash": row["assignment_hash"],
            "metrics": metrics,
            "claim_scope": "REVIEW_OPERATIONS_NOT_RESEARCH_EFFECT_OR_VEHICLE_SAFETY",
        }
        export_text = json.dumps(export, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with export_path.open("x", encoding="utf-8") as stream:
            stream.write(export_text)
        export_hash = hashlib.sha256(export_text.encode()).hexdigest()
        self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        backup_path, backup_hash = self.backup(backup_dir, round_id=round_id)
        self.connection.execute("PRAGMA query_only = ON")
        self.path.chmod(0o440)
        return {
            "review_round_id": round_id,
            "round_state": round_state,
            "export_path": export_path.as_posix(),
            "export_sha256": export_hash,
            "backup_path": backup_path.as_posix(),
            "backup_sha256": backup_hash,
        }

    def close_round(self, round_id: str, *, terminal_shortfall: bool, actor_id: str) -> None:
        row = self._round_open(round_id)
        state = "TERMINAL_SHORTFALL" if terminal_shortfall else "COMPLETE"
        if state not in ROUND_TRANSITIONS.get(row["state"], set()):
            raise ReviewStoreError(f"invalid round close transition: {row['state']} -> {state}")
        with self.connection:
            self.connection.execute("UPDATE rounds SET state = ?, closed_at = ? WHERE review_round_id = ?", (state, _now(), round_id))
            self._audit(round_id, actor_id, "ROUND_CLOSED", round_id)
        result = self.connection.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise ReviewStoreError(f"database integrity check failed: {result}")
