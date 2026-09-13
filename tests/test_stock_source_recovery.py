"""Synthetic recovery controls through the original host/admission/Funnel.

These fake sources/permissions are not issuer evidence or live model responses.
"""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import stock_source_recovery as recovery
from decision_kernel.runtime import stock_research_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_research_reading as reader
from decision_kernel.runtime import saved_research_once as once
from test_stock_research_host import setup_host


def setup_recovery(tmp_path, monkeypatch, *, mode='quick', fail=None):
    args, api, calls, captures, writes = setup_host(tmp_path, monkeypatch, mode=mode, fail=fail)
    now = read.clock(args['clock']()); old = 'd'*40; exposed = 'e'*40
    code = args['code']; stock = args['item']['thscode']; eid, prefix = intake.execution(stock)
    args['origin'] = {'run': {'id':42}, 'market_session':'2026-09-11'}
    selection = {'schema_version':1, 'execution_id':eid, 'thscode':stock,
        'question_kind':intake.QUESTION_KIND, 'observation':args['item']['observation'],
        'origin':args['origin']}
    failure = {'schema_version':1, 'execution_id':eid, 'thscode':stock,
        'question_kind':intake.QUESTION_KIND, 'record_kind':'PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT',
        'phase':'SOURCE_PREPARATION', 'formal_research_started':False, 'research_execution':'NOT_EXECUTED',
        'funnel_status':'NOT_REACHED', 'status':'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE',
        'error_code':'full annual or half-year business report unavailable',
        'finished_at':(now-timedelta(minutes=20)).isoformat(), **read.AUTHORITY}
    sr, fr = once.raw(selection), once.raw(failure)
    ss = once.source_ref(prefix+'prepare.json',old,sr,recovery.SELECTION_PURPOSE)
    fs = once.source_ref(prefix+'failure.json',old,fr,recovery.FAILURE_PURPOSE)
    api.files[old] = {**api.files[code],prefix+'prepare.json':sr,prefix+'failure.json':fr}
    api.heads[intake.WORK_REF] = old
    payload = read.assemble(code_commit=code,checked_at=(now-timedelta(minutes=15)).isoformat(),
        check_started_at=(now-timedelta(minutes=16)).isoformat(), lanes={}, capabilities=[],refresh_identity={},
        research={'handoffs':{'active':[]}, 'stock_business_work':{'status':'READ_OK',
            'latest_execution_attempt':{'id':43}, 'items':[{'thscode':stock,'status':'PRE_EXECUTION_FAILURE',
                'sources':{'failure':fs}}]}})
    er = once.raw(payload);api.files[exposed]={'current-state.json':er}
    permission = {'id':2,'body':'Synthetic explicitly scoped source recovery, not real Human authority.',
        'created_at':(now-timedelta(minutes=5)).isoformat(),
        'issue_url':'https://api.github.com/repos/'+once.REPO+'/issues/297'}
    request = {'schema_version':1,'enabled':True,'mode':recovery.MODE,
        'permission':{'comment_id':2,'created_at':permission['created_at'],
                      'body_sha256':once.sha(permission['body'].encode())},
        'exposed_reading':once.source_ref('current-state.json',exposed,er,'SHOWN_READING'),
        'source_stock_run_id':42,'source_research_run_id':43,
        'items':[{'thscode':stock,'selection':ss,'failure':fs,
                  'repair':{'kind':'REPORT_TITLE_PREFIX','report_id':'123'}}]}
    api.files[code][recovery.REQUEST]=once.raw(request)
    api.recovery_comment=permission
    base_get=api.get
    def get(path):
        if path=='issues/comments/2':api.calls+=1;return deepcopy(api.recovery_comment)
        if path in {'git/commits/'+old,'git/commits/'+exposed}:
            api.calls+=1;return {'sha':path.split('/')[-1],
                'committer':{'date':(now-timedelta(minutes=10)).isoformat()}}
        return base_get(path)
    monkeypatch.setattr(api,'get',get)
    capture=args['capture']
    def captured(**kw):
        context,reads,process=capture(**kw)
        context['issuer_inventory']['report_id']='123'
        context['issuer_documents'][0]['announcement_id']='123'
        reads[0]['identity']=stock[:6]+':123'
        return context,reads,process
    child,p = recovery.execution(stock)
    args.update(item={**args['item'],'execution_id':child,'prefix':p},capture=captured,recovery_request=request)
    return args,api,calls,captures,writes,old,exposed


