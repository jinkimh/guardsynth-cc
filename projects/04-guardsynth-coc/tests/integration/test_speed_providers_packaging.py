"""Source-only provider boundary and preservation of real masks/CoC in staged rows."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'PROJECT_REGISTRY.json').exists())
sys.path.insert(0,str(ROOT/'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import speed_source_providers as providers
import package_speed_development as packaging
import run_real_development as real


class ProvidersPackagingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=json.loads((real.READINESS/'stop-control-source-acceptance-2026-09-29-001/source_speed_bindings.json').read_text())['records']

    def test_action_answers_and_original_coc_cannot_enter_source_provider(self):
        row=copy.deepcopy(next(r for r in self.rows if r.get('accepted_stop_control')))
        row.update(raw_assessments='FORBIDDEN_ANSWER_SENTINEL',raw_reason='FORBIDDEN_REASON_SENTINEL',
                   original_coc='FORBIDDEN_COC_SENTINEL')
        for arm in ('L1','L2'):
            prompt=providers.request_for(row,arm)
            self.assertNotIn('FORBIDDEN_',prompt)
            self.assertIn(row['accepted_stop_control']['source_ref'],prompt)
            self.assertIn('UNKNOWN',prompt)

    def test_l2_renderer_is_unverified_and_rejects_invented_evidence(self):
        row=next(r for r in self.rows if r.get('accepted_stop_control'))
        candidate={'clause_kind':'STOP_REQUIRED','predicate_id':'stop_applies',
                   'target_entity_id':row['accepted_stop_control']['target_id'],
                   'source_refs':[row['accepted_stop_control']['source_ref']]}
        result=providers.render_candidate(json.dumps(candidate),row)
        self.assertEqual(result['status'],'UNVERIFIED_CANDIDATE')
        self.assertFalse(result['semantic_verification_performed'])
        self.assertIn('UNKNOWN motion',result['cnl'])
        candidate['source_refs']=['invented:legal_authority']
        with self.assertRaises(ValueError):providers.render_candidate(json.dumps(candidate),row)
        self.assertEqual(providers.render_candidate('{"abstain":true}',row)['status'],'ABSTAIN')

    def test_staging_preserves_raw_choices_but_masks_only_scoped_fields(self):
        targets=[json.loads(s) for s in (real.READINESS/'speed-action-intake-2026-09-29-001/development_action_targets.jsonl').read_text().splitlines()]
        masked=[]
        for target in targets:
            original='Unchanged original CoC, including any disagreement.'
            segments=packaging.target_segments(original,target)
            self.assertEqual(segments[0]['text'],'ORIGINAL_COC\n'+original+'\n')
            for segment in segments[1:]:
                self.assertIn(target['raw_assessments'][segment['kind']],segment['text'])
                if not segment['supervise']:masked.append((target['candidate_index'],segment['kind']))
        self.assertEqual(masked,[(68,'DECELERATE'),(86,'START_OR_ACCELERATE'),(94,'START_OR_ACCELERATE')])

    def test_pretrained_frozen_inputs_are_blind_causal_and_use_all_frames(self):
        run=real.BASE/'pretrained-speed-development-2026-09-29-002'
        lock=json.loads((run/'protocol_lock.json').read_text())
        rows=json.loads((run/'blind_inputs.json').read_text())
        self.assertEqual(real.digest(run/'blind_inputs.json'),lock['frozen_inputs_sha256'])
        self.assertEqual(len(rows),19)
        self.assertEqual(sum(len(r['frames']) for r in rows),133)
        for row in rows:
            self.assertEqual(set(row),{'sample_id','frames'})
            times=[r['timestamp_us'] for r in row['frames']]
            self.assertEqual(times,sorted(times))
        self.assertFalse(lock['answer_coc_cnl_in_input'])
        self.assertEqual(lock['optimizer_updates'],0)

    def test_matched_provider_requests_preserve_coc_images_and_full_denominator(self):
        run=real.BASE/'matched-speed-providers-2026-09-29-001'
        lock=json.loads((run/'protocol_lock.json').read_text())
        requests=json.loads((run/'requests.json').read_text())
        self.assertEqual(len(lock['full_denominator_candidates']),19)
        self.assertEqual(lock['selected_candidates'],[7,68])
        self.assertFalse(lock['ACTION_answers_used'])
        self.assertFalse(lock['training_eligible'])
        source=json.loads((real.READINESS/'speed-contract-execution-2026-09-28-001/coordinator_bindings.json').read_text())['records']
        for idx in (7,68):
            pair=[r for r in requests if r['candidate_index']==idx]
            coc=next(r['original_coc'] for r in source if r['candidate_index']==idx)
            self.assertEqual([r['arm'] for r in pair],['L1','L2'])
            self.assertEqual(pair[0]['frame_hashes'],pair[1]['frame_hashes'])
            self.assertEqual(len(pair[0]['frame_hashes']),7)
            self.assertTrue(all(coc in r['prompt'] for r in pair))


if __name__=='__main__':unittest.main()
