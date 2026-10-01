"""Stock-only recovery contracts; all source envelopes here are synthetic."""
import copy
from decimal import Decimal, Inexact, localcontext

import pytest

from decision_kernel.runtime import hithink_stock_reading as own
from test_hithink_stock_reading import inputs, check


def cash_event(history, actions, *, index=-1, cash='0.13'):
    actions['data']['item'] = [{
        'ticker': '002714', 'ex_date_ms': history['data']['item'][index]['date_ms'],
        'dividend_per_share': cash, 'per_share_bonus': '0',
    }]


def test_recent_window_mode_does_not_opt_legacy_consumers_into_adjustment():
    _, _, h, q, a = inputs()
    cash_event(h, a, index=50)
    with pytest.raises(own.StockReadingInputError, match='REPORTED_CORPORATE_ACTION_IN_WINDOW'):
        check(h, q, a, selection_mode=True)
    _, meta = check(h, q, a, selection_mode=True, action_reference_adjustment=True)
    assert not meta['action_window_checks']['20']['usable_for_raw_comparison']
    assert meta['action_window_checks']['20']['usable_for_price_reference_adjusted_comparison']


def test_legacy_sixty_day_context_stays_unavailable_without_explicit_opt_in():
    _, _, h, q, a = inputs()
    cash_event(h, a, index=20)
    _, meta = check(h, q, a, selection_mode=True)
    assert not meta['action_window_checks']['60']['usable_for_raw_comparison']
    assert not meta['action_window_checks']['60']['usable_for_price_reference_adjusted_comparison']
    assert meta['adjustment_or_total_return_qualification'] == 'NOT_ESTABLISHED'


def test_current_cash_reference_uses_exact_subtraction_not_ratio_round_trip():
    _, _, h, q, a = inputs()
    cash_event(h, a)
    q['data']['item'][0]['prev_price'] = '68.87'
    with localcontext() as context:
        context.prec = 6
        context.traps[Inexact] = True
        _, meta = check(h, q, a, selection_mode=True, action_reference_adjustment=True)
    assert Decimal(meta['latest_quote_previous_reference']['expected_reference_price']) == Decimal('68.87')
    q['data']['item'][0]['prev_price'] = '68.870001'
    with pytest.raises(own.StockReadingInputError, match='PRICE_REFERENCE_DISCONTINUITY'):
        check(h, q, a, selection_mode=True, action_reference_adjustment=True)


@pytest.mark.parametrize('flag', [None, 1, 'true'])
def test_action_opt_in_requires_an_actual_boolean(flag):
    with pytest.raises(own.StockReadingInputError):
        check(selection_mode=True, action_reference_adjustment=flag)


@pytest.mark.parametrize('field', ['volume', 'turnover'])
def test_forward_history_cannot_silently_change_raw_activity(field):
    days, at, h, q, _ = inputs()
    adjusted = copy.deepcopy(h)
    adjusted['data']['item'][20][field] = '9999'
    with pytest.raises(own.StockReadingInputError, match='CURRENT_QUOTE_HISTORY_MISMATCH'):
        own.qualify_forward_adjusted_fallback(
            h, adjusted, q, code='002714.SZ', sessions=days,
            raw_params=own.history_params('002714.SZ', days),
            adjusted_params=own.history_params('002714.SZ', days, adjust='forward'),
            observed_at=at, provider_business_code=3002)


def test_transport_sends_forward_history_and_rejects_unplanned_modes(monkeypatch):
    from decision_kernel.runtime import hithink_dump_trial as transport
    calls = []
    payload = b'{"code":0,"data":{}}'

    class Response:
        status_code = 200
        headers = {'Content-Length': str(len(payload))}
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def iter_content(self, chunk_size): yield payload

    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()

    monkeypatch.setattr(transport, '_session', Session)
    days, *_ = inputs()
    params = own.history_params('002714.SZ', days, adjust='forward')
    assert own.request_json(own.HISTORY, params, api_key='synthetic-test-key')['code'] == 0
    assert len(calls) == 1 and calls[0][1]['params'] == params
    assert calls[0][1]['allow_redirects'] is False
    for bad in ({**params, 'adjust': 'backward'}, {**params, 'interval': '1w'}):
        with pytest.raises(ValueError):
            own.request_json(own.HISTORY, bad, api_key='synthetic-test-key')
    assert len(calls) == 1


def test_successful_forward_capture_retains_original_3002_and_replays(monkeypatch, tmp_path):
    from decision_kernel.runtime import stock_radar_reading as stock
    from test_stock_issuer_isolation import expanded_provider
    from test_stock_radar_capture import setup
    from test_sector_radar_audit import prohibit_network
    prohibit_network(monkeypatch)
    _, plan, provider, calls = expanded_provider(monkeypatch, 3)
    mod, _, out, _, _, run = setup(tmp_path)
    bad = plan['issuers'][0]['thscode']
    failure = {'code': 3002, 'data': None, 'message': 'No adjustment events'}

    def request(path, params):
        value = provider(path, params)
        return failure if path == own.ACTIONS and params['thscode'] == bad else value

    report = run(reference_inputs=None, transport=request)
    assert report['status'] == mod['COMPLETE']
    original = next(r for r in report['requests'] if r['path'] == own.ACTIONS)
    assert mod['read'](out/original['response_file']) == failure
    projection = mod['read'](out/'stock-reading.json')['projection']
    row = next(r for r in projection['all_stock_observations'] if r['thscode'] == bad)
    checks = row['stock_path']['input_checks']
    assert checks['corporate_action_query_succeeded'] is False
    assert checks['adjusted_history_fallback']['status'] == 'USED'
    assert row['stock_path']['price_convention'] == 'PROVIDER_FORWARD_ADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN'
    replay = mod['verify'](out)
    assert replay['requests_replayed'] == len(calls) and replay['network_calls'] == 0
    assert replay['coverage'] == report['coverage']
    assert '3002' in (out/'index.html').read_text()
    assert '不是无事件证明' in stock.price_basis_notice(row['stock_path'])


def test_one_batch_reserve_is_not_one_extra_request_per_issuer(monkeypatch):
    from decision_kernel.runtime import stock_radar_reading as stock
    from test_stock_issuer_isolation import expanded_provider
    from test_stock_radar_reading import NOW
    from test_sector_radar_audit import prohibit_network
    prohibit_network(monkeypatch)
    state, plan, provider, calls = expanded_provider(monkeypatch, 3)

    def request(path, params):
        value = provider(path, params)
        return {'code': 3002, 'data': None} if path == own.ACTIONS else value

    p = stock.observe_stock_reading(plan, state, request_json=request, observed_at=NOW)['projection']
    assert p['coverage']['price_path_checked_issuers'] == 1
    assert p['coverage']['unavailable_issuers'] == 2
    assert len([1 for path, params in calls if path == own.HISTORY and params['adjust'] == 'forward']) == 1
    assert len(calls) <= plan['maximum_request_count'] <= stock.MAX_REQUESTS


def test_raw_stock_path_keeps_the_existing_consumer_convention():
    from decision_kernel.runtime import stock_radar_reading as stock
    days, at, h, q, a = inputs()
    path = stock.stock_path_for_sessions(days, '002714.SZ', h, at=at, quote=q, actions=a)
    assert path['price_convention'] == 'RAW_UNADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN'
    assert path['returns']['20'] == Decimal('70') / Decimal('50') - 1
    assert path['corporate_action_adjustment'] == 'NOT_PERFORMED'
    assert '未复权' in stock.price_basis_notice(path)
