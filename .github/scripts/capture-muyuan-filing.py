"""Bounded Muyuan 2026 H1 original for Radar source review, not a data feed.

Reuse the existing public Requests transport, issuer resolver and CNINFO parser.
Exactly one stock directory, one fixed query and at most one original PDF.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from decision_kernel.adapters.cninfo import normalize_cninfo_announcement_page
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime.stock_field_source_study import (
    SYMBOLS, PDF_ORIGIN, PDF_PATH, TZ, request_spec, notice_query, MAX_BYTES,
)
from decision_kernel.runtime.economic_release_review import _safe_path, _read, _clock
from decision_kernel.runtime.judgment_timeline import _unique_object

CODE, TITLE = '002714.SZ', '2026年半年度报告'
WINDOW = '2026-08-01~2026-09-06'
SEMANTICS = 'ONE_ISSUER_ORIGINAL_FOR_REVIEW_NOT_ACCEPTED_COMPANY_FACT'
AUTHORITY = dict(investment_authority='NONE', research_authority='NONE',
                 human_attention_authority='NONE', market_state_writes=0, events_created=0)
FIRST = dict(id='cninfo-symbols', url=SYMBOLS, method='GET', params={})


def query(symbols):
    spec = notice_query(CODE, symbols, date(2026, 9, 6))
    spec['params'].update(searchkey=TITLE, seDate=WINDOW)
    return spec


def select(payload, spec):
    org = spec['params']['stock'].split(',', 1)[1]
    if payload.get('hasMore') is not False:
        raise ValueError('INCOMPLETE_QUERY_WINDOW')
    if any(r.get('secCode') != CODE[:6] or r.get('orgId') != org
           for r in payload.get('announcements') or []):
        raise ValueError('ISSUER_IDENTITY_MISMATCH')
    page = normalize_cninfo_announcement_page(payload, stock_code=CODE[:6], org_id=org)
    if page.total_announcement_count != len(page.announcements) or len(page.announcements) > 30:
        raise ValueError('INCOMPLETE_QUERY_WINDOW')
    for item in page.announcements:
        if item.published_at is None or not date(2026, 8, 1) <= item.published_at.astimezone(TZ).date() <= date(2026, 9, 6):
            raise ValueError('OUTSIDE_REVIEWED_WINDOW')
    found = [r for r in page.announcements if r.title in {TITLE, '牧原股份：' + TITLE}]
    if len(found) != 1:
        raise ValueError('FULL_REPORT_MISSING_OR_AMBIGUOUS')
    item = found[0]
    if not item.source_locator.startswith(PDF_ORIGIN) or not PDF_PATH.fullmatch(item.source_locator[len(PDF_ORIGIN):]):
        raise ValueError('ORIGINAL_PATH_REQUIRED')
    return (dict(id='muyuan-h1-original', method='GET', url=item.source_locator, params={}),
            dict(announcement_id=item.announcement_id, title=item.title, org_id=org,
                 published_at=item.published_at.isoformat(), source_url=item.source_locator))


def _json(raw):
    obj = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(obj, dict):
        raise ValueError('OBJECT_REQUIRED')
    return obj


def _data(obj):
    return (canonical_json(obj) + '\n').encode()


def run(root: Path, *, request=None, now=None):
    _safe_path(root)
    if root.exists() or 'decision-state' in root.resolve().parts:
        raise ValueError('NEW_ISOLATED_OUTPUT_REQUIRED')
    provenance = 'PUBLIC_CNINFO_CAPTURE' if request is None else 'SYNTHETIC_TEST_ONLY'
    request = request or (lambda spec: request_spec(spec, api_key=''))
    now = now or (lambda: datetime.now(timezone.utc))
    root.mkdir(parents=True)
    records, files, selected, problem = [], [], None, None
    spec = dict(FIRST)
    previous = None
    try:
        for index in range(3):
            before = now(); _clock(before.isoformat())
            if previous is not None and before < previous:
                raise ValueError('CLOCK_REGRESSED')
            rec = dict(spec=spec, started_at=before.isoformat(), completed_at=None,
                       http_status=None, body=None)
            records.append(rec)
            status, raw = request(spec)
            after = now(); _clock(after.isoformat())
            if after < before:
                raise ValueError('CLOCK_REGRESSED')
            rec['completed_at'] = after.isoformat(); previous = after
            if type(status) is not int or not 100 <= status <= 599:
                raise ValueError('INVALID_HTTP_STATUS')
            rec['http_status'] = status
            if status != 200:
                raise ValueError('HTTP_REFUSED')
            if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
                raise ValueError('BODY_BOUND')
            name = f'{index + 1:02d}.' + ('pdf' if index == 2 else 'json')
            if index == 2 and not raw.startswith(b'%PDF-'):
                raise ValueError('PDF_CONTAINER_REQUIRED')
            if index < 2:
                payload = _json(raw)
            (root / name).write_bytes(raw)
            files.append(dict(name=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
            rec['body'] = name
            if index == 0:
                spec = query(payload)
            elif index == 1:
                spec, selected = select(payload, spec)
    except Exception as exc:
        problem = type(exc).__name__  # no headers, response/error text or credentials
    value = dict(schema_version=1, semantics=SEMANTICS, provenance=provenance,
                 company=CODE, report_title=TITLE, query_window=WINDOW, selected=selected,
                 requests=records, files=files, problem=problem,
                 status='ORIGINAL_CAPTURED_REVIEW_REQUIRED' if problem is None else 'INCOMPLETE', **AUTHORITY)
    value['capture_hash'] = canonical_hash(value)
    (root / 'capture.json').write_bytes(_data(value))
    return value


def verify(root: Path):
    _safe_path(root)
    value = _read(root / 'capture.json', 256 * 1024)
    if (value.get('semantics') != SEMANTICS or value.get('company') != CODE
            or value.get('report_title') != TITLE or value.get('query_window') != WINDOW
            or any(value.get(k) != v for k, v in AUTHORITY.items())
            or value.get('provenance') not in {'PUBLIC_CNINFO_CAPTURE', 'SYNTHETIC_TEST_ONLY'}
            or value.get('capture_hash') != canonical_hash({k:v for k,v in value.items() if k != 'capture_hash'})):
        raise ValueError('CAPTURE_IDENTITY_MISMATCH')
    names = [r['name'] for r in value['files']]
    if len(names) != len(set(names)) or not set(names) <= {'01.json', '02.json', '03.pdf'}:
        raise ValueError('INVENTORY_MISMATCH')
    if {p.name for p in root.iterdir()} != {'capture.json', *names}:
        raise ValueError('INVENTORY_MISMATCH')
    raw = {}
    for item in value['files']:
        path = root / item['name']; _safe_path(path)
        with path.open('rb') as stream:
            content = stream.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES or len(content) != item['bytes'] or hashlib.sha256(content).hexdigest() != item['sha256']:
            raise ValueError('BODY_MISMATCH')
        raw[item['name']] = content
    records = value['requests']
    if not 1 <= len(records) <= 3:
        raise ValueError('REQUEST_BUDGET')
    expected, selected, previous, used = FIRST, None, None, []
    for index, rec in enumerate(records):
        if rec['spec'] != expected:
            raise ValueError('REQUEST_PLAN_MISMATCH')
        before = _clock(rec['started_at'])
        if previous is not None and before < previous:
            raise ValueError('CLOCK_REGRESSED')
        if rec['completed_at'] is not None:
            previous = _clock(rec['completed_at'])
            if previous < before:
                raise ValueError('CLOCK_REGRESSED')
        body = rec['body']
        if body is None:
            if index != len(records) - 1 or value['status'] != 'INCOMPLETE':
                raise ValueError('MISSING_BODY')
            break
        if rec['http_status'] != 200 or rec['completed_at'] is None or body != f'{index+1:02d}.' + ('pdf' if index == 2 else 'json'):
            raise ValueError('RESPONSE_IDENTITY_MISMATCH')
        used.append(body)
        try:
            if index == 0:
                expected = query(_json(raw[body]))
            elif index == 1:
                expected, selected = select(_json(raw[body]), expected)
            elif not raw[body].startswith(b'%PDF-'):
                raise ValueError('PDF_CONTAINER_REQUIRED')
        except ValueError:
            if value['status'] != 'INCOMPLETE' or index != len(records) - 1:
                raise
    complete = len(records) == 3 and len(used) == 3 and selected is not None
    if (set(used) != set(names) or selected != value['selected']
            or (value['status'] == 'ORIGINAL_CAPTURED_REVIEW_REQUIRED') != (complete and value['problem'] is None)):
        raise ValueError('RESULT_MISMATCH')
    return value


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['capture', 'verify']); p.add_argument('directory', type=Path)
    a = p.parse_args()
    result = run(a.directory) if a.command == 'capture' else verify(a.directory)
    print(canonical_json(result))
    raise SystemExit(0 if a.command == 'verify' or result['status'] == 'ORIGINAL_CAPTURED_REVIEW_REQUIRED' else 2)
