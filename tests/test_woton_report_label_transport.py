"""Fixed issue-label transport is not source authorization or a Research trigger."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import woton_report_custody as c
from decision_kernel.runtime import stock_research_reading as reader
from test_woton_report_custody import CODE, AT, env, execute, pdf, no_network


def label_env():
    return {**env(), 'GITHUB_EVENT_NAME': 'issues', 'REPORT_INPUTS': '{}',
        'REPORT_EVENT_ACTION': 'labeled', 'REPORT_ISSUE_NUMBER': '297',
        'REPORT_LABEL': c.READY_LABEL, 'REPORT_SENDER': 'auguspp',
        'REPORT_IS_PULL_REQUEST': 'false'}


def test_fixed_label_and_original_manual_dispatch_are_separate_valid_transports():
    c.check_environment(label_env(), CODE)
    c.check_environment(env(), CODE)


@pytest.mark.parametrize('key,value', [
    ('REPORT_EVENT_ACTION','edited'), ('REPORT_ISSUE_NUMBER','481'),
    ('REPORT_LABEL','daily-question-ready'), ('REPORT_SENDER','other'),
    ('REPORT_IS_PULL_REQUEST','true'), ('REPORT_INPUTS','{"retain-report-source":true}'),
    ('GITHUB_EVENT_NAME','issue_comment'), ('GITHUB_SHA','b'*40),
    ('GITHUB_RUN_ATTEMPT','2'), ('GITHUB_REF','refs/heads/topic'),
    ('GITHUB_REPOSITORY','other/repo'), ('EXPECTED_CODE_SHA','main'),
])
def test_label_transport_rejects_wrong_identity_and_mixed_inputs(key,value):
    with pytest.raises(ValueError): c.check_environment({**label_env(), key:value}, CODE)


@pytest.mark.parametrize('key', ['REPORT_EVENT_ACTION','REPORT_ISSUE_NUMBER',
    'REPORT_LABEL','REPORT_SENDER','REPORT_IS_PULL_REQUEST'])
def test_label_transport_rejects_missing_fields(key):
    actual=label_env(); del actual[key]
    with pytest.raises(ValueError): c.check_environment(actual, CODE)


def test_actual_source_reservation_retains_issue_event_without_forging_dispatch(tmp_path,monkeypatch,pdf):
    for key,value in label_env().items(): monkeypatch.setenv(key,value)
    result,api=execute(tmp_path,monkeypatch,pdf)
    assert result['status']==c.COMPLETE
    import json
    prepare=json.loads(api.versions[api.head][c.PREFIX+'prepare.json'])
    assert (prepare['trigger_event'],prepare['trigger_issue'],prepare['trigger_label']) == (
        'issues','297',c.READY_LABEL)
    assert prepare['scope']==c.SCOPE and result['source_requests']==1
    assert result['model_calls']==0 and not result['formal_research_started']


@pytest.mark.parametrize('active', ['retain-public-report-source','research-stock-business',
    'prepare-stock-sources','deepseek-compatibility'])
def test_issue_events_cannot_be_classified_as_original_research_modes(active):
    run={'id':42,'event':'issues','path':'.github/workflows/stock-business-research.yml',
        'head_branch':'main','run_attempt':1,'head_sha':CODE,
        'head_repository':{'full_name':c.once.REPO},'created_at':AT,'updated_at':AT,
        'status':'completed','conclusion':'success'}
    jobs=[{'run_id':42,'name':name,'conclusion':'success' if name==active else 'skipped'}
        for name in ('research-stock-business','prepare-stock-sources',
                     'deepseek-compatibility','retain-public-report-source')]
    def get(endpoint):
        return {'workflow_runs':[run],'total_count':1} if 'workflows/' in endpoint else {
            'jobs':jobs,'total_count':len(jobs)}
    result=reader.attempts(SimpleNamespace(api=SimpleNamespace(get=get,calls=0,max_calls=252),files={}))
    assert all(result[k] is None for k in ('latest_execution_attempt',
        'latest_source_preparation_attempt','latest_compatibility_attempt'))
    if active=='retain-public-report-source':
        assert result['latest_report_source_attempt']['event']=='issues'
        assert not result['unclassified_invocations']
    else:
        assert result['latest_report_source_attempt'] is None
        assert result['attempt_classification_status']=='PARTIAL_OR_UNAVAILABLE'


def test_actual_workflow_label_scope_and_legacy_job_permissions_remain_separate():
    text=Path('.github/workflows/stock-business-research.yml').read_text()
    trigger=text.split('on:\n',1)[1].split('\npermissions:',1)[0]
    assert 'issues:\n    types: [labeled]' in trigger
    assert 'workflow_run:' not in trigger and 'schedule:' not in trigger
    for job in ('research-stock-business','deepseek-compatibility','prepare-stock-sources'):
        condition=text.split('  '+job+':\n',1)[1].split('    runs-on:',1)[0]
        assert "github.event_name == 'workflow_dispatch'" in condition
        assert '!inputs.retain-report-source' in condition
    source=text.split('  retain-public-report-source:\n',1)[1].split('  prepare-stock-sources:',1)[0]
    for fragment in ("github.event_name == 'issues'", "github.event.action == 'labeled'",
        'github.event.issue.number == 297', '!github.event.issue.pull_request',
        "github.event.sender.login == 'auguspp'", "github.event.label.name == 'woton-h1-source-ready'"):
        assert fragment in source
    assert 'secrets.' not in source and 'research-api' not in source
    assert 'github.event.issue.body' not in source and 'github.event.comment.body' not in source
    legacy=text.split('  prepare-stock-sources:\n',1)[1]
    assert 'contents: read' in legacy and 'contents: write' not in legacy
