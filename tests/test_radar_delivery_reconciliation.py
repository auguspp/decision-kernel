"""Finite recovery tests; synthetic cases never prove live fault recovery."""
from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import json
from types import SimpleNamespace
import pytest


def module():
    path = Path(__file__).resolve().parents[1] / '.github/scripts/reconcile-radar-delivery.py'
    spec = importlib.util.spec_from_file_location('radar_reconciliation_test', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

M = 'a' * 40
NOW = datetime(2026, 9, 25, 11, 5, tzinfo=timezone.utc)


def run(number, created='2026-09-25T10:13:00Z', **kwargs):
    return dict(id=number, created_at=created, updated_at=created, head_sha=M,
                status='completed', conclusion='success', run_attempt=1, **kwargs)


def snapshot():
    sector = {'run': run(10), 'market_session': '2026-09-24',
              'status': 'APPENDED_COMPLETED_SESSION_WITH_SHADOW_CANDIDATES'}
    stock = {'run': run(9), 'market_session': '2026-09-24', 'coverage': {'scope_complete': True}}
    return dict(code_sha=M, run_id='101', active=[], sector={
        'last_qualified_result': sector, 'latest_state_validation': dict(sector, run=run(11)),
        'reading_copy_kind': 'VERIFIED_SAVED_PRODUCT', 'health': 'LATEST_ATTEMPT_SUCCEEDED',
        'gaps': [], 'latest_attempt': run(11)}, stock={
        'last_qualified_result': stock, 'reading_copy_kind': 'VERIFIED_SAVED_PRODUCT',
        'health': 'LATEST_ATTEMPT_SUCCEEDED', 'gaps': []}, stock_parent='10',
        sector_runs=[run(11), run(10)], stock_runs=[run(9)], main_ci_ready=True,
        source_retryable=False, intents=[])


def test_up_to_date_holiday_and_partial_do_not_refetch():
    mod, data = module(), snapshot()
    assert mod.choose(data, NOW)['status'] == 'UP_TO_DATE'
    data['stock']['last_qualified_result']['coverage']['scope_complete'] = False
    result = mod.choose(data, NOW)
    assert result['status'] == 'UP_TO_DATE_WITH_ISSUER_GAPS'
    assert result['action'] is None and result['open_gap']


def test_busy_then_same_day_noop_recovers_original_missing_stock():
    mod, data = module(), snapshot()
    data['stock_parent'] = '8'
    data['active'] = [20]
    assert mod.choose(data, NOW)['status'] == 'WAITING_FOR_ACTIVE_WORK'
    data['active'] = []
    result = mod.choose(data, NOW)
    assert result['action']['inputs'] == {'trial-purpose': 'stock-reading',
        'stock-market-run-id': '10', 'recovery-key': 'radar-stock-10-101'}
    data['stock_parent'] = '10'
    assert mod.choose(data, NOW)['action'] is None


def test_absent_daily_invocation_uses_original_produce_once():
    mod, data = module(), snapshot()
    for obj in (data['sector']['last_qualified_result'], data['sector']['latest_state_validation']):
        obj['run']['created_at'] = '2026-09-24T10:13:00Z'
    data['sector_runs'] = [run(10, '2026-09-24T10:13:00Z')]
    result = mod.choose(data, NOW)
    assert result['action']['workflow'] == 'sector-radar-shadow.yml'
    assert result['action']['inputs']['operation'] == 'produce'
    assert mod.choose(data, NOW.replace(hour=10, minute=20))['status'] == 'WAITING_FOR_PRIMARY_CAPTURE'


def test_source_retry_budget_and_nonretryable_failure_are_not_erased():
    mod, data = module(), snapshot()
    data['sector'].pop('latest_state_validation')
    data['sector']['last_qualified_result']['run']['created_at'] = '2026-09-24T10:13:00Z'
    failure = run(12)
    failure['conclusion'] = 'failure'
    data['sector_runs'] = [failure]
    assert mod.choose(data, NOW)['status'] == 'SOURCE_FAILURE_REQUIRES_ENGINEERING'
    data['source_retryable'] = True
    assert mod.choose(data, NOW)['action']['lane'] == 'sector'
    data['sector_runs'] = [dict(failure, id=n) for n in (12, 13, 14)]
    assert mod.choose(data, NOW)['status'] == 'SOURCE_ATTEMPT_BUDGET_EXHAUSTED'


@pytest.mark.parametrize('message,allowed', [
    ('HiThink request or response decoding failed for /api/a-share/a; failure_kind=TIMEOUT; elapsed_ms=10000', True),
    ('HiThink request or response decoding failed for /api/a-share/a; failure_kind=URL_ERROR; elapsed_ms=10', True),
    ('failure_kind=HTTP_OTHER; elapsed_ms=10; HiThink HTTP request failed for /api/a-share/a with status 502', True),
    ('failure_kind=HTTP_429; elapsed_ms=10; HiThink HTTP request failed for /api/a-share/a with status 429', False),
    ('failure_kind=HTTP_OTHER; elapsed_ms=10; HiThink HTTP request failed for /api/a-share/a with status 401; failure_kind=TIMEOUT', False),
    ('failure_kind=HTTP_OTHER; elapsed_ms=10; HiThink HTTP request failed for /api/a-share/a with status 403', False),
    ('timestamp mismatch failure_kind=TIMEOUT', False),
    ('HiThink request or response decoding failed for /api/a-share/a; failure_kind=JSON_DECODE_ERROR; elapsed_ms=10', False),
])
def test_failure_classification_uses_own_anchored_codes(message, allowed):
    assert module().source_retryable({'error_message': message}) is allowed


@pytest.mark.parametrize('lane', ['sector', 'stock'])
def test_rejected_archive_never_dispatches(lane):
    data = snapshot()
    data[lane]['health'] = 'LATEST_SUCCESS_INPUT_REJECTED'
    result = module().choose(data, NOW)
    assert result['status'] == f'{lane.upper()}_READ_REJECTED' and result['action'] is None


def test_existing_child_or_uncertain_intent_stops_duplicate():
    mod, data = module(), snapshot()
    data['stock_parent'] = '8'
    data['intents'] = [mod.choose(data, NOW)]
    assert mod.choose(data, NOW)['status'] == 'UNRECONCILED_DISPATCH_INTENT'
    data['intents'][0]['dispatch_occurred'] = False
    assert mod.choose(data, NOW)['action'] is not None
    data['stock_runs'].append(run(20, display_title='stock-reading | sector=10 | page=base | recovery=radar-stock-10-101'))
    assert mod.choose(data, NOW)['status'] == 'EXISTING_STOCK_ATTEMPT_REQUIRES_RECONCILIATION'


def test_missing_main_ci_is_wait_not_dispatch():
    data = snapshot()
    data['stock_parent'], data['main_ci_ready'] = '8', False
    assert module().choose(data, NOW)['status'] == 'WAITING_FOR_CURRENT_MAIN_CI'


def test_main_move_leaves_proof_no_post_occurred(monkeypatch):
    mod, data = module(), snapshot()
    data['stock_parent'] = '8'
    plan = mod.choose(data, NOW)
    monkeypatch.setenv('GITHUB_SHA', M)
    monkeypatch.setenv('GITHUB_RUN_ID', '101')
    api = SimpleNamespace(get=lambda _: {'object': {'sha': 'b'*40}})
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: pytest.fail('no dispatch'))
    report = mod.dispatch(plan, api)
    assert report['status'] == 'NOT_DISPATCHED_PRECHECK_CHANGED' and report['dispatch_occurred'] is False


