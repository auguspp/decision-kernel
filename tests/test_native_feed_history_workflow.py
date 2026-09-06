"""No network: original source, scan, execution and history replayers are used.

Public-branch metadata is simulated locally, not real publication evidence.
"""
from __future__ import annotations

import copy
import json
import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import radar_feed_consumer as consumer
from decision_kernel.runtime import radar_feed_history as history
from decision_kernel.runtime import radar_feed_intake as feed
from decision_kernel.runtime import theme_radar_probe as probe
from decision_kernel.runtime.economic_source_capture import PublicResponse
from test_native_feed_acceptance import code, environment, remote, prepared
from test_radar_feed_consumer import setup, contents, AS_OF
from test_radar_feed_intake import AT, item, xml
from test_theme_radar_probe import fixture
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(feed.feedparser.http, 'get', lambda *a, **k: pytest.fail('no RSS fetch'))


def env_mode(mode='initialize', *, run='999', prior='102', pin='d'*64):
    env = environment(); env['GITHUB_RUN_ID'] = run
    env['NATIVE_HISTORY_MODE'] = mode
    if mode == 'continue':
        env.update(NATIVE_HISTORY_RUN_ID=prior, NATIVE_HISTORY_HASH=pin)
    return env


@pytest.mark.parametrize('mode', ['initialize', 'continue'])
def test_history_intent_is_explicit_and_does_not_enable_market(mode):
    mod = code(); request = mod['intent'](env_mode(mode), AS_OF.isoformat())
    assert request['history_mode'] == mode and request['history_scope'] == mod['TRACKED']
    assert not request['execute_market']
    assert request['history_hash'] == ('d'*64 if mode == 'continue' else None)


@pytest.mark.parametrize('key,value', [
    ('NATIVE_HISTORY_MODE','latest'), ('NATIVE_HISTORY_RUN_ID','latest'),
    ('NATIVE_HISTORY_RUN_ID','999'), ('NATIVE_HISTORY_RUN_ID','100'),
    ('NATIVE_HISTORY_HASH',''), ('NATIVE_HISTORY_HASH','a'*63), ('NATIVE_HISTORY_HASH','A'*64)])
def test_bad_continuation_never_becomes_isolated(key,value):
    env = env_mode('continue'); env[key] = value
    with pytest.raises(ValueError): code()['intent'](env, AS_OF.isoformat())


@pytest.mark.parametrize('mode',['initialize','isolated'])
def test_noncontinuation_rejects_stray_predecessor(mode):
    env = env_mode(mode); env['NATIVE_HISTORY_RUN_ID']='102'
    with pytest.raises(ValueError): code()['intent'](env, AS_OF.isoformat())


def run_again(mod, source, state, output, parent, pin, at, *, batch_size=32, fail_transport=False):
    _, inputs = fixture(); calls=[]
    clock = iter(at + timedelta(seconds=25*i) for i in range(100))
    def transport(path, params):
        calls.append((path, params))
        if fail_transport: pytest.fail('invalid history reached transport')
        assert path == probe.CATALOG, 'restored progress must not execute any old plan'
        key = 'concept_catalog' if params['tag'] == 'cn_concept' else 'industry_catalog'
        return json.dumps(inputs[key]['response']).encode()
    result = mod['trial'](source,state,output,batch_size=batch_size,execute_market=True,
        workflow={'test':'synthetic'},transport=transport,now=lambda:next(clock),pause=lambda _:None,
        history_mode='continue',history_root=parent,history_hash=pin)
    return result,calls


