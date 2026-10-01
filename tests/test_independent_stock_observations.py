"""Synthetic source envelopes, real consumer boundaries, all network prohibited."""
from copy import deepcopy
from datetime import datetime, time, timedelta
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import independent_stock_observations as independent
from decision_kernel.runtime import sector_radar_audit as audit
from decision_kernel.runtime import hithink_stock_reading as own
from decision_kernel.runtime import stock_radar_reading as stock
from test_hithink_stock_reading import inputs


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('independent consumer attempted network access')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(own, 'request_json', denied)
    monkeypatch.setattr(independent.indices, '_default_request_json', denied)
    monkeypatch.setattr(independent.quotes, '_default_request_json', denied)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((canonical_json(value)+'\n').encode())


def digest_tree(root):
    return {p.relative_to(root).as_posix(): audit._sha(p.read_bytes())
            for p in root.rglob('*') if p.is_file()}


def source(tmp_path, *, count=503):
    days, at, history, quote, actions = inputs()
    days = tuple(days)
    root = tmp_path / 'audit'
    recorder = audit._Recorder(root, provenance=audit.SYNTHETIC_PROVENANCE,
        credential=None, capture_now=lambda: at)
    # These are inert container entries, explicitly not a fabricated Sector
    # state. This fixture has no Sector result, member, company or Research.
    for name in audit._INPUT_FILES:
        value = {'observed_at': at.isoformat()} if name == 'context.json' else {'unavailable': True}
        recorder.add('inputs/'+name, audit._json_bytes(value))
    ms = lambda d: int(datetime.combine(d, time(), own.TZ).timestamp()*1000)
    now_ms = int(at.timestamp()*1000)
    calendar = {'code': 0, 'data': {'item': [{'date': d.strftime('%Y%m%d')} for d in days]}}
    last = {'thscode': '000300.SH', 'ticker': '1B0300', 'last_price': '70', 'prev_price': '69',
            'price_change': '1', 'price_change_ratio_pct': '1.4492753623', 'open_price': '70',
            'high_price': '71', 'low_price': '69', 'volume': '100', 'turnover': '7000'}
    index_quote = {'code': 0, 'data': {'timestamp': now_ms, 'total': 1, 'item': [last]}}
    index_history = {'code': 0, 'data': {'thscode': '000300.SH', 'interval': '1d', 'adjust': None,
        'timestamp': ms(days[-1]), 'item': [dict(r) for r in history['data']['item']]}}
    rows = [{'thscode': f'{600000+i:06}.SH', 'ticker': f'{600000+i:06}',
             'last_price': '10', 'prev_price': '10', 'turnover': '0'} for i in range(count)]
    rows[0].update(thscode='002714.SZ', ticker='002714', last_price='70', prev_price='69')
    rows[1].update(last_price='5')  # Negative move must survive abs-only sample ordering.
    rows[2].update(last_price=None, prev_price=None)
    rows[3].update(last_price='15')  # Equal magnitude; code tie-break.
    recorder.request(lambda p, q: calendar)(independent.HITHINK_CALENDAR_PATH, {})
    recorder.request(lambda p, q: index_quote)(independent.indices.HITHINK_INDEX_SNAPSHOT_PATH,
                                               {'thscodes': '000300.SH'})
    independent.indices.fetch_hithink_completed_index_history(thscode='000300.SH',
        observed_at=at, api_key='OFFLINE', trading_sessions=days,
        request_json=recorder.request(lambda p, q: index_history))
    for offset in range(0, count, 500):
        envelope = {'code': 0, 'data': {'timestamp': now_ms, 'total': count,
                                       'item': rows[offset:offset+500]}}
        recorder.request(lambda p, q, e=envelope: e)(own.SNAPSHOT,
                                                    {'limit': '500', 'offset': str(offset)})
    recorder.manifest.update(status='REJECTED', error_type='SyntheticSectorUnavailable',
                             run_clocks=[at.isoformat()])
    recorder.flush()
    return SimpleNamespace(root=root, recorder=recorder, days=days, at=at,
                           history=history, quote=quote, actions=actions)


