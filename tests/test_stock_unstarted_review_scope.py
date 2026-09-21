"""Unstarted Stock placeholders are review work, not existing Research results.

Regression shape comes from the saved September21 six-row batch, run35588490572,
readinge85d64e98abd1c2b33e76ce48c5e70659e7af2b1. This compact fixture is not a
replacement market artifact or a formal distinct-question declaration.
"""
from copy import deepcopy
import socket

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import reviewed_question_reading as reader
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_research_reading as stock_reader
from decision_kernel.runtime import saved_research_once as once
from test_stock_research_host import setup_host

CODES = ['603507.SH', '002285.SZ', '688205.SH', '301155.SZ', '000560.SZ', '002792.SZ']
ELIGIBLE = [CODES[i] for i in (0, 1, 4, 5)]


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('projection regression must not access networking')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def payload():
    rows = []
    names = ['振江股份', '世联行', '德科立', '海力风电', '我爱我家', '通宇通讯']
    for code, name in zip(CODES, names):
        rows.append({'thscode': code, 'company_name': name,
                     'status': 'CONTRACT_CHECKED_RAW_READING', 'input_failure': None,
                     'excluded_reasons': []})
    rows[2].update(status='DATA_QUALIFICATION_FAILED', input_failure={
        'reason_code': 'REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW'})
    rows[3].update(status='CONDITIONS_NOT_MET', excluded_reasons=[
        'TWENTY_DAY_PATH_DOES_NOT_BEAT_ANY_ROUTED_SECTOR'])
    return {'lanes': {'stock': {'health': 'LATEST_ATTEMPT_SUCCEEDED',
        'last_qualified_result': {'market_session': '2026-09-21',
            'projection_hash': '9c60e3ee61ea82c71369f2659f86fc51c1d43d940070e1aa9c9763e5e13ab5c3',
            'archive': {'origin_run': {'id': 35588490572}},
            'coverage': {'planned_issuers': 6, 'qualified_issuers': 4}, 'dispositions': rows}}},
        'research': {'stock_business_work': {'status': 'READ_OK', 'items': [
            {'thscode': c, 'status': 'NOT_STARTED', 'sources': {}, 'terminal_state': None,
             'question_kind': intake.QUESTION_KIND, 'execution_id': intake.execution(c)[0]}
            for c in ELIGIBLE]}}}


def assert_no_authority(scope):
    assert scope['reviewed_question_count'] == 0
    assert scope['automatic_research_execution'] is False
    assert all(scope[k] == v for k, v in model.AUTHORITY.items())
    for row in scope['items']:
        assert row['distinct_question_assessment'] == 'NOT_PERFORMED'
        assert row['economic_question_assessed'] is False
        assert row['research_execution_allowed'] is False


def test_september21_placeholders_do_not_hide_four_review_candidates():
    value = payload(); before = deepcopy(value)
    scope = reader.stock_review_scope(value)
    assert scope['question_review_required_count'] == 4
    assert [r['thscode'] for r in scope['items'] if r['review_status'] == 'QUESTION_REVIEW_REQUIRED'] == ELIGIBLE
    assert [r['thscode'] for r in scope['items']] == CODES
    assert scope['data_unavailable_count'] == 1 and scope['existing_baseline_gap_count'] == 0
    assert scope['items'][2]['review_status'] == 'DATA_UNAVAILABLE_NOT_PRICE_REJECTED'
    assert scope['items'][3]['review_status'] == 'ORIGINAL_PRICE_DISPOSITION_ONLY'
    stock = value['lanes']['stock']['last_qualified_result']
    assert scope['batch_id'] == canonical_hash({'source_run': 35588490572,
        'market_session': '2026-09-21', 'projection_hash': stock['projection_hash'],
        'dispositions': stock['dispositions']})
    assert value == before
    assert_no_authority(scope)


@pytest.mark.parametrize('status', ['NOT_STARTED', 'UNAVAILABLE_OR_REJECTED', 'READ_OK_WITH_GAPS', None])
def test_placeholder_without_successful_work_read_is_not_a_new_question(status):
    value = payload(); value['research']['stock_business_work']['status'] = status
    scope = reader.stock_review_scope(value)
    assert scope['question_review_required_count'] == 0
    assert all(r['review_status'] == 'RESEARCH_CONTEXT_UNAVAILABLE_NOT_NEW_QUESTION'
               for r in scope['items'] if r['thscode'] in ELIGIBLE)
    assert_no_authority(scope)


