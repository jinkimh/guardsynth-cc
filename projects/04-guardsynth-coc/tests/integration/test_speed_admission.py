"""Synthetic receipts test software paths; these fixtures confer no real research authority."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'PROJECT_REGISTRY.json').exists())
sys.path.insert(0,str(ROOT/'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
sys.path.insert(0,str(ROOT/'platforms/eblc-bcv/src'))
from speed_admission import audit_row, canonical_sha


class AdmissionTest(unittest.TestCase):
    def setUp(self):
        self.row={'candidate_index':999,'candidate_digest':'fixture-only','clip_id':'fixture',
            'speed_premises':{'applicability':'TRUE','evidence_valid':True,'motion_state':'UNKNOWN'},
            'accepted_stop_control':{'scope':'USER_CONFIRMED_DEVELOPMENT_STOP_CONTROL_ONLY',
                'source_ref':'fixture:source','target_id':'fixture_target'}}
        self.contract={'clause_kind':'STOP_REQUIRED','contract_version':'eblc-speed-contract-v0.1',
                       'source_refs':['fixture:source'],'target_entity_id':'fixture_target',
                       'contract_id':'fixture','subject_id':'ego','predicate_id':'stop_applies',
                       'rule_ref':'fixture:source','claim_scope':'CONDITIONAL_SINGLE_DECISION_NOT_VEHICLE_SAFETY'}
        self.text='Synthetic test CNL, not real receipt.'
        self.mapping={'text_sha256':hashlib.sha256(self.text.encode()).hexdigest(),
                      'contract_sha256':canonical_sha(self.contract),'source_refs':['fixture:source']}
        identity={'candidate_digest':'fixture-only','source_binding_sha256':canonical_sha(self.row),
                  'contract_version':self.contract['contract_version'],'provenance_ref':'fixture:not-human'}
        self.receipt={**identity,'receipt_kind':'HUMAN_CNL_FIDELITY','status':'ACCEPTED',
                      'cnl_text_sha256':self.mapping['text_sha256']}
        self.policy={**identity,'status':'AUTHORIZED','scope':'DEVELOPMENT_SPEED_SUPERVISION_ONLY',
                     'clause_kind':'STOP_REQUIRED','allowed_motion_states':['UNKNOWN'],'main_training_allowed':False}

    def audit(self):
        return audit_row(self.row,self.contract,self.text,self.mapping,[self.receipt],[self.policy])

    def test_positive_fixture_and_separate_gates(self):
        self.assertTrue(self.audit()['training_eligible'])
        r=audit_row(self.row,self.contract,self.text,self.mapping)
        self.assertTrue(r['checks']['mechanical_ready'])
        self.assertEqual(r['reasons'],['human_cnl_receipt','research_policy_scope'])

    def test_source_text_contract_and_scope_drift_fail_closed(self):
        for field in ('source','text','contract','scope','provenance','motion_scope','receipt_scene','schema'):
            with self.subTest(field=field):
                self.setUp()
                if field=='source':self.row['speed_premises']['applicability']='UNKNOWN'
                if field=='text':self.text+=' changed'
                if field=='contract':self.contract['target_entity_id']='different'
                if field=='scope':self.policy['scope']='DEVELOPMENT_ENTRY_ONLY'
                if field=='provenance':self.receipt['provenance_ref']=''
                if field=='motion_scope':self.policy['allowed_motion_states']=['MOVING']
                if field=='receipt_scene':self.receipt['candidate_digest']='another'
                if field=='schema':self.contract['contract_version']='invented'
                self.assertFalse(self.audit()['training_eligible'])

    def test_input_evidence_is_not_mutated(self):
        before=copy.deepcopy((self.row,self.contract,self.mapping,self.receipt,self.policy))
        self.audit()
        self.assertEqual(before,(self.row,self.contract,self.mapping,self.receipt,self.policy))

    def test_new_projection_cannot_inherit_old_human_receipt_or_policy(self):
        version='eblc-speed-common-consequence-v0.1-proposal'
        self.mapping['semantic_projection_version']=version
        self.assertFalse(self.audit()['checks']['human_cnl_receipt'])
        self.assertFalse(self.audit()['checks']['research_policy_scope'])
        self.receipt['semantic_projection_version']=version
        self.policy['semantic_projection_version']=version
        self.assertTrue(self.audit()['training_eligible'])


if __name__=='__main__':unittest.main()
