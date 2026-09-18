"""Synthetic original-capture/Collector integration, with networking prohibited."""
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import concept_radar_capture as capture
from decision_kernel.runtime import concept_radar_reading as cr
from decision_kernel.runtime import institutional_radar_reading as r
from decision_kernel.runtime import radar_company_reading as c
from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import current_state_delivery as d
from test_concept_radar import Fixture, AT, DAY, WF, SHA, raw, no_network
from test_radar_company_reading import baseline, collector, source_fixture, reseal

CUTOFF = '2026-09-18T10:00:00+00:00'


def inputs(tmp_path, change=None):
    api, _, _ = source_fixture(tmp_path)
    f = Fixture()
    if change:
        f.change = change
    out = tmp_path/'concept-payload'
    clock = iter(AT + timedelta(seconds=i) for i in range(40))
    cap = capture.capture(out, market_session=DAY, workflow=WF, expected_code=SHA,
        transport=lambda path, params: raw(f.body(path, params)), now=lambda: next(clock),
        pause=lambda _: None, credential='synthetic-key', provenance='LIVE_HITHINK')
    # LIVE exercises the real branch with explicitly synthetic source bytes.
    files = {'payload/'+p.name: p.read_bytes() for p in out.iterdir()}
    files['verification.json'] = raw(capture.verify(out))
    files['implementation-source.tar'] = b'NOT_EXECUTABLE_SOURCE_AND_MUST_NOT_BE_OPENED'
    run = {'id': 123456, 'path': cr.WORKFLOW, 'head_sha': SHA, 'head_branch': 'main',
        'repository': {'full_name': m.REPOSITORY}, 'head_repository': {'full_name': m.REPOSITORY},
        'status': 'completed', 'conclusion': 'success', 'event': 'workflow_dispatch', 'run_attempt': 1,
        'created_at': '2026-09-18T07:59:00Z', 'updated_at': '2026-09-18T08:02:00Z'}
    art = {'id': 300, 'name': 'concept-radar-123456-1', 'expired': False,
           'workflow_run': {'id': 123456, 'head_sha': SHA}}
    api.responses.update({cr.QUERY: {'total_count': 1, 'workflow_runs': [run]},
        'actions/runs/123456': run, 'actions/runs/123456/artifacts?per_page=100': {'total_count': 1, 'artifacts': [art]}})
    original = api.raw_archive
    def archive(artifact):
        api.calls += 1; api.reads.append('ARCHIVE:' + str(artifact['id']))
        return original if artifact['id'] == 200 else api.concept_archive
    api.archive = archive
    repack(api, art, files)
    col = collector(api, tmp_path); col.now = lambda: CUTOFF; col.include_concept_discovery = True
    b, _, _ = baseline(col)
    return col, b, run, art, files, cap


