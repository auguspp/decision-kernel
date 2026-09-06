from __future__ import annotations

import copy
import json
import runpy
import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import radar_feed_consumer as consumer
from decision_kernel.runtime import radar_feed_intake as feed
from decision_kernel.runtime import theme_plan_execution as execute
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError
from test_radar_feed_consumer import setup, register, contents, AS_OF
from test_radar_feed_intake import item
from test_theme_radar_probe import fixture, THEMES, choices
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(feed.feedparser.http,'get',lambda *a,**k:pytest.fail('no RSS refetch'))


def prepared(tmp_path):
    state,source,receipts,context=setup(tmp_path,[item('We deny '+ ' and '.join(t['name'] for t in THEMES))])
    context['industries']=choices(state)
    consumer.scan(source,state,context,receipts,tmp_path/'scan',as_of=AS_OF.isoformat(),generated_at=AS_OF.isoformat(),batch_size=32)
    _,inputs=fixture()
    lookup={(r['path'],canonical_json(r['params'])):r['response'] for r in inputs['captures'].values()}
    calls,pauses=[],[]; output=tmp_path/'execution'
    clock=iter(AS_OF+timedelta(seconds=30*i) for i in range(100))
    def transport(path,params):
        assert (output/'plan.json').is_file()
        assert (output/'source-scan/scan-receipt.json').is_file()
        calls.append((path,params))
        return (json.dumps(lookup[(path,canonical_json(params))],ensure_ascii=False)+'\n').encode()
    def run(**kwargs):
        return execute.capture_plan(tmp_path/'scan',output,transport=kwargs.pop('transport',transport),
                    now=kwargs.pop('now',lambda:next(clock)),pause=pauses.append,**kwargs)
    return (state,source,receipts,context),output,calls,pauses,run


def test_exact_plan_is_executed_with_no_catalog_refetch_and_rebuilt(tmp_path):
    values,output,calls,pauses,run=prepared(tmp_path)
    before=contents(tmp_path/'scan'), contents(values[1])
    result=run()
    assert result['status']==execute.COMPLETE, result['failure']
    assert len(calls)==len(result['requests'])==7 and pauses==[20]*7
    assert result['catalog_requests_executed']==0
    assert all(p!=consumer.probe.CATALOG for p,_ in calls)
    checked=execute.verify_execution(output)
    assert checked['status']=='EXACT_SOURCE_PLAN_AND_MARKET_REBUILT'
    assert checked['market_stage_succeeded'] is True
    assert checked['source_delivery_acknowledged'] is False and checked['publication_verified'] is False
    assert checked['network_calls']==0 and checked['events_created']==0
    assert before==(contents(tmp_path/'scan'),contents(values[1]))
    proof=consumer.verify_scan(tmp_path/'scan')
    assert result['scan_receipt_hash']==proof['receipt']['receipt_hash']
    assert result['plan_hash']==canonical_hash(proof['result']['acquisition_plan'])


def test_successful_raw_execution_closes_only_its_exact_market_stage(tmp_path):
    values,output,_,_,run=prepared(tmp_path); assert run()['status']==execute.COMPLETE
    register(tmp_path)
    executions=tmp_path/'executions'; executions.mkdir()
    shutil.copytree(output,executions/'one'); shutil.copytree(output,executions/'copy')
    state,source,receipts,context=values; at=AS_OF+timedelta(hours=1)
    result=consumer.scan(source,state,context,receipts,tmp_path/'next',as_of=at.isoformat(),generated_at=at.isoformat(),
                         batch_size=32,executions=executions)
    assert result['status']=='NO_PENDING_SOURCE_SCAN'
    assert result['unexecuted_prior_plans']==[] and len(result['market_execution_observations'])==1
    assert result['remote_publication_verified'] is False and result['source_delivery_acknowledged'] is False
    assert consumer.verify_scan(tmp_path/'receipts/scan')['receipt']['acquisition_status']=='PLAN_NOT_EXECUTED'


