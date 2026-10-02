"""Strict speed contracts, shared Core semantics and deterministic CNL boundaries."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
sys.path[:0] = [str(ROOT), str(ROOT / 'platforms/eblc-bcv/src')]
from cli.solver_runtime import configure_project_z3
configure_project_z3(ROOT)
from guard_synth_eblc.speed_contract import parse_speed_contract, lower_speed_contract, render_speed_contract
from guard_synth_eblc.smt_compiler import compile_core_model, solve_assignment
from guard_synth_eblc.core_ir import parse_core_model


def fixture():
    return {'contract_version': 'eblc-speed-contract-v0.1', 'contract_id': 'speed_fixture',
            'subject_id': 'ego', 'target_entity_id': None, 'predicate_id': 'stop_required',
            'clause_kind': 'STOP_REQUIRED', 'rule_ref': 'synthetic:policy', 'source_refs': ['synthetic:policy'],
            'claim_scope': 'CONDITIONAL_SINGLE_DECISION_NOT_VEHICLE_SAFETY'}


class SpeedContractTest(unittest.TestCase):
    def test_strict_fields_policy_and_source_refs(self):
        for key, value in (('contract_version', 'eblc-action-contract-v0.1'), ('clause_kind', 'ACCELERATE_REQUIRED'),
                           ('contract_id', 'not an id'), ('target_entity_id', 2), ('extra', True),
                           ('source_refs', []), ('source_refs', ['synthetic:policy'] * 2),
                           ('rule_ref', 'missing'), ('claim_scope', 'SCENE_SAFE')):
            raw = fixture()
            raw[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_speed_contract(raw)

    def test_mutation_revalidated_and_source_isolated(self):
        raw = fixture()
        contract = parse_speed_contract(raw)
        raw['clause_kind'] = 'WRONG'
        self.assertEqual(contract.raw['clause_kind'], 'STOP_REQUIRED')
        contract.raw['clause_kind'] = 'WRONG'
        with self.assertRaises(ValueError):
            lower_speed_contract(contract)
        with self.assertRaises(ValueError):
            render_speed_contract(contract)

    def test_cnl_fields_sources_and_stop_intention(self):
        for kind in ('STOP_REQUIRED', 'SPEED_REDUCTION_REQUIRED'):
            raw = fixture()
            raw['clause_kind'] = kind
            with patch('guard_synth_eblc.smt_compiler.compile_core_model', side_effect=AssertionError('renderer called solver')):
                document = render_speed_contract(parse_speed_contract(raw))
            self.assertEqual(set(document.covered_paths), {'$.' + k for k in raw})
            self.assertEqual(document.omitted_paths, ())
            self.assertIn('UNBOUND', document.text)
            self.assertIn('UNKNOWN or CONFLICT', document.text)
            self.assertIn('does not prohibit deceleration intended to stop', document.text)
            self.assertIn('not-excluded certifies', document.text)
            self.assertTrue(all(c.source_refs == ('synthetic:policy',) for c in document.clauses))
            self.assertEqual(document, render_speed_contract(parse_speed_contract(raw)))

    def test_gate_mutation_reproduces_excluded_action(self):
        core = lower_speed_contract(parse_speed_contract(fixture()))
        assignments = {('motion', 0): 'MOVING', ('applicability', 0): 'TRUE',
                       ('evidence_valid', 0): True, ('action', 0): 'DECELERATE'}
        def status(model):
            return solve_assignment(compile_core_model(parse_core_model(model)), assignments)['status']
        self.assertEqual(status(core), 'UNSAT')
        mutant = deepcopy(core)
        mutant['clauses'] = [c for c in mutant['clauses'] if c['id'] != 'speed_action_gate']
        self.assertEqual(status(mutant), 'SAT')
        assignments[('action', 0)] = 'STOP_OR_WAIT'
        self.assertEqual(status(core), 'SAT')

    def test_padding_frame_has_no_future_policy_claim(self):
        core = lower_speed_contract(parse_speed_contract(fixture()))
        self.assertEqual(core['horizon'], 2)
        self.assertTrue(all(c['enforcement'] == 'INITIAL' for c in core['clauses']))
        # The current-frame stop restriction must not certify a future decision.
        assignments = {('motion', 1): 'MOVING', ('applicability', 1): 'TRUE',
                       ('evidence_valid', 1): True, ('action', 1): 'START_OR_ACCELERATE'}
        self.assertEqual(solve_assignment(compile_core_model(parse_core_model(core)), assignments)['status'], 'SAT')


if __name__ == '__main__':
    unittest.main()
