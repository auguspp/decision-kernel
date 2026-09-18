"""Synthetic source-bound supplement execution, never a live data claim."""
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import concept_detail_capture as capture
from decision_kernel.runtime import concept_detail_supplement as detail
from decision_kernel.runtime import concept_radar_capture as original
from tests.test_concept_radar import Fixture, AT, DAY, SHA, WF, raw, no_network

WF2 = {**WF, 'GITHUB_WORKFLOW':capture.WORKFLOW, 'GITHUB_RUN_ID':'234567'}
START = AT + timedelta(hours=1)


def base(tmp_path, count=10, *, provenance='SYNTHETIC_TEST_ONLY', change_fixture=None):
    f = Fixture(count); t = AT
    if change_fixture: change_fixture(f)
    def now():
        nonlocal t
        t += timedelta(seconds=1)
        return t
    root = tmp_path/'original'
    receipt = original.capture(root, market_session=DAY, workflow=WF, expected_code=SHA,
        transport=lambda p,q:raw(f.body(p,q)), now=now, pause=lambda _:None,
        provenance=provenance, credential='DUMMY-MARKET-KEY' if provenance=='LIVE_HITHINK' else '')
    verification = original.verify(root)
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in root.iterdir(): z.writestr('payload/'+path.name,path.read_bytes())
        z.writestr('verification.json',raw(verification))
        z.writestr('implementation-source.tar',b'INERT_NOT_EXECUTED')
    payload = b.getvalue()
    run = {'id':123456,'head_sha':SHA,'path':capture.SOURCE_WORKFLOW,'head_branch':'main',
        'event':'workflow_dispatch','run_attempt':1,'status':'completed','conclusion':'success',
        'repository':{'full_name':capture.model.REPOSITORY},'head_repository':{'full_name':capture.model.REPOSITORY},
        'created_at':AT.isoformat(),'updated_at':(AT+timedelta(minutes=2)).isoformat()}
    artifact = {'id':123,'name':'concept-radar-123456-1','size_in_bytes':len(payload),'expired':False,
        'digest':'sha256:'+capture.model.sha256(payload),
        'created_at':(AT+timedelta(minutes=1)).isoformat(),
        'expires_at':(AT+timedelta(days=30)).isoformat(),'workflow_run':{'id':run['id'],'head_sha':SHA}}
    meta = {'run':run,'artifact':artifact,'prepared_at':(START-timedelta(minutes=1)).isoformat()}
    inputs=tmp_path/'input';inputs.mkdir()
    (inputs/'base.zip').write_bytes(payload);(inputs/'source.json').write_bytes(raw(meta))
    return inputs, f, meta


def execute(tmp_path, *, mutation=None, offset=0, start=START, transport_error=None):
    inputs,f,meta=base(tmp_path)
    if mutation:f.change=mutation
    f.called=[];t=start
    def now():
        nonlocal t
        t += timedelta(seconds=1)
        return t
    def transport(path,params):
        if transport_error: raise transport_error
        return raw(f.body(path,params))
    out=tmp_path/'supplement'
    receipt=capture.capture(out,inputs=inputs,offset=offset,workflow=WF2,expected_code=SHA,
        transport=transport,now=now,pause=lambda _:None,credential='DO-NOT-RETAIN-KEY')
    return out,receipt,f,inputs,meta


def test_actual_executor_calls_six_original_endpoints_and_replays(tmp_path):
    out,r,f,inputs,_=execute(tmp_path)
    assert r['status']==capture.COMPLETE
    p=json.loads((out/'observation.json').read_bytes())['projection']
    assert len(f.called)==6 and all(path in {detail.source.probe.HISTORY,detail.source.probe.MEMBERS} for path,_ in f.called)
    base_report=json.loads(zipfile.ZipFile(inputs/'base.zip').read('payload/observation.json'))
    selected=detail.plan(base_report,offset=0)['plan']['selected_codes']
    assert [d['thscode'] for d in p['details']]==selected
    assert set(selected).isdisjoint(base_report['projection']['detail_selected_codes'])
    assert p['coverage']['history_checked']==p['coverage']['memberships_checked']==3
    assert (out/'base.zip').read_bytes()==(inputs/'base.zip').read_bytes()
    assert capture.verify(out)['status']=='ORIGINAL_CONCEPT_DETAIL_REQUESTS_AND_RESULTS_REBUILT'
    assert p['coverage']['full_multiday_radar'] is False and p['model_calls']==0
    assert all(c['pre_quick_execution']=='NOT_EXECUTED' for c in p['companies'])


