from copy import deepcopy
import json
from pathlib import Path
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from apps.guardsynth_studio.common import StudioError, uid, digest
from apps.guardsynth_studio.store import Store
from apps.guardsynth_studio.service import Service, payload
from apps.guardsynth_studio.jobs import Worker, child
from apps.guardsynth_studio.provider import MockProvider
from .helpers import fixture, edit, approve, prepare, binding, contract, proposal, video_bytes


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.s, self.api, self.ids, self.extraction, self.video, self.group = fixture(self.temp.name)
        self.m = self.ids[6]

    def tearDown(self):
        self.s.close()
        self.temp.cleanup()

    def run_job(self, kind):
        j = self.api.enqueue(self.m, self.s.moment(self.m)["revision"], kind, "reviewer", uid())["job_id"]
        Worker(self.api).run_once()
        result = self.s.get(j, "job")
        self.assertEqual(result["status"], "SUCCEEDED", result.get("error"))
        return result

    def full_check(self, real=False, truth="FALSE"):
        prepare(self.api, self.m, real, truth)
        self.run_job("CHECK")
        self.run_job("CNL")
        approve(self.api, self.m, "cnl")
        self.run_job("COMBINE")
        approve(self.api, self.m, "combined")

    def test_navigation_cas_idempotency_restart(self):
        edit(self.api, self.m, "coc", {"edited_text": "保存"})
        for index, expected in [(6, list(range(7))), (7, list(range(1, 8))), (6, list(range(7)))]:
            self.assertEqual([f["ordinal"] for f in self.api.moment(self.ids[index])["frames"]], expected)
        self.assertEqual(len(self.api.moment(self.ids[0])["frames"]), 1)
        self.assertEqual(len(self.api.moment(self.ids[-1])["frames"]), 7)
        base = self.s.moment(self.m)["revision"]
        k = uid()
        first = self.api.edit(self.m, base, "coc", {"edited_text": "persist"}, "reviewer", k)
        self.assertEqual(first, self.api.edit(self.m, base, "coc", {"edited_text": "persist"}, "reviewer", k))
        with self.assertRaises(StudioError) as caught:
            self.api.edit(self.m, base, "coc", {"edited_text": "lost update"}, "reviewer", uid())
        self.assertEqual(caught.exception.status, 409)
        self.s.close()
        self.s = Store(self.temp.name)
        self.api = Service(self.s)
        self.assertEqual(payload(self.s.moment(self.m), "coc")["edited_text"], "persist")

    def test_future_binding_and_generated_provenance_rejected(self):
        b = binding(self.api, self.m)
        b["max_observed_timestamp_us"] += 1
        with self.assertRaises(StudioError): edit(self.api, self.m, "binding", b)
        b = binding(self.api, self.m)
        b["frame_id"] = self.s.moment(self.ids[7])["frame"]["frame_id"]
        with self.assertRaises(StudioError): edit(self.api, self.m, "binding", b)
        with self.assertRaises(StudioError): edit(self.api, self.m, "coc", {"origin": "REAL"})
        with self.assertRaises(StudioError): edit(self.api, self.m, "check", {"status": "PASS"})

    def test_geometry_delete_and_dependency_invalidation(self):
        self.full_check()
        m = self.s.moment(self.m)
        action = m["components"]["action"]["id"]
        b = payload(m, "binding")
        b.pop("target_point")
        b.pop("zone_polygon")
        edit(self.api, self.m, "binding", b)
        m = self.s.moment(self.m)
        self.assertNotIn("zone_polygon", payload(m, "binding"))
        self.assertTrue(m["components"]["check"]["stale"])
        self.assertTrue(m["components"]["combined"]["stale"])
        self.assertEqual(action, m["components"]["action"]["id"])
        self.assertTrue(self.s.approved(m, "action"))
        self.assertFalse(self.s.approved(m, "contract"))

    def test_q1_q5_cnl_determinism_and_unknown(self):
        from guard_synth.studio_contract import check, render
        b, c = binding(self.api, self.m), contract()
        result = check(c, b)
        self.assertEqual(result["status"], "PASS")
        ids = {r["query_id"] for group in result["results"] for r in group["results"]}
        self.assertTrue(all(any(q.startswith(f"q{i}_") for q in ids) for i in range(1, 6)))
        self.assertFalse(result["scene_truth_certified"])
        self.assertEqual(render(c, b, result), render(c, b, result))
        b["event_predicates"]["ped"]["truth"] = "UNKNOWN"
        result = check(c, b)
        self.assertEqual(result["status"], "PASS")
        cnl = render(c, b, result)
        self.assertTrue(cnl["review_required"])
        self.assertEqual(cnl["allowed_actions"], ["DEFER_ENTRY"])
        enter = next(r for r in result["results"][0]["results"] if r["query_id"] == "q2_enter")
        self.assertEqual(enter["status"], "UNSAT")
        with self.assertRaises(ValueError): render(c, binding(self.api, self.m), result)

    def test_tool_version_invalidation_is_scoped(self):
        self.full_check(real=True)
        with patch("guard_synth.studio_contract.RENDERER_VERSION", "changed-renderer"):
            m = self.api.moment(self.m)
            self.assertTrue(m["components"]["cnl"]["stale"])
            self.assertTrue(m["components"]["combined"]["stale"])
            self.assertFalse(m["components"]["check"]["stale"])
            self.assertTrue(self.s.approved(m, "action"))
        with patch("guard_synth.studio_contract.QUERY_VERSION", "changed-queries"):
            m = self.api.moment(self.m)
            self.assertTrue(m["components"]["check"]["stale"])
            self.assertEqual(m["eligibility"]["state"], "HELD")
            self.assertTrue(self.s.approved(m, "coc"))

    def test_nonvacuity_unsupported_and_solver_unknown(self):
        from guard_synth.studio_contract import build_models, check
        from guard_synth_eblc.core_ir import parse_core_model
        from guard_synth_eblc.smt_compiler import compile_core_model, check_queries
        from guard_synth_eblc.action_contract import literal
        c, b = contract(), binding(self.api, self.m)
        model, _ = build_models(c, b)
        model["clauses"].append({"id": "contradiction", "kind": "ASSUMPTION", "enforcement": "INITIAL", "formula": literal(False), "source_refs": ["policy"], "description": "test"})
        result = check_queries(compile_core_model(parse_core_model(model)))
        self.assertEqual(result["results"][0]["status"], "UNSAT")
        self.assertLess(result["matches_expected"], result["query_count"])
        c["obligations"][0]["predicate_id"] = "accelerate_after_two_seconds"
        with self.assertRaises(ValueError): build_models(c, b)
        with patch("guard_synth.studio_contract.check_queries", return_value={"query_count": 1, "matches_expected": 0, "results": [{"status": "UNKNOWN"}]}):
            self.assertEqual(check(contract(), b)["status"], "FAILED")

    def test_empty_not_applicable_and_separate_action(self):
        prepare(self.api, self.m)
        p = proposal(); p["proposals"] = []
        edit(self.api, self.m, "proposal", p)
        with self.assertRaises(StudioError): approve(self.api, self.m, "proposal")
        edit(self.api, self.m, "applicability", {"status": "NOT_APPLICABLE"})
        with self.assertRaises(StudioError): approve(self.api, self.m, "applicability")
        edit(self.api, self.m, "applicability", {"status": "NOT_APPLICABLE", "candidate_reviewed": True, "reason": "No applicable rule"})
        approve(self.api, self.m, "applicability")
        self.assertEqual(self.api.eligibility(self.s.moment(self.m))["state"], "HELD")
        self.assertTrue(self.s.approved(self.s.moment(self.m), "action"))

    def test_stale_job_cancel_recovery_and_timeout(self):
        self.api.provider = MockProvider()
        identity = self.api.enqueue(self.m, 0, "COC", "reviewer", uid())["job_id"]
        worker = Worker(self.api)
        j = worker.claim()
        result = worker.execute(j)
        edit(self.api, self.m, "coc", {"edited_text": "human wins"})
        worker.publish(j, result)
        self.assertEqual(self.s.get(identity, "job")["status"], "STALE_RESULT")
        self.assertEqual(payload(self.s.moment(self.m), "coc")["edited_text"], "human wins")
        identity = self.api.enqueue(self.m, self.s.moment(self.m)["revision"], "COC", "reviewer", uid())["job_id"]
        j = worker.claim()
        self.api.job_action(identity, "cancel", "reviewer", uid())
        worker.publish(j, result)
        self.assertEqual(self.s.get(identity, "job")["status"], "CANCELLED")
        identity = self.api.enqueue(self.m, self.s.moment(self.m)["revision"], "COC", "reviewer", uid())["job_id"]
        worker.claim();worker.recover()
        self.assertEqual(self.s.get(identity, "job")["status"], "OUTCOME_UNKNOWN")
        self.api.job_action(identity, "retry", "reviewer", uid())
        with patch.object(worker, "execute", side_effect=subprocess.TimeoutExpired("test", .01)):
            worker.run_once()
        self.assertEqual(self.s.get(identity, "job")["status"], "TIMED_OUT")

    def test_mock_and_disabled_provider(self):
        with self.assertRaises(StudioError) as e: self.api.enqueue(self.m, 0, "COC", "reviewer", uid())
        self.assertEqual(e.exception.status, 503)
        self.api.provider = MockProvider()
        self.run_job("COC")
        self.assertEqual(payload(self.s.moment(self.m), "coc")["origin"], "MOCK")
        self.assertIn("REAL_PROVIDER_REQUIRED", self.api.eligibility(self.s.moment(self.m))["reasons"])

    def test_export_snapshot_pair_and_split(self):
        self.full_check(real=True)
        before = self.s.moment(self.m)
        self.assertEqual(self.api.eligibility(before)["state"], "ENHANCED_READY")
        req = {"moments": [{"id": self.m, "revision": before["revision"]}], "mode": "COC_TARGET", "purpose": "DEVELOPMENT_TRAINING"}
        exp = self.api.export(req, "reviewer", uid())
        edit(self.api, self.m, "coc", {"edited_text": "later change"})
        Worker(self.api).run_once()
        e = self.s.get(exp["export_id"], "export")
        self.assertEqual(e["status"], "READY")
        path = self.api.asset_path(e["files"][0]["asset_id"])
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["inputs"], rows[1]["inputs"])
        self.assertEqual(rows[0]["targets"]["labels"], rows[1]["targets"]["labels"])
        self.assertEqual(rows[0]["targets"]["coc"], "현재 관찰")
        self.assertNotIn("labels", rows[0]["inputs"])
        with self.assertRaises(StudioError): self.api.export(req, "reviewer", uid())
        with self.assertRaises(StudioError): self.api.lineage(self.group, 0, "test", True, "reviewer", uid())
        self.api.lineage(self.group, 0, "train", False, "reviewer", uid())
        with self.assertRaises(StudioError): self.api.asset_path(e["files"][0]["asset_id"])

    def test_context_manual_cnl_and_completed_counts(self):
        self.full_check(real=True)
        edit(self.api, self.m, "derived", {"text": "수동 번역"})
        self.assertEqual(payload(self.s.moment(self.m), "cnl")["kind"], "DETERMINISTIC")
        before = self.s.moment(self.m)
        req = {"moments": [{"id": self.m, "revision": before["revision"]}], "mode": "ACTION_WITH_CONTEXT", "purpose": "DEVELOPMENT_TRAINING"}
        result = self.api.export(req, "reviewer", uid())
        Worker(self.api).run_once()
        e = self.s.get(result["export_id"], "export")
        self.assertEqual(e["row_count"], 0)
        self.assertIn("CONTEXT_LABEL_LEAKAGE_REVIEW_REQUIRED", e["excluded"][0]["reasons"])
        self.api.complete(self.m, before["revision"], "reviewer", uid())
        edit(self.api, self.ids[0], "action", {"labels": {"DEFER_ENTRY": "NOT_APPLICABLE"}})
        m = self.s.moment(self.ids[0]);self.api.complete(m["id"], m["revision"], "reviewer", uid())
        moments = self.api.moments(self.extraction)
        self.assertEqual(sum(m["completion"] is not None for m in moments), 2)
        self.assertEqual(sum(m["eligibility"]["state"] != "HELD" for m in moments), 1)

    def test_batch_approval_atomicity(self):
        items=[]
        for identity in self.ids[:2]:
            m=edit(self.api, identity, "coc", {"edited_text": "test", "causal_confirmed": True})
            c=m["components"]["coc"]
            items.append({"moment_id": identity,"revision":m["revision"],"stage":"coc","component_id":c["id"],"dependency_digest":digest(c["dependencies"]),"decision":"APPROVE"})
        edit(self.api,self.ids[1],"coc",{"edited_text":"changed"})
        with self.assertRaises(StudioError):self.api.approve(items,"reviewer",uid())
        self.assertFalse(self.s.approved(self.s.moment(self.ids[0]),"coc"))

    def test_simultaneous_cas_and_actual_child_timeout(self):
        barrier = threading.Barrier(2)
        def update(text):
            barrier.wait()
            try:
                self.api.edit(self.m, 0, "coc", {"edited_text": text}, "reviewer", uid())
                return 200
            except StudioError as exc:
                return exc.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(update, ("one", "two")))
        self.assertEqual(sorted(results), [200,409])
        self.assertEqual(self.s.moment(self.m)["revision"],1)
        with self.assertRaises(subprocess.TimeoutExpired):
            child("PROBE", {"path": "/nonexistent-test-input"}, timeout=.000001)

    def test_source_integrity_secret_and_lineage_merge(self):
        prepare(self.api, self.m)
        bad = deepcopy(payload(self.s.moment(self.m), "source"))
        bad["records"][0]["quote"] = "changed excerpt"
        edit(self.api, self.m, "source", bad)
        with self.assertRaises(StudioError): approve(self.api, self.m, "source")
        with self.assertRaises(StudioError): edit(self.api, self.m, "derived", {"api_key": "must-not-export"})
        other = self.s.put("lineage", {"revision": 0, "split": "test", "confirmed": True})
        result = self.api.merge_lineages([{"id": self.group, "revision": 0}, {"id": other, "revision": 0}], "same drive", "reviewer", uid())
        self.assertIsNone(result["split"])
        self.assertFalse(result["confirmed"])
        self.assertIn("LINEAGE_SPLIT_UNRESOLVED", self.api.eligibility(self.s.moment(self.m))["reasons"])
        v = self.s.get(self.video, "video")
        self.api.video_permission(self.video, v["revision"], False, "reviewer", uid())
        self.assertIn("PERMISSION_REVOKED", self.api.eligibility(self.s.moment(self.m))["reasons"])

    def test_model_input_separation_and_invalid_output_preserved(self):
        class RecordingProvider(MockProvider):
            def generate(provider, task, frames, prompt, schema, limits):
                provider.seen = (frames, prompt)
                return {"raw_output": "invalid candidate", "parsed_candidate": {"origin": "REAL"},
                        "model_version": "fixture", "provider_request_id": "test"}
        provider = RecordingProvider();self.api.provider = provider
        edit(self.api, self.m, "action", {"labels": {"ENTER_ZONE": "APPROPRIATE"}})
        j = self.api.enqueue(self.m, self.s.moment(self.m)["revision"], "COC", "reviewer", uid())["job_id"]
        Worker(self.api).run_once()
        frames, prompt = provider.seen
        self.assertLessEqual(max(f["timestamp_us"] for f in frames), self.s.moment(self.m)["t0_us"])
        self.assertNotIn("labels", json.dumps(prompt))
        self.assertEqual(self.s.get(j, "job")["status"], "FAILED")
        self.assertEqual(self.s.objects("model_output")[0]["result"]["raw_output"], "invalid candidate")


