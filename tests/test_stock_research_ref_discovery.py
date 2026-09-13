"""Synthetic first-ref responses and real module class identity, never live calls."""
from copy import deepcopy
import runpy
import socket
import warnings

import pytest

from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_research_reading as reader


CODES = ['600184.SH', '300183.SZ', '603353.SH', '300711.SZ']
REF = 'refs/heads/' + intake.WORK_REF
COMMIT = 'b' * 40


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail('network forbidden in first-ref discovery tests')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)


@pytest.fixture(scope='module')
def entry_error():
    # runpy loads the REAL transport definitions in a second namespace, as -m
    # does before the reader imports the canonical module. A non-main run_name
    # intentionally avoids executing the production CLI or making any requests.
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        entry = runpy.run_module(delivery.__name__, run_name=delivery.__package__ + '._reader_entry_probe')
    error = entry['GitHubReadError']
    assert error is not delivery.GitHubReadError
    assert not isinstance(error('GitHub HTTP 404'), delivery.GitHubReadError)
    return error


def setup_read(tmp_path, *, refs, error_type, failure=None):
    class API:
        calls = 0
        max_calls = delivery.MAX_API_CALLS + reader.EXTRA_API_CALLS
        def __init__(self): self.seen = []
        def get(self, path):
            self.calls += 1
            self.seen.append(path)
            if path == 'actions/workflows/stock-business-research.yml/runs?branch=main&per_page=10':
                return {'total_count': 0, 'workflow_runs': []}
            if path == 'git/ref/heads/' + intake.WORK_REF:
                # Original missing-ref endpoint. Its exception must not be
                # confused with another module's identically named class.
                raise error_type('GitHub HTTP 404')
            if path == 'git/matching-refs/heads/' + intake.WORK_REF:
                if failure is not None: raise error_type(failure)
                return deepcopy(refs)
            if path == 'git/trees/' + COMMIT + '?recursive=1':
                return {'truncated': False, 'tree': []}
            raise AssertionError('unexpected read-only endpoint: ' + path)
    stamp = '2026-09-13T07:00:00+00:00'
    lanes = {'stock': {'health': 'LATEST_ATTEMPT_SUCCEEDED', 'gaps': [], 'last_qualified_result': {
        'market_session': '2026-09-11', 'coverage': {'qualified_issuers': len(CODES)},
        'dispositions': [{'thscode': c, 'status': 'CONTRACT_CHECKED_RAW_READING', 'input_failure': None}
                         for c in CODES]}}}
    baseline = model.assemble(code_commit='a' * 40, checked_at=stamp, check_started_at=stamp,
        lanes=lanes, research={'handoffs': {'active': []}, 'candidate_work': {'status': 'READ_OK', 'items': []}},
        capabilities=[], refresh_identity={})
    collector = delivery.Collector(API(), 'a' * 40, tmp_path, now=lambda: stamp)
    collector.files = {'current-state.json': model.json_bytes(baseline),
                       'README.md': model.render_summary(baseline).encode(), 'old-market.bin': b'unchanged'}
    return collector, baseline


@pytest.mark.parametrize('refs', [[], [{'ref': REF + '-other', 'object': {'type': 'commit', 'sha': COMMIT}}]])
def test_missing_exact_ref_is_not_started_with_entry_module_error(tmp_path, entry_error, refs):
    c, baseline = setup_read(tmp_path, refs=refs, error_type=entry_error)
    result = reader.attach(c, baseline)
    work = result['research']['stock_business_work']
    assert work['status'] == 'NOT_STARTED', work
    assert [i['thscode'] for i in work['items']] == CODES
    assert all(i['status'] == 'NOT_STARTED' and all(i[k] == v for k, v in model.AUTHORITY.items())
               for i in work['items'])
    assert work['latest_execution_attempt'] is None
    assert c.api.calls == 2 and c.api.seen[-1].startswith('git/matching-refs/')
    assert result['lanes'] == baseline['lanes']
    assert result['research']['candidate_work'] == baseline['research']['candidate_work']
    assert c.files['old-market.bin'] == b'unchanged' and not c.sources
    model.validate_read_package(result)


def test_existing_exact_ref_still_uses_original_inventory(tmp_path, entry_error):
    refs = [{'ref': REF, 'object': {'type': 'commit', 'sha': COMMIT}}]
    c, baseline = setup_read(tmp_path, refs=refs, error_type=entry_error)
    result = reader.attach(c, baseline)
    work = result['research']['stock_business_work']
    assert work['status'] == 'READ_OK' and work['work_commit'] == COMMIT
    assert work['counts']['NOT_STARTED'] == 4
    assert c.api.seen[-1] == 'git/trees/' + COMMIT + '?recursive=1'


@pytest.mark.parametrize('refs', [
    {}, None, [None], [{}], [{'ref': 5}],
    [{'ref': REF, 'object': {'type': 'tag', 'sha': COMMIT}}],
    [{'ref': REF, 'object': {'type': 'commit', 'sha': 'main'}}],
    [{'ref': REF}],
    [{'ref': REF, 'object': {'type': 'commit', 'sha': COMMIT}}] * 2,
])
def test_invalid_or_ambiguous_ref_response_is_a_gap_not_not_started(tmp_path, entry_error, refs):
    c, baseline = setup_read(tmp_path, refs=refs, error_type=entry_error)
    result = reader.attach(c, baseline)
    assert result['research']['stock_business_work']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert result['lanes'] == baseline['lanes']
    assert result['research']['candidate_work'] == baseline['research']['candidate_work']
    assert c.files['old-market.bin'] == b'unchanged'


@pytest.mark.parametrize('failure', ['GitHub HTTP 403', 'GitHub HTTP 404', 'GitHub transport unavailable'])
def test_matching_ref_request_failure_never_means_absence(tmp_path, entry_error, failure):
    c, baseline = setup_read(tmp_path, refs=[], error_type=entry_error, failure=failure)
    result = reader.attach(c, baseline)
    assert result['research']['stock_business_work']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert result['lanes'] == baseline['lanes']
    assert c.files['old-market.bin'] == b'unchanged'
