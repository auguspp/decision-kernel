"""Synthetic source responses, real capture/replay and existing reading composition."""
from copy import deepcopy
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


def fixtures(tmp_path, monkeypatch, *, live=True):
    root = tmp_path/'capture'
    # Simulated native client only: these tests never access a real source.
    monkeypatch.setattr(relay, 'request', make_request())
    report = inputs.capture(root, observed_at=NOW, workflow=IDENTITY,
        request=None if live else make_request(), clock=NOW.isoformat)
    files = {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    run = {'id':123, 'display_title':inputs.TITLE, 'path':inputs.WORKFLOW, 'head_branch':'main',
        'event':'workflow_dispatch','run_attempt':1,'head_sha':'a'*40,'status':'completed', 'conclusion':'success',
        'created_at':NOW.isoformat(), 'updated_at':NOW.isoformat(), 'run_started_at':NOW.isoformat(),
        'html_url':'https://github.com/auguspp/decision-kernel/actions/runs/123',
        'repository':{'full_name':'auguspp/decision-kernel'}, 'head_repository':{'full_name':'auguspp/decision-kernel'}}
    artifact = {'name':inputs.TITLE+'-123-1','expired':False,'expires_at':'2026-11-01T00:00:00Z'}
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
