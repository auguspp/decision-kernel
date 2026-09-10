"""Regress run 34452107559 without any live request or new market conclusion.

The JSON fixture contains retained first-issuer records and source-context
excerpts. A TEST-ONLY endpoint below applies inclusive/exclusive timestamp
selection; the second issuer's prices in that test are wholly synthetic. Neither
that mock nor its result is production evidence or a recertified failed run.
"""
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import hithink_stock_reading as own
from decision_kernel.runtime import sector_member_reading as member
from decision_kernel.runtime import stock_radar_reading as stock

FIXTURE = Path(__file__).parent / 'fixtures/sector_member_end_34452107559.json'


@pytest.fixture
def retained():
    value = json.loads(FIXTURE.read_text(encoding='utf-8'))
    state = SimpleNamespace(
        sessions=tuple(map(date.fromisoformat, value['sessions'])),
        series=[SimpleNamespace(thscode=s['thscode'], closes=tuple(map(Decimal, s['closes'])))
                for s in value['series']],
    )
    return value, state


def test_retained_records_are_unchanged_and_explain_the_count(retained):
    v, state = retained
    for name, content in [('capture/responses/600598.SH-history.json', v['history']),
                          ('capture/responses/600598.SH-actions.json', v['actions']),
                          ('derived-quotes.json', v['quotes'])]:
        raw = (canonical_json(content) + '\n').encode('utf-8')
        assert hashlib.sha256(raw).hexdigest() == v['retained_file_sha256'][name]
    rows = v['history']['data']['item']
    days = [datetime.fromtimestamp(r['date_ms'] / 1000, own.TZ).date() for r in rows]
    assert len(rows) == 62
    assert days[:-1] == list(state.sessions)
    assert days[-1] == date(2026, 9, 10)
    assert state.sessions[-1] == date(2026, 9, 9)
    # Original oversized response STILL fails; no production filtering/trimming.
    with pytest.raises(own.StockReadingInputError, match='EXACT_61_COMPLETED_STOCK_SESSIONS_REQUIRED'):
        own.qualify(v['history'], v['quotes']['600598.SH']['quote'], v['actions'],
                    code='600598.SH', sessions=state.sessions,
                    params=own.history_params('600598.SH', state.sessions),
                    observed_at=member.saved.clock(v['receipts']['600598.SH']['actions']),
                    quote_received_at=member.saved.clock(v['quotes']['600598.SH']['received_at']))


def test_new_query_never_reaches_the_following_midnight(retained):
    _, state = retained
    query = own.history_params('600598.SH', state.sessions)
    assert query == {'thscode': '600598.SH', 'interval': '1d', 'adjust': 'none',
                     'start': '1781539200000', 'end': '1788969599999'}
    assert own.CONTRACT == 'hithink-own-61-bars-history-actions-through-session-v4'
    assert stock.POLICY['source_contract'] == own.CONTRACT
    assert stock._history_params('600598.SH', state.sessions) == query


@pytest.mark.parametrize('last', [date(2026, 9, 9), date(2026, 9, 11), date(2026, 9, 30), date(2026, 12, 31)])
def test_cutoff_is_inside_last_calendar_day_not_next_day(last):
    # SYNTHETIC date sequence for boundary arithmetic only, not an exchange calendar.
    dates = [last - timedelta(days=i) for i in reversed(range(61))]
    query = own.history_params('600598.SH', dates)
    end = datetime.fromtimestamp(int(query['end']) / 1000, own.TZ)
    assert end.date() == last and end.time() == time(23, 59, 59, 999000)
    assert int(query['end']) + 1 == int(datetime.combine(last + timedelta(days=1), time(), own.TZ).timestamp() * 1000)


