"""Dual-trigger wiring, fail-closed operations, not real schedule acceptance.

Provider fixtures below exercise the existing adapters/detector/audit/replayer.
No live acquisition, workflow dispatch or claims of GitHub cron execution.
"""
import ast
import json
import os
import runpy
import socket
import subprocess
import textwrap
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/sector-radar-shadow.yml'
SCRIPTS = ROOT / '.github/scripts'
EVENTS = ('workflow_dispatch', 'schedule')


def activity_module():
    return runpy.run_path(str(SCRIPTS / 'check-sector-scheduled-activity.py'))


def environment(event='schedule'):
    return {'GITHUB_REPOSITORY': 'auguspp/decision-kernel',
            'GITHUB_REF': 'refs/heads/main', 'GITHUB_RUN_ATTEMPT': '1',
            'GITHUB_EVENT_NAME': event, 'GITHUB_RUN_ID': '101', 'GITHUB_SHA': 'a'*40}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('schedule regression must not use the network')
    monkeypatch.setattr(socket, 'create_connection', deny)


def step(name):
    return WORKFLOW.read_text().split('      - name: ' + name + '\n', 1)[1].split('      - name: ', 1)[0]


@pytest.mark.parametrize('event', EVENTS)
def test_workflow_guards_apply_to_both_triggers(event):
    mod = activity_module()
    mod['require_invocation'](environment(event))
    for name, key, bad in (
        ('Require main branch', 'GITHUB_REF', 'refs/heads/other'),
        ('Require fresh workflow dispatch', 'GITHUB_RUN_ATTEMPT', '2'),
    ):
        script = textwrap.dedent(step(name).split('run: |\n', 1)[1])
        env = environment(event)
        assert subprocess.run(['bash', '-e', '-c', script], env=env, capture_output=True).returncode == 0
        env[key] = bad
        assert subprocess.run(['bash', '-e', '-c', script], env=env, capture_output=True).returncode != 0
        with pytest.raises(mod['CheckError']):
            mod['require_invocation'](env)
    for event_not_allowed in ('push', 'pull_request', 'workflow_run', ''):
        with pytest.raises(mod['CheckError']):
            mod['require_invocation'](environment(event_not_allowed))


def test_one_production_path_and_existing_publication_gates():
    raw = WORKFLOW.read_text()
    trigger = raw.split('on:\n', 1)[1].split('\npermissions:', 1)[0]
    assert '  workflow_dispatch:\n' in trigger
    assert '    - cron: "13 10 * * 1-5"' in trigger
    assert trigger.count('cron:') == 1 and 'push:' not in trigger
    assert raw.count('python -m decision_kernel.runtime.sector_radar_producer run') == 1
    assert raw.index('Require main branch') < raw.index('Check shared-Key activity')
    assert raw.index('Require fresh workflow dispatch') < raw.index('Check shared-Key activity')
    assert raw.index('Check shared-Key activity') < raw.index('Run independent Sector Radar shadow producer')
    normal_gate = "if: github.event_name != 'workflow_dispatch' || inputs.operation == 'produce'"
    assert normal_gate in step('Check shared-Key activity once before acquisition')
    assert normal_gate in step('Run independent Sector Radar shadow producer')
    assert 'HITHINK_SECTOR_REQUEST_PACING: "1"' in raw
    for name in ('Verify exact offline replay before publication',
                 'Render read-only saved-state context', 'Package joint economic and company reading',
                 'Upload authoritative state bundle', 'Save cache acceleration copy'):
        assert 'if: success()' in step(name)
    assert 'if: always()' in step('Upload complete run audit')
    assert 'continue-on-error' not in raw
    assert 'cancel-in-progress: false' in raw and 'timeout-minutes: 20' in raw
    assert 'GITHUB_EVENT_NAME' in step('Publish separate shadow summary')
    assert 'qualified recovery' in step('Publish separate shadow summary')
    assert 'cat sector-radar-run/summary.md >> "$GITHUB_STEP_SUMMARY"' in raw


@pytest.mark.parametrize('blocked', [False, True])
def test_activity_observation_checks_all_peer_statuses_once(blocked):
    mod = activity_module(); calls = []
    def read(url):
        status = parse_qs(urlsplit(url).query)['status'][0]; calls.append(status)
        # A queued Sector successor must not deadlock the current serialized run.
        rows = [{'id': 102, 'path': '.github/workflows/sector-radar-shadow.yml', 'status': status}]
        if blocked:
            rows += [{'id': 200+i, 'path': p + '@refs/heads/main', 'status': status}
                     for i, p in enumerate(sorted(mod['PEERS']))]
        return {'total_count': len(rows), 'workflow_runs': rows}
    assert mod['check_activity'](read) == ([200, 201, 202] if blocked else [])
    assert tuple(calls) == mod['ACTIVE']


