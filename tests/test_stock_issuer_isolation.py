"""Synthetic multi-issuer plans; production selector/recorder/replayer, no network.

The expanded evidence scope below is TEST ONLY. It proves isolation mechanics,
not new real company coverage, real stock selection or provider availability.
"""
import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime import hithink_stock_reading as own
from test_hithink_stock_reading_integration import contract_provider
from test_stock_radar_capture import setup
from test_stock_radar_reading import NOW
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def expanded_provider(monkeypatch, count=6):
    original = stock.prepare_stock_reading

    def prepare(*args, **kwargs):
        plan = copy.deepcopy(original(*args, **kwargs))
        template = plan['issuers'][0]
        issuers = []
        for i in range(count):
            row = copy.deepcopy(template)
            row['thscode'] = f'{101+i:06d}.SZ'
            row['company_name'] = f'SYNTHETIC issuer {i+1}'
            for origin in row['origins']:
                origin['company']['company_name'] = row['company_name']
                origin['company']['ticker'] = row['thscode'][:6]
                origin['company']['business_scope'] = 'SYNTHETIC_TEST_ONLY business fixture'
            issuers.append(row)
        plan['issuers'] = issuers
        plan['evidence_scope_issuers'] = [
            {'thscode': r['thscode'], 'company_name': r['company_name']} for r in issuers]
        plan['maximum_request_count'] = 4+len(plan['directions'])+3*count
        assert plan['maximum_request_count'] <= 26
        plan['plan_hash'] = canonical_hash({k:v for k,v in plan.items() if k != 'plan_hash'})
        return plan

    monkeypatch.setattr(stock, 'prepare_stock_reading', prepare)
    return contract_provider()


def rehash_capture(mod, out, report):
    report['files'] = {k:v for k,v in mod['inventory'](out).items() if k != 'capture.json'}
    report['capture_hash'] = canonical_hash({k:v for k,v in report.items() if k != 'capture_hash'})
    (out/'capture.json').write_bytes(mod['data'](report))


def test_five_good_one_3002_preserves_all_six_identities_and_original_selector(monkeypatch):
    state, plan, provider, calls = expanded_provider(monkeypatch)
    bad = plan['issuers'][0]['thscode']
    raw = {'code':3002, 'data':None, 'message':f'No adjustment events for thscode={bad}',
           'request_id':'synthetic-request-id'}
    before = copy.deepcopy(raw), copy.deepcopy(plan)
    def request(path, params):
        body = provider(path, params)
        return raw if path == own.ACTIONS and params['thscode'] == bad else body
    result = stock.observe_stock_reading(plan, state, request_json=request, observed_at=NOW)
    p = result['projection']; c = p['coverage']
    assert c == {'planned_issuers':6, 'dispositioned_issuers':6, 'evaluated_issuers':5,
                 'price_path_checked_issuers':5, 'qualified_issuers':5,
                 'conditions_not_met_issuers':0, 'unavailable_issuers':1,
                 'not_evaluated_issuers':0, 'scope_complete':False}
    assert p['status'] == 'PARTIAL_STOCKS_FOR_SHADOW_READING'
    assert len(p['surfaced_stocks']) == 3 and len(p['omitted_eligible_stock_codes']) == 2
    assert bad not in {r['thscode'] for r in p['surfaced_stocks']}
    assert p['surfaced_stocks'] == stock._select(p['all_stock_observations'], plan['node_order'])
    r = p['all_stock_observations'][0]
    assert r['input_failure']['provider_business_code'] == 3002
    assert r['input_failure']['phase'] == 'CORPORATE_ACTIONS'
    assert r['stock_path'] is None and not r['excluded_reasons']
    assert len(calls) <= plan['maximum_request_count'] <= 26
    assert before == (raw, plan)
    assert p['events_created'] == p['market_state_writes'] == 0
    text = BeautifulSoup(stock.render_stock_reading(result), 'html.parser').get_text()
    assert '可用数据子集' in text and '数据不可用 1' in text and bad in text


