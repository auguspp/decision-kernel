from __future__ import annotations

import copy
import json
import runpy
from datetime import timedelta
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_json
from decision_kernel.runtime import radar_feed_intake as feed
from decision_kernel.runtime import theme_radar_probe as probe
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError
from test_radar_feed_consumer import setup, contents, AS_OF
from test_radar_feed_intake import capture, item, AT, OTHER
from test_theme_radar_probe import fixture, THEMES
from test_sector_radar_audit import prohibit_network

SCRIPT = Path('.github/scripts/native-feed-acceptance.py')


def code():
    return runpy.run_path(str(SCRIPT.resolve()), run_name='native_acceptance_test')


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(feed.feedparser.http, 'get', lambda *a, **k: pytest.fail('no RSS fetch'))


def environment():
    return {'GITHUB_REPOSITORY': 'auguspp/decision-kernel', 'GITHUB_REF': 'refs/heads/main',
            'GITHUB_WORKFLOW': 'hithink-stock-dump-trial', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
            'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': 'a'*40, 'GITHUB_RUN_ID': '999',
            'TRIAL_PURPOSE': 'native-feed-acceptance', 'NATIVE_FEED_RUN_ID': '100',
            'NATIVE_MARKET_RUN_ID': '101', 'NATIVE_BATCH_SIZE': '32', 'NATIVE_EXECUTE': 'false'}


def remote(kind='source'):
    name = 'economic-release-discovery' if kind == 'source' else 'sector-radar-shadow'
    number = 100 if kind == 'source' else 101
    run = {'id': number, 'name': name, 'path': f'.github/workflows/{name}.yml', 'head_sha': 'b'*40,
           'head_branch': 'main', 'repository': {'full_name':'auguspp/decision-kernel','id':55},
           'run_attempt':1, 'status':'completed', 'conclusion':'success', 'event':'workflow_dispatch',
           'created_at': (AS_OF-timedelta(minutes=2)).isoformat(),
           'updated_at': (AS_OF-timedelta(minutes=1)).isoformat()}
    artifact = {'id':200, 'name':'radar-feed-intake-100-1' if kind=='source' else 'sector-radar-state-bundle',
                'expired':False, 'size_in_bytes':100, 'digest':'sha256:'+'c'*64,
                'expires_at':(AS_OF+timedelta(days=90)).isoformat(),
                'workflow_run':{'id':number,'head_branch':'main','head_sha':'b'*40,
                                'repository_id':55,'head_repository_id':55}}
    return run, {'total_count':1,'artifacts':[artifact]}


def prepared(tmp_path, rows=None):
    mod = code()
    state, source, _, _ = setup(tmp_path, rows if rows is not None else [item('We deny ' + ' and '.join(t['name'] for t in THEMES))])
    _, inputs = fixture()
    calls, pauses = [], []
    output = tmp_path/'acceptance'
    clock = iter(AS_OF + timedelta(seconds=25*i) for i in range(100))

    def transport(path, params):
        calls.append((path, params))
        if path == probe.CATALOG:
            key = 'concept_catalog' if params['tag']=='cn_concept' else 'industry_catalog'
            body = inputs[key]['response']
        else:
            assert (output/'scan/scan-receipt.json').exists()
            assert (output/'execution/plan.json').exists()
            if path == probe.SNAPSHOT:
                body = copy.deepcopy(inputs['captures']['snapshot']['response'])
                wanted = params['thscodes'].split(',')
                body['data']['item'] = [r for r in body['data']['item'] if r['thscode'] in wanted]
                body['data']['total'] = len(wanted)
            else:
                prefix = 'history:' if path==probe.HISTORY else 'members:'
                body = inputs['captures'][prefix+params['thscode']]['response']
        return json.dumps(body, ensure_ascii=False).encode()

    def run(execute_market=True, **kwargs):
        return mod['trial'](source, state, output, batch_size=kwargs.pop('batch_size',32),
                 execute_market=execute_market, workflow={'test':'synthetic'},
                 transport=kwargs.pop('transport',transport), now=lambda:next(clock), pause=pauses.append, **kwargs)
    return mod, state, source, output, calls, pauses, run


