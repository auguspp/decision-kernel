"""Eight public source attempts inside the existing Industry workflow, no retries."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import os
import time

import requests

from ..identity import canonical_hash, canonical_json
from . import easy_stock_context as c
from .hithink_dump_trial import _session, _check_response
from .sector_radar_audit import _check_safe_json

WORKFLOW = '.github/workflows/radar-industry-breadth.yml'
ARTIFACT_PREFIX = 'easy-stock-context-'
MAX_SECONDS = 180
ERRORS = (ValueError, TypeError, KeyError, OSError, RuntimeError, OverflowError,
          UnicodeError, csv.Error, requests.RequestException)


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return (canonical_json(value) + '\n').encode()


def identity(value):
    # Use the existing native Industry workflow identity, not a parallel authority.
    from .industry_breadth import workflow_identity
    return workflow_identity(value)


def request_raw(spec, target_date):
    c.require(spec in c.requests_for(target_date), 'PUBLIC_REQUEST_NOT_REVIEWED')
    referer = {'TENCENT': 'https://stockapp.finance.qq.com/',
               'EASTMONEY': 'https://data.eastmoney.com/', 'CFFEX': 'http://www.cffex.com.cn/'}[spec['provider']]
    with _session() as session:
        with session.get(spec['url'], params=spec['params'], stream=True, allow_redirects=False,
                timeout=(10, 20), headers={'Accept-Encoding': 'identity',
                    'User-Agent': 'Mozilla/5.0 DecisionKernel-public-context', 'Referer': referer}) as response:
            length = _check_response(response)
            expected = requests.Request('GET', spec['url'], params=spec['params']).prepare().url
            c.require(response.url == expected and (length is None or length <= c.MAX_BODY),
                      'PUBLIC_RESPONSE_DESTINATION_OR_SIZE_DIFFERS')
            parts, size = [], 0
            for part in response.iter_content(chunk_size=65536):
                size += len(part)
                c.require(size <= c.MAX_BODY, 'PUBLIC_BODY_BUDGET')
                parts.append(part)
            c.require(length is None or size == length, 'PUBLIC_BODY_LENGTH_DIFFERS')
    return b''.join(parts)


def safe_body(raw, spec):
    c.require(isinstance(raw, bytes) and 0 < len(raw) <= c.MAX_BODY, 'PUBLIC_BODY_BUDGET')
    if spec['provider'] != 'CFFEX':
        _check_safe_json(c.decode(raw))
    else:
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('gb18030')
        c.require('\x00' not in text, 'PUBLIC_CSV_BINARY_REJECTED')


def capture(output, workflow, *, transport=request_raw, clock=now, monotonic=time.monotonic):
    identity(workflow)
    root = Path(output)
    c.require(not root.exists() and not root.is_symlink()
              and not any(p.is_symlink() for p in root.parents), 'PUBLIC_OUTPUT_CREATE_ONLY')
    start = clock(); target = c.clock(start).astimezone(c.ZONE).date().isoformat()
    plan = {'version': c.VERSION, 'upstream_commit': c.UPSTREAM, 'workflow': workflow,
            'started_at': start, 'target_date': target, 'requests': c.requests_for(target),
            'target_date_meaning': 'LOCAL_CALENDAR_DATE_NOT_QUALIFIED_COMPLETED_SESSION', **c.AUTHORITY}
    root.mkdir(parents=True, exist_ok=False)
    def save(name, raw):
        with (root / name).open('xb') as stream:
            stream.write(raw)
    save('plan.json', encoded(plan))
    records, blocked = [], set()
    begin = monotonic()
    for spec in plan['requests']:
        elapsed_ms = round((monotonic() - begin) * 1000)
        c.require(elapsed_ms >= 0, 'PUBLIC_MONOTONIC_CLOCK_REVERSED')
        record = {'request': spec, 'target_date': target, 'requested_at': None, 'received_at': None,
            'http_status': None, 'bytes': None, 'sha256': None, 'body_file': None,
            'elapsed_ms_before_request': elapsed_ms,
            'representation': 'RETAINED_HTTP_BODY', 'status': 'NOT_ATTEMPTED_TIME_BUDGET', 'error_type': None}
        if spec['provider'] in blocked:
            record['status'] = 'NOT_ATTEMPTED_PROVIDER_RATE_LIMIT'
        elif elapsed_ms < MAX_SECONDS * 1000:
            record['requested_at'] = clock()
            try:
                raw = transport(spec, target)
                record['received_at'] = clock()
                record['http_status'] = 200
                safe_body(raw, spec)
                filename = spec['id'] + '.body'
                save(filename, raw)
                record.update(status='CAPTURED_HTTP_BODY', http_status=200, bytes=len(raw),
                              sha256=c.sha256(raw).hexdigest(), body_file=filename)
            except ERRORS as exc:
                record.update(status='BODY_NOT_RETAINED' if record['http_status'] == 200 else 'SOURCE_UNAVAILABLE',
                              received_at=clock(), error_type=type(exc).__name__)
                status = getattr(exc, 'http_status', None)
                if type(status) is int and 100 <= status <= 599:
                    record['http_status'] = status
                if status == 429:
                    blocked.add(spec['provider'])
        records.append(record)
    result = {'version': c.VERSION, 'upstream_commit': c.UPSTREAM, 'plan_hash': canonical_hash(plan),
        'workflow': workflow, 'started_at': start, 'finished_at': clock(), 'target_date': target,
        'records': records, 'attempted_requests': sum(r['requested_at'] is not None for r in records),
        'retry_count': 0, **c.AUTHORITY}
    result['capture_hash'] = canonical_hash(result)
    save('capture.json', encoded(result))
    return result


def replay(files, run, *, cutoff):
    c.require(isinstance(files, dict) and {'plan.json', 'capture.json'} <= set(files)
        and len(files) <= 10 and all(isinstance(v, bytes) and 0 < len(v) <= c.MAX_BODY for v in files.values())
        and sum(map(len, files.values())) <= 8 * c.MAX_BODY + 65536, 'PUBLIC_FILE_INVENTORY_INVALID')
    plan, saved = c.decode(files['plan.json']), c.decode(files['capture.json'])
    c.require(saved['capture_hash'] == canonical_hash({k: v for k, v in saved.items() if k != 'capture_hash'})
        and saved['plan_hash'] == canonical_hash(plan) and saved['version'] == plan['version'] == c.VERSION
        and saved['upstream_commit'] == plan['upstream_commit'] == c.UPSTREAM
        and all(saved.get(k) == plan.get(k) == v for k, v in c.AUTHORITY.items()), 'PUBLIC_CAPTURE_IDENTITY_DIFFERS')
    wf = identity(saved['workflow'])
    c.require(wf == plan['workflow'] and wf['code_commit'] == run['head_sha'] and wf['run_id'] == run['id']
        and wf['attempt'] == run['run_attempt'] and wf['event'] == run['event'], 'PUBLIC_RUN_BINDING_DIFFERS')
    target = saved['target_date']; started = c.clock(saved['started_at']); finished = c.clock(saved['finished_at'])
    c.require(saved['started_at'] == plan['started_at'] and target == plan['target_date']
        and target == started.astimezone(c.ZONE).date().isoformat()
        and c.clock(run['created_at']) <= started <= finished <= c.clock(run['updated_at']) <= c.clock(cutoff),
        'PUBLIC_RUN_CLOCKS_DIFFER')
    specs = c.requests_for(target); records = saved['records']
    c.require(plan['requests'] == specs and isinstance(records, list) and len(records) == 8
        and plan['target_date_meaning'] == 'LOCAL_CALENDAR_DATE_NOT_QUALIFIED_COMPLETED_SESSION'
        and type(saved['retry_count']) is int and saved['retry_count'] == 0, 'PUBLIC_PLAN_DIFFERS')
    names, sections, blocked = {'plan.json', 'capture.json'}, [], set()
    previous, attempted, elapsed_previous = started, 0, 0
    for spec, r in zip(specs, records):
        c.require(r['request'] == spec and r['target_date'] == target
            and r['representation'] == 'RETAINED_HTTP_BODY', 'PUBLIC_RECEIPT_REQUEST_DIFFERS')
        elapsed = r['elapsed_ms_before_request']
        c.require(type(elapsed) is int and elapsed >= elapsed_previous, 'PUBLIC_MONOTONIC_RECORD_DIFFERS')
        elapsed_previous = elapsed
        section = {'source_id': spec['id'], 'status': r['status'], 'receipt': r, 'result': None}
        if r['requested_at'] is None:
            c.require(r['status'] in {'NOT_ATTEMPTED_PROVIDER_RATE_LIMIT', 'NOT_ATTEMPTED_TIME_BUDGET'}
                and all(r[k] is None for k in ('received_at', 'http_status', 'bytes', 'sha256', 'body_file', 'error_type')),
                'PUBLIC_NOT_ATTEMPTED_DIFFERS')
            c.require(r['status'] != 'NOT_ATTEMPTED_TIME_BUDGET' or elapsed >= MAX_SECONDS * 1000,
                      'PUBLIC_TIME_BUDGET_NOT_REACHED')
            c.require((r['status'] == 'NOT_ATTEMPTED_PROVIDER_RATE_LIMIT') == (spec['provider'] in blocked),
                      'PUBLIC_RATE_LIMIT_ORDER_DIFFERS')
        else:
            attempted += 1
            c.require(elapsed < MAX_SECONDS * 1000 and spec['provider'] not in blocked and previous <= c.clock(r['requested_at'])
                <= c.clock(r['received_at']) <= finished, 'PUBLIC_RECEIPT_CLOCK_OR_RETRY_DIFFERS')
            previous = c.clock(r['received_at'])
            if r['status'] in {'SOURCE_UNAVAILABLE', 'BODY_NOT_RETAINED'}:
                c.require(all(r[k] is None for k in ('bytes', 'sha256', 'body_file'))
                    and isinstance(r['error_type'], str) and r['error_type'].isidentifier()
                    and (r['http_status'] is None or (type(r['http_status']) is int and 100 <= r['http_status'] <= 599)),
                    'PUBLIC_FAILURE_DIFFERS')
                c.require((r['status'] == 'BODY_NOT_RETAINED') == (r['http_status'] == 200),
                          'PUBLIC_FAILURE_PHASE_DIFFERS')
                if r['http_status'] == 429:
                    blocked.add(spec['provider'])
            else:
                filename = spec['id'] + '.body'
                c.require(r['status'] == 'CAPTURED_HTTP_BODY' and r['body_file'] == filename
                    and r['error_type'] is None and r['http_status'] == 200, 'PUBLIC_BODY_IDENTITY_DIFFERS')
                body = files[filename]; names.add(filename); safe_body(body, spec)
                c.require(type(r['bytes']) is int and r['bytes'] == len(body)
                    and r['sha256'] == c.sha256(body).hexdigest(), 'PUBLIC_RETAINED_BYTES_DIFFER')
                try:
                    section['result'] = c.normalize(body, r, cutoff=cutoff)
                    section['status'] = section['result']['projection']['status']
                except ERRORS as exc:
                    section.update(status='RETAINED_BODY_CONTRACT_REJECTED', error_type=type(exc).__name__)
        sections.append(section)
    c.require(names == set(files) and type(saved['attempted_requests']) is int
              and saved['attempted_requests'] == attempted <= 8, 'PUBLIC_REQUEST_OR_FILE_COUNT_DIFFERS')
    return {'version': c.VERSION, 'workflow': wf, 'capture_hash': saved['capture_hash'],
        'target_date': target, 'started_at': saved['started_at'], 'finished_at': saved['finished_at'],
        'sections': sections, 'attempted_requests': attempted, 'source_calls_during_replay': 0,
        'meaning': 'RAW_REPLAY_NOT_LIVE_FIELD_TRUTH_OR_RESEARCH_ACCEPTANCE', **c.AUTHORITY}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv); env = os.environ
    wf = {'repository': env['GITHUB_REPOSITORY'], 'workflow': WORKFLOW,
        'ref': env['GITHUB_REF'], 'event': env['GITHUB_EVENT_NAME'], 'code_commit': env['GITHUB_SHA'],
        'run_id': int(env['GITHUB_RUN_ID']), 'attempt': int(env['GITHUB_RUN_ATTEMPT']),
        'trigger_run_id': int(env['TRIGGER_RUN_ID']) if env.get('TRIGGER_RUN_ID') else None}
    value = capture(args.output, wf)
    print('PUBLIC_CONTEXT_ATTEMPTED_REQUESTS=' + str(value['attempted_requests']))
    return 0  # Receipt success is explicitly NOT eight successful source contracts.


if __name__ == '__main__':
    raise SystemExit(main())
