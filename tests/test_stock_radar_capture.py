from __future__ import annotations

import copy
import json
import runpy
import shutil
from datetime import timedelta
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.sector_parent_hints import load_sector_parent_hints
from decision_kernel.runtime.sector_radar_persistence import write_sector_radar_persistent_bundle
from test_stock_radar_reading import prepared, ROOT, NOW, synthetic_references
from test_sector_radar_audit import prohibit_network
from test_native_feed_acceptance import environment, remote

SCRIPT=Path('.github/scripts/capture-stock-reading.py')


def code():
    return runpy.run_path(str(SCRIPT.resolve()),run_name='stock_capture_test')


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def setup(tmp_path):
    mod=code();state,ledger,_,plan,response,calls=prepared()
    state_dir=tmp_path/'state'
    hints=load_sector_parent_hints(ROOT/'radar_inputs/sector-parent-hints-2026-09-05.json')
    write_sector_radar_persistent_bundle(state_dir,market_state=state,event_ledger=ledger,
        created_at=NOW,updated_at=NOW,source_repository='auguspp/decision-kernel',
        source_workflow='.github/workflows/sector-radar-shadow.yml',source_run_id=101,
        source_run_attempt=1,source_commit_sha='b'*40,parent_hint_mapping_hash=hints.mapping_hash,
        last_result_hash=None,last_operation_status='VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT')
    out=tmp_path/'reading';clock=iter(NOW+timedelta(seconds=i*21) for i in range(100));pauses=[]
    def run(**kwargs):
        return mod['capture'](ROOT,state_dir,out,observed_at=NOW,transport=kwargs.pop('transport',response),
            workflow={'test':'synthetic'},now=kwargs.pop('now',lambda:next(clock)),pause=pauses.append,
            reference_inputs=kwargs.pop('reference_inputs',synthetic_references(state,[r['thscode'] for r in plan['issuers']])),
            **kwargs)
    return mod,state_dir,out,calls,pauses,run


@pytest.fixture(scope='module')
def complete_capture_baseline(tmp_path_factory):
    """One real immutable successful capture reused only as negative-test input bytes."""
    root=tmp_path_factory.mktemp('stock-capture-baseline')
    mod,_,out,_,_,run=setup(root)
    report=run()
    assert report['status']==mod['COMPLETE']
    assert mod['verify'](out)['status']=='ORIGINAL_STOCK_INPUTS_AND_PAGE_REBUILT'
    return out


@pytest.fixture
def complete_capture_copy(tmp_path,complete_capture_baseline):
    """Private bytes for one mutation; verification is never cached or shared."""
    out=tmp_path/'reading'
    shutil.copytree(complete_capture_baseline,out)
    return code(),out


def test_full_capture_replays_actual_calculation_and_synthetic_page(tmp_path):
    mod,state,out,calls,pauses,run=setup(tmp_path)
    original=mod['inventory'](state)
    report=run()
    assert report['status']==mod['COMPLETE'],report
    result=mod['verify'](out)
    assert result['status']=='ORIGINAL_STOCK_INPUTS_AND_PAGE_REBUILT'
    assert result['stock_count']>=1 and result['provenance']==mod['SYNTHETIC']
    assert result['requests_replayed']==len(calls) and result['network_calls']==0
    assert pauses==[20]*(len(calls)-1)
    assert original==mod['inventory'](state)
    assert '合成验收样本' in (out/'index.html').read_text()
    assert (out/'inputs/radar_inputs/economic-reviewed-releases').is_dir()
    assert report['remote_upload_verified'] is False and report['recommendation'] is None
    assert report['response_semantics']=='DECODED_PROVIDER_JSON_NOT_ORIGINAL_HTTP_BYTES'


def test_source_copy_is_sufficient_for_replay_without_original_state_directory(tmp_path):
    mod,state,out,_,_,run=setup(tmp_path);run()
    shutil.rmtree(state)
    assert mod['verify'](out)['stock_count']>=1


@pytest.mark.parametrize('name',['stock-reading.json','index.html','plan.json','association.json','responses/01.json',
    'inputs/state/market-state.json','inputs/radar_inputs/company-evidence/002714-muyuan-h1-2026-09-06.json',
    'synthetic-reference-inputs.json'])
def test_modified_bytes_cannot_be_published_as_stock_results(complete_capture_copy,name):
    mod,out=complete_capture_copy
    p=out/name;p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(ValueError):mod['verify'](out)


def test_rehashed_stock_card_does_not_replace_recomputation(complete_capture_copy):
    mod,out=complete_capture_copy
    result=mod['read'](out/'stock-reading.json')
    result['projection']['surfaced_stocks'][0]['company_name']='fabricated recommendation'
    result['projection_hash']=canonical_hash(result['projection'])
    (out/'stock-reading.json').write_bytes(mod['data'](result))
    report=mod['read'](out/'capture.json')
    report['files']= {k:v for k,v in mod['inventory'](out).items() if k!='capture.json'}
    report['capture_hash']=canonical_hash({k:v for k,v in report.items() if k!='capture_hash'})
    (out/'capture.json').write_bytes(mod['data'](report))
    with pytest.raises(ValueError,match='reconstruct'):mod['verify'](out)


