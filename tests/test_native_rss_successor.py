from __future__ import annotations

import copy
import json
import runpy
from datetime import timedelta
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import radar_feed_intake as intake
from decision_kernel.runtime.economic_source_capture import PublicResponse
from test_radar_feed_intake import AT, item, xml
from test_sector_radar_audit import prohibit_network

SCRIPT = Path('.github/scripts/prepare-native-rss-successor.py')


def code():
    return runpy.run_path(str(SCRIPT), run_name='test_native_successor')


def environment():
    return {'GITHUB_REPOSITORY':'auguspp/decision-kernel', 'GITHUB_WORKFLOW':'economic-release-discovery',
        'GITHUB_REF':'refs/heads/main', 'GITHUB_RUN_ATTEMPT':'1', 'GITHUB_RUN_ID':'20',
        'GITHUB_SHA':'b'*40, 'SOURCE_EVENT':'push', 'BOOTSTRAP':'false', 'PREVIOUS_RUN_ID':''}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(intake.feedparser.http, 'get', lambda *a, **k: pytest.fail('no parser fetching'))


def prepared(tmp_path, monkeypatch):
    # Synthetic XML through actual feedparser/capture/rebuilder; transport alone is replaced.
    body = xml([item(published='2026-09-04 09:30:00')])
    calls = []
    def fetch(feed):
        calls.append(feed)
        return PublicResponse(intake.FEEDS[feed], 200, {'content-type':'text/xml'}, body)
    monkeypatch.setattr(intake, 'fetch_feed', fetch)
    current = environment()
    previous_context = {k:v for k,v in current.items() if k.startswith('GITHUB_')}
    previous_context.update(GITHUB_RUN_ID='10', GITHUB_SHA='a'*40)
    clock = iter(AT + timedelta(seconds=i) for i in range(20))
    root = tmp_path / 'previous'
    receipt = intake.capture(root, bootstrap=True, context=previous_context, now=lambda:next(clock))
    assert receipt['status'] == 'COMPLETE_FEED_INTAKE'
    registry = json.loads((root/'registry.json').read_text())
    pin = {'schema_version':1, 'purpose':'Synthetic exact-predecessor acceptance, not a live source test',
           'previous_run_id':'10', 'previous_commit':'a'*40, 'artifact_id':'30',
           'artifact_sha256':'d'*64, 'capture_hash':receipt['capture_hash'], 'registry_hash':registry['registry_hash']}
    mod = code(); now = (AT+timedelta(minutes=1)).isoformat()
    preflight = mod['resolve'](current, pin, now=now)
    run = {'id':10,'name':'economic-release-discovery','path':'.github/workflows/economic-release-discovery.yml',
           'repository':{'full_name':'auguspp/decision-kernel','id':55},'head_branch':'main',
           'run_attempt':1,'status':'completed','conclusion':'success','event':'push','head_sha':'a'*40}
    artifact = {'id':30,'name':'radar-feed-intake-10-1','expired':False,'size_in_bytes':1234,
                'digest':'sha256:'+'d'*64,'expires_at':(AT+timedelta(days=90)).isoformat(),
                'workflow_run':{'id':10,'head_branch':'main','head_sha':'a'*40,'repository_id':55,'head_repository_id':55}}
    listing = {'total_count':1,'artifacts':[artifact]}
    binding = mod['bind_metadata'](preflight, run, listing)
    return mod, preflight, binding, run, listing, root, calls


def test_exact_binding_then_actual_unchanged_successor_preserves_initial_versions(tmp_path, monkeypatch):
    mod, pre, binding, _, _, root, calls = prepared(tmp_path, monkeypatch)
    before = {p.name:p.read_bytes() for p in root.iterdir()}
    checked = mod['verify_restored'](pre,binding,root,now=(AT+timedelta(minutes=1)).isoformat())
    assert checked['status'] == 'EXACT_PREDECESSOR_REBUILT_BEFORE_REQUESTS'
    assert len(calls) == 2 and checked['network_calls'] == 0
    clock = iter(AT+timedelta(minutes=2,seconds=i) for i in range(20))
    child = tmp_path/'child'
    result = intake.capture(child, previous=root, context=pre['workflow'], now=lambda:next(clock))
    assert result['status']=='COMPLETE_FEED_INTAKE' and not result['bootstrap']
    assert result['previous_capture_hash']==checked['capture_hash'] and len(calls)==4
    old=json.loads(before['registry.json']); new=json.loads((child/'registry.json').read_text())
    assert new['versions']==old['versions'] and new['initialized_at']==old['initialized_at']
    assert new['parent_registry_hash']==old['registry_hash']
    delta=json.loads((child/'delta.json').read_text()); exported=json.loads((child/'source-rows.json').read_text())
    assert delta['status']=='NO_NEW_FEED_VERSIONS' and delta['changes']==[]
    assert exported['status']=='NO_NEW_SOURCE_ROWS' and exported['sources']==[]
    assert intake.publication_clock('2026-09-04 09:30:00') is None
    assert intake.verify_capture(child)['status']=='ORIGINAL_FEEDS_REGISTRY_AND_PAGE_REBUILT'
    assert before=={p.name:p.read_bytes() for p in root.iterdir()}


@pytest.mark.parametrize('field,value',[('GITHUB_RUN_ATTEMPT','2'),('GITHUB_REF','refs/heads/other'),
    ('GITHUB_REPOSITORY','other/repo'),('GITHUB_SHA','main'),('GITHUB_RUN_ID','20\nX=1'),('SOURCE_EVENT','schedule')])
def test_invalid_current_context_cannot_resolve_a_source_run(field,value):
    env=environment(); env[field]=value
    with pytest.raises((ValueError,TypeError)): code()['resolve'](env,{},now=AT.isoformat())


