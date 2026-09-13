"""Synthetic source-only composition. No network, issuer facts or model calls."""
from copy import deepcopy
from types import SimpleNamespace
import json
import socket

import pytest

from decision_kernel.runtime import stock_source_preparation as prep
from decision_kernel.runtime import stock_research_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_source_recovery as recovery
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import current_state as read


@pytest.fixture(autouse=True)
def no_network_or_research(monkeypatch):
    def denied(*a, **k): raise AssertionError('network/model/work writes are forbidden')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(once, 'Retainer', denied)
    monkeypatch.setattr(once, 'research', denied)
    monkeypatch.setattr(once, 'model_call', denied)


def fixture(tmp_path):
    code, work, exposed = 'a'*40, 'b'*40, 'c'*40
    now = '2026-09-13T12:00:00+00:00'
    clock = lambda: now
    permission = {'id': 1, 'body': 'SYNTHETIC two source repairs only',
        'created_at': '2026-09-13T11:00:00Z',
        'issue_url': 'https://api.github.com/repos/'+once.REPO+'/issues/297'}
    request = {'schema_version':1,'enabled':True,'mode':prep.MODE,
        'permission':{'comment_id':1,'body_sha256':once.sha(permission['body'].encode()),
                      'created_at':permission['created_at']},
        'source_stock_run_id':42,'source_research_run_id':99,'items':[]}
    origin = {'run':{'id':42},'market_session':'2026-09-11'}
    selected = {'items':[], 'excluded':[{'thscode':'600967.SH'}]}
    rows, work_files = [], {}
    for c in ('600184.SH','300183.SZ','603353.SH','300711.SZ'):
        eid, prefix = intake.execution(c)
        item = {'thscode':c, 'security_id':intake.security(c),'company_name':'SYNTHETIC',
            'execution_id':eid,'prefix':prefix,'observation':{'thscode':c,'eligible_for_shadow_reading':True}}
        selected['items'].append(item)
        if c in ('600184.SH','300183.SZ'): continue
        previous_id, previous_prefix = recovery.execution(c)
        selection = {'thscode':c,'execution_id':previous_id,'question_kind':intake.QUESTION_KIND,
            'origin':origin,'observation':item['observation']}
        failure = {'schema_version':1,'execution_id':previous_id,'thscode':c,
            'question_kind':intake.QUESTION_KIND,'record_kind':'PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT',
            'formal_research_started':False,'research_execution':'NOT_EXECUTED','funnel_status':'NOT_REACHED',
            'phase':'SOURCE_PREPARATION','status':'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE',
            'error_code':'required page visual review unavailable',
            'finished_at':'2026-09-13T09:00:00Z',**read.AUTHORITY}
        entry = {'thscode':c}
        for name,value,file in (('selection',selection,'prepare.json'),('failure',failure,'failure.json')):
            path = previous_prefix+file
            work_files[path] = once.raw(value)
            entry[name] = once.source_ref(path,work,work_files[path],'SYNTHETIC_PREDECESSOR')
        request['items'].append(entry)
        rows.append({'thscode':c,'source_recovery':{'status':'PRE_EXECUTION_FAILURE',
            'execution_id':previous_id,'sources':{n:entry[n] for n in ('selection','failure')}}})
    payload = read.assemble(code_commit=code,checked_at='2026-09-13T10:00:00Z',
        check_started_at='2026-09-13T10:00:00Z',lanes={},capabilities=[],refresh_identity={},
        research={'handoffs':{'active':[]},'stock_business_work':{'status':'READ_OK',
            'work_commit':work,'latest_execution_attempt':{'id':99,
                'path':'.github/workflows/stock-business-research.yml','event':'workflow_dispatch',
                'run_attempt':1,'status':'completed','conclusion':'failure'},'items':rows}})
    request['exposed_reading'] = once.source_ref('current-state.json',exposed,once.raw(payload),'SYNTHETIC_EXPOSURE')
    files = {work:work_files,exposed:{'current-state.json':once.raw(payload)},code:{prep.REQUEST:once.raw(request)}}
    meta = {ref:{'sha':ref,'committer':{'date':'2026-09-13T10:00:00Z'}} for ref in files}
    class API:
        calls = 0
        def __init__(self):
            self.permission=permission;self.files=files;self.meta=meta;self.live=deepcopy(work_files);self.code=code
        def _call(self,method,path):
            assert method=='GET'
            self.calls+=1
            if path=='git/ref/heads/main': value={'object':{'type':'commit','sha':self.code}}
            elif path=='git/ref/heads/'+intake.WORK_REF: value={'object':{'type':'commit','sha':work}}
            elif path=='issues/comments/1': value=deepcopy(self.permission)
            else: raise AssertionError(path)
            return SimpleNamespace(json=lambda:value)
        def get(self,path):
            self.calls+=1
            if path.startswith('git/commits/'):return self.meta[path.removeprefix('git/commits/')]
            if path.startswith('git/trees/'):
                return {'truncated':False,'tree':[{'path':p,'type':'blob','mode':'100644',
                    'sha':once.blob(b),'size':len(b)} for p,b in self.live.items()]}
            raise AssertionError(path)
        def file(self,path,ref): self.calls+=1;return self.files[ref][path]
    api = API()
    output = tmp_path/'run';output.mkdir()
    args = dict(api=api,code=code,selected=selected,origin=origin,reading_commit=exposed,output=output,clock=clock)
    return args, request, api


