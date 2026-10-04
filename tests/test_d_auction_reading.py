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
