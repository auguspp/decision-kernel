"""Pure synthetic adapter regression. No live service, model or source calls."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
import socket

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import external_radar_observations as obs

CUTOFF = '2026-09-20T04:00:00Z'
PERIOD = dict(price_start='2026-08-01', recent_start='2026-09-01', period_end='2026-09-18', cutoff=CUTOFF)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('adapter attempted networking')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


def raw(value):
    return json.dumps(value, ensure_ascii=False).encode()


def millis(day):
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)


def news_pair(source='cls', items=None):
    body = raw({'id': source, 'status': 'cache', 'updatedTime': millis('2026-09-20T02:00:00'),
                'items': items if items is not None else [{'id': 1, 'title': '公司甲发布新产品',
                                                         'url': 'https://www.cls.cn/detail/1',
                                                         'pubDate': millis('2026-09-19T10:00:00')}]})
    return body, {'label': source, 'url': 'http://127.0.0.1:4444/api/s?id=' + source + '&latest',
                  'status': 'CAPTURED_PUBLIC_RESPONSE', 'http_status': 200, 'bytes': len(body),
                  'sha256': sha256(body).hexdigest(), 'requested_at': '2026-09-20T03:00:00Z',
                  'received_at': '2026-09-20T03:00:01Z'}


def edit(pair, modify):
    body, receipt = pair
    obj = json.loads(body); modify(obj); body = raw(obj); receipt = deepcopy(receipt)
    if 'response_bytes' in receipt:
        receipt.update(response_bytes=len(body), response_sha256=sha256(body).hexdigest())
    else:
        receipt.update(bytes=len(body), sha256=sha256(body).hexdigest())
    return body, receipt


def hp(path, params, items, **extra):
    body = raw({'code': 0, 'data': {'timestamp': millis('2026-09-20T02:00:00'), 'item': items, **extra}})
    return body, {'path': '/api/futures/' + path, 'params': params, 'response_bytes': len(body),
                  'response_sha256': sha256(body).hexdigest(), 'requested_at': '2026-09-20T03:00:00Z',
                  'received_at': '2026-09-20T03:00:01Z', 'status': 'CAPTURED_DECODED_RESPONSE',
                  'representation': 'DECODED_JSON_TOOL_RETURN_NOT_WIRE_BYTES'}


def industry_inputs():
    code = 'LCZL.GFE'
    points = [{'timestamp': millis((datetime(2026, 8, 25) + timedelta(days=i)).isoformat()),
               'close_price': 100+i} for i in range(25)]
    return {
        'identity': hp('basis/main-continuous-latest', {}, [
            {'thscode': code, 'variety_name': '碳酸锂', 'ticker': 'lc9999', 'default_value': 'Y',
             'spot_indicator_id': 'spot-1', 'spot_publish_date': '2026-09-18'},
            {'thscode': code, 'variety_name': '碳酸锂', 'ticker': 'lc9999', 'default_value': 'N',
             'spot_indicator_id': 'spot-2', 'spot_publish_date': '2026-09-18'}]),
        'prices': hp('prices/daily', {'thscode': code, 'start': str(millis('2026-07-31T16:00:00')),
                                     'end': str(millis('2026-09-18T16:00:00')-1)}, points, thscode=code, interval='1d'),
        'basis': hp('basis/historical', {'thscode': code}, [
            {'date': '2026-08-31', 'converted_spot_price': None, 'close_price': None,
             'close_basis': None, 'close_basis_rate': None},
            {'date': '2026-09-11', 'converted_spot_price': 145100, 'close_price': 134820,
             'close_basis': 10280, 'close_basis_rate': 7.09},
            {'date': '2026-09-15', 'converted_spot_price': 137500, 'close_price': 129120,
             'close_basis': 8380, 'close_basis_rate': 6.10}]),
        'warehouse': hp('warehouse-receipts/historical', {'thscode': code, 'start_date': '2026-09-01',
                                                         'end_date': '2026-09-18'}, [
            {'date': '2026-09-11', 'amount': 30}, {'date': '2026-09-15', 'amount': 40}]),
    }


def test_news_rebuild_is_pure_and_keeps_cache_and_clock_meanings():
    pair = news_pair(); before = deepcopy(pair)
    first = obs.news(*pair, cutoff=CUTOFF)
    assert first == obs.news(*pair, cutoff=CUTOFF) and pair == before
    p = first['projection']; row = p['observations'][0]
    assert p['service_status'] == 'cache' and p['service_clock_meaning'] != 'PUBLICATION_TIME'
    assert row['publication_claims']['pubDate']['status'] == 'PARSED_CLAIM_NOT_PUBLISHER_VERIFIED'
    assert row['qualification'] == 'CONTEXT_ONLY' and row['business_linkage'] == 'NOT_ESTABLISHED'
    assert p['model_calls'] == p['network_calls'] == 0 and p['automatic_admission'] is False


@pytest.mark.parametrize('value,status', [(None, 'MISSING_CLAIM'), ('2026-09-19', 'UNPARSEABLE_CLAIM'),
    (True, 'UNPARSEABLE_CLAIM'), (1234567890, 'UNPARSEABLE_CLAIM'),
    ('2026-09-21T01:00:00Z', 'FUTURE_CLAIM')])
def test_publication_claims_do_not_get_filled_or_qualified(value, status):
    pair = edit(news_pair(), lambda v: v['items'][0].update(pubDate=value))
    row = obs.news(*pair, cutoff=CUTOFF)['projection']['observations'][0]
    assert row['publication_claims']['pubDate']['status'] == status
    assert row['question_status'] == 'NOT_FORMED'


@pytest.mark.parametrize('damage', ['hash', 'clock', 'request-id', 'body-source-id', 'missing-source-id',
                                  'userinfo', 'hostname', 'too-many', 'missing-title', 'rebound-id'])
def test_news_rejects_identity_or_window_damage(damage):
    pair = news_pair()
    if damage == 'hash': pair[1]['sha256'] = '0'*64
    elif damage == 'clock': pair[1]['received_at'] = '2026-09-21T04:00:00Z'
    elif damage == 'request-id': pair[1]['url'] = 'https://newsnow.busiyi.world/api/s?id=jin10'
    else:
        def change(v):
            if damage == 'body-source-id': v['id'] = 'jin10'
            elif damage == 'missing-source-id': v.pop('id')
            elif damage == 'userinfo': v['items'][0]['url'] = 'https://cls.cn@evil.invalid/1'
            elif damage == 'hostname': v['items'][0]['url'] = 'https://evilcls.cn/1'
            elif damage == 'too-many': v['items'] *= 31
            elif damage == 'missing-title': v['items'][0]['title'] = ''
            elif damage == 'rebound-id': v['items'].append({**v['items'][0], 'url': 'https://cls.cn/other'})
        pair = edit(pair, change)
    with pytest.raises(ValueError): obs.news(*pair, cutoff=CUTOFF)


def test_unavailable_is_not_no_news():
    body, rec = news_pair(); body = b'<h1>403</h1>'
    rec.update(bytes=len(body), sha256=sha256(body).hexdigest(), http_status=403, status='SOURCE_UNAVAILABLE')
    p = obs.news(body, rec, cutoff=CUTOFF)['projection']
    assert p['status'] == 'SOURCE_UNAVAILABLE' and p['observations'] == []


def test_duplicate_json_keys_rejected_even_when_hash_matches():
    _, rec = news_pair(); body = b'{"id":"cls","id":"jin10"}'
    rec.update(bytes=len(body), sha256=sha256(body).hexdigest())
    with pytest.raises(ValueError, match='DUPLICATE_JSON'): obs.news(body, rec, cutoff=CUTOFF)


def test_event_groups_are_candidates_only_and_never_erase_numbers_or_negation():
    titles = ['订单增加10%', '订单增加100%', '订单未增加10%', '订单增加10%']
    items = [{'id': i, 'title': title, 'url': f'https://cls.cn/detail/{i}'} for i, title in enumerate(titles)]
    captures = [news_pair(items=items)]
    result = obs.news_context(captures, cutoff=CUTOFF)
    p = result['projection']; assert len(p['observations']) == 4
    assert len(p['possible_event_groups']) == 1 and p['possible_event_groups'][0]['event_identity'] == 'UNVERIFIED'
    obs.verify_news(result, captures, cutoff=CUTOFF)
    result['projection']['possible_event_groups'][0]['event_identity'] = 'VERIFIED'
    result['projection_hash'] = canonical_hash(result['projection'])
    with pytest.raises(ValueError, match='DOES_NOT_REBUILD'): obs.verify_news(result, captures, cutoff=CUTOFF)


def test_same_version_is_not_new_event_when_fetched_again():
    pair = news_pair(); later = deepcopy(pair)
    later[1].update(requested_at='2026-09-20T03:10:00Z', received_at='2026-09-20T03:10:01Z')
    result = obs.news_context([pair, later], cutoff=CUTOFF)['projection']
    assert len(result['observations']) == 1 and len(result['sources']) == 2


def test_industry_rebuild_preserves_two_rate_gaps_and_unrelated_price_math():
    captures = industry_inputs(); before = deepcopy(captures)
    result = obs.industry('LC', captures, **PERIOD); p = result['projection']
    assert captures == before and p['thscode'] == 'LCZL.GFE'
    assert 'CONTINUOUS' in p['series_kind'] and p['continuous_roll_composition'] == 'UNKNOWN'
    assert len(p['field_gaps']) == 2 and all(g['cause'] == 'UNKNOWN' for g in p['field_gaps'])
    assert p['basis_rows'][0]['reported_percent'] == '7.09'
    assert p['basis_rows'][0]['reported_fraction'] == '0.0709'
    assert abs(Decimal(p['returns_over_observations']['5']) - (Decimal(124)/119-1)) < Decimal('1e-27')
    assert p['warehouse_delta_raw_unit'] == '10' and p['warehouse_unit'] == 'UNKNOWN'
    assert p['basis_excluded_from_declared_window'] == 1
    assert p['industry_inflection_established'] is False and p['company_materiality'] == 'NOT_ESTABLISHED'
    obs.verify_industry(result, 'LC', captures, **PERIOD)
    p['warehouse_unit'] = 'TONNES'; result['projection_hash'] = canonical_hash(p)
    with pytest.raises(ValueError, match='DOES_NOT_REBUILD'): obs.verify_industry(result, 'LC', captures, **PERIOD)


@pytest.mark.parametrize('damage', ['future-price', 'duplicate-price', 'unordered', 'wrong-price-code', 'wrong-request-code',
                                  'duplicate-default', 'wrong-spot', 'boolean-price', 'nonfinite-price',
                                  'duplicate-basis-date', 'boolean-business-code', 'future-provider-clock'])
def test_industry_rejects_identity_clock_and_numeric_damage(damage):
    c = industry_inputs()
    if damage == 'wrong-request-code': c['prices'][1]['params']['thscode'] = 'LC2609.GFE'
    elif damage == 'wrong-spot': c['basis'][1]['params']['spot_indicator_id'] = 'wrong'
    else:
        key = 'identity' if damage == 'duplicate-default' else 'basis' if damage == 'duplicate-basis-date' else 'prices'
        def change(v):
            rows = v['data']['item']
            if damage == 'future-price': rows[-1]['timestamp'] = millis('2026-09-21T00:00:00')
            elif damage == 'duplicate-price': rows.append(rows[-1])
            elif damage == 'unordered': rows.reverse()
            elif damage == 'wrong-price-code': v['data']['thscode'] = 'CUZL.SHF'
            elif damage == 'duplicate-default': rows[1]['default_value'] = 'Y'
            elif damage == 'boolean-price': rows[-1]['close_price'] = True
            elif damage == 'nonfinite-price': rows[-1]['close_price'] = float('nan')
            elif damage == 'duplicate-basis-date': rows.append(rows[-1])
            elif damage == 'boolean-business-code': v['code'] = False
            elif damage == 'future-provider-clock': v['data']['timestamp'] = millis('2026-09-21T00:00:00')
        c[key] = edit(c[key], change)
    with pytest.raises(ValueError): obs.industry('LC', c, **PERIOD)


def test_nulls_are_not_zero_or_compressed_observations():
    c = industry_inputs()
    c['prices'] = edit(c['prices'], lambda v: v['data']['item'][-3].update(close_price=None))
    c['warehouse'] = edit(c['warehouse'], lambda v: v['data']['item'][-1].update(amount=None))
    p = obs.industry('LC', c, **PERIOD)['projection']
    assert len(p['price_points']) == 25 and p['returns_over_observations'] == {'5': None, '20': None}
    assert p['warehouse_rows'][-1]['amount'] is None and p['warehouse_delta_raw_unit'] is None


def test_explicit_spot_binding_and_same_dated_positions():
    c = industry_inputs(); c['basis'][1]['params']['spot_indicator_id'] = 'spot-1'
    c['positions'] = hp('positions/variety-daily', {'date': '2026-09-18'}, [{'variety_code': 'LC', 'date': '2026-09-18', 'net_position': -3}])
    p = obs.industry('LC', c, **PERIOD)['projection']
    assert p['historical_spot_binding'] == 'EXPLICIT_REQUEST_ID'
    assert p['positions']['net_position'] == '-3' and p['positions']['long_position'] is None
    c['positions'] = edit(c['positions'], lambda v: v['data']['item'][0].update(date='2026-09-17'))
    with pytest.raises(ValueError, match='POSITION_DATE'): obs.industry('LC', c, **PERIOD)
