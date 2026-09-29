"""B1 joins actual saved-archive machinery; all prices/transport here are synthetic."""
from copy import deepcopy
import json
import socket
from pathlib import Path

import pytest

from decision_kernel.runtime import current_state as m, global_market_context as g
from decision_kernel.runtime import global_market_reading as r
from test_external_radar_reading import setup, pack
from test_global_market_context import IDENTITY, ASOF, NOW, KEY, request_fixture, saved

CHECKED = '2026-09-27T08:30:00Z'
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail('B1 reading attempted external networking')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def ready(tmp_path, monkeypatch, *, legacy=False, event='workflow_dispatch'):
    c, baseline, _ = setup(monkeypatch)
    c.now = lambda: CHECKED
    c.previous = c.previous_commit = None
    monkeypatch.setenv(g.relay.SECRET_ENV, KEY)
    records = {}
    for family, run_id in [('indices', 901), ('shibor', 902)]:
        identity = {**IDENTITY, 'run_id': run_id, 'event': event}
        request, _, _ = request_fixture()
        root = tmp_path / family
        report = g.capture(root, identity, family, ASOF, request=request, now=lambda: NOW)
        files = saved(root)
        run = {'id': run_id, 'path': g.WORKFLOW, 'head_sha': identity['code_commit'],
               'head_branch': 'main', 'repository': {'full_name': m.REPOSITORY},
               'head_repository': {'full_name': m.REPOSITORY}, 'event': event,
               'run_attempt': 1, 'status': 'completed', 'conclusion': 'success',
               'created_at': '2026-09-27T07:59:00Z', 'updated_at': '2026-09-27T08:01:00Z',
               'display_title': 'radar-global-market' if legacy else 'global-market / ' + family}
        raw = pack(files)
        art_id = run_id + 1000
        artifact = {'id': art_id, 'name': f'global-market-{family}-{run_id}-1', 'expired': False,
                    'size_in_bytes': len(raw), 'digest': 'sha256:' + m.sha256(raw),
                    'workflow_run': {'id': run_id, 'head_sha': identity['code_commit']}}
        c.api.responses['actions/runs/' + str(run_id)] = run
        c.api.responses[f'actions/runs/{run_id}/artifacts?per_page=100'] = {'total_count': 1, 'artifacts': [artifact]}
        c.api.archives[art_id] = raw
        records[family] = (run, artifact, files, report)
    c.api.responses[r.QUERY] = {'total_count': 2, 'workflow_runs': [records[f][0] for f in g.FAMILIES]}
    monkeypatch.delenv(g.relay.SECRET_ENV)
    return c, baseline, records


def previous(c, payload):
    files = dict(c.files)
    c.previous, c.previous_commit = deepcopy(payload), 'b' * 40
    c.files = {'README.md': b'Original entry\n', 'current-state.json': m.read_package_bytes(payload)}
    c.archive_cache = {}
    c.api.calls = 0
    c.api.reads.clear()
    def file(path, ref):
        c.api.calls += 1
        c.api.reads.append(('file', path, ref))
        assert ref == 'b' * 40
        return files[path]
    c.api.file = file
    return files


def projection(c):
    return json.loads(c.files[r.REPORT])['projection']


@pytest.mark.parametrize('event', ['workflow_dispatch', 'schedule'])
def test_two_families_replay_original_archives_in_same_R(tmp_path, monkeypatch, event):
    c, baseline, records = ready(tmp_path, monkeypatch, event=event)
    old, old_files = deepcopy(baseline), dict(c.files)
    payload = r.attach(c, baseline)
    m.validate_read_package(payload)
    p = projection(c)
    assert payload['research']['global_market']['status'] == 'SAVED_CONTEXT'
    assert p['families']['indices']['snapshot']['report']['available_values'] == 6
    assert p['families']['shibor']['snapshot']['report']['available_values'] == 8
    for family in g.FAMILIES:
        snap = p['families'][family]['snapshot']
        assert c.files[snap['archive']['read_path']] == c.api.archives[records[family][1]['id']]
        assert snap['report'] == records[family][3]
    assert baseline == old and payload['lanes'] == old['lanes']
    assert p['source_calls'] == 0 and not p['complete_global_coverage']
    assert all(payload['research'][k] == v for k, v in old['research'].items())
    for name, raw in old_files.items():
        if name not in {'README.md', 'current-state.json'}:
            assert c.files[name] == raw
    assert b'ORIGINAL_COMPANY_CONCEPT_NAV' in c.files['README.md']
    assert '不是美债' in c.files[r.DETAIL].decode()


