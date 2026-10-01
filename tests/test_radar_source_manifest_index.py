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
    assert all(out[k] == v for k, v in model.AUTHORITY.items())
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


def test_real_collector_closes_radar_before_later_root_growth(tmp_path, monkeypatch):
    """The actual orchestration order, with inert saved-module boundaries."""
    import sys
    from types import ModuleType
    from decision_kernel.runtime import current_state_delivery_with_odds_watch as entry
    col, early, full = sample(tmp_path)
    original_files = dict(col.files)
    extra = 'x' * (192*1024 - len(model.read_package_bytes(early)) + 1000)

    def append_late(base):
        research = deepcopy(base['research'])
        research['synthetic_later_section'] = extra
        return model.assemble(code_commit=col.code_commit, checked_at=AT,
                              check_started_at=base['checks']['started_at'],
                              lanes=base['lanes'], research=research,
                              capabilities=base['capability_gaps'], refresh_identity=base['refresh'])

    # This is the missed #709 case: Radar alone fits, later original assemble fails.
    assert len(model.read_package_bytes(early)) < 192*1024
    assert 'source_status_scope' not in early['research']['radar_discovery']
    with pytest.raises(ValueError, match='bounded index size'):
        append_late(early)

    calls = []
    late_module = ModuleType('decision_kernel.runtime.news_daily_reading')
    def late_attach(collector, parent):
        calls.append('later')
        assert parent['research']['radar_discovery']['source_status_scope'] == shared.SOURCE_STATUS_SCOPE
        assert shared.saved_source_status(collector, parent['research']['radar_discovery']) == full
        return append_late(parent)  # The later module does not own Radar compaction.
    late_module.attach = late_attach
    monkeypatch.setitem(sys.modules, late_module.__name__, late_module)
    monkeypatch.setattr(entry.base.Collector, 'collect', lambda self, refresh: early)
    monkeypatch.setattr(shared, 'attach', lambda self, parent: parent)
    current = entry.Collector(col.api, col.code_commit, tmp_path, now=lambda: AT)
    current.files = col.files
    current.include_radar_discovery = True
    current.include_daily_news = True
    final = current.collect({})
    assert calls == ['later'] and len(model.read_package_bytes(final)) <= 192*1024
    assert final['research']['synthetic_later_section'] == extra
    assert all(current.files[path] == raw for path, raw in original_files.items())
    assert 'source_status_scope' not in early['research']['radar_discovery']
    assert final['lanes'] == early['lanes'] and final['pending'] == early['pending']
    assert all(final[k] == v for k, v in model.AUTHORITY.items())
    assert col.api.calls == 0


def test_closing_index_is_exact_idempotent_and_preserves_unavailable(tmp_path):
    col, base, full = sample(tmp_path)
    result = shared.index_source_status(col, base)
    assert shared.saved_source_status(col, result['research']['radar_discovery']) == full
    before = dict(col.files)
    assert shared.index_source_status(col, result) is result
    assert col.files == before
    failed = deepcopy(base)
    failed['research']['radar_discovery'] = {'status': 'UNAVAILABLE_OR_REJECTED'}
    failed['reading_hash'] = canonical_hash({k:v for k,v in failed.items() if k != 'reading_hash'})
    assert shared.index_source_status(col, failed) is failed
    assert col.files == before
