"""Pure adapters for retained NewsNow/HiThink observations, never acquisition.

The caller retains raw bytes and receipts. Rebuild from those exact inputs to
verify a saved projection; a matching hash alone is not source verification.
No parser service, provider registry, scheduler, model, Evidence or admission.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
from hashlib import sha256
import json
import re
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

from decision_kernel.identity import canonical_hash, canonical_json

VERSION = 'retained-external-radar-observations-v1'
NEWS_KIND = 'NEWS_EVENT_CANDIDATE'
INDUSTRY_KIND = 'INDUSTRY_VARIABLE_OBSERVATION'
AUTHORITY = {'investment_authority': 'NONE', 'research_authority': 'NONE',
             'human_attention_authority': 'NONE', 'signal_transition_authority': 'NONE',
             'automatic_admission': False, 'model_calls': 0, 'network_calls': 0}
NEWS_DOMAINS = {'cls': ('cls.cn',), 'wallstreetcn': ('wallstreetcn.com',),
                'fastbull': ('fastbull.com', 'fastbull.cn'), 'jin10': ('jin10.com',),
                'mktnews': ('mktnews.net',), 'gelonghui': ('gelonghui.com',),
                'thepaper': ('thepaper.cn',)}
CONTINUOUS = {'LC': ('LCZL.GFE', '碳酸锂'), 'CU': ('CUZL.SHF', '沪铜'),
              'RB': ('RBZL.SHF', '螺纹钢')}
SHANGHAI = ZoneInfo('Asia/Shanghai')
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def require(condition, code):
    if not condition:
        raise ValueError(code)


def clock(value):
    require(isinstance(value, str), 'OBSERVATION_CLOCK_INVALID')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('OBSERVATION_CLOCK_INVALID') from None
    require(result.tzinfo is not None, 'OBSERVATION_CLOCK_UNZONED')
    return result


def _day(value):
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'SERIES_DATE_INVALID')
    return date.fromisoformat(value)


def _ms(value):
    require(type(value) is int and 0 < value < 100_000_000_000_000, 'SOURCE_TIMESTAMP_INVALID')
    return EPOCH + timedelta(milliseconds=value)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'SOURCE_DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _decode(body):
    def bad_constant(_):
        raise ValueError('SOURCE_NONFINITE_NUMBER')
    return json.loads(body.decode('utf-8'), parse_float=Decimal,
                      parse_constant=bad_constant, object_pairs_hook=_unique)


def _seal(payload):
    # Original Kernel canonical serialization rejects floats and preserves Decimal.
    payload = json.loads(canonical_json(payload))
    return {'projection': payload, 'projection_hash': canonical_hash(payload)}


def _bound(body, receipt, cutoff, *, hithink=False):
    require(isinstance(body, bytes) and 0 < len(body) <= 4 * 1024 * 1024, 'SOURCE_BODY_BUDGET')
    size, digest = ('response_bytes', 'response_sha256') if hithink else ('bytes', 'sha256')
    require(type(receipt.get(size)) is int and receipt[size] == len(body)
            and receipt.get(digest) == sha256(body).hexdigest(), 'SOURCE_RECEIPT_BYTES_DIFFER')
    require(clock(receipt['requested_at']) <= clock(receipt['received_at']) <= clock(cutoff),
            'SOURCE_RECEIPT_CLOCK_ORDER')
    return {'bytes': len(body), 'sha256': receipt[digest],
            'requested_at': receipt['requested_at'], 'received_at': receipt['received_at']}


def _url(value, domains):
    require(isinstance(value, str) and len(value) <= 2048
            and not re.search(r'[\x00-\x20\\]', value), 'NEWS_URL_INVALID')
    p = urlsplit(value)
    require(p.scheme == 'https' and p.username is None and p.password is None
            and p.port in (None, 443) and p.hostname is not None
            and any(p.hostname == d or p.hostname.endswith('.' + d) for d in domains),
            'NEWS_PUBLISHER_DOMAIN_DIFFERS')
    return value


def _claim(value, received):
    if value in (None, ''):
        return {'raw': value, 'parsed_at': None, 'status': 'MISSING_CLAIM'}
    try:
        # NewsNow reviewed numeric contract is epoch milliseconds, not guessed seconds.
        parsed = _ms(value) if type(value) is int else clock(value)
        require(parsed >= datetime(2000, 1, 1, tzinfo=timezone.utc), 'CLAIM_OUT_OF_RANGE')
    except (ValueError, TypeError, OverflowError):
        return {'raw': value, 'parsed_at': None, 'status': 'UNPARSEABLE_CLAIM'}
    return {'raw': value, 'parsed_at': parsed.isoformat(),
            'status': 'FUTURE_CLAIM' if parsed > received else 'PARSED_CLAIM_NOT_PUBLISHER_VERIFIED'}


def news(body: bytes, receipt: dict, *, cutoff: str) -> dict:
    """Normalize one original probe-compatible NewsNow response, no HTTP request."""
    source = _bound(body, receipt, cutoff)
    kind = receipt['label']
    require(kind in NEWS_DOMAINS, 'NEWS_SOURCE_PROFILE_UNKNOWN')
    request = urlsplit(receipt['url'])
    require(request.username is None and request.password is None and request.path == '/api/s'
            and (request.scheme == 'https' or (request.scheme == 'http' and request.hostname == '127.0.0.1'))
            and parse_qs(request.query).get('id') == [kind]
            and set(parse_qs(request.query, keep_blank_values=True)) <= {'id', 'latest'}, 'NEWS_REQUEST_IDENTITY_DIFFERS')
    source.update(source_id=kind, request_url=receipt['url'], representation='RETAINED_HTTP_BODY')
    if receipt.get('http_status') != 200:
        return _seal({'version': VERSION, 'kind': NEWS_KIND, 'source': source,
                      'status': 'SOURCE_UNAVAILABLE', 'observations': [], **AUTHORITY})
    require(receipt.get('status') == 'CAPTURED_PUBLIC_RESPONSE', 'NEWS_RECEIPT_STATUS_DIFFERS')
    obj = _decode(body)
    require(isinstance(obj, dict) and obj.get('status') in {'success', 'cache'}
            and obj.get('id') in {kind, {'cls': 'cls-telegraph', 'wallstreetcn': 'wallstreetcn-quick',
                                       'fastbull': 'fastbull-express', 'mktnews': 'mktnews-flash'}.get(kind, kind)},
            'NEWS_ENVELOPE_IDENTITY_DIFFERS')
    items = obj.get('items')
    require(isinstance(items, list) and len(items) <= 30, 'NEWS_WINDOW_BUDGET')
    rows, aliases = [], {}
    for index, item in enumerate(items):
        require(isinstance(item, dict), 'NEWS_ITEM_INVALID')
        title = item.get('title')
        require(isinstance(title, str) and 0 < len(title.strip()) <= 8192, 'NEWS_TITLE_INVALID')
        link = _url(item.get('url'), NEWS_DOMAINS[kind])
        if item.get('mobileUrl'):
            _url(item['mobileUrl'], NEWS_DOMAINS[kind])
        item_id = item.get('id')
        require(type(item_id) in (int, str) and len(str(item_id)) <= 256, 'NEWS_ITEM_ID_INVALID')
        alias = str(item_id)
        require(alias not in aliases or aliases[alias] == link, 'NEWS_ITEM_ID_REBOUND')
        aliases[alias] = link
        extra = item.get('extra') if isinstance(item.get('extra'), dict) else {}
        claims = {key: _claim(value, clock(source['received_at'])) for key, value in
                  [('pubDate', item.get('pubDate')), ('extra.date', extra.get('date'))]}
        identity = {'source_id': kind, 'item_id': alias, 'url': link}
        version = {**identity, 'title': title, 'publication_claims': claims}
        rows.append({**version, 'article_id': canonical_hash(identity), 'version_id': canonical_hash(version),
                     'window_position': index, 'clock_origin': 'RELATIVE_TIME_DERIVED_BY_SOURCE_ADAPTER' if kind == 'gelonghui'
                     else 'SERVICE_PASSTHROUGH_NOT_VERIFIED_PUBLISHER_TIME',
                     'fetched_at': source['received_at'], 'business_linkage': 'NOT_ESTABLISHED',
                     'question_status': 'NOT_FORMED', 'qualification': 'CONTEXT_ONLY'})
    return _seal({'version': VERSION, 'kind': NEWS_KIND, 'source': source, 'status': 'OBSERVATIONS_NORMALIZED',
                  'service_status': obj['status'], 'service_clock_claim': _claim(obj.get('updatedTime'), clock(source['received_at'])),
                  'service_clock_meaning': 'CACHE_OR_SERVICE_CLOCK_NOT_ARTICLE_PUBLICATION',
                  'coverage': 'ONE_UPSTREAM_CAPPED_WINDOW_NOT_COMPLETE_NEWS', 'observations': rows, **AUTHORITY})


def news_context(captures: list, *, cutoff: str, company_reading=None) -> dict:
    """Rebuild every input; optionally reuse the existing company-reading validator.

    captures are (raw_bytes, original_receipt) pairs. Title equality makes a
    review candidate only; it is NOT an economic-event deduplication decision.
    """
    require(0 < len(captures) <= 10, 'NEWS_SOURCE_COUNT_BUDGET')
    reports = [news(body, receipt, cutoff=cutoff) for body, receipt in captures]
    seen, rows = set(), []
    for report in reports:
        for row in report['projection']['observations']:
            if row['version_id'] not in seen:
                rows.append(row); seen.add(row['version_id'])
    groups = {}
    for row in rows:
        # Whitespace only: never erase numbers, negation, punctuation or currency.
        key = ' '.join(row['title'].split())
        groups.setdefault(key, []).append(row['version_id'])
    events = [{'candidate_id': canonical_hash(sorted(ids)), 'members': sorted(ids),
               'rule': 'EXACT_TITLE_WHITESPACE_ONLY', 'event_identity': 'UNVERIFIED'}
              for ids in groups.values() if len(ids) > 1]
    companies, reading_hash = [], None
    if company_reading is not None:
        from . import radar_company_reading as existing
        existing.render(company_reading)  # Existing identity/authority/stock-code checks.
        p = company_reading['projection']
        require(clock(p['generated_at']) <= clock(cutoff), 'COMPANY_CONTEXT_AFTER_CUTOFF')
        require(len(p['companies']) <= 5000, 'COMPANY_CONTEXT_BUDGET')
        reading_hash = company_reading['projection_hash']
        for company in p['companies']:
            names = company['source_names']
            require(isinstance(names, list) and 0 < len(names) <= 20
                    and all(isinstance(n, str) and 2 <= len(n) <= 128 for n in names), 'COMPANY_NAMES_INVALID')
            matches = [{'observation_id': r['version_id'], 'matched_names': [n for n in names if n in r['title']]}
                       for r in rows if any(n in r['title'] for n in names)]
            if matches:
                companies.append({'thscode': company['thscode'], 'source_names': deepcopy(names),
                                  'matches': matches, 'research': deepcopy(company['research']),
                                  'qualification': 'CONTEXT_ONLY', 'business_linkage': 'NOT_ESTABLISHED',
                                  'question_status': 'NOT_FORMED', 'automatic_admission': False})
    return _seal({'version': VERSION, 'kind': NEWS_KIND, 'cutoff': cutoff,
                  'sources': reports, 'observations': rows, 'possible_event_groups': events,
                  'company_reading_hash': reading_hash, 'companies': companies,
                  'company_mapping': 'EXACT_SAVED_NAME_TEXT_ONLY_NOT_SECURITY_OR_EXPOSURE_ACCEPTANCE',
                  'semantic_review': 'NOT_PERFORMED', **AUTHORITY})


def _number(value):
    require(value is None or type(value) in (int, Decimal), 'SERIES_NUMBER_INVALID')
    if value is None:
        return None
    value = Decimal(value)
    require(value.is_finite() and abs(value) < Decimal('1e30'), 'SERIES_NUMBER_OUT_OF_RANGE')
    return value


def _hithink(pair, cutoff, path, params):
    body, receipt = pair
    bound = _bound(body, receipt, cutoff, hithink=True)
    require(receipt.get('path') == '/api/futures/' + path and receipt.get('params') == params
            and receipt.get('status') == 'CAPTURED_DECODED_RESPONSE'
            and receipt.get('representation') == 'DECODED_JSON_TOOL_RETURN_NOT_WIRE_BYTES', 'FUTURES_REQUEST_DIFFERS')
    obj = _decode(body)
    require(isinstance(obj, dict) and type(obj.get('code')) is int and obj['code'] == 0
            and isinstance(obj.get('data'), dict), 'FUTURES_BUSINESS_RESPONSE_FAILED')
    data = obj['data']
    require(_ms(data['timestamp']) <= clock(receipt['received_at']), 'FUTURES_PROVIDER_CLOCK_FUTURE')
    require(isinstance(data.get('item'), list) and len(data['item']) <= 5000
            and all(isinstance(r, dict) for r in data['item']), 'FUTURES_ITEM_BUDGET_OR_SHAPE')
    bound.update(path=receipt['path'], params=deepcopy(params), representation=receipt['representation'],
                 provider_timestamp=data['timestamp'])
    return data, bound


def _window(items, start, end):
    dates = [_day(row['date']) for row in items]
    require(len(set(dates)) == len(dates), 'SERIES_DUPLICATE_DATE')
    rows = sorted((deepcopy(r) for r, d in zip(items, dates) if start <= d <= end), key=lambda r: r['date'])
    return rows, len(items) - len(rows)


def industry(variety: str, captures: dict, *, price_start: str, recent_start: str,
             period_end: str, cutoff: str) -> dict:
    """Rebuild selected LC/CU/RB continuous-series observations with original bytes.

    Required capture keys: identity, prices, basis, warehouse. Values are
    (body, original receipt); optional positions is the same dated source. This
    contract is windowed retrospective reading, not historical PIT availability.
    """
    require(variety in CONTINUOUS and set(captures) in
            ({'identity', 'prices', 'basis', 'warehouse'}, {'identity', 'prices', 'basis', 'warehouse', 'positions'}),
            'FUTURES_PROFILE_OR_CAPTURE_SET_DIFFERS')
    code, name = CONTINUOUS[variety]
    first, recent, last = map(_day, (price_start, recent_start, period_end))
    require(first <= recent <= last, 'FUTURES_WINDOW_REVERSED')
    end = datetime.combine(last + timedelta(days=1), time(), SHANGHAI) - timedelta(milliseconds=1)
    require(end <= clock(cutoff), 'FUTURES_WINDOW_NOT_ENDED')
    epoch_ms = lambda dt: int((dt.astimezone(timezone.utc) - EPOCH) // timedelta(milliseconds=1))
    history_params = {'thscode': code, 'start': str(epoch_ms(datetime.combine(first, time(), SHANGHAI))), 'end': str(epoch_ms(end))}
    identity, ib = _hithink(captures['identity'], cutoff, 'basis/main-continuous-latest', {})
    options = [r for r in identity['item'] if r.get('thscode') == code]
    require(options and all(r.get('variety_name') == name for r in options), 'CONTINUOUS_IDENTITY_DIFFERS')
    defaults = [r for r in options if r.get('default_value') == 'Y']
    require(len(defaults) == 1 and isinstance(defaults[0].get('spot_indicator_id'), str)
            and defaults[0]['spot_indicator_id'] and _day(defaults[0]['spot_publish_date']) <= last,
            'SPOT_DEFAULT_AMBIGUOUS_OR_AFTER_WINDOW')
    spot_id = defaults[0]['spot_indicator_id']
    prices, pb = _hithink(captures['prices'], cutoff, 'prices/daily', history_params)
    require(prices.get('thscode') == code and prices.get('interval') == '1d', 'PRICE_IDENTITY_DIFFERS')
    points = []
    for row in prices['item']:
        d = _ms(row['timestamp']).astimezone(SHANGHAI).date()
        require(first <= d <= last and (not points or points[-1]['date'] < d.isoformat()), 'PRICE_DATE_OUTSIDE_WINDOW_OR_UNORDERED')
        close = _number(row.get('close_price'))
        require(close is None or close > 0, 'PRICE_NONPOSITIVE')
        points.append({'date': d.isoformat(), 'close': close})
    require(bool(points), 'PRICE_WINDOW_EMPTY')
    bp = captures['basis'][1]['params']
    require(bp in ({'thscode': code}, {'thscode': code, 'spot_indicator_id': spot_id}), 'BASIS_SPOT_ID_DIFFERS')
    basis, bb = _hithink(captures['basis'], cutoff, 'basis/historical', bp)
    warehouse, wb = _hithink(captures['warehouse'], cutoff, 'warehouse-receipts/historical',
                            {'thscode': code, 'start_date': recent_start, 'end_date': period_end})
    b_rows, b_excluded = _window(basis['item'], recent, last)
    w_rows, w_excluded = _window(warehouse['item'], recent, last)
    gaps = []
    rates = []
    with localcontext() as ctx:
        ctx.prec = 40
        returns = {}
        for n in (5, 20):
            selected = points[-n-1:]
            complete = len(selected) == n + 1 and all(r['close'] is not None for r in selected)
            returns[str(n)] = selected[-1]['close'] / selected[0]['close'] - 1 if complete else None
        for row in b_rows:
            s, f, b, reported = [_number(row.get(k)) for k in ('converted_spot_price', 'close_price', 'close_basis', 'close_basis_rate')]
            calculated = (s-f) / s * 100 if s is not None and s > 0 and f is not None else None
            residual = reported - calculated if reported is not None and calculated is not None else None
            amount_ok = None if None in (s, f, b) else s-f == b
            rate_ok = None if residual is None else abs(residual) <= Decimal('0.005')
            if amount_ok is not True or rate_ok is not True:
                gaps.append({'date': row['date'], 'amount_reconciled': amount_ok,
                             'rate_reconciled': rate_ok, 'cause': 'UNKNOWN'})
            rates.append({'date': row['date'], 'reported_percent': reported, 'calculated_percent': calculated,
                          'reported_fraction': reported / 100 if reported is not None else None,
                          'residual_percentage_points': residual, 'amount_reconciled': amount_ok, 'rate_reconciled': rate_ok})
        amounts = [{'date': r['date'], 'amount': _number(r.get('amount'))} for r in w_rows]
        delta = lambda rows, field: (rows[-1][field] - rows[0][field] if len(rows) > 1
                                     and all(r[field] is not None for r in rows) else None)
        b_change, w_change = delta(rates, 'reported_percent'), delta(amounts, 'amount')
    sources, positions = {'identity': ib, 'prices': pb, 'basis': bb, 'warehouse': wb}, None
    if 'positions' in captures:
        pd, sources['positions'] = _hithink(captures['positions'], cutoff, 'positions/variety-daily', {'date': period_end})
        selected = [r for r in pd['item'] if r.get('variety_code') == variety]
        require(len(selected) <= 1, 'POSITION_VARIETY_AMBIGUOUS')
        if selected:
            require(selected[0].get('date') == period_end, 'POSITION_DATE_DIFFERS')
            positions = {'date': period_end, **{k: _number(selected[0].get(k)) for k in
                         ('long_position', 'short_position', 'net_position', 'net_position_change')}}
    return _seal({'version': VERSION, 'kind': INDUSTRY_KIND, 'variety': variety, 'name': name,
                  'thscode': code, 'series_kind': 'PROVIDER_MAIN_CONTINUOUS_NOT_FIXED_EXPIRY_CONTRACT',
                  'sources': sources, 'cutoff': cutoff, 'period_end': period_end,
                  'spot_snapshot_id': spot_id, 'spot_alternatives': deepcopy(options),
                  'historical_spot_binding': 'EXPLICIT_REQUEST_ID' if 'spot_indicator_id' in bp else 'UPSTREAM_DEFAULT_HISTORY_NOT_CONFIRMED',
                  'price_points': points, 'returns_over_observations': returns,
                  'basis_rows': rates, 'basis_excluded_from_declared_window': b_excluded,
                  'basis_amount_convention': 'CONVERTED_SPOT_MINUS_FUTURES',
                  'basis_rate_convention': 'PERCENT_OF_CONVERTED_SPOT',
                  'basis_rate_tolerance_percentage_points': '0.005', 'field_gaps': gaps,
                  'basis_reported_delta_percentage_points': b_change, 'warehouse_rows': amounts,
                  'warehouse_excluded_from_declared_window': w_excluded,
                  'warehouse_delta_raw_unit': w_change, 'warehouse_unit': 'UNKNOWN', 'positions': positions,
                  'calendar_completeness': 'NOT_ESTABLISHED', 'historical_pit_availability': 'NOT_ESTABLISHED',
                  'continuous_roll_composition': 'UNKNOWN', 'company_materiality': 'NOT_ESTABLISHED',
                  'industry_inflection_established': False, 'qualification': 'CONTEXT_ONLY', **AUTHORITY})


def verify_news(saved: dict, captures: list, *, cutoff: str, company_reading=None) -> None:
    require(saved == news_context(captures, cutoff=cutoff, company_reading=company_reading),
            'EXTERNAL_OBSERVATION_DOES_NOT_REBUILD')


def verify_industry(saved: dict, variety: str, captures: dict, *, price_start: str,
                    recent_start: str, period_end: str, cutoff: str) -> None:
    require(saved == industry(variety, captures, price_start=price_start, recent_start=recent_start,
                              period_end=period_end, cutoff=cutoff), 'EXTERNAL_OBSERVATION_DOES_NOT_REBUILD')
