"""Synthetic Stock composition tests; real original admission/Pre/Quick/Retainer."""
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import stock_research_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import current_state as reading
from decision_kernel.runtime import current_state_delivery as delivery
from test_saved_research_once import fixture, pre, quick


def setup_host(tmp_path, monkeypatch, *, mode='quick', fail=None):
    stamp = datetime.now(timezone.utc).replace(microsecond=123456)
    def clock(): return stamp.isoformat()
    def sleep(seconds):
        nonlocal stamp
        stamp += timedelta(seconds=seconds)
    monkeypatch.setattr(once, 'now', clock)
    monkeypatch.setattr(once.time, 'sleep', sleep)
    code, old, r = 'a'*40, 'b'*40, 'c'*40
    packet, _, _ = fixture()
    packet_raw=once.raw(packet)
    spec=once.source_ref('old-input.json', old, packet_raw, 'IDENTITY_OBSERVATION')
    catalog={'schema_version':1, 'inputs':[{**once.identity.input_key(packet).as_dict(), 'input':spec}]}
    payload=reading.assemble(code_commit=code, checked_at=clock(), check_started_at=clock(),
        lanes={}, research={'handoffs':{'active':[]}}, capabilities=[], refresh_identity={})
    comment={'id':1, 'body':'Synthetic scoped Human permission. Not real authority.',
        'created_at':(stamp-timedelta(hours=1)).isoformat(),
        'issue_url':'https://api.github.com/repos/'+once.REPO+'/issues/297'}
    request={'schema_version':1, 'enabled':True, 'mode':intake.QUESTION_KIND,
        'permission':{'comment_id':1, 'body_sha256':once.sha(comment['body'].encode()), 'created_at':comment['created_at']}}
    files={code:{once.identity.CATALOG_PATH:once.raw(catalog), host.REQUEST:once.raw(request)},
        old:{'old-input.json':packet_raw}, r:{'current-state.json':once.raw(payload)}}
    commits={ref:{'sha':ref, 'committer':{'date':(stamp-timedelta(minutes=30)).isoformat()}} for ref in files}
    heads={'main':code, reading.READ_REF:r}
    calls, captures, mutations=[],[],[]
    class API:
        def __init__(self): self.calls=0;self.comment=comment;self.files=files;self.heads=heads
        def get(self,path):
            self.calls+=1
            if path.startswith('actions/workflows/stock-business-research.yml/runs'):
                return {'total_count':0,'workflow_runs':[]}
            if path.startswith('git/ref/heads/'):
                name=path.removeprefix('git/ref/heads/')
                if name not in heads: raise delivery.GitHubReadError('GitHub HTTP 404')
                return {'object':{'sha':heads[name], 'type':'commit'}}
            if path.startswith('git/commits/'): return commits[path.removeprefix('git/commits/')]
            if path.startswith('issues/comments/'): return deepcopy(self.comment)
            if path.startswith('git/trees/'):
                ref=path.split('/')[2].split('?')[0]
                return {'truncated':False, 'tree':[{'path':p,'sha':once.blob(v), 'size':len(v),
                    'mode':'100644', 'type':'blob'} for p,v in files[ref].items()]}
            raise AssertionError(path)
        def _call(self,method,path):
            assert method=='GET'; value=self.get(path);return SimpleNamespace(json=lambda:value)
        def file(self,path,ref):
            self.calls+=1
            try: return files[ref][path]
            except KeyError: raise delivery.GitHubReadError('GitHub HTTP 404') from None
    api=API()
    def native(self,method,endpoint,body):
        mutations.append((method,endpoint,body))
        if endpoint=='git/refs':
            name=body['ref'].removeprefix('refs/heads/');heads[name]=body['sha'];return {'object':{'sha':body['sha']}}
        assert method=='PUT' and endpoint.startswith('contents/') and 'sha' not in body
        assert body['branch']==intake.WORK_REF
        path=endpoint.removeprefix('contents/');before=heads[intake.WORK_REF]
        if path in files[before]:
            self.uncertain=True;raise ValueError('existing file')
        new=f'{len(mutations):040x}';files[new]={**files[before], path:base64.b64decode(body['content'])};heads[intake.WORK_REF]=new
        commits[new]={'sha':new,'committer':{'date':stamp.replace(microsecond=0).isoformat()}}
        return {'commit':{'sha':new},'content':{'sha':once.blob(files[new][path])}}
    monkeypatch.setattr(once.Retainer,'native',native)
    eid,prefix=intake.execution('600184.SH')
    item={'thscode':'600184.SH','company_name':'Synthetic','security_id':'SSE:600184',
          'execution_id':eid,'prefix':prefix,'observation':{'thscode':'600184.SH','eligible_for_shadow_reading':True}}
    def capture(**kw):
        captures.append(kw['ticker'])
        if fail=='source': raise once.TrialError('synthetic required source unavailable')
        context={'stock_observation':kw['observation'], 'issuer_inventory':{'report_id':'synthetic-report'},
                 'issuer_documents':[{'pages':[{'page_number':1,'text':'Synthetic public business body, not an issuer fact.'}]}]}
        reads=[{'id':'body1','identity':kw['ticker']+':synthetic-report', 'locator':'https://static.cninfo.com.cn/synthetic.pdf',
            'authority':'PRIMARY','kind':'BODY','succeeded':True,'checked_at':clock(),'body_sha256':'f'*64,'tool_reference':'SYNTHETIC'}]
        return context,reads,{'started_at':clock(),'finished_at':clock(),'inventory_finished_at':clock()}
    def call(stage,prompt,model,out,usage):
        calls.append(stage)
        if fail==stage: raise RuntimeError('SECRET_EXCEPTION_DO_NOT_ECHO')
        if fail=='revoke_after_pre': api.comment['body']='revoked'
        return pre(prompt,'CONTINUE_TO_QUICK' if mode=='quick' else mode) if stage=='pre' else quick(prompt)
    args={'api':api,'code':code,'request':request,'item':item,'origin':{'market_session':'2026-09-11','run_id':5},
          'reading_commit':r,'output':tmp_path/'run','capture':capture,'call':call,'clock':clock}
    return args,api,calls,captures,mutations


