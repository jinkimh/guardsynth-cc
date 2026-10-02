"""Evidence checks only: mechanical readiness, human receipt and policy are separate gates."""
import hashlib
import json

from guard_synth_eblc.speed_contract import parse_speed_contract


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def audit_row(row, contract=None, cnl_text=None, mapping=None, receipts=(), policies=()):
    """Receipts/policies must be real provenance records supplied by the coordinator, not predictions."""
    premises = row.get('speed_premises', {})
    accepted = row.get('accepted_stop_control', {})
    source = (premises.get('applicability') == 'TRUE' and premises.get('evidence_valid') is True
              and accepted.get('scope') == 'USER_CONFIRMED_DEVELOPMENT_STOP_CONTROL_ONLY'
              and bool(accepted.get('source_ref')))
    try:
        parse_speed_contract(contract)
        schema_ok = True
    except ValueError:
        schema_ok = False
    contract_ok = bool(schema_ok and contract and accepted.get('target_id')
                       and contract.get('clause_kind') == 'STOP_REQUIRED'
                       and contract.get('target_entity_id') == accepted.get('target_id')
                       and accepted.get('source_ref') in contract.get('source_refs', []))
    text_sha = hashlib.sha256(cnl_text.encode()).hexdigest() if cnl_text is not None else None
    mapping_ok = bool(contract_ok and mapping and text_sha
                      and mapping.get('text_sha256') == text_sha
                      and mapping.get('contract_sha256') == canonical_sha(contract)
                      and accepted.get('source_ref') in mapping.get('source_refs', []))
    version = contract.get('contract_version') if contract else None
    projection_version = (mapping or {}).get('semantic_projection_version', version)
    # Match exact scene AND exact reviewed bytes/version; unrelated entry approval cannot admit speed.
    def identity(record):
        return (record.get('candidate_digest') == row['candidate_digest']
                and record.get('source_binding_sha256') == canonical_sha(row)
                and record.get('contract_version') == version
                and record.get('semantic_projection_version', version) == projection_version
                and bool(record.get('provenance_ref')))
    human = any(identity(r) and r.get('status') == 'ACCEPTED'
                and r.get('receipt_kind') == 'HUMAN_CNL_FIDELITY'
                and r.get('cnl_text_sha256') == text_sha and text_sha is not None for r in receipts)
    policy = any(identity(p) and p.get('status') == 'AUTHORIZED'
                 and p.get('scope') == 'DEVELOPMENT_SPEED_SUPERVISION_ONLY'
                 and p.get('clause_kind') == (contract or {}).get('clause_kind')
                 and premises.get('motion_state') in p.get('allowed_motion_states', [])
                 and p.get('main_training_allowed') is False for p in policies)
    mechanical = source and contract_ok and mapping_ok
    checks = {'source_stop_premise': source, 'source_bound_contract': contract_ok,
              'cnl_hash_and_source_mapping': mapping_ok, 'mechanical_ready': mechanical,
              'human_cnl_receipt': human, 'research_policy_scope': policy}
    reasons = [name for name in ('source_stop_premise', 'source_bound_contract',
               'cnl_hash_and_source_mapping', 'human_cnl_receipt', 'research_policy_scope') if not checks[name]]
    return {'candidate_index': row['candidate_index'], 'clip_id': row['clip_id'],
            'candidate_digest': row['candidate_digest'], 'checks': checks,
            'training_eligible': mechanical and human and policy, 'reasons': reasons,
            'source_stop_premise_accepted': source, 'motion_state': premises.get('motion_state', 'UNKNOWN'),
            'source_binding_sha256': canonical_sha(row), 'cnl_text_sha256': text_sha,
            'semantic_projection_version': projection_version,
            'existing_conditional_contract_ref': row.get('existing_contract_ref'),
            'unresolved_source_fields': row.get('gaps', []),
            'main_training_allowed': False}
