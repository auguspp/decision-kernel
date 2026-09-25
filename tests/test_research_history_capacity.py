"""Larger saved history is not new execution authority; all edges stay offline."""
from copy import deepcopy
import json
import socket
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import reviewed_question_reading as reader
from decision_kernel.runtime import stock_research_reading as legacy
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import saved_research_once as once
from test_reviewed_question_reading import completed, report
from test_stock_daily_question import setup_daily
from test_stock_daily_question_capacity import retain_case_files, capacity_input, view


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("history capacity tests cannot use live networking")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


def test_history_capacity_is_shared_and_does_not_increase_execution_permission():
    assert legacy.MAX_STOCK_SOURCE_FILES == 256
    assert reader.MAX_EXECUTIONS == 16
    assert legacy.EXTRA_API_CALLS == 2 * legacy.MAX_STOCK_SOURCE_FILES + 64 == 576
    assert delivery.MAX_API_CALLS + legacy.EXTRA_API_CALLS <= 1024
    assert daily.POLICY["max_market_days"] == 10
    assert daily.POLICY["max_attempts_per_market_day"] == 1
    assert daily.POLICY["automatic_retry"] is False
    assert daily.POLICY["automatic_deep"] is False
    assert daily.POLICY["retained_source_file_bytes"] == 512 * 1024


def add_partial(c, template_prefix, number):
    """Add an explicitly synthetic stored partial, not a fabricated live execution."""
    stored = c.api.files[c.api.heads[intake.WORK_REF]]
    original = json.loads(stored[template_prefix + 'prepare.json'])
    source = original['question_source']
    q = json.loads(c.api.file(source['path'], source['ref']))
    q['question_id'] = 'synthetic-history-' + str(number)
    eid, prefix = host.question_execution(q['security_id'], q['question_id'])
    body = once.raw(q)
    qs = once.source_ref('research_runs/synthetic-history/' + str(number) + '/question.json',
                         source['ref'], body, source['purpose'])
    c.api.files[qs['ref']][qs['path']] = body
    prepared = deepcopy(original)
    prepared.update(question_id=q['question_id'], question_source=qs)
    prepared['execution_key']['execution_id'] = eid
    stored[prefix + 'prepare.json'] = once.raw(prepared)


@pytest.mark.parametrize('count', [16, 17])
def test_actual_reader_keeps_large_history_and_rejects_new_execution_bound(tmp_path, monkeypatch, count):
    _, c, baseline, prefix, calls, writes = completed(tmp_path, monkeypatch, stock=False)
    for i in range(1, count):
        add_partial(c, prefix, i)
    before = deepcopy(c.api.files[c.api.heads[intake.WORK_REF]])
    call_count, write_count = len(calls), len(writes)
    result = reader.attach(c, baseline)
    entry = result['research']['reviewed_question_work']
    if count == 16:
        assert entry['status'] == 'READ_OK', entry
        work = report(c, result)['question_work']
        assert len(work['items']) == 16 and work['retained_source_file_count'] > 32
        assert sum(i['status'] == 'VALIDATED_FUNNEL_RESULT' for i in work['items']) == 1
        assert sum(i['status'] == 'RETAINED_NO_RESEARCH_RESULT' for i in work['items']) == 15
    else:
        assert entry['status'] == 'UNAVAILABLE_OR_REJECTED'
        assert entry['diagnostic']['code'] == 'EXECUTION_SCOPE_BOUND'
        assert entry['execution_count'] is None
    assert len(calls) == call_count and len(writes) == write_count
    assert c.api.files[c.api.heads[intake.WORK_REF]] == before
    assert result['pending'] == [] and result['lanes'] == baseline['lanes']


