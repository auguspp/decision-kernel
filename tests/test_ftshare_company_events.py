"""Company inputs use original preparation; synthetic network unless labelled."""
from datetime import date
from decimal import Decimal
import hashlib
import json
from types import SimpleNamespace
from urllib.error import URLError

import pytest
from decision_kernel.runtime import ftshare_company_events as e
from decision_kernel.runtime import stock_research_sources as source

TICKER = '603507.SH'
NOW = '2026-09-22T02:00:00+00:00'
START, END = date(2026, 1, 1), date(2026, 9, 21)


def row(family, **kw):
    value = {
        'contracts': {'security_code': '603507', 'contract_name': 'synthetic framework',
            'dim_rdate': '2026-08-26', 'sign_date': None, 'amounts': '123456789012345.67'},
        'holder_counts': {'stock_code': TICKER, 'report_date': '2026-06-30',
            'publish_date': '2026-08-26', 'holder_num': 100},
        'holder_changes': {'trade_code': '603507', 'holder_name': 'synthetic holder',
            'announcement_date': '2026-08-26', 'shareholding_change_info': '增持',
            'change_start_date': '2026-08-01', 'change_end_date': '2026-08-25',
            'change_quantity': '100.00', 'latest_price': '1.0'},
    }[family]
    return {**value, **kw}


def response(family, rows=None, **kw):
    rows = [row(family)] if rows is None else rows
    if family == 'contracts':
        data = {'records': rows, 'total': len(rows), 'pages': 1 if rows else 0,
                'pageNum': 1, 'pageSize': 200}
    else:
        data = {'items': rows, 'total_items': len(rows), 'total_pages': 1 if rows else 0}
    return e.raw_json({'code': 200, 'data': {**data, **kw}})


def capture(tmp_path, family='contracts', raw=None, status=200):
    return e.capture_family(family=family, ticker=TICKER, output=tmp_path/family,
        fetch=lambda *a: (status, response(family) if raw is None else raw), clock=lambda: NOW)


def window(c):
    return e.window_context(c, start_date=START, end_date=END)


def test_original_consumer_three_different_contracts_and_safe_reading(tmp_path):
    calls = []
    def fetch(family, params):
        calls.append((family, params))
        return 200, response(family, [row(family, contract_name='[unsafe](https://example.org) <script>')])
    r = source.prepare_company_event_context(ticker=TICKER, start_date=START, end_date=END,
        output=tmp_path/'all', fetch=fetch, clock=lambda: NOW)
    assert r['status'] == 'COMPANY_CONTEXT_PREPARED_NOT_ADMITTED'
    assert calls == [(f, e.parameters(f, TICKER, 1)) for f in e.ROUTES]
    assert calls[1][1] == {'stock_code': TICKER}
    assert r['model_calls'] == r['pdf_calls'] == 0 and not r['research_execution_allowed']
    text = (tmp_path/'all/company-event-context.md').read_text()
    assert '人数变化不等于具体股东增减持' in text
    assert '[unsafe]' not in text and '<script>' not in text
    for f in e.ROUTES:
        record = r['families'][f]['records'][0]
        assert record['available_at'] == NOW and record['historical_available_at'] == 'NOT_ESTABLISHED'
        assert record['publish_timezone'] == 'UNKNOWN'
        raw = (tmp_path/'all'/f/'page-1.json').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['raw_sha256']


def test_decimal_and_capture_serialization_roundtrip(tmp_path):
    raw = response('contracts').replace(b'"123456789012345.67"', b'123456789012345.67')
    c = capture(tmp_path, raw=raw)
    assert c['rows'][0]['provider_fields']['amounts'] == Decimal('123456789012345.67')
    r = window(c)
    assert r == window(json.loads(e.raw_json(c)))
    assert r['records'][0]['contract_amount']['value'] == '123456789012345.67'
    assert r['records'][0]['contract_amount']['unit'] == 'PROVIDER_YUAN_CURRENCY_UNVERIFIED'


@pytest.mark.parametrize('family', list(e.ROUTES))
def test_no_window_record_is_not_absence_of_issuer_event(tmp_path, family):
    datefield = {'contracts': 'dim_rdate', 'holder_counts': 'publish_date', 'holder_changes': 'announcement_date'}[family]
    c = capture(tmp_path, family, response(family, [row(family, **{datefield:'2025-01-01'})]))
    assert c['status'] == 'COMPLETE'
    assert window(c)['status'] == 'NO_RECORDS_IN_PUBLICATION_WINDOW'
    assert window(c)['excluded_outside_window'] == 1


