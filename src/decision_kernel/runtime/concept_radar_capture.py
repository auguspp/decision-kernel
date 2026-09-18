"""One explicit concept-source attempt and original-byte replay. No schedule."""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from . import concept_radar as radar
from .institutional_radar import decode, MAX_BYTES
from .institutional_radar_capture import _bytes, _digest, _write
from .hithink_dump_trial import _session, _check_response
from .hithink_http import HITHINK_API_KEY_ENV, HITHINK_BASE_URL
from .sector_radar_audit import _check_request, _check_safe_json, _clock
from .theme_radar_probe import _safe_path

VERSION = 'concept-source-original-capture-v1'
COMPLETE = 'CAPTURED_CONCEPT_OBSERVATION'
PARTIAL = 'CAPTURED_CONCEPT_OBSERVATION_WITH_DETAIL_GAPS'
FAILED = 'INCOMPLETE_CONCEPT_SOURCE_CAPTURE'
MAX_TOTAL = 32 * 1024 * 1024
FAILURE_HTML = ('<!doctype html><meta charset="utf-8"><h1>概念来源未完成</h1>'
    '<p>不是概念没有变化。安全的阶段和原因见 capture.json，已取得原件仍保留。'
    '没有自动重试、Stock 检查、Pre／Quick、Odds 或投资权限。</p>\n').encode('utf-8')


def workflow_identity(env, expected_code):
    keys = ('GITHUB_REPOSITORY', 'GITHUB_WORKFLOW', 'GITHUB_REF', 'GITHUB_EVENT_NAME',
            'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA')
    radar.require(isinstance(expected_code, str) and re.fullmatch('[0-9a-f]{40}', expected_code)
        and env.get('GITHUB_REPOSITORY') == 'auguspp/decision-kernel'
        and env.get('GITHUB_WORKFLOW') == 'radar-concept-source'
        and env.get('GITHUB_REF') == 'refs/heads/main'
        and env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
        and env.get('GITHUB_RUN_ATTEMPT') == '1'
        and re.fullmatch('[1-9][0-9]{0,19}', env.get('GITHUB_RUN_ID', ''))
        and env.get('GITHUB_SHA') == expected_code, 'WORKFLOW_IDENTITY_REJECTED')
    return {k: env[k] for k in keys}


def _implementation():
    root = Path(__file__).resolve().parents[1]
    names = ('identity.py', 'adapters/hithink.py', 'adapters/hithink_index.py',
        'runtime/concept_radar.py', 'runtime/concept_radar_capture.py',
        'runtime/theme_radar_probe.py', 'runtime/hithink_sector_breadth_http.py',
        'runtime/sector_radar.py', 'runtime/sector_breadth.py',
        'runtime/institutional_radar.py', 'runtime/institutional_radar_capture.py',
        'runtime/hithink_dump_trial.py', 'runtime/sector_radar_audit.py')
    return {n: _digest((root / n).read_bytes())['sha256'] for n in names}


def _inventory(root):
    _safe_path(root)
    files, total = {}, 0
    for p in sorted(root.iterdir()):
        _safe_path(p)
        radar.require(p.is_file(), 'FILE_SCOPE_REJECTED')
        if p.name == 'capture.json':
            continue
        radar.require(p.name in {'plan.json', 'observation.json', 'index.html'}
            or re.fullmatch(r'(request|response)-(?:[1-9]|1[0-5])\.json', p.name), 'FILE_SCOPE_REJECTED')
        radar.require(p.stat().st_size <= MAX_BYTES, 'FILE_SIZE_REJECTED')
        raw = p.read_bytes()
        total += len(raw)
        radar.require(total <= MAX_TOTAL and len(files) < 2 * radar.MAX_REQUESTS + 3, 'CAPTURE_BUDGET_REJECTED')
        files[p.name] = _digest(raw)
    return files


def request_raw(path, params, *, credential):
    _check_request(path, params)
    radar.require(path in {radar.HITHINK_CALENDAR_PATH, radar.probe.CATALOG,
        radar.probe.SNAPSHOT, radar.probe.HISTORY, radar.probe.MEMBERS}, 'TRANSPORT_ROUTE_REJECTED')
    with _session() as session:
        with session.get(HITHINK_BASE_URL + path, params=params,
                headers={'X-api-key': credential, 'Accept': 'application/json', 'Accept-Encoding': 'identity'},
                timeout=(10, 20), stream=True, allow_redirects=False) as response:
            length = _check_response(response)
            radar.require(length is None or length <= MAX_BYTES, 'BODY_SIZE_REJECTED')
            chunks, total = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                radar.require(total <= MAX_BYTES, 'BODY_SIZE_REJECTED')
                chunks.append(chunk)
            radar.require(length is None or length == total, 'BODY_LENGTH_DIFFERS')
    return b''.join(chunks)


