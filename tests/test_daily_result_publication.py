"""Exercise the actual publisher condition; no new production Research call."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).parents[1]
WORKFLOW=ROOT/'.github/workflows/current-state-read-entry.yml'


def expression():
    raw=WORKFLOW.read_text()
    body=raw.split('  publish-reading:\n    if: >-\n',1)[1].split('    runs-on:',1)[0]
    return ' '.join(body.split()).replace('&&',' and ').replace('||',' or ')


def namespace(value):
    return SimpleNamespace(**{k:namespace(v) if isinstance(v,dict) else v for k,v in value.items()})


def event():
    return {'repository':'auguspp/decision-kernel','ref':'refs/heads/main','run_attempt':1,
      'event':{'action':'completed','workflow_run':{
      'name':'stock-business-research','path':'.github/workflows/stock-business-research.yml',
      'event':'issues','head_repository':{'full_name':'auguspp/decision-kernel'},
      'head_branch':'main','run_attempt':1,'conclusion':'success','actor':{'login':'auguspp'}}}}


def allows(data):
    # Expression is trusted checked-in configuration, not source or provider text.
    return eval(compile(expression(),str(WORKFLOW),'eval'),{'__builtins__':{}},{'github':namespace(data)})


@pytest.mark.parametrize('conclusion',['success','failure','cancelled'])
def test_owned_daily_completion_refreshes_saved_result_or_gap(conclusion):
    data=event(); data['event']['workflow_run']['conclusion']=conclusion
    assert allows(data)


@pytest.mark.parametrize('field,value',[
 ('repository','other/repo'),('ref','refs/heads/work'),('run_attempt',2),
 ('event.action','requested'),('event.workflow_run.run_attempt',2),
 ('event.workflow_run.head_repository.full_name','other/repo'),
 ('event.workflow_run.head_branch','work'),('event.workflow_run.actor.login','other'),
 ('event.workflow_run.path','.github/workflows/unreviewed.yml'),
 ('event.workflow_run.name','unreviewed-research')])
def test_unqualified_issue_event_does_not_enter_publisher(field,value):
    data=event(); target=data; keys=field.split('.')
    for k in keys[:-1]: target=target[k]
    target[keys[-1]]=value
    assert not allows(data)


@pytest.mark.parametrize('name,trigger,conclusion,expected',[
 ('kernel-tests','push','success',True),('kernel-tests','push','failure',False),
 ('stock-business-research','workflow_dispatch','success',True),
 ('stock-business-research','workflow_run','failure',True),
 ('saved-disclosure-research','push','success',True),
 ('saved-disclosure-research','issues','success',False),
 ('sector-radar-shadow','schedule','success',True),
 ('sector-radar-shadow','workflow_dispatch','failure',True),
 ('sector-radar-shadow','issues','success',False)])
def test_previous_trigger_routes_keep_their_contract(name,trigger,conclusion,expected):
    data=event();data['event']['workflow_run'].update(name=name,event=trigger,conclusion=conclusion)
    assert allows(data) is expected


def test_publisher_does_not_execute_research_or_workflow_run_code():
    raw=WORKFLOW.read_text()
    assert 'ref: ${{ github.sha }}' in raw
    assert 'persist-credentials: false' in raw and 'secrets.' not in raw
    assert 'stock_question_host' not in raw and '--include-reviewed-questions' in raw
    assert 'schedule:' not in raw and 'workflow_dispatch:' not in raw
