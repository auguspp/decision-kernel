"""Bounded source qualification via the existing Relay; no daily activation.

The cohort/calendar comes from an exact retained independent observation, not
from successful histories. Relay-adjusted prices do not establish action details,
PIT knowledge, total return, official-Tushare identity or production admission.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from decision_kernel.identity import canonical_hash, canonical_json
from . import tushare_relay as relay

MODE = 'tushare-c2-price-check'
TITLE = MODE + ' | sector=none | page=base | recovery=none'
READING = '5b116c5741b4e813bc9e9f8b145750448d1236ec'
DETAIL = 'details/stock/independent-observations.json'
DETAIL_SHA256 = '2d4cd81c19e5723af1d785e0a6a2407eecbd1ae5be700bb4d27a0bfb28ebe854'
MAX_LOGICAL, MAX_HTTP, MAX_BYTES = 33, 66, 16 * 1024 * 1024
DAILY_FIELDS = 'ts_code,trade_date,open,high,low,close,pre_close,vol,amount,ah_vol,ah_amount'
FACTOR_FIELDS = 'ts_code,trade_date,adj_factor'
VERSION = 'c2-tushare-retained-cohort-price-check-v1'
GAP_MODE = 'tushare-c2-factor-gaps'
GAP_TITLE = GAP_MODE + ' | sector=none | page=base | recovery=none'
GAP_VERSION = 'c2-tushare-factor-gap-supplement-v1'
GAP_DATES = ('20260930', '20260707', '20260715', '20260818', '20260918')
BASE_RUN = 37091291428
BASE_COMMIT = '48cbce5bc22bdc919fa628ba4ce65daa2cb8a086'
BASE_ARTIFACT = 11261749659
BASE_BYTES = 310123
BASE_ZIP_SHA256 = 'd603a6897df27f4afd17e7e935a486e08860e9b6d161b86d7d9d55351d8be409'
require = relay.require


def raw_json(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= relay.MAX_BODY, 'BODY_SIZE')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=relay._unique,
        parse_float=Decimal, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def clock(text):
    value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    require(value.tzinfo is not None and value.utcoffset() is not None, 'CLOCK_ZONE')
    return value


def write(root, name, value):
    (root / name).write_text(canonical_json(value) + '\n', encoding='utf-8')


def reference(raw):
    require(sha256(raw).hexdigest() == DETAIL_SHA256, 'REFERENCE_PIN')
    obj = raw_json(raw)
    source = obj['observations']
    rows = source['selected_observations']
    inventory = source['inventory']
    columns = inventory['columns']
    quotes = {r[columns.index('thscode')]: r[columns.index('last_price')] for r in inventory['rows']}
    return {'reading': READING, 'path': DETAIL, 'sha256': DETAIL_SHA256,
        'selection_hash': source['selection']['selection_hash'],
        'sessions': source['context']['sessions'],
        'symbols': [r['thscode'] for r in rows],
        'end_closes': {r['thscode']: quotes[r['thscode']] for r in rows},
        'calendar_basis': 'EXACT_RETAINED_QUALIFIED_CALENDAR_NOT_NEW_CALENDAR_CAPTURE'}


def request_plan(ref):
    days, codes = ref['sessions'], ref['symbols']
    require(len(days) == 61 and days == sorted(set(days)) and
        all(date.fromisoformat(d).isoformat() == d for d in days), 'CALENDAR_SCOPE')
    require(1 <= len(codes) <= 16 and len(set(codes)) == len(codes) and
        all(re.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)', c) for c in codes), 'COHORT_SCOPE')
    require(set(ref['end_closes']) == set(codes), 'QUOTE_SCOPE')
    end = days[-1].replace('-', '')
    plan = [{'api': 'daily', 'params': {'trade_date': end, 'fields': DAILY_FIELDS, 'limit': '6000'}}]
    for code in codes:
        common = {'ts_code': code, 'start_date': days[0].replace('-', ''), 'end_date': end, 'limit': '100'}
        plan += [{'api': 'daily', 'params': {**common, 'fields': DAILY_FIELDS}},
                 {'api': 'adj_factor', 'params': {**common, 'fields': FACTOR_FIELDS}}]
    require(len(plan) <= MAX_LOGICAL, 'LOGICAL_BUDGET')
    return plan


def is_source_check_run(run):
    return (run.get('path') == '.github/workflows/hithink-stock-dump-trial.yml'
        and run.get('event') == 'workflow_dispatch' and run.get('display_title') == TITLE)


def one_shot_scope(runs, total, current_id, *, mode=MODE):
    require(mode in (MODE, GAP_MODE), 'MODE_SCOPE')
    title = TITLE if mode == MODE else GAP_TITLE
    require(type(total) is int and total == len(runs) and len({r['id'] for r in runs}) == total,
            'RUN_SCOPE_INCOMPLETE')
    selected = [r for r in runs if r.get('display_title') == title]
    require(len(selected) == 1 and selected[0]['id'] == current_id
        and selected[0]['run_attempt'] == 1 and selected[0]['event'] == 'workflow_dispatch'
        and selected[0]['head_branch'] == 'main', 'AUTHORIZATION_ALREADY_USED')


def table(raw, api, params):
    obj = raw_json(raw)
    require(isinstance(obj, dict) and type(obj.get('code')) is int and obj['code'] == 0
            and obj.get('ok') is not False and obj.get('error') in (None, ''), 'BUSINESS_STATUS')
    require(obj.get('api_name', api) == api, 'API_IDENTITY')
    data = obj.get('data')
    require(isinstance(data, dict), 'DATA_ENVELOPE')
    fields = data.get('fields')
    required = {'ts_code', 'trade_date', 'adj_factor'} if api == 'adj_factor' else set(DAILY_FIELDS.split(',')) - {'ah_vol', 'ah_amount'}
    require(isinstance(fields, list) and all(isinstance(x, str) for x in fields)
            and len(fields) == len(set(fields)) and required <= set(fields), 'DATA_FIELDS')
    rows = relay.rows(obj)
    require(len(rows) < int(params['limit']), 'POSSIBLE_TRUNCATION')
    for container in (obj, data):
        for key in ('count', 'total'):
            if key in container:
                require(type(container[key]) is int and container[key] == len(rows), 'COUNT_CONFLICT')
        for key in ('has_more', 'has_next', 'truncated'):
            require(container.get(key, False) is False, 'PAGINATION_INCOMPLETE')
        for key in ('next', 'next_page', 'next_cursor'):
            require(container.get(key) in (None, ''), 'PAGINATION_INCOMPLETE')
    seen = set()
    for row in rows:
        code, day = row.get('ts_code'), row.get('trade_date')
        require(isinstance(code, str) and re.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)', code), 'SYMBOL_IDENTITY')
        require(isinstance(day, str) and re.fullmatch('[0-9]{8}', day), 'DATE_IDENTITY')
        require(date.fromisoformat(day).strftime('%Y%m%d') == day, 'DATE_IDENTITY')
        require((code, day) not in seen, 'DUPLICATE_ROW'); seen.add((code, day))
        require('ts_code' not in params or code == params['ts_code'], 'SYMBOL_IDENTITY')
        if 'trade_date' in params:
            require(day == params['trade_date'], 'DATE_IDENTITY')
        else:
            require(params['start_date'] <= day <= params['end_date'], 'DATE_IDENTITY')
    return rows


def number(value, positive=True):
    require(type(value) in (str, int, Decimal), 'NUMBER_TYPE')
    try:
        value = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('NUMBER_INVALID') from exc
    require(value.is_finite() and (value > 0 if positive else value >= 0)
        and len(value.as_tuple().digits) <= 28 and abs(value.as_tuple().exponent) <= 12, 'NUMBER_RANGE')
    return value


def evaluate(ref, plan, calls, bodies):
    """Pure per-window interpretation. Never mix factors or prices across providers."""
    data, dispositions = {}, []
    for i, item in enumerate(plan):
        if i >= len(calls):
            dispositions.append('NOT_REQUESTED_AFTER_SOURCE_STOP'); continue
        call = calls[i]
        if call['status'] != 'SUCCESS':
            dispositions.append(call['status']); continue
        try:
            data[i] = table(bodies[call['attempts'][-1]['response_file']], item['api'], item['params'])
            dispositions.append('TABLE_CHECKED')
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            dispositions.append('INPUT_SCHEMA_OR_SCOPE_REJECTED')
    return _evaluate_tables(ref, data, dispositions)


def _evaluate_tables(ref, data, dispositions):
    snapshot = {r['ts_code']: r for r in data.get(0, [])}
    output = []
    days = [d.replace('-', '') for d in ref['sessions']]
    for k, code in enumerate(ref['symbols']):
        hi, fi = 1 + 2*k, 2 + 2*k
        histories, factors = data.get(hi), data.get(fi)
        row = {'symbol': code, 'history_status': dispositions[hi], 'factor_status': dispositions[fi],
               'history_rows': None if histories is None else len(histories),
               'factor_rows': None if factors is None else len(factors), 'windows': {},
               'comparison_basis': 'THIRD_PARTY_RELAY_FACTOR_ADJUSTED_PRICE_NOT_TOTAL_RETURN',
               'corporate_action_details': 'NOT_OBTAINED_NOT_INFERRED_FROM_FACTORS'}
        bars = {r['trade_date']: r for r in histories or []}
        fac = {r['trade_date']: r for r in factors or []}
        foreign_days = (set(bars) | set(fac)) - set(days)
        for n in (5, 20, 60):
            required = days[-n-1:]
            missing = [d for d in required if d not in bars]
            missing_factors = [d for d in required if d not in fac]
            window = {'base_session': ref['sessions'][-n-1], 'end_session': ref['sessions'][-1],
                'required_sessions': n+1, 'missing_price_dates': missing, 'missing_factor_dates': missing_factors,
                'status': 'INPUT_UNAVAILABLE', 'price_change': None}
            row['windows'][str(n)] = window
            if histories is None or factors is None or 0 not in data:
                continue
            if missing or missing_factors:
                window['status'] = 'WINDOW_HISTORY_INCOMPLETE'; continue
            try:
                require(not foreign_days, 'OFF_CALENDAR_ROWS')
                for day in required:
                    bar = bars[day]
                    p = {f: number(bar[f]) for f in ('open', 'high', 'low', 'close', 'pre_close', 'vol', 'amount')}
                    require(p['low'] <= min(p['open'], p['close']) <= max(p['open'], p['close']) <= p['high'], 'OHLC_RANGE')
                    number(fac[day]['adj_factor'])
                end = number(bars[days[-1]]['close'])
                require(code in snapshot and end == number(snapshot[code]['close'])
                        == number(ref['end_closes'][code]), 'END_QUOTE_MISMATCH')
                with localcontext() as ctx:
                    ctx.prec = 28
                    base = number(bars[required[0]]['close'])
                    base_factor = number(fac[required[0]]['adj_factor'])
                    end_factor = number(fac[required[-1]]['adj_factor'])
                    adjusted = end * end_factor / (base * base_factor) - 1
                window.update(status='PROVIDER_ADJUSTED_PRICE_COMPARABLE', price_change=str(adjusted),
                    base_raw_close=str(base), end_raw_close=str(end),
                    base_factor=str(base_factor), end_factor=str(end_factor),
                    formula='end_close * end_factor / (base_close * base_factor) - 1')
            except (ValueError, TypeError, KeyError, IndexError, InvalidOperation):
                window['status'] = 'VALUE_DATE_OR_END_QUOTE_REJECTED'
        output.append(row)
    return {'version': VERSION, 'reference': ref, 'request_dispositions': dispositions,
        'snapshot': {'status': dispositions[0], 'returned_rows': len(data[0]) if 0 in data else None,
            'symbols': sorted(snapshot), 'scope': 'RETURNED_DAILY_TRADING_ROWS_NOT_ALL_LISTED_SECURITIES',
            'missing_cohort_symbols': [c for c in ref['symbols'] if c not in snapshot],
            'suspension_and_listing_census': 'NOT_ESTABLISHED'},
        'cohort_denominator': len(output), 'observations': output,
        'qualified_windows': {str(n): sum(r['windows'][str(n)]['price_change'] is not None for r in output) for n in (5, 20, 60)},
        'daily_admission': False, 'new_selection': False, 'research_authority': 'NONE',
        'investment_authority': 'NONE', 'pit_knowledge': 'NOT_ESTABLISHED',
        'volume_basis': 'TUSHARE_CONTRACT_HANDS_AMOUNT_THOUSAND_CNY_AFTER_HOURS_SEPARATE_NOT_CROSS_PROVIDER_MATCHED'}


def workflow_identity(env, *, mode=MODE):
    require(mode in (MODE, GAP_MODE), 'MODE_SCOPE')
    require(env.get('GITHUB_REPOSITORY') == 'auguspp/decision-kernel'
        and env.get('GITHUB_REF') == 'refs/heads/main'
        and env.get('GITHUB_RUN_ATTEMPT') == '1'
        and env.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
        and env.get('GITHUB_JOB') == MODE and env.get('TRIAL_PURPOSE') == mode
        and re.fullmatch('[0-9a-f]{40}', env.get('GITHUB_SHA', '')) is not None
        and re.fullmatch('[1-9][0-9]*', env.get('GITHUB_RUN_ID', '')) is not None,
        'EXECUTION_IDENTITY')
    return {k: env[k] for k in ('GITHUB_REPOSITORY', 'GITHUB_REF', 'GITHUB_RUN_ATTEMPT',
        'GITHUB_EVENT_NAME', 'GITHUB_JOB', 'TRIAL_PURPOSE', 'GITHUB_SHA', 'GITHUB_RUN_ID')}


def capture(root, reference_raw, *, identity, request=None, now=relay.now):
    return _capture(root, reference_raw, identity=identity, request=request, now=now)


def _capture(root, reference_raw, *, identity, request, now, parent=None):
    root = Path(root)
    require(not root.exists() and not root.is_symlink() and not any(p.is_symlink() for p in root.parents), 'OUTPUT_EXISTS_OR_SYMLINK')
    mode = GAP_MODE if parent is not None else MODE
    identity = workflow_identity(identity, mode=mode)
    ref = reference(reference_raw)
    plan = gap_plan() if parent is not None else request_plan(ref)
    logical, http = (5, 10) if parent is not None else (MAX_LOGICAL, MAX_HTTP)
    root.mkdir(parents=True); (root / 'raw').mkdir()
    (root / 'reference.json').write_bytes(reference_raw)
    receipt = {'version': GAP_VERSION if parent is not None else VERSION, 'reference': ref, 'plan': plan, 'plan_hash': canonical_hash(plan),
        'source': 'THIRD_PARTY_TUSHARE_RELAY', 'host': relay.PRO, 'workflow': identity,
        'max_logical_requests': logical, 'max_http_attempts': http,
        'started_at': now(), 'calls': [], 'stopped': None, 'http_attempts_known': True}
    if parent is not None:
        (root / 'original.zip').write_bytes(parent['zip'])
        receipt['predecessor_zip_sha256'] = BASE_ZIP_SHA256
        require(clock(receipt['started_at']) >= clock(parent['receipt']['finished_at']), 'PREDECESSOR_CLOCK')
    request = request or relay.request
    bodies, size, attempts = {}, 0, 0
    last_received = clock(receipt['started_at'])
    for i, item in enumerate(plan):
        if size + relay.MAX_BODY*2 > MAX_BYTES:
            receipt['stopped'] = 'RAW_CUSTODY_BUDGET'; break
        call = {**item, 'status': 'REQUEST_STARTED', 'attempts': []}
        receipt['calls'].append(call); write(root, 'receipt.json', receipt)
        try:
            result = request(item['api'], dict(item['params']))
            require(result['api'] == item['api'] and result['params'] == item['params'], 'REQUEST_IDENTITY')
            for j, attempt in enumerate(result['attempts'], 1):
                require(j <= 2, 'ATTEMPT_BUDGET')
                attempts += 1; require(attempts <= http, 'HTTP_BUDGET')
                record = {k: attempt[k] for k in ('attempt', 'http_status', 'classification', 'requested_at', 'received_at', 'headers')}
                raw = attempt['raw']; record['response_file'] = None
                if raw is not None:
                    require(isinstance(raw, bytes) and len(raw) <= relay.MAX_BODY, 'BODY_SIZE')
                    size += len(raw); require(size <= MAX_BYTES, 'RAW_CUSTODY_BUDGET')
                    name = f'raw/{i:02d}-{j}.json'
                    (root / name).write_bytes(raw); bodies[name] = raw
                    record.update(response_file=name, bytes=len(raw), sha256=sha256(raw).hexdigest())
                call['attempts'].append(record)
                requested, received = clock(record['requested_at']), clock(record['received_at'])
                require(last_received <= requested <= received, 'ATTEMPT_CLOCK')
                if j == 2:
                    require(call['attempts'][0]['classification'] == 'TEMPORARY_QUEUE'
                        and (requested-last_received).total_seconds() >= relay.RETRY_WAIT_SECONDS, 'RETRY_SCOPE')
                last_received = received
            call['status'] = result['status']
            require(call['attempts'] and call['status'] == call['attempts'][-1]['classification'], 'ATTEMPT_STATUS')
        except Exception as exc:
            call['status'] = 'TRANSPORT_OR_CAPTURE_UNCERTAIN'
            call['error_type'] = type(exc).__name__
            receipt['http_attempts_known'] = False
        write(root, 'receipt.json', receipt)
        if call['status'] != 'SUCCESS':
            receipt['stopped'] = call['status']; break
        try:
            _checked_table(bodies[call['attempts'][-1]['response_file']], item, parent)
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            receipt['stopped'] = 'INPUT_SCHEMA_OR_SCOPE_REJECTED'; break
    receipt['finished_at'] = now()
    receipt['recorded_http_attempts'] = attempts
    receipt['logical_requests_started'] = len(receipt['calls'])
    receipt['raw_bytes'] = size
    write(root, 'receipt.json', receipt)
    report = evaluate_gaps(parent, plan, receipt['calls'], bodies) if parent is not None else evaluate(ref, plan, receipt['calls'], bodies)
    write(root, 'report.json', report)
    return receipt, report


def verify(root, *, expected_identity=None):
    return _verify(root, expected_identity=expected_identity)


def _verify(root, *, expected_identity=None, parent=None):
    root = Path(root)
    require(not root.is_symlink() and not any(p.is_symlink() for p in root.parents), 'SOURCE_SYMLINK')
    require(all(not p.is_symlink() for p in root.rglob('*')), 'SOURCE_SYMLINK')
    receipt = raw_json((root / 'receipt.json').read_bytes())
    mode = GAP_MODE if parent is not None else MODE
    identity = workflow_identity(receipt['workflow'], mode=mode)
    require(expected_identity is None or identity == workflow_identity(expected_identity, mode=mode), 'EXTERNAL_EXECUTION_IDENTITY')
    logical, http = (5, 10) if parent is not None else (MAX_LOGICAL, MAX_HTTP)
    version = GAP_VERSION if parent is not None else VERSION
    require(receipt['version'] == version and receipt['source'] == 'THIRD_PARTY_TUSHARE_RELAY'
        and receipt['max_logical_requests'] == logical and receipt['max_http_attempts'] == http,
        'RECEIPT_IDENTITY')
    ref = reference((root / 'reference.json').read_bytes())
    plan = gap_plan() if parent is not None else request_plan(ref)
    require(receipt['reference'] == ref and receipt['plan'] == plan
            and receipt['plan_hash'] == canonical_hash(plan) and receipt['host'] == relay.PRO, 'PLAN_IDENTITY')
    calls = receipt['calls']; require(1 <= len(calls) <= len(plan), 'CALL_SCOPE')
    bodies, size, count = {}, 0, 0
    last, end = clock(receipt['started_at']), clock(receipt['finished_at'])
    require(last <= end, 'CAPTURE_CLOCK')
    if parent is not None:
        require(receipt.get('predecessor_zip_sha256') == BASE_ZIP_SHA256 and
            (root / 'original.zip').read_bytes() == parent['zip'] and ref == parent['reference'] and
            clock(parent['receipt']['finished_at']) <= last and (end-last).total_seconds() <= 1200,
            'PREDECESSOR_BINDING')
    for i, call in enumerate(calls):
        require(all(call[k] == plan[i][k] for k in ('api', 'params')), 'CALL_IDENTITY')
        require(call['status'] != 'TRANSPORT_OR_CAPTURE_UNCERTAIN' and receipt['http_attempts_known'], 'UNRESOLVED_ATTEMPT')
        require(1 <= len(call['attempts']) <= 2, 'ATTEMPT_BUDGET')
        for j, attempt in enumerate(call['attempts'], 1):
            at, received = clock(attempt['requested_at']), clock(attempt['received_at'])
            require(last <= at <= received <= end and attempt['attempt'] == j, 'ATTEMPT_CLOCK')
            if j == 2:
                require(call['attempts'][0]['classification'] == 'TEMPORARY_QUEUE'
                        and (at-last).total_seconds() >= relay.RETRY_WAIT_SECONDS, 'RETRY_SCOPE')
            last = received; count += 1
            name = attempt['response_file']
            if name is None:
                require(attempt['http_status'] is None and attempt['classification'] in
                    {'TEMPORARY_QUEUE', 'TRANSPORT_CONNECTION', 'TRANSPORT_ERROR'}, 'MISSING_RESPONSE')
            else:
                require(name == f'raw/{i:02d}-{j}.json', 'RAW_PATH')
                raw = (root / name).read_bytes()
                require(len(raw) == attempt['bytes'] <= relay.MAX_BODY
                        and sha256(raw).hexdigest() == attempt['sha256'], 'RAW_INTEGRITY')
                bodies[name] = raw; size += len(raw)
                try:
                    classification = relay.classify(attempt['http_status'], relay.decode(raw))
                except relay.RelayError:
                    classification = 'MALFORMED_RESPONSE'
                require(classification == attempt['classification'], 'RESPONSE_CLASSIFICATION')
        require(call['status'] == call['attempts'][-1]['classification'], 'ATTEMPT_STATUS')
        if i < len(calls)-1:
            require(call['status'] == 'SUCCESS', 'REQUEST_AFTER_SOURCE_STOP')
            _checked_table(bodies[call['attempts'][-1]['response_file']], call, parent)
    require(size == receipt['raw_bytes'] <= MAX_BYTES and count == receipt['recorded_http_attempts'] <= http
            and len(calls) == receipt['logical_requests_started'], 'BUDGET_IDENTITY')
    terminal = calls[-1]
    if terminal['status'] != 'SUCCESS':
        require(receipt['stopped'] == terminal['status'], 'STOP_IDENTITY')
    else:
        try:
            _checked_table(bodies[terminal['attempts'][-1]['response_file']], terminal, parent)
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            require(receipt['stopped'] == 'INPUT_SCHEMA_OR_SCOPE_REJECTED', 'STOP_IDENTITY')
        else:
            if len(calls) == len(plan):
                require(receipt['stopped'] is None, 'STOP_IDENTITY')
            else:
                require(receipt['stopped'] == 'RAW_CUSTODY_BUDGET'
                    and size + relay.MAX_BODY*2 > MAX_BYTES, 'UNEXPLAINED_MISSING_CALLS')
    expected = {'reference.json', 'receipt.json', 'report.json'} | set(bodies)
    if parent is not None:
        expected.add('original.zip')
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} == expected, 'FILE_INVENTORY')
    report = evaluate_gaps(parent, plan, calls, bodies) if parent is not None else evaluate(ref, plan, calls, bodies)
    require((root / 'report.json').read_bytes() == (canonical_json(report)+'\n').encode(), 'REPORT_REBUILD')
    return {'status': 'REBUILT_FROM_RETAINED_RELAY_RESPONSES', 'network_calls': 0,
            'logical_requests': len(calls), 'recorded_http_attempts': count,
            'report_sha256': sha256((root/'report.json').read_bytes()).hexdigest()}



def gap_plan():
    return [{'api': 'adj_factor', 'params': {'trade_date': day,
        'fields': FACTOR_FIELDS, 'limit': '6000'}} for day in GAP_DATES]


def original_input(raw):
    """Recover the pinned original; never authenticate it by its own receipt."""
    from . import current_state as saved
    require(len(raw) == BASE_BYTES and sha256(raw).hexdigest() == BASE_ZIP_SHA256, 'ORIGINAL_ARCHIVE_PIN')
    run = {'id': BASE_RUN, 'head_sha': BASE_COMMIT}
    files = saved.unpack_archive(raw, {'expired': False, 'digest': 'sha256:'+BASE_ZIP_SHA256,
        'size_in_bytes': BASE_BYTES, 'workflow_run': run}, run)
    expected = {'GITHUB_REPOSITORY': saved.REPOSITORY, 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_JOB': MODE, 'TRIAL_PURPOSE': MODE, 'GITHUB_SHA': BASE_COMMIT, 'GITHUB_RUN_ID': str(BASE_RUN)}
    with TemporaryDirectory() as directory:
        root = Path(directory)
        for name, body in files.items():
            path = root / saved.safe_path(name); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        proof = verify(root, expected_identity=expected)
    receipt = raw_json(files['receipt.json'])
    require(receipt['stopped'] is None and receipt['logical_requests_started'] == 33, 'ORIGINAL_INCOMPLETE')
    tables = {i: table(files[call['attempts'][-1]['response_file']], call['api'], call['params'])
              for i, call in enumerate(receipt['calls'])}
    return {'zip': raw, 'files': files, 'receipt': receipt, 'reference': receipt['reference'],
            'tables': tables, 'proof': proof}


def _checked_table(raw, item, parent=None):
    rows = table(raw, item['api'], item['params'])
    if parent is None:
        return rows
    # Different response shapes are not permission to swap source identity.
    obj = raw_json(raw)
    declarations = [{k: level[k] for k in ('provider', 'source') if k in level} for level in (obj, obj['data'])]
    day = item['params']['trade_date']
    found = {r['ts_code']: r for r in rows}
    for row in rows:
        number(row['adj_factor'])
    for k, code in enumerate(parent['reference']['symbols']):
        old = {r['trade_date']: r for r in parent['tables'][2+2*k]}
        if day == GAP_DATES[0]:
            require(code in found and day in old, 'FACTOR_ANCHOR_MISSING')
        if code in found and day in old:
            require(number(found[code]['adj_factor']) == number(old[day]['adj_factor']), 'FACTOR_VALUE_CONFLICT')
        call = parent['receipt']['calls'][2+2*k]
        old_obj = raw_json(parent['files'][call['attempts'][-1]['response_file']])
        old_declarations = [{key: level[key] for key in ('provider', 'source') if key in level}
                            for level in (old_obj, old_obj['data'])]
        require(declarations == old_declarations, 'FACTOR_SOURCE_DECLARATION_CHANGED')
    return rows


def evaluate_gaps(parent, plan, calls, bodies):
    from copy import deepcopy
    tables = deepcopy(parent['tables'])
    ref = parent['reference']; gaps = {}; filled = []; dispositions = []
    for k, code in enumerate(ref['symbols']):
        prices = {r['trade_date'] for r in tables[1+2*k]}
        factors = {r['trade_date'] for r in tables[2+2*k]}
        gaps[code] = sorted(prices-factors)
    require(set(d for dates in gaps.values() for d in dates) <= set(GAP_DATES[1:]), 'GAP_SCOPE_CHANGED')
    anchor = False
    for i, item in enumerate(plan):
        if i >= len(calls):
            dispositions.append('NOT_REQUESTED_AFTER_SOURCE_STOP'); continue
        call = calls[i]
        if call['status'] != 'SUCCESS':
            dispositions.append(call['status']); continue
        try:
            rows = _checked_table(bodies[call['attempts'][-1]['response_file']], item, parent)
        except (ValueError, TypeError, KeyError, IndexError, OverflowError):
            dispositions.append('INPUT_SCHEMA_OR_SCOPE_REJECTED'); continue
        dispositions.append('TABLE_CHECKED')
        if i == 0:
            anchor = True; continue
        require(anchor, 'FACTOR_ANCHOR_REQUIRED')
        by_code = {r['ts_code']: (pos, r) for pos, r in enumerate(rows)}
        day = item['params']['trade_date']
        for k, code in enumerate(ref['symbols']):
            if day in gaps[code] and code in by_code:
                position, row = by_code[code]
                tables[2+2*k].append(row)
                filled.append({'symbol': code, 'trade_date': day,
                    'response_file': call['attempts'][-1]['response_file'], 'row_position': position})
    report = _evaluate_tables(ref, tables, ['TABLE_CHECKED']*33)
    original = raw_json(parent['files']['report.json'])
    report.update(version=GAP_VERSION, request_dispositions=dispositions,
        factor_repair={'predecessor_run_id': BASE_RUN, 'predecessor_zip_sha256': BASE_ZIP_SHA256,
            'predecessor_report_sha256': parent['proof']['report_sha256'],
            'original_qualified_windows': original['qualified_windows'],
            'missing_factor_keys': gaps, 'target_keys': sum(map(len, gaps.values())),
            'filled_keys': filled, 'filled_key_count': len(filled), 'anchor_checked': anchor,
            'scope': 'ONLY_ORIGINAL_PRICE_DATES_MISSING_FACTORS_NO_PRICE_BACKFILL',
            'vintage_consistency': 'ENDPOINT_OVERLAP_CHECK_NOT_FULL_VINTAGE_CERTIFICATION',
            'underlying_provider_identity': 'NOT_ESTABLISHED_BY_RELAY_ENDPOINT'})
    return report


def capture_gaps(root, original_raw, *, identity, request=None, now=relay.now):
    parent = original_input(original_raw)
    return _capture(root, parent['files']['reference.json'], identity=identity,
                    request=request, now=now, parent=parent)


def verify_gaps(root, *, expected_identity=None):
    root = Path(root)
    require(not root.is_symlink() and not any(p.is_symlink() for p in root.parents)
            and not (root/'original.zip').is_symlink(), 'SOURCE_SYMLINK')
    parent = original_input((root/'original.zip').read_bytes())
    return _verify(root, expected_identity=expected_identity, parent=parent)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('capture', 'verify', 'capture-gaps', 'verify-gaps'))
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--reference', type=Path)
    p.add_argument('--original', type=Path)
    args = p.parse_args(argv)
    if args.mode == 'verify-gaps':
        print(canonical_json(verify_gaps(args.root))); return 0
    if args.mode == 'capture-gaps':
        require(args.original is not None, 'ORIGINAL_REQUIRED')
        receipt, report = capture_gaps(args.root, args.original.read_bytes(), identity=os.environ)
        print(canonical_json({'logical_requests': receipt['logical_requests_started'],
            'stopped': receipt['stopped'], 'qualified_windows': report['qualified_windows']}))
        return 0
    if args.mode == 'verify':
        print(canonical_json(verify(args.root))); return 0
    identity = workflow_identity(os.environ)
    require(args.reference is not None, 'REFERENCE_REQUIRED')
    receipt, report = capture(args.root, args.reference.read_bytes(), identity=identity)
    print(canonical_json({'logical_requests': receipt['logical_requests_started'],
        'stopped': receipt['stopped'], 'qualified_windows': report['qualified_windows']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
