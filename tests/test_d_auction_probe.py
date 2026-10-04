"""Synthetic source envelopes exercise the real capture/replay. No live claims."""
from copy import deepcopy
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import socket

import pytest
import yaml

from decision_kernel.runtime import d_auction_probe as p
from decision_kernel.runtime import tushare_relay as relay

AT = datetime.fromisoformat('2026-10-08T09:27:00+08:00')
TARGET = '2026-10-08'
PRIOR = '20260930'
IDENTITY = {'GITHUB_REPOSITORY':'auguspp/decision-kernel','GITHUB_REF':'refs/heads/main',
    'GITHUB_RUN_ATTEMPT':'1','GITHUB_JOB':p.JOB,'GITHUB_EVENT_NAME':'workflow_dispatch',
    'GITHUB_WORKFLOW_REF':'auguspp/decision-kernel/'+p.WORKFLOW+'@refs/heads/main',
    'GITHUB_SHA':'a'*40,'GITHUB_RUN_ID':'123'}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs): raise AssertionError('unexpected network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def body(api, fields, rows, **extras):
    return p.saved.dumps({'api_name':api,'code':0,'data':{'fields':fields,'items':rows,**extras}})


def pool_row(symbol='600001.SH', turnover='20', limit='U', name='合成示例', streak=2, day=PRIOR):
    return [day,symbol,name,'10',turnover,streak,limit]


def sources(*, prior_rows=None, auction_rows=None, target=TARGET, target_open=True, incomplete=None):
    day = p.target_day(target); start = day-timedelta(days=31)
    calendar = [["SSE",(start+timedelta(days=i)).strftime('%Y%m%d'),
        int((start+timedelta(days=i)).strftime('%Y%m%d') == PRIOR or
            start+timedelta(days=i) == day and target_open)] for i in range(32)]
    return {
        'trade_cal':body('trade_cal',['exchange','cal_date','is_open'],calendar),
        'limit_list_d':body('limit_list_d',p.query('limit_list_d',day)['params']['fields'].split(','),
                           prior_rows if prior_rows is not None else [pool_row()],
                           **({'has_more':True} if incomplete == 'prior' else {})),
        'stk_auction':body('stk_auction',['ts_code','trade_date','price','pre_close'],
                           auction_rows if auction_rows is not None else [['600001.SH',day.strftime('%Y%m%d'),'10.5','10']],
                           **({'has_more':True} if incomplete == 'auction' else {}))}


def fake_request(data, at=AT, fail=None, status=403):
    calls=[]
    def request(api, params):
        calls.append((api,params))
        raw = b'{"code":1,"error":"forbidden"}' if api == fail else data[api]
        code = status if api == fail else 200
        classification = relay.classify(code,relay.decode(raw))
        return {'api':api,'params':params,'status':classification,'attempts':[
            {'attempt':1,'http_status':code,'raw':raw,'requested_at':at.isoformat(),
             'received_at':at.isoformat(),'classification':classification,'headers':{}}]}
    request.calls=calls
    return request


def capture(tmp_path, **options):
    at=options.pop('at',AT); target=options.pop('target',TARGET)
    fetch=fake_request(sources(target=target,**options),at)
    root=tmp_path/'capture'
    report=p.capture(root,observed_at=at,market_session=target,request=fetch,clock=at.isoformat)
    return report,root,fetch


def rows(report):
    return p.row_dicts(report)


def test_capture_replay_exact_three_calls_no_ohlc_history_or_factor_gate(tmp_path):
    report,root,fetch=capture(tmp_path)
    assert p.verify(root)==report
    assert [a for a,_ in fetch.calls]==['trade_cal','limit_list_d','stk_auction']
    assert report['cohort_denominator']==report['static_eligible']==report['comparable']==report['matched']==1
    assert rows(report)[0]['gap_pct']=='5'
    assert report['previous_session']=='2026-09-30'
    assert report['provenance']=='SYNTHETIC_TEST_ONLY'
    assert report['investment_authority']=='NONE' and not report['odds_recomputed']
    assert set(fetch.calls[-1][1])=={'trade_date','fields','limit','ts_type'}
    with pytest.raises(FileExistsError):
        p.capture(root,market_session=TARGET,observed_at=AT,request=fetch,clock=AT.isoformat)


@pytest.mark.parametrize('turnover,price,match', [('10','10.3',True),('30','10.9',True),
    ('9.99','10.5',False),('30.01','10.5',False),('20','10.2999',False),('20','10.9001',False)])
def test_original_boundaries_are_inclusive(tmp_path,turnover,price,match):
    report,_,_=capture(tmp_path,prior_rows=[pool_row(turnover=turnover)],
        auction_rows=[['600001.SH','20261008',price,'10']])
    assert bool(report['matched']) is match
    assert report['cohort_denominator']==1


def test_missing_streak_does_not_require_new_field_or_block_price(tmp_path):
    report,_,_=capture(tmp_path,prior_rows=[pool_row(streak=None)])
    assert report['matched']==1
    assert report['prior_temperature']['maximum_consecutive'] is None
    assert report['prior_temperature']['missing_streak_symbols']==['600001.SH']


def test_complete_pool_keeps_exclusions_and_gap_rows(tmp_path):
    source=[pool_row(),pool_row('300001.SZ'),pool_row('688001.SH'),pool_row('920001.BJ'),
            pool_row('000001.SZ',name='*ST合成'),pool_row('000002.SZ',turnover=None),
            pool_row('000003.SZ',turnover='5'),pool_row('000004.SZ'),
            pool_row('000005.SZ',name=None),pool_row('000006.SZ',limit='D',streak=1)]
    report,_,_=capture(tmp_path,prior_rows=source)
    assert report['cohort_denominator']==9 and len(rows(report))==9
    assert report['matched']==1 and report['static_eligible']==2 and report['comparable']==1
    assert Counter(r['status'] for r in rows(report))['EXCLUDED_BOARD']==3
    assert report['prior_temperature']['limit_down']==1
    assert report['coverage_gaps']


from collections import Counter


def test_conflicting_source_duplicates_are_not_arbitrated_or_deleted(tmp_path):
    report,_,_=capture(tmp_path,prior_rows=[pool_row(),pool_row(turnover='21'),pool_row('000001.SZ')],
        auction_rows=[['000001.SZ','20261008','10.5','10'],['000001.SZ','20261008','10.6','10']])
    assert report['cohort_denominator']==2 and report['matched']==0
    assert [r['status'] for r in rows(report)]==['AUCTION_VALUE_UNAVAILABLE_OR_CONFLICT','PRIOR_IDENTITY_CONFLICT']


def test_identical_duplicates_not_extra_members(tmp_path):
    report,_,_=capture(tmp_path,prior_rows=[pool_row(),pool_row()])
    assert report['cohort_denominator']==1 and report['prior_temperature']['limit_up']==1


@pytest.mark.parametrize('incomplete',['prior','auction'])
def test_source_truncation_is_visible_without_discarding_good_ratios(tmp_path,incomplete):
    report,_,_=capture(tmp_path,incomplete=incomplete)
    assert report['matched']==1 and report['coverage_gaps']


def test_prior_close_not_used_as_auction_reference_and_missing_auction_fields_local(tmp_path):
    data=[['600001.SH','20261008','10.71','10.2'],['000001.SZ','20261008',None,'10']]
    report,_,_=capture(tmp_path,prior_rows=[pool_row(),pool_row('000001.SZ')],auction_rows=data)
    assert report['matched']==1 and report['cohort_denominator']==2
    assert next(r for r in rows(report) if r['symbol']=='600001.SH')['gap_pct']=='5'


@pytest.mark.parametrize('at,target,expected',[(AT.replace(hour=10),TARGET,'HISTORICAL_OR_LATE_NOT_PREOPEN_DISCOVERY'),
    (AT.replace(day=9),TARGET,'HISTORICAL_OR_LATE_NOT_PREOPEN_DISCOVERY')])
def test_late_and_historical_reading_not_backdated(tmp_path,at,target,expected):
    report,_,_=capture(tmp_path,at=at,target=target)
    assert report['matched']==1 and report['timeliness']==expected


def test_closed_session_and_before_open_only_calendar(tmp_path):
    report,_,fetch=capture(tmp_path,target_open=False)
    assert report['status']=='TARGET_IS_CLOSED_SESSION' and len(fetch.calls)==1
    root=tmp_path/'early'
    at=AT.replace(hour=9,minute=25)
    request=fake_request(sources(),at)
    result=p.capture(root,market_session=TARGET,observed_at=at,request=request,clock=at.isoformat)
    assert result['status']=='BEFORE_AUCTION_DATA_WINDOW' and len(request.calls)==1


@pytest.mark.parametrize('fail',['trade_cal','limit_list_d','stk_auction'])
def test_permission_denial_preserves_response_no_retry_or_other_api(tmp_path,fail):
    request=fake_request(sources(),fail=fail)
    root=tmp_path/'cap'
    result=p.capture(root,market_session=TARGET,observed_at=AT,request=request,clock=AT.isoformat)
    assert [a for a,_ in request.calls][-1]==fail
    assert result['matched']==0
    assert result['source_outcomes'][-1]['status']=='AUTH_OR_ENTITLEMENT'
    assert any(b'forbidden' in f.read_bytes() for f in (root/'raw').iterdir())
    assert p.verify(root)==result


@pytest.mark.parametrize('damage',['raw','report','summary','extra','clock','future','workflow','classification','query','stop'])
def test_replay_rejects_damage(tmp_path,damage):
    _,root,_=capture(tmp_path)
    receipt=json.loads((root/'receipt.json').read_bytes())
    if damage=='raw':(root/'raw/03-1.json').write_bytes(b'{}')
    elif damage=='report':(root/'report.json').write_bytes(b'{}')
    elif damage=='summary':(root/'summary.md').write_bytes(b'changed')
    elif damage=='extra':(root/'extra.txt').write_bytes(b'extra')
    elif damage=='clock':receipt['calls'][-1]['attempts'][-1]['received_at']='2026-10-08T08:00:00+08:00'
    elif damage=='future':receipt['market_session']='2026-10-09'
    elif damage=='workflow':receipt['provenance']='LIVE_TUSHARE_RELAY'
    elif damage=='classification':receipt['calls'][-1]['attempts'][-1]['classification']='SOURCE_ERROR'
    elif damage=='query':receipt['calls'][-1]['params']['trade_date']='20261007'
    else:receipt['calls'][0]['status']='AUTH_OR_ENTITLEMENT'
    (root/'receipt.json').write_bytes(p.saved.dumps(receipt))
    with pytest.raises((ValueError,KeyError)):
        p.verify(root)


def test_request_names_added_without_expanding_general_relay(tmp_path,monkeypatch):
    for name in ('stk_auction','limit_list_d'):
        assert name in relay.ALLOWED
    with pytest.raises(relay.RelayError):relay._params('unreviewed_api',{})
    calls=[]
    def native(api,params,**kw):
        assert kw['retry_waits']==(30,) and isinstance(kw['deadline'],float)
        calls.append(api)
        return fake_request(sources())(api,params)
    monkeypatch.setattr(relay,'request',native)
    result=p.capture(tmp_path/'live-shaped-test',market_session=TARGET,observed_at=AT,
                     workflow=IDENTITY,clock=AT.isoformat)
    # Monkeypatched native transport is test-only, never uploaded as real data.
    assert result['provenance']=='LIVE_TUSHARE_RELAY' and calls==['trade_cal','limit_list_d','stk_auction']
    assert p.verify(tmp_path/'live-shaped-test',expected_workflow=IDENTITY)==result


def test_carrier_manual_only_and_normal_publisher_integration():
    root=Path(__file__).resolve().parents[1]
    workflow=yaml.safe_load((root/'.github/workflows/stock-reading-after-sector.yml').read_text())
    on=workflow.get('on',workflow.get(True))
    assert on['schedule']==[{'cron':'35 10 * * 1-5'},{'cron':'5 11,13 * * 1-5'}]
    assert 'auction-inputs' in on['workflow_dispatch']['inputs']['mode']['options']
    job=workflow['jobs']['auction-inputs']
    assert "github.event_name == 'workflow_dispatch'" in job['if'] and 'schedule' not in job['if']
    assert "inputs.mode != 'auction-inputs'" in workflow['jobs']['reconcile-deliveries']['if']
    text=(root/'.github/workflows/current-state-read-entry.yml').read_text()
    assert "github.event.workflow_run.display_title == 'd-auction-inputs'" in text
    assert sum('TUSHARE_PROXY_API_KEY' in step.get('env',{}) for step in job['steps'])==1


def test_invalid_identity_and_wrong_dates_stay_visible(tmp_path):
    report,_,_=capture(tmp_path,prior_rows=[pool_row(),pool_row('000001.SZ',day='20260929'),
        pool_row('NOT_A_CODE')])
    assert report['cohort_denominator']==3 and report['matched']==1
    assert any(r['status']=='PRIOR_SESSION_MISMATCH' for r in rows(report))
    assert any(r['symbol'] is None and r['status']=='PRIOR_SECURITY_IDENTITY_UNAVAILABLE' for r in rows(report))
    assert report['coverage_gaps']


def test_optional_raw_field_types_do_not_cancel_good_members(tmp_path):
    report,_,_=capture(tmp_path,prior_rows=[pool_row(),pool_row('688001.SH',name=['bad']),
        pool_row('000001.SZ',turnover={'bad':True})])
    assert report['matched']==1 and report['cohort_denominator']==3


def test_equivalent_turnover_text_is_not_false_conflict(tmp_path):
    report,_,_=capture(tmp_path,prior_rows=[pool_row(turnover='20.000'),pool_row(turnover='20')])
    assert report['matched']==1 and report['cohort_denominator']==1


def test_provider_cap_full_table_survives_save_read_replay(tmp_path):
    codes=[f'{600000+i:06}.SH' for i in range(2500)]
    report,root,_=capture(tmp_path,prior_rows=[pool_row(c,streak=2) for c in codes],
        auction_rows=[[c,'20261008','10.5','10'] for c in codes])
    assert report['cohort_denominator']==2500 and len(rows(report))==2500
    assert report['prior_temperature']['truncated']
    assert (root/'report.json').stat().st_size <= p.MAX_REPORT
    assert p.verify(root)==report
