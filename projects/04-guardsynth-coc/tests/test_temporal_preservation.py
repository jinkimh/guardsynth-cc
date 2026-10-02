import copy
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import temporal_preservation as t

class TemporalPreservationTest(unittest.TestCase):
    def test_boundary_smt(self):
        for duration in (.5,1.5,.8,1.8):
            _,checks=t.verify(t.contract(duration))
            self.assertEqual(checks['query_count'],25)
            self.assertEqual(checks['matches_expected'],25)
    def test_missing_gate_mutation_detected(self):
        core,_=t.verify(t.contract(.5))
        core['clauses'][0]['formula']=t.lit(True)
        checks=t.check_queries(t.compile_core_model(t.parse_core_model(core)))
        self.assertLess(checks['matches_expected'],checks['query_count'])
    def test_no_target_dependency(self):
        from dataclasses import replace
        a=t.examples(42,'test',1,'P2')[0]
        self.assertEqual(t.independent_score(a,'A'),t.independent_score(replace(a,target='D'),'A'))
        self.assertNotEqual(t.world.prompt_for(a,'RICH_COC'),t.world.prompt_for(t.examples(42,'test',1,'P1')[0],'RICH_COC'))
    def test_contract_mutations_rejected(self):
        for key,value in [('time_unit','s'),('subject','pedestrian'),('hold','ALLOW_ENTRY'),('release_clear_ms',501)]:
            raw=t.contract(.5);raw[key]=value
            with self.assertRaises(ValueError):t.render(raw)
    def test_independent_boundary_and_deadlock(self):
        for e in t.examples(2026092901,'test',48,'P0'):
            good=[c for c in e.scene.candidates if t.independent_score(e,c.label)['correct']]
            self.assertEqual(len(good),1)
            self.assertEqual(good[0].label,e.target)
            for c in e.scene.candidates:
                score=t.independent_score(e,c.label)
                if c.role=='deadlock':
                    self.assertTrue(score['deadlock']);self.assertFalse(score['safe_goal_complete'])
                if c.role=='premature':self.assertTrue(score['guard_violation'])
            self.assertFalse(t.independent_score(e,'INVALID')['valid'])

if __name__=='__main__':unittest.main()