def audit_pin(case):
    return independent._load(case.root / 'manifest.json')['audit_hash']


def rebuild_audit(case):
    manifest = independent._load(case.root / 'manifest.json')
    for name in manifest['files']:
        raw = (case.root / name).read_bytes()
        manifest['files'][name] = {'bytes': len(raw), 'sha256': audit._sha(raw)}
    manifest['audit_hash'] = canonical_hash({k: v for k, v in manifest.items() if k != 'audit_hash'})
    write(case.root / 'manifest.json', manifest)
    return manifest


def capture(case, *, mutate=None):
    root = case.root.parent / 'stock'
    write(root / 'inputs/state/market-state.json', {'sessions': case.days})
    h, q, a = deepcopy((case.history, case.quote, case.actions))
    if mutate:
        mutate(h, q, a)
    records = []
    for i, (path, params, envelope) in enumerate((
        (own.HISTORY, own.history_params('002714.SZ', case.days), h),
        (own.SNAPSHOT, {'thscodes': '002714.SZ'}, q),
        (own.ACTIONS, own.action_params('002714.SZ', case.days), a)), 1):
        name = f'responses/{i:02}.json'
        write(root / name, envelope)
        records.append({'path': path, 'params': params, 'requested_at': case.at.isoformat(),
                        'received_at': case.at.isoformat(), 'response_file': name,
                        'error_type': None, 'http_status': 200})
    report = {'version': 'stock-reading-capture-replay-v7', 'provenance': audit.SYNTHETIC_PROVENANCE,
        'response_semantics': 'DECODED_PROVIDER_JSON_NOT_ORIGINAL_HTTP_BYTES', 'reference_input_hash': None,
        'planned_issuer_outcomes': [{'thscode': '002714.SZ'}], 'requests': records,
        'observed_at': case.at.isoformat(), 'finished_at': case.at.isoformat(), **stock.LIMITS}
    write(root / 'capture.json', report)
    return root, rebuild_capture(root)


def rebuild_capture(root):
    report = independent._load(root / 'capture.json')
    report['files'] = {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                      'sha256': audit._sha(p.read_bytes())} for p in root.rglob('*')
                      if p.is_file() and p.name != 'capture.json'}
    report['capture_hash'] = canonical_hash({k: v for k, v in report.items() if k != 'capture_hash'})
    write(root / 'capture.json', report)
    return report['capture_hash']


def build(case, **kwargs):
    return independent.build(case.root, expected_audit_hash=audit_pin(case), **kwargs)


def test_no_sector_or_research_input_complete_denominator_and_signed_sample(tmp_path):
    case = source(tmp_path)
    before = digest_tree(case.root)
    report = build(case, sample_size=3)
    c = report['coverage']
    assert (c['unique_identities'], c['complete_pages'], c['usable_quote_ratios'], c['unpriced']) == (503, 2, 502, 1)
    assert [r['thscode'] for r in report['selection']['selected']] == ['600001.SH', '600003.SH', '002714.SZ']
    assert report['selection']['selected'][0]['signed_quote_change'] == '-0.5'
    assert report['origin'] == independent.ORIGIN
    assert all(r['status'] == 'UNKNOWN' and r['reason_code'] == 'HISTORY_NOT_SUPPLIED'
               for r in report['selected_observations'])
    assert report['inventory']['company_names'].startswith('UNKNOWN')
    assert len(report['inventory']['rows']) == 503
    assert sum(r[-1] == 'D' for r in report['inventory']['rows']) == 499
    assert not report['production_admission'] and report['new_source_requests'] == 0
    assert report['research_authority'] == report['investment_authority'] == 'NONE'
    assert digest_tree(case.root) == before
    # Unreadable, unrelated Sector/company/Research data cannot influence this
    # consumer. The changed audit pin is recorded; selected identities persist.
    for name in ('inputs/market-state.json', 'inputs/candidate-events.json', 'inputs/parent-hints.json'):
        (case.root / name).write_bytes(b'not a Sector document')
    rebuild_audit(case)
    second = build(case, sample_size=3)
    assert second['selection']['selected'] == report['selection']['selected']


