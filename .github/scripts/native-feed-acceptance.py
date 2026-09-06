"""One explicit native-feed acceptance trial using existing capture and replay.

No RSS fetch, baseline reset, production receipt store, or automatic next batch.
Only the fixed sibling collector supplies HTTP; all inputs are data, never code.
"""
from __future__ import annotations

import argparse
import os
import time
import runpy
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import radar_feed_consumer as consumer
from decision_kernel.runtime import radar_feed_intake as feed
from decision_kernel.runtime import theme_plan_execution as execution
from decision_kernel.runtime import theme_radar_probe as probe
from decision_kernel.runtime.sector_radar_persistence import load_sector_radar_persistent_bundle

ROOT = Path('native-feed-acceptance')
KINDS = {'source': ('economic-release-discovery', 'radar-feed-intake-{run}-1'),
         'market': ('sector-radar-shadow', 'sector-radar-state-bundle')}
HISTORY = 'EXPLICIT_EMPTY_HISTORY_FOR_ISOLATED_ACCEPTANCE_NOT_DAILY_CONSUMPTION'
VERSION = 'manual-native-feed-acceptance-v0'


def sibling(name):
    return runpy.run_path(str(Path(__file__).with_name(name)), run_name='native_acceptance_helper')


def write(path, value):
    with path.open('xb') as stream:
        stream.write(feed.data(value))


def read(path):
    return consumer._json(path)


def intent(env, at):
    helper = sibling('prepare-native-rss-successor.py')
    workflow = sibling('capture-theme-probe.py')['workflow_identity'](env)
    if env.get('GITHUB_EVENT_NAME') != 'workflow_dispatch' or env.get('TRIAL_PURPOSE') != 'native-feed-acceptance':
        raise ValueError('native acceptance is manual only')
    source = helper['number'](env.get('NATIVE_FEED_RUN_ID', ''))
    market = env.get('NATIVE_MARKET_RUN_ID', '')
    if market:
        helper['number'](market)
    batch = env.get('NATIVE_BATCH_SIZE', '')
    if batch not in {str(i) for i in range(1, 33)} or env.get('NATIVE_EXECUTE') not in {'true', 'false'}:
        raise ValueError('explicit bounded batch and execution switch required')
    if workflow['GITHUB_RUN_ID'] in {source, market}:
        raise ValueError('an invocation cannot restore itself')
    return {'version': VERSION, 'workflow': workflow, 'source_run_id': source,
            'market_run_id': market, 'batch_size': int(batch), 'execute_market': env['NATIVE_EXECUTE'] == 'true',
            'history_scope': HISTORY, 'prepared_at': probe._clock(at).isoformat(), **probe.AUTHORITY}


def metadata(request, kind, run, listing):
    """Bind exact successful main artifacts; use the existing source binder."""
    helper = sibling('prepare-native-rss-successor.py')
    wanted = request[kind + '_run_id']
    helper['number'](wanted)
    at = probe._clock(request['prepared_at'])
    if not probe._clock(run['updated_at']) < at or not probe._clock(run['created_at']) < at:
        raise ValueError('input execution must finish before this invocation')
    if kind == 'source':
        bound = helper['bind_metadata']({'explicit_baseline': False, 'previous_run_id': wanted,
                'prepared_at': request['prepared_at'], 'pinned_previous': None,
                'preflight_hash': canonical_hash(request)}, run, listing)
        artifact_id = bound['artifact_id']
    else:
        name, artifact_name = KINDS[kind]
        if (type(run['id']) is not int or str(run['id']) != wanted or run['name'] != name
                or run['path'] != f'.github/workflows/{name}.yml' or run['head_branch'] != 'main'
                or run['repository']['full_name'] != 'auguspp/decision-kernel'
                or type(run['run_attempt']) is not int or run['run_attempt'] != 1
                or run['status'] != 'completed' or run['conclusion'] != 'success'
                or run['event'] not in {'push', 'workflow_dispatch'}):
            raise ValueError('market input run identity differs')
        helper['hash_value'](run['head_sha'], 40)
        if type(listing['total_count']) is not int or listing['total_count'] != len(listing['artifacts']):
            raise ValueError('complete artifact listing required')
        matches = [a for a in listing['artifacts'] if a['name'] == artifact_name]
        if len(matches) != 1:
            raise ValueError('one exact market state artifact required')
        a = matches[0]; relation = a['workflow_run']
        if (type(a['id']) is not int or a['expired'] is not False
                or type(a['size_in_bytes']) is not int or not 0 < a['size_in_bytes'] <= 32*1024*1024
                or relation['id'] != run['id'] or relation['head_sha'] != run['head_sha']
                or relation['head_branch'] != 'main' or relation['repository_id'] != run['repository']['id']
                or relation['head_repository_id'] != run['repository']['id']
                or probe._clock(a['expires_at']) <= at):
            raise ValueError('market artifact identity or retention differs')
        helper['number'](str(a['id']))
        if not isinstance(a['digest'], str) or not a['digest'].startswith('sha256:'):
            raise ValueError('server artifact digest required')
        helper['hash_value'](a['digest'][7:]); artifact_id = str(a['id'])
    artifact = next(a for a in listing['artifacts'] if str(a['id']) == artifact_id)
    return {'kind': kind, 'run_id': wanted, 'commit': run['head_sha'], 'artifact_id': artifact_id,
            'artifact_digest': artifact['digest'], 'request_hash': canonical_hash(request)}