def test_workflow_adapter_resumes_33_sources_without_rescanning_the_prefix(tmp_path):
    rows=[item('No literal catalog label.',url=f'https://www.stats.gov.cn/sj/zxfb/202609/t20260904_{1234500+i}.html',guid=f'e{i}') for i in range(33)]
    mod,state,source,out,_,_,run = prepared(tmp_path,rows)
    first = run(execute_market=False,history_mode='initialize')
    assert first['status']=='SOURCE_SCAN_COMPLETED_NO_LITERAL_MATCH'
    h1=history.register_history(source,tmp_path/'h1',as_of=(AS_OF+timedelta(minutes=10)).isoformat(),
        initialize=True,scans=[out/'scan'])
    r2,calls=run_again(mod,source,state,tmp_path/'second',tmp_path/'h1',h1['history_hash'],AS_OF+timedelta(minutes=11))
    assert r2['status']=='SOURCE_SCAN_COMPLETED_NO_LITERAL_MATCH' and len(calls)==2
    handoff=mod['read'](tmp_path/'second/scan/handoff.json')
    assert handoff['already_scanned_source_records']==32 and handoff['selected_source_records']==1
    h2=history.register_history(source,tmp_path/'h2',as_of=(AS_OF+timedelta(minutes=15)).isoformat(),
        previous=tmp_path/'h1',previous_hash=h1['history_hash'],scans=[tmp_path/'second/scan'])
    r3,calls=run_again(mod,source,state,tmp_path/'third',tmp_path/'h2',h2['history_hash'],AS_OF+timedelta(minutes=16))
    assert r3['status']=='NO_PENDING_SOURCE_SCAN' and len(calls)==2
    options={'history_mode':'continue','history_root':tmp_path/'h2','history_hash':h2['history_hash']}
    assert mod['verify_trial'](source,state,tmp_path/'third',**options)['acceptance_status']=='NO_PENDING_SOURCE_SCAN'
    assert not (tmp_path/'third/execution').exists()
    assert mod['read'](tmp_path/'third/scan/handoff.json')['upstream_pending_versions']==33


@pytest.mark.parametrize('execute_market',[False,True])
def test_restored_exact_execution_only_closes_its_own_plan(tmp_path,execute_market):
    mod,state,source,out,_,_,run=prepared(tmp_path)
    run(execute_market=execute_market,history_mode='initialize')
    h=history.register_history(source,tmp_path/'history',as_of=(AS_OF+timedelta(minutes=15)).isoformat(),
        initialize=True,scans=[out/'scan'],executions=[out/'execution'] if execute_market else [])
    before=contents(tmp_path/'history')
    r,calls=run_again(mod,source,state,tmp_path/'next',tmp_path/'history',h['history_hash'],AS_OF+timedelta(minutes=16))
    assert r['status']=='NO_PENDING_SOURCE_SCAN' and len(calls)==2
    value=mod['read'](tmp_path/'next/scan/handoff.json')
    assert len(value['unexecuted_prior_plans'])==(0 if execute_market else 1)
    assert contents(tmp_path/'history')==before
    assert mod['verify_trial'](source,state,tmp_path/'next',history_mode='continue',
        history_root=tmp_path/'history',history_hash=h['history_hash'])['acceptance_status']==r['status']
    with pytest.raises(ValueError):mod['verify_trial'](source,state,tmp_path/'next')


@pytest.mark.parametrize('damage',['missing','wrong_hash','changed_bytes','future'])
def test_bad_history_fails_before_catalog_transport(tmp_path,damage):
    mod,state,source,out,_,_,run=prepared(tmp_path)
    run(execute_market=False,history_mode='initialize')
    parent=tmp_path/'history'; at=AS_OF+timedelta(minutes=10)
    h=history.register_history(source,parent,as_of=at.isoformat(),initialize=True,scans=[out/'scan'])
    pin=h['history_hash']; later=at+timedelta(minutes=1)
    if damage=='missing':shutil.rmtree(parent)
    elif damage=='wrong_hash':pin='0'*64
    elif damage=='changed_bytes':
        p=next((parent/'scans').iterdir())/'index.html';p.write_bytes(p.read_bytes()+b'\n')
    else:later=at-timedelta(seconds=1)
    with pytest.raises((ValueError,OSError)):
        run_again(mod,source,state,tmp_path/'next',parent,pin,later,fail_transport=True)
    assert not (tmp_path/'next').exists()