def capture(output, *, market_session, workflow, expected_code, transport, now,
            pause=time.sleep, credential='', provenance='SYNTHETIC_TEST_ONLY'):
    workflow = workflow_identity(workflow, expected_code)
    radar.session_date(market_session)
    radar.require(provenance in {'LIVE_HITHINK', 'SYNTHETIC_TEST_ONLY'}
        and (provenance != 'LIVE_HITHINK' or bool(credential)), 'PROVENANCE_REJECTED')
    _safe_path(output)
    radar.require(not output.exists(), 'CREATE_ONLY_OUTPUT_REQUIRED')
    started = _clock(now())
    plan = {'version': VERSION, 'market_session': market_session, 'started_at': started,
            'workflow': workflow, 'provenance': provenance, 'policy': radar.POLICY, **radar.AUTHORITY}
    _check_safe_json(plan, credential or None)
    output.mkdir(parents=True)
    _write(output, 'plan.json', _bytes(plan))
    requests, stage, total = [], 'INPUT_WINDOW', 0

    def acquire(path, params):
        nonlocal stage, total
        radar.require(len(requests) < radar.MAX_REQUESTS, 'REQUEST_BUDGET_REACHED')
        if requests:
            pause(20)
        _check_request(path, params)
        requested = _clock(now())
        stage = 'REQUEST_CLOCK'
        previous = requests[-1]['received_at'] if requests else started
        radar.require(previous is not None and previous <= requested <= started + timedelta(minutes=30)
            and requested.astimezone(radar.SHANGHAI_TZ).date() == radar.session_date(market_session),
            'REQUEST_WINDOW_EXPIRED_OR_REVERSED')
        entry = {'path': path, 'params': dict(params), 'requested_at': requested,
                 'received_at': None, 'response_file': None, 'http_status': None}
        requests.append(entry)
        i = len(requests)
        _write(output, f'request-{i}.json', _bytes({k: entry[k] for k in ('path', 'params', 'requested_at')}))
        stage = 'TRANSPORT'
        raw = transport(path, dict(params))
        received = _clock(now())
        entry['received_at'] = received
        stage = 'BODY_SAFETY'
        decode(raw, credential or None)
        total += len(raw)
        radar.require(total <= MAX_TOTAL, 'CAPTURE_BUDGET_REJECTED')
        _write(output, f'response-{i}.json', raw)
        entry.update(response_file=f'response-{i}.json', http_status=200)
        stage = 'SOURCE_QUALIFICATION'
        return raw, requested, received

    status, reason, failed_type = FAILED, None, None
    try:
        report = radar.observe(acquire, market_session=market_session, started_at=started, provenance=provenance)
        stage = 'READING_RENDER'
        _write(output, 'observation.json', _bytes(report))
        _write(output, 'index.html', radar.render(report).encode('utf-8'))
        status = PARTIAL if report['projection']['coverage']['detail_gaps'] else COMPLETE
    except (ValueError, RuntimeError, TypeError, KeyError, OSError, OverflowError) as exc:
        reason = str(exc) if isinstance(exc, radar.ConceptSourceError) else 'SOURCE_PREPARATION_REJECTED'
        failed_type = type(exc).__name__
        for name in ('observation.json', 'index.html'):
            (output / name).unlink(missing_ok=True)
        _write(output, 'index.html', FAILURE_HTML)
    finished = _clock(now())
    radar.require(finished >= started and all(r['received_at'] is None or finished >= r['received_at'] for r in requests),
                  'FINISH_CLOCK_REJECTED')
    receipt = {'version': VERSION, 'workflow': workflow, 'provenance': provenance,
        'started_at': started, 'finished_at': finished, 'requests': requests,
        'status': status, 'reason_code': reason, 'failed_stage': stage if reason else None,
        'failure_type': failed_type, 'implementation': _implementation(),
        'files': _inventory(output), **radar.AUTHORITY}
    receipt['capture_hash'] = canonical_hash(receipt)
    _write(output, 'capture.json', _bytes(receipt))
    return json.loads(_bytes(receipt))


