"""One stock-first reading run. No producer, fallback prices, RSS, or state writes.

Transfer uses the existing native artifact binder and official workflow actions.
The existing joint reader enumerates source inputs. All saved responses here are
DECODED JSON, not claims to original wire bytes. No new transport or parser.
"""
from __future__ import annotations

import argparse
import json
import os
import runpy
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime import theme_radar_probe as probe
from decision_kernel.runtime import hithink_http
from decision_kernel.runtime.economic_release_inputs import load_release_inputs
from decision_kernel.runtime.economic_market_context import build_economic_market_context
from decision_kernel.runtime.sector_radar_audit import _check_safe_json
from decision_kernel.runtime.sector_radar_persistence import load_sector_radar_persistent_bundle

ROOT = Path('stock-reading-run')
VERSION = 'stock-reading-capture-replay-v0'
PUBLIC, SYNTHETIC = 'LIVE_HITHINK', 'SYNTHETIC_TEST_ONLY'
COMPLETE, FAILED = 'COMPLETE_STOCK_READING', 'INCOMPLETE_STOCK_READING'


def sibling(name):
    return runpy.run_path(str(Path(__file__).with_name(name)), run_name='stock_reading_helper')


def data(value):
    return (canonical_json(value)+'\n').encode('utf-8')


def read(path):
    from decision_kernel.runtime.economic_market_context import _read_json
    return _read_json(path)


def write(path, value):
    with path.open('xb') as f:
        f.write(data(value))


def inventory(root):
    helper = sibling('build-sector-radar-reading.py')
    files = {}
    total = 0
    probe._safe_path(root)
    if not root.is_dir():
        raise ValueError('complete stock reading directory required')
    for p in sorted(root.rglob('*')):
        probe._safe_path(p)
        if p.is_dir():
            continue
        raw = helper['_file'](p); total += len(raw)
        if len(files) >= helper['MAX_FILES'] or total > helper['MAX_BYTES']:
            raise ValueError('stock reading artifact exceeds inherited delivery budget')
        files[p.relative_to(root).as_posix()] = helper['_digest'](raw)
    return files


def load_inputs(root, at):
    helper = sibling('build-sector-radar-reading.py')
    from decision_kernel.runtime.sector_parent_hints import load_sector_parent_hints
    hints = load_sector_parent_hints(root/helper['HINTS'])
    bundle = load_sector_radar_persistent_bundle(root/'state',
        expected_repository='auguspp/decision-kernel',
        expected_workflow='.github/workflows/sector-radar-shadow.yml',
        expected_parent_hint_mapping_hash=hints.mapping_hash)
    inputs = load_release_inputs(root/helper['SEED'],root/helper['REVIEWS'],as_of=at)
    association = build_economic_market_context(market_state=bundle.market_state,event_ledger=bundle.event_ledger,
        observations=inputs.seed_observations, reviewed_releases=inputs.review_paths,
        links=read(root/helper['LINKS']), as_of=at, generated_at=at)
    plan = stock.prepare_stock_reading(root,bundle.market_state,bundle.event_ledger,association,observed_at=at)
    return bundle, association, plan


def page(report, provenance):
    result = stock.render_stock_reading(report)
    notice = ('合成验收样本：股票名称可能来自真实留存资料，成员和个股行情是测试数据，不可用于市场判断。'
              if provenance == SYNTHETIC else
              '本次 HiThink 数据读取；公司资料是已留存摘录，并未重新获取公司原文。')
    return result.replace('<h1>', '<p class="notice">'+notice+'</p><h1>',1).encode('utf-8')


