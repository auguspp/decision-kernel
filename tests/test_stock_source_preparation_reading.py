"""Synthetic workflow-purpose metadata: no source or model execution."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from decision_kernel.runtime import stock_research_reading as reader
from decision_kernel.runtime import current_state as read


def run(i):
    return {'id':i,'event':'workflow_dispatch','path':'.github/workflows/stock-business-research.yml',
        'head_branch':'main','run_attempt':1,'head_sha':'a'*40,'status':'completed','conclusion':'success',
        'created_at':'2026-09-13T12:00:00Z','head_repository':{'full_name':read.REPOSITORY}}


def fixture(rows,jobs,*,fail=None):
    class API:
        calls=0;max_calls=244
        def get(self,path):
            self.calls+=1
            if path.startswith('actions/workflows/'):
                return {'total_count':len(rows),'workflow_runs':rows}
            key=int(path.split('/')[2])
            if fail==key: raise RuntimeError('private transport details')
            names=jobs[key]
            return {'total_count':len(names),'jobs':[{'id':key*10+n,'run_id':key,'name':name,
                    'status':'completed','conclusion':conclusion} for n,(name,conclusion) in enumerate(names)]}
    return SimpleNamespace(api=API(),files={})


def test_source_success_cannot_replace_last_research_attempt():
    c=fixture([run(2),run(1)],{2:[('prepare-stock-sources','success'),('research-stock-business','skipped')],
                             1:[('research-stock-business','failure')]})
    value=reader.attempts(c)
    assert value['latest_execution_attempt']['id']==1
    assert value['latest_source_preparation_attempt']['id']==value['latest_workflow_invocation']['id']==2
    assert not value['unclassified_invocations']


@pytest.mark.parametrize('bad_jobs',[[],[('other-job','success')],
    [('prepare-stock-sources','success'),('research-stock-business','success')],
    [('research-stock-business','skipped'),('prepare-stock-sources','skipped')],
    [('research-stock-business','success'),('research-stock-business','success')]])
def test_unknown_and_ambiguous_jobs_do_not_erase_identified_execution(bad_jobs):
    c=fixture([run(2),run(1)],{2:bad_jobs,1:[('research-stock-business','failure')]})
    value=reader.attempts(c)
    assert value['latest_execution_attempt']['id']==1 and value['unclassified_invocations']
    assert value['latest_source_preparation_attempt'] is None
    assert value['attempt_classification_status']=='PARTIAL_OR_UNAVAILABLE'


def test_unreadable_latest_jobs_report_gap_not_new_research():
    c=fixture([run(2),run(1)],{1:[('research-stock-business','success')]},fail=2)
    value=reader.attempts(c)
    assert value['latest_execution_attempt']['id']==1
    assert 'private transport' not in str(value)


def test_normal_run_with_skipped_source_job_is_research():
    value=reader.attempts(fixture([run(1)],{1:[('research-stock-business','failure'),('prepare-stock-sources','skipped')]}))
    assert value['latest_execution_attempt']['id']==1 and value['latest_source_preparation_attempt'] is None


def test_source_only_window_does_not_invent_a_research_run():
    value=reader.attempts(fixture([run(1)],{1:[('prepare-stock-sources','failure')]}))
    assert value['latest_execution_attempt'] is None and value['latest_source_preparation_attempt']['id']==1
    assert value['attempt_query_scope']=='NEWEST_TEN_EXACT_WORKFLOW_INVOCATIONS_NOT_ALL_HISTORY'


@pytest.mark.parametrize('field,value',[('run_attempt',2),('run_attempt',True),('head_branch','feature'),
    ('event','push'),('head_sha','bad'),('id',True),('head_repository',{'full_name':'foreign/repo'})])
def test_wrong_run_identity_rejected(field,value):
    row=run(1);row[field]=value
    with pytest.raises(ValueError):reader.attempts(fixture([row],{1:[('research-stock-business','success')]}))


def test_duplicate_invocations_rejected():
    with pytest.raises(ValueError):reader.attempts(fixture([run(1),run(1)],{1:[('research-stock-business','success')]}))


def test_publisher_call_reserve_unchanged():
    c=fixture([run(1)],{1:[('prepare-stock-sources','success')]});c.api.calls=240
    with pytest.raises(ValueError,match='reserve'):reader.attempts(c)
    assert c.api.calls==241  # no jobs fetch after the reserve rejection