def public_source(root,monkeypatch,rows=None):
    """Simulate the public capture branch with fake XML and network forbidden."""
    source=root/'source/capture'
    clock=iter(AT+timedelta(seconds=i) for i in range(30))
    raw=xml([item(published='2026-09-04 09:30:00')])
    monkeypatch.setattr(feed,'fetch_feed',lambda key:PublicResponse(feed.FEEDS[key],200,
        {'content-type':'text/xml','content-length':str(len(raw))},raw))
    context={k:v for k,v in environment().items() if k in (
        'GITHUB_REPOSITORY','GITHUB_WORKFLOW','GITHUB_REF','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA')}
    context.update(GITHUB_WORKFLOW='economic-release-discovery',GITHUB_RUN_ID='100',GITHUB_SHA='b'*40)
    previous=None
    if rows is not None:
        previous=root/'initial-source'
        feed.capture(previous,bootstrap=True,context=context,now=lambda:next(clock))
        raw=xml(rows)
        clock=iter(AT+timedelta(minutes=1,seconds=i) for i in range(30))
    feed.capture(source,previous=previous,bootstrap=previous is None,context=context,now=lambda:next(clock))
    return source


def remote_root(root,monkeypatch,rows=None,execute=False):
    mod=code();public_source(root,monkeypatch,rows)
    env=env_mode();env['NATIVE_EXECUTE']=str(execute).lower()
    req=mod['intent'](env,AS_OF.isoformat())
    run,listing=remote('source')
    for name,value in [('request.json',req),('source-run.json',run),('source-artifacts.json',listing),
        ('source-binding.json',mod['metadata'](req,'source',run,listing))]:mod['write'](root/name,value)
    qualification=mod['qualify'](root,req)
    assert qualification['needs_market']==bool(rows)
    mod['write'](root/'source-qualification.json',qualification)
    mod['write'](root/'history-preparation.json',mod['prepare_history'](root,req))
    mod['write'](root/'verification.json',qualification)
    return mod,req


def history_remote(req,publication):
    run,listing=remote('market');run.update(id=999,name='hithink-stock-dump-trial',
        path='.github/workflows/hithink-stock-dump-trial.yml',head_sha='a'*40,
        updated_at=(AS_OF+timedelta(minutes=2)).isoformat())
    listing['artifacts'][0].update(name='native-feed-history-999-1')
    listing['artifacts'][0]['workflow_run'].update(id=999,head_sha='a'*40)
    return run,listing


def test_no_work_initialization_upload_envelope_and_remote_continuation(tmp_path,monkeypatch):
    root=tmp_path/'one';mod,req=remote_root(root,monkeypatch)
    pub=mod['save_history'](root,req,at=(AS_OF+timedelta(minutes=1)).isoformat())
    assert not (root/'market').exists() and pub['attempt_status']=='BASELINE_NOT_FORWARDED'
    assert not pub['remote_publication_verified'] and not pub['source_delivery_acknowledged']
    before=contents(root/'history-export')
    second=tmp_path/'two';second.mkdir()
    shutil.copytree(root/'source',second/'source');shutil.copytree(root/'history-export',second/'previous-history')
    request=mod['intent'](env_mode('continue',run='1000',prior='999',pin=pub['history_hash']),
        (AS_OF+timedelta(minutes=3)).isoformat())
    run,listing=history_remote(request,pub)
    for name,value in [('history-run.json',run),('history-artifacts.json',listing),
        ('history-binding.json',mod['metadata'](request,'history',run,listing))]:mod['write'](second/name,value)
    ready=mod['prepare_history'](second,request)
    assert ready['status']=='PINNED_HISTORY_REBUILT'
    assert contents(root/'history-export')==before
    assert not (second/'market').exists()


