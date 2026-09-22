"""Synthetic protocol cases; not live contract or investment acceptance."""
from copy import deepcopy
from hashlib import sha256
import csv
import io
import json
from decimal import Decimal

import pytest

from decision_kernel.runtime import easy_stock_context as c

DAY = '2026-09-22'
NOW = '2026-09-22T10:00:00+00:00'


def raw(value):
    return json.dumps(value, ensure_ascii=False).encode()


def receipt(label, body):
    return {'request': next(r for r in c.requests_for(DAY) if r['id'] == label),
        'target_date': DAY, 'requested_at': NOW, 'received_at': NOW,
        'bytes': len(body), 'sha256': sha256(body).hexdigest(), 'http_status': 200,
        'representation': 'RETAINED_HTTP_BODY'}


def market_body(label='tencent-industry'):
    if label == 'tencent-industry':
        return raw({'code': 0, 'data': [{'bd_code': 'BK1', 'bd_name': '测试行业',
            'bd_zdf': '1.25', 'bd_zdf5': '-2.0', 'bd_zdf20': '0',
            'nzg_name': '测试公司', 'nzg_code': 'sh600000', 'nzg_zdf': '3.0'}]})
    return raw({'rc': 0, 'data': {'total': 999, 'diff': [{'f12': '600000' if label.endswith('stock') else 'BK1001',
        'f13': 1, 'f14': 'ST测试' if label.endswith('stock') else '测试板块',
        'f2': '20.1', 'f3': '-1.2', 'f62': '0', 'f104': '10', 'f105': '4',
        'f109': '2.5', 'f24': '88', 'f128': '公司甲', 'f136': '1', 'f8': '3.4'}]}})


def csv_body(variety='IF', contracts=1, citic='both', encoding='utf-8', edit=None):
    rows = [['交易日', '合约', '名次', '会员', '成交量', '增减', '会员', '持买', '增减', '会员', '持卖', '增减']]
    for month in range(10, 10 + contracts):
        for rank in range(1, 21):
            long_name = c.CITIC if rank == 1 and citic in ('both', 'long') else '多头会员' + str(rank)
            short_name = c.CITIC if rank == 2 and citic in ('both', 'short') else '空头会员' + str(rank)
            rows.append(['20260922', variety + f'26{month:02}', str(rank), '成交会员', '100', '2',
                long_name, '100', '-2', short_name, '120', '-5'])
    if edit:
        edit(rows)
    stream = io.StringIO(); csv.writer(stream).writerows(rows)
    return stream.getvalue().encode(encoding)


def project(label, body=None):
    body = body if body is not None else market_body(label)
    return c.normalize(body, receipt(label, body), cutoff=NOW)['projection']


def test_fixed_eight_requests_are_bounded_and_do_not_select_companies_or_dates():
    plan = c.requests_for(DAY)
    assert len(plan) == len({r['id'] for r in plan}) == 8
    assert all(r['params'].get('pn', '1') == '1' for r in plan)
    assert [r['id'] for r in plan[-4:]] == ['cffex-IF', 'cffex-IH', 'cffex-IC', 'cffex-IM']
    assert all('202609/22/' in r['url'] for r in plan[-4:])


def test_tencent_declared_three_horizons_are_not_synthetic_zero_breadth():
    p = project('tencent-industry'); r = p['observations'][0]
    assert r['values']['twenty_day_change_percent'] == '0'
    assert r['values']['five_day_change_percent'] == '-2.0'
    assert 'rising_count' not in r['meta']['available_fields']
    assert r['meta']['stale'] is None and r['meta']['trade_date'] is None
    assert r['meta']['snapshot_id'] is None and r['meta']['next_refresh_at'] is None
    assert r['meta']['carry_forward'] is False and r['meta']['fallback_reason'] is None
    assert 'score' not in r['values'] and p['economic_exposure'] == 'NOT_ESTABLISHED'


@pytest.mark.parametrize('label', ['eastmoney-industry', 'eastmoney-theme', 'eastmoney-stock'])
def test_all_flow_dimensions_keep_real_zero_missing_fields_and_scope(label):
    p = project(label); row = p['observations'][0]
    assert row['values']['main_net_inflow'] == '0'
    assert row['values']['large_net_inflow'] is None
    assert 'large_net_inflow' not in row['meta']['available_fields']
    assert p['coverage']['upstream_total_claim'] == 999 and not p['coverage']['all_market_covered']
    assert p['kind'] == 'MARKET_EXPRESSION' and row['qualification'] == 'CONTEXT_ONLY'
    if label.endswith('stock'):
        assert row['security_id'] == '600000.SH' and row['name'] == 'ST测试'
    if label.endswith('industry'):
        assert row['values']['rising_count'] == 10
        assert row['values']['twenty_day_change_percent'] is None
        assert row['raw']['f24'] == '88'
        assert row['field_gaps'][-1]['status'] == 'QUARANTINED_HORIZON_NOT_ESTABLISHED'


@pytest.mark.parametrize('value', [None, '', '-', '--', 'null', True, [], {}, 'NaN', 'Infinity', 'oops', '12,34', '1e20'])
def test_unavailable_or_invalid_number_never_becomes_zero(value):
    n, status = c.number(value)
    assert n is None and status in {'MISSING', 'INVALID'}


