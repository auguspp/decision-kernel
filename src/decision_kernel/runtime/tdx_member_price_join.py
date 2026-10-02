"""Offline exact-date member/price join over retained qualified inputs.

Reuse the dated-member replay and raw-stock qualifier. No acquisition, as-of
fill, new ranks, return adjustment, production admission or historical-role claim.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from decimal import Context, Decimal, localcontext
from pathlib import Path
import re

from decision_kernel.identity import canonical_hash, canonical_json
from . import current_state as saved
from . import hithink_stock_reading as own
from . import tdx_member_source_check as members
from .research_commit_only import _json, _publish_report_files, _safe_path
from .sector_radar import _return_over

VERSION = 'tdx-dated-member-price-join-v1'
WINDOWS = (5, 20, 60)
CODE = re.compile(r'[0-9]{6}\.(SH|SZ|BJ)\Z')
AUTHORITY = {k: 'NONE' for k in ('research_authority', 'investment_authority',
                               'signal_transition_authority', 'human_attention_authority')}


def _run(run, workflow):
    saved.check(run['path'] == workflow and run['head_branch'] == 'main'
                and run['event'] == 'workflow_dispatch' and type(run['run_attempt']) is int and run['run_attempt'] == 1
                and run['status'] == 'completed' and run['conclusion'] == 'success'
                and type(run['id']) is int and run['id'] > 0
                and saved.SHA.fullmatch(run['head_sha']), 'source run differs')


def _prices(files, run, expected_report_hash):
    """Bind the existing capture, preserve failures, recheck usable raw windows.

    Calendar/selection qualification is inherited from the pinned original
    consumer, not a new calendar fetch or a re-selection of the sample.
    """
    _run(run, '.github/workflows/hithink-stock-dump-trial.yml')
    prefix = 'independent-stock-capture/'
    capture = _json(files[prefix + 'capture.json'])
    report = _json(files[prefix + 'observations.json'])
    saved.sealed(capture, 'capture_hash'); saved.sealed(report, 'report_hash')
    saved.check(report['report_hash'] == expected_report_hash, 'price report pin differs')
    saved.check(capture['version'] == 'hithink-independent-stock-capture-v1'
                and capture['provenance'] == 'LIVE_HITHINK'
                and report['version'] == 'independent-stock-captured-observations-v1'
                and report['source_capture_hash'] == capture['capture_hash'], 'price source differs')
    w = capture['workflow']
    saved.check(w['GITHUB_REPOSITORY'] == saved.REPOSITORY
                and w['GITHUB_SHA'] == run['head_sha'] and w['GITHUB_RUN_ID'] == str(run['id'])
                and w['GITHUB_RUN_ATTEMPT'] == '1' and w['GITHUB_REF'] == 'refs/heads/main'
                and w['GITHUB_EVENT_NAME'] == run['event'], 'price execution differs')
    saved.inventory(files, capture['files'], prefix)
    verification = _json(files['independent-stock-verification.json'])
    saved.check(verification['status'] == 'INDEPENDENT_OBSERVATIONS_REBUILT_FROM_EXACT_CAPTURE'
                and verification['report_hash'] == report['report_hash']
                and verification['capture_hash'] == capture['capture_hash']
                and verification['network_calls'] == 0, 'original replay receipt differs')
    selection = _json(files[prefix + 'selection.json'])
    saved.sealed(selection, 'selection_hash')
    saved.check(selection == report['selection']
                and selection['selection_hash'] == capture['selection_hash'], 'selection differs')
    saved.check(all(report[k] == capture[k] == v for k, v in AUTHORITY.items()), 'price authority differs')
    sessions = report['context']['sessions']
    saved.check(len(sessions) == 61 and sessions == sorted(set(sessions))
                and sessions[-1] == report['context']['comparison_session'], 'price calendar differs')
    days = tuple(date.fromisoformat(d) for d in sessions)
    inventory = report['inventory']
    saved.check(inventory['rows_hash'] == canonical_hash(inventory['rows']), 'quote inventory differs')
    column = inventory['columns'].index('thscode')
    quote_codes = [r[column] for r in inventory['rows']]
    saved.check(len(quote_codes) == len(set(quote_codes)) == selection['complete_denominator']
                and all(CODE.fullmatch(c) for c in quote_codes), 'quote denominator differs')
    observations = report['selected_observations']
    selected = [r['thscode'] for r in selection['selected']]
    saved.check(len(selected) == len(set(selected)) == report['sample_size']
                and [r['thscode'] for r in observations] == selected, 'sample changed')
    result = {}
    with localcontext(Context(prec=28)):
        for row in observations:
            code, path = row['thscode'], row['stock_path']
            saved.check(CODE.fullmatch(code), 'price security identity differs')
            if path is None:
                result[code] = {'status': 'RETAINED_INPUT_GAP', 'reason': row['reason_code'],
                                'original_status': row['status'], 'windows': {}}
                continue
            saved.check(row['status'] == 'CONTRACT_CHECKED_RAW_READING'
                        and path['price_convention'] == 'RAW_UNADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN',
                        'unsupported retained price convention')
            sources = row['sources']
            saved.check(len(sources) == 3 and [s['path'] for s in sources] ==
                        [own.HISTORY, own.SNAPSHOT, own.ACTIONS], 'price trace differs')
            parameters = [own.history_params(code, days), {'thscodes': code}, own.action_params(code, days)]
            raw = []
            previous = saved.clock(capture['observed_at'])
            for source, params in zip(sources, parameters, strict=True):
                saved.check(source['params'] == params and source['http_status'] == 200
                            and source['error_type'] is None, 'price request differs')
                requested, received = map(saved.clock, (source['requested_at'], source['received_at']))
                saved.check(previous <= requested <= received <= saved.clock(capture['finished_at']),
                            'price request clocks differ')
                previous = received
                name = source['response_file']; body = files[prefix + name]
                saved.check(capture['files'][name]['sha256'] == source['sha256'] == saved.sha256(body),
                            'price source bytes differ')
                raw.append(_json(body))
            own.check_history_receipt(raw[0], code=code, received_at=saved.clock(sources[0]['received_at']))
            own.check_quote_receipt(raw[1], code=code, received_at=saved.clock(sources[1]['received_at']))
            bars, checks = own.qualify(raw[0], raw[1], raw[2], code=code, sessions=days,
                params=parameters[0], observed_at=previous,
                quote_received_at=saved.clock(sources[1]['received_at']), selection_mode=True)
            windows = {}
            for n in WINDOWS:
                key = str(n); history = checks['history_window_checks'][key]
                action = checks['action_window_checks'][key]
                available = history['usable_for_raw_comparison'] and action['usable_for_raw_comparison']
                value = (_return_over(tuple(bars[d]['close_price'] for d in days[-n-1:]),
                                      end_index=n, sessions=n) if available else None)
                original = path['returns'][key]
                saved.check((value is None and original is None) or
                            (value is not None and original is not None and value == Decimal(original)),
                            'retained raw return no longer reproduces')
                windows[key] = {'base_session': days[-n-1].isoformat(), 'end_session': days[-1].isoformat(),
                    'status': 'RAW_COMPARABLE' if available else 'RAW_WINDOW_UNAVAILABLE',
                    'return': None if value is None else str(value),
                    'history_status': history['status'], 'action_status': action['status'],
                    'reported_action_dates': action['reported_event_dates']}
            result[code] = {'status': 'RECHECKED_RETAINED_RAW_PATH', 'reason': None,
                            'original_status': row['status'], 'windows': windows}
    return sessions, set(quote_codes), result, {
        'run_id': run['id'], 'code_commit': run['head_sha'], 'capture_hash': capture['capture_hash'],
        'report_hash': report['report_hash'], 'received_through': capture['finished_at'],
        'calendar_basis': 'PINNED_ORIGINAL_CONSUMER_NOT_FRESH_CALENDAR_QUALIFICATION',
        'unavailable_samples': [c for c, r in result.items() if r['status'] == 'RETAINED_INPUT_GAP']}


def join(snapshots, sessions, quote_codes, prices):
    """Exact date/security left join. Unobserved membership is never forward-filled."""
    saved.check(len(sessions) >= 61 and sessions == sorted(set(sessions)), 'common sessions required')
    for d in sessions:
        saved.check(date.fromisoformat(d).isoformat() == d, 'invalid session')
    end = sessions[-1]
    saved.check(end in snapshots and snapshots[end], 'terminal membership missing')
    for day, boards in snapshots.items():
        saved.check(date.fromisoformat(day).isoformat() == day and day <= end, 'future membership observation')
        for board, codes in boards.items():
            saved.check(re.fullmatch(r'[0-9]{6}\.TDX', board) and isinstance(codes, list)
                        and len(codes) == len(set(codes)) and all(CODE.fullmatch(c) for c in codes),
                        'invalid or duplicate membership')
    saved.check(all(isinstance(c, str) and CODE.fullmatch(c) for c in quote_codes)
                and set(prices) <= quote_codes, 'sample outside original quote universe')
    for source in prices.values():
        saved.check(source['status'] in {'RETAINED_INPUT_GAP', 'RECHECKED_RETAINED_RAW_PATH'},
                    'unknown price state')
        if source['status'] == 'RETAINED_INPUT_GAP':
            saved.check(source['windows'] == {} and isinstance(source['reason'], str) and source['reason'],
                        'failed price input cannot carry windows')
        else:
            saved.check(set(source['windows']) == {str(n) for n in WINDOWS}, 'missing price window')
            for w in source['windows'].values():
                saved.check(w['status'] in {'RAW_COMPARABLE', 'RAW_WINDOW_UNAVAILABLE'}, 'unknown window state')
                value = w['return']
                saved.check((value is None and w['status'] == 'RAW_WINDOW_UNAVAILABLE') or
                            (isinstance(value, str) and Decimal(value).is_finite()
                             and Decimal(value) > -1 and w['status'] == 'RAW_COMPARABLE'),
                            'price status/value inconsistent')
    groups = []
    for board, terminal in sorted(snapshots[end].items()):
        members_at = {d: set(b[board]) for d, b in snapshots.items() if board in b}
        windows = []
        for n in WINDOWS:
            required = sessions[-n-1:]
            missing = [d for d in required if d not in members_at]
            rows = []
            for code in sorted(terminal):
                observed_absent = [d for d in required if d in members_at and code not in members_at[d]]
                source = prices.get(code)
                price = None if source is None else source['windows'].get(str(n))
                state = ('QUOTE_ONLY_NO_RETAINED_PATH' if code in quote_codes else 'NOT_IN_PRICE_INPUT') if source is None else (
                    'RETAINED_INPUT_GAP' if source['status'] == 'RETAINED_INPUT_GAP' else price['status'])
                if price is not None:
                    saved.check(price['base_session'] == required[0] and price['end_session'] == end,
                                'price/member windows differ')
                rows.append({'code': code, 'price_status': state,
                    'raw_return': None if price is None else price['return'],
                    'price_gap': None if source is None else source['reason'],
                    'reported_action_dates': [] if price is None else price['reported_action_dates'],
                    'observed_nonmember_dates': observed_absent,
                    'membership_window_status': ('OBSERVED_NONMEMBER' if observed_absent else
                        'MISSING_OBSERVATIONS' if missing else 'MEMBER_OBSERVED_ALL_REQUIRED_DATES')})
            counts = dict(sorted(Counter(r['price_status'] for r in rows).items()))
            windows.append({'sessions': n, 'base_session': required[0], 'end_session': end,
                'required_member_observation_count': len(required), 'missing_member_observation_dates': missing,
                'available_member_observation_dates': [d for d in required if d in members_at],
                'terminal_member_count': len(terminal), 'price_counts': counts,
                'all_terminal_members_price_comparable': bool(rows) and all(r['price_status'] == 'RAW_COMPARABLE' for r in rows),
                'date_labeled_member_and_price_complete': bool(rows) and not missing and all(
                    not r['observed_nonmember_dates'] and r['price_status'] == 'RAW_COMPARABLE' for r in rows),
                'rows': rows})
        groups.append({'board': board, 'terminal_members': len(terminal),
            'observed_nonterminal_members': sorted(set().union(*members_at.values()) - set(terminal)),
            'nonterminal_scope': 'RETAINED_AS_OBSERVED_NOT_PRICED_OR_DROPPED_FROM_A_DYNAMIC_STUDY',
            'windows': windows})
    return groups


def build(member_raw, price_raw, pins):
    """Pins are supplied from actual GitHub metadata, not derived from candidate ZIPs."""
    saved.check(set(pins) == {'member', 'price'}, 'two explicit source pins required')
    mp, pp = pins['member'], pins['price']
    _run(mp['run'], members.WORKFLOW)
    mf = saved.unpack_archive(member_raw, mp['artifact'], mp['run'])
    pf = saved.unpack_archive(price_raw, pp['artifact'], pp['run'])
    identity = {'repository': saved.REPOSITORY, 'workflow': members.WORKFLOW,
                'code_commit': mp['run']['head_sha'], 'run_id': str(mp['run']['id']), 'run_attempt': 1}
    member_report = members.replay(mf, identity)
    saved.check(member_report['status'] == 'FOUR_DATED_GROUPS_MATCH_NATIVE', 'dated member comparison not qualified')
    native = members.native_inputs(mf)
    snapshots = {f'{d[:4]}-{d[4:6]}-{d[6:]}': {b: r['members'] for b, r in v['boards'].items()}
                 for d, v in native.items()}
    sessions, quotes, prices, price_origin = _prices(pf, pp['run'], pp['report_hash'])
    groups = join(snapshots, sessions, quotes, prices)
    payload = {'version': VERSION, 'status': 'EXACT_DATE_JOIN_WITH_EXPLICIT_GAPS',
        'estimator': 'TERMINAL_DATE_COHORT_TRAILING_WINDOWS_NOT_DYNAMIC_HISTORICAL_PORTFOLIO',
        'end_session': sessions[-1], 'groups': groups,
        'member_capture_hash': member_report['capture_hash'], 'member_acquired_at': member_report['captured_through'],
        'price_source': price_origin, 'source_pins': pins,
        'historical_effective_membership': 'NOT_ESTABLISHED', 'historical_pit_knowledge': 'NOT_ESTABLISHED',
        'rank_or_role_computed': False, 'production_admission': False, 'source_calls': 0, **AUTHORITY}
    payload['report_hash'] = canonical_hash(payload)
    return payload


def render(report):
    lines = ['# 日期成员与已保存价格路径的接合', '',
        '这是截止日成员的共同尾随窗口，不是历史动态组合、领先角色或今日行情。',
        '| 板块 | 窗口 | 完整成员 | 可用原始价格路径 | 有成员观察的日期/所需日期 | 完整接合 |',
        '|---|---:|---:|---:|---:|---|']
    for g in report['groups']:
        for w in g['windows']:
            lines.append(f"| {g['board']} | {w['sessions']} | {w['terminal_member_count']} | "
                f"{w['price_counts'].get('RAW_COMPARABLE', 0)} | "
                f"{len(w['available_member_observation_dates'])}/{w['required_member_observation_count']} | "
                f"{'日期标签及原始路径齐全' if w['date_labeled_member_and_price_complete'] else '仍有缺口'} |")
    lines += ['', '只保留两日名单，不能前向填充为整个窗口成员。已有报价不等于已有合格历史路径。',
        '缺路径、来源失败、公司行动跨窗分别保留；不删除缺失成员后排名，也不把未变两端称为连续成员。',
        '价格按原消费者重核；日历资格沿用精确保存结果。没有新采集、复权、Research、Odds或Watch。',
        '完整逐证券状态、缺失日期及原件定位见 join.json；原档案保留期不因本派生结果延长。',
        'report_hash: ' + report['report_hash'], '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('member-zip', 'price-zip', 'pins', 'pins-sha256', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    def read(path, limit):
        p = Path(path); _safe_path(p)
        with p.open('rb') as stream:
            raw = stream.read(limit + 1)
        saved.check(len(raw) <= limit, 'input exceeds bound')
        return raw
    raw_pins = read(args.pins, 64 * 1024)
    saved.check(saved.sha256(raw_pins) == args.pins_sha256, 'external pins identity differs')
    result = build(read(args.member_zip, saved.MAX_ARCHIVE), read(args.price_zip, saved.MAX_ARCHIVE), _json(raw_pins))
    _publish_report_files(Path(args.output), {'join.json': (canonical_json(result) + '\n').encode(),
                                            'join.md': render(result).encode()})
    print(result['report_hash'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