def test_legacy_runs_are_identified_from_exact_artifact_names(tmp_path, monkeypatch):
    c, baseline, _ = ready(tmp_path, monkeypatch, legacy=True)
    r.attach(c, baseline)
    p = projection(c)
    assert not p['query']['unattributed_run_ids']
    assert all(p['families'][f]['snapshot'] for f in g.FAMILIES)
    assert sum(isinstance(x, str) and '/artifacts?' in x for x in c.api.reads) == 2


def test_latest_failure_preserves_old_bytes_not_new_success(tmp_path, monkeypatch):
    c, baseline, records = ready(tmp_path, monkeypatch)
    first = r.attach(c, baseline)
    prior_files = previous(c, first)
    failed = {**deepcopy(records['indices'][0]), 'id': 903, 'conclusion': 'failure',
              'created_at': '2026-09-27T08:10:00Z', 'updated_at': '2026-09-27T08:15:00Z'}
    c.api.responses[r.QUERY]['workflow_runs'].insert(0, failed)
    c.api.responses[r.QUERY]['total_count'] = 3
    c.api.responses['actions/runs/903'] = failed
    c.api.responses['actions/runs/903/artifacts?per_page=100'] = {'total_count': 0, 'artifacts': []}
    result = r.attach(c, first)
    state = projection(c)['families']['indices']
    assert state['latest_attempt']['id'] == 903 and state['latest_attempt']['conclusion'] == 'failure'
    assert state['latest_read_status'] == 'CAPTURE_UNAVAILABLE_OR_REJECTED'
    assert state['snapshot']['run']['id'] == 901
    assert state['snapshot']['report']['outcomes'][0]['observations'][0]['source_date'] == '2026-09-25'
    assert c.files[state['snapshot']['archive']['read_path']] == prior_files[state['snapshot']['archive']['read_path']]
    assert projection(c)['families']['shibor']['latest_read_status'] == 'REUSED_RETAINED_CAPTURE'
    assert result['lanes'] == first['lanes']


def test_saved_Git_copy_survives_Actions_artifact_expiry(tmp_path, monkeypatch):
    c, baseline, records = ready(tmp_path, monkeypatch)
    first = r.attach(c, baseline)
    previous(c, first)
    for _, artifact, _, _ in records.values():
        artifact['expired'] = True
    c.now = lambda: '2026-11-01T08:30:00Z'
    r.attach(c, first)
    p = projection(c)
    assert all(p['families'][f]['latest_read_status'] == 'REUSED_RETAINED_CAPTURE' for f in g.FAMILIES)
    assert not any(isinstance(x, tuple) and x[0] == 'archive' for x in c.api.reads)
    assert all(p['families'][f]['snapshot']['report']['captured_through'] == NOW for f in g.FAMILIES)
    assert all(p['families'][f]['snapshot']['artifact_at_read']['expired'] is False for f in g.FAMILIES)


@pytest.mark.parametrize('damage', ['raw', 'summary', 'family', 'extra-file', 'expired'])
def test_bad_one_family_does_not_erase_other_family(tmp_path, monkeypatch, damage):
    c, baseline, records = ready(tmp_path, monkeypatch)
    run, artifact, files, _ = records['indices']
    if damage == 'expired':
        artifact['expired'] = True
    else:
        if damage == 'raw': files['raw-00-1.json'] += b'x'
        if damage == 'summary': files['summary.json'] += b' '
        if damage == 'family': files['capture.json'] = records['shibor'][2]['capture.json']
        if damage == 'extra-file': files['execute.py'] = b'raise RuntimeError("never execute")'
        raw = pack(files)
        c.api.archives[artifact['id']] = raw
        artifact.update(size_in_bytes=len(raw), digest='sha256:' + m.sha256(raw))
    r.attach(c, baseline)
    p = projection(c)
    assert p['families']['indices']['snapshot'] is None
    assert p['families']['indices']['latest_read_status'] == 'CAPTURE_UNAVAILABLE_OR_REJECTED'
    assert p['families']['shibor']['snapshot']['report']['available_values'] == 8