class MediaTest(unittest.TestCase):
    def test_real_cpu_decode_pts_and_duplicate_lineage(self):
        with TemporaryDirectory() as root:
            s=Store(Path(root)/"store");api=Service(s);worker=Worker(api)
            try:
                data=video_bytes(root)
                meta={"name":"synthetic.mp4","source":"generated test","license":"test","permission":True}
                uploaded=api.upload(data,meta,"reviewer",uid());worker.run_once()
                self.assertEqual(s.get(uploaded["job_id"],"job")["status"],"SUCCEEDED")
                ex=api.extraction(uploaded["video_id"],1,"reviewer",uid());worker.run_once()
                j=s.get(ex["job_id"],"job");self.assertEqual(j["status"],"SUCCEEDED",j["error"])
                frames=s.get(ex["extraction_id"],"extraction")["frames"]
                self.assertEqual([f["timestamp_us"] for f in frames],list(range(0,10000000,1000000))+[9500000])
                self.assertTrue(all(f["pts"] is not None and f["time_base"] for f in frames))
                duplicate=api.upload(data,meta,"reviewer",uid())
                self.assertEqual(s.get(uploaded["video_id"],"video")["lineage_group_id"],s.get(duplicate["video_id"],"video")["lineage_group_id"])
                broken=api.upload(b"invalid",meta,"reviewer",uid());worker.run_once();worker.run_once()
                self.assertEqual(s.get(broken["job_id"],"job")["status"],"FAILED")
            finally:s.close()


if __name__ == "__main__":unittest.main()
