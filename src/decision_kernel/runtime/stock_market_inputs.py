"""Current-session stock inputs through the existing Relay, not a frozen pilot.

Reuse the admitted transport/retry/secret owner. One calendar plus four dated
cross sections (prices and factors): no Sector dependency, ticker whitelist,
second-provider equality gate, or requirement for unconsumed intermediate bars.
"""
from __future__ import annotations

import argparse
from functools import partial
import time as elapsed_time
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

VERSION = 'current-stock-market-inputs-v1'
WORKFLOW = '.github/workflows/stock-reading-after-sector.yml'
TITLE = 'stock-market-inputs'
SOURCE = 'THIRD_PARTY_TUSHARE_RELAY'
ZONE = ZoneInfo('Asia/Shanghai')
WINDOWS = (5, 20, 60)
LIMIT = 6000
MAX_CALLS, MAX_BODY, MAX_TOTAL = 9, 4 * 1024 * 1024, 16 * 1024 * 1024
MAX_REPORT = 512 * 1024
COLUMNS = ['symbol', 'raw_close', 'change_5', 'change_20', 'change_60', 'status_5', 'status_20', 'status_60']
STATUS = {'0': 'COMPARABLE', '1': 'CALENDAR_WINDOW_UNAVAILABLE', '2': 'PRICE_ENDPOINT_UNAVAILABLE',
          '3': 'FACTOR_ENDPOINT_UNAVAILABLE', '4': 'ENDPOINT_VALUE_INVALID'}
