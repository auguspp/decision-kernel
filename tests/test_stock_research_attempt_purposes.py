"""Synthetic job identities; classified invocation is not a model-call receipt."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import stock_research_reading as reader


@pytest.mark.parametrize('active,key', [
    (['research-stock-business'], 'latest_execution_attempt'),
    (['prepare-stock-sources'], 'latest_source_preparation_attempt'),
    (['deepseek-compatibility'], 'latest_compatibility_attempt'),
    ([], None),
    (['research-stock-business', 'deepseek-compatibility'], None),
    (['unknown'], None),
])
def test_three_job_workflow_purposes_remain_separate(active, key):
    run = {'id': 123, 'head_sha': 'a' * 40, 'head_branch': 'main', 'run_attempt': 1,
           'event': 'workflow_dispatch', 'path': '.github/workflows/stock-business-research.yml',
           'head_repository': {'full_name': model.REPOSITORY}, 'status': 'completed',
           'conclusion': 'success', 'created_at': '2026-09-20T00:00:00Z'}
    names = ['research-stock-business', 'prepare-stock-sources', 'deepseek-compatibility']
    if 'unknown' in active:
        names.append('unknown')
    jobs = [{'name': n, 'run_id': 123, 'conclusion': 'success' if n in active else 'skipped'} for n in names]
    class API:
        calls = 0
        max_calls = 252
        def get(self, path):
            self.calls += 1
            if path.startswith('actions/workflows/'):
                return {'total_count': 1, 'workflow_runs': [deepcopy(run)]}
            assert path == 'actions/runs/123/jobs?per_page=100'
            return {'total_count': len(jobs), 'jobs': deepcopy(jobs)}
    result = reader.attempts(SimpleNamespace(api=API(), files={}))
    keys = ['latest_execution_attempt', 'latest_source_preparation_attempt', 'latest_compatibility_attempt']
    if key is None:
        assert result['attempt_classification_status'] == 'PARTIAL_OR_UNAVAILABLE'
        assert len(result['unclassified_invocations']) == 1
    else:
        assert result['attempt_classification_status'] == 'CLASSIFIED_WITHIN_DECLARED_WINDOW'
        assert result[key]['id'] == 123 and not result['unclassified_invocations']
    assert all(result[k] is None for k in keys if k != key)
    assert result['preparation_result_semantics'] == 'INVOCATION_METADATA_ONLY_NOT_SOURCE_OR_RESEARCH_ACCEPTANCE'
