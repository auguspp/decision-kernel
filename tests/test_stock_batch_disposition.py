"""Routing declarations cannot become economic judgments or execution authority."""
from copy import deepcopy

import pytest

from decision_kernel.runtime import stock_batch_disposition as d

NOW = '2026-09-21T04:30:00Z'
ROOT = 'stock-business-' + 'c' * 64


def example():
    scope = {'batch_id': 'b' * 64, 'source_run_id': 101, 'market_session': '2026-09-18', 'items': [
        {'thscode': '000019.SZ', 'company_name': 'filter',
         'review_status': 'ORIGINAL_PRICE_DISPOSITION_ONLY', 'existing_research_relation': None,
         'original_stock_disposition': {'status': 'CONDITIONS_NOT_MET', 'input_failure': None}},
        {'thscode': '600127.SH', 'company_name': 'data gap',
         'review_status': 'DATA_UNAVAILABLE_NOT_PRICE_REJECTED', 'existing_research_relation': None,
         'original_stock_disposition': {'status': 'DATA_QUALIFICATION_FAILED', 'input_failure': {'reason_code': 'MISMATCH'}}},
        {'thscode': '000920.SZ', 'company_name': 'same root',
         'review_status': 'EXISTING_BASELINE_SOURCE_OR_INPUT_GAP',
         'existing_research_relation': {'execution_id': ROOT, 'status': 'PRE_EXECUTION_FAILURE'},
         'original_stock_disposition': {'status': 'CONTRACT_CHECKED_RAW_READING', 'input_failure': None}},
    ]}
    review = {'format': d.FORMAT, 'reviewed_reading_commit': 'a' * 40,
              'reviewed_at': NOW, 'batch_id': scope['batch_id'], 'source_run_id': 101,
              'market_session': scope['market_session'], 'question_source': None, **d.model.AUTHORITY,
              'items': [
                  {'thscode': '000019.SZ', 'disposition': 'ORIGINAL_PRICE_DISPOSITION_ONLY',
                   'reason': 'Original filter only, not economic rejection.', 'existing_execution_id': None, 'progress_record_ids': []},
                  {'thscode': '600127.SH', 'disposition': 'DATA_UNAVAILABLE',
                   'reason': 'Keep the data qualification failure visible.', 'existing_execution_id': None, 'progress_record_ids': []},
                  {'thscode': '000920.SZ', 'disposition': 'EXISTING_RESEARCH',
                   'reason': 'Continue the same question; do not reset its launch.', 'existing_execution_id': ROOT, 'progress_record_ids': []},
              ]}
    return review, scope


def test_complete_routing_is_not_economic_completion_or_new_research():
    review, scope = example()
    before = deepcopy((review, scope))
    out = d.project(review, scope, [], NOW)
    assert out['status'] == d.RECORDED and out['applied'] is True
    assert out['dispositioned_count'] == 3 and out['new_question_selected_count'] == 0
    assert out['economic_question_assessed'] is False and out['research_execution'] == 'NOT_EXECUTED'
    assert all(out[k] == v for k, v in d.model.AUTHORITY.items())
    assert (review, scope) == before
    out['items'][0]['reason'] = 'modified projection'
    assert (review, scope) == before


@pytest.mark.parametrize('damage', ['omit', 'reorder', 'duplicate', 'extra-security', 'rename-root',
    'invent-root', 'hide-data-gap', 'filter-becomes-research', 'select-new', 'business-wait',
    'authority', 'question-source', 'extra-key', 'future', 'missing-timezone', 'bad-ref',
    'bad-batch-id', 'bool-run', 'blank-reason', 'large-reason', 'control-text',
    'extra-item-key', 'duplicate-progress', 'bad-progress-type', 'wrong-date', 'pre-market-clock'])
def test_unbound_partial_or_authority_widening_declarations_reject(damage):
    review, scope = example()
    if damage == 'omit': review['items'].pop()
    elif damage == 'reorder': review['items'].reverse()
    elif damage == 'duplicate': review['items'][1] = deepcopy(review['items'][0])
    elif damage == 'extra-security': review['items'][0]['thscode'] = '000020.SZ'
    elif damage == 'rename-root': review['items'][2]['existing_execution_id'] += '-fresh'
    elif damage == 'invent-root': review['items'][0]['existing_execution_id'] = ROOT
    elif damage == 'hide-data-gap': review['items'][1]['disposition'] = 'ORIGINAL_PRICE_DISPOSITION_ONLY'
    elif damage == 'filter-becomes-research': review['items'][0]['disposition'] = 'EXISTING_RESEARCH'
    elif damage == 'select-new': review['items'][2]['disposition'] = 'SELECTED_NEW_DISTINCT_QUESTION'
    elif damage == 'business-wait': review['items'][2]['disposition'] = 'WAIT_FOR_TRIGGER'
    elif damage == 'authority': review['research_authority'] = 'EXECUTE'
    elif damage == 'question-source': review['question_source'] = {'path': 'run-me.json'}
    elif damage == 'extra-key': review['enabled'] = True
    elif damage == 'future': review['reviewed_at'] = '2026-09-22T00:00:00Z'
    elif damage == 'missing-timezone': review['reviewed_at'] = '2026-09-21T04:30:00'
    elif damage == 'bad-ref': review['reviewed_reading_commit'] = 'main'
    elif damage == 'bad-batch-id': review['batch_id'] = 'latest'
    elif damage == 'bool-run': review['source_run_id'] = True
    elif damage == 'blank-reason': review['items'][0]['reason'] = ' '
    elif damage == 'large-reason': review['items'][0]['reason'] = 'x' * 2001
    elif damage == 'control-text': review['items'][0]['reason'] = 'do\nnot execute'
    elif damage == 'extra-item-key': review['items'][0]['execute'] = True
    elif damage == 'duplicate-progress': review['items'][2]['progress_record_ids'] = ['x', 'x']
    elif damage == 'bad-progress-type': review['items'][2]['progress_record_ids'] = [123]
    elif damage == 'wrong-date': review['market_session'] = '2026-09-31'
    elif damage == 'pre-market-clock': review['reviewed_at'] = '2026-09-17T23:00:00Z'
    with pytest.raises((ValueError, TypeError, KeyError)):
        d.project(review, scope, [], NOW)


@pytest.mark.parametrize('key,value', [('batch_id', 'd' * 64), ('source_run_id', 102), ('market_session', '2026-09-21')])
def test_old_disposition_never_becomes_review_of_a_new_batch(key, value):
    review, scope = example()
    scope[key] = value
    out = d.project(review, scope, [], NOW)
    assert out['status'] == d.STALE and out['applied'] is False and out['items'] == []
    assert 'new_question_selected_count' not in out


def test_new_unknown_row_is_not_silently_folded_into_no_new_execution():
    review, scope = example()
    scope['items'].append({**scope['items'][0], 'thscode': '000021.SZ'})
    with pytest.raises(ValueError, match='every row'):
        d.project(review, scope, [], NOW)


def test_changed_existing_relation_rejects_instead_of_replaying_old_decision():
    review, scope = example()
    scope['items'][2]['existing_research_relation']['execution_id'] = 'different-original-root'
    with pytest.raises(ValueError, match='root differs'):
        d.project(review, scope, [], NOW)
