"""HiThink-only raw stock observation inputs; no second selector or total-return claim.

The frozen caller supplies an independently checked calendar/state and records
all requests and receipts. History identity is bound to the explicit single-code
request when the documented response omits echoes; contradictory echoes fail.
Provider ready clocks are never substituted for individual bar dates.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation, Context, localcontext
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Shanghai')
HISTORY = '/api/a-share/prices/historical'
SNAPSHOT = '/api/a-share/prices/snapshot'
ACTIONS = '/api/a-share/corporate-actions/adjustment-factors'
CONTRACT = 'hithink-own-61-bars-history-actions-through-session-v4'
MAX_ACTION_EVENTS = 256  # The existing event-row ceiling; do not page or truncate.
# Project reconciliation policy, not HiThink precision or a supplier guarantee.
# PEP 485 symmetric relative/absolute comparison, with an extra CNY hard cap.
TURNOVER_POLICY = {
    'version': 'stock-snapshot-turnover-cny-v1',
    'relative_tolerance': '0.0000001', 'absolute_tolerance_cny': '0.01',
    'hard_cap_cny': '100', 'calculation_source': 'DATED_HISTORY_UNCHANGED',
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
    """Accept null or an actual upstream-ready timestamp, never a trade-date claim.

    The website prices contract allows a non-null latest upstream timestamp even
    though the older repository contract describes null for explicit thscodes.
    Validate it against THIS response's receipt before the action request; a later
    response must not make a future timestamp retroactively valid.
    """
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


def history_params(code, sessions):
    start = datetime.combine(sessions[-61], time(), TZ)
    end = datetime.combine(sessions[-1] + timedelta(days=1), time(), TZ)
    return {'thscode': code, 'interval': '1d', 'adjust': 'none',
            'start': str(int(start.timestamp()*1000)), 'end': str(int(end.timestamp()*1000))}


def action_params(code, sessions):
    """One documented history query, clipped at the exact completed session.

    HiThink makes from/to optional and documents omitted-from history retrieval.
    Do not first request a short window and then retry/widen after a 3002. Every
    planned issuer uses this same initial query, with the original request budget.
    A successful response remains required; no error-to-empty conversion exists.
    """
    return {'thscode': code, 'to': sessions[-1].isoformat()}


def reconcile_turnover(historical, snapshot, *, code):
    """A narrow field-only tolerance; never round, replace or fill source values."""
    a = _number({'turnover': historical}, 'turnover', code, positive=True)
    b = _number({'turnover': snapshot}, 'turnover', code, positive=True)
    # Independent of the caller's Decimal context. Inputs have <=28 digits and
    # exponent magnitude <=12, so this also preserves the boundary subtraction.
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


def action_window_checks(expected, dates):
    """The ex-date affects an interval only after its base CLOSE: (base, end].

    These are checks of reported events, not proof of exhaustive event coverage.
    No adjustment formula, inferred no-event response or issuer-specific exception.
    """
    windows = {str(n): (expected[-n-1], expected[-1]) for n in (1,5,20,60)}
    windows['20_five_sessions_ago'] = (expected[-26], expected[-6])
    result = {}
    for name,(base,end) in windows.items():
        crossing = [d.date().isoformat() for d in dates if base < d.date() <= end]
        result[name] = {'base_session': base.isoformat(), 'end_session': end.isoformat(),
                        'boundary': 'BASE_CLOSE_EXCLUSIVE_END_CLOSE_INCLUSIVE',
                        'reported_event_dates': crossing,
                        'status': ('REPORTED_ACTION_CROSSES_RAW_WINDOW' if crossing else
                                   'NO_REPORTED_ACTION_CROSSES_RAW_WINDOW'),
                        'usable_for_raw_comparison': not crossing,
                        'is_selection_window': name in {'5','20'}}
    return result


def qualify(history, quote, actions, *, code, sessions, params, observed_at,
            quote_received_at=None):
    """Check actual same-provider values without inventing 61 daily prev_price fields.

    Require a successful, validated action response. Reported events block only
    the selection intervals they cross; affected context intervals are unavailable.
    Empty means no event REPORTED BY THIS PROVIDER, not exhaustive absence proof.
    The snapshot has no individual date: OHLC/volume/previous close remain exact,
    turnover alone has a bounded policy, and trade date is not independently certified.
    """
    if not isinstance(code, str) or not re.fullmatch(r'\d{6}\.(SH|SZ|BJ)', code):
        _bad(code)
    expected = tuple(sessions[-61:])
    if (len(expected) != 61 or expected != tuple(sorted(set(expected)))
            or params != history_params(code, sessions)):
        _bad(code, 'EXACT_61_COMPLETED_STOCK_SESSIONS_REQUIRED', 'DATA_INSUFFICIENT')
    if (not isinstance(observed_at, datetime) or observed_at.tzinfo is None
            or observed_at.utcoffset() is None
            or observed_at < datetime.combine(expected[-1], time(15), TZ)):
        _bad(code)
    d = _data(history, code)
    # These are optional echoes in the real contract, not missing price fields.
    for key, value in (('thscode', code), ('interval', '1d'), ('adjust', 'none')):
        if key in d and d[key] != value:
            _bad(code)
    if 'timestamp' not in d:
        _bad(code, 'REQUIRED_INPUT_OR_FIELD_MISSING', 'DATA_INSUFFICIENT')
    ready = _instant(d['timestamp'], code)
    if not datetime.combine(expected[-1], time(), TZ) <= ready <= observed_at:
        _bad(code)
    items = d.get('item')
    if not isinstance(items, list) or len(items) != 61:
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
    last = bars[expected[-1]]
    for current, historical in (('last_price','close_price'),('open_price','open_price'),
            ('high_price','high_price'),('low_price','low_price'),('volume','volume')):
        if _number(last_quote, current, code) != last[historical]:
            _bad(code, 'CURRENT_QUOTE_HISTORY_MISMATCH')
    turnover_check = reconcile_turnover(str(last['turnover']), last_quote.get('turnover'), code=code)
    if _number(last_quote, 'prev_price', code, positive=True) != bars[expected[-2]]['close_price']:
        _bad(code, 'PRICE_REFERENCE_DISCONTINUITY_REQUIRES_SEPARATE_REVIEW')
    event_data = _data(actions, code)
    if event_data.get('thscode') != code or event_data.get('ticker') != code[:6]:
        _bad(code)
    events = event_data.get('item')
    if not isinstance(events, list) or len(events) > MAX_ACTION_EVENTS:
        _bad(code)
    # The documented event endpoint is not paginated. A newly exposed partial
    # response cannot support window exclusions; stop this issuer, never follow
    # cursors, raise the budget, or treat a retained prefix as the whole response.
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
        # Earlier history is permitted, but never used to invent trading sessions.
        # Inside the retained price calendar, the original session check stays strict.
        if key.date() >= expected[0] and key.date() not in expected:
            _bad(code)
        dates.append(key)
        cash = _number(event, 'dividend_per_share', code)
        bonus = _number(event, 'per_share_bonus', code)
        retained_events.append({'ticker': code[:6], 'ex_date': key.date().isoformat(),
                                'dividend_per_share': str(cash), 'per_share_bonus': str(bonus)})
    if dates != sorted(set(dates), reverse=True):
        _bad(code)
    window_checks = action_window_checks(expected, dates)
    if any(not window_checks[str(n)]['usable_for_raw_comparison'] for n in SELECTION_WINDOWS):
        _bad(code, 'REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW')
    return bars, {
        'contract': CONTRACT,
        'history_identity_basis': 'EXPLICIT_SINGLE_STOCK_REQUEST_OPTIONAL_ECHO_CHECKED',
        'history_request': dict(params), 'history_provider_ready_at': ready.isoformat(),
        'market_session_basis': 'EXACT_61_COMPLETED_DATED_OWN_BARS_AND_QUALIFIED_CALENDAR',
        'latest_quote_check': 'EXACT_OHLC_VOLUME_PREVIOUS_CLOSE_WITH_BOUNDED_TURNOVER_TOLERANCE',
        'turnover_reconciliation': turnover_check,
        'snapshot_individual_trade_date': 'NOT_SUPPLIED_NOT_INFERRED_FROM_READY_CLOCK',
        'quote_ready_time_check': 'NULL_OR_NOT_AFTER_EXACT_QUOTE_RECEIPT',
        'quote_provider_ready_at': None if q['timestamp'] is None else _instant(q['timestamp'], code).isoformat(),
        # Captures serialize actual clocks in UTC; equivalent offset inputs must
        # regenerate identical metadata rather than preserve a caller's spelling.
        'quote_received_at': None if quote_received_at is None else quote_received_at.astimezone(timezone.utc).isoformat(),
        'corporate_actions': ('REPORTED_ACTIONS_OUTSIDE_SELECTION_WINDOWS_NOT_EXHAUSTIVE_ABSENCE_PROOF'
                              if events else 'NONE_REPORTED_IN_REQUESTED_WINDOW_NOT_EXHAUSTIVE_ABSENCE_PROOF'),
        'reported_corporate_actions': retained_events, 'action_window_checks': window_checks,
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
        'historical_daily_reference_check': 'NOT_AVAILABLE_NOT_REQUIRED_FOR_RAW_CLOSE_RATIOS',
        'adjustment_or_total_return_qualification': 'NOT_ESTABLISHED',
    }


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
    if path in own:
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
