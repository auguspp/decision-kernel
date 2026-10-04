"""Synthetic saved-source checks; actual fixed native engine, no market requests."""
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import d_price_structure as d
from decision_kernel.runtime import d_price_structure_reading as reading
from decision_kernel.runtime import current_state as model

AT = '2026-10-04T12:00:00+00:00'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a, **k):
        raise AssertionError('No network in structure tests')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def synthetic(n=80):
    bars = []; day = date(2026, 1, 5)
    while len(bars) < n:
        if day.weekday() < 5:
            i = len(bars); close = Decimal(100 + ((i // 7) % 2 * 2 - 1) * (i % 7) * 2 + i // 14)
            ms = int(datetime.combine(day, datetime.min.time(), tzinfo=d.ZONE).timestamp() * 1000)
            bars.append({'session': day.isoformat(), 'source_date_ms': ms, 'open': str(close - 1),
                         'close': str(close), 'high': str(close + 2), 'low': str(close - 3),
                         'source_volume': '1000.000', 'source_turnover': '100000.000'})
        day += timedelta(days=1)
    return {'subject': '000300.SH', 'subject_type': 'BENCHMARK_INDEX_NOT_STOCK_COHORT', 'interval': '1d',
            'source_adjust': None, 'requested_adjust': 'OMITTED',
            'geometry': 'PROVIDER_INDEX_OHLC_NO_EXTRA_ADJUSTMENT',
            'source_captured_at': AT, 'historical_public_availability': 'NOT_ESTABLISHED', 'bars': bars}


def archive_fixture():
    src = synthetic(20); bars = src['bars']
    calendar = {'code': 0, 'data': {'item': [{'date': b['session'].replace('-', '')} for b in bars]}}
    history = {'code': 0, 'data': {'thscode': src['subject'], 'interval': '1d', 'adjust': None,
        'timestamp': bars[-1]['source_date_ms'], 'item': [dict(date_ms=b['source_date_ms'],
        open_price=b['open'], close_price=b['close'], high_price=b['high'], low_price=b['low'],
        volume=b['source_volume'], turnover=b['source_turnover']) for b in bars]}}
    files = {'input-audit/responses/calendar.json': d.encode(calendar),
             'input-audit/responses/history.json': d.encode(history)}
    result = {'benchmark_thscode': src['subject'], 'market_session': bars[-1]['session']}
    result['result_hash'] = canonical_hash(result); files['result.json'] = d.encode(result)
    audit = {'provenance': 'LIVE_HITHINK', 'status': 'SUCCEEDED', 'requests': [
        {'path': reading.CALENDAR_PATH, 'params': {}, 'error_type': None, 'captured_at': AT,
         'response_file': 'responses/calendar.json'},
        {'path': reading.HISTORY_PATH, 'params': {'thscode': src['subject'], 'interval': '1d',
         'start': str(bars[0]['source_date_ms']), 'end': str(bars[-1]['source_date_ms'] + 86399999)},
         'error_type': None, 'captured_at': AT, 'response_file': 'responses/history.json'}]}
    return reseal(files, audit), audit


def reseal(files, audit):
    audit['files'] = {k.removeprefix('input-audit/'): {'bytes': len(v), 'sha256': model.sha256(v)}
                      for k, v in files.items() if k.startswith('input-audit/') and not k.endswith('manifest.json')}
    audit.pop('audit_hash', None); audit['audit_hash'] = canonical_hash(audit)
    files['input-audit/manifest.json'] = d.encode(audit)
    return files


def test_native_prefixes_rebuild_determinism_and_source_immutability():
    from czsc import CZSC
    src = synthetic(40); before = d.encode(src)
    first = d.project(src, computed_at=AT); second = d.project(src, computed_at=AT)
    assert first == second and d.encode(src) == before
    for n, row in enumerate(first['prefix_checks'], 1):
        engine = CZSC([d.make_bar(src, b, i) for i, b in enumerate(src['bars'][:n])], **d.PARAMETERS)
        assert row['state_hash'] == canonical_hash(d.snapshot(engine))
        assert row['input_prefix_hash'] == canonical_hash(src['bars'][:n])
    assert first['algorithm']['version'] == '1.0.1'
    assert first['parameters'] == {'max_bi_num': 50, 'min_bi_len': 6}
    assert all(e['prefix_count'] <= len(src['bars']) for e in first['replay_events'])
    assert first['investment_authority'] == 'NONE' and not first['odds_recomputed']


def test_float_bindings_preserve_original_decimal_strings():
    src = synthetic(4); src['bars'][0].update(open='99.0100', close='100.0300')
    out = d.project(src, computed_at=AT)
    for bar, row in zip(src['bars'], out['native_binding'], strict=True):
        for source_key, native in d.FIELDS.items():
            value = row['fields'][native]
            assert value['source_decimal'] == bar[source_key]
            assert value['hex'] == float(Decimal(bar[source_key])).hex()
    assert out['native_binding'][0]['fields']['open']['source_decimal'] == '99.0100'


@pytest.mark.parametrize('damage', ['date', 'duplicate', 'float', 'negative', 'geometry', 'basis', 'subject'])
def test_invalid_geometry_is_local(damage):
    src = synthetic(4)
    if damage == 'date': src['bars'][0]['source_date_ms'] += 86400000
    elif damage == 'duplicate': src['bars'][1] = deepcopy(src['bars'][0])
    elif damage == 'float': src['bars'][0]['close'] = 1.0
    elif damage == 'negative': src['bars'][0]['source_volume'] = '-1'
    elif damage == 'geometry': src['bars'][0]['high'] = '1'
    elif damage == 'basis': src['source_adjust'] = 'qfq'
    else: src['subject'] = '00123'
    with pytest.raises((ValueError, TypeError)): d.validate_input(src)


def test_one_bar_remains_a_valid_input_not_a_160_bar_gate():
    out = d.project(synthetic(1), computed_at=AT)
    assert out['bar_count'] == 1 and out['state']['bi_list'] == []
    assert out['baseline']['ranges']['60']['status'] == 'INSUFFICIENT_PREFIX'


def test_same_input_forward_window_roll_and_revision_are_separate():
    old = d.project(synthetic(35), computed_at=AT); new = d.project(synthetic(36), computed_at=AT)
    assert d.compare(old, old)['status'] == 'UNCHANGED_INPUT_NOT_NEW_MARKET_EVENT'
    assert d.compare(old, new)['status'] == 'APPENDED_MARKET_SESSIONS'
    rolled = deepcopy(new); rolled['input_members'] = rolled['input_members'][1:]
    assert d.compare(old, rolled)['status'] == 'LOOKBACK_CHANGED_NOT_PURE_FORWARD_CHANGE'
    changed = deepcopy(new); changed['input_members'][1]['hash'] = 'c' * 64
    assert d.compare(old, changed)['status'] == 'SOURCE_HISTORY_REVISED_NOT_PURE_FORWARD_CHANGE'
    other = deepcopy(new); other['subject'] = '000001.SH'
    assert d.compare(old, other)['status'] == 'METHOD_OR_SUBJECT_CHANGED_NOT_COMPARABLE'
    assert d.compare(new, old)['status'] == 'NON_ADVANCING_WINDOW_NOT_NEW_MARKET_EVENT'


def test_actual_observation_clock_never_inherits_geometric_dates():
    old = d.project(synthetic(35), computed_at=AT)
    old['observed_strokes'] = d.observed_strokes(old, None)
    new = d.project(synthetic(36), computed_at='2026-10-04T13:00:00+00:00')
    rows = d.observed_strokes(new, old)
    old_map = {r['key']: r for r in old['observed_strokes']}
    for row in rows:
        assert row['first_observed_at'] in (AT, new['computed_at'])
        if row['key'] in old_map:
            assert row['first_observed_at'] == old_map[row['key']]['first_observed_at']


def test_saved_source_normalizes_without_fixed_response_names_or_dates():
    files, audit = archive_fixture()
    out = reading.normalize_archive(files, {'artifact_id': 123}, AT)
    assert out['bars'] == synthetic(20)['bars']
    assert out['response_file'] == 'input-audit/responses/history.json'
    assert out['subject'] == '000300.SH'
    assert out['archive'] == {'artifact_id': 123}


@pytest.mark.parametrize('damage', ['hash', 'missing', 'gap', 'duplicate', 'wrong-subject', 'future', 'truncated', 'request-error'])
def test_saved_source_rejections_do_not_fabricate_geometry(damage):
    files, audit = archive_fixture()
    path = 'input-audit/responses/history.json'; history = json.loads(files[path])
    if damage == 'hash': files[path] += b' '; return reject(files)
    if damage == 'missing': del files[path]; return reject(files)
    if damage == 'gap': del history['data']['item'][3]
    elif damage == 'duplicate': history['data']['item'][3] = deepcopy(history['data']['item'][2])
    elif damage == 'wrong-subject': history['data']['thscode'] = '000001.SH'
    elif damage == 'future': audit['requests'][1]['captured_at'] = '2099-01-01T00:00:00Z'
    elif damage == 'truncated': history['data']['has_more'] = True
    else: audit['requests'][1]['error_type'] = 'ConnectionError'
    files[path] = d.encode(history); reseal(files, audit); reject(files)


def reject(files):
    with pytest.raises((ValueError, KeyError, TypeError)):
        reading.normalize_archive(files, {}, AT)


def test_later_sector_failure_does_not_destroy_complete_benchmark():
    files, audit = archive_fixture(); del files['result.json']
    files['input-audit/inputs/market-state.json'] = d.encode({'benchmark': {'thscode': '000300.SH'}})
    audit['status'] = 'FAILED'; audit['error_type'] = 'MembershipRequestError'; reseal(files, audit)
    assert len(reading.normalize_archive(files, {}, AT)['bars']) == 20


def test_native_worker_runs_normal_public_module():
    source = synthetic(12)
    source['source_captured_at'] = '2026-01-31T18:00:00+00:00'
    out = reading.run_native(source)
    assert out['input_hash'] == canonical_hash(source['bars'])
    assert out['bar_count'] == 12 and out['algorithm'] == d.ALGORITHM
