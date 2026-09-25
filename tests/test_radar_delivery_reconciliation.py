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
