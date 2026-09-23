"""Bounded eval driver uses actual installed SDK over mock HTTP; no live spend."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import socket

import pytest
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import single_quick_contract as single
from test_single_quick_execution import assessment
from test_single_quick_full_wire import full_case, sse
from test_saved_research_once import pre, quick

spec = importlib.util.spec_from_file_location('r4_2_eval',Path(__file__).parents[1]/'experiments/r4_2_sub2api.py')
eval = importlib.util.module_from_spec(spec);spec.loader.exec_module(eval)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args,**kwargs): raise AssertionError('Test cannot access a real network')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket,'create_connection',deny)
    monkeypatch.setattr(socket,'getaddrinfo',deny)


def prompt():
    p,d,ctx,_=full_case();return p,d,ctx,once.initial_prompt(p,d,ctx)


def test_s0_changes_only_one_policy_description_not_material_or_structure():
    *_,p=prompt()
    a=eval.parameters(p,single.QuickAssessment,'S0'); b=eval.parameters(p,single.QuickAssessment,'S1')
    assert a != b
    a['text']['format']['schema']['properties']['route']['description']=b['text']['format']['schema']['properties']['route']['description']
    assert a==b and a['model']==once.MODEL and 'reasoning' not in a


@pytest.mark.parametrize('route',['STOP','WAIT_FOR_TRIGGER','FULL_CANDIDATE','INVALID'])
def test_full_material_real_sdk_preview_send_and_raw_first_retention(tmp_path,monkeypatch,route):
    import openai
    import httpx2 as httpx
    *_,p=prompt();seen=[]
    text='{"route":' if route=='INVALID' else assessment(p,route).model_dump_json()
    def transport(req):
        seen.append(req.content);params=json.loads(req.content)
        assert str(req.url)==once.BASE_URL+'/responses'
        assert json.loads(params['input'][0]['content'])['public_context']==p['public_context']
        assert len(req.content)>512*1024 and params['tools']==[] and params['store'] is False
        assert params['max_output_tokens']==6000 and params['text']['format']['strict'] is True
        return httpx.Response(200,headers={'content-type':'text/event-stream'},content=sse(text))
    def client(**kw):
        kw.setdefault('transport',httpx.MockTransport(transport));return httpx.Client(**kw)
    monkeypatch.setattr(openai,'DefaultHttpxClient',client)
    monkeypatch.setenv('SUB2API_API_KEY','synthetic-not-a-real-credential')
    value,record=eval.send_one(p,single.QuickAssessment,'S1',tmp_path)
    assert len(seen)==record['physical_sends']==1
    assert record['pre_send']['request_sha256']==json.loads((tmp_path/'sdk-preview.json').read_bytes())['request_sha256']
    assert (tmp_path/'model-output.txt').read_text()==text
    assert record['usage']['total_tokens']==12
    assert (value is None)==(route=='INVALID')
    assert not record.get('stop_batch',False)
    assert 'synthetic-not-a-real-credential' not in ''.join(f.read_text() for f in tmp_path.iterdir())


@pytest.mark.parametrize('change',['model','output_tokens','tool','store','system','reasoning'])
def test_provider_scope_change_rejected_before_preview_or_send(change):
    *_,p=prompt();params=eval.parameters(p,single.QuickAssessment,'S1')
    if change=='model':params['model']='other'
    elif change=='output_tokens':params['max_output_tokens']=9000
    elif change=='tool':params['tools']=[{'type':'web_search'}]
    elif change=='store':params['store']=True
    elif change=='system':params['instructions']='changed'
    else:params['reasoning']={'effort':'none'}
    with pytest.raises(ValueError,match='EVAL_PROVIDER_PARAMETERS'):eval.request_guard(p,params)


@pytest.mark.parametrize('damage',['repeat','destination','body'])
def test_existing_full_guard_rejects_changed_or_repeated_request(damage):
    import httpx2 as httpx
    *_,p=prompt();params=eval.parameters(p,single.QuickAssessment,'S1');record={}
    guard=eval.request_guard(p,params).hook(record)
    req=httpx.Request('POST',once.BASE_URL+'/responses',content=once.raw({**params,'stream':True}))
    if damage=='repeat':guard(req)
    elif damage=='destination':req=httpx.Request('POST','https://invalid.example/responses',content=req.content)
    else:req=httpx.Request('POST',once.BASE_URL+'/responses',content=b'{}')
    with pytest.raises(ValueError):guard(req)


@pytest.mark.parametrize('continuation',[True,False])
def test_original_pre_controls_only_its_quick_and_singles_have_no_pre(tmp_path,continuation):
    p,d,ctx,_=full_case();calls=[]
    def send(prompt,model,arm,out):
        calls.append((arm,deepcopy(prompt)))
        if model is once.PreResearchResult:return pre(prompt,'CONTINUE_TO_QUICK' if continuation else 'WAIT_FOR_TRIGGER'),{'physical_sends':1}
        if model is once.QuickResearchResult:
            assert prompt['pre_research_hash']==once.canonical_hash(pre(calls[0][1],'CONTINUE_TO_QUICK'))
            return quick(prompt),{'physical_sends':1}
        assert not {'pre_research','pre_research_hash'} & prompt.keys()
        return assessment(prompt),{'physical_sends':1}
    rows,stop=eval.run_arms(p,d,ctx,tmp_path,send=send)
    assert not stop and len(rows)==(4 if continuation else 3)
    assert [c[0] for c in calls]==(['O','O','S0','S1'] if continuation else ['O','S0','S1'])


def test_transport_uncertainty_stops_batch_without_retry(tmp_path):
    p,d,ctx,_=full_case();calls=[]
    def send(*args):calls.append(args);return None,{'stop_batch':True,'physical_sends':1}
    rows,stop=eval.run_arms(p,d,ctx,tmp_path,send=send)
    assert stop and len(calls)==len(rows)==1


def test_missing_approval_cannot_start_sources_or_model(monkeypatch):
    import sys
    monkeypatch.setattr(sys,'argv',['eval','--execute']);monkeypatch.delenv('R4_2_APPROVAL',raising=False)
    with pytest.raises(ValueError,match='EVAL_EXPLICIT_AUTHORITY'):eval.main()


def test_amount_unlimited_is_still_two_cases_eight_requests_and_no_production():
    assert {s['ticker'] for s in eval.SAMPLES}=={'600362','603507'}
    assert eval.WORK_REF.startswith('research-eval/')
    assert eval.PREFIX.startswith('research_runs/evaluations/')
    assert 'stock-questions' not in eval.PREFIX
    assert eval.M=='f956ea490ede8f31fe82fae4a1dc7f43c94d1a6d'
