import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import temporal_diversity as d
import analyze_temporal_diversity as a

class DiversityTest(unittest.TestCase):
    def test_profile_separate_and_precision(self):
        self.assertRaises(ValueError,d.primary.contract,.2)
        for ms in (0,201,3100,True):self.assertRaises(ValueError,d.contract,ms)
        for ms in (200,500,600,1200,1400,1500):
            _,checks=d.check_core(d.core_for(d.contract(ms)),ms)
            self.assertEqual(checks['matches_expected'],7)
            for style in ('canonical','paraphrase1','paraphrase2'):
                for arm in ('P1','P2'):
                    self.assertEqual(d.parse_rendered(d.render(d.contract(ms),style,arm)),d.contract(ms))
    def test_model_action_binding_and_independent_reference(self):
        rows=d.base_rows('test',[1.7],[.6,1.4],[.5,.6,1.5])
        for row in rows:
            for c in row['candidates']:
                score=d.oracle(row,c['label']);check=d.execute_choice(row,c['label'])
                self.assertEqual(check['status'],'UNSAT' if score['violation'] else 'SAT')
            row['reference']='INVALID'
            self.assertNotEqual(d.oracle(row,'INVALID')['reference'],'INVALID')
        self.assertEqual(d.execute_choice(rows[0],'INVALID')['status'],'INVALID_OUTPUT_NOT_EXECUTABLE')
    def test_mutations_positive_controls_and_source_miss(self):
        rows=d.d4_rows(d.base_rows('quality',[1.2],[.2,1.2],[.1,.2,1.2])[:2])
        summary=a.quality_summary(rows)
        self.assertEqual(summary['valid_acceptance_coverage'],1.)
        self.assertEqual(summary['by_type']['shared_source_error']['misses'],2)
        self.assertEqual(summary['by_type']['threshold_change']['internally_SAT_count'],2)
        for kind,item in summary['by_type'].items():
            if kind not in ('valid','shared_source_error'):self.assertEqual(item['detected'],2)
    def test_visual_intervention_only_changes_pixels(self):
        row=d.base_rows('joint',[4.6],[.2,1.2],[-.5,.5,1.5])[0]
        self.assertLess(row['clear_ms']+1000,6000)
        self.assertNotEqual(d.image_for(row,'original').tobytes(),d.image_for(row,'swapped').tobytes())
        before=d.prompt(row,'P2','canonical');d.image_for(row,'blank')
        self.assertEqual(before,d.prompt(row,'P2','canonical'))
    def test_label_balance(self):
        rows=d.base_rows('joint',[1.2,2.8,4.6],[.2,1.2],[-.5,.5,1.5])
        self.assertEqual(dict(d.Counter(r['reference'] for r in rows)),dict(A=6,B=6,C=6,D=6))

if __name__=='__main__':unittest.main()
