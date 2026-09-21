"""Same-reader composition, native retention/hash/budget, and no network or writes."""
from copy import deepcopy
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import stock_batch_disposition as d
from decision_kernel.runtime import reviewed_question_reading as reader
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import current_state_delivery_with_odds_watch as production
from decision_kernel.runtime import research_archive_index as index
from decision_kernel.runtime import stock_research_reading as stock_reader
from test_stock_batch_disposition import example, NOW, ROOT


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('No acquisition, model, dispatch or source write permitted')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def setup(tmp_path, monkeypatch):
    review, scope = example()
    scope['status'] = 'SAVED_STOCK_SCOPE_WITH_RESEARCH_RELATIONS_NOT_FORMAL_QUESTION_REVIEW'
    work = {'status': 'READ_OK', 'items': [], 'scope': reader.PREFIX, **d.model.AUTHORITY}
    report = {'format': 'reviewed-question-reading-v1', 'stock_review_scope': scope,
              'question_work': work, 'research_execution': 'NOT_EXECUTED', **d.model.AUTHORITY}
    body = d.model.json_bytes(report)
    detail = reader.render(report).encode()
    research = {'handoffs': {'active': []}, 'records': [], 'gaps': [],
                'stock_business_work': {'items': [], 'status': 'READ_OK'},
                'reviewed_question_work': {'status': 'READ_OK', 'execution_count': 0,
                    'structured': d._meta(reader.REPORT, body), 'details': d._meta(reader.DETAIL, detail)}}
    baseline = d.model.assemble(code_commit='a'*40, checked_at=NOW, check_started_at=NOW,
        lanes={'stock': {'gaps': ['PARTIAL_COVERAGE'], 'health': 'LATEST_ATTEMPT_SUCCEEDED'}},
        research=research, capabilities=[], refresh_identity={})
    api = SimpleNamespace(calls=0, max_calls=delivery.MAX_API_CALLS + stock_reader.EXTRA_API_CALLS)
    c = delivery.Collector(api, 'a'*40, tmp_path, now=lambda: NOW)
    c.files = {'current-state.json': d.model.read_package_bytes(baseline), 'README.md': b'original navigation\n',
               reader.REPORT: body, reader.DETAIL: detail, 'sources/old-failure.json': b'original failure'}
    c.sources = {}
    monkeypatch.setattr(delivery, 'git_file', lambda root, code, path: d.model.json_bytes(review))
    return c, baseline, review, report


def test_native_composition_retains_original_scope_failure_and_exact_source(tmp_path, monkeypatch):
    c, baseline, review, original = setup(tmp_path, monkeypatch)
    before = deepcopy(baseline)
    result = d.attach(c, baseline)
    report = json.loads(c.files[reader.REPORT])
    assert report['stock_review_scope'] == original['stock_review_scope']
    assert report['question_work'] == original['question_work']
    assert result['lanes'] == baseline['lanes'] and result['pending'] == []
    assert c.files['sources/old-failure.json'] == b'original failure'
    assert c.api.calls == 0 and c.sources == {} and baseline == before
    summary = result['research']['reviewed_question_work']
    assert summary['execution_count'] == 0
    value = summary['saved_batch_disposition']
    assert value['status'] == d.RECORDED and 'items' not in value
    assert c.files[value['source']['read_path']] == d.model.json_bytes(review)
    for spec in (summary['structured'], summary['details']):
        assert spec == d._meta(spec['read_path'], c.files[spec['read_path']])
    assert b'original navigation' in c.files['README.md']
    assert len(c.files['current-state.json']) <= 192*1024
    d.model.validate_read_package(result)
    assert json.loads(c.files['current-state.json']) == result


@pytest.mark.parametrize('case', ['absent', 'duplicate-json-key', 'invalid-json', 'oversize', 'omit-row', 'wrong-root', 'future'])
def test_source_problem_is_visible_gap_not_zero_or_hidden_question_result(tmp_path, monkeypatch, case):
    c, baseline, review, original = setup(tmp_path, monkeypatch)
    if case == 'omit-row': review['items'].pop()
    if case == 'wrong-root': review['items'][2]['existing_execution_id'] += '-new'
    if case == 'future': review['reviewed_at'] = '2027-01-01T00:00:00Z'
    def read(*args):
        if case == 'absent': raise ValueError('unavailable file')
        if case == 'duplicate-json-key': return b'{"format":"x","format":"y"}'
        if case == 'invalid-json': return b'not JSON'
        if case == 'oversize': return b' ' * (d.MAX_BYTES + 1)
        return d.model.json_bytes(review)
    monkeypatch.setattr(delivery, 'git_file', read)
    result = d.attach(c, baseline)
    out = json.loads(c.files[reader.REPORT])
    assert out['question_work'] == original['question_work']
    assert out['stock_review_scope'] == original['stock_review_scope']
    assert out['saved_batch_disposition']['status'] == d.GAP
    assert out['saved_batch_disposition']['applied'] is False
    assert 'new_question_selected_count' not in out['saved_batch_disposition']
    assert result['research']['reviewed_question_work']['execution_count'] == 0
    assert result['lanes'] == baseline['lanes']
    d.model.validate_read_package(result)


def test_stale_batch_retains_history_without_applying_zero_to_new_batch(tmp_path, monkeypatch):
    c, baseline, review, _ = setup(tmp_path, monkeypatch)
    review['batch_id'] = 'c'*64
    result = d.attach(c, baseline)
    value = result['research']['reviewed_question_work']['saved_batch_disposition']
    assert value['status'] == d.STALE and value['applied'] is False
    assert value['source']['read_path'] in c.files
    assert 'new_question_selected_count' not in value


