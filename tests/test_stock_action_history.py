"""Documented history-query scope on synthetic events, not new HiThink data."""
import copy
from datetime import datetime, time, timedelta

import pytest

from decision_kernel.runtime import hithink_stock_reading as own
from test_hithink_stock_reading import inputs, check

CODE = '002714.SZ'


def event(day, *, ticker=CODE[:6]):
    return {'ticker': ticker,
            'ex_date_ms': int(datetime.combine(day, time(), own.TZ).timestamp()*1000),
            'dividend_per_share': '0.2', 'per_share_bonus': 0}


@pytest.mark.parametrize('code', ['002714.SZ','300498.SZ','603477.SH','605296.SH'])
def test_same_documented_initial_history_request_for_every_issuer(code):
    days, *_ = inputs()
    assert own.action_params(code, days) == {'thscode': code, 'to': days[-1].isoformat()}
    assert 'history-actions-through-session' in own.CONTRACT


@pytest.mark.parametrize('age', [1,200,3650])
def test_successful_older_history_is_retained_not_converted_to_empty(age):
    days,_,h,q,a = inputs()
    old = days[0]-timedelta(days=age)
    a['data']['item'] = [event(old)]
    before = copy.deepcopy((h,q,a))
    bars,meta = check(h,q,a)
    assert (h,q,a) == before and len(bars) == 61
    assert meta['reported_corporate_actions'][0]['ex_date'] == old.isoformat()
    assert all(w['usable_for_raw_comparison'] for w in meta['action_window_checks'].values())
    query = meta['corporate_action_query']
    assert query['scope'] == 'AVAILABLE_HISTORY_THROUGH_COMPLETED_SESSION'
    assert query['expected_request'] == own.action_params(CODE,days)
    assert query['response_event_count'] == query['events_before_price_window'] == 1
    assert query['exhaustive_absence_proven'] is False
    assert query['older_event_session_qualification'] == 'NOT_ASSERTED_OUTSIDE_RETAINED_CALENDAR'
    assert meta['corporate_actions'].startswith('REPORTED_ACTIONS_')
    assert meta['adjustment_or_total_return_qualification'] == 'NOT_ESTABLISHED'


def test_old_and_context_events_keep_separate_window_effects():
    days,_,h,q,a = inputs()
    a['data']['item'] = [event(days[20]),event(days[0]-timedelta(days=200))]
    _,m = check(h,q,a)
    assert m['corporate_action_query']['response_event_count'] == 2
    assert m['corporate_action_query']['events_before_price_window'] == 1
    assert m['action_window_checks']['20']['usable_for_raw_comparison']
    assert not m['action_window_checks']['60']['usable_for_raw_comparison']


@pytest.mark.parametrize('index', [41,55,60])
def test_older_history_never_hides_an_event_crossing_selection(index):
    days,_,h,q,a = inputs()
    a['data']['item'] = [event(days[index]),event(days[0]-timedelta(days=365))]
    with pytest.raises(own.StockReadingInputError,match='REPORTED_CORPORATE_ACTION_IN_WINDOW'):
        check(h,q,a)


@pytest.mark.parametrize('kind', ['duplicate','reversed','ticker','cash','bonus','intraday','bool_date','future','inside_holiday'])
def test_history_scope_does_not_relax_event_validation(kind):
    days,_,h,q,a = inputs()
    a['data']['item'] = [event(days[0]-timedelta(days=200))]
    row=a['data']['item'][0]
    if kind=='duplicate': a['data']['item'].append(copy.deepcopy(row))
    elif kind=='reversed': a['data']['item'].append(event(days[20]))
    elif kind=='ticker': row['ticker']='000001'
    elif kind=='cash': row['dividend_per_share']='NaN'
    elif kind=='bonus': row['per_share_bonus']=-1
    elif kind=='intraday': row['ex_date_ms']+=1
    elif kind=='bool_date': row['ex_date_ms']=True
    elif kind=='future': a['data']['item']=[event(days[-1]+timedelta(days=1))]
    else: a['data']['item']=[event(days[4]+timedelta(days=1))]
    with pytest.raises(own.StockReadingInputError): check(h,q,a)


@pytest.mark.parametrize('key,value', [
    ('total',2),('total',True),('total',None),('total','1'),
    ('has_more',True),('has_more','false'),('has_more',0),('has_next',True),
    ('truncated',True),('next_cursor','next'),('next_page',2),('next','url'),
])
def test_partial_history_cannot_support_no_reported_events_in_window(key,value):
    days,_,h,q,a=inputs()
    a['data']['item']=[event(days[0]-timedelta(days=200))]
    a['data'][key]=value
    with pytest.raises(own.StockReadingInputError,match='REQUIRED_INPUT_OR_FIELD_MISSING') as exc:
        check(h,q,a)
    assert exc.value.category=='DATA_INSUFFICIENT'


@pytest.mark.parametrize('key,value',[('from','2026-06-01'),('to','2020-01-01')])
def test_response_cannot_echo_a_different_query_scope(key,value):
    days,_,h,q,a=inputs();a['data'][key]=value
    with pytest.raises(own.StockReadingInputError): check(h,q,a)


@pytest.mark.parametrize('count',[0,1,256,257])
def test_event_row_budget_is_not_expanded_or_truncated(count):
    days,_,h,q,a=inputs()
    a['data']['item']=[event(days[0]-timedelta(days=200+i)) for i in range(count)]
    if count>256:
        with pytest.raises(own.StockReadingInputError): check(h,q,a)
    else:
        _,m=check(h,q,a)
        assert m['corporate_action_query']['response_event_count']==count
        assert m['corporate_action_query']['maximum_event_rows']==256
        assert len(m['reported_corporate_actions'])==count


def test_matching_nonpartial_metadata_is_accepted_without_absence_guarantee():
    days,_,h,q,a=inputs()
    a['data'].update(total=0,has_more=False,truncated=False,next_cursor=None,to=days[-1].isoformat())
    _,m=check(h,q,a)
    assert m['corporate_action_query_succeeded'] is True
    assert m['corporate_action_query']['exhaustive_absence_proven'] is False


@pytest.mark.parametrize('status',[3002,3001,3004,4001,2001,5003])
def test_no_events_message_never_overrides_nonzero_business_code(status):
    _,_,h,q,a=inputs()
    failure={'code':status,'message':'No adjustment events for thscode='+CODE,'data':None}
    before=copy.deepcopy(failure)
    with pytest.raises(own.StockReadingInputError,match='PROVIDER_BUSINESS_REQUEST_FAILED'):
        check(h,q,failure)
    assert failure==before