def test_freeze_before_history_intersection_and_legacy_arithmetic_equality(tmp_path):
    case = source(tmp_path)
    absent = build(case, sample_size=3)
    root, pin = capture(case)
    before = digest_tree(root)
    supplied = build(case, sample_size=3, stock_root=root, expected_capture_hash=pin)
    assert supplied['selection'] == absent['selection']
    assert supplied['coverage']['selected_with_supplied_history'] == supplied['coverage']['selected_qualified'] == 1
    assert supplied['selected_observations'][:2] == absent['selected_observations'][:2]
    actual = supplied['selected_observations'][2]['stock_path']
    legacy = stock._stock_path(SimpleNamespace(sessions=case.days), '002714.SZ', case.history,
        at=case.at, quote=case.quote, actions=case.actions, quote_received_at=case.at)
    assert actual == stock._plain(legacy)
    assert actual['history_session_count'] == 61
    assert supplied['replay_controls']['origin'].startswith('ORIGINAL_SECTOR_SELECTED')
    assert digest_tree(root) == before
    assert independent.verify(supplied, case.root, expected_audit_hash=audit_pin(case),
        sample_size=3, stock_root=root, expected_capture_hash=pin)['network_calls'] == 0


@pytest.mark.parametrize('damage', ['missing_page', 'duplicate', 'truncated', 'changed_total', 'excess_total',
    'wrong_offset', 'future_ready', 'future_capture', 'zero_previous', 'negative_last'])
def test_rehashed_bad_full_pages_fail_closed_through_reused_parser(tmp_path, damage):
    case = source(tmp_path)
    manifest = independent._load(case.root / 'manifest.json')
    record = manifest['requests'][3]
    page = independent._load(case.root / record['response_file'])
    if damage == 'missing_page':
        (case.root / manifest['requests'][-1]['response_file']).unlink()
        with pytest.raises((ValueError, audit.SectorRadarAuditError)):
            build(case)
        return
    if damage == 'duplicate': page['data']['item'][4] = deepcopy(page['data']['item'][3])
    elif damage == 'truncated': page['data']['item'].pop()
    elif damage == 'changed_total': page['data']['total'] += 1
    elif damage == 'excess_total': page['data']['total'] = 499
    elif damage == 'wrong_offset': record['params']['offset'] = '1'
    elif damage == 'future_ready': page['data']['timestamp'] += 1
    elif damage == 'future_capture': record['captured_at'] = (case.at+timedelta(seconds=1)).isoformat()
    elif damage == 'zero_previous': page['data']['item'][0]['prev_price'] = '0'
    else: page['data']['item'][0]['last_price'] = '-1'
    write(case.root / record['response_file'], page)
    write(case.root / 'manifest.json', manifest)
    rebuild_audit(case)
    with pytest.raises((ValueError, RuntimeError)):
        build(case)


def test_no_page_and_extra_unplanned_page_are_never_empty_success(tmp_path):
    case = source(tmp_path)
    manifest = independent._load(case.root / 'manifest.json')
    for record in manifest['requests'][3:]:
        (case.root / record['response_file']).unlink()
        del manifest['files'][record['response_file']]
    manifest['requests'] = manifest['requests'][:3]
    write(case.root / 'manifest.json', manifest)
    rebuild_audit(case)
    with pytest.raises(ValueError, match='not an empty scan'):
        build(case)


def test_coherent_pretrading_zero_is_retained_unpriced_not_dropped(tmp_path):
    case = source(tmp_path)
    path = case.root / 'responses/0003.json'
    page = independent._load(path)
    page['data']['item'][2].update(prev_price=0, last_price=None, volume=0, turnover=0)
    write(path, page); rebuild_audit(case)
    report = build(case)
    row = next(r for r in report['inventory']['rows'] if r[0] == '600002.SH')
    assert row[3:] == [None, None, None, 'U']
    assert report['coverage']['unique_identities'] == 503


