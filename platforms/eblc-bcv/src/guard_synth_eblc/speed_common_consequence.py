"""Proposed skeptical consequences across physical motion alternatives, separate from v0.1."""
from copy import deepcopy

from .action_contract import conjunction, neg
from .core_ir import parse_core_model
from .smt_compiler import compile_core_model, check_queries
from .speed_contract import ACTIONS, eq, lower_speed_contract

VERSION = 'eblc-speed-common-consequence-v0.1-proposal'


def derive(contract, applicability, evidence_valid):
    if contract.raw['clause_kind'] != 'STOP_REQUIRED':
        raise ValueError('proposal is scoped to STOP_REQUIRED only')
    core = lower_speed_contract(contract)
    core['queries'] = []
    def query(qid, formula):
        core['queries'].append({'id': qid, 'formula': formula, 'expected': 'SAT',
            'classification': 'EXAMPLE', 'source_refs': core['source_refs'], 'description': qid})
    for motion in ('MOVING', 'STATIONARY', 'UNKNOWN'):
        premise = conjunction(eq('motion', motion, 'Motion'), eq('applicability', applicability, 'Truth'),
                              eq('evidence_valid', evidence_valid))
        query(motion + '_consistent', premise)
        for action in ACTIONS:
            excluded = eq(action.lower() + '_verdict', 'EXCLUDED', 'SpeedVerdict')
            query(motion + '_' + action + '_excluded', conjunction(premise, excluded))
            query(motion + '_' + action + '_counterexample', conjunction(premise, neg(excluded)))
    probe = check_queries(compile_core_model(parse_core_model(core)))
    observed = {r['query_id']: r['status'] for r in probe['results']}
    if any(observed[m + '_consistent'] != 'SAT' for m in ('MOVING', 'STATIONARY', 'UNKNOWN')):
        raise ValueError('vacuous or unknown branch support')
    excluded = [a for a in ACTIONS if all(observed[m+'_'+a+'_counterexample']=='UNSAT'
                and observed[m+'_'+a+'_excluded']=='SAT' for m in ('MOVING','STATIONARY'))]
    # A proof artifact with the solver-observed expectations, not an approval or source observation.
    proof = deepcopy(core)
    for q in proof['queries']: q['expected'] = observed[q['id']]
    return {'derivation_version': VERSION, 'status': 'PROPOSAL_NOT_ADMITTED',
        'physical_alternatives': ['MOVING', 'STATIONARY'], 'observed_motion': 'UNKNOWN',
        'motion_inferred': False, 'excluded_by_all_supported_branches': excluded,
        'positive_permission_inferred': False, 'replaces_v01_unknown_semantics': False,
        'legacy_unknown_excluded': [a for a in ACTIONS if observed['UNKNOWN_'+a+'_excluded']=='SAT'],
        'proof_core': proof}