@pytest.mark.parametrize('change',['workflow','history_hash','parent','provenance','extra','future'])
def test_remote_metadata_alone_cannot_qualify_a_history(tmp_path,monkeypatch,change):
    root=tmp_path/'one';mod,req=remote_root(root,monkeypatch)
    pub=mod['save_history'](root,req,at=(AS_OF+timedelta(minutes=1)).isoformat())
    second=tmp_path/'two';second.mkdir();shutil.copytree(root/'source',second/'source')
    shutil.copytree(root/'history-export',second/'previous-history')
    request=mod['intent'](env_mode('continue',run='1000',prior='999',pin=pub['history_hash']),
        (AS_OF+timedelta(minutes=3)).isoformat())
    run,listing=history_remote(request,pub)
    for name,value in [('history-run.json',run),('history-artifacts.json',listing),
        ('history-binding.json',mod['metadata'](request,'history',run,listing))]:mod['write'](second/name,value)
    p=second/'previous-history/publication.json';v=mod['read'](p)
    if change=='workflow':v['workflow']['GITHUB_SHA']='e'*40
    elif change=='history_hash':v['history_hash']='e'*64
    elif change=='parent':v['parent_history_hash']='e'*64
    elif change=='provenance':
        raw=mod['read'](second/'previous-history/history/feed-capture/capture.json');raw['provenance']=probe.SYNTHETIC
        (second/'previous-history/history/feed-capture/capture.json').write_bytes(feed.data(raw))
    elif change=='extra':(second/'previous-history/unknown.json').write_text('{}')
    else:v['registered_at']=(AS_OF+timedelta(days=1)).isoformat()
    p.write_bytes(feed.data(feed._sealed({k:val for k,val in v.items() if k!='publication_hash'},'publication_hash')))
    with pytest.raises(ValueError):mod['prepare_history'](second,request)


@pytest.mark.parametrize('conclusion',['success','failure','cancelled','timed_out'])
def test_only_completed_success_or_failure_can_supply_a_verified_history(conclusion):
    mod=code();req=mod['intent'](env_mode('continue'),AS_OF.isoformat())
    run,listing=remote('market');run.update(id=102,name='hithink-stock-dump-trial',
        path='.github/workflows/hithink-stock-dump-trial.yml',conclusion=conclusion)
    listing['artifacts'][0].update(name='native-feed-history-102-1')
    listing['artifacts'][0]['workflow_run']['id']=102
    if conclusion in {'success','failure'}:assert mod['metadata'](req,'history',run,listing)['run_id']=='102'
    else:
        with pytest.raises(ValueError):mod['metadata'](req,'history',run,listing)


def test_missing_verification_or_wrong_cutoff_cannot_publish_empty_success(tmp_path,monkeypatch):
    root=tmp_path/'one';mod,req=remote_root(root,monkeypatch)
    with pytest.raises(ValueError):mod['save_history'](root,req,at=(AS_OF-timedelta(seconds=1)).isoformat())
    (root/'verification.json').unlink()
    with pytest.raises((ValueError,OSError)):mod['save_history'](root,req,at=(AS_OF+timedelta(minutes=1)).isoformat())
    assert not (root/'history-export').exists()


