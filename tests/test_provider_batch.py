"""Whole batch, not isolated endpoint acceptance; synthetic transport, no secrets."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import provider_batch as b, ftshare_market_inputs as m

CONFIG={'ticker':'603507.SH','session':'2026-09-21','sw_code':'801736.SI','sw_name':'风电设备',
        'concept_code':'BK0595','concept_name':'风能','contracts':{'LC':'LC2610.GFE','CU':'CU2610.SHF','RB':'RB2610.SHF'}}
CLOCK='2026-09-22T04:00:00+00:00'


def payload(route,params):
    if route=='stock':
        rows=[{'symbol':params['code'],'trade_date':20260921,'open':'24.22','high':'26.5',
               'low':'24.22','close':'26.48','prev_close':'24.20','volume':21725345,'turnover':'562388552'}]
    elif route=='flow':rows=[{'code':'603507','market':'1','trade_date':'2026-09-21','main_net':'49174612'}]
    elif route=='sw_members':rows=[{'stockCode':'603507','stockName':'振江股份','inDate':'2017-10-30','outDate':None,
                                  'swLevel1Code':'801730.SI','swLevel2Code':'801736.SI','swLevel3Code':None}]
    elif route=='sw_metrics':rows=[{'industryCode':'801736.SI','tradeDate':'2026-09-21','closePrice':None}]
    elif route=='concept_members':return {'code':200,'data':{'board_code':'BK0595','constituents':[{'stock_code':'603507'}]}}
    elif route=='concept_prices':rows=[{'board_code':'BK0595','date':'2026-09-21','close':'2625.68','turnover':'138652400913'}]
    elif route=='futures_base':rows=[{'symbol':params['symbol'],'product':params['symbol'][:2],
             'exchange':'GFEX' if params['symbol'].startswith('LC') else 'SHFE','trade_date':20260921,
             'put_price':'人民币元/吨','trade_unit':'吨','multiplier':1}]
    elif route=='futures_prices':rows=[{'symbol':params['symbol'].split('.')[0].lower(),'trade_date':20260921,
                'open':10,'high':12,'low':9,'close':11,'dominant_contract':None,'forward_factor':None,'backward_factor':None}]
    elif route=='warehouse':rows=[{'symbol':params['symbol'],'exchange':'GFEX' if params['symbol']=='LC' else 'SHFE',
                    'trade_date':20260921,'unit':'手' if params['symbol']=='LC' else '吨','vol':'123'}]
    else:raise AssertionError(route)
    if route in m.PAGED:return {'code':200,'data':{'pageNum':1,'pageSize':200,'total':len(rows),'pages':1,'records':rows}}
    return {'code':200,'data':{'items':rows,'total':len(rows)}}


def fetch(route,params):return 200,m.raw_json(payload(route,params))


def captures(tmp_path):
    return {label:m.capture(route,params,tmp_path/label,fetch=fetch,clock=lambda:CLOCK)
            for label,route,params in b.plan(CONFIG)}


def test_one_batch_all_families_and_original_types(tmp_path):
    result=b.prepare(CONFIG,tmp_path/'batch',fetch=fetch,clock=lambda:CLOCK)
    assert result['status']=='BATCH_CONTEXT_READY'
    assert len(result['families'])==9
    assert result['families']['concept_market']['typed_price_series']['thscode']=='BK0595'
    assert result['families']['concept_members']['as_of'] is None
    assert result['families']['LC']['observation']['projection']['warehouses'][0]['data']['unit']=='手'
    assert result['families']['CU']['observation']['projection']['price_unit']=='CNY_PER_TONNE'
    assert not result['default_provider_changed'] and not result['model_calls']
    assert (tmp_path/'batch'/'provider-batch.md').is_file()


@pytest.mark.parametrize('route,params',[ (r,p) for _,r,p in b.plan(CONFIG)],ids=[x[0] for x in b.plan(CONFIG)])
def test_every_configured_contract_captures(tmp_path,route,params):
    result=m.capture(route,params,tmp_path/'capture',fetch=fetch,clock=lambda:CLOCK)
    assert result['status']=='COMPLETE' and result['rows']
    assert result['requests'][0]['sha256']


@pytest.mark.parametrize('bad', ['evil.example','603507.SZ','603507.SH/other'])
def test_bad_stock_identity_stops_before_fetch(tmp_path,bad):
    config=deepcopy(CONFIG);config['ticker']=bad
    with pytest.raises(ValueError):b.prepare(config,tmp_path/'out',fetch=lambda *a:pytest.fail('network'),clock=lambda:CLOCK)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('status,reason',[(401,'AUTHENTICATION_FAILED'),(403,'ENTITLEMENT_DENIED'),(429,'RATE_LIMITED')])
def test_global_stop_not_full_batch_success(tmp_path,status,reason):
    calls=[]
    def reject(*args):calls.append(args);return status,b'{}'
    result=b.prepare(CONFIG,tmp_path/'out',fetch=reject,clock=lambda:CLOCK)
    assert len(calls)==1 and result['status']=='PARTIAL_BATCH_CONTEXT'
    assert result['capture_statuses']['stock']==reason
    assert result['capture_statuses']['flow']=='NOT_ATTEMPTED_AFTER_'+reason


def test_same_session_comparison_does_not_change_gate(tmp_path):
    data=captures(tmp_path);context=b.stock_context(data['stock'],'603507.SH',date(2026,9,21))
    reference={'ticker':'603507.SH','session':'2026-09-21','prices':{k:str(v) for k,v in context['prices'].items()},
               'turnover':'562388550','volume':21725345,'volume_unit':'SHARES','currency':'CNY',
               'adjustment':'NONE','source_sha256':'a'*64}
    result=b.compare_stock(context,reference)
    assert result['turnover_residual']==2 and result['volume_residual']==0 and not result['qualification_changed']
    reference['session']='2026-09-18'
    with pytest.raises(ValueError):b.compare_stock(context,reference)


def test_invalid_lc_price_preserves_warehouse_not_invalid_price_use(tmp_path):
    data=captures(tmp_path);data['LC_prices']['rows'][0]['data']['open']=20
    result=b.project(CONFIG,data)
    lc=result['families']['LC']
    assert lc['status']=='PARTIAL_INDUSTRY_CONTEXT'
    assert lc['observation']['projection']['price_validation']=='INVALID_OHLC'
    assert lc['observation']['projection']['warehouses'] and not lc['observation']['projection']['prices_usable']
    assert result['families']['CU']['status']=='CONTEXT_READY'


def test_sw_multiple_level_records_preserved_without_double_count(tmp_path):
    data=captures(tmp_path);another=deepcopy(data['sw_members']['rows'][0]);another['data']['swLevel3Code']='857362.SI'
    data['sw_members']['rows'].append(another)
    result=b.membership_context(data['sw_members'],'801736.SI',date(2026,9,21))
    assert len(result['members'])==1 and len(result['members'][0]['source_records'])==2
    another['data']['inDate']='2018-01-01'
    with pytest.raises(ValueError,match='MEMBERSHIP_CONFLICT'):b.membership_context(data['sw_members'],'801736.SI',date(2026,9,21))


@pytest.mark.parametrize('target,field,value',[('stock','symbol','600000.SH'),('flow','market','0'),
    ('LC_base','symbol','LC2611.GFE'),('CU_prices','symbol','cu2701'),('RB_warehouse','unit','未知')])
def test_wrong_identity_units_not_qualified(tmp_path,target,field,value):
    data=captures(tmp_path);data[target]['rows'][0]['data'][field]=value
    result=b.project(CONFIG,data)
    family={'stock':'market','flow':'flow','LC_base':'LC','CU_prices':'CU','RB_warehouse':'RB'}[target]
    assert result['families'][family]['status']=='SOURCE_UNAVAILABLE'


def test_board_envelopes_both_exact_and_no_partial_pages(tmp_path):
    params=dict(b.plan(CONFIG)[5][2]);obj=payload('concept_prices',params)
    rows=obj['data']['records'];obj['data']={'items':rows,'total_items':1,'total_pages':1}
    assert m.unpack('concept_prices',obj,1)[0]==rows
    obj['data']['total_items']=201;obj['data']['total_pages']=2
    with pytest.raises(ValueError,match='PAGE_INCOMPLETE'):m.unpack('concept_prices',obj,1)


@pytest.mark.parametrize('body',[b'{"code":200,"code":0}',b'{"code":200,"data":NaN}',b'not json'])
def test_bad_json_preserves_raw_failure(tmp_path,body):
    params=b.plan(CONFIG)[0][2]
    result=m.capture('stock',params,tmp_path/'raw',fetch=lambda *args:(200,body),clock=lambda:CLOCK)
    assert result['status']!='COMPLETE' and not result['rows']
    assert (tmp_path/'raw'/'page-1.json').read_bytes()==body


def test_current_session_is_not_completed(tmp_path):
    config=deepcopy(CONFIG);config['session']='2026-09-22'
    with pytest.raises(ValueError,match='COMPLETED_SESSION_REQUIRED'):b.prepare(config,tmp_path/'out',fetch=lambda *a:pytest.fail('network'),clock=lambda:CLOCK)


def test_bad_company_scope_no_requests(tmp_path):
    with pytest.raises(ValueError,match='COMPANY_SCOPE_INVALID'):
        b.prepare(CONFIG,tmp_path/'out',company={'wrong':1},fetch=lambda *a:pytest.fail('network'),clock=lambda:CLOCK)


def test_request_without_key_never_opens_network(monkeypatch):
    monkeypatch.delenv('FTSHARE_API_KEY',raising=False)
    monkeypatch.setattr(m,'build_opener',lambda *a:pytest.fail('network'))
    with pytest.raises(ValueError,match='AUTHENTICATION_UNAVAILABLE'):m.request('stock',b.plan(CONFIG)[0][2])
