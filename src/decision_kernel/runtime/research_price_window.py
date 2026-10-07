"""Explicit historical daily-price custody; no current-state or trading effects.

The transport and scalar/table checks belong to existing source modules. This
adapter only bounds a requested research window and preserves its raw replies.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import InvalidOperation
from functools import partial
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time

from .stock_market_inputs import (SOURCE, STOP, ZONE, day, dumps, number, require,
                                  safe_root, table, unique)

VERSION = 'research-price-window-v1'
WORKFLOW = '.github/workflows/research-price-window.yml'
MAX_CODES, MAX_DAYS = 5, 31
MAX_CALLS, MAX_BODY, MAX_TOTAL = 12, 4 * 1024 * 1024, 16 * 1024 * 1024
FIELDS = {'daily': 'ts_code,trade_date,open,high,low,close,pre_close',
          'adj_factor': 'ts_code,trade_date,adj_factor',
          'trade_cal': 'exchange,cal_date,is_open'}
TERMINAL = STOP | {'REQUEST_BUDGET_EXHAUSTED', 'BYTE_BUDGET', 'TRANSPORT_CONTRACT_FAILED'}


def plan(codes, start, end, observed_at):
    require(isinstance(codes, list) and 1 <= len(codes) <= MAX_CODES
            and all(isinstance(c, str) and re.fullmatch(r'[0-9]{6}\.(SH|SZ)', c) for c in codes)
            and len(codes) == len(set(codes)), 'SECURITY_SCOPE')
    a, b = day(start), day(end)
    require(a <= b and (b-a).days < MAX_DAYS, 'DATE_WINDOW')
    require(observed_at.tzinfo is not None and observed_at.utcoffset() is not None, 'CLOCK_ZONE')
    # No partly completed current day. This adapter is not the daily producer.
    require(b < observed_at.astimezone(ZONE).date(), 'HISTORICAL_WINDOW_ONLY')
    exchanges = sorted({'SSE' if c.endswith('.SH') else 'SZSE' for c in codes})
    calls = [{'api': 'trade_cal', 'params': {'exchange': x, 'start_date': start,
              'end_date': end, 'fields': FIELDS['trade_cal'], 'limit': '1000'}} for x in exchanges]
    calls += [{'api': api, 'params': {'ts_code': c, 'start_date': start, 'end_date': end,
               'fields': FIELDS[api], 'limit': '1000'}} for c in codes for api in ('daily', 'adj_factor')]
    require(len(calls) <= MAX_CALLS, 'CALL_BUDGET')
    return calls


def workflow_identity(env):
    require(env.get('GITHUB_REPOSITORY') == 'auguspp/decision-kernel'
            and env.get('GITHUB_REF') == 'refs/heads/main'
            and env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
            and env.get('GITHUB_RUN_ATTEMPT') == '1'
            and env.get('GITHUB_JOB') == 'capture'
            and env.get('GITHUB_WORKFLOW_REF') == 'auguspp/decision-kernel/'+WORKFLOW+'@refs/heads/main'
            and re.fullmatch(r'[0-9a-f]{40}', env.get('GITHUB_SHA', '')) is not None
            and re.fullmatch(r'[1-9][0-9]*', env.get('GITHUB_RUN_ID', '')) is not None,
            'EXECUTION_IDENTITY')
    return {k: env[k] for k in ('GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_EVENT_NAME',
            'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB', 'GITHUB_WORKFLOW_REF', 'GITHUB_SHA', 'GITHUB_RUN_ID')}


def qualified(raw, item):
    api, params = item['api'], item['params']
    rows, incomplete = table(raw, api, FIELDS[api].split(','))
    require(not incomplete and len(rows) < 1000, 'SOURCE_TRUNCATED')
    a, b = day(params['start_date']), day(params['end_date'])
    result = {}
    for row in rows:
        when = row['cal_date' if api == 'trade_cal' else 'trade_date']
        d = day(when)
        require(a <= d <= b and when not in result, 'ROW_DATE_OR_DUPLICATE')
        if api == 'trade_cal':
            require(row['exchange'] == params['exchange'] and type(row['is_open']) in (int, str)
                    and str(row['is_open']) in ('0', '1'), 'CALENDAR_IDENTITY')
            result[when] = str(row['is_open']) == '1'
        else:
            require(row['ts_code'] == params['ts_code'], 'SECURITY_IDENTITY')
            values = {k: number(row[k]) for k in FIELDS[api].split(',')[2:]}
            if api == 'daily':
                require(values['low'] <= min(values['open'], values['close'])
                        <= max(values['open'], values['close']) <= values['high'], 'OHLC_ORDER')
            result[when] = {k: format(v, 'f') for k, v in values.items()}
    if api == 'trade_cal':
        require(set(result) == {(a+timedelta(days=i)).strftime('%Y%m%d')
                for i in range((b-a).days+1)}, 'CALENDAR_COVERAGE')
    return result


def build(receipt, bodies):
    observed = datetime.fromisoformat(receipt['observed_at'])
    expected = plan(receipt['codes'], receipt['start'], receipt['end'], observed)
    require(receipt['plan'] == expected and receipt['plan_sha256'] == sha256(dumps(expected)).hexdigest(), 'PLAN_IDENTITY')
    calls = receipt['calls']; require(len(calls) <= len(expected), 'CALL_BUDGET')
    tables, statuses = {}, []
    for i, item in enumerate(expected):
        key = (item['api'], item['params'].get('ts_code', item['params'].get('exchange')))
        status = 'NOT_REQUESTED'
        if i < len(calls):
            call = calls[i]
            require({k: call[k] for k in ('api', 'params')} == item, 'REQUEST_IDENTITY')
            status = call['status']
            if status == 'SUCCESS':
                try:
                    tables[key] = qualified(bodies[call['attempts'][-1]['response_file']], item)
                    status = 'SOURCE_ROWS_QUALIFIED'
                except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
                    status = 'SOURCE_QUALIFICATION_FAILED:' + type(exc).__name__
        statuses.append({'api': key[0], 'object': key[1], 'status': status,
                         'qualified_rows': len(tables[key]) if key in tables else None})
    securities = []
    for c in receipt['codes']:
        cal = tables.get(('trade_cal', 'SSE' if c.endswith('.SH') else 'SZSE'))
        prices, factors = tables.get(('daily', c), {}), tables.get(('adj_factor', c), {})
        sessions = sorted(d for d, opened in (cal or {}).items() if opened)
        missing_price = [d for d in sessions if d not in prices]
        missing_factor = [d for d in sessions if d not in factors]
        outside = sorted((set(prices) | set(factors)) - set(sessions)) if cal is not None else []
        # Unknown missing dates are not filled or silently treated as suspensions.
        complete = cal is not None and bool(sessions) and not (missing_price or missing_factor or outside)
        securities.append({'ts_code': c, 'status': 'COMPLETE_PROVIDER_DAILY_WINDOW' if complete else 'WINDOW_GAPS',
            'calendar_available': cal is not None, 'sessions': sessions,
            'missing_price_sessions': missing_price, 'missing_factor_sessions': missing_factor,
            'rows_outside_open_sessions': outside, 'prices': prices, 'factors': factors})
    return {'version': VERSION, 'source': SOURCE, 'provenance': receipt['provenance'],
        'observed_at': receipt['observed_at'], 'received_through': receipt['finished_at'],
        'start': receipt['start'], 'end': receipt['end'], 'plan_sha256': receipt['plan_sha256'],
        'source_requests': len(calls), 'source_statuses': statuses, 'securities': securities,
        'status': 'COMPLETE_PROVIDER_DAILY_WINDOWS' if all(s['status'] == 'COMPLETE_PROVIDER_DAILY_WINDOW'
                  for s in securities) else 'PARTIAL_OR_UNAVAILABLE',
        'historical_acquisition': 'NOT_ESTABLISHED_BY_LATER_RETRIEVAL',
        'price_semantics': 'RAW_OHLC_AND_PROVIDER_FACTORS_NOT_TOTAL_RETURN_OR_EXECUTABLE_PRICES',
        'company_action_details': 'NOT_OBTAINED', 'revised_history': 'NOT_EXCLUDED',
        'intraday_timeliness': 'NOT_ESTABLISHED', 'investment_authority': 'NONE',
        'research_executed': False, 'current_state_updated': False, 'watch_registered': False}


def render(report):
    lines = ['# 有限研究日线窗口', '', f"{report['start']}–{report['end']}；{report['source']}。", '',
             '| 证券 | 开市日 | 缺日价 | 缺因子 | 状态 |', '|---|---:|---:|---:|---|']
    for s in report['securities']:
        lines.append(f"| {s['ts_code']} | {len(s['sessions'])} | {len(s['missing_price_sessions'])} | "
                     f"{len(s['missing_factor_sessions'])} | {s['status']} |")
    lines += ['', '日历不可用时上表零计数不代表没有交易日。原始响应、拒绝与未请求项另见收据。',
              '后取得的历史日线不证明当时已知、可成交、总回报或盘中及时性；公司行动和研究结论另审。',
              '本入口不写当前行情、Research、Human、Watch或交易状态。Investment Authority=NONE。', '']
    return '\n'.join(lines)


def capture(root, *, codes, start, end, observed_at, workflow, request=None,
            clock=lambda: datetime.now(timezone.utc).isoformat()):
    queries = plan(codes, start, end, observed_at)
    live = request is None
    if live:
        require(workflow == workflow_identity(workflow), 'WORKFLOW_IDENTITY')
        from .tushare_relay import request
        request = partial(request, retry_waits=(30,), deadline=time.monotonic()+14*60)
    root = safe_root(root); require(not root.exists(), 'CREATE_ONLY_OUTPUT')
    root.mkdir(parents=True); (root/'raw').mkdir()
    receipt = {'version': VERSION, 'source': SOURCE, 'codes': codes, 'start': start, 'end': end,
        'observed_at': observed_at.isoformat(), 'finished_at': None, 'workflow': workflow,
        'provenance': 'LIVE_TUSHARE_RELAY' if live else 'SYNTHETIC_TEST_ONLY', 'plan': queries,
        'plan_sha256': sha256(dumps(queries)).hexdigest(), 'calls': [], 'files': {}, 'retry_waits': [30]}
    bodies, total = {}, 0
    def checkpoint():
        (root/'receipt.json').write_bytes(dumps(receipt))
    for query in queries:
        call = {**query, 'status': 'REQUEST_STARTED', 'attempts': []}
        receipt['calls'].append(call); checkpoint()
        try:
            result = request(query['api'], query['params'])
            require(result['api'] == query['api'] and result['params'] == query['params']
                    and isinstance(result['attempts'], list) and len(result['attempts']) <= 2
                    and (result['attempts'] or result['status'] == 'REQUEST_BUDGET_EXHAUSTED'),
                    'TRANSPORT_CONTRACT_FAILED')
            call['status'] = result['status']
            for i, a in enumerate(result['attempts'], 1):
                require(a['attempt'] == i, 'TRANSPORT_CONTRACT_FAILED')
                saved = {k: a.get(k) for k in ('attempt', 'http_status', 'requested_at', 'received_at', 'classification')}
                saved['headers'] = {k: v for k, v in a.get('headers', {}).items() if k in
                    ('X-Request-ID', 'X-Cache', 'X-RateLimit-Remaining', 'X-RateLimit-IP-Remaining', 'Retry-After')}
                credential = os.environ.get('TUSHARE_PROXY_API_KEY', '') if live else ''
                require(not credential or credential not in json.dumps(saved, ensure_ascii=False), 'CREDENTIAL_REFLECTION')
                raw = a.get('raw'); saved['response_file'] = None
                if raw is not None:
                    require(isinstance(raw, bytes) and len(raw) <= MAX_BODY and total+len(raw) <= MAX_TOTAL, 'BYTE_BUDGET')
                    require(not credential or credential.encode() not in raw, 'CREDENTIAL_REFLECTION')
                    name = f'raw/{len(receipt["calls"]):02}-{i}.json'
                    with (root/name).open('xb') as f:
                        f.write(raw)
                    bodies[name] = raw; total += len(raw)
                    receipt['files'][name] = {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
                    saved['response_file'] = name
                call['attempts'].append(saved)
        except Exception as exc:
            call['status'] = str(exc) if str(exc) in TERMINAL else 'SOURCE_REQUEST_FAILED'
            call['error_type'] = type(exc).__name__
        checkpoint()
        if call['status'] in TERMINAL:
            break
    receipt['finished_at'] = clock(); checkpoint()
    report = build(receipt, bodies)
    require(len(dumps(report)) <= 1024*1024, 'REPORT_SIZE')
    (root/'report.json').write_bytes(dumps(report))
    (root/'summary.md').write_text(render(report), encoding='utf-8')
    return report


def verify(root, expected_workflow=None):
    root = safe_root(root)
    for name, limit in (('receipt.json', 256*1024), ('report.json', 1024*1024), ('summary.md', 64*1024)):
        require(safe_root(root/name).stat().st_size <= limit, 'SAVED_FILE_SIZE')
    receipt = json.loads((root/'receipt.json').read_bytes(), object_pairs_hook=unique)
    require(receipt['version'] == VERSION and receipt['source'] == SOURCE
            and receipt['retry_waits'] == [30], 'CAPTURE_VERSION')
    require(receipt['provenance'] in ('LIVE_TUSHARE_RELAY', 'SYNTHETIC_TEST_ONLY'), 'PROVENANCE')
    require(expected_workflow is None or receipt['workflow'] == expected_workflow, 'WORKFLOW_IDENTITY')
    if receipt['provenance'] == 'LIVE_TUSHARE_RELAY':
        require(receipt['workflow'] == workflow_identity(receipt['workflow']), 'WORKFLOW_IDENTITY')
    start, end = (datetime.fromisoformat(receipt[k]) for k in ('observed_at', 'finished_at'))
    require(start.tzinfo is not None and end.tzinfo is not None and start <= end <= start+timedelta(minutes=16), 'CAPTURE_CLOCK')
    require(1 <= len(receipt['calls']) <= MAX_CALLS, 'CALL_BUDGET')
    stopped, last, total = False, start, 0
    bodies = {}
    for n, call in enumerate(receipt['calls'], 1):
        require(not stopped and call['status'] != 'REQUEST_STARTED' and len(call['attempts']) <= 2, 'INCOMPLETE_OR_AFTER_STOP')
        stopped = call['status'] in TERMINAL
        for i, a in enumerate(call['attempts'], 1):
            require(a['attempt'] == i, 'ATTEMPT_ORDER')
            asked, got = (datetime.fromisoformat(a[k]) for k in ('requested_at', 'received_at'))
            require(asked.tzinfo is not None and got.tzinfo is not None and last <= asked <= got <= end, 'REQUEST_CLOCK')
            if i > 1:
                require(call['attempts'][i-2]['classification'] == 'TEMPORARY_QUEUE'
                        and asked >= last+timedelta(seconds=30), 'RETRY_CONTRACT')
            last = got
            name = a['response_file']
            if name is not None:
                require(name == f'raw/{n:02}-{i}.json' and name not in bodies, 'RAW_PATH')
                path = safe_root(root/name)
                require(path.stat().st_size <= MAX_BODY, 'BODY_SIZE')
                raw = path.read_bytes(); total += len(raw)
                require(total <= MAX_TOTAL and receipt['files'][name] ==
                        {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}, 'RAW_IDENTITY')
                bodies[name] = raw
        if call['status'] == 'SUCCESS':
            require(call['attempts'] and call['attempts'][-1]['classification'] == 'SUCCESS'
                    and call['attempts'][-1]['http_status'] == 200
                    and call['attempts'][-1]['response_file'] in bodies, 'SUCCESS_BODY_REQUIRED')
    require(set(bodies) == set(receipt['files']) ==
            {p.relative_to(root).as_posix() for p in (root/'raw').iterdir()}, 'RAW_INVENTORY')
    report = build(receipt, bodies)
    require((root/'report.json').read_bytes() == dumps(report)
            and (root/'summary.md').read_text(encoding='utf-8') == render(report), 'REPLAY_DIFFERS')
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--codes', default='')
    p.add_argument('--start', default='')
    p.add_argument('--end', default='')
    p.add_argument('--verify', action='store_true')
    args = p.parse_args()
    identity = workflow_identity(os.environ)
    report = verify(args.output, identity) if args.verify else capture(args.output,
        codes=args.codes.split(','), start=args.start, end=args.end,
        observed_at=datetime.now(timezone.utc), workflow=identity)
    print(render(report))
    return 0 if report['status'] == 'COMPLETE_PROVIDER_DAILY_WINDOWS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
