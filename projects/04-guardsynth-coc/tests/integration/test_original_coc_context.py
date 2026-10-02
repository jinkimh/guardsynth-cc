"""Source text clues are neither invented task routes nor independent action gold."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
CODE = ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'


def load(name):
    spec = importlib.util.spec_from_file_location(name, CODE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load('audit_original_coc_context')


class OriginalCoCContextTest(unittest.TestCase):
    def test_direction_and_release_do_not_become_route_or_gold(self):
        for text in ('Steer right after passing the person directing traffic.',
                     'Decelerate to maintain a safe distance from the driver on the right.',
                     'Yield to the pedestrian crossing the crosswalk.',
                     'Resume speed after the flagger has cleared the roadway.'):
            result = audit.audit_text(text)
            self.assertEqual(result['context_spans'], [])
            self.assertFalse(result['route_assigned'])
            self.assertIsNone(result['action_gold'])
            self.assertIsNone(result['neutral_prompt'])
        self.assertEqual(audit.audit_text('Steer right after passing the person directing traffic.')['classification'], 'LATERAL_ACTION_ONLY_NOT_ROUTE')

    def test_exact_context_does_not_erase_recommended_action(self):
        text = 'Gentle acceleration to proceed straight while maintaining a safe distance from construction workers and traffic cones.'
        result = audit.audit_text(text)
        self.assertEqual(result['source_action_family'], 'SPEED_RECOVERY_OR_ACCELERATION')
        self.assertEqual(result['context_spans'][0]['kind'], 'STRAIGHT')
        for span in result['context_spans'] + result['recommended_action_spans'] + [result['answer_bearing_remainder']]:
            start, end = span['span']
            self.assertEqual(text[start:end], span['text'])
        self.assertFalse(result['context_verified'])
        result = audit.audit_text('Decelerate for the oncoming vehicle while turning and keeping left to avoid the construction zone on the right.')
        self.assertEqual([s['kind'] for s in result['context_spans']], ['TURN_DIRECTION_UNSPECIFIED'])
        self.assertFalse(result['new_review_ready'])

    def test_all_source_hashes_spans_and_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'audit'
            result = audit.execute(output)
            self.assertEqual(result['original_coc_verified'], 32)
            self.assertEqual(list(result['context_screen_counts'].values()), [10, 20, 2])
            self.assertEqual(sum(result['source_action_family_counts'].values()), 32)
            self.assertEqual(result['source_action_family_counts']['DECELERATE'], 9)
            self.assertEqual(result['source_action_family_counts']['STOP'], 6)
            self.assertEqual(result['source_progress_recommendation_indices'], [48, 50, 85, 86, 88])
            records = json.loads((output / 'original_coc_context_audit.json').read_text())['records']
            for row in records:
                self.assertEqual(audit.sha(row['original_coc'].encode()), row['original_coc_sha256'])
                for span in row['context_spans'] + row['recommended_action_spans']:
                    a, b = span['span']
                    self.assertEqual(row['original_coc'][a:b], span['text'])
                self.assertFalse(row['learning_export_allowed'])
            candidate27 = next(r for r in records if r['candidate_index'] == 27)
            self.assertEqual(candidate27['context_spans'], [])
            self.assertIn('RightTurn', candidate27['source_observed_actions_context_only'][0]['action_type'])
            self.assertFalse(candidate27['source_action_annotations_are_route_log'])
            manifest = json.loads((output / 'RUN_MANIFEST.json').read_text())
            for name, digest in manifest['output_hashes'].items():
                self.assertEqual(audit.sha((output / name).read_bytes()), digest)
            with self.assertRaises(FileExistsError):
                audit.execute(output)

    def test_withdrawn_prototype_cannot_assign_or_write(self):
        prototype = load('prepare_controlled_maneuver')
        with self.assertRaisesRegex(RuntimeError, 'WITHDRAWN'):
            prototype.task_for({'clip_id': 'test'})
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'must_not_exist'
            with self.assertRaisesRegex(RuntimeError, 'WITHDRAWN'):
                prototype.prepare(output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
