"""Existing source answers must not become speed-action gold or reviewer hints."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
CODE = ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning/prepare_longitudinal_endpoint.py'
spec = importlib.util.spec_from_file_location('prepare_longitudinal_endpoint', CODE)
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)


class LongitudinalPreparationTest(unittest.TestCase):
    def test_blind_input_rejects_future_and_identity_drift(self):
        row = {'candidate_digest': 'x', 'clip_id': 'c', 'event_timestamp_us': 10}
        scene = {**row, 'original_coc': 'ANSWER CUE', 'frames': [
            {'timestamp_us': 9, 'frame_index': 0, 'sha256': 'abc'}]}
        out = prep.blind_input(row, scene, 'sample-01')
        self.assertNotIn('ANSWER CUE', json.dumps(out))
        self.assertEqual(set(out), {'sample_id', 'event_timestamp_us', 'frames'})
        scene['frames'][0]['timestamp_us'] = 11
        with self.assertRaisesRegex(ValueError, 'causal'):
            prep.blind_input(row, scene, 'sample-01')
        scene['frames'][0]['timestamp_us'] = 9
        scene['clip_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'identity'):
            prep.blind_input(row, scene, 'sample-01')

    def test_blind_input_rejects_empty_duplicate_and_noninteger_times(self):
        row = {'candidate_digest': 'x', 'clip_id': 'c', 'event_timestamp_us': 10}
        frame = {'timestamp_us': 9, 'frame_index': 0, 'sha256': 'abc'}
        for frames in ([], [frame, frame], [{**frame, 'timestamp_us': 9.5}]):
            with self.assertRaisesRegex(ValueError, 'causal'):
                prep.blind_input(row, {**row, 'frames': frames}, 'sample-01')

    def test_slow_note_and_not_applicable_do_not_release(self):
        obs = {'raw_answer': {'control_truth': 'FALSE', 'control_reason': '천천히',
                             'road_truth': 'NOT_APPLICABLE', 'ped_truth': 'UNKNOWN'}}
        original = copy.deepcopy(obs)
        out = prep.reuse_observation(obs)
        self.assertEqual(obs, original)
        self.assertEqual(out['raw_answer'], original['raw_answer'])
        self.assertEqual(out['reported_unknown_fields'], ['ped_truth'])
        self.assertEqual(out['legacy_not_applicable_fields'], ['road_truth'])
        self.assertIsNone(out['speed_action_gold'])
        self.assertFalse(out['entry_clearance_implies_speed_release'])

    def test_free_text_is_not_a_choice_field(self):
        out = prep.reuse_observation({'raw_answer': {
            'control_truth': 'FALSE', 'control_reason': 'UNKNOWN',
            'target_description': 'NOT_APPLICABLE'}})
        self.assertEqual(out['reported_unknown_fields'], [])
        self.assertEqual(out['legacy_not_applicable_fields'], [])

    def test_end_to_end_reuse_and_no_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'prep'
            result = prep.execute(output)
            self.assertEqual(result['candidate_denominator'], 32)
            self.assertEqual(result['speed_candidates'], 21)
            self.assertEqual(result['speed_clip_groups'], 19)
            self.assertEqual(result['source_observations_reused'], 21)
            self.assertEqual(result['new_endpoint_gold_missing'], 21)
            self.assertEqual(result['reviewer_dispatched'], 0)
            self.assertEqual(result['new_training_scenes'], 0)
            self.assertFalse(result['main_endpoint_frozen'])
            rows = json.loads((output / 'coordinator_reuse_audit.json').read_text())['records']
            source = json.loads((prep.INTAKE / 'review_submission.json').read_text())
            raw_by_id = {r['candidate_digest']: r for r in source['records']}
            for row in rows:
                self.assertEqual(row['reuse']['raw_answer'], raw_by_id[row['candidate_digest']])
                self.assertIsNone(row['reuse']['speed_action_gold'])
                self.assertIsNone(row['current_motion_state'])
                self.assertFalse(row['training_allowed'])
                self.assertFalse(row['old_entry_contract_covers_speed_actions'])
                self.assertIsNone(row['independent_violation_reference'])
                self.assertIsNone(row['independent_progress_reference'])
            slow = next(r for r in rows if r['candidate_index'] == 86)
            self.assertEqual(slow['reuse']['raw_answer']['control_truth'], 'FALSE')
            self.assertEqual(slow['reuse']['raw_answer']['control_reason'], '천천히')
            signal = next(r for r in rows if r['candidate_index'] == 59)
            self.assertEqual(signal['user_clarification']['interpretation'], 'SIGNAL_NOT_OBSERVED_AT_JUDGMENT_TIME')
            packet = json.loads((output / 'action_input_draft.json').read_text())
            self.assertEqual(len(packet['scenes']), 21)
            self.assertEqual(len(packet['actions']), 4)
            for scene in packet['scenes']:
                self.assertEqual(set(scene), {'sample_id', 'event_timestamp_us', 'frames'})
                self.assertEqual(len(scene['frames']), 7)
                self.assertTrue(all(f['timestamp_us'] <= scene['event_timestamp_us'] for f in scene['frames']))
            raw = json.dumps(packet)
            for key in ('original_coc', 'raw_answer', 'zone_polygon', 'target_point', 'control_reason', 'action_gold', 'source_action_family'):
                self.assertNotIn('"' + key + '"', raw)
            responses = json.loads((output / 'unfilled_action_records.json').read_text())['records']
            self.assertEqual(len(responses), 21)
            self.assertTrue(all(all(v is None for v in r['action_assessments'].values()) for r in responses))
            manifest = json.loads((output / 'RUN_MANIFEST.json').read_text())
            for name, digest in manifest['output_hashes'].items():
                self.assertEqual(prep.sha((output / name).read_bytes()), digest)
            with self.assertRaises(FileExistsError):
                prep.execute(output)


if __name__ == '__main__':
    unittest.main()