@pytest.mark.parametrize('status',[403,429,500])
def test_failed_attempt_remains_pending_and_is_not_retried(tmp_path,status):
    values,output,calls,pauses,run=prepared(tmp_path)
    attempts=[]
    def reject(path,params):
        attempts.append(path); raise DumpTrialError('HTTP_REJECTED',http_status=status)
    result=run(transport=reject)
    assert result['status']==execute.FAILED and len(attempts)==1 and pauses==[20]
    assert result['requests'][0]['http_status']==status and not (output/'index.html').exists()
    assert execute.verify_execution(output)['market_stage_succeeded'] is False
    register(tmp_path); executions=tmp_path/'executions'; executions.mkdir(); shutil.copytree(output,executions/'failed')
    state,source,receipts,context=values; at=AS_OF+timedelta(hours=1)
    next_result=consumer.scan(source,state,context,receipts,tmp_path/'next',as_of=at.isoformat(),generated_at=at.isoformat(),executions=executions)
    assert len(next_result['unexecuted_prior_plans'])==1
    assert next_result['market_execution_observations'][0]['status']=='INCOMPLETE_ATTEMPT_NOT_ACKNOWLEDGED'


def test_missing_latest_bar_never_gets_execution_confirmation(tmp_path):
    _,output,_,_,run=prepared(tmp_path)
    _,inputs=fixture()
    inputs['captures']['history:886001.TI']['response']['data']['item'].pop()
    lookup={(r['path'],canonical_json(r['params'])):r['response'] for r in inputs['captures'].values()}
    result=run(transport=lambda p,q:json.dumps(lookup[(p,canonical_json(q))]).encode())
    assert result['status']==execute.FAILED and not (output/'theme-probe.json').exists()
    assert execute.verify_execution(output)['market_stage_succeeded'] is False


@pytest.mark.parametrize('name',['plan.json','responses/01.json','source-scan/scan-receipt.json','theme-probe.json','index.html'])
def test_modified_bytes_cannot_clear_market_work(tmp_path,name):
    _,output,_,_,run=prepared(tmp_path); run()
    path=output/name; path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError): execute.verify_execution(output)


def test_rehashing_derived_market_page_does_not_bypass_replay(tmp_path):
    _,output,_,_,run=prepared(tmp_path); run()
    (output/'index.html').write_text('pretend success')
    report=json.loads((output/'execution.json').read_text())
    report['files']['index.html']=feed.digest((output/'index.html').read_bytes())
    report=feed._sealed({k:v for k,v in report.items() if k!='execution_hash'},'execution_hash')
    (output/'execution.json').write_bytes(feed.data(report))
    with pytest.raises(ValueError,match='does not rebuild'): execute.verify_execution(output)


def test_no_match_is_not_a_market_execution(tmp_path):
    values=setup(tmp_path,[item('No catalog label.')]);state,source,receipts,context=values
    consumer.scan(source,state,context,receipts,tmp_path/'scan',as_of=AS_OF.isoformat(),generated_at=AS_OF.isoformat())
    calls=[]
    with pytest.raises(ValueError,match='no market plan'):
        execute.capture_plan(tmp_path/'scan',tmp_path/'out',transport=lambda *x:calls.append(x),now=lambda:AS_OF)
    assert calls==[] and not (tmp_path/'out').exists()


def test_expired_plan_refused_before_transport(tmp_path):
    _,output,calls,_,run=prepared(tmp_path)
    with pytest.raises(ValueError): run(now=lambda:AS_OF+timedelta(days=3))
    assert calls==[] and not output.exists()