def test_plan_is_complete_and_matches_map_order_without_daily_ranking():
    report=Fixture(10).run();s=detail.plan(report,offset=0)['plan']
    wanted=sorted(set(r['thscode'] for r in report['projection']['concepts'])-set(report['projection']['detail_selected_codes']))
    assert s['base_unexamined_codes']==wanted and s['selected_codes']==wanted[:3]
    seen=[]
    for offset in range(0,len(wanted),3):
        p=detail.plan(report,offset=offset)['plan'];seen+=p['selected_codes']
        assert set(p['outside_this_batch'])==set(wanted)-set(p['selected_codes'])
    assert seen==wanted and len(seen)==len(set(seen))
    before=deepcopy(detail.POLICY);s['policy']['order']='tampered';assert detail.POLICY==before


@pytest.mark.parametrize('offset',[-1,True,'0',1,2,9,100])
def test_offset_invalid_before_provider_call(tmp_path,offset):
    inputs,f,_=base(tmp_path);f.called=[]
    with pytest.raises(ValueError,match='DETAIL_OFFSET_REJECTED'):
        capture.capture(tmp_path/'out',inputs=inputs,offset=offset,workflow=WF2,expected_code=SHA,
            transport=f.request,now=lambda:START)
    assert not f.called


def test_last_small_batch_and_prior_offsets_not_assumed_executed(tmp_path):
    out,r,f,_,_=execute(tmp_path,offset=6)
    assert len(f.called)==2 and r['status']==capture.COMPLETE
    p=json.loads((out/'plan.json').read_bytes())['selection']['plan']
    assert len(p['outside_this_batch'])==6 and p['next_offset'] is None
    assert capture.verify(out)['coverage']['batch_attempted']==1


@pytest.mark.parametrize('rate',['0','-.01'])
def test_quiet_and_negative_selected_history_not_filtered(tmp_path,rate):
    def quiet(f):
        prior=f.rate
        f.rate=lambda c:detail.source.Decimal(rate) if c==f.codes[1] else prior(c)
    inputs,f,_=base(tmp_path,change_fixture=quiet)
    data=json.loads(zipfile.ZipFile(inputs/'base.zip').read('payload/observation.json'))
    selected=detail.plan(data,offset=0)['plan']['selected_codes']
    assert f.codes[1] in selected and f.codes[1] not in data['projection']['detail_selected_codes']
    f.called=[];t=START
    def now():
        nonlocal t
        t+=timedelta(seconds=1)
        return t
    out=tmp_path/'quiet-result'
    r=capture.capture(out,inputs=inputs,offset=0,workflow=WF2,expected_code=SHA,
        transport=lambda p,q:raw(f.body(p,q)),now=now,pause=lambda _:None)
    assert r['status']==capture.COMPLETE and len(f.called)==6
    result=json.loads((out/'observation.json').read_bytes())['projection']
    d=next(d for d in result['details'] if d['thscode']==f.codes[1])
    assert d['history_status']=='EXACT_WINDOW_CHECKED'
    assert (detail.source.Decimal(d['path']['horizons'][0]['index_return'])==0) == (rate=='0')
    assert capture.verify(out)['coverage']['history_checked']==3


@pytest.mark.parametrize('endpoint',[detail.source.probe.HISTORY,detail.source.probe.MEMBERS])
@pytest.mark.parametrize('code',[3001,3002,3004])
def test_detail_unavailable_is_retained_gap_not_no_trend(tmp_path,endpoint,code):
    out,r,f,_,_=execute(tmp_path,mutation=lambda p,q,v:{'code':code} if p==endpoint else v)
    assert r['status']==capture.PARTIAL and len(f.called)==6
    assert capture.verify(out)['coverage']['detail_gaps']==3


@pytest.mark.parametrize('mutation',['bars','identity','snapshot','date','volume'])
def test_bad_history_stays_unavailable_not_repaired(tmp_path,mutation):
    def change(path,params,v):
        if path==detail.source.probe.HISTORY:
            if mutation=='bars':v['data']['item'].pop()
            elif mutation=='identity':v['data']['thscode']='886999.TI'
            elif mutation=='snapshot':v['data']['item'][-1]['close_price']='999'
            elif mutation=='date':v['data']['item'][-1]['date_ms']+=1000
            else:v['data']['item'][-1]['volume']='1001'
        return v
    out,r,_,_,_=execute(tmp_path,mutation=change)
    assert r['status']==capture.PARTIAL
    assert capture.verify(out)['coverage']['history_checked']==0
    assert capture.verify(out)['coverage']['memberships_checked']==3


