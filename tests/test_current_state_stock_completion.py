"""Synthetic read-contract cases; no market call or production acceptance claim."""
from __future__ import annotations

import copy

import pytest

from decision_kernel.runtime import current_state as read

FULL = ('COMPLETE_STOCK_READING', 'ORIGINAL_STOCK_INPUTS_AND_PAGE_REBUILT')
PARTIAL = ('COMPLETED_BATCH_WITH_STOCK_DATA_GAPS', 'STOCK_BATCH_WITH_DATA_GAPS_REBUILT')


@pytest.mark.parametrize('complete,pair', [(True, FULL), (False, PARTIAL)])
def test_existing_capture_replay_pairs_are_preserved_not_relabelled(complete, pair):
    capture = {'status': pair[0]}
    verification = {'status': pair[1]}
    projection = {'coverage': {'scope_complete': complete}}
    before = copy.deepcopy((capture, verification, projection))
    read._validate_stock_replay_completion(capture, verification, projection)
    assert (capture, verification, projection) == before


@pytest.mark.parametrize('complete,pair', [
    (False, ('INCOMPLETE_STOCK_READING', PARTIAL[1])),
    (False, ('INCOMPLETE_STOCK_READING', 'RETAINED_INCOMPLETE_ATTEMPT_NOT_STOCK_SELECTION')),
    (False, (FULL[0], PARTIAL[1])),
    (False, (PARTIAL[0], FULL[1])),
    (True, PARTIAL),
    (True, (FULL[0], PARTIAL[1])),
    (True, ('INCOMPLETE_STOCK_READING', FULL[1])),
])
def test_wrong_or_failed_completion_cannot_be_promoted_by_a_successful_job(complete, pair):
    with pytest.raises(ValueError, match='completion differs'):
        read._validate_stock_replay_completion(
            {'status': pair[0]}, {'status': pair[1]},
            {'coverage': {'scope_complete': complete}})


@pytest.mark.parametrize('value', [1, 0, None, 'true', 'false'])
def test_completion_scope_requires_a_real_boolean(value):
    with pytest.raises(ValueError, match='boolean'):
        read._validate_stock_replay_completion(
            {'status': FULL[0]}, {'status': FULL[1]},
            {'coverage': {'scope_complete': value}})


@pytest.mark.parametrize('qualified,unavailable', [(4, 2), (0, 6)])
def test_existing_lane_keeps_partial_denominator_and_gap(qualified, unavailable):
    saved = {'market_session': '2026-09-11',
             'status': 'PARTIAL_STOCKS_FOR_SHADOW_READING' if qualified else 'NO_USABLE_STOCK_DATA',
             'coverage': {'planned_issuers': 6, 'evaluated_issuers': qualified,
                          'qualified_issuers': qualified, 'unavailable_issuers': unavailable,
                          'conditions_not_met_issuers': 0, 'scope_complete': False},
             'surfaced_codes': ['SYNTHETIC_NOT_A_REAL_CODE'] if qualified else []}
    before = copy.deepcopy(saved)
    lane = read.lane_reading(
        latest={'id': 101, 'status': 'completed', 'conclusion': 'success'},
        qualified=saved, failure=None, checked_at='2026-09-12T05:00:00Z', query_complete=True)
    assert lane['last_qualified_result'] == before
    assert lane['last_qualified_result']['coverage']['scope_complete'] is False
    assert 'PARTIAL_STOCK_COVERAGE_NOT_COMPLETE_OR_QUIET' in lane['gaps']
    assert lane['restore_authority'] is False
    assert saved == before