@pytest.mark.parametrize('damage,expected', [
    ('missing_recent', 'REQUIRED_SELECTION_WINDOW_STOCK_SESSIONS_MISSING'),
    ('previous', 'PRICE_REFERENCE_DISCONTINUITY_REQUIRES_SEPARATE_REVIEW'),
    ('business', 'PROVIDER_BUSINESS_REQUEST_FAILED'),
    ('action', 'REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW'),
    ('older_gap', None)])
def test_existing_26_required_61_context_and_failure_semantics(tmp_path, damage, expected):
    case = source(tmp_path)
    def mutate(h, q, a):
        if damage == 'missing_recent': h['data']['item'].pop(-3)
        elif damage == 'older_gap': h['data']['item'].pop(0)
        elif damage == 'previous': q['data']['item'][0]['prev_price'] = '68'
        elif damage == 'business': a.update(code=3002, data=None)
        else: a['data']['item'] = [{'ticker': '002714', 'ex_date_ms': h['data']['item'][-1]['date_ms'],
                                  'dividend_per_share': '1', 'per_share_bonus': '0'}]
    root, pin = capture(case, mutate=mutate)
    report = build(case, sample_size=3, stock_root=root, expected_capture_hash=pin)
    row = report['selected_observations'][2]
    assert row['reason_code'] == expected
    if damage == 'older_gap':
        assert row['stock_path']['returns']['60'] is None
        assert row['stock_path']['returns']['5'] is not None
        assert row['stock_path']['history_session_count'] == 60
    else:
        assert row['stock_path'] is None and row['status'] != 'CONDITIONS_NOT_MET'
    if damage == 'business':
        assert row['input_failure']['provider_business_code'] == 3002
        assert row['input_failure']['phase'] == 'CORPORATE_ACTIONS'


@pytest.mark.parametrize('target', ['source', 'request', 'session'])
def test_rehashed_tampering_cannot_replace_independently_pinned_inputs(tmp_path, target):
    case = source(tmp_path)
    root, pin = capture(case)
    audit_hash = audit_pin(case)
    if target == 'source':
        path = case.root / 'responses/0003.json'; page = independent._load(path)
        page['data']['item'][0]['last_price'] = '1'; write(path, page); rebuild_audit(case)
    elif target == 'request':
        path = root / 'capture.json'; report = independent._load(path)
        report['requests'][0]['params']['thscode'] = '000001.SZ'; write(path, report); rebuild_capture(root)
    else:
        path = root / 'inputs/state/market-state.json'; state = independent._load(path)
        state['sessions'][0] = '2001-01-01'; write(path, state); rebuild_capture(root)
    with pytest.raises(ValueError, match='source pin differs'):
        independent.build(case.root, expected_audit_hash=audit_hash, stock_root=root, expected_capture_hash=pin)


@pytest.mark.parametrize('target', ['request', 'session', 'clock'])
def test_new_pin_does_not_bypass_request_session_or_clock_checks(tmp_path, target):
    case = source(tmp_path)
    root, _ = capture(case)
    if target == 'session':
        path = root / 'inputs/state/market-state.json'; state = independent._load(path)
        state['sessions'][0] = '2001-01-01'; write(path, state)
    else:
        path = root / 'capture.json'; report = independent._load(path)
        if target == 'request': report['requests'][0]['params']['thscode'] = '000001.SZ'
        else: report['requests'][0]['received_at'] = (case.at+timedelta(seconds=1)).isoformat()
        write(path, report)
    pin = rebuild_capture(root)
    with pytest.raises(ValueError):
        build(case, stock_root=root, expected_capture_hash=pin)


@pytest.mark.parametrize('field,value', [('origin', 'SECTOR_TRIGGER'), ('selection', {}), ('inventory', {})])
def test_rehashed_derived_origin_or_inventory_tampering_cannot_verify(tmp_path, field, value):
    case = source(tmp_path)
    report = build(case)
    report[field] = value
    report['report_hash'] = canonical_hash({k: v for k, v in report.items() if k != 'report_hash'})
    with pytest.raises(ValueError, match='do not rebuild'):
        independent.verify(report, case.root, expected_audit_hash=audit_pin(case))


