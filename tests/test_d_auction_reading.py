"""Native-shaped synthetic archives through the real publisher reader; no I/O."""
from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
import json

import pytest

from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import d_auction_reading as reading
from decision_kernel.runtime import d_auction_probe as probe
from decision_kernel.runtime import tushare_relay as relay
from test_d_auction_probe import AT, TARGET, IDENTITY, fake_request, sources, offline


def fixture(tmp_path, monkeypatch, *, synthetic=False):
    request=fake_request(sources())
    def native(api,params,**kwargs):return request(api,params)
    monkeypatch.setattr(relay,'request',native)
    root=tmp_path/'source'
    report=probe.capture(root,market_session=TARGET,observed_at=AT,
        workflow=IDENTITY,clock=AT.isoformat,request=request if synthetic else None)
    raw_files={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    run={'id':123,'run_attempt':1,'display_title':probe.TITLE,'path':probe.WORKFLOW,
         'head_branch':'main','head_sha':'a'*40,'event':'workflow_dispatch','status':'completed','conclusion':'success',
         'created_at':(AT-timedelta(seconds=5)).isoformat(),'updated_at':(AT+timedelta(seconds=10)).isoformat(),
         'run_started_at':AT.isoformat(),'repository':{'full_name':model.REPOSITORY},
         'head_repository':{'full_name':model.REPOSITORY},'html_url':'https://github.com/auguspp/decision-kernel/actions/runs/123'}
    artifact={'id':321,'name':probe.TITLE+'-123-1','expired':False,'expires_at':(AT+timedelta(days=30)).isoformat()}
    api=SimpleNamespace(calls=0,max_calls=180)
    def get(path):
        assert path==reading.QUERY
        api.calls+=1
        return {'total_count':1,'workflow_runs':[run]}
    api.get=get
    c=SimpleNamespace(api=api,files={'daily.json':b'ORIGINAL_DAILY','README.md':b'ORIGINAL'},archive_cache={})
    c.artifacts=lambda selected:[artifact]
    def archive(a,r):
        c.files['source.zip']=b'SYNTHETIC_ARCHIVE_PLACEHOLDER'
        c.archive_cache[321]=raw_files
        return raw_files,{'artifact_id':321}
    c.archive=archive
    def retain(path,raw):
        c.files[path]=raw
        return {'read_path':path,'bytes':len(raw),'git_blob':model.blob_sha(raw),'sha256':model.sha256(raw),
                'read_ref_rule':'USE_THE_SAME_PINNED_READING_COMMIT'}
    c.retain=retain
    baseline={'checks':{'finished_at':(AT+timedelta(seconds=20)).isoformat()}}
    return c,baseline,raw_files,run,artifact,report


def test_native_shaped_saved_result_read_through_without_sector(tmp_path,monkeypatch):
    c,b,_,_,_,report=fixture(tmp_path,monkeypatch)
    result=reading.read_saved(c,b)
    assert result['status']=='SHADOW_AUCTION_READING' and result['matched']==1
    assert c.files['daily.json']==b'ORIGINAL_DAILY' and c.files['README.md']==b'ORIGINAL'
    assert result['file']['sha256']==model.sha256(c.files[probe.PATH])
    assert json.loads(c.files[probe.PATH])==report and result['new_source_requests']==0


@pytest.mark.parametrize('damage',['synthetic','hash','foreign','attempt','id-bool','future-run','early-report','expired','budget'])
def test_rejection_keeps_other_inputs_and_never_falls_back(tmp_path,monkeypatch,damage):
    c,b,files,run,artifact,_=fixture(tmp_path,monkeypatch,synthetic=damage=='synthetic')
    old=deepcopy(c.files)
    if damage=='hash':files['raw/03-1.json']=b'{}'
    elif damage=='foreign':run['head_repository']['full_name']='someone/else'
    elif damage=='attempt':run['run_attempt']=2
    elif damage=='id-bool':run['id']=True
    elif damage=='future-run':run['updated_at']=(AT+timedelta(days=2)).isoformat()
    elif damage=='early-report':run['run_started_at']=(AT+timedelta(seconds=1)).isoformat()
    elif damage=='expired':artifact['expires_at']=(AT-timedelta(days=1)).isoformat()
    elif damage=='budget':c.api.max_calls=2
    result=reading.read_saved(c,b)
    assert result['status']=='AUCTION_READING_GAP_NOT_QUIET'
    assert c.files==old and c.archive_cache=={}
    assert probe.PATH not in c.files


def test_pending_only_described_not_promoted(tmp_path,monkeypatch):
    c,b,_,run,_,_=fixture(tmp_path,monkeypatch);run['status']='in_progress'
    result=reading.read_saved(c,b)
    assert result['status']=='AUCTION_ATTEMPT_PENDING' and probe.PATH not in c.files


def test_unrelated_stock_run_is_not_auction(tmp_path,monkeypatch):
    c,b,_,run,_,_=fixture(tmp_path,monkeypatch);run['display_title']='stock-market-inputs'
    result=reading.read_saved(c,b)
    assert result['status']=='NO_SAVED_AUCTION_RUN_IN_QUERY' and not result['summary']


def test_failed_sibling_does_not_remove_replayable_source(tmp_path,monkeypatch):
    c,b,_,run,_,_=fixture(tmp_path,monkeypatch);run['conclusion']='failure'
    result=reading.read_saved(c,b)
    assert result['status']=='SHADOW_AUCTION_READING'
    assert result['latest_attempt']['conclusion']=='failure'


def test_existing_native_query_reused_without_requiring_api_cache(tmp_path,monkeypatch):
    c,b,_,run,_,_=fixture(tmp_path,monkeypatch)
    def unexpected(path):raise AssertionError('a second native GET is not needed')
    c.api.get=unexpected
    result=reading.read_saved(c,b,run_query={'total_count':1,'workflow_runs':[run]})
    assert result['matched']==1 and c.api.calls==0


def test_failed_native_query_is_not_retried_by_independent_reader(tmp_path,monkeypatch):
    c,b,_,_,_,_=fixture(tmp_path,monkeypatch)
    before=deepcopy(c.files)
    def unexpected(path):raise AssertionError('failed native GET cannot be retried by sibling')
    c.api.get=unexpected
    result=reading.read_saved(c,b,run_query={})
    assert result['status']=='AUCTION_READING_GAP_NOT_QUIET'
    assert c.files==before and c.api.calls==0


def test_existing_public_price_entry_consumes_query_without_leaking_it(tmp_path,monkeypatch):
    from decision_kernel.runtime import stock_market_input_reading as stock
    c,b,_,run,_,_=fixture(tmp_path,monkeypatch)
    def unexpected(path):raise AssertionError('shared query was already obtained')
    c.api.get=unexpected
    monkeypatch.setattr(stock,'_read_current_prices',lambda *a:{'status':'PRICE_READING',
        'summary':'original price summary','_run_query':{'total_count':1,'workflow_runs':[run]}})
    result=stock.read_current(c,b)
    assert result['auction_probe']['matched']==1 and '_run_query' not in result
    assert result['summary'].startswith('original price summary')


def test_v1_publisher_adds_count_interpretation_without_source_io_or_history_rewrite(tmp_path,monkeypatch):
    from test_d_auction_streak import legacy_files
    c,b,files,run,_,_=fixture(tmp_path,monkeypatch)
    receipt=json.loads(files['receipt.json'])
    name=receipt['calls'][1]['attempts'][-1]['response_file']
    source=json.loads(files[name]); field=source['data']['fields'].index('limit_times')
    source['data']['items'][0][field]=2.0  # Source JSON numeric 2.0, parsed as exact Decimal.
    files[name]=probe.saved.dumps(source)
    receipt['files'][name]={'bytes':len(files[name]),'sha256':model.sha256(files[name])}
    files['receipt.json']=probe.saved.dumps(receipt)
    old=legacy_files(files); original_files=deepcopy(files)
    def no_new_request(*a,**k):raise AssertionError('existing archive is sufficient')
    monkeypatch.setattr(relay,'request',no_new_request)
    result=reading.read_saved(c,b,run_query={'total_count':1,'workflow_runs':[run]})
    published=json.loads(c.files[probe.PATH]); projection=published.pop('prior_temperature_qualification')
    assert result['status']=='SHADOW_AUCTION_READING' and published==old
    assert projection['temperature']['maximum_consecutive']==2
    assert projection['source_report_sha256']==model.sha256(files['report.json'])
    assert files==original_files and c.api.calls==0 and result['new_source_requests']==0
    assert c.files['daily.json']==b'ORIGINAL_DAILY' and c.files['README.md']==b'ORIGINAL'
    assert '不是重新采集' in result['summary'] and '最高连板2' in result['summary']


def test_daily_reader_publishes_same_day_outcome_after_real_saved_auction_reader(tmp_path, monkeypatch):
    from decision_kernel.runtime import stock_market_input_reading as stock
    from decision_kernel.runtime import d_auction_follow_through as outcome
    c, b, _, _, _, _ = fixture(tmp_path, monkeypatch)
    c.code_commit = 'a' * 40
    clock = (AT + timedelta(hours=8)).isoformat()
    b['checks']['finished_at'] = clock
    price_report = {'version': probe.saved.VERSION, 'source': probe.saved.SOURCE,
        'provenance': 'LIVE_TUSHARE_RELAY', 'market_session': TARGET,
        'end_date': TARGET.replace('-', ''), 'columns': probe.saved.COLUMNS,
        'rows': [['600001.SH', '11', None, None, None, 3, 3, 3]],
        'cohort_denominator': 1, 'observed_at': clock, 'received_through': clock}
    descriptor = c.retain('daily-close.json', probe.saved.dumps(price_report))
    daily = {'status': 'PRICE_INPUTS_AVAILABLE_WITH_GAPS', 'summary': 'original price summary',
        'market_session': TARGET, 'file': descriptor, 'source_archive': {'artifact_id': 987},
        'cohort_denominator': 1, 'qualified_windows': {'5': 0, '20': 0, '60': 0},
        'publication_verification': 'REBUILT_FROM_EXACT_RETAINED_RESPONSE_BYTES'}
    monkeypatch.setattr(stock, '_read_current_prices', lambda *_: deepcopy(daily))
    result = stock.read_current(c, b)
    follow = result['auction_follow_through']
    assert follow['status'] == 'SAVED_SAME_SESSION_OUTCOMES' and follow['comparable'] == 1
    assert follow['groups']['MATCHED']['above_auction'] == 1
    assert result['auction_probe']['matched'] == 1 and c.api.calls == 1
    assert result['summary'].startswith('original price summary') and '竞价到同日收盘' in result['summary']
    assert json.loads(c.files[outcome.PATH])['auction_file'] == result['auction_probe']['file']
    assert c.files['daily.json'] == b'ORIGINAL_DAILY' and c.files['README.md'] == b'ORIGINAL'
