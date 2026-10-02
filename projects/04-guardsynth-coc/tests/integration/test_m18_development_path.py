"""Fixed-denominator independent scoring and real-data launch authority."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'PROJECT_REGISTRY.json').is_file())
sys.path.insert(0,str(ROOT/'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import run_real_development as real
import prepare_m18_development as prep
import train_speed_development as training
from score_speed_development import score


class DevelopmentPathTest(unittest.TestCase):
    def test_matched_config_cannot_masquerade_as_executable_or_oracle_test(self):
        config=json.loads((ROOT/'projects/04-guardsynth-coc/experiments/paper1_cnl_learning/real_speed_development_config.json').read_text())
        self.assertEqual(config['status'],'SCOPED_DEVELOPMENT_DATA_ADMITTED_MAIN_GATES_REMAIN')
        self.assertTrue(config['main_four_arm_gate_unchanged'])
        self.assertFalse(config['inference_gold_CNL'])
        self.assertTrue(all(config['arms'][a]['dataset'] is None for a in ('L1','L2')))

    def test_scorer_preserves_masks_abstentions_and_no_safety_label_fabrication(self):
        targets=[{'sample_id':'a','clip_group':'c','endpoint_assessments':{
            'MAINTAIN_SPEED':'APPROPRIATE','DECELERATE':None,'STOP_OR_WAIT':'INAPPROPRIATE','START_OR_ACCELERATE':'UNDETERMINED'}}]
        r=score(targets,[{'sample_id':'a','action':'STOP_OR_WAIT'}])
        self.assertEqual(r['metrics']['reference_inappropriate']['rate'],1)
        self.assertEqual(r['metrics']['unnecessary_stop_reference']['rate'],1)
        self.assertEqual(r['metrics']['normal_progress_reference']['rate'],0)
        self.assertTrue(r['safety_violation_rate'].startswith('NOT_IDENTIFIED'))
        r=score(targets,[{'sample_id':'a','action':'DECELERATE'}])
        self.assertEqual(r['scene_denominator'],1)
        self.assertEqual(r['known_selected_reference_count'],0)
        self.assertIsNone(r['metrics']['reference_inappropriate']['rate'])
        r=score(targets,[{'sample_id':'a','action':'malformed'}])
        self.assertEqual(r['valid_output_count'],0)
        self.assertEqual(r['metrics']['normal_progress_reference']['rate'],0)
        with self.assertRaises(ValueError):score(targets,[])

    def test_idle_gpu_refuses_existing_users_even_with_free_memory(self):
        with patch('subprocess.check_output',return_value='4, GPU-test, 2000, 79000, 0'):
            with self.assertRaises(RuntimeError):real.idle_gpu(4)
        with patch('subprocess.check_output',return_value='4, GPU-test, 0, 81153, 0'):
            self.assertEqual(real.idle_gpu(4)['uuid'],'GPU-test')

    def test_reviewed_entry_export_has_explicit_bounded_development_permission(self):
        rows=real.verified_examples()
        self.assertEqual([r['arm'] for r in rows],['L0','L3'])
        self.assertEqual(rows[0]['common_example_sha256'],rows[1]['common_example_sha256'])
        self.assertTrue(all(r['development_training_allowed'] and not r['main_training_allowed'] for r in rows))
        self.assertEqual(rows[0]['action'],'DEFER_ENTRY')

    def test_cohort_audit_has_no_implicit_speed_admission_or_main_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'prep-001'
            config=real.BASE/'m18-cohort-feasibility-2026-09-29-005/admission_evidence.json'
            result=prep.execute(out,config)
            self.assertEqual(result['speed_training_eligible'],0)
            self.assertEqual(result['speed_mechanically_ready'],2)
            self.assertEqual(result['prior_primary_runs_audited'],15)
            split=json.loads((out/'exploratory_split_lock.json').read_text())
            self.assertFalse(split['main_test'])
            self.assertFalse(set(split['train_clip_groups']) & set(split['evaluation_clip_groups']))
            grouped={}
            for r in split['records']:
                grouped.setdefault(r['clip_group'],set()).add(r['partition'])
            self.assertTrue(all(len(v)==1 for v in grouped.values()))
            self.assertEqual(len(split['records']),19)
            for r in json.loads((out/'admission_audit.json').read_text()):
                self.assertFalse(r['training_eligible'])
                if r['checks']['mechanical_ready']:
                    self.assertEqual(r['semantic_projection_version'],'eblc-speed-common-consequence-v0.1-proposal')
            with self.assertRaises(FileExistsError):prep.execute(out)

    def test_actual_user_assent_admits_only_two_version_bound_training_rows(self):
        config=ROOT/'projects/04-guardsynth-coc/experiments/paper1_cnl_learning/real_speed_development_config.json'
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'prep-001';result=prep.execute(out,config)
            self.assertEqual(result['speed_training_eligible'],2)
            self.assertEqual(result['speed_human_cnl_receipts'],2)
            self.assertEqual(result['speed_policy_scope_met'],2)
            rows=json.loads((out/'admission_audit.json').read_text())
            self.assertEqual([r['candidate_index'] for r in rows if r['training_eligible']],[7,68])
            self.assertTrue(all(not r['main_training_allowed'] for r in rows))
            receipt=json.loads((real.READINESS/'stop-common-consequence-acceptance-2026-09-29-001/confirmation.json').read_text())
            self.assertEqual(receipt['answer_verbatim'],'네')
            self.assertEqual(receipt['human_reply_count'],1)
            self.assertFalse(receipt['new_Jonh_attestation'])
            self.assertIsNone(receipt['utterance_time'])

    def test_projection_proof_drift_is_not_a_missing_human_gate(self):
        config=ROOT/'projects/04-guardsynth-coc/experiments/paper1_cnl_learning/real_speed_development_config.json'
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'prep-001'
            with patch('guard_synth_eblc.speed_common_consequence.derive',return_value={'changed':True}):
                with self.assertRaisesRegex(ValueError,'proof/contract drift'):prep.execute(out,config)
            self.assertFalse(out.exists())

    def test_admitted_training_export_is_matched_and_excludes_evaluation_rows(self):
        config,rows,_=training.validated_data()
        self.assertEqual(config['proposed_optimizer_steps_per_arm_seed'],72)
        for arm in ('L0','L3'):
            self.assertEqual([r['candidate_index'] for r in rows[arm]],[7,68])
            self.assertTrue(all(r['partition']=='train' and not r['main_training_allowed'] for r in rows[arm]))
            masked=[s['kind'] for r in rows[arm] for s in r['target_segments'] if not s['supervise']]
            self.assertEqual(masked,['DECELERATE'])

    def test_training_refuses_occupied_gpu_before_creating_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'training-001'
            with patch('subprocess.check_output',return_value='4, GPU-test, 547, 80606, 0'):
                with self.assertRaisesRegex(RuntimeError,'occupied'):training.execute(out,4)
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
