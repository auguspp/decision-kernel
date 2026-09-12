"""Clock regressions through actual stock/capture/replay code; all market data synthetic."""
from datetime import datetime, timedelta

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime import theme_radar_probe as theme
from test_stock_radar_reading import prepared, ROOT
from test_stock_radar_capture import setup
from test_hithink_stock_reading_integration import contract_provider
from test_sector_radar_audit import prohibit_network

MONDAY = datetime(2026,9,7,7,tzinfo=stock.SHANGHAI_TZ)
SATURDAY = datetime(2026,9,12,10,tzinfo=stock.SHANGHAI_TZ)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def inputs(at=MONDAY, *, calendar_mode=None):
    state,ledger,association,_,_,_=prepared()
    plan=stock.prepare_stock_reading(ROOT,state,ledger,association,observed_at=at)
    _,_,base,_=contract_provider()
    calls=[]
    def response(path,params):
        calls.append((path,dict(params)))
        value=base(path,params)
        if path in {stock.indices.HITHINK_INDEX_CATALOG_PATH,stock.members.HITHINK_SECTOR_CONSTITUENTS_PATH}:
            value['data']['timestamp']=int(at.timestamp()*1000)
        if path==stock.HITHINK_CALENDAR_PATH:
            rows=value['data']['item']
            value['data']['timestamp']=int(at.timestamp()*1000)
            if calendar_mode=='truncated':value['data']['item']=rows[:-3]
            elif calendar_mode=='missing_middle':rows.pop(20)
            elif calendar_mode=='holiday':rows.pop(-2)  # explicitly synthetic closure, not real Sept 7
        return value
    return state,plan,response,calls


def test_monday_plan_can_reach_real_calendar_check_without_rewriting_clock():
    state,plan,response,calls=inputs()
    with pytest.raises(ValueError):theme._window(state,MONDAY)  # Other observers are unchanged.
    report=stock.observe_stock_reading(plan,state,request_json=response,observed_at=MONDAY)
    p=report['projection']
    assert p['surfaced_stocks'] and p['market_session']=='2026-09-04'
    assert p['observed_at']==stock._plain(MONDAY)
    assert calls[0]==(stock.HITHINK_CALENDAR_PATH,{})
    assert len(calls)<=plan['maximum_request_count']<=26
    assert p['events_created']==p['market_state_writes']==0
    assert p['research_authority']==p['investment_authority']=='NONE'
    assert p['reference_input_hash'] is None
    assert all(r['stock_path']['history_session_count']==61 for r in p['surfaced_stocks'])


@pytest.mark.parametrize('at,mode,reason',[
    (MONDAY,'truncated','STOCK_CALENDAR_COVERAGE_INSUFFICIENT'),
    (MONDAY,'missing_middle','STOCK_CALENDAR_STATE_WINDOW_DIFFERS'),
    (MONDAY.replace(hour=15),None,'STOCK_STATE_NOT_LATEST_COMPLETED_SESSION'),
    (MONDAY.replace(hour=16),None,'STOCK_STATE_NOT_LATEST_COMPLETED_SESSION'),
    (MONDAY+timedelta(days=1),None,'STOCK_STATE_NOT_LATEST_COMPLETED_SESSION'),
])
def test_calendar_not_weekday_decides_and_blocks_later_market_calls(at,mode,reason):
    state,plan,response,calls=inputs(at,calendar_mode=mode)
    with pytest.raises(stock.StockReadingInputError,match=reason):
        stock.observe_stock_reading(plan,state,request_json=response,observed_at=at)
    assert calls==[(stock.HITHINK_CALENDAR_PATH,{})]


def test_explicit_synthetic_holiday_does_not_become_weekday_inference():
    at=MONDAY.replace(hour=16)
    state,plan,response,calls=inputs(at,calendar_mode='holiday')
    result=stock.observe_stock_reading(plan,state,request_json=response,observed_at=at)
    assert result['projection']['surfaced_stocks']
    assert result['projection']['market_session']=='2026-09-04'
    assert calls[0][0]==stock.HITHINK_CALENDAR_PATH


def test_current_provider_calendar_can_end_at_prior_session_without_weekday_inference():
    state,plan,response,calls=inputs(SATURDAY)
    def current_source(path,params):
        value=response(path,params)
        if path==stock.HITHINK_CALENDAR_PATH:
            last=state.sessions[-1].strftime('%Y%m%d')
            value['data']['item']=[row for row in value['data']['item'] if row['date']<=last]
        return value
    result=stock.observe_stock_reading(plan,state,request_json=current_source,observed_at=SATURDAY)
    assert result['projection']['surfaced_stocks']
    assert result['projection']['market_session']=='2026-09-04'
    assert calls[0]==(stock.HITHINK_CALENDAR_PATH,{})


def test_prior_date_provider_clock_does_not_relax_calendar_coverage():
    state,plan,response,calls=inputs(SATURDAY)
    def stale_source(path,params):
        value=response(path,params)
        if path==stock.HITHINK_CALENDAR_PATH:
            last=state.sessions[-1].strftime('%Y%m%d')
            value['data']['item']=[row for row in value['data']['item'] if row['date']<=last]
            value['data']['timestamp']=int((SATURDAY-timedelta(days=1)).timestamp()*1000)
        return value
    with pytest.raises(stock.StockReadingInputError,match='STOCK_CALENDAR_COVERAGE_INSUFFICIENT'):
        stock.observe_stock_reading(plan,state,request_json=stale_source,observed_at=SATURDAY)
    assert calls==[(stock.HITHINK_CALENDAR_PATH,{})]


