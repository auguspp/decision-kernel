"""Synthetic joins/replay and publication isolation; no live financial claims."""
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import socket
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import current_state_delivery as d
from decision_kernel.runtime import current_state_delivery_with_odds_watch as entry
from decision_kernel.runtime import institutional_radar_capture as capture
from decision_kernel.runtime import institutional_radar_reading as r
from decision_kernel.runtime import radar_company_reading as c
from test_institutional_radar import fixtures, raw, NOW, DAY, project
from test_radar_stock_candidates import source

SHA = 'a' * 40
AT = '2026-09-18T04:00:00+00:00'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('unexpected network request')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)


def baseline(collector, sector=None):
    sector = source(groups=4, leaders=1) if sector is None else sector
    ref = collector.retain('details/sector/10/result.json', m.json_bytes(sector))
    lanes = {name: {'health': 'SAVED', 'gaps': [], 'last_qualified_result': None} for name in m.WORKFLOWS}
    lanes['sector']['last_qualified_result'] = {'market_session': DAY, 'status': 'SAVED',
        'market_state_hash': sector['output_market_state_hash'],
        'event_ledger_hash': sector['event_ledger_update']['event_ledger_hash'],
        'details': {'result.json': ref}, 'coverage': []}
    research = {'records': [], 'gaps': [], 'candidate_work': {'status': 'UNAVAILABLE_OR_REJECTED'},
                'stock_business_work': {'status': 'READ_OK', 'items': []}, 'handoffs': {'active': []}}
    p = m.assemble(code_commit=SHA, checked_at=AT, check_started_at=AT, lanes=lanes,
                   research=research, capabilities=[], refresh_identity={})
    collector.files.update({'current-state.json': m.json_bytes(p), 'README.md': m.render_summary(p).encode()})
    return p, sector, ref


class API:
    def __init__(self, responses=None, archive=None, used=0):
        self.responses = responses or {}; self.raw_archive = archive
        self.calls = used; self.max_calls = 252; self.reads = []
    def get(self, path):
        self.calls += 1; self.reads.append(path); return deepcopy(self.responses[path])
    def archive(self, artifact):
        self.calls += 1; self.reads.append('ARCHIVE'); return self.raw_archive


def collector(api=None, tmp_path=Path('.')):
    return d.Collector(api or API(), SHA, tmp_path, now=lambda: AT)


def composed():
    col = collector(); b, sector, ref = baseline(col)
    institution = project(); iref = col.retain('details/institutional/20/observation.json', m.json_bytes(institution))
    return col, b, sector, ref, institution, iref


def compose(args):
    col, b, sector, ref, institution, iref = args
    return c.build(b, sector_result=sector, sector_source=ref,
        institution_report=institution, institution_source=iref, source_status={}, generated_at=AT)


def test_all_company_origins_preserved_without_price_or_research_gate():
    args = composed(); before = deepcopy(args[1:]); report = compose(args); p = report['projection']
    assert p['coverage']['distinct_companies'] == 6
    assert p['coverage']['institution_only_companies'] == 2
    assert p['coverage']['new_research_executions'] == 0
    assert all(row['research']['status'] == 'UNKNOWN_WITHIN_READ_SCOPE' for row in p['companies'])
    assert args[1:] == before and compose(args) == report
    assert all(row['new_research_execution'] == 'NOT_EXECUTED' for row in p['companies'])
    assert '603000.SH' in [row['thscode'] for row in p['companies']]  # Outside homepage.


def test_exact_security_overlap_retains_names_and_opposite_windows():
    args = list(composed()); institution = args[4]
    item = institution['projection']['companies'][0]; item['thscode'] = '600000.SH'
    # This composition test supplies a separately validated source projection.
    institution['projection_hash'] = canonical_hash(institution['projection'])
    p = compose(args)['projection']; row = p['companies'][0]
    assert p['coverage']['distinct_companies'] == 5 and p['coverage']['overlap_companies'] == 1
    assert len(row['origins']) == 2 and len(row['source_names']) == 2
    assert row['name_status'] == 'SOURCE_NAMES_DIFFER_NOT_RESOLVED'
    assert [v['institution_net_cny'] for v in row['origins'][1]['observations']] == ['1250000.125', '-3000000.50']
    assert any('不相加' in q for q in row['questions'])


def reseal(b):
    b['reading_hash'] = canonical_hash({k: v for k, v in b.items() if k != 'reading_hash'})


def test_saved_failure_is_not_wait_or_new_research_and_bad_stock_health_visible():
    args = list(composed()); b = args[1]; code = '600000.SH'
    b['research']['stock_business_work']['items'] = [{'thscode': code, 'status': 'PRE_EXECUTION_FAILURE',
        'sources': {}, 'error_type': 'SourceFailure', **m.AUTHORITY}]
    b['lanes']['stock'].update(health='LATEST_SUCCESS_INPUT_REJECTED', last_qualified_result={
        'market_session': '2026-09-16', 'dispositions': [{'thscode': code, 'status': 'CONDITIONS_NOT_MET'}]})
    reseal(b); row = compose(args)['projection']['companies'][0]
    assert row['research']['stock_business_states'][0]['record']['status'] == 'PRE_EXECUTION_FAILURE'
    assert row['stock']['market_session'] == '2026-09-16'
    assert row['stock']['lane_health'] == 'LATEST_SUCCESS_INPUT_REJECTED'
    assert 'WAIT' not in row['research']['stock_business_states'][0]['record'].values()
    assert row['new_research_execution'] == 'NOT_EXECUTED'