STOP = {'AUTH_OR_ENTITLEMENT', 'RATE_LIMIT', 'CREDENTIAL_UNAVAILABLE', 'CREDENTIAL_REFLECTION'}
CODE = re.compile(r'[0-9]{6}\.(SH|SZ|BJ)\Z')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def dumps(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def loads(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY, 'BODY_SIZE')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique, parse_float=Decimal,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def day(text):
    require(isinstance(text, str) and re.fullmatch('[0-9]{8}', text) is not None, 'DATE_IDENTITY')
    value = date.fromisoformat(text)
    require(value.strftime('%Y%m%d') == text, 'DATE_IDENTITY')
    return value


def number(value):
    require(type(value) in (str, int, Decimal), 'NUMBER_TYPE')
    result = Decimal(value)
    require(result.is_finite() and result > 0 and len(result.as_tuple().digits) <= 28
            and abs(result.as_tuple().exponent) <= 12, 'NUMBER_RANGE')
    return result


def table(raw, api, required):
    body = loads(raw)
    require(isinstance(body, dict) and type(body.get('code')) is int and body['code'] == 0
            and body.get('ok') is not False and body.get('error') in (None, ''), 'BUSINESS_STATUS')
    require(body.get('api_name', api) == api, 'API_IDENTITY')
    data = body['data']; fields, items = data['fields'], data['items']
    require(isinstance(fields, list) and all(isinstance(x, str) for x in fields)
            and len(fields) == len(set(fields)) <= 512 and set(required) <= set(fields), 'FIELDS')
    require(isinstance(items, list) and len(items) <= 10000, 'ROWS')
    require(all(isinstance(row, list) and len(row) == len(fields) for row in items), 'ROW_SHAPE')
    incomplete = len(items) >= LIMIT
    for obj in (body, data):
        for key in ('count', 'total'):
            if key in obj:
                require(type(obj[key]) is int and obj[key] >= len(items), 'COUNT_CONFLICT')
                incomplete |= obj[key] > len(items)
        incomplete |= any(obj.get(k) not in (None, False, '') for k in
                          ('has_more', 'has_next', 'truncated', 'next', 'next_page', 'next_cursor'))
    return [dict(zip(fields, row)) for row in items], bool(incomplete)


def calendar_plan(observed_at):
    require(observed_at.tzinfo is not None and observed_at.utcoffset() is not None, 'CLOCK_ZONE')
    today = observed_at.astimezone(ZONE).date()
    return {'api': 'trade_cal', 'params': {'exchange': 'SSE',
        'start_date': (today - timedelta(days=200)).strftime('%Y%m%d'), 'end_date': today.strftime('%Y%m%d'),
        'fields': 'exchange,cal_date,is_open', 'limit': '1000'}}


def calendar(raw, observed_at):
    query = calendar_plan(observed_at)['params']; start, finish = day(query['start_date']), day(query['end_date'])
    rows, incomplete = table(raw, 'trade_cal', ('exchange', 'cal_date', 'is_open'))
    require(not incomplete, 'CALENDAR_TRUNCATED')
    values = {}
    for row in rows:
        d = day(row['cal_date'])
        require(row['exchange'] == 'SSE' and start <= d <= finish and d not in values
                and type(row['is_open']) in (str, int) and str(row['is_open']) in ('0', '1'), 'CALENDAR_IDENTITY')
        values[d] = str(row['is_open']) == '1'
    local = observed_at.astimezone(ZONE)
    cutoff = finish if local.time() >= time(15, 30) else finish - timedelta(days=1)
    sessions = sorted(d for d, opened in values.items() if opened and d <= cutoff)
    require(sessions, 'NO_COMPLETED_SESSION')
    end = sessions[-1]
    require(all(end + timedelta(days=i) in values for i in range((finish - end).days + 1)),
            'LATEST_SESSION_CALENDAR_UNCERTAIN')
    windows = {}
    for n in WINDOWS:
        base = sessions[-n-1] if len(sessions) > n else None
        if base is not None and not all(base + timedelta(days=i) in values for i in range((end-base).days+1)):
            base = None
        windows[str(n)] = base.strftime('%Y%m%d') if base else None
    return {'market_session': end.isoformat(), 'end_date': end.strftime('%Y%m%d'), 'bases': windows,
            'calendar_source': SOURCE, 'calendar_exchange': 'SSE',
            'session_basis': 'PROVIDER_DATED_CALENDAR_WITH_COMPLETION_CUTOFF_NOT_PIT'}


def price_plan(context, *, daily_fields="close"):
    require(daily_fields in ("close", "close,open"), "DAILY_FIELD_SCOPE")
    dates = list(dict.fromkeys([context['end_date']] + [context['bases'][str(n)] for n in WINDOWS
                                                       if context['bases'][str(n)] is not None]))
    return [{'api': api, 'params': {'trade_date': d, 'fields': 'ts_code,trade_date,' + field, 'limit': str(LIMIT)}}
            for d in dates for api, field in (('daily', daily_fields), ('adj_factor', 'adj_factor'))]


def keyed(raw, item):
    rows, incomplete = table(raw, item['api'], ('ts_code', 'trade_date',
                                              'close' if item['api'] == 'daily' else 'adj_factor'))
    result, rejected, duplicate = {}, [], set()
    for position, row in enumerate(rows):
        symbol = row['ts_code']
        if not isinstance(symbol, str) or CODE.fullmatch(symbol) is None or row['trade_date'] != item['params']['trade_date']:
            rejected.append(position); continue
        if symbol in result or symbol in duplicate:
            duplicate.add(symbol); result.pop(symbol, None); rejected.append(position); continue
        result[symbol] = row
    return result, {'returned_rows': len(rows), 'rejected_row_positions': rejected,
                    'duplicate_symbols': sorted(duplicate), 'possibly_truncated': incomplete}


def evaluate(context, tables, coverage):
    end = context['end_date']; latest = tables.get(('daily', end), {})
    # Conflicting end quotes invalidate that price, not the security's place in
    # the denominator. The original duplicate rows stay in the source archive.
    symbols = set(latest) | set(coverage.get('daily:' + end, {}).get('duplicate_symbols', []))
    output = []
    with localcontext() as ctx:
        ctx.prec = 40
        for symbol in sorted(symbols):
            close = latest.get(symbol, {}).get('close'); values, states = [], []
            try:
                # Equal prices must not exhaust the table budget solely because
                # a provider emits trailing zeros; exact lexemes remain in raw/.
                close = format(number(close).normalize(), 'f')
            except (ValueError, InvalidOperation):
                close = None
            for n in WINDOWS:
                base = context['bases'][str(n)]; value, state = None, 0
                if base is None:
                    state = 1
                elif close is None:
                    state = 4
                elif symbol not in tables.get(('daily', base), {}):
                    state = 2
                elif any(symbol not in tables.get(('adj_factor', d), {}) for d in (base, end)):
                    state = 3
                else:
                    try:
                        p = number(tables['daily', base][symbol]['close']); q = number(close)
                        a = number(tables['adj_factor', base][symbol]['adj_factor'])
                        b = number(tables['adj_factor', end][symbol]['adj_factor'])
                        value = format(q*b/(p*a)-1, '.12f')
                    except (ValueError, InvalidOperation, OverflowError):
                        state = 4
                values.append(value); states.append(state)
            output.append([symbol, close, *values, *states])
    counts = {str(n): sum(r[5+i] == 0 for r in output) for i, n in enumerate(WINDOWS)}
    return {'version': VERSION, 'source': SOURCE, **context, 'columns': COLUMNS, 'rows': output,
        'status_codes': STATUS, 'qualified_windows': counts, 'cohort_denominator': len(output),
        'source_row_coverage': coverage,
        'universe': 'ALL_VALID_IDENTITIES_RETURNED_FOR_END_SESSION_NOT_ALL_LISTED_SECURITIES',
        'status': 'PRICE_INPUTS_AVAILABLE_WITH_GAPS' if output else 'PRICE_INPUT_UNAVAILABLE_NOT_QUIET',
        'formula': 'end_close * end_factor / (base_close * base_factor) - 1',
        'fraction_rounding_decimal_places': 12, 'comparison_basis': 'PROVIDER_ADJUSTED_PRICE_NOT_TOTAL_RETURN',
        'continuous_path': 'NOT_REQUESTED_NOT_REQUIRED_FOR_INTERVAL', 'company_action_details': 'NOT_OBTAINED',
        'missing_history_reason': 'UNKNOWN_NOT_INFERRED_AS_NEW_LISTING_OR_SUSPENSION',
        'pit_knowledge': 'NOT_ESTABLISHED', 'automatic_research_routing': False, 'investment_authority': 'NONE'}


def build(receipt, bodies):
    require(receipt.get('daily_fields', 'close') in ('close', 'close,open'), 'DAILY_FIELD_SCOPE')
    observed_at = datetime.fromisoformat(receipt['observed_at'])
    calls = receipt['calls']; tables, coverage = {}, {}
    require(calls and calls[0]['api'] == 'trade_cal' and calls[0]['params'] == calendar_plan(observed_at)['params'], 'CALENDAR_REQUEST')
    first = calls[0]
    context = None
    try:
        require(first['status'] == 'SUCCESS', 'CALENDAR_SOURCE_UNAVAILABLE')
        context = calendar(bodies[first['attempts'][-1]['response_file']], observed_at)
    except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
        require(len(calls) == 1, 'REQUEST_WITHOUT_CALENDAR')
        return {'version': VERSION, 'source': SOURCE, 'market_session': None,
                'status': 'CALENDAR_INPUT_UNAVAILABLE_NOT_QUIET', 'error_type': type(exc).__name__,
                'rows': [], 'columns': COLUMNS, 'cohort_denominator': 0,
                'qualified_windows': {str(n): 0 for n in WINDOWS}, 'investment_authority': 'NONE'}
    plan = price_plan(context, daily_fields=receipt.get("daily_fields", "close"))
    require(len(calls) <= len(plan)+1, 'UNPLANNED_REQUEST')
    for i, item in enumerate(plan, 1):
        name = item['api'] + ':' + item['params']['trade_date']
        if i >= len(calls):
            coverage[name] = {'status': 'NOT_REQUESTED_AFTER_SOURCE_STOP'}; continue
        call = calls[i]
        require({k: call[k] for k in ('api', 'params')} == item, 'REQUEST_IDENTITY')
        coverage[name] = {'status': call['status']}
        if call['status'] != 'SUCCESS':
            continue
        try:
            rows, info = keyed(bodies[call['attempts'][-1]['response_file']], item)
            tables[item['api'], item['params']['trade_date']] = rows
            coverage[name] = {'status': 'SOURCE_ROWS_READ', **info}
        except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
            coverage[name] = {'status': 'SOURCE_SCHEMA_REJECTED', 'error_type': type(exc).__name__}
    report = evaluate(context, tables, coverage)
    if "daily_fields" in receipt:
        report["daily_fields_requested"] = receipt["daily_fields"]
    return report


def safe_root(root):
    root = Path(root)
    require(not root.is_symlink() and not any(p.is_symlink() for p in root.parents), 'SYMLINK')
    return root


def capture(root, *, observed_at, workflow, request=None, clock=lambda: datetime.now(timezone.utc).isoformat(),
            include_open=True):
    live = request is None
    if live:
        require(workflow == workflow_identity(workflow), 'WORKFLOW_IDENTITY')
        from .tushare_relay import request
        request = partial(request, retry_waits=(30, 90), deadline=elapsed_time.monotonic() + 17*60)
    root = safe_root(root); require(not root.exists(), 'CREATE_ONLY_OUTPUT')
    root.mkdir(parents=True); (root/'raw').mkdir()
    receipt = {'version': VERSION, 'source': SOURCE, 'observed_at': observed_at.isoformat(),
               'workflow': workflow, 'provenance': 'LIVE_TUSHARE_RELAY' if live else 'SYNTHETIC_TEST_ONLY',
               'calls': [], 'files': {}, 'finished_at': None, 'retry_waits': [30, 90]}
    require(type(include_open) is bool, "DAILY_FIELD_SCOPE")
    if include_open:
        receipt["daily_fields"] = "close,open"
    bodies = {}; total = 0
    def checkpoint():
        (root/'receipt.json').write_bytes(dumps(receipt))
    def one(item):
        nonlocal total
        require(len(receipt['calls']) < MAX_CALLS, 'CALL_BUDGET')
        saved = {**item, 'status': 'REQUEST_STARTED', 'attempts': []}
        receipt['calls'].append(saved); checkpoint()
        try:
            result = request(item['api'], item['params'])
            require(result['api'] == item['api'] and result['params'] == item['params'], 'TRANSPORT_IDENTITY')
            require(0 <= len(result['attempts']) <= 3 and (result['attempts'] or
                    result['status'] == 'REQUEST_BUDGET_EXHAUSTED'), 'ATTEMPT_BUDGET')
            saved['status'] = result['status']
            for attempt in result['attempts']:
                # Preserve native transport clocks and statuses; do not retain arbitrary error prose.
                entry = {k: attempt.get(k) for k in ('attempt', 'http_status', 'requested_at', 'received_at', 'classification')}
                if 'transport_error_type' in attempt:
                    require(attempt['transport_error_type'] in ('STREAM_READ_TIMEOUT', 'REQUEST_TIMEOUT',
                            'CONNECTION_ERROR', 'REQUEST_ERROR'), 'TRANSPORT_ERROR_TYPE')
                    entry['transport_error_type'] = attempt['transport_error_type']
                raw = attempt.get('raw'); entry['response_file'] = None
                entry['headers'] = {k: v for k, v in attempt.get('headers', {}).items()
                    if k in ('X-Request-ID', 'X-Cache', 'X-RateLimit-Remaining', 'X-RateLimit-IP-Remaining', 'Retry-After')}
                credential = os.environ.get('TUSHARE_PROXY_API_KEY', '') if live else ''
                require(not credential or all(credential not in str(v) for v in entry['headers'].values()), 'CREDENTIAL_REFLECTION')
                if raw is not None:
                    require(isinstance(raw, bytes) and len(raw) <= MAX_BODY and total+len(raw) <= MAX_TOTAL, 'BYTE_BUDGET')
                    name = f'raw/{len(receipt["calls"]):02}-{len(saved["attempts"])+1}.json'
                    (root/name).write_bytes(raw); bodies[name] = raw; total += len(raw)
                    receipt['files'][name] = {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
                    entry['response_file'] = name
                saved['attempts'].append(entry)
        except Exception as exc:
            # No invented 403/entitlement explanation and no implicit retry on parser/transport failure.
            saved['status'] = str(exc) if str(exc) in STOP else 'SOURCE_REQUEST_FAILED'
            saved['error_type'] = type(exc).__name__
        checkpoint()
        return saved
    first = one(calendar_plan(observed_at))
    if first['status'] == 'SUCCESS':
        try:
            context = calendar(bodies[first['attempts'][-1]['response_file']], observed_at)
        except (ValueError, KeyError, TypeError, InvalidOperation):
            context = None
        if context:
            for item in price_plan(context, daily_fields=receipt.get("daily_fields", "close")):
                if one(item)['status'] in STOP | {'REQUEST_BUDGET_EXHAUSTED'}:
                    break
    receipt['finished_at'] = clock(); checkpoint()
    report = build(receipt, bodies)
    report['observed_at'] = receipt['observed_at']; report['received_through'] = receipt['finished_at']
    report['source_requests'] = len(receipt['calls']); report['provenance'] = receipt['provenance']
    raw = dumps(report); require(len(raw) <= MAX_REPORT, 'REPORT_BYTE_BUDGET')
    (root/'report.json').write_bytes(raw); (root/'summary.md').write_text(render(report), encoding='utf-8')
    return report


def verify(root, *, expected_workflow=None):
    root = safe_root(root)
    for name, limit in (('receipt.json', 256*1024), ('report.json', MAX_REPORT), ('summary.md', 64*1024)):
        require(safe_root(root/name).stat().st_size <= limit, 'SAVED_FILE_SIZE')
    receipt = json.loads((root/'receipt.json').read_bytes(), object_pairs_hook=unique)
    require(receipt['version'] == VERSION and receipt['source'] == SOURCE, 'CAPTURE_VERSION')
    require(expected_workflow is None or receipt['workflow'] == expected_workflow, 'WORKFLOW_IDENTITY')
    require(receipt['provenance'] in ('LIVE_TUSHARE_RELAY', 'SYNTHETIC_TEST_ONLY'), 'CAPTURE_PROVENANCE')
    if receipt['provenance'] == 'LIVE_TUSHARE_RELAY':
        require(receipt['workflow'] == workflow_identity(receipt['workflow']), 'WORKFLOW_IDENTITY')
    require(1 <= len(receipt['calls']) <= MAX_CALLS, 'CALL_BUDGET')
    start, finish = (datetime.fromisoformat(receipt[k]) for k in ('observed_at', 'finished_at'))
    require(start.tzinfo is not None and finish.tzinfo is not None and start <= finish <= start+timedelta(minutes=20), 'CAPTURE_CLOCK')
    waits = receipt.get('retry_waits', [30])
    require(waits in ([30], [30, 90]), 'RETRY_POLICY')
    bodies = {}; names = set(); total = 0; last = start
    stopped = False
    for call in receipt['calls']:
        require(not stopped, 'REQUEST_AFTER_SOURCE_STOP')
        stopped = call['status'] in STOP | {'REQUEST_BUDGET_EXHAUSTED'}
        require(len(call['attempts']) <= len(waits) + 1 and call['status'] != 'REQUEST_STARTED', 'INCOMPLETE_ATTEMPT')
        for i, attempt in enumerate(call['attempts'], 1):
            require(attempt['attempt'] == i, 'ATTEMPT_ORDER')
            require('transport_error_type' not in attempt or attempt['transport_error_type'] in
                    ('STREAM_READ_TIMEOUT', 'REQUEST_TIMEOUT', 'CONNECTION_ERROR', 'REQUEST_ERROR'),
                    'TRANSPORT_ERROR_TYPE')
            asked, got = (datetime.fromisoformat(attempt[k]) for k in ('requested_at', 'received_at'))
            require(asked.tzinfo is not None and got.tzinfo is not None and last <= asked <= got <= finish, 'REQUEST_CLOCK')
            if i > 1:
                require(call['attempts'][i-2]['classification'] == 'TEMPORARY_QUEUE'
                        and asked >= last + timedelta(seconds=waits[i-2]), 'RETRY_CONTRACT')
            last = got
            name = attempt['response_file']
            if name is None:
                continue
            require(re.fullmatch(r'raw/[0-9]{2}-[123]\.json', name) is not None and name not in names, 'RAW_PATH')
            names.add(name); path = safe_root(root/name)
            require(path.stat().st_size <= MAX_BODY, 'RAW_FILE_SIZE')
            raw = path.read_bytes(); total += len(raw)
            require(len(raw) <= MAX_BODY and total <= MAX_TOTAL and receipt['files'][name] ==
                    {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}, 'RAW_IDENTITY')
            bodies[name] = raw
        if call['status'] == 'SUCCESS':
            require(call['attempts'] and call['attempts'][-1]['classification'] == 'SUCCESS'
                    and call['attempts'][-1]['http_status'] == 200 and call['attempts'][-1]['response_file'] in bodies
                    and len(bodies[call['attempts'][-1]['response_file']]) > 0,
                    'SUCCESS_BODY_REQUIRED')
    require(names == set(receipt['files']) == {p.relative_to(root).as_posix() for p in (root/'raw').iterdir()}, 'RAW_INVENTORY')
    report = build(receipt, bodies)
    report.update(observed_at=receipt['observed_at'], received_through=receipt['finished_at'], source_requests=len(receipt['calls']), provenance=receipt['provenance'])
    require((root/'report.json').read_bytes() == dumps(report) and
            (root/'summary.md').read_text(encoding='utf-8') == render(report), 'REPLAY_DIFFERS')
    return report


def render(report):
    if report.get('market_session') is None:
        return '# 日常个股输入\n\n交易日来源未取得；不是市场无变化。\n'
    counts = report['qualified_windows']; total = report['cohort_denominator']
    lines = ['# 日常个股输入', '', f"市场日：{report['market_session']}。本次覆盖 {total} 个有效证券身份；不是全部上市证券清单。",
        f"5／20／60交易日区间可比：{counts['5']}／{counts['20']}／{counts['60']}（各分母 {total}）。",
        '来源：现有第三方 Tushare Relay。仅比较准确日期的两端价格与因子；中间逐日数据不作前提。',
        '缺历史或缺因子只影响对应期限；不补零、不推断停牌或上市日，不替代经营研究或投资决定。', '']
    warnings = [key for key, info in report['source_row_coverage'].items()
                if info['status'] != 'SOURCE_ROWS_READ' or info.get('possibly_truncated')
                or info.get('rejected_row_positions') or info.get('duplicate_symbols')]
    if warnings:
        lines += ['来源覆盖缺口：' + '、'.join(warnings) + '。完整范围与行级处置见正文数据表。', '']
    for i, n in enumerate(WINDOWS):
        comparable = [r for r in report['rows'] if r[5+i] == 0]
        ordered = sorted(comparable, key=lambda r: (Decimal(r[2+i]), r[0]))
        shown = list(dict.fromkeys(r[0] for r in (ordered[-5:][::-1] + ordered[:5])))
        lookup = {r[0]: r for r in comparable}
        lines += [f'## {n}日区间两端变化（本次可比子集）', '', '| 证券 | 区间变化 |', '|---|---:|']
        lines += [f'| {symbol} | {Decimal(lookup[symbol][2+i]):+.2%} |' for symbol in shown]
        if not shown:
            lines.append('| 暂无可比输入，不是没有变化 | — |')
        lines.append('')
    return '\n'.join(lines) + '\n'


def workflow_identity(env):
    require(env.get('GITHUB_REPOSITORY') == 'auguspp/decision-kernel'
        and env.get('GITHUB_REF') == 'refs/heads/main' and env.get('GITHUB_RUN_ATTEMPT') == '1'
        and env.get('GITHUB_JOB') == 'daily-market-inputs'
        and env.get('GITHUB_EVENT_NAME') in ('schedule', 'workflow_dispatch')
        and env.get('GITHUB_WORKFLOW_REF') == 'auguspp/decision-kernel/'+WORKFLOW+'@refs/heads/main'
        and re.fullmatch(r'[0-9a-f]{40}', env.get('GITHUB_SHA', '')) is not None
        and re.fullmatch(r'[1-9][0-9]*', env.get('GITHUB_RUN_ID', '')) is not None, 'EXECUTION_IDENTITY')
    return {k: env[k] for k in ('GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_RUN_ATTEMPT',
        'GITHUB_JOB', 'GITHUB_EVENT_NAME', 'GITHUB_WORKFLOW_REF', 'GITHUB_SHA', 'GITHUB_RUN_ID')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args(); identity = workflow_identity(os.environ)
    report = (verify(args.output, expected_workflow=identity) if args.verify else
              capture(args.output, observed_at=datetime.now(timezone.utc), workflow=identity))
    print(render(report))
    return 0 if report.get('rows') else 2


if __name__ == '__main__':
    raise SystemExit(main())
