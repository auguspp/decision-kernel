"""Stock-first shadow reading; not a third canonical attention lane.

Existing industry gates select directions. Existing curated company evidence
limits the reviewed issuer scope; membership alone is never business evidence.
Existing HiThink adapters qualify individual raw histories, not the unqualified
all-stock dump. No weights, recommendation, event ledger, or Research routing.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from decimal import Decimal, localcontext, Context
from html import escape
from pathlib import Path

from decision_kernel.adapters.hithink import (
    SHANGHAI_TZ, latest_completed_a_share_session, normalize_hithink_calendar,
    normalize_hithink_completed_price_history, to_hithink_thscode,
)
from decision_kernel.identity import canonical_hash, canonical_json
from . import economic_company_context as company
from . import hithink_index_http as indices
from . import hithink_sector_breadth_http as members
from . import theme_radar_probe as probe
from .hithink_http import HITHINK_CALENDAR_PATH
from .sector_radar import _return_over, _average
from .sector_radar_context import build_sector_radar_context
from .sector_radar_state import serialize_sector_radar_market_state

VERSION = 'stock-first-reviewed-scope-raw-path-v0'
SEMANTICS = 'BOUNDED_STOCK_READING_NOT_RECOMMENDATION_OR_CANONICAL_ATTENTION'
STOCK_HISTORY = '/api/a-share/prices/historical'
MAX_ISSUERS, MAX_MEMBERSHIPS, MAX_REQUESTS = 16, 6, 26
COMPANY_MANIFEST = 'radar_inputs/economic-company-links-livestock-v1.json'
POLICY = {
    'version': VERSION,
    'direction': 'EXISTING_CURRENT_SECTOR_GATE_NOT_NEW_EVENT_REQUIRED',
    'issuer_universe': 'ALL_REVIEWED_ISSUERS_IN_ACTIVE_LINKED_NODES_NOT_ALL_A_SHARES',
    'membership': 'EXACT_CURRENT_MEMBER_REQUIRED_NOT_HISTORICAL_EXPOSURE',
    'stock_gate': 'POSITIVE_5D_RAW_AND_5D_MARKET_EXCESS_AND_20D_MARKET_EXCESS_AND_ONE_20D_SECTOR_EXCESS',
    'sixty_day': 'CONTEXT_ONLY_NOT_A_GATE',
    'activity': 'POSITIVE_LATEST_VOLUME_AND_TURNOVER_NOT_EXECUTION_ELIGIBILITY',
    'name_guard': 'ST_DELISTING_AND_N_C_PREFIX_LABELS_ONLY_NOT_FULL_REGULATORY_STATUS',
    'presentation': 'NODE_ORDER_ROUND_ROBIN_THEN_20D_MARKET_EXCESS_5D_MARKET_EXCESS_CODE',
    'max_cards': 3, 'max_issuers': MAX_ISSUERS, 'max_memberships': MAX_MEMBERSHIPS,
    'no_composite_score': True,
}
LIMITS = {
    **probe.AUTHORITY, 'creates_canonical_wake': False, 'events_created': 0,
    'market_state_writes': 0, 'automatic_research_routing': False,
    'recommendation': None, 'independent_forecast_count': None,
    'business_benefit_established': False,
}


def _plain(value):
    return json.loads(canonical_json(value))


def _state_rows(state):
    return {r['thscode']: r for r in json.loads(serialize_sector_radar_market_state(state))['series']}


def _hash_ok(value, key):
    return value.get(key) == canonical_hash({k: v for k, v in value.items() if k != key})


def prepare_stock_reading(source_root: Path, state, ledger, association: dict, *,
                          observed_at: datetime, company_manifest: str = COMPANY_MANIFEST) -> dict:
    """Resolve all reviewed issuers before requesting prices; never pick a top three first."""
    probe._window(state, observed_at)
    linked = company.build_company_links(source_root, association, manifest_path=company_manifest)
    p = association['projection']
    if (p['market_state_hash'] != state.state_hash or p['event_ledger_hash'] != ledger.ledger_hash
            or probe._clock(p['as_of']) > observed_at):
        raise ValueError('stock reading association belongs to different or future inputs')
    context = build_sector_radar_context(market_state=state, event_ledger=ledger, generated_at=observed_at)
    all_rows = {r['observation']['thscode']: r for u in context['universes'] for r in u['rows']}
    panels = {row['node_id']: row for row in p['panels']}
    directions, issuers, order = {}, {}, []
    for node in linked['projection']['nodes']:
        panel = panels[node['node_id']]
        active = []
        for row in panel['markets']:
            code = row['identity']['thscode']
            if row['saved_market'] != all_rows.get(code):
                raise ValueError('embedded sector state does not reproduce from exact saved market')
            if row['saved_market']['currently_gate_active']:
                active.append(code)
        if not active or not node['companies']:
            continue
        order.append(node['node_id'])
        for code in active:
            directions[code] = all_rows[code]
        for c in node['companies']:
            code = to_hithink_thscode(ticker=c['ticker'], exchange=c['exchange'])
            if code not in issuers:
                issuers[code] = {'thscode': code, 'company_name': c['company_name'], 'origins': []}
            elif issuers[code]['company_name'] != c['company_name']:
                raise ValueError('one exact stock identity has conflicting company names')
            issuers[code]['origins'].append({
                'node_id': node['node_id'], 'node_label': panel['label'],
                'sector_codes': sorted(active), 'company': c,
                'node_relation_note': panel['relation_note'], 'review_question': panel['review_question'],
                'economic_coverage': node['economic_coverage'],
            })
    if len(issuers) > MAX_ISSUERS or len(directions) > MAX_MEMBERSHIPS:
        raise ValueError('stock reading request budget exceeded; no partial top-three enrichment')
    active_codes = {code for code, r in all_rows.items() if r['currently_gate_active']}
    body = {
        'version': VERSION, 'semantics': SEMANTICS, 'policy': POLICY,
        'observed_at': observed_at, 'market_session': state.sessions[-1],
        'market_state_hash': state.state_hash, 'event_ledger_hash': ledger.ledger_hash,
        'association_hash': association['projection_hash'], 'company_links_hash': linked['projection_hash'],
        'company_manifest': company_manifest,
        'directions': {k: directions[k] for k in sorted(directions)},
        'issuers': [issuers[k] for k in sorted(issuers)], 'node_order': order,
        'all_active_direction_count': len(active_codes),
        'active_directions_without_stock_business_scope': sorted(active_codes - set(directions)),
        'reviewed_company_coverage': 'CURATED_LINKS_ONLY_NOT_A_BLIND_ALL_STOCK_SCREEN',
        'maximum_request_count': 4 + len(directions) + len(issuers) if issuers else 0,
        'stock_gate_is_unvalidated_shadow_policy': True,
        **LIMITS,
    }
    body['plan_hash'] = canonical_hash(body)
    return _plain(body)


def _history_params(code, sessions):
    start = datetime.combine(sessions[-61], datetime.min.time(), tzinfo=SHANGHAI_TZ)
    end = datetime.combine(sessions[-1] + timedelta(days=1), datetime.min.time(), tzinfo=SHANGHAI_TZ)
    return {'thscode': code, 'interval': '1d', 'adjust': 'none',
            'start': str(int(start.timestamp() * 1000)), 'end': str(int(end.timestamp() * 1000))}


def _stock_path(state, code, response, *, at):
    qualified = normalize_hithink_completed_price_history(
        response, thscode=code, sessions=state.sessions, observed_at=at)
    expected = tuple(state.sessions[-61:])
    if (tuple(p.as_of.astimezone(SHANGHAI_TZ).date() for p in qualified.points) != expected
            or qualified.response_session != state.sessions[-1]
            or qualified.expected_latest_session != state.sessions[-1]):
        raise ValueError('stock must have every one of the exact 61 completed sessions; no drop or fill')
    by_day = {datetime.fromtimestamp(int(r['date_ms']) / 1000, tz=SHANGHAI_TZ).date(): r
              for r in response['data']['item']}
    closes = tuple(p.close for p in qualified.points)
    amounts = tuple(Decimal(str(by_day[d]['turnover'])) for d in expected)
    prior = _average(amounts[-25:-5])
    return {
        'last_close': closes[-1], 'previous_raw_close': closes[-2],
        'latest_volume': Decimal(str(by_day[expected[-1]]['volume'])),
        'latest_turnover': amounts[-1],
        'daily_raw_return': closes[-1] / closes[-2] - 1,
        'returns': {str(n): _return_over(closes, end_index=60, sessions=n) for n in (5, 20, 60)},
        'turnover_pulse_5_vs_prior_20': _average(amounts[-5:]) / prior if prior else None,
        'twenty_day_return_five_sessions_ago': _return_over(closes, end_index=55, sessions=20),
        'price_convention': 'RAW_UNADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN',
        'corporate_action_adjustment': 'NOT_PERFORMED',
        'tradability': 'NOT_CERTIFIED_BY_PRICE_AND_VOLUME',
        'history_session_count': 61,
    }


def _select(rows, node_order):
    """Visible lexicographic presentation only, not a weighted opportunity score."""
    eligible = [r for r in rows if r['eligible_for_shadow_reading']]
    ordered = sorted(eligible, key=lambda r: (
        -Decimal(r['market_comparison']['20']['excess_return']),
        -Decimal(r['market_comparison']['5']['excess_return']), r['thscode']))
    selected, seen = [], set()
    while len(selected) < 3:
        advanced = False
        for node in node_order:
            available = [r for r in ordered if r['thscode'] not in seen and node in r['eligible_nodes']]
            if available:
                selected.append(available[0]); seen.add(available[0]['thscode']); advanced = True
            if len(selected) == 3:
                break
        if not advanced:
            break
    return selected


def observe_stock_reading(plan: dict, state, *, request_json, observed_at: datetime,
                          cutoff_clock=None) -> dict:
    """Run an original-input-verified plan; all issuers precede compression.

    cutoff_clock is the last actual response receipt, supplied by capture/replay.
    Fixed offline callers use observed_at. No guessed future receipt is accepted.
    """
    with localcontext(Context(prec=28)):
        return _observe(plan, state, request_json=request_json, observed_at=observed_at,
                        cutoff_clock=cutoff_clock)


def _observe(plan, state, *, request_json, observed_at, cutoff_clock):
    if (plan['version'] != VERSION or plan['policy'] != POLICY or not _hash_ok(plan, 'plan_hash')
            or plan['market_state_hash'] != state.state_hash
            or any(plan[k] != v for k, v in LIMITS.items())
            or len(plan['issuers']) > MAX_ISSUERS or len(plan['directions']) > MAX_MEMBERSHIPS):
        raise ValueError('stock plan identity, policy or authority differs')
    last = observed_at
    def at():
        nonlocal last
        value = cutoff_clock() if cutoff_clock else observed_at
        probe._window(state, value)
        if not probe._clock(plan['observed_at']) <= last <= value <= probe._clock(plan['observed_at']) + timedelta(minutes=30):
            raise ValueError('stock observation is outside its declared plan lifetime or clock reversed')
        last = value
        return value
    at()
    rows, memberships = [], {}
    state_rows = _state_rows(state)
    def get(path, params):
        value = request_json(path, params)
        at()
        return value
    if plan['issuers']:
        calendar = normalize_hithink_calendar(get(HITHINK_CALENDAR_PATH, {}))
        if (latest_completed_a_share_session(calendar, observed_at=at()) != state.sessions[-1]
                or tuple(d for d in calendar if state.sessions[0] <= d <= state.sessions[-1]) != tuple(state.sessions)):
            raise ValueError('saved industry state is not the exact latest calendar window; run producer separately')
        catalog = indices.fetch_hithink_industry_catalog(api_key='INJECTED', request_json=get)
        if catalog.catalog_hash != state.catalog_hash:
            raise ValueError('industry catalog changed; no name or proxy substitution')
        raw_snapshot = indices.fetch_hithink_index_snapshot_batch(
            thscodes=tuple(sorted(state_rows)), api_key='INJECTED', request_json=get)
        benchmark_history = indices.fetch_hithink_completed_index_history(
            thscode=state.benchmark_thscode, observed_at=at(), api_key='INJECTED',
            request_json=get, trading_sessions=calendar)
        snapshot = indices.qualify_hithink_index_snapshot(raw_snapshot,
            benchmark_history=benchmark_history, trading_sessions=calendar, observed_at=at())
        if (snapshot.market_session != state.sessions[-1]
                or datetime.fromtimestamp(snapshot.provider_timestamp_ms/1000, tz=SHANGHAI_TZ) > at()):
            raise ValueError('fresh index snapshot has another completed session or future ready time')
        for p in snapshot.points:
            prices = state_rows[p.thscode]['closes']
            if p.last_price != Decimal(prices[-1]) or p.prev_price != Decimal(prices[-2]):
                raise ValueError('fresh index last/previous closes differ from exact saved state')
        for code, direction in plan['directions'].items():
            m = members.fetch_hithink_sector_membership(sector_thscode=code,
                sector_name=direction['observation']['name'], api_key='INJECTED', request_json=get)
            received = at()
            if m.captured_at > received:
                raise ValueError('membership is future relative to reading cutoff')
            if m.captured_at.astimezone(SHANGHAI_TZ).date() != received.astimezone(SHANGHAI_TZ).date():
                raise ValueError('membership is not from this current observation date')
            memberships[code] = m
    benchmark = tuple(Decimal(v) for v in state_rows[state.benchmark_thscode]['closes'])
    bret = {str(n): _return_over(benchmark, end_index=len(benchmark)-1, sessions=n) for n in (5, 20, 60)}
    identities = {}
    for m in memberships.values():
        for member in m.members:
            if member.thscode in identities and identities[member.thscode] != member:
                raise ValueError('current memberships disagree on stock identity')
            identities[member.thscode] = member
    for issuer in plan['issuers']:
        code = issuer['thscode']
        valid_origins = []
        for origin in issuer['origins']:
            present = [s for s in origin['sector_codes'] if any(m.thscode == code for m in memberships[s].members)]
            if present:
                valid_origins.append({**origin, 'current_member_sectors': present})
        row = {**issuer, 'current_origins': valid_origins, 'stock_path': None,
               'market_comparison': {}, 'sector_comparisons': [], 'eligible_nodes': [],
               'excluded_reasons': [], 'eligible_for_shadow_reading': False}
        if not valid_origins:
            row['excluded_reasons'].append('NOT_A_CURRENT_MEMBER_OF_REVIEWED_ACTIVE_DIRECTION')
            rows.append(row); continue
        name = identities[code].name
        row['current_member_name'] = name
        if re.match(r'^(?:\*?ST|[NC])', name) or '退' in name:
            row['excluded_reasons'].append('RISK_OR_NEW_LISTING_NAME_LABEL')
            rows.append(row); continue
        response = get(STOCK_HISTORY, _history_params(code, state.sessions))
        path = _stock_path(state, code, response, at=at())
        row['stock_path'] = path
        row['market_comparison'] = {n: {'stock_return': value, 'benchmark_return': bret[n],
            'excess_return': value - bret[n]} for n, value in path['returns'].items()}
        for origin in valid_origins:
            beat = False
            for sector in origin['current_member_sectors']:
                comparison = {'node_id': origin['node_id'], 'thscode': sector,
                    'name': plan['directions'][sector]['observation']['name'], 'horizons': {}}
                prices = tuple(Decimal(v) for v in state_rows[sector]['closes'])
                for n in (5, 20, 60):
                    ret = _return_over(prices, end_index=len(prices)-1, sessions=n)
                    comparison['horizons'][str(n)] = {'sector_return': ret,
                        'stock_excess_return': path['returns'][str(n)] - ret}
                beat |= comparison['horizons']['20']['stock_excess_return'] > 0
                row['sector_comparisons'].append(comparison)
            if beat:
                row['eligible_nodes'].append(origin['node_id'])
        reasons = row['excluded_reasons']
        if path['latest_volume'] <= 0 or path['latest_turnover'] <= 0:
            reasons.append('NO_POSITIVE_LATEST_REPORTED_TRADING_ACTIVITY')
        if path['returns']['5'] <= 0 or row['market_comparison']['5']['excess_return'] <= 0:
            reasons.append('FIVE_DAY_RAW_PATH_OR_MARKET_EXCESS_NOT_POSITIVE')
        if row['market_comparison']['20']['excess_return'] <= 0:
            reasons.append('TWENTY_DAY_MARKET_EXCESS_NOT_POSITIVE')
        if not row['eligible_nodes']:
            reasons.append('TWENTY_DAY_PATH_DOES_NOT_BEAT_ANY_REVIEWED_SECTOR')
        row['eligible_for_shadow_reading'] = not reasons
        rows.append(row)
    rows = _plain(rows)
    selected = _select(rows, plan['node_order'])
    reviewed_codes = {r['thscode'] for r in plan['issuers']}
    payload = {
        'version': VERSION, 'semantics': SEMANTICS, 'policy': POLICY, 'plan_hash': plan['plan_hash'],
        'market_session': state.sessions[-1], 'observed_at': at(),
        'status': 'STOCKS_FOR_SHADOW_READING' if selected else 'NO_MATCH_WITHIN_REVIEWED_COMPANY_SCOPE',
        'scope': plan['reviewed_company_coverage'], 'reviewed_issuers': len(plan['issuers']),
        'active_directions_without_stock_business_scope': plan['active_directions_without_stock_business_scope'],
        'current_member_union_count': len(identities),
        'unreviewed_current_members': [vars(identities[k]) for k in sorted(set(identities)-reviewed_codes)],
        'membership_hashes': {k: m.constituent_set_hash for k, m in memberships.items()},
        'all_stock_observations': rows, 'surfaced_stocks': selected,
        'eligible_stock_count': sum(r['eligible_for_shadow_reading'] for r in rows),
        'omitted_eligible_stock_codes': [r['thscode'] for r in rows if r['eligible_for_shadow_reading']
                                       and r['thscode'] not in {s['thscode'] for s in selected}],
        'market_state_hash': state.state_hash, 'event_ledger_hash': plan['event_ledger_hash'],
        'new_stock_event_created': False, 'price_path_is_not_total_return': True,
        'profitability_valuation_or_odds_established': False, **LIMITS,
    }
    return _plain({'projection': payload, 'projection_hash': canonical_hash(payload)})


def render_stock_reading(report: dict) -> str:
    p = report['projection']
    if (report['projection_hash'] != canonical_hash(p) or p['semantics'] != SEMANTICS
            or p['policy'] != POLICY or any(p[k] != v for k, v in LIMITS.items())
            or len(p['surfaced_stocks']) > 3):
        raise ValueError('stock reading identity or authority differs')
    e = lambda x: escape(str(x), quote=True)
    pct = lambda x: f'{Decimal(x)*100:+.2f}%'
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">',
        '<title>股票观察 · Radar</title><style>body{font:16px/1.65 system-ui;margin:0;background:#f4f6f8;color:#20313d}main{max-width:980px;margin:auto;padding:24px}header,article,section{background:white;margin:16px 0;padding:24px;border:1px solid #dce3e7;border-radius:10px}h1{font-size:28px}h2{font-size:23px}.notice{padding:12px;background:#fff4d9}small{color:#52636f}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:right}p,code,pre,a{overflow-wrap:anywhere}pre{white-space:pre-wrap;font-size:12px;max-height:360px;overflow:auto}summary{cursor:pointer;padding:10px 0}.scroll{overflow:auto}@media(max-width:600px){main{padding:10px}header,article,section{padding:15px}}</style>',
        '<main><header><h1>股票观察 · 可以展开看的对象</h1>',
        f'<p><strong>{len(p["surfaced_stocks"])} 只通过本版观察条件</strong>；行情交易日 {e(p["market_session"])}；读取截止 {e(p["observed_at"])}</p>',
        '<p class="notice">这是按需打开的 shadow 股票页，不是买入建议或 canonical Inbox 推送。只覆盖已接入公司依据的范围，不是全 A 股盲选；价格走强不等于盈利改善、估值便宜或赔率成立。</p>',
        f'<p>本次审阅公司范围 {p["reviewed_issuers"]} 只；所查方向成员并集 {p["current_member_union_count"]} 只；其中未接入公司依据 {len(p["unreviewed_current_members"])} 只。另有 {len(p["active_directions_without_stock_business_scope"])} 个强方向尚无股票业务观察范围。</p></header>']
    if not p['surfaced_stocks']:
        parts.append('<section><h2>本范围没有通过全部观察条件的股票</h2><p>不等于市场没有机会。缺业务覆盖、无当前成员关系与股票表现未通过，均在完整结果中分开保留；缺失或无效行情不会产生这份成功空结果。</p></section>')
    for row in p['surfaced_stocks']:
        path = row['stock_path']
        parts += [f'<article><h2>{e(row["company_name"])} <small>{e(row["thscode"])}</small></h2>',
            f'<p>原始收盘价 <strong>{e(path["last_close"])} CNY</strong>；当日原始价格变化 {pct(path["daily_raw_return"])}。不是成交建议。</p>',
            '<div class="scroll"><table><tr><th>窗口</th><th>股票原始收益</th><th>沪深300收益</th><th>超额收益</th></tr>']
        for n in ('5', '20', '60'):
            values = row['market_comparison'][n]
            parts.append('<tr>'+''.join(f'<td>{e(v)}</td>' for v in (n+'日',pct(values['stock_return']),pct(values['benchmark_return']),pct(values['excess_return'])))+'</tr>')
        parts += ['</table></div>', '<p><small>未复权价格路径，不含分红再投资，不等于投资者总回报；60日仅展示，不参与本版门槛。没有自动复权或使用全市场试验文件。</small></p>']
        for origin in row['current_origins']:
            c = origin['company']
            parts += [f'<h3>来自：{e(origin["node_label"])}</h3><p>{e(c["business_scope"])}</p>',
                f'<p><strong>下一步核查：</strong>{e(origin["review_question"])}</p>',
                '<p>业务依据：有已留存字段，不是净受益确认；当前经营新鲜度、暴露比例和估值仍未建立。</p>']
            for comparison in (v for v in row['sector_comparisons'] if v['node_id']==origin['node_id']):
                parts.append(f'<p>{e(comparison["name"])} · {e(comparison["thscode"])}：股票20日相对该行业 {pct(comparison["horizons"]["20"]["stock_excess_return"])}。881／884分别比较，不混合排名；当前成员不倒灌历史。</p>')
            parts += ['<details><summary>公司依据、原始位置及仍需核查的问题</summary>',
                      '<pre>'+e(canonical_json({'basis':c['basis'],'mechanisms':c['mechanisms']}))+'</pre></details>']
        parts.append('</article>')
    parts += ['<section><h2>完整范围与未选中原因</h2><details><summary>所有公司、未覆盖成员及省略项</summary><pre>',
              e(canonical_json({k:p[k] for k in ('all_stock_observations','unreviewed_current_members','omitted_eligible_stock_codes','active_directions_without_stock_business_scope')})),
              '</pre></details><p>固定的股票价格条件尚未经过前瞻效果验证；最多3只只是阅读压缩，不是机会分数或独立预测数。</p>',
              '<a href="stock-reading.json">完整结构化结果</a></section>',
              '<footer>SHADOW OBSERVATION ONLY · HUMAN ATTENTION / RESEARCH / INVESTMENT AUTHORITY = NONE</footer></main></html>']
    return '\n'.join(parts)+'\n'
