"""Synthetic checks of existing Radar contracts, not a question-layer executor."""
from copy import deepcopy
from pathlib import Path
import socket

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import radar_company_reading as company
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime.radar_stock_candidates import build_stock_discovery_pool
from test_radar_company_reading import composed, compose, reseal
from test_radar_stock_candidates import source


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('no live source or Research in contract regression')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def test_contract_is_reachable_and_does_not_claim_new_runtime():
    root = Path(__file__).resolve().parents[1]
    link = '(radar-research-question-contract-v0.md)'
    for path in ('docs/radar-company-reading-v1.md', 'docs/research-source-scope-v0.md'):
        assert link in (root / path).read_text(encoding='utf-8')
    assert '(research-source-scope-v0.md)' in (root / 'docs/RESEARCH-ENTRY.md').read_text(encoding='utf-8')
    text = (root / 'docs/radar-research-question-contract-v0.md').read_text(encoding='utf-8')
    assert 'TARGET_CONTRACT_ONLY / NOT_IMPLEMENTED' in text
    assert 'qualified observations -> company-first context -> Research Question Layer -> Pre' in text
    for name in ('MARKET_EXPRESSION', 'OBSERVATION_QUALIFICATION', 'DIRECT_EXPOSURE',
                 'ECONOMIC_MATERIALITY', 'VALUE_CHAIN_DIRECTION', 'QUESTION_ANSWERABLE',
                 'COUNTEREVIDENCE_DECLARED', 'FIRST_BUSINESS_BASELINE', 'SOURCE_UNAVAILABLE',
                 'company/security', 'origin(s)', 'question', 'why_now', 'required evidence classes',
                 'known counterevidence', 'existing research relation', 'UNKNOWN', 'dedup/version identity'):
        assert name in text


def test_pool_qualification_remains_separate_from_stock_and_business():
    raw = source(groups=4, leaders=2); before = deepcopy(raw)
    pool = build_stock_discovery_pool(raw)
    assert raw == before and len(pool['candidates']) == 8
    assert pool['automatic_research_routing'] is False and pool['market_requests'] == 0
    for row in pool['candidates']:
        assert row['stock_qualification'] == 'NOT_CHECKED_BY_THIS_POOL'
        assert row['business_link'] == 'NOT_ESTABLISHED_BY_THIS_POOL'
        assert row['origins'] and all('retained_leader' in o for o in row['origins'])


@pytest.mark.parametrize('price_status', [None, 'CONDITIONS_NOT_MET', 'CHECK_INCOMPLETE'])
def test_saved_price_is_context_not_a_global_origin_filter(price_status):
    args = list(composed())
    # A synthetic, already qualified institutional observation for a Sector member.
    args[4]['projection']['companies'][0]['thscode'] = '600000.SH'
    args[4]['projection_hash'] = canonical_hash(args[4]['projection'])
    before_report = compose(args)
    if price_status is not None:
        args[1]['lanes']['stock']['last_qualified_result'] = {
            'market_session': '2026-09-16',
            'dispositions': [{'thscode': '600000.SH', 'status': price_status,
                              'reason': 'SYNTHETIC_SAVED_PRICE_REASON'}]}
        reseal(args[1])
    before = deepcopy(args[1:]); report = compose(args); p = report['projection']
    row = next(r for r in p['companies'] if r['thscode'] == '600000.SH')
    original = next(r for r in before_report['projection']['companies'] if r['thscode'] == row['thscode'])
    assert row['origins'] == original['origins']
    assert {o['kind'] for o in row['origins']} == {'SECTOR_LEADER', 'INSTITUTIONAL_WINDOWS'}
    assert [r['thscode'] for r in p['companies']] == [r['thscode'] for r in before_report['projection']['companies']]
    assert p['coverage']['institution_only_companies'] > 0
    if price_status is None:
        assert row['stock']['status'] == 'NOT_PRESENT_IN_SAVED_STOCK_SCOPE'
    else:
        assert row['stock']['dispositions'][0]['status'] == price_status
        assert row['stock']['dispositions'][0]['reason'] == 'SYNTHETIC_SAVED_PRICE_REASON'
    assert args[1:] == before
    assert all(not r['automatic_admission'] and r['new_research_execution'] == 'NOT_EXECUTED' for r in p['companies'])