@pytest.mark.parametrize('mode,stages',[('quick',['pre','quick']),('STOP',['pre']),('WAIT_FOR_TRIGGER',['pre'])])
def test_recovery_reuses_original_host_and_preserves_parent(tmp_path,monkeypatch,mode,stages):
    args,api,calls,captures,writes,old,_=setup_recovery(tmp_path,monkeypatch,mode=mode)
    original=deepcopy(api.files[old]); result=host.run_item(**args)
    assert result['status']=='VALIDATED_FUNNEL_CANDIDATE',result
    assert calls==stages and len(captures)==1
    assert result['work_kind']=='SOURCE_PREPARATION_RECOVERY' and result['new_disclosure'] is False
    latest=api.files[api.heads[intake.WORK_REF]]
    assert all(latest[p]==data for p,data in original.items())
    assert all(p.startswith(args['item']['prefix']) for p in set(latest)-set(original))
    packet=json.loads((args['output']/'input.json').read_bytes())
    assert len([s for s in packet['source_refs'] if s['purpose']==recovery.FAILURE_PURPOSE])==1
    assert json.loads((args['output']/'admission.json').read_bytes())['research_execution_allowed']
    args['output']=tmp_path/'again';before=len(writes)
    assert host.run_item(**args)['status']=='EXISTING_BASELINE_REUSED_NO_EXECUTION'
    assert calls==stages and len(captures)==1 and len(writes)==before


@pytest.mark.parametrize('name',sorted(once.OUTPUT_NAMES))
def test_any_child_partial_file_blocks_another_recovery(tmp_path,monkeypatch,name):
    args,api,calls,captures,writes,old,_=setup_recovery(tmp_path,monkeypatch)
    api.files[old][args['item']['prefix']+name]=b'{}'
    # A new permission number must not create another child name or execution.
    result=host.run_item(**args)
    assert result['status']=='EXISTING_BASELINE_REUSED_NO_EXECUTION'
    assert not calls and not captures and not writes
    assert list(__import__('inspect').signature(recovery.execution).parameters)==['thscode']


@pytest.mark.parametrize('bad',['candidate','launch','parent-bytes','exposure-time','exposure-membership',
                                'scope','permission','wrong-report','source','quick'])
def test_failure_boundaries_stop_without_a_false_wait(tmp_path,monkeypatch,bad):
    args,api,calls,captures,writes,old,exposed=setup_recovery(tmp_path,monkeypatch,
        fail=bad if bad in {'source','quick'} else None)
    _,parent_prefix=intake.execution(args['item']['thscode'])
    request=args['recovery_request']
    if bad in {'candidate','launch'}:api.files[old][parent_prefix+bad+'.json']=b'{}'
    elif bad=='parent-bytes':api.files[old][parent_prefix+'failure.json']+=b' '
    elif bad=='exposure-time':
        get=api.get
        def later(path):
            value=get(path)
            if path=='git/commits/'+exposed:value['committer']['date']=args['clock']()
            return value
        monkeypatch.setattr(api,'get',later)
    elif bad=='exposure-membership':
        value=json.loads(api.files[exposed]['current-state.json'])
        value['research']['stock_business_work']['items']=[]
        value['reading_hash']=read.canonical_hash({k:v for k,v in value.items() if k!='reading_hash'})
        raw=once.raw(value);api.files[exposed]['current-state.json']=raw
        request['exposed_reading']=once.source_ref('current-state.json',exposed,raw,'SHOWN_READING')
    elif bad=='scope':request['items'][0]['thscode']='300183.SZ'
    elif bad=='permission':api.recovery_comment['body']='revoked'
    elif bad=='wrong-report':request['items'][0]['repair']['report_id']='456'
    api.files[args['code']][recovery.REQUEST]=once.raw(request)
    result=host.run_item(**args)
    assert result['status']==('VALIDATED_EXECUTION_GAP' if bad=='quick' else 'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE'),result
    assert not (args['output']/'funnel.json').exists()
    if bad!='quick':assert not calls
    if bad not in {'quick','wrong-report','source'}:assert not captures and not writes


