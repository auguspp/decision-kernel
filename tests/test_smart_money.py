"""Offline contracts. Synthetic fixtures are not evidence of actual traders."""
from copy import deepcopy
from datetime import datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import runpy
import socket

import pytest
import requests

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import smart_money_sources as s
from decision_kernel.runtime import smart_money_capture as c
from decision_kernel.runtime import smart_money_documents as d
from decision_kernel.runtime import smart_money_view as v

NOW='2026-09-26T01:20:00+00:00'
DAY='2026-09-24'
IDENT={'repository':'auguspp/decision-kernel','workflow':s.WORKFLOW,'ref':'refs/heads/main',
       'event':'workflow_dispatch','code_commit':'a'*40,'run_id':900001,'attempt':1}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args,**kwargs):raise AssertionError('unexpected live network')
    monkeypatch.setattr(socket.socket,'connect',denied)
    monkeypatch.setattr(socket,'getaddrinfo',denied)


def cal():
    days=['2026-09-21','2026-09-22','2026-09-23','2026-09-24','2026-09-28']
    return {'code':0,'data':{'timestamp':int(s.clock(NOW).timestamp()*1000),
        'item':[{'date':x.replace('-',''),'date_ms':int(datetime.combine(s.day(x),time(),s.ZONE).timestamp()*1000)} for x in days]}}


def html(channel='SH',period='2026-06-30'):
    values={'__EVENTTARGET':'','__EVENTARGUMENT':'','__VIEWSTATE':'public-state','__VIEWSTATEGENERATOR':'1234',
            'today':'20260926','sortBy':'stockcode','sortDirection':'asc',
            'originalShareholdingDate':'2026/09/25','alertMsg':'','txtShareholdingDate':period.replace('-','/')}
    inputs=''.join(f'<input name="{k}" value="{val}">' for k,val in values.items())
    exchange='SSE' if channel=='SH' else 'SZSE';code='600000' if channel=='SH' else '000001'
    return (f'<form id="form1" method="post" action="./mutualmarket.aspx?t={channel.lower()}">{inputs}</form>'
        f'<h2 class="ccass-heading">Shareholding Date:{period.replace("-","/")}</h2>'
        f'<table id="mutualmarket-result"><thead><tr><th>Stock Code</th><th>Name</th><th>Shareholding in CCASS</th>'
        f'<th>% of {exchange} listed traded securities</th></tr></thead><tbody><tr>'
        +''.join(f'<td><div class="mobile-list-body">{x}</div></td>' for x in ['90000',f'Sample (A # {code})','1,200','2.5%'])
        +'</tr></tbody></table>').encode()


