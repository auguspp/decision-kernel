"""One-time bounded FTShare historical bars for 14 YinQuan symbols; not a PIT claim."""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

VERSION = 'yinquan-ftshare-56-one-shot-v1'
ROUTE = 'yinquan_ftshare_56'
SYMBOLS = (
    '000001.SZ', '000002.SZ', '000006.SZ', '000007.SZ',
    '000008.SZ', '000009.SZ', '000010.SZ', '000099.SZ',
    '000151.SZ', '000155.SZ', '600395.SH', '600397.SH',
    '603551.SH', '603580.SH',
)
PERIODS = ((2023, 12, 31), (2024, 12, 31), (2025, 12, 31), (2026, 9, 30))
SHANGHAI = ZoneInfo('Asia/Shanghai')
MAX_CALLS, MAX_RESPONSE, MAX_TOTAL = 56, 2 * 1024 * 1024, 48 * 1024 * 1024
OUTPUT_COLUMNS = ('date', 'open', 'high', 'low', 'close', 'turnover_rate',
                  'volume', 'turnover', 'code')

def require(ok, why):
    if not ok:
        raise ValueError(why)

def milliseconds(d, end):
    t = time(23, 59, 59, 999000) if end else time(0, 0)
    return int(datetime.combine(d, t, SHANGHAI).timestamp() * 1000)

def plan():
    result = []
    for symbol in SYMBOLS:
        for year, month, last in PERIODS:
            begin, finish = date(year, 1, 1), date(year, month, last)
            params = {'symbol': symbol, 'interval_unit': 'day', 'adjust_kind': 'none',
                      'since_ts_millis': milliseconds(begin, False),
                      'until_ts_millis': milliseconds(finish, True)}
            result.append({'symbol': symbol, 'period': str(year),
                           'first': begin.isoformat(), 'last': finish.isoformat(),
                           'route': ROUTE, 'params': params})
    require(len(result) == MAX_CALLS and len(set(SYMBOLS)) == len(SYMBOLS), 'PLAN_INTEGRITY')
    return result

def validate_request(params):
    require(isinstance(params, dict) and any(params == p['params'] for p in plan()),
            'YINQUAN_REQUEST_SCOPE')

def parse_clock(value):
    require(isinstance(value, str), 'CLOCK_INVALID')
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('CLOCK_INVALID') from exc
    require(d.tzinfo is not None and d.utcoffset() is not None, 'CLOCK_UNZONED')
    return d

def number(value, *, positive=False, integer=False, optional=False):
    if value is None and optional:
        return None
    require(type(value) in (str, int, float, Decimal), 'NUMBER_TYPE')
    try:
        x = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('NUMBER_INVALID') from exc
    require(x.is_finite() and len(x.as_tuple().digits) <= 32
            and (x > 0 if positive else x >= 0)
            and (not integer or x == x.to_integral_value()), 'NUMBER_RANGE')
    return str(x)

def decode(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_RESPONSE, 'BODY_SIZE')
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            require(k not in obj, 'DUPLICATE_JSON_KEY')
            obj[k] = v
        return obj
    def reject(_):
        raise ValueError('NONFINITE_JSON')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique,
                      parse_float=Decimal, parse_constant=reject)

def window_bars(raw, item):
    data = decode(raw)
    if isinstance(data, dict):
        require(type(data.get('code')) is int and data['code'] in (0, 200),
                'PROVIDER_REJECTED')
        require(set(data) <= {'code', 'data', 'message'}
                and (data.get('message') is None or isinstance(data['message'], str)),
                'ENVELOPE_INVALID')
        data = data.get('data')
    require(isinstance(data, list) and len(data) <= 370, 'BAR_CONTAINER_INVALID')
    result = {}
    for bar in data:
        require(isinstance(bar, dict), 'BAR_INVALID')
        opened, closed = bar.get('ts_millis_open'), bar.get('ts_millis')
        require(type(opened) is int and type(closed) is int and
                item['params']['since_ts_millis'] <= opened <= closed <= item['params']['until_ts_millis'],
                'BAR_TIME_OUT_OF_WINDOW')
        start_day = datetime.fromtimestamp(opened / 1000, SHANGHAI).date().isoformat()
        end_day = datetime.fromtimestamp(closed / 1000, SHANGHAI).date().isoformat()
        require(start_day == end_day and item['first'] <= end_day <= item['last'],
                'BAR_DATE_MISMATCH')
        require(end_day not in result, 'DUPLICATE_BAR')
        values = {k: number(bar.get(k), positive=k in ('open', 'high', 'low', 'close'),
                            integer=k == 'volume', optional=k == 'turnover_rate')
                  for k in ('open', 'high', 'low', 'close', 'volume',
                            'turnover', 'turnover_rate')}
        o, h, l, c = (Decimal(values[k]) for k in ('open', 'high', 'low', 'close'))
        require(l <= o <= h and l <= c <= h, 'PRICE_RANGE_INVALID')
        result[end_day] = values
    return result

