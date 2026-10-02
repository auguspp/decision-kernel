"""Offline reader for the retired fixed C2 historical-window capture format.

No acquisition entry remains. Retain original input, plan, price qualification
and failure semantics; this reader neither completes C2 nor restores authority.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
from decimal import Context, localcontext
import json
from pathlib import Path
import re

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import current_state as saved
from decision_kernel.runtime import global_market_context as common
from decision_kernel.runtime import hithink_stock_reading as own
from decision_kernel.runtime import tdx_member_price_join as joined
from decision_kernel.runtime import tdx_member_source_check as member
from decision_kernel.runtime import tushare_relay as relay
from decision_kernel.runtime.research_commit_only import _json, _safe_path
from decision_kernel.runtime.sector_radar import _return_over

PILOT = 'c2-dye-five-session-20261002'
WORKFLOW = '.github/workflows/c2-dated-window.yml'
BOARD = '880706.TDX'
TARGETS = {BOARD: '分散染料'}
PINS_PATH = 'docs/readings/c2-dated-member-price-join-2026-10-02/input-pins.json'
PINS_SHA = '0d2bc18dd624a4aa500c53190107a5ff0a17b772f8545038d1e0f14c828b0cf3'
DATES = ['2026-09-22', '2026-09-23', '2026-09-24', '2026-09-28', '2026-09-29', '2026-09-30']
MAX_TOTAL = 16 * 1024 * 1024
PAUSE = 20


def encoded(value):
    return (canonical_json(value) + '\n').encode()


def inputs(root):
    """Recheck both original archives; never infer pins from candidate bytes."""
    root = Path(root)
    for name in ('input-pins.json', 'member-source.zip', 'price-source.zip'):
        _safe_path(root/name)
        saved.check((root/name).is_file() and (root/name).stat().st_size <= saved.MAX_ARCHIVE, 'input size/path differs')
    raw = (root / 'input-pins.json').read_bytes()
    saved.check(saved.sha256(raw) == PINS_SHA, 'input pins changed')
    pins = _json(raw)
    mf = saved.unpack_archive((root/'member-source.zip').read_bytes(), pins['member']['artifact'], pins['member']['run'])
    pf = saved.unpack_archive((root/'price-source.zip').read_bytes(), pins['price']['artifact'], pins['price']['run'])
    original = joined.build((root/'member-source.zip').read_bytes(), (root/'price-source.zip').read_bytes(), pins)
    native = member.native_inputs(mf)
    snapshots = {f'{d[:4]}-{d[4:6]}-{d[6:]}': {BOARD: v['boards'][BOARD]['members']} for d, v in native.items()}
    sessions, quote_codes, prices, _ = joined._prices(pf, pins['price']['run'], pins['price']['report_hash'])
    cohort = snapshots[DATES[-1]][BOARD]
    saved.check(sessions[-6:] == DATES and len(cohort) == 20 and '301190.SZ' in cohort,
                'fixed cohort/calendar differs')
    report = _json(pf['independent-stock-capture/observations.json'])
    quotes = {}
    for page in report['pages']:
        name = 'independent-stock-capture/' + page['file']
        body = pf[name]
        saved.check(page['path'] == own.SNAPSHOT and saved.sha256(body) == page['sha256']
                    and len(body) == page['bytes'], 'original quote page differs')
        data = _json(body)['data']
        for row in data['item']:
            code = row['thscode']
            if code not in cohort:
                continue
            saved.check(code not in quotes, 'duplicate original quote')
            quotes[code] = {'quote': {'code': 0, 'data': {'timestamp': data['timestamp'], 'item': [row]}},
                'received_at': page['captured_at'], 'source_file': name, 'source_sha256': page['sha256'],
                'semantics': 'DERIVED_ONE_ROW_OF_RETAINED_ALL_MARKET_RESPONSE_NOT_NEW_QUOTE'}
    saved.check(set(quotes) == set(cohort) and set(prices).intersection(cohort) == {'301190.SZ'},
                'price reuse scope changed')
    return snapshots, sessions, quote_codes, prices, quotes, original


def plan(base):
    snapshots, sessions, _, prices, quotes, _ = base
    specs = []
    for day in DATES:
        if day in snapshots:
            continue
        for api in ('tdx_index', 'tdx_member'):
            params = {'trade_date': day.replace('-', ''), 'fields': ','.join(member.FIELDS[api]),
                      'limit': '1000' if api == 'tdx_index' else '3000'}
            params.update({'idx_type': '概念板块'} if api == 'tdx_index' else {'ts_code': BOARD})
            specs.append({'source': 'RELAY', 'api': api, 'params': params})
    days = tuple(map(date.fromisoformat, sessions))
    for code in sorted(quotes.keys() - prices.keys()):
        for kind, path, params in [('history', own.HISTORY, own.history_params(code, days)),
                                   ('actions', own.ACTIONS, own.action_params(code, days))]:
            specs.append({'source': 'HITHINK', 'code': code, 'kind': kind, 'path': path, 'params': params})
    saved.check(len(specs) == 46 and sum(s['source'] == 'RELAY' for s in specs) == 8, 'request budget differs')
    return specs


def identity(env):
    value = {k: env.get(k) for k in ('GITHUB_REPOSITORY', 'GITHUB_SHA', 'GITHUB_RUN_ID',
             'GITHUB_RUN_ATTEMPT', 'GITHUB_REF', 'GITHUB_EVENT_NAME')}
    saved.check(value['GITHUB_REPOSITORY'] == saved.REPOSITORY and value['GITHUB_REF'] == 'refs/heads/main'
                and value['GITHUB_EVENT_NAME'] == 'workflow_dispatch' and value['GITHUB_RUN_ATTEMPT'] == '1'
                and re.fullmatch(r'[0-9a-f]{40}', value['GITHUB_SHA'] or '')
                and re.fullmatch(r'[1-9][0-9]*', value['GITHUB_RUN_ID'] or ''), 'execution identity differs')
    return value


def raw_windows(history, actions, quote, sessions, received):
    days = tuple(map(date.fromisoformat, sessions))
    own.check_history_receipt(history, code=quote['quote']['data']['item'][0]['thscode'], received_at=saved.clock(received))
    code = quote['quote']['data']['item'][0]['thscode']
    bars, checks = own.qualify(history, quote['quote'], actions, code=code, sessions=days,
        params=own.history_params(code, days), observed_at=saved.clock(received),
        quote_received_at=saved.clock(quote['received_at']), selection_mode=True)
    windows = {}
    with localcontext(Context(prec=28)):
        for n in joined.WINDOWS:
            h, a = checks['history_window_checks'][str(n)], checks['action_window_checks'][str(n)]
            available = h['usable_for_raw_comparison'] and a['usable_for_raw_comparison']
            value = _return_over(tuple(bars[d]['close_price'] for d in days[-n-1:]), end_index=n, sessions=n) if available else None
            windows[str(n)] = {'base_session': sessions[-n-1], 'end_session': sessions[-1],
                'status': 'RAW_COMPARABLE' if available else 'RAW_WINDOW_UNAVAILABLE',
                'return': None if value is None else str(value), 'history_status': h['status'],
                'action_status': a['status'], 'reported_action_dates': a['reported_event_dates']}
    return {'status': 'RECHECKED_RETAINED_RAW_PATH', 'reason': None, 'windows': windows}


def rebuild(root, expected):
    """Pure reconstruction including partial failures; no writes or source calls."""
    root = Path(root); expected = identity(expected)
    _safe_path(root/'capture.json'); _safe_path(root/'result')
    saved.check(len(list(root.iterdir())) <= 110 and sum(p.stat().st_size for p in root.iterdir() if p.is_file()) <= MAX_TOTAL, 'capture size exceeded')
    base = inputs(root)
    snapshots, sessions, quote_codes, prices, quotes, original = deepcopy(base)
    m = _json((root/'capture.json').read_bytes())
    saved.sealed(m, 'capture_hash')
    saved.check(m['pilot'] == PILOT and m['identity'] == expected and m['workflow'] == WORKFLOW
                and m['authority'] == joined.AUTHORITY and m['plan'] == plan(base), 'capture binding differs')
    saved.check(type(m['complete']) is bool and len(m['records']) == len(m['plan']), 'capture completion differs')
    first, finish = map(saved.clock, (m['started_at'], m['finished_at']))
    saved.check(first <= finish, 'capture time reversed')
    seen = {'input-pins.json', 'member-source.zip', 'price-source.zip', 'capture.json'}
    catalogs, histories, outcomes, stopped = {}, {}, [], False
    previous = first
    last_own = None
    for i, (spec, record) in enumerate(zip(m['plan'], m['records'], strict=True)):
        saved.check(record['index'] == i and record['spec'] == spec, 'request identity differs')
        attempts = record['attempts']
        saved.check(len(attempts) <= (2 if spec['source'] == 'RELAY' else 1), 'request attempts exceeded')
        saved.check(not stopped or not attempts and record['status'] == 'NOT_ATTEMPTED_STOP', 'stop was ignored')
        state, reason = record['status'], None
        if not attempts:
            saved.check(state in {'NOT_ATTEMPTED_STOP', 'CREDENTIAL_UNAVAILABLE', 'REQUEST_IN_PROGRESS',
                                  'NOT_ATTEMPTED', 'REQUEST_RECEIPT_UNAVAILABLE'}, 'unknown unexecuted state')
            saved.check(not m['complete'] or state not in {'NOT_ATTEMPTED', 'REQUEST_IN_PROGRESS'}, 'false completion')
            stopped = True
        bodies = []
        for k, attempt in enumerate(attempts, 1):
            name = attempt['body']
            saved.check(name is None or name == f'raw-{i:02d}-{k}.json', 'response path differs')
            raw = None if name is None else (root/name).read_bytes()
            if name: seen.add(name)
            requested, received = map(saved.clock, (attempt['requested_at'], attempt['received_at']))
            saved.check(previous <= requested <= received <= finish and attempt['attempt'] == k, 'receipt clock differs')
            if spec['source'] == 'RELAY':
                common.validate_attempt(attempt, raw, first, finish)
                if k == 2:
                    saved.check(attempts[0]['classification'] == 'TEMPORARY_QUEUE'
                        and (requested-previous).total_seconds() >= relay.RETRY_WAIT_SECONDS, 'retry differs')
            else:
                saved.check(k == 1 and first <= requested and raw is not None and attempt['http_status'] == 200
                    and len(raw) == attempt['bytes'] and saved.sha256(raw) == attempt['sha256'], 'own response differs')
                if last_own is not None:
                    saved.check((requested-last_own).total_seconds() >= PAUSE, 'stock pacing differs')
                last_own = received
            bodies.append(raw); previous = received
        if attempts:
            saved.check(state == attempts[-1]['classification'], 'last request state differs')
            if state != 'SUCCESS': stopped = True
            else:
                try:
                    if spec['source'] == 'RELAY':
                        table = member.qualify_page(bodies[-1], {'api': spec['api'], 'params': spec['params']},
                                                    attempts[-1]['received_at'], boards=TARGETS)
                        d = spec['params']['trade_date']; day = f'{d[:4]}-{d[4:6]}-{d[6:]}'
                        if spec['api'] == 'tdx_index':
                            catalogs[day] = next(r['idx_count'] for r in table['rows'] if r['ts_code'] == BOARD)
                        else:
                            codes = sorted(r['con_code'] for r in table['rows'])
                            saved.check(len(codes) == catalogs[day], 'same-day catalog count differs')
                            snapshots[day] = {BOARD: codes}
                    elif spec['kind'] == 'history':
                        value = _json(bodies[-1])
                        own.check_history_receipt(value, code=spec['code'], received_at=previous)
                        histories[spec['code']] = value
                    else:
                        code = spec['code']
                        value = _json(bodies[-1])
                        # Match capture's stop before issuer-local price qualification.
                        saved.check(isinstance(value, dict) and type(value.get('code')) is int
                                    and value['code'] == 0, 'stock business response requires stop')
                        try:
                            prices[code] = raw_windows(histories[code], value, quotes[code], sessions,
                                                      attempts[-1]['received_at'])
                        except own.StockReadingInputError as exc:
                            prices[code] = {'status': 'RETAINED_INPUT_GAP', 'reason': exc.reason_code, 'windows': {}}
                            state, reason = 'PRICE_INPUT_GAP', exc.reason_code
                except (ValueError, KeyError, TypeError):
                    state, stopped = 'SOURCE_INPUT_UNQUALIFIED', True
        outcomes.append({'index': i, 'spec': spec, 'status': state, 'reason': reason, 'attempts': len(attempts)})
    allowed = seen | {'result', 'verification.json'}
    saved.check({p.name for p in root.iterdir()} <= allowed, 'unexpected capture file')
    groups = joined.join(snapshots, sessions, quote_codes, prices)
    five = groups[0]['windows'][0]
    report = {'version': PILOT, 'status': 'FIVE_SESSION_COHORT_INPUTS_COMPLETE' if five['date_labeled_member_and_price_complete']
        else 'WINDOW_INPUTS_WITH_EXPLICIT_GAPS', 'groups': groups, 'end_session': sessions[-1],
        'identity': expected, 'capture_hash': m['capture_hash'], 'source_pins': original['source_pins'],
        'base_report_hash': original['report_hash'], 'original_price_gaps': original['price_source']['unavailable_samples'],
        'outcomes': outcomes, 'logical_queries': sum(r['status'] not in {'NOT_ATTEMPTED_STOP', 'CREDENTIAL_UNAVAILABLE', 'NOT_ATTEMPTED'} for r in m['records']),
        'logical_queries_with_receipts': sum(bool(r['attempts']) for r in m['records']),
        'unknown_request_receipts': sum(r['status'] in {'REQUEST_IN_PROGRESS', 'REQUEST_RECEIPT_UNAVAILABLE'} for r in m['records']),
        'http_attempts': sum(len(r['attempts']) for r in m['records']), 'source_calls_during_replay': 0,
        'raw_price_contract': own.CONTRACT, 'quote_provenance': quotes, 'requested_member_dates': DATES,
        'acquired_through': m['finished_at'], 'historical_pit_knowledge': 'NOT_ESTABLISHED',
        'historical_effective_membership': 'NOT_ESTABLISHED', 'rank_or_role_computed': False,
        'production_admission': False, **joined.AUTHORITY}
    report['report_hash'] = canonical_hash(report)
    return report


def render(report):
    text = joined.render(report)
    # The old renderer described a two-day/offline-only example, not this acquisition.
    text = text.replace('只保留两日名单，不能前向填充为整个窗口成员。已有报价不等于已有合格历史路径。',
                        '仅按实际取得的各日名单连接；未取得的日期不前向填充。已有报价不等于合格历史路径。')
    text = text.replace('价格按原消费者重核；日历资格沿用精确保存结果。没有新采集、复权、Research、Odds或Watch。',
                        '本次有界补取来源输入；价格沿原消费者重核，日历沿精确保存结果。没有复权、Research、Odds或Watch。')
    return text + '\n本次状态：' + report['status'] + '；原始取得时间：' + report['acquired_through'] + '\n'



def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['verify'])
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--run-id', required=True)
    p.add_argument('--code-commit', required=True)
    a = p.parse_args(argv)
    expected = identity({
        'GITHUB_REPOSITORY': saved.REPOSITORY, 'GITHUB_SHA': a.code_commit, 'GITHUB_RUN_ID': a.run_id,
        'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_REF': 'refs/heads/main', 'GITHUB_EVENT_NAME': 'workflow_dispatch'})
    r = rebuild(a.root, expected)
    saved.check((a.root/'result/join.json').read_bytes() == encoded(r) and
                (a.root/'result/join.md').read_bytes() == render(r).encode(), 'offline reconstruction differs')
    # Verification is read-only, including repeated reads. No credentials or writes.
    print(r['status'], r['report_hash'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
