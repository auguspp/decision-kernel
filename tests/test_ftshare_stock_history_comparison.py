"""Synthetic endpoint diagnostics; no live source, secrets or raw-publication proof."""
from copy import deepcopy
from pathlib import Path
import json
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


@pytest.mark.parametrize('wrapped',[False,True])
@pytest.mark.parametrize('kind',['duplicate','outside','bad_ohlc','bad_open_clock','fractional_volume','too_many'])
def test_invalid_candles_are_not_compared(kind,wrapped):
    rows=bars()
    if kind=='duplicate':rows*=2
    if kind=='outside':rows[0]['ts_millis']=h.UNTIL+1
    if kind=='bad_ohlc':rows[0]['open']='12'
    if kind=='bad_open_clock':rows[0]['ts_millis_open']=rows[0]['ts_millis']+1
    if kind=='fractional_volume':rows[0]['volume']='0.5'
    if kind=='too_many':rows*=87
    if wrapped:rows={'code':200,'data':rows}
    with pytest.raises(ValueError):h.compare_candles(rows,prior()[h.SYMBOLS[0]]['bars'],h.SYMBOLS[0])


@pytest.mark.parametrize('code',[0,200])
@pytest.mark.parametrize('empty',[False,True])
def test_documented_candle_data_array_matches_bare_array(code,empty,tmp_path):
    rows=[] if empty else bars()
    payload={'code':code,'data':rows,'message':'SYNTHETIC_PROVIDER_MESSAGE'}
    p=prior()[h.SYMBOLS[0]]['bars']
    assert h.compare_candles(payload,p,h.SYMBOLS[0])==h.compare_candles(rows,p,h.SYMBOLS[0])
    def fake(route,params):
        return (200,h.raw_json(payload)) if route=='history_candles' else fetch(route,params)
    result=h.capture(tmp_path/'out',prior(),fetch=fake,clock=lambda:NOW)
    assert result['source_calls']==9
    assert result['calls'][0]['response_data_type']=='list'
    assert result['calls'][0]['response_root_keys']==['code','data','message']
    assert result['calls'][0]['provider_code']==code
    assert result['results'][0]['ftshare_rows']==len(rows)
    assert result['results'][0]['complete_expected_session_coverage']=='UNKNOWN'
    assert not result['results'][0]['empty_is_no_trading_proof']
    assert not result['independent_raw_replay'] and not result['adjusted_prices_computed']
    assert 'SYNTHETIC_PROVIDER_MESSAGE' not in (tmp_path/'out/safe-report/report.json').read_text()
    assert (tmp_path/'out/runner-local-raw/01.json').read_bytes()==h.raw_json(payload)
    assert result['calls'][0]['sha256']==h.sha256(h.raw_json(payload)).hexdigest()


@pytest.mark.parametrize('bad',[
    {'data':[]}, {'code':'200','data':[]}, {'code':'0','data':[]},
    {'code':True,'data':[]}, {'code':False,'data':[]}, {'code':200.0,'data':[]},
    {'code':None,'data':[]}, {'code':[],'data':[]}, {'code':{},'data':[]},
    {'code':200}, {'code':200,'data':None}, {'code':200,'data':'[]'},
    {'code':200,'data':{}}, {'code':200,'data':{'items':[]}},
    {'code':200,'data':{'records':[]}}, {'code':200,'items':[]},
    {'code':200,'data':[],'items':[]}, {'code':200,'data':[],'status':403},
    {'code':200,'data':[],'message':{}}, {'code':200,'data':[{'data':[]}]},
    {'code':200,'data':[[{}]]}, None, '[]', 200,
])
def test_candle_adapter_never_fuzzily_unwraps_or_coerces(bad):
    with pytest.raises(ValueError):
        h.compare_candles(bad,prior()[h.SYMBOLS[0]]['bars'],h.SYMBOLS[0])


@pytest.mark.parametrize('code',[1,3002,401,403,429])
def test_candle_failure_code_cannot_be_overridden_by_valid_data(code):
    with pytest.raises(ValueError,match=h.STOP.get(code,'PROVIDER_REJECTED')):
        h.compare_candles({'code':code,'data':bars()},prior()[h.SYMBOLS[0]]['bars'],h.SYMBOLS[0])


@pytest.mark.parametrize('change',[{'thscode':h.SYMBOLS[1]},{'adjust':'forward'},{'interval':'1w'}])
def test_candle_wrapper_preserves_reference_identity(change):
    p=prior()[h.SYMBOLS[0]]['bars']; p['data'].update(change)
    with pytest.raises(ValueError,match='REFERENCE_IDENTITY'):
        h.compare_candles({'code':200,'data':bars()},p,h.SYMBOLS[0])