@pytest.mark.parametrize('value,expected', [('0', 0), ('-12', -12), ('1,234', 1234), (5, 5), ('+2', 2)])
def test_signed_integer_and_zero_exact(value, expected):
    assert c.number(value, integer=True) == (expected, 'AVAILABLE')


@pytest.mark.parametrize('label', ['tencent-industry', 'eastmoney-industry'])
def test_empty_is_not_no_activity(label):
    body = raw({'code': 0, 'data': []} if label.startswith('tencent') else {'rc': 0, 'data': {'total': 0, 'diff': []}})
    p = project(label, body)
    assert p['status'] == 'EMPTY_WINDOW_NOT_NO_ACTIVITY' and p['observations'] == []


@pytest.mark.parametrize('encoding', ['utf-8', 'gb18030'])
@pytest.mark.parametrize('variety', c.VARIETIES)
def test_all_returned_contracts_top20_signed_changes_and_exact_citic(variety, encoding):
    p = project('cffex-' + variety, csv_body(variety, contracts=2, encoding=encoding))
    assert len(p['contracts']) == 2 and len(p['rows']) == 40
    assert p['totals']['net_long_position'] == -800
    assert p['totals']['net_short_position'] == 800
    assert p['totals']['net_long_change'] == 120
    assert p['totals']['net_short_change'] == -120
    assert p['totals']['citic_net_long_change'] == 6
    assert p['totals']['citic_net_short_change'] == -6
    assert p['meta']['trade_date'] == DAY and not p['meta']['transport_authenticated']
    assert p['coverage']['exchange_contract_catalog_complete'] == 'NOT_ESTABLISHED'
    assert p['kind'] == 'POSITIONING_CONTEXT' and 'score' not in p
    assert all(p[k] == v for k, v in c.AUTHORITY.items())


@pytest.mark.parametrize('citic', ['long', 'short', 'neither'])
def test_absent_member_side_is_unknown_not_zero(citic):
    p = project('cffex-IF', csv_body(citic=citic))
    assert p['totals']['citic_net_long_change'] is None
    assert not p['coverage']['citic_both_sides_all_returned_contracts']
    assert p['contracts'][0]['citic']['coverage'] == 'MISSING_RANKED_SIDE_UNKNOWN_NOT_ZERO'


def test_fuzzy_citic_name_is_not_the_exact_customer_member():
    body = csv_body(edit=lambda rows: rows[1].__setitem__(6, '中信建投期货(代客)'))
    assert project('cffex-IF', body)['totals']['citic_net_long_change'] is None


@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'wrong_date', 'mixed_variety', 'rank21', 'missing_change', 'negative_position', 'decimal_count', 'duplicate_member', 'bad_contract'])
def test_incomplete_or_mismatched_csv_rejected_not_partial_top20(damage):
    def edit(rows):
        if damage == 'missing': rows.pop()
        elif damage == 'duplicate': rows.append(list(rows[1]))
        elif damage == 'wrong_date': rows[1][0] = '20260921'
        elif damage == 'mixed_variety': rows[1][1] = 'IH2610'
        elif damage == 'rank21': rows[1][2] = '21'
        elif damage == 'missing_change': rows[1][8] = '--'
        elif damage == 'negative_position': rows[1][7] = '-1'
        elif damage == 'decimal_count': rows[1][7] = '1.5'
        elif damage == 'duplicate_member': rows[2][6] = rows[1][6]
        else: rows[1][1] = 'IF2613'
    with pytest.raises(ValueError): project('cffex-IF', csv_body(edit=edit))


@pytest.mark.parametrize('damage', ['hash', 'bytes', 'path', 'params', 'future', 'unzone', 'http', 'representation', 'target'])
def test_exact_request_body_clock_binding(damage):
    body = market_body(); r = receipt('tencent-industry', body)
    if damage == 'hash': r['sha256'] = '0' * 64
    elif damage == 'bytes': r['bytes'] += 1
    elif damage == 'path': r['request']['url'] = 'https://example.com/'
    elif damage == 'params': r['request']['params']['p'] = '2'
    elif damage == 'future': r['received_at'] = '2026-09-23T00:00:00Z'
    elif damage == 'unzone': r['requested_at'] = '2026-09-22T10:00:00'
    elif damage == 'http': r['http_status'] = 403
    elif damage == 'representation': r['representation'] = 'DECODED_OBJECT'
    else: r['target_date'] = '2026-09-23'
    with pytest.raises(ValueError): c.normalize(body, r, cutoff=NOW)


@pytest.mark.parametrize('body', [b'{"code":0,"code":1,"data":[]}', b'{"code":0,"data":[NaN]}'])
def test_duplicate_keys_and_nonfinite_json_rejected(body):
    with pytest.raises(ValueError): project('tencent-industry', body)


def test_same_source_content_keeps_version_across_fetch_clocks():
    body = market_body(); r = receipt('tencent-industry', body)
    a = c.normalize(body, r, cutoff=NOW)['projection']['observations'][0]
    r['requested_at'] = r['received_at'] = '2026-09-22T10:01:00Z'
    b = c.normalize(body, r, cutoff=r['received_at'])['projection']['observations'][0]
    assert a['version_id'] == b['version_id'] and a['observation_id'] == b['observation_id']
