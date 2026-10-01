"""Finite NewsNow capture and raw-byte replay using the existing news adapter.

This is a source-input boundary, not an event/Evidence/Research authority.
The publisher reads the resulting bytes; it never executes a saved program.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from ..identity import canonical_hash
from . import current_state as m
from . import external_radar_observations as news
from .ftshare_discovery import _NoRedirect

VERSION = 'native-newsnow-window-v1'
WORKFLOW = '.github/workflows/radar-newsnow-daily.yml'
IMAGE = 'ghcr.io/ourongxing/newsnow@sha256:98b62bd971d308040937fdfde5263a00715b357894936e88b3ce3c0d8adbf55a'
SOURCES = ('cls', 'wallstreetcn', 'fastbull', 'jin10', 'mktnews', 'gelonghui', 'thepaper')
MAX_BODY, MAX_BUNDLE = 1024 * 1024, 12 * 1024 * 1024
HISTORY_VERSION = 'native-newsnow-rolling-v1'
HISTORY_FILE = 'history.json'
HISTORY_HOURS = 18
MAX_HISTORY_OBSERVATIONS = 2000
MAX_HISTORY_CAPTURES = 120
MAX_HISTORY_BYTES = 2 * 1024 * 1024
AUTHORITY = {**m.AUTHORITY, 'automatic_admission': False, 'model_calls': 0,
             'market_requests': 0, 'new_attention_events': 0, 'research_executions': 0}
ERRORS = (ValueError, TypeError, KeyError, OSError, RuntimeError, OverflowError)


def now():
    return datetime.now(timezone.utc).isoformat()


def url(label):
    m.check(label in SOURCES, 'News source outside scope')
    return 'http://127.0.0.1:4444/api/s?id=' + label + '&latest'


def workflow_identity(value):
    m.check(isinstance(value, dict) and set(value) == {
        'repository', 'ref', 'event', 'code_commit', 'run_id', 'attempt', 'workflow', 'trigger_run_id'},
        'News workflow identity shape')
    m.check(value['repository'] == m.REPOSITORY and value['ref'] == 'refs/heads/main'
            and value['workflow'] == WORKFLOW and value['event'] in {'workflow_run', 'workflow_dispatch', 'schedule'}
            and m.SHA.fullmatch(value['code_commit']) is not None
            and type(value['run_id']) is int and value['run_id'] > 0
            and type(value['attempt']) is int and value['attempt'] == 1,
            'News workflow identity differs')
    trigger = value['trigger_run_id']
    m.check((trigger is None and value['event'] in {'workflow_dispatch', 'schedule'}) or
            (type(trigger) is int and trigger > 0 and value['event'] == 'workflow_run'),
            'News trigger identity differs')
    return value


def image_identity(raw):
    m.check(isinstance(raw, bytes) and 0 < len(raw) <= 4096, 'News image identity budget')
    text = raw.decode('utf-8')
    digests, end = json.JSONDecoder().raw_decode(text)
    m.check(isinstance(digests, list) and IMAGE in digests
            and re.fullmatch(r'\s+sha256:[a-f0-9]{64}\s*', text[end:]) is not None,
            'News image digest differs')



def _history_observation(row):
    m.check(isinstance(row, dict) and isinstance(row.get('version_id'), str)
            and re.fullmatch(r'[a-f0-9]{64}', row['version_id']) is not None,
            'News history observation identity invalid')
    source_id = row.get('source_id')
    m.check(source_id in SOURCES and isinstance(row.get('item_id'), str)
            and isinstance(row.get('title'), str) and 0 < len(row['title'].strip()) <= 8192,
            'News history observation shape invalid')
    news._url(row.get('url'), news.NEWS_DOMAINS[source_id])
    claims = row.get('publication_claims')
    m.check(isinstance(claims, dict) and set(claims) == {'pubDate', 'extra.date'}
            and all(isinstance(v, dict) and 'raw' in v for v in claims.values()),
            'News history publication claims invalid')
    identity = {'source_id': source_id, 'item_id': row['item_id'], 'url': row['url']}
    payload = {**identity, 'title': row['title'],
               'publication_claims': {k: v['raw'] for k, v in claims.items()}}
    m.check(row['version_id'] == canonical_hash(payload)
            and row.get('article_id') == canonical_hash(identity),
            'News history observation hash differs')
    return row


def validate_history(value):
    m.check(isinstance(value, dict) and set(value) == {'projection', 'projection_hash'},
            'News rolling history wrapper differs')
    p = value['projection']
    m.check(value['projection_hash'] == canonical_hash(p), 'News rolling history hash differs')
    m.check(isinstance(p, dict) and p.get('version') == HISTORY_VERSION
            and p.get('window_hours') == HISTORY_HOURS
            and p.get('semantics') == 'CAPTURE_FIRST_SEEN_ROLLING_INDEX_NOT_PUBLISHER_TIME_OR_COMPLETE_NEWS',
            'News rolling history contract differs')
    generated = m.clock(p['generated_at'])
    m.check(isinstance(p.get('captures'), list) and len(p['captures']) <= MAX_HISTORY_CAPTURES
            and isinstance(p.get('observations'), list) and len(p['observations']) <= MAX_HISTORY_OBSERVATIONS,
            'News rolling history budget differs')
    run_ids, previous = set(), None
    for capture_row in p['captures']:
        m.check(isinstance(capture_row, dict)
                and set(capture_row) == {'run_id', 'code_commit', 'event', 'captured_from',
                                        'captured_through', 'status', 'source_outcomes'},
                'News rolling capture shape differs')
        m.check(type(capture_row['run_id']) is int and capture_row['run_id'] > 0
                and m.SHA.fullmatch(capture_row['code_commit']) is not None
                and capture_row['event'] in {'workflow_run', 'workflow_dispatch', 'schedule'}
                and capture_row['run_id'] not in run_ids,
                'News rolling capture identity differs')
        start, finish = m.clock(capture_row['captured_from']), m.clock(capture_row['captured_through'])
        m.check(start <= finish <= generated and (previous is None or previous <= start),
                'News rolling capture chronology differs')
        m.check(isinstance(capture_row['source_outcomes'], list)
                and len(capture_row['source_outcomes']) == len(SOURCES),
                'News rolling source outcomes differ')
        run_ids.add(capture_row['run_id']); previous = finish
    seen_versions = set()
    for entry in p['observations']:
        m.check(isinstance(entry, dict) and set(entry) == {
            'observation', 'first_seen_at', 'last_seen_at',
            'first_seen_run_id', 'last_seen_run_id', 'seen_capture_count'},
            'News rolling observation entry differs')
        row = _history_observation(entry['observation'])
        first, last = m.clock(entry['first_seen_at']), m.clock(entry['last_seen_at'])
        m.check(first <= last <= generated and type(entry['seen_capture_count']) is int
                and entry['seen_capture_count'] > 0
                and type(entry['first_seen_run_id']) is int and entry['first_seen_run_id'] > 0
                and type(entry['last_seen_run_id']) is int and entry['last_seen_run_id'] > 0
                and row['version_id'] not in seen_versions,
                'News rolling observation chronology differs')
        seen_versions.add(row['version_id'])
    coverage = p.get('coverage')
    m.check(isinstance(coverage, dict)
            and type(coverage.get('observation_count')) is int
            and coverage['observation_count'] == len(p['observations'])
            and type(coverage.get('capture_count')) is int
            and coverage['capture_count'] == len(p['captures'])
            and type(coverage.get('dropped_observation_count')) is int
            and coverage['dropped_observation_count'] >= 0
            and coverage.get('complete_news_coverage') is False,
            'News rolling coverage differs')
    return value


def _capture_summary(report):
    p = report['projection']
    return {
        'run_id': p['workflow']['run_id'],
        'code_commit': p['workflow']['code_commit'],
        'event': p['workflow']['event'],
        'captured_from': p['captured_from'],
        'captured_through': p['captured_through'],
        'status': p['status'],
        'source_outcomes': [
            {'source_id': o['source_id'], 'status': o['status'],
             'observations_in_window': o.get('observations_in_window')}
            for o in p['source_outcomes']
        ],
    }


def rolling_history(current, previous_raw=None):
    m.check(isinstance(current, dict) and current.get('projection_hash') == canonical_hash(current.get('projection')),
            'News current projection invalid for rolling history')
    p = current['projection']
    finish = m.clock(p['captured_through'])
    window_start = finish - timedelta(hours=HISTORY_HOURS)
    previous = None
    if previous_raw:
        m.check(isinstance(previous_raw, bytes) and 0 < len(previous_raw) <= MAX_HISTORY_BYTES,
                'News previous rolling history byte budget')
        previous = validate_history(news._decode(previous_raw))
        m.check(m.clock(previous['projection']['generated_at']) <= m.clock(p['captured_from']),
                'News previous rolling history is not prior to current capture')

    captures = []
    observations = {}
    if previous is not None:
        prev = previous['projection']
        captures = [deepcopy(x) for x in prev['captures']
                    if m.clock(x['captured_through']) >= window_start]
        for entry in prev['observations']:
            if m.clock(entry['last_seen_at']) >= window_start:
                observations[entry['observation']['version_id']] = deepcopy(entry)

    summary = _capture_summary(current)
    captures = [x for x in captures if x['run_id'] != summary['run_id']]
    captures.append(summary)
    captures.sort(key=lambda x: (m.clock(x['captured_from']), x['run_id']))
    captures = captures[-MAX_HISTORY_CAPTURES:]

    current_rows = []
    if p.get('news') is not None:
        current_rows = p['news']['projection']['observations']
    for row in current_rows:
        _history_observation(row)
        key = row['version_id']
        fetched = row['fetched_at']
        existing = observations.get(key)
        if existing is None:
            observations[key] = {
                'observation': deepcopy(row),
                'first_seen_at': fetched,
                'last_seen_at': fetched,
                'first_seen_run_id': summary['run_id'],
                'last_seen_run_id': summary['run_id'],
                'seen_capture_count': 1,
            }
        else:
            m.check(m.clock(existing['last_seen_at']) <= m.clock(fetched),
                    'News rolling observation time reversed')
            existing['observation'] = deepcopy(row)
            existing['last_seen_at'] = fetched
            existing['last_seen_run_id'] = summary['run_id']
            existing['seen_capture_count'] += 1

    ordered = sorted(observations.values(),
                     key=lambda x: (m.clock(x['last_seen_at']), x['observation']['version_id']),
                     reverse=True)
    original_count = len(ordered)
    ordered = ordered[:MAX_HISTORY_OBSERVATIONS]
    dropped = original_count - len(ordered)

    def seal(rows, dropped_count):
        rows = sorted(rows, key=lambda x: (m.clock(x['first_seen_at']),
                                           x['observation']['source_id'],
                                           x['observation']['version_id']))
        payload = {
            'version': HISTORY_VERSION,
            'window_hours': HISTORY_HOURS,
            'generated_at': p['captured_through'],
            'window_start': window_start.isoformat(),
            'captures': captures,
            'observations': rows,
            'status': 'ROLLING_HISTORY_TRUNCATED' if dropped_count else
                      ('ROLLING_HISTORY_READY' if previous is not None else 'ROLLING_HISTORY_STARTED'),
            'coverage': {
                'capture_count': len(captures),
                'observation_count': len(rows),
                'dropped_observation_count': dropped_count,
                'predecessor_used': previous is not None,
                'complete_news_coverage': False,
            },
            'semantics': 'CAPTURE_FIRST_SEEN_ROLLING_INDEX_NOT_PUBLISHER_TIME_OR_COMPLETE_NEWS',
            **AUTHORITY,
        }
        report = {'projection': payload, 'projection_hash': canonical_hash(payload)}
        return report, m.json_bytes(report)

    report, raw = seal(ordered, dropped)
    while len(raw) > MAX_HISTORY_BYTES and ordered:
        remove = max(1, len(ordered) // 10)
        ordered = ordered[:-remove]
        dropped = original_count - len(ordered)
        report, raw = seal(ordered, dropped)
    m.check(len(raw) <= MAX_HISTORY_BYTES, 'News rolling history byte budget')
    validate_history(report)
    return report

def fetch(label):
    """One fixed local-service GET. No credentials, proxy, redirect or retry."""
    address = url(label)
    req = Request(address, headers={'Accept': 'application/json', 'Accept-Encoding': 'identity',
                                   'User-Agent': 'decision-kernel/' + VERSION})
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    try:
        response = opener.open(req, timeout=15)
    except HTTPError as exc:
        response = exc  # Preserve a bounded error body; do not follow Location.
    with response:
        m.check(response.geturl() == address, 'News redirect rejected')
        m.check(response.headers.get('Content-Encoding', 'identity') == 'identity',
                'News encoded response rejected')
        length = response.headers.get('Content-Length')
        m.check(length is None or length.isdigit() and int(length) <= MAX_BODY,
                'News response length rejected')
        raw = response.read(MAX_BODY + 1)
        m.check(len(raw) <= MAX_BODY and (length is None or len(raw) == int(length)),
                'News response byte bound or length differs')
        m.check(type(response.status) is int and 100 <= response.status <= 599, 'News HTTP status invalid')
        return response.status, raw


def _write(root, path, raw):
    target = root / m.safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as out:
        out.write(raw)


def capture(output, identity, image_raw, *, request=fetch, clock=now, previous_history=None):
    workflow_identity(identity)
    image_identity(image_raw)
    output = Path(output)
    m.check(not output.exists() and not output.is_symlink()
            and not any(p.is_symlink() for p in output.parents), 'News output must be create-only')
    output.mkdir(parents=True, exist_ok=False)
    plan = {'version': VERSION, 'workflow': identity, 'source_ids': list(SOURCES),
            'started_at': clock(), 'image': IMAGE, 'upstream_request_count': 'UNKNOWN',
            'image_source_commit_equivalence': 'NOT_INDEPENDENTLY_ESTABLISHED', **AUTHORITY}
    files = {'plan.json': m.json_bytes(plan), 'image-identity.txt': image_raw}
    for name, raw in files.items():
        _write(output, name, raw)
    for label in SOURCES:
        req = {'label': label, 'url': url(label), 'requested_at': clock()}
        req_path, receipt_path = 'requests/' + label + '.json', 'receipts/' + label + '.json'
        files[req_path] = m.json_bytes(req); _write(output, req_path, files[req_path])
        receipt = {**req, 'received_at': None, 'http_status': None, 'status': 'SOURCE_UNAVAILABLE',
                   'bytes': None, 'sha256': None, 'error_type': None}
        raw = None
        try:
            status, raw = request(label)
            receipt.update(received_at=clock(), http_status=status)
            m.check(type(status) is int and 100 <= status <= 599
                    and isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY, 'News response invalid or empty')
            receipt.update(bytes=len(raw), sha256=m.sha256(raw),
                           status='CAPTURED_PUBLIC_RESPONSE' if status == 200 else 'SOURCE_UNAVAILABLE')
        except ERRORS as exc:
            raw = None
            receipt.update(received_at=clock(), error_type=type(exc).__name__)
        if raw is not None:
            name = 'raw/newsnow-' + label + '.json'
            files[name] = raw; _write(output, name, raw)
        files[receipt_path] = m.json_bytes(receipt); _write(output, receipt_path, files[receipt_path])
    manifest = {'version': VERSION, 'finished_at': clock(), 'local_service_requests': len(SOURCES),
                'files': {name: {'bytes': len(raw), 'sha256': m.sha256(raw)} for name, raw in files.items()}}
    files['capture.json'] = m.json_bytes(manifest); _write(output, 'capture.json', files['capture.json'])
    result = rebuild(files, cutoff=manifest['finished_at'])
    files['observations.json'] = m.json_bytes(result)
    history = rolling_history(result, previous_history)
    files[HISTORY_FILE] = m.json_bytes(history)
    m.check(sum(map(len, files.values())) <= MAX_BUNDLE, 'News bundle exceeds source budget')
    _write(output, 'observations.json', files['observations.json'])
    _write(output, HISTORY_FILE, files[HISTORY_FILE])
    return result


def rebuild(files, *, cutoff, run=None, company_reading=None):
    """Rebuild exact original windows; individual source gaps do not erase peers."""
    m.check(isinstance(files, dict) and len(files) <= 32
            and all(isinstance(v, bytes) for v in files.values())
            and sum(map(len, files.values())) <= MAX_BUNDLE, 'News bundle shape or budget')
    manifest = news._decode(files['capture.json'])
    m.check(set(manifest) == {'version', 'finished_at', 'local_service_requests', 'files'}
            and manifest['version'] == VERSION and manifest['local_service_requests'] == len(SOURCES),
            'News manifest differs')
    entries = manifest['files']
    required = {'plan.json', 'image-identity.txt'} | {
        directory + '/' + label + '.json' for directory in ('requests', 'receipts') for label in SOURCES}
    optional = {'raw/newsnow-' + label + '.json' for label in SOURCES}
    allowed_derived = {'capture.json', 'observations.json', HISTORY_FILE}
    m.check(isinstance(entries, dict) and required <= set(entries) <= required | optional
            and set(entries) | {'capture.json'} <= set(files) <= set(entries) | allowed_derived,
            'News file inventory differs')
    for name, meta in entries.items():
        m.safe_path(name)
        m.check(type(meta.get('bytes')) is int and meta == {'bytes': len(files[name]), 'sha256': m.sha256(files[name])}, 'News raw identity differs')
    image_identity(files['image-identity.txt'])
    plan = news._decode(files['plan.json']); identity = workflow_identity(plan['workflow'])
    m.check(plan['version'] == VERSION and plan['source_ids'] == list(SOURCES) and plan['image'] == IMAGE
            and all(plan.get(k) == v for k, v in AUTHORITY.items()), 'News plan differs')
    start, finish = m.clock(plan['started_at']), m.clock(manifest['finished_at'])
    m.check(start <= finish <= m.clock(cutoff), 'News capture clock differs')
    if run is not None:
        m.check(identity['code_commit'] == run['head_sha'] and identity['run_id'] == run['id']
                and identity['event'] == run['event'] and identity['attempt'] == run['run_attempt']
                and m.clock(run['created_at']) <= start <= finish <= m.clock(run['updated_at']),
                'News capture does not match native run')
    pairs, outcomes = [], []
    previous = start
    for label in SOURCES:
        req = news._decode(files['requests/' + label + '.json'])
        receipt = news._decode(files['receipts/' + label + '.json'])
        m.check(set(receipt) == {'label', 'url', 'requested_at', 'received_at', 'http_status',
                                 'status', 'bytes', 'sha256', 'error_type'}, 'News receipt shape differs')
        m.check(receipt['http_status'] is None or type(receipt['http_status']) is int
                and 100 <= receipt['http_status'] <= 599, 'News receipt HTTP status differs')
        m.check(set(req) == {'label', 'url', 'requested_at'} and req['label'] == label and req['url'] == url(label)
                and all(receipt.get(k) == v for k, v in req.items()), 'News request binding differs')
        m.check(previous <= m.clock(req['requested_at']) <= m.clock(receipt['received_at']) <= finish,
                'News source chronology differs')
        previous = m.clock(receipt['received_at'])
        path = 'raw/newsnow-' + label + '.json'
        if path not in files:
            m.check(receipt['status'] == 'SOURCE_UNAVAILABLE' and receipt['bytes'] is None
                    and receipt['sha256'] is None and isinstance(receipt['error_type'], str),
                    'News missing body cannot be success or empty window')
            outcomes.append({'source_id': label, 'status': 'RESPONSE_UNAVAILABLE', 'receipt': receipt})
            continue
        m.check(0 < len(files[path]) <= MAX_BODY, 'News per-source byte budget')
        news._bound(files[path], receipt, manifest['finished_at'])
        m.check(receipt['status'] == ('CAPTURED_PUBLIC_RESPONSE' if receipt['http_status'] == 200
                                     else 'SOURCE_UNAVAILABLE'), 'News HTTP/receipt status differs')
        try:
            value = news.news(files[path], receipt, cutoff=manifest['finished_at'])
            outcomes.append({'source_id': label, 'status': value['projection']['status'], 'receipt': receipt,
                             'observations_in_window': len(value['projection']['observations'])
                             if value['projection']['status'] == 'OBSERVATIONS_NORMALIZED' else None})
            pairs.append((files[path], receipt))
        except ERRORS as exc:
            outcomes.append({'source_id': label, 'status': 'SOURCE_REPRESENTATION_REJECTED',
                             'receipt': receipt, 'error_type': type(exc).__name__})
    normalized = news.news_context(pairs, cutoff=cutoff,
                                   company_reading=company_reading) if pairs else None
    good = sum(o['status'] == 'OBSERVATIONS_NORMALIZED' for o in outcomes)
    value = {'version': VERSION, 'workflow': identity, 'image': IMAGE,
             'capture_hash': canonical_hash(manifest), 'captured_from': plan['started_at'],
             'captured_through': manifest['finished_at'], 'source_outcomes': outcomes, 'news': normalized,
             'status': 'WINDOWS_CAPTURED' if good == len(SOURCES) else 'PARTIAL_NEWS_WINDOWS' if good else 'NEWS_SOURCE_UNAVAILABLE',
             'coverage': {'planned_sources': len(SOURCES), 'normalized_sources': good,
                          'complete_news_coverage': False, 'window_limit_per_source': 30},
             'upstream_request_count': 'UNKNOWN', 'local_service_requests': len(SOURCES),
             'semantics': 'DATED_NEWS_WINDOWS_NOT_VERIFIED_EVENTS_OR_REVIEWED_QUESTIONS', **AUTHORITY}
    return {'projection': value, 'projection_hash': canonical_hash(value)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--image-identity', type=Path, required=True)
    parser.add_argument('--previous-history', type=Path)
    args = parser.parse_args(argv)
    env = os.environ
    identity = {'repository': env['GITHUB_REPOSITORY'], 'ref': env['GITHUB_REF'],
                'event': env['GITHUB_EVENT_NAME'], 'code_commit': env['GITHUB_SHA'],
                'run_id': int(env['GITHUB_RUN_ID']), 'attempt': int(env['GITHUB_RUN_ATTEMPT']),
                'workflow': WORKFLOW,
                'trigger_run_id': int(env['TRIGGER_RUN_ID']) if env.get('TRIGGER_RUN_ID') else None}
    previous = args.previous_history.read_bytes() if args.previous_history else None
    result = capture(args.output, identity, args.image_identity.read_bytes(), previous_history=previous)
    print('NEWS_CAPTURE_STATUS=' + result['projection']['status'])
    return 0  # Completed finite capture may honestly contain source gaps.


if __name__ == '__main__':
    raise SystemExit(main())