@pytest.mark.parametrize('family', list(e.ROUTES))
def test_empty_return_remains_explicit(tmp_path, family):
    c = capture(tmp_path, family, response(family, []))
    assert c['status'] == 'EMPTY' and window(c)['status'] == 'NO_RECORDS_IN_PUBLICATION_WINDOW'


@pytest.mark.parametrize('code,reason', [(401,'AUTHENTICATION_FAILED'),(403,'ENTITLEMENT_DENIED'),
    (404,'HTTP_NOT_FOUND'),(429,'RATE_LIMITED'),(503,'HTTP_REJECTED')])
def test_http_failure_keeps_raw_not_empty(tmp_path,code,reason):
    c = capture(tmp_path, raw=b'not-json', status=code)
    assert c['status'] == reason and not c['rows']
    assert (tmp_path/'contracts/page-1.json').read_bytes() == b'not-json'
    assert window(c)['status'] == 'SOURCE_UNAVAILABLE'


@pytest.mark.parametrize('raw,reason', [(b'{','PARSE_FAILURE'),(b'{"code":200,"code":200}','PARSE_FAILURE'),
    (b'{"code":NaN}','PARSE_FAILURE'),(response('contracts',[row('contracts',security_code='000920')]),'IDENTITY_MISMATCH'),
    (response('contracts',[row('contracts'),row('contracts')]),'DUPLICATE_RECORD'),
    (response('contracts',total=201),'PAGINATION_MISMATCH'),
    (response('contracts',total=1000,pages=5),'PAGINATION_LIMIT')],
    ids=['syntax','duplicate-key','nan','identity','duplicate-row','page-count','page-limit'])
def test_bad_responses_never_qualify(tmp_path,raw,reason):
    c = capture(tmp_path,raw=raw)
    assert c['status'] == reason and c['rows'] == []


@pytest.mark.parametrize('family,changed,reason', [
    ('contracts',{'dim_rdate':None},'EVENT_DATE_UNKNOWN'),
    ('contracts',{'dim_rdate':'2026-09-23'},'FUTURE_PUBLICATION'),
    ('contracts',{'amounts':True},'AMOUNT_INVALID'),
    ('contracts',{'amounts':'1亿元'},'AMOUNT_INVALID'),
    ('contracts',{'sign_date':'2026-09-01'},'SIGNING_AFTER_PUBLICATION_REVIEW_REQUIRED'),
    ('holder_counts',{'holder_num':True},'HOLDER_COUNT_INVALID'),
    ('holder_counts',{'holder_num':-1},'HOLDER_COUNT_INVALID'),
    ('holder_counts',{'report_date':'2026-09-01'},'HOLDING_DATE_AFTER_PUBLICATION'),
    ('holder_changes',{'holder_name':''},'HOLDER_CHANGE_IDENTITY'),
    ('holder_changes',{'shareholding_change_info':'未知'},'HOLDER_CHANGE_IDENTITY'),
    ('holder_changes',{'change_start_date':'2026-09-01'},'CHANGE_DATE_ORDER')])
def test_material_dates_and_meanings_not_coerced(tmp_path,family,changed,reason):
    c = capture(tmp_path,family,response(family,[row(family,**changed)]))
    assert window(c)['status'] == reason and not window(c)['records']


def test_holder_count_history_not_forced_into_financial_pagination(tmp_path):
    rows = [row('holder_counts',holder_num=i) for i in range(250)]
    c = capture(tmp_path,'holder_counts',response('holder_counts',rows))
    assert c['status']=='COMPLETE' and len(c['rows'])==250 and len(c['requests'])==1


@pytest.mark.parametrize('family', ['contracts','holder_changes'])
def test_second_page_failure_retains_first_without_partial_success(tmp_path,family):
    calls=[]
    def fetch(f,p):
        calls.append(p['page'])
        if p['page']==2: raise URLError('private diagnostic never copied')
        rows=[row(f,seq=i) for i in range(200)]
        return 200,response(f,rows,**({'total':201,'pages':2} if f=='contracts' else {'total_items':201,'total_pages':2}))
    c=e.capture_family(family=family,ticker=TICKER,output=tmp_path/family,fetch=fetch,clock=lambda:NOW)
    assert calls==[1,2] and c['status']=='TRANSPORT_FAILURE' and c['rows']==[]
    assert (tmp_path/family/'page-1.json').exists()
    assert 'private diagnostic' not in (tmp_path/family/'capture.json').read_text()