@pytest.mark.parametrize('source_state', ['missing', 'null', 'selection'])
def test_not_started_with_missing_or_nonempty_sources_is_not_an_empty_root(source_state):
    value = payload()
    for item in value['research']['stock_business_work']['items']:
        if source_state == 'missing':
            del item['sources']
        else:
            item['sources'] = None if source_state == 'null' else {'selection': {'path': 'saved/prepare.json'}}
    scope = reader.stock_review_scope(value)
    assert scope['question_review_required_count'] == 0
    assert all(r['review_status'] == 'RESEARCH_CONTEXT_UNAVAILABLE_NOT_NEW_QUESTION'
               for r in scope['items'] if r['thscode'] in ELIGIBLE)
    assert_no_authority(scope)


@pytest.mark.parametrize('status,expected', [
    ('PRE_EXECUTION_FAILURE', 'EXISTING_BASELINE_SOURCE_OR_INPUT_GAP'),
    ('VALIDATED_EXECUTION_GAP', 'EXISTING_BASELINE_EXECUTION_GAP'),
    ('VALIDATED_FUNNEL_CANDIDATE', 'EXISTING_BASELINE_RESULT_PRESENT'),
    ('RETAINED_NO_RESEARCH_RESULT', 'EXISTING_BASELINE_PARTIAL_NO_RESULT'),
    ('UNRECOGNIZED_RETAINED_STATE', 'EXISTING_BASELINE_STATE_PRESENT'),
])
def test_actual_saved_history_remains_history_not_a_fresh_invocation(status, expected):
    value = payload(); work = value['research']['stock_business_work']
    for item in work['items']:
        item.update(status=status, sources={'selection': {'path': 'saved/prepare.json'}})
    before = deepcopy(value)
    scope = reader.stock_review_scope(value)
    assert scope['question_review_required_count'] == 0
    assert all(r['review_status'] == expected for r in scope['items'] if r['thscode'] in ELIGIBLE)
    assert [r['existing_research_relation'] for r in scope['items'] if r['thscode'] in ELIGIBLE] == [
        {k: v for k, v in item.items() if k != 'thscode'} for item in work['items']]
    assert value == before
    assert_no_authority(scope)


def test_render_labels_not_started_as_status_and_preserves_saved_failure():
    value = payload()
    value['research']['stock_business_work']['items'][1]['status'] = 'PRE_EXECUTION_FAILURE'
    scope = reader.stock_review_scope(value)
    text = reader.render({'stock_review_scope': scope, 'question_work': {'status': 'READ_OK', 'items': []}})
    assert text.count('原首次业务研究状态：NOT&#95;STARTED') == 3
    assert '既有研究关系：NOT&#95;STARTED' not in text
    assert '既有研究关系：PRE&#95;EXECUTION&#95;FAILURE' in text
    assert all(c in text for c in CODES)
    assert '不创建Human待办、新研究或重试' in text


def test_real_stock_reader_empty_roots_flow_into_review_scope_without_model_or_writes(tmp_path, monkeypatch):
    # Original Git fixture only; real _collect, inventory, scope and render functions.
    args, api, calls, captures, writes = setup_host(tmp_path, monkeypatch)
    api.heads[intake.WORK_REF] = args['code']
    api.calls = 0; api.max_calls = 244
    value = payload(); value['research'].pop('stock_business_work')
    before_files = deepcopy(api.files); before_heads = deepcopy(api.heads)
    collector = delivery.Collector(api, args['code'], tmp_path, now=args['clock'])
    work = stock_reader._collect(collector, value)
    assert work['status'] == 'READ_OK'
    assert [r['thscode'] for r in work['items']] == ELIGIBLE
    assert all(r['status'] == 'NOT_STARTED' and r['sources'] == {} for r in work['items'])
    value['research']['stock_business_work'] = work
    scope = reader.stock_review_scope(value)
    assert scope['question_review_required_count'] == 4
    text = reader.render({'stock_review_scope': scope, 'question_work': {'status': 'READ_OK', 'items': []}})
    assert text.count('QUESTION&#95;REVIEW&#95;REQUIRED') == 4
    assert not calls and not captures and not writes
    assert api.files == before_files and api.heads == before_heads
    assert_no_authority(scope)
