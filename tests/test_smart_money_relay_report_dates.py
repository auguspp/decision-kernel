"""The relay's actual 400 requires a date, not an unqualified range query."""
from copy import deepcopy
from hashlib import sha256
import json
import socket

import pytest

from decision_kernel.runtime import smart_money_relay as relay
from decision_kernel.runtime import smart_money_sources as source
from decision_kernel.runtime import smart_money_reading as reading
from test_smart_money_relay import IDENT, response
from test_smart_money_relay_execution import (
    NOW, BOUND, make_reuse,
    test_actual_preflight_relay_only_does_not_reset_or_reacquire_primary as preflight_example,
)
from test_smart_money_reading import preserve_as_previous


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('network forbidden in report-date tests')
    monkeypatch.setattr(socket.socket, 'connect', reject)
    monkeypatch.setattr(socket, 'getaddrinfo', reject)
    monkeypatch.setenv(relay.relay.SECRET_ENV, 'test-not-a-real-key')


def capture(tmp_path, request=None, reports_only=True, revision=3):
    return relay.capture(tmp_path/'reports', IDENT, '2026-09-24', revision=revision,
        reports_only=reports_only, source_capture=deepcopy(BOUND), clock=lambda:NOW,
        request=request or (lambda api, params, key, clock:response(api,params,clock)))


def files(tmp_path):
    return {p.name:p.read_bytes() for p in (tmp_path/'reports').iterdir()}


def test_date_plan_preserves_weekend_window_without_guessing_market_day():
    full=relay.plan('2026-09-24',revision=3,as_of='2026-09-26')
    narrow=relay.plan('2026-09-24',revision=3,as_of='2026-09-26',reports_only=True)
    assert len(full)==11 and len(narrow)==7
    assert [s['params']['report_date'] for s in narrow]==[f'202609{i}' for i in range(26,19,-1)]
    assert all(s['api']=='report_rc' and set(s['params'])=={'report_date','limit'} for s in narrow)
    assert all(s['params'].get('trade_date','20260924')=='20260924' for s in full)
    assert relay.plan(None,revision=3,as_of='2026-09-26',reports_only=True)==[]


def test_actual_gateway_parameter_constraint_and_all_daily_pages_survive(tmp_path):
    calls=[]
    def gateway(api,params,key,clock):
        calls.append((api,params))
        assert api=='report_rc' and params.get('report_date'), 'real relay rejects range-only request'
        return response(api,params,clock)
    result=capture(tmp_path,gateway)
    assert len(calls)==7 and result['status']=='READY' and result['reports_only']
    family=result['families']['report_rc']
    assert family['row_count']==7 and family['interpretation']['qualified_row_count']==7
    assert len(family['pages'])==7 and len(family['row_origins'])==7
    assert family['recorded_http_attempt_count']==7
    assert [p['row_offset'] for p in family['pages']]==list(range(7))
    assert [r['report_date'] for r in family['rows']]==[p['report_date'] for p in family['pages']]
    assert all(r['quarter']=='2027Q4' for r in family['rows'])
    assert all(not p['interpretation']['coverage']['complete_market'] for p in family['pages'])
    assert relay.replay(files(tmp_path),identity=IDENT,cutoff=NOW)==result
    manifest=source.decode(files(tmp_path)['capture.json'])
    assert manifest['market_session']=='2026-09-24' and manifest['as_of_date']=='2026-09-26'
    assert len({a['body'] for r in manifest['records'] for a in r['attempts']})==7


def test_full_plan_retains_other_interfaces_and_does_not_overwrite_report_pages(tmp_path):
    result=capture(tmp_path,reports_only=False)
    assert set(result['families'])==set(relay.APIS)
    assert result['families']['report_rc']['row_count']==7
    assert all(result['families'][api]['row_count']==1 for api in relay.APIS if api!='report_rc')
    assert result['status']=='READY' and not result['reports_only']


