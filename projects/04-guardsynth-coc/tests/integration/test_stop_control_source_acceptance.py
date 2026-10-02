"""Two scoped source confirmations cannot become motion, red-light or ACTION gold."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
sys.path.insert(0, str(ROOT / 'projects/04-guardsynth-coc/experiments/paper1_cnl_learning'))
import accept_stop_control_sources as accept


class StopSourceAcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((accept.SOURCE / 'source_speed_bindings.json').read_text())['records']

    def note(self, row):
        return {**{k: row[k] for k in ('candidate_index', 'candidate_digest', 'event_timestamp_us')},
                'verbatim': accept.STATEMENTS[row['candidate_index']], 'source_type': 'USER_CONVERSATION',
                'authenticated_reviewer_attestation': False}

    def test_provenance_identity_and_scope_rejected_on_drift(self):
        row = next(r for r in self.rows if r['candidate_index'] == 68)
        for key, value in [('verbatim', '적색 신호 확인'), ('source_type', 'JONH_AUTHENTICATED'),
                           ('event_timestamp_us', 0), ('candidate_digest', 'other'),
                           ('authenticated_reviewer_attestation', True)]:
            note = self.note(row)
            note[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                accept.apply_confirmation(row, note, 'ref')
        other = next(r for r in self.rows if r['candidate_index'] == 52)
        with self.assertRaises(ValueError):
            accept.apply_confirmation(other, self.note(row), 'ref')

    def test_source_scope_does_not_certify_other_fields(self):
        row = next(r for r in self.rows if r['candidate_index'] == 68)
        snapshot = deepcopy(row)
        result = accept.apply_confirmation(row, self.note(row), 'ref')
        self.assertEqual(row, snapshot)
        self.assertEqual(result['speed_premises'], {'motion_state': 'UNKNOWN', 'applicability': 'TRUE', 'evidence_valid': True})
        for key in ('red_light_certified', 'motion_certified', 'release_certified', 'cascade_physical_identity_certified'):
            self.assertFalse(result['accepted_stop_control'][key])
        self.assertEqual(result['target_binding'], row['target_binding'])
        self.assertEqual(result['motion_evidence'], row['motion_evidence'])
        self.assertFalse(result['training_allowed'])

    def test_complete_run_cnl_smt_and_no_action_inputs(self):
        read = Path.read_bytes
        def guarded(path):
            if any(s in str(path) for s in ('speed-action-intake', 'speed-action-submission', 'speed-action-clarification')):
                raise AssertionError('ACTION answer input forbidden')
            return read(path)
        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, 'read_bytes', guarded):
            output = Path(tmp) / 'acceptance-001'
            result = accept.execute(output)
            self.assertEqual((result['actual_smt_queries'], result['hypothetical_smt_queries']), (24, 48))
            notes = json.loads((output / 'confirmation.json').read_text())
            self.assertIsNone(notes['utterance_timestamp'])
            self.assertFalse(notes['jonh_new_attestation'])
            self.assertEqual([n['verbatim'] for n in notes['records']], list(accept.STATEMENTS.values()))
            updated = json.loads((output / 'source_speed_bindings.json').read_text())['records']
            for old, new in zip(self.rows, updated):
                if old['candidate_index'] not in accept.STATEMENTS:
                    self.assertEqual(old, new)
                    continue
                n = old['candidate_index']
                contract = json.loads((output / f'candidate_{n}_contract.json').read_text())
                text, mapping = accept.render_bound_cnl(contract, new)
                self.assertEqual(text, (output / f'candidate_{n}_cnl.txt').read_text())
                self.assertEqual(mapping['text_sha256'], accept.prior.sha(text.encode()))
                self.assertIn('motion=UNKNOWN', text)
                self.assertIn('정지 목적 감속을 금지하지 않는다', text)
                if n == 68:
                    self.assertIn('red-light 주장은 별개이며 확인되지 않았다', text)
                bad = deepcopy(new)
                bad['speed_premises']['motion_state'] = 'STATIONARY'
                with self.assertRaises(ValueError): accept.render_bound_cnl(contract, bad)
                with self.assertRaises(ValueError): accept.bound_core(contract, bad)
                core = accept.bound_core(contract, new)
                core['clauses'] = [c for c in core['clauses'] if c['id'] != 'pinned_source_report_facts']
                checks = accept.e.check_queries(accept.e.compile_core_model(accept.e.parse_core_model(core)))
                self.assertLess(checks['matches_expected'], checks['query_count'])
            manifest = json.loads((output / 'RUN_MANIFEST.json').read_text())
            for group in ('input_hashes', 'code_hashes', 'output_hashes'):
                for path, digest in manifest[group].items():
                    self.assertEqual(accept.prior.sha(((output if group == 'output_hashes' else ROOT) / path).read_bytes()), digest)
            with self.assertRaises(FileExistsError): accept.execute(output)


if __name__ == '__main__':
    unittest.main()