def repack(api, artifact, files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            z.writestr(name, body)
    api.concept_archive = stream.getvalue()
    artifact.update(size_in_bytes=len(api.concept_archive), digest='sha256:'+m.sha256(api.concept_archive))


def reading(col, b):
    p = r.attach(col, b)
    meta = p['research']['radar_discovery']
    report = json.loads(c.retained_bytes(col.files, meta['details']['company_reading']))
    return p, meta, report['projection']


def test_three_source_read_preserves_original_payload_dates_gaps_and_authority(tmp_path):
    col, b, _, _, files, _ = inputs(tmp_path); before = deepcopy(b)
    p, meta, view = reading(col, b)
    assert meta['status'] == 'READ_OK' and view['version'] == c.CONCEPT_VERSION
    assert view['coverage']['concept_companies'] == 4
    assert view['coverage']['concept_only_companies'] == 3
    assert view['coverage']['distinct_companies'] == 9
    assert view['coverage']['concept_overlap_existing_companies'] == 1
    assert view['concept_context']['coverage']['detail_deferred'] == 1
    assert view['concept_context']['detail_selection_policy']['detail_order_meaning'].endswith('NOT_RESEARCH_PRIORITY')
    assert len(view['concept_context']['overlaps']) == 3 and view['coverage']['full_concept_trend_radar'] is False
    assert b == before and p['lanes'] == b['lanes'] and p['pending'] == []
    assert c.retained_bytes(col.files, meta['details']['base_context']) == m.json_bytes(b)
    source = meta['source_status']['concept']
    assert source['replay']['network_calls'] == 0
    for name, body in files.items():
        if name.startswith('payload/'):
            assert c.retained_bytes(col.files, source['details'][name[8:]]) == body
    assert col.files[source['archive']['read_path']] == col.api.concept_archive
    common = next(v for v in view['companies'] if v['thscode'] == '600000.SH')
    assert {o['kind'] for o in common['origins']} == {'SECTOR_LEADER', 'CONCEPT_CURRENT_MEMBER'}
    assert len(common['source_names']) == 2 and 'market_session' not in view
    assert all(v['new_research_execution'] == 'NOT_EXECUTED' and not v['automatic_admission'] for v in view['companies'])
    assert all(view[k] == v for k, v in c.AUTHORITY.items())
    assert len(col.api.reads) == 8  # Four saved GitHub reads per source; no provider.
    assert b'concept-payload' not in col.files['README.md']
    assert '概念 4' in col.files['README.md'].decode()


@pytest.mark.parametrize('kind', ['failure', 'running', 'expired', 'digest', 'wrong_sha', 'rerun',
    'future', 'foreign', 'wrong_workflow', 'duplicate_listing', 'missing_listing'])
def test_invalid_latest_concept_keeps_other_sources_and_never_falls_back(tmp_path, kind):
    col, b, run, art, _, _ = inputs(tmp_path)
    listing = col.api.responses[cr.QUERY]
    listing['workflow_runs'].append(dict(run, id=123455, created_at='2026-09-18T07:00:00Z'))
    listing['total_count'] = 2
    if kind == 'failure': run['conclusion'] = 'failure'
    elif kind == 'running': run.update(status='in_progress', conclusion=None)
    elif kind == 'expired': art['expired'] = True
    elif kind == 'digest': art['digest'] = 'sha256:'+'0'*64
    elif kind == 'wrong_sha': run['head_sha'] = 'b'*40
    elif kind == 'rerun': run['run_attempt'] = 2
    elif kind == 'future': run['updated_at'] = '2027-01-01T00:00:00Z'
    elif kind == 'foreign': run['head_repository']['full_name'] = 'foreign/repo'
    elif kind == 'wrong_workflow': run['path'] = r.WORKFLOW
    elif kind == 'duplicate_listing': listing['workflow_runs'].append(deepcopy(run))
    else: listing['workflow_runs'] = []
    p, meta, view = reading(col, b)
    assert meta['status'] == 'READ_OK_WITH_SOURCE_GAPS'
    assert view['coverage']['distinct_companies'] == 6 and view['coverage']['institutional_companies'] == 2
    assert view['coverage']['concept_companies'] == 0 and not view['coverage']['concept_radar']
    assert p['lanes'] == b['lanes'] and not any('/123455' in s for s in col.api.reads)
    assert not any(k.startswith('details/concept/') for k in col.files)
    assert any(k.startswith('details/institutional/') for k in col.files)


@pytest.mark.parametrize('kind', ['rehashed_output', 'fingerprint', 'wrong_capture_run', 'synthetic',
    'verification', 'nested_payload', 'extra_payload', 'finish_after_run', 'raw_response'])
def test_bad_payload_cannot_be_laundered_by_new_archive_digest(tmp_path, kind):
    col, b, _, art, files, _ = inputs(tmp_path)
    cap = json.loads(files['payload/capture.json'])
    if kind == 'rehashed_output':
        observation = json.loads(files['payload/observation.json'])
        observation['projection']['companies'][0]['source_names'] = ['forged company']
        observation['projection_hash'] = canonical_hash(observation['projection'])
        files['payload/observation.json'] = raw(observation)
        cap['files']['observation.json'] = capture._digest(files['payload/observation.json'])
    elif kind == 'fingerprint': cap['implementation']['runtime/concept_radar.py'] = '0'*64
    elif kind == 'wrong_capture_run': cap['workflow']['GITHUB_RUN_ID'] = '123455'
    elif kind == 'synthetic': cap['provenance'] = 'SYNTHETIC_TEST_ONLY'
    elif kind == 'verification': files['verification.json'] = b'{}'
    elif kind == 'nested_payload': files['payload/nested/evil.py'] = b'raise AssertionError("do not execute")'
    elif kind == 'extra_payload': files['payload/extra.json'] = b'{}'
    elif kind == 'finish_after_run': cap['finished_at'] = '2026-09-18T09:00:00Z'
    else: files['payload/response-1.json'] += b' '
    cap['capture_hash'] = canonical_hash({k: v for k, v in cap.items() if k != 'capture_hash'})
    files['payload/capture.json'] = raw(cap); repack(col.api, art, files)
    _, meta, view = reading(col, b)
    assert meta['source_status']['concept']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert view['coverage']['distinct_companies'] == 6
    assert not any(k.startswith('details/concept/') for k in col.files)


def test_partial_history_retains_members_and_explicit_partial_status(tmp_path):
    def change(path, params, body):
        if path == capture.radar.probe.HISTORY and params['thscode'] == '886000.TI':
            body['data']['item'] = body['data']['item'][:-1]
        return body
    col, b, _, _, _, cap = inputs(tmp_path, change)
    assert cap['status'] == capture.PARTIAL
    _, meta, view = reading(col, b)
    assert meta['status'] == 'READ_OK_WITH_SOURCE_GAPS'
    assert view['coverage']['concept_companies'] == 4
    assert view['concept_context']['coverage']['detail_gaps'] == 1
    assert view['concept_context']['details'][0]['path'] is None


def test_bse_scope_and_saved_failed_research_never_disappear_or_reset(tmp_path):
    def change(path, params, body):
        if path == capture.radar.probe.MEMBERS:
            body['data']['item'].append({'thscode': '920001.BJ', 'ticker': '920001', 'name': 'Synthetic BSE'})
        return body
    col, b, _, _, _, _ = inputs(tmp_path, change)
    b['research']['stock_business_work']['items'] = [{'thscode': '600000.SH', 'status': 'PRE_EXECUTION_FAILURE',
        'sources': {}, 'execution_id': 'original-root', **m.AUTHORITY}]
    reseal(b)
    _, _, view = reading(col, b)
    bycode = {r['thscode']: r for r in view['companies']}
    assert bycode['920001.BJ']['stock_business_research_scope'] == 'RESEARCH_SCOPE_UNSUPPORTED'
    assert bycode['920001.BJ']['research']['status'] == 'UNKNOWN_WITHIN_READ_SCOPE'
    assert bycode['600000.SH']['research']['stock_business_states'][0]['record']['execution_id'] == 'original-root'
    assert bycode['600000.SH']['new_research_execution'] == 'NOT_EXECUTED'
    assert view['coverage']['unsupported_stock_business_research_companies'] == 1


def test_concept_budget_preflight_keeps_institutional_and_api_costs(tmp_path):
    col, b, _, _, _, _ = inputs(tmp_path)
    col.api.max_calls = 59
    _, meta, view = reading(col, b)
    assert meta['source_status']['concept']['failed_stage'] == 'BUDGET_PREFLIGHT'
    assert view['coverage']['distinct_companies'] == 6
    assert cr.QUERY not in col.api.reads and col.api.calls == 4


@pytest.mark.parametrize('phase', ['retention', 'composition', 'render', 'assembly'])
def test_concept_failure_rolls_back_only_new_input_and_output_without_counter_reset(tmp_path, monkeypatch, phase):
    col, b, _, _, _, _ = inputs(tmp_path)
    if phase == 'retention':
        old = col.retain
        def fail(path, body):
            result = old(path, body)
            if path.startswith('details/concept/'):
                raise ValueError('sensitive failure must not be quoted')
            return result
        monkeypatch.setattr(col, 'retain', fail)
    elif phase == 'composition':
        old = c.build
        def fail(*args, **kwargs):
            if kwargs.get('concept_report') is not None:
                raise ValueError('sensitive failure must not be quoted')
            return old(*args, **kwargs)
        monkeypatch.setattr(c, 'build', fail)
    elif phase == 'render':
        old = c.render
        def fail(report):
            if report['projection'].get('coverage', {}).get('concept_radar'):
                raise ValueError('sensitive failure must not be quoted')
            return old(report)
        monkeypatch.setattr(c, 'render', fail)
    else:
        old = r._assemble
        def fail(collector, baseline, research):
            if research['radar_discovery'].get('coverage', {}).get('concept_radar'):
                raise ValueError('sensitive failure must not be quoted')
            return old(collector, baseline, research)
        monkeypatch.setattr(r, '_assemble', fail)
    p, meta, view = reading(col, b)
    assert meta['status'] == 'READ_OK_WITH_SOURCE_GAPS' and view['coverage']['distinct_companies'] == 6
    assert col.api.calls == 8 and p['lanes'] == b['lanes']
    assert 'sensitive failure' not in json.dumps(p)
    assert not any(k.startswith('details/concept/') for k in col.files)
    assert len(col.archive_cache) == 1  # Original institutional archive survives.


def test_html_escapes_concept_names_and_keeps_exact_same_reading_links(tmp_path):
    def change(path, params, body):
        if path == capture.radar.probe.CATALOG and params == {'tag': 'cn_concept'}:
            body['data']['item'][0]['name'] = '<script>unsafe</script>'
        return body
    col, b, _, _, _, _ = inputs(tmp_path, change)
    _, meta, _ = reading(col, b)
    page = c.retained_bytes(col.files, meta['details']['index']).decode()
    assert '<script>' not in page and '&lt;script&gt;' in page
    assert '../../details/concept/123456/index.html' in page
    assert '未取详情 1' in page and '不是完整连续趋势雷达' in page


def test_no_concept_source_is_visible_without_erasing_original_reading(tmp_path):
    col, b, _, _, _, _ = inputs(tmp_path)
    col.api.responses[cr.QUERY] = {'total_count': 0, 'workflow_runs': []}
    _, meta, view = reading(col, b)
    assert meta['source_status']['concept']['status'] == 'NO_RETAINED_RUN'
    assert view['coverage']['distinct_companies'] == 6 and view['version'] == c.CONCEPT_VERSION


def test_disabled_extension_does_not_read_concept_or_change_v1(tmp_path):
    col, b, _, _, _, _ = inputs(tmp_path)
    col.include_concept_discovery = False
    _, meta, view = reading(col, b)
    assert meta['status'] == 'READ_OK' and view['version'] == c.VERSION
    assert 'concept_companies' not in view['coverage'] and 'concept_context' not in view
    assert cr.QUERY not in col.api.reads


def test_existing_publisher_is_only_new_listener_and_source_remains_manual():
    pub = Path('.github/workflows/current-state-read-entry.yml').read_text()
    src = Path('.github/workflows/radar-concept-source.yml').read_text()
    entry = Path('src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py').read_text()
    assert 'radar-concept-source, radar-institutional-source]' in pub
    assert '--include-concept-discovery' in pub and '--include-radar-discovery' in pub
    assert 'args.include_concept_discovery or args.include_radar_discovery' in entry
    assert 'schedule:' not in pub and 'workflow_dispatch:' not in pub and 'secrets.' not in pub
    assert 'workflow_dispatch:' in src and 'schedule:' not in src and 'workflow_run:' not in src
    assert 'ref: ${{ github.sha }}' in pub


def test_concept_is_readable_even_without_sector_and_institutional_sources(tmp_path):
    col, b, _, _, _, _ = inputs(tmp_path)
    col.api.responses['actions/workflows/radar-institutional-source.yml/runs?branch=main&per_page=20'] = {
        'total_count': 0, 'workflow_runs': []}
    b['lanes']['sector']['last_qualified_result'] = None
    reseal(b)
    _, meta, view = reading(col, b)
    assert meta['status'] == 'READ_OK_WITH_SOURCE_GAPS'
    assert view['coverage']['distinct_companies'] == view['coverage']['concept_companies'] == 4
    assert view['coverage']['sector_companies'] == view['coverage']['institutional_companies'] == 0


@pytest.mark.parametrize('kind', ['future', 'duplicate_company', 'invalid_request_index', 'bad_membership_hash'])
def test_composition_rejects_invalid_concept_origins_not_just_bad_hash(tmp_path, kind):
    col, b, _, _, files, _ = inputs(tmp_path)
    report = json.loads(files['payload/observation.json']); cp = report['projection']
    if kind == 'future': cp['as_of'] = '2027-01-01T00:00:00Z'
    elif kind == 'duplicate_company': cp['companies'].append(deepcopy(cp['companies'][0]))
    elif kind == 'invalid_request_index': cp['companies'][0]['origins'][0]['membership_request_index'] = -1
    else: cp['companies'][0]['origins'][0]['membership_hash'] = '0'*64
    report['projection_hash'] = canonical_hash(cp)
    with pytest.raises(ValueError):
        c.build(b, sector_result=None, sector_source=None, institution_report=None, institution_source=None,
                source_status={}, generated_at=CUTOFF, include_concept=True,
                concept_report=report, concept_source={'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'})
