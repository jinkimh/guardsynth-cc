"""Single-decision qualitative speed contracts; no scene or normative inference."""

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json

from .action_contract import IDENTIFIER, binary, conjunction, literal, neg, var
from .core_ir import parse_core_model
from .cnl_renderer import CNLClause, CNLDocument

VERSION = 'eblc-speed-contract-v0.1'
ACTIONS = ('MAINTAIN_SPEED', 'DECELERATE', 'STOP_OR_WAIT', 'START_OR_ACCELERATE')
KINDS = ('SPEED_REDUCTION_REQUIRED', 'STOP_REQUIRED')
VERDICTS = ('UNRESOLVED', 'EXCLUDED', 'NOT_EXCLUDED_BY_THIS_CLAUSE')


@dataclass(frozen=True)
class SpeedContract:
    raw: dict


def parse_speed_contract(raw):
    fields = {'contract_version', 'contract_id', 'subject_id', 'target_entity_id', 'predicate_id',
              'clause_kind', 'rule_ref', 'source_refs', 'claim_scope'}
    if not isinstance(raw, dict) or set(raw) != fields:
        raise ValueError('invalid speed contract fields')
    if (raw['contract_version'] != VERSION or raw['clause_kind'] not in KINDS
            or raw['claim_scope'] != 'CONDITIONAL_SINGLE_DECISION_NOT_VEHICLE_SAFETY'):
        raise ValueError('unsupported speed version/kind/scope')
    for field in ('contract_id', 'subject_id', 'predicate_id'):
        if not isinstance(raw[field], str) or not IDENTIFIER.fullmatch(raw[field]):
            raise ValueError('invalid speed identifier')
    if raw['target_entity_id'] is not None and (
            not isinstance(raw['target_entity_id'], str) or not IDENTIFIER.fullmatch(raw['target_entity_id'])):
        raise ValueError('invalid speed target')
    refs = raw['source_refs']
    if (not isinstance(refs, list) or not refs or any(not isinstance(r, str) or not r.strip() for r in refs)
            or len(refs) != len(set(refs)) or raw['rule_ref'] not in refs):
        raise ValueError('unbound speed source/rule reference')
    return SpeedContract(deepcopy(raw))


def eq(name, value, enum=None):
    return binary('eq', var(name), literal(value, enum))


def lower_speed_contract(contract):
    raw = parse_speed_contract(contract.raw).raw
    refs = raw['source_refs']
    declarations, clauses = [], []

    def declare(name, enum=None, values=()):
        declarations.append({'name': name, 'sort': 'ENUM' if enum else 'BOOL', 'time_varying': True,
            'enum_name': enum, 'enum_values': list(values), 'unit': None, 'frame': None, 'source_refs': refs})

    def clause(cid, formula):
        clauses.append({'id': cid, 'kind': 'INVARIANT', 'enforcement': 'INITIAL',
                        'formula': formula, 'source_refs': refs, 'description': 'Single speed-clause semantics: ' + cid})

    declare('motion', 'Motion', ('MOVING', 'STATIONARY', 'UNKNOWN'))
    declare('applicability', 'Truth', ('TRUE', 'FALSE', 'UNKNOWN', 'CONFLICT'))
    declare('evidence_valid')
    declare('action', 'SpeedAction', ACTIONS)
    known = conjunction(var('evidence_valid'), neg(eq('motion', 'UNKNOWN', 'Motion')),
                        {'op': 'or', 'args': [eq('applicability', t, 'Truth') for t in ('TRUE', 'FALSE')]})
    excluded = {'MAINTAIN_SPEED', 'START_OR_ACCELERATE'}
    if raw['clause_kind'] == 'STOP_REQUIRED':
        excluded.add('DECELERATE')
    gates = []
    for action in ACTIONS:
        name = action.lower() + '_verdict'
        declare(name, 'SpeedVerdict', VERDICTS)
        supported = known
        if raw['clause_kind'] == 'SPEED_REDUCTION_REQUIRED' or action in ('MAINTAIN_SPEED', 'DECELERATE'):
            supported = conjunction(known, eq('motion', 'MOVING', 'Motion'))
        value = {'op': 'ite', 'condition': conjunction(eq('applicability', 'TRUE', 'Truth'), literal(action in excluded)),
                 'then': literal('EXCLUDED', 'SpeedVerdict'),
                 'else': literal('NOT_EXCLUDED_BY_THIS_CLAUSE', 'SpeedVerdict')}
        clause(name, binary('eq', var(name), {'op': 'ite', 'condition': supported, 'then': value,
                                            'else': literal('UNRESOLVED', 'SpeedVerdict')}))
        gates.append(binary('implies', eq('action', action, 'SpeedAction'), neg(eq(name, 'EXCLUDED', 'SpeedVerdict'))))
    clause('speed_action_gate', conjunction(*gates))
    # Core requires >=2 frames. Only INITIAL is constrained; frame 1 is padding, not a prediction.
    core = {'grammar_version': 'eblc-core-v0.1', 'model_id': raw['contract_id'], 'horizon': 2,
            'source_refs': refs, 'claim_scope': raw['claim_scope'], 'declarations': declarations,
            'clauses': clauses, 'queries': [{'id': 'base_consistency', 'formula': literal(True),
                'expected': 'SAT', 'classification': 'CONSISTENCY', 'source_refs': refs,
                'description': 'Non-vacuous conditional speed model.'}]}
    parse_core_model(core)
    return core


