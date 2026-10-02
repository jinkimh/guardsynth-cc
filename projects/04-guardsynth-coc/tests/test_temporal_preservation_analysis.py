import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import temporal_preservation as t
import analyze_temporal_preservation as a

class PreservationAnalysisTest(unittest.TestCase):
    def fixture(self,base,weak):
        cfg=json.loads(t.CONFIG.read_text());cfg['test_scenes']=2
        cfg['uncertainty']['bootstrap_replicates']=20
        protocol=base/'protocol';protocol.mkdir();(protocol/'protocol.json').write_text(json.dumps(cfg))
        run=base/'run';run.mkdir()
        for seed in cfg['seeds']:
            for arm in cfg['arms']:
                out=run/f'{arm.lower()}-seed{seed}';out.mkdir()
                for split in cfg['evaluation']:
                    rows=[]
                    for i in range(4):
                        violation=(weak or arm=='P0') and i%2==0
                        rows.append({'seed':seed,'scene_id':i//2,'contract_level':str(i%2),'semantic_cluster':str(i//2),
                                     'guard_violation':violation,'safe_goal_complete':not violation,'deadlock':False,
                                     'correct':not violation,'valid':True})
                    (out/(split+'.jsonl')).write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
        return run,protocol
    def test_equal_weak_controls_fail(self):
        with tempfile.TemporaryDirectory() as d:
            result=a.summarize(*self.fixture(Path(d),True))
            for verdict in result['verdicts'].values():
                self.assertTrue(verdict['checks']['P2_vs_P1'])
                self.assertFalse(verdict['checks']['P1_level'])
                self.assertEqual(verdict['point_criteria'],'NOT_SUPPORTED')
    def test_preserved_strong_controls_and_uncertainty(self):
        with tempfile.TemporaryDirectory() as d:
            result=a.summarize(*self.fixture(Path(d),False))
            for verdict in result['verdicts'].values():
                self.assertEqual(verdict['point_criteria'],'SUPPORTED_ON_REUSED_TEMPLATES')
                self.assertEqual(verdict['formal_noninferiority'],'NOT_CLAIMED')
            ci=result['results']['new_seed_confirmation']['paired_differences']['P2-P0']['guard_violation_rate']['template_cluster_bootstrap_95ci']
            self.assertEqual(ci,[-.5,-.5])
    def test_missing_evaluation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            run,protocol=self.fixture(Path(d),False)
            (run/'p2-seed123/new_seed_confirmation.jsonl').write_text('')
            with self.assertRaises(ValueError):a.summarize(run,protocol)
    def test_immutable_output_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            run,protocol=self.fixture(Path(d),False)
            for base in (run,protocol):
                files={str(p.relative_to(base)):t.sha(p) for p in base.rglob('*') if p.is_file()}
                (base/'RUN_MANIFEST.json').write_text(json.dumps({'status':'COMPLETE','output_hashes':files}))
            a.verify_completed_run(run,protocol)
            (run/'p2-seed123/new_seed_confirmation.jsonl').write_text('')
            with self.assertRaises(ValueError):a.verify_completed_run(run,protocol)

if __name__=='__main__':unittest.main()
