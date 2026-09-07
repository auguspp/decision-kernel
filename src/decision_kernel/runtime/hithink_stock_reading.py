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
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Shanghai')
HISTORY = '/api/a-share/prices/historical'
SNAPSHOT = '/api/a-share/prices/snapshot'
ACTIONS = '/api/a-share/corporate-actions/adjustment-factors'
CONTRACT = 'hithink-own-61-raw-bars-receipt-bound-quote-and-reported-actions-v2'


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
    return {'thscode': code, 'from': sessions[-61].isoformat(), 'to': sessions[-1].isoformat()}


def qualify(history, quote, actions, *, code, sessions, params, observed_at,
            quote_received_at=None):
    """Check actual same-provider values without inventing 61 daily prev_price fields.

    A nonempty reported action window is conservatively blocked, not adjusted.
    Empty means no event REPORTED BY THIS PROVIDER, not exhaustive absence proof.
    The snapshot has no individual date: its values must exactly match the dated
    history, and its date is explicitly NOT independently certified.
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
            ('high_price','high_price'),('low_price','low_price'),('volume','volume'),('turnover','turnover')):
        if _number(last_quote, current, code) != last[historical]:
            _bad(code, 'CURRENT_QUOTE_HISTORY_MISMATCH')
    if _number(last_quote, 'prev_price', code, positive=True) != bars[expected[-2]]['close_price']:
        _bad(code, 'PRICE_REFERENCE_DISCONTINUITY_REQUIRES_SEPARATE_REVIEW')
    event_data = _data(actions, code)
    if event_data.get('thscode') != code or event_data.get('ticker') != code[:6]:
        _bad(code)
    events = event_data.get('item')
    if not isinstance(events, list) or len(events) > 256:
        _bad(code)
    dates = []
    for event in events:
        if not isinstance(event, dict) or event.get('ticker') != code[:6]:
            _bad(code)
        key = _instant(event.get('ex_date_ms'), code)
        if key.time() != time() or key.date() not in expected:
            _bad(code)
        dates.append(key)
        _number(event, 'dividend_per_share', code)
        _number(event, 'per_share_bonus', code)
    if dates != sorted(dates, reverse=True):
        _bad(code)
    if events:
        _bad(code, 'REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW')
    return bars, {
        'contract': CONTRACT,
        'history_identity_basis': 'EXPLICIT_SINGLE_STOCK_REQUEST_OPTIONAL_ECHO_CHECKED',
        'history_request': dict(params), 'history_provider_ready_at': ready.isoformat(),
        'market_session_basis': 'EXACT_61_COMPLETED_DATED_OWN_BARS_AND_QUALIFIED_CALENDAR',
        'latest_quote_check': 'EXACT_OHLC_VOLUME_TURNOVER_AND_PREVIOUS_RAW_CLOSE_MATCH',
        'snapshot_individual_trade_date': 'NOT_SUPPLIED_NOT_INFERRED_FROM_READY_CLOCK',
        'quote_ready_time_check': 'NULL_OR_NOT_AFTER_EXACT_QUOTE_RECEIPT',
        'quote_provider_ready_at': None if q['timestamp'] is None else _instant(q['timestamp'], code).isoformat(),
        # Captures serialize actual clocks in UTC; equivalent offset inputs must
        # regenerate identical metadata rather than preserve a caller's spelling.
        'quote_received_at': None if quote_received_at is None else quote_received_at.astimezone(timezone.utc).isoformat(),
        'corporate_actions': 'NONE_REPORTED_IN_REQUESTED_WINDOW_NOT_EXHAUSTIVE_ABSENCE_PROOF',
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
           SNAPSHOT: {'thscodes'}, ACTIONS: {'thscode','from','to'}}
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