def test_more_origins_do_not_move_a_company_to_the_front_or_into_pre():
    args = list(composed()); initial = compose(args)['projection']
    target = '603000.SH'  # Last Sector member, outside the fixture homepage.
    before_position = [r['thscode'] for r in initial['companies']].index(target)
    args[4]['projection']['companies'][0]['thscode'] = target
    args[4]['projection_hash'] = canonical_hash(args[4]['projection'])
    p = compose(args)['projection']
    assert [r['thscode'] for r in p['companies']].index(target) == before_position
    row = next(r for r in p['companies'] if r['thscode'] == target)
    assert len(row['origins']) == 2 and row['automatic_admission'] is False
    assert row['question_status'] == 'OBSERVATION_QUESTIONS_NOT_PRE_OR_QUICK_RESULTS'
    assert p['automatic_research_routing'] is False and p['model_calls'] == 0


def test_existing_origins_keep_separate_qualification_references_and_clocks():
    args = list(composed()); args[4]['projection']['market_session'] = '2026-09-16'
    args[4]['projection_hash'] = canonical_hash(args[4]['projection'])
    report = compose(args); before = deepcopy(report)
    sector = [o for r in report['projection']['companies'] for o in r['origins'] if o['kind'] == 'SECTOR_LEADER']
    seats = [o for r in report['projection']['companies'] for o in r['origins'] if o['kind'] == 'INSTITUTIONAL_WINDOWS']
    assert all(o['source'] == args[3] and o['source_result_hash'] == args[2]['result_hash'] for o in sector)
    assert all(o['source'] == args[5] and o['projection_hash'] == args[4]['projection_hash'] for o in seats)
    assert seats[0]['observations'] == args[4]['projection']['companies'][0]['observations']
    assert seats[0]['market_session'] == '2026-09-16' and seats[0]['publication_time'] == 'UNKNOWN'
    assert sector[0]['market_session'] != seats[0]['market_session']
    html = company.render(report)
    assert 'SECTOR_LEADER' in html and 'INSTITUTIONAL_WINDOWS' in html
    assert report == before  # The existing details display, not a new classifier.


def test_old_baseline_failure_stays_a_failure_not_a_new_question_execution():
    args = list(composed())
    old = {'thscode': '600000.SH', 'status': 'PRE_EXECUTION_FAILURE', 'sources': {},
           'question_kind': 'FIRST_BUSINESS_BASELINE', 'execution_id': 'synthetic-old-root',
           'error_type': 'SourceFailure', **model.AUTHORITY}
    args[1]['research']['stock_business_work']['items'] = [deepcopy(old)]; reseal(args[1])
    p = compose(args)['projection']; row = next(r for r in p['companies'] if r['thscode'] == old['thscode'])
    assert row['research']['stock_business_states'][0] == {'role': 'ROOT', 'record': old}
    assert all(isinstance(q, str) for q in row['questions'])
    assert row['question_status'] == 'OBSERVATION_QUESTIONS_NOT_PRE_OR_QUICK_RESULTS'
    assert row['new_research_execution'] == 'NOT_EXECUTED' and not row['automatic_admission']
    assert args[1]['research']['stock_business_work']['items'] == [old]


def test_concept_membership_and_partial_history_do_not_become_business_or_pre(tmp_path):
    from test_concept_company_reading import inputs, reading
    from decision_kernel.runtime import concept_radar_capture as capture
    def partial(path, params, body):
        if path == capture.radar.probe.HISTORY and params['thscode'] == '886000.TI':
            body['data']['item'] = body['data']['item'][:-1]
        return body
    col, baseline, _, _, _, _ = inputs(tmp_path, partial)
    before = deepcopy(baseline); _, meta, p = reading(col, baseline)
    assert meta['status'] == 'READ_OK_WITH_SOURCE_GAPS'
    assert p['concept_context']['coverage']['detail_gaps'] == 1
    origins = [o for r in p['companies'] for o in r['origins'] if o['kind'] == 'CONCEPT_CURRENT_MEMBER']
    assert origins and all(o['business_linkage'] == 'NOT_ESTABLISHED' for o in origins)
    assert all(o['source'] and o['membership_hash'] and o['source_observed_at'] for o in origins)
    assert all(not r['automatic_admission'] and r['new_research_execution'] == 'NOT_EXECUTED' for r in p['companies'])
    assert p['model_calls'] == 0 and p['new_market_requests'] == 0 and baseline == before
