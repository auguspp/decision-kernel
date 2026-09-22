"""Financial preparation, not model/research admission. Network is simulated."""
import hashlib
import json
from types import SimpleNamespace
from urllib.error import URLError

import pytest

from decision_kernel.runtime import ftshare_financial as f
from decision_kernel.runtime import stock_research_sources as source

NOW = "2026-09-22T01:00:00+00:00"
TICKER = "603507.SH"


def row(**changes):
    return {"stock_code": TICKER, "stock_name": "test issuer", "year": 2026,
        "report_type": "q2", "report_form_type": "合并未调整", "detail_report_type": "合并未调整",
        "publish_date": "2026-08-26", "t_assets": "123456789012345.67", "t_revenue": 15,
        "net_oper_cash_flow": -2, "parcomp_n_profit": 10, **changes}


def response(rows=None, **data):
    rows = [row()] if rows is None else rows
    return f.raw_json({"code": 200, "data": {"items": rows, "total_items": len(rows),
                                           "total_pages": 1 if rows else 0, **data}})


def capture(tmp_path, raw=None, family="income", status=200):
    return f.capture_family(family=family, ticker=TICKER, output=tmp_path/family,
        fetch=lambda *args: (status, response() if raw is None else raw), clock=lambda: NOW)


def context(captured, **kwargs):
    return f.period_context(captured, year=2026, report_type="q2", **kwargs)


def test_real_consumer_uses_single_issuer_and_preserves_unknowns(tmp_path):
    calls = []
    def get(family, params):
        calls.append((family, params))
        return 200, response([row(year=2025), row()])
    result = source.prepare_financial_context(ticker=TICKER, year=2026, report_type="q2",
        output=tmp_path/'whole', fetch=get, clock=lambda: NOW)
    assert [n for n, _ in calls] == list(f.ROUTES)
    assert all(p == {"stock_code": TICKER, "page": 1, "page_size": 200} for _, p in calls)
    assert result["status"] == "FINANCIAL_CONTEXT_PREPARED_NOT_ADMITTED"
    assert not result["research_execution_allowed"] and result["model_calls"] == result["pdf_calls"] == 0
    assert result["families"]["balance"]["period_semantics"] == "POINT_IN_TIME"
    inc = result["families"]["income"]
    assert inc["period_start"] == "2026-01-01" and inc["period_end"] == "2026-06-30"
    assert inc["excluded_other_periods"] == 1
    assert inc["records"][0]["metrics"]["n_profit"]["status"] == "UNKNOWN"
    assert "parcomp_n_profit" not in inc["records"][0]["metrics"]
    assert inc["records"][0]["provider_fields"]["parcomp_n_profit"] == 10
    assert inc["records"][0]["historical_available_at"] == "NOT_ESTABLISHED"
    assert inc["records"][0]["available_at"] == NOW
    assert (tmp_path/'whole/financial-context.md').read_text().startswith('# 财务资料输入')
    assert (tmp_path/'whole/income/page-1.json').read_bytes() == response([row(year=2025), row()])


def test_decimal_roundtrip_does_not_change_cents(tmp_path):
    raw = response().replace(b'"t_assets":"123456789012345.67"', b'"t_assets":123456789012345.67')
    captured = capture(tmp_path, raw, 'balance')
    result = context(captured)
    assert result['records'][0]['metrics']['t_assets']['value'] == '123456789012345.67'
    assert result == context(json.loads(f.raw_json(captured)))
    assert result['records'][0]['raw_sha256'] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('status,reason', [(401,'AUTHENTICATION_FAILED'), (403,'ENTITLEMENT_DENIED'),
    (404,'HTTP_NOT_FOUND'), (429,'RATE_LIMITED'), (503,'HTTP_REJECTED')])
def test_http_failures_keep_raw_and_never_become_empty(tmp_path,status,reason):
    raw=b'{"code":403,"message":"not available"}'
    result=capture(tmp_path,raw,status=status)
    assert result['status']==reason and not result['rows']
    assert context(result)['status']=='SOURCE_UNAVAILABLE'
    assert (tmp_path/'income/page-1.json').read_bytes()==raw


@pytest.mark.parametrize('raw,reason', [(b'{','PARSE_FAILURE'),(b'{"code":200,"code":200}','PARSE_FAILURE'),
    (b'{"code":200,"data":NaN}','PARSE_FAILURE'),(response([row(stock_code='000920.SZ')]),'IDENTITY_MISMATCH'),
    (response([row(),row()]),'DUPLICATE_RECORD'),(response(total_items=201),'PAGINATION_MISMATCH'),
    (response(total_items=1000,total_pages=5),'PAGINATION_LIMIT')],ids=['json','duplicate-key','nan','identity','duplicate-row','count','limit'])
