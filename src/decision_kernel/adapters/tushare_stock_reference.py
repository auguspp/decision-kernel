"""Tushare daily source-contract check, NOT a live-source authentication or selector.

Official contracts: tushare.pro/document/2?doc_id=27 and /document/1?doc_id=130.
Only source-returned close/pre_close are used. Volumes are shares after an exact
100 conversion, amounts CNY after 1000; after-hours fields remain separate.
No network, credentials, price fill, adjustment, market state or authority write.
A successful parse must NOT be passed off as the stock reader's live provenance.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from decimal import Context, Decimal, InvalidOperation, localcontext
from typing import Any
from zoneinfo import ZoneInfo

SEMANTICS = 'TUSHARE_DAILY_CONTRACT_CHECK_NOT_LIVE_QUALIFICATION'
REQUIRED_FIELDS = ('ts_code', 'trade_date', 'close', 'pre_close', 'vol', 'amount', 'ah_vol', 'ah_amount')
FIELDS = ','.join(REQUIRED_FIELDS)
TZ = ZoneInfo('Asia/Shanghai')
MAX_BYTES = 1024 * 1024
MAX_RESPONSE_ROWS = 61
MAX_LIFETIME = timedelta(minutes=30)


class TushareReferenceError(ValueError):
    """Finite diagnostics only: never echo a token, provider msg or arbitrary input."""
    def __init__(self, category: str, reason: str):
        self.category, self.reason = category, reason
        super().__init__(reason)


def _fail(category: str, reason: str) -> None:
    raise TushareReferenceError(category, reason)


def _window(thscode: str, sessions: Sequence[date]) -> tuple[date, ...]:
    if not isinstance(thscode, str) or not re.fullmatch(r'\d{6}\.(SH|SZ|BJ)', thscode):
        _fail('DATA_QUALIFICATION_FAILED', 'EXPLICIT_STOCK_IDENTITY_REQUIRED')
    days = tuple(sessions)
    if (len(days) != 61 or any(type(d) is not date for d in days)
            or days != tuple(sorted(set(days)))):
        _fail('DATA_INSUFFICIENT', 'EXACT_61_QUALIFIED_SESSIONS_REQUIRED')
    return days


def daily_request(thscode: str, sessions: Sequence[date]) -> dict[str, Any]:
    """A bounded credential-free descriptor, NOT permission to call any endpoint.

    The caller must supply the exact stock identity from its frozen scope and an
    independently qualified exchange calendar; weekday arithmetic is not a calendar.
    """
    days = _window(thscode, sessions)
    return {'api_name': 'daily', 'params': {'ts_code': thscode,
        'start_date': days[0].strftime('%Y%m%d'), 'end_date': days[-1].strftime('%Y%m%d')}, 'fields': FIELDS}


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            _fail('DATA_QUALIFICATION_FAILED', 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _constant(_):
    _fail('DATA_QUALIFICATION_FAILED', 'NONFINITE_JSON_NUMBER')


def _number(value, *, positive=False) -> Decimal:
    if type(value) not in (str, int):
        _fail('DATA_QUALIFICATION_FAILED', 'INVALID_EXACT_MARKET_NUMBER')
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        _fail('DATA_QUALIFICATION_FAILED', 'INVALID_EXACT_MARKET_NUMBER')
    if not number.is_finite() or number < 0 or (positive and number == 0):
        _fail('DATA_QUALIFICATION_FAILED', 'INVALID_EXACT_MARKET_NUMBER')
    if len(number.as_tuple().digits) > 28 or abs(number.as_tuple().exponent) > 12:
        _fail('DATA_QUALIFICATION_FAILED', 'UNSUPPORTED_MARKET_NUMBER_PRECISION')
    return number


def check_daily_response(raw: bytes, *, request: dict, thscode: str,
                         sessions: Sequence[date], requested_at: datetime,
                         received_at: datetime, input_cutoff: datetime) -> dict:
    """Check exact provider JSON bytes and preserve partial after-hours coverage.

    Observation clocks are caller-supplied and do not authenticate the origin.
    No status from this function permits production cards, even with matching hashes.
    Nonzero/unknown after-hours values are retained, never silently added to the reported
    vol/amount fields or declared equivalent to another provider's daily totals.
    The contract does not establish whether vol/amount already include after-hours.
    """
    days = _window(thscode, sessions)
    if request != daily_request(thscode, days):
        _fail('DATA_QUALIFICATION_FAILED', 'REQUEST_SCOPE_OR_FIELDS_DIFFER')
    clocks = (requested_at, received_at, input_cutoff)
    if any(not isinstance(c, datetime) or c.tzinfo is None or c.utcoffset() is None for c in clocks):
        _fail('DATA_QUALIFICATION_FAILED', 'TIMEZONE_AWARE_CAPTURE_REQUIRED')
    if not requested_at <= received_at <= input_cutoff or input_cutoff-requested_at > MAX_LIFETIME:
        _fail('DATA_QUALIFICATION_FAILED', 'CAPTURE_CLOCK_REVERSED_OR_EXPIRED')
    # Official daily ingestion is 15:00--16:00; never certify an in-progress day.
    if requested_at < datetime.combine(days[-1], time(16), TZ):
        _fail('DATA_INSUFFICIENT', 'LATEST_DAILY_INGESTION_WINDOW_NOT_COMPLETE')
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        _fail('DATA_QUALIFICATION_FAILED', 'RESPONSE_BYTE_BUDGET_OR_TYPE_INVALID')
    try:
        envelope = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                              parse_float=str, parse_constant=_constant)
    except TushareReferenceError:
        raise
    except (UnicodeError, ValueError, RecursionError):
        _fail('DATA_QUALIFICATION_FAILED', 'MALFORMED_PROVIDER_JSON')
    if not isinstance(envelope, dict) or type(envelope.get('code')) is not int:
        _fail('DATA_QUALIFICATION_FAILED', 'INVALID_PROVIDER_ENVELOPE')
    if envelope['code'] != 0:
        _fail('REQUEST_FAILED', 'PROVIDER_BUSINESS_REQUEST_FAILED')
    data = envelope.get('data')
    if not isinstance(data, dict):
        _fail('DATA_INSUFFICIENT', 'PROVIDER_DATA_MISSING')
    fields, items = data.get('fields'), data.get('items')
    if (not isinstance(fields, list) or any(type(f) is not str for f in fields)
            or len(fields) != len(set(fields)) or set(fields) != set(REQUIRED_FIELDS)):
        _fail('DATA_QUALIFICATION_FAILED', 'RESPONSE_FIELDS_DIFFER')
    if not isinstance(items, list) or len(items) != MAX_RESPONSE_ROWS:
        _fail('DATA_INSUFFICIENT', 'EXACT_61_RETURNED_ROWS_REQUIRED')
    by_day = {}
    with localcontext(Context(prec=50)):
        for values in items:
            if not isinstance(values, list) or len(values) != len(fields):
                _fail('DATA_QUALIFICATION_FAILED', 'RAGGED_PROVIDER_ROW')
            row = dict(zip(fields, values, strict=True))
            if row['ts_code'] != thscode:
                _fail('DATA_QUALIFICATION_FAILED', 'PROVIDER_STOCK_IDENTITY_DIFFERS')
            label = row['trade_date']
            if type(label) is not str or not re.fullmatch(r'\d{8}', label):
                _fail('DATA_QUALIFICATION_FAILED', 'INVALID_PROVIDER_DATE')
            try:
                day = datetime.strptime(label, '%Y%m%d').date()
            except ValueError:
                _fail('DATA_QUALIFICATION_FAILED', 'INVALID_PROVIDER_DATE')
            if day not in days or day in by_day:
                _fail('DATA_QUALIFICATION_FAILED', 'DUPLICATE_OR_OFF_CALENDAR_DAY')
            close, reference = (_number(row[k], positive=True) for k in ('close', 'pre_close'))
            volume, amount = _number(row['vol']) * 100, _number(row['amount']) * 1000
            if volume != volume.to_integral_value():
                _fail('DATA_QUALIFICATION_FAILED', 'VOLUME_NOT_WHOLE_SHARES')
            if volume <= 0 or amount <= 0:
                _fail('DATA_INSUFFICIENT', 'UNPRICED_OR_NONTRADING_SESSION_IN_PATH')
            ah_volume = None if row['ah_vol'] is None else _number(row['ah_vol']) * 100
            ah_amount = None if row['ah_amount'] is None else _number(row['ah_amount']) * 1000
            if ah_volume is not None and ah_volume != ah_volume.to_integral_value():
                _fail('DATA_QUALIFICATION_FAILED', 'AFTER_HOURS_VOLUME_NOT_WHOLE_SHARES')
            by_day[day] = {'market_session': day.isoformat(), 'thscode': thscode,
                'close': str(close), 'reported_ex_reference': str(reference),
                'reported_volume_shares': str(volume), 'reported_turnover_cny': str(amount),
                'after_hours_volume_shares': None if ah_volume is None else str(ah_volume),
                'after_hours_turnover_cny': None if ah_amount is None else str(ah_amount)}
    rows = [by_day[d] for d in days]
    discontinuities = [row['market_session'] for prior, row in zip(rows, rows[1:])
                       if Decimal(row['reported_ex_reference']) != Decimal(prior['close'])]
    return {'semantics': SEMANTICS,
        'status': 'REFERENCE_DISCONTINUITY_REQUIRES_REVIEW' if discontinuities else 'SOURCE_FIELDS_CHECKED_ONLY',
        'source_response_sha256': hashlib.sha256(raw).hexdigest(),
        'request': request, 'requested_at': requested_at.isoformat(), 'received_at': received_at.isoformat(),
        'input_cutoff': input_cutoff.isoformat(), 'rows': rows, 'discontinuity_sessions': discontinuities,
        'origin_authenticated': False, 'latest_quote_independently_matched': False,
        'cross_provider_amount_scope_established': False, 'qualified_for_stock_reading': False,
        'price_convention': 'PROVIDER_RAW_CLOSE_WITH_REPORTED_EX_REFERENCE_NOT_TOTAL_RETURN',
        'historical_publication_pit_established': False, 'network_calls': 0,
        'market_state_writes': 0, 'events_created': 0,
        'human_attention_authority': 'NONE', 'research_authority': 'NONE', 'investment_authority': 'NONE'}
