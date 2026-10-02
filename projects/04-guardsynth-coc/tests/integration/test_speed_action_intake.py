"""Received answers stay distinct from source premises, scoped meanings and formal gold."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
CODE = ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning/intake_speed_actions.py'
sys.path.insert(0, str(CODE.parent))
spec = importlib.util.spec_from_file_location('intake_speed_actions', CODE)
intake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intake)


class SpeedActionIntakeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.response = json.loads((intake.SUBMISSION / 'jonh_speed_action_submission.json').read_text())
        cls.packet = json.loads((intake.ASSIGNMENT / 'action_review_packet.json').read_text())
        cls.assignment = json.loads((intake.ASSIGNMENT / 'assignment_record.json').read_text())
        cls.clarifications = json.loads((intake.CLARIFICATION / 'clarifications.json').read_text())

    def test_incomplete_mismatched_and_synthetic_submissions_rejected(self):
        digest = self.assignment['packet_sha256']
        intake.validate_response(self.response, self.packet, digest)
        for kind in ('draft', 'packet', 'reviewer', 'missing', 'duplicate', 'reason', 'choice', 'synthetic', 'timestamp'):
            bad = deepcopy(self.response)
            if kind == 'draft': bad['status'] = 'DRAFT_NOT_SUBMITTED'
            if kind == 'packet': bad['packet_sha256'] = 'wrong'
            if kind == 'reviewer': bad['reviewer_id'] = 'different'
            if kind == 'missing': bad['records'].pop()
            if kind == 'duplicate': bad['records'][1] = deepcopy(bad['records'][0])
            if kind == 'reason': bad['records'][0]['reason'] = ' '
            if kind == 'choice': bad['records'][0]['action_assessments']['DECELERATE'] = None
            if kind == 'synthetic': bad['records'][0]['reason'] = 'BROWSER TEST ONLY'
            if kind == 'timestamp': bad['exported_at'] = '2026-09-29T00:00:00'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                intake.validate_response(bad, self.packet, digest)

    def test_clarifications_mask_only_the_three_scoped_fields(self):
        original = deepcopy(self.response)
        rows = intake.targets_with_scope(self.response, self.clarifications, self.assignment)
        masked = {(r['candidate_index'], a) for r in rows for a, v in r['endpoint_assessments'].items() if v is None}
        self.assertEqual(masked, {(68, 'DECELERATE'), (86, 'START_OR_ACCELERATE'), (94, 'START_OR_ACCELERATE')})
        self.assertEqual(self.response, original)
        self.assertEqual(rows[11]['raw_assessments']['DECELERATE'], 'APPROPRIATE')
        self.assertEqual(rows[11]['endpoint_assessments']['STOP_OR_WAIT'], 'APPROPRIATE')
        self.assertEqual(rows[2]['endpoint_assessments']['STOP_OR_WAIT'], 'UNDETERMINED')
        bad = deepcopy(self.clarifications)
        bad['records'][0]['sample_id'] = 'wrong'
        with self.assertRaises(ValueError):
            intake.targets_with_scope(self.response, bad, self.assignment)

    def test_scorer_retains_denominator_and_does_not_treat_scope_as_false(self):
        targets = intake.targets_with_scope(self.response, self.clarifications, self.assignment)
        predictions = [{'sample_id': r['sample_id'], 'action_assessments': dict(r['raw_assessments'])} for r in targets]
        result = intake.score_development(targets, predictions)
        self.assertEqual((result['slots_total'], result['slots_scored'], result['matches']), (76, 72, 72))
        for p, row in zip(predictions, targets):
            for a in row['scope_limited_actions']:
                p['action_assessments'][a] = 'INAPPROPRIATE'
        self.assertEqual(intake.score_development(targets, predictions)['matches'], 72)
        for p in predictions:
            p['action_assessments'] = dict.fromkeys(intake.ACTIONS, 'UNDETERMINED')
        abstaining = intake.score_development(targets, predictions)
        self.assertEqual(abstaining['slots_scored'], 72)
        self.assertEqual(abstaining['matches'], 0)
        self.assertEqual(abstaining['prediction_abstentions_on_scored_slots'], 72)
        with self.assertRaises(ValueError):
            intake.score_development(targets, predictions[:-1])

    def test_end_to_end_receipt_bank_cnl_and_no_gold_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'intake-001'
            result = intake.execute(output)
            self.assertEqual(result['accepted_response_scenes'], 19)
            self.assertEqual(result['determinate_development_fields'], 72)
            self.assertEqual(result['comparable_fields_including_undetermined'], 73)
            self.assertEqual(result['fully_unmasked_scene_records'], 16)
            self.assertEqual(result['causal_images_verified'], 133)
            self.assertEqual(result['clip_groups'], 17)
            self.assertEqual(result['conditional_cnl_linked'], 13)
            self.assertEqual(result['no_speed_contract'], 6)
            self.assertEqual(result['conditional_smt_queries_replayed'], 130)
            self.assertEqual(result['cnl_semantic_template_groups'], 2)
            self.assertEqual(result['source_action_disagreement_candidates'], [52, 55, 60])
            for key in ('formal_gold_added', 'scene_applicability_certified', 'new_cnl_human_reviews', 'new_training_scenes', 'new_review_requests'):
                self.assertEqual(result[key], 0)
            self.assertEqual((output / 'review_submission.json').read_bytes(), (intake.SUBMISSION / 'jonh_speed_action_submission.json').read_bytes())
            inputs = [json.loads(line) for line in (output / 'development_action_inputs.jsonl').read_text().splitlines()]
            self.assertEqual(len(inputs), 19)
            self.assertTrue(all(set(r) == {'sample_id', 'question_ko', 'actions', 'assessment_choices', 'instructions_ko',
                'time_scope', 'packet_ref', 'packet_sha256', 'scene_pointer', 'frames'} for r in inputs))
            m = json.loads((output / 'RUN_MANIFEST.json').read_text())
            for group in ('input_hashes', 'code_hashes', 'output_hashes'):
                for path, digest in m[group].items():
                    self.assertEqual(intake.prep.sha(((output if group == 'output_hashes' else ROOT) / path).read_bytes()), digest)
            with self.assertRaises(FileExistsError):
                intake.execute(output)


if __name__ == '__main__':
    unittest.main()
