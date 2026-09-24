"""Synthetic, network-blocked reuse regressions; no live market acceptance."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
import requests

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import vibe_concept_snapshot as s
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError

NOW = '2026-09-24T09:00:00+00:00'
EXEC = {'repository': 'auguspp/decision-kernel', 'workflow': s.WORKFLOW,
        'ref': 'refs/heads/main', 'event': 'workflow_dispatch',
        'code_commit': 'a' * 40, 'run_id': 123, 'attempt': 1}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No real source requests in tests')
    monkeypatch.setattr(requests.sessions.Session, 'send', forbidden)


def body(spec, total=496, page_size=100, *, change=None):
    begin = (spec['page'] - 1) * page_size
    rows = []
    for i in range(begin, min(begin + page_size, total)):
        fields = s.PERIODS[spec['period']]
        row = {'f12': f'BK{i + 1000:04}', 'f14': f'概念{i}',
               fields[0]: '-1.25', fields[1]: str(250 - i), fields[2]: '2.0'}
        rows.append(row)
    obj = {'rc': 0, 'data': {'total': total, 'diff': rows}}
    if change:
        change(obj)
    return json.dumps(obj, ensure_ascii=False).encode()


def run(tmp_path, fetch=None, **kwargs):
    calls = []
    def transport(spec):
        calls.append(deepcopy(spec))
        return (fetch or body)(spec)
    root = tmp_path / 'capture'
    result = s.capture(root, EXEC, transport=transport, clock=lambda: NOW,
                       monotonic=kwargs.get('monotonic', lambda: 0), sleep=lambda _: None)
    files = s.read_files(root)
    assert s.replay(files, expected_execution=EXEC) == result
    return result['projection'], files, calls


def test_actual_smaller_pages_retain_whole_tail_and_all_periods(tmp_path):
    # Adapt Vibe's 496/100 regression, with real BK format and strict identity.
    p, files, calls = run(tmp_path)
    assert len(calls) == 15 and len(p['observations']) == 496
    assert p['status'] == 'MATCHED_REPORTED_CATALOGS'
    assert p['coverage']['5d']['returned_pages'] == 5
    assert all(c['matched_reported_catalog'] for c in p['coverage'].values())
    assert p['observations'][-1]['periods']['10d']['main_net_cny'] == '-245'
    assert all(c['params']['pz'] == '200' and c['params']['fid'] == 'f12' for c in calls)
    assert all(c['params']['fs'] == 'm:90+t:3' and 'f24' not in c['params']['fields'] for c in calls)
    assert p['source_trade_date'] is None and p['source_calls_during_replay'] == 0
    assert p['investment_authority'] == 'NONE' and p['automatic_admission'] is False
    assert b'496' in files['summary.md'] and b'BK1495' in files['summary.md']


def test_short_page_before_total_is_not_silently_complete(tmp_path):
    def fetch(spec):
        raw = body(spec, total=250)
        if spec['page'] == 2:
            obj = json.loads(raw); obj['data']['diff'] = obj['data']['diff'][:50]
            return json.dumps(obj).encode()
        return raw
    p, _, calls = run(tmp_path, fetch)
    # We continue after the short second page, and reject the subsequent empty page.
    assert [c['page'] for c in calls] == [1, 2, 3, 4]
    assert p['stop_reason'] == 'BODY_REJECTED'
    assert p['coverage']['today']['returned_rows'] == 200
    assert not p['coverage']['today']['matched_reported_catalog']


@pytest.mark.parametrize('case', ['duplicate', 'changed_total', 'empty', 'invalid_code', 'missing_total', 'total_bool', 'rc', 'dict_diff'])
def test_bad_second_page_preserves_original_and_prior_progress(tmp_path, case):
    def change(obj):
        if case == 'duplicate': obj['data']['diff'][0]['f12'] = 'BK1000'
        if case == 'changed_total': obj['data']['total'] += 1
        if case == 'empty': obj['data']['diff'] = []
        if case == 'invalid_code': obj['data']['diff'][0]['f12'] = '885311.TI'
        if case == 'missing_total': obj['data'].pop('total')
        if case == 'total_bool': obj['data']['total'] = True
        if case == 'rc': obj['rc'] = 403
        if case == 'dict_diff': obj['data']['diff'] = {'0': obj['data']['diff'][0]}
    p, files, calls = run(tmp_path, lambda spec: body(spec, change=change if spec['page'] == 2 else None))
    assert len(calls) == 2 and p['coverage']['today']['returned_rows'] == 100
    assert p['stop_reason'] == 'BODY_REJECTED' and 'today-2.json' in files
    assert p['coverage']['5d']['upstream_total_claim'] is None


@pytest.mark.parametrize('value,status', [(None, 'MISSING'), ('-', 'MISSING'), ('', 'MISSING'),
    (True, 'INVALID'), ('NaN', 'INVALID'), ('1e999999', 'INVALID'), ('garbage', 'INVALID')])
def test_missing_and_invalid_values_never_become_zero(tmp_path, value, status):
    def fetch(spec):
        return body(spec, total=1, change=lambda obj: obj['data']['diff'][0].update({s.PERIODS[spec['period']][0]: value}))
    p, _, _ = run(tmp_path, fetch)
    for r in p['observations'][0]['periods'].values():
        assert r['change_percent'] is None and r['field_gaps']['change_percent'] == status
    assert p['coverage']['today']['matched_reported_catalog']  # coverage is not data quality
    assert p['coverage']['today']['missing_or_invalid_values'] == 1


@pytest.mark.parametrize('status', [401, 403, 429, 500])
def test_http_failure_stops_provider_without_retry_or_other_periods(tmp_path, status):
    def fetch(spec):
        raise DumpTrialError('HTTP_REJECTED', http_status=status)
    p, files, calls = run(tmp_path, fetch)
    assert len(calls) == 1 and p['stop_reason'] == 'SOURCE_ERROR'
    assert not p['observations']
    assert json.loads(files['capture.json'])['records'][0]['http_status'] == status
    assert set(files) == {'plan.json', 'capture.json', 'observation.json', 'summary.md'}


def test_transport_failure_after_good_page_does_not_erase_it(tmp_path):
    def fetch(spec):
        if spec['page'] == 2: raise requests.Timeout()
        return body(spec)
    p, _, calls = run(tmp_path, fetch)
    assert len(calls) == 2 and len(p['observations']) == 100
    assert p['stop_reason'] == 'SOURCE_ERROR'


def test_empty_catalog_is_not_all_market_no_activity(tmp_path):
    p, _, calls = run(tmp_path, lambda spec: body(spec, total=0))
    assert len(calls) == 3 and p['stop_reason'] == 'COMPLETE'
    assert p['status'] == 'PARTIAL_OR_UNAVAILABLE'
    assert all(c['upstream_total_claim'] == 0 and not c['matched_reported_catalog'] for c in p['coverage'].values())


def test_request_cap_is_global_not_per_period(tmp_path):
    p, _, calls = run(tmp_path, lambda spec: body(spec, total=4000))
    assert len(calls) == s.MAX_REQUESTS == 32
    assert p['stop_reason'] == 'REQUEST_BUDGET'
    assert p['coverage']['today']['returned_rows'] == 3200 and not p['coverage']['5d']['matched_reported_catalog']


def test_time_budget_before_any_source_is_honest(tmp_path):
    values = iter([0, 181, 181])
    p, _, calls = run(tmp_path, monotonic=lambda: next(values))
    assert not calls and p['stop_reason'] == 'TIME_BUDGET'
    assert p['attempted_requests'] == 0 and not p['observations']


def resign(files, mutate):
    files = dict(files); saved = json.loads(files['capture.json']); mutate(saved)
    saved['capture_hash'] = canonical_hash({k:v for k,v in saved.items() if k != 'capture_hash'})
    files['capture.json'] = s.encoded(saved)
    files.pop('observation.json', None); files.pop('summary.md', None)
    return files


@pytest.mark.parametrize('case', ['query', 'page', 'raw', 'clock', 'elapsed', 'run', 'retry', 'stop', 'authority'])
def test_rehashed_custody_tampering_is_rejected(tmp_path, case):
    _, files, _ = run(tmp_path, lambda spec: body(spec, total=1))
    def mutate(saved):
        r = saved['records'][0]
        if case == 'query': r['request']['params']['fs'] = 'm:90+t:2'
        if case == 'page': r['request']['page'] = 2
        if case == 'raw': r['sha256'] = '0' * 64
        if case == 'clock': r['received_at'] = '2026-09-25T00:00:00+00:00'
        if case == 'elapsed': r['elapsed_ms'] = 180000
        if case == 'run': saved['execution']['run_id'] = 999
        if case == 'retry': saved['retry_count'] = 1
        if case == 'stop': saved['stop_reason'] = 'TIME_BUDGET'
        if case == 'authority': saved['model_calls'] = False
    with pytest.raises(ValueError):
        s.replay(resign(files, mutate), expected_execution=EXEC)


def test_repeated_replay_is_identical_and_no_new_observation(tmp_path):
    p, files, _ = run(tmp_path)
    first = s.replay(files, expected_execution=EXEC)
    assert first == s.replay(files, expected_execution=EXEC)
    assert first['projection']['capture_hash'] == p['capture_hash']


@pytest.mark.parametrize('path', ['observation.json', 'summary.md', 'today-1.json'])
def test_changed_retained_bytes_are_rejected(tmp_path, path):
    _, files, _ = run(tmp_path, lambda spec: body(spec, total=1)); files[path] += b' '
    with pytest.raises(ValueError): s.replay(files, expected_execution=EXEC)


def test_extra_file_not_in_manifest_is_rejected(tmp_path):
    _, files, _ = run(tmp_path, lambda spec: body(spec, total=1)); files['extra.json'] = b'{}'
    with pytest.raises(ValueError): s.replay(files, expected_execution=EXEC)


def test_different_period_memberships_and_names_are_not_dropped(tmp_path):
    def fetch(spec):
        return body(spec, total=1, change=lambda obj: obj['data']['diff'][0].update({
            'f12': 'BK1001' if spec['period'] == '10d' else 'BK1000', 'f14': spec['period']}))
    p, _, _ = run(tmp_path, fetch)
    assert len(p['observations']) == 2
    assert set(p['observations'][0]['periods']) == {'today', '5d'}
    assert p['observations'][0]['periods']['5d']['name'] == '5d'
    assert set(p['observations'][1]['periods']) == {'10d'}


def test_source_text_is_not_an_executable_or_markdown_link(tmp_path):
    p, files, _ = run(tmp_path, lambda spec: body(spec, total=1, change=lambda obj:
        obj['data']['diff'][0].update(f14='<script>[run](https://x) |\n# hi')))
    md = files['summary.md'].decode()
    assert '<script>' not in md and '[run](' not in md and '\n# hi' not in md
    assert p['model_calls'] == p['research_executions'] == 0


def test_capture_create_only_and_read_reject_symlinks(tmp_path):
    _, _, _ = run(tmp_path, lambda spec: body(spec, total=1))
    with pytest.raises(ValueError): s.capture(tmp_path/'capture', EXEC)
    (tmp_path/'capture'/'extra').symlink_to(tmp_path/'capture'/'plan.json')
    with pytest.raises(ValueError): s.read_files(tmp_path/'capture')


@pytest.mark.parametrize('field,value', [('ref','refs/heads/other'), ('event','push'), ('attempt',2),
    ('attempt',True), ('repository','elsewhere/kernel'), ('code_commit','main'), ('run_id',True)])
def test_explicit_execution_binding(field, value, tmp_path):
    execution = {**EXEC, field:value}
    with pytest.raises(ValueError): s.capture(tmp_path/'never', execution)
    assert not (tmp_path/'never').exists()


def test_http_uses_original_isolated_session_and_no_redirects(monkeypatch):
    spec = s.request_spec('today', 1); raw = body(spec, total=1)
    url = requests.Request('GET', s.URL, params=spec['params']).prepare().url
    class Response:
        status_code = 200
        headers = {'Content-Length': str(len(raw)), 'Content-Encoding': 'identity'}
        def __init__(self): self.url = url
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, **kwargs): yield raw
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, target, **kwargs):
            assert target == s.URL and kwargs['allow_redirects'] is False
            assert kwargs['timeout'] == (10,20) and kwargs['stream'] is True
            assert 'Authorization' not in kwargs['headers'] and 'Cookie' not in kwargs['headers']
            return Response()
    monkeypatch.setattr(s, '_session', lambda: Session())
    assert s.request_raw(spec) == raw
    bad = deepcopy(spec); bad['url'] = 'https://elsewhere/'
    with pytest.raises(ValueError): s.request_raw(bad)


def test_manual_workflow_does_not_change_existing_source_clocks():
    path = Path(__file__).parents[1]/'.github/workflows/vibe-concept-snapshot.yml'
    text = path.read_text()
    assert 'workflow_dispatch:' in text and 'schedule:' not in text and '\n  push:' not in text
    assert 'contents: read' in text and 'actions: read' in text and 'secrets.' not in text
    assert 'persist-credentials: false' in text and 'code-sha:' in text
    assert "r['event']=='push'" in text and "r['conclusion']=='success'" in text
    assert 'source_calls_during_replay' in text and '--mode' not in text  # no arbitrary source/provider selector