def test_history_workflow_preserves_order_exact_transfers_and_failed_attempts():
    text=Path('.github/workflows/hithink-stock-dump-trial.yml').read_text()
    job=text.split('  native-feed:\n',1)[1]
    assert 'options: [isolated, initialize, continue]' in text
    assert "default: isolated" in text
    assert job.index('qualify sources')<job.index('Bind explicitly selected history')<job.index('Verify pinned history')<job.index('Bind exact saved market')
    assert job.count('uses: actions/download-artifact@v8')==job.count('digest-mismatch: error')==3
    assert job.index('Rebuild isolated')<job.index('Register replayed history')<job.index('Publish only fully verified')
    save=job.split('- name: Register replayed history',1)[1].split('- name: Preserve isolated',1)[0]
    assert "if: always() && steps.history-save.outcome == 'success'" in save
    assert 'steps.native-capture.outcome' not in save
    assert "HITHINK_FINANCE_API_KEY: ''" in save and '${{ secrets.' not in save
    assert "os.environ['HISTORY_UPLOAD'] == 'success' and os.environ['HISTORY_URL']" in job
    assert 'native-feed-history-${{ github.run_id }}-${{ github.run_attempt }}' in job
    paths=text.split('    paths:\n',1)[1].split('\n\n',1)[0]
    assert 'native' not in paths
    for forbidden in ('schedule:', 'continue-on-error', 'actions/cache', 'sector_radar_producer', 'contents: write'):
        assert forbidden not in text


