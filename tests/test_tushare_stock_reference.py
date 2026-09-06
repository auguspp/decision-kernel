"""Provider-contract fixtures only; no live request, secret, or source authentication."""
import copy
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext

import pytest

from decision_kernel.adapters import tushare_stock_reference as source


def sample():
    # Explicit synthetic calendar for parser tests, never a real exchange calendar.
    days=[]
    day=date(2026, 6, 1)
    while len(days)<61:
        if day.weekday()<5:
            days.append(day)
        day+=timedelta(days=1)
    at=datetime.combine(days[-1], datetime.min.time(), source.TZ).replace(hour=17)
    request=source.daily_request('002714.SZ',days)
    rows=[]
    for i,day in enumerate(days):
        rows.append(['002714.SZ',day.strftime('%Y%m%d'),str(Decimal('10')+i/Decimal('10')),
            str(Decimal('9.9')+i/Decimal('10')),'1.25','0.01234',None if i==0 else '0.01','0.0002'])
    payload={'code':0,'msg':None,'data':{'fields':list(source.REQUIRED_FIELDS),'items':list(reversed(rows))}}
    return days,at,request,payload


def check(payload=None, **kwargs):
    days,at,request,default=sample()
    raw=json.dumps(payload if payload is not None else default,separators=(',',':')).encode()
    args={'request':request,'thscode':'002714.SZ','sessions':days,
        'requested_at':at,'received_at':at+timedelta(seconds=1),'input_cutoff':at+timedelta(seconds=2)}
    args.update(kwargs)
    return source.check_daily_response(raw,**args)


def test_exact_daily_reference_units_and_after_hours_are_separate():
    report=check();rows=report['rows']
    assert len(rows)==61 and Decimal(rows[0]['close'])==10
    assert Decimal(rows[0]['reported_volume_shares'])==125
    assert Decimal(rows[0]['reported_turnover_cny'])==Decimal('12.34000')
    assert rows[0]['after_hours_volume_shares'] is None
    assert Decimal(rows[-1]['after_hours_volume_shares'])==1
    assert Decimal(rows[-1]['after_hours_turnover_cny'])==Decimal('0.2')
    assert not report['cross_provider_amount_scope_established']
    assert not report['qualified_for_stock_reading'] and not report['origin_authenticated']
    assert not report['latest_quote_independently_matched']
    assert report['status']=='SOURCE_FIELDS_CHECKED_ONLY'
    assert report['network_calls']==report['events_created']==report['market_state_writes']==0


def test_decimal_context_is_not_a_hidden_rounding_tolerance():
    expected=check()
    days,at,request,payload=sample()
    raw=json.dumps(payload).encode()
    with localcontext() as ctx:
        ctx.prec=3
        report=source.check_daily_response(raw,request=request,thscode='002714.SZ',sessions=days,
            requested_at=at,received_at=at+timedelta(seconds=1),input_cutoff=at+timedelta(seconds=2))
    assert report['rows']==expected['rows']


def test_discontinuity_is_retained_not_repaired_or_interpreted_as_cash_adjustment():
    _,_,_,payload=sample();payload['data']['items'][20][3]='7.21'
    before=copy.deepcopy(payload)
    report=check(payload)
    assert payload==before
    assert report['status']=='REFERENCE_DISCONTINUITY_REQUIRES_REVIEW'
    assert len(report['discontinuity_sessions'])==1 and not report['qualified_for_stock_reading']
    assert any(r['reported_ex_reference']=='7.21' for r in report['rows'])


@pytest.mark.parametrize('kind',['missing','extra','duplicate','off_calendar','wrong_code','wrong_exchange',
    'date_format','invalid_date','duplicate_field','missing_field','extra_field','ragged','nan',
    'boolean','null','negative_volume','zero_volume','fractional_share','fractional_ah_share','huge_precision'])
