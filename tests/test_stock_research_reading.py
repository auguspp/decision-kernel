"""Original Collector/publication isolation, not business truth or live outcomes."""
from copy import deepcopy
import json

import pytest

from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import stock_research_reading as reader
from decision_kernel.runtime import stock_research_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import saved_research_once as once
from test_stock_research_host import setup_host


def setup_reading(tmp_path,monkeypatch,*,fail=None):
    args,api,calls,captures,writes=setup_host(tmp_path,monkeypatch,fail=fail)
    result=host.run_item(**args)
    assert result['status'] in {'VALIDATED_FUNNEL_CANDIDATE','VALIDATED_EXECUTION_GAP','SOURCE_OR_INPUT_PREPARATION_INCOMPLETE'}
    api.calls=10;api.max_calls=244
    lanes={'stock':{'health':'LATEST_ATTEMPT_SUCCEEDED','gaps':[], 'last_qualified_result':{
        'market_session':'2026-09-11','coverage':{'qualified_issuers':1},'dispositions':[
            {'thscode':'600184.SH','status':'CONTRACT_CHECKED_RAW_READING','input_failure':None}]}}}
    payload=model.assemble(code_commit=args['code'],checked_at=args['clock'](),check_started_at=args['clock'](),
        lanes=lanes,research={'handoffs':{'active':[]},'candidate_work':{'status':'READ_OK','items':['old disclosure unchanged']},'gaps':[]},
        capabilities=[],refresh_identity={})
    collector=delivery.Collector(api,args['code'],tmp_path,now=args['clock'])
    collector.files={'current-state.json':model.json_bytes(payload),'README.md':model.render_summary(payload).encode(),
                     'existing-market.bin':b'existing market bytes'}
    return args,collector,payload


def test_stock_reads_keep_original_full_source_budget_separate(tmp_path,monkeypatch):
    _,c,p=setup_reading(tmp_path,monkeypatch)
    c.sources={(f'old-{n}','d'*40):(b'old',{}) for n in range(delivery.MAX_SOURCE_FILES)}
    previous=deepcopy(c.sources)
    result=reader.attach(c,p)
    assert result['research']['stock_business_work']['status']=='READ_OK',result['research']['stock_business_work']
    assert c.sources==previous and c.files['existing-market.bin']==b'existing market bytes'
    assert result['research']['candidate_work']==p['research']['candidate_work']
    assert len(result['research']['stock_business_work']['items'])==1
    assert result['pending']==[] and result['investment_authority']=='NONE'


@pytest.mark.parametrize('failure,status',[(None,'VALIDATED_FUNNEL_CANDIDATE'),('pre','VALIDATED_EXECUTION_GAP'),('source','PRE_EXECUTION_FAILURE')])
def test_stock_result_failure_and_partial_states_are_distinct(tmp_path,monkeypatch,failure,status):
    args,c,p=setup_reading(tmp_path,monkeypatch,fail=failure)
    result=reader.attach(c,p)
    work=result['research']['stock_business_work']
    assert work['status']=='READ_OK',work
    row=work['items'][0];assert row['status']==status
    assert row['registered_current_handoff'] is False and row['investment_authority']=='NONE'
    if failure: assert row['terminal_state'] is None
    model.validate_read_package(result)
    for spec in row['sources'].values():
        assert model.blob_sha(c.files[spec['read_path']])==spec['git_blob']


@pytest.mark.parametrize('problem',['candidate-corrupt','prepare-corrupt','missing-input','both-failure-candidate','missing-reservation'])
def test_bad_stock_history_rejected_without_losing_existing_lanes(tmp_path,monkeypatch,problem):
    args,c,p=setup_reading(tmp_path,monkeypatch)
    files=c.api.files[c.api.heads[intake.WORK_REF]];prefix=args['item']['prefix']
    if problem=='candidate-corrupt': files[prefix+'candidate.json']=b'{}'
    elif problem=='prepare-corrupt':
        value=json.loads(files[prefix+'prepare.json']);value['thscode']='300183.SZ';files[prefix+'prepare.json']=once.raw(value)
    elif problem=='missing-input': del files[prefix+'input.json']
    elif problem=='both-failure-candidate':files[prefix+'failure.json']=b'{}'
    elif problem=='missing-reservation':del files[prefix+'prepare.json']
    before={k:v for k,v in c.files.items() if k not in {'README.md','current-state.json'}}
    result=reader.attach(c,p)
    assert result['research']['stock_business_work']['status']=='UNAVAILABLE_OR_REJECTED'
    assert result['lanes']==p['lanes'] and result['research']['candidate_work']==p['research']['candidate_work']
    assert before=={k:v for k,v in c.files.items() if k not in {'README.md','current-state.json'}}
    assert not c.sources


def test_stock_api_reserve_rejects_before_metadata_spends_baseline(tmp_path,monkeypatch):
    _,c,p=setup_reading(tmp_path,monkeypatch)
    c.api.calls=244-len(c.files)-5;before=c.api.calls
    result=reader.attach(c,p)
    assert c.api.calls==before
    assert result['research']['stock_business_work']['status']=='UNAVAILABLE_OR_REJECTED'


def test_partial_work_is_not_not_started_or_research_success(tmp_path,monkeypatch):
    args,c,p=setup_reading(tmp_path,monkeypatch)
    files=c.api.files[c.api.heads[intake.WORK_REF]];prefix=args['item']['prefix']
    for path in list(files):
        if path.startswith(prefix) and not path.endswith('/prepare.json'): del files[path]
    result=reader.attach(c,p)
    assert result['research']['stock_business_work']['items'][0]['status']=='RETAINED_NO_RESEARCH_RESULT'