@pytest.mark.parametrize('fault',['queue','wrong_date','empty','receipt'])
def test_one_daily_gap_or_empty_never_erases_other_days(tmp_path,fault):
    def request(api,params,key,clock):
        if params['report_date']=='20260924':
            if fault=='queue':
                return response(api,params,clock,status='TEMPORARY_QUEUE',error='upstream_pool_exhausted')
            if fault=='receipt':raise ValueError('missing receipt')
            if fault=='empty':return response(api,params,clock,rows=[])
            result=response(api,params,clock)
            body=json.loads(result['attempts'][0]['raw']);body['data']['items'][0][0]='20260925'
            result['attempts'][0]['raw']=json.dumps(body).encode()
            return result
        return response(api,params,clock)
    result=capture(tmp_path,request);family=result['families']['report_rc']
    assert len(family['pages'])==7
    if fault=='empty':
        assert result['status']=='READY' and family['row_count']==6
        assert not family['interpretation']['coverage']['complete_market']
    else:
        assert result['status']=='PARTIAL_WITH_EXPLICIT_GAPS'
        assert any(g.get('report_date')=='20260924' for g in result['unresolved'])
    if fault=='queue':assert family['row_count']==6 and family['recorded_http_attempt_count']==7
    if fault=='wrong_date':
        assert family['row_count']==7 and family['interpretation']['qualified_row_count']==6
        assert family['rows'][2]['report_date']=='20260925'
        assert family['row_origins'][2]['report_date']=='20260924'
    if fault=='receipt':
        assert family['row_count']==2 and family['recorded_http_attempt_count'] is None
        assert all(p['status']=='NOT_ATTEMPTED_SERVICE_STOP' for p in family['pages'][3:])
    assert relay.replay(files(tmp_path),identity=IDENT,cutoff=NOW)==result


def test_service_refusal_stops_all_remaining_report_dates(tmp_path):
    calls=[]
    def request(api,params,key,clock):
        calls.append(params['report_date'])
        if len(calls)==2:
            value=response(api,params,clock,status='AUTH_OR_ENTITLEMENT')
            value['attempts'][0]['http_status']=403
            return value
        return response(api,params,clock)
    result=capture(tmp_path,request)
    assert len(calls)==2 and result['families']['report_rc']['row_count']==1
    assert all(p['status']=='NOT_ATTEMPTED_SERVICE_STOP' for p in result['families']['report_rc']['pages'][2:])


def test_interrupted_window_keeps_qualified_pages_and_unattempted_dates(tmp_path):
    calls=[]
    def request(api,params,key,clock):
        calls.append(params['report_date'])
        if len(calls)==3:raise KeyboardInterrupt()
        return response(api,params,clock)
    with pytest.raises(KeyboardInterrupt):capture(tmp_path,request)
    result=relay.replay(files(tmp_path),identity=IDENT,cutoff=NOW)
    assert result['execution_complete'] is False
    assert result['families']['report_rc']['row_count']==2
    assert len(result['families']['report_rc']['pages'])==7
    assert result['status']=='PARTIAL_WITH_EXPLICIT_GAPS'


@pytest.mark.parametrize('fault',['date','scope','scope_type','removed_date'])
def test_rehash_does_not_authorize_new_scope_or_fewer_days(tmp_path,fault):
    capture(tmp_path);saved=files(tmp_path);manifest=source.decode(saved['capture.json'])
    if fault=='date':manifest['records'][0]['spec']['params']['report_date']='20260925'
    elif fault=='scope':manifest['reports_only']=False
    elif fault=='scope_type':manifest['reports_only']='true'
    else:manifest['records'].pop()
    manifest['capture_hash']=relay._manifest_hash(manifest);saved['capture.json']=source.encoded(manifest)
    with pytest.raises(ValueError):relay.replay(saved,identity=IDENT,cutoff=NOW)


def test_original_revision_two_range_request_is_not_rewritten_as_correct(tmp_path):
    calls=[]
    def gateway(api,params,key,clock):
        calls.append((api,params))
        if api=='report_rc':
            assert 'report_date' not in params
            value=response(api,params,clock,status='INVALID_PARAMS',error='invalid_params')
            value['attempts'][0]['http_status']=400
            return value
        return response(api,params,clock)
    result=capture(tmp_path,gateway,reports_only=False,revision=2)
    assert len(calls)==5 and result['families']['report_rc']['status']=='INVALID_PARAMS'
    assert result['plan_revision']==2 and 'reports_only' not in result
    assert relay.replay(files(tmp_path),identity=IDENT,cutoff=NOW)==result


