"""Explicit settled-403 continuation controls; no source/model/Git network writes."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import socket

import pytest

spec = importlib.util.spec_from_file_location('r4_resume403', Path(__file__).parents[1] / 'experiments/r4_2_resume403.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Resume control tests cannot access a network')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def parent_fixture(monkeypatch, damage=None):
    usage = dict(http_status=403, error_type='PermissionDeniedError', physical_sends=1,
                 response_received=False, request_id='029a79da-308f-4c67-a316-7ec61e7a937f',
                 arm='O', stage='PRE')
    launch = dict(id=r.e.EXPERIMENT, run_id='35877859341')
    receipt = dict(experiment=r.e.EXPERIMENT, model_requests_started=1, stopped_early=True,
                   records=[{**usage, 'ticker': '600362'}], samples=list(r.e.SAMPLES))
    if damage == 'successful_response': usage['response_received'] = True
    elif damage == 'other_status': usage['http_status'] = 500
    elif damage == 'uncertain_error': usage['error_type'] = 'APITimeoutError'
    elif damage == 'wrong_request': usage['request_id'] = 'different'
    elif damage == 'different_arm': usage['arm'] = 'S0'
    elif damage == 'another_run': launch['run_id'] = '2'
    elif damage == 'new_experiment': receipt['experiment'] = 'new-id'
    elif damage == 'already_more_calls': receipt['model_requests_started'] = 2
    elif damage == 'extra_result': receipt['records'].append(deepcopy(receipt['records'][0]))
    elif damage == 'different_samples': receipt['samples'] = list(reversed(receipt['samples']))
    elif damage == 'not_stopped': receipt['stopped_early'] = False
    if damage in {'successful_response', 'other_status', 'uncertain_error', 'wrong_request', 'different_arm'}:
        receipt['records'] = [{**usage, 'ticker': '600362'}]
    data = dict(zip(r.PARENT_HASHES, map(r.e.once.raw, (launch, receipt, usage)), strict=True))
    monkeypatch.setattr(r, 'PARENT_HASHES', {key: r.e.once.sha(value) for key, value in data.items()})
    class API:
        def get(self, path):
            assert path == 'git/ref/heads/' + r.e.WORK_REF
            return {'object': {'sha': r.PARENT if damage != 'head_changed' else 'other-head'}}
        def file(self, path, ref):
            assert ref == r.PARENT and path.startswith(r.e.PREFIX)
            body = data[path[len(r.e.PREFIX):]]
            return body + b' ' if damage == 'changed_bytes' else body
    return API(), usage


def test_exact_failed_request_is_recoverable_without_erasing_history(monkeypatch):
    api, usage = parent_fixture(monkeypatch)
    assert r.check_parent(api) == usage
    assert r.CHILD == 'continuations/permission-retry-1/'
    assert r.e.EXPERIMENT == 'r4-2-sub2api-20260923-v1'
    assert r.e.WORK_REF == 'research-eval/' + r.e.EXPERIMENT


@pytest.mark.parametrize('damage', ['successful_response', 'other_status', 'uncertain_error',
    'wrong_request', 'different_arm', 'another_run', 'new_experiment', 'already_more_calls',
    'extra_result', 'different_samples', 'not_stopped', 'head_changed', 'changed_bytes'])
def test_no_retry_of_changed_successful_or_unknown_work(monkeypatch, damage):
    api, _ = parent_fixture(monkeypatch, damage)
    with pytest.raises(ValueError):
        r.check_parent(api)


def controls(monkeypatch, mode=None):
    samples = [(s, (None, {'ticker': s['ticker']}, {})) for s in r.e.SAMPLES]
    first = {'discovery_observation': {'ticker': '600362'}, 'stage': 'PRE'}
    previous = {'prompt_sha256': r.e.once.sha(r.e.once.raw(first)),
                'pre_send': {'request_sha256': 'same-exact-request'}, 'request_id': 'retained-403-id'}
    monkeypatch.setattr(r.e, 'parameters', lambda *args: {})
    monkeypatch.setattr(r.e, 'preview', lambda *args: {'request_sha256':
        'changed' if mode == 'preview_changed' else 'same-exact-request'})
    def arms(packet, discovery, context, out, *, send):
        rows = []
        plan = [('O', 'PRE'), ('O', 'QUICK'), ('S0', 'QUICK'), ('S1', 'QUICK')]
        if mode == 'duplicate': plan[1] = plan[0]
        for arm, stage in plan:
            prompt = {'discovery_observation': discovery, 'stage': stage}
            if mode == 'prompt_changed': prompt['extra'] = 'changed'
            _, row = send(prompt, None, arm, out / arm / stage)
            rows.append(row)
            if row.get('stop_batch'): return rows, True
        return rows, False
    monkeypatch.setattr(r.e, 'run_arms', arms)
    calls = []
    def sender(prompt, model, arm, destination):
        calls.append((prompt['discovery_observation']['ticker'], arm, prompt['stage']))
        return None, {'physical_sends': 1, 'stop_batch': mode == 'denied_again'}
    return samples, previous, calls, sender


def test_one_replacement_plus_original_unrun_arms_count_the_first_failure(tmp_path, monkeypatch):
    samples, previous, calls, sender = controls(monkeypatch)
    rows, stop = r.run_remaining(samples, tmp_path, previous, send=sender)
    assert not stop and len(calls) == len(rows) == 8 and len(set(calls)) == 8
    assert sum(x['physical_sends'] for x in rows) + 1 == 9
    assert [x['replaces_request_id'] for x in rows] == ['retained-403-id'] + [None] * 7
    assert rows[0]['attempt_kind'] == 'HUMAN_AUTHORIZED_PERMISSION_RETRY'
    assert all(x['attempt_kind'] == 'ORIGINAL_PREVIOUSLY_UNRUN_ARM' for x in rows[1:])


@pytest.mark.parametrize('mode,expected_calls', [('denied_again', 1), ('duplicate', 1),
                                                ('preview_changed', 0), ('prompt_changed', 0)])
def test_stop_without_automatic_retry_or_changed_first_request(tmp_path, monkeypatch, mode, expected_calls):
    samples, previous, calls, sender = controls(monkeypatch, mode)
    if mode == 'denied_again':
        rows, stop = r.run_remaining(samples, tmp_path, previous, send=sender)
        assert stop and len(rows) == 1
    else:
        with pytest.raises(ValueError):
            r.run_remaining(samples, tmp_path, previous, send=sender)
    assert len(calls) == expected_calls


def test_changed_sample_plan_is_zero_call(tmp_path, monkeypatch):
    samples, previous, calls, sender = controls(monkeypatch)
    with pytest.raises(ValueError, match='RETRY_SAMPLE_SCOPE'):
        r.run_remaining(list(reversed(samples)), tmp_path, previous, send=sender)
    assert not calls


def test_concurrent_writer_stops_before_transport(tmp_path, monkeypatch):
    samples, previous, calls, sender = controls(monkeypatch)
    def changed(): raise ValueError('concurrent write')
    with pytest.raises(ValueError, match='concurrent write'):
        r.run_remaining(samples, tmp_path, previous, send=sender, before_send=changed)
    assert not calls


@pytest.mark.parametrize('approval,attempt', [(None, '1'), ('old-approval', '1'), (r.APPROVAL, '2')])
def test_explicit_retry_permission_and_first_workflow_attempt_required(monkeypatch, approval, attempt):
    monkeypatch.setenv('R4_2_RETRY_APPROVAL', approval or '')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', attempt)
    with pytest.raises(ValueError, match='RETRY_EXPLICIT_AUTHORITY'):
        r.main()
