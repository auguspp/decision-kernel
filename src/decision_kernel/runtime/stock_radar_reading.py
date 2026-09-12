"""One stock-first shadow reader using the existing HiThink acquisition path.

Raw close ratios and independently reference-qualified/adjusted performance are
not interchangeable contracts. Real input uses HiThink's dated raw bars, exact
latest price checks, bounded turnover reconciliation and window-scoped action
checks, not synthetic daily references.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, time, timedelta
from decimal import Decimal, localcontext, Context, InvalidOperation
from html import escape
from pathlib import Path

from decision_kernel.adapters.hithink import (
    SHANGHAI_TZ, latest_completed_a_share_session, normalize_hithink_calendar,
    normalize_hithink_completed_price_history, to_hithink_thscode,
)
from decision_kernel.adapters.hithink_index import (
    HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
    HithinkIndexAdapterError,
    HithinkQualifiedIndexSnapshotBatch,
)
from decision_kernel.identity import canonical_hash, canonical_json
from . import economic_company_context as company
from . import hithink_index_http as indices
from . import hithink_sector_breadth_http as members
from . import theme_radar_probe as probe
from . import hithink_stock_reading as own_stock
from .hithink_stock_reading import StockReadingInputError
from .hithink_http import HITHINK_CALENDAR_PATH
from .sector_radar import _return_over, _average
from .sector_radar_context import build_sector_radar_context
from .sector_radar_state import serialize_sector_radar_market_state

VERSION = 'stock-first-reviewed-scope-window-qualified-v6'
SEMANTICS = 'BOUNDED_STOCK_READING_NOT_RECOMMENDATION_OR_CANONICAL_ATTENTION'
STOCK_HISTORY = '/api/a-share/prices/historical'
MAX_ISSUERS, MAX_MEMBERSHIPS, MAX_REQUESTS = 16, 6, 26
COMPANY_MANIFEST = 'radar_inputs/economic-company-links-livestock-v1.json'
SYNTHETIC_REFERENCES = 'SYNTHETIC_TEST_ONLY'
HITHINK_RAW = 'HITHINK_REQUEST_BOUND_RAW_OBSERVATION'
PREMARKET_CARRY_CUTOFF = time(9, 15)
_LATER_TRADING_DAY_SNAPSHOT_ERROR = (
    'index snapshot provider data-ready time falls on a later trading session'
)
# Only an explicit single-stock response may be isolated. Authentication,
# rate limits, unknown business errors, transport/safety errors, shared inputs,
# request clocks and budgets remain batch-fatal. Never convert 3002 to no events.
_ISSUER_BUSINESS_CODES = frozenset({3001, 3002, 3004})
_ISSUER_DATA_REASONS = frozenset({
    'REQUIRED_INPUT_OR_FIELD_MISSING', 'EXACT_61_COMPLETED_STOCK_SESSIONS_REQUIRED',
    'UNPRICED_OR_NONTRADING_SESSION_IN_PATH', 'CURRENT_QUOTE_HISTORY_MISMATCH',
    'PRICE_REFERENCE_DISCONTINUITY_REQUIRES_SEPARATE_REVIEW',
    'REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW',
    'INPUT_CLOCK_IDENTITY_OR_SCHEMA_REJECTED',
})
POLICY = {
    'version': VERSION,
    'direction': 'EXISTING_CURRENT_SECTOR_GATE_NOT_NEW_EVENT_REQUIRED',
    'issuer_universe': 'ALL_REVIEWED_ISSUERS_IN_ACTIVE_LINKED_NODES_NOT_ALL_A_SHARES',
    'membership': 'EXACT_CURRENT_MEMBER_REQUIRED_NOT_HISTORICAL_EXPOSURE',
    'stock_gate': 'POSITIVE_5D_RAW_AND_5D_MARKET_EXCESS_AND_20D_MARKET_EXCESS_AND_ONE_20D_SECTOR_EXCESS',
    'sixty_day': 'CONTEXT_ONLY_NOT_A_GATE_NULL_IF_REPORTED_ACTION_CROSSES',
    'activity': 'POSITIVE_LATEST_VOLUME_AND_TURNOVER_NOT_EXECUTION_ELIGIBILITY',
    'name_guard': 'ST_DELISTING_AND_N_C_PREFIX_LABELS_ONLY_NOT_FULL_REGULATORY_STATUS',
    'presentation': 'NODE_ORDER_ROUND_ROBIN_THEN_20D_MARKET_EXCESS_5D_MARKET_EXCESS_CODE',
    'reference_requirement': 'HITHINK_61_OWN_BARS_EXACT_PRICES_VOLUME_TOLERANT_TURNOVER_ACTIONS_BY_WINDOW',
    'turnover_reconciliation': dict(own_stock.TURNOVER_POLICY),
    'corporate_actions': 'SUCCESSFUL_QUERY_REQUIRED_NO_REPORTED_EVENT_CROSSING_5D_OR_20D',
    'live_reference_source': 'HITHINK_EXISTING_GITHUB_SECRET_NO_SECOND_PROVIDER_REQUIRED',
    'source_contract': own_stock.CONTRACT,
    'session_freshness': 'FETCHED_CALENDAR_LATEST_COMPLETED_NOT_WEEKDAY_HEURISTIC',
    'premarket_index_carry': 'STOCK_ONLY_RECEIPT_BOUND_STRICTLY_BEFORE_0915_OPENING_AUCTION',
    'issuer_failure_scope': 'ISOLATE_KNOWN_STOCK_DATA_FAILURES_NOT_SHARED_OR_TRANSPORT_FAILURES',
    'partial_result': 'USABLE_SUBSET_ONLY_WITH_FULL_PLAN_DENOMINATOR_AND_EXPLICIT_GAPS',
    'max_cards': 3, 'max_issuers': MAX_ISSUERS, 'max_memberships': MAX_MEMBERSHIPS,
    'no_composite_score': True,
}
MARKET_EXPRESSION_VERSION = 'stock-market-expression-window-qualified-v7'
MARKET_EXPRESSION_SEMANTICS = 'BOUNDED_MARKET_EXPRESSION_NOT_BUSINESS_BENEFIT_OR_RECOMMENDATION'
MARKET_EXPRESSION_POLICY = {
    **POLICY,
    'version': MARKET_EXPRESSION_VERSION,
    'issuer_universe': 'BOUNDED_SURFACED_SECTOR_BREADTH_LEADERS_NOT_ALL_A_SHARES',
    'business_evidence': 'ANNOTATION_ONLY_NOT_CANDIDATE_GATE',
    'presentation': 'SURFACED_GROUP_ROUND_ROBIN_CANDIDATES_THEN_EXISTING_STOCK_GATE',
}
LIMITS = {
    **probe.AUTHORITY, 'creates_canonical_wake': False, 'events_created': 0,
    'market_state_writes': 0, 'automatic_research_routing': False,
    'recommendation': None, 'independent_forecast_count': None,
    'business_benefit_established': False,
}
STATUS_LABELS = {
    'STOCKS_FOR_SHADOW_READING': '本范围有通过观察条件的股票',
    'PARTIAL_STOCKS_FOR_SHADOW_READING': '可用数据子集有通过观察条件的股票；另有隔离项',
    'NO_MATCH_IN_EVALUATED_SUBSET_WITH_DATA_GAPS': '已完成检查的子集没有匹配；其他股票数据不可用，不能判断',
    'NO_USABLE_STOCK_DATA': '计划内股票数据均不可用；不是完整检查后的零匹配',
    'NO_MATCH_WITHIN_REVIEWED_COMPANY_SCOPE': '资料完整，但本范围没有通过全部观察条件的股票',
    'NO_ACTIVE_DIRECTIONS': '当前没有满足既有行业门槛的方向',
    'BUSINESS_COVERAGE_INSUFFICIENT': '有活跃方向，但没有相应已接入公司依据',
    'NO_SURFACED_SECTOR_GROUPS': 'Sector 本轮没有进入首页有界组；未执行股票市场表达候选',
    'NO_MARKET_EXPRESSION_CANDIDATES': 'Sector 有界组没有可路由的 breadth leader 候选',
    'NO_MATCH_WITHIN_BOUNDED_MARKET_EXPRESSION_SCOPE': '本次有界市场表达候选没有通过全部价格观察条件',
    'DATA_INSUFFICIENT': '数据不足，不能形成合格股票名单',
    'DATA_QUALIFICATION_FAILED': '输入资格校验未通过，不能形成合格股票名单',
    'REQUEST_FAILED': '请求失败，本次检查未完成',
}


def _plain(value):
    return json.loads(canonical_json(value))


def _state_rows(state):
    return {r['thscode']: r for r in json.loads(serialize_sector_radar_market_state(state))['series']}


def _hash_ok(value, key):
    return value.get(key) == canonical_hash({k: v for k, v in value.items() if k != key})


def _reference_inputs(value):
    if value is None:
        return
    # Retained B normalized references are still TEST ONLY, never a real source.
    if (not isinstance(value, dict) or set(value) != {'provenance', 'windows', 'latest_quotes'}
            or value['provenance'] != SYNTHETIC_REFERENCES
            or not isinstance(value['windows'], dict) or not isinstance(value['latest_quotes'], dict)):
        raise ValueError('reference input is not an explicitly synthetic normalized fixture')


def _current_calendar_source_date(envelope, *, received_at):
    """Use an optional provider-ready clock only as same-day calendar coverage evidence.

    A current provider timestamp can prove that a trading-day list ending before
    the wall-clock date is this source's current response (for example, a closure
    or non-session date).  It never invents a session from weekday arithmetic.
    Missing timestamps preserve the older explicit-date coverage rule.
    """
    if not isinstance(received_at, datetime) or received_at.tzinfo is None or received_at.utcoffset() is None:
        raise ValueError('calendar receipt clock must be timezone-aware')
    data = envelope.get('data') if isinstance(envelope, dict) else None
    stamp = data.get('timestamp') if isinstance(data, dict) else None
    if stamp is None:
        return None
    if type(stamp) is not int:
        raise ValueError('calendar provider timestamp must be an exact integer millisecond clock')
    try:
        provider_ready_at = datetime.fromtimestamp(stamp / 1000, tz=SHANGHAI_TZ)
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError('calendar provider timestamp is invalid') from exc
    received_local = received_at.astimezone(SHANGHAI_TZ)
    if provider_ready_at > received_local:
        raise ValueError('calendar provider-ready time follows actual receipt')
    return provider_ready_at.date() if provider_ready_at.date() == received_local.date() else None


def check_observation_clock(state, at, *, calendar=None, calendar_source_date=None):
    """A real cutoff first; freshness only after this attempt's calendar arrives.

    Preparing a bounded plan is not qualification. The recorder/replayer calls
    this for actual timestamps; the selector supplies the retained calendar on
    every subsequent request/receipt and at final projection. Never rewrite at.
    """
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError('stock observation clock must be timezone-aware')
    close = datetime.combine(state.sessions[-1], time(15), tzinfo=SHANGHAI_TZ)
    if at < close:
        raise ValueError('saved stock context session is not completed at the observation clock')
    if calendar is not None:
        local_date = at.astimezone(SHANGHAI_TZ).date()
        if (not calendar or calendar != tuple(sorted(set(calendar)))
                or calendar[0] > state.sessions[0]
                or calendar[-1] < state.sessions[-1]
                or (calendar[-1] < local_date and calendar_source_date != local_date)):
            raise StockReadingInputError('DATA_INSUFFICIENT', 'STOCK_CALENDAR_COVERAGE_INSUFFICIENT')
        if tuple(d for d in calendar if state.sessions[0] <= d <= state.sessions[-1]) != tuple(state.sessions):
            raise StockReadingInputError('DATA_QUALIFICATION_FAILED', 'STOCK_CALENDAR_STATE_WINDOW_DIFFERS')
        if latest_completed_a_share_session(calendar, observed_at=at) != state.sessions[-1]:
            raise StockReadingInputError('DATA_INSUFFICIENT', 'STOCK_STATE_NOT_LATEST_COMPLETED_SESSION')
    return close


def _qualify_stock_index_snapshot(raw_snapshot, benchmark_history, calendar, *,
                                  observed_at, received_at):
    """Stock-only carry of the latest completed snapshot before opening auction.

    Shared index qualification remains strict. This exception is entered only
    when every earlier benchmark/calendar check passed and the sole rejection was
    that the provider data-ready date is today's later trading session. Exact
    response receipt is mandatory; waiting for a later request can never repair a
    future clock. 09:15 is a hard expiry, not an inferred market session.
    """
    if (not isinstance(received_at, datetime) or received_at.tzinfo is None
            or received_at.utcoffset() is None or not isinstance(observed_at, datetime)
            or observed_at.tzinfo is None or observed_at.utcoffset() is None):
        raise ValueError('index snapshot receipt and qualification clocks must be timezone-aware')
    provider_ready_at = datetime.fromtimestamp(
        raw_snapshot.provider_timestamp_ms / 1000, tz=SHANGHAI_TZ)
    received_local = received_at.astimezone(SHANGHAI_TZ)
    observed_local = observed_at.astimezone(SHANGHAI_TZ)
    if provider_ready_at > received_local or received_local > observed_local:
        raise ValueError('index snapshot provider-ready time follows actual receipt or observation clock')
    try:
        qualified = indices.qualify_hithink_index_snapshot(
            raw_snapshot, benchmark_history=benchmark_history,
            trading_sessions=calendar, observed_at=observed_at)
        return qualified, None
    except HithinkIndexAdapterError as exc:
        if str(exc) != _LATER_TRADING_DAY_SNAPSHOT_ERROR:
            raise
    ready_date = provider_ready_at.date()
    if (ready_date != received_local.date() or ready_date != observed_local.date()
            or ready_date not in set(calendar)
            or ready_date <= benchmark_history.response_session):
        raise ValueError('premarket index carry must be same-date on the later observed trading session')
    if (provider_ready_at.time() >= PREMARKET_CARRY_CUTOFF
            or received_local.time() >= PREMARKET_CARRY_CUTOFF
            or observed_local.time() >= PREMARKET_CARRY_CUTOFF):
        raise ValueError('premarket index snapshot carry expired at the 09:15 opening auction')
    if latest_completed_a_share_session(calendar, observed_at=observed_at) != benchmark_history.response_session:
        raise ValueError('premarket index carry cannot pass a newer completed session')
    qualified = HithinkQualifiedIndexSnapshotBatch(
        market_session=benchmark_history.response_session,
        benchmark_thscode=benchmark_history.thscode,
        provider_timestamp_ms=raw_snapshot.provider_timestamp_ms,
        qualification_method=HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
        points=raw_snapshot.points,
    )
    expires_at = datetime.combine(ready_date, PREMARKET_CARRY_CUTOFF, tzinfo=SHANGHAI_TZ)
    return qualified, expires_at


def prepare_stock_reading(source_root: Path, state, ledger, association: dict, *,
                          observed_at: datetime, company_manifest: str = COMPANY_MANIFEST) -> dict:
    """Freeze the whole reviewed scope before any stock history or compression."""
    check_observation_clock(state, observed_at)
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
    # Reserve history + explicit single-stock quote + action query for EVERY issuer.
    # Keep the old 26-call ceiling; an over-budget plan fails, not top-three truncates.
    request_count = 4 + len(directions) + 3*len(issuers) if issuers else 0
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
    return own_stock.history_params(code, sessions)


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
    """B's separate supplied-reference invariant, not a requirement to buy another API."""
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


