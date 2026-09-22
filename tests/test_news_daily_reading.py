"""New native-source reading through the existing Collector and ZIP verifier."""
from copy import deepcopy
import json

import pytest

from decision_kernel.runtime import current_state as m, news_daily as s, news_daily_reading as r
from test_external_radar_reading import setup, pack
from test_news_daily import captured, IDENTITY, TIME, no_network

QUERY = 'actions/workflows/radar-newsnow-daily.yml/runs?branch=main&per_page=20'


def ready(tmp_path, monkeypatch):
    col, baseline, _ = setup(monkeypatch)
    _, files, result = captured(tmp_path)
    run = {'id': 901, 'head_sha': IDENTITY['code_commit'], 'head_branch': 'main', 'path': s.WORKFLOW,
           'repository': {'full_name': m.REPOSITORY}, 'head_repository': {'full_name': m.REPOSITORY},
           'event': IDENTITY['event'], 'run_attempt': 1, 'status': 'completed', 'conclusion': 'success',
           'created_at': '2026-09-20T03:55:00Z', 'updated_at': '2026-09-20T04:10:00Z'}
    col.api.responses[QUERY] = {'total_count': 1, 'workflow_runs': [run]}
    col.api.responses['actions/runs/901'] = run
    raw = pack(files)
    artifact = {'id': 991, 'name': 'newsnow-daily-901-1', 'expired': False,
                'size_in_bytes': len(raw), 'digest': 'sha256:' + m.sha256(raw),
                'workflow_run': {'id': 901, 'head_sha': IDENTITY['code_commit']}}
    col.api.responses['actions/runs/901/artifacts?per_page=100'] = {'total_count': 1, 'artifacts': [artifact]}
    col.api.archives[991] = raw
    return col, baseline, run, artifact, files


def test_native_read_replays_bytes_and_preserves_existing_research(tmp_path, monkeypatch):
    col, baseline, _, _, files = ready(tmp_path, monkeypatch)
    before, before_files = deepcopy(baseline), dict(col.files)
    result = r.attach(col, baseline)
    assert result['research']['daily_news']['status'] == 'WINDOWS_CAPTURED'
    m.validate_read_package(result)
    assert baseline == before and result['lanes'] == before['lanes']
    assert result['research']['radar_discovery'] == before['research']['radar_discovery']
    report = json.loads(col.files[r.REPORT])['projection']
    news = report['capture']['projection']['news']['projection']
    assert len(news['observations']) == 7 and len(news['companies']) == 1
    assert news['companies'][0]['question_status'] == 'NOT_FORMED'
    assert report['semantic_review'] == 'NOT_PERFORMED'
    assert report['research_executions'] == report['new_attention_events'] == 0
    archive = report['state']['archive']; assert col.files[archive['read_path']] == col.api.archives[991]
    for name, raw in before_files.items():
        if name not in {'README.md', 'current-state.json'}: assert col.files[name] == raw
    assert b'ORIGINAL_COMPANY_CONCEPT_NAV' in col.files['README.md']
    assert '<script>' not in col.files[r.DETAIL].decode()
    assert col.api.calls == 4


@pytest.mark.parametrize('damage', ['expired', 'digest', 'head', 'attempt', 'repo', 'event', 'future', 'projection'])
def test_native_bad_identity_rejects_without_erasing_other_lanes(tmp_path, monkeypatch, damage):
    col, baseline, run, artifact, files = ready(tmp_path, monkeypatch)
    if damage == 'expired': artifact['expired'] = True
    elif damage == 'digest': artifact['digest'] = 'sha256:'+'0'*64
    elif damage == 'head': run['head_sha'] = 'f'*40
    elif damage == 'attempt': run['run_attempt'] = 2
    elif damage == 'repo': run['head_repository'] = {'full_name':'other/repo'}
    elif damage == 'event': run['event'] = 'push'
    elif damage == 'future': run['updated_at'] = '2027-01-01T00:00:00Z'
    else:
        report=json.loads(files['observations.json']); report['projection']['status']='FALSE_SUCCESS'
        files['observations.json']=m.json_bytes(report); raw=pack(files)
        col.api.archives[991]=raw; artifact.update(size_in_bytes=len(raw), digest='sha256:'+m.sha256(raw))
    result = r.attach(col, baseline)
    assert result['research']['daily_news']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert result['lanes'] == baseline['lanes'] and 'details' not in result['research']['daily_news']
    assert result['research']['daily_news']['meaning'] == 'NEWS_READ_GAP_NOT_NO_NEWS'


def test_latest_failed_attempt_does_not_fall_back_to_older_success(tmp_path, monkeypatch):
    col, baseline, run, _, _ = ready(tmp_path, monkeypatch)
    failed = {**deepcopy(run), 'id': 902, 'conclusion': 'failure',
              'created_at':'2026-09-20T04:20:00Z', 'updated_at':'2026-09-20T04:25:00Z'}
    col.api.responses[QUERY] = {'total_count': 2, 'workflow_runs': [failed, run]}
    col.api.responses['actions/runs/902'] = failed
    result = r.attach(col, baseline)
    assert result['research']['daily_news']['status'] == 'LATEST_ATTEMPT_NOT_SUCCESSFUL'
    assert ('archive', 991) not in col.api.reads and 'actions/runs/901' not in col.api.reads


def test_no_run_and_stale_window_are_not_quiet(tmp_path, monkeypatch):
    col, baseline, _, _, _ = ready(tmp_path, monkeypatch)
    col.now = lambda: '2026-09-22T04:30:00Z'
    result = r.attach(col, baseline)
    assert result['research']['daily_news']['status'] == 'STALE_CAPTURE_NOT_TODAY_NEWS'
    assert '2026-09-20' in col.files[r.DETAIL].decode()
    col, baseline, _, _, _ = ready(tmp_path/'again', monkeypatch)
    col.api.responses[QUERY] = {'total_count':0, 'workflow_runs':[]}
    result = r.attach(col, baseline)
    assert result['research']['daily_news']['status'] == 'NOT_RUN'
    assert result['research']['daily_news']['meaning'] == 'NOT_NO_NEWS'


def test_unreadable_company_context_does_not_erase_verified_windows(tmp_path, monkeypatch):
    col, baseline, _, _, _ = ready(tmp_path, monkeypatch)
    ref = baseline['research']['radar_discovery']['details']['company_reading']
    col.files[ref['read_path']] += b'corrupt'
    result = r.attach(col, baseline)
    state = result['research']['daily_news']
    assert state['status'] == 'WINDOWS_CAPTURED'
    assert state['company_context_status'] == 'COMPANY_READING_UNAVAILABLE_OR_REJECTED'
    p = json.loads(col.files[r.REPORT])['projection']['capture']['projection']['news']['projection']
    assert len(p['observations']) == 7 and not p['companies']


def test_budget_failure_does_not_issue_new_get_or_delete_existing_files(tmp_path, monkeypatch):
    col, baseline, _, _, _ = ready(tmp_path, monkeypatch)
    col.api.calls = col.api.max_calls
    before = dict(col.files)
    with pytest.raises(ValueError): r.attach(col, baseline)
    assert col.api.reads == [] and col.files == before