def example(f,part='disclosures'):
    if f=='hot_money':return {'name':'测试游资标签','rows':[{'thscode':'600000.SH','name':'测试公司','range_days':1,'hot_money_item_net_value':'12.5'}]}
    if f=='institutional':return {'thscode':'600000.SH','name':'测试公司','range_days':3,'org_net_value':'-5','org_buy_num':1,'org_sell_num':2}
    if f=='seats':return {'symbol':'600000.SH','top_buyers':[{'name':'某券商某营业部','buy':'20','sell':'5','net':'15'}],
                         'top_sellers':[{'name':'某券商某营业部','buy':'20','sell':'5','net':'15'}]}
    if f=='northbound':return {'date':part.replace('-',''),'currency':'CNY','total_amount':'30',
                              'channels':{'SH':{'amount':'10','trade_count':1},'SZ':{'amount':'20','trade_count':2}}}
    if f=='holdings':return {'SECUCODE':'600000.SH','SECURITY_CODE':'600000','SECURITY_NAME_ABBR':'测试公司','END_DATE':part,
                            'HOLDER_NAME':'同名甲','HOLDER_CODE':None,'HOLDER_TYPE':'个人','HOLDER_RANK':7,
                            'SHARES_TYPE':'A股','HOLD_NUM':100 if part.endswith('03-31') else 200,'HOLD_RATIO':'0.5',
                            'FREE_HOLDNUM_RATIO':'0.7','NOTICE_DATE':'2026-08-20','HOLD_NUM_CHANGE':'增持','XZCHANGE':100}
    if f=='activity':return {'SECUCODE':'600000.SH','SECURITY_CODE':'600000','SECURITY_NAME_ABBR':'测试公司',
                            'NOTICE_DATE':'2026-09-24','RECEIVE_START_DATE':'2026-09-23','RECEIVE_END_DATE':'2026-09-23',
                            'URL':'AN2026092400001','OBJECT_CODE':'org1','RECEIVE_OBJECT':'测试基金','ORG_TYPE':'基金',
                            'RECEIVE_WAY_EXPLAIN':'线上调研','INVESTIGATORS':'甲、乙'}
    if f=='forecasts':return {'stockCode':'600000','market':'SHANGHAI','stockName':'测试公司','orgCode':'broker1','orgSName':'测试证券',
                             'infoCode':'AP202609240000000001','publishDate':'2026-09-24','title':'测试研报',
                             'predictThisYearEps':None}
    if f=='executives':return {'stock_code':'600000','stock_name':'测试公司','change_date':'2026-09-24','notice_date':'2026-09-24',
                              'changer':'同名甲','change_direction':'增持','change_shares':'100','change_amount':'1200','avg_price':'12'}
    if f=='holder_changes':return {'SECURITY_CODE':'600000','SECURITY_NAME_ABBR':'测试公司','HOLDER_NAME':'同名甲',
                                  'NOTICE_DATE':'2026-09-24','START_DATE':'2026-08-01','END_DATE':'2026-09-23',
                                  'DIRECTION':'减持','CHANGE_NUM':'10','AFTER_HOLDER_NUM':'300'}
    if f=='repurchases':return {'DIM_SCODE':'600000','SECURITYSHORTNAME':'测试公司','REPURCODE':1000,
                               'UPD':'2026-09-24','REPURAMOUNTLOWER':'100','REPURAMOUNTLIMIT':'200',
                               'REPURAMOUNT':'120','REPURNUM':'10','REPURPROGRESS':'004','REPUROBJECTIVE':'员工持股'}
    if f=='placements':return {'SECUCODE':'600000.SH','SECURITY_NAME_ABBR':'测试公司','ISSUE_DATE':'2026-09-24',
                              'SEO_TYPE':'1','FINANCE_CODE':'issue1','ISSUE_NUM':'100','ISSUE_PRICE':'12',
                              'TOTAL_RAISE_FUNDS':'1200','PRICE_PRINCIPLE':'发行股份购买资产','LOCKIN_PERIOD':'三年',
                              'ISSUE_OBJECT':'交易对手甲'}
    raise AssertionError(f)


def transport(req):
    f=req['family'];part=req['partition']
    if f=='calendar':return 200,s.encoded(cal())
    if f=='north_holdings':
        channel=part.split('@')[0];period=part.split('@')[1] if '@' in part else '2026-06-30'
        return 200,html(channel,period)
    row=example(f,part)
    if req['provider']=='HT':
        body={'code':0,'data':{'board_type':'hot_money' if f=='hot_money' else 'org','trade_date':part,
            'timestamp':int(datetime.combine(s.day(part),time(),s.ZONE).timestamp()*1000),
            'count':1,'stock_count':1,'hot_money_items':[row] if f=='hot_money' else [],
            'stock_items':[row] if f=='institutional' else []}}
    elif f=='northbound':body={'code':200,'data':row}
    elif req['provider']=='FT':body={'code':200,'data':{'pageNum':req['page'],'pageSize':200,'total':1,'pages':1,'records':[row]}}
    elif f=='forecasts':body={'pageNo':req['page'],'currentYear':2026,'data':[row],'hits':1,'TotalPage':1}
    else:body={'code':0,'success':True,'result':{'data':[row],'count':1,'pages':1}}
    return 200,s.encoded(body)


def captured(tmp_path,tx=transport,previous=None):
    result=c.capture(tmp_path/'capture',IDENT,previous_state=previous,transport=tx,clock=lambda:NOW,
                     monotonic=lambda:0,sleep=lambda _:None)
    files={p.name:p.read_bytes() for p in (tmp_path/'capture').iterdir()}
    return result,files


@pytest.mark.parametrize('f',s.FAMILIES)
def test_all_independent_families_obtain_qualified_synthetic_results(tmp_path,f):
    obs,files=captured(tmp_path)
    parts=[p for p in obs['partitions'] if p['family']==f]
    assert parts and all(p['complete'] for p in parts)
    assert obs['status']=='READY'
    assert c.replay(files,IDENT,cutoff=NOW)==obs
    assert obs['source_calls_during_replay']==0 and not obs['automatic_full']


def test_holiday_calendar_not_calendar_day_defines_windows(tmp_path):
    obs,_=captured(tmp_path)
    assert obs['target_date']=='2026-09-26' and obs['trading_sessions'][-1]=='2026-09-24'
    assert not any(p['partition']=='2026-09-25' for p in obs['partitions'])


