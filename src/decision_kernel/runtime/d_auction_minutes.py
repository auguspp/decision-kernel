"""FTShare minute observations for an existing auction cohort, not another feed engine.

The original auction verifier owns selection; FTShare owns minute prices. Reuse
its existing HTTP transport and the standard saved-byte/Git archive boundary.
No scheduler, inferred bars, cross-provider return, ranking or trade is added.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, time, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import URLError

from decision_kernel.identity import canonical_hash, canonical_json
from . import current_state as model
from . import stock_market_inputs as saved
from . import d_auction_probe as auction
from .d_auction_follow_through import GROUPS, _group
from . import ftshare_discovery as common

VERSION = 'd-auction-minute-observation-v1'
ROUTE = 'auction_minutes'
ENDPOINT = 'https://market.ft.tech/gateway/api/v2/market/data/stock_minutes/batch'
TITLE, JOB = 'd-auction-minutes', 'auction-minutes'
WORKFLOW = saved.WORKFLOW
PATH = 'details/stock/auction-minutes.json'
BATCH_SIZE, MAX_BATCHES = 20, 16
MAX_BODY, MAX_TOTAL = 2 * 1024 * 1024, 16 * 1024 * 1024
SOURCE = 'FTSHARE_STOCK_MINUTES_BATCH'
ERR = (ValueError, KeyError, TypeError, IndexError, ArithmeticError, UnicodeError)
STOP_CODES = {'AUTHENTICATION_FAILED', 'ENTITLEMENT_DENIED', 'RATE_LIMITED',
              'TRANSPORT_FAILURE', 'PARSE_FAILURE', 'HTTP_REJECTED', 'PROVIDER_REJECTED',
              'AUTHENTICATION_UNAVAILABLE', 'CREDENTIAL_REFLECTION_REJECTED', 'SOURCE_REQUEST_FAILED',
              'RESPONSE_TOO_LARGE', 'REDIRECT_REJECTED', 'ENCODING_REJECTED', 'RESPONSE_LENGTH_MISMATCH'}


def encode(value):
    return (canonical_json(value) + '\n').encode()


def bound(raw, description):
    model.check(isinstance(raw, bytes) and len(raw) == description['bytes']
                and model.sha256(raw) == description['sha256'], 'minute source bytes differ')
    if 'git_blob' in description:
        model.check(model.blob_sha(raw) == description['git_blob'], 'minute source blob differs')


def workflow_identity(env):
    expected = {'GITHUB_REPOSITORY': model.REPOSITORY, 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_JOB': JOB, 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_WORKFLOW_REF': model.REPOSITORY+'/'+WORKFLOW+'@refs/heads/main'}
    model.check(all(env.get(k) == v for k, v in expected.items())
                and model.SHA.fullmatch(env.get('GITHUB_SHA', '')) is not None
                and str(env.get('GITHUB_RUN_ID', '')).isdigit() and int(env['GITHUB_RUN_ID']) > 0,
                'minute workflow identity')
    return {**expected, 'GITHUB_SHA': env['GITHUB_SHA'], 'GITHUB_RUN_ID': str(env['GITHUB_RUN_ID'])}


def replay_auction(raw, description):
    """Original ZIP custody and original verifier; never execute archived code."""
    bound(raw, description)
    run = description['origin_run']
    artifact = {'expired': False, 'digest': 'sha256:'+description['sha256'],
        'size_in_bytes': description['bytes'], 'workflow_run': {'id': run['id'], 'head_sha': run['head_sha']}}
    files = model.unpack_archive(raw, artifact, run)
    with TemporaryDirectory() as directory:
        root = Path(directory)
        for name, body in files.items():
            path = root/model.safe_path(name); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(body)
        return auction.verify(root, qualify_temperature=True)


def plan_for(report, source, reading_commit):
    model.check(model.SHA.fullmatch(reading_commit or '') is not None, 'minute seed reading commit')
    model.check(report['version'] in (auction.LEGACY_VERSION, auction.VERSION)
                and report['profile'] == auction.PROFILE and report['source'] == saved.SOURCE,
                'minute original auction identity')
    rows = auction.row_dicts(report)
    model.check(len(rows) == report['cohort_denominator'], 'minute original denominator')
    symbols = [r['symbol'] for r in rows if r['symbol'] is not None]
    model.check(len(symbols) == len(set(symbols)) and all(saved.CODE.fullmatch(s) for s in symbols),
                'minute original security identity')
    day = auction.target_day(report['market_session'])
    def ms(t): return int(datetime.combine(day, t, tzinfo=saved.ZONE).timestamp()) * 1000
    batches = [{'symbols': symbols[i:i+BATCH_SIZE], 'interval_value': 1,
                'since_ts_millis': ms(time(9, 30)), 'until_ts_millis': ms(time(9, 41)), 'limit': 1000}
               for i in range(0, len(symbols), BATCH_SIZE)]
    # This finite invocation leaves any budget-excluded members visible; it does
    # not turn an arbitrarily long all-market history into a daily prerequisite.
    return {'version': VERSION, 'source': SOURCE, 'endpoint': ENDPOINT,
        'seed_reading_commit': reading_commit, 'auction_archive': source,
        'auction_report_hash': canonical_hash(report), 'market_session': day.isoformat(),
        'cohort_denominator': len(rows), 'target_end_ms': ms(time(9, 40)),
        'target_open_ms': ms(time(9, 39)), 'requested_adjust': 'OMITTED_OFFICIAL_NONE_DEFAULT',
        'symbol_encoding': 'REPEATED_QUERY_PARAMETERS', 'batch_budget': MAX_BATCHES,
        'batches': batches[:MAX_BATCHES], 'unrequested_symbols': symbols[MAX_BATCHES*BATCH_SIZE:]}


def validate_parameters(params):
    model.check(set(params) == {'symbols', 'interval_value', 'since_ts_millis', 'until_ts_millis', 'limit'},
                'minute request fields')
    symbols = params['symbols']
    model.check(isinstance(symbols, list) and 1 <= len(symbols) <= BATCH_SIZE
                and len(symbols) == len(set(symbols)) and all(isinstance(s, str) and saved.CODE.fullmatch(s) for s in symbols),
                'minute request securities')
    a, b = params['since_ts_millis'], params['until_ts_millis']
    model.check(type(a) is int and type(b) is int and 0 < a < b and b-a == 11*60000
                and params['interval_value'] == 1 and type(params['interval_value']) is int
                and params['limit'] == 1000 and type(params['limit']) is int, 'minute request window')
    start, end = (datetime.fromtimestamp(n//1000, saved.ZONE) for n in (a, b))
    model.check(a % 1000 == b % 1000 == 0 and start.date() == end.date()
                and start.time() == time(9, 30) and end.time() == time(9, 41), 'minute request session')


def response_status(status, raw):
    if status != 200:
        return {401: 'AUTHENTICATION_FAILED', 403: 'ENTITLEMENT_DENIED', 429: 'RATE_LIMITED'}.get(status, 'HTTP_REJECTED')
    try:
        body = saved.loads(raw)
        if not isinstance(body, dict) or type(body.get('code')) is not int:
            return 'PARSE_FAILURE'
        if body['code'] not in (0, 200):
            return {401: 'AUTHENTICATION_FAILED', 403: 'ENTITLEMENT_DENIED', 429: 'RATE_LIMITED'}.get(body['code'], 'PROVIDER_REJECTED')
        data = body.get('data')
        if not isinstance(data, list) or (data and not any(isinstance(row, dict)
                and isinstance(row.get('symbol'), str) and isinstance(row.get('items'), list) for row in data)):
            return 'PARSE_FAILURE'
        return 'RESPONSE_SAVED'
    except ERR:
        return 'PARSE_FAILURE'


def observe_symbol(item, plan):
    """Only a unique exact closing minute qualifies. No nearest-bar/asof filling."""
    out = {'close_0940': None, 'status': 'MINUTE_ITEMS_UNAVAILABLE', 'row_index': None,
           'source_ts_millis': None, 'source_ts_millis_open': None, 'reported_total': item.get('total'),
           'returned_count': None, 'return_count_consistent': False, 'timestamp_semantics': 'EXACT_ONE_MINUTE_BOUNDARY_REQUIRED'}
    items = item.get('items')
    if not isinstance(items, list) or len(items) > 1000:
        return out
    out.update(returned_count=len(items), return_count_consistent=type(item.get('total')) is int and item['total'] == len(items))
    # An unrelated missing/invalid minute, total metadata or OHLC/volume cannot
    # veto a unique exact close needed by this particular purpose.
    matches = [(i, row) for i, row in enumerate(items) if isinstance(row, dict)
               and type(row.get('ts_millis')) is int and row['ts_millis'] == plan['target_end_ms']]
    out['status'] = 'TARGET_MINUTE_NOT_RETURNED' if not matches else 'TARGET_MINUTE_AMBIGUOUS'
    if len(matches) != 1:
        return out
    index, row = matches[0]
    out.update(row_index=index, source_ts_millis=row['ts_millis'], source_ts_millis_open=row.get('ts_millis_open'))
    if type(row.get('ts_millis_open')) is not int or row['ts_millis_open'] != plan['target_open_ms']:
        out['status'] = 'TARGET_MINUTE_TIME_UNQUALIFIED'; return out
    try:
        number = auction.number(row['close'])
        model.check(number > 0, 'minute nonpositive close')
        out.update(close_0940=str(number), status='EXACT_0940_CLOSE_OBSERVED',
                   timestamp_semantics='PROVIDER_0939_OPEN_0940_CLOSE_BOUNDARY_NOT_RECEIPT_TIME')
    except ERR:
        out['status'] = 'TARGET_CLOSE_INVALID'
    return out


def build(plan, report, receipt, bodies):
    by_symbol, extra_rows = {}, []
    for i, call in enumerate(receipt['calls']):
        names = call['parameters']['symbols']
        if call['status'] != 'RESPONSE_SAVED':
            for s in names: by_symbol[s] = {'status': call['status'], 'close_0940': None, 'request_index': i}
            continue
        raw = bodies[call['response_file']]
        data = saved.loads(raw)['data']
        counts = Counter(r.get('symbol') for r in data if isinstance(r, dict) and isinstance(r.get('symbol'), str))
        for row in data:
            if not isinstance(row, dict) or row.get('symbol') not in names:
                extra_rows.append({'request_index': i, 'reason': 'UNREQUESTED_OR_INVALID_IDENTITY'})
        for s in names:
            if counts[s] != 1:
                value = {'status': 'SYMBOL_NOT_RETURNED' if counts[s] == 0 else 'SYMBOL_AMBIGUOUS', 'close_0940': None}
            else:
                value = observe_symbol(next(r for r in data if isinstance(r, dict) and r.get('symbol') == s), plan)
            by_symbol[s] = {**value, 'request_index': i, 'source_file': call['response_file'],
                           'source_sha256': model.sha256(raw), 'received_at': call['received_at']}
    rows = []
    for original in auction.row_dicts(report):
        s = original['symbol']
        missing = ('COHORT_IDENTITY_UNRESOLVED' if s is None else 'REQUEST_BUDGET_NOT_REQUESTED'
                   if s in plan['unrequested_symbols'] else 'NOT_REQUESTED_AFTER_SOURCE_STOP')
        rows.append({'symbol': s, 'name': original['name'], 'group': _group(original),
                     'original_auction_status': original['status'], 'auction_price': original['auction_price'],
                     'minute': by_symbol.get(s, {'status': missing, 'close_0940': None})})
    groups = {g: {'denominator': sum(r['group'] == g for r in rows),
                   'observed_0940': sum(r['group'] == g and r['minute']['close_0940'] is not None for r in rows)} for g in GROUPS}
    n = sum(r['minute']['close_0940'] is not None for r in rows)
    return {'version': VERSION, 'source': SOURCE, 'market_session': plan['market_session'],
        'status': 'DATED_MINUTE_OBSERVATIONS' if n == len(rows) and rows else
                  'DATED_MINUTE_OBSERVATIONS_WITH_GAPS' if n else 'MINUTE_INPUT_UNAVAILABLE_NOT_QUIET',
        'observed_at': receipt['started_at'], 'received_through': receipt['finished_at'],
        'provenance': receipt['provenance'], 'workflow': receipt['workflow'],
        'auction_origin': {'reading_commit': plan['seed_reading_commit'], 'archive': plan['auction_archive']},
        'auction_report_hash': plan['auction_report_hash'], 'auction_timeliness': report['timeliness'],
        'cohort_denominator': len(rows), 'observed_0940': n, 'groups': groups, 'rows': rows,
        'capture_timing': 'HISTORICAL_OR_LATE_NOT_0940_DISCOVERY' if model.clock(receipt['started_at']) >
            datetime.fromtimestamp(plan['target_end_ms']//1000, saved.ZONE) else 'AT_BOUNDARY_NOT_FRESHNESS_CERTIFICATION',
        'target_close_time': datetime.fromtimestamp(plan['target_end_ms']//1000, saved.ZONE).isoformat(),
        'source_stop': receipt['stopped'], 'source_request_count': len(receipt['calls']),
        'unrequested_symbols': plan['unrequested_symbols'], 'unexpected_rows': extra_rows,
        'price_basis': plan['requested_adjust'], 'cross_provider_return': 'NOT_COMPUTED',
        'intraday_leadership': 'NOT_ESTABLISHED', 'economic_result': 'NOT_EVALUATED',
        'new_opportunity_judgment': False, 'odds_recomputed': False, **model.AUTHORITY}


def render(report):
    lines = ['\n\n## D：原竞价名单的09:40分钟观察\n',
        f"市场日：{report['market_session']}；目标为09:39–09:40这一分钟的供应商收盘字段。",
        f"原名单{report['cohort_denominator']}名，准确09:40收盘可读{report['observed_0940']}名；{report['capture_timing']}。",
        f"原竞价：{report['auction_timeliness']}；分钟资料取得截止：{report['received_through']}。",
        f"本次来源停止原因：{report['source_stop'] or '未停止'}；其后的请求未执行。",
        '| 原分组 | 完整分母 | 09:40可读 |', '|---|---:|---:|']
    for key, label in GROUPS.items():
        group = report['groups'][key]; lines.append(f"| {label} | {group['denominator']} | {group['observed_0940']} |")
    lines += ['\n| 证券 | 原分组 | 原竞价价 | 09:40收盘 | 状态 |', '|---|---|---:|---:|---|']
    for row in report['rows']:
        lines.append(f"| {row['symbol'] or '身份未解决'} | {GROUPS[row['group']]} | "
                     f"{row['auction_price'] or '—'} | {row['minute']['close_0940'] or '—'} | {row['minute']['status']} |")
    lines += ['后补历史分钟不是当时发现；没有最近值填补、跨来源收益、买卖点或概率。缺量额/其他分钟不取消准确时点的收盘。',
              f'完整名单、每项缺口、原始请求与取得时间见 [{PATH}]({PATH})。\n']
    return '\n'.join(lines)


def prepare(api, reading_commit, root):
    """Read only the explicitly pinned existing reading and auction original."""
    root = saved.safe_root(root); root.mkdir()
    baseline = saved.loads(api.file('current-state.json', reading_commit)); model.validate_read_package(baseline)
    reference = baseline['research']['independent_stock_observations']
    raw = api.file(reference['read_path'], reading_commit); bound(raw, reference)
    description = saved.loads(raw)['daily_market_inputs']['auction_probe']
    source = description['source_archive']; raw = api.file(source['read_path'], reading_commit)
    report = replay_auction(raw, source)
    model.check(report['provenance'] == 'LIVE_TUSHARE_RELAY', 'minute seed must be a real retained source')
    model.check(model.clock(source['expires_at']) > model.clock(common.now()), 'minute seed live archive expired')
    plan = plan_for(report, source, reading_commit)
    (root/'auction-source.zip').write_bytes(raw); (root/'plan.json').write_bytes(encode(plan))
    return plan


def capture(root, *, fetch=None, clock=common.now, workflow=None):
    root = saved.safe_root(root)
    model.check(not (root/'receipt.json').exists(), 'minute capture already attempted')
    plan = saved.loads((root/'plan.json').read_bytes())
    original = replay_auction((root/'auction-source.zip').read_bytes(), plan['auction_archive'])
    model.check(plan == plan_for(original, plan['auction_archive'], plan['seed_reading_commit']), 'minute plan differs')
    live = fetch is None
    identity = workflow_identity(workflow or os.environ) if live else {}
    if live:
        from .ftshare_market_inputs import request
        fetch = request
    started = clock()
    model.check(model.clock(started) >= datetime.fromtimestamp(plan['batches'][0]['until_ts_millis']//1000, saved.ZONE)
                if plan['batches'] else True, 'minute capture before bounded window completes')
    receipt = {'version': VERSION, 'started_at': started, 'finished_at': started,
               'workflow': identity, 'provenance': 'LIVE_FTSHARE' if live else 'SYNTHETIC_TEST_ONLY',
               'calls': [], 'files': {}, 'stopped': None}
    bodies = {}; (root/'raw').mkdir(exist_ok=False)
    def checkpoint(): (root/'receipt.json').write_bytes(encode(receipt))
    checkpoint()
    for i, parameters in enumerate(plan['batches']):
        validate_parameters(parameters)
        call = {'parameters': parameters, 'requested_at': clock(), 'received_at': None,
                'status': 'REQUEST_STARTED', 'http_status': None, 'response_file': None}
        receipt['calls'].append(call); checkpoint()
        try:
            status, raw = fetch(ROUTE, parameters)
            model.check(type(status) is int and isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY
                        and sum(map(len, bodies.values())) + len(raw) <= MAX_TOTAL, 'minute response bound')
            key = os.environ.get('FTSHARE_API_KEY', '') if live else ''
            model.check(not key or key.encode() not in raw, 'CREDENTIAL_REFLECTION_REJECTED')
            name = f'raw/{i+1:02}.json'; (root/name).write_bytes(raw); bodies[name] = raw
            receipt['files'][name] = {'bytes': len(raw), 'sha256': model.sha256(raw)}
            call.update(http_status=status, response_file=name, status=response_status(status, raw))
        except (URLError, OSError, TimeoutError):
            call['status'] = 'TRANSPORT_FAILURE'
        except Exception as exc:
            call.update(status=str(exc) if str(exc) in STOP_CODES else 'SOURCE_REQUEST_FAILED', error_type=type(exc).__name__)
        call['received_at'] = clock(); receipt['finished_at'] = call['received_at']
        if call['status'] != 'RESPONSE_SAVED': receipt['stopped'] = call['status']
        checkpoint()
        if receipt['stopped']: break
    receipt['finished_at'] = clock(); checkpoint()
    report = build(plan, original, receipt, bodies)
    raw = encode(report); model.check(len(raw) <= saved.MAX_REPORT, 'minute report capacity')
    (root/'report.json').write_bytes(raw); (root/'summary.md').write_text(render(report), encoding='utf-8')
    return verify(root, expected_workflow=identity if live else None)


def verify(root, *, expected_workflow=None):
    root = saved.safe_root(root)
    def read(name, limit):
        p = saved.safe_root(root/model.safe_path(name)); model.check(p.stat().st_size <= limit, 'minute saved byte bound')
        return p.read_bytes()
    plan = saved.loads(read('plan.json', saved.MAX_REPORT)); receipt = saved.loads(read('receipt.json', saved.MAX_REPORT))
    original = replay_auction(read('auction-source.zip', model.MAX_ARCHIVE), plan['auction_archive'])
    model.check(plan == plan_for(original, plan['auction_archive'], plan['seed_reading_commit']), 'minute plan replay differs')
    model.check(receipt['version'] == VERSION and receipt['provenance'] in ('LIVE_FTSHARE', 'SYNTHETIC_TEST_ONLY'), 'minute receipt identity')
    model.check(receipt['workflow'] == (workflow_identity(receipt['workflow']) if receipt['provenance'] == 'LIVE_FTSHARE' else {}), 'minute workflow')
    model.check(expected_workflow is None or expected_workflow == receipt['workflow'], 'minute workflow mismatch')
    model.check(receipt['provenance'] != 'LIVE_FTSHARE' or original['provenance'] == 'LIVE_TUSHARE_RELAY',
                'minute live seed provenance')
    begin, finish = model.clock(receipt['started_at']), model.clock(receipt['finished_at'])
    model.check(begin <= finish <= begin+timedelta(minutes=10), 'minute capture clock')
    model.check(not plan['batches'] or begin >= datetime.fromtimestamp(plan['batches'][0]['until_ts_millis']//1000, saved.ZONE), 'minute future window')
    calls = receipt['calls']; model.check(0 <= len(calls) <= len(plan['batches']), 'minute request count')
    bodies, last, stop = {}, begin, None
    for i, call in enumerate(calls):
        model.check(stop is None and call['parameters'] == plan['batches'][i], 'minute request stop/order')
        validate_parameters(call['parameters'])
        asked, got = model.clock(call['requested_at']), model.clock(call['received_at'])
        model.check(last <= asked <= got <= finish, 'minute request clock'); last = got
        name = call['response_file']
        if name is None:
            model.check(call['http_status'] is None and call['status'] in STOP_CODES, 'minute transport outcome')
        else:
            model.check(name == f'raw/{i+1:02}.json', 'minute raw path')
            raw = read(name, MAX_BODY); bound(raw, receipt['files'][name]); bodies[name] = raw
            model.check(type(call['http_status']) is int and call['status'] == response_status(call['http_status'], raw), 'minute response replay')
        if call['status'] != 'RESPONSE_SAVED': stop = call['status']
    model.check(stop == receipt['stopped'] and (len(calls) == len(plan['batches']) or stop is not None), 'minute unexplained incomplete capture')
    model.check(set(receipt['files']) == set(bodies) and sum(map(len, bodies.values())) <= MAX_TOTAL, 'minute file inventory')
    model.check({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} ==
                set(bodies) | {'auction-source.zip', 'plan.json', 'receipt.json', 'report.json', 'summary.md'}, 'minute extra or absent files')
    result = build(plan, original, receipt, bodies)
    model.check(read('report.json', saved.MAX_REPORT) == encode(result)
                and read('summary.md', saved.MAX_REPORT) == render(result).encode(), 'minute report replay')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'capture', 'verify'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--reading-commit')
    args = parser.parse_args()
    if args.operation == 'prepare':
        from .current_state_delivery import GitHubAPI
        model.check(model.SHA.fullmatch(args.reading_commit or '') is not None, 'explicit reading commit required')
        plan = prepare(GitHubAPI(os.environ['GH_TOKEN'], max_calls=8), args.reading_commit, args.output)
        print(json.dumps({'planned_batches': len(plan['batches']), 'cohort_denominator': plan['cohort_denominator'], 'source_calls': 0}))
        return 0
    result = capture(args.output) if args.operation == 'capture' else verify(args.output)
    print(json.dumps({k: result[k] for k in ('status', 'observed_0940', 'cohort_denominator', 'source_stop', 'source_request_count')}))
    return 0 if result['source_stop'] is None else 2


if __name__ == '__main__':
    raise SystemExit(main())