@pytest.mark.parametrize('code,stdout,state', [(0, 'HTTP/2.0 204 No Content', 'DISPATCH_ACCEPTED_AWAITING_RESULT'),
                                              (1, '', 'DISPATCH_UNCERTAIN')])
def test_dispatch_at_most_once_and_no_uncertain_retry(monkeypatch, code, stdout, state):
    mod, data = module(), snapshot()
    data['stock_parent'] = '8'
    plan = mod.choose(data, NOW)
    monkeypatch.setenv('GITHUB_SHA', M)
    monkeypatch.setenv('GITHUB_RUN_ID', '101')
    monkeypatch.setattr(mod, 'active_work', lambda _: [])
    calls = []
    def call(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=code, stdout=stdout)
    monkeypatch.setattr(mod.subprocess, 'run', call)
    api = SimpleNamespace(get=lambda _: {'object': {'sha': M}})
    report = mod.dispatch(plan, api)
    assert report['status'] == state and len(calls) == 1
    payload = json.loads(calls[0][1]['input'])
    assert payload['inputs']['stock-market-run-id'] == '10' and payload['ref'] == 'main'


def test_old_missing_stock_does_not_disappear_when_new_day_succeeds():
    mod, data = module(), snapshot()
    data['stock_parent'] = '8'
    waiting = mod.retain_unresolved({}, mod.choose(data, NOW))
    data['stock_parent'] = '99'
    data['sector']['last_qualified_result']['run']['id'] = 99
    current = mod.choose(data, NOW)
    result = mod.retain_unresolved(waiting, current)
    assert result['open_gap'] and result['unresolved_deliveries'][0]['target'] == '10'
    assert mod.retain_unresolved(result, dict(current, stock_parent='10'))['unresolved_deliveries'] == []


