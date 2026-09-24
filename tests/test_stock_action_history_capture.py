"""Real planner/capture/replayer; synthetic histories and events; no live calls."""
import copy
from pathlib import Path
import runpy
import shutil
from datetime import datetime, time, timedelta

import pytest

from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime import hithink_stock_reading as own
from test_stock_issuer_isolation import expanded_provider, rehash_capture
from test_stock_radar_capture import setup
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def scenario(tmp_path,monkeypatch,*,failure=3002,partial=False):
    state,plan,provider,calls=expanded_provider(monkeypatch,3)
    mod,_,out,_,pauses,run=setup(tmp_path)
    bad=plan['issuers'][0]['thscode']
    old=state.sessions[-61]-timedelta(days=200)
    old_ms=int(datetime.combine(old,time(),stock.SHANGHAI_TZ).timestamp()*1000)
    def request(path,params):
        body=provider(path,params)
        if path==own.ACTIONS:
            code=params['thscode']
            assert params=={'thscode':code,'to':state.sessions[-1].isoformat()}
            if code==bad and not partial:
                return {'code':failure,'data':None,'message':'No adjustment events for thscode='+bad}
            body['data']['item']=[{'ticker':code[:6],'ex_date_ms':old_ms,
                                  'dividend_per_share':'0.2','per_share_bonus':0}]
            if code==bad and partial: body['data']['has_more']=True
        return body
    report=run(reference_inputs=None,transport=request)
    return mod,out,report,calls,pauses


@pytest.fixture(scope='module')
def partial_history_capture_baseline(tmp_path_factory):
    """Retain one real partial capture as immutable input, never a cached verdict."""
    with pytest.MonkeyPatch.context() as patch:
        prohibit_network(patch)
        root=tmp_path_factory.mktemp('stock-action-history-baseline')
        mod,out,report,_,_=scenario(root,patch)
        assert report['status']==mod['PARTIAL']
        rebuilt=mod['verify'](out)
        assert rebuilt['network_calls']==0 and rebuilt['coverage']==report['coverage']
        return out


@pytest.fixture
def partial_history_capture_copy(tmp_path,partial_history_capture_baseline):
    """Each tamper owns its files, report and real replay callable."""
    out=tmp_path/'reading'
    shutil.copytree(partial_history_capture_baseline,out)
    root=Path(__file__).resolve().parents[1]
    mod=runpy.run_path(str(root/'.github/scripts/capture-stock-reading.py'))
    return mod,out,mod['read'](out/'capture.json')


@pytest.mark.parametrize('partial',[False,True])
def test_uniform_history_requests_retain_events_and_rebuild_partial_result(tmp_path,monkeypatch,partial):
    mod,out,r,calls,pauses=scenario(tmp_path,monkeypatch,partial=partial)
    assert r['status']==mod['PARTIAL']
    assert r['coverage']['unavailable_issuers']==1 and r['coverage']['qualified_issuers']==2
    p=mod['read'](out/'stock-reading.json')['projection']
    assert p['policy']['source_contract']==own.CONTRACT
    requests=[e for e in r['requests'] if e['path']==own.ACTIONS]
    assert len(requests)==3 and len({e['params']['thscode'] for e in requests})==3
    assert all(set(e['params'])=={'thscode','to'} for e in requests)
    assert len(calls)<=mod['read'](out/'plan.json')['maximum_request_count']<=26
    for row in p['surfaced_stocks']:
        m=row['stock_path']['input_checks']
        assert m['corporate_action_query']['events_before_price_window']==1
        assert len(m['reported_corporate_actions'])==1
        assert row['stock_path']['returns']['60'] is not None
        assert not m['corporate_action_query']['exhaustive_absence_proven']
    replay=mod['verify'](out)
    assert replay['coverage']==r['coverage'] and replay['requests_replayed']==len(calls)
    assert replay['network_calls']==0 and replay['stock_count']==2
    assert pauses==[20]*(len(calls)-1)
    assert '已报告公司行为' in (out/'index.html').read_text()
    assert p['human_attention_authority']==p['research_authority']==p['investment_authority']=='NONE'


@pytest.mark.parametrize('status',[4001,2001,5003])
def test_history_request_does_not_retry_or_isolate_batch_fatal_codes(tmp_path,monkeypatch,status):
    mod,out,r,calls,_=scenario(tmp_path,monkeypatch,failure=status)
    assert r['status']==mod['FAILED'] and r['failure_category']=='REQUEST_FAILED'
    requests=[e for e in r['requests'] if e['path']==own.ACTIONS]
    assert len(requests)==1
    assert not (out/'stock-reading.json').exists()
    assert mod['verify'](out)['network_calls']==0


@pytest.mark.parametrize('tamper',['add_from','remove_to','change_to','inject_recent_event'])
def test_replayer_binds_exact_history_request_and_full_retained_event_list(partial_history_capture_copy,tamper):
    mod,out,r=partial_history_capture_copy
    entry=[e for e in r['requests'] if e['path']==own.ACTIONS][1]
    if tamper=='add_from': entry['params']['from']='2026-06-01'
    elif tamper=='remove_to': del entry['params']['to']
    elif tamper=='change_to': entry['params']['to']='2020-01-01'
    else:
        h=next(e for e in r['requests'] if e['path']==own.HISTORY and e['params']['thscode']==entry['params']['thscode'])
        file=out/entry['response_file'];body=mod['read'](file)
        recent=copy.deepcopy(body['data']['item'][0])
        recent['ex_date_ms']=mod['read'](out/h['response_file'])['data']['item'][50]['date_ms']
        body['data']['item'].insert(0,recent)
        file.write_bytes(mod['data'](body))
    rehash_capture(mod,out,r)
    with pytest.raises(ValueError): mod['verify'](out)


def test_production_transport_only_sends_the_pinned_to_only_request(monkeypatch):
    from decision_kernel.runtime import hithink_dump_trial as transport
    calls=[];payload=b'{"code":3002,"data":null,"message":"No adjustment events"}'
    class Response:
        status_code=200;headers={'Content-Length':str(len(payload))}
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def iter_content(self,chunk_size): yield payload
    class Session:
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def get(self,url,**kw): calls.append((url,kw));return Response()
    monkeypatch.setattr(transport,'_session',Session)
    params={'thscode':'002714.SZ','to':'2026-09-07'}
    result=own.request_json(own.ACTIONS,params,api_key='synthetic-test-key')
    assert result['code']==3002 and result['data'] is None and len(calls)==1
    assert calls[0][1]['params']==params and calls[0][1]['allow_redirects'] is False
    for bad in ({**params,'from':'2026-06-12'},{'thscode':'002714.SZ'},{}):
        with pytest.raises(ValueError): own.request_json(own.ACTIONS,bad,api_key='synthetic-test-key')
    assert len(calls)==1
