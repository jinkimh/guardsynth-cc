"""Assignment authorization must not become response receipt or source leakage."""
import importlib.util
import json
import re
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
CODE = ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning/assign_speed_review.py'
sys.path.insert(0, str(CODE.parent))
spec = importlib.util.spec_from_file_location('assign_speed_review', CODE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class AssignedSpeedReviewTest(unittest.TestCase):
    def test_ui_refresh_preserves_assigned_packet_and_storage_identity(self):
        import refresh_speed_review_ui as refresh
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'ui-001'
            result = refresh.execute(output)
            old = (refresh.SOURCE / 'assigned_speed_action_review.html').read_text()
            new = (output / 'assigned_speed_action_review.html').read_text()
            pattern = r'<script id="packet" type="application/json">(.*?)</script>'
            self.assertEqual(json.loads(re.search(pattern, old, re.S).group(1)),
                             json.loads(re.search(pattern, new, re.S).group(1)))
            storage = "const storageKey='speed-action-assigned-'+packet.assignment_id+'-'+packet.packet_sha256;"
            self.assertIn(storage, old)
            self.assertIn(storage, new)
            for button in ('save_scene', 'complete_scene'):
                self.assertIn(f'id="{button}"', new)
            self.assertEqual(result['new_assignments'], 0)
            self.assertFalse(result['question_choices_and_completion_criteria_changed'])
            manifest = json.loads((output / 'RUN_MANIFEST.json').read_text())
            for group in ('input_hashes', 'code_hashes', 'output_hashes'):
                for name, digest in manifest[group].items():
                    self.assertEqual(runner.prep.sha(((output if group == 'output_hashes' else ROOT) / name).read_bytes()), digest)
            with self.assertRaises(FileExistsError):
                refresh.execute(output)

    def test_assignment_exact_scope_and_no_response_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'assigned-001'
            result = runner.execute(output)
            self.assertEqual(result['actual_assignment_count'], 19)
            self.assertEqual(result['action_slots'], 76)
            for key in ('responses_received', 'independent_action_gold_added', 'training_scenes_added'):
                self.assertEqual(result[key], 0)
            record = json.loads((output / 'assignment_record.json').read_text())
            self.assertEqual(record['candidate_indices'], runner.prep.INDICES)
            self.assertEqual(record['held_candidate_indices'], [79, 81])
            self.assertEqual(record['reviewer_id'], 'Jonh')
            self.assertFalse(record['dispatched'])
            self.assertEqual(record['formal_reviewers_required'], 2)
            approval = json.loads((output / 'approval_record.json').read_text())
            self.assertEqual(approval['answer_verbatim'], '네..')
            self.assertIsNone(approval['approved_at'])
            packet = json.loads((output / 'action_review_packet.json').read_text())
            self.assertEqual(len(packet['scenes']), 19)
            self.assertEqual(packet['reviewer_id'], 'Jonh')
            html = (output / 'assigned_speed_action_review.html').read_text()
            self.assertNotIn('__PACKET__', html)
            for token in ('original_coc', 'raw_answer', 'zone_polygon', 'cnl_file', 'rule_ref', 'href="/', 'fetch('):
                self.assertNotIn(token, html)
            self.assertIn('COMPLETED_NOT_RECEIVED', html)
            m = json.loads((output / 'RUN_MANIFEST.json').read_text())
            for group in ('input_hashes', 'code_hashes', 'output_hashes'):
                for name, digest in m[group].items():
                    self.assertEqual(runner.prep.sha(((output if group == 'output_hashes' else ROOT) / name).read_bytes()), digest)
            with self.assertRaises(FileExistsError):
                runner.execute(output)


if __name__ == '__main__':
    unittest.main()