def test_permission_is_fresh_again_before_quick(tmp_path,monkeypatch):
    args,api,calls,captures,writes,_,_=setup_recovery(tmp_path,monkeypatch)
    original=args['call']
    def call(*a):
        value=original(*a)
        api.recovery_comment['body']='revoked after Pre'
        return value
    args['call']=call
    result=host.run_item(**args)
    assert result['status']=='VALIDATED_EXECUTION_GAP' and calls==['pre']


def test_root_automatic_mode_does_not_consume_recovery(tmp_path,monkeypatch):
    args,api,calls,captures,writes,_,_=setup_recovery(tmp_path,monkeypatch)
    args.pop('recovery_request');eid,prefix=intake.execution(args['item']['thscode'])
    args['item'].update(execution_id=eid,prefix=prefix)
    assert host.run_item(**args)['status']=='EXISTING_BASELINE_REUSED_NO_EXECUTION'
    assert not captures and not calls and not writes


def test_only_authorized_three_are_selected_from_complete_four_plan(tmp_path,monkeypatch):
    args,_,_,_,_,_,_=setup_recovery(tmp_path,monkeypatch)
    request=args['recovery_request'];template=request['items'][0]
    codes=['600184.SH','300183.SZ','603353.SH','300711.SZ']
    request['items']=[{**template,'thscode':code} for code in codes if code!='300183.SZ']
    selected={'items':[{'thscode':code} for code in codes]}
    value=recovery.select(selected,request,42)
    assert [r['thscode'] for r in value]==['600184.SH','603353.SH','300711.SZ']
    assert selected['items']==[{'thscode':code} for code in codes]
    assert [r['prefix'] for r in value]==[recovery.execution(r['thscode'])[1] for r in value]


def collect_result(args,api,tmp_path):
    api.calls=10;api.max_calls=244
    lanes={'stock':{'health':'LATEST_ATTEMPT_SUCCEEDED','gaps':[], 'last_qualified_result':{'coverage':{'qualified_issuers':1},'dispositions':[
        {'thscode':args['item']['thscode'],'status':'CONTRACT_CHECKED_RAW_READING','input_failure':None}]}}}
    payload=read.assemble(code_commit=args['code'],checked_at=args['clock'](),check_started_at=args['clock'](),
        lanes=lanes,research={'handoffs':{'active':[]}},capabilities=[],refresh_identity={})
    c=delivery.Collector(api,args['code'],tmp_path,now=args['clock'])
    c.files={'current-state.json':read.json_bytes(payload),'README.md':b'existing entry','market.bin':b'existing market'}
    c.sources={('old'+str(n),'f'*40):(b'old',{}) for n in range(delivery.MAX_SOURCE_FILES)}
    before=deepcopy(c.sources)
    value=reader.attach(c,payload)
    assert c.files['market.bin']==b'existing market' and c.sources==before
    return value,c


@pytest.mark.parametrize('failure',[None,'source','quick'])
def test_parent_and_recovery_are_both_readable_without_promotion(tmp_path,monkeypatch,failure):
    args,api,_,_,_,_,_=setup_recovery(tmp_path,monkeypatch,fail=failure)
    result=host.run_item(**args)
    value,c=collect_result(args,api,tmp_path)
    work=value['research']['stock_business_work'];assert work['status']=='READ_OK',work
    row=work['items'][0];child=row['source_recovery']
    assert row['status']=='PRE_EXECUTION_FAILURE'
    assert child['status']==('PRE_EXECUTION_FAILURE' if failure=='source' else result['status'])
    assert work['counts']['PRE_EXECUTION_FAILURE']==1
    assert child['new_disclosure'] is False and child['investment_authority']=='NONE'
    assert value['pending']==[]
    read.validate_read_package(value)


