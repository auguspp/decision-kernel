"""Actual same-PDF note loaders run with synthetic Git, without PDF/model network."""
from copy import deepcopy
import json
import socket

import pytest

from decision_kernel.runtime import disclosure_source_reading as pages
from decision_kernel.runtime import stock_quick_continuation as resume
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import saved_research_once as once
from test_stock_quick_continuation import setup, CODE, NOW


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('checkpoint review tests cannot use live networking')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def note_path(case):
    return next(path for path in case.files[CODE] if path.startswith(pages.REVIEW_ROOT))


def test_host_reads_both_versions_of_retained_note_before_one_quick(tmp_path, monkeypatch):
    case = setup(tmp_path, monkeypatch)
    path = note_path(case)
    refs = {ref for ref, files in case.files.items() if path in files}
    assert len(refs) == 2
    reads = []
    original = case.api.file
    def read(p, ref):
        if p == path: reads.append(ref)
        return original(p, ref)
    case.api.file = read
    result = host.run_question(**case.args)
    assert result['status'] == 'VALIDATED_FUNNEL_RESULT', json.dumps(result)
    assert set(reads) == refs and all(reads.count(ref) >= 2 for ref in refs)
    assert case.calls == ['quick'] and result['pre_model_calls'] == 0


@pytest.mark.parametrize('damage', ['missing', 'changed', 'added', 'readback', 'future-commit', 'symlink', 'truncated'])
def test_current_review_changes_are_not_hidden_by_lazy_loader(tmp_path, monkeypatch, damage):
    case = setup(tmp_path, monkeypatch)
    path = note_path(case)
    if damage == 'missing':
        del case.files[CODE][path]
    elif damage == 'changed':
        case.files[CODE][path] += b' '
    elif damage == 'added':
        case.files[CODE][path.replace('page-100.json', 'page-101.json')] = case.files[CODE][path]
    elif damage == 'future-commit':
        case.meta[CODE]['committer']['date'] = '2030-01-01T00:00:00Z'
    elif damage == 'readback':
        original = case.api.file
        def read(p, ref):
            raw = original(p, ref)
            if p == path and ref == CODE:
                note = json.loads(raw); note['text'] += ' SYNTHETIC changed reading'
                return once.raw(note)
            return raw
        case.api.file = read
    else:
        original = case.api.get
        def get(endpoint):
            value = original(endpoint)
            if endpoint.startswith('git/trees/' + CODE):
                if damage == 'truncated': value['truncated'] = True
                else: next(r for r in value['tree'] if r['path'] == path)['mode'] = '120000'
            return value
        case.api.get = get
    before = deepcopy(case.files)
    result = host.run_question(**case.args)
    assert result['status'] == 'NOT_EXECUTED', json.dumps(result)
    assert not case.calls and not case.writes and case.files == before


def test_note_changed_after_launch_is_rechecked_before_egress(tmp_path, monkeypatch):
    case = setup(tmp_path, monkeypatch)
    path = note_path(case)
    original = once.Retainer.native
    def write(owner, method, endpoint, body):
        result = original(owner, method, endpoint, body)
        if endpoint.endswith('/launch.json'):
            case.files[CODE][path] += b' '
        return result
    monkeypatch.setattr(once.Retainer, 'native', write)
    result = host.run_question(**case.args)
    assert any(p.endswith('/launch.json') for p in case.writes), json.dumps(result)
    assert result['status'] == 'EXECUTION_GAP', json.dumps(result)
    assert result['quick_model_attempts'] == 0 and case.calls == []