def capture_calls(calls, status='SOURCES_CHECKED_NOT_EXECUTION_ADMITTED'):
    def capture(**kw):
        assert kw['preparation_only'] is True
        calls.append(kw['ticker'])
        return {'kind':'SOURCE_PREPARATION_ONLY','ticker':kw['ticker'], 'code_commit':kw['code_commit'],
            'status':status,'research_execution_allowed':False,
            'inventory_checked':True,'all_planned_bodies_inspected':True,
            'selected_ids':['SYNTHETIC'],'checked_body_ids':['SYNTHETIC'],
            'unattempted_ids':[],'missing_page_reviews':[],
            'complete_context':{'within_current_limit':True,'within_source_reference_limit':True},**read.AUTHORITY}
    return capture


def test_only_two_sources_no_model_no_work_mutation(tmp_path):
    args,request,api=fixture(tmp_path)
    before=deepcopy(api.files);calls=[]
    result=prep.prepare(**args,capture=capture_calls(calls))
    assert calls==['603353','300711']
    assert result['status']=='SOURCES_CHECKED_NOT_EXECUTION_ADMITTED'
    assert result['model_calls']==result['research_work_writes']==0
    assert not result['research_execution_allowed'] and not result['formal_research_started']
    assert not result['unattempted_issuers'] and before==api.files
    assert json.loads((args['output']/'source-preparation-batch.json').read_bytes())==result
    assert not list(args['output'].rglob('launch.json'))


@pytest.mark.parametrize('case',['foreign_target','duplicate_target','wrong_origin','main_moved',
    'permission_changed','exposure_after_permission','failure_changed','selection_changed',
    'old_parent_path','exposed_run_differs','bool_schema'])
def test_boundaries_reject_before_capture(tmp_path,case):
    args,request,api=fixture(tmp_path)
    if case=='foreign_target': request['items'][0]['thscode']='600184.SH'
    elif case=='duplicate_target': request['items'].append(deepcopy(request['items'][0]))
    elif case=='wrong_origin': args['origin']={'run':{'id':999}}
    elif case=='main_moved': api.code='e'*40
    elif case=='permission_changed': api.permission['body']='revoked'
    elif case=='exposure_after_permission': api.meta[request['exposed_reading']['ref']]['committer']['date']='2026-09-13T11:00:01Z'
    elif case=='failure_changed': api.live[request['items'][0]['failure']['path']]=b'{}'
    elif case=='selection_changed': api.live[request['items'][0]['selection']['path']]=b'{}'
    elif case=='old_parent_path': request['items'][0]['failure']['path']=request['items'][0]['failure']['path'].replace('source-recovery-v1/','')
    elif case=='exposed_run_differs': request['source_research_run_id']=101
    else: request['schema_version']=True
    api.files[args['code']][prep.REQUEST]=once.raw(request)
    calls=[]
    with pytest.raises((ValueError,KeyError)):
        prep.prepare(**args,capture=capture_calls(calls))
    assert not calls