@pytest.mark.parametrize('kind',['wrong_ref','wrong_workflow','rerun','foreign','bool_run','bool_attempt','event'])
def test_identity_boundary_precedes_output_and_source(tmp_path,kind):
    obj=deepcopy(IDENT)
    changes={'wrong_ref':('ref','refs/heads/other'),'wrong_workflow':('workflow','x'),
      'rerun':('attempt',2),'foreign':('repository','other/repo'),'bool_run':('run_id',True),
      'bool_attempt':('attempt',True),'event':('event','push')}
    k,val=changes[kind];obj[k]=val
    calls=[]
    with pytest.raises(ValueError):c.capture(tmp_path/'c',obj,transport=lambda r:calls.append(r))
    assert not calls and not (tmp_path/'c').exists()


@pytest.mark.parametrize('damage',['hash','raw','clock','source_url','extra_file','reorder','target','authority'])
def test_original_bytes_identity_and_plan_reject_forgery(tmp_path,damage):
    obs,files=captured(tmp_path);manifest=json.loads(files['capture.json'])
    if damage=='hash':manifest['capture_hash']='0'*64
    elif damage=='raw':files['raw-0001.body']+=b' '
    elif damage=='clock':manifest['records'][1]['requested_at']='2027-01-01T00:00:00Z'
    elif damage=='source_url':manifest['records'][1]['request']['url']='https://unreviewed.invalid/'
    elif damage=='extra_file':files['code.py']=b'print(1)'
    elif damage=='reorder':manifest['records'][1],manifest['records'][2]=manifest['records'][2],manifest['records'][1]
    elif damage=='target':manifest['plan']['target_date']='2026-09-25'
    else:manifest['authority']['automatic_full']=True
    if damage!='hash':manifest['capture_hash']=canonical_hash({k:v for k,v in manifest.items() if k!='capture_hash'})
    files['capture.json']=s.encoded(manifest)
    with pytest.raises((ValueError,KeyError)):c.replay(files,IDENT,cutoff=NOW)


@pytest.mark.parametrize('status',[401,403,429])
def test_provider_policy_stops_only_affected_provider(tmp_path,status):
    calls=[]
    def tx(req):
        calls.append(req)
        if req['provider']=='FT':return status,b'{"error":"bounded"}'
        return transport(req)
    obs,files=captured(tmp_path,tx)
    assert sum(x['provider']=='FT' for x in calls)==1
    assert any(p['family']=='activity' and p['complete'] for p in obs['partitions'])
    assert any(g['family']=='executives' for g in obs['unresolved'])
    assert c.replay(files,IDENT,cutoff=NOW)==obs


def test_busy_hithink_does_not_block_public_disclosures(tmp_path):
    obs=c.capture(tmp_path/'c',IDENT,skip_hithink=True,transport=transport,clock=lambda:NOW,monotonic=lambda:0,sleep=lambda _:None)
    assert any(g['partition']=='CALENDAR_UNAVAILABLE' for g in obs['unresolved'])
    assert any(p['family']=='holdings' and p['complete'] for p in obs['partitions'])
    assert not any(p['family']=='hot_money' for p in obs['partitions'])


def test_row_error_not_quiet_other_rows_survive(tmp_path):
    def tx(req):
        status,raw=transport(req)
        if req['family']=='executives':
            obj=json.loads(raw);obj['data']['records'][0]['notice_date']='2027-01-01';return 200,s.encoded(obj)
        return status,raw
    obs,_=captured(tmp_path,tx)
    p=next(p for p in obs['partitions'] if p['family']=='executives')
    assert not p['complete'] and p['row_errors']
    assert any(p['complete'] for p in obs['partitions'] if p['family']=='repurchases')


def test_exact_stock_windows_not_merged_into_current_holdings():
    req=s.spec('institutional',DAY,DAY,DAY)
    one=example('institutional');two={**one,'range_days':1}
    a=s.normalize(one,req,0,1)[0];b=s.normalize(two,req,1,1)[0]
    assert a['id']!=b['id'] and a['values']['holding']=='NOT_INFERRED'
    req=s.spec('hot_money',DAY,DAY,DAY)
    row=s.normalize(example('hot_money'),req,0,1)[0]
    assert row['values']['seat_mapping']=='NOT_SUPPLIED_BY_THIS_SOURCE'


def test_seat_buy_sell_list_duplicates_are_one_observation():
    req=s.spec('seats',DAY,DAY,DAY)
    rows=s.normalize(example('seats'),req,0,1)
    assert len(rows)==1 and len(rows[0]['source_rows'])==2
    assert rows[0]['values']['window_days'] is None
    changed=example('seats');changed['close']='999'
    assert s.normalize(changed,req,0,1)[0]['id']==rows[0]['id']