def source_status(source, *, as_of):
    captured, registry, _ = consumer._load_feed(source, as_of)
    delta = read(source / 'delta.json')
    wanted, _, gaps = feed._source_candidates(registry, delta)
    status = ('SOURCE_QUALIFICATION_BLOCKED' if gaps else 'BASELINE_NOT_FORWARDED'
              if delta['status'] == 'INITIAL_BASELINE_ONLY' else 'READY_FOR_ISOLATED_SCAN'
              if wanted else 'NO_POST_BASELINE_VERSIONS')
    return {'status': status, 'capture_hash': captured['capture_hash'], 'registry_hash': registry['registry_hash'],
            'pending_versions': len(wanted), 'gaps': gaps, 'needs_market': bool(wanted) and not gaps,
            'source_delivery_acknowledged': False, 'network_calls': 0, **probe.AUTHORITY}


def qualify(root, request):
    run, listing = read(root/'source-run.json'), read(root/'source-artifacts.json')
    bound = metadata(request, 'source', run, listing)
    if read(root/'source-binding.json') != bound:
        raise ValueError('source metadata binding differs')
    source = root/'source/capture'
    value = source_status(source, as_of=request['prepared_at'])
    receipt = read(source/'capture.json')
    expected = {k: request['workflow'][k] for k in sibling('prepare-native-rss-successor.py')['CONTEXT_KEYS']}
    expected.update(GITHUB_WORKFLOW=KINDS['source'][0], GITHUB_RUN_ID=bound['run_id'], GITHUB_SHA=bound['commit'])
    if receipt['provenance'] != 'PUBLIC_HTTP_CAPTURE' or receipt['workflow'] != expected:
        raise ValueError('source bytes do not identify the selected public execution')
    return value


def market_state(root, request):
    bound = metadata(request, 'market', read(root/'market-run.json'), read(root/'market-artifacts.json'))
    if read(root/'market-binding.json') != bound:
        raise ValueError('market metadata binding differs')
    directory = root/'market'
    if set(consumer._inventory(directory)) != {'manifest.json', 'market-state.json', 'candidate-events.json'}:
        raise ValueError('exact market bundle inventory required')
    bundle = load_sector_radar_persistent_bundle(directory, expected_repository='auguspp/decision-kernel',
                           expected_workflow='.github/workflows/sector-radar-shadow.yml')
    m = bundle.manifest
    if (str(m.source_run_id) != bound['run_id'] or m.source_commit_sha != bound['commit']
            or m.source_run_attempt != 1 or m.updated_at > probe._clock(request['prepared_at'])):
        raise ValueError('saved state belongs to another remote run or future time')
    return bundle.market_state