def test_invalid_provider_returns_do_not_qualify(tmp_path,raw,reason):
    result=capture(tmp_path,raw)
    assert result['status']==reason and result['rows']==[]


@pytest.mark.parametrize('change,status', [({'publish_date':None},'PUBLISH_DATE_UNKNOWN'),
    ({'publish_date':'2026-09-23'},'FUTURE_PUBLICATION'),
    ({'publish_date':'2026-02-01'},'PUBLICATION_BEFORE_PERIOD_END'),
    ({'report_form_type':'母公司'},'REPORT_FORM_UNKNOWN'),
    ({'year':'2026'},'REPORT_PERIOD_UNKNOWN'),
    ({'t_revenue':True},'METRIC_TYPE_INVALID'),
    ({'t_revenue':'nan'},'METRIC_TYPE_INVALID'),
    ({'t_revenue':'1亿元'},'METRIC_TYPE_INVALID')])
def test_period_form_clock_and_amount_not_coerced(tmp_path,change,status):
    assert context(capture(tmp_path,response([row(**change)])))['status']==status


def test_adjusted_variants_not_arbitrarily_combined(tmp_path):
    c=capture(tmp_path,response([row(),row(report_form_type='合并调整',t_revenue=20)]))
    a=context(c);b=context(c,report_form='合并调整')
    assert a['excluded_other_forms']==b['excluded_other_forms']==1
    assert a['records'][0]['metrics']['t_revenue']['value']=='15'
    assert b['records'][0]['metrics']['t_revenue']['value']=='20'


def test_two_published_versions_require_review(tmp_path):
    c=capture(tmp_path,response([row(),row(publish_date='2026-08-27',t_revenue=20)]))
    assert context(c)['status']=='MULTIPLE_REPORT_VERSIONS_REVIEW_REQUIRED'
    assert len(context(c)['records'])==2


@pytest.mark.parametrize('rows', [[],[row(year=2025)]],ids=['empty','other-period'])
def test_no_target_does_not_mean_no_issuer_disclosure(tmp_path,rows):
    c=capture(tmp_path,response(rows)); x=context(c)
    assert x['status']=='TARGET_PERIOD_NOT_RETURNED' and not x['records']
    assert c['status']==('EMPTY' if not rows else 'COMPLETE')


def test_partial_page_failure_preserves_prior_raw_not_qualified_rows(tmp_path):
    rows=[row(stock_name=str(i)) for i in range(200)]
    calls=[]
    def get(family,params):
        calls.append(params['page'])
        if params['page']==2: raise URLError('do not expose transport details')
        return 200,response(rows,total_items=201,total_pages=2)
    c=f.capture_family(family='income',ticker=TICKER,output=tmp_path/'income',fetch=get,clock=lambda:NOW)
    assert calls==[1,2] and c['status']=='TRANSPORT_FAILURE' and not c['rows']
    assert (tmp_path/'income/page-1.json').exists()
    assert 'do not expose' not in (tmp_path/'income/capture.json').read_text()


def test_global_provider_stop_is_not_an_automatic_retry(tmp_path):
    calls=[]
    def get(family,params): calls.append(family); return 429,b'{}'
    r=f.prepare(ticker=TICKER,year=2026,report_type='q2',output=tmp_path/'a',fetch=get,clock=lambda:NOW)
    assert calls==['balance'] and r['status']=='PARTIAL_FINANCIAL_CONTEXT'
    assert r['families']['income']['status']=='NOT_ATTEMPTED_AFTER_PROVIDER_STOP'


def test_create_only_and_symlink_no_network(tmp_path):
    calls=[]
    def get(*args): calls.append(args); return 200,response()
    occupied=tmp_path/'occupied';occupied.mkdir()
    with pytest.raises(FileExistsError):
        f.prepare(ticker=TICKER,year=2026,report_type='q2',output=occupied,fetch=get,clock=lambda:NOW)
    link=tmp_path/'link';link.symlink_to(occupied,target_is_directory=True)
    with pytest.raises(f.DataError,match='UNSAFE_OUTPUT'):
        f.prepare(ticker=TICKER,year=2026,report_type='q2',output=link/'out',fetch=get,clock=lambda:NOW)
    assert calls==[]


def test_future_period_rejected_without_calls(tmp_path):
    calls=[]
    with pytest.raises(f.DataError,match='REPORT_PERIOD_IN_FUTURE'):
        f.prepare(ticker=TICKER,year=2027,report_type='q2',output=tmp_path/'future',
                  fetch=lambda *args:calls.append(args),clock=lambda:NOW)
    assert calls==[]


