import json
import tempfile
import unittest
from pathlib import Path

from apps.research_portal.review_backend import (
    BackendError,
    ReviewBackend,
    build_public_export,
    write_public_export_run,
)
from apps.research_portal.review_store import ReviewStore
from apps.research_portal.sample_manifest import REQUIRED_SOURCE_FIELDS


class ReviewWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = ReviewStore.create(
            Path(self.directory.name) / "round.sqlite3",
            owner_project_id="guardsynth-coc",
            classification="RESTRICTED",
        )
        self.store.create_round(
            "round-01", review_type="M16_SOURCE_REVIEW", purpose="source review", created_by="lead"
        )
        self.store.add_sample("round-01", "sample-01")
        self.store.add_membership("round-01", "reviewer-a", "REVIEW")
        self.store.add_membership("round-01", "reviewer-b", "REVIEW")
        self.assignments = self.store.assign("round-01", reviewers_per_sample=2, seed=b"locked-seed")
        self.backend = ReviewBackend(self.store, lead_actor_ids={"lead"})

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_reviewer_reads_only_own_assignments_and_never_peer_verdicts(self):
        rounds = self.backend.dispatch("GET", "/api/rounds", actor_id="reviewer-a", body=None)
        own = self.backend.dispatch(
            "GET", "/api/rounds/round-01/assignments", actor_id="reviewer-a", body=None
        )

        self.assertEqual(rounds.data["rounds"][0]["capability"], "REVIEW")
        self.assertEqual(own.status, 200)
        self.assertEqual({item["reviewer_id"] for item in own.data["assignments"]}, {"reviewer-a"})
        self.assertTrue(all("peer_verdict" not in item for item in own.data["assignments"]))
        self.assertTrue(all("required_sources" in item["sample"] for item in own.data["assignments"]))

    def test_reviewer_cannot_submit_another_reviewers_assignment(self):
        other = next(item for item in self.assignments if item["reviewer_id"] == "reviewer-b")

        with self.assertRaises(BackendError) as caught:
            self.backend.dispatch(
                "POST",
                f"/api/assignments/{other['assignment_id']}/reviews",
                actor_id="reviewer-a",
                body={"verdict": "SOURCE_COMPLETE", "revision": 0, "finalize": True},
            )
        self.assertEqual(caught.exception.status, 403)

    def test_unsafe_route_segment_fails_as_a_client_error(self):
        with self.assertRaises(BackendError) as caught:
            self.backend.dispatch(
                "POST", "/api/assignments/%2e%2e/reviews", actor_id="reviewer-a",
                body={"verdict": "SOURCE_COMPLETE", "revision": 0, "finalize": True},
            )
        self.assertEqual(caught.exception.status, 400)

    def test_current_m16_gate_rejects_empirical_annotation_start(self):
        m16_store = ReviewStore.create(
            Path(self.directory.name) / "m16-round.sqlite3",
            owner_project_id="guardsynth-coc", classification="RESTRICTED",
        )
        backend = ReviewBackend(m16_store, lead_actor_ids={"lead"})
        try:
            backend.dispatch("POST", "/api/rounds", actor_id="lead", body={
                "review_round_id": "m16-round-001", "review_type": "M16_EXPERT_PILOT", "purpose": "M16 pilot",
            })
            for actor in ("reviewer-a", "reviewer-b"):
                backend.dispatch(
                    "POST", "/api/rounds/m16-round-001/memberships", actor_id="lead",
                    body={"actor_id": actor, "capability": "REVIEW"},
                )
            sources = {
                field: {"source_id": f"source-{field.replace('_', '-')}", "sha256": f"{index + 1:064x}"}
                for index, field in enumerate(REQUIRED_SOURCE_FIELDS)
            }
            backend.dispatch("POST", "/api/rounds/m16-round-001/manifest", actor_id="lead", body={
                "schema_version": 1, "project_id": "guardsynth-coc",
                "review_round_id": "m16-round-001", "review_type": "M16_EXPERT_PILOT",
                "classification": "RESTRICTED", "samples": [{
                    "sample_id": "sample-eligible-001", "slice": "PEDESTRIAN_CYCLIST_YIELD",
                    "outcome": "NOMINAL", "source_closure": "SOURCE_COMPLETE",
                    "required_sources": sources, "reason_codes": [],
                }],
            })
            backend.dispatch(
                "POST", "/api/rounds/m16-round-001/assignments", actor_id="lead",
                body={"reviewers_per_sample": 2, "seed": "a" * 32},
            )
            with self.assertRaises(BackendError) as caught:
                backend.dispatch(
                    "POST", "/api/rounds/m16-round-001/calibration/start", actor_id="lead",
                    body={"schema_ui_export_validated": True},
                )
            self.assertEqual(caught.exception.status, 403)
            self.assertEqual(caught.exception.data["eligible_shortfall"], 59)
            self.assertEqual(m16_store.round_record("m16-round-001")["state"], "ELIGIBILITY_BLOCKED")
        finally:
            m16_store.close()

    def test_lead_can_create_freeze_and_assign_but_reviewer_cannot_administer(self):
        admin_store = ReviewStore.create(
            Path(self.directory.name) / "round-02.sqlite3",
            owner_project_id="guardsynth-coc", classification="RESTRICTED",
        )
        backend = ReviewBackend(admin_store, lead_actor_ids={"lead"})
        create_body = {
            "review_round_id": "round-02",
            "review_type": "PAPER_INTERNAL_CLAIM_REVIEW",
            "purpose": "claim audit",
        }
        with self.assertRaises(BackendError) as caught:
            backend.dispatch("POST", "/api/rounds", actor_id="reviewer-a", body=create_body)
        self.assertEqual(caught.exception.status, 403)

        try:
            backend.dispatch("POST", "/api/rounds", actor_id="lead", body=create_body)
            for actor in ("reviewer-a", "reviewer-b"):
                backend.dispatch(
                    "POST", "/api/rounds/round-02/memberships", actor_id="lead",
                    body={"actor_id": actor, "capability": "REVIEW"},
                )
            manifest = {
                "schema_version": 1,
                "project_id": "guardsynth-coc",
                "review_round_id": "round-02",
                "review_type": "PAPER_INTERNAL_CLAIM_REVIEW",
                "classification": "RESTRICTED",
                "samples": [{
                    "sample_id": "sample-claim-001", "slice": "CLAIM", "outcome": "REVIEW",
                    "source_closure": "REVIEW_REQUIRED", "required_sources": {},
                    "reason_codes": ["HUMAN_REVIEW_REQUIRED"],
                }],
            }
            frozen = backend.dispatch(
                "POST", "/api/rounds/round-02/manifest", actor_id="lead", body=manifest
            )
            self.assertRegex(frozen.data["manifest_hash"], r"^[a-f0-9]{64}$")
            assigned = backend.dispatch(
                "POST", "/api/rounds/round-02/assignments", actor_id="lead",
                body={"reviewers_per_sample": 2, "seed": "a" * 32},
            )
            self.assertEqual(assigned.data["assignment_count"], 2)
            self.assertNotIn("seed", assigned.data)
        finally:
            admin_store.close()

    def test_guideline_revision_three_is_rejected_through_lead_api(self):
        for index in range(3):
            response = self.backend.dispatch(
                "POST", "/api/rounds/round-01/guidelines", actor_id="lead",
                body={"content_hash": f"{index + 1:064x}"},
            )
            self.assertEqual(response.data["revision"], index)
        with self.assertRaises(BackendError):
            self.backend.dispatch(
                "POST", "/api/rounds/round-01/guidelines", actor_id="lead",
                body={"content_hash": f"{4:064x}"},
            )

    def test_public_export_rejects_paths_and_raw_identifiers(self):
        exported = build_public_export(
            project_id="guardsynth-coc",
            review_round_id="round-01",
            progress={"finalized": 2, "assigned": 2},
            agreement={"alpha": 0.7},
            claim_limitations=["not vehicle safety evidence"],
        )
        self.assertNotIn("canonical_path", exported)
        with self.assertRaises(BackendError):
            build_public_export(
                project_id="guardsynth-coc",
                review_round_id="round-01",
                progress={"canonical_path": "/restricted/round.sqlite3"},
                agreement={"alpha": 0.7},
                claim_limitations=[],
            )

        output = Path(self.directory.name) / "artifacts/projects/guardsynth-coc/public/review-export-001/run-v1"
        result = write_public_export_run(
            output, exported, experiment_id="GUARDSYNTH-REVIEW-EXPORT-001", run_id="run-v1"
        )
        self.assertTrue((output / "REVIEW_EXPORT.json").is_file())
        self.assertRegex(result["export_sha256"], r"^[a-f0-9]{64}$")
        with self.assertRaises(BackendError):
            write_public_export_run(
                output, exported, experiment_id="GUARDSYNTH-REVIEW-EXPORT-001", run_id="run-v1"
            )

    def test_lead_exports_only_aggregate_from_a_closed_round(self):
        self.store.transition_round("round-01", "ELIGIBILITY_BLOCKED", actor_id="lead")
        public_root = Path(self.directory.name) / "artifacts/projects/guardsynth-coc/public/research-review-export-001"
        backend = ReviewBackend(
            self.store,
            lead_actor_ids={"lead"},
            public_export_root=public_root,
        )
        backend.dispatch(
            "POST", "/api/rounds/round-01/finalize", actor_id="lead",
            body={"terminal_shortfall": True},
        )
        response = backend.dispatch(
            "POST", "/api/rounds/round-01/public-export", actor_id="lead",
            body={
                "run_id": "review-export-run-001",
                "claim_limitations": ["aggregate only; not vehicle safety evidence"],
            },
        )
        self.assertEqual(response.status, 201)
        exported = json.loads(
            (public_root / "review-export-run-001/REVIEW_EXPORT.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("sample_id", json.dumps(exported))


if __name__ == "__main__":
    unittest.main()
