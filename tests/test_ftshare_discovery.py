"""FTShare index -> existing source preparation, without model or PDF calls."""
from copy import deepcopy
from datetime import date, datetime
from io import BytesIO
import json
from pathlib import Path
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request

import pytest
from decision_kernel.runtime import ftshare_discovery as ft
from decision_kernel.runtime import stock_research_sources as sources

FIXTURES = Path(__file__).parent / 'fixtures' / 'ftshare'
CLOCK = lambda: '2026-09-22T00:15:00+00:00'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('unit tests cannot access a network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def raw(value):
    return json.dumps(value, ensure_ascii=False).encode()


def response(ticker='603507'):
    return json.loads((FIXTURES / (ticker + ('-20260826.json' if ticker == '603507' else '-20260821.json'))).read_bytes())


def run(tmp_path, payload=None, status=200, fetch=None):
    return ft.discover(ticker='603507', announcement_date=date(2026, 8, 26), output=tmp_path/'index',
                       clock=CLOCK, fetch=fetch or (lambda params: (status, raw(payload if payload is not None else response()))))


@pytest.mark.parametrize('ticker,day,expected_id,name', [
    ('000920',21,'1225486931','沃顿科技'), ('603507',26,'1225506358','振江股份')])
def test_original_retained_two_issuer_responses_enter_original_source_preparation(tmp_path, monkeypatch, ticker, day, expected_id, name):
    original=(FIXTURES/f'{ticker}-202608{day}.json').read_bytes()
    body=json.loads(original)
    seen=[]
    def discovery(**kwargs):
        return ft.discover(**kwargs, fetch=lambda params:(200,original))
    def official(*, url, method, form, timeout_seconds):
        seen.append((url, method, form))
        if url == sources.cninfo.CNINFO_STOCK_MAP_URL:
            return [{'code':ticker, 'orgId':'official-org'}]
        assert form['stock'] == ticker+',official-org'
        return {'totalAnnouncement':len(body['data']['records']), 'announcements':[
            {'announcementId':r['announcement_id'], 'announcementTitle':r['announcement_title'],
             'secCode':ticker, 'orgId':'official-org', 'announcementTime':int(datetime(2026,8,day,tzinfo=sources.SHANGHAI_TZ).timestamp()*1000),
             'adjunctUrl':f"finalpage/2026-08-{day}/{r['announcement_id']}.PDF"}
            for r in body['data']['records']]}
    monkeypatch.setattr(sources.cninfo, '_request_json', official)
    monkeypatch.setattr(sources.cninfo, 'fetch_cninfo_pdf_bytes', lambda **kwargs:pytest.fail('no PDF'))
    result=sources.prepare_report_discovery(ticker=ticker, announcement_date=date(2026,8,day),
        period='2026H1',issuer_name=name,output=tmp_path/'source',discover=discovery,clock=CLOCK)
    assert result['status']=='OFFICIAL_REPORT_LOCATED_NOT_ACQUIRED', result
    assert result['official_report']['announcement_id']==expected_id
    assert result['official_report']['published_at'].endswith('00:00:00+08:00')
    assert result['ftshare_lead']['provider_time_raw'].endswith('08:00:00')
    assert result['ftshare_lead']['provider_timezone']=='UNKNOWN'
    assert result['model_calls']==result['pdf_calls']==0
    assert result['research_execution_allowed'] is False
    assert result['source_custody']=='NOT_ESTABLISHED'
    assert (tmp_path/'source/ftshare/page-1.json').read_bytes()==original
    assert len(seen)==2 and len(result['official_queries'])==2


@pytest.mark.parametrize('http,expected', [(401,'AUTHENTICATION_FAILED'),(403,'ENTITLEMENT_DENIED'),
    (404,'HTTP_NOT_FOUND'),(429,'RATE_LIMITED'),(500,'HTTP_REJECTED')])
def test_http_failures_are_not_empty_and_never_retry(tmp_path,http,expected):
    calls=[]
    result=run(tmp_path,fetch=lambda params:(calls.append(params) or http,b'{}'))
    assert result['status']==expected and result['announcements']==[] and len(calls)==1
    assert result['requests'][0]['http_status']==http
    assert (tmp_path/'index/page-1.json').read_bytes()==b'{}'


@pytest.mark.parametrize('mutator,expected', [
 (lambda b:b['data']['records'][0].update(sec_code='000920'),'IDENTITY_MISMATCH'),
 (lambda b:b['data']['records'][0].update(announcement_id='../bad'),'IDENTITY_MISMATCH'),
 (lambda b:b['data']['records'][0].update(url_hash='bad'),'IDENTITY_MISMATCH'),
 (lambda b:b['data']['records'][0].update(announcement_time='2026-08-25 08:00:00'),'PROVIDER_DATE_MISMATCH'),
 (lambda b:b['data'].update(pageNum=2),'PAGINATION_MISMATCH'),
 (lambda b:b['data'].update(total=7),'PAGINATION_MISMATCH'),
 (lambda b:b['data'].update(pageSize=True),'PAGINATION_MISMATCH'),
 (lambda b:b['data']['records'].__setitem__(1,deepcopy(b['data']['records'][0])),'DUPLICATE_ANNOUNCEMENT'),
 (lambda b:b['data'].update(total=801,pages=5),'PAGINATION_LIMIT'),
 (lambda b:b.update(code=500),'PROVIDER_REJECTED')])
def test_bad_inputs_retained_but_no_qualified_leads(tmp_path,mutator,expected):
    payload=response();mutator(payload)
    result=run(tmp_path,payload)
    assert result['status']==expected and not result['announcements']
    assert (tmp_path/'index/page-1.json').read_bytes()==raw(payload)


@pytest.mark.parametrize('data', [b'{', b'{"code":200,"code":200}', b'{"code":NaN}', b'[]'])
def test_malformed_returns_not_empty(tmp_path,data):
    result=run(tmp_path,fetch=lambda params:(200,data))
    assert result['status']=='PARSE_FAILURE'


def test_empty_is_complete_only_for_the_declared_day(tmp_path):
    payload=response();payload['data'].update(total=0,pages=0,records=[])
    result=run(tmp_path,payload)
    assert result['status']=='EMPTY' and result['total']==0
    assert result['coverage']=='ONE_ISSUER_ONE_DATE_ONLY'


def test_pagination_complete_and_changed_total_rejected(tmp_path):
    template=response()['data']['records'][0]
    all_rows=[{**template,'announcement_id':str(1000000+i)} for i in range(201)]
    calls=[]
    def fetch(params):
        calls.append(params)
        n=params['page'];return 200,raw({'code':200,'data':{'pageNum':n,'pageSize':200,
            'pages':2,'total':201,'records':all_rows[(n-1)*200:n*200]}})
    result=run(tmp_path,fetch=fetch)
    assert result['status']=='COMPLETE' and len(result['announcements'])==201 and len(calls)==2
    def changed(params):
        status,body=fetch(params);value=json.loads(body)
        if params['page']==2:value['data'].update(total=202,records=all_rows[-1:]*2)
        return status,raw(value)
    result=run(tmp_path/'changed',fetch=changed)
    assert result['status']=='PAGINATION_MISMATCH' and result['announcements']==[]


def test_transport_failure_is_retained_once(tmp_path):
    def fetch(params):raise URLError('remote detail must not enter summary')
    result=run(tmp_path,fetch=fetch)
    assert result['status']=='TRANSPORT_FAILURE' and len(result['requests'])==1
    assert 'remote detail' not in (tmp_path/'index/discovery.json').read_text()


def test_create_only_future_and_symlink_guards(tmp_path):
    run(tmp_path)
    with pytest.raises(FileExistsError):run(tmp_path)
    with pytest.raises(ft.DiscoveryError,match='FUTURE_REQUEST_DATE'):
        ft.discover(ticker='603507',announcement_date=date(2027,1,1),output=tmp_path/'future',clock=CLOCK)
    (tmp_path/'link').symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ft.DiscoveryError,match='UNSAFE_OUTPUT'):
        ft.discover(ticker='603507',announcement_date=date(2026,8,26),output=tmp_path/'link/out',clock=CLOCK)