@pytest.mark.parametrize('mode,stages',[('WAIT_FOR_TRIGGER',['pre']),('STOP',['pre']),('quick',['pre','quick'])])
def test_original_admission_executor_and_retention(tmp_path,monkeypatch,mode,stages):
    args,api,calls,captures,writes=setup_host(tmp_path,monkeypatch,mode=mode)
    result=host.run_item(**args)
    assert result['status']=='VALIDATED_FUNNEL_CANDIDATE',result
    assert calls==stages and captures==['600184']
    assert result['investment_authority']=='NONE' and not result['registered_current_handoff']
    assert json.loads((args['output']/'admission.json').read_bytes())['research_execution_allowed']
    before=deepcopy(api.files[api.heads[intake.WORK_REF]])
    # A changed price, date or run does not give the same business question a second execution.
    args['output']=tmp_path/'repeat';args['origin']={'market_session':'2026-09-15','run_id':999}
    args['item']['observation']['price']=100000
    repeated=host.run_item(**args)
    assert repeated['status']=='EXISTING_BASELINE_REUSED_NO_EXECUTION'
    assert calls==stages and captures==['600184'] and before==api.files[api.heads[intake.WORK_REF]]


@pytest.mark.parametrize('failure', ['source','pre','quick','revoke_after_pre'])
def test_source_model_and_permission_failures_are_not_wait_or_retried(tmp_path,monkeypatch,failure):
    args,api,calls,captures,writes=setup_host(tmp_path,monkeypatch,fail=failure)
    result=host.run_item(**args)
    expected='SOURCE_OR_INPUT_PREPARATION_INCOMPLETE' if failure=='source' else 'VALIDATED_EXECUTION_GAP'
    assert result['status']==expected,result
    assert not (args['output']/'funnel.json').exists()
    assert calls==({'source':[],'pre':['pre'],'quick':['pre','quick'],'revoke_after_pre':['pre']}[failure])
    prior=list(calls);args['output']=tmp_path/'repeat'
    repeat=host.run_item(**args)
    assert repeat['status']==('SOURCE_OR_INPUT_PREPARATION_INCOMPLETE' if failure=='revoke_after_pre' else 'EXISTING_BASELINE_REUSED_NO_EXECUTION')
    assert calls==prior and len(captures)==1
    assert all('SECRET_EXCEPTION' not in v.decode() for v in api.files[api.heads[intake.WORK_REF]].values())


@pytest.mark.parametrize('name',sorted(once.OUTPUT_NAMES))
def test_any_retained_history_blocks_new_preparation(tmp_path,monkeypatch,name):
    args,api,calls,captures,writes=setup_host(tmp_path,monkeypatch)
    api.heads[intake.WORK_REF]=args['code']
    api.files[args['code']][args['item']['prefix']+name]=b'{}'
    result=host.run_item(**args)
    assert result['status']=='EXISTING_BASELINE_REUSED_NO_EXECUTION'
    assert not calls and not captures and not writes


def test_permission_change_before_start_does_not_capture_or_create(tmp_path,monkeypatch):
    args,api,calls,captures,writes=setup_host(tmp_path,monkeypatch)
    api.comment['body']='Changed'
    result=host.run_item(**args)
    assert result['status']=='SOURCE_OR_INPUT_PREPARATION_INCOMPLETE' and not writes and not captures and not calls
