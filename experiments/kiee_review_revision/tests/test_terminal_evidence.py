import importlib.util
from pathlib import Path
import unittest

MODULE=Path(__file__).resolve().parents[1]/'audit_terminal_evidence.py'
class TerminalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(),'terminal evidence audit absent')
        spec=importlib.util.spec_from_file_location('terminal_audit',MODULE)
        self.api=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.api)
    def test_complete_state_retains_multiple_reasons(self):
        output='\n'.join('Formula is '+('satisfied.' if b else 'NOT satisfied.') for b in [True,False,True,False,True,False])
        self.assertEqual(self.api.parse_terminal(output),['OVERLAPPING_OBLIGATION','ACTIVE_RELEASE_UNKNOWN'])
    def test_incomplete_solver_output_rejected(self):
        with self.assertRaises(ValueError):self.api.parse_terminal('Formula is satisfied.')
    def test_unreachable_completion_rejected(self):
        with self.assertRaises(ValueError):self.api.parse_terminal('\n'.join(['Formula is NOT satisfied.']*6))
if __name__=='__main__':unittest.main()
