"""D derived-purpose controls; no source I/O, economic or intraday certification."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal

import pytest

from decision_kernel.runtime.d_market_expression import close_structure, member_expression, render


def prices():
    return {'columns': ['symbol', 'raw_close', 'change_5', 'change_20', 'change_60',
                        'status_5', 'status_20', 'status_60'],
            'bases': {'5': '20260922', '20': '20260901', '60': '20260707'},
            'market_session': '2026-09-30', 'cohort_denominator': 3,
            'comparison_basis': 'PROVIDER_ADJUSTED_PRICE_NOT_TOTAL_RETURN',
            'rows': [['000001.SZ', '10', '0.2', '-0.1', None, 0, 0, 2],
                     ['000002.SZ', '11', '0.2', '0.1', '0.3', 0, 0, 0],
                     ['000003.SZ', '12', '-0.2', '0', '0.1', 0, 0, 0]]}


def groups():
    return [{'code': '884001.TI', 'name': 'Actual child', 'parent_group_key': '881101.TI',
             'membership_market_session': '2026-09-29', 'members': [
                 {'symbol': '000001.SZ', 'name': 'One'},
                 {'symbol': '000002.SZ', 'name': 'Two'},
                 {'symbol': '000003.SZ', 'name': 'Three'},
                 {'symbol': '000004.SZ', 'name': 'Missing'}]}]


def test_member_gaps_ties_signed_medians_and_no_input_mutation():
    source, universe = prices(), groups()
    before = deepcopy((source, universe))
    result = member_expression(source, universe)
    group = result['groups'][0]
    assert group['code'] == '884001.TI' and group['parent_group_key'] == '881101.TI'
    assert group['membership_market_session'] == '2026-09-29'
    assert result['market_session'] == '2026-09-30'
    assert group['member_count'] == 4
    assert group['windows']['5']['comparable'] == 3
    assert group['windows']['5']['median_return'] == '0.2'
    assert group['windows']['20']['median_return'] == '0'
    assert group['windows']['60']['comparable'] == 2
    assert group['windows']['60']['median_return'] == '0.2'
    assert group['windows']['5']['ranking_scope'] == 'COMPARABLE_SUBSET'
    assert [r['windows']['5']['rank'] for r in group['rows']] == [1, 1, 3, None]
    assert group['rows'][0]['windows']['60']['source_status'] == 2
    assert group['rows'][3]['windows']['5']['source_status'] == 'END_IDENTITY_NOT_RETURNED'
    assert group['rows'][2]['windows']['5']['relative_to_median'] == '-0.4'
    assert (source, universe) == before
    assert result['investment_authority'] == 'NONE' and not result['automatic_research_routing']
    assert 'Actual child' in render(result)


@pytest.mark.parametrize('bad', ['duplicate_price', 'duplicate_member', 'wrong_denominator',
                               'qualified_null', 'failed_value', 'nan', 'float'])
def test_rejects_conflicts_not_repairs(bad):
    source, universe = prices(), groups()
    if bad == 'duplicate_price':
        source['rows'].append(source['rows'][0]); source['cohort_denominator'] += 1
    elif bad == 'duplicate_member':
        universe[0]['members'].append(universe[0]['members'][0])
    elif bad == 'wrong_denominator':
        source['cohort_denominator'] = 100
    elif bad == 'qualified_null':
        source['rows'][0][2] = None
    elif bad == 'failed_value':
        source['rows'][0][5] = 2
    elif bad == 'nan':
        source['rows'][0][2] = 'NaN'
    elif bad == 'float':
        source['rows'][0][2] = 0.2
    with pytest.raises(ValueError):
        member_expression(source, universe)


def test_empty_groups_and_all_unavailable_are_not_no_opportunity():
    assert member_expression(prices(), [])['group_count'] == 0
    universe = groups(); universe[0]['members'] = [{'symbol': '000004.SZ', 'name': 'Missing'}]
    result = member_expression(prices(), universe)
    assert result['groups'][0]['windows']['5']['median_return'] is None
    assert result['groups'][0]['windows']['5']['top_symbols'] == []
    assert result['meaning'] == 'DECLARED_MEMBERS_PRICE_CONTEXT_NOT_OPPORTUNITY_ODDS'


def test_confirmed_turn_does_not_use_turn_day_as_confirmation_day():
    sessions = ['2026-09-21', '2026-09-22', '2026-09-23', '2026-09-24']
    first = close_structure(sessions[:2], ['10', '12'], (1, 3))
    assert first['last_confirmed_turn'] is None
    assert first['current_candidate']['status'] == 'UNCONFIRMED_RIGHT_BAR_NOT_AVAILABLE'
    third = close_structure(sessions[:3], ['10', '12', '11'], (1, 3))
    assert third['last_confirmed_turn'] == {'kind': 'CLOSE_PEAK', 'turn_session': '2026-09-22',
        'confirmed_session': '2026-09-23', 'close': '12'}
    fourth = close_structure(sessions, ['10', '12', '11', '9'], (1, 3))
    assert fourth['last_confirmed_turn'] == third['last_confirmed_turn']
    assert fourth['ranges']['3']['status'] == 'BELOW_PRECEDING_CLOSE_RANGE'
    assert first == close_structure(sessions[:2], ['10', '12'], (1, 3))


def test_range_excludes_current_close_and_does_not_synthesize_high_low():
    result = close_structure(['2026-09-21', '2026-09-22', '2026-09-23'], ['10', '11', '14'], (2, 20))
    assert result['ranges']['2']['upper'] == '11'
    assert result['ranges']['2']['status'] == 'ABOVE_PRECEDING_CLOSE_RANGE'
    assert result['ranges']['20']['status'] == 'INSUFFICIENT_PREFIX'
    assert result['input_basis'] == 'CLOSE_ONLY_NOT_OHLC_OR_CHAN'
    flat = close_structure(['2026-09-21', '2026-09-22', '2026-09-23'], ['10']*3, (2,))
    assert flat['current_candidate'] is None
    assert flat['last_confirmed_turn'] is None
    assert flat['ranges']['2']['status'] == 'AT_CLOSE_RANGE_BOUNDARY'


@pytest.mark.parametrize('sessions,values,windows', [
    (['2026-09-22', '2026-09-21'], ['1', '2'], (1,)),
    (['2026-09-22', '2026-09-22'], ['1', '2'], (1,)),
    (['2026-09-22'], ['0'], (1,)),
    (['2026-09-22'], ['NaN'], (1,)),
    (['2026-09-22'], ['oops'], (1,)),
    (['2026-09-22'], ['1'], (0,)),
    (['2026-09-22'], ['1'], (1, 1)),
])
def test_structure_invalid_inputs(sessions, values, windows):
    with pytest.raises(ValueError):
        close_structure(sessions, values, windows)


def test_longer_warmup_preserves_same_bounded_range_but_not_claims_full_chan_stability():
    sessions = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(90)]
    closes = [str(100+(i % 9)) for i in range(90)]
    full = close_structure(sessions, closes, (5, 20))
    short = close_structure(sessions[-21:], closes[-21:], (5, 20))
    assert full['ranges'] == short['ranges']
    assert full['knowledge_semantics'] == 'PREFIX_ARITHMETIC_NOT_HISTORICAL_AVAILABILITY_PROOF'


def test_decimal_context_does_not_change_member_median():
    from decimal import localcontext
    with localcontext() as ctx:
        ctx.prec = 3
        result = member_expression(prices(), groups())
    assert result['groups'][0]['windows']['5']['median_return'] == '0.2'


def retained_reader_fixture(tmp_path):
    """Synthetic provider data, real archive, normalizer and Collector boundary."""
    import io
    import json
    from types import SimpleNamespace
    from zipfile import ZipFile, ZIP_DEFLATED
    from decision_kernel.identity import canonical_hash, canonical_json
    from decision_kernel.runtime import current_state as model
    from decision_kernel.runtime.current_state_delivery import Collector
    from decision_kernel.runtime.hithink_sector_breadth_http import HITHINK_SECTOR_CONSTITUENTS_PATH

    collector = Collector(SimpleNamespace(calls=0, max_calls=1000), 'a'*40, tmp_path)
    collector.files['README.md'] = b'original navigation\n'
    price_raw = json.dumps(prices()).encode()
    descriptor = collector.retain('details/stock/daily-market-inputs.json', price_raw)
    body = json.dumps({'code': 0, 'data': {'timestamp': 1790763404811, 'item': [
        {'thscode': row['symbol'], 'ticker': row['symbol'].split('.')[0], 'name': row['name']}
        for row in groups()[0]['members']]}}).encode()
    manifest = {'requests': [{'path': HITHINK_SECTOR_CONSTITUENTS_PATH,
        'params': {'thscode': '884001.TI'}, 'response_file': 'responses/0001.json', 'error_type': None}],
        'files': {'responses/0001.json': {'bytes': len(body), 'sha256': model.sha256(body)}}}
    source = {'market_session': '2026-09-30', 'composition': {'all_groups': [
        {'group_key': '881101.TI', 'primary_candidate': {'thscode': '884001.TI', 'name': 'Actual child'}}]}}
    source['result_hash'] = canonical_hash(source)
    files = {'result.json': canonical_json(source).encode(),
        'input-audit/manifest.json': json.dumps(manifest).encode(),
        'input-audit/responses/0001.json': body}
    stream = io.BytesIO()
    with ZipFile(stream, 'w', ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    raw = stream.getvalue()
    ref = collector.retain('sources/artifacts/'+model.sha256(raw)+'.zip', raw)
    ref.update(artifact_id=1, expires_at='2099-01-01T00:00:00Z',
               origin_run={'id': 101, 'head_sha': 'a'*40})
    collector.archive_cache[1] = (files, ref)
    baseline = {'checks': {'finished_at': '2026-10-04T00:00:00Z'}, 'lanes': {'sector': {
        'last_qualified_result': {'archive': ref, 'market_session': '2026-09-30'}}}}
    daily = {'status': 'PRICE_INPUTS_AVAILABLE_WITH_GAPS', 'file': descriptor,
        'qualified_windows': {'5': 3, '20': 3, '60': 2},
        'received_through': '2026-10-03T13:18:00Z'}
    return collector, baseline, daily


def test_retained_reader_uses_real_archive_and_keeps_structure_separate(tmp_path):
    import json
    from decision_kernel.runtime.d_market_expression import read_saved, PATH
    c, baseline, daily = retained_reader_fixture(tmp_path)
    original = deepcopy((baseline, daily, c.files))
    result = read_saved(c, baseline, daily)
    assert result['status'] == 'D_SAVED_EXPRESSION_READ_OK'
    report = json.loads(c.files[PATH])
    assert report['groups'][0]['member_count'] == 4
    assert report['groups'][0]['name'] == 'Actual child'
    assert report['groups'][0]['windows']['60']['comparable'] == 2
    assert report['structure_status'] == 'NOT_AVAILABLE' and report['structure_gap'] == 'KeyError'
    assert report['price_file'] == daily['file']
    assert report['price_received_through'] == daily['received_through']
    assert not report['using_last_qualified_result']
    assert c.api.calls == 0 and baseline == original[0] and daily == original[1]
    assert {k: v for k, v in c.files.items() if k != PATH} == original[2]


def test_retained_reader_uses_exact_saved_result_without_replacing_failed_attempt(tmp_path):
    import json
    from decision_kernel.runtime.d_market_expression import read_saved, PATH
    c, baseline, saved = retained_reader_fixture(tmp_path)
    daily = {'status': 'PRICE_INPUT_UNAVAILABLE_NOT_QUIET', 'qualified_windows': {'5': 0},
             'last_qualified_result': saved}
    before = deepcopy(daily)
    assert read_saved(c, baseline, daily)['status'] == 'D_SAVED_EXPRESSION_READ_OK'
    report = json.loads(c.files[PATH])
    assert report['using_last_qualified_result']
    assert report['latest_price_attempt_status'] == 'PRICE_INPUT_UNAVAILABLE_NOT_QUIET'
    assert daily == before and c.api.calls == 0


@pytest.mark.parametrize('damage', ['archive', 'price', 'budget', 'missing_sector'])
def test_derived_failure_keeps_original_prices_and_prior_output(tmp_path, damage):
    from decision_kernel.runtime.d_market_expression import read_saved, PATH
    c, baseline, daily = retained_reader_fixture(tmp_path)
    c.files[PATH] = b'previous result'
    if damage == 'archive':
        ref = baseline['lanes']['sector']['last_qualified_result']['archive']
        c.files[ref['read_path']] += b'changed'
    elif damage == 'price':
        c.files[daily['file']['read_path']] += b'changed'
    elif damage == 'budget':
        c.api.max_calls = 0
    else:
        baseline['lanes']['sector']['last_qualified_result'] = None
    before = deepcopy((c.files, daily))
    result = read_saved(c, baseline, daily)
    assert result['status'] == 'D_EXPRESSION_READING_GAP'
    assert c.files == before[0] and daily == before[1] and c.api.calls == 0


def test_normal_daily_reader_preserves_independent_input_when_d_has_no_sector(tmp_path, monkeypatch):
    from test_stock_market_input_reading import fixtures
    from decision_kernel.runtime.stock_market_input_reading import read_current
    c, baseline, _, _, original_report = fixtures(tmp_path, monkeypatch)
    result = read_current(c, baseline)
    assert result['cohort_denominator'] == original_report['cohort_denominator'] == 2
    assert result['qualified_windows'] == original_report['qualified_windows']
    assert result['market_expression']['status'] == 'D_EXPRESSION_READING_GAP'
    assert result['status'] == 'PRICE_INPUTS_AVAILABLE_WITH_GAPS'
