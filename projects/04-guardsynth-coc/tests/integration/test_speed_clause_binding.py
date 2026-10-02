"""Regression boundaries for source-only speed binding and unaccepted policy proposals."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
CODE = ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning/prepare_speed_clause_binding.py'
spec = importlib.util.spec_from_file_location('speed_binding', CODE)
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)


class SpeedClauseBindingTest(unittest.TestCase):
    def test_unknown_conflict_invalid_never_become_stop_gold(self):
        for kind in binding.KINDS:
            for motion in binding.MOTIONS:
                for truth in binding.TRUTHS:
                    for valid in (False, True):
                        if motion == 'UNKNOWN' or not valid or truth in ('UNKNOWN', 'CONFLICT'):
                            self.assertEqual(set(binding.probe(kind, motion, truth, valid).values()),
                                             {binding.UNRESOLVED})

    def test_deceleration_and_stop_are_distinct_intentions(self):
        decel = binding.probe('SPEED_REDUCTION_REQUIRED', 'MOVING', 'TRUE', True)
        stop = binding.probe('STOP_REQUIRED', 'MOVING', 'TRUE', True)
        self.assertEqual(decel['DECELERATE'], binding.NOT_EXCLUDED)
        self.assertEqual(stop['DECELERATE'], binding.BLOCKED)
        for result in (decel, stop):
            self.assertEqual(result['START_OR_ACCELERATE'], binding.BLOCKED)
            self.assertEqual(result['MAINTAIN_SPEED'], binding.BLOCKED)
            self.assertEqual(result['STOP_OR_WAIT'], binding.NOT_EXCLUDED)

    def test_stationary_semantics_are_not_moving_assumptions(self):
        self.assertEqual(set(binding.probe('SPEED_REDUCTION_REQUIRED', 'STATIONARY', 'TRUE', True).values()),
                         {binding.UNRESOLVED})
        stop = binding.probe('STOP_REQUIRED', 'STATIONARY', 'TRUE', True)
        self.assertEqual(stop['MAINTAIN_SPEED'], binding.UNRESOLVED)
        self.assertEqual(stop['DECELERATE'], binding.UNRESOLVED)
        self.assertEqual(stop['START_OR_ACCELERATE'], binding.BLOCKED)
        self.assertEqual(stop['STOP_OR_WAIT'], binding.NOT_EXCLUDED)

    def test_false_discharge_is_not_permission(self):
        for kind in binding.KINDS:
            self.assertEqual(set(binding.probe(kind, 'MOVING', 'FALSE', True).values()),
                             {'NOT_EXCLUDED_BY_THIS_CLAUSE_NOT_PERMISSION'})
            self.assertEqual(set(binding.probe(kind, 'MOVING', 'FALSE', False).values()),
                             {binding.UNRESOLVED})

    def test_legacy_entry_policy_and_na_are_rejected(self):
        for args in (('CLEAR_REQUIRED_FOR_ENTRY', 'MOVING', 'TRUE', True),
                     ('STOP_REQUIRED', 'MOVING', 'NOT_APPLICABLE', True),
                     ('STOP_REQUIRED', 'MOVING', 'FALSE', 1),
                     ('STOP_REQUIRED', 'INFERRED_FROM_COC', 'TRUE', True)):
            with self.assertRaises(ValueError):
                binding.probe(*args)

    def test_source_spans_preserve_strength_without_certification(self):
        text = 'Strong deceleration for the approaching pedestrians.'
        row = {'original_coc': text, 'original_coc_sha256': binding.sha(text.encode())}
        claim = binding.source_claim(row)
        self.assertEqual(text[claim['start']:claim['end']], 'Strong deceleration')
        self.assertFalse(claim['magnitude_evaluated'])
        self.assertEqual(claim['authority'], 'SOURCE_CLAIM_NOT_NORMATIVE_OR_GOLD')
        row['original_coc'] = text.replace('Strong', 'Gentle')
        with self.assertRaisesRegex(ValueError, 'hash'):
            binding.source_claim(row)

    def test_resume_adapt_and_acceleration_create_no_obligation(self):
        for text in ('Resume speed after yielding.', 'Adapt speed for the construction zone.',
                     'Gentle acceleration to proceed straight.'):
            claim = binding.source_claim({'original_coc': text, 'original_coc_sha256': binding.sha(text.encode())})
            self.assertIsNone(claim['proposed_clause_kind'])
            if text.startswith(('Resume', 'Adapt')):
                self.assertIsNone(claim['source_recommendation_action'])

    def test_end_to_end_provenance_no_promotion_and_immutable_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'binding-001'
            result = binding.execute(output)
            self.assertEqual(result['candidate_denominator'], 32)
            self.assertEqual(result['speed_candidates'], 21)
            self.assertEqual(result['speed_clip_groups'], 19)
            self.assertEqual(result['excluded_test_clips'], 81)
            self.assertEqual(result['proposed_clause_counts'], {
                'SPEED_REDUCTION_REQUIRED': 9, 'STOP_REQUIRED': 6, 'NO_CLAUSE_PROPOSED': 6})
            self.assertEqual(result['single_action_mapping_unresolved'], [48, 50, 85, 94])
            for key in ('speed_smt_queries', 'accepted_speed_clauses', 'independent_speed_action_gold',
                        'reviewer_dispatched', 'new_training_scenes'):
                self.assertEqual(result[key], 0)
            previous = json.loads((binding.PREPARATION / 'coordinator_reuse_audit.json').read_text())
            source = {r['candidate_index']: r for r in previous['records']}
            rows = json.loads((output / 'source_clause_bindings.json').read_text())['records']
            for row in rows:
                old = source[row['candidate_index']]
                self.assertEqual(row['original_coc'], old['original_coc'])
                self.assertEqual(row['scope_reminders'], old['scope_reminders'])
                self.assertEqual(set(row['scene_clause_verdicts'].values()), {binding.UNRESOLVED})
                self.assertIsNone(row['action_gold'])
                self.assertIsNone(row['independent_violation_reference'])
                self.assertIsNone(row['independent_progress_reference'])
                self.assertFalse(row['training_allowed'])
                self.assertFalse(row['reviewer_dispatch_allowed'])
            cases = json.loads((output / 'proposed_interface_cases.json').read_text())['cases']
            self.assertEqual(len(cases), 48)
            self.assertEqual(sum(len(c['verdicts']) for c in cases), 192)
            manifest = json.loads((output / 'RUN_MANIFEST.json').read_text())
            for key in ('input_hashes', 'code_hashes', 'output_hashes'):
                for path, digest in manifest[key].items():
                    self.assertEqual(binding.sha(((output if key == 'output_hashes' else ROOT) / path).read_bytes()), digest)
            with self.assertRaises(FileExistsError):
                binding.execute(output)


if __name__ == '__main__':
    unittest.main()