@pytest.mark.parametrize('payload', [None, {}, {'total_count': True, 'workflow_runs': []},
    {'total_count': 101, 'workflow_runs': []}, {'total_count': 1, 'workflow_runs': []},
    {'total_count': 1, 'workflow_runs': [{'id': 1}]},
    {'total_count': 1, 'workflow_runs': [{'id': 1, 'path': 'x', 'status': 'completed'}]}])
def test_incomplete_activity_visibility_fails_without_retry(payload):
    mod = activity_module(); calls = []
    def read(url):
        calls.append(url); return payload
    with pytest.raises(mod['CheckError']):
        mod['check_activity'](read)
    assert len(calls) == 1


def test_metadata_http_failure_has_one_attempt_and_no_token_diagnostic(monkeypatch, capsys, tmp_path):
    mod = activity_module(); scope = mod['main'].__globals__; calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            raise HTTPError(request.full_url, 403, 'PRIVATE-CANARY', {}, None)
    monkeypatch.setitem(scope, 'build_opener', lambda *args: Opener())
    for k, v in environment().items(): monkeypatch.setenv(k, v)
    monkeypatch.setenv('GITHUB_TOKEN', 'PRIVATE-CANARY')
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(tmp_path/'summary.md'))
    assert mod['main']() == 2
    assert len(calls) == 1
    text = capsys.readouterr().out + (tmp_path/'summary.md').read_text()
    assert 'GITHUB_HTTP_403' in text and 'PRIVATE-CANARY' not in text
    assert 'global Key lock' in text


@pytest.mark.parametrize('script', ['verify-sector-radar-publication.py', 'build-sector-radar-reading.py'])
@pytest.mark.parametrize('event', EVENTS)
def test_existing_delivery_entrypoints_admit_both_events_without_skipping_guards(
        monkeypatch, tmp_path, script, event):
    # Only this test isolates the heavy downstream function to inspect admission.
    # Existing publication/reading tests still exercise its full checks separately.
    mod = runpy.run_path(str(SCRIPTS/script)); scope = mod['main'].__globals__; calls = []
    for k, v in environment(event).items(): monkeypatch.setenv(k, v)
    monkeypatch.setenv('HITHINK_FINANCE_API_KEY', '')
    monkeypatch.setenv('GITHUB_WORKSPACE', str(tmp_path))
    monkeypatch.setenv('RUNNER_TEMP', str(tmp_path/'scratch'))
    monkeypatch.chdir(tmp_path)
    (tmp_path/'sector-radar-run').mkdir()
    if script.startswith('verify'):
        monkeypatch.setitem(scope, 'verify_publication', lambda *args: calls.append(args) or {})
        assert mod['main']() is None
    else:
        monkeypatch.setattr(scope['subprocess'], 'run', lambda *a, **kw: SimpleNamespace(stdout=('a'*40+'\n').encode()))
        monkeypatch.setitem(scope, 'build_delivery', lambda *args, **kw: calls.append((args, kw)))
        assert mod['main']() == 0
    assert len(calls) == 1
    for key, bad in (('GITHUB_REF', 'refs/heads/other'), ('GITHUB_RUN_ATTEMPT', '2'),
                     ('GITHUB_EVENT_NAME', 'push'), ('HITHINK_FINANCE_API_KEY', 'PRIVATE-CANARY')):
        prior = os.environ[key]; monkeypatch.setenv(key, bad)
        if script.startswith('verify'):
            with pytest.raises(ValueError): mod['main']()
        else:
            assert mod['main']() == 2
        assert len(calls) == 1
        monkeypatch.setenv(key, prior)


@pytest.mark.parametrize('event', EVENTS)
@pytest.mark.parametrize('kind', ['same', 'quiet', 'candidates'])
def test_dual_trigger_reuses_original_audited_session_machine(tmp_path, monkeypatch, event, kind):
    from test_sector_radar_audit import execute, resolution, FRIDAY, MONDAY, audit
    activity_module()['require_invocation'](environment(event))
    monkeypatch.setenv('GITHUB_EVENT_NAME', event)
    original = resolution()
    outcome, provider, root = execute(tmp_path, restored=original,
        session=FRIDAY if kind == 'same' else MONDAY, jump=kind == 'candidates')
    ops = outcome.operations
    assert ops.candidate_count == (2 if kind == 'candidates' else 0)
    assert ops.status == {'same': 'VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT',
        'quiet': 'APPENDED_COMPLETED_SESSION_QUIET',
        'candidates': 'APPENDED_COMPLETED_SESSION_WITH_SHADOW_CANDIDATES'}[kind]
    if kind == 'same':
        assert outcome.result is None
        assert outcome.persistent_bundle.market_state == original.market_state
        assert outcome.persistent_bundle.event_ledger == original.event_ledger
    else:
        assert outcome.persistent_bundle.market_state.sessions[:-1] == original.market_state.sessions[1:]
        assert outcome.persistent_bundle.market_state.sessions[-1] == MONDAY
        assert len(outcome.result.composition.surfaced_groups) <= 3
        from decision_kernel.runtime.sector_radar_daily import render_sector_radar_daily_summary
        text = render_sector_radar_daily_summary(outcome.result)
        assert 'qualified-market-change-must-remain-human-discoverable' in text
        assert all(g.primary_candidate.thscode in text for g in outcome.result.composition.all_groups)
    assert ops.human_attention_authority == ops.research_authority == ops.investment_authority == 'NONE'
    assert audit.replay_sector_radar_input_audit(root)['status'] == 'MATCHED_SUCCEEDED'
    assert not (tmp_path/'live-state').exists()  # synthetic fixture cannot publish live