def test_homonym_natural_people_never_merged_across_issuers():
    req=s.spec('holdings','2026-06-30','2026-06-28','2026-09-26')
    row=example('holdings','2026-06-30');a=s.normalize(row,req,0,1)[0]
    row['SECUCODE']='000001.SZ';row['SECURITY_CODE']='000001';b=s.normalize(row,req,1,1)[0]
    assert a['actor_name']==b['actor_name'] and a['actor_id']!=b['actor_id']
    assert a['values']['shares']=='2E+2' and a['values']['identity'].startswith('ISSUER_SCOPED')


def test_visit_event_count_not_participant_rows():
    req=s.spec('activity','disclosures','2026-06-28','2026-09-26')
    row=example('activity');a=s.normalize(row,req,0,1)[0]
    b=s.normalize({**row,'OBJECT_CODE':'org2','RECEIVE_OBJECT':'基金乙'},req,1,1)[0]
    z=s.normalize({**row,'OBJECT_CODE':None,'RECEIVE_OBJECT':'投资者'},req,2,1)[0]
    grouped=s.aggregate_activity([a,b,z])
    assert len(grouped)==1 and grouped[0]['values']['known_institution_codes']==2
    assert grouped[0]['values']['distinct_institutions'] is None and grouped[0]['values']['participants_count'] is None


def test_forecast_relative_slots_do_not_invent_year_or_revision():
    req=s.spec('forecasts','disclosures','2026-06-28','2026-09-26')
    row={**example('forecasts'),'predictThisYearEps':'2.3'}
    out=s.normalize(row,req,0,1,{'currentYear':2026})[0]['values']
    assert out['target_period']=='NOT_REPORT_VERIFIED' and out['currency'] is None


def test_actual_vs_plan_and_asset_purchase_vs_cash():
    req=s.spec('repurchases','disclosures','2026-06-28','2026-09-26')
    vals=s.normalize(example('repurchases'),req,0,1)[0]['values']
    assert vals['executed_cumulative_cny']=='1.2E+2' and vals['planned_max_cny']=='2E+2'
    assert vals['actual_cancelled_shares'] is None
    req=s.spec('placements','disclosures','2026-06-28','2026-09-26')
    vals=s.normalize(example('placements'),req,0,1)[0]['values']
    assert vals['consideration']=='ASSET_PURCHASE_DESCRIBED' and vals['actual_cash_received_cny'] is None


def test_aggregate_turnover_never_called_net_flow():
    req=s.spec('northbound',DAY,DAY,DAY)
    values=s.normalize(example('northbound',DAY),req,0,1)[0]['values']
    assert values['turnover_cny']=='3E+1' and values['net_buy_cny'] is None
    bad=example('northbound',DAY);bad['total_amount']='31'
    with pytest.raises(ValueError):s.normalize(bad,req,0,1)


def test_hkex_actual_displayed_quarter_not_default_hidden_date():
    req=s.spec('north_holdings','SH','2026-06-28','2026-09-26')
    data=d.northbound_table(html(),req)
    assert data['period']=='2026-06-30' and data['rows'][0]['code']=='600000.SH'
    req=s.spec('north_holdings','SH@2026-03-31','2026-06-28','2026-09-26')
    with pytest.raises(ValueError):d.northbound_table(html(),req)
    form=d.post_form(html(),'SH','2026-03-31')
    assert form['txtShareholdingDate']=='2026/03/31' and form['__EVENTTARGET']=='btnSearch'


def test_publishing_same_capture_does_not_erase_increment(tmp_path):
    obs,_=captured(tmp_path);first=v.history(obs)
    assert v.history(obs,first)==first and first['first_baseline']
    second=deepcopy(obs);second['capture_hash']='c'*64
    changed=v.history(second,first)
    assert changed['changes']['UNCHANGED']>0 and not changed['first_baseline']
    assert len(changed['records'])==len(first['records'])


def test_gzip_history_and_browse_roundtrip_escape_sources(tmp_path):
    obs,_=captured(tmp_path);hist=v.history(obs);chunks,meta=v.encode_chunks(hist)
    assert v.decode_chunks(meta,chunks)==hist
    overview=v.summarize(obs,hist)
    assert overview['holding_comparisons']['comparable_nonzero_pairs']==1
    page=v.browser(overview,chunks,meta,{})
    assert 'fetch(' not in page and 'innerHTML' not in page
    assert 'textContent' in page and 'sha256-' in page
    bad=dict(chunks);key=next(iter(bad));bad[key]+=b' '
    with pytest.raises(ValueError):v.decode_chunks(meta,bad)


