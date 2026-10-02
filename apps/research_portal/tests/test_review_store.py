import tempfile
import json
import unittest
from pathlib import Path

from apps.research_portal.review_store import ReviewStore, ReviewStoreError
from apps.research_portal.run import initialize_review_db


class ReviewStoreTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "round.sqlite3"
        self.store = ReviewStore.create(
            self.path, owner_project_id="guardsynth-coc", classification="RESTRICTED"
        )
        self.store.create_round(
            "round-01", review_type="M16_SOURCE_REVIEW", purpose="source review", created_by="lead"
        )
        for sample in ("sample-01", "sample-02", "sample-03"):
            self.store.add_sample("round-01", sample)
        for reviewer in ("reviewer-a", "reviewer-b", "reviewer-c"):
            self.store.add_membership("round-01", reviewer, "REVIEW")

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_assignment_is_deterministic_balanced_and_independent(self):
        first = self.store.assign("round-01", reviewers_per_sample=2, seed=b"locked-seed")
        self.store.clear_draft_assignments("round-01")
        second = self.store.assign("round-01", reviewers_per_sample=2, seed=b"locked-seed")

        self.assertEqual(first, second)
        sample_reviewers = {}
        loads = {}
        for assignment in first:
            sample_reviewers.setdefault(assignment["sample_id"], set()).add(assignment["reviewer_id"])
            loads[assignment["reviewer_id"]] = loads.get(assignment["reviewer_id"], 0) + 1
        self.assertTrue(all(len(reviewers) == 2 for reviewers in sample_reviewers.values()))
        self.assertLessEqual(max(loads.values()) - min(loads.values()), 1)

    def test_finalized_original_is_immutable_and_revision_cap_is_two(self):
        assignments = self.store.assign("round-01", reviewers_per_sample=2, seed=b"locked-seed")
        assignment_id = assignments[0]["assignment_id"]
        self.store.submit_review(assignment_id, "SOURCE_COMPLETE", revision=0, finalize=True)
        with self.assertRaises(ReviewStoreError):
            self.store.submit_review(assignment_id, "CONFLICT", revision=0, finalize=True)
        self.store.submit_review(assignment_id, "CONFLICT", revision=1, finalize=True)
        self.store.submit_review(assignment_id, "REVIEW_REQUIRED", revision=2, finalize=True)
        with self.assertRaises(ReviewStoreError):
            self.store.submit_review(assignment_id, "UNSUPPORTED", revision=3, finalize=True)

    def test_server_activity_excludes_idle_time_and_is_stored_with_revision(self):
        assignments = self.store.assign("round-01", reviewers_per_sample=2, seed=b"locked-seed")
        assignment = assignments[0]
        self.store.start_assignment(
            assignment["assignment_id"], actor_id=assignment["reviewer_id"],
            at="2026-08-14T12:00:00+00:00",
        )
        self.store.touch_assignment(
            assignment["assignment_id"], actor_id=assignment["reviewer_id"],
            at="2026-08-14T12:00:10+00:00", idle_timeout_seconds=300,
        )
        self.store.touch_assignment(
            assignment["assignment_id"], actor_id=assignment["reviewer_id"],
            at="2026-08-14T12:10:10+00:00", idle_timeout_seconds=300,
        )
        active = self.store.touch_assignment(
            assignment["assignment_id"], actor_id=assignment["reviewer_id"],
            at="2026-08-14T12:10:20+00:00", idle_timeout_seconds=300,
        )
        self.assertEqual(active, 20)
        self.store.submit_review(
            assignment["assignment_id"], "SOURCE_COMPLETE", revision=0, finalize=True
        )
        stored = self.store.connection.execute(
            "SELECT active_seconds FROM review_revisions WHERE assignment_id = ?",
            (assignment["assignment_id"],),
        ).fetchone()[0]
        self.assertEqual(stored, 20)

    def test_adjudicator_cannot_be_a_reviewer_in_the_same_round(self):
        self.store.add_membership("round-01", "reviewer-a", "ADJUDICATE")
        with self.assertRaises(ReviewStoreError):
            self.store.assign("round-01", reviewers_per_sample=2, seed=b"locked-seed")

    def test_disagreement_is_adjudicated_in_a_separate_record(self):
        self.store.add_membership("round-01", "adjudicator", "ADJUDICATE")
        assignments = self.store.assign("round-01", reviewers_per_sample=2, seed=b"locked-seed")
        sample_assignments = [item for item in assignments if item["sample_id"] == "sample-01"]
        first_interval = {"low": 0, "high": 10, "unit": "m", "frame": "map"}
        second_interval = {"low": 5, "high": 15, "unit": "m", "frame": "map"}
        self.store.submit_review(
            sample_assignments[0]["assignment_id"], "SOURCE_COMPLETE", revision=0, finalize=True,
            payload={"field_values": {"range": first_interval}, "source_ids": ["source-a"]},
        )
        self.store.submit_review(
            sample_assignments[1]["assignment_id"], "CONFLICT", revision=0, finalize=True,
            payload={"field_values": {"range": second_interval}, "source_ids": ["source-b"]},
        )

        queue = self.store.adjudication_queue("round-01", "adjudicator")
        self.assertEqual([item["sample_id"] for item in queue], ["sample-01"])
        self.store.adjudicate(
            "round-01", "sample-01", adjudicator_id="adjudicator",
            verdict="REVIEW_REQUIRED", rationale="source conflict requires follow-up",
            payload={"final_fields": {"range": first_interval}},
        )
        self.assertEqual(self.store.adjudication_queue("round-01", "adjudicator"), [])
        metrics = self.store.round_metrics("round-01")
        self.assertEqual(metrics["field_agreement"]["range"]["kind"], "NUMERIC_INTERVAL")
        self.assertAlmostEqual(metrics["field_agreement"]["range"]["mean_iou"], 1 / 3)
        self.assertEqual(metrics["correction_rates"]["scene_correction_rate"], 1)

    def test_database_is_bound_to_one_owner_and_classification(self):
        with self.assertRaises(ReviewStoreError):
            ReviewStore.open(
                self.path, owner_project_id="specification-alignment", classification="RESTRICTED"
            )

    def test_explicit_initializer_enforces_registered_owner_classification_root(self):
        fake_root = Path(self.directory.name) / "repository"
        fake_root.mkdir()
        (fake_root / "PROJECT_REGISTRY.json").write_text(json.dumps({
            "projects": [{
                "id": "guardsynth-coc",
                "artifact_root": "artifacts/projects/guardsynth-coc",
            }],
        }), encoding="utf-8")
        target = fake_root / "artifacts/projects/guardsynth-coc/restricted/round-001/round.sqlite3"
        result = initialize_review_db(
            target,
            owner_project_id="guardsynth-coc",
            classification="RESTRICTED",
            root=fake_root,
        )
        self.assertTrue(target.is_file())
        self.assertEqual(result["schema_version"], "2")
        with self.assertRaises(ValueError):
            initialize_review_db(
                fake_root / "outside/round.sqlite3",
                owner_project_id="guardsynth-coc",
                classification="RESTRICTED",
                root=fake_root,
            )

    def test_round_state_machine_rejects_skipped_gates_and_closes(self):
        with self.assertRaises(ReviewStoreError):
            self.store.transition_round("round-01", "EMPIRICAL_ACTIVE", actor_id="lead")
        self.store.transition_round("round-01", "ELIGIBILITY_BLOCKED", actor_id="lead")
        self.store.transition_round("round-01", "READY_CALIBRATION", actor_id="lead")
        self.store.transition_round("round-01", "CALIBRATION_ACTIVE", actor_id="lead")
        self.store.transition_round("round-01", "READY_EMPIRICAL", actor_id="lead")
        self.store.transition_round("round-01", "EMPIRICAL_ACTIVE", actor_id="lead")
        self.store.transition_round("round-01", "ADJUDICATION_ACTIVE", actor_id="lead")
        self.store.close_round("round-01", terminal_shortfall=False, actor_id="lead")
        with self.assertRaises(ReviewStoreError):
            self.store.add_sample("round-01", "sample-after-close")

    def test_sample_manifest_freezes_once_and_binds_owner(self):
        other = ReviewStore.create(
            self.path.parent / "round-02.sqlite3",
            owner_project_id="guardsynth-coc", classification="RESTRICTED",
        )
        other.create_round(
            "round-02", review_type="M16_SOURCE_REVIEW", purpose="manifest freeze", created_by="lead"
        )
        manifest = {
            "schema_version": 1,
            "project_id": "guardsynth-coc",
            "review_round_id": "round-02",
            "review_type": "M16_SOURCE_REVIEW",
            "classification": "RESTRICTED",
            "samples": [{
                "sample_id": "sample-manifest-001", "slice": "UNKNOWN", "outcome": "UNKNOWN",
                "source_closure": "REVIEW_REQUIRED", "required_sources": {},
                "reason_codes": ["HUMAN_REVIEW_REQUIRED"],
            }],
        }
        try:
            report = other.freeze_sample_manifest("round-02", manifest, actor_id="lead")
            self.assertEqual(report["distinct_samples"], 1)
            with self.assertRaisesRegex(ReviewStoreError, "already frozen"):
                other.freeze_sample_manifest("round-02", manifest, actor_id="lead")
        finally:
            other.close()

    def test_finalize_checkpoints_backs_up_exports_and_makes_store_query_only(self):
        assignments = self.store.assign("round-01", reviewers_per_sample=2, seed=b"locked-seed")
        for assignment in assignments:
            self.store.submit_review(
                assignment["assignment_id"], "SOURCE_COMPLETE", revision=0, finalize=True
            )
        for state in (
            "ELIGIBILITY_BLOCKED", "READY_CALIBRATION", "CALIBRATION_ACTIVE",
            "READY_EMPIRICAL", "EMPIRICAL_ACTIVE",
        ):
            self.store.transition_round("round-01", state, actor_id="lead")
        export_path = self.path.parent / "ROUND_EXPORT.json"
        result = self.store.finalize_round(
            "round-01", actor_id="lead", terminal_shortfall=False,
            backup_dir=self.path.parent / "backups", export_path=export_path,
        )

        self.assertTrue(Path(result["backup_path"]).is_file())
        self.assertTrue(export_path.is_file())
        self.assertEqual(json.loads(export_path.read_text(encoding="utf-8"))["round_state"], "COMPLETE")
        self.assertEqual(self.store.connection.execute("PRAGMA query_only").fetchone()[0], 1)
        with self.assertRaises(ReviewStoreError):
            self.store.add_sample("round-01", "sample-after-finalize")


if __name__ == "__main__":
    unittest.main()
