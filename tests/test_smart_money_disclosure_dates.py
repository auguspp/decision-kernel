"""Disclosure variants and deferred PDF context; all fixtures are synthetic."""
from copy import deepcopy
from hashlib import sha256

import pytest

from decision_kernel.runtime import smart_money_capture as c
from decision_kernel.runtime import smart_money_sources as s
from decision_kernel.runtime import smart_money_view as v
from decision_kernel.runtime import smart_money_reading as reading
from test_smart_money import example, NOW, IDENT, captured


def activity_rows():
    request=s.spec('activity','disclosures','2026-06-28','2026-09-26')
    one=example('activity');two={**one,'NOTICE_DATE':'2026-09-25'}
    return request,one,two


def test_duplicate_disclosure_dates_preserve_both_without_inventing_public_time():
    q,a,b=activity_rows()
    records=[s.normalize(x,q,i,2)[0] for i,x in enumerate((a,b))]
    result=s.aggregate_activity(records)
    assert len(result)==1
    row=result[0]
    assert row['disclosed'] is None
    assert row['values']['disclosure_date_claims']==['2026-09-24','2026-09-25']
    assert row['values']['disclosure_date_status']=='MULTIPLE_SOURCE_DATES_NOT_RESOLVED'
    assert len(row['source_rows'])==2 and len(row['values']['roster'])==1
    assert s.aggregate_activity(list(reversed(records)))[0]['version']==row['version']


@pytest.mark.parametrize('field,value',[('ticker','600001.SH'),('date','2026-09-20')])
def test_actual_event_identity_conflicts_still_rejected(field,value):
    q,a,b=activity_rows()
    records=[s.normalize(x,q,i,2)[0] for i,x in enumerate((a,b))]
    records[1][field]=value
    with pytest.raises(s.SourceError,match='ACTIVITY_EVENT_CONFLICT'):
        s.aggregate_activity(records)


def test_multiple_reported_institution_counts_are_not_last_write_wins():
    q,a,b=activity_rows();a['SUM']=5;b['SUM']=8
    result=s.aggregate_activity([s.normalize(x,q,i,2)[0] for i,x in enumerate((a,b))])[0]
    assert result['values']['provider_reported_institution_entries'] is None
    assert result['values']['reported_institution_entry_claims']==['5','8']


def test_complete_pages_can_contain_explicit_date_ambiguity_without_losing_family():
    q,a,b=activity_rows()
    raw=s.encoded({'success':True,'code':0,'result':{'data':[a,b],'count':2,'pages':1}})
    rec={'index':2,'request':q,'body':'raw-0002.body','http_status':200,'error':None}
    scope={k:q[k] for k in ('family','partition','begin','end')}
    result=c._parse_partition([rec],{'raw-0002.body':raw},scope)
    assert result['complete'] and result['normalized_rows']==1
    assert result['returned_rows']==2 and result['source_version_conflicts']==1
    assert result['conflicting_identities']==0 and result['ambiguous_disclosure_groups']==1


def test_future_buyback_finish_does_not_erase_observed_amount_or_claim_completion():
    q=s.spec('repurchases','disclosures','2026-06-28','2026-09-26')
    row={**example('repurchases'),'FINISHDATE':'2027-07-03'}
    r=s.normalize(row,q,0,1)[0]
    assert r['values']['actual_finish'] is None and r['date']=='2026-09-24'
    assert r['values']['executed_cumulative_cny']=='1.2E+2'
    assert r['values']['finish_date_raw']=='2027-07-03'
    assert r['values']['field_gaps']==['FUTURE_FINISH_FIELD_NOT_ACTUAL_COMPLETION']
    row['UPD']='2027-07-03'
    with pytest.raises(s.SourceError,match='FUTURE_SOURCE_DATE'):
        s.normalize(row,q,0,1)


def test_deferred_forecast_documents_keep_original_capture_not_new_cutoff(tmp_path):
    obs,_=captured(tmp_path)
    obs['forecast_documents']=[{'report_id':'AP202609240000000001','status':'REPORTED_COMPARABLE_REVISION','revisions':[]}]
    first=v.history(obs)
    newer=deepcopy(obs);newer['capture_hash']='2'*64
    newer['cutoff']='2026-09-26T02:30:00+00:00'
    newer['forecast_documents']=[];newer['partitions']=[p for p in obs['partitions'] if p['family']!='forecasts']
    hist=v.history(newer,first)
    doc=v.summarize(newer,hist)['forecast_documents'][0]
    assert doc['origin_capture_hash']==obs['capture_hash'] and doc['origin_cutoff']==obs['cutoff']


def test_missing_document_metadata_restores_only_exact_saved_origin(monkeypatch):
    old={'history':{'records':[{'family':'forecasts','origin':'a'*64}]},
         'origins':{'a'*64:{'cutoff':NOW,'run':{'id':4}}}}
    obs={'partitions':[],'cutoff':NOW};calls=[]
    def load(col,run,*,follow_control):
        calls.append((run,follow_control))
        return {'observation':{'capture_hash':'a'*64,'cutoff':NOW,
            'forecast_documents':[{'report_id':'r','status':'NO_QUALIFIED_REVISION_PATTERN'}]}}
    monkeypatch.setattr(reading,'read_run',load)
    reading.restore_deferred_documents(None,old,obs)
    assert calls==[({'id':4},False)]
    assert old['history']['forecast_documents'][0]['origin_capture_hash']=='a'*64
    reading.restore_deferred_documents(None,old,obs)
    assert len(calls)==1


def test_wrong_origin_does_not_turn_into_successful_document_recovery(monkeypatch):
    old={'history':{'records':[{'family':'forecasts','origin':'a'*64}]},
         'origins':{'a'*64:{'cutoff':NOW,'run':{'id':4}}}}
    monkeypatch.setattr(reading,'read_run',lambda *a,**k:{'observation':{'capture_hash':'b'*64,'cutoff':NOW}})
    reading.restore_deferred_documents(None,old,{'partitions':[],'cutoff':NOW})
    assert 'forecast_documents' not in old['history']
    assert old['history']['forecast_document_recovery'].startswith('RETAINED_DOCUMENT_CONTEXT_GAP_')


def test_independent_northbound_channels_never_withdraw_each_others_rows(tmp_path):
    obs,_=captured(tmp_path)
    hist=v.history(obs)
    rows=v.latest_rows(hist,'north_holdings')
    assert len(rows)==4
    assert {r['ticker'][-2:] for r in rows}=={'SH','SZ'}
    assert len(v.latest_rows(v.history({**obs,'capture_hash':'9'*64},hist),'north_holdings'))==4


def test_recent_disclosure_of_old_event_remains_in_history(tmp_path):
    obs,_=captured(tmp_path)
    part=next(p for p in obs['partitions'] if p['family']=='repurchases')
    row=part['rows'][0];row['date']='2025-01-01'
    hist=v.history(obs)
    assert any(r['id']==row['id'] for r in v.latest_rows(hist,'repurchases'))