@pytest.mark.parametrize('failed',[False,True])
def test_public_branch_full_scan_execution_and_export_keep_actual_failure(tmp_path,monkeypatch,failed):
    from decision_kernel.runtime.sector_radar_events import create_sector_radar_candidate_event_ledger
    from decision_kernel.runtime.sector_radar_persistence import write_sector_radar_persistent_bundle
    from decision_kernel.runtime.hithink_dump_trial import DumpTrialError
    from test_theme_radar_probe import THEMES
    root=tmp_path/'run';mod,req=remote_root(root,monkeypatch,[item(THEMES[0]['name'])],execute=True)
    state,inputs=fixture();run,listing=remote('market')
    for name,val in [('market-run.json',run),('market-artifacts.json',listing),
        ('market-binding.json',mod['metadata'](req,'market',run,listing))]:mod['write'](root/name,val)
    write_sector_radar_persistent_bundle(root/'market',market_state=state,
        event_ledger=create_sector_radar_candidate_event_ledger(created_at=state.created_at,source='synthetic'),
        created_at=state.created_at,updated_at=AS_OF-timedelta(minutes=1),source_repository='auguspp/decision-kernel',
        source_workflow='.github/workflows/sector-radar-shadow.yml',source_run_id=101,source_run_attempt=1,
        source_commit_sha='b'*40,parent_hint_mapping_hash='c'*64,last_result_hash=None,
        last_operation_status='VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT')
    calls=[];clock=iter(AS_OF+timedelta(seconds=25*i) for i in range(100))
    def transport(path,params):
        calls.append(path)
        if path==probe.CATALOG:
            body=inputs['concept_catalog' if params['tag']=='cn_concept' else 'industry_catalog']['response']
        elif failed:raise DumpTrialError('HTTP_REJECTED',http_status=429)
        elif path==probe.SNAPSHOT:
            body=copy.deepcopy(inputs['captures']['snapshot']['response'])
            wanted=params['thscodes'].split(',');body['data']['item']=[v for v in body['data']['item'] if v['thscode'] in wanted]
            body['data']['total']=len(wanted)
        else:body=inputs['captures'][('history:' if path==probe.HISTORY else 'members:')+params['thscode']]['response']
        return json.dumps(body).encode()
    result=mod['trial'](root/'source/capture',mod['market_state'](root,req),root/'trial',batch_size=32,
        execute_market=True,workflow=req['workflow'],transport=transport,public_http=True,credential='fake-test-key',
        now=lambda:next(clock),pause=lambda _:None,history_mode='initialize')
    assert result['status']==('MARKET_STAGE_FAILED' if failed else 'MARKET_STAGE_COMPLETED')
    proof=mod['verify_trial'](root/'source/capture',state,root/'trial',history_mode='initialize')
    (root/'verification.json').write_bytes(feed.data(proof))
    publication=mod['save_history'](root,req,at=(AS_OF+timedelta(minutes=10)).isoformat())
    h=history.verify_history(root/'history-export/history')
    assert len(h['scans'])==len(h['executions'])==1
    assert next(iter(h['executions'].values()))['market_stage_succeeded']==(not failed)
    assert publication['attempt_status']==result['status']
    assert not publication['remote_publication_verified']
    receipt=consumer.verify_scan(next((root/'history-export/history/scans').iterdir()))['receipt']
    assert receipt['acquisition_status']=='PLAN_NOT_EXECUTED'
    assert all(b'fake-test-key' not in raw for raw in contents(root/'history-export').values())
    # A red market run with a verified history artifact can be the explicit parent.
    # This simulates transfer; no GitHub request or artifact upload occurs in tests.
    second=tmp_path/'next-run';second.mkdir()
    shutil.copytree(root/'source',second/'source')
    shutil.copytree(root/'history-export',second/'previous-history')
    req2=mod['intent'](env_mode('continue',run='1000',prior='999',pin=publication['history_hash']),
        (AS_OF+timedelta(minutes=12)).isoformat())
    for kind in ('source','market'):
        run_meta,listed=remote(kind)
        for name,value in [(f'{kind}-run.json',run_meta),(f'{kind}-artifacts.json',listed),
            (f'{kind}-binding.json',mod['metadata'](req2,kind,run_meta,listed))]:mod['write'](second/name,value)
    shutil.copytree(root/'market',second/'market')
    run_meta,listed=history_remote(req2,publication)
    run_meta.update(conclusion='failure' if failed else 'success',updated_at=(AS_OF+timedelta(minutes=11)).isoformat())
    for name,value in [('history-run.json',run_meta),('history-artifacts.json',listed),
        ('history-binding.json',mod['metadata'](req2,'history',run_meta,listed))]:mod['write'](second/name,value)
    mod['write'](second/'source-qualification.json',mod['qualify'](second,req2))
    mod['write'](second/'history-preparation.json',mod['prepare_history'](second,req2))
    options=mod['history_options'](second,req2);after=[]
    def catalogs_only(path,params):
        assert path==probe.CATALOG, 'no automatic retry of the historical plan'
        after.append(path);return transport(path,params)
    next_clock=iter(AS_OF+timedelta(minutes=12,seconds=25*i) for i in range(100))
    continued=mod['trial'](second/'source/capture',state,second/'trial',batch_size=32,execute_market=False,
        workflow=req2['workflow'],transport=catalogs_only,public_http=True,credential='fake-test-key',
        now=lambda:next(next_clock),pause=lambda _:None,**options)
    assert continued['status']=='NO_PENDING_SOURCE_SCAN' and len(after)==2
    handoff=mod['read'](second/'trial/scan/handoff.json')
    assert len(handoff['unexecuted_prior_plans'])==int(failed)
    mod['write'](second/'verification.json',mod['verify_trial'](second/'source/capture',state,second/'trial',**options))
    successor=mod['save_history'](second,req2,at=(AS_OF+timedelta(minutes=16)).isoformat())
    h2=history.verify_history(second/'history-export/history')
    assert successor['parent_history_hash']==publication['history_hash']
    assert h2['scans']==h['scans'] and h2['executions']==h['executions']


def test_history_cli_saves_only_after_checks_and_refuses_overwrite(tmp_path,monkeypatch):
    root=tmp_path/'cli';mod,request=remote_root(root,monkeypatch)
    for key,value in env_mode().items():monkeypatch.setenv(key,value)
    monkeypatch.setenv('HITHINK_FINANCE_API_KEY','')
    monkeypatch.setenv('GITHUB_OUTPUT',str(tmp_path/'outputs'))
    assert mod['main'](['history-save','--root',str(root)])==0
    publication=mod['read'](root/'history-export/publication.json')
    assert 'history_hash='+publication['history_hash'] in (tmp_path/'outputs').read_text()
    before=contents(root/'history-export')
    assert mod['main'](['history-save','--root',str(root)])==2
    assert contents(root/'history-export')==before
