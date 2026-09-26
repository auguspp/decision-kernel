"""Small synthetic analogues of faults exposed by first complete source run.

The actual 204-request archive is separately replayed, not embedded in CI.
"""
from copy import deepcopy
from datetime import timedelta
import json
import pytest
from decision_kernel.runtime import smart_money_sources as s
from decision_kernel.runtime import smart_money_capture as c
from decision_kernel.runtime import smart_money_documents as d
from decision_kernel.runtime import smart_money_view as v
from test_smart_money_continuity import calendar, obs, part, row, NOW


def test_legacy_pdf_selection_uses_original_broker_order_not_new_issuer_pairs():
    rows=[]
    for i in range(14):
        rows.append({'ticker':f'600{i:03d}.SH','actor_id':str(i//2),'disclosed':'2026-09-24',
                     'values':{'report_id':str(i),'eps_slots':['1']}})
    assert [r['values']['report_id'] for r in d.select_reports(rows,legacy=True)]==list(map(str,range(12)))
    assert len(d.select_reports(rows))==6


def test_request_revision_keeps_legacy_size_but_new_small_families_use_500():
    for f in ('repurchases','holder_changes','activity'):
        a=s.spec(f,'disclosures','2026-06-28','2026-09-26',revision=1)
        b=s.spec(f,'disclosures','2026-06-28','2026-09-26')
        assert a['params']['pageSize']=='1000' and 'contract_revision' not in a
        assert b['params']['pageSize']=='500' and b['contract_revision']==2
    with pytest.raises(ValueError):s.spec('activity','disclosures','2026-06-28','2026-09-26',revision=True)


def test_busy_body_is_transient_but_other_provider_failure_is_not():
    assert c._http_reason(200,b'{"success":false,"code":9701}')=='SOURCE_BUSY'
    assert c._http_reason(200,b'{"success":false,"code":9201}') is None
    assert c._http_reason(429,b'anything')=='HTTP_429'


def test_anonymous_institution_rows_do_not_become_one_actor_or_fake_conflict():
    request=s.spec('seats','2026-09-24','2026-09-24','2026-09-24')
    x={'buy':'100','sell':'20','net':'80','name':'机构专用'}
    raw={'symbol':'600001.SH','top_buyers':[x,x],'top_sellers':[x]}
    rows=s.normalize(raw,request,0,1)
    assert len(rows)==3 and len({r['id'] for r in rows})==3
    assert all(r['values']['additive_across_sides'] is False for r in rows)
    assert s.economic_rows(rows)[1]==0


def test_same_holder_code_distinct_named_accounts_and_same_name_ranks_remain_rows():
    req=s.spec('holdings','2026-06-30','2026-06-28','2026-09-26')
    base={'SECUCODE':'600001.SH','SECURITY_CODE':'600001','END_DATE':'2026-06-30',
          'NOTICE_DATE':'2026-08-30','HOLDER_CODE':'x','HOLDER_NAME':'测试账户','HOLD_NUM':100,
          'SHARES_TYPE':'A股','HOLDER_RANK':2}
    a=s.normalize(base,req,0,1)[0]
    b=s.normalize({**base,'HOLDER_NAME':'测试账户(QFII)','HOLDER_RANK':7},req,1,1)[0]
    assert a['id']!=b['id'] and a['actor_id']==b['actor_id']
    base['HOLDER_CODE']=None
    a=s.normalize(base,req,0,1)[0];b=s.normalize({**base,'HOLDER_RANK':7},req,1,1)[0]
    assert a['id']!=b['id'] and a['actor_id']==b['actor_id']


def test_reinterpretation_keeps_same_capture_but_does_not_hide_parser_correction():
    o=obs([part(rows=[row()])]);old=v.history(o)
    old.pop('projection_revision')
    fixed=deepcopy(o);fixed['partitions'][0]['rows'][0]=row(shares='200')
    h=v.history(fixed,old)
    assert h['capture_hash']==old['capture_hash'] and h['reinterpretation'] is True
    assert len(h['records'])==1 and h['records'][0]['data']['values']['shares']=='200'
    assert h['changes']=={'REINTERPRETED_SAME_SOURCE_NOT_NEW_EVENT':1}
    assert v.history(fixed,h)==h


def test_pending_repair_keeps_new_uncollected_dates_and_skips_completed_dates():
    previous={'version':s.VERSION,'cutoff':NOW,'target_date':'2026-09-26',
              'unresolved':[{'family':'activity','partition':'disclosures','begin':'2026-06-28',
                             'end':'2026-09-26','failure':'SOURCE_BUSY'}],
              'completed_partitions':[{'family':f,'partition':'2026-09-24','begin':'2026-09-24',
                'end':'2026-09-24','cutoff':NOW} for f in ('seats','hot_money','institutional','northbound')]}
    cal=calendar('2026-09-28');p=c.make_plan('2026-09-28T09:00:00+00:00',cal,previous,pending_only=True)
    assert any(x['family']=='seats' and x['partition']=='2026-09-28' for x in p['partitions'])
    assert not any(x['family']=='seats' and x['partition']=='2026-09-24' for x in p['partitions'])
    assert any(x['family']=='seats' and x['partition']=='2026-09-24' for x in p['deferred_partitions'])


def test_legacy_plan_shape_stays_legacy_and_new_watermarks_explicit():
    cal=calendar()
    old=c.make_plan(NOW,cal,track_calendar=False)
    new=c.make_plan(NOW,cal)
    assert not any(k in old for k in ('calendar_enumerated_through','calendar_pending_since','pending_only'))
    assert new['calendar_enumerated_through']=='2026-09-24' and new['pending_only'] is False