@pytest.mark.parametrize("status", ["VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT", "ADOPTED_RECOVERY", "UNKNOWN"])
def test_non_result_origins_never_dispatch_stock(status):
    data = snapshot()
    data["stock_parent"] = "8"
    data["sector"]["last_qualified_result"]["status"] = status
    result = module().choose(data, NOW)
    assert result["status"] == "RESULT_BEARING_SECTOR_DELIVERY_UNAVAILABLE"
    assert result["action"] is None


def stock_upstream(monkeypatch, title='stock-reading | sector=10 | page=base | recovery=none'):
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'workflow_run')
    monkeypatch.setenv('GITHUB_SHA', M)
    monkeypatch.setenv('GITHUB_RUN_ID', '101')
    monkeypatch.setenv('UPSTREAM_PATH', '.github/workflows/hithink-stock-dump-trial.yml')
    monkeypatch.setenv('UPSTREAM_DISPLAY_TITLE', title)
    monkeypatch.setenv('UPSTREAM_RUN_ID', '100')
    monkeypatch.setenv('UPSTREAM_RUN_ATTEMPT', '1')


def upstream_job(name, conclusion):
    return dict(name=name, status='completed', conclusion=conclusion, run_id=100, run_attempt=1)


@pytest.mark.parametrize('conclusion', ['success', 'failure', 'cancelled', 'timed_out'])
def test_exact_independent_job_completion_never_reconciles_or_dispatches(monkeypatch, tmp_path, conclusion):
    mod = module()
    # Missing/misleading title cannot defeat the exact upstream-job check.
    stock_upstream(monkeypatch)
    calls = []
    def get(path):
        calls.append(path)
        assert path == 'actions/runs/100/attempts/1/jobs?per_page=100'
        return {'total_count': 2, 'jobs': [upstream_job('stock-reading', 'skipped'),
            upstream_job('stock-independent-observations', conclusion)]}
    api = SimpleNamespace(get=get)
    monkeypatch.setattr(mod, 'active_work', lambda _: pytest.fail('no daily collection'))
    data = mod.collect(api, tmp_path, NOW)
    plan = mod.choose(data, NOW)
    assert plan['status'] == mod.INDEPENDENT_NO_RECOVERY
    assert plan['action'] is None and not plan['open_gap']
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: pytest.fail('no dispatch'))
    with pytest.raises(ValueError, match='^DISPATCH_PLAN_REQUIRED$'):
        mod.dispatch(plan, api)
    assert len(calls) == 1


def test_explicit_independent_purpose_is_suppressed_even_without_job_metadata(monkeypatch, tmp_path):
    mod = module()
    stock_upstream(monkeypatch, 'stock-independent-observations | sector=none | page=base | recovery=none')
    api = SimpleNamespace(get=lambda _: pytest.fail('title already excludes daily recovery'))
    data = mod.collect(api, tmp_path, NOW)
    assert mod.choose(data, NOW)['status'] == mod.INDEPENDENT_NO_RECOVERY


@pytest.mark.parametrize('jobs', [
    [upstream_job('stock-reading', 'success')],
    [upstream_job('stock-reading', 'failure'), upstream_job('stock-independent-observations', 'skipped')],
])
def test_original_stock_completion_still_uses_existing_recovery(monkeypatch, tmp_path, jobs):
    mod = module()
    stock_upstream(monkeypatch)
    def get(path):
        if path == 'actions/runs/100/attempts/1/jobs?per_page=100':
            return {'total_count': len(jobs), 'jobs': jobs}
        assert path == 'git/ref/heads/main'
        return {'object': {'sha': M}}
    api = SimpleNamespace(get=get)
    monkeypatch.setattr(mod, 'active_work', lambda _: [20])
    data = mod.collect(api, tmp_path, NOW)
    assert 'independent_stock_capture' not in data
    assert mod.choose(data, NOW)['status'] == 'WAITING_FOR_ACTIVE_WORK'
    # Both unchanged missing-delivery routes remain eligible after activity ends.
    legacy = snapshot()
    legacy['independent_stock_capture'] = mod.independent_stock_upstream(api)
    legacy['stock_parent'] = '8'
    assert mod.choose(legacy, NOW)['action']['workflow'] == mod.STOCK
    legacy['sector'].pop('latest_state_validation')
    legacy['sector']['last_qualified_result']['run']['created_at'] = '2026-09-24T10:13:00Z'
    legacy['sector_runs'] = [run(10, '2026-09-24T10:13:00Z')]
    assert mod.choose(legacy, NOW)['action']['workflow'] == mod.SECTOR


