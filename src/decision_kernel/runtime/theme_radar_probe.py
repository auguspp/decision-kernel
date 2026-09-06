"""Bounded concept-index reading; reuse market adapters, never industry ranking.

Explicit input requests are evidence claims, not certified HTTP execution. The
probe cannot append state, signal events, qualify a provider, or route Research.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from dataclasses import asdict
from datetime import datetime, time, timedelta, timezone
from decimal import Context, Decimal, localcontext
from html import escape
from itertools import combinations
from pathlib import Path

from decision_kernel.adapters.hithink import SHANGHAI_TZ, require_hithink_data
from decision_kernel.adapters.hithink_index import (
    normalize_hithink_completed_index_history, normalize_hithink_industry_catalog,
    normalize_hithink_index_snapshot,
)
from decision_kernel.identity import canonical_hash, canonical_json
from .economic_market_context import _clock, _keys
from .economic_release_review import _safe_path
from .hithink_sector_breadth_http import normalize_hithink_sector_membership
from .sector_breadth import calculate_current_membership_overlap
from .sector_radar import _average, _persistence, _return_over, SECTOR_RADAR_MAX_WINDOW_SESSIONS
from .sector_radar_state import parse_sector_radar_market_state, serialize_sector_radar_market_state
from .judgment_timeline import _unique_object

VERSION = 'bounded-theme-path-current-overlap-v0'
SEMANTICS = 'SELECTED_CONCEPT_PROBE_NOT_INDUSTRY_SIGNAL_OR_GLOBAL_THEME_RANK'
SUPPLIED = 'SUPPLIED_HITHINK_RECORDS_NOT_LIVE_CERTIFIED'
SYNTHETIC = 'SYNTHETIC_TEST_ONLY'
CATALOG = '/api/a-share-index/catalog/ths-index-list'
HISTORY = '/api/a-share-index/prices/historical'
SNAPSHOT = '/api/a-share-index/prices/snapshot'
MEMBERS = '/api/a-share-index/constituents/ths-stock-list'
MAX_THEMES, MAX_INDUSTRIES, MAX_INPUT_BYTES = 3, 6, 8 * 1024 * 1024
AUTHORITY = {'human_attention_authority': 'NONE', 'research_authority': 'NONE',
             'investment_authority': 'NONE', 'signal_transition_authority': 'NONE',
             'market_state_writes': 0, 'events_created': 0, 'creates_canonical_wake': False}


def _window(state, at):
    """Conservative v0: completed day or its immediately adjacent weekend only."""
    day = state.sessions[-1]
    close = datetime.combine(day, time(15), tzinfo=SHANGHAI_TZ)
    local = at.astimezone(SHANGHAI_TZ)
    if at < close or not (local.date() == day or (
        day.weekday() == 4 and local.weekday() in (5, 6)
        and 1 <= (local.date() - day).days <= 2
    )):
        raise ValueError('probe is not aligned to the saved completed day; no weekday-gap or holiday inference')
    return close


def _record(record, path, params, *, lower, upper, ready_after=None):
    _keys(record, {'path', 'params', 'requested_at', 'received_at', 'response'})
    if record['path'] != path or record['params'] != params:
        raise ValueError('capture request identity differs from the explicit probe plan')
    started, received = _clock(record['requested_at']), _clock(record['received_at'])
    if not lower <= started <= received <= upper:
        raise ValueError('capture clock lies outside its explicit acquisition window')
    data = require_hithink_data(record['response'], endpoint=path)
    stamp = data.get('timestamp')
    if type(stamp) is not int or stamp <= 0:
        raise ValueError('provider ready timestamp must be integer milliseconds')
    try:
        ready = datetime.fromtimestamp(stamp / 1000, tz=SHANGHAI_TZ)
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError('invalid provider ready clock') from exc
    if path == MEMBERS and len(data.get('item', [])) > 10000:
        raise ValueError('membership reading budget exceeded')
    if ready > received or (ready_after is not None and ready < ready_after):
        raise ValueError('future or stale provider ready clock')
    return record['response']


def _choices(rows, catalog, maximum, minimum):
    if not isinstance(rows, list) or not minimum <= len(rows) <= maximum:
        raise ValueError('probe request budget exceeded or empty theme selection; no truncation')
    names, seen = {x.thscode: x.name for x in catalog.identities}, set()
    for item in rows:
        _keys(item, {'thscode', 'name', 'reason'})
        code = item['thscode']
        if not isinstance(code, str) or code in seen or names.get(code) != item['name']:
            raise ValueError('missing, renamed or duplicate exact catalog selection')
        if not isinstance(item['reason'], str) or not 1 <= len(item['reason'].strip()) <= 1600:
            raise ValueError('explicit selection reason is required; not an opportunity score')
        seen.add(code)
    return sorted(rows, key=lambda x: x['thscode'])


def make_theme_plan(state, concept_catalog, industry_catalog, *, themes, industries, planned_at):
    """Plan only; the two exact catalog captures precede manual bounded selection."""
    planned_at = _clock(planned_at)
    state = parse_sector_radar_market_state(serialize_sector_radar_market_state(state))
    close = _window(state, planned_at)
    if state.updated_at > planned_at or state.benchmark_thscode != '000300.SH':
        raise ValueError('saved state must precede selection and use the qualified CSI300 identity')
    # Reuse the existing strict .TI identity/name/timestamp/hash parser only. Its
    # family partitions are NEVER used to rank or relabel a concept as industry.
    parsed = []
    for record, tag in ((concept_catalog, 'cn_concept'), (industry_catalog, 'industry')):
        body = _record(record, CATALOG, {'tag': tag}, lower=close, upper=planned_at)
        if len(body['data'].get('item', [])) > 4096:
            raise ValueError('catalog reading budget exceeded')
        parsed.append(normalize_hithink_industry_catalog(body))
    concepts, industry = parsed
    if industry.catalog_hash != state.catalog_hash or industry.unexpected_industries:
        raise ValueError('industry catalog drift from saved market identity')
    if ({x.thscode for x in concepts.identities} & {x.thscode for x in industry.identities}
            or any(re.fullmatch(r'(881|884)[0-9]{3}\.TI', x.thscode) for x in concepts.identities)):
        raise ValueError('concept catalog must remain disjoint from 881/884')
    selected = _choices(themes, concepts, MAX_THEMES, 1)
    probes = _choices(industries, industry, MAX_INDUSTRIES, 0)
    if any(not re.fullmatch(r'881[0-9]{3}\.TI', x['thscode']) for x in probes):
        raise ValueError('cross-industry coverage probes use 881 only; no parent-child double count')
    millis = lambda d: str(int(datetime.combine(d, time(), tzinfo=SHANGHAI_TZ).timestamp() * 1000))
    codes = [x['thscode'] for x in selected]
    requests = [{'id': 'snapshot', 'path': SNAPSHOT,
                 'params': {'thscodes': ','.join([state.benchmark_thscode, *codes])}}]
    for code in codes:
        requests.append({'id': 'history:' + code, 'path': HISTORY, 'params': {
            'thscode': code, 'interval': '1d', 'start': millis(state.sessions[0]),
            'end': millis(state.sessions[-1] + timedelta(days=1))}})
    for code in sorted(codes + [x['thscode'] for x in probes]):
        requests.append({'id': 'members:' + code, 'path': MEMBERS, 'params': {'thscode': code}})
    plan = {'formula_version': VERSION, 'market_state_hash': state.state_hash,
            'market_session': state.sessions[-1], 'planned_at': planned_at,
            'catalog_captures_hash': canonical_hash([concept_catalog, industry_catalog]),
            'concept_catalog_hash': canonical_hash({'tag': 'cn_concept', 'identities': [asdict(x) for x in concepts.identities]}),
            'industry_catalog_hash': industry.catalog_hash, 'themes': selected, 'industries': probes,
            'requests': requests, 'planned_request_count_including_catalogs': len(requests) + 2,
            'maximum_request_count': 15, 'requests_executed_by_planner': 0}
    return json.loads(canonical_json({**plan, 'plan_hash': canonical_hash(plan)}))


def _path_observation(code, points, benchmark, sessions):
    # Exactly the existing 126-session observation window, no tiny-subset ranks.
    n = SECTOR_RADAR_MAX_WINDOW_SESSIONS
    points, benchmark, sessions = points[-n:], benchmark[-n:], sessions[-n:]
    closes = [p.close for p in points]
    returns = lambda values, end, span: _return_over(values, end_index=end, sessions=span)
    history = {i: {code: returns(closes, i, 20) - returns(benchmark, i, 20)} for i in range(20, len(points))}
    end = len(points) - 1
    count, started, censored = _persistence(sessions=sessions, history=history, thscode=code,
        condition=lambda v: v > 0, first_computable_index=20)
    horizons = []
    for span in (5, 20, 60):
        a, b = returns(closes, end, span), returns(benchmark, end, span)
        horizons.append({'sessions': span, 'index_return': a, 'benchmark_return': b, 'excess_return': a - b})
    prior = _average([p.turnover for p in points[-25:-5]])
    return {'horizons': horizons, 'excess_acceleration_5_sessions_20d': history[end][code] - history[end-5][code],
            'positive_20d_excess_persistence_sessions': count, 'positive_20d_excess_run_started': started,
            'positive_20d_excess_persistence_left_censored': censored,
            'turnover_pulse_5_vs_prior_20': None if prior == 0 else _average([p.turnover for p in points[-5:]]) / prior,
            'history_window_start': sessions[0], 'history_window_end': sessions[-1],
            'cross_sectional_rank': None, 'rating': None, 'first_system_discovery_at': None}


def build_theme_probe(state, inputs, *, as_of, generated_at):
    """Validate ALL selected inputs before displaying any theme; no partial rank."""
    _keys(inputs, {'schema_version', 'provenance', 'plan', 'concept_catalog', 'industry_catalog', 'captures'})
    if type(inputs['schema_version']) is not int or inputs['schema_version'] != 1 or inputs['provenance'] not in {SUPPLIED, SYNTHETIC}:
        raise ValueError('unsupported supplied probe format or provenance')
    as_of, generated_at = _clock(as_of), _clock(generated_at)
    state = parse_sector_radar_market_state(serialize_sector_radar_market_state(state))
    close = _window(state, as_of)
    p = inputs['plan']
    plan = make_theme_plan(state, inputs['concept_catalog'], inputs['industry_catalog'],
        themes=p['themes'], industries=p['industries'], planned_at=p['planned_at'])
    if p != plan:
        raise ValueError('probe plan identity or request budget changed')
    planned = _clock(plan['planned_at'])
    if planned > as_of or as_of > generated_at or as_of - planned > timedelta(minutes=30):
        raise ValueError('probe capture window exceeds 30 minutes or generation precedes cutoff')
    captures = inputs['captures']
    expected = {r['id'] for r in plan['requests']}
    if not isinstance(captures, dict) or set(captures) != expected:
        raise ValueError('every planned response must exist; missing/extra captures are not quiet success')
    bodies = {r['id']: _record(captures[r['id']], r['path'], r['params'], lower=planned, upper=as_of,
                ready_after=close if r['path'] != HISTORY else None) for r in plan['requests']}
    batch = normalize_hithink_index_snapshot(bodies['snapshot'],
        requested_thscodes=[state.benchmark_thscode, *[x['thscode'] for x in plan['themes']]])
    snapshot = {p.thscode: p for p in batch.points}
    benchmark = next(s for s in state.series if s.thscode == state.benchmark_thscode)
    anchor = snapshot[state.benchmark_thscode]
    if (anchor.last_price, anchor.prev_price) != (benchmark.closes[-1], benchmark.closes[-2]):
        raise ValueError('snapshot benchmark differs from saved latest/previous completed closes')
    memberships = {}
    for item in plan['themes'] + plan['industries']:
        code = item['thscode']
        memberships[code] = normalize_hithink_sector_membership(bodies['members:' + code],
            sector_thscode=code, sector_name=item['name'])
    themes = []
    with localcontext(Context(prec=28)):
        for selected in plan['themes']:
            code = selected['thscode']
            series = normalize_hithink_completed_index_history(bodies['history:' + code],
                thscode=code, sessions=state.sessions, observed_at=as_of)
            if tuple(p.as_of.date() for p in series.points) != state.sessions:
                raise ValueError('theme history missing latest/intermediate/initial session; no dropped or filled days')
            current, previous, snap = series.points[-1], series.points[-2], snapshot[code]
            if (current.close, previous.close, current.turnover, current.volume) != (
                    snap.last_price, snap.prev_price, snap.turnover, snap.volume):
                raise ValueError('theme snapshot latest/previous/volume/turnover differs from dated history')
            member = memberships[code]
            overlaps = [asdict(calculate_current_membership_overlap(left=member, right=memberships[i['thscode']]))
                        for i in plan['industries']]
            claims = {m.thscode: [o['right_sector_thscode'] for o in overlaps if m.thscode in o['intersection_members']]
                      for m in member.members}
            exclusive = {i['thscode']: sorted(c for c, matches in claims.items() if matches == [i['thscode']])
                         for i in plan['industries']}
            ambiguous = {c: matches for c, matches in sorted(claims.items()) if len(matches) > 1}
            unassigned = sorted(c for c, matches in claims.items() if not matches)
            nonempty = sum(bool(v) for v in exclusive.values())
            status = ('NO_INDUSTRIES_PROBED' if not overlaps else 'AMBIGUOUS_CURRENT_MEMBERSHIP' if ambiguous
                      else 'OBSERVED_ACROSS_PROBED_INDUSTRIES' if nonempty >= 2 else 'LIMITED_PROBED_COVERAGE')
            themes.append({'selection': selected, 'path': _path_observation(code, series.points, benchmark.closes, state.sessions),
                'current_membership': asdict(member), 'membership_response_received_at': captures['members:' + code]['received_at'],
                'industry_probe_status': status, 'industry_overlaps': overlaps, 'exclusive_industry_members': exclusive,
                'ambiguous_industry_members': ambiguous, 'unassigned_in_probed_industries': unassigned,
                'denominator': len(member.members), 'historical_constituents': 'NOT_ESTABLISHED',
                'current_price_breadth': 'NOT_ACQUIRED', 'company_economic_exposure': 'NOT_ESTABLISHED'})
        pairs = [asdict(calculate_current_membership_overlap(left=memberships[a['thscode']], right=memberships[b['thscode']]))
                 for a, b in combinations(plan['themes'], 2)]
    union = {m.thscode for t in plan['themes'] for m in memberships[t['thscode']].members}
    projection = {'schema_version': 1, 'semantics': SEMANTICS, 'formula_version': VERSION,
        'provenance': inputs['provenance'], 'as_of': as_of, 'market_session': state.sessions[-1],
        'market_state_hash': state.state_hash, 'benchmark_thscode': state.benchmark_thscode,
        'plan': plan, 'input_hash': canonical_hash(inputs), 'themes': themes, 'theme_overlaps': pairs,
        'unique_selected_theme_members': len(union), 'summed_theme_member_count': sum(t['denominator'] for t in themes),
        'global_theme_ranking': 'NOT_COMPUTED', 'independent_forecast_count': None,
        'live_prospective_evidence_created': False, 'network_calls': 0, **AUTHORITY}
    return json.loads(canonical_json({'generated_at': generated_at, 'projection': projection,
                                      'projection_hash': canonical_hash(projection)}))


def render_theme_probe(report):
    """Presentation after build_theme_probe, not a new untrusted deserializer."""
    p = report['projection']
    if report['projection_hash'] != canonical_hash(p) or p['semantics'] != SEMANTICS or any(p[k] != v for k,v in AUTHORITY.items()):
        raise ValueError('invalid theme report identity or authority')
    e = lambda x: escape(str(x), quote=True)
    pct = lambda x: f'{Decimal(x) * 100:+.2f}%'
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
        '<title>跨行业主题探针</title><style>body{font:16px/1.7 system-ui;margin:24px auto;padding:16px;max-width:1040px}section{border:1px solid;padding:18px;margin:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}td,th{padding:8px;text-align:left;border-bottom:1px solid}details{margin:12px 0}a,code,p{overflow-wrap:anywhere}.scroll{overflow:auto}</style><main>',
        '<h1>跨行业主题观察 · 有界探针</h1><p><strong>SHADOW OBSERVATION ONLY · NOT RESEARCH · NOT A RECOMMENDATION</strong></p>',
        f'<p>来源标记：{e(p["provenance"])}；本页没有实时采集证明。<br>保存行情日 {e(p["market_session"])}；输入截止 {e(p["as_of"])}；生成 {e(report["generated_at"])}</p>',
        '<p>只读明确选择的最多三个概念，不是全市场扫描或排名。趋势起点不等于系统发现时间；当前成员不回填历史，不构造可投资组合。</p>']
    for t in p['themes']:
        selected, path = t['selection'], t['path']
        parts += [f'<section><h2>{e(selected["name"])} · {e(selected["thscode"])}</h2><p>选取理由（声明）：{e(selected["reason"])}</p>',
                  '<div class="scroll"><table><tr><th>交易日窗口</th><th>指数</th><th>基准</th><th>超额</th></tr>']
        for h in path['horizons']:
            parts.append('<tr>' + ''.join(f'<td>{e(x)}</td>' for x in (h['sessions'], pct(h['index_return']), pct(h['benchmark_return']), pct(h['excess_return']))) + '</tr>')
        age = ('至少 ' if path['positive_20d_excess_persistence_left_censored'] else '') + str(path['positive_20d_excess_persistence_sessions'])
        parts += ['</table></div>', f'<p>20 日正超额连续 {e(age)} 个可计算交易日；5 日加速度 {e(pct(path["excess_acceleration_5_sessions_20d"]))}；成交额脉冲 {e(path["turnover_pulse_5_vs_prior_20"] if path["turnover_pulse_5_vs_prior_20"] is not None else "前期成交额为零，未计算")}。</p>',
                  f'<p>当前成员 {t["denominator"]}；行业探针状态 {e(t["industry_probe_status"])}。未映射 {len(t["unassigned_in_probed_industries"])}，重复行业归属 {len(t["ambiguous_industry_members"])}。</p>',
                  '<p>行业分母仅涵盖所选 881 查询；未映射不是“没有所属行业”。重复归属不按最大交集强行分配。成员数不是指数权重，当前涨跌宽度未采集，公司受益未建立。</p>']
        for overlap in t['industry_overlaps']:
            parts.append(f'<p>{e(overlap["right_sector_name"])} · {e(overlap["right_sector_thscode"])}：原始交集 {overlap["intersection_count"]}/{t["denominator"]}；仅属该探针 {len(t["exclusive_industry_members"][overlap["right_sector_thscode"]])}。</p>')
        parts.append(f'<details><summary>精确成员、缺口与计算字段</summary><pre>{e(canonical_json(t))}</pre></details></section>')
    parts.append('<h2>主题之间是否重复？</h2><p>保留全部身份，不自动合并主题或增加独立样本数。</p>')
    for pair in p['theme_overlaps']:
        parts.append(f'<p>{e(pair["left_sector_name"])} × {e(pair["right_sector_name"])}：共享 {pair["intersection_count"]}，并集 {pair["union_count"]}，Jaccard {e(pair["jaccard"])}。这是当前集合关系，不是历史相关性或因果关系。</p>')
    return '\n'.join(parts + ['<p>Human / Research / Investment authority = NONE。没有评分、候选写入、自动 Research 或 Inbox 提醒。</p><a href="theme-probe.json">完整记录</a></main></html>']) + '\n'


def _read(path):
    _safe_path(path)
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError('probe file must be regular and within byte budget')
    raw = path.read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError('probe file exceeds byte budget')
    return raw


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline selected concept probe; no network or production writes.')
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _safe_path(args.output)
        if args.output.exists() or any(args.output.resolve().is_relative_to(p.resolve().parent) for p in (args.state, args.input)):
            raise ValueError('output must be new and outside input directories')
        raw_state, raw_input = _read(args.state), _read(args.input)
        inputs = json.loads(raw_input, object_pairs_hook=_unique_object, parse_float=Decimal)
        report = build_theme_probe(parse_sector_radar_market_state(raw_state.decode()), inputs,
                                   as_of=args.as_of, generated_at=datetime.now(timezone.utc).isoformat())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.theme-probe-', dir=args.output.parent) as temporary:
            stage = Path(temporary) / 'result'; stage.mkdir()
            for name, raw in {'index.html': render_theme_probe(report).encode(),
                'theme-probe.json': (canonical_json(report) + '\n').encode(),
                'supplied-input.json': raw_input, 'saved-market-state.json': raw_state}.items():
                (stage / name).write_bytes(raw)
            receipt = {'semantics': 'READ_ONLY_LOCAL_PROBE_NOT_SOURCE_AUTHENTICATION_OR_RESTORE',
                'projection_hash': report['projection_hash'],
                'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir()}, **AUTHORITY}
            (stage / 'files.json').write_text(canonical_json(receipt) + '\n', encoding='utf-8')
            if _read(args.state) != raw_state or _read(args.input) != raw_input:
                raise ValueError('input bytes changed while building the probe')
            _safe_path(args.output)
            if args.output.exists():
                raise ValueError('output appeared during probe generation')
            stage.rename(args.output)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print('Theme probe unavailable:', type(exc).__name__)
        return 2
    print('Selected theme probe written; no live evidence, global ranking or new events')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