def render_speed_contract(contract):
    raw = parse_speed_contract(contract.raw).raw
    refs = tuple(raw['source_refs'])
    excluded = 'MAINTAIN_SPEED and START_OR_ACCELERATE'
    if raw['clause_kind'] == 'STOP_REQUIRED':
        excluded = 'MAINTAIN_SPEED, DECELERATE and START_OR_ACCELERATE'
    stationary = ('For STATIONARY motion this reduction clause is unsupported: every verdict is UNRESOLVED.'
                  if raw['clause_kind'] == 'SPEED_REDUCTION_REQUIRED' else
                  'For STATIONARY motion, MAINTAIN_SPEED and DECELERATE are UNRESOLVED. '
                  'With valid TRUE applicability, START_OR_ACCELERATE is EXCLUDED and STOP_OR_WAIT is not excluded by this clause.')
    clauses = [CNLClause('speed.identity',
        f"Contract {raw['contract_id']} ({raw['contract_version']}) concerns subject {raw['subject_id']}, "
        f"target {raw['target_entity_id'] or 'UNBOUND'}, predicate {raw['predicate_id']}, "
        f"kind {raw['clause_kind']}, rule {raw['rule_ref']}, scope {raw['claim_scope']}. "
        'This is one decision, not lifecycle, metric stopping assurance or certified scene applicability.',
        tuple('$.' + k for k in raw if k != 'source_refs'), refs),
        CNLClause('speed.actions',
        'MAINTAIN_SPEED maintains moving speed, not stationary waiting. DECELERATE reduces speed without choosing a full stop. '
        'STOP_OR_WAIT begins deceleration intended to stop when moving, or continues waiting when stationary. '
        'START_OR_ACCELERATE starts when stationary or increases speed when moving. '
        'Excluding DECELERATE under a stop obligation does not prohibit deceleration intended to stop.', ('$.clause_kind',), refs),
        CNLClause('speed.gate',
        f'For MOVING motion with valid TRUE applicability of this speed obligation, {excluded} are EXCLUDED. '
        'Other actions are not excluded by this clause alone. ' + stationary + ' '
        'For supported motion/action pairs, valid FALSE applicability excludes no action by this clause alone. '
        'UNKNOWN motion, UNKNOWN or CONFLICT applicability, or invalid evidence makes every verdict UNRESOLVED. '
        'An EXCLUDED action cannot be selected under this contract. UNRESOLVED is not STOP gold. '
        'Neither UNRESOLVED nor not-excluded certifies appropriateness, overall permission, safety or nominal progress. '
        'Entry-clearance evidence does not establish speed applicability. Magnitude and other obligations require separate evidence.',
        ('$.clause_kind', '$.predicate_id', '$.rule_ref'), refs),
        CNLClause('speed.sources', 'Declared sources: ' + ', '.join(refs) + '.', ('$.source_refs',), refs)]
    text = '\n'.join(f'[{c.clause_id}] {c.text}' for c in clauses) + '\n'
    digest = lambda b: hashlib.sha256(b).hexdigest()
    return CNLDocument('eblc-speed-cnl-renderer-v0.1', 'EBLC-SPEED-CNL-EN-v0.1', 'SPEED_CONTRACT',
        raw['contract_id'], text, tuple(clauses), tuple(sorted({p for c in clauses for p in c.field_paths})), (),
        digest(json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()), digest(text.encode()))
