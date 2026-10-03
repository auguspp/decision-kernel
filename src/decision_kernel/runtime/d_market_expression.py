"""Read-only D context over already retained inputs; no acquisition or decisions.

This is the simple close-range baseline for #331 and the completed-session
member-expression building block for #677, not a Chan or intraday detector.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import json
from html import escape
from statistics import median
from zipfile import BadZipFile

PATH = 'details/stock/market-expression.json'
VERSION = 'd-saved-market-expression-v1'
PROFILE = 'preceding-close-range-and-confirmed-close-turn-v1'
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, BadZipFile)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value):
    _require(type(value) in (str, int, Decimal), 'expression number type')
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('expression invalid decimal') from exc
    _require(number.is_finite(), 'expression nonfinite number')
    return number


def _text(value):
    if value is None:
        return None
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def close_structure(sessions, closes, windows):
    """Use only the supplied prefix. Confirmation time is NOT the turn time.

    Windows are explicit caller choices. Closing ranges are not OHLC ranges,
    Chan strokes, economic evidence, or inferred timestamps of public knowledge.
    """
    _require(len(sessions) == len(closes) and bool(sessions), 'structure dimensions')
    days = [date.fromisoformat(day) for day in sessions]
    _require(days == sorted(set(days)), 'structure session order')
    values = [_number(value) for value in closes]
    _require(all(value > 0 for value in values), 'structure positive close')
    _require(len(windows) == len(set(windows)) and all(type(n) is int and n > 0 for n in windows),
             'structure windows')
    ranges = {}
    for n in windows:
        if len(values) <= n:
            ranges[str(n)] = {'status': 'INSUFFICIENT_PREFIX', 'required_closes': n + 1}
            continue
        prior = values[-n-1:-1]
        low, high, current = min(prior), max(prior), values[-1]
        state = ('ABOVE_PRECEDING_CLOSE_RANGE' if current > high else
                 'BELOW_PRECEDING_CLOSE_RANGE' if current < low else
                 'AT_CLOSE_RANGE_BOUNDARY' if current in (low, high) else 'WITHIN_PRECEDING_CLOSE_RANGE')
        ranges[str(n)] = {'status': state, 'lower': _text(low), 'upper': _text(high),
            'range_start': sessions[-n-1], 'range_end': sessions[-2]}
    turns = []
    for i in range(1, len(values)-1):
        kind = ('CLOSE_PEAK' if values[i] > max(values[i-1], values[i+1]) else
                'CLOSE_TROUGH' if values[i] < min(values[i-1], values[i+1]) else None)
        if kind:
            turns.append({'kind': kind, 'turn_session': sessions[i],
                          'confirmed_session': sessions[i+1], 'close': _text(values[i])})
    candidate = None
    if len(values) >= 2 and values[-1] != values[-2]:
        candidate = {'kind': 'CLOSE_PEAK' if values[-1] > values[-2] else 'CLOSE_TROUGH',
                     'turn_session': sessions[-1], 'close': _text(values[-1]),
                     'status': 'UNCONFIRMED_RIGHT_BAR_NOT_AVAILABLE'}
    return {'profile': PROFILE, 'market_session': sessions[-1], 'prefix_count': len(values),
            'ranges': ranges, 'last_confirmed_turn': turns[-1] if turns else None,
            'current_candidate': candidate, 'input_basis': 'CLOSE_ONLY_NOT_OHLC_OR_CHAN',
            'knowledge_semantics': 'PREFIX_ARITHMETIC_NOT_HISTORICAL_AVAILABILITY_PROOF'}


def member_expression(report, groups):
    """Join identities, not providers' prices; retain every member and gap."""
    columns = report['columns']
    _require(len(columns) == len(set(columns)), 'duplicate expression columns')
    positions = {key: i for i, key in enumerate(columns)}
    windows = tuple(sorted((int(n) for n in report['bases']), key=int))
    prices = {}
    for raw in report['rows']:
        _require(len(raw) == len(columns), 'expression row shape')
        symbol = raw[positions['symbol']]
        _require(symbol not in prices, 'duplicate price identity')
        prices[symbol] = raw
    _require(len(prices) == report['cohort_denominator'], 'expression price denominator')
    output = []
    for group in groups:
        members = group['members']
        symbols = [row['symbol'] for row in members]
        _require(len(symbols) == len(set(symbols)), 'duplicate membership identity')
        rows, summaries = [], {}
        for member in members:
            rows.append({'symbol': member['symbol'], 'name': member['name'], 'windows': {}})
        for n in windows:
            changes = {}
            for row in rows:
                raw = prices.get(row['symbol'])
                status = raw[positions[f'status_{n}']] if raw is not None else 'END_IDENTITY_NOT_RETURNED'
                change = raw[positions[f'change_{n}']] if raw is not None else None
                _require(type(status) in (int, str), 'expression status type')
                _require((type(status) is int and status == 0) == (change is not None),
                         'expression qualification/value disagreement')
                value = _number(change) if change is not None else None
                if value is not None:
                    changes[row['symbol']] = value
                row['windows'][str(n)] = {'source_status': status, 'return': _text(value),
                                         'relative_to_median': None, 'rank': None}
            with localcontext() as ctx:
                ctx.prec = 60
                center = median(changes.values()) if changes else None
                ordered = sorted(changes.values(), reverse=True)
                ranks = {}
                for i, value in enumerate(ordered, 1):
                    ranks.setdefault(value, i)
                for row in rows:
                    if row['symbol'] in changes:
                        value = changes[row['symbol']]
                        row['windows'][str(n)].update(relative_to_median=_text(value-center), rank=ranks[value])
            summaries[str(n)] = {'denominator': len(members), 'comparable': len(changes),
                'unavailable': len(members)-len(changes), 'median_return': _text(center),
                'positive': sum(value > 0 for value in changes.values()),
                'negative': sum(value < 0 for value in changes.values()),
                'unchanged': sum(value == 0 for value in changes.values()),
                'ranking_scope': 'ALL_DECLARED_MEMBERS' if len(changes) == len(members) else 'COMPARABLE_SUBSET',
                'top_symbols': sorted(key for key, value in changes.items() if ranks[value] == 1)}
        output.append({key: value for key, value in group.items() if key != 'members'} |
                      {'member_count': len(members), 'windows': summaries, 'rows': rows})
    return {'version': VERSION, 'market_session': report['market_session'], 'bases': report['bases'],
            'price_denominator': len(prices), 'group_count': len(output), 'groups': output,
            'member_occurrences': sum(group['member_count'] for group in output),
            'distinct_members': len({row['symbol'] for group in output for row in group['rows']}),
            'price_basis': report['comparison_basis'],
            'meaning': 'DECLARED_MEMBERS_PRICE_CONTEXT_NOT_OPPORTUNITY_ODDS',
            'intraday_freshness': 'NOT_ESTABLISHED', 'persistence_rotation': 'NOT_ESTABLISHED',
            'historical_membership': 'NOT_ESTABLISHED', 'economic_leadership': 'NOT_ESTABLISHED',
            'investment_authority': 'NONE', 'human_attention_authority': 'NONE',
            'automatic_research_routing': False, 'new_source_requests': 0}


