"""Bounded Eastmoney report discovery; no PDF, Research or investment execution.

Protocol mapping adapted from manymore13/report-cli@0d98dde87a6b295359ae68152ca2693428baef83.
MIT notice and adoption/exit scope: docs/broker-report-discovery-v1.md.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import requests

from ..identity import canonical_hash, canonical_json

VERSION = 'broker-report-discovery-v1'
KINDS = {'industry': ('list', '1', 'zw_industry'),
         'strategy': ('jg', '2', 'zw_strategy'),
         'macro': ('jg', '3', 'zw_macresearch'),
         'morning': ('jg', '4', 'zw_macresearch')}
PREFIXES = {'strategy': '002001002', 'macro': '002001001', 'morning': '002003001'}
MAX_PAGES, PAGE_SIZE, MAX_BODY = 4, 50, 512 * 1024
ZONE = ZoneInfo('Asia/Shanghai')
AUTHORITY = {'qualification': 'DISCOVERY_ONLY_NOT_REPORT_BODY', 'investment_authority': 'NONE',
             'research_executions': 0, 'pdf_requests': 0, 'automatic_full': False,
             'odds_recomputed': False, 'watch_created': False}


def require(ok, code):
    if not ok:
        raise ValueError(code)


def encoded(value):
    return (canonical_json(value) + '\n').encode('utf-8')


def decode(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, 'DUPLICATE_JSON_KEY')
            out[key] = value
        return out
    return json.loads(raw.decode('utf-8-sig'), parse_float=Decimal, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False, 'NONFINITE_JSON'))


def clock(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'CLOCK_ZONE')
    return parsed.astimezone(timezone.utc)


def now():
    return datetime.now(timezone.utc).isoformat()


def scope(kind, begin, end, pages=1, industry_code=None):
    require(kind in KINDS, 'REPORT_KIND')
    require(all(isinstance(x, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', x)
                for x in (begin, end)), 'DATE_FORMAT')
    require(0 <= (date.fromisoformat(end) - date.fromisoformat(begin)).days <= 92, 'WINDOW')
    require(type(pages) is int and 1 <= pages <= MAX_PAGES, 'PAGE_BUDGET')
    require(industry_code is None or kind == 'industry' and isinstance(industry_code, str)
            and re.fullmatch(r'\d{1,12}', industry_code), 'INDUSTRY_CODE')
    return dict(kind=kind, begin=begin, end=end, pages=pages, industry_code=industry_code)


def spec(selected, page):
    require(selected == scope(**selected), 'SCOPE')
    require(type(page) is int and 1 <= page <= selected['pages'], 'PAGE')
    route, qtype, _ = KINDS[selected['kind']]
    params = {'pageSize': str(PAGE_SIZE), 'pageNo': str(page), 'beginTime': selected['begin'],
              'endTime': selected['end'], 'qType': qtype, 'fields': '', 'industry': '*',
              'rating': '*', 'ratingChange': '*', 'orgCode': '', 'rcode': ''}
    if selected['kind'] == 'industry':
        params['industryCode'] = selected['industry_code'] or '*'
    return {'url': 'https://reportapi.eastmoney.com/report/' + route, 'params': params}


def request_raw(request, selected, *, session_factory=None):
    require(request in [spec(selected, p) for p in range(1, selected['pages'] + 1)], 'REQUEST_SPEC')
    if session_factory is None:
        from .hithink_dump_trial import _session
        session_factory = _session
    with session_factory() as session:
        session.trust_env = False
        with session.get(request['url'], params=request['params'], stream=True,
                         allow_redirects=False, timeout=(10, 20),
                         headers={'Accept-Encoding': 'identity', 'Accept': 'application/json',
                                  'User-Agent': 'DecisionKernel-ReportDiscovery/1'}) as response:
            expected = requests.Request('GET', request['url'], params=request['params']).prepare().url
            require(response.url == expected, 'DESTINATION_CHANGED')
            require(response.headers.get('Content-Encoding', 'identity').lower() in {'', 'identity'}, 'ENCODING')
            length = response.headers.get('Content-Length')
            require(length is None or length.isdigit() and int(length) <= MAX_BODY, 'BODY_SIZE')
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                require(size <= MAX_BODY, 'BODY_SIZE')
                chunks.append(chunk)
            require(length is None or int(length) == size, 'BODY_LENGTH')
            return response.status_code, b''.join(chunks)


def page_data(raw, selected, page):
    obj = decode(raw)
    require(isinstance(obj, dict), 'ENVELOPE')
    require(('success' not in obj or obj['success'] is True) and (obj.get('code') is None or type(obj['code']) is int and obj['code'] in (0, 200)), 'BUSINESS_FAILURE')
    rows = obj.get('data')
    require(isinstance(rows, list) and len(rows) <= PAGE_SIZE, 'ROWS')
    # Never treat report-cli's ambiguous `total` as a page count.
    count, pages, returned = obj.get('hits'), obj.get('TotalPage'), obj.get('pageNo')
    require(type(count) is int and count >= 0 and type(pages) is int and pages >= 0, 'COUNTERS_UNKNOWN')
    require(type(returned) is int and returned == page, 'RETURNED_PAGE')
    require(pages == (count + PAGE_SIZE - 1) // PAGE_SIZE or count == 0 and pages in (0, 1), 'COUNTERS')
    require(page <= max(1, pages), 'PAGE_OUTSIDE_TOTAL')
    require(len(rows) == min(PAGE_SIZE, max(0, count - (page - 1) * PAGE_SIZE)), 'PAGE_ROW_COUNT')
    return rows, count, pages


def field(row, key, limit=2000):
    value = row.get(key)
    if value is None or value == '':
        return None
    require(isinstance(value, str) and len(value) <= limit
            and not any(ord(c) < 32 for c in value), 'FIELD_FORMAT')
    return value


def row_version(value):
    """Source JSON types are significant; Decimal 1.2 is not the string '1.2'."""
    def typed(item):
        if isinstance(item, dict):
            return ['object', [[key, typed(item[key])] for key in sorted(item)]]
        if isinstance(item, list):
            return ['array', [typed(x) for x in item]]
        return [type(item).__name__, item]
    return canonical_hash(typed(value))


def candidate(row, selected, rec, index):
    require(isinstance(row, dict), 'ROW')
    published = field(row, 'publishDate')
    require(published is not None and re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)?', published), 'PUBLICATION_DATE')
    datetime.fromisoformat(published)
    require(selected['begin'] <= published[:10] <= selected['end']
            and date.fromisoformat(published[:10]) <= clock(rec['received_at']).astimezone(ZONE).date(), 'PUBLICATION_WINDOW')
    info, token = field(row, 'infoCode', 80), field(row, 'encodeUrl', 1024)
    require(info is not None or token is not None, 'REPORT_ID_MISSING')
    require(info is None or re.fullmatch(r'[A-Za-z0-9_-]{1,80}', info), 'REPORT_ID_FORMAT')
    title = field(row, 'title')
    require(title is not None, 'TITLE_MISSING')
    column = field(row, 'column', 80)
    prefix = PREFIXES.get(selected['kind'])
    type_status = ('REQUEST_ONLY_NOT_INDEPENDENTLY_VERIFIED' if prefix is None or column is None
                   else 'COLUMN_MATCH' if column.startswith(prefix) else 'COLUMN_CONFLICT')
    require(selected['industry_code'] is None or row.get('industryCode') == selected['industry_code'], 'INDUSTRY_FILTER_MISMATCH')
    query = {'encodeUrl': token} if token else {'infocode': info}
    url = 'https://data.eastmoney.com/report/' + KINDS[selected['kind']][2] + '.jshtml?' + urlencode(query)
    return {'report_key': canonical_hash(['EASTMONEY', 'infoCode' if info else 'encodeUrl', info or token]),
            'version': row_version(row), 'info_code': info, 'encode_url': token,
            'title': title, 'institution': field(row, 'orgSName'), 'institution_code': field(row, 'orgCode'),
            'industry': field(row, 'industryName'), 'publication_raw': published,
            'publication_date': published[:10], 'publication_timezone': 'UNKNOWN',
            'acquired_at': rec['received_at'], 'historical_available_at': 'NOT_ESTABLISHED',
            'requested_kind': selected['kind'], 'column': column, 'type_status': type_status,
            'rating_fields': {k: row.get(k) for k in ('ratingName', 'emRatingName', 'sRatingName')},
            'detail_url': url, 'detail_status': 'UNFETCHED_LOCATOR',
            'source_rows': [{'body': rec['body'], 'sha256': rec['sha256'], 'row': index}]}


def project(meta, bodies):
    require(meta['version'] == VERSION and meta['authority'] == AUTHORITY, 'VERSION_OR_AUTHORITY')
    require(meta['capture_hash'] == canonical_hash({k: v for k, v in meta.items() if k != 'capture_hash'}), 'CAPTURE_HASH')
    selected = meta['scope']
    require(selected == scope(**selected), 'SCOPE')
    start, finish = clock(meta['started_at']), clock(meta['finished_at'])
    require(start <= finish and date.fromisoformat(selected['end']) <= start.astimezone(ZONE).date(), 'CAPTURE_CLOCKS')
    require(type(meta['final']) is bool and isinstance(meta['records'], list)
            and len(meta['records']) <= selected['pages']
            and (not meta['final'] or bool(meta['records'])), 'RECORDS')
    unique, seen_ids, used, total, pages = {}, set(), set(), None, None
    failure_detail = None
    terminal, reason, previous, returned_rows = False, 'INCOMPLETE_CAPTURE', start, 0
    for page, rec in enumerate(meta['records'], 1):
        require(not terminal and rec['request'] == spec(selected, page), 'REQUEST_AFTER_STOP_OR_CHANGED')
        requested, received = clock(rec['requested_at']), clock(rec['received_at'])
        require(previous <= requested <= received <= finish, 'REQUEST_CLOCKS')
        previous = received
        status = rec['http_status']
        require(status is None or type(status) is int and 100 <= status <= 599, 'HTTP_STATUS')
        if rec['body'] is None:
            require(status is None and rec['sha256'] is None and rec['bytes'] is None
                    and rec['error'] in {'TRANSPORT_ERROR', 'TRANSPORT_CONTRACT'}, 'TRANSPORT_RECEIPT')
            terminal, reason = True, rec['error']
            continue
        name = f'page-{page}.body'
        require(rec['body'] == name and rec['error'] is None and status is not None, 'BODY_RECEIPT')
        raw = bodies[name]
        require(isinstance(raw, bytes) and len(raw) <= MAX_BODY and type(rec['bytes']) is int
                and len(raw) == rec['bytes'] and sha256(raw).hexdigest() == rec['sha256'], 'BODY_IDENTITY')
        used.add(name)
        if status != 200:
            terminal, reason = True, 'POLICY_STOP' if status in (401, 403, 429) or 300 <= status < 400 else 'HTTP_UNAVAILABLE'
            continue
        try:
            rows, count, npages = page_data(raw, selected, page)
            require(total is None or (total, pages) == (count, npages), 'PAGE_DENOMINATOR_DRIFT')
            items = [candidate(r, selected, rec, i) for i, r in enumerate(rows)]
            # Commit the page only after every row qualifies; raw bytes remain even on failure.
            total, pages = count, npages
            returned_rows += len(rows)
            for item in items:
                key = (item['report_key'], item['version'])
                if key in unique:
                    unique[key]['source_rows'].extend(item['source_rows'])
                else:
                    unique[key] = item
                seen_ids.add(item['report_key'])
            terminal = page >= max(1, pages)
            reason = 'PROVIDER_PAGES_READ_NOT_CORPUS_COMPLETENESS' if terminal else 'PAGE_BUDGET_REACHED'
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
            terminal, reason = True, 'RETAINED_PAGE_UNQUALIFIED'
            detail = str(exc)
            failure_detail = detail if re.fullmatch(r'[A-Z_]{1,80}', detail) else 'INVALID_JSON_OR_FIELDS'
    require(used == set(bodies), 'UNBOUND_BODY')
    if len(meta['records']) == selected['pages']:
        terminal = True
    if not meta['final']:
        reason = 'INTERRUPTED_OR_IN_PROGRESS'
    records = sorted(unique.values(), key=lambda r: (r['publication_date'], r['report_key'], r['version']), reverse=True)
    # Repeated IDs across pages are not a complete unique catalogue, even when counters match.
    return {'scope': selected, 'capture_hash': meta['capture_hash'], 'coverage': reason,
            'provider_total': total, 'provider_pages': pages, 'pages_attempted': len(meta['records']),
            'failure_detail': failure_detail,
            'returned_rows': returned_rows, 'unique_reports': len(seen_ids), 'versions': len(records),
            'duplicate_or_variant_rows': returned_rows - len(seen_ids),
            'window_completeness': 'NOT_ESTABLISHED', 'source_calls_during_replay': 0,
            'terminal': terminal, 'records': records, **AUTHORITY}


def render(result):
    def text(value):
        value = escape(str(value)).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')
        return re.sub(r'([\\`*_{}\[\]()#!])', r'\\\1', value)
    lines = ['# 券商研报候选目录', '', text(canonical_json(result['scope'])), '',
             '仅发现线索；未取得/阅读PDF，不是共识、预测修订或投资建议。',
             '日期为来源声明；取得时间不等于历史首次可得时间。',
             '覆盖：' + text(result['coverage']),
             f"已取 {result['returned_rows']} 行 / {result['unique_reports']} 个报告身份 / {result['versions']} 个版本；完整市场覆盖未建立。", '']
    for row in result['records']:
        lines.append(f"- {row['publication_date']} | {text(row['institution'])} | {text(row['title'])} | {text(row['type_status'])}")
    return '\n'.join(lines) + '\n'


def capture(root, selected, *, transport=request_raw, clock_fn=now, sleep=time.sleep):
    selected = scope(**selected)
    started = clock_fn()
    require(date.fromisoformat(selected['end']) <= clock(started).astimezone(ZONE).date(), 'FUTURE_WINDOW')
    root = Path(root)
    require(not root.exists() and not any(p.is_symlink() for p in (root, *root.parents)), 'OUTPUT_CREATE_ONLY')
    root.mkdir(parents=True)
    meta = {'version': VERSION, 'scope': selected, 'authority': deepcopy(AUTHORITY),
            'started_at': started, 'finished_at': started, 'records': [], 'final': False}
    bodies = {}
    def checkpoint():
        meta['finished_at'] = clock_fn()
        meta['capture_hash'] = canonical_hash({k: v for k, v in meta.items() if k != 'capture_hash'})
        temp = root / 'capture.tmp'
        with temp.open('xb') as stream:
            stream.write(encoded(meta))
        temp.replace(root / 'capture.json')
    checkpoint()
    for page in range(1, selected['pages'] + 1):
        if page > 1:
            sleep(0.5)
        rec = {'request': spec(selected, page), 'requested_at': clock_fn(), 'received_at': None,
               'http_status': None, 'body': None, 'bytes': None, 'sha256': None, 'error': None}
        raw = None
        try:
            status, raw = transport(rec['request'], selected)
            require(type(status) is int and 100 <= status <= 599 and isinstance(raw, bytes)
                    and len(raw) <= MAX_BODY, 'TRANSPORT_CONTRACT')
        except requests.RequestException:
            rec['error'] = 'TRANSPORT_ERROR'
        except ValueError:
            rec['error'] = 'TRANSPORT_CONTRACT'
        rec['received_at'] = clock_fn()
        if rec['error'] is None:
            name = f'page-{page}.body'
            # A custody write failure is fatal, not a source timeout and never retried.
            with (root / name).open('xb') as stream:
                stream.write(raw)
            bodies[name] = raw
            rec.update(http_status=status, body=name, bytes=len(raw), sha256=sha256(raw).hexdigest())
        meta['records'].append(rec)
        checkpoint()
        if project(meta, bodies)['terminal']:
            break
    meta['final'] = True
    checkpoint()
    result = project(meta, bodies)
    for name, raw in (('catalog.json', encoded(result)), ('summary.md', render(result).encode('utf-8'))):
        with (root / name).open('xb') as stream:
            stream.write(raw)
    return result


def replay(root, expected_hash):
    root = Path(root)
    require(root.is_dir() and not any(p.is_symlink() for p in (root, *root.parents)), 'UNSAFE_DIRECTORY')
    paths = list(root.iterdir())
    require(len(paths) <= MAX_PAGES + 3 and all(p.is_file() and not p.is_symlink()
            and p.stat().st_size <= MAX_BODY * MAX_PAGES * 2 for p in paths), 'FILE_BUDGET')
    files = {p.name: p.read_bytes() for p in paths}
    meta = decode(files.pop('capture.json'))
    require(meta['capture_hash'] == expected_hash, 'EXPECTED_CAPTURE_HASH')
    catalog, summary = files.pop('catalog.json', None), files.pop('summary.md', None)
    result = project(meta, files)
    require(catalog is None or catalog == encoded(result), 'CATALOG_DIFFERS')
    require(summary is None or summary == render(result).encode('utf-8'), 'SUMMARY_DIFFERS')
    return result


def search(result, keyword):
    require(isinstance(keyword, str) and 0 < len(keyword.strip()) <= 200, 'KEYWORD')
    needle = keyword.strip().casefold()
    matches = [r for r in result['records'] if r['type_status'] != 'COLUMN_CONFLICT'
               and any(needle in (r[k] or '').casefold() for k in ('title', 'institution', 'industry'))]
    return {**result, 'filter': {'keyword': keyword, 'basis': 'LOCAL_TITLE_BROKER_INDUSTRY_SUBSTRING',
                                'not_fulltext_search': True, 'matched_versions': len(matches)},
            'records': matches}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['plan', 'capture', 'replay', 'search'])
    parser.add_argument('--kind', choices=KINDS)
    parser.add_argument('--begin')
    parser.add_argument('--end')
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--industry-code')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--expected-hash')
    parser.add_argument('--keyword')
    args = parser.parse_args(argv)
    try:
        if args.operation in {'plan', 'capture'}:
            selected = scope(args.kind, args.begin, args.end, args.pages, args.industry_code)
            if args.operation == 'plan':
                result = {'scope': selected, 'requests': [spec(selected, p) for p in range(1, selected['pages'] + 1)], **AUTHORITY}
            else:
                require(args.output is not None, 'OUTPUT_REQUIRED')
                result = capture(args.output, selected)
        else:
            require(args.output is not None and args.expected_hash is not None, 'OUTPUT_AND_HASH_REQUIRED')
            result = replay(args.output, args.expected_hash)
            if args.operation == 'search':
                result = search(result, args.keyword)
        print(canonical_json(result))
    except (ValueError, TypeError, KeyError, OSError):
        parser.exit(2, 'Report discovery failed; retain the existing output and inspect its coverage. No automatic retry.\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
