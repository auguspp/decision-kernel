"""Finite EasyStock protocol reuse; source data never acquires Evidence authority.

Derived protocol/CSV logic: jundizhou/easy-stock@0470c34b2d77a18c8389c6e9e0bcf324611c2b3a,
backend/internal/providers/{eastmoney/market_overview.go,futuresposition/client.go,
tencent/industry.go}. Modified: Decimal/unknown handling, exact request custody,
no scores/fallbacks, no cross-variety sum, incomplete CITIC sides remain unknown.
PolyForm Noncommercial 1.0.0: https://polyformproject.org/licenses/noncommercial/1.0.0
Required Notice: Copyright (c) 2026 jundizhou. Commercial use of easy-stock requires prior written permission from the copyright holder.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
import re
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from ..identity import canonical_hash, canonical_json

VERSION = 'easy-stock-public-context-v1'
UPSTREAM = '0470c34b2d77a18c8389c6e9e0bcf324611c2b3a'
MAX_BODY = 4 * 1024 * 1024
VARIETIES = ('IF', 'IH', 'IC', 'IM')
CITIC = '中信期货(代客)'
ZONE = ZoneInfo('Asia/Shanghai')
AUTHORITY = {'investment_authority': 'NONE', 'research_authority': 'NONE',
    'human_attention_authority': 'NONE', 'signal_transition_authority': 'NONE',
    'automatic_admission': False, 'model_calls': 0, 'research_executions': 0,
    'new_attention_events': 0, 'odds_recomputed': False}
FLOW_FIELDS = {'price': 'f2', 'change_percent': 'f3', 'main_net_inflow': 'f62',
    'main_net_inflow_ratio': 'f184', 'super_large_net_inflow': 'f66',
    'super_large_net_inflow_ratio': 'f69', 'large_net_inflow': 'f72',
    'large_net_inflow_ratio': 'f75', 'medium_net_inflow': 'f78',
    'medium_net_inflow_ratio': 'f81', 'small_net_inflow': 'f84',
    'small_net_inflow_ratio': 'f87'}
INDUSTRY_FIELDS = {'five_day_change_percent': 'f109', 'turnover_rate': 'f8',
    'rising_count': 'f104', 'falling_count': 'f105', 'leader_change_percent': 'f136'}
TENCENT_FIELDS = {'change_percent': 'bd_zdf', 'five_day_change_percent': 'bd_zdf5',
    'twenty_day_change_percent': 'bd_zdf20', 'leader_change_percent': 'nzg_zdf'}


def require(ok, code):
    if not ok:
        raise ValueError(code)


def clock(value):
    require(isinstance(value, str), 'CONTEXT_CLOCK_INVALID')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None and result.utcoffset() is not None, 'CONTEXT_CLOCK_UNZONED')
    return result


def day(value):
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'CONTEXT_DATE_INVALID')
    return date.fromisoformat(value)


def decode(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY, 'CONTEXT_BODY_BUDGET')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'CONTEXT_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('CONTEXT_NONFINITE_JSON')
    def bounded_decimal(text):
        value = Decimal(text)
        require(len(text) <= 96 and len(value.as_tuple().digits) <= 64
                and -30 <= value.as_tuple().exponent <= 30, 'CONTEXT_DECIMAL_SIZE')
        return value
    def bounded_int(text):
        require(len(text.lstrip('-')) <= 30, 'CONTEXT_INTEGER_SIZE')
        return int(text)
    return json.loads(raw.decode('utf-8-sig'), parse_float=bounded_decimal, parse_int=bounded_int,
                      parse_constant=invalid, object_pairs_hook=unique)


def seal(value):
    payload = json.loads(canonical_json(value))
    return {'projection': payload, 'projection_hash': canonical_hash(payload)}


def requests_for(target_date):
    d = day(target_date)
    items = [{'id': 'tencent-industry', 'provider': 'TENCENT',
        'url': 'https://proxy.finance.qq.com/ifzqgtimg/appstock/app/mktHs/rank',
        'params': {'l': '150', 'p': '1', 't': '01/averatio', 'ordertype': '', 'o': '0'}}]
    for dimension, fs in (('industry', 'm:90+t:2+f:!50'), ('theme', 'm:90+t:3+f:!50'),
                          ('stock', 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23')):
        fields = ['f12', 'f13', 'f14', *FLOW_FIELDS.values()]
        if dimension == 'industry':
            fields += [*INDUSTRY_FIELDS.values(), 'f128', 'f24']
        items.append({'id': 'eastmoney-' + dimension, 'provider': 'EASTMONEY',
            'url': 'https://push2.eastmoney.com/api/qt/clist/get',
            'params': {'pn': '1', 'pz': '200', 'po': '1', 'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281', 'fltt': '2', 'invt': '2',
                'fid': 'f62', 'fs': fs, 'fields': ','.join(dict.fromkeys(fields))}})
    for variety in VARIETIES:
        items.append({'id': 'cffex-' + variety, 'provider': 'CFFEX',
            'url': f'http://www.cffex.com.cn/sj/ccpm/{d:%Y%m}/{d:%d}/{variety}_1.csv',
            'params': {}})
    return items


def number(value, *, integer=False, nonnegative=False):
    if value is None or (isinstance(value, str) and value.strip() in {'', '-', '--', 'null'}):
        return None, 'MISSING'
    if type(value) not in (int, Decimal, str):
        return None, 'INVALID'
    text = str(value).strip()
    if ',' in text:
        if not re.fullmatch(r'[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?', text):
            return None, 'INVALID'
        text = text.replace(',', '')
    try:
        n = Decimal(text)
    except InvalidOperation:
        return None, 'INVALID'
    if (not n.is_finite() or len(n.as_tuple().digits) > 64
            or not -30 <= n.as_tuple().exponent <= 30
            or n.copy_abs() > Decimal('1e15') or (nonnegative and n < 0)):
        return None, 'INVALID'
    if integer and n != n.to_integral_value():
        return None, 'INVALID'
    return int(n) if integer else n, 'AVAILABLE'


def source_meta(receipt, available, trade_date=None):
    spec = receipt['request']
    return {'source': spec['provider'], 'source_url': spec['url'] +
        ('?' + urlencode(spec['params']) if spec['params'] else ''),
        'available_fields': sorted(available), 'fetched_at': receipt['received_at'],
        'stale': None, 'trade_date': trade_date, 'snapshot_id': None,
        'next_refresh_at': None, 'fallback_reason': None, 'carry_forward': False,
        'market_freshness': 'NOT_ESTABLISHED_NO_CALENDAR_OR_CACHE_PROMOTION',
        'request_target_date': receipt['target_date'],
        'raw_sha256': receipt['sha256'], 'representation': 'RETAINED_HTTP_BODY',
        'transport_authenticated': spec['url'].startswith('https://'),
        'contract_basis': 'PINNED_UPSTREAM_IMPLEMENTATION_NOT_LIVE_SEMANTIC_ACCEPTANCE'}


def market_rows(label, raw, receipt):
    obj = decode(raw)
    require(isinstance(obj, dict), 'MARKET_ENVELOPE_INVALID')
    tencent = label == 'tencent-industry'
    status_key = 'code' if tencent else 'rc'
    require(type(obj.get(status_key)) is int and obj[status_key] == 0, 'MARKET_PROVIDER_REJECTED')
    data = obj.get('data')
    if tencent:
        rows, total, maximum = data, None, 150
    else:
        require(isinstance(data, dict), 'MARKET_DATA_UNAVAILABLE')
        rows, total, maximum = data.get('diff'), data.get('total'), 200
        require(total is None or (type(total) is int and 0 <= total <= 100000), 'MARKET_TOTAL_INVALID')
    require(isinstance(rows, list) and len(rows) <= maximum, 'MARKET_ROW_BUDGET_OR_SHAPE')
    require(total is None or total >= len(rows), 'MARKET_TOTAL_LESS_THAN_ROWS')
    mapping = dict(TENCENT_FIELDS if tencent else FLOW_FIELDS)
    if label == 'eastmoney-industry':
        mapping.update(INDUSTRY_FIELDS)
    result = []
    for index, row in enumerate(rows):
        require(isinstance(row, dict), 'MARKET_ROW_INVALID')
        values, gaps = {}, []
        for name, field in mapping.items():
            count = name in {'rising_count', 'falling_count'}
            values[name], status = number(row.get(field), integer=count, nonnegative=count)
            if status != 'AVAILABLE':
                gaps.append({'field': field, 'name': name, 'status': status})
        code, name = row.get('bd_code' if tencent else 'f12'), row.get('bd_name' if tencent else 'f14')
        identity_ok = isinstance(code, str) and bool(re.fullmatch(r'[A-Za-z0-9_.-]{1,32}', code))
        symbol = None
        if label == 'eastmoney-stock' and identity_ok and re.fullmatch(r'\d{6}', code):
            market = row.get('f13')
            if type(market) is int and market in (0, 1):
                symbol = code + ('.SH' if market == 1 else '.SZ')
        if label.endswith('industry'):
            values['leader_name'] = row.get('nzg_name' if tencent else 'f128')
            if not isinstance(values['leader_name'], str) or not values['leader_name'].strip():
                values['leader_name'] = None
            if tencent:
                leader = row.get('nzg_code')
                values['leader_source_code'] = (leader if isinstance(leader, str)
                    and re.fullmatch(r'(?:sh|sz|bj)\d{6}', leader) else None)
        if label == 'eastmoney-industry':
            values['twenty_day_change_percent'] = None
            gaps.append({'field': 'f24', 'name': 'twenty_day_change_percent',
                         'status': 'QUARANTINED_HORIZON_NOT_ESTABLISHED'})
        available = [k for k, v in values.items() if v is not None]
        identity = {'source_id': label, 'source_code': code, 'source_market': row.get('f13')}
        result.append({'source_row': index, 'identity': identity, 'name': name,
            'security_id': symbol, 'identity_status': 'SOURCE_CODE_ONLY' if identity_ok else 'UNKNOWN',
            'observation_id': canonical_hash(identity),
            'version_id': canonical_hash({'source_id': label, 'raw': row}),
            'values': values, 'raw': row, 'field_gaps': gaps,
            'meta': source_meta(receipt, available), 'qualification': 'CONTEXT_ONLY'})
    return {'status': 'EMPTY_WINDOW_NOT_NO_ACTIVITY' if not rows else 'MARKET_CONTEXT',
        'kind': 'MARKET_EXPRESSION', 'source_id': label, 'observations': result,
        'coverage': {'returned_rows': len(rows), 'upstream_total_claim': total,
            'page': 1, 'page_limit': maximum, 'all_market_covered': False,
            'selection': 'UPSTREAM_RANKED_FIRST_PAGE_NOT_UNBIASED_UNIVERSE'},
        'taxonomy': 'TENCENT_SOURCE_CLASSIFICATION' if tencent else 'EASTMONEY_SOURCE_CLASSIFICATION',
        'classification_equivalent_to_existing_ths_sector': False,
        'units': 'UPSTREAM_PERCENT_POINTS_AND_CNY_FLOW_NOT_INDEPENDENTLY_VERIFIED',
        'breadth': 'RAW_UP_DOWN_COUNTS_ONLY_UNCHANGED_MEMBERS_NOT_ESTABLISHED',
        'meta': source_meta(receipt, sorted({k for r in result for k in r['meta']['available_fields']}))}


def cffex_rows(variety, raw, receipt):
    try:
        text, encoding = raw.decode('utf-8-sig'), 'UTF-8'
    except UnicodeDecodeError:
        text, encoding = raw.decode('gb18030'), 'GB18030'
    records = list(csv.reader(io.StringIO(text), strict=True))
    require(len(records) <= 2048, 'CFFEX_ROW_BUDGET')
    target = receipt['target_date']
    contracts, rows = {}, []
    for index, cells in enumerate(records):
        if not cells or not any(c.strip() for c in cells):
            continue
        if cells[0].strip() in {'交易日', '交易日期', '日期'}:
            continue
        # The exchange export has a two-row header, not an undated data row.
        # Match both complete rows only at the start; never skip unknown records.
        if (index == 1 and tuple(c.strip() for c in records[0]) == (
                '交易日', '合约', '排名', '成交量排名', '', '',
                '持买单量排名', '', '', '持卖单量排名', '', '')
                and tuple(c.strip() for c in cells) == (
                    '', '', '', '会员简称', '成交量', '比上一交易日增减',
                    '会员简称', '持买单量', '比上一交易日增减',
                    '会员简称', '持卖单量', '比上一交易日增减')):
            continue
        require(len(cells) >= 12, 'CFFEX_ROW_SHAPE_INVALID')
        row_date = cells[0].strip().replace('-', '').replace('/', '')
        require(row_date == target.replace('-', ''), 'CFFEX_DATE_DIFFERS')
        contract = cells[1].strip().upper()
        require(re.fullmatch(variety + r'\d{2}(?:0[1-9]|1[0-2])', contract), 'CFFEX_CONTRACT_DIFFERS')
        rank, status = number(cells[2], integer=True)
        require(status == 'AVAILABLE' and 1 <= rank <= 20, 'CFFEX_RANK_INVALID')
        byrank = contracts.setdefault(contract, {})
        require(rank not in byrank, 'CFFEX_DUPLICATE_RANK')
        row = {'contract': contract, 'rank': rank, 'source_row': index, 'raw': cells}
        for name, offset in (('long_position', 7), ('long_change', 8), ('short_position', 10), ('short_change', 11)):
            row[name], status = number(cells[offset], integer=True, nonnegative=name.endswith('position'))
            require(status == 'AVAILABLE', 'CFFEX_POSITION_OR_CHANGE_INVALID')
        row['long_name'], row['short_name'] = cells[6].strip(), cells[9].strip()
        require(all(0 < len(row[k]) <= 128 for k in ('long_name', 'short_name')), 'CFFEX_MEMBER_INVALID')
        byrank[rank] = row
        rows.append(row)
    require(bool(contracts) and len(contracts) <= 16, 'CFFEX_NO_CONTRACTS_OR_BUDGET')
    summaries = []
    for contract, byrank in sorted(contracts.items()):
        require(set(byrank) == set(range(1, 21)), 'CFFEX_INCOMPLETE_TOP20')
        members = list(byrank.values())
        for side in ('long', 'short'):
            require(len({''.join(r[side + '_name'].split()) for r in members}) == 20,
                    'CFFEX_DUPLICATE_MEMBER')
        item = {'contract': contract, **{k: sum(r[k] for r in members)
            for k in ('long_position', 'short_position', 'long_change', 'short_change')}}
        citic = {}
        for side in ('long', 'short'):
            found = [r for r in members if ''.join(r[side + '_name'].split()) == CITIC]
            citic[side + '_change'] = found[0][side + '_change'] if found else None
            citic[side + '_position'] = found[0][side + '_position'] if found else None
        citic['net_long_change'] = (citic['long_change'] - citic['short_change']
            if all(citic[s + '_change'] is not None for s in ('long', 'short')) else None)
        citic['coverage'] = ('BOTH_DISCLOSED_SIDES' if citic['net_long_change'] is not None
                             else 'MISSING_RANKED_SIDE_UNKNOWN_NOT_ZERO')
        item.update(net_long_position=item['long_position'] - item['short_position'],
            net_short_position=item['short_position'] - item['long_position'],
            net_long_change=item['long_change'] - item['short_change'],
            net_short_change=item['short_change'] - item['long_change'], citic=citic)
        summaries.append(item)
    total = {k: sum(r[k] for r in summaries) for k in ('long_position', 'short_position',
        'long_change', 'short_change', 'net_long_position', 'net_short_position', 'net_long_change', 'net_short_change')}
    citic_complete = all(r['citic']['net_long_change'] is not None for r in summaries)
    total['citic_net_long_change'] = sum(r['citic']['net_long_change'] for r in summaries) if citic_complete else None
    total['citic_net_short_change'] = -total['citic_net_long_change'] if citic_complete else None
    return {'status': 'POSITIONING_CONTEXT', 'kind': 'POSITIONING_CONTEXT',
        'source_id': 'cffex-' + variety, 'variety': variety, 'trade_date': target,
        'encoding': encoding, 'contracts': summaries, 'rows': rows, 'totals': total,
        'meta': source_meta(receipt, [k for k, v in total.items() if v is not None], target),
        'coverage': {'returned_contract_count': len(contracts), 'top20_complete_for_returned_contracts': True,
            'exchange_contract_catalog_complete': 'NOT_ESTABLISHED',
            'citic_both_sides_all_returned_contracts': citic_complete},
        'units': 'CONTRACT_LOTS_NOT_NOTIONAL_OR_EQUAL_RISK',
        'change_basis': 'CURRENT_RANKED_MEMBERS_REPORTED_CHANGES_NOT_FIXED_COHORT_DELTA',
        'citic_match': 'WHITESPACE_ONLY_EXACT_' + CITIC,
        'meaning': 'SUM_OF_DISCLOSED_TOP20_NOT_TOTAL_MARKET_OR_BROKER_PROPRIETARY_POSITION'}


def normalize(raw, receipt, *, cutoff):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY, 'CONTEXT_BODY_BUDGET')
    require(type(receipt.get('bytes')) is int and receipt['bytes'] == len(raw)
            and receipt.get('sha256') == sha256(raw).hexdigest(), 'CONTEXT_BYTES_DIFFER')
    spec = receipt['request']
    expected = {r['id']: r for r in requests_for(receipt['target_date'])}
    require(spec.get('id') in expected and spec == expected[spec['id']], 'CONTEXT_REQUEST_DIFFERS')
    require(clock(receipt['requested_at']) <= clock(receipt['received_at']) <= clock(cutoff), 'CONTEXT_CLOCK_ORDER')
    require(day(receipt['target_date']) <= clock(receipt['requested_at']).astimezone(ZONE).date(), 'CONTEXT_FUTURE_TARGET_DATE')
    require(type(receipt.get('http_status')) is int and receipt['http_status'] == 200
            and receipt.get('representation') == 'RETAINED_HTTP_BODY', 'CONTEXT_HTTP_IDENTITY_DIFFERS')
    value = (cffex_rows(spec['id'][6:], raw, receipt) if spec['provider'] == 'CFFEX'
             else market_rows(spec['id'], raw, receipt))
    return seal({**value, 'version': VERSION, 'upstream_commit': UPSTREAM,
        'historical_pit_availability': 'NOT_ESTABLISHED_BY_CURRENT_RETRIEVAL',
        'economic_exposure': 'NOT_ESTABLISHED', 'question_status': 'NOT_FORMED', **AUTHORITY})