def test_invalid_or_incomplete_provider_input_never_passes(kind):
    days,_,_,payload=sample();d=payload['data'];r=d['items'][20]
    if kind=='missing':d['items'].pop()
    elif kind=='extra':d['items'].append(copy.deepcopy(r))
    elif kind=='duplicate':d['items'][21]=copy.deepcopy(r)
    elif kind=='off_calendar':r[1]='20260101'
    elif kind=='wrong_code':r[0]='000001.SZ'
    elif kind=='wrong_exchange':r[0]='002714.SH'
    elif kind=='date_format':r[1]='2026-06-01'
    elif kind=='invalid_date':r[1]='20260230'
    elif kind=='duplicate_field':d['fields'][-1]=d['fields'][0]
    elif kind=='missing_field':d['fields'].pop()
    elif kind=='extra_field':d['fields'].append('token')
    elif kind=='ragged':r.pop()
    elif kind=='nan':r[2]=float('nan')
    elif kind=='boolean':r[2]=True
    elif kind=='null':r[3]=None
    elif kind=='negative_volume':r[4]='-1'
    elif kind=='zero_volume':r[4]='0'
    elif kind=='fractional_share':r[4]='0.001'
    elif kind=='fractional_ah_share':r[6]='0.001'
    else:r[2]='1e999'
    with pytest.raises(source.TushareReferenceError):check(payload)


@pytest.mark.parametrize('kind',['naive','request_after_receipt','receipt_after_cutoff','expired','before_daily_complete'])
def test_unqualified_clocks_rejected(kind):
    _,at,_,_=sample()
    kwargs={}
    if kind=='naive':kwargs['requested_at']=at.replace(tzinfo=None)
    elif kind=='request_after_receipt':kwargs['received_at']=at-timedelta(seconds=1)
    elif kind=='receipt_after_cutoff':kwargs['input_cutoff']=at
    elif kind=='expired':kwargs['input_cutoff']=at+timedelta(minutes=31)
    else:
        at=at.replace(hour=15,minute=59)
        kwargs.update(requested_at=at,received_at=at+timedelta(seconds=1),input_cutoff=at+timedelta(seconds=2))
    with pytest.raises(source.TushareReferenceError):check(**kwargs)


def test_business_failure_never_echoes_remote_error_or_token():
    with pytest.raises(source.TushareReferenceError) as exc:
        check({'code':2002,'msg':'do not echo private-token','data':None})
    assert exc.value.category=='REQUEST_FAILED'
    assert str(exc.value)=='PROVIDER_BUSINESS_REQUEST_FAILED'


def test_request_cannot_broaden_into_all_market_query_or_change_adjustment():
    _,_,request,_=sample()
    request['params'].pop('ts_code')
    with pytest.raises(source.TushareReferenceError,match='REQUEST_SCOPE'):
        check(request=request)
    request=sample()[2];request['params']['adj']='qfq'
    with pytest.raises(source.TushareReferenceError,match='REQUEST_SCOPE'):
        check(request=request)


@pytest.mark.parametrize('raw',[b'{"code":0,"code":1}',b'{"code":NaN}',b'not json',b'\xff',b' '*(source.MAX_BYTES+1)])
def test_raw_json_identity_and_byte_limits(raw):
    days,at,request,_=sample()
    with pytest.raises(source.TushareReferenceError):
        source.check_daily_response(raw,request=request,thscode='002714.SZ',sessions=days,
            requested_at=at,received_at=at,input_cutoff=at)


def test_boolean_business_success_is_not_integer_zero():
    _,_,_,payload=sample();payload['code']=False
    with pytest.raises(source.TushareReferenceError,match='INVALID_PROVIDER_ENVELOPE'):check(payload)


def test_source_contract_result_never_has_normalized_live_reference_shape():
    result=check()
    assert result['semantics']==source.SEMANTICS
    assert 'windows' not in result and 'latest_quotes' not in result and 'provenance' not in result
    assert result['qualified_for_stock_reading'] is False


def test_numeric_json_values_are_read_without_binary_float_roundtrip():
    _,_,_,payload=sample()
    for row in payload['data']['items']:
        row[2]=float(row[2]);row[3]=float(row[3])
        row[4]=1.25;row[5]=0.01234
    report=check(payload)
    assert report['status']=='SOURCE_FIELDS_CHECKED_ONLY'
    assert all(Decimal(r['reported_turnover_cny'])==Decimal('12.34') for r in report['rows'])
