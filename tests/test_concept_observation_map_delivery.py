"""Real Collector retention/assembly over synthetic already-qualified input."""
from copy import deepcopy
import json

import pytest

from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as base
from decision_kernel.runtime import current_state_delivery_with_odds_watch as entry
from decision_kernel.runtime import concept_observation_map as view
from decision_kernel.runtime import concept_observation_map_delivery as delivery
from tests.test_concept_radar import Fixture, no_network
from test_radar_company_reading import API, baseline, SHA

CUTOFF = '2026-09-18T09:00:00+00:00'


def prepared(tmp_path):
    col = entry.Collector(API(), SHA, tmp_path, now=lambda: CUTOFF)
    b, _, _ = baseline(col)
    report = Fixture().run()
    ref = col.retain('details/concept/123456/observation.json', model.json_bytes(report))
    index = col.retain('details/radar/index.html', b'<p>Synthetic existing company reading</p>')
    companies = col.retain('details/radar/company-reading.json', b'{"synthetic_unchanged":true}')
    research = deepcopy(b['research'])
    research['radar_discovery'] = {'status': 'READ_OK', 'coverage': {
        'distinct_companies': 0, 'sector_companies': 0, 'institutional_companies': 0, 'overlap_companies': 0},
        'details': {'index': index, 'company_reading': companies}, 'source_status': {'concept': {
            'status': 'VERIFIED_SAVED_CONCEPT_SOURCE', 'details': {'observation.json': ref},
            'projection_hash': report['projection_hash'], 'market_session': report['projection']['market_session'],
            'source_observed_at': report['projection']['as_of']}}}
    b = model.assemble(code_commit=SHA, checked_at=CUTOFF, check_started_at=b['checks']['started_at'],
        lanes=b['lanes'], research=research, capabilities=[], refresh_identity={})
    col.files.update({'current-state.json': model.json_bytes(b), 'README.md': model.render_summary(b).encode()})
    return col, b, report


def test_normal_attachment_uses_no_new_reads_preserves_source_and_company_bytes(tmp_path):
    col, b, source = prepared(tmp_path); before = dict(col.files)
    result = delivery.attach(col, b); model.validate_read_package(result)
    item = result['research']['radar_discovery']['concept_observation_map']
    assert item['status'] == 'READ_OK' and col.api.calls == 0 and not col.api.reads
    assert set(col.files) - set(before) == {delivery.PREFIX+'json', delivery.PREFIX+'html'}
    for path, raw in before.items():
        if path not in {'README.md', 'current-state.json'}: assert col.files[path] == raw
    value = json.loads(col.files[delivery.PREFIX+'json'])
    assert view.verify(value, source)['new_market_requests'] == 0
    assert item['source_projection_hash'] == source['projection_hash']
    assert '打开概念观察地图'.encode() in col.files['README.md']
    assert b'concept_observation_map' not in before['current-state.json']


@pytest.mark.parametrize('failure', ['source_hash', 'reference', 'render', 'second_retain', 'final_assembly'])
def test_optional_map_failure_preserves_qualified_data_and_reports_gap(tmp_path, monkeypatch, failure):
    col, b, source = prepared(tmp_path)
    status = b['research']['radar_discovery']['source_status']['concept']
    if failure == 'source_hash': status['projection_hash'] = '0'*64
    elif failure == 'reference': status['details']['observation.json']['read_ref_rule'] = 'LATEST_REF'
    elif failure == 'render': monkeypatch.setattr(view, 'render', lambda value: (_ for _ in ()).throw(ValueError('synthetic')))
    elif failure == 'second_retain':
        original = col.retain
        def retain(path, raw):
            if path == delivery.PREFIX+'html': raise ValueError('synthetic')
            return original(path, raw)
        monkeypatch.setattr(col, 'retain', retain)
    else:
        original = delivery.radar_reading._assemble; calls = []
        def assemble(*args):
            calls.append(1)
            if len(calls) == 1: raise ValueError('synthetic')
            return original(*args)
        monkeypatch.setattr(delivery.radar_reading, '_assemble', assemble)
    # Explicitly reseal this synthetic parent; a real caller qualifies its source separately.
    from decision_kernel.identity import canonical_hash
    b['reading_hash'] = canonical_hash({k: v for k, v in b.items() if k != 'reading_hash'})
    before = dict(col.files)
    result = delivery.attach(col, b)
    item = result['research']['radar_discovery']['concept_observation_map']
    assert item['status'] == 'UNAVAILABLE_OR_REJECTED' and col.api.calls == 0
    assert result['research']['radar_discovery']['source_status'] == b['research']['radar_discovery']['source_status']
    assert not any(path.startswith(delivery.PREFIX) for path in col.files)
    for path, raw in before.items():
        if path not in {'README.md', 'current-state.json'}: assert col.files[path] == raw
    assert '读取有缺口'.encode() in col.files['README.md']
    model.validate_read_package(result)


def test_small_existing_budget_does_not_get_inflated_or_reset(tmp_path):
    col, b, _ = prepared(tmp_path)
    col.api.calls = 7
    col.api.max_calls = col.api.calls + len(col.files) + 5
    limit = col.api.max_calls
    before_count = len(col.files)
    result = delivery.attach(col, b)
    assert result['research']['radar_discovery']['concept_observation_map']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert col.api.calls == 7 and col.api.max_calls == limit
    assert len(col.files) == before_count


def test_unqualified_source_leaves_parent_unchanged_without_old_fallback(tmp_path):
    col, b, _ = prepared(tmp_path)
    b['research']['radar_discovery']['source_status']['concept']['status'] = 'LATEST_ATTEMPT_NOT_SUCCESSFUL'
    from decision_kernel.identity import canonical_hash
    b['reading_hash'] = canonical_hash({k: v for k, v in b.items() if k != 'reading_hash'})
    before = dict(col.files)
    assert delivery.attach(col, b) is b and col.files == before and col.api.calls == 0


@pytest.mark.parametrize('enabled', [False, True])
def test_existing_collector_only_attaches_map_when_concept_option_is_on(tmp_path, monkeypatch, enabled):
    col, b, _ = prepared(tmp_path)
    monkeypatch.setattr(base.Collector, 'collect', lambda self, refresh: b)
    monkeypatch.setattr(delivery.radar_reading, 'attach', lambda self, baseline: baseline)
    col.include_radar_discovery = True; col.include_concept_discovery = enabled
    result = col.collect({})
    assert ('concept_observation_map' in result['research']['radar_discovery']) is enabled