def render(report):
    lines = ['\n\n## D：已保存名单的多期限市场表达（只读）\n',
        f"价格市场日：{report['market_session']}；{report['group_count']}个主节点，"
        f"{report['member_occurrences']}次成员关系。名单日期分别保留，不冒称历史当时成员。",
        '以下为可比成员等权中位数，不是行业指数收益；不同期限的强势个体不自动成为跨周期龙头。',
        '\n| 主节点 | 成员 | 5日可比／中位数 | 20日可比／中位数 | 60日可比／中位数 |',
        '|---|---:|---:|---:|---:|']
    for group in report['groups']:
        cells = []
        for n in (5, 20, 60):
            window = group['windows'].get(str(n))
            if window is None:
                cells.append('未请求')
                continue
            center = window['median_return']
            change = '—' if center is None else f"{Decimal(center)*100:+.2f}%"
            cells.append(f"{window['comparable']}/{window['denominator']}；{change}")
        name = escape(group['name']).replace('|', '／').replace('\n', ' ').replace('[', '［').replace(']', '］')
        lines.append(f"| {name} | {group['member_count']} | " + ' | '.join(cells) + ' |')
    structures = [g for g in report['groups'] if 'index_close_structure' in g]
    if structures:
        labels = {'ABOVE_PRECEDING_CLOSE_RANGE': '高于区间',
                  'BELOW_PRECEDING_CLOSE_RANGE': '低于区间',
                  'AT_CLOSE_RANGE_BOUNDARY': '区间边界',
                  'WITHIN_PRECEDING_CLOSE_RANGE': '区间内',
                  'INSUFFICIENT_PREFIX': '历史不足'}
        lines += ['\n| 主节点指数 | 结构市场日 | 前5／20／60日收盘区间位置 | 最近局部转折：发生→确认 |',
                  '|---|---|---|---|']
        for group in structures:
            structure = group['index_close_structure']
            states = '／'.join(labels.get(structure['ranges'].get(str(n), {}).get('status'), '未请求')
                              for n in (5, 20, 60))
            turn = structure['last_confirmed_turn']
            mark = ('收盘局部高点' if turn and turn['kind'] == 'CLOSE_PEAK' else '收盘局部低点')
            turn_text = f"{mark} {turn['turn_session']}→{turn['confirmed_session']}" if turn else '无已确认转折'
            lines.append(f"| {group['code']} | {structure['market_session']} | {states} | {turn_text} |")
    lines += ['\n价格结构仅为收盘区间／局部转折的简单基线，不是缠论认证、盘中领先、短线买卖点或预期收益。',
              f'完整成员、逐期限强弱／缺口、结构日期及来源见 [{PATH}]({PATH})。\n']
    return '\n'.join(lines)