def test_transport_uses_only_named_key_and_fixed_host(tmp_path,monkeypatch):
    monkeypatch.setenv('FTSHARE_API_KEY','FAKE_TEST_TOKEN')
    monkeypatch.setenv('FTSHARE_BASE_URL','https://untrusted.invalid')
    calls=[]
    class Reply:
        status=200
        headers={'Content-Length':'2'}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):assert n==f.MAX_BYTES+1;return b'{}'
        def geturl(self):return calls[0].full_url
    def open_(req,timeout):calls.append(req);assert timeout==20;return Reply()
    monkeypatch.setattr(f,'build_opener',lambda handler:SimpleNamespace(open=open_))
    assert f.request_page('income',{'stock_code':TICKER,'page':1,'page_size':200})==(200,b'{}')
    assert calls[0].full_url.startswith(f.BASE+'income?')
    assert calls[0].headers['Ftshare_api_key']=='FAKE_TEST_TOKEN'
    assert 'FAKE_TEST_TOKEN' not in calls[0].full_url


def test_no_key_no_request(monkeypatch):
    monkeypatch.delenv('FTSHARE_API_KEY',raising=False)
    monkeypatch.setattr(f,'build_opener',lambda *a:pytest.fail('network without credential'))
    with pytest.raises(f.DataError,match='AUTHENTICATION_UNAVAILABLE'):
        f.request_page('income',{'stock_code':TICKER,'page':1,'page_size':200})


def test_cli_keeps_report_discovery_default_and_financial_opt_in(tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr(source,'prepare_report_discovery',lambda **k:calls.append(k) or
                        {'status':'OFFICIAL_REPORT_LOCATED_NOT_ACQUIRED'})
    assert source.main(['--ticker','603507','--announcement-date','2026-08-26','--period','2026H1',
        '--issuer-name','振江股份','--output',str(tmp_path/'old')])==0
    assert len(calls)==1
    monkeypatch.setattr(source,'prepare_financial_context',lambda **k:calls.append(k) or
                        {'status':'FINANCIAL_CONTEXT_PREPARED_NOT_ADMITTED'})
    assert source.main(['--mode','financial','--ticker',TICKER,'--year','2026','--report-type','q2',
                       '--output',str(tmp_path/'new')])==0
    assert calls[-1]['year']==2026 and calls[-1]['report_type']=='q2'
    with pytest.raises(SystemExit):
        source.main(['--mode','financial','--ticker',TICKER,'--output',str(tmp_path/'bad')])
    assert len(calls)==2


@pytest.mark.parametrize('params', [{}, {'stock_code': TICKER},
    {'stock_code': TICKER, 'page': 1, 'page_size': 200, 'url': 'https://untrusted.invalid'},
    {'stock_code': 'all', 'page': 1, 'page_size': 200}], ids=['none','incomplete','extra','all-market'])
def test_transport_cannot_expand_the_declared_scope(monkeypatch,params):
    monkeypatch.setattr(f,'build_opener',lambda *a:pytest.fail('request before validation'))
    with pytest.raises(f.DataError,match='REQUEST_IDENTITY'):
        f.request_page('income',params)


@pytest.mark.parametrize('failure', ['reflection','redirect','length'])
def test_transport_never_retains_a_reflected_credential_or_redirects(tmp_path,monkeypatch,failure):
    monkeypatch.setenv('FTSHARE_API_KEY','FAKE_TEST_TOKEN')
    class Reply:
        status=200
        headers={'Content-Length':'999'} if failure=='length' else {}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return b'FAKE_TEST_TOKEN' if failure=='reflection' else b'{}'
        def geturl(self):return 'https://other.invalid' if failure=='redirect' else f.BASE+'income?stock_code=603507.SH&page=1&page_size=200'
    monkeypatch.setattr(f,'build_opener',lambda h:SimpleNamespace(open=lambda *a,**kw:Reply()))
    c=f.capture_family(family='income',ticker=TICKER,output=tmp_path/'c',clock=lambda:NOW)
    assert c['status']=={'reflection':'CREDENTIAL_REFLECTION_REJECTED','redirect':'REDIRECT_REJECTED',
                        'length':'RESPONSE_LENGTH_MISMATCH'}[failure]
    assert not (tmp_path/'c/page-1.json').exists()
    assert 'FAKE_TEST_TOKEN' not in (tmp_path/'c/capture.json').read_text()


def test_original_context_budget_is_not_relaxed_or_clipped(tmp_path,monkeypatch):
    monkeypatch.setattr(source,'CONTEXT_BYTES',1)
    with pytest.raises(source.once.TrialError,match='full financial context too large; no clipping'):
        source.prepare_financial_context(ticker=TICKER,year=2026,report_type='q2',output=tmp_path/'c',
            fetch=lambda *args:(200,response()),clock=lambda:NOW)
    assert (tmp_path/'c/financial-context.json').stat().st_size>1
    assert not (tmp_path/'c/financial-context.md').exists()
