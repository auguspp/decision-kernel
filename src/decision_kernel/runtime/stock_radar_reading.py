"""One stock-first shadow reader, reconciled with the separate local projection.

A's direction, gates and round-robin presentation are retained. B's exact dated
reference checks are reused here, not a second selector. Current HiThink daily
history does NOT document daily prev_price. No live reference source is wired;
that is a visible data gap, never a price fabricated from yesterday's close.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from decimal import Decimal, localcontext, Context, InvalidOperation
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

VERSION = 'stock-first-reviewed-scope-raw-path-v1'
SEMANTICS = 'BOUNDED_STOCK_READING_NOT_RECOMMENDATION_OR_CANONICAL_ATTENTION'
STOCK_HISTORY = '/api/a-share/prices/historical'
MAX_ISSUERS, MAX_MEMBERSHIPS, MAX_REQUESTS = 16, 6, 26
COMPANY_MANIFEST = 'radar_inputs/economic-company-links-livestock-v1.json'
SYNTHETIC_REFERENCES = 'SYNTHETIC_TEST_ONLY'
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
    'reference_requirement': 'EXACT_DATED_INDEPENDENT_REFERENCE_WINDOW_AND_LATEST_QUOTE_NO_FILL',
    'live_reference_source': 'NOT_ESTABLISHED',
    'max_cards': 3, 'max_issuers': MAX_ISSUERS, 'max_memberships': MAX_MEMBERSHIPS,
    'no_composite_score': True,
}
LIMITS = {
    **probe.AUTHORITY, 'creates_canonical_wake': False, 'events_created': 0,
    'market_state_writes': 0, 'automatic_research_routing': False,
    'recommendation': None, 'independent_forecast_count': None,
    'business_benefit_established': False,
}
STATUS_LABELS = {
    'STOCKS_FOR_SHADOW_READING': '本范围有通过观察条件的股票',
    'NO_MATCH_WITHIN_REVIEWED_COMPANY_SCOPE': '资料完整，但本范围没有通过全部观察条件的股票',
    'NO_ACTIVE_DIRECTIONS': '当前没有满足既有行业门槛的方向',
    'BUSINESS_COVERAGE_INSUFFICIENT': '有活跃方向，但没有相应已接入公司依据',
    'DATA_INSUFFICIENT': '数据不足，不能形成合格股票名单',
    'DATA_QUALIFICATION_FAILED': '输入资格校验未通过，不能形成合格股票名单',
    'REQUEST_FAILED': '请求失败，本次检查未完成',
}


class StockReadingInputError(ValueError):
    """Sanitized, finite diagnostic vocabulary; never echo provider error text."""
    def __init__(self, category, reason_code, *, thscode=None):
        self.category, self.reason_code, self.thscode = category, reason_code, thscode
        super().__init__(reason_code)


def _plain(value):
    return json.loads(canonical_json(value))


def _state_rows(state):
    return {r['thscode']: r for r in json.loads(serialize_sector_radar_market_state(state))['series']}


def _hash_ok(value, key):
    return value.get(key) == canonical_hash({k: v for k, v in value.items() if k != key})


def _reference_inputs(value):
    if value is None:
        return
    # The local ZIP was a normalized-input demonstration, not a provider adapter.
    # Until a real origin-qualified source exists, supplied references are TEST ONLY.
    if (not isinstance(value, dict) or set(value) != {'provenance', 'windows', 'latest_quotes'}
            or value['provenance'] != SYNTHETIC_REFERENCES
            or not isinstance(value['windows'], dict) or not isinstance(value['latest_quotes'], dict)):
        raise ValueError('reference input is not an explicitly synthetic normalized fixture')


def prepare_stock_reading(source_root: Path, state, ledger, association: dict, *,
                          observed_at: datetime, company_manifest: str = COMPANY_MANIFEST) -> dict:
    """Freeze the whole reviewed scope before any stock history or compression."""
    probe._window(state, observed_at)
    linked = company.build_company_links(source_root, association, manifest_path=company_manifest)
    p = association['projection']
    if (p['market_state_hash'] != state.state_hash or p['event_ledger_hash'] != ledger.ledger_hash
            or probe._clock(p['as_of']) > observed_at):
        raise ValueError('stock reading association belongs to different or future inputs')
    context = build_sector_radar_context(market_state=state, event_ledger=ledger, generated_at=observed_at)
    all_rows = {r['observation']['thscode']: r for u in context['universes'] for r in u['rows']}
    families = {r['observation']['thscode']: u['family'] for u in context['universes'] for r in u['rows']}
    panels = {row['node_id']: row for row in p['panels']}
    directions, issuers, order, evidence_scope = {}, {}, [], {}
    for node in linked['projection']['nodes']:
        panel = panels[node['node_id']]
        for c in node['companies']:
            code = to_hithink_thscode(ticker=c['ticker'], exchange=c['exchange'])
            if code in evidence_scope and evidence_scope[code] != c['company_name']:
                raise ValueError('one exact stock identity has conflicting company names')
            evidence_scope[code] = c['company_name']
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
        sources = [{
            'thscode': code, 'name': all_rows[code]['observation']['name'], 'family': families[code],
            'source_kind': ('RECORDED_NEW_SECTOR_EVENT' if all_rows[code]['recorded_event_ids_latest_session']
                            else 'CURRENT_STRONG_PATH_NOT_A_NEW_EVENT'),
            'recorded_event_ids': all_rows[code]['recorded_event_ids_latest_session'],
        } for code in sorted(active)]
        for c in node['companies']:
            code = to_hithink_thscode(ticker=c['ticker'], exchange=c['exchange'])
            if code not in issuers:
                issuers[code] = {'thscode': code, 'company_name': c['company_name'], 'origins': []}
            issuers[code]['origins'].append({
                'node_id': node['node_id'], 'node_label': panel['label'],
                'sector_codes': sorted(active), 'direction_sources': sources, 'company': c,
                'node_relation_note': panel['relation_note'], 'review_question': panel['review_question'],
                'economic_coverage': node['economic_coverage'],
            })
    request_count = 4 + len(directions) + len(issuers) if issuers else 0
    if len(issuers) > MAX_ISSUERS or len(directions) > MAX_MEMBERSHIPS or request_count > MAX_REQUESTS:
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
        'evidence_scope_issuers': [{'thscode': k, 'company_name': evidence_scope[k]} for k in sorted(evidence_scope)],
        'all_active_direction_count': len(active_codes),
        'active_directions_without_stock_business_scope': sorted(active_codes - set(directions)),
        'recorded_sector_events_latest_session': context['recorded_events_latest_session'],
        'reviewed_company_coverage': 'CURATED_LINKS_ONLY_NOT_A_BLIND_ALL_STOCK_SCREEN',
        'maximum_request_count': request_count, 'stock_gate_is_unvalidated_shadow_policy': True, **LIMITS,
    }
    body['plan_hash'] = canonical_hash(body)
    return _plain(body)


def _history_params(code, sessions):
    start = datetime.combine(sessions[-61], datetime.min.time(), tzinfo=SHANGHAI_TZ)
    end = datetime.combine(sessions[-1] + timedelta(days=1), datetime.min.time(), tzinfo=SHANGHAI_TZ)
    return {'thscode': code, 'interval': '1d', 'adjust': 'none',
            'start': str(int(start.timestamp() * 1000)), 'end': str(int(end.timestamp() * 1000))}


def _reference_number(value):
    if isinstance(value, (bool, float)):
        raise ValueError('reference values must be exact decimal strings or integers')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('reference value is not an exact decimal') from exc
    if not number.is_finite() or number < 0:
        raise ValueError('reference values must be finite and nonnegative')
    return number


def _qualify_references(code, expected, bars, references, at):
    """B's independent-reference invariant; no derived prev_price or tolerance.

    The supplied test windows and latest quote are separate inputs. No caller can
    relabel them LIVE_HITHINK. A live source needs a separately reviewed adapter.
    """
    if references is None:
        raise StockReadingInputError('DATA_INSUFFICIENT',
            'QUALIFIED_DAILY_REFERENCE_HISTORY_UNAVAILABLE', thscode=code)
    _reference_inputs(references)
    rows = references['windows'].get(code)
    latest = references['latest_quotes'].get(code)
    if not rows or latest is None or len(rows) != 61:
        raise StockReadingInputError('DATA_INSUFFICIENT', 'REFERENCE_WINDOW_OR_CURRENT_QUOTE_MISSING', thscode=code)
    last_receipt = None
    for i, (day, ref) in enumerate(zip(expected, rows, strict=True)):
        if ref['thscode'] != code or ref['market_session'] != day.isoformat():
            raise ValueError('reference identity or exact completed calendar differs')
        received = probe._clock(ref['captured_at'])
        close_at = datetime.combine(day, datetime.min.time(), tzinfo=SHANGHAI_TZ) + timedelta(hours=15, minutes=30)
        if received < close_at or received > at or (last_receipt is not None and received < last_receipt):
            raise ValueError('reference receipt is unfinished, future, or reversed')
        last_receipt = received
        values = tuple(_reference_number(ref[k]) for k in ('last_price', 'prev_price', 'volume', 'turnover'))
        if values[0] <= 0 or values[1] <= 0:
            raise ValueError('reference prices must be positive')
        if values[2] <= 0 or values[3] <= 0:
            raise StockReadingInputError('DATA_INSUFFICIENT',
                'UNPRICED_OR_NONTRADING_SESSION_IN_PATH', thscode=code)
        bar = bars[day]
        if (values[0], values[2], values[3]) != tuple(Decimal(str(bar[k])) for k in ('close_price', 'volume', 'turnover')):
            raise ValueError('dated independent reference and own historical bar differ')
        if i and values[1] != Decimal(str(bars[expected[i-1]]['close_price'])):
            raise StockReadingInputError('DATA_QUALIFICATION_FAILED',
                'PRICE_REFERENCE_DISCONTINUITY_REQUIRES_SEPARATE_REVIEW', thscode=code)
    if (latest['thscode'] != code or latest['market_session'] != expected[-1].isoformat()
            or not last_receipt <= probe._clock(latest['captured_at']) <= at
            or any(_reference_number(latest[k]) != _reference_number(rows[-1][k])
                   for k in ('last_price', 'prev_price', 'volume', 'turnover'))):
        raise ValueError('current quote differs from the exact latest dated reference')


def _stock_path(state, code, response, *, at, references=None):
    qualified = normalize_hithink_completed_price_history(
        response, thscode=code, sessions=state.sessions, observed_at=at)
    expected = tuple(state.sessions[-61:])
    if (tuple(p.as_of.astimezone(SHANGHAI_TZ).date() for p in qualified.points) != expected
            or qualified.response_session != state.sessions[-1]
            or qualified.expected_latest_session != state.sessions[-1]):
        raise StockReadingInputError('DATA_INSUFFICIENT', 'EXACT_61_COMPLETED_STOCK_SESSIONS_REQUIRED', thscode=code)
    by_day = {}
    for row in response['data']['item']:
        stamp = row['date_ms']
        if type(stamp) is not int:
            raise ValueError('stock bar timestamp must be exact integer milliseconds')
        instant = datetime.fromtimestamp(stamp / 1000, tz=SHANGHAI_TZ)
        if instant.time() != datetime.min.time():
            raise ValueError('stock bar must use an explicit Shanghai-midnight date key')
        by_day[instant.date()] = row
    _qualify_references(code, expected, by_day, references, at)
    closes = tuple(p.close for p in qualified.points)
    amounts = tuple(Decimal(str(by_day[d]['turnover'])) for d in expected)
    prior = _average(amounts[-25:-5])
    return {
        'last_close': closes[-1], 'previous_raw_close': closes[-2],
        'latest_volume': Decimal(str(by_day[expected[-1]]['volume'])), 'latest_turnover': amounts[-1],
        'daily_raw_return': closes[-1] / closes[-2] - 1,
        'returns': {str(n): _return_over(closes, end_index=60, sessions=n) for n in (5, 20, 60)},
        'turnover_pulse_5_vs_prior_20': _average(amounts[-5:]) / prior if prior else None,
        'twenty_day_return_five_sessions_ago': _return_over(closes, end_index=55, sessions=20),
        'price_convention': 'RAW_UNADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN',
        'corporate_action_adjustment': 'NOT_PERFORMED', 'tradability': 'NOT_CERTIFIED_BY_PRICE_AND_VOLUME',
        'reference_continuity': 'EXACT_SUPPLIED_TEST_REFERENCES_NOT_LIVE_ORIGIN_PROOF',
        'history_session_count': 61,
    }


def _select(rows, node_order):
    """A's unchanged visible lexicographic order; never a weighted opportunity score."""
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
                          cutoff_clock=None, reference_inputs=None) -> dict:
    _reference_inputs(reference_inputs)
    with localcontext(Context(prec=28)):
        return _observe(plan, state, request_json=request_json, observed_at=observed_at,
                        cutoff_clock=cutoff_clock, reference_inputs=reference_inputs)