@pytest.mark.parametrize('overflow', [False, True])
def test_shared_file_bound_includes_declaration_at_256_not_just_core(tmp_path, monkeypatch, overflow):
    _, c, baseline, _, calls, writes = completed(tmp_path, monkeypatch, stock=False)
    research = deepcopy(baseline['research'])
    # One real synthetic-host result needs nine CORE files and its declaration.
    n = legacy.MAX_STOCK_SOURCE_FILES - len(reader.CORE) - 1 + int(overflow)
    research['stock_business_work'] = {'items': [{'sources': {
        str(i): {'read_path': f'sources/git/synthetic-legacy-{i}/input.json'} for i in range(n)}}]}
    baseline = model.assemble(code_commit=baseline['code_commit'], checked_at=baseline['generated_at'],
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'],
        research=research, capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    call_count, write_count = len(calls), len(writes)
    result = reader.attach(c, baseline)
    work = report(c, result)['question_work']
    assert work['status'] == ('READ_OK_WITH_QUESTION_GAPS' if overflow else 'READ_OK'), work
    assert work['items'][0]['status'] == ('UNAVAILABLE_OR_REJECTED' if overflow else 'VALIDATED_FUNNEL_RESULT')
    assert work['retained_source_file_count'] == 256
    assert len(calls) == call_count and len(writes) == write_count


def test_current_three_result_history_no_longer_blocks_original_daily_capacity(tmp_path, monkeypatch):
    c = setup_daily(tmp_path, monkeypatch)
    for key in ('1', '2', '3'):
        retain_case_files(c, reader.PREFIX + key * 64 + '/', reader.CORE)
    packet, state = capacity_input(c)
    commit, rows = view(c)
    before_calls, before_writes = len(c.calls), len(c.writes)
    daily.capacity(c.api, commit, rows, state, packet)
    with monkeypatch.context() as m:
        m.setattr(legacy, 'MAX_STOCK_SOURCE_FILES', 32)
        with pytest.raises(once.TrialError, match='DAILY_READING_CAPACITY_UNAVAILABLE'):
            daily.capacity(c.api, commit, rows, state, packet)
    assert len(c.calls) == before_calls and len(c.writes) == before_writes


def test_read_and_publication_api_reserve_remains_finite():
    limit = delivery.MAX_API_CALLS + legacy.EXTRA_API_CALLS
    c = SimpleNamespace(api=SimpleNamespace(calls=limit - 512 - 7, max_calls=limit), files={})
    reader._reserve(c, reads=256, new_files=256)
    c.api.calls += 1
    with pytest.raises(ValueError, match='Question publication reserve'):
        reader._reserve(c, reads=256, new_files=256)
    assert legacy.call_limit(SimpleNamespace(max_calls=100)) == 100


CURRENT_STOCK_BUSINESS_JOBS = ['research-stock-business', 'prepare-stock-sources',
    'deepseek-compatibility', 'prepare-declared-report-sources']


def stock_business_attempt(active, event, conclusion, *, historical_source_job=False, incomplete=False):
    run = {'id': 42, 'event': event, 'path': '.github/workflows/stock-business-research.yml',
        'head_branch': 'main', 'run_attempt': 1, 'head_sha': 'a' * 40,
        'head_repository': {'full_name': once.REPO}, 'created_at': '2026-09-23T03:00:00Z',
        'updated_at': '2026-09-23T03:01:00Z', 'status': 'completed', 'conclusion': conclusion}
    names = list(CURRENT_STOCK_BUSINESS_JOBS)
    if historical_source_job:
        names.append('retain-public-report-source')
    if active == 'unknown':
        names.append('unknown')
    selected = {active} if active != 'both' else {'research-stock-business', 'prepare-declared-report-sources'}
    jobs = [{'run_id': 42, 'name': n, 'conclusion': conclusion if n in selected else 'skipped'} for n in names]
    def get(path):
        if 'workflows/' in path:
            return {'workflow_runs': [run], 'total_count': 1}
        return {'jobs': jobs, 'total_count': len(jobs) + int(incomplete)}
    return legacy.attempts(SimpleNamespace(api=SimpleNamespace(get=get, calls=0, max_calls=756), files={}))


@pytest.mark.parametrize('active,event,conclusion,expected', [
    ('prepare-declared-report-sources', 'issues', 'success', 'latest_report_source_attempt'),
    ('prepare-declared-report-sources', 'issues', 'failure', 'latest_report_source_attempt'),
    ('research-stock-business', 'issues', 'success', 'latest_execution_attempt'),
    ('research-stock-business', 'issues', 'failure', 'latest_execution_attempt'),
    ('prepare-declared-report-sources', 'workflow_dispatch', 'success', None),
    ('unknown', 'issues', 'success', None),
    ('both', 'issues', 'success', None),
    ('incomplete', 'issues', 'success', None),
])
def test_current_four_job_workflow_classification_never_promotes_sources(active, event, conclusion, expected):
    result = stock_business_attempt(active, event, conclusion, incomplete=active == 'incomplete')
    keys = ['latest_execution_attempt', 'latest_source_preparation_attempt',
            'latest_compatibility_attempt', 'latest_report_source_attempt']
    if expected:
        assert result[expected]['id'] == 42 and result[expected]['conclusion'] == conclusion
        assert not result['unclassified_invocations']
    else:
        assert result['attempt_classification_status'] == 'PARTIAL_OR_UNAVAILABLE'
    assert all(result[k] is None for k in keys if k != expected)
    assert result['preparation_result_semantics'] == 'INVOCATION_METADATA_ONLY_NOT_SOURCE_OR_RESEARCH_ACCEPTANCE'


def test_retired_woton_source_job_remains_readable_as_historical_attempt():
    result = stock_business_attempt('retain-public-report-source', 'issues', 'success',
                                    historical_source_job=True)
    assert result['latest_report_source_attempt']['id'] == 42
    assert result['latest_report_source_attempt']['conclusion'] == 'success'
    assert not result['unclassified_invocations']
    assert result['preparation_result_semantics'] == 'INVOCATION_METADATA_ONLY_NOT_SOURCE_OR_RESEARCH_ACCEPTANCE'
