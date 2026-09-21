"""Display a saved no-launch batch disposition in the existing question reading.

This records routing work, not economic qualification, admission or execution.
Reuse the original batch identity, Git reader, archive links and publisher bounds.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import re

from . import current_state as model
from . import current_state_delivery as delivery
from . import external_research_identity as identity

PATH = 'research_runs/stock-batch-disposition.json'
FORMAT = 'stock-batch-disposition-v1'
MAX_BYTES = 16 * 1024
RECORDED = 'FULL_BATCH_DISPOSITION_RECORDED_NO_NEW_EXECUTION'
STALE = 'SAVED_DISPOSITION_FOR_DIFFERENT_BATCH_NOT_APPLIED'
GAP = 'BATCH_DISPOSITION_UNAVAILABLE_OR_REJECTED'
MEANING = 'ROUTING_REVIEW_NOT_ECONOMIC_QUALIFICATION_OR_NO_OPPORTUNITIES'
CATEGORIES = {'ORIGINAL_PRICE_DISPOSITION_ONLY', 'DATA_UNAVAILABLE', 'EXISTING_RESEARCH'}


def project(review: dict, scope: dict, archives: list[dict], now: str) -> dict:
    """Validate a researcher declaration against every original row; never select."""
    keys = {'format', 'reviewed_reading_commit', 'reviewed_at', 'batch_id',
            'source_run_id', 'market_session', 'question_source', 'items', *model.AUTHORITY}
    model.check(set(review) == keys and review['format'] == FORMAT
                and all(review[k] == v for k, v in model.AUTHORITY.items())
                and review['question_source'] is None, 'batch disposition declaration invalid')
    model.check(model.SHA.fullmatch(review['reviewed_reading_commit'] or '') is not None
                and re.fullmatch(r'[0-9a-f]{64}', review['batch_id'] or '') is not None
                and type(review['source_run_id']) is int and review['source_run_id'] > 0
                and date.fromisoformat(review['market_session']).isoformat() == review['market_session']
                and date.fromisoformat(review['market_session']) <= model.clock(review['reviewed_at']).date()
                and model.clock(review['reviewed_at']) <= model.clock(now),
                'batch disposition identity or clock invalid')
    items = review['items']
    model.check(isinstance(items, list) and 1 <= len(items) <= 16
                and all(isinstance(i, dict) and set(i) == {
                    'thscode', 'disposition', 'reason', 'existing_execution_id', 'progress_record_ids'}
                    for i in items), 'batch disposition items invalid')
    for item in items:
        model.check(isinstance(item['thscode'], str)
                    and re.fullmatch(r'[0-9]{6}\.(SH|SZ)', item['thscode']) is not None
                    and item['disposition'] in CATEGORIES
                    and isinstance(item['reason'], str) and 1 <= len(item['reason'].strip()) <= 2000
                    and not any(ord(c) < 32 for c in item['reason'])
                    and (item['existing_execution_id'] is None or
                         isinstance(item['existing_execution_id'], str))
                    and isinstance(item['progress_record_ids'], list)
                    and len(item['progress_record_ids']) <= 3
                    and all(isinstance(s, str) and 0 < len(s) <= 200 for s in item['progress_record_ids'])
                    and len(set(item['progress_record_ids'])) == len(item['progress_record_ids']),
                    'batch disposition row invalid')
    model.check(len({i['thscode'] for i in items}) == len(items), 'batch disposition duplicate security')
    common = {'reviewed_at': review['reviewed_at'], 'reviewed_reading_commit': review['reviewed_reading_commit'],
              'saved_batch_id': review['batch_id'], 'saved_market_session': review['market_session'],
              'research_execution': 'NOT_EXECUTED', 'meaning': MEANING, **model.AUTHORITY}
    if any(review[k] != scope.get(k) for k in ('batch_id', 'source_run_id', 'market_session')):
        return {**common, 'status': STALE, 'applied': False, 'items': []}
    rows = scope['items']
    model.check([i['thscode'] for i in items] == [r['thscode'] for r in rows],
                'batch disposition must cover every row in original order')
    model.check(isinstance(archives, list)
                and len({r['id'] for r in archives}) == len(archives), 'ambiguous progress index')
    by_id = {r['id']: r for r in archives}
    result = []
    for item, row in zip(items, rows, strict=True):
        relation = row.get('existing_research_relation')
        original = row['original_stock_disposition']
        if item['disposition'] == 'DATA_UNAVAILABLE':
            model.check(row['review_status'] == 'DATA_UNAVAILABLE_NOT_PRICE_REJECTED'
                        and original['input_failure'] is not None, 'data gap disposition differs')
        elif item['disposition'] == 'ORIGINAL_PRICE_DISPOSITION_ONLY':
            model.check(row['review_status'] == 'ORIGINAL_PRICE_DISPOSITION_ONLY'
                        and original['input_failure'] is None
                        and original['status'] == 'CONDITIONS_NOT_MET', 'original filter disposition differs')
        else:
            model.check(isinstance(relation, dict) and relation.get('execution_id')
                        and row['review_status'].startswith('EXISTING_BASELINE_')
                        and original['input_failure'] is None
                        and original['status'] == 'CONTRACT_CHECKED_RAW_READING',
                        'existing research disposition differs')
        expected = relation.get('execution_id') if isinstance(relation, dict) else None
        model.check(item['existing_execution_id'] == expected, 'original research root differs')
        links = []
        for record_id in item['progress_record_ids']:
            from .research_archive_index import entry_url
            entry = by_id[record_id]
            model.check(entry['case'] == row['thscode'] and item['disposition'] == 'EXISTING_RESEARCH'
                        and entry.get('archive', {}).get('format') == 'RESEARCH_PROGRESS'
                        and entry['archive'].get('question_id') == expected,
                        'progress locator must bind the same original question')
            links.append({'id': record_id, 'url': entry_url(entry),
                          'meaning': 'REGISTERED_LOCATOR_NOT_BODY_READ_OR_ACCEPTED'})
        result.append({**deepcopy(item), 'company_name': row.get('company_name'), 'progress_locators': links})
    return {**common, 'status': RECORDED, 'applied': True, 'items': result,
            'dispositioned_count': len(result), 'new_question_selected_count': 0,
            'economic_question_assessed': False}


def render(value: dict) -> str:
    from .reviewed_question_reading import _text
    lines = ['## 已保存的本批路由处置', '', '状态：' + _text(value['status']) + '。']
    if value.get('applied'):
        lines += ['已逐行记录 ' + str(value['dispositioned_count'])
                  + ' 个对象的处置，本次选择 0 个新执行。不是已穷尽经济问题、没有机会或业务 WAIT/DROP。',
                  '保存市场日：' + _text(value['saved_market_session'])
                  + '；处置记录时间：' + _text(value['reviewed_at']) + '。不是今日重采。', '']
        for item in value['items']:
            lines += ['- ' + _text(item.get('company_name') or item['thscode']) + ' ' + _text(item['thscode'])
                      + '：' + _text(item['reason'])]
            for link in item['progress_locators']:
                lines += ['  - [已登记的同问题进度：' + _text(link['id']) + '](' + link['url']
                          + ')；仅档案定位，本读取未取正文，不代表研究接受。']
    else:
        lines += ['此记录未应用到当前批次；不能据此判断当前批次没有新问题或已经完成审阅。']
    lines += ['', '下方自动观察、原价格处置与历史执行保持原样；处置留存不会授予执行权限。', '']
    return '\n'.join(lines)


def _meta(path: str, raw: bytes) -> dict:
    return {'read_path': path, 'bytes': len(raw), 'git_blob': model.blob_sha(raw),
            'sha256': model.sha256(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}


def attach(collector, baseline: dict) -> dict:
    """Compose into the same detail/root atomically, with no remote acquisition."""
    from . import reviewed_question_reading as reader
    from . import stock_research_reading as stock_reader
    from .read_blob_reuse import pending_blob_writes
    model.validate_read_package(baseline)
    summary = baseline['research'].get('reviewed_question_work', {})
    if not summary.get('structured'):
        return baseline  # Original question-reader gap remains explicit; no inferred zero.
    source_spec = summary['structured']
    body = collector.files[reader.REPORT]
    model.check(source_spec == _meta(reader.REPORT, body), 'batch disposition report binding differs')
    report = identity._json(body)
    replacements = dict(collector.files)
    try:
        raw = delivery.git_file(collector.root, collector.code_commit, PATH)
        model.check(len(raw) <= MAX_BYTES, 'batch disposition source too large')
        value = project(identity._json(raw), report['stock_review_scope'],
                        baseline['research'].get('on_demand_archives', []), collector.now())
        source_path = 'sources/git/' + model.blob_sha(raw) + '/stock-batch-disposition.json'
        shared = reader._legacy_sources(baseline)
        for item in report['question_work']['items']:
            shared.update(s['read_path'] for s in item.get('sources', {}).values())
            if item.get('question_source'):
                shared.add(item['question_source']['read_path'])
        model.check(len(shared | {source_path}) <= stock_reader.MAX_STOCK_SOURCE_FILES,
                    'batch disposition shared source-file bound')
        model.check(source_path not in replacements or replacements[source_path] == raw,
                    'batch disposition retained source conflict')
        replacements[source_path] = raw
        value['source'] = {'repository': model.REPOSITORY, 'ref': collector.code_commit,
                           'path': PATH, **_meta(source_path, raw)}
    except reader.ERRORS as exc:
        value = {'status': GAP, 'applied': False, 'items': [], 'error_type': type(exc).__name__,
                 'research_execution': 'NOT_EXECUTED', 'meaning': 'NOT_ZERO_OR_COMPLETED_REVIEW', **model.AUTHORITY}
    report['saved_batch_disposition'] = value
    report_raw = model.json_bytes(report)
    detail = (render(value) + '\n' + reader.render(report)).encode()
    replacements.update({reader.REPORT: report_raw, reader.DETAIL: detail})
    research = deepcopy(baseline['research'])
    work = research['reviewed_question_work']
    work.update(structured=_meta(reader.REPORT, report_raw), details=_meta(reader.DETAIL, detail),
                saved_batch_disposition={k: deepcopy(v) for k, v in value.items() if k != 'items'})
    result = model.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    replacements['current-state.json'] = model.read_package_bytes(result)
    replacements['README.md'] += ('\n本批路由处置：' + reader._text(value['status'])
        + '；选择新执行数：' + ('0' if value.get('applied') else '未知')
        + '。与经济问题审阅、Pre/Quick及Human接受分开；见上方同批详情。\n').encode()
    model.check(sum(map(len, replacements.values())) <= delivery.MAX_RETAINED_OUTPUT,
                'batch disposition retained-byte budget')
    model.check(collector.api.calls + pending_blob_writes(collector.api, replacements) + 7
                <= stock_reader.call_limit(collector.api), 'batch disposition publication reserve')
    collector.files = replacements
    return result