def normalized(bodies):
    specs = plan()
    csvs, coverage = {}, []
    for i, symbol in enumerate(SYMBOLS):
        bars, segments = {}, []
        for j in range(4):
            spec = specs[4*i+j]
            group = window_bars(bodies[4*i+j], spec)
            require(not (set(bars) & set(group)), 'CROSS_WINDOW_DUPLICATE')
            bars.update(group)
            segments.append({'year': spec['period'], 'rows': len(group),
                             'first': min(group) if group else None,
                             'last': max(group) if group else None})
        out = io.StringIO(newline='')
        writer = csv.writer(out, lineterminator='\n')
        writer.writerow(OUTPUT_COLUMNS)
        for d in sorted(bars):
            b = bars[d]
            writer.writerow((d, b['open'], b['high'], b['low'], b['close'],
                             b['turnover_rate'] or '', b['volume'], b['turnover'], symbol))
        name = symbol[:6] + '.csv'
        csvs[name] = out.getvalue().encode('utf-8')
        coverage.append({'symbol': symbol, 'rows': len(bars), 'segments': segments,
                         'first': min(bars) if bars else None,
                         'last': max(bars) if bars else None,
                         'hsl_nonnull': sum(b['turnover_rate'] is not None for b in bars.values()),
                         'hsl_null': sum(b['turnover_rate'] is None for b in bars.values()),
                         'qualification': 'OBSERVED_ROWS_ONLY_NOT_EXCHANGE_CALENDAR_CERTIFIED'})
    return csvs, coverage