def capture(source_root, state_dir, output, *, observed_at, transport, workflow,
            provenance=SYNTHETIC, credential='', now=lambda:datetime.now(timezone.utc), pause=time.sleep):
    """Testable one-shot coordinator. Public workflow binding is checked by main."""
    for p in (source_root,state_dir,output):
        probe._safe_path(p)
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (source_root,state_dir)):
        raise ValueError('stock output must be new and outside source directories')
    if provenance not in {PUBLIC,SYNTHETIC} or (provenance==PUBLIC and not credential):
        raise ValueError('explicit transport provenance and live credential required')
    helper = sibling('build-sector-radar-reading.py')
    files, directories = helper['_source_files'](source_root,state_dir,as_of=observed_at)
    output.mkdir(parents=True)
    for name in directories:
        (output/'inputs'/name).mkdir(parents=True,exist_ok=True)
    for name, raw in files.items():
        p=output/'inputs'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    report = {'version':VERSION,'status':FAILED,'observed_at':observed_at,'finished_at':None,
        'provenance':provenance,'workflow':workflow,'failure_type':None,'requests':[],
        'response_semantics':'DECODED_PROVIDER_JSON_NOT_ORIGINAL_HTTP_BYTES',
        'source_directories':directories,'plan_hash':None,'projection_hash':None,
        'remote_upload_verified':False,**stock.LIMITS}
    last=observed_at
    try:
        bundle, association, plan = load_inputs(output/'inputs',observed_at)
        write(output/'association.json',association);write(output/'plan.json',plan)
        report['plan_hash']=plan['plan_hash']
        def clock(value):
            nonlocal last
            probe._window(bundle.market_state,value)
            if not last <= value <= observed_at+timedelta(minutes=30):
                raise ValueError('request/receipt clock reversed or plan expired')
            last=value
        def request(path,params):
            nonlocal last
            if len(report['requests']) >= plan['maximum_request_count'] or len(report['requests']) >= stock.MAX_REQUESTS:
                raise ValueError('stock request budget reached; no partial success')
            if report['requests']:
                pause(20)
            clock(now())
            entry={'path':path,'params':dict(params),'requested_at':last,'received_at':None,
                   'response_file':None,'error_type':None,'http_status':None}
            report['requests'].append(entry)
            try:
                value=transport(path,params)
                entry['received_at']=now();clock(entry['received_at'])
                _check_safe_json(value,credential or None)
                raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
                if len(raw)>8*1024*1024:
                    raise ValueError('decoded stock response exceeds audit byte budget')
                name=f'responses/{len(report["requests"]):02d}.json'
                p=output/name;p.parent.mkdir(exist_ok=True);p.write_bytes(raw)
                entry.update(response_file=name,http_status=200)
                return value
            except (ValueError,RuntimeError,OSError,TypeError) as exc:
                entry['error_type']=type(exc).__name__
                status=getattr(exc,'code',getattr(exc,'http_status',None))
                if type(status) is int:entry['http_status']=status
                raise
        result=stock.observe_stock_reading(plan,bundle.market_state,request_json=request,
                                          observed_at=observed_at,cutoff_clock=lambda:last)
        report['projection_hash']=result['projection_hash']
        write(output/'stock-reading.json',result)
        (output/'index.html').write_bytes(page(result,provenance))
        if helper['_source_files'](source_root,state_dir,as_of=observed_at)!=(files,directories):
            raise ValueError('source inputs changed during stock reading')
        report['status']=COMPLETE
    except (ValueError,RuntimeError,OSError,KeyError,TypeError) as exc:
        report['failure_type']=type(exc).__name__
        report['projection_hash']=None
        for name in ('stock-reading.json','index.html'):(output/name).unlink(missing_ok=True)
    report['finished_at']=now()
    if report['finished_at']<last:
        report['status']=FAILED;report['failure_type']='ReversedFinishClock';report['projection_hash']=None
        for name in ('stock-reading.json','index.html'):(output/name).unlink(missing_ok=True)
    report['files']=inventory(output)
    report['capture_hash']=canonical_hash(report)
    write(output/'capture.json',report)
    return read(output/'capture.json')


def verify(output):
    report=read(output/'capture.json')
    if (report['version']!=VERSION or not stock._hash_ok(report,'capture_hash')
            or any(report[k]!=v for k,v in stock.LIMITS.items()) or report['remote_upload_verified'] is not False
            or report['provenance'] not in {PUBLIC,SYNTHETIC}
            or report['files']!={k:v for k,v in inventory(output).items() if k!='capture.json'}):
        raise ValueError('stock capture identity or retained bytes differ')
    at=probe._clock(report['observed_at']);finished=probe._clock(report['finished_at'])
    if finished<at:raise ValueError('invalid finish clock')
    bundle,association,plan=load_inputs(output/'inputs',at)
    if report['status']!=COMPLETE:
        if (output/'index.html').exists() or (output/'stock-reading.json').exists():
            raise ValueError('failed stock attempt cannot contain a success page')
        return {'status':'RETAINED_INCOMPLETE_ATTEMPT_NOT_STOCK_SELECTION','network_calls':0,
                'capture_hash':report['capture_hash'],**stock.LIMITS}
    if (plan!=read(output/'plan.json') or association!=read(output/'association.json')
            or report['plan_hash']!=plan['plan_hash'] or report['failure_type'] is not None):
        raise ValueError('stock plan does not reconstruct from original source/state inputs')
    position=0;last=at
    def request(path,params):
        nonlocal position,last
        if position>=len(report['requests']):raise ValueError('unrecorded request; no network fallback')
        entry=report['requests'][position];position+=1
        requested,received=probe._clock(entry['requested_at']),probe._clock(entry['received_at'])
        if (entry['path']!=path or entry['params']!=params or entry['error_type'] is not None
                or entry['http_status']!=200 or entry['response_file']!=f'responses/{position:02d}.json'
                or not last<=requested<=received<=finished or received>at+timedelta(minutes=30)):
            raise ValueError('stock request identity or actual clock differs')
        probe._window(bundle.market_state,requested);probe._window(bundle.market_state,received)
        value=read(output/entry['response_file']);_check_safe_json(value)
        last=received;return value
    result=stock.observe_stock_reading(plan,bundle.market_state,request_json=request,
                                      observed_at=at,cutoff_clock=lambda:last)
    if (position!=len(report['requests']) or position>plan['maximum_request_count']
            or position>stock.MAX_REQUESTS or report['projection_hash']!=result['projection_hash']
            or (output/'stock-reading.json').read_bytes()!=data(result)
            or (output/'index.html').read_bytes()!=page(result,report['provenance'])):
        raise ValueError('stock result/page does not reconstruct from exact original inputs')
    return {'status':'ORIGINAL_STOCK_INPUTS_AND_PAGE_REBUILT','capture_hash':report['capture_hash'],
            'projection_hash':result['projection_hash'],'stock_count':len(result['projection']['surfaced_stocks']),
            'provenance':report['provenance'],'requests_replayed':position,'network_calls':0,**stock.LIMITS}