@pytest.mark.parametrize('kind', ['retained-bytes', 'api', 'shared-files'])
def test_original_budgets_cannot_be_expanded_or_partial_projection_published(tmp_path, monkeypatch, kind):
    c, baseline, _, _ = setup(tmp_path, monkeypatch)
    before = dict(c.files)
    if kind == 'retained-bytes': monkeypatch.setattr(delivery, 'MAX_RETAINED_OUTPUT', 1)
    elif kind == 'api': c.api.calls = c.api.max_calls
    else: monkeypatch.setattr(stock_reader, 'MAX_STOCK_SOURCE_FILES', 0)
    if kind == 'shared-files':
        result = d.attach(c, baseline)
        assert result['research']['reviewed_question_work']['saved_batch_disposition']['status'] == d.GAP
        assert not any(p.endswith('/stock-batch-disposition.json') for p in c.files)
    else:
        with pytest.raises(ValueError): d.attach(c, baseline)
        assert c.files == before


def test_report_tamper_is_not_resealed_as_valid(tmp_path, monkeypatch):
    c, baseline, _, _ = setup(tmp_path, monkeypatch)
    c.files[reader.REPORT] += b' '
    before = dict(c.files)
    with pytest.raises(ValueError, match='report binding'):
        d.attach(c, baseline)
    assert c.files == before


def test_original_question_reader_gap_is_not_overwritten(tmp_path, monkeypatch):
    c, baseline, _, _ = setup(tmp_path, monkeypatch)
    research = deepcopy(baseline['research'])
    research['reviewed_question_work'] = {'status': 'UNAVAILABLE_OR_REJECTED'}
    baseline = d.model.assemble(code_commit='a'*40, checked_at=NOW, check_started_at=NOW,
        lanes=baseline['lanes'], research=research, capabilities=[], refresh_identity={})
    before = dict(c.files)
    assert d.attach(c, baseline) is baseline and c.files == before


def archive_entry():
    return index.project({'id': 'same-root-r3', 'case': '000920.SZ', 'use': 'RETAINED_RESEARCH_DOCUMENT',
        'purpose_note': 'Synthetic retained progress; no body read.', 'read_policy': index.POLICY,
        'archive_source': {'path': 'docs/readings/synthetic-progress/workpaper.md', 'ref': 'd'*40,
            'git_blob': 'e'*40, 'sha256': 'f'*64, 'bytes': 10},
        'archive': {'format': 'RESEARCH_PROGRESS', 'expected_sha256': 'f'*64, 'question_id': ROOT}})


@pytest.mark.parametrize('damage', [None, 'case', 'question', 'foreign-repository', 'missing', 'duplicate'])
def test_progress_links_reuse_validated_same_question_locators_only(damage):
    review, scope = example()
    review['items'][2]['progress_record_ids'] = ['same-root-r3']
    entry = archive_entry()
    if damage == 'case': entry['case'] = '600276.SH'
    if damage == 'question': entry['archive']['question_id'] = 'different-question'
    if damage == 'foreign-repository': entry['source']['repository'] = 'foreign/repo'
    entries = [] if damage == 'missing' else [entry]
    if damage == 'duplicate': entries.append(deepcopy(entry))
    if damage:
        with pytest.raises((ValueError, KeyError)): d.project(review, scope, entries, NOW)
    else:
        out = d.project(review, scope, entries, NOW)
        link = out['items'][2]['progress_locators'][0]
        assert link['url'] == index.entry_url(entry)
        assert link['meaning'] == 'REGISTERED_LOCATOR_NOT_BODY_READ_OR_ACCEPTED'


def test_source_reason_is_escaped_not_executable_markdown():
    review, scope = example()
    review['items'][0]['reason'] = '<script>alert(1)</script> [run](https://example.invalid)'
    text = d.render(d.project(review, scope, [], NOW))
    assert '<script>' not in text and '[run](' not in text
    assert '&lt;script&gt;' in text and '不是已穷尽经济问题' in text


def test_normal_existing_collector_composes_disposition_without_new_flag(tmp_path, monkeypatch):
    c, baseline, _, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(delivery.Collector, 'collect', lambda self, refresh: baseline)
    monkeypatch.setattr(reader, 'attach', lambda self, payload: payload)
    c.__class__ = production.Collector
    c.include_reviewed_questions = True
    result = c.collect({})
    assert result['research']['reviewed_question_work']['saved_batch_disposition']['status'] == d.RECORDED
    assert c.api.calls == 0


def test_real_saved_declaration_is_bounded_and_has_no_execution_selector():
    raw = Path(d.PATH).read_bytes()
    assert len(raw) <= d.MAX_BYTES
    saved = d.identity._json(raw)
    assert saved['question_source'] is None and len(saved['items']) == 6
    assert saved['batch_id'] == 'a5f7fb0222fc80fa377dc4ea923637750785e8859f57b493eb0bafa887b9f518'
    assert [r['thscode'] for r in saved['items']] == [
        '002632.SZ', '600127.SH', '688066.SH', '000920.SZ', '000019.SZ', '603268.SH']
    assert all(r['disposition'] in d.CATEGORIES for r in saved['items'])
    assert all(saved[k] == v for k, v in d.model.AUTHORITY.items())
