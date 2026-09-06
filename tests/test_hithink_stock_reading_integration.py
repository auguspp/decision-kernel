"""Real builder/recorder/replayer code, synthetic HiThink envelopes, network prohibited."""
import copy
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime import hithink_stock_reading as own
from test_stock_radar_reading import prepared, NOW
from test_stock_radar_capture import setup
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def contract_provider(*, missing_quote=False):
    state,ledger,association,plan,base,_=prepared()
    saved={};calls=[]
    def request(path,params):
        calls.append((path,dict(params)))
        if path==own.SNAPSHOT:
            code=params['thscodes'];rows=saved[code]['data']['item'];last=rows[-1]
            row={'thscode':code,'ticker':code[:6],'last_price':last['close_price'],
                 'prev_price':rows[-2]['close_price'],
                 **{k:last[k] for k in ('open_price','high_price','low_price','volume','turnover')}}
            if missing_quote:row.pop('prev_price')
            return {'code':0,'data':{'timestamp':None,'total':5000,'item':[row]}}
        if path==own.ACTIONS:
            code=params['thscode']
            return {'code':0,'data':{'thscode':code,'ticker':code[:6],'item':[]}}
        body=base(path,params)
        if path==own.HISTORY:
            d=body['data']
            for k in ('thscode','interval','adjust'):d.pop(k)
            d['timestamp']=int(NOW.timestamp()*1000)  # ready time, NOT last trade date
            for row in d['item']:
                row.update(open_price=row['close_price'],high_price=row['close_price'],low_price=row['close_price'])
            saved[params['thscode']]=copy.deepcopy(body)
        return body
    return state,plan,request,calls


def test_hithink_only_path_reuses_original_stock_selector_and_full_plan():
    state,plan,request,calls=contract_provider()
    result=stock.observe_stock_reading(plan,state,request_json=request,observed_at=NOW)
    p=result['projection']
    assert p['surfaced_stocks'] and p['reference_input_hash'] is None
    assert p['reference_input_provenance']==stock.HITHINK_RAW
    assert len(calls)<=plan['maximum_request_count']<=26
    for row in p['surfaced_stocks']:
        assert row['stock_path']['history_session_count']==61
        assert row['stock_path']['input_checks']['snapshot_individual_trade_date']=='NOT_SUPPLIED_NOT_INFERRED_FROM_READY_CLOCK'
        assert row['status']=='CONTRACT_CHECKED_RAW_READING'
    assert not any('tushare' in path or 'dump' in path for path,_ in calls)
    assert p['market_state_writes']==p['events_created']==0
    page=stock.render_stock_reading(result)
    assert '没有逐日历史前收核验' in page and '未复权原始价格变化' in page


def test_capture_and_offline_replay_use_real_builder_boundaries_without_reference_fixture(tmp_path):
    mod,state_dir,out,_,_,run=setup(tmp_path)
    _,_,provider,calls=contract_provider()
    before=mod['inventory'](state_dir)
    r=run(reference_inputs=None,transport=provider)  # explicitly SYNTHETIC_TEST_ONLY
    assert r['status']==mod['COMPLETE'],r
    assert not (out/'synthetic-reference-inputs.json').exists()
    assert r['provenance']==mod['SYNTHETIC']
    assert mod['inventory'](state_dir)==before
    v=mod['verify'](out)
    assert v['requests_replayed']==len(calls) and v['network_calls']==0
    assert v['stock_count']>=1 and not r['remote_upload_verified']
    assert '合成验收样本' in (out/'index.html').read_text()


def test_rehashed_action_response_cannot_reuse_success_page(tmp_path):
    mod,_,out,_,_,run=setup(tmp_path)
    _,_,provider,_=contract_provider()
    report=run(reference_inputs=None,transport=provider)
    assert report['status']==mod['COMPLETE']
    entry=next(r for r in report['requests'] if r['path']==own.ACTIONS)
    p=out/entry['response_file'];body=mod['read'](p)
    body['data']['thscode']='000001.SZ'
    p.write_bytes(mod['data'](body))
    report['files']={k:v for k,v in mod['inventory'](out).items() if k!='capture.json'}
    report['capture_hash']=canonical_hash({k:v for k,v in report.items() if k!='capture_hash'})
    (out/'capture.json').write_bytes(mod['data'](report))
    with pytest.raises(ValueError):mod['verify'](out)


def test_transport_reuses_fixed_origin_no_redirects_and_preserves_decimal_lexemes(monkeypatch):
    from decision_kernel.runtime import hithink_dump_trial as transport
    payload=b'{"code":0,"data":{"value":0.12345678901234567890}}'
    calls=[]
    class Response:
        status_code=200
        headers={'Content-Length':str(len(payload))}
        def __enter__(self):return self
        def __exit__(self,*a):return False
        def iter_content(self,chunk_size):yield payload
    class Session:
        def __enter__(self):return self
        def __exit__(self,*a):return False
        def get(self,url,**kwargs):calls.append((url,kwargs));return Response()
    monkeypatch.setattr(transport,'_session',Session)
    value=own.request_json(own.SNAPSHOT,{'thscodes':'002714.SZ'},api_key='dummy-secret')
    assert value['data']['value']=='0.12345678901234567890'
    url,args=calls[0]
    assert url=='https://fuyao.aicubes.cn'+own.SNAPSHOT
    assert args['allow_redirects'] is False and args['stream'] is True
    assert args['headers']['X-api-key']=='dummy-secret'
    assert args['headers']['Accept-Encoding']=='identity'
    actual_session=transport._session
    assert actual_session is Session


@pytest.mark.parametrize('raw',[b'{"code":0,"code":1}',b'{"code":0,"data":NaN}'])
def test_transport_duplicate_or_nonfinite_json_is_rejected(monkeypatch,raw):
    from decision_kernel.runtime import hithink_dump_trial as transport
    class Response:
        status_code=200;headers={}
        def __enter__(self):return self
        def __exit__(self,*a):return False
        def iter_content(self,chunk_size):yield raw
    class Session:
        def __enter__(self):return self
        def __exit__(self,*a):return False
        def get(self,*a,**kw):return Response()
    monkeypatch.setattr(transport,'_session',Session)
    with pytest.raises(ValueError):own.request_json(own.SNAPSHOT,{'thscodes':'002714.SZ'},api_key='dummy-secret')


def test_manual_capture_entry_uses_only_existing_hithink_credential_and_no_provider_switch():
    source=Path('.github/scripts/capture-stock-reading.py').read_text()
    assert 'hithink_stock_reading.request_json(api_key=key,path=p,params=q)' in source
    assert "os.environ.get('HITHINK_FINANCE_API_KEY','')" in source
    assert 'TUSHARE' not in source and 'tushare' not in source
