"""HiThink-only raw stock observation inputs; no second selector or total-return claim.

The frozen caller supplies an independently checked calendar/state and records
all requests and receipts. History identity is bound to the explicit single-code
request when the documented response omits echoes; contradictory echoes fail.
Provider ready clocks are never substituted for individual bar dates.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, Context, localcontext
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Shanghai')
HISTORY = '/api/a-share/prices/historical'
SNAPSHOT = '/api/a-share/prices/snapshot'
ACTIONS = '/api/a-share/corporate-actions/adjustment-factors'
# The request/source identity stays the existing v4 contract for every caller.
# Stock Market Expression applies an additional bounded qualification policy on
# top of those same bytes; it is recorded separately and is not a new provider
# or acquisition contract. SELECTION_CONTRACT remains a source-identity alias so
# existing callers cannot accidentally reinterpret the acquisition bytes.
CONTRACT = 'hithink-own-61-bars-history-actions-through-session-v4'
SELECTION_CONTRACT = CONTRACT
SELECTION_QUALIFICATION_CONTRACT = 'hithink-selection-window-qualified-history-actions-v6'
MAX_ACTION_EVENTS = 256  # The existing event-row ceiling; do not page or truncate.
REQUIRED_RECENT_SESSIONS = 26  # Covers 20d gate, shifted 20d and turnover pulse.
# Project reconciliation policies, not HiThink precision or supplier guarantees.
TURNOVER_POLICY = {
    'version': 'stock-snapshot-turnover-cny-v1',
    'relative_tolerance': '0.0000001', 'absolute_tolerance_cny': '0.01',
    'hard_cap_cny': '100', 'calculation_source': 'DATED_HISTORY_UNCHANGED',
    'supplier_precision_rule_established': False,
}
VOLUME_POLICY = {
    'version': 'stock-snapshot-volume-shares-v1',
    'relative_tolerance': '0.00000001', 'absolute_tolerance_shares': '2',
    'hard_cap_shares': '10', 'calculation_source': 'DATED_HISTORY_UNCHANGED',
    'supplier_precision_rule_established': False,
}
SELECTION_WINDOWS = (5, 20)


class StockReadingInputError(ValueError):
    """Finite diagnostic codes only; never echo provider text or credentials."""
    def __init__(self, category, reason_code, *, thscode=None, provider_code=None):
        self.category, self.reason_code, self.thscode = category, reason_code, thscode
        self.provider_code = provider_code
        super().__init__(reason_code)


def _bad(code, reason='INPUT_CLOCK_IDENTITY_OR_SCHEMA_REJECTED', category='DATA_QUALIFICATION_FAILED'):
    raise StockReadingInputError(category, reason, thscode=code)


def _data(value, code):
    if not isinstance(value, dict) or type(value.get('code')) is not int:
        _bad(code)
    if value['code'] != 0:
        _bad(code, 'PROVIDER_BUSINESS_REQUEST_FAILED', 'REQUEST_FAILED')
    if not isinstance(value.get('data'), dict):
        _bad(code, 'REQUIRED_INPUT_OR_FIELD_MISSING', 'DATA_INSUFFICIENT')
    return value['data']


def _number(row, field, code, *, positive=False):
    value = row.get(field)
    if value is None:
        _bad(code, 'REQUIRED_INPUT_OR_FIELD_MISSING', 'DATA_INSUFFICIENT')
    if type(value) not in (str, int, float):
        _bad(code)
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        _bad(code)
    if not number.is_finite() or number < 0 or (positive and number == 0):
        _bad(code)
    if len(number.as_tuple().digits) > 28 or abs(number.as_tuple().exponent) > 12:
        _bad(code)
    return number


def _instant(value, code):
    if type(value) is not int or value <= 0:
        _bad(code)
    try:
        return datetime.fromtimestamp(value / 1000, tz=TZ)
    except (ValueError, OverflowError, OSError):
        _bad(code)


def check_history_receipt(history, *, code, received_at):
    """Check the actual history receipt before any subsequent market request."""
    data = _data(history, code)
    if (not isinstance(received_at, datetime) or received_at.tzinfo is None
            or received_at.utcoffset() is None):
        _bad(code)
    if 'timestamp' not in data:
        _bad(code, 'REQUIRED_INPUT_OR_FIELD_MISSING', 'DATA_INSUFFICIENT')
    if _instant(data['timestamp'], code) > received_at:
        _bad(code, 'HISTORY_READY_AFTER_ACTUAL_RECEIPT')


def check_quote_receipt(quote, *, code, received_at):
    """Accept null or an actual upstream-ready timestamp, never a trade-date claim."""
    data = _data(quote, code)
    if 'timestamp' not in data:
        _bad(code, 'REQUIRED_INPUT_OR_FIELD_MISSING', 'DATA_INSUFFICIENT')
    if data['timestamp'] is None:
        return
    if (not isinstance(received_at, datetime) or received_at.tzinfo is None
            or received_at.utcoffset() is None):
        _bad(code, 'QUOTE_ACTUAL_RECEIPT_REQUIRED')
    if _instant(data['timestamp'], code) > received_at:
        _bad(code, 'QUOTE_READY_AFTER_ACTUAL_RECEIPT')


def history_params(code, sessions, *, adjust='none'):
    if adjust not in {'none', 'forward'}:
        raise ValueError('stock history adjustment mode is outside the bounded contract')
    start = datetime.combine(sessions[-61], time(), TZ)
    # The observed endpoint can include a bar keyed exactly at `end`.
    # Stop INSIDE the cutoff day, not at the following day's midnight.
    # Never widen/retry after an issuer-local missing row.
    end = datetime.combine(sessions[-1] + timedelta(days=1), time(), TZ) - timedelta(milliseconds=1)
    return {'thscode': code, 'interval': '1d', 'adjust': adjust,
            'start': str(int(start.timestamp()*1000)), 'end': str(int(end.timestamp()*1000))}


def action_params(code, sessions):
    """One documented history query, clipped at the exact completed session."""
    return {'thscode': code, 'to': sessions[-1].isoformat()}


def reconcile_turnover(historical, snapshot, *, code):
    """A narrow field-only tolerance; never round, replace or fill source values."""
    a = _number({'turnover': historical}, 'turnover', code, positive=True)
    b = _number({'turnover': snapshot}, 'turnover', code, positive=True)
    with localcontext(Context(prec=64)):
        delta = abs(a-b)
        bound = min(Decimal(TURNOVER_POLICY['hard_cap_cny']),
                    max(Decimal(TURNOVER_POLICY['absolute_tolerance_cny']),
                        Decimal(TURNOVER_POLICY['relative_tolerance'])*max(a,b)))
        if delta > bound:
            _bad(code, 'CURRENT_QUOTE_HISTORY_MISMATCH')
        return {**TURNOVER_POLICY, 'historical_cny': str(a), 'snapshot_cny': str(b),
                'absolute_difference_cny': str(delta), 'allowed_difference_cny': str(bound),
                'status': 'EXACT' if a == b else 'WITHIN_EXPLICIT_TOLERANCE'}


def reconcile_volume(historical, snapshot, *, code):
    """Bound only tiny whole-share endpoint drift; never alter either source value."""
    a = _number({'volume': historical}, 'volume', code, positive=True)
    b = _number({'volume': snapshot}, 'volume', code, positive=True)
    if a != a.to_integral_value() or b != b.to_integral_value():
        _bad(code, 'CURRENT_QUOTE_HISTORY_MISMATCH')
    with localcontext(Context(prec=64)):
        delta = abs(a-b)
        bound = min(Decimal(VOLUME_POLICY['hard_cap_shares']),
                    max(Decimal(VOLUME_POLICY['absolute_tolerance_shares']),
                        Decimal(VOLUME_POLICY['relative_tolerance'])*max(a,b)))
        if delta > bound:
            _bad(code, 'CURRENT_QUOTE_HISTORY_MISMATCH')
        return {**VOLUME_POLICY, 'historical_shares': str(a), 'snapshot_shares': str(b),
                'absolute_difference_shares': str(delta), 'allowed_difference_shares': str(bound),
                'status': 'EXACT' if a == b else 'WITHIN_EXPLICIT_TOLERANCE'}


def history_window_checks(expected, bars):
    """Expose missing own bars without inventing a suspension/zero-trading reason."""
    windows = {str(n): (expected[-n-1], expected[-1]) for n in (1,5,20,60)}
    windows['20_five_sessions_ago'] = (expected[-26], expected[-6])
    present = set(bars)
    result = {}
    for name, (base, end) in windows.items():
        required = [d for d in expected if base <= d <= end]
        missing = [d.isoformat() for d in required if d not in present]
        result[name] = {
            'base_session': base.isoformat(), 'end_session': end.isoformat(),
            'required_market_sessions': len(required), 'missing_market_sessions': missing,
            'status': 'MARKET_SESSION_BAR_GAP' if missing else 'ALL_REQUIRED_MARKET_SESSION_BARS_PRESENT',
            'usable_for_raw_comparison': not missing,
            'is_selection_window': name in {'5','20'},
            'absence_reason': 'UNKNOWN_NOT_INFERRED_AS_SUSPENSION' if missing else None,
        }
    return result


def _qualify_history_payload(history, *, code, sessions, params, observed_at,
                             selection_mode, adjust):
    if type(selection_mode) is not bool:
        _bad(code)
    if not isinstance(code, str) or not re.fullmatch(r'\d{6}\.(SH|SZ|BJ)', code):
        _bad(code)
    expected = tuple(sessions[-61:])
    if (len(expected) != 61 or expected != tuple(sorted(set(expected)))
            or params != history_params(code, sessions, adjust=adjust)):
        _bad(code, 'EXACT_61_COMPLETED_STOCK_SESSIONS_REQUIRED', 'DATA_INSUFFICIENT')
    if (not isinstance(observed_at, datetime) or observed_at.tzinfo is None
            or observed_at.utcoffset() is None
            or observed_at < datetime.combine(expected[-1], time(15), TZ)):
        _bad(code)
    d = _data(history, code)
    for key, value in (('thscode', code), ('interval', '1d'), ('adjust', adjust)):
        if key in d and d[key] != value:
            _bad(code)
    if 'timestamp' not in d:
        _bad(code, 'REQUIRED_INPUT_OR_FIELD_MISSING', 'DATA_INSUFFICIENT')
    ready = _instant(d['timestamp'], code)
    if not datetime.combine(expected[-1], time(), TZ) <= ready <= observed_at:
        _bad(code)
    items = d.get('item')
    valid_count = isinstance(items, list) and ((1 <= len(items) <= 61) if selection_mode else len(items) == 61)
    if not valid_count:
        _bad(code, 'EXACT_61_COMPLETED_STOCK_SESSIONS_REQUIRED', 'DATA_INSUFFICIENT')
    bars = {}
    for row in items:
        if not isinstance(row, dict):
            _bad(code)
        day_key = _instant(row.get('date_ms'), code)
        day = day_key.date()
        if day_key.time() != time() or day not in expected or day in bars:
            _bad(code)
        if ('thscode' in row and row['thscode'] != code) or ('ticker' in row and row['ticker'] != code[:6]):
            _bad(code)
        values = {key: _number(row, key, code, positive=key.endswith('_price'))
                  for key in ('open_price','high_price','low_price','close_price','volume','turnover')}
        if (values['low_price'] > min(values['open_price'], values['close_price'])
                or values['high_price'] < max(values['open_price'], values['close_price'])):
            _bad(code)
        if values['volume'] <= 0 or values['turnover'] <= 0:
            _bad(code, 'UNPRICED_OR_NONTRADING_SESSION_IN_PATH', 'DATA_INSUFFICIENT')
        bars[day] = values
    missing = [day for day in expected if day not in bars]
    if not selection_mode and missing:
        _bad(code, 'EXACT_61_COMPLETED_STOCK_SESSIONS_REQUIRED', 'DATA_INSUFFICIENT')
    if selection_mode:
        required_missing = [day for day in expected[-REQUIRED_RECENT_SESSIONS:] if day not in bars]
        if required_missing:
            _bad(code, 'REQUIRED_SELECTION_WINDOW_STOCK_SESSIONS_MISSING', 'DATA_INSUFFICIENT')
        history_checks = history_window_checks(expected, bars)
    else:
        history_checks = None
    return expected, bars, missing, history_checks, ready


def _qualify_quote(quote, *, code, expected, raw_bars, quote_received_at, observed_at,
                   selection_mode, expected_previous_close):
    q = _data(quote, code)
    check_quote_receipt(quote, code=code, received_at=quote_received_at)
    if quote_received_at is not None:
        if (not isinstance(quote_received_at, datetime) or quote_received_at.tzinfo is None
                or quote_received_at.utcoffset() is None or quote_received_at > observed_at):
            _bad(code, 'QUOTE_ACTUAL_RECEIPT_REQUIRED')
    if not isinstance(q.get('item'), list) or len(q['item']) != 1:
        _bad(code)
    last_quote = q['item'][0]
    if not isinstance(last_quote, dict) or last_quote.get('thscode') != code or last_quote.get('ticker') != code[:6]:
        _bad(code)
    last = raw_bars[expected[-1]]
    exact_fields = [('last_price','close_price'),('open_price','open_price'),
                    ('high_price','high_price'),('low_price','low_price')]
    if not selection_mode:
        exact_fields.append(('volume','volume'))
    for current, historical in exact_fields:
        if _number(last_quote, current, code) != last[historical]:
            _bad(code, 'CURRENT_QUOTE_HISTORY_MISMATCH')
    volume_check = (reconcile_volume(str(last['volume']), last_quote.get('volume'), code=code)
                    if selection_mode else None)
    turnover_check = reconcile_turnover(str(last['turnover']), last_quote.get('turnover'), code=code)
    actual_previous = _number(last_quote, 'prev_price', code, positive=True)
    if actual_previous != expected_previous_close:
        _bad(code, 'PRICE_REFERENCE_DISCONTINUITY_REQUIRES_SEPARATE_REVIEW')
    return q, last_quote, volume_check, turnover_check, actual_previous


def _reported_action_adjustments(expected, bars, retained_events, *, code):
    position = {day: i for i, day in enumerate(expected)}
    result = {}
    for event in retained_events:
        day = date.fromisoformat(event['ex_date'])
        if day <= expected[0]:
            continue
        i = position.get(day)
        if i is None or i == 0 or expected[i-1] not in bars:
            result[day] = {'status': 'REFERENCE_INPUT_UNAVAILABLE', 'factor': None}
            continue
        previous = bars[expected[i-1]]['close_price']
        cash = Decimal(event['dividend_per_share'])
        bonus = Decimal(event['per_share_bonus'])
        if cash == 0 and bonus == 0:
            result[day] = {'status': 'UNSUPPORTED_ZERO_EFFECT_EVENT', 'factor': None}
            continue
        with localcontext(Context(prec=64)):
            numerator = previous - cash
            denominator = previous * (Decimal(1) + bonus)
            if numerator <= 0 or denominator <= 0:
                result[day] = {'status': 'INVALID_REFERENCE_ARITHMETIC', 'factor': None}
                continue
            factor = numerator / denominator
        result[day] = {
            'status': 'SUPPORTED_CASH_OR_BONUS_REFERENCE',
            'factor': str(factor),
            'previous_raw_close': str(previous),
            'dividend_per_share': str(cash),
            'per_share_bonus': str(bonus),
            'reference_price': str(previous * factor),
        }
    return result


def action_window_checks(expected, dates, adjustments=None):
    """The ex-date affects an interval only after its base CLOSE: (base, end].

    Raw close comparison remains separately identified. When the provider reports
    only supported cash/bonus fields, the same source rows may establish a bounded
    ex-rights reference factor for price comparison; this is not total return.
    """
    windows = {str(n): (expected[-n-1], expected[-1]) for n in (1,5,20,60)}
    windows['20_five_sessions_ago'] = (expected[-26], expected[-6])
    adjustments = adjustments or {}
    result = {}
    for name,(base,end) in windows.items():
        crossing_days = [d.date() for d in dates if base < d.date() <= end]
        crossing = [d.isoformat() for d in crossing_days]
        supported = all(adjustments.get(d, {}).get('factor') is not None for d in crossing_days)
        factor = Decimal(1)
        if supported:
            with localcontext(Context(prec=64)):
                for day in crossing_days:
                    factor *= Decimal(adjustments[day]['factor'])
        result[name] = {
            'base_session': base.isoformat(), 'end_session': end.isoformat(),
            'boundary': 'BASE_CLOSE_EXCLUSIVE_END_CLOSE_INCLUSIVE',
            'reported_event_dates': crossing,
            'status': ('REPORTED_ACTION_CROSSES_RAW_WINDOW' if crossing else
                       'NO_REPORTED_ACTION_CROSSES_RAW_WINDOW'),
            'usable_for_raw_comparison': not crossing,
            'usable_for_price_reference_adjusted_comparison': (not crossing or supported),
            'reference_adjustment_factor': str(factor) if (not crossing or supported) else None,
            'comparison_basis': ('RAW_UNADJUSTED' if not crossing else
                                 'REPORTED_ACTION_REFERENCE_ADJUSTED' if supported else
                                 'UNAVAILABLE_UNSUPPORTED_REPORTED_ACTION'),
            'is_selection_window': name in {'5','20'},
        }
    return result


def qualify(history, quote, actions, *, code, sessions, params, observed_at,
            quote_received_at=None, selection_mode=False):
    """Qualify one raw stock input under the shared source contract.

    Default is the pre-existing exact-61/exact-volume qualification used by shared
    consumers. `selection_mode=True` keeps raw source rows but can use a bounded
    provider-reported cash/bonus ex-rights reference for an affected comparison.
    It never manufactures an event, total-return series or successful empty action
    response.
    """
    expected, bars, missing, history_checks, ready = _qualify_history_payload(
        history, code=code, sessions=sessions, params=params, observed_at=observed_at,
        selection_mode=selection_mode, adjust='none')

    event_data = _data(actions, code)
    if event_data.get('thscode') != code or event_data.get('ticker') != code[:6]:
        _bad(code)
    events = event_data.get('item')
    if not isinstance(events, list) or len(events) > MAX_ACTION_EVENTS:
        _bad(code)
    if ('total' in event_data and (type(event_data['total']) is not int
                                   or event_data['total'] != len(events))):
        _bad(code, 'REQUIRED_INPUT_OR_FIELD_MISSING', 'DATA_INSUFFICIENT')
    for flag in ('has_more', 'has_next', 'truncated'):
        if flag in event_data and event_data[flag] is not False:
            _bad(code, 'REQUIRED_INPUT_OR_FIELD_MISSING', 'DATA_INSUFFICIENT')
    for cursor in ('next_cursor', 'next_page', 'next'):
        if cursor in event_data and event_data[cursor] not in (None, ''):
            _bad(code, 'REQUIRED_INPUT_OR_FIELD_MISSING', 'DATA_INSUFFICIENT')
    if (('from' in event_data and event_data['from'] not in (None, ''))
            or ('to' in event_data and event_data['to'] != expected[-1].isoformat())):
        _bad(code)
    dates, retained_events = [], []
    for event in events:
        if not isinstance(event, dict) or event.get('ticker') != code[:6]:
            _bad(code)
        key = _instant(event.get('ex_date_ms'), code)
        if key.time() != time() or key.date() > expected[-1]:
            _bad(code)
        if key.date() >= expected[0] and key.date() not in expected:
            _bad(code)
        dates.append(key)
        cash = _number(event, 'dividend_per_share', code)
        bonus = _number(event, 'per_share_bonus', code)
        retained_events.append({'ticker': code[:6], 'ex_date': key.date().isoformat(),
                                'dividend_per_share': str(cash), 'per_share_bonus': str(bonus)})
    if dates != sorted(set(dates), reverse=True):
        _bad(code)

    adjustments = _reported_action_adjustments(expected, bars, retained_events, code=code)
    window_checks = action_window_checks(expected, dates, adjustments)
    if selection_mode:
        if any(not window_checks[str(n)]['usable_for_price_reference_adjusted_comparison']
               for n in SELECTION_WINDOWS):
            _bad(code, 'REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW')
    elif any(not window_checks[str(n)]['usable_for_raw_comparison'] for n in SELECTION_WINDOWS):
        # Preserve the shared v4 acquisition contract outside Stock selection.
        _bad(code, 'REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW')

    latest_factor = Decimal(1)
    if selection_mode and expected[-1] in adjustments:
        item = adjustments[expected[-1]]
        if item['factor'] is None:
            _bad(code, 'REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW')
        latest_factor = Decimal(item['factor'])
    expected_previous = bars[expected[-2]]['close_price'] * latest_factor
    q, last_quote, volume_check, turnover_check, actual_previous = _qualify_quote(
        quote, code=code, expected=expected, raw_bars=bars,
        quote_received_at=quote_received_at, observed_at=observed_at,
        selection_mode=selection_mode, expected_previous_close=expected_previous)

    meta = {
        'contract': CONTRACT,
        'history_identity_basis': 'EXPLICIT_SINGLE_STOCK_REQUEST_OPTIONAL_ECHO_CHECKED',
        'history_request': dict(params), 'history_provider_ready_at': ready.isoformat(),
        'market_session_basis': ('LAST_26_REQUIRED_DATED_BARS_OLDER_GAPS_EXPLICIT_NOT_FILLED'
                                 if selection_mode else 'EXACT_61_COMPLETED_DATED_OWN_BARS_AND_QUALIFIED_CALENDAR'),
        'latest_quote_check': ('EXACT_OHLC_ACTION_AWARE_PREVIOUS_REFERENCE_WITH_BOUNDED_VOLUME_AND_TURNOVER_RECONCILIATION'
                               if selection_mode else 'EXACT_OHLC_VOLUME_ACTION_AWARE_PREVIOUS_REFERENCE_WITH_BOUNDED_TURNOVER_TOLERANCE'),
        'latest_quote_previous_reference': {
            'snapshot_prev_price': str(actual_previous),
            'expected_reference_price': str(expected_previous),
            'basis': ('REPORTED_ACTION_REFERENCE_ADJUSTED' if latest_factor != 1 else
                      'RAW_PREVIOUS_CLOSE'),
        },
        'turnover_reconciliation': turnover_check,
        'snapshot_individual_trade_date': 'NOT_SUPPLIED_NOT_INFERRED_FROM_READY_CLOCK',
        'quote_ready_time_check': 'NULL_OR_NOT_AFTER_EXACT_QUOTE_RECEIPT',
        'quote_provider_ready_at': None if q['timestamp'] is None else _instant(q['timestamp'], code).isoformat(),
        'quote_received_at': None if quote_received_at is None else quote_received_at.astimezone(timezone.utc).isoformat(),
        'corporate_actions': ('REPORTED_ACTIONS_OUTSIDE_OR_INSIDE_SELECTION_WINDOWS_REFERENCE_QUALIFIED'
                              if events else 'NONE_REPORTED_IN_REQUESTED_WINDOW_NOT_EXHAUSTIVE_ABSENCE_PROOF'),
        'reported_corporate_actions': retained_events,
        'reported_action_reference_adjustments': {
            d.isoformat(): value for d, value in sorted(adjustments.items())
        },
        'action_window_checks': window_checks,
        'corporate_action_query_succeeded': True,
        'corporate_action_query': {
            'scope': 'AVAILABLE_HISTORY_THROUGH_COMPLETED_SESSION',
            'expected_request': action_params(code, sessions),
            'response_event_count': len(events),
            'events_before_price_window': sum(d.date() < expected[0] for d in dates),
            'maximum_event_rows': MAX_ACTION_EVENTS,
            'older_event_session_qualification': 'NOT_ASSERTED_OUTSIDE_RETAINED_CALENDAR',
            'exhaustive_absence_proven': False,
        },
        'historical_daily_reference_check': 'NOT_AVAILABLE_NOT_REQUIRED_FOR_RAW_OR_REPORTED_ACTION_REFERENCE_PRICE_RATIOS',
        'adjustment_or_total_return_qualification': (
            'REPORTED_CASH_OR_BONUS_REFERENCE_ADJUSTMENT_NOT_TOTAL_RETURN'
            if any(value.get('factor') is not None for value in adjustments.values())
            else 'NOT_ESTABLISHED'),
    }
    if selection_mode:
        meta.update(
            selection_qualification_contract=SELECTION_QUALIFICATION_CONTRACT,
            history_bar_count=len(bars),
            history_market_session_gaps=[d.isoformat() for d in missing],
            history_gap_meaning='ABSENCE_REASON_UNKNOWN_NOT_INFERRED_AS_SUSPENSION_OR_ZERO_TRADING',
            history_window_checks=history_checks,
            volume_reconciliation=volume_check,
        )
    return bars, meta


def qualify_forward_adjusted_fallback(raw_history, adjusted_history, quote, *, code, sessions,
                                      raw_params, adjusted_params, observed_at,
                                      quote_received_at=None, provider_business_code=3002):
    """Qualify a provider-native forward-adjusted price path when action rows are unavailable.

    The original nonzero action response remains a source gap. This fallback does
    not relabel it as an empty event history and does not infer any event details.
    """
    if provider_business_code != 3002:
        _bad(code, 'PROVIDER_BUSINESS_REQUEST_FAILED', 'REQUEST_FAILED')
    expected, raw_bars, raw_missing, raw_checks, raw_ready = _qualify_history_payload(
        raw_history, code=code, sessions=sessions, params=raw_params, observed_at=observed_at,
        selection_mode=True, adjust='none')
    expected2, adjusted_bars, adjusted_missing, adjusted_checks, adjusted_ready = _qualify_history_payload(
        adjusted_history, code=code, sessions=sessions, params=adjusted_params,
        observed_at=observed_at, selection_mode=True, adjust='forward')
    if expected2 != expected or set(adjusted_bars) != set(raw_bars):
        _bad(code, 'REQUIRED_SELECTION_WINDOW_STOCK_SESSIONS_MISSING', 'DATA_INSUFFICIENT')
    last_raw = raw_bars[expected[-1]]
    last_adjusted = adjusted_bars[expected[-1]]
    for field in ('open_price','high_price','low_price','close_price'):
        if last_adjusted[field] != last_raw[field]:
            _bad(code, 'CURRENT_QUOTE_HISTORY_MISMATCH')
    q, last_quote, volume_check, turnover_check, actual_previous = _qualify_quote(
        quote, code=code, expected=expected, raw_bars=raw_bars,
        quote_received_at=quote_received_at, observed_at=observed_at, selection_mode=True,
        expected_previous_close=adjusted_bars[expected[-2]]['close_price'])
    meta = {
        'contract': CONTRACT,
        'selection_qualification_contract': SELECTION_QUALIFICATION_CONTRACT,
        'history_identity_basis': 'EXPLICIT_SINGLE_STOCK_REQUEST_OPTIONAL_ECHO_CHECKED',
        'history_request': dict(raw_params),
        'history_provider_ready_at': raw_ready.isoformat(),
        'history_bar_count': len(raw_bars),
        'history_market_session_gaps': [d.isoformat() for d in raw_missing],
        'history_gap_meaning': 'ABSENCE_REASON_UNKNOWN_NOT_INFERRED_AS_SUSPENSION_OR_ZERO_TRADING',
        'history_window_checks': raw_checks,
        'volume_reconciliation': volume_check,
        'turnover_reconciliation': turnover_check,
        'latest_quote_check': 'EXACT_RAW_OHLC_PROVIDER_FORWARD_PREVIOUS_REFERENCE_WITH_BOUNDED_VOLUME_AND_TURNOVER_RECONCILIATION',
        'latest_quote_previous_reference': {
            'snapshot_prev_price': str(actual_previous),
            'expected_reference_price': str(adjusted_bars[expected[-2]]['close_price']),
            'basis': 'PROVIDER_FORWARD_ADJUSTED_PREVIOUS_CLOSE',
        },
        'snapshot_individual_trade_date': 'NOT_SUPPLIED_NOT_INFERRED_FROM_READY_CLOCK',
        'quote_ready_time_check': 'NULL_OR_NOT_AFTER_EXACT_QUOTE_RECEIPT',
        'quote_provider_ready_at': None if q['timestamp'] is None else _instant(q['timestamp'], code).isoformat(),
        'quote_received_at': None if quote_received_at is None else quote_received_at.astimezone(timezone.utc).isoformat(),
        'corporate_actions': 'QUERY_UNAVAILABLE_PROVIDER_3002_NOT_INTERPRETED_AS_EMPTY',
        'reported_corporate_actions': [],
        'reported_action_reference_adjustments': {},
        'action_window_checks': None,
        'corporate_action_query_succeeded': False,
        'corporate_action_query': {
            'scope': 'AVAILABLE_HISTORY_THROUGH_COMPLETED_SESSION',
            'expected_request': action_params(code, sessions),
            'provider_business_code': provider_business_code,
            'exhaustive_absence_proven': False,
        },
        'adjusted_history_fallback': {
            'status': 'USED',
            'provider_business_code_that_triggered_fallback': provider_business_code,
            'request': dict(adjusted_params),
            'provider_ready_at': adjusted_ready.isoformat(),
            'history_bar_count': len(adjusted_bars),
            'history_market_session_gaps': [d.isoformat() for d in adjusted_missing],
            'history_window_checks': adjusted_checks,
            'adjustment_mode': 'forward',
            'event_details_inferred': False,
        },
        'historical_daily_reference_check': 'PROVIDER_FORWARD_ADJUSTED_HISTORY_USED_FOR_PRICE_COMPARISON',
        'adjustment_or_total_return_qualification': 'PROVIDER_FORWARD_PRICE_ADJUSTMENT_NOT_TOTAL_RETURN',
    }
    return raw_bars, adjusted_bars, meta


def request_json(path, params, *, api_key):
    """Reuse existing mature bounded HTTPS transport; no redirects or env credentials.

    This is specific to this finite stock workflow, not a generic client. The
    recorder preserves decoded JSON, not original wire bytes. Decimal lexemes are
    retained as strings so a binary-float round trip cannot invent price precision.
    """
    from .hithink_dump_trial import _session, _check_response, MAX_JSON_BYTES, DumpTrialError
    from .hithink_http import HITHINK_BASE_URL
    from .sector_radar_audit import _check_request
    from .judgment_timeline import _unique_object
    own = {HISTORY: {'thscode','interval','adjust','start','end'},
           SNAPSHOT: {'thscodes'}, ACTIONS: {'thscode','to'}}
    if path == SNAPSHOT and isinstance(params, dict) and set(params) == {'limit', 'offset'}:
        # Existing full-market endpoint, narrowly bounded for independent K3 capture.
        # 3 context + 14 pages + 9 own-stock requests is the existing ceiling of 26.
        if (params['limit'] != '500' or not isinstance(params['offset'], str)
                or not re.fullmatch(r'0|[1-9][0-9]*', params['offset'])
                or int(params['offset']) % 500 or int(params['offset']) > 6500):
            raise ValueError('stock full-market page request contract differs')
    elif path in own:
        if not isinstance(params, dict) or set(params) != own[path] or any(type(v) is not str for v in params.values()):
            raise ValueError('stock request contract differs')
        code = params.get('thscode', params.get('thscodes'))
        if not re.fullmatch(r'\d{6}\.(SH|SZ|BJ)', code):
            raise ValueError('stock requests require one explicit identity')
        if path == HISTORY and (params['adjust'] != 'none' or params['interval'] != '1d'):
            raise ValueError('stock reading is raw daily only')
    else:
        _check_request(path, params)
    def nonfinite(_):
        raise ValueError('nonfinite provider JSON')
    with _session() as session:
        with session.get(HITHINK_BASE_URL + path, params=params,
                headers={'X-api-key':api_key,'Accept':'application/json','Accept-Encoding':'identity'},
                timeout=(10,20), stream=True, allow_redirects=False) as response:
            length = _check_response(response)
            if length is not None and length > MAX_JSON_BYTES:
                raise DumpTrialError('JSON_BYTE_BUDGET_EXCEEDED')
            chunks, size = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > MAX_JSON_BYTES:
                    raise DumpTrialError('JSON_BYTE_BUDGET_EXCEEDED')
                chunks.append(chunk)
            if length is not None and size != length:
                raise DumpTrialError('JSON_LENGTH_MISMATCH')
    value = json.loads(b''.join(chunks).decode('utf-8'), object_pairs_hook=_unique_object,
                       parse_float=str, parse_constant=nonfinite)
    if not isinstance(value, dict):
        raise ValueError('provider JSON object required')
    return value