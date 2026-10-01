"""Synthetic endpoint diagnostics; no live source, secrets or raw-publication proof."""
from copy import deepcopy
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import ftshare_stock_history_comparison as h
from decision_kernel.runtime import ftshare_market_inputs as client

NOW = '2026-10-01T05:00:00+00:00'
TS = 1790697600000


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a: pytest.fail('live network'))
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a: pytest.fail('live DNS'))


def bars():
    return [{'open': '10', 'high': '11', 'low': '9', 'close': '10.5',
             'volume': 100, 'turnover': '1050', 'ts_millis': TS+15*3600000,
             'ts_millis_open': TS+9*3600000+30*60000}]


def prior():
    return {s: {'bars': {'code': 0, 'data': {'thscode': s, 'adjust': 'none', 'interval': '1d',
              'item': [{'date_ms': TS, 'open_price': '10', 'high_price': '11', 'low_price': '9',
                        'close_price': '10.5', 'volume': 100, 'turnover': '1050'}]}},
                'actions': {'code': 3002, 'data': None, 'message': 'No adjustment events'}} for s in h.SYMBOLS}


def envelope(rows, page=1, size=200, total=None):
    total = len(rows) if total is None else total
    return {'code': 200, 'data': {'pageNum': page, 'pageSize': size, 'total': total,
             'pages': (total+size-1)//size, 'records': rows}}


def fetch(route, params):
    if route == 'history_candles': obj = bars()
    else: obj = envelope([], size=params['page_size'])
    return 200, h.raw_json(obj)


def test_nine_calls_safe_summary_only_and_no_empty_factor_one(tmp_path):
    result = h.capture(tmp_path/'out', prior(), fetch=fetch, clock=lambda: NOW)
    assert result['source_calls'] == 9 and not result['adjusted_prices_computed']
    assert len(list((tmp_path/'out/runner-local-raw').iterdir())) == 9
    assert list((tmp_path/'out/safe-report').iterdir()) == [tmp_path/'out/safe-report/report.json']
    candles = result['results'][0]
    assert candles['matched_sessions'] == 1 and set(candles['mismatch_counts'].values()) == {0}
    factors = result['results'][1]
    assert factors['status'] == 'RAW_FACTOR_SCHEMA_UNQUALIFIED' and not factors['empty_is_factor_one']
    events = result['results'][2]
    assert events['hithink_provider_code'] == 3002 and not events['hithink_nonzero_is_empty']
    assert result['raw_custody'] == 'RUNNER_LOCAL_EPHEMERAL' and not result['independent_raw_replay']


def test_validated_factor_pagination_caps_at_twelve(tmp_path):
    calls = []
    def fake(route, params):
        calls.append((route, params))
        if route == 'history_factors':
            page=params['page']
            rows=[{'unknown_factor': str(i)} for i in range(50 if page==1 else 11)]
            return 200, h.raw_json(envelope(rows, page, 50, 61))
        return fetch(route, params)
    result=h.capture(tmp_path/'out', prior(), fetch=fake, clock=lambda: NOW)
    assert len(calls)==12 and all(i['pagination_complete'] for i in result['results'] if i['route']=='history_factors')
    assert all(i['factor_date_coverage']=='UNKNOWN' for i in result['results'] if i['route']=='history_factors')


@pytest.mark.parametrize('total',[101,10000])
def test_beyond_factor_budget_does_not_claim_complete(tmp_path,total):
    def fake(route, params):
        if route=='history_factors':
            return 200,h.raw_json(envelope([{}]*50,1,50,total))
        return fetch(route,params)
    result=h.capture(tmp_path/'out',prior(),fetch=fake,clock=lambda:NOW)
    assert result['source_calls']==9
    assert not result['results'][1]['pagination_complete']


@pytest.mark.parametrize('bad',[{'code':200,'data':{'items':[]}}, {'code':3002,'data':None}, []])
def test_unknown_factor_schema_and_rejection_not_empty(tmp_path,bad):
    def fake(route,params):return (200,h.raw_json(bad)) if route=='history_factors' else fetch(route,params)
    result=h.capture(tmp_path/'out',prior(),fetch=fake,clock=lambda:NOW)
    assert result['source_calls']==9 and result['results'][1]['status']!='RAW_FACTOR_SCHEMA_UNQUALIFIED'
    assert not result['results'][1]['pagination_complete']


@pytest.mark.parametrize('code',[401,403,429])
@pytest.mark.parametrize('http',[True,False])
def test_auth_entitlement_rate_limits_stop_global_without_retry(tmp_path,code,http):
    calls=[]
    def fake(*a):calls.append(a);return (code,b'{}') if http else (200,h.raw_json({'code':code}))
    result=h.capture(tmp_path/'out',prior(),fetch=fake,clock=lambda:NOW)
    assert len(calls)==1 and result['results'][0]['status']==h.STOP[code]
    assert all(i['status']=='NOT_ATTEMPTED_AFTER_'+h.STOP[code] for i in result['results'][1:])


@pytest.mark.parametrize('change',[{'limit':1},{'adjust_kind':'forward'},{'symbol':'600519.SH'},
                                   {'until_ts_millis':h.UNTIL+1},{'since_ts_millis':h.SINCE-1}])
def test_unreviewed_requests_stop_before_credentials(monkeypatch,change):
    params={**h.parameters('history_candles',h.SYMBOLS[0]),**change}
    monkeypatch.setattr(client.os.environ,'get',lambda *a:pytest.fail('secret read'))
    with pytest.raises(ValueError,match='REQUEST_SCOPE'):client.request('history_candles',params)


def test_documented_dates_no_trade_date_fallback_and_no_dividend_ann_filter():
    p=h.parameters('history_factors',h.SYMBOLS[1]);assert p['start_date']=='20260707' and p['end_date']=='20260930'
    assert 'trade_date' not in p and 'since_date' not in h.parameters('history_dividends',h.SYMBOLS[1])
    assert 'limit' not in h.parameters('history_candles',h.SYMBOLS[0])


def test_dividend_totals_consumed_once_not_summed():
    s=h.SYMBOLS[2]
    rows=[{'symbol':s,'ann_date':'2026-06-30','ex_dividend_date':'2026-07-14',
           'cash_dividend_ratio':'0.10','total_cash_dividend_ratio':'0.15'},
          {'symbol':s,'ann_date':'2026-06-30','ex_dividend_date':'2026-07-14',
           'cash_dividend_ratio':'0.05','total_cash_dividend_ratio':'0.15'}]
    p={'code':0,'data':{'thscode':s,'item':[{'ex_date_ms':1783958400000,'dividend_per_share':'0.15'}]}}
    out=h.dividend_summary(rows,p,s,True)
    assert out['window_ex_date_groups']==1 and out['cash_numeric_mismatch_count']==0
    assert out['cash_comparison_qualification']=='NUMERIC_DIFFERENCE_UNQUALIFIED_UNITS'
    rows[1]['total_cash_dividend_ratio']='0.2'
    with pytest.raises(ValueError,match='DIVIDEND_TOTAL_CONFLICT'):h.dividend_summary(rows,p,s,True)


@pytest.mark.parametrize('kind',['duplicate','outside','bad_ohlc','envelope'])
def test_invalid_candles_are_not_compared(kind):
    rows=bars()
    if kind=='duplicate':rows*=2
    if kind=='outside':rows[0]['ts_millis']=h.UNTIL+1
    if kind=='bad_ohlc':rows[0]['open']='12'
    if kind=='envelope':rows={'code':200,'data':rows}
    with pytest.raises(ValueError):h.compare_candles(rows,prior()[h.SYMBOLS[0]]['bars'],h.SYMBOLS[0])


def test_existing_client_fixed_host_and_reflection_guard(monkeypatch):
    monkeypatch.setenv('FTSHARE_API_KEY','SYNTHETIC_TOKEN')
    monkeypatch.setenv('FTSHARE_BASE_URL','https://untrusted.invalid')
    captured=[]
    class Response:
        status=200;headers={}
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def geturl(self):return captured[-1].full_url
        def read(self,n):return b'SYNTHETIC_TOKEN'
    class Opener:
        def open(self,req,timeout):captured.append(req);return Response()
    monkeypatch.setattr(client,'build_opener',lambda *a:Opener())
    with pytest.raises(ValueError,match='CREDENTIAL_REFLECTION_REJECTED'):
        client.request('history_dividends',h.parameters('history_dividends',h.SYMBOLS[0]))
    assert captured[0].full_url.startswith(h.ROUTES['history_dividends']+'?')
    assert captured[0].get_header('Ftshare_api_key')=='SYNTHETIC_TOKEN'


def test_workflow_is_isolated_and_never_uploads_raw():
    source=(Path(__file__).parents[1]/'.github/workflows/radar-smart-money.yml').read_text()
    new,old=source.split('  compare-ftshare-stock-history:',1)[1].split('  capture-smart-money:',1)
    assert "inputs.ftshare-stock-history != 'three-stock-20260930'" in old
    assert "github.event_name == 'workflow_dispatch'" in new and 'inputs.code-sha == github.sha' in new
    assert '!inputs.relay-only' in new and '!inputs.relay-reports-only' in new and '!inputs.repair-pending' in new
    assert 'safe-report/report.json' in new and 'runner-local-raw' not in new
    assert 'HITHINK_FINANCE_API_KEY' not in new and 'TUSHARE_PROXY_API_KEY' not in new
    assert 'MAIN_CI_NOT_PASSED' in new and "artifact-ids: '11141865519'" in new


@pytest.mark.parametrize('field,value',[('event','schedule'),('head_branch','other'),
    ('path','.github/workflows/other.yml'),('display_title','radar-smart-money')])
def test_exclusion_never_hides_production_or_near_matches(field,value):
    run={'id':1,'event':'workflow_dispatch','head_branch':'main',
         'path':'.github/workflows/radar-smart-money.yml','display_title':h.RUN_TITLE}
    assert h.is_comparison_run(run)
    assert not h.is_comparison_run({**run,field:value})


def test_reader_excludes_exact_comparison_before_selecting_latest(tmp_path,monkeypatch):
    from decision_kernel.runtime import smart_money_reading as reading
    from test_smart_money_reading import setup
    col,base,run,job,artifact=setup(tmp_path)
    comparison={**run,'id':run['id']+1,'display_title':h.RUN_TITLE,'created_at':NOW}
    col.api.responses[reading.QUERY]={'total_count':2,'workflow_runs':[comparison,run]}
    out=reading.native(col)
    assert out['observation'] is not None
    assert out['latest_attempt']['id']==run['id'] and out['excluded_comparison_runs']==[comparison['id']]


def test_only_comparisons_in_bounded_history_is_not_never_run(tmp_path):
    from decision_kernel.runtime import smart_money_reading as reading
    from test_smart_money_reading import setup
    col,base,run,*_=setup(tmp_path)
    col.api.responses[reading.QUERY]={'total_count':99,'workflow_runs':[{**run,'display_title':h.RUN_TITLE}]}
    out=reading.native(col)
    assert out['status']=='ONLY_COMPARISON_RUNS_IN_BOUNDED_WINDOW' and out['observation'] is None


def test_publisher_and_control_exclusion_is_exact_and_keeps_scanned_budget_guard():
    from itertools import product
    from test_daily_result_publication import allows, event

    root=Path(__file__).parents[1]
    # Execute the checked-in publisher condition, including both native actions;
    # a text match alone cannot establish exact exclusion or expression validity.
    for action, path, trigger, title in product(
            ('requested', 'completed'),
            ('.github/workflows/radar-smart-money.yml', '.github/workflows/other.yml'),
            ('workflow_dispatch', 'schedule'),
            (h.RUN_TITLE, 'radar-smart-money')):
        data=event(); data['event']['action']=action
        data['event']['workflow_run'].update(name='radar-smart-money', path=path,
                                             event=trigger, display_title=title)
        comparison=(path=='.github/workflows/radar-smart-money.yml' and
                    trigger=='workflow_dispatch' and title==h.RUN_TITLE)
        assert allows(data) is (not comparison)
    control=(root/'.github/scripts/smart-money-control.py').read_text()
    assert control.index('runs=[r for r in runs if not is_comparison_run(r)]') < control.index('today_runs=')
    assert 'len(scanned_runs)==30' in control and 'comparison_source_quota' in control


def test_production_control_count_preserves_old_runs_and_excludes_only_diagnostic():
    import runpy
    scope=runpy.run_path('.github/scripts/smart-money-control.py')['production_run_scope']
    base={'head_branch':'main','path':'.github/workflows/radar-smart-money.yml',
          'created_at':NOW,'event':'workflow_dispatch','display_title':'radar-smart-money'}
    normal=[{**base,'id':1},{**base,'id':2,'event':'schedule'}]
    diagnostics=[{**base,'id':i,'display_title':h.RUN_TITLE} for i in range(3,7)]
    runs,today,excluded=scope({'total_count':6,'workflow_runs':normal+diagnostics},'2026-10-01')
    assert runs==today==normal and excluded==[3,4,5,6]
    assert scope({'total_count':2,'workflow_runs':normal},'2026-10-01')==(normal,normal,[])
    with pytest.raises(ValueError,match='DAILY_RUN_SCOPE_INCOMPLETE'):
        scope({'total_count':40,'workflow_runs':[dict(base,id=i,display_title=h.RUN_TITLE) for i in range(30)]},'2026-10-01')
