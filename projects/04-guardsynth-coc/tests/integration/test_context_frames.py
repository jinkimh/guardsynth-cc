"""Frame-based triage is reproducible provenance, not independent behavioral gold."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
CODE = ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning/audit_context_frames.py'
spec = importlib.util.spec_from_file_location('audit_context_frames', CODE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ContextFrameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notes = json.loads(audit.NOTES.read_text())['records']
        cls.rows = json.loads((audit.SOURCE / 'original_coc_context_audit.json').read_text())['records']
        scenes = json.loads((audit.FRAMES / 'source_gap_packet.json').read_text())['scenes']
        cls.row = next(r for r in cls.rows if r['candidate_index'] == 1)
        cls.scene = next(s for s in scenes if s['candidate_digest'] == cls.row['candidate_digest'])
        cls.note = next(n for n in cls.notes if n['candidate_index'] == 1)

    def test_frame_identity_and_visual_coverage(self):
        audit.check_frames(self.scene, self.note, self.row)
        scene = copy.deepcopy(self.scene)
        scene['frames'][1]['timestamp_us'] = self.row['event_timestamp_us'] + 1
        with self.assertRaisesRegex(ValueError, 'noncausal'):
            audit.check_frames(scene, self.note, self.row)

    def test_hash_and_inspection_drift_rejected(self):
        scene = copy.deepcopy(self.scene)
        scene['frames'][1]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'frame hash'):
            audit.check_frames(scene, self.note, self.row)
        note = copy.deepcopy(self.note)
        note['inspected_frames'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'inspected frame'):
            audit.check_frames(self.scene, note, self.row)

    def test_no_context_or_gold_promotion(self):
        for key, value in [('context_accepted', True), ('action_gold', 'PROCEED')]:
            note = copy.deepcopy(self.note)
            note[key] = value
            with self.assertRaisesRegex(ValueError, 'cannot promote'):
                audit.check_frames(self.scene, note, self.row)

    def test_source_identity_and_frame_order(self):
        for key, value in [('original_coc', 'modified'), ('clip_id', 'different')]:
            scene = copy.deepcopy(self.scene)
            scene[key] = value
            with self.assertRaises(ValueError):
                audit.check_frames(scene, self.note, self.row)
        scene = copy.deepcopy(self.scene)
        scene['frames'][1]['timestamp_us'] = scene['frames'][0]['timestamp_us']
        with self.assertRaisesRegex(ValueError, 'order'):
            audit.check_frames(scene, self.note, self.row)

    def test_endpoint_is_not_new_task_or_human_answer(self):
        notes = {n['candidate_index']: n for n in self.notes}
        self.assertEqual(notes[66]['context_status'], 'ANSWER_BEARING_CONTEXT_BLOCKED')
        self.assertEqual(notes[66]['endpoint_axis'], 'LATERAL_MANEUVER')
        self.assertEqual(notes[79]['context_status'], 'PARTIAL_CONTEXT_UNRESOLVED')
        for note in notes.values():
            self.assertIsNone(note['action_gold'])
            self.assertFalse(note['context_accepted'])

    def test_complete_run_preserves_denominator_and_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'audit'
            result = audit.execute(output)
            self.assertEqual(result['original_candidate_denominator'], 32)
            self.assertEqual(result['context_candidates_audited'], 10)
            self.assertEqual(result['other_candidates_not_visually_audited'], 22)
            self.assertEqual(result['audited_clip_groups'], 9)
            self.assertEqual(result['frame_packet_entries_hash_time_checked'], 70)
            self.assertEqual(result['visual_frame_inspections'], 40)
            self.assertEqual(result['unique_visually_inspected_jpegs'], 39)
            self.assertEqual(result['same_clip_candidate_groups'], [[86, 94]])
            self.assertEqual(result['endpoint_axis_counts'], {'LATERAL_PATH': 4, 'LONGITUDINAL': 5, 'LATERAL_MANEUVER': 1})
            self.assertEqual(result['potential_source_action_tension_candidates'], [88])
            for key in ('neutral_contexts_accepted', 'independent_action_gold_created', 'new_training_scenes'):
                self.assertEqual(result[key], 0)
            for key in ('route_assigned', 'new_review_ready', 'repeat_source_survey_requested', 'main_cohort_frozen'):
                self.assertFalse(result[key])
            data = json.loads((output / 'context_frame_endpoint_audit.json').read_text())
            self.assertTrue(data['original_coc_exposed'])
            self.assertFalse(data['independent_human_review'])
            for row in data['records']:
                self.assertIsNone(row['action_gold'])
                self.assertFalse(row['learning_export_allowed'])
                self.assertFalse(row['context_verified'])
            manifest = json.loads((output / 'RUN_MANIFEST.json').read_text())
            for name, digest in manifest['output_hashes'].items():
                self.assertEqual(audit.sha((output / name).read_bytes()), digest)
            with self.assertRaises(FileExistsError):
                audit.execute(output)


if __name__ == '__main__':
    unittest.main()