def trial(source, state, output, *, batch_size, execute_market, workflow, transport,
          public_http=False, credential='', now=lambda: datetime.now(timezone.utc), pause=time.sleep):
    """Single bounded trial; empty receipt history is explicit, never a reset."""
    if type(execute_market) is not bool or type(batch_size) is not int or not 1 <= batch_size <= 32:
        raise ValueError('invalid explicit acceptance limits')
    probe._safe_path(output)
    if output.exists() or output.resolve().is_relative_to(source.resolve()):
        raise ValueError('new isolated trial directory required')
    started = now().isoformat()
    qualification = source_status(source, as_of=started)
    if not qualification['needs_market']:
        raise ValueError('source qualification must precede market requests')
    captured = read(source/'capture.json')
    expected_provenance = 'PUBLIC_HTTP_CAPTURE' if public_http else probe.SYNTHETIC
    if captured['provenance'] != expected_provenance:
        raise ValueError('source and transport provenance differ')
    if public_http:
        execution._workflow(workflow)
        if not credential:
            raise ValueError('market credential is not configured')
    probe._window(state, probe._clock(started))
    output.mkdir(parents=True)
    report = {'version': VERSION, 'status': 'INCOMPLETE_ACCEPTANCE', 'started_at': started,
              'finished_at': None, 'workflow': workflow, 'history_scope': HISTORY, 'batch_size': batch_size,
              'execute_market': execute_market, 'public_http': public_http, 'catalogs': [],
              'scan_as_of': None, 'failure_type': None, 'source_qualification': qualification,
              'requests_attempted': 0, 'maximum_requests': 15, 'source_delivery_acknowledged': False,
              'remote_publication_verified': False, **probe.AUTHORITY}
    collector = sibling('capture-theme-probe.py')
    context = {'industries': []}
    last = probe._clock(started)
    try:
        for index, (key, params) in enumerate(collector['CATALOGS'], 1):
            if index > 1:
                pause(20)
            at = now().isoformat()
            probe._window(state, probe._clock(at))
            if probe._clock(at) < last:
                raise ValueError('catalog request clock reversed')
            entry = {'id': key, 'path': probe.CATALOG, 'params': params, 'requested_at': at,
                     'received_at': None, 'response_file': None, 'http_status': None, 'error_type': None}
            report['catalogs'].append(entry); report['requests_attempted'] += 1
            try:
                raw = transport(probe.CATALOG, params)
                entry['http_status'] = 200
                entry['received_at'] = now().isoformat()
                end = probe._clock(entry['received_at']); probe._window(state, end)
                if end < probe._clock(at) or not isinstance(raw, bytes) or len(raw) > probe.MAX_INPUT_BYTES:
                    raise ValueError('invalid catalog body or receipt clock')
                body = execution._decode(raw, credential=credential)
                name = f'catalog-{index}.json'
                (output/name).write_bytes(raw)
                entry.update(response_file=name, http_status=200)
                context[key] = {k: entry[k] for k in ('path', 'params', 'requested_at', 'received_at')}
                context[key]['response'] = body
                last = end
            except (ValueError, OSError, RuntimeError) as exc:
                entry['received_at'] = entry['received_at'] or now().isoformat()
                entry['error_type'] = type(exc).__name__
                if type(getattr(exc, 'http_status', None)) is int:
                    entry['http_status'] = exc.http_status
                raise
        write(output/'context.json', context)
        report['scan_as_of'] = now().isoformat()
        with tempfile.TemporaryDirectory(prefix='native-empty-history-') as temp:
            result = consumer.scan(source, state, context, Path(temp), output/'scan',
                    as_of=report['scan_as_of'], generated_at=report['scan_as_of'], batch_size=batch_size)
        if result['status'] != 'SOURCE_SCAN_COMPLETED':
            report['status'] = 'SOURCE_SCAN_BLOCKED'
        else:
            checked = consumer.verify_scan(output/'scan')
            plan = checked['result']['acquisition_plan']
            report['status'] = 'SOURCE_SCAN_COMPLETED_PLAN_NOT_EXECUTED' if plan else 'SOURCE_SCAN_COMPLETED_NO_LITERAL_MATCH'
            if plan and execute_market:
                attempt = execution.capture_plan(output/'scan', output/'execution', transport=transport,
                    context=workflow, public_http=public_http, credential=credential, now=now, pause=pause)
                report['requests_attempted'] += len(attempt['requests'])
                report['status'] = 'MARKET_STAGE_COMPLETED' if attempt['status'] == execution.COMPLETE else 'MARKET_STAGE_FAILED'
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        report['failure_type'] = type(exc).__name__
    report['finished_at'] = now().isoformat()
    report['files'] = consumer._inventory(output, maximum_files=128)
    report = feed._sealed(report, 'acceptance_hash')
    write(output/'acceptance.json', report)
    return report