def _stock_path(state, code, response, *, at, references=None, quote=None, actions=None,
                quote_received_at=None):
    expected = tuple(state.sessions[-61:])
    if references is None:
        by_day, checks = own_stock.qualify(response, quote, actions, code=code,
            sessions=state.sessions, params=_history_params(code,state.sessions), observed_at=at,
            quote_received_at=quote_received_at)
        closes = tuple(by_day[d]['close_price'] for d in expected)
    else:
        qualified = normalize_hithink_completed_price_history(
            response, thscode=code, sessions=state.sessions, observed_at=at)
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
        checks = {'contract':'SUPPLIED_SYNTHETIC_REFERENCES_ONLY',
                  'historical_daily_reference_check':'EXACT_SUPPLIED_TEST_REFERENCES_NOT_LIVE_ORIGIN_PROOF'}
    amounts = tuple(Decimal(str(by_day[d]['turnover'])) for d in expected)
    prior = _average(amounts[-25:-5])
    windows = checks.get('action_window_checks', {})
    def comparable(name):
        return references is not None or windows[name]['usable_for_raw_comparison']
    return {
        'last_close': closes[-1], 'previous_raw_close': closes[-2],
        'latest_volume': Decimal(str(by_day[expected[-1]]['volume'])), 'latest_turnover': amounts[-1],
        'daily_raw_return': closes[-1] / closes[-2] - 1,
        'returns': {str(n): (_return_over(closes, end_index=60, sessions=n)
                             if comparable(str(n)) else None) for n in (5, 20, 60)},
        'unavailable_price_metrics': [name for name, w in windows.items()
                                      if not w['usable_for_raw_comparison']],
        'turnover_pulse_5_vs_prior_20': _average(amounts[-5:]) / prior if prior else None,
        'twenty_day_return_five_sessions_ago': (_return_over(closes, end_index=55, sessions=20)
                                              if comparable('20_five_sessions_ago') else None),
        'price_convention': 'RAW_UNADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN',
        'corporate_action_adjustment': 'NOT_PERFORMED', 'tradability': 'NOT_CERTIFIED_BY_PRICE_AND_VOLUME',
        'reference_continuity': checks['historical_daily_reference_check'],
        'input_checks': checks, 'history_session_count': 61,
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


def _isolatable_stock_error(exc, code):
    if exc.thscode != code:
        return False
    if exc.category == 'REQUEST_FAILED':
        return (exc.reason_code == 'PROVIDER_BUSINESS_REQUEST_FAILED'
                and type(exc.provider_code) is int and exc.provider_code in _ISSUER_BUSINESS_CODES)
    return (exc.category in {'DATA_INSUFFICIENT', 'DATA_QUALIFICATION_FAILED'}
            and exc.reason_code in _ISSUER_DATA_REASONS)


def _coverage(rows):
    unavailable = [r for r in rows if r['input_failure'] is not None]
    if any(r['eligible_for_shadow_reading'] or r['stock_path'] is not None
           or r['excluded_reasons'] for r in unavailable):
        raise ValueError('isolated stock cannot be selected, priced or labelled conditions-not-met')
    return {
        'planned_issuers': len(rows), 'dispositioned_issuers': len(rows),
        'evaluated_issuers': len(rows)-len(unavailable),
        'price_path_checked_issuers': sum(r['stock_path'] is not None for r in rows),
        'qualified_issuers': sum(r['eligible_for_shadow_reading'] for r in rows),
        'conditions_not_met_issuers': sum(r['status'] == 'CONDITIONS_NOT_MET' for r in rows),
        'unavailable_issuers': len(unavailable), 'not_evaluated_issuers': 0,
        'scope_complete': not unavailable,
    }


def _partial_status(coverage, selected):
    if coverage['scope_complete']:
        return None
    return ('PARTIAL_STOCKS_FOR_SHADOW_READING' if selected else
            'NO_USABLE_STOCK_DATA' if not coverage['evaluated_issuers'] else
            'NO_MATCH_IN_EVALUATED_SUBSET_WITH_DATA_GAPS')


def _plan_contract(plan: dict):
    if plan.get('version') == VERSION:
        return SEMANTICS, POLICY, False
    if plan.get('version') == MARKET_EXPRESSION_VERSION:
        return MARKET_EXPRESSION_SEMANTICS, MARKET_EXPRESSION_POLICY, True
    return None


def observe_stock_reading(plan: dict, state, *, request_json, observed_at: datetime,
                          cutoff_clock=None, reference_inputs=None) -> dict:
    _reference_inputs(reference_inputs)
    with localcontext(Context(prec=28)):
        return _observe(plan, state, request_json=request_json, observed_at=observed_at,
                        cutoff_clock=cutoff_clock, reference_inputs=reference_inputs)


def _observe(plan, state, *, request_json, observed_at, cutoff_clock, reference_inputs):
    expected_requests = 4 + len(plan['directions']) + 3*len(plan['issuers']) if plan['issuers'] else 0
    if reference_inputs is not None:
        planned_codes = {r['thscode'] for r in plan['issuers']}
        if (set(reference_inputs['windows']) - planned_codes
                or set(reference_inputs['latest_quotes']) - planned_codes):
            raise ValueError('reference inputs contain unplanned stock identities')
    contract = _plan_contract(plan)
    if contract is None:
        raise ValueError('stock plan identity, policy, budget or authority differs')
    contract_semantics, contract_policy, is_market_expression = contract
    if (plan['policy'] != contract_policy or not _hash_ok(plan, 'plan_hash')
            or plan['market_state_hash'] != state.state_hash or plan['semantics'] != contract_semantics
            or any(plan[k] != v for k, v in LIMITS.items())
            or len(plan['issuers']) > MAX_ISSUERS or len(plan['directions']) > MAX_MEMBERSHIPS
            or expected_requests != plan['maximum_request_count'] or expected_requests > MAX_REQUESTS):
        raise ValueError('stock plan identity, policy, budget or authority differs')
    last = observed_at
    calendar = None
    calendar_source_date = None
    snapshot_valid_until = None
    def at():
        nonlocal last
        value = cutoff_clock() if cutoff_clock else observed_at
        check_observation_clock(state, value, calendar=calendar, calendar_source_date=calendar_source_date)
        if snapshot_valid_until is not None and value.astimezone(SHANGHAI_TZ) >= snapshot_valid_until:
            raise ValueError('premarket index snapshot carry expired at the 09:15 opening auction')
        if not probe._clock(plan['observed_at']) <= last <= value <= probe._clock(plan['observed_at']) + timedelta(minutes=30):
            raise ValueError('stock observation is outside its declared plan lifetime or clock reversed')
        last = value
        return value
    at()
    rows, memberships = [], {}
    state_rows = _state_rows(state)
    def get(path, params):
        at()
        value = request_json(path, params)
        received = at()
        # Do not misread a malformed authentication/rate-limit envelope as an
        # issuer-local schema failure. Unknown business status stops the batch.
        if not isinstance(value, dict) or type(value.get('code')) is not int:
            raise ValueError('provider business envelope is invalid; batch cannot continue')
        if value['code'] != 0:
            code = None
            if path in {STOCK_HISTORY, own_stock.SNAPSHOT, own_stock.ACTIONS}:
                code = params.get('thscode', params.get('thscodes'))
            raise StockReadingInputError('REQUEST_FAILED', 'PROVIDER_BUSINESS_REQUEST_FAILED',
                                         thscode=code, provider_code=value['code'])
        # Check readiness at the exact response receipt, before later requests.
        if reference_inputs is None:
            if path == STOCK_HISTORY:
                own_stock.check_history_receipt(value, code=params['thscode'], received_at=received)
            elif path == own_stock.SNAPSHOT:
                own_stock.check_quote_receipt(value, code=params['thscodes'], received_at=received)
        return value
    if plan['issuers']:
        raw_calendar = get(HITHINK_CALENDAR_PATH, {})
        calendar_received_at = last
        calendar_source_date = _current_calendar_source_date(raw_calendar, received_at=calendar_received_at)
        calendar = normalize_hithink_calendar(raw_calendar)
        at()  # Qualify exact dates plus optional same-day provider source clock before later requests.
        catalog = indices.fetch_hithink_industry_catalog(api_key='INJECTED', request_json=get)
        if catalog.catalog_hash != state.catalog_hash:
            raise ValueError('industry catalog changed; no name or proxy substitution')
        snapshot_received_at = None
        def snapshot_get(path, params):
            nonlocal snapshot_received_at
            value = get(path, params)
            snapshot_received_at = last
            return value
        raw_snapshot = indices.fetch_hithink_index_snapshot_batch(
            thscodes=tuple(sorted(state_rows)), api_key='INJECTED', request_json=snapshot_get)
        if snapshot_received_at is None:
            raise ValueError('index snapshot receipt was not bound to the exact response')
        benchmark_history = indices.fetch_hithink_completed_index_history(
            thscode=state.benchmark_thscode, observed_at=at(), api_key='INJECTED',
            request_json=get, trading_sessions=calendar)
        qualification_at = at()
        snapshot, snapshot_valid_until = _qualify_stock_index_snapshot(
            raw_snapshot, benchmark_history, calendar, observed_at=qualification_at,
            received_at=snapshot_received_at)
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
               'market_expression_status': 'NOT_ESTABLISHED',
               'business_linkage_status': issuer.get('business_linkage_status', 'REVIEWED_BUSINESS_LINK_PRESENT'),
               'business_benefit_status': issuer.get('business_benefit_status', 'NOT_ESTABLISHED'),
               'status': 'CONDITIONS_NOT_MET', 'input_failure': None}
        if not valid_origins:
            row['excluded_reasons'].append('NOT_A_CURRENT_MEMBER_OF_ROUTED_ACTIVE_DIRECTION' if is_market_expression
                                           else 'NOT_A_CURRENT_MEMBER_OF_REVIEWED_ACTIVE_DIRECTION')
            rows.append(row); continue
        name = identities[code].name
        row['current_member_name'] = name
        if re.match(r'^(?:\*?ST|[NC])', name) or '退' in name:
            row['excluded_reasons'].append('RISK_OR_NEW_LISTING_NAME_LABEL')
            rows.append(row); continue
        phase = 'HISTORY'
        try:
            response = get(STOCK_HISTORY, _history_params(code, state.sessions))
            quote = actions = quote_received_at = None
            if reference_inputs is None:
                phase = 'QUOTE'
                quote = get(own_stock.SNAPSHOT, {'thscodes':code})
                quote_received_at = last
                phase = 'CORPORATE_ACTIONS'
                actions = get(own_stock.ACTIONS, own_stock.action_params(code,state.sessions))
            phase = 'INPUT_QUALIFICATION'
            path = _stock_path(state, code, response, at=at(), references=reference_inputs,
                              quote=quote, actions=actions, quote_received_at=quote_received_at)
        except StockReadingInputError as exc:
            # Reference-fixture corruption, shared errors, clocks, credentials,
            # 429/4001 and unknown failures must never be hidden as stock gaps.
            if reference_inputs is not None or not _isolatable_stock_error(exc, code):
                raise
            row['status'] = exc.category
            row['input_failure'] = {
                'scope': 'ISSUER_LOCAL', 'category': exc.category,
                'reason_code': exc.reason_code, 'phase': phase,
                'provider_business_code': exc.provider_code,
                'selection_claim': 'NONE_DATA_UNAVAILABLE_NOT_CONDITIONS_NOT_MET',
            }
            rows.append(row)
            continue
        row['stock_path'] = path
        row['market_comparison'] = {n: {'stock_return': value, 'benchmark_return': bret[n],
            'excess_return': None if value is None else value - bret[n]} for n, value in path['returns'].items()}
        for origin in valid_origins:
            beat = False
            for sector in origin['current_member_sectors']:
                comparison = {'node_id': origin['node_id'], 'thscode': sector,
                    'name': plan['directions'][sector]['observation']['name'], 'horizons': {}}
                prices = tuple(Decimal(v) for v in state_rows[sector]['closes'])
                for n in (5, 20, 60):
                    ret = _return_over(prices, end_index=len(prices)-1, sessions=n)
                    comparison['horizons'][str(n)] = {'sector_return': ret,
                        'stock_excess_return': (None if path['returns'][str(n)] is None
                                                else path['returns'][str(n)] - ret)}
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
            reasons.append('TWENTY_DAY_PATH_DOES_NOT_BEAT_ANY_ROUTED_SECTOR' if is_market_expression
                           else 'TWENTY_DAY_PATH_DOES_NOT_BEAT_ANY_REVIEWED_SECTOR')
        row['eligible_for_shadow_reading'] = not reasons
        if is_market_expression and not reasons:
            row['market_expression_status'] = 'OBSERVED'
        row['status'] = ('QUALIFIED_SYNTHETIC_READING' if reference_inputs is not None else
                         'CONTRACT_CHECKED_RAW_READING') if not reasons else 'CONDITIONS_NOT_MET'
        rows.append(row)
    rows = _plain(rows)
    coverage = _coverage(rows)
    selected = _select(rows, plan['node_order'])
    reviewed_codes = {r['thscode'] for r in (plan['evidence_scope_issuers'] if is_market_expression else plan['issuers'])}
    if is_market_expression:
        complete_status = ('STOCKS_FOR_SHADOW_READING' if selected else
            'NO_SURFACED_SECTOR_GROUPS' if not plan['candidate_source_group_count'] else
            'NO_MARKET_EXPRESSION_CANDIDATES' if not plan['issuers'] else
            'NO_MATCH_WITHIN_BOUNDED_MARKET_EXPRESSION_SCOPE')
    else:
        complete_status = ('STOCKS_FOR_SHADOW_READING' if selected else
            'NO_ACTIVE_DIRECTIONS' if not plan['all_active_direction_count'] else
            'BUSINESS_COVERAGE_INSUFFICIENT' if not plan['issuers'] else
            'NO_MATCH_WITHIN_REVIEWED_COMPANY_SCOPE')
    status = _partial_status(coverage, selected) or complete_status
    payload = {
        'version': plan['version'], 'semantics': plan['semantics'], 'policy': plan['policy'], 'plan_hash': plan['plan_hash'],
        'market_session': state.sessions[-1], 'observed_at': at(), 'status': status,
        'scope': plan.get('reading_scope', plan['reviewed_company_coverage']),
        'reviewed_issuers': (sum(r.get('business_linkage_status') == 'REVIEWED_BUSINESS_LINK_PRESENT' for r in plan['issuers'])
                             if is_market_expression else len(plan['issuers'])),
        'coverage': coverage, 'selection_scope_complete': coverage['scope_complete'],
        'evidence_scope_issuers': plan['evidence_scope_issuers'],
        'active_directions_without_stock_business_scope': plan['active_directions_without_stock_business_scope'],
        'recorded_sector_events_latest_session': plan['recorded_sector_events_latest_session'],
        'source_event_status': ('RECORDED_SECTOR_EVENTS_PRESENT' if plan['recorded_sector_events_latest_session']
                                else 'NO_NEW_RECORDED_SECTOR_EVENT_NOT_NO_STOCK_OPPORTUNITY'),
        'fresh_context_revalidated': bool(plan['issuers']),
        'reference_input_provenance': reference_inputs['provenance'] if reference_inputs else HITHINK_RAW,
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
        **({'sector_result_hash': plan['sector_result_hash'],
            'candidate_source_group_count': plan['candidate_source_group_count'],
            'candidate_routing': plan['candidate_routing']} if is_market_expression else {}),
    }
    return _plain({'projection': payload, 'projection_hash': canonical_hash(payload)})


