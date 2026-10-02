import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
from run_temporal_cost_queue import upstream_state


class CostQueueTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)

    def write(self, result, manifest):
        (self.path / 'RESULT.json').write_text(json.dumps(result))
        (self.path / 'RUN_MANIFEST.json').write_text(json.dumps(manifest))

    def test_waits_for_both_completion_records(self):
        self.assertEqual(upstream_state(self.path), 'WAITING_UPSTREAM_SNAPSHOT')
        self.write({'status': 'COMPLETE'}, {'status': 'RUNNING'})
        self.assertEqual(upstream_state(self.path), 'WAITING_UPSTREAM_COMPLETION')

    def test_failed_parent_stops(self):
        self.write({'status': 'FAILED'}, {'status': 'RUNNING'})
        with self.assertRaises(RuntimeError):
            upstream_state(self.path)

    def test_incomplete_budget_rejected(self):
        self.write({'status': 'COMPLETE', 'fits': 3, 'optimizer_updates': 540}, {'status': 'COMPLETE'})
        with self.assertRaises(ValueError):
            upstream_state(self.path)

    def test_negative_scientific_verdict_is_not_execution_failure(self):
        self.write({'status': 'COMPLETE', 'fits': 18, 'optimizer_updates': 3240,
                    'verdict': 'NOT_SUPPORTED'}, {'status': 'COMPLETE'})
        self.assertEqual(upstream_state(self.path), 'READY')


if __name__ == '__main__':
    unittest.main()
