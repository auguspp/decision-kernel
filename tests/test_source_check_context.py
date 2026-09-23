"""Bound collection records are input context, never source truth or permission."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import external_research_admission as gate
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import single_quick_contract as single
from decision_kernel.runtime.external_research_execution import ExternalResearchInputPacket
from test_external_research_admission import setup, checks


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a, **kw): raise AssertionError('Source-status projection must not access the network')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def prepared(parts=None):
    args = checks(*(parts or setup()))
    return ExternalResearchInputPacket.model_validate_json(args['input_raw']), args


def test_projection_preserves_query_window_body_binding_and_explicit_limits():
    packet, args = prepared(); before = canonical_hash(packet)
    value = gate.prompt_source_checks(packet, args['preflight_raw'])
    pf = json.loads(args['preflight_raw'])
    assert value['status'] == 'BOUND_SOURCE_PREFLIGHT_RECORDS_VALIDATED'
    assert value['preflight_source']['sha256'] == gate.digest(args['preflight_raw'])
    assert value['recorded_window'] == {k: pf[k] for k in ('started_at', 'finished_at', 'valid_until')}
    assert value['inventories'][0]['query_events'] == pf['inventories'][0]['query_events']
    assert value['reads'][1]['body_sha256'] == pf['reads'][1]['body_sha256']
    assert value['inventories'][0]['leads'][0]['body_id'] == 'update'
    assert 'not assertions that checks were not done' in value['interpretation']
    assert 'not certify source truth' in value['interpretation']
    assert 'not proof of no events' in value['interpretation']
    assert 'research_execution_allowed' not in value and 'evidence_artifacts' not in value
    assert canonical_hash(packet) == before


def test_no_free_form_notes_or_seed_publications_are_exported():
    parts = setup(); parts[1]['notes'] = 'SECRET-LIKE-NOTE-MUST-NOT-BE-PROJECTED'
    parts[1]['inventories'][0]['leads'][0]['relevance_note'] += ' DO-NOT-EXECUTE-ME'
    packet, args = prepared(parts)
    serialized = json.dumps(gate.prompt_source_checks(packet, args['preflight_raw']))
    assert 'SECRET-LIKE' not in serialized and 'DO-NOT-EXECUTE' not in serialized
    assert 'seed_publications' not in serialized and 'relevance_note' not in serialized


@pytest.mark.parametrize('damage', ['expired', 'body-failed', 'query-failed', 'query-missing',
                                   'missing-class', 'wrong-security', 'future-finish', 'provenance'])
def test_invalid_preflight_cannot_be_projected_as_completed(damage):
    parts = setup(); pf = parts[1]
    if damage == 'expired': pf['valid_until'] = pf['finished_at']
    elif damage == 'body-failed': pf['reads'][0]['succeeded'] = False
    elif damage == 'query-failed': pf['inventories'][0]['query_events'][0]['status'] = 'FAILED'
    elif damage == 'query-missing': pf['inventories'][0]['query_events'] = []
    elif damage == 'missing-class': pf['required_classes'][0]['id'] = 'OTHER_REPORT'
    elif damage == 'wrong-security': pf['security_id'] = 'SSE:999999'
    elif damage == 'future-finish': pf['finished_at'] = '2026-09-08T11:01:00Z'
    else: pf['provenance'] = 'MODEL_INFERRED'
    packet, args = prepared(parts)
    with pytest.raises(ValueError): gate.prompt_source_checks(packet, args['preflight_raw'])


@pytest.mark.parametrize('damage', ['changed-bytes', 'missing-binding', 'missing-marker', 'duplicate-marker'])
def test_exact_input_source_and_requirement_binding_cannot_be_bypassed(damage):
    packet, args = prepared(); raw = args['preflight_raw']
    if damage == 'changed-bytes': raw += b' '
    elif damage == 'missing-binding': packet = packet.model_copy(update={'source_refs': ()})
    elif damage == 'missing-marker': packet = packet.model_copy(update={'known_unknowns': ('business unknown',)})
    else: packet = packet.model_copy(update={'known_unknowns': (*packet.known_unknowns, packet.known_unknowns[0])})
    with pytest.raises(ValueError): gate.prompt_source_checks(packet, raw)


def test_empty_inventory_remains_scoped_success_not_no_events():
    parts = setup(); parts[1]['inventories'][0]['leads'] = [];parts[1]['required_classes'][1]['body_ids'] = []
    packet, args = prepared(parts); value = gate.prompt_source_checks(packet, args['preflight_raw'])
    assert value['inventories'][0]['leads'] == [] and value['inventories'][0]['query_events']
    assert 'No listed lead is not proof of no events' in value['interpretation']


def test_projection_is_stable_within_window_but_does_not_extend_validity():
    packet, args = prepared(); raw = args['preflight_raw']
    later = packet.model_copy(update={'research_cutoff': packet.research_cutoff + timedelta(minutes=1)})
    assert gate.prompt_source_checks(packet, raw) == gate.prompt_source_checks(later, raw)
    stale = packet.model_copy(update={'research_cutoff': packet.research_cutoff + timedelta(days=1)})
    with pytest.raises(ValueError): gate.prompt_source_checks(stale, raw)


def test_real_jiangxi_retained_check_is_visible_without_replaying_or_retiming_research():
    root = Path(__file__).parent / 'fixtures' / 'host_source_check_context'
    packet_raw = (root / 'input.json').read_bytes(); pf_raw = (root / 'preflight.json').read_bytes()
    packet = ExternalResearchInputPacket.model_validate_json(packet_raw)
    assert once.sha(packet_raw) == '2626a4237beb14f674ae0e304466558ad5011730054ef9318410e57efbe0c5db'
    assert once.blob(pf_raw) == 'f36f55f22029679c8b0256a52c1c9923a2f3429d'
    facts = gate.prompt_source_checks(packet, pf_raw)
    assert facts['preflight_source']['ref'] == '3b85b865ba61c2a29b24ff7981869363324d6d5c'
    inv = facts['inventories'][0]
    assert inv['planned_queries'] == ['CNINFO:600362:2026-03-27:2026-09-23:financial-report-corrections']
    assert inv['query_events'][0]['status'] == 'SUCCEEDED'
    assert 'b001090b6263ce3902c8a94e6fb2be906cd5e209' in inv['query_events'][0]['tool_reference']
    assert {c['id'] for c in facts['required_classes']} == {
        'FULL_ANNUAL_REPORT', 'FULL_INTERIM_REPORT', 'FINANCIAL_REPORT_CORRECTION_CHECK'}
    assert packet.research_cutoff.isoformat() == '2026-09-23T04:44:29.795878+00:00'
    assert once.sha((root / 'input.json').read_bytes()) == once.sha(packet_raw)