def test_reference_purpose_is_not_rewritten_as_completed_or_accepted():
    args = list(composed()); b = args[1]
    record = {'case': '600000.SH', 'id': 'old', 'use': 'METHOD_SUPPLEMENT',
              'purpose_note': 'not Research completion', 'source': args[3]}
    b['research']['records'] = [record, dict(record, case='600000', id='unqualified-ticker')]
    reseal(b); research = compose(args)['projection']['companies'][0]['research']
    assert research['references'] == [record]
    assert research['status'] == 'SAVED_CONTEXT_PRESENT'


def test_unequal_source_dates_and_actual_clocks_are_preserved():
    args = list(composed()); args[4]['projection']['market_session'] = '2026-09-16'
    args[4]['projection_hash'] = canonical_hash(args[4]['projection'])
    p = compose(args)['projection']
    assert {o['market_session'] for row in p['companies'] for o in row['origins']} == {DAY, '2026-09-16'}
    assert 'market_session' not in p  # No single-date laundering.


@pytest.mark.parametrize('what', ['baseline', 'sector_hash', 'institution_hash', 'future', 'authority', 'duplicate_stock'])
def test_invalid_inputs_fail_closed(what):
    args = list(composed())
    if what == 'baseline': args[1]['investment_authority'] = 'BUY'
    elif what == 'sector_hash': args[2]['result_hash'] = '0' * 64
    elif what == 'institution_hash': args[4]['projection_hash'] = '0' * 64
    elif what == 'future':
        args[4]['projection']['generated_at'] = '2027-01-01T00:00:00Z'
        args[4]['projection_hash'] = canonical_hash(args[4]['projection'])
    elif what == 'authority':
        args[4]['projection']['investment_authority'] = 'BUY'
        args[4]['projection_hash'] = canonical_hash(args[4]['projection'])
    else:
        args[1]['lanes']['stock']['last_qualified_result'] = {'dispositions': [{'thscode': '600000.SH'}] * 2}
        reseal(args[1])
    with pytest.raises(ValueError): compose(args)


def test_reference_bytes_and_html_safety():
    args = list(composed()); col, _, _, ref, _, _ = args
    assert c.retained_bytes(col.files, ref) == m.json_bytes(args[2])
    with pytest.raises(ValueError): c.retained_bytes(col.files, dict(ref, sha256='0'*64))
    for company in args[4]['projection']['companies']:
        company['company_name'] = '<script>unsafe</script>'
    args[4]['projection_hash'] = canonical_hash(args[4]['projection'])
    html = c.render(compose(args))
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert 'http://' not in html and '<img' not in html


def source_fixture(tmp_path):
    run = {'id': 20, 'path': r.WORKFLOW, 'head_sha': SHA, 'head_branch': 'main',
           'repository': {'full_name': m.REPOSITORY}, 'head_repository': {'full_name': m.REPOSITORY},
           'status': 'completed', 'conclusion': 'success', 'event': 'workflow_dispatch', 'run_attempt': 1,
           'created_at': '2026-09-18T00:30:00Z', 'updated_at': '2026-09-18T00:50:00Z'}
    workflow = {'GITHUB_REPOSITORY': m.REPOSITORY, 'GITHUB_WORKFLOW': 'radar-institutional-source',
        'GITHUB_REF': 'refs/heads/main', 'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1',
        'GITHUB_SHA': SHA, 'GITHUB_RUN_ID': '20'}
    times = iter(NOW + timedelta(seconds=i) for i in range(15))
    bodies = iter(map(raw, fixtures()))
    root = tmp_path/'payload'
    capture.capture(root, market_session=DAY, workflow=workflow, transport=lambda *a: next(bodies),
                    now=lambda: next(times), pause=lambda _: None, credential='test-credential', provenance='LIVE_HITHINK')
    # LIVE marks the exercised production branch; this test's bodies are synthetic.
    files = {'payload/'+p.name: p.read_bytes() for p in root.iterdir()}
    replay = capture.verify(root)
    files['verification.json'] = m.json_bytes({k: replay[k] for k in ('status', 'capture_hash')})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items(): z.writestr(name, data)
    data = stream.getvalue()
    artifact = {'id': 200, 'name': 'institutional-radar-20-1', 'expired': False,
                'size_in_bytes': len(data), 'digest': 'sha256:'+m.sha256(data),
                'workflow_run': {'id': 20, 'head_sha': SHA}}
    responses = {'actions/workflows/radar-institutional-source.yml/runs?branch=main&per_page=20':
                 {'total_count': 1, 'workflow_runs': [run]},
                 'actions/runs/20': run,
                 'actions/runs/20/artifacts?per_page=100': {'total_count': 1, 'artifacts': [artifact]}}
    return API(responses, data), run, artifact