def test_safe_structure_is_allowlisted_bounded_and_value_free(tmp_path):
    secret='SYNTHETIC_SECRET_TOKEN'
    malicious={secret:'not published', 'bad-key':'not published',
               'x'*65:'not published', **{'unknown_'+str(i):i for i in range(100)}}
    payload={'code':200,'data':{'items':bars(),**malicious},'message':secret,**malicious}
    shape=h.response_structure(payload)
    assert shape=={'response_top_type':'dict','response_root_keys':['code','data','message'],
                  'response_root_other_key_count':64,'response_data_type':'dict',
                  'response_data_keys':['items'],'response_data_other_key_count':64,'provider_code':200}
    assert secret not in h.raw_json(shape).decode()
    rows=bars(); rows[0].update(malicious)
    row_shape=h.response_structure({'code':0,'data':rows})
    assert row_shape['response_row_field_names']==sorted(bars()[0])
    assert h.response_structure(rows)['response_row_field_names']==sorted(bars()[0])
    assert secret not in h.raw_json(row_shape).decode()
    def fake(route,params):
        if route=='history_candles':return 200,h.raw_json(payload)
        if route=='history_factors':return 200,h.raw_json(envelope([{'adj_factor':'1.23456789',**malicious}],size=50))
        return fetch(route,params)
    result=h.capture(tmp_path/'out',prior(),fetch=fake,clock=lambda:NOW)
    assert result['results'][0]['status']=='CANDLE_SHAPE'
    assert result['results'][1]['returned_field_names']==['adj_factor']
    safe=(tmp_path/'out/safe-report/report.json').read_text()
    assert all(value not in safe for value in (secret,'unknown_','1.23456789','bad-key','not published'))


@pytest.mark.parametrize('code',['403',True,None,[],{},100000,-100000])
def test_diagnostic_provider_code_never_echoes_arbitrary_or_unbounded_values(code):
    assert 'provider_code' not in h.response_structure({'code':code})


@pytest.mark.parametrize('raw',[b'not json', b'{"code":403,"code":200}', b'\xff',
                               b'{"code":200,"data":[]}', b'{"code":403,"message":"not published"}'])
def test_http_rejection_keeps_global_stop_with_safe_diagnostics(tmp_path,raw):
    result=h.capture(tmp_path/'out',prior(),fetch=lambda *a:(403,raw),clock=lambda:NOW)
    assert result['source_calls']==1 and result['results'][0]['status']=='ENTITLEMENT_DENIED'
    assert all(i['status']=='NOT_ATTEMPTED_AFTER_ENTITLEMENT_DENIED' for i in result['results'][1:])
    assert 'not published' not in (tmp_path/'out/safe-report/report.json').read_text()
    if raw.startswith(b'{"code":200'):
        assert result['calls'][0]['provider_code']==200
        assert result['calls'][0]['response_data_type']=='list'
    if b'"message"' in raw:
        assert result['calls'][0]['provider_code']==403
        assert result['calls'][0]['response_root_keys']==['code','message']


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


def observed_attempt():
    # Projection of native GET actions/runs/36821818724/attempts/1, read
    # 2026-10-01. The original notification was NOT retained. Missing fields
    # below are counterexamples, not a claim about the incident's payload.
    return {'id':36821818724, 'run_attempt':1,
        'head_sha':'1d2e277572f20c57f1ca4d36e02136317043700e',
        'head_branch':'main', 'path':'.github/workflows/radar-smart-money.yml',
        'event':'workflow_dispatch', 'display_title':'FTShare three-stock comparison 20260930',
        'name':'FTShare three-stock comparison 20260930',
        'status':'completed', 'conclusion':'success',
        'repository':{'full_name':'auguspp/decision-kernel'},
        'head_repository':{'full_name':'auguspp/decision-kernel'}}


def publisher_fixture(tmp_path, monkeypatch, native, *, action='requested'):
    from decision_kernel.runtime import current_state_delivery_with_odds_watch as publisher
    from test_current_state_delivery import API
    notification={'action':action, 'workflow_run':{k:observed_attempt()[k]
                  for k in ('id','run_attempt','head_sha')}}
    path=tmp_path/'event.json'; path.write_text(json.dumps(notification))
    summary=tmp_path/'summary.md'
    env={'GH_TOKEN':'TEST_ONLY', 'GITHUB_EVENT_NAME':'workflow_run',
         'GITHUB_EVENT_PATH':str(path), 'TRIGGER_RUN_ID':'36821818724',
         'GITHUB_STEP_SUMMARY':str(summary)}
    for k,v in env.items():monkeypatch.setenv(k,v)
    endpoint='actions/runs/36821818724/attempts/1'
    api=API({endpoint:native, 'git/matching-refs/heads/'+publisher.model.READ_REF:[]})
    api.calls=0
    monkeypatch.setattr(publisher.base,'GitHubAPI',lambda *a,**kw:api)
    collections=[]
    class Collector:
        def __init__(self,*a):self.files={'current-state.json':b'index'}
        def collect(self,refresh):
            collections.append(refresh)
            return {'reading_hash':'f'*64}
    monkeypatch.setattr(publisher,'Collector',Collector)
    args=['--code-commit',observed_attempt()['head_sha'],'--output',str(tmp_path/'out'),'--publish']
    return publisher,args,api,collections,summary,path