@pytest.mark.parametrize('inclusive', [True, False])
def test_test_only_endpoint_runs_capture_serialize_and_offline_compare(tmp_path, retained, inclusive):
    v, state = retained
    quotes = deepcopy(v['quotes'])
    synthetic_second = []
    for i, day in enumerate(state.sessions):
        price = str(Decimal(10) + Decimal(i) / 100)
        synthetic_second.append({'date_ms': int(datetime.combine(day, time(), own.TZ).timestamp() * 1000),
            **{k: price for k in ('open_price', 'high_price', 'low_price', 'close_price')},
            'volume': '100', 'turnover': str(1000 + i)})
    last = synthetic_second[-1]
    quotes['601952.SH']['quote'] = {'code': 0, 'data': {'timestamp': None, 'item': [{
        **{k: last[k] for k in ('open_price', 'high_price', 'low_price', 'volume', 'turnover')},
        'thscode': '601952.SH', 'ticker': '601952', 'last_price': last['close_price'],
        'prev_price': synthetic_second[-2]['close_price']}]}}
    calls, pauses = [], []

    def test_only_endpoint(endpoint, params):
        calls.append((endpoint, deepcopy(params)))
        code = params['thscode']
        if endpoint == own.ACTIONS:
            return deepcopy(v['actions']) if code == '600598.SH' else {
                'code': 0, 'data': {'thscode': code, 'ticker': code[:6], 'item': []}}
        assert endpoint == own.HISTORY
        all_rows = v['history']['data']['item'] if code == '600598.SH' else synthetic_second
        # This is a simulated SERVER predicate, never production response slicing.
        selected = [r for r in all_rows if int(params['start']) <= r['date_ms'] and
                    (r['date_ms'] <= int(params['end']) if inclusive else r['date_ms'] < int(params['end']))]
        assert len(selected) == 61
        return {'code': 0, 'data': {'thscode': code, 'interval': '1d', 'adjust': 'none',
                                  'timestamp': selected[-1]['date_ms'], 'item': deepcopy(selected)}}

    root = tmp_path / 'capture'
    result = member.capture(root, v['request'], state, quotes, transport=test_only_endpoint,
        now=lambda: datetime(2026, 9, 10, 17, tzinfo=own.TZ), pause=pauses.append)
    assert len(calls) == 4 and pauses == [20, 20, 20]
    assert all(int(p['end']) == 1788969599999 for e, p in calls if e == own.HISTORY)
    assert (root / 'summary.md').is_file() and not (root / 'failure.json').exists()
    responses = {c: {kind: member.read(root / f'responses/{c}-{kind}.json')
                     for kind in ('history', 'actions')} for c in ('600598.SH', '601952.SH')}
    replay = member.compare(v['request'], state, quotes, responses, member.read(root / 'receipts.json'))
    assert canonical_hash(replay) == canonical_hash(member.read(root / 'reading.json'))
    assert member.render(replay) == (root / 'summary.md').read_text(encoding='utf-8')
    assert all(r['role'].startswith('UNDETERMINED') for r in result['rows'])
    assert all(r['price_checks']['contract'] == own.CONTRACT for r in result['rows'])


@pytest.mark.parametrize('bad', ['extra', 'missing', 'replace_last_by_tomorrow', 'duplicate'])
def test_window_guard_not_relaxed_to_make_capture_succeed(retained, bad):
    v, state = retained
    history = deepcopy(v['history'])
    if bad != 'extra':
        history['data']['item'] = history['data']['item'][:-1]  # TEST mutation, not production handling.
    rows = history['data']['item']
    if bad == 'missing': rows.pop(30)
    if bad == 'replace_last_by_tomorrow': rows[-1] = deepcopy(v['history']['data']['item'][-1])
    if bad == 'duplicate': rows[30] = deepcopy(rows[29])
    with pytest.raises(own.StockReadingInputError):
        own.qualify(history, v['quotes']['600598.SH']['quote'], v['actions'],
            code='600598.SH', sessions=state.sessions, params=own.history_params('600598.SH', state.sessions),
            observed_at=member.saved.clock(v['receipts']['600598.SH']['actions']),
            quote_received_at=member.saved.clock(v['quotes']['600598.SH']['received_at']))