def test_actual_capture_replay_and_existing_collector_retention_join(tmp_path):
    api, run, artifact = source_fixture(tmp_path); col = collector(api, tmp_path)
    b, _, _ = baseline(col); original = deepcopy(b)
    p = r.attach(col, b); x = p['research']['radar_discovery']
    assert x['status'] == 'READ_OK' and x['coverage']['distinct_companies'] == 6
    assert x['source_status']['institutional']['replay']['network_calls'] == 0
    assert x['source_status']['institutional']['archive']['artifact_id'] == 200
    assert c.retained_bytes(col.files, x['details']['base_context']) == m.json_bytes(original)
    assert b == original and p['lanes'] == original['lanes'] and p['pending'] == []
    assert m.read_package_bytes(p) == col.files['current-state.json']
    assert '打开全部公司' in col.files['README.md'].decode()
    assert len(api.reads) == 4 and api.reads[-1] == 'ARCHIVE'
    assert all(not ('prices' in v or 'dragon-tiger' in v) for v in api.reads)


@pytest.mark.parametrize('kind', ['failed', 'running', 'expired', 'digest', 'wrong_sha', 'rerun', 'future', 'foreign'])
def test_latest_invalid_attempt_never_falls_back_and_sector_survives(tmp_path, kind):
    api, run, artifact = source_fixture(tmp_path)
    listing = api.responses['actions/workflows/radar-institutional-source.yml/runs?branch=main&per_page=20']
    listing['workflow_runs'].append(dict(run, id=19, created_at='2026-09-17T20:00:00Z'))
    listing['total_count'] = 2
    if kind == 'failed': run['conclusion'] = 'failure'
    elif kind == 'running': run.update(status='in_progress', conclusion=None)
    elif kind == 'expired': artifact['expired'] = True
    elif kind == 'digest': artifact['digest'] = 'sha256:'+'0'*64
    elif kind == 'wrong_sha': run['head_sha'] = 'b'*40
    elif kind == 'rerun': run['run_attempt'] = 2
    elif kind == 'future': run['updated_at'] = '2027-01-01T00:00:00Z'
    else: run['head_repository']['full_name'] = 'foreign/repo'
    col = collector(api, tmp_path); b, _, _ = baseline(col)
    p = r.attach(col, b); x = p['research']['radar_discovery']
    assert x['status'] == 'READ_OK_WITH_SOURCE_GAPS'
    assert x['coverage']['institutional_companies'] == 0 and x['coverage']['sector_companies'] == 4
    assert not any('/19' in str(v) for v in api.reads)
    assert p['lanes'] == b['lanes'] and 'QUIET' not in x['status']


def test_budget_refusal_does_not_spend_or_reset_api_counter(tmp_path):
    api, _, _ = source_fixture(tmp_path); col = collector(api, tmp_path); b, _, _ = baseline(col)
    api.calls = 240
    p = r.attach(col, b)
    assert api.calls == 240 and api.reads == []
    assert p['research']['radar_discovery']['source_status']['institutional']['failed_stage'] == 'BUDGET_PREFLIGHT'
    assert not any(k.startswith('sources/artifacts/') for k in col.files)


def test_unconfigured_wrapper_leaves_base_collector_unchanged(monkeypatch, tmp_path):
    col = entry.Collector(API(), SHA, tmp_path, now=lambda: AT); b, _, _ = baseline(col)
    monkeypatch.setattr(d.Collector, 'collect', lambda self, refresh: b)
    assert col.collect({}) is b
    col.include_radar_discovery = True
    calls=[]; monkeypatch.setattr(r, 'attach', lambda a, value: calls.append(value) or value)
    assert col.collect({}) is b and calls == [b]


def test_no_new_scheduler_or_secret_and_manual_source_keeps_original_boundary():
    source_workflow = Path('.github/workflows/radar-institutional-source.yml').read_text()
    publisher = Path('.github/workflows/current-state-read-entry.yml').read_text()
    assert 'schedule:' not in source_workflow and 'workflow_run:' not in source_workflow
    assert 'radar-institutional-source]' in publisher and '--include-radar-discovery' in publisher
    assert 'schedule:' not in publisher and 'workflow_dispatch:' not in publisher
    assert 'secrets.' not in publisher and 'ref: ${{ github.sha }}' in publisher


def test_source_workflow_receipt_uses_actual_cli_shape(tmp_path, capsys):
    source_fixture(tmp_path)
    assert capture.main(['verify', '--output', str(tmp_path/'payload')]) == 0
    saved = json.loads(capsys.readouterr().out)
    assert set(saved) == {'status', 'capture_hash'}
    assert saved['status'] == 'ORIGINAL_INSTITUTIONAL_BODIES_AND_READING_REBUILT'