@pytest.mark.parametrize('name',prep.EXECUTION_FILES)
def test_any_recovered_execution_history_rejects_preparation(tmp_path,name):
    args,request,api=fixture(tmp_path)
    _,prefix=recovery.execution('603353.SH');api.live[prefix+name]=b'{}'
    with pytest.raises(once.TrialError,match='executed recovery'):
        prep.prepare(**args,capture=capture_calls([]))


def test_revocation_between_issuers_keeps_unattempted_scope(tmp_path):
    args,request,api=fixture(tmp_path);calls=[]
    ordinary=capture_calls(calls)
    def capture(**kw):
        value=ordinary(**kw);api.permission['body']='revoked';return value
    with pytest.raises(once.TrialError): prep.prepare(**args,capture=capture)
    saved=json.loads((args['output']/'source-preparation-batch.json').read_bytes())
    assert calls==['603353'] and saved['unattempted_issuers']==['300711.SZ']
    assert saved['status']=='SOURCE_PREPARATION_INCOMPLETE' and saved['model_calls']==0


def test_source_error_is_not_wait_or_quiet_and_other_issuer_can_be_inspected(tmp_path):
    args,_,_=fixture(tmp_path);calls=[]
    def capture(**kw):
        calls.append(kw['ticker'])
        if kw['ticker']=='603353':raise RuntimeError('SECRET_DO_NOT_RETAIN')
        return capture_calls([],status='PREPARATION_INCOMPLETE')(**kw)
    result=prep.prepare(**args,capture=capture)
    assert result['status']=='SOURCE_PREPARATION_INCOMPLETE' and calls==['603353','300711']
    raw=(args['output']/'source-preparation-batch.json').read_text()
    assert 'SECRET_DO_NOT_RETAIN' not in raw and 'WAIT_FOR_TRIGGER' not in raw


def test_same_local_receipt_is_create_only(tmp_path):
    args,_,_=fixture(tmp_path);calls=[]
    prep.prepare(**args,capture=capture_calls(calls))
    before=(args['output']/'source-preparation-batch.json').read_bytes()
    with pytest.raises(once.TrialError):prep.prepare(**args,capture=capture_calls(calls))
    assert len(calls)==2 and (args['output']/'source-preparation-batch.json').read_bytes()==before


@pytest.mark.parametrize('values',[(True,True),(1,False),(False,1),('true',False)])
def test_host_flags_reject_before_output(tmp_path,values):
    with pytest.raises(once.TrialError):
        host.consume(api=None,code='a'*40,source_run_id=42,output=tmp_path/'none',
                     prepare_sources=values[0],recover_sources=values[1])
    assert not (tmp_path/'none').exists()


