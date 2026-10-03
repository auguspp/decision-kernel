from datetime import datetime, timedelta, timezone
import json

import pytest

from decision_kernel.runtime import stock_market_inputs as m

NOW = datetime(2026, 10, 3, 8, tzinfo=timezone.utc)


def body(api, fields, rows, **extra):
    return m.dumps({'code': 0, 'api_name': api, 'data': {'fields': fields, 'items': rows}, **extra})


def calendar_body(at=NOW):
    query = m.calendar_plan(at)['params']; start, end = m.day(query['start_date']), m.day(query['end_date'])
    rows = []
    for i in range((end-start).days+1):
        d = start+timedelta(days=i)
        rows.append(['SSE', d.strftime('%Y%m%d'), int(d.weekday() < 5 and not (d.month == 10 and d.day <= 7))])
    return body('trade_cal', ['exchange', 'cal_date', 'is_open'], rows)


def test_dates_follow_calendar_not_frozen_september():
    first = m.calendar(calendar_body(), NOW)
    later_at = datetime(2026, 10, 15, 8, tzinfo=timezone.utc)
    later = m.calendar(calendar_body(later_at), later_at)
    assert first['market_session'] == '2026-09-30'
    assert later['market_session'] == '2026-10-15'
    assert m.price_plan(first) != m.price_plan(later)
    assert len(m.price_plan(later)) == 8
    assert all('ts_code' not in q['params'] for q in m.price_plan(later))


def test_intraday_does_not_use_todays_close():
    at = datetime(2026, 10, 15, 2, tzinfo=timezone.utc)
    assert m.calendar(calendar_body(at), at)['market_session'] == '2026-10-14'


def test_calendar_gap_only_blocks_dependent_windows():
    raw = json.loads(calendar_body()); rows = raw['data']['items']
    raw['data']['items'] = [r for r in rows if r[1] >= '20260901']
    context = m.calendar(m.dumps(raw), NOW)
    assert context['bases']['5'] is not None
    assert context['bases']['60'] is None


def make_request(at=NOW, *, fail=None):
    def request(api, params):
        if api == 'trade_cal':
            raw = calendar_body(at)
        else:
            d = params['trade_date']; end = m.calendar(calendar_body(at), at)['end_date']
            fields = ['ts_code', 'trade_date', 'close' if api == 'daily' else 'adj_factor']
            rows = [['600000.SH', d, '12' if d == end else '10']] if api == 'daily' else [['600000.SH', d, '1']]
            if d == end:
                rows.append(['001246.SZ', d, '20' if api == 'daily' else '1'])
            raw = body(api, fields, rows)
        status = 'SOURCE_UNAVAILABLE' if fail == (api, params.get('trade_date')) else 'SUCCESS'
        return {'api': api, 'params': params, 'status': status, 'attempts': [{'attempt': 1, 'http_status': 200,
            'raw': raw, 'requested_at': at.isoformat(), 'received_at': at.isoformat(), 'classification': status}]}
    return request


def test_capture_replay_dynamic_universe_endpoint_only(tmp_path):
    root = tmp_path/'capture'
    report = m.capture(root, observed_at=NOW, workflow={'test': True}, request=make_request(), clock=NOW.isoformat)
    assert report['source_requests'] == 9
    assert report['cohort_denominator'] == 2
    assert report['qualified_windows'] == {'5': 1, '20': 1, '60': 1}
    assert report['rows'][0][0] == '001246.SZ' and report['rows'][0][5:] == [2, 2, 2]
    assert report['rows'][1][2:5] == ['0.200000000000']*3
    assert m.verify(root, expected_workflow={'test': True}) == report
    assert 'Sector' not in json.dumps(json.loads((root/'receipt.json').read_bytes()))


def test_one_missing_factor_date_does_not_kill_other_windows(tmp_path):
    context = m.calendar(calendar_body(), NOW)
    report = m.capture(tmp_path/'capture', observed_at=NOW, workflow={},
        request=make_request(fail=('adj_factor', context['bases']['60'])), clock=NOW.isoformat)
    assert report['qualified_windows'] == {'5': 1, '20': 1, '60': 0}
    assert report['rows'][1][5:] == [0, 0, 3]


def test_auth_stops_supplier_without_retrying_other_dates(tmp_path):
    fetch = make_request(); count = []
    def request(api, params):
        count.append(api)
        if api == 'daily':
            result = fetch(api, params); result['status'] = 'AUTH_OR_ENTITLEMENT'
            result['attempts'][0]['classification'] = result['status']; return result
        return fetch(api, params)
    report = m.capture(tmp_path/'capture', observed_at=NOW, workflow={}, request=request, clock=NOW.isoformat)
    assert count == ['trade_cal', 'daily']
    assert not report['rows']


def test_price_qualification_does_not_require_unused_ohlcv():
    item = {'api': 'daily', 'params': {'trade_date': '20260930'}}
    rows, info = m.keyed(body('daily', ['ts_code','trade_date','close'], [['600000.SH','20260930','12']]), item)
    assert rows['600000.SH']['close'] == '12' and info['returned_rows'] == 1


@pytest.mark.parametrize('bad', [None, True, 'NaN', 'Infinity', '-2', '0'])
def test_bad_price_is_not_turned_into_a_zero_change(bad):
    context = {'end_date': '20260930', 'market_session':'2026-09-30', 'bases': {'5':'20260922','20':None,'60':None}}
    tables = {('daily','20260930'): {'600000.SH':{'close':bad}}, ('daily','20260922'):{'600000.SH':{'close':'10'}},
        ('adj_factor','20260930'):{'600000.SH':{'adj_factor':'1'}}, ('adj_factor','20260922'):{'600000.SH':{'adj_factor':'1'}}}
    report = m.evaluate(context, tables, {})
    assert report['cohort_denominator'] == 1 and report['rows'][0][2] is None and report['rows'][0][5] == 4


def test_duplicates_wrong_dates_and_truncation_are_visible():
    item = {'api':'daily','params':{'trade_date':'20260930'}}
    rows, info = m.keyed(body('daily', ['ts_code','trade_date','close'],
        [['600000.SH','20260930','12'], ['600000.SH','20260930','13'], ['600001.SH','20260929','3'],
         ['600002.SH','20260930','2']], count=10), item)
    assert set(rows) == {'600002.SH'}
    assert info['possibly_truncated'] and info['duplicate_symbols'] == ['600000.SH']
    assert info['rejected_row_positions'] == [1, 2]


def test_tampered_raw_or_report_does_not_publish(tmp_path):
    root = tmp_path/'capture'
    m.capture(root, observed_at=NOW, workflow={}, request=make_request(), clock=NOW.isoformat)
    (root/'report.json').write_text('{}')
    with pytest.raises(ValueError, match='REPLAY_DIFFERS'):
        m.verify(root)


def test_arbitrary_workflow_cannot_call_live_capture():
    with pytest.raises(ValueError, match='EXECUTION_IDENTITY'):
        m.workflow_identity({'GITHUB_REPOSITORY':'auguspp/decision-kernel'})
