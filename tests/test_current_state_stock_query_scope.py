"""Production query scope, not stock qualification; all run data is synthetic."""
from __future__ import annotations

import copy

import pytest

from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import current_state_delivery as delivery
from test_current_state import AT, SHA, run
from test_current_state_delivery import API

ENDPOINT = 'actions/workflows/hithink-stock-dump-trial.yml/runs?branch=main&per_page=20'


def collector(tmp_path, rows, jobs):
    responses = {ENDPOINT: {'total_count': len(rows), 'workflow_runs': rows}}
    responses.update({f'actions/runs/{number}/jobs?per_page=100': value
                      for number, value in jobs.items()})
    api = API(responses)
    return delivery.Collector(api, SHA, tmp_path, now=lambda: AT), api


def stock_job(conclusion='success'):
    return {'total_count': 1, 'jobs': [{'name': 'stock-reading', 'conclusion': conclusion}]}


@pytest.mark.parametrize('event', ['push', 'pull_request', 'workflow_run'])
@pytest.mark.parametrize('status,conclusion', [('completed', 'failure'), ('queued', None)])
def test_nonproduction_trial_cannot_poison_production_query(tmp_path, event, status, conclusion):
    production = run(10, lane='stock')
    trial = run(11, lane='stock', event=event, status=status, conclusion=conclusion)
    c, api = collector(tmp_path, [trial, production], {10: stock_job()})
    before = copy.deepcopy(api.responses)
    assert c.runs('stock') == ([production], True)
    assert api.reads == [ENDPOINT, 'actions/runs/10/jobs?per_page=100']
    assert api.responses == before and api.writes == []


@pytest.mark.parametrize('event', ['schedule', 'workflow_dispatch'])
@pytest.mark.parametrize('day', [7, 9])
def test_unknown_production_purpose_still_blocks_even_if_older(tmp_path, event, day):
    production = run(10, lane='stock')
    unknown = run(11, lane='stock', event=event, conclusion='failure', day=day)
    c, api = collector(tmp_path, [unknown, production], {
        10: stock_job(), 11: {'total_count': 1, 'jobs': [{'name': 'inspect', 'conclusion': 'failure'}]}})
    assert c.runs('stock') == ([production], False)
    assert len(api.reads) == 3 and not api.writes


def test_push_success_is_not_stock_even_if_its_job_name_matches(tmp_path):
    trial = run(11, lane='stock', event='push')
    c, api = collector(tmp_path, [trial], {})
    assert c.runs('stock') == ([], True)
    assert api.reads == [ENDPOINT]


def test_partial_stock_product_keeps_coverage_gap_not_old_push_failure(tmp_path, monkeypatch):
    production = run(10, lane='stock')
    trial = run(9, lane='stock', event='push', conclusion='failure', day=7)
    c, api = collector(tmp_path, [production, trial], {10: stock_job()})
    saved = {'run': production, 'market_session': '2026-09-07',
             'status': 'PARTIAL_STOCKS_FOR_SHADOW_READING',
             'coverage': {'planned_issuers': 6, 'evaluated_issuers': 4,
                          'qualified_issuers': 4, 'unavailable_issuers': 2,
                          'scope_complete': False}}
    monkeypatch.setattr(c, 'saved_product', lambda lane, chosen: copy.deepcopy(saved))
    result = c.lane('stock')
    assert result['health'] == 'LATEST_ATTEMPT_SUCCEEDED'
    assert result['last_qualified_result'] == saved
    assert result['gaps'] == ['PARTIAL_STOCK_COVERAGE_NOT_COMPLETE_OR_QUIET']
    assert not result['restore_authority'] and not api.writes


def test_real_production_failure_cannot_hide_behind_prior_success(tmp_path, monkeypatch):
    good = run(9, lane='stock', day=7)
    failed = run(10, lane='stock', conclusion='failure')
    c, api = collector(tmp_path, [failed, good], {10: stock_job('failure'), 9: stock_job()})
    monkeypatch.setattr(c, 'saved_product', lambda lane, chosen: {'run': chosen})
    result = c.lane('stock')
    assert result['health'] == 'LATEST_ATTEMPT_FAILED'
    assert result['latest_attempt']['id'] == 10
    assert result['last_qualified_result']['run']['id'] == 9
    assert not api.writes


def test_incomplete_production_job_enumeration_is_still_rejected(tmp_path):
    c, _ = collector(tmp_path, [run(10, lane='stock')], {10: {'total_count': 1, 'jobs': []}})
    with pytest.raises(ValueError, match='enumeration incomplete'):
        c.runs('stock')
