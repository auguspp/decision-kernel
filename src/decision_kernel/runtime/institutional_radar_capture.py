"""Bounded manual capture and credential-free original-byte replay; no schedule."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from . import institutional_radar as radar
from .hithink_http import HITHINK_BASE_URL, HITHINK_CALENDAR_PATH, HITHINK_API_KEY_ENV
from .hithink_dump_trial import _session, _check_response
from .sector_radar_audit import _check_safe_json, _clock
from .theme_radar_probe import _safe_path

VERSION = 'institutional-radar-capture-v1'
MAX_TOTAL_BYTES = 32 * 1024 * 1024
COMPLETE, FAILED = 'CAPTURED_INSTITUTIONAL_OBSERVATION', 'INCOMPLETE_INSTITUTIONAL_OBSERVATION'


def _bytes(value):
    return (canonical_json(value) + '\n').encode('utf-8')


def _digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _write(root, name, raw):
    with (root / name).open('xb') as stream:
        stream.write(raw)


def _inventory(root):
    _safe_path(root)
    files, total = {}, 0
    for path in sorted(root.iterdir()):
        _safe_path(path)
        radar._require(path.is_file(), 'CAPTURE_FILE_SCOPE_REJECTED')
        if path.name == 'capture.json':
            continue
        radar._require(path.stat().st_size <= radar.MAX_BYTES, 'CAPTURE_FILE_SIZE_REJECTED')
        raw = path.read_bytes()
        total += len(raw)
        radar._require(len(files) < 12 and total <= MAX_TOTAL_BYTES, 'CAPTURE_SIZE_REJECTED')
        files[path.name] = _digest(raw)
    return files


def _implementation():
    base = Path(__file__).resolve().parents[1]
    paths = ('identity.py', 'adapters/hithink.py', 'runtime/institutional_radar.py',
             'runtime/institutional_radar_capture.py', 'runtime/hithink_dump_trial.py',
             'runtime/sector_radar_audit.py', 'runtime/theme_radar_probe.py')
    return {p: _digest((base / p).read_bytes())['sha256'] for p in paths}


def request_raw(path, params, *, credential):
    radar._require((path == HITHINK_CALENDAR_PATH and params == {})
                   or (path == radar.BOARD_PATH and set(params) == {'board_type', 'date'}
                       and params['board_type'] == 'org'
                       and radar.session_date(params['date']).isoformat() == params['date']),
                   'REQUEST_SCOPE_REJECTED')
    # Reuse the established no-netrc/no-proxy session and HTTP/encoding policy.
    # Fresh session, fixed host, no redirects, no retries, no third-party hosts.
    with _session() as session:
        with session.get(HITHINK_BASE_URL + path, params=params,
                         headers={'X-api-key': credential, 'Accept': 'application/json',
                                  'Accept-Encoding': 'identity'},
                         timeout=(10, 20), stream=True, allow_redirects=False) as response:
            length = _check_response(response)
            radar._require(length is None or length <= radar.MAX_BYTES, 'BODY_SIZE_REJECTED')
            chunks, count = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                count += len(chunk)
                radar._require(count <= radar.MAX_BYTES, 'BODY_SIZE_REJECTED')
                chunks.append(chunk)
            radar._require(length is None or count == length, 'BODY_LENGTH_DIFFERS')
    return b''.join(chunks)


def capture(output, *, market_session, workflow, transport, now, pause=time.sleep,
            credential='', provenance='SYNTHETIC_TEST_ONLY'):
    radar.session_date(market_session)
    radar._require(provenance in {'LIVE_HITHINK', 'SYNTHETIC_TEST_ONLY'}
                   and (provenance != 'LIVE_HITHINK' or bool(credential)), 'CAPTURE_PROVENANCE_REJECTED')
    _safe_path(output)
    radar._require(not output.exists(), 'CREATE_ONLY_OUTPUT_REQUIRED')
    started = _clock(now())
    plan = {'version': VERSION, 'market_session': market_session, 'started_at': started,
            'workflow': workflow, 'provenance': provenance,
            'maximum_requests': 2, 'retry_count': 0,
            'requests': [{'path': HITHINK_CALENDAR_PATH, 'params': {}},
                         {'path': radar.BOARD_PATH, 'params': {'board_type': 'org', 'date': market_session}}],
            **radar.AUTHORITY}
    _check_safe_json(plan, credential or None)
    output.mkdir(parents=True)
    _write(output, 'plan.json', _bytes(plan))
    records, bodies, stage = [], [], 'REQUEST'
    status, reason, http_status = FAILED, None, None
    try:
        for index, intended in enumerate(plan['requests']):
            if index:
                pause(20)
            requested = _clock(now())
            radar._require(started <= requested and (not records or _clock(records[-1]['received_at']) <= requested),
                           'REQUEST_CLOCK_DIFFERS')
            stage = 'CALENDAR_REQUEST' if index == 0 else 'BOARD_REQUEST'
            _write(output, f'request-{index + 1}.json', _bytes({**intended, 'requested_at': requested}))
            raw = transport(intended['path'], dict(intended['params']))
            received = _clock(now())
            radar._require(requested <= received and (received - started).total_seconds() <= 180,
                           'REQUEST_CLOCK_DIFFERS')
            stage = 'BODY_SAFETY'
            radar.decode(raw, credential or None)  # unsafe or malformed bodies are NOT archived
            _write(output, f'response-{index + 1}.json', raw)
            records.append({**intended, 'requested_at': requested, 'received_at': received, **_digest(raw)})
            bodies.append(raw)
            stage = 'BUSINESS_ENVELOPE'
            radar._data(raw)  # HTTP 200 business failure still stops the attempt here
        stage = 'NORMALIZATION'
        generated = _clock(now())
        report = radar.build(*bodies, requests=records, market_session=market_session,
                             generated_at=generated, provenance=provenance)
        page = radar.render(report).encode('utf-8')
        _write(output, 'observation.json', _bytes(report))
        _write(output, 'index.html', page)
        status = COMPLETE
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, radar.InstitutionalSourceError) else 'SOURCE_PREPARATION_REJECTED'
        candidate = getattr(exc, 'http_status', None)
        http_status = candidate if type(candidate) is int and 100 <= candidate <= 599 else None
        (output / 'observation.json').unlink(missing_ok=True)
        (output / 'index.html').unlink(missing_ok=True)
        # Constant safe text only. Partial responses remain evidence, not a quiet result.
        _write(output, 'index.html', ('<!doctype html><meta charset="utf-8"><h1>机构观察未完成</h1>'
            '<p>来源准备未完成，不是机构没有活动；没有自动重试、股票检查或 Research。</p>'
            '<p>安全的阶段和原因代码见 capture.json；已取得原件保留。</p>').encode('utf-8'))
    finished = _clock(now())
    radar._require(finished >= started and (not records or finished >= _clock(records[-1]['received_at'])),
                   'FINISH_CLOCK_DIFFERS')
    receipt = {'version': VERSION, 'status': status, 'reason_code': reason, 'failed_stage': stage if reason else None,
               'http_status': http_status, 'started_at': started, 'finished_at': finished,
               'requests': records, 'attempted_requests': len(list(output.glob('request-*.json'))),
               'provenance': provenance, 'workflow': workflow, 'implementation': _implementation(),
               'runtime': {'python': platform.python_version(), 'requests': version('requests')},
               'files': _inventory(output), **radar.AUTHORITY}
    receipt['capture_hash'] = canonical_hash(receipt)
    _write(output, 'capture.json', _bytes(receipt))
    return json.loads(_bytes(receipt))


def verify(output):
    _safe_path(output)
    _safe_path(output / 'capture.json')
    radar._require((output / 'capture.json').stat().st_size <= radar.MAX_BYTES, 'RECEIPT_SIZE_REJECTED')
    receipt = radar.decode((output / 'capture.json').read_bytes())
    radar._require(receipt.get('version') == VERSION
                   and receipt.get('capture_hash') == canonical_hash({k: v for k, v in receipt.items() if k != 'capture_hash'})
                   and all(receipt.get(k) == v for k, v in radar.AUTHORITY.items())
                   and receipt['implementation'] == _implementation()
                   and receipt['files'] == _inventory(output), 'CAPTURE_IDENTITY_DIFFERS')
    plan = radar.decode((output / 'plan.json').read_bytes())
    day = radar.session_date(plan['market_session']).isoformat()
    radar._require(plan['version'] == VERSION and plan['maximum_requests'] == 2 and plan['retry_count'] == 0
                   and plan['workflow'] == receipt['workflow'] and plan['provenance'] == receipt['provenance']
                   and all(plan.get(k) == v for k, v in radar.AUTHORITY.items())
                   and plan['requests'] == [{'path': HITHINK_CALENDAR_PATH, 'params': {}},
                       {'path': radar.BOARD_PATH, 'params': {'board_type': 'org', 'date': day}}], 'PLAN_IDENTITY_DIFFERS')
    radar._require(0 <= receipt['attempted_requests'] <= 2
                   and len(receipt['requests']) <= receipt['attempted_requests'], 'REQUEST_COUNT_DIFFERS')
    started, finished = _clock(receipt['started_at']), _clock(receipt['finished_at'])
    radar._require(_clock(plan['started_at']) == started <= finished, 'CAPTURE_CLOCK_DIFFERS')
    expected_names = {'plan.json', 'index.html'}
    expected_names.update(f'request-{i + 1}.json' for i in range(receipt['attempted_requests']))
    expected_names.update(f'response-{i + 1}.json' for i in range(len(receipt['requests'])))
    if receipt['status'] == COMPLETE:
        expected_names.add('observation.json')
    radar._require(set(receipt['files']) == expected_names, 'CAPTURE_FILE_SET_DIFFERS')
    previous = started
    for i in range(receipt['attempted_requests']):
        intent = radar.decode((output / f'request-{i + 1}.json').read_bytes())
        radar._require(set(intent) == {'path', 'params', 'requested_at'}
                       and {k: intent[k] for k in ('path', 'params')} == plan['requests'][i]
                       and previous <= _clock(intent['requested_at']) <= finished, 'REQUEST_INTENT_DIFFERS')
        previous = _clock(intent['requested_at'])
        if i < len(receipt['requests']):
            record = receipt['requests'][i]
            body = (output / f'response-{i + 1}.json').read_bytes()
            radar.decode(body)
            radar._require(set(record) == {'path', 'params', 'requested_at', 'received_at', 'sha256', 'bytes'}
                           and intent == {k: record[k] for k in intent}
                           and _digest(body) == {k: record[k] for k in ('sha256', 'bytes')}
                           and previous <= _clock(record['received_at']) <= finished
                           and (_clock(record['received_at']) - started).total_seconds() <= 180,
                           'RETAINED_REQUEST_DIFFERS')
            previous = _clock(record['received_at'])
    if receipt['status'] == FAILED:
        radar._require(not (output / 'observation.json').exists()
                       and isinstance(receipt['reason_code'], str)
                       and re.fullmatch('[A-Z_]{1,100}', receipt['reason_code']) is not None
                       and receipt['failed_stage'] in {'REQUEST', 'CALENDAR_REQUEST', 'BOARD_REQUEST',
                                                      'BODY_SAFETY', 'BUSINESS_ENVELOPE', 'NORMALIZATION'},
                       'FAILED_RESULT_DIFFERS')
        return {'status': 'RETAINED_FAILED_ATTEMPT_NOT_REMOTE_RETRY_OR_QUIET', 'network_calls': 0,
                'capture_hash': receipt['capture_hash'], **radar.AUTHORITY}
    radar._require(receipt['status'] == COMPLETE and receipt['attempted_requests'] == 2
                   and receipt['reason_code'] is None and receipt['failed_stage'] is None
                   and receipt['http_status'] is None, 'COMPLETE_STATUS_DIFFERS')
    saved = radar.decode((output / 'observation.json').read_bytes())
    for index, record in enumerate(receipt['requests'], 1):
        intent = radar.decode((output / f'request-{index}.json').read_bytes())
        radar._require(intent == {k: record[k] for k in ('path', 'params', 'requested_at')}, 'REQUEST_INTENT_DIFFERS')
    rebuilt = radar.build((output / 'response-1.json').read_bytes(), (output / 'response-2.json').read_bytes(),
                           requests=receipt['requests'], market_session=day,
                           generated_at=saved['projection']['generated_at'], provenance=receipt['provenance'])
    radar._require(_clock(plan['started_at']) == _clock(receipt['started_at'])
                   <= _clock(receipt['requests'][0]['requested_at'])
                   and _clock(saved['projection']['generated_at']) <= _clock(receipt['finished_at'])
                   and saved == rebuilt and (output / 'index.html').read_text() == radar.render(rebuilt),
                   'ORIGINAL_INPUT_REBUILD_DIFFERS')
    return {'status': 'ORIGINAL_INSTITUTIONAL_BODIES_AND_READING_REBUILT', 'network_calls': 0,
            'capture_hash': receipt['capture_hash'], 'projection_hash': rebuilt['projection_hash'],
            'company_count': len(rebuilt['projection']['companies']), **radar.AUTHORITY}


def workflow_identity(env, expected_code):
    required = {'GITHUB_REPOSITORY': 'auguspp/decision-kernel', 'GITHUB_WORKFLOW': 'radar-institutional-source',
                'GITHUB_REF': 'refs/heads/main', 'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1'}
    radar._require(all(env.get(k) == v for k, v in required.items())
                   and re.fullmatch('[0-9a-f]{40}', expected_code or '') is not None
                   and env.get('GITHUB_SHA') == expected_code
                   and re.fullmatch('[1-9][0-9]{0,19}', env.get('GITHUB_RUN_ID', '')) is not None,
                   'FRESH_EXPLICIT_MAIN_WORKFLOW_REQUIRED')
    return {k: env[k] for k in (*required, 'GITHUB_SHA', 'GITHUB_RUN_ID')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('capture', 'verify'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--market-session')
    parser.add_argument('--expected-code')
    args = parser.parse_args(argv)
    try:
        if args.operation == 'verify':
            result = verify(args.output)
        else:
            wf = workflow_identity(os.environ, args.expected_code)
            credential = os.environ.get(HITHINK_API_KEY_ENV, '')
            radar._require(bool(credential), 'PROVIDER_CREDENTIAL_MISSING')
            result = capture(args.output, market_session=args.market_session, workflow=wf,
                             transport=lambda path, params: request_raw(path, params, credential=credential),
                             now=lambda: datetime.now(timezone.utc), credential=credential, provenance='LIVE_HITHINK')
        print(canonical_json({k: result[k] for k in ('status', 'capture_hash')}))
        return 2 if result['status'] in {FAILED, 'RETAINED_FAILED_ATTEMPT_NOT_REMOTE_RETRY_OR_QUIET'} else 0
    except (ValueError, RuntimeError, OSError, KeyError, TypeError):
        print('INSTITUTIONAL_SOURCE_OPERATION_REJECTED; inspect retained bounded receipt if present')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
