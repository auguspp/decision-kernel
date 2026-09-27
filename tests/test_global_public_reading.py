"""Six-family fixed-R integration. Original codecs, synthetic source bytes only."""
from copy import deepcopy
import json

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import global_market_reading as r, global_public_context as g
from decision_kernel.runtime import current_state as m
from test_global_market_reading import ready, previous, projection
from test_external_radar_reading import pack
from test_global_public_context import body, IDENT, ASOF, TIME
from test_radar_company_reading import reseal

CHECKED = '2026-09-27T12:30:00Z'


def add_public(c, tmp_path):
    c.now = lambda: CHECKED
    records = {}
    for run_id, family in enumerate(g.FAMILIES, 1001):
        ident = {**IDENT, 'run_id': run_id}
        output = tmp_path/family
        report = g.capture(output, ident, family, ASOF, time=lambda: TIME,
            request=lambda spec: g.PublicResponse(spec['url'], 200, {}, body(spec)))
        files = {p.name: p.read_bytes() for p in output.iterdir()}
        run = {'id': run_id, 'path': g.WORKFLOW, 'head_sha': ident['code_commit'],
            'head_branch': 'main', 'repository': {'full_name': m.REPOSITORY},
            'head_repository': {'full_name': m.REPOSITORY}, 'event': 'workflow_dispatch',
            'run_attempt': 1, 'status': 'completed', 'conclusion': 'success',
            'created_at': '2026-09-27T10:59:00Z', 'updated_at': '2026-09-27T11:01:00Z',
            'display_title': 'B1 public · ' + family + ' · ' + ASOF}
        raw = pack(files)
        artifact = {'id': run_id+2000, 'name': f'global-public-{family}-{run_id}-1',
            'expired': False, 'size_in_bytes': len(raw), 'digest': 'sha256:'+m.sha256(raw),
            'workflow_run': {'id': run_id, 'head_sha': ident['code_commit']}}
        c.api.responses['actions/runs/'+str(run_id)] = run
        c.api.responses[f'actions/runs/{run_id}/artifacts?per_page=100'] = {'total_count': 1, 'artifacts': [artifact]}
        c.api.archives[artifact['id']] = raw
        records[family] = (run, artifact, files, report)
    c.api.responses[r.PUBLIC_QUERY] = {'total_count': 4, 'workflow_runs': [v[0] for v in records.values()]}
    return records


def test_six_families_keep_exact_codec_units_raw_archives_and_no_new_authority(tmp_path, monkeypatch):
    c, baseline, relay = ready(tmp_path, monkeypatch)
    public = add_public(c, tmp_path)
    before = deepcopy(baseline)
    payload = r.attach(c, baseline)
    m.validate_read_package(payload)
    p = projection(c)
    assert p['version'] == r.VERSION and set(p['families']) == set(r.FAMILIES)
    for family, original in {**relay, **public}.items():
        snap = p['families'][family]['snapshot']
        assert snap['report'] == original[3]
        assert c.files[snap['archive']['read_path']] == c.api.archives[original[1]['id']]
        assert snap['report']['source_calls_during_replay'] == 0
    assert baseline == before and payload['lanes'] == before['lanes']
    assert p['source_calls'] == 0 and p['authority'] == g.AUTHORITY
    assert not p['complete_global_coverage']
    assert [p['families'][f]['snapshot']['report']['available_values'] for f in g.FAMILIES] == [8, 4, 3, 2]
    assert all(v['change'] is None for v in p['families']['commodities']['snapshot']['report']['observations'])
    assert len(c.files[r.REPORT]) < 256*1024


def test_v1_two_family_prior_remains_recoverable_under_v2(tmp_path, monkeypatch):
    c, baseline, _ = ready(tmp_path, monkeypatch)
    first = r.attach(c, baseline)
    p = projection(c)
    p.update(version=r.LEGACY_VERSION, families={f:p['families'][f] for f in ('indices', 'shibor')})
    p.pop('public_query')
    old = {'projection': p, 'projection_hash': canonical_hash(p)}
    meta = first['research']['global_market']
    meta.update(version=r.LEGACY_VERSION, projection_hash=old['projection_hash'])
    meta['details']['json'] = c.retain(r.REPORT, m.json_bytes(old))
    reseal(first)
    previous(c, first)
    add_public(c, tmp_path)
    r.attach(c, first)
    assert projection(c)['prior_read_gaps'] == []
    assert projection(c)['families']['indices']['latest_read_status'] == 'REUSED_RETAINED_CAPTURE'
    assert projection(c)['families']['treasury']['snapshot']['report']['available_values'] == 8