def test_default_is_explicit_manual_nonexecuting_isolated_intent():
    mod=code(); env=environment(); r=mod['intent'](env, AS_OF.isoformat())
    assert not r['execute_market'] and r['batch_size']==32
    assert r['history_scope']==mod['HISTORY']
    env['NATIVE_MARKET_RUN_ID']=''
    assert mod['intent'](env,AS_OF.isoformat())['market_run_id']==''


@pytest.mark.parametrize('key,value', [
    ('GITHUB_EVENT_NAME','push'), ('TRIAL_PURPOSE','stock-dump'), ('GITHUB_REF','refs/heads/other'),
    ('GITHUB_RUN_ATTEMPT','2'), ('NATIVE_FEED_RUN_ID','100;echo'), ('NATIVE_FEED_RUN_ID','999'),
    ('NATIVE_BATCH_SIZE','33'), ('NATIVE_BATCH_SIZE','0'), ('NATIVE_EXECUTE','yes'), ('NATIVE_MARKET_RUN_ID','latest')])
def test_unbounded_or_implicit_intent_is_refused(key,value):
    env=environment();env[key]=value
    with pytest.raises(ValueError): code()['intent'](env,AS_OF.isoformat())


@pytest.mark.parametrize('kind',['source','market'])
def test_actual_existing_metadata_binding_rules_reused(kind):
    mod=code();r=mod['intent'](environment(),AS_OF.isoformat()); run,listing=remote(kind)
    binding=mod['metadata'](r,kind,run,listing)
    assert binding['artifact_id']=='200' and binding['commit']=='b'*40


@pytest.mark.parametrize('kind',['source','market'])
@pytest.mark.parametrize('change',['failed','foreign','future','expired','digest','duplicate','listing','commit'])
def test_bad_remote_inputs_fail_before_download_or_market(kind,change):
    mod=code();r=mod['intent'](environment(),AS_OF.isoformat());run,listing=remote(kind)
    a=listing['artifacts'][0]
    if change=='failed': run['conclusion']='failure'
    elif change=='foreign': run['repository']['full_name']='someone/else'
    elif change=='future': run['updated_at']=(AS_OF+timedelta(seconds=1)).isoformat()
    elif change=='expired': a['expired']=True
    elif change=='digest': a['digest']=''
    elif change=='duplicate': listing['artifacts'].append(copy.deepcopy(a));listing['total_count']=2
    elif change=='listing': listing['total_count']=2
    else: a['workflow_run']['head_sha']='d'*40
    with pytest.raises(ValueError):mod['metadata'](r,kind,run,listing)


def test_source_only_status_distinguishes_baseline_and_unchanged_successor(tmp_path):
    mod=code(); baseline=tmp_path/'base';later=tmp_path/'later'
    capture(baseline,[item(published='2026-09-04 09:30:00')])
    capture(later,[item(published='2026-09-04 09:30:00')],AT+timedelta(minutes=1),baseline)
    assert mod['source_status'](baseline,as_of=AS_OF.isoformat())['status']=='BASELINE_NOT_FORWARDED'
    s=mod['source_status'](later,as_of=AS_OF.isoformat())
    assert s['status']=='NO_POST_BASELINE_VERSIONS' and not s['needs_market']
    assert s['pending_versions']==0 and not s['source_delivery_acknowledged']


@pytest.mark.parametrize('rows',[[],[item(published='2026-09-04 09:30:00')],[item('',published='2026-09-04')]])
def test_unqualified_or_empty_source_never_calls_catalog_or_market(tmp_path,rows):
    mod,state,source,out,calls,pauses,run=prepared(tmp_path,rows)
    with pytest.raises(ValueError,match='qualification'):run()
    assert calls==pauses==[] and not out.exists()


