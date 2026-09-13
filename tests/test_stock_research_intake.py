"""Selection-only synthetic tests; original Stock validation is a required seam."""
from copy import deepcopy
import inspect
from pathlib import Path

import pytest

from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_research_sources as sources
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import current_state_delivery as delivery
from test_current_state import run


def setup_plan(monkeypatch):
    codes=['600184.SH','300183.SZ','603353.SH','600967.SH','300711.SZ','001316.SZ']
    rows=[{'thscode':code,'company_name':'Synthetic '+code,'eligible_for_shadow_reading':n not in {3,5},
        'status':'CONTRACT_CHECKED_RAW_READING' if n not in {3,5} else 'DATA_QUALIFICATION_FAILED',
        'input_failure':None if n not in {3,5} else {'reason':'synthetic'},'excluded_reasons':[]} for n,code in enumerate(codes)]
    data={'projection':{'all_stock_observations':rows,'surfaced_stocks':[rows[0],rows[2],rows[4]]}}
    calls=[]
    def validate(run,files):
        calls.append(run)
        return {'coverage':{'planned_issuers':6,'qualified_issuers':4},'market_session':'2026-09-11','projection_hash':'a'*64}
    monkeypatch.setattr(intake.reading,'validate_stock',validate)
    return data,calls


def test_all_four_including_omitted_card_not_two_unavailable(monkeypatch):
    value,calls=setup_plan(monkeypatch);before=deepcopy(value)
    result=intake.plan(run(lane='stock'),{'reading/stock-reading.json':once.raw(value)})
    assert len(calls)==1 and value==before
    assert [i['thscode'] for i in result['items']]==['600184.SH','300183.SZ','603353.SH','300711.SZ']
    assert [i['thscode'] for i in result['excluded']]==['600967.SH','001316.SZ']
    assert result['new_research_result'] is False and result['research_authority']=='NONE'


@pytest.mark.parametrize('problem',['duplicate','missing','eligibility-count','qualification-conflict'])
def test_inconsistent_stock_plan_never_enters_research(monkeypatch,problem):
    value,calls=setup_plan(monkeypatch);rows=value['projection']['all_stock_observations']
    if problem=='duplicate': rows[1]['thscode']=rows[0]['thscode']
    elif problem=='missing': rows.pop()
    elif problem=='eligibility-count':rows[1]['eligible_for_shadow_reading']=False
    else:rows[1]['input_failure']={'reason':'synthetic conflicting failure'}
    with pytest.raises(ValueError):intake.plan(run(lane='stock'),{'reading/stock-reading.json':once.raw(value)})


def test_original_validator_rejection_is_not_ignored(monkeypatch):
    def reject(*_):raise ValueError('original Stock replay rejected')
    monkeypatch.setattr(intake.reading,'validate_stock',reject)
    with pytest.raises(ValueError,match='original Stock replay'):intake.plan({}, {})


@pytest.mark.parametrize('code',['../600184.SH','600184.SZ','300183.SH','920006.BJ',None,'600184.SH/extra'])
def test_security_exchange_and_path_constraints(code):
    with pytest.raises(ValueError):intake.execution(code)


def test_first_business_identity_has_no_price_or_run_parameter():
    assert list(inspect.signature(intake.execution).parameters)==['thscode']
    assert intake.execution('600184.SH')==intake.execution('600184.SH')
    assert intake.execution('600184.SH')!=intake.execution('300183.SZ')


@pytest.mark.parametrize('value',[0,True,1025,'180'])
def test_github_api_bound_is_explicit_and_invalid_values_rejected(value):
    with pytest.raises(ValueError):delivery.GitHubAPI('synthetic-only',max_calls=value)


def test_original_api_default_and_stock_opt_in_do_not_change_write_permissions():
    api=delivery.GitHubAPI('synthetic-only')
    assert api.max_calls==delivery.MAX_API_CALLS==180
    with pytest.raises(ValueError,match='write outside'):api.write('contents/main.py',{})
    bigger=delivery.GitHubAPI('synthetic-only',max_calls=1024)
    assert bigger.max_calls==1024
    with pytest.raises(ValueError,match='write outside'):bigger.write('contents/main.py',{})


@pytest.mark.parametrize('limit',[0,True,131071,524289,1.5])
def test_unsupported_model_byte_bounds_fail_before_sdk(limit,tmp_path):
    with pytest.raises(ValueError,match='unsupported'):
        once.model_call('pre',{},None,tmp_path,[],max_prompt_bytes=limit)


def test_model_input_over_bound_is_not_clipped_or_sent(tmp_path):
    with pytest.raises(ValueError,match='model input byte budget'):
        once.model_call('pre',{'context':'x'*(512*1024)},None,tmp_path,[],max_prompt_bytes=512*1024)
    assert not list(tmp_path.iterdir())


def test_workflow_reuses_stock_successor_and_original_publication():
    root=Path(__file__).parents[1]
    s=(root/'.github/workflows/stock-business-research.yml').read_text()
    assert 'workflows: [hithink-stock-dump-trial]' in s and 'source-stock-run-id:' in s
    assert 'github.run_attempt == 1' in s and "github.ref == 'refs/heads/main'" in s
    assert 'github.event.workflow_run.head_repository.full_name == github.repository' in s
    assert 'persist-credentials: false' in s and 'if: always()' in s
    assert 'schedule:' not in s and '\n  push:' not in s and 'continue-research' not in s
    publisher=(root/'.github/workflows/current-state-read-entry.yml').read_text()
    assert 'stock-business-research' in publisher and 'saved-disclosure-research' in publisher
    assert 'decision_kernel.runtime.current_state_delivery' in publisher


def test_original_default_byte_bound_is_resolved_at_call_time(tmp_path,monkeypatch):
    monkeypatch.setattr(once,'MAX_PROMPT_BYTES',1)
    with pytest.raises(ValueError,match='model input byte budget'):
        once.model_call('pre',{},None,tmp_path,[])
    assert not list(tmp_path.iterdir())