def test_unrelated_later_success_does_not_erase_uncovered_historical_gap(tmp_path):
    # Outside the bounded one-year recovery capability; later success cannot erase it.
    old={'version':s.VERSION,'unresolved':[{'family':'activity','partition':'disclosures',
         'begin':'2024-01-01','end':'2024-02-01','failure':'TRANSPORT_TIMEOUT'}]}
    obs,_=captured(tmp_path,previous=old)
    assert any(g.get('begin')=='2024-01-01' for g in obs['unresolved'])


def test_actual_expanded_disclosure_query_can_close_covered_old_gap(tmp_path):
    old={'version':s.VERSION,'unresolved':[{'family':'activity','partition':'disclosures',
         'begin':'2026-01-01','end':'2026-02-01','failure':'TRANSPORT_TIMEOUT'}]}
    obs,files=captured(tmp_path,previous=old)
    part=next(p for p in obs['partitions'] if p['family']=='activity')
    assert part['begin']=='2026-01-01' and part['complete']
    assert not any(g.get('family')=='activity' for g in obs['unresolved'])
    assert c.replay(files,IDENT,cutoff=NOW)==obs


def test_known_calendar_gap_can_close_but_retains_exact_dated_gaps(tmp_path):
    old={'version':s.VERSION,'unresolved':[{'family':'seats','partition':'CALENDAR_UNAVAILABLE','failure':'CALENDAR_UNAVAILABLE'}]}
    obs,_=captured(tmp_path,previous=old)
    assert not obs['unresolved']


def test_quarterly_baseline_reuse_has_explicit_age(tmp_path):
    obs,_=captured(tmp_path);state=v.state(obs)
    plan=c.make_plan(NOW,cal(),state)
    assert len(plan['deferred_partitions'])==2
    assert all(p['family']=='holdings' for p in plan['deferred_partitions'])
    later=c.make_plan('2026-10-04T01:20:00Z',cal(),state)
    assert not later['deferred_partitions']


@pytest.mark.parametrize('number,expect',[(1,'RUN_INITIAL_OR_DAILY'),(4,'SKIP_DAILY_ATTEMPT_BOUND')])
def test_bounded_daily_control(number,expect):
    mod=runpy.run_path('.github/scripts/smart-money-control.py')
    assert mod['choose'](None,'2026-09-26',number,'schedule')==expect


def test_delivery_control_noops_and_stops_unknown_not_all_failures_retried():
    choose=runpy.run_path('.github/scripts/smart-money-control.py')['choose']
    prev={'target_date':'2026-09-26','unresolved':[]}
    assert choose(prev,'2026-09-26',2,'schedule')=='SKIP_ALREADY_DELIVERED'
    prev['unresolved']=[{'failure':'HTTP_429'}]
    assert choose(prev,'2026-09-26',2,'schedule')=='SKIP_NONTRANSIENT_GAPS'
    prev['unresolved']=[{'failure':'TRANSPORT_TIMEOUT'}]
    assert choose(prev,'2026-09-26',2,'schedule')=='RUN_BOUNDED_RECOVERY'


def test_workflow_lifecycle_source_scope_and_reader_link():
    text=Path('.github/workflows/radar-smart-money.yml').read_text()
    assert "'20 9 * * 1-5'" in text and "'10 12 * * 1-5'" in text
    assert 'contents: write' not in text and 'workflow_run:' not in text
    primary=text.split('  capture-smart-money:',1)[1].split('  capture-tushare-relay:',1)[0]
    source=primary.split('- name: Capture public participants',1)[1].split('- name: Rebuild originals',1)[0]
    assert 'GH_TOKEN' not in source and 'FTSHARE_API_KEY' in source
    after=primary.split('- name: Rebuild originals',1)[1]
    assert 'TUSHARE_PROXY_API_KEY' not in primary and 'secrets.' not in after
    relay=text.split('  capture-tushare-relay:',1)[1]
    assert 'needs: capture-smart-money' in relay
    assert 'TUSHARE_PROXY_API_KEY: ${{ secrets.TUSHARE_PROXY_API_KEY }}' in relay
    assert 'actions/download-artifact@v8' in relay and 'digest-mismatch: error' in relay
    assert 'HITHINK_FINANCE_API_KEY' not in relay and 'FTSHARE_API_KEY' not in relay
    assert 'radar-smart-money' in Path('.github/workflows/current-state-read-entry.yml').read_text()
