"""Synthetic source/continuity contracts. No market or investment claims.

Actual saved-probe replay is separately recorded in the delivery receipt; these
fixtures intentionally contain invented actors and are never published as data.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta
import gzip
import io
import json
from pathlib import Path
import runpy
import socket
import zipfile

import pytest
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import smart_money_sources as s
from decision_kernel.runtime import smart_money_capture as c
from decision_kernel.runtime import smart_money_view as v

NOW='2026-09-26T02:00:00+00:00'
CODE='a'*40
IDENT={'repository':'auguspp/decision-kernel','workflow':s.WORKFLOW,'ref':'refs/heads/main',
       'event':'workflow_dispatch','code_commit':CODE,'run_id':900001,'attempt':1}

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a,**k): raise AssertionError('unexpected network in synthetic test')
    monkeypatch.setattr(socket.socket,'connect',denied)
    monkeypatch.setattr(socket,'getaddrinfo',denied)


def calendar(last='2026-09-24',first='2026-09-01'):
    start,end=s.day(first),s.day(last)
    dates=[start+timedelta(days=i) for i in range((end-start).days+1) if (start+timedelta(days=i)).weekday()<5]
    return {'code':0,'data':{'item':[{'date':d.strftime('%Y%m%d'),
       'date_ms':int(datetime.fromisoformat(str(d)+'T00:00:00+08:00').timestamp())*1000} for d in dates]}}


def row(f='holdings',actor='X',code='600001.SH',period='2026-06-30',shares='100',disclosed='2026-08-30'):
    vals={'shares':shares,'share_class':'A股','holder_type':'个人','event_id':None}
    return s._entry(f,[code,actor,period],code,'合成公司',actor,actor,period,disclosed,vals,[0,0])


def part(f='holdings',key='2026-06-30',rows=None,complete=True,begin='2026-06-28',end='2026-09-26'):
    rr=deepcopy(rows or [])
    return {'family':f,'partition':key,'begin':begin,'end':end,'rows':rr,'complete':complete,
      'normalized_rows':len(rr),'returned_rows':len(rr),'provider_total':len(rr),
      'provider_pages':1,'row_errors':[],'failure':None if complete else 'PAGE_OR_TIME_BUDGET'}


def obs(parts=None,cutoff=NOW,hash='1'*64,unresolved=None):
    return {'version':s.VERSION,'partitions':parts or [],'capture_hash':hash,'cutoff':cutoff,
       'target_date':str(s.clock(cutoff).astimezone(s.ZONE).date()),'trading_sessions':['2026-09-24'],
       'unresolved':unresolved or [],'status':'READY','identity':IDENT,'forecast_documents':[],
       'calendar_enumerated_through':'2026-09-24','calendar_pending_since':None}


@pytest.mark.parametrize('value',['600001.SZ','000001.SH','920001.SH','999999','000001.BJ'])
def test_ticker_conflict(value):
    with pytest.raises(ValueError):s.ticker(value)

@pytest.mark.parametrize('value,market',[('600001','SHENZHEN'),('000001','SHANGHAI'),('600001','UNKNOWN')])
def test_short_code_cannot_override_exchange(value,market):
    with pytest.raises(ValueError):s.ticker(value,market)

@pytest.mark.parametrize('value',[True,float('nan'),float('inf'),1.5,{},[],'NaN','Infinity'])
def test_invalid_number(value):
    with pytest.raises((ValueError,TypeError)):s.number(value)

@pytest.mark.parametrize('value',[None,'','--','新进','不变'])
def test_missing_is_not_zero(value):assert s.number(value) is None

def test_zero_negative_separate():
    assert s.number('0')=='0' and s.number('-12.5')=='-12.5'

@pytest.mark.parametrize('bad',[b'{"a":1,"a":2}',b'{"a":NaN}',b'[]',b''])
def test_decode_rejects_unsafe_or_nonobject_when_applicable(bad):
    if bad==b'[]':
        with pytest.raises(ValueError):s.page_data(s.decode(bad),s.spec('holdings','2026-06-30','2026-06-28','2026-09-26'))
    else:
        with pytest.raises(ValueError):s.decode(bad)


def test_same_name_without_provider_id_is_not_cross_company_identity():
    raw={'SECURITY_CODE':'600001','SECUCODE':'600001.SH','END_DATE':'2026-06-30','NOTICE_DATE':'2026-08-30',
         'HOLDER_NAME':'合成同名','HOLD_NUM':100,'SHARES_TYPE':'A股'}
    request=s.spec('holdings','2026-06-30','2026-06-28','2026-09-26')
    a=s.normalize(raw,request,0,0)[0]
    b=s.normalize({**raw,'SECURITY_CODE':'600002','SECUCODE':'600002.SH'},request,1,0)[0]
    assert a['actor_id']!=b['actor_id'] and a['values']['name_match_group']==b['values']['name_match_group']


def test_hot_windows_are_distinct_not_sum():
    rr={'name':'测试游资标签','rows':[{'thscode':'600001.SH','name':'合成','range_days':i,
         'hot_money_item_net_value':n} for i,n in ((1,'100'),(3,'-50'))]}
    rows=s.normalize(rr,s.spec('hot_money','2026-09-24','2026-09-24','2026-09-24'),0,0)
    assert len(rows)==2 and rows[0]['id']!=rows[1]['id']
    assert all(r['values']['holding']=='NOT_INFERRED' for r in rows)


def test_two_sides_same_seat_collapsed_not_double_counted():
    seat={'name':'合成营业部','buy':'100','sell':'30','net':'70'}
    rows=s.normalize({'symbol':'600001.SH','top_buyers':[seat],'top_sellers':[seat]},
        s.spec('seats','2026-09-24','2026-09-24','2026-09-24'),0,0)
    assert len(rows)==1 and len(rows[0]['source_rows'])==2
    assert rows[0]['values']['window_days'] is None


def test_northbound_turnover_is_not_net_flow():
    raw={'channels':{'SH':{'amount':'60'},'SZ':{'amount':'40'}},'total_amount':'100'}
    r=s.normalize(raw,s.spec('northbound','2026-09-24','2026-09-24','2026-09-24'),0,0)[0]
    assert r['values']['turnover_cny']=='1E+2' and r['values']['net_buy_cny'] is None


def test_calendar_outage_does_not_move_recovery_start():
    previous={'version':s.VERSION,'target_date':'2026-09-23','cutoff':'2026-09-23T12:00:00+00:00',
        'calendar_enumerated_through':'2026-09-04','calendar_pending_since':'2026-09-07',
        'unresolved':[{'family':'hot_money','partition':'CALENDAR_UNAVAILABLE','failure':'CALENDAR_UNAVAILABLE'}]}
    p=c.make_plan(NOW,calendar(),previous)
    assert '2026-09-07' in p['trading_sessions']
    assert p['calendar_enumerated_through']=='2026-09-24'


def test_first_calendar_outage_preserves_first_failed_date():
    previous={'version':s.VERSION,'target_date':'2026-09-03','cutoff':'2026-09-03T12:00:00Z',
        'calendar_enumerated_through':None,'calendar_pending_since':'2026-09-01','unresolved':[]}
    p=c.make_plan(NOW,None,previous)
    assert p['calendar_pending_since']=='2026-09-01' and p['trading_sessions']==[]


def test_more_than_twenty_sessions_remain_explicit():
    previous={'version':s.VERSION,'cutoff':'2026-09-01T12:00:00Z','target_date':'2026-09-01',
        'calendar_enumerated_through':'2026-09-01','unresolved':[]}
    p=c.make_plan('2026-10-30T12:00:00Z',calendar('2026-10-30'),previous)
    assert len(p['trading_sessions'])==20 and p['unprocessed_trading_sessions']


def test_source_version_same_capture_repeat_no_fake_new_event():
    o=obs([part(rows=[row()])]);h=v.history(o)
    assert v.history(o,h)==h
    new=v.history(obs([part(rows=[row()])],hash='2'*64),h)
    assert new['changes']=={'UNCHANGED':1} and len(new['records'])==1


def test_complete_same_quarter_correction_removes_only_current_membership():
    old=v.history(obs([part(rows=[row(actor='A'),row(actor='B')])]))
    new=v.history(obs([part(rows=[row(actor='B')])],cutoff='2026-09-26T03:00:00Z',hash='2'*64),old)
    assert len(new['records'])==2   # history still retained
    assert {r['actor_id'] for r in v.latest_rows(new,'holdings')}=={'B'}


def test_partial_same_quarter_does_not_claim_withdrawal():
    old=v.history(obs([part(rows=[row(actor='A'),row(actor='B')])]))
    new=v.history(obs([part(rows=[row(actor='B')],complete=False)],hash='2'*64),old)
    assert {r['actor_id'] for r in v.latest_rows(new,'holdings')}=={'A','B'}


def test_top_ten_absence_is_not_sale_and_requires_both_complete():
    a=part(key='2026-03-31',rows=[row(actor='A',period='2026-03-31')])
    b=part(rows=[row(actor='B')]);h=v.history(obs([a,b]))
    x=v.top_ten_transitions(h)
    assert x['departures'][0]['meaning']=='ABSENT_FROM_DISCLOSED_TOP_TEN_NOT_PROVEN_SALE_OR_ZERO'
    h['coverage']['holdings|2026-03-31']['complete']=False
    assert not v.top_ten_transitions(h)['departures']


def test_unresolved_history_not_hidden_by_today_complete():
    gap={'family':'northbound','partition':'2026-09-10','failure':'HTTP_403'}
    o=obs([part('northbound','2026-09-24')],unresolved=[gap]);h=v.history(o)
    summary=v.summarize(o,h)['families']['northbound']
    assert summary['unresolved_partitions']==1
    assert summary['status']!='COMPLETE_PROVIDER_SCOPES'


def test_invalid_calendar_cannot_claim_late_confirmation():
    o=obs();o.update(trading_sessions=[],calendar_enumerated_through=None,calendar_pending_since='2026-09-26')
    assert v.state(o)['late_confirmation_complete'] is False


def test_chunks_round_trip_reject_hash_damage():
    h=v.history(obs([part(rows=[row()])]))
    chunks,meta=v.encode_chunks(h);assert v.decode_chunks(meta,chunks)==h
    name=next(iter(chunks));damaged=dict(chunks);damaged[name]=chunks[name]+b'X'
    with pytest.raises(ValueError):v.decode_chunks(meta,damaged)


def test_chunks_do_not_exhaust_memory_when_expansion_lies():
    h=v.history(obs([part(rows=[row()])]))
    chunks,meta=v.encode_chunks(h);meta['chunks'][0]['expanded_bytes']=1
    with pytest.raises(ValueError):v.decode_chunks(meta,chunks)


def test_browser_checks_compressed_sha_before_expansion():
    h=v.history(obs([part(rows=[row()])]))
    overview=v.summarize(obs([part(rows=[row()])]),h);chunks,meta=v.encode_chunks(h)
    page=v.browser(overview,chunks,meta,{})
    assert "subtle.digest('SHA-256'" in page and 'ch.ref.sha256' in page
    assert page.index("subtle.digest('SHA-256'")<page.index("new DecompressionStream('gzip')")


def test_activity_partial_coverage_cannot_claim_acceleration():
    r=row('activity',period='2026-09-20');r['values']={'event_id':'event','roster':[], 'unresolved_roster_rows':0}
    r['version']=canonical_hash({k:x for k,x in r.items() if k not in {'version','source_rows'}})
    old=deepcopy(r);old['date']='2026-08-01';old['id']='e'*64;old['values']['event_id']='earlier';old['version']=canonical_hash({k:x for k,x in old.items() if k not in {'version','source_rows'}})
    h=v.history(obs([part('activity','disclosures',[r,old],complete=False)]))
    g=v.attention_counts(h,'2026-09-26')[0]
    assert g['recent_vs_prior_monthly_rate'] is None and g['count_qualification']=='OBSERVED_LOWER_BOUND'


def test_control_waits_for_unpublished_previous_capture():
    mod=runpy.run_path('.github/scripts/smart-money-control.py')
    runs=[{'id':10,'created_at':'2026-09-26T01:00:00Z','status':'completed'},
          {'id':11,'created_at':'2026-09-26T02:00:00Z','status':'in_progress'}]
    calls=[]
    def artifacts(runid):
        calls.append(runid);return {'total_count':1,'artifacts':[{'name':f'smart-money-{runid}-1'}]}
    assert mod['pending_publication'](runs,11,None,artifacts)==10 and calls==[10]


def test_old_institutional_reader_actually_calls_compatibility():
    import ast, inspect
    from decision_kernel.runtime import institutional_radar_reading
    tree=ast.parse(inspect.getsource(institutional_radar_reading._institutional))
    names={a.asname or a.name for node in ast.walk(tree)
           if isinstance(node,ast.ImportFrom) and node.module=='institutional_radar_compat'
           for a in node.names if a.name=='verify'}
    assert names and any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                         and n.func.id in names for n in ast.walk(tree))


def test_compatibility_is_scoped_and_does_not_mutate_original_verifier(tmp_path):
    from test_institutional_radar import run_capture
    from decision_kernel.runtime import institutional_radar_capture as old
    from decision_kernel.runtime import institutional_radar_compat as compat
    root,_,_,_=run_capture(tmp_path)
    receipt=s.decode((root/'capture.json').read_bytes());receipt['implementation']=dict(compat.HISTORICAL)
    receipt['capture_hash']=canonical_hash({k:x for k,x in receipt.items() if k!='capture_hash'})
    (root/'capture.json').write_bytes(s.encoded(receipt))
    installed=old._implementation()
    with pytest.raises(ValueError):old.verify(root)
    result,basis=compat.verify(root)
    assert result['network_calls']==0 and basis=='REVIEWED_SECTOR_ONLY_CHANGE_579'
    assert old._implementation()==installed
    receipt['implementation']['identity.py']='0'*64
    receipt['capture_hash']=canonical_hash({k:x for k,x in receipt.items() if k!='capture_hash'})
    (root/'capture.json').write_bytes(s.encoded(receipt))
    with pytest.raises(ValueError):compat.verify(root)
