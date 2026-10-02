"""No hazard polygon, reported clearance or retrospective turn may become route/action gold."""

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
MODULE = ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning/audit_action_task.py"
spec = importlib.util.spec_from_file_location("audit_action_task", MODULE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
RUN = audit.BASE / "m17-action-task-audit-2026-09-28-001"


class ActionTaskAuditTest(unittest.TestCase):
    def test_denominators_provenance_and_no_gold_promotion(self):
        result = json.loads((RUN / "RESULT.json").read_text())
        records = json.loads((RUN / "route_context_audit.json").read_text())["records"]
        self.assertEqual(len(records), 32)
        self.assertEqual(result["observations_retained"], 30)
        self.assertEqual(result["suspended_subset_relation_counts"], {"FALSE": 8, "TRUE": 8})
        self.assertEqual(result["reported_clear_candidates"], [1, 48, 64, 66, 70, 79, 85, 88])
        self.assertFalse(result["replacement_review_ready"])
        for row in records:
            self.assertIsNone(row["normal_progress_gold"])
            self.assertFalse(row["main_training_allowed"])
            self.assertFalse(row["hazard_polygon_is_route"])
        row = next(r for r in records if r["candidate_index"] == 27)
        self.assertTrue(row["source_turn_claims"])
        self.assertEqual(row["intended_route_status"], "NOT_ESTABLISHED_IN_AUDITED_INPUTS")
        manifest = json.loads((RUN / "RUN_MANIFEST.json").read_text())
        for name, expected in manifest["output_hashes"].items():
            self.assertEqual(audit.digest(RUN / name), expected)
        for name, expected in manifest["input_hashes"].items():
            self.assertEqual(audit.digest(ROOT / name), expected)

    def test_clear_report_and_intent_named_field_are_not_route_certification(self):
        row = {"candidate_digest": "test", "geometry_index": 1, "review_index": 1, "clip_id": "test", "event_timestamp_us": 100}
        raw = dict(ped_truth="FALSE", ped_reason="outside path", road_context="NOT_APPLICABLE", road_truth="NOT_APPLICABLE", control_context="UNKNOWN", control_truth="UNKNOWN")
        observation = {"raw_answer": raw, "position": 1, "scope_route": "CONDITIONAL_PEDESTRIAN_CANDIDATE"}
        binding = {"active_ego_actions": [{"action_type": "oxd:MakeARightTurn (unprotected)"}]}
        result = audit.screen(row, binding, observation, {"annotation": {"agents": [{"intent": "Proceed"}]}})
        self.assertTrue(result["reported_clear_screening_candidate"])
        self.assertTrue(result["route_like_field_paths"])
        self.assertEqual(result["other_condition_reports"]["control_truth"], "UNKNOWN")
        self.assertEqual(result["intended_route_status"], "NOT_ESTABLISHED_IN_AUDITED_INPUTS")
        self.assertIsNone(result["normal_progress_gold"])

    def test_suspended_page_only_backs_up_exact_draft_bytes(self):
        html = (RUN / "action_review_suspended.html").read_text()
        self.assertNotIn('<form', html)
        self.assertNotIn('<img', html)
        self.assertNotIn('setItem', html)
        self.assertNotIn('removeItem', html)
        script = re.findall(r'<script>(.*?)</script>', html, re.S)[0]
        stub = """
const assert=require('node:assert/strict');const nodes={backup:{},status:{}};
const original=' {"synthetic":"draft", "complete":false}  ';
let stored=original, blob=null, filename=null;
const document={getElementById:k=>nodes[k],createElement:()=>({click(){filename=this.download}})};
const localStorage={getItem:k=>{assert.ok(k.startsWith('guardsynth-action-batch:'));return stored}};
const URL={createObjectURL:b=>{blob=b;return 'blob:test'},revokeObjectURL(){}};
const setTimeout=f=>f();
"""
        checks = """
nodes.backup.onclick();assert.equal(filename,'paper1_action_review_suspended_draft.json');
blob.text().then(text=>{assert.equal(text,original);assert.equal(stored,original);stored=null;blob=null;nodes.backup.onclick();assert.equal(blob,null);assert.ok(nodes.status.textContent.includes('초안이 없습니다'));console.log('PASS')});
"""
        result = subprocess.run(["node"], input=stub + script + checks, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