@pytest.mark.parametrize('action',['requested','completed'])
@pytest.mark.parametrize('missing',['path','display_title','both'])
def test_notification_shortcut_cannot_authorize_diagnostic_publication(tmp_path,monkeypatch,capsys,action,missing):
    from test_daily_result_publication import allows,event
    data=event(); data['event']['action']=action
    data['event']['workflow_run'].update(observed_attempt())
    for key in (('path','display_title') if missing=='both' else (missing,)):
        del data['event']['workflow_run'][key]
    # This reproduces a weakness of the old early condition with incomplete
    # notification fields, even though full-field synthetic tests pass.
    assert allows(data)
    p,args,api,col,summary,path=publisher_fixture(tmp_path,monkeypatch,observed_attempt(),action=action)
    path.write_text(json.dumps(data['event']))
    assert p.main(args)==0
    assert api.reads==['actions/runs/36821818724/attempts/1']
    assert not api.writes and not col and not (tmp_path/'out').exists()
    assert 'READ_ENTRY_PUBLICATION_SKIPPED: FTSHARE_DIAGNOSTIC' in capsys.readouterr().out
    assert 'no reading collection or public Git writes' in summary.read_text()


@pytest.mark.parametrize('action',['requested','completed'])
@pytest.mark.parametrize('trigger',['schedule','workflow_dispatch'])
def test_normal_smart_money_still_publishes_for_both_actions(tmp_path,monkeypatch,action,trigger):
    native={**observed_attempt(),'event':trigger,'display_title':'radar-smart-money'}
    p,args,api,col,*_=publisher_fixture(tmp_path,monkeypatch,native,action=action)
    assert p.main(args)==0
    assert len(col)==1 and api.writes[-1][0]=='git/refs'


@pytest.mark.parametrize('path',[
    'radar-newsnow-daily.yml','ci.yml','stock-business-research.yml','radar-global-market.yml'])
def test_other_producers_do_not_inherit_smart_money_title_rules(tmp_path,monkeypatch,path):
    native={**observed_attempt(),'path':'.github/workflows/'+path}
    native.pop('display_title')
    p,args,api,col,*_=publisher_fixture(tmp_path,monkeypatch,native,action='completed')
    assert p.main(args)==0 and len(col)==1 and api.writes


@pytest.mark.parametrize('field,value',[
    ('id',36821818725),('run_attempt',2),('head_sha','a'*40),('head_branch','other'),
    ('repository',{}),('head_repository',{'full_name':'other/repo'}),('path',None),
    ('display_title',None),('display_title','unknown purpose'),('event',None)])
def test_unknown_or_conflicting_native_attempt_fails_before_collection_or_write(tmp_path,monkeypatch,capsys,field,value):
    native={**observed_attempt(),field:value}
    p,args,api,col,*_=publisher_fixture(tmp_path,monkeypatch,native)
    assert p.main(args)==2
    assert not api.writes and not col and not (tmp_path/'out').exists()
    assert '"failure_stage": "TRIGGER_QUALIFICATION"' in capsys.readouterr().out


@pytest.mark.parametrize('field',['id','run_attempt','head_sha'])
def test_unknown_notification_attempt_is_not_replaced_by_latest(tmp_path,monkeypatch,field):
    p,args,api,col,summary,path=publisher_fixture(tmp_path,monkeypatch,observed_attempt())
    event=json.loads(path.read_text());del event['workflow_run'][field];path.write_text(json.dumps(event))
    assert p.main(args)==2 and not api.writes and not col
    assert all('/attempts/1' in read for read in api.reads)


def test_unavailable_native_attempt_does_not_fall_back_or_retry(tmp_path,monkeypatch,capsys):
    p,args,api,col,*_=publisher_fixture(tmp_path,monkeypatch,observed_attempt())
    def unavailable(endpoint):
        api.reads.append(endpoint)
        raise p.base.GitHubReadError('GitHub HTTP 503')
    monkeypatch.setattr(api,'get',unavailable)
    assert p.main(args)==2 and len(api.reads)==1 and not api.writes and not col
    assert 'GitHub HTTP 503' in capsys.readouterr().out


def test_direct_publication_schedule_needs_no_upstream_attempt(tmp_path,monkeypatch):
    p,args,api,col,*_=publisher_fixture(tmp_path,monkeypatch,observed_attempt())
    monkeypatch.setenv('GITHUB_EVENT_NAME','schedule')
    assert p.main(args)==0 and len(col)==1 and api.writes
    assert not any(r.startswith('actions/runs/') for r in api.reads)