def verify(output):
    _safe_path(output)
    _safe_path(output / 'capture.json')
    radar.require((output / 'capture.json').stat().st_size <= MAX_BYTES, 'RECEIPT_SIZE_REJECTED')
    receipt = decode((output / 'capture.json').read_bytes())
    radar.require(receipt.get('version') == VERSION
        and receipt.get('capture_hash') == canonical_hash({k: v for k, v in receipt.items() if k != 'capture_hash'})
        and receipt['implementation'] == _implementation() and receipt['files'] == _inventory(output)
        and all(receipt.get(k) == v for k, v in radar.AUTHORITY.items()), 'CAPTURE_IDENTITY_REJECTED')
    wf = workflow_identity(receipt['workflow'], receipt['workflow']['GITHUB_SHA'])
    plan = decode((output / 'plan.json').read_bytes())
    radar.require(plan == {'version': VERSION, 'market_session': radar.session_date(plan['market_session']).isoformat(),
        'started_at': receipt['started_at'], 'workflow': wf, 'provenance': receipt['provenance'],
        'policy': radar.POLICY, **radar.AUTHORITY}, 'PLAN_IDENTITY_REJECTED')
    radar.require(receipt['provenance'] in {'LIVE_HITHINK', 'SYNTHETIC_TEST_ONLY'}
        and receipt['status'] in {COMPLETE, PARTIAL, FAILED}
        and isinstance(receipt['requests'], list) and len(receipt['requests']) <= radar.MAX_REQUESTS,
        'CAPTURE_SCOPE_REJECTED')
    start, finish = _clock(receipt['started_at']), _clock(receipt['finished_at'])
    radar.require(start <= finish, 'FINISH_CLOCK_REJECTED')
    names = {'plan.json', 'index.html'}
    last = start
    for i, entry in enumerate(receipt['requests'], 1):
        _check_request(entry['path'], entry['params'])
        name = f'request-{i}.json'
        names.add(name)
        radar.require((output / name).read_bytes() == _bytes({k: entry[k] for k in ('path', 'params', 'requested_at')}),
                      'REQUEST_IDENTITY_REJECTED')
        at = _clock(entry['requested_at'])
        radar.require(last <= at <= finish, 'REQUEST_CLOCK_REJECTED')
        last = at
        if entry['received_at'] is not None:
            last = _clock(entry['received_at'])
            radar.require(at <= last <= finish, 'RESPONSE_CLOCK_REJECTED')
        if entry['response_file'] is not None:
            radar.require(entry['response_file'] == f'response-{i}.json' and entry['http_status'] == 200
                and entry['received_at'] is not None, 'RESPONSE_IDENTITY_REJECTED')
            names.add(entry['response_file'])
            decode((output / entry['response_file']).read_bytes())
        else:
            radar.require(i == len(receipt['requests']) and receipt['status'] == FAILED,
                          'INCOMPLETE_RESPONSE_SCOPE_REJECTED')
    if receipt['status'] in {COMPLETE, PARTIAL}:
        names.add('observation.json')
    radar.require(set(receipt['files']) == names, 'FILE_SET_REJECTED')
    if receipt['status'] == FAILED:
        radar.require(receipt['reason_code'] and receipt['failed_stage']
            and (output / 'index.html').read_bytes() == FAILURE_HTML, 'FAILED_CAPTURE_REJECTED')
        return {'status': 'RETAINED_FAILED_CONCEPT_CAPTURE_REMOTE_CAUSE_NOT_REPROVEN',
                'capture_hash': receipt['capture_hash'], 'network_calls': 0}
    position = 0

    def replay(path, params):
        nonlocal position
        radar.require(position < len(receipt['requests']), 'UNRECORDED_REQUEST')
        entry = receipt['requests'][position]
        position += 1
        radar.require(entry['path'] == path and entry['params'] == params, 'REPLAY_REQUEST_DIFFERS')
        return (output / entry['response_file']).read_bytes(), entry['requested_at'], entry['received_at']

    rebuilt = radar.observe(replay, market_session=plan['market_session'], started_at=start,
                            provenance=receipt['provenance'])
    expected_status = PARTIAL if rebuilt['projection']['coverage']['detail_gaps'] else COMPLETE
    radar.require(position == len(receipt['requests']) and receipt['status'] == expected_status
        and receipt['reason_code'] is None and receipt['failed_stage'] is None and receipt['failure_type'] is None
        and (output / 'observation.json').read_bytes() == _bytes(rebuilt)
        and (output / 'index.html').read_bytes() == radar.render(rebuilt).encode('utf-8'), 'READING_REBUILD_DIFFERS')
    return {'status': 'ORIGINAL_CONCEPT_REQUESTS_BODIES_AND_READING_REBUILT',
            'capture_hash': receipt['capture_hash'], 'projection_hash': rebuilt['projection_hash'],
            'catalog_count': rebuilt['projection']['catalog_count'],
            'company_count': len(rebuilt['projection']['companies']), 'network_calls': 0}


def main(argv=None):
    p = argparse.ArgumentParser(description='One independent concept source; no automatic research.')
    p.add_argument('mode', choices=('capture', 'verify'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--market-session')
    p.add_argument('--expected-code')
    args = p.parse_args(argv)
    try:
        if args.mode == 'verify':
            radar.require(not os.environ.get(HITHINK_API_KEY_ENV), 'REPLAY_MUST_NOT_RECEIVE_CREDENTIAL')
            print(canonical_json(verify(args.output)))
            return 0
        wf = workflow_identity(os.environ, args.expected_code)
        key = os.environ.get(HITHINK_API_KEY_ENV, '')
        radar.require(bool(key), 'EXISTING_PROVIDER_CREDENTIAL_REQUIRED')
        receipt = capture(args.output, market_session=args.market_session, workflow=wf, expected_code=args.expected_code,
            transport=lambda path, params: request_raw(path, params, credential=key),
            now=lambda: datetime.now(timezone.utc), credential=key, provenance='LIVE_HITHINK')
        print(canonical_json({'status': receipt['status'], 'capture_hash': receipt['capture_hash']}))
        return 0 if receipt['status'] in {COMPLETE, PARTIAL} else 2
    except (ValueError, RuntimeError, TypeError, KeyError, OSError, OverflowError):
        print('Concept source unavailable; inspect the retained finite receipt where available.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
