"""One independent, source-labelled institutional leaderboard observation.

No Sector/Stock price gate, Research, Odds, trader inference or investment score.
One-day and three-day disclosures remain distinct overlapping source windows.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time
from decimal import Context, Decimal, InvalidOperation, localcontext
from html import escape

from decision_kernel.adapters.hithink import (
    SHANGHAI_TZ, latest_completed_a_share_session, normalize_hithink_calendar,
    to_hithink_thscode,
)
from decision_kernel.identity import canonical_hash, canonical_json
from .hithink_http import HITHINK_CALENDAR_PATH
from .sector_radar_audit import SectorRadarAuditError, _check_safe_json, _clock
from .theme_radar_probe import _unique_object

VERSION = 'institutional-leaderboard-observation-v1'
BOARD_PATH = '/api/a-share/special-data/dragon-tiger-list'
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 2048
AUTHORITY = {
    'human_attention_authority': 'NONE', 'research_authority': 'NONE',
    'investment_authority': 'NONE', 'signal_transition_authority': 'NONE',
    'automatic_research_routing': False, 'market_state_writes': 0,
    'events_created': 0, 'odds_recomputed': False,
}


class InstitutionalSourceError(ValueError):
    """Finite, safe reason codes; never retain provider exception text."""


def _require(condition, reason):
    if not condition:
        raise InstitutionalSourceError(reason)


def session_date(value):
    _require(isinstance(value, str), 'EXPLICIT_SESSION_REQUIRED')
    try:
        day = date.fromisoformat(value)
    except ValueError:
        raise InstitutionalSourceError('EXPLICIT_SESSION_REQUIRED') from None
    _require(day.isoformat() == value, 'EXPLICIT_SESSION_REQUIRED')
    return day


def decode(raw, credential=None):
    _require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BYTES, 'BODY_SIZE_REJECTED')
    _require(not credential or credential.encode() not in raw, 'UNSAFE_BODY_NOT_RETAINED')
    value = json.loads(raw.decode('utf-8'), parse_float=Decimal, object_pairs_hook=_unique_object)
    try:
        _check_safe_json(value, credential)
    except SectorRadarAuditError:
        raise InstitutionalSourceError('UNSAFE_BODY_NOT_RETAINED') from None
    canonical_json(value)
    _require(isinstance(value, dict), 'ENVELOPE_REJECTED')
    return value


def _data(raw):
    value = decode(raw)
    _require(type(value.get('code')) is int, 'BUSINESS_CODE_MISSING')
    _require(value['code'] == 0, 'PROVIDER_BUSINESS_FAILURE')
    _require(isinstance(value.get('data'), dict), 'DATA_CONTAINER_REJECTED')
    return value, value['data']


def _optional_number(row, key, *, integer=False, nonnegative=False):
    value = row.get(key)
    if value is None:
        return None
    _require(not isinstance(value, (bool, float)) and isinstance(value, (str, int, Decimal)),
             'NUMERIC_REPRESENTATION_REJECTED')
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise InstitutionalSourceError('NUMERIC_VALUE_REJECTED') from None
    _require(number.is_finite() and (not nonnegative or number >= 0)
             and (not integer or number == number.to_integral_value()), 'NUMERIC_VALUE_REJECTED')
    return int(number) if integer else str(number)


def build(calendar_raw, board_raw, *, requests, market_session, generated_at, provenance):
    """Rebuild from original response bytes and exact actual request clocks."""
    day, end = session_date(market_session), _clock(generated_at)
    _require(provenance in {'LIVE_HITHINK', 'SYNTHETIC_TEST_ONLY'}, 'PROVENANCE_REJECTED')
    expected = [(HITHINK_CALENDAR_PATH, {}), (BOARD_PATH, {'board_type': 'org', 'date': market_session})]
    _require(isinstance(requests, list) and len(requests) == 2, 'EXACT_TWO_REQUESTS_REQUIRED')
    prior = None
    for record, (path, params), raw in zip(requests, expected, (calendar_raw, board_raw), strict=True):
        _require(set(record) == {'path', 'params', 'requested_at', 'received_at', 'sha256', 'bytes'},
                 'REQUEST_FIELDS_REJECTED')
        started, received = _clock(record['requested_at']), _clock(record['received_at'])
        _require(record['path'] == path and record['params'] == params, 'REQUEST_IDENTITY_DIFFERS')
        _require(started <= received <= end and (prior is None or prior <= started), 'REQUEST_CLOCK_DIFFERS')
        _require(record['sha256'] == hashlib.sha256(raw).hexdigest() and record['bytes'] == len(raw),
                 'ORIGINAL_BODY_IDENTITY_DIFFERS')
        prior = received
    calendar_value, _ = _data(calendar_raw)
    calendar = normalize_hithink_calendar(calendar_value)
    _require(day in calendar and day <= latest_completed_a_share_session(calendar, observed_at=end),
             'SESSION_NOT_COMPLETED_IN_SUPPLIED_CALENDAR')
    close = datetime.combine(day, time(15), tzinfo=SHANGHAI_TZ)
    _require(close <= _clock(requests[1]['requested_at']), 'BOARD_REQUEST_BEFORE_SESSION_CLOSE')
    _, board = _data(board_raw)
    _require(board.get('board_type') == 'org' and board.get('trade_date') == market_session,
             'ACTUAL_BOARD_OR_SESSION_DIFFERS')
    stamp = board.get('timestamp')
    _require(type(stamp) is int and stamp == int(datetime.combine(day, time(), tzinfo=SHANGHAI_TZ).timestamp()) * 1000,
             'BOARD_DATE_KEY_DIFFERS')
    rows = board.get('stock_items')
    _require(isinstance(rows, list) and len(rows) <= MAX_ROWS, 'ROW_SCOPE_REJECTED')
    _require(board.get('hot_money_items') == [], 'MIXED_BOARD_REJECTED')
    count, stock_count = board.get('count'), board.get('stock_count')
    _require(type(count) is int and type(stock_count) is int and 0 <= stock_count <= count,
             'SOURCE_DENOMINATORS_REJECTED')
    companies, periods = {}, set()
    for index, row in enumerate(rows):
        _require(isinstance(row, dict), 'ROW_REJECTED')
        code, ticker, name = row.get('thscode'), row.get('ticker'), row.get('name')
        _require(all(isinstance(v, str) and v and v == v.strip() for v in (code, ticker, name))
                 and len(name) <= 200, 'SECURITY_IDENTITY_REJECTED')
        exchange = {'SH': 'SSE', 'SZ': 'SZSE', 'BJ': 'BSE'}.get(code[-2:])
        _require(exchange is not None and len(ticker) == 6
                 and to_hithink_thscode(ticker=ticker, exchange=exchange) == code,
                 'SECURITY_IDENTITY_REJECTED')
        days = row.get('range_days')
        _require(type(days) is int and days in {1, 3}, 'DISCLOSURE_WINDOW_REJECTED')
        key = (code, days)
        _require(key not in periods, 'DUPLICATE_SECURITY_WINDOW_REQUIRES_REVIEW')
        periods.add(key)
        item = companies.setdefault(code, {
            'thscode': code, 'company_name': name, 'observations': [],
            'entry': 'INSTITUTIONAL_LEADERBOARD_SOURCE_NOT_SECTOR_PRICE_FILTER',
            'stock_price_qualification': 'NOT_EXECUTED', 'research_status': 'NOT_EXECUTED',
            'business_link': 'NOT_ESTABLISHED',
            'next_question': '该披露区间的机构席位行为，是否伴随可核实的公司经营或预期变化？单次席位净额不足以判断。',
        })
        _require(item['company_name'] == name, 'CONFLICTING_SECURITY_NAMES')
        net = _optional_number(row, 'org_net_value')
        item['observations'].append({
            'source_row_index': index, 'range_days': days, 'window_end': market_session,
            'institution_net_cny': net,
            'institution_buy_count': _optional_number(row, 'org_buy_num', integer=True, nonnegative=True),
            'institution_sell_count': _optional_number(row, 'org_sell_num', integer=True, nonnegative=True),
            'institution_fields_status': 'NET_NOT_SUPPLIED' if net is None else 'SUPPLIER_REPORTED_NET',
            'source_row': row,
        })
    _require(len(companies) == stock_count and (bool(rows) or count == 0), 'DISTINCT_STOCK_COUNT_DIFFERS')
    # Source count denotes upstream records, not necessarily returned window rows.
    # Do not guess aggregation or claim independently exhaustive exchange coverage.
    payload = {
        'version': VERSION, 'market_session': market_session, 'generated_at': end,
        'provenance': provenance, 'origin': {'endpoint': BOARD_PATH, 'board_type': 'org', 'requests': requests},
        'clock_meaning': 'TARGET_DATE_KEY_NOT_PUBLICATION_TIME; ACTUAL_LATER_ACQUISITION_NOT_FIRST_VINTAGE_PIT',
        'source_publication_time': 'UNKNOWN',
        'coverage': {'source_record_count': count, 'returned_window_rows': len(rows),
                     'distinct_stocks': len(companies),
                     'source_count_equals_returned_rows': count == len(rows),
                     'exchange_exhaustiveness': 'NOT_INDEPENDENTLY_ESTABLISHED',
                     'all_market_institution_activity': False,
                     'concept_radar': False, 'other_smart_money_dimensions': False},
        'companies': list(companies.values()),
        'ordering': 'SOURCE_FIRST_APPEARANCE_NOT_RESEARCH_OR_INVESTMENT_RANK',
        'window_aggregation': 'NONE_ONE_AND_THREE_DAY_WINDOWS_MAY_OVERLAP',
        'source_labels': 'CONCEPTS_AND_REASONS_UNVERIFIED_NOT_BUSINESS_EVIDENCE',
        **AUTHORITY,
    }
    payload = json.loads(canonical_json(payload))
    return {'projection': payload, 'projection_hash': canonical_hash(payload)}


def render(report):
    p = report['projection']
    _require(report.get('projection_hash') == canonical_hash(p) and p['version'] == VERSION
             and all(p.get(k) == v for k, v in AUTHORITY.items()), 'READING_IDENTITY_DIFFERS')
    e = lambda value: escape(str(value), quote=True)
    def money(value):
        with localcontext(Context(prec=64)):
            return '未提供' if value is None else f'{Decimal(value) / Decimal(10000):+,.2f} 万元'
    lines = [
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">',
        '<title>机构席位观察 · 独立发现</title>',
        '<style>body{font:16px/1.7 system-ui;max-width:1000px;margin:auto;padding:22px}article{border-top:1px solid #bbb;padding:18px 0}p,pre,td{overflow-wrap:anywhere}pre{white-space:pre-wrap}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:8px;border-bottom:1px solid #ddd}h1{font-size:28px}summary{cursor:pointer}@media(max-width:600px){body{padding:12px}td,th{padding:5px;font-size:13px}}</style>',
        '<h1>机构席位观察 · 独立发现</h1>',
        f'<p>目标交易日：<b>{e(p["market_session"])}</b>；本次读取：{e(p["generated_at"])}</p>',
        f'<p>{p["coverage"]["distinct_stocks"]} 家公司，{p["coverage"]["returned_window_rows"]} 条区间记录；供应商上游记录数 {p["coverage"]["source_record_count"]}。</p>',
        '<p><b>不要求先进入行业首页或通过强势价格筛选。这里是待解释的来源观察，不是推荐名单。</b></p>',
        '<p>单日榜与三日榜不相加，不推断连续买入或当前持仓；不在榜单上不等于机构没有交易。概念标签和涨跌原因仅是供应商标签，未核实业务联系。</p>',
        '<p>披露发生日、来源取得日分开；午夜时间戳只是交易日键，不是发布时间。本次不证明历史当时可得，也不建立完整聪明钱或概念覆盖。</p>',
    ]
    if p['provenance'] == 'SYNTHETIC_TEST_ONLY':
        lines.append('<p><b>合成测试样本，不是实际机构活动。</b></p>')
    if not p['companies']:
        lines.append('<p>这个来源范围返回零家公司，不代表市场没有值得研究的对象。</p>')
    for company in p['companies']:
        lines += [f'<article><h2>{e(company["company_name"])} {e(company["thscode"])}</h2>',
                  '<table><tr><th>披露窗口</th><th>机构席位净额</th><th>买入/卖出机构数</th></tr>']
        for row in company['observations']:
            buy, sell = row['institution_buy_count'], row['institution_sell_count']
            lines.append(f'<tr><td>{row["range_days"]} 日</td><td>{e(money(row["institution_net_cny"]))}</td>'
                         f'<td>{e("未提供" if buy is None else buy)} / {e("未提供" if sell is None else sell)}</td></tr>')
        lines += ['</table>', f'<p><b>下一研究问题：</b>{e(company["next_question"])}</p>',
                  '<p>Stock 价格资格：未执行；Pre / Quick：未执行；业务联系：未建立。</p>',
                  '<details><summary>区间原始字段与供应商标签</summary><pre>',
                  e(canonical_json(company['observations'])), '</pre></details></article>']
    lines += ['<footer>SHADOW SOURCE OBSERVATION · 投资权限 NONE · 不自动研究、重算赔率或交易。</footer></html>']
    return '\n'.join(lines) + '\n'
