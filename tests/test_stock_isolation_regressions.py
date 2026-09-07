"""Follow-up isolation boundaries and offset-stable replay; synthetic inputs only."""
from datetime import timezone

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import hithink_stock_reading as own
from decision_kernel.runtime import stock_radar_reading as stock
from test_hithink_stock_reading import inputs
from test_stock_issuer_isolation import expanded_provider
from test_stock_radar_reading import observe, NOW
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


@pytest.mark.parametrize('body',[
    {'code':'4001','data':None}, {'code':2003.0,'data':None},
    {'code':False,'data':None}, {'data':None}, [], None,
])
def test_malformed_business_envelope_stops_before_any_later_stock(monkeypatch,body):
    state,plan,provider,calls=expanded_provider(monkeypatch,3)
    bad=plan['issuers'][1]['thscode']
    def request(path,params):
        value=provider(path,params)
        return body if path==own.ACTIONS and params['thscode']==bad else value
    with pytest.raises(ValueError,match='business envelope'):
        stock.observe_stock_reading(plan,state,request_json=request,observed_at=NOW)
    assert calls[-1]==(own.ACTIONS,own.action_params(bad,state.sessions))
    assert not any(path==own.HISTORY and params['thscode']==plan['issuers'][2]['thscode']
                   for path,params in calls)


@pytest.mark.parametrize('nonnull',[False,True])
def test_equal_instants_in_different_offsets_produce_identical_quote_metadata(nonnull):
    days,at,history,quote,actions=inputs()
    if nonnull:
        quote['data']['timestamp']=int(at.timestamp()*1000)
    kw={'code':'002714.SZ','sessions':days,'params':own.history_params('002714.SZ',days)}
    local=own.qualify(history,quote,actions,observed_at=at,quote_received_at=at,**kw)
    utc=at.astimezone(timezone.utc)
    replay=own.qualify(history,quote,actions,observed_at=utc,quote_received_at=utc,**kw)
    assert local==replay
    assert local[1]['quote_received_at']==utc.isoformat()
    assert local[1]['snapshot_individual_trade_date']=='NOT_SUPPLIED_NOT_INFERRED_FROM_READY_CLOCK'


@pytest.mark.parametrize('claimed',['STOCKS_FOR_SHADOW_READING','NO_MATCH_WITHIN_REVIEWED_COMPANY_SCOPE'])
def test_partial_page_cannot_be_relabelled_complete_even_with_rehashed_projection(monkeypatch,claimed):
    state,plan,provider,_=expanded_provider(monkeypatch,2)
    bad=plan['issuers'][0]['thscode']
    def request(path,params):
        value=provider(path,params)
        return {'code':3002,'data':None} if path==own.ACTIONS and params['thscode']==bad else value
    report=stock.observe_stock_reading(plan,state,request_json=request,observed_at=NOW)
    report['projection']['status']=claimed
    report['projection_hash']=canonical_hash(report['projection'])
    with pytest.raises(ValueError,match='identity or authority'):
        stock.render_stock_reading(report)


def test_selected_row_must_still_match_its_complete_scope_counterpart():
    report,_,_=observe()
    report['projection']['surfaced_stocks'][0]['company_name']='different issuer name'
    report['projection_hash']=canonical_hash(report['projection'])
    with pytest.raises(ValueError,match='identity or authority'):
        stock.render_stock_reading(report)