@pytest.mark.parametrize('failure', ['gap', 'provider', '429'])
def test_scheduled_failures_keep_rejected_audit_and_never_publish(tmp_path, monkeypatch, failure):
    from datetime import datetime, time, timedelta
    from test_sector_radar_audit import SyntheticProvider, resolution, hints_json, MONDAY, TUESDAY, TZ, audit
    from decision_kernel.runtime import hithink_http, hithink_index_http, sector_radar_producer as producer
    activity_module()['require_invocation'](environment('schedule'))
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'schedule')
    monkeypatch.setenv('HITHINK_FINANCE_API_KEY', 'fixture-credential-do-not-retain')
    restored = resolution(); session = TUESDAY if failure == 'gap' else MONDAY
    observed = datetime.combine(session, time(18, 13), tzinfo=TZ)
    calls = []; original = SyntheticProvider.__call__
    def response(self, path, params):
        calls.append(path)
        if failure != 'gap' and path == hithink_index_http.HITHINK_INDEX_CATALOG_PATH:
            raise hithink_http.HithinkRuntimeError('synthetic HTTP 429' if failure == '429' else 'synthetic provider failure')
        return original(self, path, params)
    monkeypatch.setattr(SyntheticProvider, '__call__', response)
    transport = SyntheticProvider(restored, session=session)
    class Clock:
        @staticmethod
        def now(tz=None): return observed
    monkeypatch.setattr(producer, 'datetime', Clock)
    monkeypatch.setattr(producer, 'resolve_sector_radar_persistence', lambda **kw: restored)
    def audited(**kwargs):
        return audit.run_audited_sector_radar_producer(**kwargs,
            request_json=transport, provenance=audit.SYNTHETIC_PROVENANCE,
            now=lambda: observed+timedelta(minutes=5), capture_now=lambda: observed)
    monkeypatch.setattr(producer, 'run_audited_sector_radar_producer', audited)
    hints = tmp_path/'hints.json'; hints.write_text(hints_json())
    assert producer.main(['run', '--repository', 'auguspp/decision-kernel',
        '--run-id', '101', '--run-attempt', '1', '--commit-sha', 'a'*40,
        '--prior-success-found', 'true', '--artifact-available', 'true',
        '--parent-hints', str(hints), '--state-directory', str(tmp_path/'live-state'),
        '--output-directory', str(tmp_path/'run')]) == 2
    assert calls.count(hithink_http.HITHINK_CALENDAR_PATH) == 1
    assert calls.count(hithink_index_http.HITHINK_INDEX_CATALOG_PATH) == (0 if failure == 'gap' else 1)
    assert len(calls) == (1 if failure == 'gap' else 2)
    root = tmp_path/'run/input-audit'
    manifest = audit.validate_sector_radar_input_audit(root)
    assert manifest['status'] == 'REJECTED'
    assert not any(p.startswith('expected/state/') for p in manifest['files'])
    ops = json.loads((tmp_path/'run/operations.json').read_text())
    assert ops['status'] == 'FAILED_CLOSED'
    assert ops['output_market_state_hash'] is None
    assert not (tmp_path/'live-state').exists()
    assert audit.replay_sector_radar_input_audit(root)['status'] == 'MATCHED_REJECTED'


def test_metadata_precheck_cannot_read_market_key_or_become_a_scheduler():
    source = (SCRIPTS/'check-sector-scheduled-activity.py').read_text()
    assert 'HITHINK_FINANCE_API_KEY' not in source
    tree = ast.parse(source)
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))
    assert 'sleep(' not in source and '/dispatches' not in source and '/rerun' not in source
    assert 'POST' not in source and 'PUT' not in source
    assert 'sector-radar-run' not in source  # sealed output inventory unchanged
