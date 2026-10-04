"""One dated #317 shadow reading, reusing the existing Tushare Relay.

No schedule, live quote substitution, Research/Odds changes or trading. The old
10-30 / 3-9 profile is an explicit experiment, not a source-admission threshold.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
from html import escape
import os
from pathlib import Path
import re
import time as elapsed

from . import stock_market_inputs as saved

VERSION = 'd-opening-auction-shadow-v1'
PROFILE = 'registered-317-prior-turnover10-30-auction-gap3-9-v1'
TITLE = 'd-auction-inputs'
JOB = 'auction-inputs'
WORKFLOW = saved.WORKFLOW
MAX_TOTAL = 24 * 1024 * 1024
MAX_REPORT = 512 * 1024
PATH = 'details/stock/auction-probe.json'
ROW_COLUMNS = ('symbol', 'name', 'prior_turnover_pct', 'status', 'auction_price',
               'auction_pre_close', 'gap_pct', 'matched_profile', 'prior_rows')
STOPS = saved.STOP | {'REQUEST_BUDGET_EXHAUSTED'}
ERRORS = (ValueError, KeyError, TypeError, IndexError, ArithmeticError, UnicodeError)
require = saved.require


def stamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'CLOCK_ZONE')
    return result.astimezone(timezone.utc)


def target_day(value):
    require(isinstance(value, str) and date.fromisoformat(value).isoformat() == value, 'TARGET_DATE')
    return date.fromisoformat(value)


def number(value):
    require(type(value) in (str, int, Decimal), 'NUMBER_TYPE')
    result = Decimal(value)
    require(result.is_finite() and len(result.as_tuple().digits) <= 28
            and abs(result.as_tuple().exponent) <= 12, 'NUMBER_RANGE')
    return result


def text(value):
    s = format(value, 'f')
    return s.rstrip('0').rstrip('.') if '.' in s else s


def query(api, day):
    fields = {
        'limit_list_d': 'trade_date,ts_code,name,close,turnover_ratio,limit_times,limit',
        'stk_auction': 'ts_code,trade_date,price,pre_close',
    }
    params = {'trade_date': day.strftime('%Y%m%d'), 'fields': fields[api],
              'limit': '2500' if api == 'limit_list_d' else '8000'}
    if api == 'stk_auction':
        params['ts_type'] = 'STK'
    return {'api': api, 'params': params}


def calendar_query(target):
    return {'api': 'trade_cal', 'params': {'exchange': 'SSE',
        'start_date': (target - timedelta(days=31)).strftime('%Y%m%d'),
        'end_date': target.strftime('%Y%m%d'), 'fields': 'exchange,cal_date,is_open', 'limit': '1000'}}


def table(raw, api):
    body = saved.loads(raw)
    require(isinstance(body, dict) and type(body.get('code')) is int and body['code'] == 0
            and body.get('ok') is not False and body.get('api_name', api) == api
            and body.get('error') in (None, ''), 'SOURCE_ENVELOPE')
    data = body['data']; fields, rows = data['fields'], data['items']
    require(isinstance(fields, list) and all(isinstance(x, str) for x in fields)
            and len(fields) == len(set(fields)) <= 128, 'FIELDS')
    required = {'exchange', 'cal_date', 'is_open'} if api == 'trade_cal' else {'ts_code', 'trade_date'}
    if api == 'limit_list_d':
        required.add('limit')
    require(required <= set(fields), 'IDENTITY_FIELDS')
    require(isinstance(rows, list) and len(rows) <= 10000
            and all(isinstance(r, list) and len(r) == len(fields) for r in rows), 'ROW_SHAPE')
    cap = {'trade_cal': 1000, 'limit_list_d': 2500, 'stk_auction': 8000}[api]
    truncated = len(rows) >= cap
    for obj in (body, data):
        for key in ('total', 'count'):
            if key in obj:
                require(type(obj[key]) is int and obj[key] >= len(rows), 'COUNT_CONFLICT')
                truncated |= obj[key] > len(rows)
        truncated |= any(obj.get(k) not in (None, False, '') for k in
                         ('has_more', 'has_next', 'truncated', 'next', 'next_page', 'next_cursor'))
    return [dict(zip(fields, r)) for r in rows], bool(truncated)


def calendar(raw, target):
    rows, incomplete = table(raw, 'trade_cal')
    # Missing older dates do not invalidate the exact interval actually used.
    start = target - timedelta(days=31)
    values = {}
    for row in rows:
        day = saved.day(row['cal_date'])
        require(row['exchange'] == 'SSE' and start <= day <= target and day not in values
                and type(row['is_open']) is int and row['is_open'] in (0, 1), 'CALENDAR_IDENTITY')
        values[day] = row['is_open']
    require(target in values, 'TARGET_CALENDAR_UNAVAILABLE')
    prior = max((d for d, open_ in values.items() if open_ and d < target), default=None)
    if not values[target]:
        return False, prior
    require(prior is not None, 'PREVIOUS_SESSION_UNAVAILABLE')
    require(all(prior+timedelta(days=n) in values for n in range((target-prior).days+1)),
            'PREVIOUS_TO_TARGET_CALENDAR_GAP')
    return True, prior


def scoped(rows, day):
    groups, invalid = defaultdict(list), []
    for i, row in enumerate(rows):
        symbol = row.get('ts_code')
        if not isinstance(symbol, str) or saved.CODE.fullmatch(symbol) is None or row.get('trade_date') != day.strftime('%Y%m%d'):
            invalid.append(i)  # Original offending row remains in the raw response.
        else:
            groups[symbol].append(row)
    return groups, invalid


def row_dicts(report):
    return [dict(zip(report['columns'], values, strict=True)) for values in report['rows']]


def packed(result):
    # A complete columnar table, as in the existing daily stock input. Do not
    # discard securities merely to fit repeated JSON key names into the bound.
    result['columns'] = list(ROW_COLUMNS)
    result['rows'] = [[row[key] for key in ROW_COLUMNS] for row in result['rows']]
    return result


def prior_pool(raw, prior):
    source, truncated = table(raw, 'limit_list_d')
    groups, invalid = scoped(source, prior)
    # Valid securities on a wrong date stay in the U denominator, but cannot
    # pass. Unidentifiable U rows are also retained, not silently subtracted.
    unidentified = []
    for index in invalid:
        row = source[index]
        if row.get('limit') != 'U':
            continue
        code = row.get('ts_code')
        if isinstance(code, str) and saved.CODE.fullmatch(code):
            groups[code].append(row)
        else:
            unidentified.append(index)
    output, counts, ladder, ambiguous = [], Counter(), [], []
    for symbol, values in sorted(groups.items()):
        types = {r.get('limit') if isinstance(r.get('limit'), str) else '<INVALID>' for r in values}
        wrong_date = any(r['trade_date'] != prior.strftime('%Y%m%d') for r in values)
        if wrong_date or len(types) != 1 or not types <= {'U', 'D', 'Z'}:
            ambiguous.append(symbol)
        else:
            counts[next(iter(types))] += 1
        if 'U' not in types:
            continue
        def key(row):
            try:
                rate = number(row.get('turnover_ratio'))
            except ERRORS:
                rate = repr(row.get('turnover_ratio'))
            return (repr(row.get('name')), rate, repr(row.get('limit')))
        consumed = {key(r) for r in values}
        row = values[0]
        name = row.get('name')
        valid_name = isinstance(name, str) and 0 < len(name.strip()) <= 80 and not any(ord(c) < 32 for c in name)
        item = {'symbol': symbol, 'name': name if valid_name else None, 'prior_turnover_pct': None,
                'status': 'STATIC_ELIGIBLE', 'auction_price': None, 'auction_pre_close': None,
                'gap_pct': None, 'matched_profile': False, 'prior_rows': len(values)}
        output.append(item)
        if wrong_date:
            item['status'] = 'PRIOR_SESSION_MISMATCH'; continue
        if len(consumed) != 1:
            item['status'] = 'PRIOR_IDENTITY_CONFLICT'; continue
        if not re.fullmatch(r'(?:60[0135][0-9]{3}\.SH|00[0123][0-9]{3}\.SZ)', symbol):
            item['status'] = 'EXCLUDED_BOARD'; continue
        name = row.get('name')
        if not valid_name:
            item['name'] = None; item['status'] = 'PRIOR_NAME_UNAVAILABLE'; continue
        if 'ST' in name.upper():
            item['status'] = 'EXCLUDED_PRIOR_ST_NAME'; continue
        try:
            turnover = number(row.get('turnover_ratio'))
            require(turnover >= 0, 'NEGATIVE_TURNOVER')
            item['prior_turnover_pct'] = text(turnover)
            if not Decimal(10) <= turnover <= Decimal(30):
                item['status'] = 'OUTSIDE_PRIOR_TURNOVER_PROFILE'
        except ERRORS:
            item['status'] = 'PRIOR_TURNOVER_UNAVAILABLE'
    for index in unidentified:
        output.append({'symbol': None, 'name': None, 'prior_turnover_pct': None,
            'status': 'PRIOR_SECURITY_IDENTITY_UNAVAILABLE', 'auction_price': None,
            'auction_pre_close': None, 'gap_pct': None, 'matched_profile': False, 'prior_rows': 1})
    # Temperature has its own qualification. Missing streaks cannot reject price ratios.
    missing_streaks = []
    for symbol, values in sorted(groups.items()):
        if any(r.get('limit') != 'U' or r.get('trade_date') != prior.strftime('%Y%m%d') for r in values):
            continue
        streaks = [r.get('limit_times') for r in values]
        if any(type(n) is not int or n < 1 for n in streaks) or len(set(streaks)) != 1:
            missing_streaks.append(symbol); continue
        ladder.append({'symbol': symbol, 'consecutive_limits': streaks[0]})
    return output, {'market_session': prior.isoformat(), 'source_pool': 'LIMIT_LIST_D_EXCLUDES_ST',
        'limit_up': counts['U'], 'limit_down': counts['D'], 'opened_limit': counts['Z'],
        'maximum_consecutive': max((r['consecutive_limits'] for r in ladder), default=None),
        'ladder_at_least_two': [r for r in ladder if r['consecutive_limits'] >= 2],
        'missing_streak_symbols': missing_streaks, 'ambiguous_symbols': ambiguous,
        'invalid_row_indices': invalid, 'returned_rows': len(source), 'truncated': truncated,
        'scope': 'RETURNED_PREVIOUS_SESSION_POOL_NOT_TODAY_OR_INDEPENDENT_MARKET_EXHAUSTIVENESS'}


def apply_auction(rows, raw, target):
    source, truncated = table(raw, 'stk_auction')
    groups, invalid = scoped(source, target)
    for row in rows:
        if row['status'] != 'STATIC_ELIGIBLE':
            continue
        values = groups.get(row['symbol'], [])
        if not values:
            row['status'] = 'AUCTION_ROW_UNAVAILABLE'; continue
        try:
            pairs = {(number(v.get('price')), number(v.get('pre_close'))) for v in values}
            require(len(pairs) == 1, 'CONFLICT')
            price, reference = pairs.pop()
            require(price > 0 and reference > 0, 'PRICE_POSITIVE')
            with localcontext() as ctx:
                ctx.prec = 28
                gap = (price / reference - 1) * 100
            row.update(auction_price=text(price), auction_pre_close=text(reference), gap_pct=text(gap),
                       matched_profile=Decimal(3) <= gap <= Decimal(9))
            row['status'] = 'SHADOW_PROFILE_MATCH' if row['matched_profile'] else 'OUTSIDE_AUCTION_GAP_PROFILE'
        except ERRORS:
            row['status'] = 'AUCTION_VALUE_UNAVAILABLE_OR_CONFLICT'
    return {'returned_rows': len(source), 'truncated': truncated, 'invalid_row_indices': invalid,
            'price_semantics': 'STK_AUCTION_MATCHED_PRICE_OVER_SAME_ROW_PRE_CLOSE',
            'historical_or_late_capture_is_not_preopen_discovery': True}


def response(call, bodies):
    require(call['status'] == 'SUCCESS' and call['attempts'], 'SOURCE_NOT_SUCCESSFUL')
    return bodies[call['attempts'][-1]['response_file']]


def build(receipt, bodies):
    target = target_day(receipt['market_session']); at = stamp(receipt['observed_at'])
    calls = receipt['calls']
    result = {'version': VERSION, 'profile': PROFILE, 'source': saved.SOURCE,
        'market_session': target.isoformat(), 'previous_session': None,
        'observed_at': at.isoformat(), 'received_through': receipt['finished_at'],
        'provenance': receipt['provenance'], 'status': 'CALENDAR_UNAVAILABLE',
        'cohort_denominator': 0, 'static_eligible': 0, 'comparable': 0, 'matched': 0,
        'rows': [], 'prior_temperature': None, 'auction_scope': None,
        'source_outcomes': [{'api': c['api'], 'status': c['status']} for c in calls],
        'timeliness': 'NOT_ESTABLISHED', 'human_attention_authority': 'NONE',
        'research_authority': 'NONE', 'investment_authority': 'NONE', 'odds_recomputed': False,
        'name_filter': 'PREVIOUS_SESSION_NAME_ONLY_NOT_CURRENT_STATUS_CERTIFICATION',
        'meaning': 'SHADOW_PRICE_PROFILE_NOT_WEAK_TO_STRONG_PROOF_OR_TRADE', 'source_requests': len(calls)}
    require(calls and calls[0]['api'] == 'trade_cal' and
            {k: calls[0][k] for k in ('api', 'params')} == calendar_query(target), 'CALENDAR_REQUEST')
    try:
        open_, prior = calendar(response(calls[0], bodies), target)
    except ERRORS:
        require(len(calls) == 1, 'REQUEST_AFTER_INVALID_CALENDAR')
        return packed(result)
    result['previous_session'] = prior.isoformat() if prior else None
    calendar_rows, calendar_truncated = table(response(calls[0], bodies), 'trade_cal')
    result['calendar_scope'] = {'returned_rows': len(calendar_rows), 'truncated': calendar_truncated,
        'qualification': 'EXACT_PREVIOUS_TO_TARGET_INTERVAL_ONLY_NOT_WHOLE_QUERY_COMPLETENESS'}
    if not open_ or (target == at.astimezone(saved.ZONE).date() and at.astimezone(saved.ZONE).time() < time(9, 26)):
        require(len(calls) == 1, 'REQUEST_OUTSIDE_PLANNED_SESSION')
        result['status'] = 'TARGET_IS_CLOSED_SESSION' if not open_ else 'BEFORE_AUCTION_DATA_WINDOW'
        return packed(result)
    expected = [calendar_query(target), query('limit_list_d', prior), query('stk_auction', target)]
    require(len(calls) <= 3 and all({k: c[k] for k in ('api', 'params')} == q for c, q in zip(calls, expected)), 'REQUEST_SEQUENCE')
    result['status'] = 'PRIOR_POOL_UNAVAILABLE'
    if len(calls) == 1:
        return packed(result)
    try:
        rows, context = prior_pool(response(calls[1], bodies), prior)
    except ERRORS:
        require(len(calls) == 2, 'REQUEST_AFTER_INVALID_PRIOR')
        return packed(result)
    result.update(rows=rows, prior_temperature=context, cohort_denominator=len(rows),
                  static_eligible=sum(r['status'] == 'STATIC_ELIGIBLE' for r in rows))
    if not result['static_eligible']:
        require(len(calls) == 2, 'UNNEEDED_AUCTION_REQUEST')
        result['status'] = 'NO_STATIC_MATCH_IN_RETURNED_POOL'
    else:
        result['status'] = 'AUCTION_INPUT_UNAVAILABLE'
        if len(calls) == 3:
            try:
                result['auction_scope'] = apply_auction(rows, response(calls[2], bodies), target)
                result['status'] = 'SHADOW_AUCTION_READING'
                got = stamp(calls[2]['attempts'][-1]['received_at']).astimezone(saved.ZONE)
                asked = stamp(calls[2]['attempts'][-1]['requested_at']).astimezone(saved.ZONE)
                result['timeliness'] = ('RECEIVED_BEFORE_CONTINUOUS_OPEN' if target == asked.date() == got.date()
                    and time(9, 26) <= asked.time() <= got.time() < time(9, 30)
                    else 'HISTORICAL_OR_LATE_NOT_PREOPEN_DISCOVERY')
            except ERRORS:
                result['auction_scope'] = {'status': 'SOURCE_SCHEMA_OR_FIELDS_UNAVAILABLE'}
        for row in rows:
            if row['status'] == 'STATIC_ELIGIBLE':
                row['status'] = 'AUCTION_INPUT_UNAVAILABLE'
    result['comparable'] = sum(r['gap_pct'] is not None for r in rows)
    result['matched'] = sum(r['matched_profile'] for r in rows)
    result['coverage_gaps'] = bool(context['truncated'] or context['invalid_row_indices'] or context['ambiguous_symbols']
        or result['comparable'] < result['static_eligible']
        or (result['auction_scope'] or {}).get('truncated') or (result['auction_scope'] or {}).get('invalid_row_indices')
        or any(r['status'] in ('PRIOR_IDENTITY_CONFLICT', 'PRIOR_NAME_UNAVAILABLE', 'PRIOR_TURNOVER_UNAVAILABLE',
                                   'PRIOR_SESSION_MISMATCH', 'PRIOR_SECURITY_IDENTITY_UNAVAILABLE') for r in rows))
    return packed(result)


def render(report):
    lines = ['## D：集合竞价条件观察（shadow）', '',
        f"目标交易日：{report['market_session']}；昨日池日期：{report['previous_session']}。",
        f"状态：{report['status']}；时点：{report['timeliness']}。",
        f"返回涨停池分母 {report['cohort_denominator']}；静态条件内 {report['static_eligible']}；"
        f"竞价可比 {report['comparable']}；原条件匹配 {report['matched']}。",
        '来源截断或逐名缺口：' + ('有，已逐项保留。' if report.get('coverage_gaps', True) else '本次返回范围未发现；不是独立穷尽认证。'),
        '固定观察条件：昨日换手10–30%、沪深主板且昨日名称不含ST、竞价相对接口昨收高开3–9%。',
        '历史/盘后补读不是开盘前发现；昨日池、缺口及筛掉项全部保留。不修改Research/Odds，不形成买卖或唤醒。']
    matches = [r for r in row_dicts(report) if r['matched_profile']]
    if matches:
        if len(matches) > 20:
            lines += ['', f'首页按证券代码仅展示前20项，另{len(matches)-20}项及所有非匹配项见完整明细；不是强弱排名。']
        lines += ['', '| 证券 | 昨日名称 | 昨日换手% | 竞价相对昨收% |', '|---|---|---:|---:|']
        for row in matches[:20]:
            name = escape(row['name']).replace('|', '／').replace('[', '［').replace(']', '］')
            lines.append(f"| {row['symbol']} | {name} | {row['prior_turnover_pct']} | {Decimal(row['gap_pct']):.2f} |")
    lines += ['', f'完整返回池、逐名理由与独立来源时钟见 [{PATH}]({PATH})。']
    return '\n'.join(lines) + '\n'


def workflow_identity(env):
    expected = {'GITHUB_REPOSITORY': 'auguspp/decision-kernel', 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_JOB': JOB, 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_WORKFLOW_REF': 'auguspp/decision-kernel/'+WORKFLOW+'@refs/heads/main'}
    require(all(env.get(k) == v for k, v in expected.items()) and
            re.fullmatch(r'[a-f0-9]{40}', env.get('GITHUB_SHA', '')) is not None and
            re.fullmatch(r'[1-9][0-9]*', env.get('GITHUB_RUN_ID', '')) is not None, 'WORKFLOW_IDENTITY')
    return {**expected, 'GITHUB_SHA': env['GITHUB_SHA'], 'GITHUB_RUN_ID': env['GITHUB_RUN_ID']}


def capture(root, *, market_session=None, observed_at=None, workflow=None, request=None, clock=None):
    from . import tushare_relay as relay
    at = observed_at or datetime.now(timezone.utc)
    require(at.tzinfo is not None, 'CLOCK_ZONE')
    target = target_day(market_session or at.astimezone(saved.ZONE).date().isoformat())
    require(target <= at.astimezone(saved.ZONE).date(), 'FUTURE_SESSION')
    live = request is None
    identity = workflow_identity(workflow or os.environ) if live else {}
    root = saved.safe_root(root); root.mkdir(); (root/'raw').mkdir()
    clock = clock or relay.now
    deadline = elapsed.monotonic() + 8*60
    fetch = request or (lambda api, params: relay.request(api, params, retry_waits=(30,), deadline=deadline))
    receipt = {'version': VERSION, 'market_session': target.isoformat(), 'source': saved.SOURCE,
        'observed_at': at.isoformat(), 'finished_at': at.isoformat(), 'workflow': identity,
        'provenance': 'LIVE_TUSHARE_RELAY' if live else 'SYNTHETIC_TEST_ONLY', 'calls': [], 'files': {}}
    bodies = {}
    def checkpoint():
        (root/'receipt.json').write_bytes(saved.dumps(receipt))
    def one(item):
        call = {**item, 'status': 'REQUEST_STARTED', 'attempts': []}
        receipt['calls'].append(call); checkpoint()
        try:
            result = fetch(item['api'], item['params'])
            require(result['api'] == item['api'] and result['params'] == item['params'], 'RELAY_REQUEST_IDENTITY')
            call['status'] = result['status']
            for attempt in result['attempts']:
                entry = {k: attempt[k] for k in ('attempt', 'http_status', 'requested_at', 'received_at', 'classification')}
                if 'transport_error_type' in attempt:
                    entry['transport_error_type'] = attempt['transport_error_type']
                entry['response_file'] = None
                raw = attempt.get('raw')
                if raw is not None:
                    require(isinstance(raw, bytes) and len(raw) <= saved.MAX_BODY and
                            sum(map(len, bodies.values()))+len(raw) <= MAX_TOTAL, 'BODY_BUDGET')
                    key = os.environ.get(relay.SECRET_ENV, '') if live else ''
                    require(not key or key.encode() not in raw, 'CREDENTIAL_REFLECTION')
                    name = f'raw/{len(receipt["calls"]):02}-{len(call["attempts"])+1}.json'
                    (root/name).write_bytes(raw); bodies[name] = raw
                    receipt['files'][name] = {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
                    entry['response_file'] = name
                call['attempts'].append(entry)
        except Exception as exc:
            call['status'] = str(exc) if str(exc) in STOPS else 'SOURCE_REQUEST_FAILED'
            call['error_type'] = type(exc).__name__
        receipt['finished_at'] = clock(); checkpoint()
        return call
    one(calendar_query(target))
    first = build(receipt, bodies)
    if first['previous_session'] and first['status'] == 'PRIOR_POOL_UNAVAILABLE' and receipt['calls'][-1]['status'] not in STOPS:
        one(query('limit_list_d', target_day(first['previous_session'])))
        second = build(receipt, bodies)
        if second['static_eligible'] and receipt['calls'][-1]['status'] not in STOPS:
            one(query('stk_auction', target))
    receipt['finished_at'] = clock(); checkpoint()
    report = build(receipt, bodies)
    raw = saved.dumps(report); require(len(raw) <= MAX_REPORT, 'REPORT_BYTE_BUDGET')
    (root/'report.json').write_bytes(raw); (root/'summary.md').write_text(render(report), encoding='utf-8')
    return verify(root, expected_workflow=identity if live else None)


def verify(root, *, expected_workflow=None):
    """Replay exact saved envelopes; no source/network call or silent correction."""
    from . import tushare_relay as relay
    root = saved.safe_root(root)
    def read(name, limit):
        path = saved.safe_root(root/name)
        require(path.is_file() and path.stat().st_size <= limit, 'SAVED_BYTE_BOUND')
        return path.read_bytes()
    receipt = saved.loads(read('receipt.json', 256*1024))
    require(receipt['version'] == VERSION and receipt['source'] == saved.SOURCE and
            receipt['provenance'] in ('LIVE_TUSHARE_RELAY', 'SYNTHETIC_TEST_ONLY'), 'CAPTURE_IDENTITY')
    if receipt['provenance'] == 'LIVE_TUSHARE_RELAY':
        require(receipt['workflow'] == workflow_identity(receipt['workflow']), 'WORKFLOW_IDENTITY')
    else:
        require(receipt['workflow'] == {}, 'SYNTHETIC_WORKFLOW')
    require(expected_workflow is None or receipt['workflow'] == expected_workflow, 'WORKFLOW_MISMATCH')
    start, finish = stamp(receipt['observed_at']), stamp(receipt['finished_at'])
    require(start <= finish <= start+timedelta(minutes=10) and
            target_day(receipt['market_session']) <= start.astimezone(saved.ZONE).date(), 'CAPTURE_CLOCK')
    require(1 <= len(receipt['calls']) <= 3, 'CALL_BOUND')
    bodies = {}; last = start; stopped = False
    for n, call in enumerate(receipt['calls'], 1):
        require(not stopped and call['status'] != 'REQUEST_STARTED' and len(call['attempts']) <= 2, 'SOURCE_STOP_OR_ATTEMPTS')
        stopped = call['status'] in STOPS
        for i, a in enumerate(call['attempts'], 1):
            require(type(a['attempt']) is int and a['attempt'] == i, 'ATTEMPT_ORDER')
            asked, got = stamp(a['requested_at']), stamp(a['received_at'])
            require(last <= asked <= got <= finish, 'ATTEMPT_CLOCK')
            if i > 1:
                require(call['attempts'][i-2]['classification'] == 'TEMPORARY_QUEUE' and
                        asked >= last + timedelta(seconds=30), 'RETRY_POLICY')
            last = got
            raw = None; name = a['response_file']
            if name is not None:
                require(name == f'raw/{n:02}-{i}.json' and name not in bodies, 'RAW_PATH')
                raw = read(name, saved.MAX_BODY); bodies[name] = raw
                require(receipt['files'][name] == {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}, 'RAW_IDENTITY')
            status = a['http_status']
            if status is None:
                allowed = {'REQUEST_TIMEOUT': 'TEMPORARY_QUEUE', 'STREAM_READ_TIMEOUT': 'TEMPORARY_QUEUE',
                           'CONNECTION_ERROR': 'TRANSPORT_CONNECTION', 'REQUEST_ERROR': 'TRANSPORT_ERROR'}
                require(raw is None and allowed.get(a.get('transport_error_type')) == a['classification'], 'TRANSPORT_IDENTITY')
            else:
                require(type(status) is int and 100 <= status <= 599 and raw is not None, 'HTTP_IDENTITY')
                try:
                    body = relay.decode(raw); classification = relay.classify(status, body)
                except relay.RelayError:
                    classification = relay.classify(status, {}) if status in (400,401,403,429,502,503,504) else 'MALFORMED_RESPONSE'
                require(a['classification'] == classification, 'RESPONSE_CLASSIFICATION')
        require(call['status'] in STOPS | {'SOURCE_REQUEST_FAILED'} or
                bool(call['attempts']) and call['status'] == call['attempts'][-1]['classification'], 'CALL_STATUS')
        if call['status'] == 'SUCCESS':
            require(call['attempts'] and call['attempts'][-1]['http_status'] == 200, 'SUCCESS_BODY')
    require(sum(map(len, bodies.values())) <= MAX_TOTAL and set(bodies) == set(receipt['files']) and
            {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} ==
            set(bodies) | {'receipt.json','report.json','summary.md'}, 'FILE_INVENTORY')
    rebuilt = build(receipt, bodies)
    require(read('report.json', MAX_REPORT) == saved.dumps(rebuilt) and
            read('summary.md', 256*1024) == render(rebuilt).encode(), 'REPORT_REPLAY')
    return rebuilt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--market-session', default=None)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    report = verify(args.output) if args.verify else capture(args.output, market_session=args.market_session)
    print(report['status'])
    return 0 if report['status'] in ('SHADOW_AUCTION_READING', 'NO_STATIC_MATCH_IN_RETURNED_POOL',
        'TARGET_IS_CLOSED_SESSION', 'BEFORE_AUCTION_DATA_WINDOW') else 2


if __name__ == '__main__':
    raise SystemExit(main())
