"""One explicit C2 FTShare diagnostic; never a production or fallback provider.

Reuse the existing transport, history contracts, selector and comparison. Raw
custody is explicitly authorized for this new pilot. Existing comparison runs
and their ephemeral-raw restriction are unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import os
from pathlib import Path
import re
from types import SimpleNamespace

from . import ftshare_stock_history_comparison as history
from .ftshare_financial import decode, raw_json
from . import ftshare_discovery as common

TITLE = 'FTShare C2 bounded pilot 20260930'
MODE = 'c2-pilot-20260930'
ROUTE = 'c2_quotes'
ENDPOINT = 'https://market.ft.tech/gateway/api/v1/market/data/daec/stocks'
FILTER = '(ex_id = "XSHE" OR ex_id = "XSHG" OR ex_id = "BJSE")'
MAX_CALLS, MAX_QUOTE_PAGES = 100, 88  # reserve existing maximum twelve history calls
BASE_READING = '2ba96a11e7e0d208bd1f303124f5ebfd94f2971c'
BASE_DETAIL_HASH = 'fad9e15c88576dd0326a6d0b62753ce88e3c41ab7070e34f1424a8d29f1effc6'
require = common._require


def parameters(page):
    require(type(page) is int and 1 <= page <= MAX_QUOTE_PAGES, 'PAGE_BUDGET')
    # Official handler maps CLI page_no to HTTP page. Do not exclude null latest.
    return {'order_by': 'latest asc', 'page': page, 'page_size': 100, 'filter': FILTER}


def validate_request(params):
    require(isinstance(params, dict) and params == parameters(params.get('page')), 'REQUEST_SCOPE')


def one_shot_scope(runs, total, current_id):
    """Complete native inventory: no second attempt under this authorization."""
    require(type(total) is int and total == len(runs)
            and len({r['id'] for r in runs}) == total, 'PILOT_RUN_SCOPE_INCOMPLETE')
    selected = [r for r in runs if r.get('display_title') == TITLE]
    require(len(selected) == 1 and selected[0]['id'] == current_id
            and selected[0]['run_attempt'] == 1
            and selected[0]['event'] == 'workflow_dispatch'
            and selected[0]['head_branch'] == 'main', 'PILOT_AUTHORIZATION_ALREADY_USED')


def quote_page(obj, page):
    require(isinstance(obj, dict) and type(obj.get('code')) is int
            and obj['code'] in (0, 200), 'PROVIDER_REJECTED')
    data = obj.get('data')
    require(isinstance(data, dict) and type(data.get('page')) is int
            and data['page'] == page and type(data.get('page_size')) is int
            and data['page_size'] == 100, 'PAGE_IDENTITY')
    rows = data.get('items')
    require(isinstance(rows, list) and len(rows) <= 100
            and all(isinstance(r, dict) for r in rows), 'PAGE_ROWS')
    # Metadata is reported, never used as filtered denominator or stop condition.
    return rows, {k: data.get(k) for k in ('total_pages', 'total_items')}


def positive(value):
    if type(value) not in (str, int, Decimal):
        return None
    try:
        n = Decimal(value)
    except InvalidOperation:
        return None
    return n if n.is_finite() and n > 0 else None


def inventory(pages, complete):
    points, locations, ids, invalid, stamps = [], {}, [], [], Counter()
    statuses, st = Counter(), Counter()
    for page, rows in enumerate(pages, 1):
        for offset, row in enumerate(rows):
            symbol = row.get('symbol')
            status = row.get('status')
            statuses[str(status)] += 1
            st[str(row.get('st'))] += 1
            stamp = row.get('ts_millis')
            if type(stamp) is int and 0 <= stamp <= 253402214400000:
                stamps[datetime.fromtimestamp(stamp / 1000, history.ZONE).isoformat()] += 1
            else:
                stamps['INVALID_OR_MISSING'] += 1
            if not isinstance(symbol, str) or not re.fullmatch(r'\d{6}\.(SH|SZ|BJ)', symbol) or (
                    row.get('symbol_id') not in (None, symbol[:6])):
                invalid.append([page, offset]); continue
            ids.append(symbol)
            latest, previous = positive(row.get('latest')), positive(row.get('prev_close'))
            if latest is None or previous is None:
                latest = previous = None
            points.append(SimpleNamespace(thscode=symbol, last_price=latest, prev_price=previous))
            locations[symbol] = [page, offset]
    duplicates = {s: n for s, n in Counter(ids).items() if n > 1}
    out = {'actual_rows': sum(map(len, pages)), 'unique_valid_symbols': len(set(ids)),
           'invalid_rows': invalid, 'invalid_count': len(invalid), 'duplicate_symbols': duplicates,
           'duplicate_excess_rows': sum(n-1 for n in duplicates.values()),
           'unpriced_rows': sum(p.last_price is None for p in points),
           'status_counts': dict(statuses), 'st_counts': dict(st),
           'timestamp_counts': dict(stamps), 'pagination_complete': complete,
           'session': history.END, 'session_qualification': 'LATEST_PAGE_SESSION_NOT_ESTABLISHED',
           'timestamp_semantics': 'PROVIDER_QUOTE_TIMESTAMP_NOT_INDEPENDENTLY_ESTABLISHED',
           'status': 'INPUT_UNAVAILABLE_NOT_QUIET', 'selection': None}
    if complete and not invalid and not duplicates and points:
        from .independent_stock_observations import _sample
        batch = SimpleNamespace(points=points, returned_unique_rows=len(points))
        digest = sha256(raw_json(pages)).hexdigest()
        _, _, _, selection = _sample(batch, locations, 16, digest, source_key='ftshare_rows_hash')
        out.update(status='COMPLETE_LATEST_ROWS_DATE_UNQUALIFIED', selection=selection)
    return out


def capture(output, prior, *, fetch=None, clock=common.now):
    from . import ftshare_market_inputs as client
    fetch = fetch or client.request
    require(not output.exists() and not output.is_symlink()
            and not any(p.is_symlink() for p in output.parents), 'UNSAFE_OUTPUT')
    output.mkdir(parents=True)
    (output / 'raw').mkdir()
    result = {'version': 'ftshare-c2-bounded-pilot-v1', 'source': 'FTShare',
              'target_session': history.END, 'max_source_requests': MAX_CALLS,
              'account_quota': {'daily': 1000, 'resets_daily': True, 'evidence': 'HUMAN_ACCOUNT_PAGE_CONFIRMATION'},
              'sample_basis': {'reading': BASE_READING, 'path': 'details/stock/independent-observations.json',
                               'sha256': BASE_DETAIL_HASH,
                               'symbols': list(history.SYMBOLS), 'rule': 'FIRST_THREE_CURRENT_INDEPENDENT_SELECTED'},
              'started_at': clock(), 'calls': [], 'snapshot': None, 'history': None,
              'production_admission': False, 'investment_authority': 'NONE'}
    last = common._clock(result['started_at'])

    def checkpoint():
        result['source_requests'] = len(result['calls'])
        (output / 'receipt.json').write_bytes(raw_json(result))

    def recorded(route, params):
        nonlocal last
        require(len(result['calls']) < MAX_CALLS, 'CALL_BUDGET')
        at = clock()
        require(common._clock(at) >= last, 'CLOCK_REVERSED')
        call = {'route': route, 'method': 'GET',
                'credential_header': 'FTSHARE_API_KEY_FROM_EXISTING_SECRET_VALUE_NOT_RETAINED',
                'headers': {'Accept': 'application/json', 'Accept-Encoding': 'identity',
                            'User-Agent': 'decision-kernel/' + client.VERSION,
                            **({'X-Client-Name': 'ft-claw', 'Content-Type': 'application/json'} if route == ROUTE else {})},
                'endpoint': ENDPOINT if route == ROUTE else history.ROUTES[route],
                'params': params, 'requested_at': at, 'status': 'REQUEST_STARTED',
                'http_status': None, 'provider_code': None, 'response_file': None}
        result['calls'].append(call)
        checkpoint()  # unknown transport outcomes count toward the budget
        try:
            status, raw = fetch(route, params)
            received = clock()
            require(common._clock(received) >= common._clock(at), 'CLOCK_REVERSED')
            last = common._clock(received)
            require(type(status) is int and isinstance(raw, bytes)
                    and len(raw) <= history.MAX_BYTES, 'RESPONSE_INVALID')
            filename = f'raw/{len(result["calls"]):03}.json'
            (output / filename).write_bytes(raw)
            call.update(status='RAW_CAPTURED', http_status=status, received_at=received,
                        response_file=filename, bytes=len(raw), sha256=sha256(raw).hexdigest())
            try:
                obj = decode(raw)
                if isinstance(obj, dict) and type(obj.get('code')) is int:
                    call['provider_code'] = obj['code']
            except (ValueError, TypeError, OverflowError, RecursionError):
                pass
            return status, raw
        except Exception:
            call['status'] = 'RESPONSE_UNAVAILABLE'
            raise
        finally:
            checkpoint()

    pages, complete, halted = [], False, None
    for page in range(1, MAX_QUOTE_PAGES+1):
        try:
            status, raw = recorded(ROUTE, parameters(page))
            obj = decode(raw)
            code = obj.get('code') if isinstance(obj, dict) else None
            if status in history.STOP or type(code) is int and code in history.STOP:
                halted = 'SOURCE_REJECTED_STOP_CAUSE_UNKNOWN'
                break
            require(status == 200, 'HTTP_REJECTED')
            rows, meta = quote_page(obj, page)
            result['calls'][-1]['pagination_metadata'] = meta
            pages.append(rows)
            if not rows:  # explicit empty tail, never total_items or a short-page guess
                complete = True; break
        except (ValueError, TypeError, OSError, KeyError, OverflowError):
            halted = 'SNAPSHOT_REQUEST_OR_SCHEMA_FAILURE'; break
    result['snapshot'] = inventory(pages, complete)
    result['snapshot']['halt_reason'] = halted if halted else (None if complete else 'PAGE_BUDGET_INCOMPLETE')
    checkpoint()
    # Even a complete latest-page inventory is not dated market qualification.
    # Three pre-frozen names help test that semantic, without extending selection.
    if complete and result['snapshot']['selection'] is not None and not halted:
        result['history'] = history.capture(output / 'history', prior, fetch=recorded, clock=clock)
        result['history']['raw_custody'] = 'PILOT_ORIGINALS_30_DAY_ACTIONS_ARTIFACT'
        (output / 'history' / 'safe-report' / 'report.json').write_bytes(raw_json(result['history']))
    else:
        result['history'] = {'source_calls': 0, 'status': 'NOT_REQUESTED_SNAPSHOT_INCOMPLETE'}
    result['finished_at'] = clock()
    checkpoint()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    args = parser.parse_args()
    env = os.environ
    require(env.get('GITHUB_REPOSITORY') == 'auguspp/decision-kernel'
            and env.get('GITHUB_REF') == 'refs/heads/main'
            and env.get('GITHUB_RUN_ATTEMPT') == '1'
            and env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
            and env.get('GITHUB_JOB') == 'pilot-ftshare-c2'
            and env.get('FTSHARE_COMPARISON') == MODE
            and re.fullmatch('[0-9a-f]{40}', env.get('EXPECTED_CODE', '')) is not None
            and env.get('GITHUB_SHA') == env.get('EXPECTED_CODE'), 'EXECUTION_IDENTITY')
    result = capture(args.output, history.reference(args.reference))
    result['workflow'] = {k: env[k] for k in ('GITHUB_REPOSITORY', 'GITHUB_SHA',
        'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_EVENT_NAME', 'GITHUB_JOB')}
    (args.output / 'receipt.json').write_bytes(raw_json(result))
    print(raw_json({'source_requests': result['source_requests'],
                    'status': result['snapshot']['status']}).decode())


if __name__ == '__main__':
    main()