def verify_trial(source, state, output):
    report = read(output/'acceptance.json')
    if (report['version'] != VERSION or report['history_scope'] != HISTORY
            or report['acceptance_hash'] != canonical_hash({k:v for k,v in report.items() if k != 'acceptance_hash'})
            or report['files'] != {k:v for k,v in consumer._inventory(output, maximum_files=128).items() if k != 'acceptance.json'}
            or any(report.get(k) != v for k,v in probe.AUTHORITY.items())
            or report['source_delivery_acknowledged'] is not False or report['remote_publication_verified'] is not False):
        raise ValueError('acceptance identity or file bytes differ')
    if source_status(source, as_of=report['started_at']) != report['source_qualification']:
        raise ValueError('source qualification differs from original input')
    if (type(report['execute_market']) is not bool or type(report['public_http']) is not bool
            or probe._clock(report['finished_at']) < probe._clock(report['started_at'])):
        raise ValueError('invalid trial mode or finish clock')
    expected_provenance = 'PUBLIC_HTTP_CAPTURE' if report['public_http'] else probe.SYNTHETIC
    if read(source/'capture.json')['provenance'] != expected_provenance:
        raise ValueError('source and acceptance provenance differ')
    if report['public_http']:
        execution._workflow(report['workflow'])
    if not {p.name for p in output.iterdir()} <= {'acceptance.json','context.json','catalog-1.json','catalog-2.json','scan','execution'}:
        raise ValueError('unexpected acceptance files')
    # Replay exactly the two retained catalog responses; no HTTP is reachable.
    raw = [probe._read(output/e['response_file']) for e in report['catalogs'] if e['response_file']]
    if len(report['catalogs']) > 2:
        raise ValueError('catalog request budget exceeded')
    if len(raw) != 2 or report['status'] == 'INCOMPLETE_ACCEPTANCE':
        return {'status': 'RETAINED_INCOMPLETE_ATTEMPT_NOT_SUCCESS', 'network_calls': 0}
    context = {'industries': []}
    collector = sibling('capture-theme-probe.py')
    last = probe._clock(report['started_at'])
    for e, (key, params), body in zip(report['catalogs'], collector['CATALOGS'], raw):
        if e['id'] != key or e['params'] != params or e['path'] != probe.CATALOG or e['http_status'] != 200 or e['error_type']:
            raise ValueError('catalog request identity differs')
        if e['response_file'] != f'catalog-{len(context)}.json':
            raise ValueError('catalog response slot differs')
        at, received = probe._clock(e['requested_at']), probe._clock(e['received_at'])
        if not last <= at <= received <= probe._clock(report['scan_as_of']):
            raise ValueError('catalog clocks differ')
        context[key] = {k:e[k] for k in ('path', 'params', 'requested_at', 'received_at')}
        context[key]['response'] = execution._decode(body); last = received
    if context != read(output/'context.json'):
        raise ValueError('catalog context does not rebuild from original bytes')
    if not probe._clock(report['started_at']) <= probe._clock(report['scan_as_of']) <= probe._clock(report['finished_at']):
        raise ValueError('scan clock outside trial')
    with tempfile.TemporaryDirectory(prefix='native-acceptance-replay-') as temp:
        root = Path(temp); (root/'receipts').mkdir()
        handoff = consumer.scan(source, state, context, root/'receipts', root/'scan',
                as_of=report['scan_as_of'], generated_at=report['scan_as_of'], batch_size=report['batch_size'])
        if consumer._inventory(root/'scan') != consumer._inventory(output/'scan'):
            raise ValueError('source selection and scan do not rebuild')
    expected = 'SOURCE_SCAN_BLOCKED'
    detail_count = 0
    if handoff['status'] == 'SOURCE_SCAN_COMPLETED':
        proof = consumer.verify_scan(output/'scan')
        plan = proof['result']['acquisition_plan']
        expected = 'SOURCE_SCAN_COMPLETED_PLAN_NOT_EXECUTED' if plan else 'SOURCE_SCAN_COMPLETED_NO_LITERAL_MATCH'
        if plan and report['execute_market']:
            checked = execution.verify_execution(output/'execution', as_of=report['finished_at'])
            attempt = read(output/'execution/execution.json')
            if checked['scan_receipt_hash'] != proof['receipt']['receipt_hash'] or attempt['workflow'] != report['workflow']:
                raise ValueError('execution belongs to another acceptance scan')
            detail_count = len(attempt['requests'])
            expected = 'MARKET_STAGE_COMPLETED' if checked['market_stage_succeeded'] else 'MARKET_STAGE_FAILED'
        elif (output/'execution').exists():
            raise ValueError('execution was not requested or no plan existed')
    if expected != report['status'] or report['requests_attempted'] != 2 + detail_count or report['requests_attempted'] > 15:
        raise ValueError('acceptance status or request budget does not reconstruct')
    return {'status': 'ORIGINAL_SOURCE_SCAN_AND_OPTIONAL_EXECUTION_REBUILT', 'acceptance_status': expected,
            'acceptance_hash': report['acceptance_hash'], 'network_calls': 0, **probe.AUTHORITY}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['init', 'metadata', 'qualify', 'run', 'verify'])
    parser.add_argument('--kind', choices=KINDS)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv); root = args.root
    outputs = {}
    try:
        probe._safe_path(root)
        if args.mode == 'init':
            value = intent(os.environ, datetime.now(timezone.utc).isoformat())
            root.mkdir(parents=True, exist_ok=False); write(root/'request.json', value)
            outputs = {'source_run_id': value['source_run_id'], 'market_run_id': value['market_run_id']}
        else:
            request = read(root/'request.json')
            if request['workflow'] != sibling('capture-theme-probe.py')['workflow_identity'](os.environ):
                raise ValueError('acceptance run identity changed')
            if args.mode == 'metadata':
                value = metadata(request, args.kind, read(root/f'{args.kind}-run.json'), read(root/f'{args.kind}-artifacts.json'))
                write(root/f'{args.kind}-binding.json', value); outputs = {'artifact_id': value['artifact_id']}
            else:
                qualification = qualify(root, request)
                if args.mode == 'qualify':
                    write(root/'source-qualification.json', qualification)
                    outputs = {'needs_market': str(qualification['needs_market']).lower()}
                    value = qualification
                elif args.mode == 'run':
                    if not qualification['needs_market']:
                        raise ValueError('no qualified sources require a market scan')
                    state = market_state(root, request)
                    collector = sibling('capture-theme-probe.py')
                    key = os.environ.get('HITHINK_FINANCE_API_KEY', '')
                    value = trial(root/'source/capture', state, root/'trial', batch_size=request['batch_size'],
                        execute_market=request['execute_market'], workflow=request['workflow'], public_http=True,
                        credential=key, transport=lambda p,q:collector['request_raw'](p,q,api_key=key), pause=time.sleep)
                else:
                    if os.environ.get('HITHINK_FINANCE_API_KEY'):
                        raise ValueError('offline verification cannot receive market credential')
                    if qualification != read(root/'source-qualification.json'):
                        raise ValueError('source precheck does not reconstruct')
                    if qualification['needs_market']:
                        saved = read(root/'trial/acceptance.json')
                        if any(saved[k] != request[k] for k in ('workflow', 'history_scope', 'batch_size', 'execute_market')):
                            raise ValueError('trial differs from explicit manual intent')
                        value = verify_trial(root/'source/capture', market_state(root, request), root/'trial')
                    else:
                        if (root/'trial').exists():
                            raise ValueError('unqualified source cannot acquire market inputs')
                        value = qualification
                    write(root/'verification.json', value)
        if outputs:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
                for key, val in outputs.items(): stream.write(f'{key}={val}\n')
        print(feed.data(value).decode())
        status = value.get('acceptance_status', value.get('status'))
        return 2 if status in {'SOURCE_QUALIFICATION_BLOCKED', 'INCOMPLETE_ACCEPTANCE', 'SOURCE_SCAN_BLOCKED',
                              'MARKET_STAGE_FAILED', 'RETAINED_INCOMPLETE_ATTEMPT_NOT_SUCCESS'} else 0
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        print(feed.data({'status': 'NATIVE_ACCEPTANCE_UNAVAILABLE', 'error_type': type(exc).__name__}).decode())
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