def render_stock_reading(report: dict) -> str:
    p = report['projection']
    codes = [r['thscode'] for r in p['surfaced_stocks']]
    coverage = _coverage(p['all_stock_observations'])
    partial_status = _partial_status(coverage, codes)
    if (report['projection_hash'] != canonical_hash(p) or p['semantics'] != SEMANTICS
            or p['policy'] != POLICY or any(p[k] != v for k, v in LIMITS.items())
            or len(codes) > 3 or len(codes) != len(set(codes))
            or p['status'] not in STATUS_LABELS
            or (partial_status is not None and p['status'] != partial_status)
            or (partial_status is None and p['status'] in {
                'PARTIAL_STOCKS_FOR_SHADOW_READING', 'NO_USABLE_STOCK_DATA',
                'NO_MATCH_IN_EVALUATED_SUBSET_WITH_DATA_GAPS'})
            or p['coverage'] != coverage or p['reviewed_issuers'] != coverage['planned_issuers']
            or p['selection_scope_complete'] != coverage['scope_complete']
            or any(r['input_failure'] is not None or not r['eligible_for_shadow_reading']
                   or r not in p['all_stock_observations'] for r in p['surfaced_stocks'])
            or (codes and p['reference_input_provenance'] not in {SYNTHETIC_REFERENCES,HITHINK_RAW})):
        raise ValueError('stock reading identity or authority differs')
    e = lambda x: escape(str(x), quote=True)
    pct = lambda x: '不可比（跨公司行为）' if x is None else f'{Decimal(x)*100:+.2f}%'
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">',
        '<title>股票观察 · Radar</title><style>body{font:16px/1.65 system-ui;margin:0;background:#f4f6f8;color:#20313d}main{max-width:980px;margin:auto;padding:24px}header,article,section{background:white;margin:16px 0;padding:24px;border:1px solid #dce3e7;border-radius:10px}h1{font-size:28px}h2{font-size:23px}.notice{padding:12px;background:#fff4d9}small{color:#52636f}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:right}p,code,pre,a{overflow-wrap:anywhere}pre{white-space:pre-wrap;font-size:12px;max-height:360px;overflow:auto}summary{cursor:pointer;padding:10px 0}.scroll{overflow:auto}@media(max-width:600px){main{padding:10px}header,article,section{padding:15px}}</style>',
        '<main><header><h1>股票观察 · 可以展开看的对象</h1>',
        f'<p><strong>{len(codes)} 只通过本版观察条件</strong>；行情交易日 {e(p["market_session"])}；读取截止 {e(p["observed_at"])}</p>',
        '<p class="notice">值得看不等于值得买。按需打开的 shadow 页面，不是买入建议或 canonical Inbox 推送；不是全 A 股盲选。</p>',
        f'<p>已接入依据的公司：{e("、".join(r["company_name"]+" "+r["thscode"] for r in p["evidence_scope_issuers"]))}。本次活跃方向内计划审阅 {p["reviewed_issuers"]} 只；未接入业务依据的所查成员 {len(p["unreviewed_current_members"])} 只。</p>',
        f'<p>来源事件：{p["recorded_sector_events_latest_session"]} 个已记录行业事件；没有新事件不等于没有仍强势路径。本层不生成事件。</p></header>',
        f'<section><h2>{e(STATUS_LABELS[p["status"]])}</h2><p>计划 {coverage["planned_issuers"]} 只；已完成条件检查 {coverage["evaluated_issuers"]} 只；其中61日数据及筛选窗口已核验 {coverage["price_path_checked_issuers"]} 只；条件不满足 {coverage["conditions_not_met_issuers"]} 只；数据不可用 {coverage["unavailable_issuers"]} 只；未处理 {coverage["not_evaluated_issuers"]} 只。</p>']
    if not coverage['scope_complete']:
        parts.append('<p class="notice">部分股票已隔离，其他股票继续按原条件检查。下面的结果只代表可用数据子集，不是全计划排名或完整零匹配；被隔离股票仍计入计划分母，不能视为条件不满足。</p>')
    parts.append('</section>')
    if p['reference_input_provenance'] == SYNTHETIC_REFERENCES:
        parts.append('<p class="notice">SYNTHETIC_TEST_ONLY：合成行情及参考价验收样本，不是真实程序选股；不能用作市场判断。</p>')
    if not codes:
        parts.append('<section><h2>本次没有可展示的合格卡片</h2><p>不等于市场没有机会。覆盖缺口、条件不满足与数据不足分别记录；数据不足的尝试不会生成成功空名单。</p></section>')
    for row in p['surfaced_stocks']:
        path = row['stock_path']
        parts += [f'<article><h2>{e(row["company_name"])} <small>{e(row["thscode"])}</small></h2>',
            '<p><strong>为什么值得进一步看：</strong>当前有关联的强势方向及留存业务依据；个股5日上涨并跑赢基准，20日跑赢基准及至少一个相关行业。只是固定试行观察条件，未证明投资价值。</p>',
            f'<p>原始收盘价 <strong>{e(path["last_close"])} CNY</strong>；当日原始价格变化 {pct(path["daily_raw_return"])}。</p>',
            '<div class="scroll"><table><tr><th>窗口</th><th>个股原始价格变化</th><th>沪深300价格变化</th><th>变化率差</th></tr>']
        for n in ('5', '20', '60'):
            values = row['market_comparison'][n]
            parts.append('<tr>'+''.join(f'<td>{e(v)}</td>' for v in (n+'日',pct(values['stock_return']),pct(values['benchmark_return']),pct(values['excess_return'])))+'</tr>')
        parts += ['</table></div><p><small>61个完成交易日；未复权原始价格变化，非含分红总回报；60日不参与门槛，跨已报告公司行为时不计算其比较值。当前成员不倒灌历史。</small></p>']
        if p['reference_input_provenance'] == HITHINK_RAW:
            parts.append('<p class="notice">本版仅原始收盘价路径观察：价格、前收及成交量严格核对，成交额使用明示容差；公司行为查询成功且5/20日筛选区间未跨已报告事件。更早事件保留，受影响的60日或移位窗口不提供比较值。事件接口未报告不等于所有公司行为已被独立排除；没有逐日历史前收核验，不声称复权表现或投资者总回报。</p>')
            checks = path['input_checks']
            amount = checks['turnover_reconciliation']
            parts.append(f'<p>成交额核对：历史 {e(amount["historical_cny"])} 元；快照 {e(amount["snapshot_cny"])} 元；差额 {e(amount["absolute_difference_cny"])} 元，允许上限 {e(amount["allowed_difference_cny"])} 元。计算仍使用历史原值；不是供应商精度保证。</p>')
            for event in checks['reported_corporate_actions']:
                parts.append(f'<p class="notice">已报告公司行为：{e(event["ex_date"])}，每股现金 {e(event["dividend_per_share"])}，每股送转 {e(event["per_share_bonus"])}。事件未隐去；未自动复权。</p>')
            parts += ['<details><summary>金额容差与各价格窗口的公司行为检查</summary><pre>',
                      e(canonical_json({'turnover': amount, 'windows': checks['action_window_checks']})),
                      '</pre></details>']
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
    if coverage['unavailable_issuers']:
        parts.append('<section><h2>数据不可用的股票 · 不进入合格名单</h2><div class="scroll"><table><tr><th>公司</th><th>阶段</th><th>原因</th><th>业务码</th></tr>')
        for row in p['all_stock_observations']:
            failure = row['input_failure']
            if failure is not None:
                values = (row['company_name']+' '+row['thscode'], failure['phase'],
                          failure['reason_code'], failure['provider_business_code'])
                parts.append('<tr>'+''.join('<td>'+e(v)+'</td>' for v in values)+'</tr>')
        parts.append('</table></div><p>原始响应和精确请求保留在附件；没有删除证券身份、填补价格或伪造无公司行为；只有成交额使用明示的有界容差，其他关键字段仍严格检查。</p></section>')
    parts += ['<section><h2>完整范围与未选中原因</h2><details><summary>全部公司、未覆盖成员及合格但未展示项</summary><pre>',
              e(canonical_json({k:p[k] for k in ('coverage','all_stock_observations','unreviewed_current_members','omitted_eligible_stock_codes','active_directions_without_stock_business_scope')})),
              '</pre></details><p>固定条件尚未经过前瞻效果验证；最多3只只是阅读压缩，不是综合机会分数。</p>',
              '<a href="stock-reading.json">完整结构化结果</a></section>',
              '<footer>SHADOW OBSERVATION ONLY · HUMAN ATTENTION AUTHORITY = NONE · RESEARCH AUTHORITY = NONE · INVESTMENT AUTHORITY = NONE</footer></main></html>']
    return '\n'.join(parts)+'\n'
