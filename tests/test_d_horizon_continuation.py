"""Exact retained-text delivery; synthetic I/O is not source or investment proof."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import d_horizon_follow_up as h
from decision_kernel.runtime import stock_market_inputs as p

AT = '2026-10-05T09:00:00+00:00'
CUTOFF = '2026-10-05T06:15:55Z'
LIMIT = 20 * 1024 * 1024


def descriptor(path, raw):
    return {'read_path': path, 'bytes': len(raw), 'sha256': model.sha256(raw),
            'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}


@pytest.fixture
def saved(monkeypatch):
    case = {'id': 'original-case', 'record_id': 'original-record', 'symbol': '603986.SH',
            'frozen_at': '2026-10-04T01:03:53Z', 'long_research_deadline': '2027-09-02',
            'analyst_review_by': '2026-11-30', 'contract_hash': 'f' * 64,
            'anchor_session': None, 'checkpoints': [{'period': 5, 'change': None}],
            'opportunity_established': None, 'opportunity_probability': None}
    parent = {'id': case['record_id'], 'source': {'path': 'docs/original.md', 'ref': 'b' * 40}}
    excerpts = ['Retained economic hypothesis; opportunity not established.',
                'A lower margin can coexist with higher gross profit.',
                'Missing data do not turn into an adverse operating result.']
    body = ('/blob/' + parent['source']['ref'] + '/' + parent['source']['path'] + '\n' +
            '\n'.join([case['frozen_at'], case['long_research_deadline'],
                       case['analyst_review_by'], CUTOFF, *excerpts])).encode()
    source = {**descriptor('sources/continuation.md', body),
              'path': 'docs/continuation.md', 'ref': 'c' * 40}
    record = {'id': 'continuation-record', 'case': case['symbol'],
              'use': 'RETAINED_RESEARCH_DOCUMENT', 'archive': {'format': 'RETAINED_FILES'},
              'source': source}
    item = {'case_id': case['id'], 'record_id': record['id'],
            'document_sha256': model.sha256(body), 'research_cutoff': CUTOFF, 'excerpts': excerpts}
    report = {'version': h.VERSION, 'checked_at': AT, 'code_commit': 'a' * 40,
              'cases': [case], 'previous_reading_gap': None,
              'latest_price_status': 'PRICE_INPUT_UNAVAILABLE_NOT_QUIET',
              'using_prior_price_source': True, 'new_source_requests': 0, **model.AUTHORITY}
    report['report_hash'] = canonical_hash(report)
    raw = p.dumps(report)
    baseline = model.assemble(code_commit='a' * 40, checked_at=AT, check_started_at=AT,
        lanes={'stock': {'gaps': ['retained source failure']}}, capabilities=[], refresh_identity={},
        research={'handoffs': {'active': []}, h.KEY: descriptor(h.PATH, raw),
                  'records': [{'id': 'human-action-must-remain'}]})
    collector = SimpleNamespace(files={h.PATH: raw, 'current-state.json': model.read_package_bytes(baseline),
        'README.md': b'Original frozen case and price section\n', 'sources/keep.txt': b'old evidence'},
        sources={}, api=SimpleNamespace(calls=0), now=lambda: AT)
    def read(spec):
        assert spec == {k: source[k] for k in ('path', 'ref', 'git_blob')}
        collector.api.calls += 1
        collector.files[source['read_path']] = body
        collector.sources['continuation'] = source
        return body, deepcopy(source)
    collector.source = read
    reserves = []
    def reserve(*args, **kwargs):
        reserves.append(kwargs)
    monkeypatch.setitem(sys.modules, 'decision_kernel.runtime.institutional_radar_reading',
                        SimpleNamespace(_reserve=reserve))
    return SimpleNamespace(collector=collector, baseline=baseline, report=report, item=item, body=body,
        registry={parent['id']: parent, record['id']: record}, record=record, reserves=reserves)


def apply(s, items=None, limit=LIMIT):
    return h._attach_continuations(s.collector, s.baseline, s.report,
        [s.item] if items is None else items, s.registry, retained_limit=limit)


def result(s):
    return p.loads(s.collector.files[h.PATH])


def assert_core_preserved(s, output):
    model.validate_read_package(output)
    h._bound(s.collector.files[h.PATH], output['research'][h.KEY])
    saved = result(s)
    assert saved['cases'] == s.report['cases']
    assert saved['latest_price_status'] == s.report['latest_price_status']
    assert saved['using_prior_price_source'] is True
    assert saved['report_hash'] == canonical_hash({k: v for k, v in saved.items() if k != 'report_hash'})
    assert output['lanes'] == s.baseline['lanes']
    assert output['research']['records'] == s.baseline['research']['records']
    assert s.collector.files['sources/keep.txt'] == b'old evidence'


def test_exact_retained_excerpts_reach_normal_reading_without_changing_case(saved):
    original = deepcopy(saved.baseline), deepcopy(saved.report), deepcopy(saved.item)
    output = apply(saved)
    assert_core_preserved(saved, output)
    row = result(saved)['economic_continuations'][0]
    assert row['status'] == 'RETAINED_CONTINUATION_READ_OK'
    assert row['source']['ref'] == 'c' * 40
    assert row['research_cutoff'] == CUTOFF and row['read_at'] == AT
    assert row['original_contract_hash'] == saved.report['cases'][0]['contract_hash']
    assert row['excerpts'] == saved.item['excerpts']
    assert all(row[key] == 'NONE' for key in model.AUTHORITY)
    reading = saved.collector.files['README.md'].decode()
    assert reading.startswith('Original frozen case and price section\n')
    assert all(excerpt in reading for excerpt in saved.item['excerpts'])
    assert 'sources/continuation.md' in reading and '不是本轮新研究' in reading
    assert original == (saved.baseline, saved.report, saved.item)
    assert saved.collector.api.calls == 1
    assert any(r.get('calls') == 1 and r.get('files') == 3 for r in saved.reserves)
    assert any('replacements' in r for r in saved.reserves)


def test_old_config_has_byte_identical_output_and_no_extra_read(saved):
    files = dict(saved.collector.files)
    output = apply(saved, [])
    assert output is saved.baseline and saved.collector.files == files
    assert saved.collector.api.calls == 0 and saved.reserves == []


@pytest.mark.parametrize('damage', ['unknown_case', 'unknown_record', 'wrong_symbol', 'wrong_use',
    'wrong_format', 'mutable_ref', 'wrong_digest', 'invented_excerpt', 'empty_excerpt',
    'no_timezone', 'future_cutoff', 'before_freeze', 'cutoff_not_in_body', 'wrong_predecessor',
    'wrong_long_deadline', 'wrong_review_date'])
def test_local_rejection_does_not_discard_frozen_case_or_other_products(saved, damage):
    if damage == 'unknown_case': saved.item['case_id'] = 'not-a-case'
    elif damage == 'unknown_record': saved.item['record_id'] = 'not-a-record'
    elif damage == 'wrong_symbol': saved.record['case'] = '600000.SH'
    elif damage == 'wrong_use': saved.record['use'] = 'HUMAN_DECISION_CHECKPOINT'
    elif damage == 'wrong_format': saved.record['archive']['format'] = 'EXECUTABLE'
    elif damage == 'mutable_ref': saved.record['source']['ref'] = 'main'
    elif damage == 'wrong_digest': saved.item['document_sha256'] = 'e' * 64
    elif damage == 'invented_excerpt': saved.item['excerpts'] = ['Buy immediately; invented text']
    elif damage == 'empty_excerpt': saved.item['excerpts'] = ['  ']
    elif damage == 'no_timezone': saved.item['research_cutoff'] = '2026-10-05T06:15:55'
    elif damage == 'future_cutoff': saved.item['research_cutoff'] = '2026-10-06T00:00:00Z'
    elif damage == 'before_freeze': saved.item['research_cutoff'] = '2026-10-03T00:00:00Z'
    elif damage == 'cutoff_not_in_body': saved.item['research_cutoff'] = '2026-10-05T06:15:54Z'
    elif damage == 'wrong_predecessor': saved.registry['original-record']['source']['ref'] = 'd' * 40
    elif damage == 'wrong_long_deadline': saved.report['cases'][0]['long_research_deadline'] = '2028-09-02'
    elif damage == 'wrong_review_date': saved.report['cases'][0]['analyst_review_by'] = '2026-12-31'
    output = apply(saved)
    assert_core_preserved(saved, output)
    row = result(saved)['economic_continuations'][0]
    assert row['status'] == 'CONTINUATION_UNAVAILABLE_CORE_PRESERVED'
    assert 'error_type' in row and 'source' not in row and 'excerpts' not in row
    assert 'sources/continuation.md' not in saved.collector.files
    assert saved.collector.sources == {}
    assert saved.collector.api.calls <= 1
    assert '后继解释读取缺口' in saved.collector.files['README.md'].decode()


@pytest.mark.parametrize('damage', ['returned_bytes', 'returned_descriptor', 'denial'])
def test_actual_read_failure_is_not_retried_or_substituted(saved, damage):
    original = saved.collector.source
    def read(spec):
        raw, desc = original(spec)
        if damage == 'denial': raise PermissionError('synthetic explicit denial')
        if damage == 'returned_bytes': return raw + b'corruption', desc
        return raw, {**desc, 'sha256': '0' * 64}
    saved.collector.source = read
    output = apply(saved)
    assert_core_preserved(saved, output)
    assert result(saved)['economic_continuations'][0]['status'] == 'CONTINUATION_UNAVAILABLE_CORE_PRESERVED'
    assert saved.collector.api.calls == 1 and saved.collector.sources == {}


@pytest.mark.parametrize('items', [None, {}, 'not a list', [None], [{'case_id': 1}]])
def test_malformed_optional_selection_is_isolated(saved, items):
    output = h._attach_continuations(saved.collector, saved.baseline, saved.report, items,
                                    saved.registry, retained_limit=LIMIT)
    assert_core_preserved(saved, output)
    assert result(saved)['economic_continuations'][0]['status'] == 'CONTINUATION_UNAVAILABLE_CORE_PRESERVED'
    assert saved.collector.api.calls == 0


def test_duplicate_selection_does_not_choose_newest_automatically(saved):
    output = apply(saved, [saved.item, deepcopy(saved.item)])
    assert_core_preserved(saved, output)
    assert saved.collector.api.calls == 0


def test_source_budget_failure_is_local_and_never_spends_a_call(saved, monkeypatch):
    def reserve(*args, **kwargs):
        if kwargs.get('calls'): raise ValueError('synthetic source quota exhausted')
    monkeypatch.setattr(sys.modules['decision_kernel.runtime.institutional_radar_reading'], '_reserve', reserve)
    output = apply(saved)
    assert_core_preserved(saved, output)
    assert result(saved)['economic_continuations'][0]['status'] == 'CONTINUATION_UNAVAILABLE_CORE_PRESERVED'
    assert saved.collector.api.calls == 0


def test_optional_retention_capacity_rolls_back_new_document_not_old_results(saved):
    original_size = sum(map(len, saved.collector.files.values()))
    # A core-plus-gap result fits; the larger source plus excerpts does not.
    output = apply(saved, limit=original_size + 1000)
    assert_core_preserved(saved, output)
    assert result(saved)['economic_continuations'][0]['status'] == 'CONTINUATION_UNAVAILABLE_CORE_PRESERVED'
    assert 'sources/continuation.md' not in saved.collector.files
    assert sum(map(len, saved.collector.files.values())) <= original_size + 1000
    assert saved.collector.api.calls == 1


def test_no_room_for_gap_returns_original_core_byte_for_byte(saved):
    before = dict(saved.collector.files)
    output = apply(saved, limit=sum(map(len, before.values())))
    assert output is saved.baseline and saved.collector.files == before
    assert saved.collector.sources == {} and saved.collector.api.calls == 1


def test_one_unavailable_case_does_not_hide_an_independent_readable_case(saved):
    invalid = {**deepcopy(saved.item), 'case_id': 'unavailable-case'}
    output = apply(saved, [invalid, saved.item])
    assert_core_preserved(saved, output)
    assert [r['status'] for r in result(saved)['economic_continuations']] == [
        'CONTINUATION_UNAVAILABLE_CORE_PRESERVED', 'RETAINED_CONTINUATION_READ_OK']
    assert saved.collector.api.calls == 1


def test_existing_research_excerpts_are_not_executed(saved):
    # Exact source words remain data even when they look like commands.
    assert result(saved)['cases'][0]['opportunity_established'] is None
    output = apply(saved)
    assert_core_preserved(saved, output)
    assert result(saved)['cases'][0]['opportunity_probability'] is None
    assert result(saved)['new_source_requests'] == 0


def test_real_config_preserves_original_case_hash_and_selects_746():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / h.CONFIG).read_bytes())
    assert canonical_hash(config['cases'][0]) == '0ea868b1888753dce6d1a9021cf69116d8cb30b78bcb6b01f194077636450656'
    item = config['continuations'][0]
    assert item['case_id'] == config['cases'][0]['id']
    assert item['record_id'] == 'd-mu-gigadevice-economic-bridge-20261005'
    assert item['document_sha256'] == '1a7755c6dc9217aaa6003a7cf600fa6d1d04c2cb23f5e0935aa191a69c44faa0'
    assert any('毛利率下滑不一定是经营假设失败' in text for text in item['excerpts'])
    assert any('覆盖补充' in text for text in item['excerpts'])


def test_integration_existing_attach_invokes_continuation_after_core(monkeypatch):
    from test_d_horizon_follow_up import seeded
    collector, root = seeded(monkeypatch)
    original = collector.source
    def source(spec):
        raw, desc = original(spec)
        if spec['path'] == h.CONFIG:
            config = p.loads(raw)
            config['continuations'] = [{'case_id': 'case', 'record_id': 'missing'}]
            raw = p.dumps(config)
            desc = descriptor(desc['read_path'], raw)
            collector.files[desc['read_path']] = raw
        return raw, desc
    collector.source = source
    output = h.attach(collector, root, retained_limit=LIMIT)
    model.validate_read_package(output)
    report = p.loads(collector.files[h.PATH])
    assert report['cases'][0]['checkpoints'][0]['change'] == '0.100000000000'
    assert report['economic_continuations'][0]['status'] == 'CONTINUATION_UNAVAILABLE_CORE_PRESERVED'
    assert output['lanes'] == root['lanes']


@pytest.mark.parametrize('occupied', [0, 59, 60])
def test_real_collector_source_uses_bounded_optional_scope(saved, tmp_path, occupied):
    from decision_kernel.runtime import current_state_delivery as delivery
    assert delivery.MAX_SOURCE_FILES == 60
    calls = []
    source = saved.record['source']
    def read_file(path, ref):
        calls.append((path, ref))
        return saved.body
    api = SimpleNamespace(calls=0, file=read_file)
    collector = delivery.Collector(api, 'a' * 40, tmp_path, now=lambda: AT)
    collector.files = dict(saved.collector.files)
    collector.sources = {(f'docs/base-{i}.md', 'a' * 40): (b'baseline', {})
                         for i in range(occupied)}
    before = deepcopy(collector.sources)
    saved.collector = collector
    output = apply(saved)
    assert_core_preserved(saved, output)
    row = result(saved)['economic_continuations'][0]
    assert row['status'] == 'RETAINED_CONTINUATION_READ_OK'
    assert row['source']['ref'] == source['ref']
    assert row['source']['path'] == source['path']
    assert calls == [(source['path'], source['ref'])]
    assert collector.sources == before
    assert delivery.MAX_SOURCE_FILES == 60


def test_real_collector_full_baseline_rejects_unscoped_source(saved, tmp_path):
    from decision_kernel.runtime import current_state_delivery as delivery
    api = SimpleNamespace(calls=0, file=lambda *a: pytest.fail('no read after full baseline'))
    collector = delivery.Collector(api, 'a' * 40, tmp_path, now=lambda: AT)
    collector.sources = {(f'docs/base-{i}.md', 'a' * 40): (b'baseline', {})
                         for i in range(delivery.MAX_SOURCE_FILES)}
    with pytest.raises(ValueError, match='source registry bound'):
        collector.source(saved.record['source'])
    assert len(collector.sources) == 60


def test_real_source_binding_failure_restores_full_baseline(saved, tmp_path):
    from decision_kernel.runtime import current_state_delivery as delivery
    calls = []
    def read_file(path, ref):
        calls.append((path, ref))
        return saved.body + b' changed'
    collector = delivery.Collector(SimpleNamespace(calls=0, file=read_file), 'a'*40,
                                   tmp_path, now=lambda: AT)
    collector.files = dict(saved.collector.files)
    collector.sources = {(f'docs/base-{i}.md', 'a'*40): (b'baseline', {}) for i in range(60)}
    before_sources = deepcopy(collector.sources)
    before_files = set(collector.files)
    saved.collector = collector
    output = apply(saved)
    assert_core_preserved(saved, output)
    row = result(saved)['economic_continuations'][0]
    assert row['status'] == 'CONTINUATION_UNAVAILABLE_CORE_PRESERVED'
    assert row['diagnostic'] == {'code': 'SOURCE_BLOB_MISMATCH', 'baseline_source_count': 60}
    assert collector.sources == before_sources and set(collector.files) == before_files
    assert len(calls) == 1


def test_source_cache_hit_is_preserved_without_new_read(saved, tmp_path):
    from decision_kernel.runtime import current_state_delivery as delivery
    collector = delivery.Collector(SimpleNamespace(calls=0, file=lambda *a: pytest.fail('cache miss')),
                                   'a'*40, tmp_path, now=lambda: AT)
    collector.files = dict(saved.collector.files)
    source = saved.record['source']
    collector.files[source['read_path']] = saved.body
    collector.sources = {(source['path'], source['ref']): (saved.body, source)}
    before = deepcopy(collector.sources)
    saved.collector = collector
    output = apply(saved)
    assert_core_preserved(saved, output)
    assert result(saved)['economic_continuations'][0]['status'] == 'RETAINED_CONTINUATION_READ_OK'
    assert collector.sources == before
