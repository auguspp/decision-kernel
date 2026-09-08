"""Read-only presentation of the EXISTING qualified Sector daily result.

No detector, stock selector, company mapper, network, state writer or Human wake.
The production caller validates SectorRadarDailyResult before serializing it here.
A saved-result caller must bind the original artifact/version separately: rendering
is not a new market qualification or an original-code replay certificate.
"""
from __future__ import annotations

from decimal import Context, Decimal, localcontext
from html import escape

CONTRACT = 'qualified-market-change-must-remain-human-discoverable'
_EVENT_LABELS = {
    'ACCELERATING_ENTRY': '新进入加速条件',
    'PERSISTENT_TOP_DECILE_ENTRY': '新进入持续强势条件',
    'ACCELERATING_AND_PERSISTENT_ENTRY': '新进入加速与持续强势条件',
}


def _text(value: object) -> str:
    """Treat source names as text, including inside GitHub details/Markdown."""
    text = escape(str(value), quote=True).replace('\r', ' ').replace('\n', ' ')
    for char in ('\\', '`', '[', ']', '*', '_', '|'):
        text = text.replace(char, '&#' + str(ord(char)) + ';')
    return text


def _number(value: object, *, percent: bool = False) -> str:
    if value is None:
        return '不可用 / NOT_ESTABLISHED'
    with localcontext(Context(prec=64)):
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError('non-finite discovery display value')
        return f'{number * 100:+.2f}%' if percent else f'{number:.2f}'


def _identity(row: dict) -> str:
    return f"{_text(row['name'])} {_text(row['thscode'])}"


def _candidate_breadths(group: dict) -> list[tuple[dict, dict]]:
    return [(group['primary_candidate'], group['primary_breadth']), *zip(
        group['granular_drivers'], group['granular_driver_breadth'], strict=True)]


def _validate_projection(result: dict) -> None:
    """Check lossless partition/binding, not re-detect or relax any market gate."""
    composition = result['composition']
    groups = composition['all_groups']
    surfaced, omitted = composition['surfaced_groups'], composition['omitted_groups']
    if (len(surfaced) > 3 or groups != surfaced + omitted
            or composition['truncated_group_count'] != len(omitted)
            or len({g['group_key'] for g in groups}) != len(groups)):
        raise ValueError('qualified discovery partition must preserve all groups and 0-3 summary')
    if composition['as_of_session'] != result['market_session']:
        raise ValueError('discovery composition session differs')
    entries = result['broad_entries']['candidates'] + result['granular_entries']['candidates']
    expected = {c['thscode']: c for c in entries}
    actual = {c['thscode']: c for c in composition['all_candidates']}
    if len(expected) != len(entries) or actual != expected or len(actual) != len(composition['all_candidates']):
        raise ValueError('discovery must use the existing detector entries')
    seen = []
    for group in groups:
        pairs = _candidate_breadths(group)
        local = {c['thscode']: c for c in group['all_candidates']}
        if (len(local) != len(group['all_candidates'])
                or local != {c['thscode']: c for c, _ in pairs}):
            raise ValueError('discovery must preserve grouped primary and driver candidates')
        for candidate, breadth in pairs:
            code = candidate['thscode']
            if (candidate != expected.get(code)
                    or candidate['as_of_session'] != result['market_session']
                    or breadth['market_session'] != result['market_session']
                    or breadth['sector_thscode'] != code
                    or breadth not in result['breadth_observations']):
                raise ValueError('discovery candidate/breadth binding differs')
            seen.append(code)
        for record in (group, *(b for _, b in pairs)):
            if (record['human_attention_authority'] != 'NONE' or record['investment_authority'] != 'NONE'
                    or record.get('research_authority', 'NONE') != 'NONE'):
                raise ValueError('discovery presentation has no authority')
    if len(seen) != len(set(seen)) or set(seen) != set(expected):
        raise ValueError('qualified detector entries cannot disappear or be added')
    for record in (result, composition, result['broad_entries'], result['granular_entries']):
        if (record['human_attention_authority'] != 'NONE' or record['investment_authority'] != 'NONE'
                    or record.get('research_authority', 'NONE') != 'NONE'):
            raise ValueError('discovery presentation has no authority')
    if result['broad_entries']['previous_session'] != result['granular_entries']['previous_session']:
        raise ValueError('discovery comparison sessions differ')


