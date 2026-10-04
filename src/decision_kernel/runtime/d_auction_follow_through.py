"""Join saved auction decisions to same-session closes; no acquisition or trading.

The existing readers own source replay. This projection preserves their complete
cohort, failures and clocks. It does not create a portfolio or a return backtest.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from statistics import median

from . import current_state as model
from . import d_auction_probe as probe
from . import stock_market_inputs as prices

PATH = 'details/stock/auction-follow-through.json'
VERSION = 'd-auction-same-session-outcome-v1'
COLUMNS = (*probe.ROW_COLUMNS, 'same_session_close', 'auction_to_close_change', 'outcome_status')
GROUPS = {
    'MATCHED': '原条件匹配组',
    'NOT_MATCHED': '竞价可比但未匹配组',
    'AUCTION_UNRESOLVED': '静态条件内但竞价未完成组',
    'STATIC_EXCLUDED': '静态条件排除组',
    'STATIC_UNRESOLVED': '静态条件未能判断组',
}
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, ArithmeticError)


def _group(row):
    state = row['status']
    if state == 'SHADOW_PROFILE_MATCH':
        model.check(row['matched_profile'] is True, 'outcome match flag differs')
        return 'MATCHED'
    model.check(row['matched_profile'] is False, 'outcome match flag differs')
    if state == 'OUTSIDE_AUCTION_GAP_PROFILE':
        return 'NOT_MATCHED'
    if state in ('AUCTION_INPUT_UNAVAILABLE', 'AUCTION_ROW_UNAVAILABLE', 'AUCTION_VALUE_UNAVAILABLE_OR_CONFLICT'):
        return 'AUCTION_UNRESOLVED'
    if state in ('EXCLUDED_BOARD', 'EXCLUDED_PRIOR_ST_NAME', 'OUTSIDE_PRIOR_TURNOVER_PROFILE'):
        return 'STATIC_EXCLUDED'
    return 'STATIC_UNRESOLVED'


def project(auction: dict, daily: dict | None) -> dict:
    """Pure left join on exact securities and one market date, without filtering."""
    target = probe.target_day(auction['market_session'])
    model.check(auction['version'] in (probe.LEGACY_VERSION, probe.VERSION)
                and auction['profile'] == probe.PROFILE and auction['source'] == prices.SOURCE,
                'outcome auction identity')
    model.check(auction['columns'] == list(probe.ROW_COLUMNS), 'outcome auction columns')
    source_rows = probe.row_dicts(auction)
    model.check(type(auction['cohort_denominator']) is int
                and len(source_rows) == auction['cohort_denominator'], 'outcome denominator')
    symbols = [row['symbol'] for row in source_rows if row['symbol'] is not None]
    model.check(all(isinstance(s, str) and prices.CODE.fullmatch(s) for s in symbols)
                and len(symbols) == len(set(symbols)), 'outcome cohort identity')
    close_rows = {}
    if daily is not None:
        model.check(daily['version'] == prices.VERSION and daily['source'] == auction['source']
                    and daily['provenance'] == auction['provenance'], 'outcome daily source differs')
        model.check(daily['market_session'] == target.isoformat()
                    and daily['end_date'] == target.strftime('%Y%m%d'), 'outcome session differs')
        model.check(daily['columns'] == prices.COLUMNS and type(daily['cohort_denominator']) is int
                    and len(daily['rows']) == daily['cohort_denominator'], 'outcome price dimensions')
        for values in daily['rows']:
            row = dict(zip(daily['columns'], values, strict=True))
            symbol = row['symbol']
            model.check(isinstance(symbol, str) and prices.CODE.fullmatch(symbol)
                        and symbol not in close_rows, 'outcome duplicate or invalid price identity')
            close_rows[symbol] = row['raw_close']
    rows, groups = [], {key: [] for key in GROUPS}
    with localcontext() as context:
        context.prec = 40
        for row in source_rows:
            close, change = None, None
            state = 'SAME_SESSION_CLOSE_NOT_RETAINED' if daily is None else 'CLOSE_IDENTITY_NOT_RETURNED'
            symbol = row['symbol']
            if symbol is not None and symbol in close_rows:
                try:
                    close = probe.text(prices.number(close_rows[symbol]))
                    state = 'PROFILE_AUCTION_PRICE_UNAVAILABLE'
                except ERRORS:
                    state = 'CLOSE_VALUE_UNAVAILABLE_OR_CONFLICT'
            if close is not None and row['auction_price'] is not None:
                try:
                    change = format(prices.number(close) / prices.number(row['auction_price']) - 1, '.12f')
                    state = 'SAME_SESSION_COMPARABLE'
                except ERRORS:
                    state = 'AUCTION_PRICE_INVALID'
            result = [*deepcopy([row[key] for key in probe.ROW_COLUMNS]), close, change, state]
            rows.append(result)
            groups[_group(row)].append(result)
        stats = {}
        for key, values in groups.items():
            changes = [Decimal(row[-2]) for row in values if row[-2] is not None]
            stats[key] = {'denominator': len(values), 'comparable': len(changes),
                'above_auction': sum(Decimal(r[-3]) > Decimal(r[probe.ROW_COLUMNS.index('auction_price')]) for r in values if r[-2] is not None),
                'below_auction': sum(Decimal(r[-3]) < Decimal(r[probe.ROW_COLUMNS.index('auction_price')]) for r in values if r[-2] is not None),
                'equal_to_auction': sum(Decimal(r[-3]) == Decimal(r[probe.ROW_COLUMNS.index('auction_price')]) for r in values if r[-2] is not None),
                'median_change': format(median(changes), '.12f') if changes else None}
    model.check(stats['MATCHED']['denominator'] == auction['matched'], 'outcome matched denominator differs')
    model.check(sum(stats[key]['denominator'] for key in ('MATCHED', 'NOT_MATCHED', 'AUCTION_UNRESOLVED'))
                == auction['static_eligible'], 'outcome static denominator differs')
    return {'version': VERSION, 'market_session': target.isoformat(), 'profile': auction['profile'],
        'source': auction['source'], 'auction_status': auction['status'], 'auction_timeliness': auction['timeliness'],
        'auction_observed_at': auction['observed_at'], 'auction_received_through': auction['received_through'],
        'close_observed_at': daily['observed_at'] if daily else None,
        'close_received_through': daily['received_through'] if daily else None,
        'status': 'SAVED_SAME_SESSION_OUTCOMES' if daily else 'SAME_SESSION_CLOSE_NOT_RETAINED',
        'cohort_denominator': len(rows), 'close_available': sum(r[-3] is not None for r in rows),
        'comparable': sum(r[-2] is not None for r in rows), 'groups': stats,
        'columns': list(COLUMNS), 'rows': rows, 'formula': 'same_session_close / auction_price - 1',
        'price_basis': 'SAME_SECURITY_SAME_SESSION_RAW_PRICE_RATIO_NOT_TOTAL_OR_STRATEGY_RETURN',
        'fraction_rounding_decimal_places': 12,
        'auction_coverage_gaps': auction.get('coverage_gaps'),
        'daily_source_row_coverage': deepcopy(daily.get('source_row_coverage', {})) if daily else None,
        'not_established': ['0940_SNAPSHOT', 'INTRADAY_PATH', 'NEXT_SESSION_OUTCOME', 'EXECUTION_OR_STRATEGY_EFFECT'],
        'meaning': 'SAVED_OBSERVATION_FOLLOW_THROUGH_NOT_PORTFOLIO_BACKTEST_OR_CAUSAL_PROOF',
        'new_source_requests': 0, 'odds_recomputed': False, **model.AUTHORITY}


def render(report: dict) -> str:
    def pct(value):
        return '未可比' if value is None else f'{Decimal(value) * 100:+.2f}%'
    lines = ['\n\n## D：竞价到同日收盘（已保存结果对照）\n',
        f"市场日：{report['market_session']}；原竞价时点：{report['auction_timeliness']}。",
        f"原池{report['cohort_denominator']}名全部保留；同日收盘可读{report['close_available']}名，"
        f"竞价至收盘可比{report['comparable']}名。",
        '| 原筛选分组 | 分母 | 可比 | 高于／低于／等于竞价价 | 中位变化 |',
        '|---|---:|---:|---:|---:|']
    for key, title in GROUPS.items():
        group = report['groups'][key]
        lines.append(f"| {title} | {group['denominator']} | {group['comparable']} | "
                     f"{group['above_auction']}／{group['below_auction']}／{group['equal_to_auction']} | "
                     f"{pct(group['median_change'])} |")
    lines += ['未匹配组不是推荐组合；零匹配不记为零收益。历史补读不是盘前发现，价格比值不证明策略有效或可按竞价成交。',
        '这里只比较同一交易日两端；09:40、日内路径和T+1未由本表建立。',
        f'[完整原名单、逐项收盘／缺口与两份来源时钟]({PATH})。\n']
    return '\n'.join(lines)


def _read(collector, description, cutoff):
    reference = description['file']
    model.check(description['publication_verification'] in (
        'REBUILT_FROM_RETAINED_RESPONSE_BYTES', 'REBUILT_FROM_EXACT_RETAINED_RESPONSE_BYTES'),
        'outcome requires the existing verified reader')
    model.check(reference['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT', 'outcome read ref')
    raw = collector.files[model.safe_path(reference['read_path'])]
    model.check(len(raw) == reference['bytes'] and model.sha256(raw) == reference['sha256']
                and model.blob_sha(raw) == reference['git_blob'], 'outcome retained bytes differ')
    report = prices.loads(raw)
    model.check(report['provenance'] == 'LIVE_TUSHARE_RELAY' and report['source'] == prices.SOURCE
                and report['market_session'] == description['market_session'], 'outcome retained source differs')
    model.check(model.clock(report['observed_at']) <= model.clock(report['received_through']) <= model.clock(cutoff),
                'outcome source clock')
    return report


def read_saved(collector, baseline, daily, auction, *, retained_limit):
    """Use already verified same-reading files only; never request another source."""
    result = {'status': 'AUCTION_FOLLOW_THROUGH_NOT_AVAILABLE', 'summary': '', 'new_source_requests': 0}
    if 'file' not in auction:
        return result
    prior = collector.files.get(PATH)
    try:
        cutoff = baseline['checks']['finished_at']
        auction_report = _read(collector, auction, cutoff)
        # Selection is about a dated close, NOT a qualified 5/20/60-day window.
        # A damaged selected input fails visibly; it cannot trigger older search.
        selected = next((candidate for candidate in (daily, daily.get('last_qualified_result') or {})
            if 'file' in candidate and candidate.get('market_session') == auction_report['market_session']
            and type(candidate.get('cohort_denominator')) is int and candidate['cohort_denominator'] > 0), None)
        close_report = _read(collector, selected, cutoff) if selected is not None else None
        report = project(auction_report, close_report)
        report.update(code_commit=collector.code_commit, checked_at=cutoff,
            auction_file=deepcopy(auction['file']), auction_archive=deepcopy(auction['source_archive']),
            close_file=deepcopy(selected['file']) if selected else None,
            close_archive=deepcopy(selected['source_archive']) if selected else None,
            latest_daily_attempt_status=daily['status'], using_prior_daily=selected is not None and selected is not daily)
        output, summary = prices.dumps(report), render(report)
        model.check(len(output) <= probe.MAX_REPORT, 'outcome detail byte bound')
        total = sum(len(v) for k, v in collector.files.items() if k != PATH)
        model.check(total + len(output) + 2*len(summary.encode()) + 24*1024 <= retained_limit, 'outcome total bound')
        model.check(collector.api.calls + len(set(collector.files) | {PATH, 'current-state.json', 'README.md'}) + 12
                    <= collector.api.max_calls, 'outcome publication reserve')
        result.update(status=report['status'], file=collector.retain(PATH, output), summary=summary,
            market_session=report['market_session'], cohort_denominator=report['cohort_denominator'],
            comparable=report['comparable'], groups=report['groups'])
    except ERRORS as exc:
        if prior is None:
            collector.files.pop(PATH, None)
        else:
            collector.files[PATH] = prior
        result.update(status='AUCTION_FOLLOW_THROUGH_READING_GAP', error_type=type(exc).__name__,
                      summary='\n竞价后续对照未能恢复；原竞价、日常价格与失败记录保持，未将空白当作零收益。\n')
    return result
