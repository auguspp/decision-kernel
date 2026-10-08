"""Synthetic-only tests of fixed scope, first-error stop and source replay."""
from datetime import datetime, timezone, timedelta
import json
import pytest
from decision_kernel.runtime import yinquan_ftshare_56 as s

def env():
    return {'GITHUB_REPOSITORY': 'auguspp/decision-kernel', 'GITHUB_REF': 'refs/heads/main',
            'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1',
            'GITHUB_SHA': 'a'*40, 'EXPECTED_CODE': 'a'*40, 'GITHUB_RUN_ID': '1234'}

def fixture(spec, *, rate='1.25', count=1, code=200):
    y,m,d=map(int,spec['first'].split('-'))
    stamp=int(datetime(y,m,d,10,0,tzinfo=s.SHANGHAI).timestamp()*1000)
    bar={'open':'10','high':'12','low':'9','close':'11',
         'ts_millis_open':stamp,'ts_millis':stamp+5*60*60*1000,
         'volume':10000,'turnover':'110000','turnover_rate':rate}
    return json.dumps({'code':code,'data':[bar.copy() for _ in range(count)]}).encode()

def clock():
    current=[datetime(2026,10,8,2,tzinfo=timezone.utc)]
    def tick():
        current[0]+=timedelta(seconds=2)
        return current[0].isoformat()
    return tick

def test_finite_four_annual_windows():
    ps=s.plan()
    assert len(ps)==56 and len(s.SYMBOLS)==14
    assert [p['period'] for p in ps[:4]]==['2023','2024','2025','2026']
    assert all(p['params']['adjust_kind']=='none' for p in ps)
    assert all(p['params']['until_ts_millis']-p['params']['since_ts_millis']
               <366*86400000 for p in ps)
    for p in ps:
        s.validate_request(p['params'])
    with pytest.raises(ValueError,match='YINQUAN_REQUEST_SCOPE'):
        s.validate_request({**ps[0]['params'],'since_ts_millis':0})

def test_full_source_replay_and_modified_raw(tmp_path):
    plans=s.plan()
    calls=[]
    def fetch(route, params):
        assert route==s.ROUTE
        item=next(p for p in plans if p['params']==params)
        calls.append(item)
        return 200,fixture(item)
    root=tmp_path/'research'
    report=s.capture(root,env(),fetch=fetch,clock=clock())
    assert report['status']=='COMPLETE_CAPTURE_NOT_PIT' and len(calls)==56
    assert s.verify(root)['network_calls']==0
    assert len(list((root/'prices').glob('*.csv')))==14
    assert 'turnover_rate' in (root/'prices'/'000151.csv').read_text()
    assert '1.25' in (root/'prices'/'000151.csv').read_text()
    path=root/'raw'/'01-000001.SZ-2023.json'
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='RAW_INTEGRITY'):
        s.verify(root)

def test_first_source_denial_not_retried(tmp_path):
    seen=[]
    def deny(route, params):
        seen.append(params)
        return 403,b'{"code":403}'
    root=tmp_path/'deny'
    report=s.capture(root,env(),fetch=deny,clock=clock())
    assert report['status']=='STOPPED_AT_0' and len(seen)==1
    assert report['requests'][0]['http_status']==403
    assert s.verify(root)['source_calls_recorded']==1
    assert not list((root/'prices').iterdir())

def test_later_transport_error_no_retry(tmp_path):
    plans=s.plan()
    called=[]
    def fetch(route, params):
        item=next(p for p in plans if p['params']==params)
        called.append(item)
        if len(called)==3:
            raise TimeoutError('synthetic')
        return 200,fixture(item)
    root=tmp_path/'timeout'
    report=s.capture(root,env(),fetch=fetch,clock=clock())
    assert report['status']=='STOPPED_AT_2' and len(called)==3
    assert s.verify(root)['capture_status']=='STOPPED_AT_2'

def test_unknown_hsl_bad_bar_and_vendor_code():
    p=s.plan()[0]
    assert s.window_bars(fixture(p,rate=None),p)[p['first']]['turnover_rate'] is None
    with pytest.raises(ValueError,match='DUPLICATE_BAR'):
        s.window_bars(fixture(p,count=2),p)
    with pytest.raises(ValueError,match='PROVIDER_REJECTED'):
        s.window_bars(fixture(p,code=403),p)
    obj=json.loads(fixture(p))
    obj['data'][0]['low']='13'
    with pytest.raises(ValueError,match='PRICE_RANGE_INVALID'):
        s.window_bars(json.dumps(obj).encode(),p)

def test_identity_scope_and_time(tmp_path):
    with pytest.raises(ValueError,match='WORKFLOW_IDENTITY_INVALID'):
        s.capture(tmp_path/'bad',{**env(),'GITHUB_REF':'refs/heads/test'},fetch=lambda *_: None)
    p=s.plan()[0]
    obj=json.loads(fixture(p))
    obj['data'][0]['ts_millis']=p['params']['until_ts_millis']+1
    with pytest.raises(ValueError,match='BAR_TIME_OUT_OF_WINDOW'):
        s.window_bars(json.dumps(obj).encode(),p)
