import unittest
from analyze_temporal_secondary import measure, summarize


class SecondaryMetricsTest(unittest.TestCase):
    def row(self):
        return {'required_clear_ms':500, 'contract_level':'short', 'scene':{'clear_time':2.,
            'candidates':[{'label':'A','entry_time':1.5,'progress':110},
                          {'label':'B','entry_time':2.5,'progress':100},
                          {'label':'C','entry_time':3.5,'progress':85},
                          {'label':'D','entry_time':None,'progress':0}]}}

    def test_boundary(self):
        r = measure(self.row(),'B','test')
        self.assertTrue(r['safe']); self.assertEqual(r['early_entry_ms'],0)
        self.assertEqual(r['gated_progress_loss_fraction'],0)

    def test_unsafe_fast_is_not_rewarded(self):
        r = measure(self.row(),'A','test')
        self.assertEqual(r['gated_progress_loss_fraction'],1)
        self.assertIsNone(r['safe_progress_loss_units'])
        self.assertEqual(r['early_entry_ms'],1000)
        self.assertEqual(r['occupancy_early_ms'],500)

    def test_safe_but_suboptimal(self):
        r = measure(self.row(),'C','test')
        self.assertEqual(r['safe_progress_loss_units'],15)
        self.assertAlmostEqual(r['gated_progress_loss_fraction'],.15)

    def test_invalid_not_stop(self):
        r = measure(self.row(),'INVALID','test')
        self.assertFalse(r['valid']); self.assertFalse(r['unnecessary_stop'])
        self.assertEqual(r['gated_progress_loss_fraction'],1)
        self.assertIsNone(r['early_entry_ms'])

    def test_stop(self):
        r = measure(self.row(),'D','test')
        self.assertTrue(r['unnecessary_stop']); self.assertEqual(r['safe_progress_loss_units'],100)

    def test_no_violation_is_undefined_conditional(self):
        s = summarize([measure(self.row(),'B','test')])
        self.assertIsNone(s['early_ms_per_violation']); self.assertEqual(s['early_ms_per_entry'],0)

    def test_unseen_transform_no_source_mutation(self):
        row = self.row(); r = measure(row,'B','unseen_duration')
        self.assertEqual(r['threshold_ms'],2800); self.assertEqual(r['entry_ms'],2800)
        self.assertEqual(row['scene']['candidates'][1]['entry_time'],2.5)

    def test_wait_violation_and_one_ms_boundary(self):
        row = self.row(); row['scene']['candidates'][1]['entry_time']=2.499
        r = measure(row,'B','test')
        self.assertTrue(r['release_wait_violation']); self.assertFalse(r['occupied_entry'])
        self.assertEqual(r['early_entry_ms'],1)

    def test_only_stop_feasible(self):
        row = self.row(); row['required_clear_ms']=5000
        r = measure(row,'D','test')
        self.assertFalse(r['unnecessary_stop']); self.assertIsNone(r['gated_progress_loss_fraction'])
        self.assertIsNone(summarize([r])['unnecessary_stop_rate'])


if __name__ == '__main__': unittest.main()