def test_public_query_failure_is_independent_of_relay_and_keeps_its_old_git_bytes(tmp_path, monkeypatch):
    c, baseline, _ = ready(tmp_path, monkeypatch)
    add_public(c, tmp_path)
    first = r.attach(c, baseline)
    prior_files = previous(c, first)
    del c.api.responses[r.PUBLIC_QUERY]
    r.attach(c, first)
    p = projection(c)
    assert p['public_query']['status'] == 'QUERY_UNAVAILABLE'
    assert p['families']['indices']['latest_read_status'] == 'REUSED_RETAINED_CAPTURE'
    for family in g.FAMILIES:
        item = p['families'][family]
        assert item['latest_read_status'] == 'QUERY_UNAVAILABLE' and item['snapshot']
        ref = item['snapshot']['archive']
        assert c.files[ref['read_path']] == prior_files[ref['read_path']]


@pytest.mark.parametrize('damage', ['raw', 'summary', 'workflow', 'family', 'extra', 'expired'])
def test_public_bad_family_cannot_launder_through_new_zip_digest_or_erase_others(tmp_path, monkeypatch, damage):
    c, baseline, _ = ready(tmp_path, monkeypatch)
    records = add_public(c, tmp_path)
    run, artifact, files, _ = records['treasury']
    if damage == 'expired':
        artifact['expired'] = True
    else:
        if damage == 'raw': files['raw-00.bin'] += b' '
        if damage == 'summary': files['summary.json'] = b'{}'
        if damage == 'extra': files['execute.py'] = b'raise RuntimeError("do not execute")'
        if damage in ('workflow', 'family'):
            cap = g.decode(files['capture.json'])
            if damage == 'workflow': cap['identity']['workflow'] = r.source.WORKFLOW
            else: cap['family'] = 'fx'
            cap['capture_hash'] = g.seal(cap)
            files['capture.json'] = g.encoded(cap)
        raw = pack(files)
        c.api.archives[artifact['id']] = raw
        artifact.update(size_in_bytes=len(raw), digest='sha256:'+m.sha256(raw))
    r.attach(c, baseline)
    p = projection(c)
    assert p['families']['treasury']['latest_read_status'] == 'CAPTURE_UNAVAILABLE_OR_REJECTED'
    assert p['families']['treasury']['snapshot'] is None
    assert all(p['families'][f]['snapshot'] for f in r.FAMILIES if f != 'treasury')


def test_public_403_checkpoint_is_retained_without_replacing_previous_readable_snapshot(tmp_path, monkeypatch):
    c, baseline, _ = ready(tmp_path, monkeypatch)
    records = add_public(c, tmp_path)
    first = r.attach(c, baseline)
    previous(c, first)
    run = {**deepcopy(records['fx'][0]), 'id': 1100, 'conclusion': 'failure',
           'created_at': '2026-09-27T11:59:00Z', 'updated_at': '2026-09-27T12:01:00Z'}
    output = tmp_path/'failed'
    g.capture(output, {**IDENT, 'run_id': 1100}, 'fx', ASOF, time=lambda:'2026-09-27T12:00:00Z',
              request=lambda spec:g.PublicResponse(spec['url'], 403, {}, b'{"error":"denied"}'))
    raw = pack({p.name:p.read_bytes() for p in output.iterdir()})
    artifact = {'id': 4100, 'name': 'global-public-fx-1100-1', 'expired': False,
        'size_in_bytes': len(raw), 'digest':'sha256:'+m.sha256(raw),
        'workflow_run': {'id':1100, 'head_sha':IDENT['code_commit']}}
    c.api.responses[r.PUBLIC_QUERY]['workflow_runs'].append(run)
    c.api.responses[r.PUBLIC_QUERY]['total_count'] += 1
    c.api.responses['actions/runs/1100'] = run
    c.api.responses['actions/runs/1100/artifacts?per_page=100'] = {'total_count':1, 'artifacts':[artifact]}
    c.api.archives[4100] = raw
    r.attach(c, first)
    state = projection(c)['families']['fx']
    assert state['latest_attempt']['id'] == 1100 and state['snapshot']['run']['id'] == 1002
    assert state['latest_capture_status'] == 'UNAVAILABLE'
    assert state['latest_outcomes'][0]['http_status'] == 403
    assert c.files[state['latest_archive']['read_path']] == raw


def test_six_family_git_custody_survives_expired_action_artifacts(tmp_path, monkeypatch):
    c, baseline, relay = ready(tmp_path, monkeypatch)
    public = add_public(c, tmp_path)
    first = r.attach(c, baseline)
    previous(c, first)
    for _, artifact, _, _ in {**relay, **public}.values(): artifact['expired'] = True
    c.now = lambda:'2026-11-01T12:30:00Z'
    r.attach(c, first)
    assert all(s['latest_read_status'] == 'REUSED_RETAINED_CAPTURE' for s in projection(c)['families'].values())
    assert not any(isinstance(v, tuple) and v[0] == 'archive' for v in c.api.reads)


def test_public_listener_is_only_saved_reading_no_source_or_new_schedule():
    from pathlib import Path
    workflow = Path('.github/workflows/current-state-read-entry.yml').read_text()
    assert 'radar-global-public' in workflow and '--include-global-market' in workflow
    assert 'schedule:' not in workflow and 'workflow_dispatch:' not in workflow
    assert 'secrets.' not in workflow and 'global_public_context --family' not in workflow