def test_synthetic_source_cannot_be_claimed_as_live(tmp_path):
    _,output,calls,_,run=prepared(tmp_path)
    context={'GITHUB_REPOSITORY':'auguspp/decision-kernel','GITHUB_REF':'refs/heads/main',
             'GITHUB_WORKFLOW':'hithink-stock-dump-trial','GITHUB_EVENT_NAME':'workflow_dispatch',
             'GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'a'*40,'GITHUB_RUN_ID':'123'}
    with pytest.raises(ValueError,match='synthetic scan'):
        run(public_http=True,credential='synthetic-secret',context=context)
    assert calls==[] and not output.exists()


def test_later_execution_cannot_suppress_earlier_work(tmp_path):
    _,output,_,_,run=prepared(tmp_path);run()
    with pytest.raises(ValueError,match='later than cutoff'): execute.verify_execution(output,as_of=AS_OF.isoformat())


def test_other_scan_of_same_theme_is_not_an_ack_for_this_plan(tmp_path):
    values,output,_,_,run=prepared(tmp_path);run()
    state,source,receipts,context=values
    consumer.scan(source,state,context,receipts,tmp_path/'other',as_of=AS_OF.isoformat(),
                  generated_at=(AS_OF+timedelta(seconds=1)).isoformat(),batch_size=32)
    shutil.copytree(tmp_path/'other',receipts/'other')
    executions=tmp_path/'executions';executions.mkdir();shutil.copytree(output,executions/'one')
    at=AS_OF+timedelta(hours=1)
    with pytest.raises(ValueError,match='another source-scan plan'):
        consumer.scan(source,state,context,receipts,tmp_path/'next',as_of=at.isoformat(),generated_at=at.isoformat(),executions=executions)


def test_loose_ack_or_missing_store_never_counts_as_success(tmp_path):
    values,_,_,_,run=prepared(tmp_path);run();register(tmp_path)
    state,source,receipts,context=values;at=AS_OF+timedelta(hours=1);executions=tmp_path/'executions'
    with pytest.raises(ValueError,match='directory missing'):
        consumer.scan(source,state,context,receipts,tmp_path/'next',as_of=at.isoformat(),generated_at=at.isoformat(),executions=executions)
    executions.mkdir();(executions/'ack.json').write_text('{"success":true}')
    with pytest.raises(ValueError,match='complete execution bundles'):
        consumer.scan(source,state,context,receipts,tmp_path/'next',as_of=at.isoformat(),generated_at=at.isoformat(),executions=executions)


def test_saved_result_can_rebuild_without_original_scan_directory(tmp_path):
    _,output,_,_,run=prepared(tmp_path);run()
    shutil.rmtree(tmp_path/'scan');shutil.rmtree(tmp_path/'feed')
    assert execute.verify_execution(output)['market_stage_succeeded'] is True


def test_failed_publication_keeps_attempt_not_a_success_page(tmp_path,monkeypatch):
    _,output,_,_,run=prepared(tmp_path);real=Path.write_bytes
    def fail(self,raw):
        if self.name=='theme-probe.json': raise OSError('synthetic interruption')
        return real(self,raw)
    monkeypatch.setattr(Path,'write_bytes',fail)
    assert run()['status']==execute.FAILED
    assert execute.verify_execution(output)['market_stage_succeeded'] is False


def test_secret_echo_does_not_enter_any_retained_file(tmp_path):
    _,output,_,_,run=prepared(tmp_path);secret='do-not-retain-this-credential'
    result=run(credential=secret,transport=lambda *x:json.dumps({'echo':secret}).encode())
    assert result['status']==execute.FAILED
    assert all(secret.encode() not in raw for raw in contents(output).values())


def test_cli_verifies_actual_saved_capture_without_credential_or_network(tmp_path,monkeypatch):
    _,output,_,_,run=prepared(tmp_path);run()
    script=runpy.run_path(str(Path('.github/scripts/capture-native-theme-plan.py').resolve()),run_name='test_native_execution')
    monkeypatch.delenv('HITHINK_FINANCE_API_KEY',raising=False)
    assert script['main'](['verify','--output',str(output)])==0
    monkeypatch.setenv('HITHINK_FINANCE_API_KEY','not-allowed')
    assert script['main'](['verify','--output',str(output)])==2
    text=Path('.github/scripts/capture-native-theme-plan.py').read_text()
    assert "existing['request_raw']" in text and 'capture-theme-probe.py' in text
    assert 'import requests' not in text and 'schedule' not in text


def test_synthetic_execution_cannot_close_a_public_source_plan(tmp_path,monkeypatch):
    _,output,calls,_,run=prepared(tmp_path)
    original=execute._identity
    def public_identity(*args,**kwargs):
        proof,plan,state,context=original(*args,**kwargs)
        proof=copy.deepcopy(proof);proof['receipt']['provenance']='PUBLIC_HTTP_CAPTURE'
        return proof,plan,state,context
    monkeypatch.setattr(execute,'_identity',public_identity)
    with pytest.raises(ValueError,match='synthetic execution'): run()
    assert calls==[] and not output.exists()
