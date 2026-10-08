"""Synthetic source responses, real capture/replay and existing reading composition."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import json

import pytest
import yaml

from decision_kernel.runtime import stock_market_inputs as inputs
from decision_kernel.runtime import stock_market_input_reading as reader
from decision_kernel.runtime import independent_stock_reading as independent
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import tushare_relay as relay
from test_stock_market_inputs import NOW, make_request, calendar_body


IDENTITY = {'GITHUB_REPOSITORY':'auguspp/decision-kernel', 'GITHUB_REF':'refs/heads/main',
    'GITHUB_RUN_ATTEMPT':'1', 'GITHUB_JOB':'daily-market-inputs', 'GITHUB_EVENT_NAME':'workflow_dispatch',
    'GITHUB_WORKFLOW_REF':'auguspp/decision-kernel/'+inputs.WORKFLOW+'@refs/heads/main',
    'GITHUB_SHA':'a'*40, 'GITHUB_RUN_ID':'123'}


def fixtures(tmp_path, monkeypatch, *, live=True, run_id=123, at=NOW, fail=None, sparse_60_factor=False):
    root = tmp_path/f'capture-{run_id}'
    # Simulated native client only: these tests never access a real source.
    fetch = make_request(at, fail=fail)
    def native_request(api, params, *, retry_waits, deadline):
        assert retry_waits == (30, 90) and isinstance(deadline, float)
        response = fetch(api, params)
        if sparse_60_factor and api == 'adj_factor':
            base = inputs.calendar(calendar_body(at), at)['bases']['60']
            if params['trade_date'] == base:
                original = json.loads(response['attempts'][-1]['raw'])
                original['data']['items'] = []
                response['attempts'][-1]['raw'] = inputs.dumps(original)
        return response
    monkeypatch.setattr(relay, 'request', native_request)
    identity = {**IDENTITY, 'GITHUB_RUN_ID': str(run_id)}
    report = inputs.capture(root, observed_at=at, workflow=identity,
        request=None if live else fetch, clock=at.isoformat)
    files = {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    run = {'id':run_id, 'display_title':inputs.TITLE, 'path':inputs.WORKFLOW, 'head_branch':'main',
        'event':'workflow_dispatch','run_attempt':1,'head_sha':'a'*40,'status':'completed', 'conclusion':'success',
        'created_at':at.isoformat(), 'updated_at':at.isoformat(), 'run_started_at':at.isoformat(),
        'html_url':f'https://github.com/auguspp/decision-kernel/actions/runs/{run_id}',
        'repository':{'full_name':'auguspp/decision-kernel'}, 'head_repository':{'full_name':'auguspp/decision-kernel'}}
    artifact = {'name':f'{inputs.TITLE}-{run_id}-1','expired':False,'expires_at':'2026-11-01T00:00:00Z'}
    api = SimpleNamespace(calls=0,max_calls=180)
    def get(path):
        assert path == 'actions/workflows/stock-reading-after-sector.yml/runs?branch=main&per_page=100'
        api.calls += 1
        return {'workflow_runs':[run], 'total_count':1}
    api.get = get
    collector = SimpleNamespace(api=api, files={'README.md':b'old'}, archive_cache={}, code_commit='a'*40)
    collector.artifacts = lambda r:[artifact]
    collector.archive = lambda a,r:(files, {'artifact_id':99})
    def retain(path, raw):
        collector.files[path] = raw
        return {'read_path':path,'sha256':model.sha256(raw),'git_blob':model.blob_sha(raw),'bytes':len(raw),
                'read_ref_rule':'USE_THE_SAME_PINNED_READING_COMMIT'}
    collector.retain = retain
    baseline = {'checks':{'finished_at':NOW.isoformat()}, 'lanes':{'sector':{'latest_attempt':{'conclusion':'failure'}}}}
    return collector, baseline, files, run, report


def test_reader_rebuilds_normal_file_even_when_sector_is_failed(tmp_path, monkeypatch):
    collector, baseline, files, run, report = fixtures(tmp_path, monkeypatch)
    result = reader.read_current(collector, baseline)
    assert result['status'] == 'PRICE_INPUTS_AVAILABLE_WITH_GAPS'
    assert result['cohort_denominator'] == 2 and result['new_source_requests'] == 0
    assert json.loads(collector.files[reader.PATH]) == report
    assert result['file']['sha256'] == model.sha256(collector.files[reader.PATH])


def test_failed_sibling_does_not_poison_successful_stock_bytes(tmp_path, monkeypatch):
    collector, baseline, files, run, report = fixtures(tmp_path, monkeypatch)
    run['conclusion'] = 'failure'
    assert reader.read_current(collector, baseline)['cohort_denominator'] == 2


def test_synthetic_transport_cannot_be_published_as_live(tmp_path, monkeypatch):
    collector, baseline, files, run, report = fixtures(tmp_path, monkeypatch, live=False)
    result = reader.read_current(collector, baseline)
    assert result['status'] == 'DAILY_INPUT_READING_GAP_NOT_QUIET'
    assert reader.PATH not in collector.files


def test_bad_current_source_is_not_replaced_by_older_success(tmp_path, monkeypatch):
    collector, baseline, files, run, report = fixtures(tmp_path, monkeypatch)
    files['report.json'] = b'{}'
    result = reader.read_current(collector, baseline)
    assert result['status'] == 'DAILY_INPUT_READING_GAP_NOT_QUIET'
    assert collector.files == {'README.md':b'old'}
    assert collector.api.calls == 1


def test_pending_run_does_not_claim_saved_data_are_current(tmp_path, monkeypatch):
    collector, baseline, files, run, report = fixtures(tmp_path, monkeypatch)
    run['status'] = 'in_progress'
    assert reader.read_current(collector, baseline)['status'] == 'DAILY_INPUT_ATTEMPT_PENDING'
    assert reader.PATH not in collector.files


def test_normal_independent_entry_reaches_daily_input_without_sector(tmp_path, monkeypatch):
    collector, baseline, files, run, report = fixtures(tmp_path, monkeypatch)
    monkeypatch.setenv('INCLUDE_CURRENT_STOCK_INPUTS','1')
    result = independent.derive(collector, baseline)
    assert result['historical_sample_status'] == 'INPUT_UNAVAILABLE_NOT_QUIET'
    assert result['daily_market_inputs']['cohort_denominator'] == 2
    assert result['status'] == 'PRICE_INPUTS_AVAILABLE_WITH_GAPS'
    assert result['preferred_current_input'] == 'daily_market_inputs'
    assert result['observations'] is None


def test_existing_clock_and_publisher_are_wired_without_sector_needs():
    root = Path(__file__).resolve().parents[1]
    source = yaml.safe_load((root/inputs.WORKFLOW).read_text())
    job = source['jobs']['daily-market-inputs']
    assert 'needs' not in job
    assert "github.event.schedule == '35 10 * * 1-5'" in job['if']
    assert "inputs.mode == 'market-inputs'" in job['if']
    assert "GITHUB_SHA" in str(job['steps'])
    publisher = yaml.safe_load((root/'.github/workflows/current-state-read-entry.yml').read_text())
    event = publisher.get('on', publisher.get(True))
    assert 'stock-reading-after-sector' in event['workflow_run']['workflows']
    steps = publisher['jobs']['publish-reading']['steps']
    assert any(s.get('env',{}).get('INCLUDE_CURRENT_STOCK_INPUTS') == '1' for s in steps)


def test_direct_live_call_requires_exact_workflow_before_any_request(tmp_path):
    with pytest.raises(ValueError, match='EXECUTION_IDENTITY'):
        inputs.capture(tmp_path/'blocked', observed_at=NOW, workflow={})
    assert not (tmp_path/'blocked').exists()


def test_raw_mutation_rejected_before_rebuild(tmp_path, monkeypatch):
    collector, baseline, files, run, report = fixtures(tmp_path, monkeypatch)
    name = next(n for n in files if n.startswith('raw/'))
    files[name] += b' '
    assert reader.read_current(collector, baseline)['status'] == 'DAILY_INPUT_READING_GAP_NOT_QUIET'


def test_full_cross_section_fits_normal_detail_budget():
    context = inputs.calendar(calendar_body(), NOW)
    tables = {}
    for item in inputs.price_plan(context):
        field = 'close' if item['api'] == 'daily' else 'adj_factor'
        tables[item['api'], item['params']['trade_date']] = {
            f'{i:06d}.SH':{field:'12.12' if field == 'close' else '1.023'} for i in range(6000)}
    report = inputs.evaluate(context, tables, {})
    assert report['cohort_denominator'] == 6000
    assert report['qualified_windows'] == {'5':6000,'20':6000,'60':6000}
    assert len(inputs.dumps(report)) < inputs.MAX_REPORT


def two_runs(tmp_path, monkeypatch, *, latest_state='failed', saved_live=True):
    old = fixtures(tmp_path, monkeypatch, live=saved_live)
    end = inputs.calendar(calendar_body(), NOW)['end_date']
    latest = fixtures(tmp_path, monkeypatch, run_id=124, at=NOW+timedelta(hours=1),
                      fail=('daily', end) if latest_state == 'failed' else None,
                      sparse_60_factor=latest_state == 'sparse_60_factor')
    collector, baseline, files, run, report = latest
    if latest_state == 'failed':
        run['conclusion'] = 'failure'
    elif latest_state == 'pending':
        run['status'] = 'in_progress'
    elif latest_state == 'corrupt':
        files['report.json'] = b'{}'
    baseline['checks']['finished_at'] = (NOW+timedelta(hours=2)).isoformat()
    def get(path):
        collector.api.calls += 1
        return {'workflow_runs':[run, old[3]], 'total_count':2}
    collector.api.get = get
    artifacts = {r[3]['id']:r[0].artifacts(r[3]) for r in (old, latest)}
    archives = {r[3]['id']:r[2] for r in (old, latest)}
    reads = []
    collector.artifacts = lambda r:artifacts[r['id']]
    def archive(a, r):
        reads.append(r['id'])
        collector.files[f'archive-{r["id"]}'] = b'original'
        return archives[r['id']], {'artifact_id':r['id']}
    collector.archive = archive
    return collector, baseline, latest, old, artifacts, reads


@pytest.mark.parametrize('state', ['failed', 'pending', 'corrupt'])
def test_latest_gap_keeps_separate_verified_saved_input(tmp_path, monkeypatch, state):
    collector, baseline, latest, old, artifacts, reads = two_runs(tmp_path, monkeypatch, latest_state=state)
    monkeypatch.setenv('INCLUDE_CURRENT_STOCK_INPUTS','1')
    result = independent.derive(collector, baseline)
    current = result['daily_market_inputs']
    saved = current['last_qualified_result']
    assert current['latest_attempt']['id'] == 124 and result['status'] == current['status']
    assert current['status'] != old[4]['status']
    assert saved['origin_run']['id'] == 123 and saved['received_through'] == NOW.isoformat()
    assert saved['market_session'] == '2026-09-30' and saved['cohort_denominator'] == 2
    assert saved['qualified_windows'] == {'5':1,'20':1,'60':1}
    assert saved['new_source_requests'] == 0 and saved['investment_authority'] == 'NONE'
    assert json.loads(collector.files[reader.LAST_PATH]) == old[4]
    assert saved['file']['sha256'] == model.sha256(collector.files[reader.LAST_PATH])
    assert '最近已验证可用输入' in result['summary'] and reader.LAST_PATH in result['summary']
    if state == 'failed':
        assert json.loads(collector.files[reader.PATH]) == latest[4]
        assert current['cohort_denominator'] == 0
    else:
        assert reader.PATH not in collector.files


@pytest.mark.parametrize('fault', ['expired', 'corrupt', 'synthetic', 'wrong_identity'])
def test_saved_candidate_rejected_without_erasing_latest_failure_or_searching_older(tmp_path, monkeypatch, fault):
    collector, baseline, latest, old, artifacts, reads = two_runs(
        tmp_path, monkeypatch, saved_live=fault != 'synthetic')
    if fault == 'expired':
        artifacts[123][0]['expires_at'] = '2026-10-02T00:00:00Z'
    elif fault == 'corrupt':
        old[2]['report.json'] = b'{}'
    elif fault == 'wrong_identity':
        old[3]['head_sha'] = 'b'*40
    older = {**old[3], 'id':122, 'created_at':(NOW-timedelta(hours=1)).isoformat()}
    collector.api.get = lambda path:{'workflow_runs':[latest[3],old[3],older], 'total_count':3}
    result = reader.read_current(collector, baseline)
    assert result['status'] == latest[4]['status']
    assert result['last_qualified_reading_gap']['origin_run']['id'] == 123
    assert 'last_qualified_result' not in result and reader.LAST_PATH not in collector.files
    assert json.loads(collector.files[reader.PATH]) == latest[4]
    assert 'archive-123' not in collector.files and 122 not in reads


def test_usable_latest_never_replaced_to_improve_coverage(tmp_path, monkeypatch):
    collector, baseline, latest, old, artifacts, reads = two_runs(tmp_path, monkeypatch, latest_state='success')
    result = reader.read_current(collector, baseline)
    assert result['qualified_windows'] == latest[4]['qualified_windows']
    assert 'last_qualified_result' not in result and reader.LAST_PATH not in collector.files
    assert reads == [124]


def test_sparse_60day_factor_can_show_separate_qualified_old_window(tmp_path, monkeypatch):
    collector, baseline, latest, old, _, reads = two_runs(
        tmp_path, monkeypatch, latest_state='sparse_60_factor')
    result = reader.read_current(collector, baseline)
    base = inputs.calendar(calendar_body(), NOW)['bases']['60']
    assert result['qualified_windows'] == {'5': 1, '20': 1, '60': 0}
    assert result['source_coverage_attention'] == [{
        'window': '60', 'base_date': base, 'price_rows': 1, 'factor_rows': 0,
        'status': 'FACTOR_ROWS_FEWER_THAN_DATE_PRICE_ROWS'}]
    saved = result['last_qualified_result']
    assert saved['qualified_windows'] == {'5': 1, '20': 1, '60': 1}
    assert saved['selection_reason'] == 'SAME_SESSION_WINDOW_COVERAGE_IMPROVEMENT'
    assert saved['origin_run']['id'] == 123 and result['latest_attempt']['id'] == 124
    assert json.loads(collector.files[reader.PATH]) == latest[4]
    assert json.loads(collector.files[reader.LAST_PATH]) == old[4]
    assert reads == [124, 123]
    assert '两批证券/因子不拼接' in result['summary']


def test_partial_factor_bad_saved_candidate_is_not_masked(tmp_path, monkeypatch):
    collector, baseline, latest, old, _, _ = two_runs(
        tmp_path, monkeypatch, latest_state='sparse_60_factor')
    old[2]['report.json'] = b'{}'
    result = reader.read_current(collector, baseline)
    assert result['qualified_windows'] == {'5': 1, '20': 1, '60': 0}
    assert 'last_qualified_result' not in result
    assert result['last_qualified_reading_gap']['status'] == 'SAVED_INPUT_UNAVAILABLE'
    assert json.loads(collector.files[reader.PATH]) == latest[4]
    assert reader.LAST_PATH not in collector.files



def _factor_history_runs(tmp_path, monkeypatch, *, bad_middle=False):
    """Three eligible archived runs, and a new partial one, on one market day."""
    older = fixtures(tmp_path, monkeypatch, run_id=121, at=NOW)
    middle = fixtures(tmp_path, monkeypatch, run_id=122, at=NOW+timedelta(minutes=10),
                      sparse_60_factor=True)
    near = fixtures(tmp_path, monkeypatch, run_id=123, at=NOW+timedelta(minutes=20),
                    sparse_60_factor=True)
    latest = fixtures(tmp_path, monkeypatch, run_id=124, at=NOW+timedelta(minutes=30),
                      sparse_60_factor=True)
    collector, baseline, _, _, _ = latest
    baseline['checks']['finished_at'] = (NOW+timedelta(hours=1)).isoformat()
    group = [latest, near, middle, older]
    if bad_middle:
        middle[2]['report.json'] = b'{}'
    collector.api.get = lambda path: {
        'workflow_runs': [item[3] for item in group], 'total_count': len(group)}
    archives = {item[3]['id']:item[2] for item in group}
    artifacts = {item[3]['id']:item[0].artifacts(item[3]) for item in group}
    collector.artifacts = lambda run:artifacts[run['id']]
    reads = []
    def archive(artifact, run):
        reads.append(run['id'])
        return archives[run['id']], {'artifact_id':run['id']}
    collector.archive = archive
    return collector, group, reads


def test_bounded_previous_verified_factor_coverage_recovers_third_older_good(tmp_path, monkeypatch):
    collector, group, reads = _factor_history_runs(tmp_path, monkeypatch)
    result = reader.read_current(collector, {'checks':{'finished_at':
        (NOW+timedelta(hours=1)).isoformat()}})
    assert reads == [124, 123, 122, 121]
    assert result['qualified_windows'] == {'5':1, '20':1, '60':0}
    assert result['last_qualified_result']['qualified_windows'] == {'5':1, '20':1, '60':1}
    assert result['last_qualified_result']['origin_run']['id'] == 121
    assert [x['status'] for x in result['last_qualified_checks']] == [
        'VALID_BUT_NOT_BETTER', 'VALID_BUT_NOT_BETTER', 'QUALIFIED_REFERENCE_SELECTED']
    assert json.loads(collector.files[reader.PATH]) == group[0][4]
    assert json.loads(collector.files[reader.LAST_PATH]) == group[3][4]


def test_bounded_recovery_does_not_jump_past_corrupt_candidate(tmp_path, monkeypatch):
    collector, group, reads = _factor_history_runs(tmp_path, monkeypatch, bad_middle=True)
    result = reader.read_current(collector, {'checks':{'finished_at':
        (NOW+timedelta(hours=1)).isoformat()}})
    assert reads == [124, 123, 122]
    assert result['last_qualified_checks'][0]['status'] == 'VALID_BUT_NOT_BETTER'
    assert result['last_qualified_checks'][1]['status'] == 'SAVED_INPUT_UNAVAILABLE_STOP'
    assert 'last_qualified_result' not in result
    assert reader.LAST_PATH not in collector.files
