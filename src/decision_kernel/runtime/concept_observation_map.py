"""Source-bound concept coverage/navigation; no new acquisition or trend gate.

The caller must first replay the original capture. This projection does not
qualify its own source merely by hashing it. No historical source is rewritten.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal, Context, localcontext
from html import escape

from decision_kernel.identity import canonical_hash, canonical_json
from . import concept_radar as source

VERSION = 'concept-observation-map-v1'
POLICY = {
    'grouping': 'EXACT_OBSERVED_NONEMPTY_MEMBER_SET_INCLUSION_ONLY',
    'partial_overlap': 'DO_NOT_COLLAPSE_OR_TAKE_TRANSITIVE_CLOSURE',
    'unexamined_order': 'EXACT_CODE_NOT_DAILY_RETURN_OR_RESEARCH_PRIORITY',
    'page_size': source.MAX_DETAILS,
    'pages': 'PLANNING_ONLY_NOT_ACCEPTED_BY_CURRENT_SOURCE_WORKFLOW',
    'continuity': 'KEEP_ALL_ACQUIRED_HISTORIES_REGARDLESS_OF_DAILY_RETURN',
}
AUTHORITY = {**source.AUTHORITY, 'new_market_requests': 0, 'model_calls': 0,
             'automatic_dispatch': False, 'research_priority_established': False}


def build(report):
    """Compose one verified source, not a cross-date universe or an economic map."""
    source.render(report)  # Original identity/policy/authority guard; not raw replay.
    p = report['projection']
    rows = p['concepts']
    source.require(0 < len(rows) <= source.MAX_CATALOG and len(rows) == p['catalog_count']
                   == p['snapshot_count'], 'MAP_CATALOG_SCOPE_DIFFERS')
    codes = [r['thscode'] for r in rows]
    source.require(len(set(codes)) == len(codes), 'MAP_DUPLICATE_CONCEPT')
    by_code = {r['thscode']: r for r in rows}
    details = {d['thscode']: d for d in p['details']}
    source.require(len(details) == len(p['details']) <= source.MAX_DETAILS
                   and set(details) == set(p['detail_selected_codes']) <= set(codes),
                   'MAP_DETAIL_SCOPE_DIFFERS')
    memberships = {}
    for code, d in details.items():
        members = d['current_membership']
        if members is None:
            source.require(d['membership_status'] != 'CURRENT_MEMBERS_CHECKED_NOT_ECONOMIC_EXPOSURE',
                           'MAP_MISSING_MEMBERSHIP')
            continue
        values = [m['thscode'] for m in members['members']]
        source.require(values and len(values) == len(set(values)) and members['sector_thscode'] == code
                       and d['membership_status'] == 'CURRENT_MEMBERS_CHECKED_NOT_ECONOMIC_EXPOSURE',
                       'MAP_MEMBERSHIP_SCOPE_DIFFERS')
        memberships[code] = set(values)
    # Representatives are maximal observed member sets. Equal sets use exact-code
    # tie-break. An index contained by two maxima is shown under both, not forced
    # into a claimed partition or transitive economic cluster.
    roots = sorted(c for c, values in memberships.items() if not any(
        values < other or (values == other and c > other_code)
        for other_code, other in memberships.items() if c != other_code))
    groups = []
    for root in roots:
        contained = sorted(c for c, values in memberships.items() if values <= memberships[root])
        groups.append({'representative': root, 'member_count': len(memberships[root]),
            'detail_codes': contained,
            'member_codes': sorted(memberships[root]),
            'meaning': 'NAVIGATION_CONTAINMENT_NOT_ONE_ECONOMIC_THEME_OR_INDEPENDENT_SIGNAL',
            'relations': [{'thscode': c,
                'relation': ('REPRESENTATIVE' if c == root else
                             'EQUAL_OBSERVED_SET' if memberships[c] == memberships[root] else 'STRICT_SUBSET'),
                'member_count': len(memberships[c]),
                'additional_members_beyond_representative': 0,
                'membership_hash': details[c]['current_membership']['constituent_set_hash'],
                'membership_captured_at': details[c]['current_membership']['captured_at'],
                'membership_observed_at': p['requests'][details[c]['membership_request_index']]['received_at'],
                'other_maximal_containers': [r for r in roots if r != root and memberships[c] <= memberships[r]]}
                for c in contained]})
    unresolved = sorted(set(details) - set(memberships))
    known_histories = sorted(c for c, d in details.items() if d['history_status'] == 'EXACT_WINDOW_CHECKED')
    for c in known_histories:
        source.require(details[c]['path'] is not None, 'MAP_HISTORY_PATH_MISSING')
    unexamined = sorted(set(codes) - set(details))
    incomplete = sorted(c for c, d in details.items() if c not in known_histories or c not in memberships)
    universe = []
    for c in sorted(codes):
        r, d = by_code[c], details.get(c)
        source.require(r['detail_acquisition'] == ('SELECTED' if d is not None else 'DEFERRED_NOT_ACQUIRED'),
                       'MAP_DETAIL_DISPOSITION_DIFFERS')
        universe.append({'thscode': c, 'name': r['name'], 'daily_return': r['daily_return'],
            'daily_benchmark_excess': r['daily_benchmark_excess'],
            'history_status': d['history_status'] if d else 'NOT_ACQUIRED',
            'membership_status': d['membership_status'] if d else 'NOT_ACQUIRED',
            'path': deepcopy(d['path']) if d else None,
            'gaps': deepcopy(d['gaps']) if d else [],
            'detail_disposition': 'NOT_ACQUIRED' if d is None else 'INCOMPLETE' if c in incomplete else 'ACQUIRED',
            'member_count': len(memberships[c]) if c in memberships else None})
    projection = {'version': VERSION, 'policy': deepcopy(POLICY),
        'source_projection_hash': report['projection_hash'],
        'source_catalog_hash': p['concept_catalog_hash'], 'market_session': p['market_session'],
        'source_started_at': p['started_at'], 'source_observed_at': p['as_of'],
        'source_provenance': p['provenance'],
        'qualification': 'REQUIRES_CALLER_ORIGINAL_CAPTURE_REPLAY_NOT_SELF_CERTIFIED',
        'groups': groups, 'unresolved_membership_details': unresolved,
        'known_history_codes': known_histories, 'incomplete_detail_codes': incomplete,
        'unexamined_codes': unexamined, 'universe': universe,
        'coverage': {'catalog_count': len(rows), 'snapshot_count': len(rows),
            'history_count': len(known_histories), 'membership_count': len(memberships),
            'maximal_observed_member_sets': len(roots),
            'contained_nonrepresentative_details': len(memberships) - len(roots),
            'unexamined_details': len(unexamined), 'incomplete_details': len(incomplete),
            'planning_pages': (len(unexamined) + source.MAX_DETAILS - 1) // source.MAX_DETAILS,
            'actual_new_pages_executed': 0, 'full_multiday_coverage': len(known_histories) == len(rows),
            'member_breadth_acquired': False, 'economic_themes_established': False},
        **AUTHORITY}
    return {'projection': projection, 'projection_hash': canonical_hash(projection)}


def verify(value, original_report):
    source.require(value == build(original_report), 'MAP_REBUILD_DIFFERS')
    return {'status': 'CONCEPT_MAP_REBUILT_FROM_SUPPLIED_SOURCE',
            'projection_hash': value['projection_hash'], 'new_market_requests': 0}


def page(value, *, expected_source_hash, offset):
    """Bounded inspection plan only. No producer accepts this as run permission."""
    _validate(value)
    p = value['projection']
    codes = p['unexamined_codes']
    source.require(expected_source_hash == p['source_projection_hash'], 'MAP_SOURCE_SELECTOR_DIFFERS')
    source.require(type(offset) is int and 0 <= offset <= len(codes)
                   and (offset == len(codes) or offset % source.MAX_DETAILS == 0), 'MAP_PAGE_OFFSET_REJECTED')
    return _page(tuple(codes), expected_source_hash, value['projection_hash'], offset)


def pages(value, *, expected_source_hash):
    """Inspect a full finite plan after one identity check, not repeated hashing."""
    _validate(value)
    p = value['projection']
    source.require(expected_source_hash == p['source_projection_hash'], 'MAP_SOURCE_SELECTOR_DIFFERS')
    codes, digest = tuple(p['unexamined_codes']), value['projection_hash']
    for offset in range(0, len(codes), source.MAX_DETAILS):
        yield _page(codes, expected_source_hash, digest, offset)


def _page(codes, expected_source_hash, digest, offset):
    selected = list(codes[offset:offset + source.MAX_DETAILS])
    return {'version': VERSION, 'source_projection_hash': expected_source_hash,
            'map_hash': digest, 'offset': offset, 'codes': selected,
            'next_offset': offset + len(selected) if offset + len(selected) < len(codes) else None,
            'remaining_after_page': len(codes) - offset - len(selected),
            'execution': 'NOT_EXECUTED', 'workflow_compatible': False,
            'meaning': POLICY['pages'], **AUTHORITY}


def _validate(value):
    p = value['projection']
    source.require(value['projection_hash'] == canonical_hash(p) and p['version'] == VERSION
                   and p['policy'] == POLICY and all(p.get(k) == v for k, v in AUTHORITY.items()),
                   'MAP_IDENTITY_DIFFERS')


def render(value):
    _validate(value)
    with localcontext(Context(prec=28)):
        return _render(value)


def _render(value):
    p = value['projection']; coverage = p['coverage']
    e = lambda x: escape(str(x), quote=True)
    pct = lambda x: f'{Decimal(x) * 100:+.2f}%'
    points = lambda x: f'{Decimal(x) * 100:+.2f}'
    observed_at = datetime.fromisoformat(p['source_observed_at'].replace('Z', '+00:00')).astimezone(source.SHANGHAI_TZ).strftime('%Y-%m-%d %H:%M:%S')
    by_code = {r['thscode']: r for r in p['universe']}
    out = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<title>概念观察地图 · 趋势、重叠与未覆盖</title>',
        '<style>body{font:16px/1.7 system-ui;max-width:1100px;margin:auto;padding:24px}h1,h2{line-height:1.3}section{margin:28px 0}table{border-collapse:collapse;width:100%;min-width:760px}th,td{white-space:nowrap}th,td{text-align:left;padding:10px;border-bottom:1px solid #ddd}details{margin:12px 0}summary{cursor:pointer;font-weight:600}p,li{overflow-wrap:anywhere}.scroll{overflow:auto}.notice{padding:16px;background:#f2f5f7;border-left:4px solid #64748b}.muted{color:#475569}</style>',
        '<h1>概念观察地图</h1>',
        f'<p>保存市场日 {e(p["market_session"])} · 实际取得截止 {e(observed_at)}（北京时间）</p>',
        f'<p><strong>{coverage["snapshot_count"]} 个当日快照 · {coverage["history_count"]} 个已知多日路径 · {coverage["unexamined_details"]} 个详情未取得</strong></p>',
        '<p class="notice">这是保存结果的阅读整理，不是今日重新扫描。成员集合包含关系只用于减少重复阅读，不代表同一产业主题、业务受益或独立确认。没有新执行 Stock、Pre 或 Quick。</p>',
        '<section><h2>先看重叠，再看各自趋势</h2>',
        f'<p>可验证成员的 {coverage["membership_count"]} 个详情，对应 {coverage["maximal_observed_member_sets"]} 个最大观测成员集合。'
        '部分重叠不会合并；成员缺失不会当成空集。各请求并非同时取得。</p>']
    for group in p['groups']:
        root = by_code[group['representative']]
        out.append(f'<details open><summary>{e(root["name"])} · {e(root["thscode"])} · {group["member_count"]} 家，关联 {len(group["detail_codes"])} 个指数详情</summary>')
        out.append('<div class="scroll"><table><tr><th>指数</th><th>集合关系</th><th>成员</th><th>5日超额（百分点）</th><th>20日超额（百分点）</th><th>60日超额（百分点）</th></tr>')
        for relation in group['relations']:
            row = by_code[relation['thscode']]
            horizons = {h['sessions']: h['excess_return'] for h in row['path']['horizons']} if row['path'] else {}
            label = {'REPRESENTATIVE': '最大观测集合', 'EQUAL_OBSERVED_SET': '成员相同，指数不等同', 'STRICT_SUBSET': '成员被包含，指标保留'}[relation['relation']]
            cells = [row['name'] + ' ' + row['thscode'], label, str(relation['member_count'])]
            cells.extend(points(horizons[n]) if n in horizons else '未取得' for n in (5, 20, 60))
            out.append('<tr>' + ''.join('<td>'+e(c)+'</td>' for c in cells) + '</tr>')
        out.append('</table></div><p class="muted">超额相对沪深300，单位为百分点；当日涨跌另用百分比。手机可在表格内横向滚动。被包含指数没有增加集合外公司，但保留自身价格路径；不能相加成更多确认。</p></details>')
    if p['unresolved_membership_details']:
        out.append('<p>成员关系无法判断：' + e('、'.join(p['unresolved_membership_details'])) + '。各自历史是否可用单独保留。</p>')
    out.append('</section><section><h2>已知多日路径，不因当日平静而隐藏</h2>')
    for code in p['known_history_codes']:
        row = by_code[code]; path = row['path']
        continuity_note = ('记录从观察窗口左端开始，实际连续时长可能更长，不能确定经济趋势起点'
            if path['positive_20d_excess_persistence_left_censored'] else '连续段在观察窗口内可定位，不等于经济趋势起点')
        out.append(f'<p><strong>{e(row["name"])} {e(code)}</strong>：当日 {pct(row["daily_return"])}；'
                   f'20日正超额连续段 {path["positive_20d_excess_persistence_sessions"]} 个交易日；'
                   f'{e(continuity_note)}。</p>')
    if not p['known_history_codes']:
        out.append('<p>本来源没有合格多日路径，不能写成所有方向均无趋势。</p>')
    out += ['</section><section><h2>完整观察范围与补查缺口</h2>',
        f'<p>尚未取详情 {coverage["unexamined_details"]} 个，已尝试但详情不完整 {coverage["incomplete_details"]} 个。'
        f'未取得范围按精确代码排列，可形成 {coverage["planning_pages"]} 个最多三项的检查计划；'
        '<strong>这些计划尚未接到采集执行器，不是已执行批次，不需要你逐页操作。</strong></p>',
        '<p>下表不以当日涨幅过滤或排序。没有历史时，不能推断强弱、持续性或业务受益。数据失败与尚未取得分开。</p>',
        '<details><summary>展开全部概念（浏览器页内查找可搜名称或代码）</summary><div class="scroll"><table><tr><th>概念／代码</th><th>当日</th><th>多日历史</th><th>成员</th><th>详情状态</th></tr>']
    for row in p['universe']:
        history = '窗口已核对' if row['history_status'] == 'EXACT_WINDOW_CHECKED' else '未取得' if row['history_status'] == 'NOT_ACQUIRED' else '数据不可用'
        disposition = {'NOT_ACQUIRED': '尚未取得', 'INCOMPLETE': '详情不完整', 'ACQUIRED': '已取得'}.get(row['detail_disposition'], row['detail_disposition'])
        cells = [row['name']+' '+row['thscode'], pct(row['daily_return']), history,
                 row['member_count'] if row['member_count'] is not None else '未取得', disposition]
        out.append('<tr>'+''.join('<td>'+e(c)+'</td>' for c in cells)+'</tr>')
    out += ['</table></div></details></section>',
        '<p><a href="concept-observation-map.json">结构化观察地图与完整补查范围</a> · <a href="index.html">公司来路与研究上下文</a></p>',
        '<footer>上涨或下跌原因尚未研究。本层没有执行研究或产生投资决定。</footer></html>']
    return '\n'.join(out)+'\n'