@pytest.mark.parametrize('event,secret',[('schedule',''),('workflow_run',''),('workflow_dispatch','SYNTHETIC_SECRET')])
def test_cli_source_mode_requires_dispatch_and_no_model_secret(tmp_path,monkeypatch,event,secret):
    for k,v in {'GITHUB_REPOSITORY':once.REPO,'GITHUB_REF':'refs/heads/main',
        'GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'a'*40,'GITHUB_EVENT_NAME':event,'SUB2API_API_KEY':secret}.items():
        monkeypatch.setenv(k,v)
    with pytest.raises(once.TrialError):
        host.main(['--source-run-id','42','--code-commit','a'*40,'--output',str(tmp_path/'none'),'--prepare-sources'])
    assert not (tmp_path/'none').exists()


def test_both_cli_modes_are_mutually_exclusive(tmp_path):
    with pytest.raises(SystemExit):
        host.main(['--source-run-id','42','--code-commit','a'*40,'--output',str(tmp_path/'none'),
                   '--prepare-sources','--recover-sources'])


def test_malformed_capture_success_cannot_mark_batch_complete(tmp_path):
    args,_,_=fixture(tmp_path)
    def capture(**kw):
        result=capture_calls([])(**kw);result['complete_context']=None;return result
    result=prep.prepare(**args,capture=capture)
    assert result['status']=='SOURCE_PREPARATION_INCOMPLETE'
    assert all(i['status']=='PREPARATION_INCOMPLETE' for i in result['items'])


def test_consume_uses_stock_validation_then_source_branch_not_research(tmp_path,monkeypatch):
    args,request,api=fixture(tmp_path)
    standard={'schema_version':1,'enabled':True,'mode':intake.QUESTION_KIND,'permission':request['permission']}
    api.files[args['code']][host.REQUEST]=once.raw(standard)
    source_run={'id':42};artifact={'id':43,'name':'stock-reading-42-1'}
    old_get=api.get;old_call=api._call;checked=[]
    def get(path):
        if path=='actions/runs/42':return source_run
        if path=='actions/runs/42/artifacts?per_page=100':return {'total_count':1,'artifacts':[artifact]}
        return old_get(path)
    def call(method,path):
        if path=='git/ref/heads/'+read.READ_REF:
            return SimpleNamespace(json=lambda:{'object':{'type':'commit','sha':args['reading_commit']}})
        return old_call(method,path)
    monkeypatch.setattr(api,'get',get);monkeypatch.setattr(api,'_call',call)
    api.archive=lambda _:b'SYNTHETIC original saved Stock archive'
    monkeypatch.setattr(read,'run_identity',lambda *a,**k:checked.append('run_identity'))
    monkeypatch.setattr(read,'select_artifact',lambda *a,**k:artifact)
    monkeypatch.setattr(read,'unpack_archive',lambda *a,**k:checked.append('unpack') or {})
    selected={**args['selected'],'projection_hash':'f'*64,'market_session':'2026-09-11'}
    monkeypatch.setattr(intake,'plan',lambda *a,**k:checked.append('original_stock_plan') or selected)
    called=[]
    monkeypatch.setattr(prep,'prepare',lambda **kw:called.append(kw) or {'status':'SYNTHETIC_PREPARATION'})
    def forbidden(**kw):raise AssertionError('research branch called')
    result=host.consume(api=api,code=args['code'],source_run_id=42,output=tmp_path/'consume',
                        prepare_sources=True,run_one=forbidden)
    assert result['status']=='SYNTHETIC_PREPARATION' and len(called)==1
    assert checked==['run_identity','unpack','original_stock_plan']
    assert called[0]['selected']==selected


def test_cli_source_failure_is_distinct_and_create_only(tmp_path,monkeypatch):
    for k,v in {'GITHUB_REPOSITORY':once.REPO,'GITHUB_REF':'refs/heads/main',
        'GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'a'*40,'GITHUB_EVENT_NAME':'workflow_dispatch',
        'SUB2API_API_KEY':'','GH_TOKEN':'SYNTHETIC'}.items():monkeypatch.setenv(k,v)
    output=tmp_path/'out';output.mkdir()
    def failed(**kw):raise RuntimeError('SECRET_NOT_RETAINED')
    monkeypatch.setattr(host,'consume',failed)
    monkeypatch.setattr(host,'GitHubAPI',lambda *a,**k:None)
    argv=['--source-run-id','42','--code-commit','a'*40,'--output',str(output),'--prepare-sources']
    assert host.main(argv)==2
    path=output/'source-preparation-failure.json';prior=path.read_bytes()
    assert b'SECRET_NOT_RETAINED' not in prior and not (output/'batch-failure.json').exists()
    assert host.main(argv)==2 and path.read_bytes()==prior


def test_workflow_source_job_has_no_model_secret_or_contents_write():
    from pathlib import Path
    text=(Path(__file__).resolve().parents[1]/'.github/workflows/stock-business-research.yml').read_text()
    source=text.split('  prepare-stock-sources:',1)[1]
    original=text.split('  prepare-stock-sources:',1)[0]
    assert 'contents: read' in source and 'contents: write' not in source
    assert 'SUB2API' not in source and 'research-api' not in source
    assert '--prepare-sources' in source and 'persist-credentials: false' in source
    assert "github.event_name == 'workflow_dispatch' && inputs.prepare-sources" in source
    assert "!(github.event_name == 'workflow_dispatch' && inputs.prepare-sources)" in original
    assert 'cancel-in-progress: false' in text
