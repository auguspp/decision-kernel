"""Field tolerance and ex-date boundaries, not a supplier-precision guarantee."""
import copy
from datetime import datetime, time, timedelta
from decimal import Decimal, Inexact, localcontext

import pytest

from decision_kernel.runtime import hithink_stock_reading as own
from test_hithink_stock_reading import inputs, check

CODE = '002714.SZ'


@pytest.mark.parametrize('historical,snapshot', [
    ('1971522143.2', '1971522100'), ('808043253.61', '808043250'),
    ('289640622.25', '289640620'), ('204524261.36', '204524260'),
    ('100000000', '99999990'), ('100000000', '99999990.000001'),
    ('10000', '9999.99'), ('1000000000000', '999999999900'),
])
def test_bounded_amount_difference_is_symmetric_and_keeps_both_values(historical, snapshot):
    a = own.reconcile_turnover(historical, snapshot, code=CODE)
    b = own.reconcile_turnover(snapshot, historical, code=CODE)
    assert a['status'] == b['status'] == 'WITHIN_EXPLICIT_TOLERANCE'
    assert a['absolute_difference_cny'] == b['absolute_difference_cny']
    assert a['allowed_difference_cny'] == b['allowed_difference_cny']
    assert a['historical_cny'] == historical and a['snapshot_cny'] == snapshot
    assert Decimal(a['absolute_difference_cny']) <= Decimal(a['allowed_difference_cny']) <= 100
    assert a['calculation_source'] == 'DATED_HISTORY_UNCHANGED'
    assert a['supplier_precision_rule_established'] is False


@pytest.mark.parametrize('historical,snapshot', [
    ('100000000', '99999989.999999'), ('10000', '9999.989999'),
    ('1000000000000', '999999999899.999999'),
    ('10000', '9956.8'), ('100000000', '10000'),
])
def test_above_scale_bound_or_hard_cap_never_auto_expands(historical, snapshot):
    for a,b in ((historical,snapshot),(snapshot,historical)):
        with pytest.raises(own.StockReadingInputError, match='CURRENT_QUOTE_HISTORY_MISMATCH'):
            own.reconcile_turnover(a,b,code=CODE)


@pytest.mark.parametrize('value', [0, '0', '-1', True, False, None, 'NaN', 'Infinity',
                                   '-Infinity', 'broken', {}, '1e29', '1e-13'])
def test_tolerance_never_legitimizes_zero_missing_or_malformed_amount(value):
    with pytest.raises(own.StockReadingInputError):
        own.reconcile_turnover('1000',value,code=CODE)


def test_exact_amount_and_decimal_context_do_not_change_receipt():
    assert own.reconcile_turnover('1000','1000',code=CODE)['status'] == 'EXACT'
    expected = own.reconcile_turnover('808043253.61','808043250',code=CODE)
    with localcontext() as context:
        context.prec = 4
        context.traps[Inexact] = True
        assert own.reconcile_turnover('808043253.61','808043250',code=CODE) == expected


@pytest.mark.parametrize('field', ['last_price','open_price','high_price','low_price','volume','prev_price'])
def test_amount_tolerance_does_not_spread_to_prices_volume_or_previous_close(field):
    _,_,_,q,_ = inputs()
    q['data']['item'][0]['turnover'] = '6999.995'
    q['data']['item'][0][field] = str(Decimal(q['data']['item'][0][field])+Decimal('0.000001'))
    with pytest.raises(own.StockReadingInputError):
        check(q=q)


def action_at(index, *, cash='0.2', bonus='0'):
    days,at,h,q,a = inputs()
    a['data']['item'] = [{'ticker':CODE[:6], 'ex_date_ms':h['data']['item'][index]['date_ms'],
                          'dividend_per_share':cash, 'per_share_bonus':bonus}]
    return days,at,h,q,a


@pytest.mark.parametrize('index', [0,1,10,20,35,39,40])
def test_events_on_or_before_twenty_day_base_close_do_not_block_selection(index):
    days,_,h,q,a = action_at(index)
    before = copy.deepcopy((h,q,a))
    bars,meta = check(h,q,a)
    assert (h,q,a) == before and len(bars) == 61
    assert len(meta['reported_corporate_actions']) == 1
    assert meta['reported_corporate_actions'][0]['ex_date'] == days[index].isoformat()
    assert meta['action_window_checks']['5']['usable_for_raw_comparison']
    assert meta['action_window_checks']['20']['usable_for_raw_comparison']
    assert meta['action_window_checks']['60']['usable_for_raw_comparison'] is (index == 0)
    assert 'NOT_EXHAUSTIVE_ABSENCE_PROOF' in meta['corporate_actions']
    assert meta['adjustment_or_total_return_qualification'] == 'NOT_ESTABLISHED'


@pytest.mark.parametrize('index', [41,54,55,56,60])
@pytest.mark.parametrize('cash,bonus', [('0.2','0'),('0','0.1'),('0','0')])
def test_any_reported_event_after_selection_base_through_end_still_blocks(index,cash,bonus):
    _,_,h,q,a = action_at(index,cash=cash,bonus=bonus)
    with pytest.raises(own.StockReadingInputError,match='REPORTED_CORPORATE_ACTION_IN_WINDOW'):
        check(h,q,a)


def test_base_close_is_exclusive_and_shifted_context_is_checked_independently():
    days,_,h,q,a = action_at(40)
    _,m = check(h,q,a)
    w = m['action_window_checks']
    assert w['20']['base_session'] == days[40].isoformat()
    assert not w['20']['reported_event_dates']
    assert w['20']['usable_for_raw_comparison']
    assert not w['20_five_sessions_ago']['usable_for_raw_comparison']
    dates = [datetime.combine(days[55],time(),own.TZ)]
    direct = own.action_window_checks(days,dates)
    assert direct['5']['usable_for_raw_comparison']
    assert not direct['20']['usable_for_raw_comparison']
    assert direct['20_five_sessions_ago']['reported_event_dates'] == [days[55].isoformat()]


@pytest.mark.parametrize('kind', ['duplicate','bad_cash','negative_bonus','wrong_ticker','intraday','off_calendar'])
def test_older_event_does_not_skip_identity_schema_or_numeric_validation(kind):
    _,_,h,q,a = action_at(20)
    e = a['data']['item'][0]
    if kind == 'duplicate': a['data']['item'].append(copy.deepcopy(e))
    elif kind == 'bad_cash': e['dividend_per_share'] = 'NaN'
    elif kind == 'negative_bonus': e['per_share_bonus'] = '-1'
    elif kind == 'wrong_ticker': e['ticker'] = '999999'
    elif kind == 'intraday': e['ex_date_ms'] += 1
    else: e['ex_date_ms'] -= 86400000*200
    with pytest.raises(own.StockReadingInputError): check(h,q,a)


@pytest.mark.parametrize('code', [3002,4001,2001])
def test_no_events_words_never_replace_a_successful_business_response(code):
    with pytest.raises(own.StockReadingInputError,match='PROVIDER_BUSINESS_REQUEST_FAILED'):
        check(a={'code':code,'data':None,'message':'No adjustment events for thscode='+CODE})