def intent(env, at):
    wf=sibling('capture-theme-probe.py')['workflow_identity'](env)
    if env.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or env.get('TRIAL_PURPOSE')!='stock-reading':
        raise ValueError('stock reading requires explicit manual intent')
    run=sibling('prepare-native-rss-successor.py')['number'](env.get('STOCK_MARKET_RUN_ID',''))
    if run==wf['GITHUB_RUN_ID']:raise ValueError('cannot use this execution as its own input')
    return {'workflow':wf,'market_run_id':run,'prepared_at':at,'semantics':stock.SEMANTICS}


def binding(root, request):
    return sibling('native-feed-acceptance.py')['metadata'](request,'market',read(root/'market-run.json'),read(root/'market-artifacts.json'))


def bound_state(root, request):
    bound=binding(root,request)
    if bound!=read(root/'market-binding.json'):raise ValueError('market binding changed')
    helper=sibling('build-sector-radar-reading.py')
    if {p.name for p in (root/'market').iterdir()}!=helper['STATE_FILES']:raise ValueError('exact market package required')
    b=load_sector_radar_persistent_bundle(root/'market',expected_repository='auguspp/decision-kernel',
                                        expected_workflow='.github/workflows/sector-radar-shadow.yml')
    m=b.manifest
    if str(m.source_run_id)!=bound['run_id'] or m.source_commit_sha!=bound['commit'] or m.source_run_attempt!=1:
        raise ValueError('state does not identify selected successful remote run')
    return b


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['init','metadata','capture','verify'])
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args(argv);root=args.root
    try:
        probe._safe_path(root)
        if args.mode=='init':
            value=intent(os.environ,datetime.now(timezone.utc).isoformat())
            root.mkdir(exist_ok=False);write(root/'request.json',value)
            with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('market_run_id='+value['market_run_id']+'\n')
        else:
            request=read(root/'request.json')
            if request['workflow']!=sibling('capture-theme-probe.py')['workflow_identity'](os.environ):
                raise ValueError('workflow identity changed')
            if args.mode=='metadata':
                value=binding(root,request);write(root/'market-binding.json',value)
                with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('artifact_id='+value['artifact_id']+'\n')
            else:
                bound_state(root,request)
                if args.mode=='capture':
                    key=os.environ.get('HITHINK_FINANCE_API_KEY','')
                    value=capture(Path(os.environ['GITHUB_WORKSPACE']),root/'market',root/'reading',
                        observed_at=datetime.now(timezone.utc),workflow=request['workflow'],provenance=PUBLIC,credential=key,
                        transport=lambda p,q:hithink_http._request_hithink_json(api_key=key,path=p,params=q,timeout_seconds=15))
                else:
                    if os.environ.get('HITHINK_FINANCE_API_KEY'):raise ValueError('replay cannot receive market credentials')
                    value=verify(root/'reading');write(root/'verification.json',value)
        print(canonical_json(value))
        return 2 if value.get('status') in {FAILED,'RETAINED_INCOMPLETE_ATTEMPT_NOT_STOCK_SELECTION'} else 0
    except (ValueError,RuntimeError,OSError,KeyError,TypeError) as exc:
        print(canonical_json({'status':'STOCK_READING_UNAVAILABLE','error_type':type(exc).__name__}))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