def use_report_repair(tmp_path,col,primary,current,control,archives,ctr,sup,zipbytes,*,scope=True):
    identity={**primary['identity'],'run_id':current['id'],'code_commit':current['head_sha']}
    out=tmp_path/'repair-pages'
    relay.capture(out,identity,max(primary['trading_sessions']),revision=3,reports_only=True,
        source_capture=relay.source_binding(primary),clock=lambda:NOW,
        request=lambda api,params,key,clock:response(api,params,clock))
    control['relay_reports_only']=scope
    archives[901]=zipbytes({'control.json':json.dumps(control).encode()})
    archives[902]=zipbytes({p.name:p.read_bytes() for p in out.iterdir()})
    for item in (ctr,sup):item.update(size_in_bytes=len(archives[item['id']]),
        digest='sha256:'+sha256(archives[item['id']]).hexdigest())
    col.archive_cache.clear()


@pytest.mark.parametrize('scope',[True,False])
def test_narrow_capture_requires_matching_control_and_keeps_exact_prior_companion(tmp_path,monkeypatch,scope):
    col,base,primary,current,control,archives,ctr,sup,zipbytes=make_reuse(tmp_path,monkeypatch)
    initial=reading.attach(col,base)
    oldvalue=json.loads(col.files[initial['research']['smart_money']['details']['relay']['read_path']])
    preserve_as_previous(col,initial)
    use_report_repair(tmp_path,col,primary,current,control,archives,ctr,sup,zipbytes,scope=scope)
    result=reading.attach(col,initial);sm=result['research']['smart_money']
    assert sm['status']=='READY' and sm['capture_hash']==primary['capture_hash']
    if not scope:
        assert sm['relay_status']=='CURRENT_RELAY_READING_GAP'
        return
    new=json.loads(col.files[sm['details']['relay']['read_path']])
    prior=json.loads(col.files[sm['details']['relay_previous']['read_path']])
    assert new['reports_only'] and set(new['families'])=={'report_rc'}
    assert new['families']['report_rc']['row_count']==7
    assert prior['capture_hash']==oldvalue['capture_hash'] and prior['cutoff']==oldvalue['cutoff']
    assert prior['families']['hm_list']==oldvalue['families']['hm_list']
    assert '前次其他Relay补充' in col.files[sm['details']['markdown']['read_path']].decode()
    companion=sm['details']['relay_previous']
    preserve_as_previous(col,result)
    again=reading.attach(col,result)
    assert again['research']['smart_money']['details']['relay_previous']==companion
    reading.m.validate_read_package(again)


def test_unavailable_companion_never_erases_current_forecast(tmp_path,monkeypatch):
    col,base,primary,current,control,archives,ctr,sup,zipbytes=make_reuse(tmp_path,monkeypatch)
    initial=reading.attach(col,base);refs=preserve_as_previous(col,initial)
    del col.api.responses['git/blobs/'+refs['relay']['git_blob']]
    use_report_repair(tmp_path,col,primary,current,control,archives,ctr,sup,zipbytes)
    result=reading.attach(col,initial);sm=result['research']['smart_money']
    assert sm['relay_status']=='READY' and sm['status']=='READY'
    assert sm['relay_companion_retained_entry'] is not None
    assert 'companion_error_type' in sm['relay_reading_diagnostics']
    assert 'relay' in sm['details'] and 'relay_previous' not in sm['details']


@pytest.mark.parametrize('started,allowed',[(0,True),(2,True),(3,False)])
def test_report_repair_still_uses_the_existing_cross_code_daily_bound(tmp_path,monkeypatch,started,allowed):
    monkeypatch.setenv('RELAY_REPORTS_ONLY','true')
    preflight_example(tmp_path,monkeypatch,started,allowed)
    control=json.loads((tmp_path/'smart-money-control'/'control.json').read_bytes())
    assert control['relay_reports_only'] is True and control['relay_jobs_started_today']==started
