"""Finite FTShare market/sector/industry inputs; no default provider replacement.

This module keeps the existing raw/clock/Decimal conventions. Endpoint schemas
are intentionally separate; it is not a generic market-data provider framework.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import hashlib
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from . import ftshare_discovery as original
from .ftshare_financial import decode, raw_json

VERSION = 'ftshare-market-inputs-v1'
BASE = 'https://market.ft.tech/gateway/api/v1/market/data/'
ROUTES = {
    'stock': 'stock-history-list', 'flow': 'eastmoney-stock-flow',
    'sw_overview': 'sw-industry/overview', 'sw_members': 'sw-industry/constituent-history',
    'sw_metrics': 'sw-industry/daily-metrics', 'concept_catalog': 'eastmoney-concept-boards',
    'concept_members': 'eastmoney-board-constituents', 'concept_prices': 'eastmoney-board-daily-ohlc',
    'futures_list': 'futures/futures-lists', 'futures_base': 'futures/futures-base-data',
    'futures_prices': 'futures/kline', 'warehouse': 'futures/fut-wsr',
}
PAGED = {'stock', 'flow', 'sw_overview', 'sw_metrics', 'concept_prices', 'warehouse'}
MAX_BYTES, MAX_PAGES, PAGE_SIZE = 2 * 1024 * 1024, 4, 200
require = original._require


def validate_request(route, params):
    require(route in ROUTES and isinstance(params, dict), 'REQUEST_INVALID')
    fields = {
        'stock': {'trade_date', 'code', 'page', 'page_size'},
        'flow': {'trade_date', 'symbol', 'page', 'page_size'},
        'sw_overview': {'date', 'page', 'page_size'},
        'sw_members': {'industry_code'},
        'sw_metrics': {'industry_code', 'start_date', 'end_date', 'page', 'page_size'},
        'concept_catalog': set(), 'concept_members': {'board_code'},
        'concept_prices': {'board_code', 'start_date', 'end_date', 'page', 'page_size'},
        'futures_list': set(), 'futures_base': {'symbol', 'trade_date'},
        'futures_prices': {'symbol', 'interval', 'start', 'end', 'limit'},
        'warehouse': {'symbol', 'trade_date', 'page', 'page_size'},
    }
    require(set(params) == fields[route], 'REQUEST_FIELDS_INVALID')
    if route in PAGED:
        require(type(params['page']) is int and 1 <= params['page'] <= MAX_PAGES
                and type(params['page_size']) is int and params['page_size'] == PAGE_SIZE, 'PAGE_BUDGET')
    for key in ('date', 'trade_date', 'start_date', 'end_date'):
        if key in params:
            value = str(params[key])
            require(re.fullmatch(r'[0-9]{8}', value) is not None, 'REQUEST_DATE_INVALID')
            date.fromisoformat(value[:4] + '-' + value[4:6] + '-' + value[6:])
    if 'start_date' in params:
        first = datetime.strptime(str(params['start_date']), '%Y%m%d').date()
        final = datetime.strptime(str(params['end_date']), '%Y%m%d').date()
        require(0 <= (final - first).days <= 40, 'WINDOW_REVERSED_OR_TOO_WIDE')
    if route in {'stock', 'flow'}:
        symbol = params['code' if route == 'stock' else 'symbol']
        require(isinstance(symbol, str) and re.fullmatch(r'(?:6[0-9]{5}\.SH|[03][0-9]{5}\.SZ)', symbol), 'SECURITY_INVALID')
    if 'board_code' in params:
        require(isinstance(params['board_code'], str) and re.fullmatch(r'BK[0-9]{4}', params['board_code']), 'BOARD_INVALID')
    if 'industry_code' in params:
        require(isinstance(params['industry_code'], str) and re.fullmatch(r'[0-9]{6}\.SI', params['industry_code']), 'INDUSTRY_INVALID')
    if route == 'warehouse':
        require(params['symbol'] in {'LC', 'CU', 'RB'}, 'VARIETY_INVALID')
    if route in {'futures_base', 'futures_prices'}:
        require(isinstance(params['symbol'], str) and re.fullmatch(r'(?:LC[0-9]{4}\.GFE|(?:CU|RB)[0-9]{4}\.SHF)', params['symbol']), 'CONTRACT_INVALID')
    if route == 'futures_prices':
        require(params['interval'] == 'daily' and params['limit'] == 64
                and type(params['start']) is int and type(params['end']) is int
                and 0 < params['start'] <= params['end']
                and params['end'] - params['start'] <= 40 * 86400000, 'FUTURES_WINDOW_INVALID')


def request(route, params):
    validate_request(route, params)
    key = os.environ.get('FTSHARE_API_KEY')
    require(isinstance(key, str) and key and key.isascii()
            and all(32 < ord(c) < 127 for c in key), 'AUTHENTICATION_UNAVAILABLE')
    req = Request(BASE + ROUTES[route] + '?' + urlencode(params), headers={
        'FTSHARE_API_KEY': key, 'Accept': 'application/json', 'Accept-Encoding': 'identity',
        'User-Agent': 'decision-kernel/' + VERSION})
    try:
        response = build_opener(original._NoRedirect()).open(req, timeout=20)
    except HTTPError as exc:
        response = exc
    with response:
        require(response.geturl() == req.full_url, 'REDIRECT_REJECTED')
        require(response.headers.get('Content-Encoding', 'identity') == 'identity', 'ENCODING_REJECTED')
        raw = response.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES, 'RESPONSE_TOO_LARGE')
        require(key.encode() not in raw, 'CREDENTIAL_REFLECTION_REJECTED')
        length = response.headers.get('Content-Length')
        require(length is None or length.isdigit() and int(length) == len(raw), 'RESPONSE_LENGTH_MISMATCH')
        return response.status, raw


def unpack(route, obj, page):
    require(isinstance(obj, dict) and type(obj.get('code')) is int, 'ENVELOPE_INVALID')
    require(obj['code'] in {0, 200}, {401: 'AUTHENTICATION_FAILED', 403: 'ENTITLEMENT_DENIED',
            429: 'RATE_LIMITED'}.get(obj['code'], 'PROVIDER_REJECTED'))
    data = obj.get('data')
    if route == 'concept_catalog':
        rows = data
        require(isinstance(rows, list) and len(rows) <= 4096, 'CATALOG_INVALID')
        return rows, len(rows), 1
    require(isinstance(data, dict), 'ENVELOPE_INVALID')
    if route == 'concept_members':
        rows = data.get('constituents')
        require(isinstance(rows, list) and len(rows) <= 4096, 'CONSTITUENTS_INVALID')
        return rows, len(rows), 1
    if route in PAGED:
        # Retain documented items and observed records envelopes separately.
        items = route == 'concept_prices' and 'items' in data and 'records' not in data
        rows, total, pages = (data.get(k) for k in
                             (('items', 'total_items', 'total_pages') if items else ('records', 'total', 'pages')))
        if not items:
            require(data.get('pageNum') == page and data.get('pageSize') == PAGE_SIZE, 'PAGE_IDENTITY')
        require(type(total) is int and type(pages) is int and total >= 0
                and pages in ({0, 1} if total == 0 else {(total + PAGE_SIZE - 1) // PAGE_SIZE}), 'PAGINATION_INVALID')
        require(pages <= MAX_PAGES, 'PAGINATION_BUDGET')
        require(isinstance(rows, list) and len(rows) == min(PAGE_SIZE, max(0, total - (page - 1) * PAGE_SIZE)), 'PAGE_INCOMPLETE')
        return rows, total, pages
    rows = data.get('items')
    require(isinstance(rows, list) and len(rows) <= 4096, 'ROWS_INVALID')
    if route in {'sw_members', 'futures_prices'}:
        require(type(data.get('total')) is int and data['total'] == len(rows), 'HISTORY_INCOMPLETE')
    if route == 'futures_prices':
        require(len(rows) <= 64, 'HISTORY_INCOMPLETE')
    return rows, len(rows), 1


def capture(route, params, output: Path, *, fetch=request, clock=original.now):
    """No automatic retries or fallback. A failed family never returns partial rows."""
    validate_request(route, params)
    require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), 'UNSAFE_OUTPUT')
    output.mkdir(parents=True, exist_ok=False)
    result = {'provider': 'FTSHARE', 'adapter_version': VERSION, 'route': route,
              'endpoint': BASE + ROUTES[route], 'parameters': dict(params), 'requests': [],
              'started_at': clock(), 'status': 'INCOMPLETE', 'rows': [], 'metadata': [],
              'automatic_retry': False, 'qualification': 'CONTEXT_ONLY'}
    last = original._clock(result['started_at'])
    expected, seen, rows = None, set(), []
    try:
        for page in range(1, MAX_PAGES + 1 if route in PAGED else 2):
            query = {**params, **({'page': page} if route in PAGED else {})}
            event = {'parameters': query, 'requested_at': clock(), 'http_status': None, 'status': 'TRANSPORT_FAILURE'}
            result['requests'].append(event)
            require(original._clock(event['requested_at']) >= last, 'CLOCK_REVERSED')
            status, raw = fetch(route, query)
            received = clock()
            require(original._clock(received) >= original._clock(event['requested_at']), 'CLOCK_REVERSED')
            last = original._clock(received)
            require(type(status) is int and isinstance(raw, bytes) and 0 < len(raw) <= MAX_BYTES, 'RESPONSE_INVALID')
            name = f'page-{page}.json'
            (output / name).write_bytes(raw)
            event.update(http_status=status, received_at=received, file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            require(status == 200, {401:'AUTHENTICATION_FAILED',403:'ENTITLEMENT_DENIED',404:'HTTP_NOT_FOUND',
                                   429:'RATE_LIMITED'}.get(status,'HTTP_REJECTED'))
            obj = decode(raw)
            page_rows, total, pages = unpack(route, obj, page)
            require(expected is None or expected == (total, pages), 'PAGINATION_CHANGED')
            expected = total, pages
            data = obj.get('data')
            result['metadata'].append({k:v for k,v in data.items() if k not in {'items','records','constituents'}} if isinstance(data,dict) else {})
            for index, row in enumerate(page_rows):
                require(isinstance(row, dict), 'ROW_INVALID')
                digest = hashlib.sha256(raw_json(row)).hexdigest()
                require(digest not in seen, 'DUPLICATE_ROW')
                seen.add(digest)
                rows.append({'data': row, 'source_file': name, 'source_sha256': event['sha256'],
                             'row_index': index, 'retrieved_at': received})
            event['status'] = 'RAW_CAPTURED'
            if page >= pages:
                require(len(rows) == total, 'PAGE_INCOMPLETE')
                result.update(status='COMPLETE' if rows else 'EMPTY', rows=rows)
                break
    except original.DiscoveryError as exc:
        result['status'] = str(exc)
    except (URLError, OSError, TimeoutError):
        result['status'] = 'TRANSPORT_FAILURE'
    except (ValueError, TypeError, KeyError, OverflowError):
        result['status'] = 'PARSE_FAILURE'
    result['finished_at'] = clock()
    require(original._clock(result['finished_at']) >= last, 'CLOCK_REVERSED')
    (output / 'capture.json').write_bytes(raw_json(result))
    return result
