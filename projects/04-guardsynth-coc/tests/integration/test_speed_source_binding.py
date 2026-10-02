"""Source binding must resist answer leakage, clock mistakes and obligation promotion."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
sys.path.insert(0, str(ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import bind_speed_sources as binding


class SpeedSourceBindingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = next(r for r in json.loads((binding.SOURCE / 'candidate_readiness.json').read_text())['records']
                             if r['geometry_index'] == 7)
        cls.answer = next(r for r in json.loads((binding.OBSERVATIONS / 'review_submission.json').read_text())['records']
                          if r['candidate_digest'] == cls.candidate['candidate_digest'])
        cls.annotation = json.loads((ROOT / cls.candidate['annotation_path']).read_text())
        cls.motion = binding.motion_sample([{'timestamp': 1, 'vx': 3., 'vy': 4., 'vz': 0.}], 2, 'sha256:' + '0'*64, 'egomotion')

    def bind(self, answer=None, annotation=None, candidate=None):
        return binding.bind_sources(candidate or self.candidate, answer or self.answer,
            annotation or self.annotation, self.candidate['annotation_sha256'], 'sha256:' + '1'*64 + '#/records/0', self.motion)

    def test_motion_excludes_future_offline_and_does_not_invent_stationary_threshold(self):
        rows = [{'timestamp': 1, 'vx': 0., 'vy': 0., 'vz': 0.},
                {'timestamp': 11, 'vx': 100., 'vy': 0., 'vz': 0.}]
        r = binding.motion_sample(rows, 10, 'ref', 'egomotion')
        self.assertEqual((r['row_index'], r['age_us'], r['velocity_norm_native']), (0, 9, 0))
        self.assertEqual(r['motion_state'], 'UNKNOWN')
        self.assertEqual(binding.motion_sample(rows, 0, 'ref', 'egomotion')['status'], 'NO_PAST_SAMPLE')
        for bad in (list(reversed(rows)), [rows[0], rows[0]], [{'timestamp': True, 'vx': 0., 'vy': 0., 'vz': 0.}],
                    [{'timestamp': 1, 'vx': float('nan'), 'vy': 0., 'vz': 0.}]):
            with self.assertRaises(ValueError):
                binding.motion_sample(bad, 10, 'ref', 'egomotion')
        with self.assertRaises(ValueError):
            binding.motion_sample(rows, 10, 'ref', 'egomotion.offline')

    def test_action_answers_reasons_and_ego_action_annotations_have_no_influence(self):
        answer, candidate, annotation = deepcopy(self.answer), deepcopy(self.candidate), deepcopy(self.annotation)
        answer.update(action_assessments={'STOP_OR_WAIT': 'INAPPROPRIATE'}, reason='invented ACTION reason')
        candidate.update(independent_action_available=True, independent_development_action='STOP_OR_WAIT', original_coc='Stop')
        annotation['annotation']['ego_vehicle']['actions'] = []
        self.assertEqual(self.bind(), self.bind(answer, annotation, candidate))

    def test_reported_true_false_na_never_become_speed_applicability(self):
        for choice in ('TRUE', 'FALSE', 'UNKNOWN', 'CONFLICT', 'NOT_APPLICABLE'):
            answer = deepcopy(self.answer)
            answer['ped_truth'] = answer['control_truth'] = choice
            row = self.bind(answer)
            self.assertEqual(row['speed_premises'], {'motion_state': 'UNKNOWN', 'applicability': 'UNKNOWN', 'evidence_valid': False})
            self.assertEqual(row['reported_predicates']['ped_truth']['reported_truth'], 'UNKNOWN' if choice == 'NOT_APPLICABLE' else choice)
        self.assertTrue(self.bind()['reported_applied_control_with_stop_annotation'])

    def test_target_anchor_is_not_cascade_identity_and_mismatch_rejected(self):
        row = self.bind()
        self.assertIsNotNone(row['target_binding']['observation_target_id'])
        self.assertIsNone(row['target_binding']['cascade_entity_id'])
        for key, value in [('candidate_digest', 'other'), ('event_timestamp_us', 0), ('target_point', [2, 0])]:
            bad = deepcopy(self.answer)
            bad[key] = value
            with self.assertRaises(ValueError):
                self.bind(bad)

    def test_inactive_or_missing_parent_interval_cannot_establish_control(self):
        annotation = deepcopy(self.annotation)
        for a in annotation['annotation']['agents']:
            a['start_timestamp'] = '19.0'
            a['end_timestamp'] = '20.0'
        self.assertFalse(self.bind(annotation=annotation)['reported_applied_control_with_stop_annotation'])
        self.assertEqual(self.bind(annotation=annotation)['active_source_controls'], [])

    def test_same_clip_materialization_preserves_requested_event(self):
        manifest = {'records': [
            {'relative_path': 'event-a/camera/video.mp4', 'role': 'camera', 'clip_id': 'clip', 'candidate_digest': 'a'},
            {'relative_path': 'event-a/egomotion/egomotion.parquet', 'role': 'egomotion', 'clip_id': 'clip', 'candidate_digest': 'a'}]}
        root = Path('/tmp/material')
        self.assertEqual(binding.sensor_member(manifest, root, root / 'event-a/camera/video.mp4', 'clip')['candidate_digest'], 'a')
        with self.assertRaises(ValueError):
            binding.sensor_member(manifest, root, root / 'event-a/camera/video.mp4', 'another_clip')

    def test_bound_core_prevents_report_drift_and_mutation_is_detected(self):
        raw = json.loads((binding.CONTRACTS / 'candidate_7_contract.json').read_text())
        core = binding.source_core(raw, self.bind())
        e = binding.execution
        checked = e.check_queries(e.compile_core_model(e.parse_core_model(core)))
        self.assertEqual(checked['query_count'], checked['matches_expected'])
        mutant = deepcopy(core)
        mutant['clauses'] = [c for c in mutant['clauses'] if c['id'] != 'pinned_source_report_facts']
        checked = e.check_queries(e.compile_core_model(e.parse_core_model(mutant)))
        self.assertLess(checked['matches_expected'], checked['query_count'])

    def test_full_run_pins_sources_without_reading_action_targets(self):
        original_read = Path.read_bytes
        def guarded(path):
            if any(s in str(path) for s in ('speed-action-intake', 'speed-action-submission', 'speed-action-clarification')):
                raise AssertionError('ACTION source leakage')
            return original_read(path)
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'read_bytes', guarded):
            output = Path(tmp) / 'binding-001'
            result = binding.execute(output)
            self.assertEqual((result['bound_scene_records'], result['reported_target_anchors'], result['raw_motion_samples_bound']), (19, 11, 19))
            self.assertEqual((result['source_bound_core_models'], result['smt_queries']), (13, 130))
            self.assertEqual(result['control_stop_agreement_candidates'], [7, 68])
            self.assertEqual(result['held_candidates'], [79, 81])
            rows = json.loads((output / 'source_speed_bindings.json').read_text())['records']
            self.assertEqual([r['candidate_index'] for r in rows], list(binding.SELECTED))
            for r in rows:
                self.assertLessEqual(r['motion_evidence']['timestamp_us'], r['event_timestamp_us'])
                self.assertEqual(r['motion_evidence']['requested_event_timestamp_us'], r['event_timestamp_us'])
                self.assertFalse(r['training_allowed'])
            manifest = json.loads((output / 'RUN_MANIFEST.json').read_text())
            for group in ('input_hashes', 'code_hashes', 'output_hashes'):
                for path, digest in manifest[group].items():
                    self.assertEqual(binding.sha(((output if group == 'output_hashes' else ROOT) / path).read_bytes()), digest)
            with self.assertRaises(FileExistsError):
                binding.execute(output)


if __name__ == '__main__':
    unittest.main()