@pytest.mark.parametrize('failure',['short_history','missing_previous','turnover','action','schema'])
def test_local_data_failure_does_not_suppress_later_stocks(monkeypatch, failure):
    state, plan, provider, calls = expanded_provider(monkeypatch, 3)
    bad = plan['issuers'][1]['thscode']
    def request(path, params):
        body = provider(path, params)
        if params.get('thscode', params.get('thscodes')) != bad:
            return body
        if failure == 'short_history' and path == own.HISTORY:
            # Remove a bar inside the latest 26 market sessions. Older gaps are
            # intentionally context-only under the Stock selector contract.
            body['data']['item'].pop(50)
        if failure == 'missing_previous' and path == own.SNAPSHOT:
            body['data']['item'][0].pop('prev_price')
        if failure == 'turnover' and path == own.SNAPSHOT:
            q = body['data']['item'][0]
            q['turnover'] = str(Decimal(str(q['turnover']))-Decimal('43.20'))
        if failure == 'action' and path == own.ACTIONS:
            body['data']['item'] = [{'ticker':bad[:6],
                'ex_date_ms':int(datetime.combine(state.sessions[-1], datetime.min.time(),
                                                tzinfo=stock.SHANGHAI_TZ).timestamp()*1000),
                'dividend_per_share':'0.1','per_share_bonus':0}]
        if failure == 'schema' and path == own.SNAPSHOT:
            body['data']['item'][0]['thscode'] = '999999.SZ'
        return body
    p = stock.observe_stock_reading(plan, state, request_json=request, observed_at=NOW)['projection']
    assert p['coverage']['unavailable_issuers'] == 1
    assert p['coverage']['qualified_issuers'] == 2
    assert {r['thscode'] for r in p['surfaced_stocks']} == {
        plan['issuers'][0]['thscode'], plan['issuers'][2]['thscode']}
    assert p['all_stock_observations'][1]['stock_path'] is None
    assert not p['selection_scope_complete']
    assert len(calls) <= plan['maximum_request_count']


@pytest.mark.parametrize('code',[3001,3002,3004])
def test_unavailable_history_skips_only_that_stock_and_does_not_fetch_its_quote(monkeypatch, code):
    state, plan, provider, calls = expanded_provider(monkeypatch, 2)
    bad = plan['issuers'][0]['thscode']
    def request(path, params):
        body = provider(path, params)
        return {'code':code,'data':None} if path == own.HISTORY and params['thscode'] == bad else body
    p = stock.observe_stock_reading(plan, state, request_json=request, observed_at=NOW)['projection']
    assert p['coverage']['unavailable_issuers'] == p['coverage']['qualified_issuers'] == 1
    assert not any(path in {own.SNAPSHOT,own.ACTIONS}
                   and params.get('thscode',params.get('thscodes')) == bad for path,params in calls)


def test_all_unavailable_is_not_complete_zero_match(monkeypatch):
    state, plan, provider, _ = expanded_provider(monkeypatch, 3)
    def request(path, params):
        body = provider(path, params)
        return {'code':3002,'data':None} if path == own.ACTIONS else body
    report = stock.observe_stock_reading(plan, state, request_json=request, observed_at=NOW)
    p = report['projection']
    assert p['status'] == 'NO_USABLE_STOCK_DATA'
    assert p['coverage']['unavailable_issuers'] == 3 and p['coverage']['evaluated_issuers'] == 0
    assert not p['surfaced_stocks'] and p['coverage']['conditions_not_met_issuers'] == 0
    assert not p['selection_scope_complete']
    assert '不是完整检查后的零匹配' in stock.render_stock_reading(report)


def test_failed_conditions_and_unavailable_have_separate_denominators(monkeypatch):
    state, plan, provider, _ = expanded_provider(monkeypatch, 3)
    bad = plan['issuers'][0]['thscode']
    def request(path, params):
        body = provider(path, params)
        if path == stock.members.HITHINK_SECTOR_CONSTITUENTS_PATH:
            for member in body['data']['item']:
                if member['thscode'] != bad:
                    member['name'] = '*ST Synthetic'
        if path == own.ACTIONS and params['thscode'] == bad:
            return {'code':3002,'data':None}
        return body
    p = stock.observe_stock_reading(plan, state, request_json=request, observed_at=NOW)['projection']
    assert p['status'] == 'NO_MATCH_IN_EVALUATED_SUBSET_WITH_DATA_GAPS'
    assert p['coverage']['conditions_not_met_issuers'] == 2
    assert p['coverage']['unavailable_issuers'] == 1
    assert p['coverage']['price_path_checked_issuers'] == 0
    assert not p['surfaced_stocks']


@pytest.mark.parametrize('code',[1003,2001,2003,4001,5001,9999])
def test_auth_limit_unknown_or_global_business_error_still_stops_batch(monkeypatch, code):
    state, plan, provider, calls = expanded_provider(monkeypatch, 3)
    bad = plan['issuers'][1]['thscode']
    def request(path, params):
        body = provider(path, params)
        return {'code':code,'data':None} if path == own.ACTIONS and params['thscode'] == bad else body
    with pytest.raises(stock.StockReadingInputError, match='PROVIDER_BUSINESS_REQUEST_FAILED'):
        stock.observe_stock_reading(plan, state, request_json=request, observed_at=NOW)
    assert calls[-1] == (own.ACTIONS, own.action_params(bad,state.sessions))