def test_push_cannot_initialize_and_manual_bootstrap_remains_explicit():
    mod=code(); env=environment(); env['BOOTSTRAP']='true'
    with pytest.raises((ValueError,TypeError)): mod['resolve'](env,None,now=AT.isoformat())
    env['SOURCE_EVENT']='workflow_dispatch'
    assert mod['resolve'](env,now=AT.isoformat())['explicit_baseline'] is True
    env['PREVIOUS_RUN_ID']='10'
    with pytest.raises(ValueError): mod['resolve'](env,now=AT.isoformat())
    env['BOOTSTRAP']='false'
    result=mod['resolve'](env,now=AT.isoformat())
    assert not result['explicit_baseline'] and result['pinned_previous'] is None
    env['PREVIOUS_RUN_ID']='20'
    with pytest.raises(ValueError): mod['resolve'](env,now=AT.isoformat())


@pytest.mark.parametrize('change',['run_sha','run_status','run_attempt','repository','artifact_sha','artifact_expired',
    'artifact_run','artifact_repo','missing','duplicate','incomplete_listing','missing_digest'])
def test_remote_identity_or_expiry_never_selects_another_artifact(tmp_path,monkeypatch,change):
    mod, pre, _, run, listing, _, calls=prepared(tmp_path,monkeypatch)
    a=listing['artifacts'][0]
    if change=='run_sha': run['head_sha']='c'*40
    elif change=='run_status': run['conclusion']='failure'
    elif change=='run_attempt': run['run_attempt']=2
    elif change=='repository': run['repository']['full_name']='other/repo'
    elif change=='artifact_sha': a['digest']='sha256:'+'e'*64
    elif change=='artifact_expired': a['expired']=True
    elif change=='artifact_run': a['workflow_run']['id']=11
    elif change=='artifact_repo': a['workflow_run']['head_repository_id']=999
    elif change=='missing': listing.update(total_count=0,artifacts=[])
    elif change=='duplicate': listing['artifacts'].append(copy.deepcopy(a)); listing['total_count']=2
    elif change=='incomplete_listing': listing['total_count']=2
    elif change=='missing_digest': a.pop('digest')
    with pytest.raises((ValueError,KeyError)): mod['bind_metadata'](pre,run,listing)
    assert len(calls)==2


@pytest.mark.parametrize('change',['source_byte','receipt_sha','receipt_provenance','future_parent','pinned_capture','pinned_registry','binding'])
def test_restored_original_identity_checked_before_new_feed_calls(tmp_path,monkeypatch,change):
    mod,pre,binding,_,_,root,calls=prepared(tmp_path,monkeypatch)
    if change=='source_byte':
        p=root/'nbs-releases.xml'; p.write_bytes(p.read_bytes()+b' ')
    elif change in {'receipt_sha','receipt_provenance'}:
        p=root/'capture.json'; r=json.loads(p.read_text())
        if change=='receipt_sha': r['workflow']['GITHUB_SHA']='c'*40
        else: r['provenance']='SYNTHETIC_TEST_ONLY'
        r['capture_hash']=canonical_hash({k:v for k,v in r.items() if k!='capture_hash'})
        p.write_bytes(intake.data(r))
    elif change in {'future_parent','pinned_capture','pinned_registry'}:
        if change=='future_parent': pre['prepared_at']=AT.isoformat()
        else: pre['pinned_previous']['capture_hash' if change=='pinned_capture' else 'registry_hash']='e'*64
        pre['preflight_hash']=canonical_hash({k:v for k,v in pre.items() if k!='preflight_hash'})
        binding['preflight_hash']=pre['preflight_hash']
        binding['binding_hash']=canonical_hash({k:v for k,v in binding.items() if k!='binding_hash'})
    else: binding['previous_commit']='c'*40
    with pytest.raises(ValueError): mod['verify_restored'](pre,binding,root,now=(AT+timedelta(minutes=1)).isoformat())
    assert len(calls)==2


def test_request_and_metadata_cli_preserve_exact_inputs_and_do_not_fetch(tmp_path,monkeypatch):
    mod,pre,_,run,listing,_,calls=prepared(tmp_path,monkeypatch)
    request=tmp_path/'request.json'; request.write_bytes(intake.data(pre['pinned_previous']))
    # runpy functions own the globals used by main.
    mod['main'].__globals__['REQUEST_PATH']=request
    for k,v in environment().items(): monkeypatch.setenv(k,v)
    outputs=tmp_path/'outputs'; monkeypatch.setenv('GITHUB_OUTPUT',str(outputs))
    root=tmp_path/'invocation'
    assert mod['main'](['request','--root',str(root)])==0
    assert 'previous_run_id=10' in outputs.read_text() and 'baseline=false' in outputs.read_text()
    (root/'predecessor-run.json').write_bytes(intake.data(run))
    (root/'predecessor-artifacts.json').write_bytes(intake.data(listing))
    assert mod['main'](['metadata','--root',str(root)])==0
    assert 'artifact_id=30' in outputs.read_text() and len(calls)==2
    assert mod['main'](['request','--root',str(root)])==2


def test_real_request_only_pins_existing_baseline_not_a_new_signal():
    declaration=json.loads(Path('radar_inputs/native-rss-successor-request.json').read_text())
    pre=code()['resolve'](environment(),declaration,now='2026-09-06T12:00:00+00:00')
    assert pre['previous_run_id']=='34010252507' and pre['pinned_previous']['artifact_id']=='9982240741'
    assert not pre['explicit_baseline']
    assert set(declaration)=={'schema_version','purpose',*code()['PIN_FIELDS']}