def test_reader_rejects_corrupt_recovery_binding_without_losing_market(tmp_path,monkeypatch):
    args,api,_,_,_,_,_=setup_recovery(tmp_path,monkeypatch);host.run_item(**args)
    path=args['item']['prefix']+'prepare.json';files=api.files[api.heads[intake.WORK_REF]]
    prep=json.loads(files[path]);prep['source_recovery']['parent_failure']['git_blob']='f'*40
    files[path]=once.raw(prep)
    value,_=collect_result(args,api,tmp_path)
    assert value['research']['stock_business_work']['status']=='UNAVAILABLE_OR_REJECTED'


@pytest.mark.parametrize('wrong',['no-doc','no-page','different-review'])
def test_visual_repair_requires_the_bound_material_not_only_new_time(wrong):
    repair={'kind':'BOUND_VISUAL_PAGE','report_id':'123','pdf_sha256':'f'*64,'page_number':4,'review_git_blob':'a'*40}
    doc={'announcement_id':'123','pdf_sha256':'f'*64,'pages':[{'text':'synthetic'}],
         'page_reading':{'pages':[{'page_number':4,'method':'AI_VISUAL_READING','review_source':{'git_blob':'a'*40}}]}}
    context={'issuer_inventory':{'report_id':'123'},'issuer_documents':[doc]}
    if wrong=='no-doc':context['issuer_documents']=[]
    elif wrong=='no-page':doc['page_reading']=None
    else:doc['page_reading']['pages'][0]['review_source']['git_blob']='b'*40
    with pytest.raises(ValueError):recovery.check_materials({'repair':repair},context)


def test_late_parent_mutation_stops_quick_without_touching_failed_history(tmp_path, monkeypatch):
    args,api,calls,_,_,_,_=setup_recovery(tmp_path,monkeypatch)
    call=args['call'];_,prefix=intake.execution(args['item']['thscode'])
    def changed(*a):
        value=call(*a)
        api.files[api.heads[intake.WORK_REF]][prefix+'failure.json'] += b' '
        return value
    args['call']=changed
    result=host.run_item(**args)
    assert result['status']=='VALIDATED_EXECUTION_GAP' and calls==['pre']
    assert not (args['output']/'funnel.json').exists()


@pytest.mark.parametrize('failure',['source','quick'])
def test_failed_recovery_is_consumed_without_respending(tmp_path,monkeypatch,failure):
    args,api,calls,captures,writes,_,_=setup_recovery(tmp_path,monkeypatch,fail=failure)
    first=host.run_item(**args);before=(list(calls),list(captures),len(writes))
    assert first['status'] in {'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE','VALIDATED_EXECUTION_GAP'}
    args['output']=tmp_path/'repeat'
    assert host.run_item(**args)['status']=='EXISTING_BASELINE_REUSED_NO_EXECUTION'
    assert (calls,captures,len(writes))==before


def test_dispatch_opt_in_and_actual_three_parent_request_are_preserved():
    root=Path(__file__).parents[1]
    workflow=(root/'.github/workflows/stock-business-research.yml').read_text()
    assert 'recover-sources:' in workflow and 'default: false' in workflow
    assert "github.event_name == 'workflow_dispatch' && inputs.recover-sources" in workflow
    assert 'extra+=(--recover-sources)' in workflow
    assert 'schedule:' not in workflow and '\n  push:' not in workflow
    request=json.loads((root/recovery.REQUEST).read_bytes())
    assert request['permission']['comment_id']==5652047028
    assert request['source_stock_run_id']==34673882756 and request['source_research_run_id']==34744840053
    entries=recovery.request_items(request)
    assert [e['thscode'] for e in entries]==['600184.SH','603353.SH','300711.SZ']
    assert entries[2]['repair']['review_git_blob']==once.blob((root/'research_runs/source-readings'/
        entries[2]['repair']['pdf_sha256']/'page-4.json').read_bytes())