def _leaders(breadth: dict) -> str:
    rows = breadth['leaders']
    return '；'.join(
        f"{_identity(row)} {_number(row['daily_return'], percent=True)}" for row in rows
    ) if rows else '未提供 / UNKNOWN'


def _where(group: dict) -> str:
    primary = _identity(group['primary_candidate'])
    if group['parent_context_thscode'] is None:
        return primary
    parent = f"{_text(group['parent_context_name'])} {_text(group['parent_context_thscode'])}"
    return primary if group['parent_context_thscode'] == group['primary_candidate']['thscode'] else parent + ' / ' + primary


def _brief(group: dict) -> str:
    c, b = group['primary_candidate'], group['primary_breadth']
    event = _EVENT_LABELS.get(c['event_type'], c['event_type'])
    leader = _identity(b['leaders'][0]) if b['leaders'] else 'UNKNOWN'
    drivers = '；组内另含：' + '、'.join(_identity(d) for d in group['granular_drivers']) if group['granular_drivers'] else ''
    return (f"{_where(group)} — {_text(event)}；当日指数 {_number(b['index_daily_return'], percent=True)}；"
            f"上涨 {b['advancers']}/{b['priced_member_count']}；当日 leader：{leader}{drivers}")


def _details(group: dict, result: dict) -> list[str]:
    previous = result['broad_entries']['previous_session']
    lines = [
        f"**WHEN**：比较完成交易日 {_text(previous)} → {_text(result['market_session'])}，"
        '本次首次进入相应门槛；不是断言行情从这一天才开始。',
        '',
    ]
    for c, b in _candidate_breadths(group):
        lines += [
            f"**WHAT / WHERE**：{_identity(c)}；{_text(_EVENT_LABELS.get(c['event_type'], c['event_type']))} "
            f"（{_text(c['event_type'])}）。",
            '',
            f"**MAGNITUDE**：当日指数 {_number(b['index_daily_return'], percent=True)}；"
            f"相对基准 {_text(result['benchmark_thscode'])} 的 5/20 日超额分别 "
            f"{_number(c['horizon_5_excess_return'], percent=True)} / {_number(c['horizon_20_excess_return'], percent=True)}；"
            f"20 日排名较 5 个交易日前变化（正数为改善） {_text(c['rank_change_5_sessions_20d'])} 位，"
            f"20 日超额的 5 日变化 {_number(c['excess_acceleration_5_sessions_20d'], percent=True)}；"
            f"成交额脉冲 {_number(c['turnover_pulse_5_vs_prior_20'])}"
            + ('x。' if c['turnover_pulse_5_vs_prior_20'] is not None else '。'),
            '',
            f"**BREADTH**：上涨 {b['advancers']}/{b['priced_member_count']}，"
            f"下跌 {b['decliners']}，平盘 {b['unchanged']}；"
            f"已定价 {b['priced_member_count']}/{b['member_count']}，"
            f"缺失或未定价 {b['missing_or_unpriced_member_count']}；"
            f"当日等权中位数 {_number(b['equal_weight_median_daily_return'], percent=True)}。"
            '仅为当期成员代理，不是历史广度或指数贡献。',
            '',
            '**LEADERS**（原 breadth 留存的当日表现突出成员，非多日强势认证或推荐）：' + _leaders(b) + '。',
            '',
            f"**KNOWN**：上述门槛变化及当期 breadth 已在本结果中记录；"
            f"20 日正超额连续 {_text(c['positive_20d_excess_persistence_sessions'])} 个交易日，"
            f"前四分位连续 {_text(c['top_quartile_20d_persistence_sessions'])} 个交易日；"
            f"成员采集 {_text(b['membership_captured_at'])}。",
            '',
        ]
    lines += [
        '**UNKNOWN**：WHY = UNKNOWN；BUSINESS LINK = NOT ESTABLISHED；'
        '公司业务依据在本变化视图中为 UNREVIEWED（未接入，不断言仓库其他地方一定没有资料）；'
        '原因、持续性、基本面受益及多日个股路径未由这份 breadth 建立。',
        '',
        '**NEXT QUESTION**：先核对突出公司的身份与业务，再查观察时点已公开的公告、政策、商品或行业共同变化；'
        '哪些证据能解释、哪些反例会否定这个解释？这是可选的发现问题，不自动发起 Research。',
        '',
        f"分组依据：{_text(group['grouping_reason'])}。父行业可仅作上下文，不因此升级为合格候选。",
        '',
        'RESEARCH CONCLUSION = NONE；BELIEF = NONE；Human Attention / Research / Investment authority = NONE。',
        '',
    ]
    return lines


