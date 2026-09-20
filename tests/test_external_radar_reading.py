"""Synthetic saved-source delivery through native archive/reading interfaces."""
from copy import deepcopy
import io
import json
from pathlib import Path
import socket
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import current_state_delivery as base
from decision_kernel.runtime import current_state_delivery_with_odds_watch as entry
from decision_kernel.runtime import external_radar_observations as obs
from decision_kernel.runtime import external_radar_reading as reading
from test_external_radar_observations import news_pair, industry_inputs, edit, hp, PERIOD
from test_radar_company_reading import composed, compose, reseal

NOW = '2026-09-20T04:30:00Z'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a, **k):
        raise AssertionError('saved Radar test attempted networking')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def pack(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    return out.getvalue()


def news_files():
    body, receipt = news_pair(items=[{'id': 1, 'title': '<script>not-code</script> 公司甲发布新产品',
                                     'url': 'https://cls.cn/detail/1'}])
    return {'attempts.json': m.json_bytes([receipt]), 'raw/newsnow-cls.json': body,
            'untrusted.py': b'raise RuntimeError("ARTIFACT_CODE_EXECUTED")'}


def industry_files():
    rows, files, alternatives = [], {}, []
    for variety, (code, name) in obs.CONTINUOUS.items():
        captures = industry_inputs()
        for row in json.loads(captures['identity'][0])['data']['item']:
            row.update(thscode=code, variety_name=name)
            alternatives.append(row)
        for key in ('prices', 'basis', 'warehouse'):
            pair = captures[key]
            pair[1]['params']['thscode'] = code
            if key == 'prices':
                pair = edit(pair, lambda v: v['data'].update(thscode=code))
            label = variety + '-' + key
            filename = 'raw/' + label + '.json'
            rows.append({**pair[1], 'label': label, 'response_file': filename})
            files[filename] = pair[0]
    body, receipt = hp('basis/main-continuous-latest', {}, alternatives)
    rows.append({**receipt, 'label': 'basis-main-continuous-latest', 'response_file': 'raw/identity.json'})
    files['raw/identity.json'] = body
    files['requests.json'] = m.json_bytes(rows)
    return files


class API:
    def __init__(self):
        self.calls, self.max_calls, self.reads = 0, 252, []
        self.responses, self.archives = {}, {}
    def get(self, path):
        self.calls += 1; self.reads.append(path)
        return deepcopy(self.responses[path])
    def archive(self, artifact):
        self.calls += 1; self.reads.append(('archive', artifact['id']))
        return self.archives[artifact['id']]


def setup(monkeypatch):
    parts = composed(); col, baseline = parts[:2]
    company = compose(parts)
    company['projection']['companies'][0]['source_names'] = ['公司甲']
    company['projection_hash'] = canonical_hash(company['projection'])
    reference = col.retain('details/radar/company-reading.json', m.json_bytes(company))
    baseline['research']['radar_discovery'] = {
        'status': 'READ_OK', 'details': {'company_reading': reference},
        'projection_hash': company['projection_hash']}
    reseal(baseline)
    col.files['current-state.json'] = m.json_bytes(baseline)
    col.files['README.md'] = m.render_summary(baseline).encode() + b'\nORIGINAL_COMPANY_CONCEPT_NAV\n'
    col.now = lambda: NOW
    api = API(); col.api = api
    config = {'format': reading.FORMAT, 'enabled': True,
              'window': {k: v for k, v in PERIOD.items() if k != 'cutoff'}}
    for index, (kind, files) in enumerate((('news', news_files()), ('industry', industry_files())), 1):
        run_id, artifact_id = 100 + index, 300 + index
        zipped = pack(files)
        spec = {'run_id': run_id, 'artifact_id': artifact_id, 'bytes': len(zipped),
                'sha256': m.sha256(zipped), 'artifact_name': kind + '-synthetic',
                'workflow': '.github/workflows/' + kind + '-probe.yml',
                'head_branch': 'probe/synthetic', 'head_sha': 'b'*40}
        config[kind] = spec
        api.responses['actions/runs/' + str(run_id)] = {
            'id': run_id, 'head_sha': spec['head_sha'], 'head_branch': spec['head_branch'],
            'path': spec['workflow'], 'repository': {'full_name': m.REPOSITORY},
            'head_repository': {'full_name': m.REPOSITORY}, 'event': 'push', 'run_attempt': 1,
            'status': 'completed', 'conclusion': 'success',
            'created_at': '2026-09-20T03:00:00Z', 'updated_at': '2026-09-20T03:02:00Z'}
        artifact = {'id': artifact_id, 'name': spec['artifact_name'], 'expired': False,
            'size_in_bytes': len(zipped), 'digest': 'sha256:' + m.sha256(zipped),
            'workflow_run': {'id': run_id, 'head_sha': spec['head_sha']}}
        api.responses[f'actions/runs/{run_id}/artifacts?per_page=100'] = {'total_count': 1, 'artifacts': [artifact]}
        api.archives[artifact_id] = zipped
    def pinned(root, commit, path):
        assert commit == col.code_commit and path == reading.CONFIG
        return m.json_bytes(config)
    monkeypatch.setattr(base, 'git_file', pinned)
    return col, baseline, config


def report(col):
    return json.loads(col.files[reading.PREFIX + 'observations.json'])


def test_native_replay_retains_originals_and_preserves_all_old_products(monkeypatch):
    col, b, cfg = setup(monkeypatch); before = deepcopy(b); files = dict(col.files)
    value = reading.attach(col, b)
    m.validate_read_package(value)
    assert b == before and value['lanes'] == b['lanes']
    assert value['research']['radar_discovery'] == b['research']['radar_discovery']
    for name, raw in files.items():
        if name not in {'current-state.json', 'README.md'}:
            assert col.files[name] == raw
    p = report(col)['projection']
    assert p['company_context_status'] == 'SAME_READING_SAVED_CONTEXT'
    n = p['sections']['news']['result']['projection']
    assert len(n['observations']) == len(n['companies']) == 1
    assert n['companies'][0]['qualification'] == 'CONTEXT_ONLY'
    assert n['companies'][0]['question_status'] == 'NOT_FORMED'
    assert len(p['sections']['industry']['results']) == 3
    assert len(p['sections']['industry']['results'][0]['projection']['field_gaps']) == 2
    assert p['research_executions'] == p['market_requests'] == p['model_calls'] == 0
    assert api_reads(col) == 6
    for kind in ('news', 'industry'):
        ref = p['sections'][kind]['archive']
        assert col.files[ref['read_path']] == col.api.archives[cfg[kind]['artifact_id']]
        assert ref['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT'
    assert b'ORIGINAL_COMPANY_CONCEPT_NAV' in col.files['README.md']
    assert '<script>' not in col.files[reading.PREFIX + 'index.html'].decode()
    assert '&lt;script&gt;' in col.files[reading.PREFIX + 'index.html'].decode()
    assert '非每日采集' in col.files[reading.PREFIX + 'index.html'].decode()


def api_reads(col):
    return col.api.calls


@pytest.mark.parametrize('damage', ['expired', 'digest', 'bytes', 'raw-corrupt', 'head', 'repo', 'event', 'attempt', 'future'])
def test_bad_news_source_does_not_destroy_industry_or_choose_other_run(monkeypatch, damage):
    col, b, cfg = setup(monkeypatch)
    artifact = col.api.responses['actions/runs/101/artifacts?per_page=100']['artifacts'][0]
    run = col.api.responses['actions/runs/101']
    if damage == 'expired': artifact['expired'] = True
    elif damage == 'digest': artifact['digest'] = 'sha256:' + '0'*64
    elif damage == 'bytes': artifact['size_in_bytes'] += 1
    elif damage == 'raw-corrupt': col.api.archives[301] += b'corrupt'
    elif damage == 'head': run['head_sha'] = 'f'*40
    elif damage == 'repo': run['head_repository']['full_name'] = 'somebody/other'
    elif damage == 'event': run['event'] = 'workflow_dispatch'
    elif damage == 'attempt': run['run_attempt'] = 2
    else: run['updated_at'] = '2026-09-21T03:00:00Z'
    value = reading.attach(col, b)
    p = report(col)['projection']
    assert p['sections']['news']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert 'result' not in p['sections']['news']
    assert p['sections']['industry']['status'] == 'SAVED_SAMPLE_REBUILT'
    assert value['research']['external_radar']['status'] == 'PARTIAL_SAVED_READING'
    assert 301 not in col.archive_cache and 302 in col.archive_cache
    assert not any('latest' in str(path) for path in col.api.reads)


def test_budget_failure_stops_before_source_reads_and_preserves_baseline(monkeypatch):
    col, b, cfg = setup(monkeypatch)
    col.api.max_calls = len(col.files) + 7
    before = dict(col.files)
    value = reading.attach(col, b)
    assert col.api.calls == 0
    assert value['research']['external_radar']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert not any(path.startswith(reading.PREFIX) for path in col.files)
    assert value['lanes'] == b['lanes']
    for path in before:
        if path not in {'README.md', 'current-state.json'}:
            assert col.files[path] == before[path]


def test_retention_failure_rolls_back_archive_copies_and_added_files(monkeypatch):
    col, b, cfg = setup(monkeypatch); before = dict(col.files)
    monkeypatch.setattr(reading, 'render', lambda _: 'x' * 100000)
    monkeypatch.setattr(base, 'MAX_RETAINED_OUTPUT', sum(map(len, before.values())) + 50000)
    value = reading.attach(col, b)
    assert value['research']['external_radar']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert not col.archive_cache
    assert not any(path.startswith(reading.PREFIX) for path in col.files)


def test_disabled_config_leaves_original_reading_byte_for_byte(monkeypatch):
    col, b, cfg = setup(monkeypatch); cfg['enabled'] = False; before = dict(col.files)
    assert reading.attach(col, b) is b and col.files == before and col.api.calls == 0


def test_no_company_context_is_not_no_news(monkeypatch):
    col, b, cfg = setup(monkeypatch)
    b['research'].pop('radar_discovery'); reseal(b)
    col.files['README.md'] = m.render_summary(b).encode()
    value = reading.attach(col, b)
    p = report(col)['projection']
    assert p['company_source'] is None
    assert p['sections']['news']['result']['projection']['observations']
    assert p['company_context_status'].startswith('NO_READABLE')


def test_refresh_does_not_change_article_version_or_source_capture_clocks(monkeypatch):
    col, b, cfg = setup(monkeypatch); reading.attach(col, b)
    first = report(col)['projection']['sections']['news']
    col, b, cfg = setup(monkeypatch); col.now = lambda: '2026-09-20T05:00:00Z'
    reading.attach(col, b); second = report(col)['projection']['sections']['news']
    assert first['captured_through'] == second['captured_through']
    assert first['result']['projection']['observations'] == second['result']['projection']['observations']


def test_entry_requires_explicit_optin_and_uses_existing_collection(monkeypatch):
    col, b, cfg = setup(monkeypatch)
    extended = entry.Collector(col.api, col.code_commit, col.root, now=lambda: NOW)
    extended.files = dict(col.files); extended.include_radar_discovery = True
    monkeypatch.setattr(base.Collector, 'collect', lambda self, refresh: b)
    monkeypatch.setattr(reading.radar, 'attach', lambda collector, baseline: baseline)
    assert extended.collect({}) is b and col.api.calls == 0
    extended.include_external_radar = True
    value = extended.collect({})
    assert value['research']['external_radar']['status'] == 'READ_OK_WITH_DECLARED_GAPS'


def test_cli_external_flag_alone_rejected_before_api_or_secret(tmp_path):
    with pytest.raises(ValueError, match='requires the existing Radar composition'):
        entry.main(['--code-commit', 'a'*40, '--output', str(tmp_path/'out'), '--include-external-radar'])


def test_workflow_only_enables_reader_not_capture_or_new_trigger():
    path = Path('.github/workflows/current-state-read-entry.yml')
    text = path.read_text()
    assert text.count('--include-external-radar') == 1
    assert 'schedule:' not in text and 'HITHINK' not in text and 'DEEPSEEK' not in text
    assert 'docker ' not in text and 'newsnow-selfhost' not in text
    assert 'persist-credentials: false' in text and 'cancel-in-progress: false' in text


def test_config_and_projection_reject_authority_and_unknown_shape(monkeypatch):
    col, b, cfg = setup(monkeypatch)
    for bad in ({**cfg, 'score': 100}, {**cfg, 'enabled': 1}):
        with pytest.raises(ValueError): reading.validate_config(bad)
    reading.attach(col, b); bad = report(col)
    bad['projection']['investment_authority'] = 'TRADE'
    bad['projection_hash'] = canonical_hash(bad['projection'])
    with pytest.raises(ValueError): reading.render(bad)