def read_saved(collector, baseline, daily):
    """Optional derived view. Its failure must not remove usable stock inputs."""
    from . import current_state as model
    from . import current_state_delivery as delivery
    from .independent_stock_reading import _cached
    from .hithink_sector_breadth_http import (HITHINK_SECTOR_CONSTITUENTS_PATH,
                                              normalize_hithink_sector_membership)
    from .sector_radar_state import parse_sector_radar_market_state
    from decision_kernel.identity import canonical_hash, canonical_json

    prior_output = collector.files.get(PATH)
    result = {'status': 'D_EXPRESSION_INPUT_NOT_AVAILABLE', 'summary': '', 'new_source_requests': 0}
    selected = daily if any(daily.get('qualified_windows', {}).values()) else daily.get('last_qualified_result')
    if not selected:
        return result
    try:
        descriptor = selected['file']
        raw = collector.files[model.safe_path(descriptor['read_path'])]
        model.check(len(raw) == descriptor['bytes'] and model.sha256(raw) == descriptor['sha256']
                    and model.blob_sha(raw) == descriptor['git_blob'], 'D price input identity')
        prices = json.loads(raw)
        sector = baseline['lanes']['sector']['last_qualified_result']
        archive = sector['archive']
        files = _cached(collector, archive, baseline['checks']['finished_at'])
        source_result = json.loads(files['result.json'])
        model.check(source_result['result_hash'] == canonical_hash({k: v for k, v in source_result.items()
                    if k != 'result_hash'}), 'D sector result identity')
        model.check(source_result['market_session'] == sector['market_session'],
                    'D sector session identity')
        audit = json.loads(files['input-audit/manifest.json'])
        groups = []
        for group in source_result['composition']['all_groups']:
            primary = group['primary_candidate']
            matches = [q for q in audit['requests'] if q['path'] == HITHINK_SECTOR_CONSTITUENTS_PATH
                       and q['params'].get('thscode') == primary['thscode']]
            model.check(len(matches) == 1 and matches[0]['error_type'] is None, 'D membership source identity')
            request = matches[0]
            body = files['input-audit/' + model.safe_path(request['response_file'])]
            inventory = audit['files'][request['response_file']]
            model.check(len(body) == inventory['bytes'] and model.sha256(body) == inventory['sha256'],
                        'D membership bytes')
            membership = normalize_hithink_sector_membership(json.loads(body),
                sector_thscode=primary['thscode'], sector_name=primary['name'])
            groups.append({'code': primary['thscode'], 'name': primary['name'],
                'parent_group_key': group['group_key'], 'membership_market_session': source_result['market_session'],
                'membership_captured_at': membership.captured_at.isoformat(),
                'membership_source_file': request['response_file'],
                'members': [{'symbol': m.thscode, 'name': m.name} for m in membership.members]})
        report = member_expression(prices, groups)
        report['price_file'] = descriptor
        report['latest_price_attempt_status'] = daily['status']
        report['using_last_qualified_result'] = selected is not daily
        report['sector_archive'] = archive
        report['price_received_through'] = selected.get('received_through')
        report['sector_market_session'] = sector['market_session']
        report['code_commit'] = collector.code_commit
        report['checked_at'] = baseline['checks']['finished_at']
        report['structure_status'] = 'NOT_AVAILABLE'
        # Independent optional purpose; unavailable structure cannot suppress
        # endpoint-qualified member comparisons or make up missing daily bars.
        try:
            state = parse_sector_radar_market_state(files['input-audit/expected/state/market-state.json'].decode())
            model.check(state.state_hash == sector['market_state_hash'], 'D close state identity')
            model.check(state.sessions[-1].isoformat() == sector['market_session'],
                        'D close state market session')
            series = {item.thscode: item for item in state.series}
            sessions = [day.isoformat() for day in state.sessions]
            for group in report['groups']:
                item = series[group['code']]
                group['index_close_structure'] = close_structure(sessions, item.closes,
                                                                  tuple(int(n) for n in prices['bases']))
            report['structure_status'] = 'SAVED_INDEX_CLOSE_BASELINE_NOT_STOCK_CHAN'
            report['structure_source_state_hash'] = state.state_hash
        except ERRORS as exc:
            report['structure_gap'] = type(exc).__name__
        report['report_hash'] = canonical_hash(report)
        output = (canonical_json(report) + '\n').encode()
        summary = render(report)
        model.check(len(output) <= 512*1024, 'D expression detail bound')
        model.check(sum(map(len, collector.files.values())) + len(output) + 2*len(summary.encode()) + 24*1024
                    <= delivery.MAX_RETAINED_OUTPUT, 'D expression total bound')
        model.check(collector.api.calls + len(set(collector.files) | {PATH, 'current-state.json', 'README.md'}) + 12
                    <= collector.api.max_calls, 'D expression publication reserve')
        result.update(status='D_SAVED_EXPRESSION_READ_OK', file=collector.retain(PATH, output),
                      summary=summary, report_hash=report['report_hash'])
    except ERRORS as exc:
        if prior_output is None:
            collector.files.pop(PATH, None)
        else:
            collector.files[PATH] = prior_output
        result.update(status='D_EXPRESSION_READING_GAP', error_type=type(exc).__name__,
                      summary='\nD成员表达暂未能读回；原日常价格和各期限资格保持，不代表没有机会。\n')
    return result