def workflow_identity(env):
    require(env.get('GITHUB_REPOSITORY') == 'auguspp/decision-kernel' and
            env.get('GITHUB_REF') == 'refs/heads/main' and
            env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and
            env.get('GITHUB_RUN_ATTEMPT') == '1' and
            re.fullmatch('[0-9a-f]{40}', env.get('GITHUB_SHA', '')) and
            env.get('GITHUB_SHA') == env.get('EXPECTED_CODE') and
            re.fullmatch('[1-9][0-9]*', env.get('GITHUB_RUN_ID', '')),
            'WORKFLOW_IDENTITY_INVALID')
    return {k: env[k] for k in ('GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_EVENT_NAME',
                                 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA', 'GITHUB_RUN_ID')}

def now():
    return datetime.now(timezone.utc).isoformat()

def write(root, report):
    (root / 'receipt.json').write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n',
        encoding='utf-8')

def capture(root, env, *, fetch=None, clock=now):
    root = Path(root)
    require(not root.exists() and not root.is_symlink()
            and not any(p.is_symlink() for p in root.parents), 'OUTPUT_EXISTS')
    identity = workflow_identity(env)
    root.mkdir(parents=True)
    (root / 'raw').mkdir()
    (root / 'prices').mkdir()
    report = {'version': VERSION, 'source': 'FTSHARE', 'workflow': identity,
              'plan': plan(), 'max_requests': MAX_CALLS, 'max_raw_bytes': MAX_TOTAL,
              'prior_tushare_run': '37718496941_NOT_REPLAYED',
              'retry': False, 'fallback': False, 'published_to_kernel': False,
              'historical_pit': 'NOT_ESTABLISHED', 'investment_authority': 'NONE',
              'requests': [], 'status': 'INCOMPLETE', 'started_at': clock()}
    write(root, report)
    if fetch is None:
        from . import ftshare_market_inputs as client
        fetch = client.request
    last, bodies, total = parse_clock(report['started_at']), {}, 0
    for i, spec in enumerate(plan()):
        item = {'index': i, **spec, 'status': 'REQUEST_STARTED', 'raw_file': None,
                'requested_at': clock()}
        report['requests'].append(item)
        write(root, report)
        try:
            at = parse_clock(item['requested_at'])
            require(at >= last, 'CLOCK_REVERSED')
            status, raw = fetch(ROUTE, dict(spec['params']))
            item['received_at'] = clock()
            received = parse_clock(item['received_at'])
            require(received >= at, 'CLOCK_REVERSED')
            last = received
            require(type(status) is int and isinstance(raw, bytes)
                    and 0 < len(raw) <= MAX_RESPONSE and total + len(raw) <= MAX_TOTAL,
                    'RESPONSE_SIZE')
            total += len(raw)
            filename = f'raw/{i+1:02d}-{spec["symbol"]}-{spec["period"]}.json'
            (root / filename).write_bytes(raw)
            item.update(raw_file=filename, bytes=len(raw),
                        sha256=sha256(raw).hexdigest(), http_status=status)
            require(status == 200, 'HTTP_REJECTED')
            bars = window_bars(raw, spec)
            item['bar_count'] = len(bars)
            item['status'] = 'VALIDATED'
            bodies[i] = raw
        except Exception as exc:
            item['status'] = 'SOURCE_OR_SCHEMA_STOP'
            item['error_type'] = type(exc).__name__
            report['status'] = 'STOPPED_AT_' + str(i)
            report['finished_at'] = clock()
            write(root, report)
            return report
        write(root, report)
    csvs, coverage = normalized(bodies)
    for filename, data in csvs.items():
        (root / 'prices' / filename).write_bytes(data)
    report.update(status='COMPLETE_CAPTURE_NOT_PIT', coverage=coverage,
                  csv_sha256={k: sha256(v).hexdigest() for k, v in csvs.items()},
                  finished_at=clock())
    write(root, report)
    return report

def verify(root, *, expected_identity=None):
    root = Path(root)
    require(not root.is_symlink() and not any(p.is_symlink() for p in root.parents)
            and all(not p.is_symlink() for p in root.rglob('*')), 'INPUT_SYMLINK')
    report = json.loads((root / 'receipt.json').read_bytes())
    require(report['version'] == VERSION and report['source'] == 'FTSHARE'
            and report['plan'] == plan() and report['max_requests'] == MAX_CALLS
            and report['max_raw_bytes'] == MAX_TOTAL and report['retry'] is False
            and report['fallback'] is False and report['published_to_kernel'] is False
            and report['historical_pit'] == 'NOT_ESTABLISHED'
            and report['investment_authority'] == 'NONE', 'RECEIPT_INVALID')
    identity = report['workflow']
    require(expected_identity is None or identity == expected_identity, 'WORKFLOW_DIFFERS')
    require(identity == workflow_identity({**identity, 'EXPECTED_CODE': identity['GITHUB_SHA']}),
            'STORED_WORKFLOW_IDENTITY')
    start = parse_clock(report['started_at'])
    finish = parse_clock(report['finished_at'])
    require(start <= finish, 'RUN_CLOCK_REVERSED')
    calls = report['requests']
    require(isinstance(calls, list) and 1 <= len(calls) <= MAX_CALLS, 'CALL_COUNT')
    raw_by_index, last, total = {}, start, 0
    for i, item in enumerate(calls):
        spec = plan()[i]
        require(item['index'] == i and
                all(item[k] == spec[k] for k in ('symbol', 'period', 'first', 'last', 'route', 'params')),
                'PLAN_MISMATCH')
        at = parse_clock(item['requested_at'])
        require(last <= at <= finish, 'REQUEST_CLOCK')
        if item['raw_file'] is None:
            require(i == len(calls)-1 and item['status'] == 'SOURCE_OR_SCHEMA_STOP',
                    'NO_RESPONSE_SCOPE')
            last = at
            continue
        received = parse_clock(item['received_at'])
        require(at <= received <= finish, 'RECEIPT_CLOCK')
        last = received
        expected = f'raw/{i+1:02d}-{spec["symbol"]}-{spec["period"]}.json'
        require(item['raw_file'] == expected, 'RESPONSE_PATH')
        raw = (root / expected).read_bytes()
        total += len(raw)
        require(len(raw) == item['bytes'] and sha256(raw).hexdigest() == item['sha256']
                and len(raw) <= MAX_RESPONSE and total <= MAX_TOTAL, 'RAW_INTEGRITY')
        if item['status'] == 'VALIDATED':
            require(item['http_status'] == 200
                    and len(window_bars(raw, spec)) == item['bar_count'],
                    'BAR_REBUILD_DIFFERENCE')
            raw_by_index[i] = raw
        else:
            require(i == len(calls)-1 and item['status'] == 'SOURCE_OR_SCHEMA_STOP',
                    'STOP_SCOPE')
    if report['status'] == 'COMPLETE_CAPTURE_NOT_PIT':
        require(len(raw_by_index) == MAX_CALLS, 'FALSE_COMPLETE')
        csvs, coverage = normalized(raw_by_index)
        require(coverage == report['coverage']
                and {k: sha256(v).hexdigest() for k, v in csvs.items()} == report['csv_sha256'],
                'COVERAGE_REBUILD_DIFFERENCE')
        for name, content in csvs.items():
            require((root / 'prices' / name).read_bytes() == content,
                    'CSV_REBUILD_DIFFERENCE')
    else:
        require(report['status'] == 'STOPPED_AT_' + str(len(calls)-1)
                and not any((root / 'prices').iterdir()), 'STOP_STATUS')
    expected_files = {'receipt.json'} | {c['raw_file'] for c in calls if c['raw_file']}
    if report['status'] == 'COMPLETE_CAPTURE_NOT_PIT':
        expected_files |= {'prices/' + n for n in report['csv_sha256']}
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
            == expected_files, 'ARTIFACT_FILES')
    return {'status': 'OFFLINE_REBUILT', 'network_calls': 0,
            'source_calls_recorded': len(calls), 'capture_status': report['status'],
            'raw_bodies_verified': sum(c['raw_file'] is not None for c in calls)}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('operation', choices=('capture', 'verify'))
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    if args.operation == 'capture':
        result = capture(args.output, os.environ)
        print(json.dumps({'status': result['status'], 'started_requests': len(result['requests'])}))
        return 0 if result['status'] == 'COMPLETE_CAPTURE_NOT_PIT' else 1
    print(json.dumps(verify(args.output)))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