def render_sector_radar_discovery(result: dict) -> str:
    """Format all qualified groups; only the existing 0-3 enter the homepage summary."""
    _validate_projection(result)
    c = result['composition']
    shown, rest = c['surfaced_groups'], c['omitted_groups']
    lines = [
        f"## Sector Discovery Radar — {_text(result['market_session'])}", '',
        '**SHADOW OBSERVATION ONLY**', '',
        '`NOT RESEARCH` · `NOT A RECOMMENDATION`', '',
        '`HUMAN ATTENTION AUTHORITY = NONE` · `RESEARCH AUTHORITY = NONE` · `INVESTMENT AUTHORITY = NONE`', '',
        f"**本次识别 {len(c['all_groups'])} 个合格变化组；首页摘要 {len(shown)} 个；其他变化 {len(rest)} 个。**", '',
        f"New false→true entries: **{len(c['all_candidates'])}** · shadow groups shown: **{len(shown)}**。"
        '候选事件数与分组数不同，不把同组驱动重复算成多个首页对象。', '',
        '**0–3 是 Attention Budget，不是 Reality Budget。Radar may detect before it understands.** '
        'Price can create a Question. Price cannot create a Belief.', '',
        f"[查看其他 {len(rest)} 个变化](#其他变化)。所有变化均可阅读；不要求额外 Human wake。"
        '这是标明交易日的保存结果，不是实时行情，也不证明今天没有更新。', '',
        '### 首页摘要', '',
    ]
    if not c['all_groups']:
        lines += ['Nothing new qualified for the separate Sector Radar shadow surface.', '',
                  '本次没有新进入原 detector 门槛的变化；不把所有上涨行业补成候选。', '']
    elif not shown:
        lines += ['本次首页预算为 0；已识别变化仍全部列在下方，不是无变化。', '']
    for i, group in enumerate(shown, 1):
        lines += [f"### {i}. {_where(group)}", '', _brief(group), '',
                  '<details>', '<summary>查看证据、未知项与下一问题</summary>', '']
        lines += _details(group, result)
        lines += ['</details>', '']
    lines += ['### 其他变化', '',
              '以下各组只从首页摘要省略，并未删除。每行给出变化、位置、幅度、广度和 leader；展开可看全部驱动及未知项。', '']
    if rest:
        lines += [f'{len(rest)} additional complete group(s) are listed below for reading; '
                  'omitted only from the homepage summary.', '']
    else:
        lines += ['没有被首页摘要省略的合格变化组。', '']
    for i, group in enumerate(rest, len(shown) + 1):
        lines += ['<details>', f'<summary>{i}. {_brief(group)}</summary>', '']
        lines += _details(group, result)
        lines += ['</details>', '']
    lines += [
        f"Market-state hash: `{_text(result['output_market_state_hash'])}`", '',
        f"Event-ledger hash: `{_text(result['event_ledger_update']['event_ledger_hash'])}`", '',
        f"Full result hash: `{_text(result['result_hash'])}`", '',
        f"Presentation contract: `{CONTRACT}`。本页读取既有 result，不重新判定市场资格；"
        '数值仅显示四舍五入，未修改原始值、门槛或次序。', '',
        'Sector price strength and current breadth are discovery facts only. '
        'They do not establish company economics, valuation, Odds, a Recommendation, or an Action.', '',
    ]
    return '\n'.join(lines)
