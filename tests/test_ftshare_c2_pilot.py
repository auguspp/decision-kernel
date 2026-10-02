"""Offline pilot boundary checks; synthetic rows do not qualify live sources."""
import socket

import pytest

from decision_kernel.runtime import ftshare_c2_pilot as p
from decision_kernel.runtime import ftshare_stock_history_comparison as h
from decision_kernel.runtime import ftshare_market_inputs as client
from test_ftshare_stock_history_comparison import prior, fetch as history_fetch, NOW


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a: pytest.fail('live network'))
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a: pytest.fail('live DNS'))


def row(symbol='301190.SZ', **kwargs):
    return dict(symbol=symbol, latest='10.5', prev_close='10', ts_millis=1790751600000, **kwargs)


def response(rows, page=1):
    return h.raw_json({'code':200,'data':{'page':page,'page_size':100,
        'total_pages':9999,'total_items':999999,'items':rows}})


def test_complete_empty_tail_ignores_filtered_total_and_reuses_history(tmp_path):
    def fetch(route, params):
        if route==p.ROUTE:
            return 200,response([row()] if params['page']==1 else [],params['page'])
        return history_fetch(route,params)
    out=p.capture(tmp_path/'out',prior(),fetch=fetch,clock=lambda:NOW)
    assert out['source_requests']==11
    assert out['snapshot']['actual_rows']==1
    assert out['snapshot']['pagination_complete']
    assert out['snapshot']['session_qualification']=='LATEST_PAGE_SESSION_NOT_ESTABLISHED'
    assert out['snapshot']['selection']['selected'][0]['thscode']=='301190.SZ'
    assert len(list((tmp_path/'out/raw').iterdir()))==11
    assert all(x['sha256'] for x in out['calls'])
    assert out['history']['source_calls']==9 and not out['production_admission']


@pytest.mark.parametrize('http,code',[(403,403),(200,429),(401,200)])
def test_rejection_is_one_call_and_no_history(tmp_path,http,code):
    out=p.capture(tmp_path/'out',prior(),fetch=lambda *a:(http,h.raw_json({'code':code})),clock=lambda:NOW)
    assert out['source_requests']==1 and out['history']['source_calls']==0
    assert out['snapshot']['status']=='INPUT_UNAVAILABLE_NOT_QUIET'
    assert out['calls'][0]['provider_code']==code


def test_page_no_repeat_is_rejected_not_silently_truncated(tmp_path):
    out=p.capture(tmp_path/'out',prior(),fetch=lambda *a:(200,response([row()])),clock=lambda:NOW)
    assert out['source_requests']==2 and not out['snapshot']['pagination_complete']
    assert out['history']['source_calls']==0


def test_quote_cap_cannot_admit_partial_scan(tmp_path):
    def fetch(route,params):return 200,response([row()],params['page'])
    out=p.capture(tmp_path/'out',prior(),fetch=fetch,clock=lambda:NOW)
    assert out['source_requests']==88 and not out['snapshot']['pagination_complete']
    assert out['history']['source_calls']==0


def test_inventory_retains_unpriced_delisted_st_duplicate_and_invalid():
    missing=row('001246.SZ',status='Delisted',st=True);missing['prev_close']=None
    out=p.inventory([[row(),row(),missing,row('INVALID')]],True)
    assert (out['actual_rows'],out['unique_valid_symbols'],out['duplicate_excess_rows'],
            out['invalid_count'],out['unpriced_rows'])==(4,2,1,1,1)
    assert out['status_counts']['Delisted']==1 and out['selection'] is None


def test_request_uses_http_page_and_does_not_filter_missing_prices():
    x=p.parameters(2)
    assert x['page']==2 and 'page_no' not in x and 'latest' not in x['filter']
    for bad in ({**x,'page_no':2},{**x,'page':True},{**x,'page_size':101},{**x,'filter':''}):
        with pytest.raises(ValueError):p.validate_request(bad)


def test_one_shot_guard_counts_failed_older_and_requires_complete_inventory():
    r=dict(id=2,display_title=p.TITLE,run_attempt=1,event='workflow_dispatch',head_branch='main')
    p.one_shot_scope([r],1,2)
    for rows,total in (([r],2),([r,{**r,'id':1,'conclusion':'failure'}],2),([{**r,'run_attempt':2}],1)):
        with pytest.raises(ValueError):p.one_shot_scope(rows,total,2)


def test_pilot_excluded_by_existing_native_purpose_guard():
    r=dict(event='workflow_dispatch',head_branch='main',path='.github/workflows/radar-smart-money.yml',display_title=p.TITLE)
    assert h.is_comparison_run(r)
    assert not h.is_comparison_run({**r,'event':'schedule'})


@pytest.mark.parametrize('action',['requested','completed'])
def test_pilot_native_guard_stops_before_collection_and_writes(tmp_path,monkeypatch,action):
    from test_ftshare_stock_history_comparison import publisher_fixture, observed_attempt
    native={**observed_attempt(),'display_title':p.TITLE}
    publisher,args,api,col,summary,path=publisher_fixture(tmp_path,monkeypatch,native,action=action)
    assert publisher.main(args)==0
    assert not api.writes and not col and not (tmp_path/'out').exists()
    assert len(api.reads)==1


def test_transport_retains_fixed_host_and_required_client_header(monkeypatch):
    seen=[]
    class Response:
        status=200
        headers={}
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def geturl(self):return seen[0].full_url
        def read(self,n):return b'{}'
    class Opener:
        def open(self,req,timeout):seen.append(req);return Response()
    monkeypatch.setenv('FTSHARE_API_KEY','unit-test-key')
    monkeypatch.setattr(client,'build_opener',lambda *a:Opener())
    assert client.request(p.ROUTE,p.parameters(2))==(200,b'{}')
    assert seen[0].get_header('X-client-name')=='ft-claw'
    assert seen[0].full_url.startswith(p.ENDPOINT+'?') and 'page=2' in seen[0].full_url


def test_source_failure_preserves_not_requested_after_stop(tmp_path):
    def fetch(route,params):
        if route==p.ROUTE:return 200,response([row()] if params['page']==1 else [],params['page'])
        if route=='history_dividends':return 403,h.raw_json({'code':403})
        return history_fetch(route,params)
    out=p.capture(tmp_path/'out',prior(),fetch=fetch,clock=lambda:NOW)
    assert out['source_requests']==5
    assert out['history']['results'][2]['status']=='ENTITLEMENT_DENIED'
    assert all(x['status'].startswith('NOT_ATTEMPTED_AFTER') for x in out['history']['results'][3:])
