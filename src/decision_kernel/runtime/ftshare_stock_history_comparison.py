"""One explicit three-stock FTShare comparison, using the existing secret owner.

Only producer-side diagnostics leave the runner. Raw bodies are local/ephemeral;
this is not a durable source archive or independent replay/adjustment acceptance.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import os
from pathlib import Path
import re
from urllib.error import URLError
from zoneinfo import ZoneInfo

from . import ftshare_discovery as original
from .ftshare_financial import decode, raw_json

VERSION = 'ftshare-three-stock-comparison-v1'
RUN_TITLE = 'FTShare three-stock comparison 20260930'
SYMBOLS = ('001246.SZ', '920202.BJ', '301190.SZ')
START, END = '2026-07-07', '2026-09-30'
SINCE, UNTIL = 1783353600000, 1790783999999
ZONE = ZoneInfo('Asia/Shanghai')
BASE = 'https://market.ft.tech/gateway/api/'
ROUTES = {'history_candles': BASE + 'v1/market/data/stock-candlesticks',
          'history_factors': BASE + 'v1/market/data/stock-adjust-factor',
          'history_dividends': BASE + 'v2/market/data/stock-dividends-effective'}
MAX_CALLS, MAX_BYTES = 12, 2 * 1024 * 1024
STOP = {401: 'AUTHENTICATION_FAILED', 403: 'ENTITLEMENT_DENIED', 429: 'RATE_LIMITED'}
require = original._require
# Exact already-retained HiThink capture, not another source acquisition.
REFERENCE_RUN, REFERENCE_ARTIFACT = 36815556951, 11141865519
REFERENCE_HASH = '60c2a60017ba3f3aca53e9fe4467e3ea397d807c8484df8fa707789571e301ef'
REFERENCE_FILES = {
    '001246.SZ': ('16', 'a131f76c6634691eaf64d0b66634d771678a0fe05c64a12111a1d19c30f995cd',
                  '18', 'ebe9a6462a5bfe350460691192621e5228247520c7ef7747d4643f1a7b96066b'),
    '920202.BJ': ('19', 'fbb6c75bc28707cc5f4fd00b083aec5826211c7e8bbc8391015094597917e833',
                 '21', '8f220c2f533df1a9ceb6cf859640ec99a378d89c5b326fc2a36e4aa59e6d4f7c'),
    '301190.SZ': ('22', '2161561935b83e84119e9182eec104cf96d9989e3fd3df5915be6ba885e5f130',
                 '24', '95c2881145b5f18260c480e0b3575e6fb8640a8810ba9a881645733006675194'),
}


def is_comparison_run(run):
    """Only this exact explicit manual purpose is outside production attempts."""
    return (run.get('event') == 'workflow_dispatch' and run.get('head_branch') == 'main'
            and run.get('path') == '.github/workflows/radar-smart-money.yml'
            and run.get('display_title') == RUN_TITLE)


def parameters(route, symbol, page=1):
    require(route in ROUTES and symbol in SYMBOLS, 'REQUEST_SCOPE')
    if route == 'history_candles':
        require(page == 1, 'PAGE_BUDGET')
        return {'symbol': symbol, 'interval_unit': 'day', 'adjust_kind': 'none',
                'since_ts_millis': SINCE, 'until_ts_millis': UNTIL}
    if route == 'history_factors':
        require(type(page) is int and 1 <= page <= 2, 'PAGE_BUDGET')
        # YYYYMMDD is documented by FTShare-python-sdk 23eb471c stock_adjust_factor.
        return {'symbol': symbol, 'start_date': '20260707', 'end_date': '20260930',
                'page': page, 'page_size': 50}
    require(page == 1, 'PAGE_BUDGET')
    # Omitting ann_date bounds avoids losing a pre-window announcement whose
    # ex-dividend date lies in the window. One page only, never --all.
    return {'symbol': symbol, 'page': 1, 'page_size': 200}


def validate_request(route, params):
    require(isinstance(params, dict), 'REQUEST_SCOPE')
    require(params == parameters(route, params.get('symbol'), params.get('page', 1)), 'REQUEST_SCOPE')


def reference(root):
    """Read exact known original bodies; ignore unrelated files in the artifact."""
    out = {}
    for symbol, (bars, bh, actions, ah) in REFERENCE_FILES.items():
        values = []
        for number, digest in ((bars, bh), (actions, ah)):
            path = root / 'responses' / (number + '.json')
            require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), 'REFERENCE_PATH')
            require(0 < path.stat().st_size <= MAX_BYTES, 'REFERENCE_SIZE')
            raw = path.read_bytes()
            require(sha256(raw).hexdigest() == digest, 'REFERENCE_HASH')
            values.append(decode(raw))
        out[symbol] = dict(zip(('bars', 'actions'), values))
    return out


def number(value):
    require(type(value) in (str, int, Decimal), 'NUMBER_TYPE')
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise original.DiscoveryError('NUMBER_INVALID') from None
    require(result.is_finite() and result >= 0, 'NUMBER_INVALID')
    return result


def session(ts):
    require(type(ts) is int and SINCE <= ts <= UNTIL, 'CANDLE_WINDOW')
    return datetime.fromtimestamp(ts / 1000, ZONE).date().isoformat()


def candle_rows(rows, *, hithink=False):
    require(isinstance(rows, list) and len(rows) <= 86, 'CANDLE_SHAPE')
    out = {}
    for row in rows:
        require(isinstance(row, dict), 'CANDLE_SHAPE')
        day = session(row.get('date_ms' if hithink else 'ts_millis'))
        require(day not in out, 'CANDLE_DUPLICATE_SESSION')
        if not hithink:
            require(session(row.get('ts_millis_open')) == day
                    and row['ts_millis_open'] <= row['ts_millis'], 'CANDLE_CLOCK')
        values = {key: number(row.get(key + '_price' if hithink and key in ('open','high','low','close') else key))
                  for key in ('open', 'high', 'low', 'close', 'volume', 'turnover')}
        require(0 < values['low'] <= values['open'] <= values['high']
                and values['low'] <= values['close'] <= values['high'], 'CANDLE_OHLC')
        require(values['volume'] == values['volume'].to_integral_value(), 'CANDLE_VOLUME')
        out[day] = values
    return out


def compare_candles(rows, prior, symbol):
    require(prior.get('code') == 0 and prior['data']['thscode'] == symbol
            and prior['data']['adjust'] == 'none' and prior['data']['interval'] == '1d', 'REFERENCE_IDENTITY')
    current, old = candle_rows(rows), candle_rows(prior['data']['item'], hithink=True)
    common = sorted(current.keys() & old.keys())
    fields = ('open', 'high', 'low', 'close', 'volume', 'turnover')
    return {'status': 'PRODUCER_SIDE_RAW_BAR_COMPARISON', 'ftshare_rows': len(current),
            'field_units': {'open': 'CNY', 'high': 'CNY', 'low': 'CNY', 'close': 'CNY',
                            'volume': 'SHARES', 'turnover': 'CNY'},
            'units_qualification': 'DOCUMENTED_ON_BOTH_ENDPOINTS',
            'hithink_rows': len(old), 'matched_sessions': len(common),
            'ftshare_first_session': min(current) if current else None,
            'ftshare_last_session': max(current) if current else None,
            'only_ftshare_sessions': sorted(current.keys() - old.keys()),
            'only_hithink_sessions': sorted(old.keys() - current.keys()),
            'mismatch_counts': {k: sum(current[d][k] != old[d][k] for d in common) for k in fields},
            'max_absolute_difference': {k: str(max(abs(current[d][k] - old[d][k]) for d in common)) if common else None for k in fields},
            'empty_is_no_trading_proof': False, 'pre_listing_history_inferred': False,
            'complete_expected_session_coverage': 'UNKNOWN'}


def page_rows(obj, page, size):
    """Recognize only strict native pagination; a new envelope remains UNKNOWN."""
    require(isinstance(obj, dict) and type(obj.get('code')) is int, 'ENVELOPE_UNKNOWN')
    require(obj['code'] in (0, 200), STOP.get(obj['code'], 'PROVIDER_REJECTED'))
    body = obj.get('data')
    require(isinstance(body, dict), 'ENVELOPE_UNKNOWN')
    require(body.get('pageNum') == page and type(body.get('pageNum')) is int
            and body.get('pageSize') == size and type(body.get('pageSize')) is int, 'PAGINATION_UNKNOWN')
    rows, total, pages = (body.get(k) for k in ('records', 'total', 'pages'))
    require(type(total) is int and total >= 0 and type(pages) is int
            and pages in ({0, 1} if total == 0 else {(total + size - 1) // size}), 'PAGINATION_UNKNOWN')
    require(isinstance(rows, list) and len(rows) == min(size, max(0, total-(page-1)*size))
            and all(isinstance(row, dict) for row in rows), 'PAGINATION_INCOMPLETE')
    return rows, total, pages


def dividend_summary(rows, prior, symbol, complete):
    groups = {}
    for row in rows:
        require(row.get('symbol') == symbol, 'DIVIDEND_IDENTITY')
        # Announcement, record, payout and ex-date are not interchangeable.
        ann = row.get('ann_date')
        require(isinstance(ann, str) and date.fromisoformat(ann).isoformat() == ann, 'DIVIDEND_ANN_DATE')
        ex = row.get('ex_dividend_date')
        if ex is None:
            continue
        require(isinstance(ex, str) and date.fromisoformat(ex).isoformat() == ex, 'DIVIDEND_EX_DATE')
        if START <= ex <= END:
            groups.setdefault(ex, []).append(row)
    cash = {}
    for ex, members in groups.items():
        totals = [number(r['total_cash_dividend_ratio']) for r in members if r.get('total_cash_dividend_ratio') is not None]
        if totals:
            require(len(totals) == len(members) and len(set(totals)) == 1, 'DIVIDEND_TOTAL_CONFLICT')
            cash[ex] = totals[0]  # Duplicate group total is consumed exactly once.
        else:
            require(len(members) == 1, 'DIVIDEND_TOTAL_UNKNOWN')
            cash[ex] = number(members[0].get('cash_dividend_ratio'))
    old = {}
    if prior.get('code') == 0:
        require(prior['data']['thscode'] == symbol, 'REFERENCE_IDENTITY')
        for row in prior['data']['item']:
            ts = row.get('ex_date_ms')
            if type(ts) is int and SINCE <= ts <= UNTIL:
                ex = session(ts)
                require(ex not in old, 'REFERENCE_DUPLICATE_EX_DATE')
                old[ex] = number(row.get('dividend_per_share'))
    common = sorted(cash.keys() & old.keys())
    return {'status': 'PRODUCER_SIDE_EVENT_NUMERIC_DIAGNOSTIC', 'pagination_complete': complete,
            'returned_rows': len(rows), 'window_ex_date_groups': len(groups),
            'matched_cash_event_dates': common,
            'cash_numeric_mismatch_count': sum(cash[d] != old[d] for d in common),
            'cash_denominator': 'PRETAX_PER_SHARE_ON_BOTH_ENDPOINTS',
            'cash_comparison_qualification': 'NUMERIC_DIFFERENCE_UNQUALIFIED_UNITS',
            'cash_currency_limitation': 'FTSHARE_DIVIDEND_DOCUMENT_DOES_NOT_EXPLICITLY_NAME_CURRENCY',
            'hithink_provider_code': prior.get('code'),
            'hithink_nonzero_is_empty': False,
            'absence_established': False, 'bonus_components_comparable': 'UNKNOWN',
            'historical_availability': 'UNKNOWN'}


def capture(output, prior, *, fetch=None, clock=original.now):
    from . import ftshare_market_inputs as client
    fetch = fetch or client.request
    require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), 'UNSAFE_OUTPUT')
    output.mkdir(parents=True, exist_ok=False)
    raw_dir, report_dir = output / 'runner-local-raw', output / 'safe-report'
    raw_dir.mkdir(); report_dir.mkdir()
    result = {'version': VERSION, 'symbols': list(SYMBOLS), 'start': START, 'end': END,
              'max_source_calls': MAX_CALLS, 'automatic_retry': False, 'calls': [], 'results': [],
              'reference_run': REFERENCE_RUN, 'reference_artifact': REFERENCE_ARTIFACT,
              'reference_capture_hash': REFERENCE_HASH, 'started_at': clock(),
              'verification': 'PRODUCER_SIDE_ONLY', 'raw_custody': 'RUNNER_LOCAL_EPHEMERAL',
              'independent_raw_replay': False, 'adjusted_prices_computed': False,
              'default_provider_changed': False, 'historical_pit_qualification': 'UNKNOWN',
              'research_authority': 'NONE', 'investment_authority': 'NONE'}
    last = original._clock(result['started_at'])
    halted = None
    for symbol in SYMBOLS:
        for route in ROUTES:
            item = {'symbol': symbol, 'route': route, 'status': 'NOT_ATTEMPTED', 'pagination_complete': False}
            result['results'].append(item)
            if halted:
                item['status'] = 'NOT_ATTEMPTED_AFTER_' + halted
                continue
            rows, expected = [], None
            try:
                for page in range(1, 3 if route == 'history_factors' else 2):
                    params = parameters(route, symbol, page)
                    require(len(result['calls']) < MAX_CALLS, 'CALL_BUDGET')
                    event = {'symbol': symbol, 'route': route, 'page': page, 'parameters': params,
                             'requested_at': clock(), 'status': 'TRANSPORT_FAILURE'}
                    result['calls'].append(event)
                    require(original._clock(event['requested_at']) >= last, 'CLOCK_REVERSED')
                    status, raw = fetch(route, params)
                    event['received_at'] = clock()
                    require(original._clock(event['received_at']) >= original._clock(event['requested_at']), 'CLOCK_REVERSED')
                    last = original._clock(event['received_at'])
                    require(type(status) is int and isinstance(raw, bytes) and 0 < len(raw) <= MAX_BYTES, 'RESPONSE_INVALID')
                    (raw_dir / f'{len(result["calls"]):02}.json').write_bytes(raw)
                    event.update(http_status=status, bytes=len(raw), sha256=sha256(raw).hexdigest())
                    require(status == 200, STOP.get(status, 'HTTP_REJECTED'))
                    obj = decode(raw)
                    event['response_top_type'] = type(obj).__name__
                    if isinstance(obj, dict) and type(obj.get('code')) is int:
                        event['provider_code'] = obj['code']
                    if isinstance(obj, dict) and obj.get('code') in STOP:
                        raise original.DiscoveryError(STOP[obj['code']])
                    if route == 'history_candles':
                        # The documented response is a bare array. An envelope is
                        # not silently unwrapped, nor mistaken for zero bars.
                        item.update(compare_candles(obj, prior[symbol]['bars'], symbol))
                        event['status'] = 'RAW_CAPTURED'; break
                    got, total, pages = page_rows(obj, page, params['page_size'])
                    require(expected in (None, (total, pages)), 'PAGINATION_CHANGED')
                    expected = total, pages
                    rows.extend(got)
                    event['status'] = 'RAW_CAPTURED'
                    item.update(returned_rows=len(rows), declared_total=total, declared_pages=pages,
                                pagination_complete=page >= pages,
                                returned_field_names=sorted({k for r in rows for k in r if isinstance(k,str) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,63}',k)})[:64])
                    if page >= pages:
                        break
                    if route != 'history_factors' or pages > 2:
                        break  # Bounded partial capture, never a full-coverage claim.
                if route == 'history_factors':
                    item.update(status='RAW_FACTOR_SCHEMA_UNQUALIFIED', factor_semantics='UNKNOWN',
                                factor_date_coverage='UNKNOWN', empty_is_factor_one=False)
                elif route == 'history_dividends':
                    item.update(dividend_summary(rows, prior[symbol]['actions'], symbol, item['pagination_complete']))
            except original.DiscoveryError as exc:
                item['status'] = str(exc)
                if result['calls'] and result['calls'][-1]['symbol'] == symbol and result['calls'][-1]['route'] == route:
                    result['calls'][-1]['status'] = str(exc)
                if str(exc) in STOP.values() or str(exc) in ('AUTHENTICATION_UNAVAILABLE', 'CREDENTIAL_REFLECTION_REJECTED', 'CLOCK_REVERSED'):
                    halted = str(exc)
            except (URLError, OSError, TimeoutError):
                item['status'] = 'TRANSPORT_FAILURE'
            except (ValueError, TypeError, KeyError, OverflowError):
                item['status'] = 'PARSE_FAILURE'
    result['finished_at'] = clock()
    require(original._clock(result['finished_at']) >= last, 'CLOCK_REVERSED')
    result['source_calls'] = len(result['calls'])
    (report_dir / 'report.json').write_bytes(raw_json(result))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    env = os.environ
    require(env.get('GITHUB_REPOSITORY') == 'auguspp/decision-kernel'
            and env.get('GITHUB_REF') == 'refs/heads/main'
            and env.get('GITHUB_RUN_ATTEMPT') == '1'
            and env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
            and env.get('GITHUB_WORKFLOW') == 'radar-smart-money'
            and env.get('GITHUB_JOB') == 'compare-ftshare-stock-history'
            and env.get('FTSHARE_COMPARISON') == 'three-stock-20260930'
            and re.fullmatch('[0-9a-f]{40}', env.get('EXPECTED_CODE','')) is not None
            and env.get('GITHUB_SHA') == env.get('EXPECTED_CODE'), 'EXECUTION_IDENTITY')
    result = capture(args.output, reference(args.reference))
    result['workflow'] = {k: env[k] for k in ('GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_SHA',
        'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_EVENT_NAME', 'GITHUB_JOB')}
    (args.output / 'safe-report' / 'report.json').write_bytes(raw_json(result))
    print(raw_json({'source_calls': result['source_calls'], 'verification': result['verification'],
                    'raw_custody': result['raw_custody']}).decode(), end='')


if __name__ == '__main__':
    main()
