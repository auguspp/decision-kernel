"""Reuse real synthetic continuation outputs in the existing read-only Collector."""
from copy import deepcopy
from types import SimpleNamespace
import pytest

from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import saved_disclosure_preparation as prep
from decision_kernel.runtime import incremental_disclosure as work
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import external_research_identity as identity
from test_disclosure_same_source_continuation import fixture, prepared_call, check, CODE

CONFIG={'ref':work.WORK_REF,'prefix':work.WORK_PREFIX,'mode':'RETAINED_DISCLOSURE_CANDIDATE_READ_ONLY','max_items':10}


def reader(api,clock,tmp_path,monkeypatch):
    get,file=api.get,api.file
    api.calls=0
    def counted_get(endpoint):
        api.calls+=1
        if endpoint=='git/ref/heads/'+work.WORK_REF:
            return {'object':{'type':'commit','sha':api.work}}
        return get(endpoint)
    def counted_file(path,ref): api.calls+=1; return file(path,ref)
    monkeypatch.setattr(api,'get',counted_get);monkeypatch.setattr(api,'file',counted_file)
    return delivery.Collector(api,CODE,tmp_path/'reading',now=clock)


@pytest.mark.parametrize('failed_model',[False,True])
def test_parent_failure_and_child_result_both_visible_without_new_disclosure_or_authority(tmp_path,monkeypatch,failed_model):
    args,api,clock,raw,_,spec,_=fixture(tmp_path,monkeypatch)
    _,result,_=prepared_call(args,api,clock,tmp_path,monkeypatch,fail=failed_model)
    c=reader(api,clock,tmp_path,monkeypatch)
    value=c.research_work(CONFIG)
    assert value['item_count']==2 and value['counts']['PRE_EXECUTION_FAILURE']==1
    assert value['counts']['VALIDATED_EXECUTION_GAP' if failed_model else 'VALIDATED_FUNNEL_CANDIDATE']==1
    child=next(i for i in value['items'] if i.get('work_kind'))
    assert child['new_disclosure'] is False and child['permission_comment_id']==7
    assert child['assessment_input_hash']==child['parent_assessment_input_hash']==work._packet(raw).assessment_input_hash
    assert child['sources']['packet']['path']==work.request_path(child['assessment_input_hash'])
    assert child['sources']['candidate']['path'].startswith(child['candidate_output_prefix'])
    assert all(i[k]=='NONE' for i in value['items'] for k in read.AUTHORITY)
    assert all(i['registered_current_handoff'] is False for i in value['items'])


def test_child_source_failure_keeps_two_distinct_failures(tmp_path,monkeypatch):
    args,api,clock,raw,_,_,note_path=fixture(tmp_path,monkeypatch)
    del api.snapshots[CODE][note_path]
    result=prep.prepare_reserved(**args)
    assert result['status']=='NOT_EXECUTED'
    c=reader(api,clock,tmp_path,monkeypatch)
    value=c.research_work(CONFIG)
    assert value['item_count']==value['counts']['PRE_EXECUTION_FAILURE']==2
    assert len({i['sources']['failure']['path'] for i in value['items']})==2


@pytest.mark.parametrize('damage',['wrong-prefix','wrong-permission-id','missing-parent-failure','child-packet'])
def test_invalid_child_cannot_hide_or_overwrite_parent(tmp_path,monkeypatch,damage):
    args,api,clock,raw,_,spec,_=fixture(tmp_path,monkeypatch)
    prepared_call(args,api,clock,tmp_path,monkeypatch)
    key=work._packet(raw).assessment_input_hash
    files=api.snapshots[api.work]
    prefix=check(args,clock,raw,spec)['execution_prefix']
    if damage=='missing-parent-failure': del files[work.request_path(key).replace('packet.json','failure.json')]
    elif damage=='child-packet': files[prefix+'packet.json']=raw
    elif damage=='wrong-prefix':
        for path in list(files):
            if path.startswith(prefix): files[path.replace('/continuations/7/','/continuations/8/')]=files.pop(path)
    else:
        obj=identity._json(files[prefix+'input.json']);obj['execution_id']='forged-child'
        files[prefix+'input.json']=once.raw(obj)
    c=reader(api,clock,tmp_path,monkeypatch)
    c.files={'baseline.txt':b'keep'};before=deepcopy(c.files)
    with pytest.raises(ValueError): c.research_work(CONFIG)
    assert c.files==before and c.sources=={}


def test_reading_budget_failures_do_not_leak_projection_or_spend_model(tmp_path,monkeypatch):
    args,api,clock,_,_,_,_=fixture(tmp_path,monkeypatch)
    prepared_call(args,api,clock,tmp_path,monkeypatch)
    c=reader(api,clock,tmp_path,monkeypatch)
    c.files={'baseline.txt':b'keep'}
    api.calls=178
    with pytest.raises(ValueError,match='base publication budget'):c.research_work(CONFIG)
    assert c.files=={'baseline.txt':b'keep'} and c.sources=={} and api.calls==178


def test_original_eight_item_config_still_rejects_nine_before_source_reads(tmp_path,monkeypatch):
    from test_incremental_disclosure import packet
    args,api,clock,_,_,_,_=fixture(tmp_path,monkeypatch)
    files={'README.md':b'original data-only'}
    for i in range(9):
        raw=packet(code='600036',day=8,version=hex(i+1)[-1])
        files[work.request_path(work._packet(raw).assessment_input_hash)]=raw
    api.snapshots[api.work]=files
    c=reader(api,clock,tmp_path,monkeypatch)
    with pytest.raises(ValueError,match='item bound'):c.research_work({**CONFIG,'max_items':8})
    assert api.calls==2
    # Deliberately configured capacity 10 permits the actual 7 parents + 2 children.
    assert c.research_work(CONFIG)['item_count']==9
