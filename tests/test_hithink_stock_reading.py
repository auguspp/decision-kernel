"""HiThink contract fixtures, not actual quotes or an independently qualified calendar."""
import copy
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from decision_kernel.runtime import hithink_stock_reading as own


def inputs():
    days=[]; d=date(2026,6,1)
    while len(days)<61:
        if d.weekday()<5: days.append(d)
        d+=timedelta(days=1)
    at=datetime.combine(days[-1],time(17),own.TZ)
    ms=lambda day:int(datetime.combine(day,time(),own.TZ).timestamp()*1000)
    rows=[{'date_ms':ms(d),'open_price':str(10+i),'high_price':str(11+i),
           'low_price':str(9+i),'close_price':str(10+i),'volume':'100','turnover':str(1000+100*i)}
          for i,d in enumerate(days)]
    h={'code':0,'data':{'timestamp':int(at.timestamp()*1000),'item':rows}}
    q={'code':0,'data':{'timestamp':None,'total':5000,'item':[
        {'thscode':'002714.SZ','ticker':'002714','last_price':'70','prev_price':'69',
         'open_price':'70','high_price':'71','low_price':'69','volume':'100','turnover':'7000'}]}}
    a={'code':0,'data':{'thscode':'002714.SZ','ticker':'002714','item':[]}}
    return days,at,h,q,a


def check(h=None,q=None,a=None,**kw):
    days,at,history,quote,actions=inputs()
    args={'code':'002714.SZ','sessions':days,'params':own.history_params('002714.SZ',days),'observed_at':at}
    args.update(kw)
    return own.qualify(h if h is not None else history,q if q is not None else quote,
                       a if a is not None else actions,**args)


def test_documented_history_needs_no_undocumented_echo_or_daily_prev_field():
    days,at,h,q,a=inputs();before=copy.deepcopy((h,q,a))
    bars,meta=check(h,q,a)
    assert (h,q,a)==before
    assert len(bars)==61 and bars[days[-1]]['close_price']==Decimal('70')
    assert meta['history_provider_ready_at']==at.isoformat()
    assert meta['snapshot_individual_trade_date']=='NOT_SUPPLIED_NOT_INFERRED_FROM_READY_CLOCK'
    assert meta['historical_daily_reference_check']=='NOT_AVAILABLE_NOT_REQUIRED_FOR_RAW_CLOSE_RATIOS'
    assert meta['adjustment_or_total_return_qualification']=='NOT_ESTABLISHED'
    assert 'NOT_EXHAUSTIVE_ABSENCE_PROOF' in meta['corporate_actions']
    assert 'prev_price' not in h['data']['item'][0]


@pytest.mark.parametrize('key,value',[('thscode','000001.SZ'),('interval','1w'),('adjust','forward')])
def test_contradictory_provider_echo_is_not_overwritten(key,value):
    _,_,h,_,_=inputs();h['data'][key]=value
    with pytest.raises(own.StockReadingInputError):check(h=h)


@pytest.mark.parametrize('kind',['missing_first','missing_middle','missing_last','duplicate','extra',
    'wrong_date','intraday_key','bool_date','future_ready','missing_ready','bool_ready',
    'zero_volume','zero_turnover','nan','missing_price','bad_ohlc','wrong_row_code','wrong_row_ticker',
    'negative','bool_number','partial_calendar'])
def test_unqualified_own_history_fails_closed(kind):
    days,at,h,_,_=inputs();d=h['data'];rows=d['item'];row=rows[20]
    kw={}
    if kind=='missing_first':rows.pop(0)
    elif kind=='missing_middle':rows.pop(20)
    elif kind=='missing_last':rows.pop()
    elif kind=='duplicate':rows[21]=copy.deepcopy(row)
    elif kind=='extra':rows.append(copy.deepcopy(row))
    elif kind=='wrong_date':row['date_ms']-=86400*1000*200
    elif kind=='intraday_key':row['date_ms']+=1000
    elif kind=='bool_date':row['date_ms']=True
    elif kind=='future_ready':d['timestamp']=int((at+timedelta(seconds=1)).timestamp()*1000)
    elif kind=='missing_ready':del d['timestamp']
    elif kind=='bool_ready':d['timestamp']=True
    elif kind=='zero_volume':row['volume']='0'
    elif kind=='zero_turnover':row['turnover']='0'
    elif kind=='nan':row['close_price']='NaN'
    elif kind=='missing_price':del row['close_price']
    elif kind=='bad_ohlc':row['high_price']='1'
    elif kind=='wrong_row_code':row['thscode']='000001.SZ'
    elif kind=='wrong_row_ticker':row['ticker']='000001'
    elif kind=='negative':row['turnover']='-1'
    elif kind=='bool_number':row['close_price']=True
    else:kw['sessions']=days[:-1]
    with pytest.raises(own.StockReadingInputError):check(h=h,**kw)


@pytest.mark.parametrize('kind',['last','previous','amount','volume','open','identity','ticker',
    'no_row','extra_row','timestamp','missing_timestamp','missing_previous'])
def test_current_snapshot_must_match_own_history_exactly(kind):
    _,_,_,q,_=inputs();d=q['data'];r=d['item'][0]
    if kind in {'last','previous','amount','volume','open'}:
        r[{'last':'last_price','previous':'prev_price','amount':'turnover','volume':'volume','open':'open_price'}[kind]]='1'
    elif kind=='identity':r['thscode']='002714.SH'
    elif kind=='ticker':r['ticker']='000001'
    elif kind=='no_row':d['item']=[]
    elif kind=='extra_row':d['item'].append(copy.deepcopy(r))
    elif kind=='timestamp':d['timestamp']=123
    elif kind=='missing_timestamp':del d['timestamp']
    else:del r['prev_price']
    with pytest.raises(own.StockReadingInputError):check(q=q)


@pytest.mark.parametrize('kind',['cash','bonus','unknown','wrong_code','wrong_ticker','missing_list','nonlist','out_of_window'])
def test_reported_actions_are_never_converted_to_inferred_adjustments(kind):
    _,_,h,_,a=inputs();d=a['data']
    if kind=='wrong_code':d['thscode']='000001.SZ'
    elif kind=='wrong_ticker':d['ticker']='000001'
    elif kind=='missing_list':del d['item']
    elif kind=='nonlist':d['item']=None
    else:
        d['item']=[{'ticker':'002714','ex_date_ms':h['data']['item'][20]['date_ms'],
            'dividend_per_share':'0.1' if kind=='cash' else '0',
            'per_share_bonus':'0.1' if kind=='bonus' else '0'}]
        if kind=='out_of_window':d['item'][0]['ex_date_ms']-=86400*1000*200
    with pytest.raises(own.StockReadingInputError):check(a=a)


def test_business_failure_does_not_echo_provider_message():
    with pytest.raises(own.StockReadingInputError) as e:
        check(a={'code':429,'msg':'private response details','data':{}})
    assert e.value.category=='REQUEST_FAILED' and str(e.value)=='PROVIDER_BUSINESS_REQUEST_FAILED'


def test_incomplete_session_and_naive_clocks_rejected():
    _,at,_,_,_=inputs()
    for bad in (at.replace(hour=14),at.replace(tzinfo=None)):
        with pytest.raises(own.StockReadingInputError):check(observed_at=bad)


def test_request_identity_cannot_be_inferred_from_missing_echo():
    days,_,_,_,_=inputs();params=own.history_params('000001.SZ',days)
    with pytest.raises(own.StockReadingInputError):check(params=params)