def test_first_transport_failure_preserves_attempt_not_an_empty_stock_success(tmp_path):
    mod,_,out,_,pauses,run=setup(tmp_path);attempts=[]
    def fail(*args):attempts.append(args);raise RuntimeError('secret-like text must not be kept')
    r=run(transport=fail)
    assert r['status']==mod['FAILED'] and len(attempts)==1 and pauses==[]
    assert r['failure_category']=='REQUEST_FAILED'
    assert (out/'index.html').exists() and not (out/'stock-reading.json').exists()
    assert 'secret-like text' not in (out/'capture.json').read_text()
    assert '请求失败' in (out/'index.html').read_text()
    assert mod['verify'](out)['status']=='RETAINED_INCOMPLETE_ATTEMPT_NOT_STOCK_SELECTION'


@pytest.mark.parametrize('value',[{'Authorization':'secret'}, {'a':{'token':'secret'}}, {'message':'dummy-secret'}])
def test_unsafe_decoded_response_is_not_retained(tmp_path,value):
    mod,_,out,_,_,run=setup(tmp_path)
    r=run(transport=lambda *a:value,credential='dummy-secret')
    assert r['status']==mod['FAILED'] and len(r['requests'])==1
    assert r['requests'][0]['response_file'] is None
    assert not (out/'responses').exists()
    assert r['reason_code']=='UNSAFE_RESPONSE_NOT_RETAINED'


def test_plan_timeout_before_first_request(tmp_path):
    mod,_,out,calls,pauses,run=setup(tmp_path)
    r=run(now=lambda:NOW+timedelta(minutes=31))
    assert r['status']==mod['FAILED'] and not calls and not r['requests']
    assert '时间' in (out/'index.html').read_text()
    assert not (out/'stock-reading.json').exists()


def test_timeout_after_response_retains_failed_attempt_and_stops(tmp_path):
    mod,_,out,calls,_,run=setup(tmp_path)
    times=iter([NOW,NOW+timedelta(minutes=31),NOW+timedelta(minutes=32)])
    r=run(now=lambda:next(times))
    assert r['status']==mod['FAILED'] and len(calls)==1
    assert r['requests'][0]['response_file'] is None


def test_output_is_not_overwritten(tmp_path):
    _,_,out,_,_,run=setup(tmp_path);out.mkdir();(out/'sentinel').write_text('keep')
    with pytest.raises(ValueError):run()
    assert (out/'sentinel').read_text()=='keep'


def stock_environment():
    env=environment();env['TRIAL_PURPOSE']='stock-reading';env['STOCK_MARKET_RUN_ID']='101'
    return env


def test_manual_input_is_exact_state_run_not_a_new_source_or_bootstrap():
    m=code();r=m['intent'](stock_environment(),NOW.isoformat())
    assert r['market_run_id']=='101' and r['workflow']['GITHUB_REF']=='refs/heads/main'


@pytest.mark.parametrize('key,value',[('STOCK_MARKET_RUN_ID','latest'),('STOCK_MARKET_RUN_ID','101;echo'),
    ('STOCK_MARKET_RUN_ID','999'),('GITHUB_REF','refs/heads/test'),('GITHUB_RUN_ATTEMPT','2'),
    ('GITHUB_EVENT_NAME','push'),('TRIAL_PURPOSE','stock-dump')])
def test_unqualified_manual_inputs_rejected(key,value):
    env=stock_environment();env[key]=value
    with pytest.raises(ValueError):code()['intent'](env,NOW.isoformat())


def test_existing_remote_market_binder_is_reused(tmp_path):
    m=code();req=m['intent'](stock_environment(),NOW.isoformat());run,listing=remote('market')
    m['write'](tmp_path/'market-run.json',run);m['write'](tmp_path/'market-artifacts.json',listing)
    bound=m['binding'](tmp_path,req)
    assert bound['run_id']=='101' and bound['artifact_id']=='200'
    listing['artifacts'][0]['expired']=True
    (tmp_path/'market-artifacts.json').write_bytes(m['data'](listing))
    with pytest.raises(ValueError):m['binding'](tmp_path,req)


def test_normal_name_containing_stock_is_not_st_status_and_has_history():
    from test_stock_radar_reading import observe
    result,_,calls=observe()
    assert result['projection']['surfaced_stocks']
    assert any(p=='/api/a-share/prices/historical' for p,_ in calls)


def test_result_is_invariant_to_caller_decimal_context():
    from decimal import localcontext
    from decision_kernel.runtime import stock_radar_reading as stock
    state,_,_,plan,response,_=prepared()
    refs=synthetic_references(state,[r['thscode'] for r in plan['issuers']])
    normal=stock.observe_stock_reading(plan,state,request_json=response,observed_at=NOW,reference_inputs=refs)
    with localcontext() as context:
        context.prec=12
        assert stock.observe_stock_reading(plan,state,request_json=response,observed_at=NOW,reference_inputs=refs)==normal