def test_cli_atomic_create_only_and_input_unchanged(tmp_path):
    case = source(tmp_path)
    output = tmp_path / 'report'
    argv = ['--audit-root', str(case.root), '--audit-hash', audit_pin(case)]
    before = digest_tree(case.root)
    assert independent.main([*argv, '--output', str(output)]) == 0
    saved = digest_tree(output)
    assert set(saved) == {'observations.json', 'README.txt'}
    assert independent.main([*argv, '--verify', str(output)]) == 0
    with pytest.raises(FileExistsError): independent.main([*argv, '--output', str(output)])
    with pytest.raises(ValueError, match='outside source'): independent.main([*argv, '--output', str(case.root/'new')])
    assert digest_tree(case.root) == before and digest_tree(output) == saved


@pytest.mark.parametrize('size', [0, 17, True, -1])
def test_sample_bound_is_exact(tmp_path, size):
    case = source(tmp_path)
    with pytest.raises(ValueError, match='between 1 and 16'): build(case, sample_size=size)


@pytest.mark.parametrize('status', [201, 401, 500, True, None, '200'])
def test_rehashed_stock_http_receipt_must_be_exact_200(tmp_path, status):
    case = source(tmp_path)
    root, _ = capture(case)
    report = independent._load(root / 'capture.json')
    report['requests'][0]['http_status'] = status
    write(root / 'capture.json', report)
    pin = rebuild_capture(root)
    with pytest.raises(ValueError, match='response missing'):
        build(case, stock_root=root, expected_capture_hash=pin)


def test_sector_audit_does_not_invent_an_unrecorded_http_status(tmp_path):
    case = source(tmp_path)
    manifest = independent._load(case.root / 'manifest.json')
    assert 'http_status' not in manifest['requests'][0]
    # Its existing exact schema records decoded JSON / transport error_type,
    # not HTTP status. Adding a purported receipt is rejected, not trusted.
    manifest['requests'][0]['http_status'] = 200
    write(case.root / 'manifest.json', manifest); rebuild_audit(case)
    with pytest.raises(audit.SectorRadarAuditError, match='fields disagree'):
        build(case)


@pytest.mark.parametrize('damage', ['changed_readme', 'missing_readme', 'extra', 'symlink'])
def test_cli_verifies_whole_published_pair(tmp_path, damage):
    case = source(tmp_path)
    output = tmp_path / 'report'
    argv = ['--audit-root', str(case.root), '--audit-hash', audit_pin(case)]
    independent.main([*argv, '--output', str(output)])
    if damage == 'changed_readme': (output / 'README.txt').write_text('contradictory certification')
    elif damage == 'missing_readme': (output / 'README.txt').unlink()
    elif damage == 'extra': (output / 'extra.txt').write_text('unbound')
    else:
        raw = (output / 'README.txt').read_bytes(); (output / 'README.txt').unlink()
        (tmp_path / 'outside.txt').write_bytes(raw); (output / 'README.txt').symlink_to(tmp_path/'outside.txt')
    with pytest.raises(ValueError): independent.main([*argv, '--verify', str(output)])


def test_unplanned_extra_page_and_missing_page_cli_have_no_published_output(tmp_path):
    case = source(tmp_path)
    manifest = independent._load(case.root / 'manifest.json')
    record = deepcopy(manifest['requests'][-1]); record['response_file'] = 'responses/0005.json'
    record['params']['offset'] = '1000'; manifest['requests'].append(record)
    write(case.root / record['response_file'], {'code': 0, 'data': {'timestamp': int(case.at.timestamp()*1000),
                                                               'total': 503, 'item': []}})
    manifest['files'][record['response_file']] = {}; write(case.root/'manifest.json', manifest)
    rebuild_audit(case)
    out = tmp_path/'result'
    with pytest.raises(ValueError, match='extra unconsumed'):
        independent.main(['--audit-root', str(case.root), '--audit-hash', audit_pin(case), '--output', str(out)])
    assert not out.exists()