@pytest.mark.parametrize('payload', [
    {}, {'total_count': 0, 'jobs': []}, {'total_count': 2, 'jobs': [upstream_job('stock-reading', 'success')]},
    {'total_count': 1, 'jobs': [dict(upstream_job('stock-independent-observations', 'failure'), run_id=99)]},
    {'total_count': 1, 'jobs': [dict(upstream_job('stock-independent-observations', 'failure'), run_attempt=2)]},
    {'total_count': 1, 'jobs': [dict(upstream_job('stock-independent-observations', 'failure'), status='in_progress')]},
    {'total_count': 1, 'jobs': [dict(upstream_job('stock-independent-observations', 'failure'), conclusion=None)]},
    {'total_count': 2, 'jobs': [upstream_job('stock-independent-observations', 'skipped')] * 2},
])
def test_incomplete_or_ambiguous_upstream_jobs_fail_closed(monkeypatch, tmp_path, payload):
    mod = module()
    stock_upstream(monkeypatch)
    api = SimpleNamespace(get=lambda _: payload)
    monkeypatch.setattr(mod, 'active_work', lambda _: pytest.fail('no daily collection'))
    with pytest.raises(ValueError, match='^UPSTREAM_STOCK_JOB'):
        mod.collect(api, tmp_path, NOW)


@pytest.mark.parametrize('event,path', [('schedule', ''), ('workflow_dispatch', ''),
    ('workflow_run', '.github/workflows/sector-radar-shadow.yml'),
    ('workflow_run', '.github/workflows/decision-inbox.yml')])
def test_other_reconciliation_origins_do_not_read_stock_jobs(monkeypatch, event, path):
    monkeypatch.setenv('GITHUB_EVENT_NAME', event)
    monkeypatch.setenv('UPSTREAM_PATH', path)
    api = SimpleNamespace(get=lambda _: pytest.fail('no new API query for other origins'))
    assert module().independent_stock_upstream(api) is False


def test_independent_completion_does_not_overwrite_daily_health(monkeypatch, tmp_path):
    import sys
    mod = module()
    monkeypatch.setenv('GITHUB_REPOSITORY', mod.REPOSITORY)
    monkeypatch.setenv('GITHUB_REF', 'refs/heads/main')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '1')
    monkeypatch.setenv('RECONCILE_MODE', 'execute')
    report = {'status': mod.INDEPENDENT_NO_RECOVERY, 'action': None, 'open_gap': False}
    (tmp_path / 'report.json').write_text(json.dumps(report))
    monkeypatch.setattr(sys, 'argv', ['reconcile-radar-delivery.py', 'report', '--output', str(tmp_path)])
    monkeypatch.setattr(mod, 'report_issue', lambda _: pytest.fail('no daily health mutation'))
    assert mod.main() == 0
    assert json.loads((tmp_path / 'report.json').read_text()) == report


def test_workflow_guard_is_specific_to_independent_stock_purpose():
    import yaml
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / '.github/workflows/stock-reading-after-sector.yml').read_text())
    job = workflow['jobs']['reconcile-deliveries']
    assert "github.event.workflow_run.path != '.github/workflows/hithink-stock-dump-trial.yml' ||" in job['if']
    assert "!startsWith(github.event.workflow_run.display_title, 'stock-independent-observations |')" in job['if']
    assert job['env']['UPSTREAM_PATH'] == '${{ github.event.workflow_run.path }}'
    assert job['env']['UPSTREAM_RUN_ID'] == '${{ github.event.workflow_run.id }}'
    assert job['env']['UPSTREAM_RUN_ATTEMPT'] == '${{ github.event.workflow_run.run_attempt }}'
    assert job['env']['UPSTREAM_DISPLAY_TITLE'] == '${{ github.event.workflow_run.display_title }}'
