"""Finite public B1 captures; dates/units/raw bytes, never Research or trading.

The source-only seam deliberately does not alter the existing Relay or publisher.
One selected family, no credentials, redirects, retries, or fallback sources.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import ProxyHandler, Request, build_opener
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from ..identity import canonical_hash
from .smart_money_sources import clock, decode, encoded, now, require
from .economic_source_capture import (
    PublicResponse, _NoRedirect, _safe_headers, _body_integrity, MAX_BODY_BYTES,
)

LEGACY_VERSION = 'global-public-context-v1'
VERSION = 'global-public-context-v2'
REPOSITORY = 'auguspp/decision-kernel'
WORKFLOW = '.github/workflows/radar-global-public.yml'
FAMILIES = {'treasury': '美国国债期限利率', 'fx': 'ECB 外汇参考价',
            'commodities': '黄金与原油 · 供应商期货日线', 'crypto': 'Coinbase BTC / ETH 日线'}
TENORS = ('1MONTH', '3MONTH', '6MONTH', '1YEAR', '2YEAR', '5YEAR', '10YEAR', '30YEAR')
CURRENCIES = ('USD', 'CNY', 'JPY', 'GBP')
FUTURES = {'GC=F': ('黄金', 'USD_PER_TROY_OUNCE'), 'CL=F': ('WTI原油', 'USD_PER_BARREL'),
           'BZ=F': ('Brent原油', 'USD_PER_BARREL')}
COINS = ('BTC-USD', 'ETH-USD')
AUTHORITY = {'qualification': 'MARKET_CONTEXT_ONLY', 'research_authority': 'NONE',
             'investment_authority': 'NONE', 'human_attention_authority': 'NONE',
             'signal_transition_authority': 'NONE', 'automatic_admission': False,
             'company_mapping': 'NOT_PERFORMED', 'odds_recomputed': False}
ATOM = '{http://www.w3.org/2005/Atom}'
DATA = '{http://schemas.microsoft.com/ado/2007/08/dataservices}'
META = '{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}'
ECB = '{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}'
GEST = '{http://www.gesmes.org/xml/2002-08-01}'


def day(value):
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'GP_DATE')
    return date.fromisoformat(value)


def date_policy(family, started):
    """A request-date ceiling, not proof of publication or a trading calendar.

    Treasury usually publishes by 18:00 Eastern; ECB usually around 16:00 CET.
    The ECB 17:00 local gate is our conservative buffer, not a source timestamp.
    Completed UTC candles and unqualified futures never inherit reference rules.
    """
    require(family in FAMILIES, 'GP_FAMILY')
    instant = clock(started)
    references = {'treasury': ('America/New_York', 18), 'fx': ('Europe/Berlin', 17)}
    if family in references:
        zone, hour = references[family]
        local = instant.astimezone(ZoneInfo(zone))
        ceiling = local.date() - timedelta(days=int(local.hour < hour))
        rule = 'DATED_REFERENCE_RELEASE_OPPORTUNITY_V1'
        not_before = f'{hour:02d}:00'
    else:
        zone, not_before = 'UTC', None
        ceiling = instant.date() - timedelta(days=1)
        rule = ('COMPLETED_UTC_DAY_ONLY' if family == 'crypto'
                else 'PRIOR_UTC_DATE_ONLY_FUTURES_FINALITY_UNKNOWN')
    return {'rule': rule, 'timezone': zone, 'not_before_local': not_before,
            'max_as_of_date': ceiling.isoformat(),
            'meaning': 'REQUEST_CEILING_NOT_ACTUAL_PUBLICATION_OR_SESSION_PROOF'}


def _qualify_date(version, family, as_of, started, policy=None):
    first, end = clock(started), day(as_of)
    require(first.date() - timedelta(days=31) <= end, 'GP_RECENT_DATE')
    if version == LEGACY_VERSION:
        require(policy is None and end < first.date(), 'GP_RECENT_DATE')
    else:
        require(version == VERSION, 'GP_CAPTURE_VERSION')
        require(policy == date_policy(family, started), 'GP_DATE_POLICY')
        require(end <= day(policy['max_as_of_date']), 'GP_RECENT_DATE')


def number(value, *, positive=False):
    require(isinstance(value, (str, int, Decimal)) and not isinstance(value, bool)
            and len(str(value)) <= 60, 'GP_NUMBER')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('GP_NUMBER') from exc
    require(result.is_finite() and abs(result) < Decimal('1e12')
            and (not positive or result > 0), 'GP_NUMBER')
    return result


def textnum(value):
    return None if value is None else format(value, 'f')


def identity(env):
    item = {'repository': env.get('GITHUB_REPOSITORY'), 'workflow': WORKFLOW,
            'code_commit': env.get('GITHUB_SHA'), 'ref': env.get('GITHUB_REF'),
            'event': env.get('GITHUB_EVENT_NAME'), 'run_id': int(env.get('GITHUB_RUN_ID', '0')),
            'attempt': int(env.get('GITHUB_RUN_ATTEMPT', '0'))}
    validate_identity(item)
    return item


def validate_identity(item):
    require(isinstance(item, dict) and set(item) == {
        'repository', 'workflow', 'code_commit', 'ref', 'event', 'run_id', 'attempt'}, 'GP_IDENTITY')
    require(item['repository'] == REPOSITORY and item['workflow'] == WORKFLOW
            and item['ref'] == 'refs/heads/main' and item['event'] in {'workflow_dispatch', 'schedule'}
            and type(item['run_id']) is int and item['run_id'] > 0
            and type(item['attempt']) is int and item['attempt'] == 1
            and isinstance(item['code_commit'], str)
            and re.fullmatch('[a-f0-9]{40}', item['code_commit']), 'GP_IDENTITY_SCOPE')


def plan(family, as_of):
    require(family in FAMILIES, 'GP_FAMILY')
    end = day(as_of); begin = end - timedelta(days=13)
    def spec(label, host, path, params=None):
        url = 'https://' + host + path
        if params: url += '?' + urlencode(params)
        return {'family': family, 'as_of_date': as_of, 'begin': begin.isoformat(),
                'id': label, 'host': host, 'url': url}
    if family == 'treasury':
        months = sorted({begin.strftime('%Y%m'), end.strftime('%Y%m')})
        return [spec(m, 'home.treasury.gov', '/resource-center/data-chart-center/interest-rates/pages/xml',
                     {'data': 'daily_treasury_yield_curve', 'field_tdr_date_value_month': m}) for m in months]
    if family == 'fx':
        return [spec('EUR', 'www.ecb.europa.eu', '/stats/eurofxref/eurofxref-hist-90d.xml')]
    if family == 'crypto':
        return [spec(c, 'api.exchange.coinbase.com', '/products/' + c + '/candles',
                     {'granularity': 86400, 'start': begin.isoformat() + 'T00:00:00Z',
                      'end': (end + timedelta(days=1)).isoformat() + 'T00:00:00Z'}) for c in COINS]
    def epoch(d): return int(datetime.combine(d, datetime.min.time(), timezone.utc).timestamp())
    return [spec(c, 'query1.finance.yahoo.com', '/v8/finance/chart/' + quote(c, safe=''),
                 {'period1': epoch(begin - timedelta(days=1)), 'period2': epoch(end + timedelta(days=2)),
                  'interval': '1d', 'includePrePost': 'false'}) for c in FUTURES]


class PublicReadError(ValueError):
    def __init__(self, status):
        self.http_status = status if type(status) is int and 100 <= status <= 599 else None
        super().__init__('GP_RESPONSE_BODY_UNAVAILABLE')


def safe_headers(value):
    result = _safe_headers(value)
    retry = [v for k, v in value.items() if k.lower() == 'retry-after']
    require(len(retry) <= 1, 'GP_HEADERS')
    if retry:
        require(isinstance(retry[0], str) and len(retry[0]) <= 2048
                and '\r' not in retry[0] and '\n' not in retry[0], 'GP_HEADERS')
        result['retry-after'] = retry[0]
    return result


def fetch(spec):
    """Reuse the original public-HTTP safeguards; fixed plan only, single GET."""
    require(spec in plan(spec['family'], spec['as_of_date']), 'GP_DESTINATION')
    request = Request(spec['url'], headers={'User-Agent': 'DecisionKernel-PublicContext/1',
                      'Accept': 'application/json,application/xml,text/xml', 'Accept-Encoding': 'identity'})
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    try:
        response = opener.open(request, timeout=25)
    except HTTPError as exc:
        response = exc  # Retain bounded original HTTP failure bytes, never follow it.
    with response:
        require(response.geturl() == spec['url'], 'GP_DESTINATION_CHANGED')
        try:
            headers = safe_headers(dict(response.headers.items()))
            require(headers.get('content-encoding', 'identity').lower() in {'', 'identity'}, 'GP_ENCODING')
            raw = response.read(MAX_BODY_BYTES + 1)
            _body_integrity(raw, headers)
        except Exception:
            raise PublicReadError(response.status) from None
        return PublicResponse(response.geturl(), response.status, headers, raw)


def xml(raw):
    # UTF-8-only feed; no DTD/entity loading or parser/network side effects.
    text = raw.decode('utf-8-sig')
    require('<!DOCTYPE' not in text.upper() and '<!ENTITY' not in text.upper(), 'GP_XML_ENTITIES')
    return ET.fromstring(text)


def parse(raw, spec):
    """Return dated source tables. Raw out-of-window rows remain retained, not used."""
    family = spec['family']; rows = []; metadata = {}
    if family == 'treasury':
        root = xml(raw); require(root.tag == ATOM + 'feed', 'GP_TREASURY_ENVELOPE')
        entries = root.findall(ATOM + 'entry'); require(len(entries) <= 31, 'GP_ROW_BOUND')
        for entry in entries:
            props = entry.find('.//' + META + 'properties'); require(props is not None, 'GP_TREASURY_FIELDS')
            require(len({p.tag for p in props}) == len(props), 'GP_DUPLICATE_FIELD')
            fields = {p.tag: p for p in props}
            date_node = fields[DATA + 'NEW_DATE']; value = date_node.text
            require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T00:00:00', value), 'GP_SOURCE_DATE')
            dt = value[:10]; require(day(dt).strftime('%Y%m') == spec['id'], 'GP_MONTH_SCOPE')
            values = {}
            for tenor in TENORS:
                node = fields.get(DATA + 'BC_' + tenor)
                missing = node is None or node.get(META + 'null') == 'true' or not node.text
                v = None if missing else number(node.text)
                require(v is None or abs(v) < 1000, 'GP_RATE_UNIT')
                values['UST:' + tenor] = v
            rows.append((dt, values))
    elif family == 'fx':
        root = xml(raw); require(root.tag == GEST + 'Envelope', 'GP_ECB_ENVELOPE')
        groups = root.findall('./' + ECB + 'Cube/' + ECB + 'Cube')
        require(len(groups) <= 100, 'GP_ROW_BOUND')
        for group in groups:
            dt = group.attrib['time']; day(dt)
            currencies = [v.attrib['currency'] for v in group]
            require(len(currencies) == len(set(currencies)) and len(currencies) <= 64, 'GP_CURRENCY_DUPLICATE')
            values = {v.attrib['currency']: number(v.attrib['rate'], positive=True) for v in group}
            rows.append((dt, {'EUR/' + c: values.get(c) for c in CURRENCIES}))
        metadata = {'base_currency': 'EUR', 'rate_kind': 'ECB_INFORMATION_REFERENCE_NOT_TRANSACTION_QUOTE'}
    elif family == 'crypto':
        body = decode(raw); require(isinstance(body, list) and len(body) <= 300, 'GP_CANDLES')
        for row in body:
            require(isinstance(row, list) and len(row) == 6 and type(row[0]) is int
                    and row[0] > 0 and row[0] % 86400 == 0, 'GP_CANDLE_SHAPE')
            low, high, opening, close, volume = [number(v) for v in row[1:]]
            require(0 < low <= opening <= high and low <= close <= high and volume >= 0, 'GP_OHLC')
            dt = datetime.fromtimestamp(row[0], timezone.utc).date().isoformat()
            rows.append((dt, {spec['id']: close}))
        metadata = {'venue': 'COINBASE_EXCHANGE', 'time_basis': 'UTC_DAILY_BUCKET',
                    'identity_basis': 'EXACT_REQUEST_PRODUCT_NOT_RESPONSE_ECHO', 'missing_buckets_filled': False}
    else:
        body = decode(raw); chart = body['chart']; require(chart['error'] is None, 'GP_YAHOO_ERROR')
        require(isinstance(chart['result'], list) and len(chart['result']) == 1, 'GP_YAHOO_ENVELOPE')
        result = chart['result'][0]; metadata = result['meta']
        require(metadata['symbol'] == spec['id'] and metadata['currency'] == 'USD'
                and metadata['instrumentType'] == 'FUTURE' and metadata.get('dataGranularity') == '1d', 'GP_FUTURE_IDENTITY')
        zone = ZoneInfo(metadata['exchangeTimezoneName'])
        stamps = result.get('timestamp', []); quotes = result['indicators']['quote']
        require(isinstance(stamps, list) and len(stamps) <= 32 and len(quotes) == 1, 'GP_YAHOO_SHAPE')
        closes = quotes[0]['close']; require(isinstance(closes, list) and len(stamps) == len(closes), 'GP_YAHOO_SHAPE')
        for stamp, close in zip(stamps, closes, strict=True):
            require(type(stamp) is int and stamp > 0, 'GP_CANDLE_TIME')
            dt = datetime.fromtimestamp(stamp, zone).date().isoformat()
            rows.append((dt, {spec['id']: None if close is None else number(close, positive=spec['id'] == 'GC=F')}))
    require(len({dt for dt, _ in rows}) == len(rows), 'GP_DUPLICATE_DATE')
    selected = [(dt, values) for dt, values in rows if spec['begin'] <= dt <= spec['as_of_date']]
    for dt, _ in rows: day(dt)
    selected.sort(key=lambda row: row[0])
    return selected, len(rows), metadata


def series_info(family):
    if family == 'treasury': return {f'UST:{t}': ('美国国债 ' + t, 'ANNUAL_PERCENT', 'bp') for t in TENORS}
    if family == 'fx': return {'EUR/' + c: ('1欧元兑' + c, c + '_PER_EUR', '%') for c in CURRENCIES}
    if family == 'crypto': return {c: (c, 'USD_PER_' + c.split('-')[0], '%') for c in COINS}
    return {c: (v[0] + ' · ' + c, v[1], None) for c, v in FUTURES.items()}


def summarize(tables, family, as_of):
    observations = []
    for symbol, (name, unit, change_unit) in series_info(family).items():
        history = sorted([(dt, row[symbol]) for dt, row in tables if symbol in row])
        require(len({dt for dt, _ in history}) == len(history), 'GP_OVERLAPPING_TABLES')
        latest = history[-1] if history else None; previous = history[-2] if len(history) > 1 else None
        value = latest[1] if latest else None; prior = previous[1] if previous else None
        change = None
        with localcontext() as ctx:
            ctx.prec = 36
            if value is not None and prior is not None:
                if change_unit == 'bp': change = (value - prior) * 100
                elif change_unit == '%' and prior > 0: change = ((value / prior - 1) * 100).quantize(Decimal('0.000001'))
        observations.append({'symbol': symbol, 'name': name, 'unit': unit, 'value': textnum(value),
            'source_date': latest[0] if latest else None, 'previous_date': previous[0] if previous else None,
            'previous_value': textnum(prior), 'change': textnum(change), 'change_unit': change_unit,
            'calendar_age_at_requested_end': (day(as_of) - day(latest[0])).days if latest else None,
            'change_scope': ('NOT_COMPUTED_CONTRACT_ROLL_IDENTITY_UNKNOWN' if family == 'commodities'
                             else 'TWO_RETURNED_DATES_NOT_ASSERTED_CONSECUTIVE_SESSIONS'),
            'price_kind': ('VENDOR_FUTURE_DAILY_CLOSE_NOT_SPOT_OR_SETTLEMENT' if family == 'commodities'
                           else 'DATED_SOURCE_OBSERVATION'),
            'publication_time': None, 'market_status': 'UNKNOWN_NOT_INFERRED'})
    return observations


def seal(manifest):
    return canonical_hash({k: v for k, v in manifest.items() if k != 'capture_hash'})


def replay(files, expected_identity, cutoff):
    """Trusted installed code only; no HTTP, saved code, or external XML resolution."""
    validate_identity(expected_identity)
    require(len(files) <= 6 and sum(map(len, files.values())) <= 7 * MAX_BODY_BYTES, 'GP_ARCHIVE_BOUND')
    cap = decode(files['capture.json'])
    require(cap['version'] in {LEGACY_VERSION, VERSION} and cap['identity'] == expected_identity
            and cap['authority'] == AUTHORITY and cap['capture_hash'] == seal(cap), 'GP_CAPTURE_IDENTITY')
    first, finish = clock(cap['started_at']), clock(cap['finished_at'])
    require(first <= finish <= clock(cutoff), 'GP_CAPTURE_TIME')
    require(cap['version'] != LEGACY_VERSION or 'date_policy' not in cap, 'GP_LEGACY_DATE_POLICY')
    _qualify_date(cap['version'], cap['family'], cap['as_of_date'], cap['started_at'], cap.get('date_policy'))
    specs = plan(cap['family'], cap['as_of_date'])
    require(type(cap['execution_complete']) is bool and len(cap['records']) == len(specs), 'GP_PLAN')
    used = {'capture.json'}; tables = []; outcomes = []; stopped = False
    fields = {'index', 'spec', 'state', 'http_status', 'requested_at', 'received_at', 'headers',
              'body', 'bytes', 'sha256', 'error_type'}
    for index, (spec, record) in enumerate(zip(specs, cap['records'], strict=True)):
        require(set(record) == fields and record['index'] == index and record['spec'] == spec, 'GP_RECORD_SCOPE')
        state = record['state']; raw = None; status = record['http_status']
        if state in {'NOT_ATTEMPTED', 'NOT_ATTEMPTED_SERVICE_STOP'}:
            require(all(record[k] is None for k in ('requested_at', 'received_at', 'body', 'bytes', 'sha256', 'http_status', 'error_type'))
                    and record['headers'] == {} and (state != 'NOT_ATTEMPTED_SERVICE_STOP' or stopped), 'GP_NOT_ATTEMPTED')
            require(not cap['execution_complete'] or state != 'NOT_ATTEMPTED', 'GP_FALSE_COMPLETE')
        else:
            require(not stopped and state in {'REQUEST_IN_PROGRESS', 'HTTP_RESPONSE', 'TRANSPORT_UNAVAILABLE'}, 'GP_REQUEST_STATE')
            require(first <= clock(record['requested_at']) <= finish, 'GP_REQUEST_TIME')
            if state == 'REQUEST_IN_PROGRESS':
                require(not cap['execution_complete'] and record['received_at'] is None and status is None
                        and record['body'] is None and record['bytes'] is None and record['sha256'] is None
                        and record['headers'] == {} and record['error_type'] is None, 'GP_IN_PROGRESS')
            else:
                require(clock(record['requested_at']) <= clock(record['received_at']) <= finish, 'GP_RESPONSE_TIME')
                require(safe_headers(record['headers']) == record['headers'], 'GP_HEADERS')
                if state == 'HTTP_RESPONSE':
                    require(type(status) is int and 100 <= status <= 599 and record['body'] == f'raw-{index:02d}.bin'
                            and record['error_type'] is None, 'GP_RESPONSE')
                    raw = files[record['body']]; _body_integrity(raw, record['headers'])
                    require(record['headers'].get('content-encoding', 'identity').lower() in {'', 'identity'}
                            and len(raw) == record['bytes'] and sha256(raw).hexdigest() == record['sha256'], 'GP_RAW_IDENTITY')
                    used.add(record['body'])
                else:
                    require(record['body'] is None and record['bytes'] is None and record['sha256'] is None
                            and (status is None or type(status) is int and 100 <= status <= 599)
                            and isinstance(record['error_type'], str)
                            and re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,79}', record['error_type']), 'GP_TRANSPORT')
        stopped = stopped or status in (401, 403, 429) or state == 'TRANSPORT_UNAVAILABLE'
        outcome = {'id': spec['id'], 'request_state': state, 'http_status': status,
                   'status': state, 'source_url': spec['url'], 'source_rows': None, 'selected_rows': 0}
        if raw is not None and status == 200:
            try:
                rows, count, meta = parse(raw, spec)
                outcome.update(status='ROWS_NORMALIZED' if rows else 'EMPTY_WINDOW_NOT_NO_CHANGE',
                               source_rows=count, selected_rows=len(rows), metadata=meta)
                tables.extend(rows)
            except (ValueError, TypeError, KeyError, IndexError, ArithmeticError, ET.ParseError, OSError):
                outcome['status'] = 'SOURCE_TABLE_UNCONFIRMED'
        elif status is not None:
            outcome['status'] = ('RESPONSE_UNAVAILABLE_HTTP_' if state == 'TRANSPORT_UNAVAILABLE' else 'HTTP_') + str(status)
        outcomes.append(outcome)
    require(set(files) <= used | {'summary.json', 'summary.md'}, 'GP_EXTRA_FILES')
    values = summarize(tables, cap['family'], cap['as_of_date'])
    available = sum(v['value'] is not None for v in values)
    complete = cap['execution_complete'] and available == len(values) and all(o['status'] == 'ROWS_NORMALIZED' for o in outcomes)
    report = {'version': cap['version'], 'identity': deepcopy(expected_identity), 'family': cap['family'],
              'as_of_date': cap['as_of_date'], 'captured_from': cap['started_at'], 'captured_through': cap['finished_at'],
              'capture_hash': cap['capture_hash'], 'outcomes': outcomes, 'observations': values,
              'available_values': available, 'status': 'AVAILABLE' if complete else 'PARTIAL' if available else 'UNAVAILABLE',
              'source_calls_during_replay': 0, 'authority': deepcopy(AUTHORITY),
              'coverage': 'SELECTED_SOURCE_DATES_NOT_FULL_GLOBAL_MARKETS',
              'vintage': 'CURRENT_RETRIEVAL_OF_DATED_ROWS_NOT_HISTORICAL_AS_KNOWN_VINTAGE'}
    if cap['version'] == VERSION:
        report['date_policy'] = deepcopy(cap['date_policy'])
    if 'summary.json' in files: require(files['summary.json'] == encoded(report), 'GP_SAVED_SUMMARY_DIFFERS')
    if 'summary.md' in files: require(files['summary.md'] == render(report).encode(), 'GP_SAVED_RENDER_DIFFERS')
    return report


def render(report):
    lines = ['# ' + FAMILIES[report['family']], '',
             '来源观察，不是研究解释、实时交易报价或投资信号。',
             '窗口截止：' + report['as_of_date'] + '；抓取截止：' + report['captured_through'],
             '状态：' + report['status'] + '；来源日期不替代抓取/发布时间。', '',
             '| 对象 | 来源日期 | 数值 | 单位 | 上一返回日期 | 变化 |', '|---|---|---|---|---|---|']
    for row in report['observations']:
        change = (row['change'] + ' ' + row['change_unit']) if row['change'] is not None else 'UNKNOWN'
        lines.append('| ' + ' | '.join(str(v) if v is not None else 'UNKNOWN' for v in
                     (row['name'], row['source_date'], row['value'], row['unit'], row['previous_date'], change)) + ' |')
    lines += ['', '变化只比较两个实际返回日期，不猜相邻交易日。失败/空值不是市场无变化。',
              '美债为年化par yield而非债券回报；ECB为每欧元信息参考价；Coinbase仅代表该场所。',
              'Yahoo =F 是供应商期货序列，不冒充现货/结算价；换月连续性未建立，不计算跨日收益。',
              '原件为本次取得版本，不冒充历史当时可知；市场开闭状态和原发布时间保持UNKNOWN。', '', '## 来源请求']
    lines += ['- ' + o['id'] + '：' + o['status'] for o in report['outcomes']]
    if report['version'] == VERSION:
        policy = report['date_policy']
        lines += ['', '## 日期资格（不是实际发布时间）',
                  '规则：' + policy['rule'] + '；时区：' + policy['timezone'],
                  '原采集开始时可请求日期上限：' + policy['max_as_of_date'],
                  '参考值机会门槛（来源当地）：' + (policy['not_before_local'] or '不适用'),
                  '到达机会时钟不证明资料已发布；只展示实际返回日期，未返回不补值。',
                  '参考利率/汇率不是全天价格线；期货终局性未知，UTC日桶未结束不得提前使用。']
    return '\n'.join(lines) + '\n'


def capture(output, run_identity, family, as_of=None, *, request=fetch, time=now):
    validate_identity(run_identity); started = time()
    policy = date_policy(family, started)
    as_of = policy['max_as_of_date'] if as_of is None else as_of
    _qualify_date(VERSION, family, as_of, started, policy)
    specs = plan(family, as_of)
    output = Path(output)
    require(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)), 'GP_OUTPUT')
    output.mkdir(parents=True)
    cap = {'version': VERSION, 'identity': deepcopy(run_identity), 'family': family, 'as_of_date': as_of,
           'date_policy': policy,
           'started_at': started, 'finished_at': started, 'execution_complete': False, 'authority': deepcopy(AUTHORITY),
           'records': [{'index': i, 'spec': spec, 'state': 'NOT_ATTEMPTED', 'http_status': None,
                        'requested_at': None, 'received_at': None, 'headers': {}, 'body': None,
                        'bytes': None, 'sha256': None, 'error_type': None} for i, spec in enumerate(specs)]}
    def checkpoint():
        cap['finished_at'] = time(); cap['capture_hash'] = seal(cap)
        temp = output / '.capture.tmp'; temp.write_bytes(encoded(cap)); temp.replace(output / 'capture.json')
    checkpoint(); stopped = False
    for record in cap['records']:
        if stopped:
            record['state'] = 'NOT_ATTEMPTED_SERVICE_STOP'; checkpoint(); continue
        record.update(state='REQUEST_IN_PROGRESS', requested_at=time()); checkpoint()
        try:
            result = request(deepcopy(record['spec']))
            require(result.url == record['spec']['url'] and type(result.status) is int
                    and 100 <= result.status <= 599, 'GP_HTTP_RECEIPT')
            headers = safe_headers(result.headers); _body_integrity(result.body, headers)
            require(headers.get('content-encoding', 'identity').lower() in {'', 'identity'}, 'GP_ENCODING')
            path = f"raw-{record['index']:02d}.bin"; (output / path).write_bytes(result.body)
            record.update(state='HTTP_RESPONSE', http_status=result.status, headers=headers, body=path,
                          bytes=len(result.body), sha256=sha256(result.body).hexdigest())
        except Exception as exc:  # Only exception type; never response text or environment.
            record.update(state='TRANSPORT_UNAVAILABLE', error_type=type(exc).__name__)
            status = getattr(exc, 'http_status', None)
            if type(status) is int and 100 <= status <= 599: record['http_status'] = status
        record['received_at'] = time(); stopped = record['http_status'] in (401, 403, 429) or record['state'] == 'TRANSPORT_UNAVAILABLE'; checkpoint()
    cap['execution_complete'] = True; checkpoint()
    report = replay({p.name: p.read_bytes() for p in output.iterdir()}, run_identity, time())
    (output / 'summary.json').write_bytes(encoded(report)); (output / 'summary.md').write_bytes(render(report).encode())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', required=True, choices=FAMILIES)
    parser.add_argument('--as-of', default=None)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    # Select once at the actual capture start, not at an earlier CLI wall clock.
    result = capture(args.output, identity(os.environ), args.family, args.as_of)
    print(encoded({k: result[k] for k in ('family', 'status', 'available_values', 'capture_hash')}).decode())
    return 0 if result['available_values'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