def test_requests_use_only_official_endpoint_no_secret_or_redirect(monkeypatch):
    seen=[]
    class Response(BytesIO):
        status=200
        headers={'Content-Length':'2'}
        def geturl(self):return seen[0].full_url
    class Opener:
        def open(self,req,timeout):seen.append(req);assert timeout==20;return Response(b'{}')
    monkeypatch.setenv('FTSHARE_API_KEY','do-not-read-secret')
    monkeypatch.setenv('FTSHARE_BASE_URL','https://untrusted.invalid')
    monkeypatch.setattr(ft,'build_opener',lambda handler:Opener())
    assert ft.request_page({'date':'20260826','sec_code':'603507','page':1,'page_size':200})==(200,b'{}')
    assert seen[0].full_url.startswith(ft.ENDPOINT+'?')
    assert 'do-not-read-secret' not in str(seen[0].headers)
    with pytest.raises(ft.DiscoveryError,match='REDIRECT_REJECTED'):
        ft._NoRedirect().redirect_request(seen[0],None,302,'',{},'https://untrusted.invalid')


def test_ftshare_unavailable_stops_before_cninfo(tmp_path):
    def discovery(**kwargs):return ft.discover(**kwargs, fetch=lambda p:(403,b'{}'))
    result=sources.prepare_report_discovery(ticker='603507',announcement_date=date(2026,8,26),period='2026H1',
        issuer_name='振江股份',output=tmp_path/'source',clock=CLOCK,discover=discovery,
        fetch=lambda **kw:pytest.fail('no fallback after failed provider'))
    assert result['status']=='DISCOVERY_UNAVAILABLE' and result['discovery_status']=='ENTITLEMENT_DENIED'
    assert result['official_queries']==[]
