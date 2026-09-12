"""Original finite FIFO/intake/preparation/executor integration, fake transport."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import base64
import pytest
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import incremental_disclosure as work
from decision_kernel.runtime import incremental_disclosure_intake as intake
from decision_kernel.runtime import saved_disclosure_host as host
from decision_kernel.runtime import saved_disclosure_preparation as prep
from decision_kernel.runtime import saved_research_once as once
from test_incremental_disclosure import scan
from test_saved_disclosure_preparation import API, CODE, READING, WORK, Clock, packet_pdf, capture_files, archive
from test_saved_research_once import pre


class HostAPI(API):
    def __init__(self, samples, clock):
        super().__init__(samples[0][0], clock)
        self.snapshots[WORK]={'README.md': b'data only'}
        self.scan_raw,self.scan_artifact,self.run=scan([p for p,_ in samples])
        rows,objects=[],{}
        for packet,pdf in samples:
            f=capture_files(packet,pdf)
            row=read.json.loads(f[prep.BODY_ROOT+'manifest.jsonl'])
            row['sequence']=len(rows)+1; rows.append(row)
            objects[prep.BODY_ROOT+row['path']]=pdf
        manifest=b''.join(once.raw(r).replace(b'\n',b'')+b'\n' for r in rows)
        summary={'schema_version':1,'status':'PACKET_PREPARATION_COMPLETED',
                 'manifest_sha256':read.sha256(manifest),'returned_pdf_reads':len(rows),
                 'unique_pdf_objects':len(objects),'completed_at':'2026-09-09T13:00:02Z',
                 'investment_authority':'NONE'}
        self.body_raw,self.body_artifact=archive({**objects,prep.BODY_ROOT+'manifest.jsonl':manifest,
              prep.BODY_ROOT+'capture-summary.json':once.raw(summary)},self.run)
        self.calls=0; self.memo=set()
    def counted(self,key):
        if key not in self.memo:
            self.calls+=1;self.memo.add(key)
            assert self.calls<=delivery.MAX_API_CALLS,'original API ceiling'
    def _call(self,method,endpoint):
        self.calls+=1
        if endpoint=='git/ref/heads/'+read.READ_REF:
            return SimpleNamespace(json=lambda:{'object':{'type':'commit','sha':READING}})
        return super()._call(method,endpoint)
    def get(self,endpoint):
        self.counted(('get',endpoint))
        if endpoint=='actions/runs/10':return deepcopy(self.run)
        if endpoint=='actions/runs/10/artifacts?per_page=100':
            return {'total_count':2,'artifacts':[self.scan_artifact,self.body_artifact]}
        return super().get(endpoint)
    def file(self,path,ref):
        self.counted(('file',path,ref))
        try:return super().file(path,ref)
        except KeyError:raise delivery.GitHubReadError('GitHub HTTP 404')
    def archive(self,artifact):
        self.calls+=1
        return self.scan_raw if artifact['id']==self.scan_artifact['id'] else self.body_raw


def setup_host(tmp_path,monkeypatch,samples=None):
    samples=samples or [packet_pdf(code='600036'),packet_pdf(code='603986')]
    clock=Clock();api=HostAPI(samples,clock);calls=[]
    monkeypatch.setattr(once,'now',clock)
    monkeypatch.setattr(once.Retainer,'native',lambda self,*a:api.native(*a))
    def model(stage,prompt,*_):
        calls.append(stage);return pre(prompt)
    monkeypatch.setattr(once,'model_call',model)
    def reserve(**kwargs):
        return intake.intake(**kwargs,create=lambda path,raw:api.native('PUT','contents/'+path,
            {'branch':work.WORK_REF,'content':base64.b64encode(raw).decode()}))
    def prepare(**kwargs):return prep.prepare_reserved(**kwargs,wait=clock.wait)
    args=dict(api=api,source_run_id=10,code_commit=CODE,output=tmp_path/'host',clock=clock,
              reserve=reserve,prepare=prepare)
    return args,api,calls


def test_multiple_new_questions_same_scan_no_daily_quota_and_repeat_is_zero(tmp_path,monkeypatch):
    args,api,calls=setup_host(tmp_path,monkeypatch)
    result=host.consume(**args)
    assert result['status']=='NO_UNRESERVED_PACKET_IN_SAVED_SCAN',result
    assert len(result['items'])==2 and calls==['pre','pre']
    assert result['daily_provider_quota'] is None
    assert all(row['research_status']=='VALIDATED_FUNNEL_RESULT' for row in result['items'])
    before=deepcopy(api.snapshots); count=len(calls)
    result=host.consume(**dict(args,output=tmp_path/'repeat'))
    assert result['items']==[] and calls==['pre','pre'] and api.snapshots==before
    assert not result['automatic_retry']


def test_known_unreadable_first_packet_stays_failed_then_original_fifo_advances(tmp_path,monkeypatch):
    args,api,calls=setup_host(tmp_path,monkeypatch,[packet_pdf('Bad\x01text','300750'),packet_pdf(code='600036')])
    result=host.consume(**args)
    assert result['status']=='NO_UNRESERVED_PACKET_IN_SAVED_SCAN',result
    assert len(result['items'])==2 and calls==['pre']
    assert result['items'][0]['research_status']=='NOT_EXECUTED'
    assert result['items'][0]['error_code']=='required text contains encoding damage'
    assert result['items'][1]['research_status']=='VALIDATED_FUNNEL_RESULT'
    assert any(p.endswith('failure.json') for p in api.writes)


@pytest.mark.parametrize('failure',['model','unknown-preparation','uncertain-retention','reservation'])
def test_shared_or_uncertain_failure_stops_without_choosing_another(tmp_path,monkeypatch,failure):
    args,api,calls=setup_host(tmp_path,monkeypatch)
    if failure=='model':
        def failed(*_):calls.append('pre');raise RuntimeError('secret not echoed')
        monkeypatch.setattr(once,'model_call',failed)
    elif failure=='reservation':
        def failed(**_):raise RuntimeError('create response lost')
        args['reserve']=failed
    else:
        args['prepare']=lambda **_:{'status':'NOT_EXECUTED','error_code':None,
                                    'mutation_uncertain':failure=='uncertain-retention'}
    result=host.consume(**args)
    assert result['status']=='BATCH_INCOMPLETE',result
    assert len(calls)<=1 and len(result['items'])<=1
    assert 'secret not echoed' not in once.raw(result).decode()


@pytest.mark.parametrize('damage',['main','wrong-run','source-failure','artifact-count','body-hash','truncated-tree'])
def test_shared_inputs_fail_before_any_reservation(tmp_path,monkeypatch,damage):
    args,api,calls=setup_host(tmp_path,monkeypatch)
    if damage=='main':api.main='d'*40
    elif damage=='wrong-run':api.run['id']=11
    elif damage=='source-failure':api.run['conclusion']='failure'
    elif damage=='body-hash':api.body_artifact['digest']='sha256:'+'f'*64
    else:
        get=api.get
        def changed(endpoint):
            result=get(endpoint)
            if damage=='artifact-count' and 'artifacts?' in endpoint:result['total_count']=3
            if damage=='truncated-tree' and endpoint.startswith('git/trees/'):result['truncated']=True
            return result
        monkeypatch.setattr(api,'get',changed)
    result=host.consume(**args)
    assert result['status']=='BATCH_INCOMPLETE' and api.writes==[] and calls==[]


def test_production_entry_bounds_each_question_with_original_alarm_pattern(tmp_path,monkeypatch):
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1');monkeypatch.setenv('GITHUB_REF','refs/heads/main')
    monkeypatch.setenv('GH_TOKEN','synthetic')
    alarms=[];monkeypatch.setattr(host.signal,'alarm',alarms.append)
    monkeypatch.setattr(host.signal,'signal',lambda *_:None)
    monkeypatch.setattr(host,'GitHubAPI',lambda _:None)
    monkeypatch.setattr(host,'execute_prepared',lambda **_:{'status':'fake'})
    def consume(**kwargs):
        kwargs['execute']();kwargs['execute']()
        return {'status':'FINITE_SCAN_PASS_COMPLETED'}
    monkeypatch.setattr(host,'consume',consume)
    assert host.main(['--source-run-id','10','--code-commit',CODE,'--output',str(tmp_path/'out')])==0
    assert alarms==[900,0,900,0,0]


def test_workflow_reuses_native_events_and_trusted_code_no_new_cron():
    root=Path(__file__).parents[1]
    wf=(root/'.github/workflows/saved-disclosure-research.yml').read_text()
    publish=(root/'.github/workflows/current-state-read-entry.yml').read_text()
    assert 'workflows: [decision-inbox]' in wf and 'schedule:' not in wf and 'cron:' not in wf
    assert 'ref: ${{ github.sha }}' in wf and 'persist-credentials: false' in wf
    assert 'group: incremental-disclosure-work-v0' in wf and 'cancel-in-progress: false' in wf
    assert 'github.run_attempt == 1' in wf and 'SUB2API_API_KEY' in wf
    assert 'HITHINK' not in wf and 'head_sha }}' not in wf
    assert "name == 'saved-disclosure-research'" in publish
    assert "github.event.workflow_run.event == 'workflow_run'" in publish
    assert 'SUB2API_API_KEY' not in publish


def test_independent_work_clients_keep_original_per_attempt_bound_not_global_daily_cap(tmp_path,monkeypatch):
    samples=[packet_pdf(code=c) for c in ('300750','600036','600519','601088','603986','002050')]
    args,backend,calls=setup_host(tmp_path,monkeypatch,samples)
    # Fake backend stores immutable shared Git data. Fresh bounded transport views
    # imitate production GitHubAPI per work unit, not a reset of an active attempt.
    class View:
        def __init__(self):self.calls=0;self.memo=set()
        def count(self,key=None):
            if key is None or key not in self.memo:
                self.calls+=1
                if key:self.memo.add(key)
                assert self.calls<=delivery.MAX_API_CALLS
        def _call(self,method,endpoint):
            self.count()
            if endpoint=='git/ref/heads/'+read.READ_REF:
                return SimpleNamespace(json=lambda:{'object':{'type':'commit','sha':READING}})
            return API._call(backend,method,endpoint)
        def get(self,endpoint):
            self.count(('get',endpoint))
            if endpoint=='actions/runs/10':return deepcopy(backend.run)
            if endpoint=='actions/runs/10/artifacts?per_page=100':
                return {'total_count':2,'artifacts':[backend.scan_artifact,backend.body_artifact]}
            return API.get(backend,endpoint)
        def file(self,path,ref):
            self.count(('file',path,ref))
            try:return API.file(backend,path,ref)
            except KeyError:raise delivery.GitHubReadError('GitHub HTTP 404')
        def archive(self,artifact):
            self.count()
            return backend.scan_raw if artifact['id']==backend.scan_artifact['id'] else backend.body_raw
    result=host.consume(**dict(args,new_question_api=View))
    assert result['status']=='NO_UNRESERVED_PACKET_IN_SAVED_SCAN',result
    assert len(calls)==6 and len(result['items'])==6
    assert len(result['github_client_calls'])==8  # source + six questions + final inventory
    assert all(n<=delivery.MAX_API_CALLS for n in result['github_client_calls'])
    assert sum(result['github_client_calls'])>delivery.MAX_API_CALLS