@pytest.mark.parametrize('at',[AT-timedelta(days=1),AT+timedelta(days=1),AT.replace(hour=15,minute=29)])
def test_wrong_day_or_before_base_has_zero_provider_calls(tmp_path,at):
    inputs,f,_=base(tmp_path);f.called=[]
    try:
        r=capture.capture(tmp_path/'out',inputs=inputs,offset=0,workflow=WF2,expected_code=SHA,
            transport=f.request,now=lambda:at)
    except ValueError:
        pass  # A future/reversed base is rejected before output creation.
    else:
        assert r['status']==capture.FAILED and r['reason_code']=='DETAIL_SAME_SESSION_REQUIRED'
        assert capture.verify(tmp_path/'out')['network_calls']==0
    assert not f.called


@pytest.mark.parametrize('code',[1001,1002,2001,429,9999])
def test_auth_rate_and_unknown_business_failures_stop_without_retry(tmp_path,code):
    out,r,f,_,_=execute(tmp_path,mutation=lambda *a:{'code':code})
    assert r['status']==capture.FAILED and len(f.called)==1
    assert capture.verify(out)['status']=='RETAINED_FAILED_DETAIL_REMOTE_CAUSE_NOT_REPROVEN'


def test_http_failure_retains_finite_status_without_message(tmp_path):
    exc=original.DumpTrialError('HTTP_REJECTED',http_status=429)
    out,r,_,_,_=execute(tmp_path,transport_error=exc)
    assert r['reason_code']=='HTTP_REJECTED' and r['requests'][0]['http_status']==429
    assert capture.verify(out)['network_calls']==0
    assert not list(out.glob('response-*'))
    assert all(b'DO-NOT-RETAIN-KEY' not in p.read_bytes() for p in out.iterdir())


def test_unsafe_response_not_saved(tmp_path):
    out,r,_,_,_=execute(tmp_path,mutation=lambda *a:{'code':0,'token':'DO-NOT-RETAIN-KEY'})
    assert r['status']==capture.FAILED and not list(out.glob('response-*'))
    assert capture.verify(out)['network_calls']==0


@pytest.mark.parametrize('name',['plan.json','observation.json','request-1.json','response-1.json'])
def test_rehashed_tampering_rejected_by_original_replay(tmp_path,name):
    out,r,_,_,_=execute(tmp_path)
    v=json.loads((out/name).read_bytes())
    if name=='plan.json':v['selection']['plan']['selected_codes']=['886999.TI']
    elif name=='observation.json':v['projection']['companies']=[];v['projection_hash']=canonical_hash(v['projection'])
    elif name=='request-1.json':v['params']['thscode']='886999.TI'
    else:v['data']['item'][-1]['volume']='1'
    (out/name).write_bytes(raw(v));r['files']=capture._inventory(out)
    r['capture_hash']=canonical_hash({k:v for k,v in r.items() if k!='capture_hash'});(out/'capture.json').write_bytes(raw(r))
    with pytest.raises(ValueError):capture.verify(out)


@pytest.mark.parametrize('mutation',['digest','expired','future','foreign','failed','rerun'])
def test_source_binding_rejected_before_new_provider_calls(tmp_path,mutation):
    inputs,f,meta=base(tmp_path);f.called=[]
    if mutation=='digest':meta['artifact']['digest']='sha256:'+'0'*64
    elif mutation=='expired':meta['artifact']['expires_at']=AT.isoformat()
    elif mutation=='future':meta['run']['updated_at']=(START+timedelta(days=1)).isoformat()
    elif mutation=='foreign':meta['run']['repository']['full_name']='other/repo'
    elif mutation=='failed':meta['run']['conclusion']='failure'
    else:meta['run']['run_attempt']=2
    (inputs/'source.json').write_bytes(raw(meta))
    with pytest.raises(ValueError):
        capture.capture(tmp_path/'out',inputs=inputs,offset=0,workflow=WF2,expected_code=SHA,transport=f.request,now=lambda:START)
    assert not f.called


