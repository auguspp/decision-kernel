"""Explicit synthetic calendar/endpoint examples; not market or strategy results."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import d_horizon_follow_up as h
from decision_kernel.runtime import stock_market_inputs as p

AT = '2026-12-01T10:00:00+00:00'
SOURCE = {'sha256': 'a' * 64, 'origin_run': {'id': 1}}


def case():
    return {'id': 'case', 'record_id': 'retained-case', 'symbol': '603986.SH',
        'frozen_at': '2026-10-04T01:03:53Z', 'checkpoints': [5, 20],
        'long_research_deadline': '2027-09-02', 'analyst_review_by': '2026-11-30',
        'interpretation': {'intermediate': 'Retained hypothesis', 'invalidation': 'Retained counterevidence'}}


def parts(end='2026-11-10'):
    # Closed dates are explicitly supplied test data, not a production calendar.
    days = {}; d = date(2026, 10, 4)
    while d <= date.fromisoformat(end):
        days[d.isoformat()] = d.weekday() < 5 and d >= date(2026, 10, 8)
        d += timedelta(days=1)
    report = {'market_session': end, 'observed_at': AT, 'received_through': AT,
              'columns': p.COLUMNS, 'rows': [['603986.SH', '353.9', None, None, None, 1, 1, 1]]}
    return report, days, {}, {}


def put(tables, session, price='100', factor='1'):
    datekey = session.replace('-', '')
    for api, field, value in [('daily', 'close', price), ('adj_factor', 'adj_factor', factor)]:
        if value is not None:
            tables[api, datekey] = {'603986.SH': {'ts_code': '603986.SH', 'trade_date': datekey, field: value}}


def project(c=None, data=None, previous=None):
    return h.project(c or case(), *(data or parts()), checked_at=AT, source=SOURCE, previous=previous, previous_reading_commit='b' * 40)


def test_pre_freeze_source_is_only_backward_context():
    data = parts('2026-09-30')
    out = project(data=data)
    assert out['anchor_session'] is None
    assert all(r['change'] is None and r['target_session'] is None for r in out['checkpoints'])
    assert out['historical_price_context']['row']['raw_close'] == '353.9'
    assert out['opportunity_established'] is None and out['opportunity_probability'] is None
    assert out['execution_result'] == 'NOT_EVALUATED_NO_EXECUTION_INPUT'


def test_exact_calendar_anchor_does_not_wait_for_available_quote():
    out = project()
    assert out['anchor_session'] == '2026-10-08'
    assert out['checkpoints'][0]['target_session'] == '2026-10-15'
    assert out['checkpoints'][1]['target_session'] == '2026-11-05'
    assert all(r['status'] == 'PRICE_ENDPOINT_UNAVAILABLE' for r in out['checkpoints'])


@pytest.mark.parametrize('freeze,anchor', [('2026-10-08T06:59:59Z', '2026-10-08'),
                                          ('2026-10-08T07:00:00Z', '2026-10-09')])
def test_strictly_after_freeze_uses_exchange_close_not_midnight(freeze, anchor):
    c = case(); c['frozen_at'] = freeze
    assert project(c)['anchor_session'] == anchor


def test_existing_factor_math_both_endpoints_not_intermediate_rows():
    data = parts(); put(data[2], '2026-10-08', '100', '2')
    put(data[2], '2026-10-15', '110', '2'); put(data[2], '2026-11-05', '60', '4')
    out = project(data=data)
    assert [r['change'] for r in out['checkpoints']] == ['0.100000000000', '0.200000000000']
    assert all(r['acquisition_timing'] == 'LATER_ACQUISITION_NOT_HISTORICAL_KNOWLEDGE' for r in out['checkpoints'])
    assert out['path_metrics'] == 'NOT_COMPUTED_NO_CONTINUOUS_PATH'


def test_factor_missing_is_local_to_its_checkpoint():
    data = parts(); put(data[2], '2026-10-08'); put(data[2], '2026-10-15', '110', None)
    put(data[2], '2026-11-05', '120')
    out = project(data=data)
    assert out['checkpoints'][0]['status'] == 'FACTOR_ENDPOINT_UNAVAILABLE'
    assert out['checkpoints'][1]['change'] == '0.200000000000'


def test_missing_s0_never_rolls_to_later_success():
    data = parts(); put(data[2], '2026-10-09'); put(data[2], '2026-10-15')
    out = project(data=data)
    assert out['anchor_session'] == '2026-10-08'
    assert out['checkpoints'][0]['change'] is None


def test_unknown_calendar_day_is_not_assumed_closed():
    data = parts(); del data[1]['2026-10-06']
    out = project(data=data)
    assert out['calendar_gap'] == '2026-10-06' and out['anchor_session'] is None


def test_later_calendar_gap_does_not_cancel_earlier_known_window():
    data = parts(); del data[1]['2026-10-16']
    put(data[2], '2026-10-08'); put(data[2], '2026-10-15', '110')
    out = project(data=data)
    assert out['checkpoints'][0]['change'] == '0.100000000000'
    assert out['checkpoints'][1]['status'] == 'CALENDAR_GAP'


def test_preserve_unchanged_and_revised_and_later_missing_results():
    data = parts(); put(data[2], '2026-10-08'); put(data[2], '2026-10-15', '110')
    old = project(data=data); snapshot = deepcopy(old)
    same = project(data=data, previous=old)
    assert same['checkpoints'][0]['observation'] == 'UNCHANGED_ENDPOINT_RESULT'
    assert same['checkpoints'][0]['first_recorded_at'] == old['checkpoints'][0]['first_recorded_at']
    put(data[2], '2026-10-15', '109')
    new = project(data=data, previous=old)
    assert new['checkpoints'][0]['observation'] == 'REVISED_ENDPOINT_RESULT'
    missing = project(previous=old)
    assert missing['checkpoints'][0]['change'] == '0.100000000000'
    assert missing['checkpoints'][0]['observation'].startswith('RETAINED_PREVIOUS')
    assert old == snapshot


def test_later_calendar_window_can_reuse_immutable_prefix_not_rebase():
    old = project()
    data = parts(); data[1].pop('2026-10-04')
    assert project(data=data, previous=old)['anchor_session'] == old['anchor_session']
    data[1]['2026-10-08'] = False
    with pytest.raises(ValueError, match='calendar revised'):
        project(data=data, previous=old)


def test_changed_freeze_does_not_reset_the_same_case():
    old = project(); c = case(); c['frozen_at'] = '2026-10-05T00:00:00Z'
    with pytest.raises(ValueError, match='contract changed'):
        project(c, previous=old)


def test_review_due_does_not_claim_economic_success():
    out = project()
    assert out['review_clock'] == 'DATE_REACHED_NOT_ECONOMIC_VERIFICATION'
    assert out['economic_result'] == 'NOT_AUTOMATICALLY_ADJUDICATED'
    assert out['long_research_deadline'] == '2027-09-02'


def test_source_decimal_strings_kept_in_endpoints():
    data = parts(); put(data[2], '2026-10-08', '100.0000', '1.00000')
    put(data[2], '2026-10-15', '110.0000', '1.00000')
    row = project(data=data)['checkpoints'][0]
    assert row['endpoints']['start']['close'] == '100.0000'
    assert row['endpoints']['end']['adj_factor'] == '1.00000'


def test_real_declaration_does_not_change_long_term_or_install_dependencies():
    root = Path(__file__).resolve().parents[1]
    c = json.loads((root / h.CONFIG).read_bytes())['cases'][0]
    assert c['frozen_at'] == '2026-10-04T01:03:53Z' and c['checkpoints'] == [5,20]
    assert c['document_sha256'] == '29f26cf24c0bc9923867f2be8f8538c967cf47893e664c689ad73d2d4944dd12'
    source = (root / 'src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py').read_text()
    assert 'from .d_horizon_follow_up import attach as attach_horizons' in source


def test_calendar_can_advance_without_promoting_old_prices_to_current():
    old_prices = parts('2026-09-30')[0]
    calendar = parts('2026-10-09')[1]
    result = h.project(case(), old_prices, calendar, {}, {}, checked_at=AT, source=SOURCE,
                       calendar_market_session='2026-10-09')
    assert result['anchor_session'] == '2026-10-08'
    assert result['historical_price_context']['market_session'] == '2026-09-30'
    assert result['checkpoints'][0]['change'] is None


def test_retained_result_points_to_original_reading_not_unavailable_same_r_archive():
    data = parts(); put(data[2], '2026-10-08'); put(data[2], '2026-10-15', '110')
    first = project(data=data)
    second = project(previous=first)
    third = h.project(case(), *parts(), checked_at=AT, source=SOURCE, previous=second,
                      previous_reading_commit='c' * 40)
    assert third['checkpoints'][0]['source']['retained_reading_commit'] == 'b' * 40
    assert 'read_ref_rule' not in third['checkpoints'][0]['source']


def seeded(monkeypatch):
    """Synthetic I/O/registry/quota seam; real byte binding/root assembly/math."""
    from io import BytesIO
    from types import SimpleNamespace
    import sys
    import zipfile
    from decision_kernel.runtime import research_archive_index as registry_index
    from decision_kernel.runtime import current_state as model
    from decision_kernel.identity import canonical_hash

    c = case()
    body = '\n'.join([c['frozen_at'], c['long_research_deadline'], c['analyst_review_by'],
                      *c['interpretation'].values()]).encode()
    c.update(document_sha256=model.sha256(body), source_assertions=[c['frozen_at']])
    config = p.dumps({'version': h.VERSION, 'cases': [c]})
    def descriptor(path, raw):
        return {'read_path': path, 'sha256': model.sha256(raw), 'bytes': len(raw),
                'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
    record = {'id': c['record_id'], 'case': c['symbol'], 'use': 'RETAINED_RESEARCH_DOCUMENT',
              'archive': {'format': 'RETAINED_FILES'}, 'source': {**descriptor('sources/case.md', body),
                  'path': 'docs/readings/case/README.md', 'ref': 'c' * 40}}
    data = parts(); put(data[2], '2026-10-08'); put(data[2], '2026-10-15', '110')
    daily = {**data[0], 'version': p.VERSION, 'source': p.SOURCE, 'provenance': 'LIVE_TUSHARE_RELAY'}
    # The LIVE field is contract-test data, not a claim that this fixture was collected.
    files = {'report.json': p.dumps(daily)}
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, raw in files.items(): z.writestr(name, raw)
    raw = stream.getvalue(); archive = {**descriptor('sources/test.zip', raw), 'artifact_id': 1,
        'expires_at': '2099-01-01T00:00:00Z', 'origin_run': {'id': 1, 'head_sha': 'a' * 40}}
    daily_ref = descriptor('details/daily.json', p.dumps(daily))
    state = {'file': daily_ref, 'source_archive': archive, 'market_session': daily['market_session'],
        'cohort_denominator': 1, 'status': 'SOURCE_TEST',
        'publication_verification': 'REBUILT_FROM_EXACT_RETAINED_RESPONSE_BYTES'}
    independent = p.dumps({'daily_market_inputs': state})
    root = model.assemble(code_commit='a' * 40, checked_at=AT, check_started_at=AT,
        research={'handoffs': {'active': []}, 'records': [{'id': 'keep-human-decision'}],
                  'independent_stock_observations': descriptor('details/independent.json', independent)},
        lanes={'stock': {'gaps': ['old failure']}}, capabilities=[], refresh_identity={})
    collector = SimpleNamespace(code_commit='a' * 40, previous=None, previous_commit=None,
        sources={}, now=lambda: AT, archive_cache={1: (files, archive)}, api=SimpleNamespace(calls=0, max_calls=500),
        files={'current-state.json': model.read_package_bytes(root), 'README.md': b'Original reading\n',
               'details/independent.json': independent, 'details/daily.json': p.dumps(daily), 'sources/test.zip': raw})
    def source(spec):
        value = config if spec['path'] == h.CONFIG else body
        path = 'sources/config.json' if spec['path'] == h.CONFIG else 'sources/case.md'
        collector.files[path] = value
        return value, descriptor(path, value)
    def retain(path, value):
        assert path not in collector.files
        collector.files[path] = value
        return descriptor(path, value)
    collector.source, collector.retain = source, retain
    monkeypatch.setitem(sys.modules, 'decision_kernel.runtime.institutional_radar_reading',
                        SimpleNamespace(_reserve=lambda *a, **k: None))
    monkeypatch.setattr(registry_index, 'read_entries', lambda *a, **k: [record])
    monkeypatch.setattr(h, 'read_price_parts', lambda *a: data[1:])
    return collector, root


def test_attach_readback_preserves_other_products_and_reuses_old_clock(monkeypatch):
    from decision_kernel.runtime import current_state as model
    collector, root = seeded(monkeypatch); old = deepcopy(root); original = dict(collector.files)
    result = h.attach(collector, root, retained_limit=20*1024*1024)
    model.validate_read_package(result)
    raw = collector.files[h.PATH]; h._bound(raw, result['research'][h.KEY])
    report = p.loads(raw)
    assert report['cases'][0]['checkpoints'][0]['change'] == '0.100000000000'
    assert report['body_scope'] == 'DECLARED_README_NOT_FULL_ARCHIVE_RECOVERY'
    assert root == old and result['lanes'] == root['lanes']
    for path, data in original.items():
        if path not in ('README.md', 'current-state.json'):
            assert collector.files[path] == data
    second, base2 = seeded(monkeypatch)
    second.previous, second.previous_commit = result, 'b' * 40
    second.api.file = lambda path, ref: raw
    next_result = h.attach(second, base2, retained_limit=20*1024*1024)
    saved = p.loads(second.files[h.PATH])
    assert saved['cases'][0]['checkpoints'][0]['first_recorded_at'] == AT
    assert saved['cases'][0]['checkpoints'][0]['observation'] == 'UNCHANGED_ENDPOINT_RESULT'
    assert collector.files[h.PATH] == raw
    model.validate_read_package(next_result)


@pytest.mark.parametrize('damage', ['price_bytes', 'case_bytes', 'capacity', 'calendar'])
def test_new_failure_only_affects_horizon_attachment(monkeypatch, damage):
    from decision_kernel.runtime import current_state as model
    collector, root = seeded(monkeypatch); before = dict(collector.files)
    if damage == 'price_bytes':
        collector.files['details/daily.json'] += b'corrupted'
        before = dict(collector.files)
    elif damage == 'case_bytes':
        original = collector.source
        collector.source = lambda spec: (b'wrong', {}) if spec['path'] != h.CONFIG else original(spec)
    elif damage == 'calendar':
        monkeypatch.setattr(h, 'read_price_parts', lambda *a: (_ for _ in ()).throw(ValueError('bad calendar')))
    limit = sum(map(len, before.values())) + 200 if damage == 'capacity' else 20*1024*1024
    result = h.attach(collector, root, retained_limit=limit)
    assert h.PATH not in collector.files
    assert result['lanes'] == root['lanes'] and result['research']['records'] == root['research']['records']
    for path, raw in before.items():
        if path not in ('README.md', 'current-state.json'): assert collector.files[path] == raw
    model.validate_read_package(result)
