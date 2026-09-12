"""Synthetic integration through actual #337, original models/Retainer/Funnel."""
from copy import deepcopy
import pytest
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import saved_disclosure_host as host
from decision_kernel.runtime import saved_disclosure_preparation as prep
from decision_kernel.runtime import saved_research_once as once
from test_saved_disclosure_preparation import setup, CODE
from test_saved_research_once import pre, quick


@pytest.mark.parametrize('route', ['WAIT_FOR_TRIGGER', 'STOP', 'CONTINUE_TO_QUICK'])
def test_preparation_to_original_executor_and_repeat_block(tmp_path, monkeypatch, route):
    args, api, clock, _, _ = setup(tmp_path, monkeypatch)
    prepared = prep.prepare_reserved(**args)
    assert prepared['status'] == 'INPUT_PREPARED_NOT_EXECUTED'
    old_file = api.file
    def file(path, ref):
        try: return old_file(path, ref)
        except KeyError: raise delivery.GitHubReadError('GitHub HTTP 404')
    monkeypatch.setattr(api, 'file', file)
    calls=[]
    def model(stage,prompt,*_):
        calls.append(stage)
        return pre(prompt,route) if stage=='pre' else quick(prompt,'DEEPEN')
    monkeypatch.setattr(once, 'model_call', model)
    result=host.execute_prepared(api=api,prepared=prepared,code_commit=CODE,
                                 output=tmp_path/'execute',clock=clock)
    assert result['status']=='VALIDATED_FUNNEL_RESULT', result
    assert result['formal_research_started'] and result['investment_authority']=='NONE'
    assert calls==(['pre','quick'] if route=='CONTINUE_TO_QUICK' else ['pre'])
    before=deepcopy(api.snapshots)
    repeated=host.execute_prepared(api=api,prepared=prepared,code_commit=CODE,
                                   output=tmp_path/'repeat-execute',clock=clock)
    assert repeated['status']=='ALREADY_LAUNCHED_NO_EXECUTION'
    assert api.snapshots==before and len(calls)<=2


def test_shared_model_failure_stays_original_gap_no_retry(tmp_path,monkeypatch):
    args,api,clock,_,_=setup(tmp_path,monkeypatch)
    prepared=prep.prepare_reserved(**args)
    original=api.file
    def file(path,ref):
        try:return original(path,ref)
        except KeyError:raise delivery.GitHubReadError('GitHub HTTP 404')
    monkeypatch.setattr(api,'file',file)
    calls=[]
    def failing(*_):
        calls.append('attempt');raise RuntimeError('private token must not be echoed')
    monkeypatch.setattr(once,'model_call',failing)
    result=host.execute_prepared(api=api,prepared=prepared,code_commit=CODE,
                                 output=tmp_path/'execute',clock=clock)
    assert result['status']=='EXECUTION_GAP',result
    assert calls==['attempt'] and not result['automatic_retry']
    assert 'private token' not in once.raw(result).decode()
    assert any(p.endswith('/candidate.json') for p in api.writes)
    assert not any(p.endswith('/funnel.json') for p in api.writes)
