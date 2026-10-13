import importlib.util
from pathlib import Path
import unittest

MODULE=Path(__file__).resolve().parents[1]/'condition_model.py'
class ConditionModelTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(),'condition-indexed UPPAAL model absent')
        spec=importlib.util.spec_from_file_location('condition_model',MODULE)
        self.api=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.api)
    def test_foreign_condition_cannot_release_original(self):
        frames=[{'event_id':'s0','action':'STOP','obligation':{'id':'A','condition_id':'A'},'evidence':[],'precondition':True},{'event_id':'s1','action':'GO','obligation':None,'evidence':[{'condition_id':'B','value':True}],'precondition':None}]
        encoded=self.api.encode(frames)
        self.assertEqual(encoded['observations'],[-1,-1])
        self.assertEqual(encoded['obligation_ids'],['A'])
    def test_multiple_obligations_have_distinct_condition_channels(self):
        frames=[{'event_id':'s0','action':'STOP','obligation':{'id':'A','condition_id':'X'},'evidence':[],'precondition':True},{'event_id':'s1','action':'STOP','obligation':{'id':'C','condition_id':'Y'},'evidence':[],'precondition':None},{'event_id':'s2','action':'GO','obligation':None,'evidence':[{'condition_id':'X','value':True},{'condition_id':'Y','value':False}],'precondition':None}]
        e=self.api.encode(frames)
        self.assertEqual(e['observations'][-2:],[1,0])
        self.assertEqual(e['new_obligations'],[0,1,-1])
    def test_solver_parse_distinguishes_unknown_from_violation(self):
        output='\n'.join('Formula is '+('satisfied.' if b else 'NOT satisfied.') for b in [True,False,True,False,False])
        result=self.api.parse_result(output,['e0','e1'])
        self.assertEqual(result['verdict'],'UNKNOWN')
        self.assertIsNone(result['first_event_id'])
    def test_first_violation_maps_to_source_event(self):
        output='\n'.join('Formula is '+('satisfied.' if b else 'NOT satisfied.') for b in [False,True,True,True,False])+'\nfirst_bad_idx=1'
        result=self.api.parse_result(output,['e0','e1'])
        self.assertEqual(result['verdict'],'CONTRADICTION')
        self.assertEqual(result['first_event_id'],'e1')
        self.assertEqual(result['reasons'],['UNRELEASED_OBLIGATION'])
    def test_empty_or_partial_solver_output_rejected(self):
        with self.assertRaises(ValueError):self.api.parse_result('Formula is satisfied.',[])
if __name__=='__main__':unittest.main()