def _observe(plan, state, *, request_json, observed_at, cutoff_clock, reference_inputs):
    expected_requests = 4 + len(plan['directions']) + len(plan['issuers']) if plan['issuers'] else 0
    if reference_inputs is not None:
        planned_codes = {r['thscode'] for r in plan['issuers']}
        if (set(reference_inputs['windows']) - planned_codes
                or set(reference_inputs['latest_quotes']) - planned_codes):
            raise ValueError('reference inputs contain unplanned stock identities')
    if (plan['version'] != VERSION or plan['policy'] != POLICY or not _hash_ok(plan, 'plan_hash')
            or plan['market_state_hash'] != state.state_hash or plan['semantics'] != SEMANTICS
            or any(plan[k] != v for k, v in LIMITS.items())
            or len(plan['issuers']) > MAX_ISSUERS or len(plan['directions']) > MAX_MEMBERSHIPS
            or expected_requests != plan['maximum_request_count'] or expected_requests > MAX_REQUESTS):
        raise ValueError('stock plan identity, policy, budget or authority differs')
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
        if isinstance(value, dict) and type(value.get('code')) is int and value['code'] != 0:
            raise StockReadingInputError('REQUEST_FAILED', 'PROVIDER_BUSINESS_REQUEST_FAILED')
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
               'excluded_reasons': [], 'eligible_for_shadow_reading': False,
               'status': 'CONDITIONS_NOT_MET'}
        if not valid_origins:
            row['excluded_reasons'].append('NOT_A_CURRENT_MEMBER_OF_REVIEWED_ACTIVE_DIRECTION')
            rows.append(row); continue
        name = identities[code].name
        row['current_member_name'] = name
        if re.match(r'^(?:\*?ST|[NC])', name) or '退' in name:
            row['excluded_reasons'].append('RISK_OR_NEW_LISTING_NAME_LABEL')
            rows.append(row); continue
        response = get(STOCK_HISTORY, _history_params(code, state.sessions))
        path = _stock_path(state, code, response, at=at(), references=reference_inputs)
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
        row['status'] = 'QUALIFIED_SYNTHETIC_READING' if not reasons else 'CONDITIONS_NOT_MET'
        rows.append(row)
    rows = _plain(rows)
    selected = _select(rows, plan['node_order'])
    reviewed_codes = {r['thscode'] for r in plan['issuers']}
    status = ('STOCKS_FOR_SHADOW_READING' if selected else
              'NO_ACTIVE_DIRECTIONS' if not plan['all_active_direction_count'] else
              'BUSINESS_COVERAGE_INSUFFICIENT' if not plan['issuers'] else
              'NO_MATCH_WITHIN_REVIEWED_COMPANY_SCOPE')
    payload = {
        'version': VERSION, 'semantics': SEMANTICS, 'policy': POLICY, 'plan_hash': plan['plan_hash'],
        'market_session': state.sessions[-1], 'observed_at': at(), 'status': status,
        'scope': plan['reviewed_company_coverage'], 'reviewed_issuers': len(plan['issuers']),
        'evidence_scope_issuers': plan['evidence_scope_issuers'],
        'active_directions_without_stock_business_scope': plan['active_directions_without_stock_business_scope'],
        'recorded_sector_events_latest_session': plan['recorded_sector_events_latest_session'],
        'source_event_status': ('RECORDED_SECTOR_EVENTS_PRESENT' if plan['recorded_sector_events_latest_session']
                                else 'NO_NEW_RECORDED_SECTOR_EVENT_NOT_NO_STOCK_OPPORTUNITY'),
        'fresh_context_revalidated': bool(plan['issuers']),
        'reference_input_provenance': reference_inputs['provenance'] if reference_inputs else 'UNAVAILABLE',
        'reference_input_hash': canonical_hash(reference_inputs) if reference_inputs else None,
        'live_stock_qualification': 'NOT_ESTABLISHED',
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
    codes = [r['thscode'] for r in p['surfaced_stocks']]
    if (report['projection_hash'] != canonical_hash(p) or p['semantics'] != SEMANTICS
            or p['policy'] != POLICY or any(p[k] != v for k, v in LIMITS.items())
            or len(codes) > 3 or len(codes) != len(set(codes))
            or p['status'] not in STATUS_LABELS
            or (codes and p['reference_input_provenance'] != SYNTHETIC_REFERENCES)):
        raise ValueError('stock reading identity or authority differs')
    e = lambda x: escape(str(x), quote=True)
    pct = lambda x: f'{Decimal(x)*100:+.2f}%'
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">',
        '<title>股票观察 · Radar</title><style>body{font:16px/1.65 system-ui;margin:0;background:#f4f6f8;color:#20313d}main{max-width:980px;margin:auto;padding:24px}header,article,section{background:white;margin:16px 0;padding:24px;border:1px solid #dce3e7;border-radius:10px}h1{font-size:28px}h2{font-size:23px}.notice{padding:12px;background:#fff4d9}small{color:#52636f}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:right}p,code,pre,a{overflow-wrap:anywhere}pre{white-space:pre-wrap;font-size:12px;max-height:360px;overflow:auto}summary{cursor:pointer;padding:10px 0}.scroll{overflow:auto}@media(max-width:600px){main{padding:10px}header,article,section{padding:15px}}</style>',
        '<main><header><h1>股票观察 · 可以展开看的对象</h1>',
        f'<p><strong>{len(codes)} 只通过本版观察条件</strong>；行情交易日 {e(p["market_session"])}；读取截止 {e(p["observed_at"])}</p>',
        '<p class="notice">值得看不等于值得买。按需打开的 shadow 页面，不是买入建议或 canonical Inbox 推送；不是全 A 股盲选。</p>',
        f'<p>已接入依据的公司：{e("、".join(r["company_name"]+" "+r["thscode"] for r in p["evidence_scope_issuers"]))}。本次活跃方向内计划审阅 {p["reviewed_issuers"]} 只；未接入业务依据的所查成员 {len(p["unreviewed_current_members"])} 只。</p>',
        f'<p>来源事件：{p["recorded_sector_events_latest_session"]} 个已记录行业事件；没有新事件不等于没有仍强势路径。本层不生成事件。</p></header>']
    if p['reference_input_provenance'] == SYNTHETIC_REFERENCES:
        parts.append('<p class="notice">SYNTHETIC_TEST_ONLY：合成行情及参考价验收样本，不是真实程序选股；不能用作市场判断。</p>')
    if not codes:
        parts.append(f'<section><h2>{e(STATUS_LABELS[p["status"]])}</h2><p>不等于市场没有机会。覆盖缺口、条件不满足与数据不足分别记录；数据不足的尝试不会生成成功空名单。</p></section>')
    for row in p['surfaced_stocks']:
        path = row['stock_path']
        parts += [f'<article><h2>{e(row["company_name"])} <small>{e(row["thscode"])}</small></h2>',
            '<p><strong>为什么值得进一步看：</strong>当前有关联的强势方向及留存业务依据；个股5日上涨并跑赢基准，20日跑赢基准及至少一个相关行业。只是固定试行观察条件，未证明投资价值。</p>',
            f'<p>原始收盘价 <strong>{e(path["last_close"])} CNY</strong>；当日原始价格变化 {pct(path["daily_raw_return"])}。</p>',
            '<div class="scroll"><table><tr><th>窗口</th><th>股票原始收益</th><th>沪深300收益</th><th>超额收益</th></tr>']
        for n in ('5', '20', '60'):
            values = row['market_comparison'][n]
            parts.append('<tr>'+''.join(f'<td>{e(v)}</td>' for v in (n+'日',pct(values['stock_return']),pct(values['benchmark_return']),pct(values['excess_return'])))+'</tr>')
        parts += ['</table></div><p><small>61个完成交易日；未复权原始价格变化，非含分红总回报；60日只展示，不参与门槛。当前成员不倒灌历史。</small></p>']
        for origin in row['current_origins']:
            c = origin['company']
            sources = [s for s in origin['direction_sources'] if s['thscode'] in origin['current_member_sectors']]
            source_text = '；'.join(s['name']+' '+s['thscode']+' / '+s['family']+' / '+(
                '已记录新进入行业事件' if s['source_kind']=='RECORDED_NEW_SECTOR_EVENT' else '仍强势阅读，非新事件') for s in sources)
            questions = list(dict.fromkeys(q for m in c['mechanisms'] for q in m['next_checks']))
            limitations = '；'.join(sorted({b['evidence']['retention_mode']+'/'+b['evidence']['replayability_level'] for b in c['basis']}))
            parts += [f'<h3>来源：{e(origin["node_label"])}</h3><p>{e(source_text)}</p>',
                f'<p><strong>公司业务依据：</strong>{e(c["business_scope"])}</p>',
                f'<p><strong>风险／缺口：</strong>{e(c["exposure_size_note"])} 留存状态：{e(limitations)}；业务存在不等于净受益，当前经营新鲜度、估值与赔率未建立。</p>',
                f'<p><strong>下一步核查：</strong>{e(questions[0] if questions else origin["review_question"])}</p>']
            for comparison in (v for v in row['sector_comparisons'] if v['node_id']==origin['node_id']):
                parts.append(f'<p>{e(comparison["name"])} · {e(comparison["thscode"])}：个股20日相对该行业 {pct(comparison["horizons"]["20"]["stock_excess_return"])}；881／884分别比较，不混合排名。</p>')
            parts += ['<details><summary>公司依据、原始位置及全部核查问题</summary><pre>',
                e(canonical_json({'basis':c['basis'],'mechanisms':c['mechanisms'], 'issuer_binding_note':c['issuer_binding_note']})), '</pre></details>']
        parts.append('</article>')
    parts += ['<section><h2>完整范围与未选中原因</h2><details><summary>全部公司、未覆盖成员及合格但未展示项</summary><pre>',
              e(canonical_json({k:p[k] for k in ('all_stock_observations','unreviewed_current_members','omitted_eligible_stock_codes','active_directions_without_stock_business_scope')})),
              '</pre></details><p>固定条件尚未经过前瞻效果验证；最多3只只是阅读压缩，不是综合机会分数。</p>',
              '<a href="stock-reading.json">完整结构化结果</a></section>',
              '<footer>SHADOW OBSERVATION ONLY · HUMAN ATTENTION AUTHORITY = NONE · RESEARCH AUTHORITY = NONE · INVESTMENT AUTHORITY = NONE</footer></main></html>']
    return '\n'.join(parts)+'\n'
