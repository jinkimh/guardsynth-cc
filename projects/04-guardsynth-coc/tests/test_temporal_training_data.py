import copy
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import temporal_training_data as d


class TemporalTrainingDataTest(unittest.TestCase):
    def test_split_disjoint_and_size(self):
        sets = [set(range(*v)) for v in d.SPLITS.values()]
        self.assertEqual([len(s) * 24 for s in sets], [960, 240, 240])
        for i, a in enumerate(sets):
            for b in sets[i + 1:]:
                self.assertFalse(a & b)

    def test_boundary_and_stop_are_executable(self):
        for duration in d.DURATIONS:
            self.assertEqual(d.action_test(duration, 6000, 6000 + duration - 100), 'UNSAT')
            self.assertEqual(d.action_test(duration, 6000, 6000 + duration), 'SAT')
            self.assertEqual(d.action_test(duration, 6000, None), 'SAT')

    def test_records_and_balanced_labels(self):
        rows = list(d.records('validation'))
        self.assertEqual(len(rows), 240)
        self.assertEqual(len({r['id'] for r in rows}), 240)
        self.assertEqual(d.Counter(r['reference_action'] for r in rows), dict.fromkeys('ABCD', 60))
        for row in rows:
            action = row['action_tests'][row['reference_action']]
            self.assertTrue(action['enters'])
            self.assertEqual(action['eblc_status'], 'SAT')
            self.assertNotEqual(row['prompts']['P1'], row['prompts']['P2'])
            self.assertEqual(row['cnl'], d.t.render(row['contract']))
            self.assertNotIn('reference_action', row['prompts']['P2'])

    def test_missing_gate_would_be_detected(self):
        raw = copy.deepcopy(d.t.lower(d.t.contract(.5)))
        raw['clauses'][0]['formula'] = d.t.lit(True)
        wrong = d.t.compile_core_model(d.t.parse_core_model(raw))
        status = d.solve_assignment(wrong, {('clear_ms', None): 6000,
            ('entry_ms', None): 6400, ('enters', None): True})['status']
        self.assertNotEqual(status, d.action_test(500, 6000, 6400))

    def test_refuses_overwrite(self):
        with self.assertRaises(FileExistsError):
            d.prepare(ROOT)


if __name__ == '__main__':
    unittest.main()
