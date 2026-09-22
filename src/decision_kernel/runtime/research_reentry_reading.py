"""Recover existing Research context before interpreting another saved observation.

A same-reading projection only: no retrieval service, research execution, decision
or automatic thesis update. Existing source/Watch/question readers own validation.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re
from urllib.parse import quote

from ..identity import canonical_hash
from . import current_state as model
from .radar_company_reading import _code, retained_bytes

VERSION = 'research-asset-reentry-reading-v1'
REPORT = 'details/research/asset-reentry.json'
DETAIL = 'details/research/asset-reentry.md'
MAX_COMPANIES, MAX_ASSETS, MAX_OBSERVATIONS = 64, 256, 64
MAX_REPORT_BYTES = 512 * 1024
SECURITY = re.compile(r'[0-9]{6}\.(?:SH|SZ|BJ)\Z')
AUTHORITY = {**model.AUTHORITY, 'automatic_admission': False,
             'new_research_executions': 0, 'odds_recomputed': False,
             'market_requests': 0, 'model_calls': 0, 'new_attention_events': 0}
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError)


def _meta(path: str, raw: bytes) -> dict:
    return {'read_path': path, 'bytes': len(raw), 'sha256': model.sha256(raw),
            'git_blob': model.blob_sha(raw),
            'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}


def _read(files: dict, source: dict) -> bytes:
    raw = retained_bytes(files, source)
    model.check(len(raw) <= model.MAX_ARCHIVE, 're-entry existing source byte bound')
    return raw


def _source_check(files: dict, sources: list) -> dict:
    """Byte verification is not semantic acceptance or a new source request."""
    gaps = []
    for source in sources:
        try:
            _read(files, source)
        except ERRORS as exc:
            gaps.append({'source': deepcopy(source), 'error_type': type(exc).__name__})
    return {'status': ('RETAINED_BYTES_VERIFIED' if sources and not gaps else
                       'SOURCE_BYTES_UNAVAILABLE' if gaps else 'NO_BODY_REFERENCE'),
            'reference_count': len(sources), 'gaps': gaps,
            'meaning': 'BYTE_IDENTITY_ONLY_NOT_ECONOMIC_OR_HUMAN_ACCEPTANCE'}


def _json_source(files: dict, source: dict) -> dict:
    value = json.loads(_read(files, source))
    model.check(isinstance(value, dict), 're-entry object required')
    return value


def _next_step(row: dict) -> str:
    if any(a['source_check']['gaps'] for a in row['assets']):
        return 'RECOVER_MISSING_RETAINED_BYTES'
    if any(a.get('use') == 'METHOD_SUPPLEMENT' for a in row['assets']):
        return 'RECONCILE_EXISTING_METHOD_REVIEW'
    watch = row.get('saved_watch')
    if watch and watch['status'] == 'PRICE_UNAVAILABLE_NOT_QUIET':
        return 'PRICE_INPUT_UNAVAILABLE_NOT_THESIS_FAILURE'
    if watch and watch['status'] == 'NEEDS_REVIEW_NOW':
        return 'REVIEW_SAVED_PRICE_CONDITION_AND_RESEARCH_PREREQUISITES'
    if row['saved_observations']:
        return 'COMPARE_SAVED_OBSERVATION_WITH_EXISTING_RESEARCH'
    if row['archives'] and not row['assets']:
        return 'RECOVER_REGISTERED_ARCHIVE'
    if watch and watch['status'] == 'ACTIVE_ODDS_WATCH':
        return 'WAITING_SAVED_PRICE_BOUNDARY_NOT_THESIS_NO_CHANGE'
    return 'NO_OBSERVATION_ASSOCIATION_IN_THIS_READING_NOT_NO_CHANGE'


def build(baseline: dict, files: dict[str, bytes]) -> dict:
    """Use only the supplied pinned package; keep the entire declared asset scope."""
    model.validate_read_package(baseline)
    model.read_package_bytes(baseline)
    research = baseline['research']
    rows, gaps = {}, deepcopy(research.get('gaps', []))

    def company(code):
        model.check(isinstance(code, str) and SECURITY.fullmatch(code), 're-entry security invalid')
        _code(code)
        if code not in rows:
            model.check(len(rows) < MAX_COMPANIES, 're-entry company bound')
            rows[code] = {'thscode': code, 'assets': [], 'archives': [],
                          'saved_observations': [], 'saved_watch': None}
        return rows[code]

    def asset(code, value, sources):
        model.check(sum(len(r['assets']) + len(r['archives']) for r in rows.values())
                    < MAX_ASSETS, 're-entry asset bound')
        company(code)['assets'].append({**deepcopy(value),
                                       'source_check': _source_check(files, sources)})

    records = research.get('records', [])
    model.check(isinstance(records, list) and len({r['id'] for r in records}) == len(records),
                're-entry purpose index ambiguous')
    for record in records:
        code = record.get('case')
        if not isinstance(code, str) or not SECURITY.fullmatch(code):
            continue  # Explicit non-security navigation is not a company asset.
        asset(code, {'kind': 'PURPOSE_REFERENCE', **record}, [record.get('source')])
    from .research_archive_index import validate, entry_url
    for record in research.get('on_demand_archives', []):
        code = record.get('case')
        if not isinstance(code, str) or not SECURITY.fullmatch(code):
            continue
        validate(record)
        model.check(sum(len(r['assets']) + len(r['archives']) for r in rows.values())
                    < MAX_ASSETS, 're-entry asset bound')
        company(code)['archives'].append({'record': deepcopy(record), 'url': entry_url(record),
            'status': 'REGISTERED_LOCATOR_NOT_BODY_RECOVERED'})
    work = research.get('stock_business_work', {})
    if work.get('status') == 'READ_OK':
        for item in work.get('items', []):
            states = [item] + [item[k] for k in ('source_recovery', 'source_successor',
                      'source_successor_continuation') if k in item]
            for state in states:
                sources = state.get('sources', {})
                if state.get('status') == 'NOT_STARTED' and not sources:
                    continue  # #489: placeholders are not saved Research.
                if sources:
                    model.check(all(state.get(k) == v for k, v in model.AUTHORITY.items()),
                                're-entry work authority differs')
                    asset(item['thscode'], {'kind': 'SAVED_BUSINESS_WORK', 'record': state},
                          list(sources.values()))
    else:
        gaps.append({'kind': 'stock_business_work', 'status': work.get('status', 'NOT_CONFIGURED')})
    question_status = research.get('reviewed_question_work', {})
    if question_status.get('structured'):
        before = deepcopy(rows)
        try:
            report = _json_source(files, question_status['structured'])
            for item in report['question_work']['items']:
                model.check(all(item.get(k) == v for k, v in model.AUTHORITY.items()),
                            're-entry question authority differs')
                sources = list(item.get('sources', {}).values())
                if item.get('question_source'):
                    sources.append(item['question_source'])
                asset(item['thscode'], {'kind': 'SAVED_QUESTION', 'record': item}, sources)
        except ERRORS as exc:
            rows = before
            gaps.append({'kind': 'reviewed_question_work', 'status': 'UNAVAILABLE_OR_REJECTED',
                         'error_type': type(exc).__name__})
    else:
        gaps.append({'kind': 'reviewed_question_work', 'status': question_status.get('status', 'NOT_CONFIGURED')})

    # No company is added merely because it appeared in Radar or Watch.
    radar = research.get('radar_discovery', {})
    ref = radar.get('details', {}).get('company_reading')
    if ref:
        before = deepcopy(rows)
        try:
            report = _json_source(files, ref)
            projection = report['projection']
            model.check(report['projection_hash'] == canonical_hash(projection)
                        and radar.get('projection_hash') == report['projection_hash']
                        and all(projection.get(k) == v for k, v in model.AUTHORITY.items()),
                        're-entry Radar projection differs')
            model.check(model.clock(projection['generated_at']) <= model.clock(baseline['generated_at']),
                        're-entry future Radar source')
            model.check(isinstance(projection['companies'], list)
                        and len({i['thscode'] for i in projection['companies']}) == len(projection['companies']),
                        're-entry Radar company identity ambiguous')
            for item in projection['companies']:
                if item['thscode'] in rows:
                    model.check(len(item['origins']) <= MAX_OBSERVATIONS, 're-entry observation bound')
                    rows[item['thscode']]['saved_observations'].append({
                        'kind': 'SAVED_RADAR_ORIGINS', 'origins': deepcopy(item['origins']),
                        'source': deepcopy(ref), 'projection_hash': report['projection_hash'],
                        'meaning': 'TICKER_ASSOCIATION_NOT_SAME_QUESTION_OR_NEW_TRIGGER'})
        except ERRORS as exc:
            rows = before
            gaps.append({'kind': 'radar_discovery', 'status': 'UNAVAILABLE_OR_REJECTED',
                         'error_type': type(exc).__name__})
    else:
        gaps.append({'kind': 'radar_discovery', 'status': radar.get('status', 'NOT_CONFIGURED')})
    stock_lane = baseline['lanes'].get('stock', {})
    stock = stock_lane.get('last_qualified_result') or {}
    stock_ref = stock.get('details', {}).get('reading/stock-reading.json')
    if stock_ref:
        before = deepcopy(rows)
        try:
            _read(files, stock_ref)
            for item in stock.get('dispositions', []):
                if item['thscode'] in rows:
                    rows[item['thscode']]['saved_observations'].append({
                        'kind': 'SAVED_STOCK_DISPOSITION', 'record': deepcopy(item),
                        'market_session': stock.get('market_session'),
                        'lane_health': stock_lane.get('health', 'UNKNOWN'), 'source': deepcopy(stock_ref),
                        'meaning': 'HISTORICAL_DISPOSITION_NOT_NEW_PRICE_QUALIFICATION'})
        except ERRORS as exc:
            rows = before
            gaps.append({'kind': 'stock', 'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__})
    watch_product = (baseline['lanes'].get('inbox', {}).get('last_qualified_result') or {})
    watch = watch_product.get('odds_watch', {})
    if watch.get('status') == 'TYPED_ODDS_WATCH_READ_OK':
        before = deepcopy(rows)
        try:
            from .odds_watch import validate_report
            watch_ref = watch_product['details']['odds-watch/watch.json']
            report = _json_source(files, watch_ref)
            model.check(report == watch['report'], 're-entry Watch bytes differ')
            validate_report(report)
            model.check(model.clock(report['watch']['observed_at']) <= model.clock(baseline['generated_at']),
                        're-entry future Watch source')
            for item in report['watch']['active_cases']:
                if item['ticker'] in rows:
                    rows[item['ticker']]['saved_watch'] = {**deepcopy(item),
                        'observed_at': report['watch']['observed_at'], 'source_report': deepcopy(watch_ref),
                        'watch_hash': report['watch_hash'],
                        'qualification': 'SAVED_TYPED_WATCH_NOT_REQUALIFIED_CURRENT_MARKET'}
        except ERRORS as exc:
            rows = before
            gaps.append({'kind': 'odds_watch', 'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__})
    else:
        gaps.append({'kind': 'odds_watch', 'status': watch.get('status', 'NOT_AVAILABLE')})

    for row in rows.values():
        row['next_step'] = _next_step(row)
        row['semantic_comparison'] = 'NOT_PERFORMED_BY_READING'
        row['human_acceptance'] = 'REFER_TO_EXACT_ORIGINAL_RECORD_NOT_TRANSFERRED'
        row['numerical_odds_eligibility'] = 'REQUALIFY_FROZEN_RESEARCH_AND_MARKET_AT_ORIGINAL_ENTRY'
        row['association_id'] = canonical_hash({k: row[k] for k in
            ('thscode', 'assets', 'archives', 'saved_observations', 'saved_watch')})
    projection = {'version': VERSION, 'base_reading_hash': baseline['reading_hash'],
        'generated_at': baseline['generated_at'], 'companies': list(rows.values()), 'read_gaps': gaps,
        'coverage': {'companies': len(rows), 'assets': sum(len(r['assets']) for r in rows.values()),
            'archive_locators': sum(len(r['archives']) for r in rows.values()),
            'with_saved_observations': sum(bool(r['saved_observations']) for r in rows.values()),
            'with_saved_watch': sum(r['saved_watch'] is not None for r in rows.values()),
            'unavailable_assets': sum(bool(a['source_check']['gaps']) for r in rows.values() for a in r['assets']),
            'read_gap_count': len(gaps), 'complete_research_history': False, 'all_theses_checked': False},
        'semantics': 'RECOVER_EXISTING_RESEARCH_BEFORE_REVIEW_NOT_AUTOMATIC_THESIS_MONITORING', **AUTHORITY}
    result = {'projection': projection, 'projection_hash': canonical_hash(projection)}
    model.check(len(model.json_bytes(result)) <= MAX_REPORT_BYTES, 're-entry report byte bound')
    return result


def render(report: dict) -> str:
    from .reviewed_question_reading import _text
    p = report['projection']
    model.check(report['projection_hash'] == canonical_hash(p), 're-entry report hash differs')
    lines = ['# 旧研究再进入：先找回，再解释变化', '',
        '仅关联同一读取包内的已有材料与保存观察；不启动研究、不判断thesis是否改变、不继承Human接受。',
        '按各原件日期阅读；保存的价格触界不是今天的新提醒，未关联变化不等于已检查且无变化。', '']
    for row in p['companies']:
        lines += ['## ' + _text(row['thscode']), '', '下一步：' + _text(row['next_step']), '']
        for item in row['assets']:
            label = item.get('id') or item.get('record', {}).get('execution_id') or item['kind']
            lines += ['- ' + _text(label) + '：' + _text(item['kind']) + ' / '
                      + _text(item['source_check']['status'])]
            sources = ([item.get('source')] if item['kind'] == 'PURPOSE_REFERENCE' else
                       list(item.get('record', {}).get('sources', {}).values()))
            for source in sources:
                if isinstance(source, dict) and isinstance(source.get('read_path'), str):
                    try:
                        path = model.safe_path(source['read_path'])
                        model.check(source.get('read_ref_rule') == 'USE_THE_SAME_PINNED_READING_COMMIT',
                                    're-entry link must stay pinned')
                        lines.append('  - [原保存材料](' + quote(path, safe='/') + ')')
                    except ERRORS:
                        lines.append('  - 原材料入口未核验。')
        for archive in row['archives']:
            lines.append('- [按需恢复：' + _text(archive['record']['id']) + '](' + archive['url']
                         + ')；只有定位，本页没有恢复正文。')
        lines += ['- 关联保存观察组：' + str(len(row['saved_observations'])) + '；不是新事件数。']
        if row['saved_watch']:
            w = row['saved_watch']
            lines += ['- 原价格条件状态：' + _text(w['status']) + '；原观察时间：' + _text(w['observed_at'])]
        lines += ['']
    if p['read_gaps']:
        lines += ['## 读取范围缺口', '', '部分来源未提供或未能核验；不能据此宣称全部thesis无需复核。', '']
    return '\n'.join(lines)


def attach(collector, baseline: dict) -> dict:
    """Atomic local composition in the original publisher; never perform GET."""
    from . import current_state_delivery as delivery
    from .institutional_radar_reading import _reserve
    model.validate_read_package(baseline)
    replacements = dict(collector.files)
    research = deepcopy(baseline['research'])
    try:
        report = build(baseline, collector.files)
        raw, page = model.json_bytes(report), render(report).encode()
        replacements.update({REPORT: raw, DETAIL: page})
        research['asset_reentry'] = {'status': ('READ_OK_WITH_GAPS' if report['projection']['read_gaps']
            or report['projection']['coverage']['unavailable_assets'] else 'READ_OK_WITH_EXPLICIT_SCOPE'),
            'coverage': report['projection']['coverage'], 'projection_hash': report['projection_hash'],
            'structured': _meta(REPORT, raw), 'details': _meta(DETAIL, page),
            'meaning': 'RETENTION_ASSOCIATION_NOT_THESIS_ACCEPTANCE_OR_RESEARCH_EXECUTION', **AUTHORITY}
        addition = '\n[旧研究再进入：已有材料、原条件与保存观察](' + DETAIL + ')；不是新研究或自动提醒。\n'
    except ERRORS as exc:
        research['asset_reentry'] = {'status': 'UNAVAILABLE_OR_REJECTED',
            'error_type': type(exc).__name__, 'meaning': 'REENTRY_READ_GAP_NOT_NO_CHANGE', **AUTHORITY}
        addition = '\n旧研究再进入读取存在缺口；原研究和其他阅读结果保留，不能据此判断无变化。\n'
    result = model.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    replacements['current-state.json'] = model.read_package_bytes(result)
    replacements['README.md'] += addition.encode()
    model.check(sum(map(len, replacements.values())) <= delivery.MAX_RETAINED_OUTPUT,
                're-entry retained-byte budget')
    _reserve(collector, replacements=replacements)
    collector.files = replacements
    return result
