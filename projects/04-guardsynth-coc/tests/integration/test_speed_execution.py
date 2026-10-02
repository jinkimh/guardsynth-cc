"""Accepted semantics execution must retain missing gold and unassigned blind inputs."""

import base64
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
sys.path.insert(0, str(ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import execute_speed_contracts as execution


class SpeedExecutionTest(unittest.TestCase):
    def inputs(self):
        frame = {'timestamp_us': 9, 'frame_index': 0, 'sha256': execution.prior.sha(b'image'),
                 'data_url': 'data:image/jpeg;base64,' + base64.b64encode(b'image').decode()}
        row = {'sample_id': 's1', 'candidate_digest': 'c1', 'candidate_index': 6,
               'clip_id': 'clip', 'event_timestamp_us': 10}
        scene = {**row, 'frames': [frame], 'original_coc': 'ANSWER', 'zone_polygon': 'CUE'}
        draft = {k: 'common' for k in ('question_ko', 'actions', 'assessment_choices', 'instructions_ko', 'time_scope')}
        draft['scenes'] = [{'sample_id': 's1', 'frames': [{k: frame[k] for k in ('timestamp_us', 'frame_index', 'sha256')}]}]
        return row, scene, draft

    def test_blind_allowlist_and_held_routes(self):
        row, scene, draft = self.inputs()
        pool = execution.blind_pool([row], draft, [scene])
        self.assertEqual(set(pool['scenes'][0]), {'sample_id', 'event_timestamp_us', 'frames'})
        self.assertNotIn('ANSWER', json.dumps(pool))
        self.assertNotIn('zone_polygon', json.dumps(pool))
        for index in (79, 81):
            self.assertEqual(execution.blind_pool([{**row, 'candidate_index': index}], draft, [scene])['scenes'], [])

    def test_input_drift_future_and_image_corruption_rejected(self):
        row, scene, draft = self.inputs()
        for key, value in (('clip_id', 'other'), ('event_timestamp_us', 11)):
            with self.assertRaises(ValueError):
                execution.blind_pool([row], draft, [{**scene, key: value}])
        for frame_key, value in (('timestamp_us', 11), ('sha256', 'wrong'), ('data_url', 'data:image/jpeg;base64,YmFk')):
            changed = deepcopy(scene)
            changed['frames'][0][frame_key] = value
            with self.assertRaises(ValueError):
                execution.blind_pool([row], draft, [changed])

    def test_actual_run_smt_cnl_pool_and_no_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'speed-001'
            result = execution.execute(output)
            self.assertEqual(result['synthetic_smt_queries'], 626)
            self.assertEqual(result['mutation_queries'], 6)
            self.assertEqual(result['scene_unknown_queries'], 150)
            self.assertEqual(result['solver_matches_expected'], 782)
            self.assertEqual(result['prepared_action_scenes'], 19)
            self.assertEqual(result['prepared_causal_jpegs'], 133)
            self.assertEqual(result['conditional_cnl_documents'], 15)
            self.assertEqual(result['excluded_test_clips'], 81)
            for key in ('scene_applicability_certified', 'independent_speed_action_gold',
                        'independent_cnl_reviews', 'reviewer_dispatched', 'new_training_scenes'):
                self.assertEqual(result[key], 0)
            pool = json.loads((output / 'action_input_pool.json').read_text())
            for scene in pool['scenes']:
                self.assertEqual(set(scene), {'sample_id', 'event_timestamp_us', 'frames'})
                self.assertEqual(len(scene['frames']), 7)
            records = json.loads((output / 'coordinator_bindings.json').read_text())['records']
            self.assertEqual({r['candidate_index'] for r in records if r['route_hold']}, {79, 81})
            for row in records:
                self.assertFalse(row['training_allowed'])
                self.assertFalse(row['reviewer_dispatch_allowed'])
                self.assertIsNone(row['action_gold'])
                self.assertEqual(set(row['scene_clause_verdicts'].values()), {'UNRESOLVED'})
            prep = json.loads((output / 'review_preparation.json').read_text())
            self.assertIsNone(prep['actual_assignment_count'])
            self.assertTrue(all(v is None for v in prep['exposure_declaration'].values()))
            self.assertTrue(all(v is None for r in prep['response_template'] for v in r['action_assessments'].values()))
            m = json.loads((output / 'RUN_MANIFEST.json').read_text())
            for field in ('input_hashes', 'code_hashes', 'output_hashes'):
                for path, sha in m[field].items():
                    self.assertEqual(execution.prior.sha(((output if field == 'output_hashes' else ROOT) / path).read_bytes()), sha)
            with self.assertRaises(FileExistsError):
                execution.execute(output)


if __name__ == '__main__':
    unittest.main()