def test_future_provider_calendar_clock_is_not_used_as_freshness_evidence():
    state,plan,response,calls=inputs(SATURDAY)
    def future_source(path,params):
        value=response(path,params)
        if path==stock.HITHINK_CALENDAR_PATH:
            value['data']['timestamp']=int((SATURDAY+timedelta(seconds=1)).timestamp()*1000)
        return value
    with pytest.raises(ValueError,match='provider-ready'):
        stock.observe_stock_reading(plan,state,request_json=future_source,observed_at=SATURDAY)
    assert calls==[(stock.HITHINK_CALENDAR_PATH,{})]


def test_calendar_failure_is_not_assumed_holiday_or_empty_success():
    state,plan,_,_=inputs();calls=[]
    def reject(path,params):
        calls.append(path)
        return {'code':429,'data':{}}
    with pytest.raises(stock.StockReadingInputError,match='PROVIDER_BUSINESS_REQUEST_FAILED'):
        stock.observe_stock_reading(plan,state,request_json=reject,observed_at=MONDAY)
    assert calls==[stock.HITHINK_CALENDAR_PATH]


def test_close_crossing_is_rechecked_after_each_response():
    start=MONDAY.replace(hour=14,minute=59)
    state,plan,base,calls=inputs(start)
    current=start
    def response(path,params):
        nonlocal current
        value=base(path,params)
        if path!=stock.HITHINK_CALENDAR_PATH:current=MONDAY.replace(hour=15)
        return value
    with pytest.raises(stock.StockReadingInputError,match='STOCK_STATE_NOT_LATEST_COMPLETED_SESSION'):
        stock.observe_stock_reading(plan,state,request_json=response,observed_at=start,cutoff_clock=lambda:current)
    assert len(calls)==2  # Calendar then catalog, no snapshot or individual requests.


@pytest.mark.parametrize('at',[MONDAY.replace(tzinfo=None),datetime(2026,9,4,14,tzinfo=stock.SHANGHAI_TZ)])
def test_unqualified_cutoff_still_fails_before_any_request(at):
    state,_,_,_=inputs()
    with pytest.raises(ValueError):stock.check_observation_clock(state,at)


def capture_at(tmp_path,at,*,calendar_mode=None):
    mod,state_dir,out,_,_,_=setup(tmp_path)
    _,_,response,calls=inputs(at,calendar_mode=calendar_mode)
    times=iter(at+timedelta(seconds=i) for i in range(100))
    before=mod['inventory'](state_dir)
    r=mod['capture'](ROOT,state_dir,out,observed_at=at,transport=response,
        workflow={'test':'synthetic-calendar-regression'},now=lambda:next(times),pause=lambda _:None)
    assert mod['inventory'](state_dir)==before
    return mod,out,r,calls


def test_monday_capture_and_original_input_replay_both_use_calendar(tmp_path):
    mod,out,r,calls=capture_at(tmp_path,MONDAY)
    assert r['status']==mod['COMPLETE'],r
    assert r['provenance']==mod['SYNTHETIC']
    v=mod['verify'](out)
    assert v['network_calls']==0 and v['requests_replayed']==len(calls)
    assert v['stock_count']>=1
    assert '合成验收样本' in (out/'index.html').read_text()
    assert not (out/'synthetic-reference-inputs.json').exists()


def test_stale_state_negative_capture_rebuilds_and_keeps_original_calendar(tmp_path):
    mod,out,r,calls=capture_at(tmp_path,MONDAY.replace(hour=16))
    assert r['status']==mod['FAILED']
    assert r['reason_code']=='STOCK_STATE_NOT_LATEST_COMPLETED_SESSION'
    assert calls==[(stock.HITHINK_CALENDAR_PATH,{})]
    assert not (out/'stock-reading.json').exists()
    assert (out/'responses/01.json').is_file()
    v=mod['verify'](out)
    assert v['failure_replay']=='REPRODUCED_FROM_RETAINED_INPUTS'
    assert v['network_calls']==0
    assert 'qualified recovery' in (out/'index.html').read_text()


def test_rehashed_new_completed_session_cannot_reuse_prior_success(tmp_path):
    mod,out,r,_=capture_at(tmp_path,MONDAY)
    assert r['status']==mod['COMPLETE']
    # A changed calendar that introduces a completed intervening date must rerun
    # qualification, not merely pass a resealed file inventory.
    path=out/'responses/01.json';value=mod['read'](path)
    value['data']['item'].insert(-2,{'date':'20260906'})
    path.write_bytes(mod['data'](value))
    r['files']={k:v for k,v in mod['inventory'](out).items() if k!='capture.json'}
    r['capture_hash']=canonical_hash({k:v for k,v in r.items() if k!='capture_hash'})
    (out/'capture.json').write_bytes(mod['data'](r))
    with pytest.raises(ValueError):mod['verify'](out)
