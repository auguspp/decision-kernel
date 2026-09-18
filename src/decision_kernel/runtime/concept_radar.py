"""Independent current concept discovery; bounded detail, no Industry gate.

The full current snapshot is not a full multiday trend cross-section. Three
absolute daily movers receive detail acquisition, never an investment score.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import datetime, time, timedelta
from decimal import Context, Decimal, localcontext
from html import escape
from itertools import combinations

from decision_kernel.adapters.hithink import (
    SHANGHAI_TZ, latest_completed_a_share_session, normalize_hithink_calendar,
)
from decision_kernel.adapters.hithink_index import (
    normalize_hithink_completed_index_history, normalize_hithink_industry_catalog,
    normalize_hithink_index_snapshot,
)
from decision_kernel.identity import canonical_hash, canonical_json
from . import theme_radar_probe as probe
from .institutional_radar import decode, session_date
from .hithink_http import HITHINK_CALENDAR_PATH
from .hithink_sector_breadth_http import normalize_hithink_sector_membership
from .sector_breadth import calculate_current_membership_overlap
from .sector_radar import SECTOR_RADAR_MAX_WINDOW_SESSIONS
from .sector_radar_audit import _check_request, _clock

VERSION = 'independent-concept-snapshot-bounded-detail-v1'
SEMANTICS = 'CONCEPT_SOURCE_OBSERVATION_NOT_RESEARCH_OR_GLOBAL_MULTIDAY_RANK'
MAX_CATALOG, SNAPSHOT_CHUNK, MAX_REQUESTS = 4096, 1024, 15
MAX_DETAILS = probe.MAX_THEMES
BENCHMARK = '000300.SH'
AUTHORITY = {**probe.AUTHORITY, 'automatic_research_routing': False,
             'odds_recomputed': False, 'business_benefit_established': False}
POLICY = {
    'version': VERSION, 'catalog_tag': 'cn_concept',
    'detail_order': 'ABSOLUTE_SAME_DAY_INDEX_RETURN_DESC_THEN_EXACT_CODE',
    'detail_order_meaning': 'BOUNDED_ACQUISITION_EXPERIMENT_NOT_RESEARCH_PRIORITY',
    'maximum_details': MAX_DETAILS, 'maximum_requests': MAX_REQUESTS,
    'maximum_catalog': MAX_CATALOG, 'snapshot_chunk': SNAPSHOT_CHUNK,
    'history_sessions': SECTOR_RADAR_MAX_WINDOW_SESSIONS,
    'window': 'EXPLICIT_SAME_DAY_AFTER_1530_SHANGHAI_ONLY',
    'industry_ranking': 'UNCHANGED_AND_NOT_CONSUMED',
    'global_multiday_rank': 'NOT_COMPUTED', 'retry_count': 0,
}


class ConceptSourceError(ValueError):
    """Finite safe source reason, without remote message text."""


class _DetailUnavailable(ConceptSourceError):
    pass


def require(condition, reason):
    if not condition:
        raise ConceptSourceError(reason)


def _plain(value):
    return json.loads(canonical_json(value))


def _history_params(code, sessions):
    millis = lambda d: str(int(datetime.combine(d, time(), tzinfo=SHANGHAI_TZ).timestamp() * 1000))
    return {'thscode': code, 'interval': '1d', 'start': millis(sessions[0]),
            'end': millis(sessions[-1] + timedelta(days=1))}


def _history(body, code, sessions, at, snapshot, *, compare_activity=True):
    # Existing normalizer plus exact window/no intraday-date-key qualification.
    rows = body['data'].get('item')
    require(isinstance(rows, list) and len(rows) == len(sessions), 'HISTORY_WINDOW_INCOMPLETE')
    for row in rows:
        stamp = row.get('date_ms')
        require(type(stamp) is int and datetime.fromtimestamp(stamp / 1000, SHANGHAI_TZ).time() == time(),
                'HISTORY_DATE_KEY_REJECTED')
    series = normalize_hithink_completed_index_history(body, thscode=code, sessions=sessions, observed_at=at)
    require(tuple(p.as_of.astimezone(SHANGHAI_TZ).date() for p in series.points) == sessions,
            'HISTORY_WINDOW_INCOMPLETE')
    last, prior = series.points[-1], series.points[-2]
    require((last.close, prior.close) == (snapshot.last_price, snapshot.prev_price),
            'SNAPSHOT_HISTORY_MISMATCH')
    if compare_activity:
        require((last.volume, last.turnover) == (snapshot.volume, snapshot.turnover),
                'SNAPSHOT_HISTORY_MISMATCH')
    return series


def observe(request_raw, *, market_session, started_at, provenance='SYNTHETIC_TEST_ONLY'):
    """One deterministic request graph, reused verbatim by credential-free replay.

    The callback returns (unchanged safe JSON bytes, requested_at, received_at).
    No current Sector state, caller stock/theme list, or model is consulted.
    """
    with localcontext(Context(prec=28)):
        return _observe(request_raw, market_session, _clock(started_at), provenance)


def _observe(request_raw, market_session, started_at, provenance):
    day = session_date(market_session)
    local = started_at.astimezone(SHANGHAI_TZ)
    require(local.date() == day and local.time() >= time(15, 30), 'SAME_DAY_COMPLETED_WINDOW_REQUIRED')
    require(provenance in {'LIVE_HITHINK', 'SYNTHETIC_TEST_ONLY'}, 'PROVENANCE_REJECTED')
    last, refs = started_at, []
    close = datetime.combine(day, time(15), tzinfo=SHANGHAI_TZ)

    def get(path, params, *, detail=False):
        nonlocal last
        require(len(refs) < MAX_REQUESTS, 'REQUEST_BUDGET_REACHED')
        _check_request(path, params)
        raw, requested, received = request_raw(path, dict(params))
        requested, received = _clock(requested), _clock(received)
        require(last <= requested <= received <= started_at + timedelta(minutes=30)
                and received.astimezone(SHANGHAI_TZ).date() == day, 'RESPONSE_CLOCK_REJECTED')
        body = decode(raw)
        refs.append({'path': path, 'params': params, 'requested_at': requested, 'received_at': received,
                     'body_sha256': hashlib.sha256(raw).hexdigest(), 'body_bytes': len(raw)})
        last = received
        require(type(body.get('code')) is int, 'BUSINESS_ENVELOPE_REJECTED')
        if body['code'] != 0:
            if detail and body['code'] in {3001, 3002, 3004}:
                raise _DetailUnavailable('DETAIL_PROVIDER_DATA_UNAVAILABLE')
            raise ConceptSourceError('PROVIDER_BUSINESS_REJECTED')
        # Original per-response data-ready check; never use a later call's clock.
        probe._record({'path': path, 'params': params, 'requested_at': requested.isoformat(),
                       'received_at': received.isoformat(), 'response': body}, path, params,
                      lower=started_at, upper=received,
                      ready_after=None if path in {probe.HISTORY, probe.CATALOG, HITHINK_CALENDAR_PATH} else close)
        return body

    calendar = normalize_hithink_calendar(get(HITHINK_CALENDAR_PATH, {}))
    require(day in calendar and latest_completed_a_share_session(calendar, observed_at=last) == day,
            'CALENDAR_SESSION_REJECTED')
    sessions = tuple(d for d in calendar if d <= day)[-SECTOR_RADAR_MAX_WINDOW_SESSIONS:]
    require(len(sessions) == SECTOR_RADAR_MAX_WINDOW_SESSIONS, 'CALENDAR_WINDOW_INCOMPLETE')
    catalogs = []
    for tag in ('cn_concept', 'industry'):
        body = get(probe.CATALOG, {'tag': tag})
        require(isinstance(body['data'].get('item'), list)
                and 0 < len(body['data']['item']) <= MAX_CATALOG, 'CATALOG_SCOPE_REJECTED')
        catalogs.append(normalize_hithink_industry_catalog(body))
    concepts, industry = catalogs
    names = {i.thscode: i.name for i in concepts.identities}
    codes = list(names)
    require(not set(codes).intersection(i.thscode for i in industry.identities)
            and not any(re.fullmatch(r'(881|884)[0-9]{3}\.TI', c) for c in codes)
            and not industry.unexpected_industries, 'CONCEPT_INDUSTRY_IDENTITY_OVERLAP')
    # Full declared catalog, not endpoint limit/offset (which is not supported).
    snapshots, snapshot_refs = {}, {}
    requested_codes = [BENCHMARK, *codes]
    for offset in range(0, len(requested_codes), SNAPSHOT_CHUNK):
        chunk = requested_codes[offset:offset + SNAPSHOT_CHUNK]
        body = get(probe.SNAPSHOT, {'thscodes': ','.join(chunk)})
        batch = normalize_hithink_index_snapshot(body, requested_thscodes=chunk)
        for point in batch.points:
            snapshots[point.thscode] = point
            snapshot_refs[point.thscode] = len(refs) - 1
    require(set(snapshots) == set(requested_codes), 'SNAPSHOT_UNIVERSE_DIFFERS')
    benchmark_body = get(probe.HISTORY, _history_params(BENCHMARK, sessions))
    benchmark = _history(benchmark_body, BENCHMARK, sessions, last, snapshots[BENCHMARK], compare_activity=False)
    daily = lambda c: snapshots[c].last_price / snapshots[c].prev_price - 1
    ordered = sorted(codes, key=lambda c: (-abs(daily(c)), c))
    selected = ordered[:MAX_DETAILS]
    details, members = {}, {}
    for code in selected:
        name = names[code]
        row = {'thscode': code, 'name': name, 'path': None, 'current_membership': None,
               'history_status': 'NOT_ACQUIRED', 'membership_status': 'NOT_ACQUIRED',
               'gaps': [], 'history_request_index': None, 'membership_request_index': None}
        try:
            body = get(probe.HISTORY, _history_params(code, sessions), detail=True)
        except _DetailUnavailable as exc:
            row['history_status'] = 'SOURCE_UNAVAILABLE'
            row['gaps'].append(str(exc))
        else:
            try:
                series = _history(body, code, sessions, last, snapshots[code])
                row['path'] = probe._path_observation(code, series.points,
                    tuple(p.close for p in benchmark.points), sessions)
                row['history_status'] = 'EXACT_WINDOW_CHECKED'
            except (ValueError, TypeError, KeyError, OverflowError, OSError):
                row['history_status'] = 'DATA_QUALIFICATION_REJECTED'
                row['gaps'].append('HISTORY_REJECTED_NOT_NO_TREND')
        row['history_request_index'] = len(refs) - 1
        try:
            body = get(probe.MEMBERS, {'thscode': code}, detail=True)
        except _DetailUnavailable as exc:
            row['membership_status'] = 'SOURCE_UNAVAILABLE'
            row['gaps'].append(str(exc))
        else:
            try:
                member = normalize_hithink_sector_membership(body, sector_thscode=code, sector_name=name)
                members[code] = member
                row['current_membership'] = asdict(member)
                row['membership_status'] = 'CURRENT_MEMBERS_CHECKED_NOT_ECONOMIC_EXPOSURE'
            except (ValueError, TypeError, KeyError, RuntimeError):
                row['membership_status'] = 'DATA_QUALIFICATION_REJECTED'
                row['gaps'].append('MEMBERSHIP_REJECTED_NOT_NO_MEMBERS')
        row['membership_request_index'] = len(refs) - 1
        details[code] = row
    companies = {}
    for code, membership in members.items():
        for member in membership.members:
            row = companies.setdefault(member.thscode, {'thscode': member.thscode,
                'source_names': [], 'origins': [], 'business_linkage': 'NOT_ESTABLISHED',
                'stock_execution': 'NOT_EXECUTED_BY_THIS_SOURCE',
                'pre_quick_execution': 'NOT_EXECUTED_BY_THIS_SOURCE'})
            if member.name not in row['source_names']:
                row['source_names'].append(member.name)
            row['origins'].append({'kind': 'CONCEPT_CURRENT_MEMBER', 'concept_thscode': code,
                'concept_name': membership.sector_name, 'membership_hash': membership.constituent_set_hash,
                'market_session': day, 'membership_request_index': details[code]['membership_request_index'],
                'history_status': details[code]['history_status']})
    rows = [{'thscode': c, 'name': names[c],
             'daily_return': daily(c), 'daily_benchmark_excess': daily(c) - daily(BENCHMARK),
             'snapshot': asdict(snapshots[c]), 'snapshot_request_index': snapshot_refs[c],
             'detail_acquisition': 'SELECTED' if c in details else 'DEFERRED_NOT_ACQUIRED'} for c in ordered]
    pairs = [asdict(calculate_current_membership_overlap(left=members[a], right=members[b]))
             for a, b in combinations(sorted(members), 2)]
    payload = {'version': VERSION, 'semantics': SEMANTICS, 'policy': POLICY, 'provenance': provenance,
        'market_session': day, 'started_at': started_at, 'as_of': last, 'requests': refs,
        'concept_catalog_hash': canonical_hash({'tag': 'cn_concept', 'identities': [asdict(i) for i in concepts.identities]}),
        'industry_catalog_hash': industry.catalog_hash, 'benchmark_thscode': BENCHMARK,
        'catalog_count': len(codes), 'snapshot_count': len(rows), 'concepts': rows,
        'detail_selected_codes': selected, 'details': [details[c] for c in selected],
        'companies': [companies[c] for c in sorted(companies)], 'overlaps': pairs,
        'coverage': {'snapshot_catalog_complete': True, 'multiday_global_ranking': False,
            'history_checked': sum(r['history_status'] == 'EXACT_WINDOW_CHECKED' for r in details.values()),
            'memberships_checked': len(members), 'detail_deferred': len(codes) - len(selected),
            'detail_gaps': sum(bool(r['gaps']) for r in details.values()),
            'member_union': len(companies), 'member_occurrences': sum(len(m.members) for m in members.values()),
            'member_price_breadth': 'NOT_ACQUIRED', 'historical_memberships': 'NOT_ESTABLISHED',
            'source_publication_time': 'UNKNOWN', 'historical_first_vintage': 'NOT_ESTABLISHED',
            'snapshot_session_basis': 'BENCHMARK_BOUND_NOT_EACH_CONCEPT_HISTORY',
            'atomic_snapshot': False, 'full_concept_trend_radar': False}, **AUTHORITY}
    return _plain({'projection': payload, 'projection_hash': canonical_hash(payload)})


def render(report):
    p = report['projection']
    require(report.get('projection_hash') == canonical_hash(p) and p.get('version') == VERSION
            and p.get('semantics') == SEMANTICS and p.get('policy') == POLICY
            and all(p.get(k) == v for k, v in AUTHORITY.items()), 'REPORT_IDENTITY_REJECTED')
    e = lambda x: escape(str(x), quote=True)
    pct = lambda x: f'{Decimal(x) * 100:+.2f}%'
    out = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<title>概念雷达 · 独立来源</title><style>body{font:16px/1.7 system-ui;max-width:1100px;margin:auto;padding:20px}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid;padding:8px;text-align:left}pre,p,td{overflow-wrap:anywhere}pre{white-space:pre-wrap}section{margin:24px 0}.scroll{overflow:auto}</style>',
        '<h1>概念／题材雷达 · 独立来源</h1>',
        f'<p>目标交易日 {e(p["market_session"])}；实际取得截止 {e(p["as_of"])}；来源 {e(p["provenance"])}。</p>',
        f'<p>目录与当日快照 {p["catalog_count"]} 个；有界详情 {len(p["details"])} 个；去重当前成员 {len(p["companies"])} 家。</p>',
        '<p><strong>全部概念快照不等于全部概念多日趋势。</strong>按当日绝对涨跌幅选取详情是取数实验，不是投资排名；下跌方向也保留。未取历史或成员不等于没有机会。</p>',
        '<p>不依赖行业首页或原股票强势筛选；不是行业与概念混排。当前成员不回填历史，概念归属不等于业务受益。本来源未执行 Stock、Pre、Quick 或 Odds。</p>',
        '<section><h2>全部概念 · 当日变化</h2><details><summary>展开完整目录与未取得详情的方向</summary><div class="scroll"><table><tr><th>概念／代码</th><th>当日</th><th>对沪深300</th><th>详情</th></tr>']
    for c in p['concepts']:
        out.append('<tr>' + ''.join('<td>' + e(x) + '</td>' for x in
            (c['name'] + ' ' + c['thscode'], pct(c['daily_return']), pct(c['daily_benchmark_excess']), c['detail_acquisition'])) + '</tr>')
    out.append('</table></div></details></section>')
    for t in p['details']:
        out += [f'<section><h2>{e(t["name"])} · {e(t["thscode"])}</h2>',
                f'<p>历史：{e(t["history_status"])}；成员：{e(t["membership_status"])}。</p>']
        if t['path'] is not None:
            for h in t['path']['horizons']:
                out.append(f'<p>{h["sessions"]}日：指数 {pct(h["index_return"])}，对沪深300超额 {pct(h["excess_return"])}。</p>')
            out.append(f'<p>20日正超额持续 {t["path"]["positive_20d_excess_persistence_sessions"]} 个交易日；左侧截断：{e(t["path"]["positive_20d_excess_persistence_left_censored"])}。不推断趋势真正起点。</p>')
        else:
            out.append('<p>多日趋势不可用，不能写成没有趋势。</p>')
        if t['current_membership'] is not None:
            out.append('<details><summary>展开全部当前成员</summary><p>' + e('；'.join(m['name']+' '+m['thscode'] for m in t['current_membership']['members'])) + '</p></details>')
        out += ['<details><summary>原指标与明确缺口</summary><pre>', e(canonical_json(t)), '</pre></details></section>']
    out += ['<section><h2>覆盖与重叠</h2><p>同一证券在多个概念出现只计一家公司；重叠不是多份独立确认。成员涨跌宽度与业务联系尚未核验。</p><pre>',
            e(canonical_json({'coverage': p['coverage'], 'overlaps': p['overlaps']})),
            '</pre></section><p><a href="observation.json">完整公司来路与结构化结果</a></p>',
            '<footer>WHY UNKNOWN · BUSINESS LINK NOT ESTABLISHED · INVESTMENT AUTHORITY NONE</footer></html>']
    return '\n'.join(out) + '\n'