@pytest.mark.parametrize('change,status', [({'status': 'in_progress', 'conclusion': None}, 'CAPTURE_IN_PROGRESS'),
                                           ({'run_attempt': 2}, 'RERUN_NOT_ADMITTED')])
def test_pending_and_rerun_are_not_source_success(tmp_path, monkeypatch, change, status):
    c, baseline, records = ready(tmp_path, monkeypatch)
    records['indices'][0].update(change)
    r.attach(c, baseline)
    state = projection(c)['families']['indices']
    assert state['latest_read_status'] == status and state['snapshot'] is None


def test_query_failure_retains_previous_and_does_not_assert_quiet(tmp_path, monkeypatch):
    c, baseline, _ = ready(tmp_path, monkeypatch)
    first = r.attach(c, baseline)
    previous(c, first)
    del c.api.responses[r.QUERY]
    r.attach(c, first)
    p = projection(c)
    assert p['query']['status'] == 'QUERY_UNAVAILABLE'
    assert all(p['families'][f]['snapshot'] for f in g.FAMILIES)
    assert all(p['families'][f]['latest_read_status'] == 'QUERY_UNAVAILABLE' for f in g.FAMILIES)


def test_unattributable_run_is_explicit_not_assigned_to_both(tmp_path, monkeypatch):
    c, baseline, records = ready(tmp_path, monkeypatch)
    unknown = {**deepcopy(records['indices'][0]), 'id': 999, 'display_title': 'radar-global-market',
               'status': 'in_progress', 'conclusion': None, 'created_at': '2026-09-27T08:20:00Z',
               'updated_at': '2026-09-27T08:25:00Z'}
    c.api.responses[r.QUERY]['workflow_runs'].insert(0, unknown)
    c.api.responses[r.QUERY]['total_count'] = 3
    c.api.responses['actions/runs/999/artifacts?per_page=100'] = {'total_count': 0, 'artifacts': []}
    r.attach(c, baseline)
    assert projection(c)['query']['unattributed_run_ids'] == [999]
    assert all(projection(c)['families'][f]['latest_attempt']['id'] != 999 for f in g.FAMILIES)


def test_no_run_does_not_create_zero_market_values(tmp_path, monkeypatch):
    c, baseline, _ = ready(tmp_path, monkeypatch)
    c.api.responses[r.QUERY] = {'total_count': 0, 'workflow_runs': []}
    result = r.attach(c, baseline)
    assert result['research']['global_market']['status'] == 'UNAVAILABLE'
    assert all(projection(c)['families'][f]['snapshot'] is None for f in g.FAMILIES)


def test_original_entry_and_publisher_opt_in_no_source_rerun():
    entry = (ROOT/'src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py').read_text()
    assert 'parser.add_argument("--include-global-market", action="store_true")' in entry
    assert 'collector.include_global_market = args.include_global_market' in entry
    assert 'getattr(self, "include_global_market", False)' in entry
    workflow = (ROOT/'.github/workflows/current-state-read-entry.yml').read_text()
    assert '--include-global-market' in workflow and 'radar-global-market' in workflow
    producer = (ROOT/'.github/workflows/radar-global-market.yml').read_text()
    assert "run-name: global-market / ${{ inputs.family ||" in producer
    assert "github.event.schedule == '17 0 * * *' && 'indices'" in producer
    assert "github.event.schedule == '37 0 * * *' && 'shibor'" in producer
    assert 'schedule:' in producer and 'TUSHARE_PROXY_API_KEY' in producer
    assert 'workflow_dispatch:' in producer