@pytest.mark.parametrize('code', [401,403,429])
def test_provider_stop_prevents_later_families(tmp_path,code):
    calls=[]
    def fetch(f,p):
        calls.append(f);return code,b'{}'
    r=e.prepare(ticker=TICKER,start_date=START,end_date=END,output=tmp_path/'all',fetch=fetch,clock=lambda:NOW)
    assert calls==['contracts']
    assert r['families']['holder_counts']['status']=='NOT_ATTEMPTED_AFTER_PROVIDER_STOP'


def test_transport_failure_does_not_erase_other_families(tmp_path):
    def fetch(f,p):
        if f=='contracts':raise URLError('not persisted')
        return 200,response(f)
    r=e.prepare(ticker=TICKER,start_date=START,end_date=END,output=tmp_path/'all',fetch=fetch,clock=lambda:NOW)
    assert r['status']=='PARTIAL_COMPANY_CONTEXT'
    assert r['families']['holder_counts']['status']=='SECONDARY_CONTEXT_READY'


def test_auth_fixed_host_and_secret_reflection_not_retained(tmp_path,monkeypatch):
    monkeypatch.setenv('FTSHARE_API_KEY','synthetic-test-credential')
    class Response:
        status=200;headers={}
        def __init__(self,url):self.url=url
        def geturl(self):return self.url
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return b'synthetic-test-credential'
    def get(req,timeout):
        assert req.full_url.startswith(e.BASE+e.ROUTES['contracts']+'?symbol=603507&')
        assert 'synthetic-test-credential' not in req.full_url
        assert req.get_header('Ftshare_api_key')=='synthetic-test-credential'
        return Response(req.full_url)
    monkeypatch.setattr(e,'build_opener',lambda *a:SimpleNamespace(open=get))
    c=e.capture_family(family='contracts',ticker=TICKER,output=tmp_path/'capture',clock=lambda:NOW)
    assert c['status']=='CREDENTIAL_REFLECTION_REJECTED'
    assert not (tmp_path/'capture/page-1.json').exists()
    assert b'synthetic-test-credential' not in (tmp_path/'capture/capture.json').read_bytes()


@pytest.mark.parametrize('params',[{'symbol':'603507','page':1,'page_size':200,'url':'https://evil.invalid'},
    {'symbol':'603507','page':True,'page_size':200},{'symbol':'http://x','page':1,'page_size':200}])
def test_invalid_request_rejected_before_credentials(params,monkeypatch):
    monkeypatch.delenv('FTSHARE_API_KEY',raising=False)
    with pytest.raises(e.DataError,match='REQUEST_IDENTITY'): e.request_page('contracts',params)


def test_source_context_budget_does_not_clip(tmp_path,monkeypatch):
    monkeypatch.setattr(source,'CONTEXT_BYTES',10)
    with pytest.raises(Exception,match='full company event context too large'):
        source.prepare_company_event_context(ticker=TICKER,start_date=START,end_date=END,output=tmp_path/'all',
            fetch=lambda f,p:(200,response(f)),clock=lambda:NOW)
    assert (tmp_path/'all/company-event-context.json').exists()
    assert not (tmp_path/'all/company-event-context.md').exists()


def test_create_only_output(tmp_path):
    with pytest.raises(FileExistsError):
        e.prepare(ticker=TICKER,start_date=START,end_date=END,output=tmp_path,clock=lambda:NOW)


def test_cli_routes_to_original_entry(tmp_path,monkeypatch):
    calls=[]
    def run(**kw):calls.append(kw);return {'status':'COMPANY_CONTEXT_PREPARED_NOT_ADMITTED'}
    monkeypatch.setattr(source,'prepare_company_event_context',run)
    assert source.main(['--mode','company-events','--ticker',TICKER,'--start-date','2026-01-01',
        '--end-date','2026-09-21','--output',str(tmp_path/'out')])==0
    assert calls[0]['start_date']==START


@pytest.mark.parametrize('extra',[['--year','2026'],['--period','2026H1'],['--announcement-date','2026-08-26']])
def test_cli_rejects_mixed_modes(tmp_path,extra):
    with pytest.raises(SystemExit):source.main(['--mode','company-events','--ticker',TICKER,
        '--start-date','2026-01-01','--end-date','2026-09-21','--output',str(tmp_path/'out'),*extra])