def test_full_source_scan_executes_exact_plan_and_replays(tmp_path):
    mod,state,source,out,calls,pauses,run=prepared(tmp_path)
    before=contents(source),probe.serialize_sector_radar_market_state(state)
    r=run()
    assert r['status']=='MARKET_STAGE_COMPLETED',r
    assert r['requests_attempted']==7 and len(calls)==7
    assert [p for p,_ in calls].count(probe.CATALOG)==2 and pauses==[20]*6
    proof=mod['verify_trial'](source,state,out)
    assert proof['acceptance_status']=='MARKET_STAGE_COMPLETED' and proof['network_calls']==0
    assert before==(contents(source),probe.serialize_sector_radar_market_state(state))
    assert r['events_created']==r['market_state_writes']==0
    assert not r['source_delivery_acknowledged'] and not r['remote_publication_verified']


def test_scan_only_does_not_execute_plan_or_acknowledge_delivery(tmp_path):
    mod,state,source,out,calls,_,run=prepared(tmp_path)
    r=run(execute_market=False)
    assert r['status']=='SOURCE_SCAN_COMPLETED_PLAN_NOT_EXECUTED' and len(calls)==2
    assert not (out/'execution').exists()
    assert mod['verify_trial'](source,state,out)['acceptance_status']==r['status']


def test_no_literal_match_is_not_an_empty_market_success(tmp_path):
    mod,state,source,out,calls,_,run=prepared(tmp_path,[item('No catalog label.')])
    r=run(); assert r['status']=='SOURCE_SCAN_COMPLETED_NO_LITERAL_MATCH' and len(calls)==2
    assert not (out/'execution').exists()
    assert mod['verify_trial'](source,state,out)['acceptance_status']==r['status']


def test_failed_first_detail_preserves_source_scan_and_stops(tmp_path):
    mod,state,source,out,calls,_,run=prepared(tmp_path)
    # Keep catalog acquisition real to the fixture, then refuse the first detail.
    _,inputs=fixture();attempts=[]
    def transport(path,params):
        attempts.append(path)
        if path != probe.CATALOG:raise DumpTrialError('HTTP_REJECTED',http_status=429)
        key='concept_catalog' if params['tag']=='cn_concept' else 'industry_catalog'
        return json.dumps(inputs[key]['response']).encode()
    r=run(transport=transport)
    assert r['status']=='MARKET_STAGE_FAILED' and len(attempts)==3
    assert (out/'scan/scan-receipt.json').exists() and not (out/'execution/index.html').exists()
    assert mod['verify_trial'](source,state,out)['acceptance_status']=='MARKET_STAGE_FAILED'


def test_unsafe_catalog_is_never_archived_or_followed_by_more_calls(tmp_path):
    mod,state,source,out,_,_,run=prepared(tmp_path);attempts=[]
    def transport(*args):attempts.append(args);return b'{"Authorization":"never retain"}'
    r=run(transport=transport)
    assert r['status']=='INCOMPLETE_ACCEPTANCE' and len(attempts)==1
    assert not (out/'catalog-1.json').exists() and not (out/'scan').exists()
    assert mod['verify_trial'](source,state,out)['status']=='RETAINED_INCOMPLETE_ATTEMPT_NOT_SUCCESS'


@pytest.mark.parametrize('name',['catalog-1.json','context.json','scan/index.html','execution/index.html'])
def test_changed_saved_bytes_cannot_be_a_successful_acceptance(tmp_path,name):
    mod,state,source,out,_,_,run=prepared(tmp_path);run()
    p=out/name;p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(ValueError):mod['verify_trial'](source,state,out)


def test_later_generated_status_cannot_claim_undeclared_execution(tmp_path):
    mod,state,source,out,_,_,run=prepared(tmp_path);run(execute_market=False)
    r=mod['read'](out/'acceptance.json');r['status']='MARKET_STAGE_COMPLETED'
    r=feed._sealed({k:v for k,v in r.items() if k!='acceptance_hash'},'acceptance_hash')
    (out/'acceptance.json').write_bytes(feed.data(r))
    with pytest.raises(ValueError,match='status'):mod['verify_trial'](source,state,out)


def test_public_mode_rejects_synthetic_source_before_requests(tmp_path):
    _,_,_,out,calls,_,run=prepared(tmp_path)
    with pytest.raises(ValueError,match='provenance'):run(public_http=True,credential='fake-only')
    assert calls==[] and not out.exists()
