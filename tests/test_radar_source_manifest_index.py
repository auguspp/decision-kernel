"""Bounded index and lossless existing sidecar; synthetic only, no new state."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import institutional_radar_reading as shared

AT = '2026-10-01T19:30:00+00:00'


def sample(tmp_path):
    api = SimpleNamespace(calls=0, max_calls=252)
    col = delivery.Collector(api, 'a' * 40, tmp_path, now=lambda: AT)
    statuses = {}
    for kind in ('institutional', 'concept', 'concept_detail'):
        details = {name: col.retain(f'details/test/{kind}/{name}', name.encode())
                   for name in ['observation.json', 'index.html', *[f'response-{i}.json' for i in range(1, 16)]]}
        statuses[kind] = {'status': {'institutional': 'VERIFIED_SAVED_INSTITUTIONAL_SOURCE',
                           'concept': 'VERIFIED_SAVED_CONCEPT_SOURCE',
                           'concept_detail': 'VERIFIED_SAVED_CONCEPT_DETAIL'}[kind],
                          'details': details, 'archive': {'synthetic': True},
                          'replay': {'network_calls': 0}, 'coverage': {'synthetic': True},
                          'market_session': '2026-09-18', 'projection_hash': 'b' * 64}
    statuses['failed'] = {'status': 'UNAVAILABLE_OR_REJECTED', 'failed_stage': 'PAYLOAD_REPLAY',
                          'error_type': 'ValueError', 'meaning': 'NOT_ZERO_ACTIVITY'}
    projection = {'source_status': statuses}
    value = {'projection': projection, 'projection_hash': canonical_hash(projection)}
    company_ref = col.retain('details/radar/company-reading.json', model.json_bytes(value))
    index_ref = col.retain('details/radar/index.html', b'synthetic')
    reading = {'status': 'READ_OK_WITH_SOURCE_GAPS', 'source_status': statuses,
               'projection_hash': value['projection_hash'],
               'details': {'company_reading': company_ref, 'index': index_ref},
               'coverage': dict(distinct_companies=0, sector_companies=0,
                                institutional_companies=0, overlap_companies=0)}
    research = {'handoffs': {'active': []}, 'radar_discovery': reading}
    baseline = model.assemble(code_commit='a'*40, checked_at=AT, check_started_at=AT,
                              lanes={}, research=research, capabilities=[], refresh_identity={})
    return col, baseline, statuses


def test_original_small_shape_remains_exact(tmp_path):
    col, base, full = sample(tmp_path)
    out = shared._assemble(col, base, base['research'])
    status = out['research']['radar_discovery']
    assert 'source_status_scope' not in status
    assert status['source_status'] == shared.saved_source_status(col, status) == full


def test_actual_size_overflow_uses_existing_manifest_without_dropping_bytes(tmp_path):
    col, base, full = sample(tmp_path)
    before_files = dict(col.files)
    research = deepcopy(base['research'])
    savings = len(model.json_bytes(full)) - len(model.json_bytes(shared._source_status_index(full)))
    assert savings > 5000
    research['capacity_test_only'] = 'x' * (192*1024 - len(model.read_package_bytes(base)) + 1000)
    before = deepcopy(research)
    with pytest.raises(ValueError, match='bounded index size'):
        model.assemble(code_commit='a'*40, checked_at=AT, check_started_at=AT,
                       lanes={}, research=research, capabilities=[], refresh_identity={})
    out = shared._assemble(col, base, research)
    assert research == before
    assert len(model.read_package_bytes(out)) <= 192*1024
    status = out['research']['radar_discovery']
    assert status['source_status_scope'] == shared.SOURCE_STATUS_SCOPE
    assert status['source_status']['failed'] == full['failed']
    assert shared.saved_source_status(col, status) == full
    assert all(col.files[path] == raw for path, raw in before_files.items())
    assert out['lanes'] == base['lanes'] and out['pending'] == base['pending']
    assert all(out[k] == v for k,v in model.AUTHORITY.items())
    # Already compacted roots remain readable; the full descriptors are not
    # silently replaced by the summary in the existing company projection.
    assert shared._assemble(col, out, out['research'])['research'] == out['research']


@pytest.mark.parametrize('kind', ['bytes', 'projection', 'summary', 'scope'])
def test_summary_or_manifest_mismatch_fails_closed(tmp_path, kind):
    col, base, full = sample(tmp_path)
    reading = deepcopy(base['research']['radar_discovery'])
    reading['source_status'] = shared._source_status_index(full)
    reading['source_status_scope'] = shared.SOURCE_STATUS_SCOPE
    if kind == 'bytes':
        col.files[reading['details']['company_reading']['read_path']] += b' '
    elif kind == 'projection':
        reading['projection_hash'] = '0' * 64
    elif kind == 'scope':
        reading['source_status_scope'] = 'UNKNOWN'
    else:
        reading['source_status']['concept']['market_session'] = '2099-01-01'
    with pytest.raises(ValueError):
        shared.saved_source_status(col, reading)


def test_no_compaction_can_increase_the_bound_or_omit_unrelated_research(tmp_path):
    col, base, _ = sample(tmp_path)
    research = deepcopy(base['research']); research['too_large'] = 'x' * (192*1024)
    before = deepcopy(research)
    with pytest.raises(ValueError, match='bounded index size'):
        shared._assemble(col, base, research)
    assert research == before
