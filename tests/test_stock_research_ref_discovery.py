"""Original matching-refs reuse, including distinct entry-module exception classes."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import stock_research_reading as reader
from decision_kernel.runtime import stock_research_intake as intake


def entry_error():
    # Load the actual module definitions twice, as -m versus subsequent import
    # does, without executing its main() or making a network request.
    name = 'decision_kernel.runtime._stock_delivery_entry_probe'
    spec = importlib.util.spec_from_file_location(name, Path(delivery.__file__))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.GitHubReadError is not delivery.GitHubReadError
    return module.GitHubReadError


def collect(refs, *, error=None):
    distinct = entry_error()
    class API:
        calls = 0
        max_calls = 244
        def get(self, path):
            self.calls += 1
            if path.startswith('actions/workflows/'):
                return {'workflow_runs': [], 'total_count': 0}
            if path == 'git/matching-refs/heads/' + intake.WORK_REF:
                if error: raise distinct(error)
                return refs
            if path == 'git/ref/heads/' + intake.WORK_REF:
                raise distinct('GitHub HTTP 404')
            raise AssertionError(path)
    collector = SimpleNamespace(api=API(), files={})
    payload = {'lanes': {'stock': {'last_qualified_result': {
        'dispositions': [{'thscode':'600184.SH', 'status':'CONTRACT_CHECKED_RAW_READING', 'input_failure':None}],
        'coverage': {'qualified_issuers':1}}}}}
    return reader._collect(collector, payload)


@pytest.mark.parametrize('refs', [[], [{'ref':'refs/heads/'+intake.WORK_REF+'-other'}]])
def test_absent_exact_work_ref_is_not_started_across_entry_module_loading(refs):
    result = collect(refs)
    assert result['status'] == 'NOT_STARTED'
    assert result['items'][0]['status'] == 'NOT_STARTED'
    assert result['items'][0]['investment_authority'] == 'NONE'


@pytest.mark.parametrize('refs', [None, {}, [{}], [None],
    [{'ref':'refs/heads/'+intake.WORK_REF}]*2,
    [{'ref':'refs/heads/'+intake.WORK_REF, 'object':{'type':'tag', 'sha':'a'*40}}]])
def test_malformed_or_ambiguous_ref_is_not_quiet(refs):
    with pytest.raises((ValueError, KeyError, TypeError)):
        collect(refs)


@pytest.mark.parametrize('error', ['GitHub HTTP 403','GitHub HTTP 404','artifact transport unavailable'])
def test_failed_matching_ref_discovery_does_not_mean_absence(error):
    with pytest.raises(RuntimeError):
        collect([], error=error)