def test_create_only_and_cli_replay_secret_rejected(tmp_path,monkeypatch):
    out,r,f,inputs,_=execute(tmp_path)
    with pytest.raises(ValueError,match='CREATE_ONLY'):
        capture.capture(out,inputs=inputs,offset=0,workflow=WF2,expected_code=SHA,transport=f.request,now=lambda:START)
    monkeypatch.setenv(original.HITHINK_API_KEY_ENV,'DUMMY')
    assert capture.main(['verify','--output',str(out)])==2


def test_prepare_uses_exact_latest_live_original_without_executing_archive_code(tmp_path):
    inputs,f,meta=base(tmp_path,provenance='LIVE_HITHINK')
    class API:
        calls=0
        def get(self,path):
            self.calls+=1
            if '/workflows/' in path:return {'total_count':1,'workflow_runs':[meta['run']]}
            if path.endswith('per_page=100'):return {'total_count':1,'artifacts':[meta['artifact']]}
            return deepcopy(meta['run'])
        def archive(self,a):self.calls+=1;return (inputs/'base.zip').read_bytes()
    api=API();out=tmp_path/'prepared'
    result=capture.prepare(api,source_run_id=123456,output=out,now=lambda:START)
    assert result['market_requests']==0 and result['github_api_calls']==4
    assert (out/'base.zip').read_bytes()==(inputs/'base.zip').read_bytes()
    meta['run']['id']=123457
    with pytest.raises(ValueError,match='NOT_LATEST'):
        capture.prepare(API(),source_run_id=123456,output=tmp_path/'no',now=lambda:START)


def test_manual_workflow_keeps_source_and_research_boundaries():
    text=(Path(__file__).resolve().parents[1]/'.github/workflows/radar-concept-detail.yml').read_text()
    assert 'workflow_dispatch:' in text and 'schedule:' not in text and 'workflow_run:' not in text
    assert 'contents: read' in text and 'actions: read' in text and 'contents: write' not in text
    assert 'persist-credentials: false' in text and 'github.run_attempt == 1' in text
    assert text.count('secrets.HITHINK_FINANCE_API_KEY')==1 and 'SUB2API' not in text
    assert 'concept_detail_capture prepare' in text and 'concept_detail_capture verify' in text
    assert 'stock-business-research' not in text and 'continue-on-error' not in text
    assert 'git archive' in text and 'tar -x' not in text and 'source-run-id "$SOURCE_RUN"' in text


@pytest.mark.parametrize('key,value',[('GITHUB_REF','refs/heads/other'),('GITHUB_RUN_ATTEMPT','2'),
    ('GITHUB_SHA','b'*40),('GITHUB_WORKFLOW','radar-concept-source'),('GITHUB_EVENT_NAME','push')])
def test_other_workflow_or_rerun_rejected_before_output(tmp_path,key,value):
    inputs,f,_=base(tmp_path);f.called=[]
    with pytest.raises(ValueError):
        capture.capture(tmp_path/'out',inputs=inputs,offset=0,workflow={**WF2,key:value},expected_code=SHA,
            transport=f.request,now=lambda:START)
    assert not f.called and not (tmp_path/'out').exists()


def test_selected_plan_tampering_cannot_change_requested_company(tmp_path):
    inputs,_,meta=base(tmp_path)
    files,report,_=capture.load_base((inputs/'base.zip').read_bytes(),meta,at=START)
    p=detail.plan(report,offset=0);p['plan']['selected_codes']=['886999.TI'];p['plan_hash']=canonical_hash(p['plan'])
    with pytest.raises(ValueError,match='PLAN_REBUILD'):
        detail.observe(lambda *a:pytest.fail('No source call'),base_files=files,report=report,selection=p,started_at=START)


def test_report_budget_failure_preserves_raw_without_success_claim(tmp_path,monkeypatch):
    original_bytes=capture._bytes
    def encode(value):
        result=original_bytes(value)
        if isinstance(value,dict) and value.get('projection',{}).get('version')==detail.VERSION:
            return result+b' '*(original.MAX_BYTES+1)
        return result
    monkeypatch.setattr(capture,'_bytes',encode)
    out,r,_,_,_=execute(tmp_path)
    assert r['status']==capture.FAILED and r['reason_code']=='DETAIL_REPORT_BUDGET_REJECTED'
    assert not (out/'observation.json').exists() and len(list(out.glob('response-*')))==6
    assert capture.verify(out)['network_calls']==0
