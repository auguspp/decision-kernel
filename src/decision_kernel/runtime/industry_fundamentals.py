"""Industrial observations, not an inflection classifier or investment engine.

Reuse reviewed public source protocols, requests/BeautifulSoup and the existing
GitHub capture/reader boundary. Statistical periods are never acquisition dates.
No ticker selection, market-price gate, secrets, provider fallback or model call.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import html
import json
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from ..identity import canonical_hash
from . import current_state as m

VERSION = 'industry-fundamentals-v1'
WORKFLOW = '.github/workflows/radar-industry-breadth.yml'
AUTHORITY = {'research_authority': 'NONE', 'investment_authority': 'NONE',
             'automatic_research_routing': False, 'business_benefit_established': False}
NBS = 'https://www.stats.gov.cn/sj/zxfb/'
EM = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
CPCA = 'http://data.cpcadata.com/api/chartlist'
MEMORY = 'https://www.dramexchange.com/'
FAMILIES = ('nbs-industry', 'nbs-energy', 'nbs-pmi', 'nbs-profit', 'nbs-goods',
            'cpca', 'ppi', 'logistics', 'tanker', 'memory')
PROFILES = {
    'nbs-industry': r'^\d{4}年\d{1,2}月份规模以上工业增加值',
    'nbs-energy': r'^\d{4}年\d{1,2}月份能源生产情况',
    'nbs-pmi': r'^\d{4}年\d{1,2}月中国采购经理(?:人)?指数运行情况',
    'nbs-profit': r'^\d{4}年1[—－–-]\d{1,2}月份?全国规模以上工业企业利润',
    'nbs-goods': r'^\d{4}年\d{1,2}月[上中下]旬流通领域重要生产资料市场价格变动情况',
}
EM_SPECS = {
    'ppi': {'reportName': 'RPT_ECONOMY_PPI',
            'columns': 'REPORT_DATE,TIME,BASE,BASE_SAME,BASE_ACCUMULATE'},
    'logistics': {'reportName': 'RPT_INDUSTRY_INDEX',
                  'columns': 'REPORT_DATE,INDICATOR_VALUE,CHANGE_RATE',
                  'filter': '(INDICATOR_ID="EMI00352262")'},
    'tanker': {'reportName': 'RPT_INDUSTRY_INDEX',
               'columns': 'REPORT_DATE,INDICATOR_VALUE,CHANGE_RATE',
               'filter': '(INDICATOR_ID="EMI00107668")'},
}
MAX_REQUESTS, MAX_BYTES, MAX_SECONDS = 16, 4 * 1024 * 1024, 240


def text(value) -> str:
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', str(value)))


def number(value):
    if value is None or isinstance(value, bool):
        return None
    value = text(value).replace(',', '').replace('−', '-')
    if value in {'', '…', '...', '—', '--', '-', 'null', 'None'}:
        return None
    value = value.removesuffix('%')
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)', value):
        return None
    try:
        result = Decimal(value)
    except InvalidOperation:
        return None
    return str(result) if result.is_finite() else None


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            m.check(key not in result, 'duplicate source JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def body(raw):
    soup = BeautifulSoup(raw, 'html.parser')
    article = soup.select_one('.TRS_Editor') or soup.select_one('.TRS_UEDITOR')
    m.check(article is not None, 'official release article body not found')
    return soup, article


def period_from_title(title):
    match = re.search(r'(\d{4})年(?:1[—－–-])?(\d{1,2})月', title)
    m.check(match is not None, 'release statistical period missing')
    year, month = map(int, match.groups())
    return date(year, month, 1).strftime('%Y-%m')


def rows(table):
    return [[text(c.get_text(' ', strip=True)) for c in tr.find_all(['td', 'th'], recursive=False)]
            for tr in table.find_all('tr')]


def series(family, label, unit, basis, points, **extra):
    clean = {}
    for point in points:
        m.check(isinstance(point['period'], str), 'statistical period missing')
        identity = point['period']
        if identity in clean:
            m.check(clean[identity] == point, 'conflicting same-period source observations')
        clean[identity] = point
    m.check(bool(clean), 'empty industrial series')
    ordered = sorted(clean.values(), key=lambda p: p['period'])
    key = canonical_hash({'family': family, 'label': label, 'unit': unit, 'basis': basis})
    return {'id': key, 'family': family, 'label': label, 'unit': unit, 'basis': basis,
            'points': ordered, 'latest': ordered[-1], **extra}


def energy_fields(content, period):
    # Explicit quantities in the official energy release; first monthly and YTD
    # paragraphs remain different bases. No image reading or guessed values.
    output = []
    patterns = (
        ('原煤产量', r'原煤产量'), ('原油产量', r'原油产量'),
        ('原油加工量', r'原油加工量'), ('天然气产量', r'天然气产量'),
        ('发电量', r'发电量'),
    )
    for label, pattern in patterns:
        matches = list(re.finditer(pattern + r'([\d.]+)(亿吨|万吨|亿立方米|亿千瓦时)[，,]同比(增长|下降)([\d.]+)%', content))
        for match in matches[:2]:
            prefix = content[max(0,match.start()-45):match.start()]
            cumulative = bool(re.search(r'1[—－–-]\d{1,2}月份?[^。]*$', prefix))
            point = {'period': period, 'value': number(match[1]),
                     'reported_yoy_pct': str(Decimal(match[4]) * (-1 if match[3]=='下降' else 1))}
            if cumulative: point['period_start'] = period[:4] + '-01'
            output.append(series('nbs-energy', label, match[2],
                'YEAR_TO_DATE_OUTPUT' if cumulative else 'MONTHLY_OUTPUT', [point]))
    m.check(len(output) >= 5, 'official energy quantity fields missing')
    return output


def pmi_tables(article):
    specs = (
        ('制造业', ('PMI','生产','新订单','原材料库存','从业人员','供应商配送时间')),
        ('制造业', ('新出口订单','进口','采购量','主要原材料购进价格','出厂价格','产成品库存','在手订单','生产经营活动预期')),
        ('非制造业', ('商务活动','新订单','投入品价格','销售价格','从业人员','业务活动预期')),
        ('非制造业', ('新出口订单','在手订单','存货','供应商配送时间')),
    )
    tables = article.find_all('table')
    if not tables: return []
    m.check(len(tables) == 4, 'PMI table inventory changed')
    output = []
    for table_, (scope, labels) in zip(tables, specs):
        header = text(table_.get_text())
        m.check(all(label in header for label in labels), 'PMI table headings changed')
        buckets = {label: [] for label in labels}
        for row in rows(table_):
            match = re.fullmatch(r'(20\d{2})年(\d{1,2})月', row[0]) if row else None
            if not match: continue
            m.check(len(row) == len(labels)+1, 'PMI table row width changed')
            period = date(int(match[1]),int(match[2]),1).strftime('%Y-%m')
            for label, cell in zip(labels,row[1:]):
                m.check(number(cell) is not None, 'PMI numeric observation missing')
                buckets[label].append({'period': period,'value': number(cell)})
        m.check(all(2 <= len(v) <= 24 for v in buckets.values()), 'PMI monthly history bound')
        output += [series('nbs-pmi',scope+'/'+label,'指数点','MONTHLY_DIFFUSION_INDEX',points)
                   for label,points in buckets.items()]
    return output


def official(family, raw, title):
    soup, article = body(raw)
    content = text(article.get_text(' ', strip=True))
    period = period_from_title(title)
    output = []
    if family == 'nbs-energy':
        output = energy_fields(content, period)
    elif family == 'nbs-industry':
        tables = [t for t in article.find_all('table')
                  if '同比增长' in text(t.get_text()) and '绝对量' in text(t.get_text())]
        m.check(bool(tables), 'monthly production table header changed')
        for table in tables:
            for row in rows(table):
                if len(row) != 5 or number(row[2]) is None:
                    continue
                name, amount, yoy, cumulative, cumulative_yoy = row
                if not name or name.startswith(('注', '附注')):
                    continue
                unit = re.search(r'\(([^()]+)\)$', name)
                if number(amount) is not None and unit:
                    output.append(series(family, name, unit.group(1), 'MONTHLY_OUTPUT',
                        [{'period': period, 'value': number(amount), 'reported_yoy_pct': number(yoy)}]))
                else:
                    output.append(series(family, name + '同比', '%', 'MONTHLY_REPORTED_YOY',
                        [{'period': period, 'value': number(yoy)}]))
                if number(cumulative) is not None and unit:
                    output.append(series(family, name, unit.group(1), 'YEAR_TO_DATE_OUTPUT',
                        [{'period': period, 'period_start': period[:4] + '-01',
                          'value': number(cumulative), 'reported_yoy_pct': number(cumulative_yoy)}]))
        m.check(len(output) >= 5, 'too few qualified production rows')
    elif family == 'nbs-pmi':
        # Match only explicitly named first-party classification indices. A
        # reported point change is not a newly fetched prior monthly observation.
        categories = [('制造业', content.split('二、中国非制造业')[0])]
        if '二、中国非制造业' in content:
            categories.append(('非制造业', content.split('二、中国非制造业', 1)[1].split('三、中国综合')[0]))
        for category, chunk in categories:
            labels = ('制造业采购经理指数(PMI)', '非制造业商务活动指数', '生产指数', '新订单指数',
                      '原材料库存指数', '从业人员指数', '供应商配送时间指数', '投入品价格指数',
                      '销售价格指数', '业务活动预期指数')
            for label in labels:
                match = re.search(re.escape(label) + r'(?:为)?([\d.]+)%[，,](?:比上月(上升|下降)([\d.]+)个百分点|与上月持平)', chunk)
                if not match:
                    continue
                value, direction, delta = match.groups()
                change = Decimal(delta or '0') * (-1 if direction == '下降' else 1)
                point = {'period': period, 'value': number(value), 'reported_change_pp': str(change),
                         'prior_value_derived_from_reported_change': str(Decimal(value) - change)}
                output.append(series(family, category + '/' + label, '指数点', 'MONTHLY_DIFFUSION_INDEX', [point]))
        historical = pmi_tables(article)
        if historical:
            output = historical
        m.check(len(output) >= 3, 'PMI source field shape changed')
    elif family == 'nbs-profit':
        for table in article.find_all('table'):
            header = text(table.get_text())
            if not all(word in header for word in ('营业收入', '营业成本', '利润总额', '亿元')):
                continue
            for row in rows(table):
                if len(row) != 7 or any(number(row[i]) is None for i in (1, 3, 5)):
                    continue
                for pos, label in ((1, '营业收入'), (3, '营业成本'), (5, '利润总额')):
                    output.append(series(family, row[0] + '/' + label, '亿元', 'YEAR_TO_DATE_REPORTED',
                        [{'period': period, 'period_start': period[:4] + '-01', 'value': number(row[pos]),
                          'reported_yoy_pct': number(row[pos + 1])}]))
        for label in ('应收账款', '产成品存货'):
            match = re.search(label + r'([\d.]+)万亿元[，,](?:同比)?增长([\d.]+)%', content)
            if match:
                output.append(series(family, '规上工业/' + label, '万亿元', 'MONTH_END_BALANCE',
                    [{'period': period, 'value': number(match[1]), 'reported_yoy_pct': number(match[2])}]))
        for label in ('产成品存货周转天数', '应收账款平均回收期'):
            match = re.search(label + r'为([\d.]+)天[，,]同比(增加|减少)([\d.]+)天', content)
            if match:
                output.append(series(family, '规上工业/' + label, '天', 'REPORTED_TURNOVER_DAYS',
                    [{'period': period, 'value': number(match[1]),
                      'reported_change_days': str(Decimal(match[3]) * (-1 if match[2] == '减少' else 1))}]))
        m.check(len(output) >= 5, 'industrial finance table shape changed')
    elif family == 'nbs-goods':
        part = re.search(r'(上|中|下)旬', title)
        m.check(part is not None, 'ten-day period missing')
        year, month = map(int, period.split('-'))
        start, end = {'上': (1, 10), '中': (11, 20), '下': (21, calendar.monthrange(year, month)[1])}[part[1]]
        period_start, period_end = date(year, month, start).isoformat(), date(year, month, end).isoformat()
        for table in article.find_all('table'):
            header = text(table.get_text())
            if not all(word in header for word in ('产品名称', '本期价格', '比上期')):
                continue
            for row in rows(table):
                if len(row) != 5 or number(row[2]) is None or number(row[4]) is None:
                    continue
                output.append(series(family, row[0], '元/' + row[1], 'TEN_DAY_SURVEY_PRICE',
                    [{'period': period_end, 'period_start': period_start, 'value': number(row[2]),
                      'reported_change_absolute': number(row[3]), 'reported_change_pct': number(row[4])}]))
        m.check(len(output) >= 10, 'too few material price rows')
    else:
        raise ValueError('unknown official family')
    # Publication clock is optional, never inferred from the URL or fetch clock.
    stamp = re.search(r'\b(20\d{2})/(\d{2})/(\d{2})\s+(\d{2}:\d{2})', soup.get_text(' ', strip=True))
    publication = f'{stamp[1]}-{stamp[2]}-{stamp[3]}T{stamp[4]}:00+08:00' if stamp else None
    unique = {}
    for item in output:
        m.check(item['id'] not in unique or unique[item['id']] == item, 'official same-period metric conflict')
        unique[item['id']] = item
    return list(unique.values()), {'publication_at': publication, 'release_title': title,
                    'scope': 'NBS_PUBLISHED_STATISTICS_COMPARABLE_SCOPE_NOT_COMPANY_FINANCIALS'}


def cars(raw):
    data = decode(raw)
    m.check(isinstance(data, list) and len(data) == 2, 'CPCA category structure changed')
    output = []
    for index, category in enumerate(('狭义乘用车', '广义乘用车')):
        rows_ = data[index].get('dataList')
        m.check(isinstance(rows_, list) and 1 <= len(rows_) <= 12, 'CPCA monthly rows changed')
        buckets = {name: [] for name in ('产量', '批发', '零售', '出口')}
        for row in rows_:
            month_match = re.fullmatch(r'(\d{1,2})月', text(row.get('month')))
            m.check(month_match is not None, 'CPCA month identity missing')
            month = int(month_match[1])
            for year_key, values in row.items():
                match = re.fullmatch(r'(20\d{2})年', year_key)
                if not match:
                    continue
                m.check(isinstance(values, list) and len(values) == 4, 'CPCA production wholesale retail export fields changed')
                year = int(match[1]); previous = row.get(str(year - 1) + '年')
                for pos, name in enumerate(buckets):
                    value = number(values[pos])
                    if value is None:
                        continue
                    point = {'period': date(year, month, 1).strftime('%Y-%m'), 'value': value}
                    if isinstance(previous, list) and len(previous) == 4 and number(previous[pos]) is not None and Decimal(number(previous[pos])) != 0:
                        point['computed_yoy_pct'] = str((Decimal(value) / Decimal(number(previous[pos])) - 1) * 100)
                    buckets[name].append(point)
        output += [series('cpca', category + '/' + name, '万辆', 'MONTHLY_CPCA', points)
                   for name, points in buckets.items() if points]
    return output, {'unit_basis': 'AKShare reviewed CPCA interface documentation: 万辆',
                    'unit_source': 'https://akshare.akfamily.xyz/data/industrial/industrial.html',
                    'transport': 'PUBLIC_HTTP_NOT_TLS', 'scope': 'PRODUCTION_WHOLESALE_RETAIL_EXPORT_NOT_INVENTORY'}


def eastmoney(family, raw):
    data = decode(raw)
    m.check(data.get('success') is True and data.get('code') == 0, 'statistical provider response unsuccessful')
    rows_ = data.get('result', {}).get('data')
    m.check(isinstance(rows_, list) and 1 <= len(rows_) <= 30, 'statistical rows missing or excessive')
    fields = [('BASE_SAME', '工业生产者出厂价格同比', '%', 'MONTHLY_REPORTED_YOY')]
    if family == 'logistics':
        fields = [('INDICATOR_VALUE', '物流业景气指数', '指数点', 'MONTHLY_DIFFUSION_INDEX')]
    elif family == 'tanker':
        fields = [('INDICATOR_VALUE', '波罗的海原油运价指数BDTI', '指数点', 'SOURCE_DATED_FREIGHT_INDEX')]
    output = []
    for field, label, unit, basis in fields:
        points = []
        for row in rows_:
            value = number(row.get(field))
            if value is None:
                continue
            day = date.fromisoformat(str(row['REPORT_DATE'])[:10])
            points.append({'period': day.isoformat() if family == 'tanker' else day.strftime('%Y-%m'), 'value': value})
        output.append(series(family, label, unit, basis, points))
    return output, {'publication_at': None, 'scope': 'PROVIDER_MIRROR_NOT_INDEPENDENT_NBS_OR_BALTIC_CONFIRMATION',
                    'deduplication': 'IDENTICAL_PERIOD_ROWS_COLLAPSED_CONFLICTS_REJECTED'}


def memory(raw):
    soup = BeautifulSoup(raw, 'html.parser')
    output = []
    for tbody_id, category in (('tb_NationalDramSpotPrice', 'DRAM'), ('tb_NationalFlashSpotPrice', 'NAND')):
        node = soup.find(id=tbody_id)
        if node is None:
            continue
        table = node if node.name == 'table' else node.find_parent('table')
        m.check(table is not None, 'memory quote table missing')
        before = table.find_previous(class_='tab_time')
        stamp_text = before.get_text(' ', strip=True) if before else ''
        match = re.search(r'([A-Za-z]{3})\.(\d{1,2})\s+(20\d{2})\s+(\d{2}:\d{2}).*GMT\+8', stamp_text)
        m.check(match is not None, 'memory source quote timestamp missing')
        stamp = datetime.strptime(' '.join(match.groups()), '%b %d %Y %H:%M').replace(tzinfo=timezone(timedelta(hours=8)))
        header = text(table.get_text())
        m.check('SessionAverage' in header and 'DailyHigh' in header, 'memory quote header changed')
        for row in rows(node):
            if len(row) < 7 or number(row[5]) is None:
                continue
            output.append(series('memory', category + '/' + row[0], 'UNKNOWN_SOURCE_CURRENCY',
                'PUBLIC_SPOT_SESSION_AVERAGE_NOT_CONTRACT_OR_EXECUTED_PRICE',
                [{'period': stamp.isoformat(), 'value': number(row[5]), 'reported_change_pct': number(row[6])}],
                unit_status='Currency not established by retained public table; no cross-source value comparison'))
    m.check(len(output) >= 2, 'public memory quote rows missing')
    return output, {'scope': 'PUBLIC_VISIBLE_QUOTES_ONLY_NO_MEMBER_HISTORY_OR_PAYWALL_BYPASS',
                    'publication_at': None, 'unit_status': 'UNKNOWN_REPORTED_EXPLICITLY'}


def allowed_url(url):
    parsed = urlsplit(url)
    m.check(not parsed.username and not parsed.password and not parsed.fragment, 'unsafe source URL')
    m.check(url in {EM, CPCA, MEMORY, NBS, NBS + 'index_1.html', NBS + 'index_2.html'}
            or re.fullmatch(r'https://www\.stats\.gov\.cn/sj/zxfb/20\d{4}/t20\d{6}_\d+\.html', url),
            'source URL outside reviewed public scope')


def catalog(raw, url):
    found = {}
    for a in BeautifulSoup(raw, 'html.parser').find_all('a', href=True):
        title = text(a.get_text(' ', strip=True))
        matches = [key for key, pattern in PROFILES.items() if re.search(pattern, title)]
        if not matches:
            continue
        target = urljoin(url, a['href'])
        allowed_url(target)
        for key in matches:
            found.setdefault(key, []).append((target, title))
    return found


def normalize(records, files, *, cutoff):
    cutoff_date = m.clock(cutoff).astimezone(timezone(timedelta(hours=8))).date()
    sections, output = {}, []
    for family in FAMILIES:
        candidates = [r for r in records if r['id'] == family]
        m.check(len(candidates) <= 1, 'duplicate source family')
        record = candidates[0] if candidates else {'id': family, 'status': 'NOT_CAPTURED'}
        section = {'status': record['status'], 'source': record, 'series_count': 0}
        if record['status'] == 'CAPTURED':
            try:
                raw = files[m.safe_path(record['file'])]
                if family.startswith('nbs-'):
                    values, context = official(family, raw, record['title'])
                elif family == 'cpca':
                    values, context = cars(raw)
                elif family == 'memory':
                    values, context = memory(raw)
                else:
                    values, context = eastmoney(family, raw)
                for item in values:
                    for point in item['points']:
                        day = point['period'][:10] if len(point['period']) >= 10 else point['period'] + '-01'
                        m.check(date.fromisoformat(day) <= cutoff_date, 'future statistical observation rejected')
                    key = item['latest']['period']
                    anchor = date.fromisoformat(key[:10] if len(key) >= 10 else key + '-01')
                    item['period_age_days'] = (cutoff_date - anchor).days
                    threshold = 7 if family in {'memory', 'tanker'} else 45 if family == 'nbs-goods' else 100
                    item['freshness'] = 'STALE_OR_DELAYED_SOURCE_PERIOD' if item['period_age_days'] > threshold else 'WITHIN_DISCLOSURE_WINDOW_NOT_NEW_TODAY'
                    item['source_record_id'] = family
                sections[family] = {**section, **context, 'status': 'OBSERVATIONS_AVAILABLE', 'series_count': len(values)}
                output.extend(values)
                continue
            except (ValueError, KeyError, TypeError, AttributeError, IndexError, InvalidOperation) as exc:
                section.update(status='SOURCE_SHAPE_OR_PERIOD_REJECTED', error_type=type(exc).__name__)
        sections[family] = section
    m.check(len(output) <= 1024 and len({r['id'] for r in output}) == len(output), 'industrial identity or output bound')
    available = sum(s['status'] == 'OBSERVATIONS_AVAILABLE' for s in sections.values())
    return {'version': VERSION, 'sections': sections, 'series': output, 'cutoff': cutoff,
            'status': 'AVAILABLE' if available == len(FAMILIES) else 'PARTIAL' if available else 'UNAVAILABLE_NOT_QUIET',
            'coverage': {'expected_families': len(FAMILIES), 'available_families': available, 'series_count': len(output)},
            'known_scope_gaps': ['Full industry coverage not established', 'Company orders and beneficiaries not inferred',
                'Semiconductor fab utilization and contract-price inventory not covered',
                'SCFI/CCFI container freight not replaced by BDTI or freight futures',
                'Current public values are not historical point-in-time snapshots'], **AUTHORITY}


def compare(current, previous=None):
    old = {s['id']: s for s in (previous or {}).get('series', [])}
    changes = []
    for item in current['series']:
        prior = old.get(item['id'])
        kind = 'BASELINE_FIRST_SEEN' if prior is None else 'UNCHANGED'
        if prior is not None:
            before, after = prior['latest'], item['latest']
            if after['period'] > before['period']:
                kind = 'NEW_STATISTICAL_PERIOD'
            elif after['period'] < before['period']:
                kind = 'SOURCE_PERIOD_REGRESSED'
            elif after != before:
                kind = 'SAME_PERIOD_REVISION'
        if kind != 'UNCHANGED':
            changes.append({'series_id': item['id'], 'kind': kind, 'period': item['latest']['period'],
                            'previous': prior['latest'] if prior else None})
    return {'comparison': 'EXACT_PREVIOUS_SAVED_CAPTURE' if previous else 'NO_PREVIOUS_BASELINE',
            'changes': changes, 'unchanged_count': len(current['series']) - len(changes),
            'missing_previous_series': sorted(set(old) - {s['id'] for s in current['series']}),
            'meaning': 'SOURCE_INCREMENT_NOT_ECONOMIC_INFLECTION_OR_RESEARCH_DECISION'}


def render(report, comparison=None):
    def esc(x):
        return html.escape(str(x), quote=True).replace('|', '&#124;').replace('\n', ' ')
    lines = ['# 产业雷达｜需求、生产、库存与利润、价格、物流', '',
        '机械观察，不自动认定产业拐点或公司受益；统计期、来源更新时间和取得时间分别保留。',
        '月度数量、累计财务、期末存量、扩散指数及现货报价不能混排；同比不是环比，价格不是利润。',
        f"本次状态：{report['status']}；来源族 {report['coverage']['available_families']}/{len(FAMILIES)}；序列 {len(report['series'])}。", '']
    featured = [x for x in report['series'] if x['basis'] != 'YEAR_TO_DATE_OUTPUT' and any(k in x['label'] for k in ('新订单','原材料库存','在手订单','规上工业/','狭义乘用车/','集成电路','工业机器人','BDTI','物流业景气'))]
    lines += ['## 本次可读线索（不解释原因）', '']
    for item in featured[:24]:
        last = item['latest']; prior = item['points'][-2] if len(item['points']) > 1 else None
        delta = {k:v for k,v in last.items() if k.startswith(('reported_', 'computed_'))}
        lines.append('- ' + esc(item['label']) + '：' + esc(last['period']) + '，' + esc(last['value']) + ' ' + esc(item['unit']) + ('；前期 ' + esc(prior['period']) + ' ' + esc(prior['value']) if prior else '') + ('；' + esc(delta) if delta else ''))
    lines += ['', '全部序列在下面逐源列出；首页不是采集或研究准入范围。', '']
    if comparison:
        kinds = {}
        for c in comparison['changes']:
            kinds[c['kind']] = kinds.get(c['kind'], 0) + 1
        lines += ['## 相对上次保存', '', esc(kinds) + '；未变序列 ' + str(comparison['unchanged_count']),
                  '初次看见旧统计资料不叫今日新事件；来源缺失不叫需求下降。', '']
    for family, section in report['sections'].items():
        lines += ['## ' + family, '', '状态：' + esc(section['status'])]
        source = section['source']
        if source.get('url'):
            lines += ['来源：' + esc(source['url']), '取得：' + esc(source.get('received_at'))]
        if section.get('publication_at'):
            lines += ['原发布日期：' + esc(section['publication_at'])]
        items = [s for s in report['series'] if s['family'] == family]
        if not items:
            lines += ['本来源尚无合格观察；不能解释为没有产业变化。', '']; continue
        lines += ['', '| 指标 | 统计期 / 口径 | 原值 / 单位 | 同比或原披露变化 | 可比前期 / 来源新鲜度 |',
                  '|---|---|---|---|---|']
        for item in items:
            last = item['latest']
            delta = {k: v for k, v in last.items() if k.startswith(('reported_', 'computed_'))}
            prior = item['points'][-2] if len(item['points']) > 1 else None
            lines += ['| ' + ' | '.join(esc(v) for v in (item['label'], last['period'] + ' / ' + item['basis'],
                str(last['value']) + ' / ' + item['unit'], delta or '未提供',
                (str(prior) if prior else '未保存独立前期值') + ' / ' + item['freshness'])) + ' |']
        lines.append('')
    lines += ['## 尚未覆盖', '', *['- ' + x for x in report['known_scope_gaps']], '',
              '[全部历史点、来源时钟与字段](industry-fundamentals.json)', '', 'AI Investment Authority = NONE。', '']
    return '\n'.join(lines)


def validate_identity(identity):
    m.check(set(identity) == {'repository', 'workflow', 'ref', 'event', 'code_commit', 'run_id', 'attempt', 'trigger_run_id'}, 'industrial run identity shape')
    m.check(identity['repository'] == m.REPOSITORY and identity['workflow'] == WORKFLOW
            and identity['ref'] == 'refs/heads/main' and identity['event'] in {'workflow_dispatch', 'workflow_run'}
            and identity['attempt'] == 1 and type(identity['run_id']) is int and identity['run_id'] > 0
            and m.SHA.fullmatch(identity['code_commit']), 'industrial run identity rejected')


def capture(output, identity, *, get=None, now=None):
    validate_identity(identity)
    now = now or (lambda: datetime.now(timezone.utc).isoformat())
    root = Path(output); root.mkdir(parents=True, exist_ok=False)
    session = requests.Session(); session.trust_env = False
    session.headers.update({'User-Agent': 'Mozilla/5.0 DecisionKernel-public-industry', 'Accept-Encoding': 'identity'})
    started = time.monotonic(); records, files = [], {}
    def request(key, url, params=None, title=None):
        allowed_url(url)
        record = {'id': key, 'url': url, 'params': params or {}, 'title': title,
                  'requested_at': now(), 'status': 'NOT_ATTEMPTED_BUDGET'}
        if len(records) < MAX_REQUESTS and time.monotonic() - started < MAX_SECONDS:
            try:
                if get:
                    status, raw = get(url, params or {})
                else:
                    with session.get(url, params=params, timeout=(7, 12), allow_redirects=False, stream=True) as response:
                        status = response.status_code
                        record['http_status'] = status
                        m.check(status == 200, 'public source HTTP not successful')
                        chunks, size = [], 0
                        for chunk in response.iter_content(65536):
                            size += len(chunk); m.check(size <= MAX_BYTES, 'public source body too large')
                            chunks.append(chunk)
                        raw = b''.join(chunks)
                record['http_status'] = status
                m.check(status == 200 and 0 < len(raw) <= MAX_BYTES, 'public source response bound/status')
                name = 'raw/' + key + '.body'
                files[name] = raw
                record.update(status='CAPTURED', file=name, bytes=len(raw), sha256=m.sha256(raw))
            except (requests.RequestException, ValueError, OSError) as exc:
                record.update(status='SOURCE_UNAVAILABLE', error_type=type(exc).__name__)
        record['received_at'] = now(); records.append(record)
        return files.get(record.get('file'))
    links = {}
    for i, url in enumerate((NBS, NBS + 'index_1.html', NBS + 'index_2.html')):
        raw = request('catalog-' + str(i), url)
        if raw:
            try:
                for key, values in catalog(raw, url).items():
                    links.setdefault(key, []).extend(values)
            except (ValueError, TypeError):
                records[-1]['discovery_status'] = 'LINK_SCOPE_REJECTED'
    for key in PROFILES:
        options = sorted(set(links.get(key, [])), reverse=True)
        if options:
            url, title = options[0]
            request(key, url, title=title)
        else:
            records.append({'id': key, 'status': 'NOT_FOUND_IN_BOUNDED_RELEASE_CATALOG', 'received_at': now()})
    request('cpca', CPCA, {'charttype': '1'})
    for key, spec in EM_SPECS.items():
        request(key, EM, {**spec, 'pageNumber': '1', 'pageSize': '30', 'sortColumns': 'REPORT_DATE',
                         'sortTypes': '-1', 'source': 'WEB', 'client': 'WEB'})
    request('memory', MEMORY)
    cutoff = now()
    result = normalize(records, files, cutoff=cutoff)
    files['observations.json'] = m.json_bytes(result)
    manifest = {'version': VERSION, 'identity': identity, 'records': records, 'cutoff': cutoff,
                'files': {name: {'bytes': len(raw), 'sha256': m.sha256(raw)} for name, raw in files.items()},
                'observation_hash': canonical_hash(result), **AUTHORITY}
    manifest['capture_hash'] = canonical_hash(manifest)
    files['capture.json'] = m.json_bytes(manifest)
    for name, raw in files.items():
        target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    replay(files, identity, cutoff=cutoff)
    (root / 'summary.md').write_text(render(result), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'coverage': result['coverage'],
                      'capture_hash': manifest['capture_hash'], 'network_replay_calls': 0}, ensure_ascii=False))
    return result


def validate_source_record(record):
    key = record['id']
    if 'url' not in record:
        m.check(key in FAMILIES and record['status'] == 'NOT_FOUND_IN_BOUNDED_RELEASE_CATALOG', 'invalid missing source receipt')
        return
    url, params = record['url'], record.get('params')
    if key.startswith('catalog-'):
        index = int(key.removeprefix('catalog-'))
        m.check(0 <= index <= 2 and url == (NBS,NBS+'index_1.html',NBS+'index_2.html')[index] and params == {}, 'catalog receipt differs')
    elif key in PROFILES:
        m.check(re.search(PROFILES[key],record.get('title') or '') is not None and params == {}, 'official release contract differs')
        m.check(url.startswith(NBS) and '/t20' in url, 'official release source differs')
    elif key in EM_SPECS:
        expected = {**EM_SPECS[key], 'pageNumber':'1','pageSize':'30','sortColumns':'REPORT_DATE',
                    'sortTypes':'-1','source':'WEB','client':'WEB'}
        m.check(url == EM and params == expected, 'statistical series request identity differs')
    elif key == 'cpca':
        m.check(url == CPCA and params == {'charttype':'1'}, 'CPCA category request differs')
    elif key == 'memory':
        m.check(url == MEMORY and params == {}, 'memory source request differs')
    else:
        raise ValueError('unreviewed source record')


def replay(files, identity, *, cutoff):
    receipt = decode(files['capture.json']); m.sealed(receipt, 'capture_hash')
    validate_identity(receipt['identity'])
    m.check(receipt['identity'] == identity and receipt['version'] == VERSION, 'industrial capture identity differs')
    m.check(all(receipt.get(k) == v for k, v in AUTHORITY.items()), 'industrial capture authority differs')
    m.check(m.clock(receipt['cutoff']) <= m.clock(cutoff), 'industrial capture is in future')
    m.check(set(files) <= set(receipt['files']) | {'capture.json', 'summary.md'}, 'unlisted industrial archive files')
    for name, meta in receipt['files'].items():
        raw = files[m.safe_path(name)]
        m.check(len(raw) == meta['bytes'] and m.sha256(raw) == meta['sha256'], 'industrial captured bytes changed')
    m.check(len(receipt['records']) <= MAX_REQUESTS, 'industrial request inventory bound')
    m.check(len({r['id'] for r in receipt['records']}) == len(receipt['records']), 'duplicate industrial request identity')
    for record in receipt['records']:
        validate_source_record(record)
        if record.get('url'):
            allowed_url(record['url'])
            m.check(m.clock(record['requested_at']) <= m.clock(record['received_at']) <= m.clock(receipt['cutoff']), 'industrial request clocks differ')
        if record['status'] == 'CAPTURED':
            raw = files[m.safe_path(record['file'])]
            m.check(m.sha256(raw) == record['sha256'] and len(raw) == record['bytes'], 'industrial receipt differs')
    report = normalize(receipt['records'], files, cutoff=receipt['cutoff'])
    m.check(canonical_hash(report) == receipt['observation_hash'] and m.json_bytes(report) == files['observations.json'], 'industrial observations cannot be rebuilt')
    return report, receipt


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True); args = parser.parse_args()
    env = os.environ
    identity = {'repository': env.get('GITHUB_REPOSITORY'), 'workflow': WORKFLOW,
        'ref': env.get('GITHUB_REF'), 'event': env.get('GITHUB_EVENT_NAME'), 'code_commit': env.get('GITHUB_SHA'),
        'run_id': int(env.get('GITHUB_RUN_ID', '0')), 'attempt': int(env.get('GITHUB_RUN_ATTEMPT', '0')),
        'trigger_run_id': env.get('TRIGGER_RUN_ID') or None}
    capture(args.output, identity)


if __name__ == '__main__':
    main()
