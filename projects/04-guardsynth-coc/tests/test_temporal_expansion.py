from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import train_temporal_expansion as e


class ExpansionTest(unittest.TestCase):
    def test_six_conditions_and_budget(self):
        self.assertEqual(len(e.ARMS), 6)
        self.assertEqual(960 // 2 // 8 * 3, 180)
        self.assertEqual(6 * 3 * 180, 3240)

    def test_scoring_uses_times_not_positional_role(self):
        row = next(e.d.records('test'))
        scene = e.d.t.world.TemporalScene(**{**row['scene'], 'candidates': tuple(
            e.d.t.world.TemporalCandidate(**c) for c in row['scene']['candidates'])})
        example = e.d.t.world.TemporalExample(scene, .5, 'short', '', '', '', 'Z', 'test')
        self.assertFalse(e.score(example, 'INVALID')['valid'])
        for c in scene.candidates:
            self.assertEqual(e.score(example, c.label)['hold_violation'],
                             c.entry_time is not None and c.entry_time < scene.clear_time)
        self.assertEqual(e.score(example, 'A'), e.score(replace(example, target='A'), 'A'))

    def test_heldout_and_paraphrase_inputs(self):
        a = e.examples('test', 'P1', 42)
        b = e.examples('paraphrase', 'P1', 42)
        c = e.examples('paraphrase', 'P2', 42)
        u = e.examples('unseen_duration', 'P2', 42)
        self.assertEqual(len(a), 240)
        self.assertNotEqual(a[0].rich_coc_text, b[0].rich_coc_text)
        self.assertEqual(b[0].rich_coc_text, c[0].rich_coc_text)
        self.assertEqual({x.required_clear_duration for x in u}, {.8, 1.8})
        for x in u:
            self.assertTrue(e.score(x, x.target)['correct'])

    def test_shuffled_control_only_training(self):
        a = e.examples('train', 'NATURAL_GUARD', 42)
        b = e.examples('train', 'SHUFFLED_GUARD', 42)
        self.assertEqual([x.target for x in a], [x.target for x in b])
        self.assertGreater(sum(x.guard_text != y.guard_text for x,y in zip(a,b)), 0)
        self.assertEqual(e.examples('test', 'NATURAL_GUARD', 42),
                         e.examples('test', 'SHUFFLED_GUARD', 42))

    def test_incomplete_pairs_rejected(self):
        with self.assertRaises(ValueError):
            e.metrics([{'scene_id': 1, 'contract_level': 'short'}])


if __name__ == '__main__':
    unittest.main()
