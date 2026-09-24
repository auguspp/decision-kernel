"""Vibe-derived, bounded Eastmoney concept snapshots; never historical price paths.

Protocol/period fields and actual-page-size lesson adapted from
simonlin1212/Vibe-Research@7f3a08b85451b54c762898789e2dcaa5d7d2ec98,
.agents/skills/data-access/scripts/sources/eastmoney.py::board_fund_flow.
MIT, Copyright (c) 2026 simonlin1212; full notice in docs/vibe-concept-snapshot.md.
Reuse Kernel's HTTP isolation, safe JSON, Decimal and canonical identity helpers.
"""
from __future__ import annotations

import argparse
from html import escape
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import os
import re
import time

import requests

from ..identity import canonical_hash, canonical_json
from . import easy_stock_context as common
from .hithink_dump_trial import _session, _check_response
from .sector_radar_audit import _check_safe_json

VERSION = 'vibe-concept-snapshot-v1'
UPSTREAM = '7f3a08b85451b54c762898789e2dcaa5d7d2ec98'
WORKFLOW = '.github/workflows/vibe-concept-snapshot.yml'
URL = 'https://push2.eastmoney.com/api/qt/clist/get'
# Vibe field map, not independently certified exchange definitions.
PERIODS = {'today': ('f3', 'f62', 'f184'), '5d': ('f109', 'f164', 'f165'),
           '10d': ('f160', 'f174', 'f175')}
MAX_REQUESTS, MAX_ROWS, MAX_SECONDS = 32, 4096, 180
MAX_BODY = 1024 * 1024
AUTHORITY = dict(common.AUTHORITY)
require = common.require
ERRORS = (ValueError, TypeError, KeyError, OSError, RuntimeError, OverflowError,
          UnicodeError, requests.RequestException)


def encoded(value):
    return (canonical_json(value) + '\n').encode('utf-8')


def now():
    return datetime.now(timezone.utc).isoformat()


def execution_identity(value):
    require(isinstance(value, dict) and set(value) == {
        'repository', 'workflow', 'ref', 'event', 'code_commit', 'run_id', 'attempt'}, 'EXECUTION_FIELDS')
    require(value['repository'] == 'auguspp/decision-kernel' and value['workflow'] == WORKFLOW
        and value['ref'] == 'refs/heads/main' and value['event'] == 'workflow_dispatch'
        and type(value['attempt']) is int and value['attempt'] == 1
        and type(value['run_id']) is int and value['run_id'] > 0
        and isinstance(value['code_commit'], str)
        and re.fullmatch('[0-9a-f]{40}', value['code_commit']), 'EXECUTION_IDENTITY')
    return dict(value)


def request_spec(period, page):
    require(period in PERIODS and type(page) is int and 1 <= page <= MAX_REQUESTS, 'REQUEST_SCOPE')
    return {'period': period, 'page': page, 'url': URL, 'params': {
        'pn': str(page), 'pz': '200', 'po': '0', 'np': '1', 'fltt': '2', 'invt': '2',
        'fid': 'f12', 'fs': 'm:90+t:3',
        'fields': ','.join(('f12', 'f14', *PERIODS[period]))}}


def request_raw(spec):
    require(spec == request_spec(spec['period'], spec['page']), 'REQUEST_DIFFERS')
    with _session() as session:
        with session.get(URL, params=spec['params'], stream=True, allow_redirects=False,
                timeout=(10, 20), headers={'Accept-Encoding': 'identity',
                    'User-Agent': 'Mozilla/5.0 DecisionKernel-concept-context',
                    'Referer': 'https://data.eastmoney.com/'}) as response:
            length = _check_response(response)
            expected = requests.Request('GET', URL, params=spec['params']).prepare().url
            require(response.url == expected and (length is None or length <= MAX_BODY), 'HTTP_DESTINATION_OR_SIZE')
            chunks, size = [], 0
            for part in response.iter_content(chunk_size=65536):
                size += len(part); require(size <= MAX_BODY, 'HTTP_BODY_BUDGET'); chunks.append(part)
            require(length is None or size == length, 'HTTP_LENGTH_DIFFERS')
    return b''.join(chunks)


def plan(execution, started_at):
    common.clock(started_at)
    return {'version': VERSION, 'upstream_commit': UPSTREAM,
        'execution': execution_identity(execution), 'started_at': started_at,
        'periods': list(PERIODS), 'request_templates': [request_spec(p, 1) for p in PERIODS],
        'max_requests': MAX_REQUESTS, 'max_rows_per_period': MAX_ROWS,
        'max_seconds': MAX_SECONDS, 'max_body_bytes': MAX_BODY,
        'selection': 'SOURCE_CODE_ORDER_NOT_TOP_GAINERS', 'retry_count': 0, **AUTHORITY}


def _states():
    return {p: {'total': None, 'rows': [], 'complete': False, 'pages': 0} for p in PERIODS}


def _consume(state, raw, spec, filename):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY, 'BODY_BUDGET')
    obj = common.decode(raw); _check_safe_json(obj)
    require(isinstance(obj, dict) and type(obj.get('rc')) is int and obj['rc'] == 0, 'PROVIDER_REJECTED')
    data = obj.get('data'); require(isinstance(data, dict), 'DATA_UNAVAILABLE')
    total, rows = data.get('total'), data.get('diff')
    require(type(total) is int and 0 <= total <= MAX_ROWS, 'CATALOG_TOTAL_INVALID')
    require(isinstance(rows, list) and len(rows) <= 200, 'PAGE_SHAPE')
    require(state['total'] is None or total == state['total'], 'CATALOG_CHANGED')
    require(spec['page'] == state['pages'] + 1 and not state['complete'], 'PAGE_ORDER')
    codes = {r['code'] for r in state['rows']}; parsed = []
    for index, row in enumerate(rows):
        require(isinstance(row, dict), 'ROW_SHAPE')
        code, name = row.get('f12'), row.get('f14')
        require(isinstance(code, str) and re.fullmatch(r'BK[0-9]{4}', code), 'BOARD_IDENTITY')
        require(isinstance(name, str) and 0 < len(name.strip()) <= 128, 'BOARD_NAME')
        require(code not in codes, 'DUPLICATE_BOARD'); codes.add(code)
        values, gaps = {}, {}
        for key, field in zip(('change_percent', 'main_net_cny', 'main_ratio_percent'), PERIODS[spec['period']]):
            values[key], status = common.number(row.get(field))
            if status != 'AVAILABLE':
                gaps[key] = status
        parsed.append({'code': code, 'name': name, **values, 'field_gaps': gaps,
            'source_file': filename, 'source_row': index})
    require(len(codes) <= total, 'TOTAL_LESS_THAN_ROWS')
    # An unexpectedly short page is NOT proof of completion; only the total is.
    require(bool(rows) or (total == 0 and not state['rows']), 'EMPTY_PAGE_BEFORE_TOTAL')
    state.update(total=total, rows=state['rows'] + parsed, pages=spec['page'],
                 complete=bool(total) and len(codes) == total)
    return state['complete'] or total == 0


def _summary(states):
    by_code = {}
    for period, state in states.items():
        for row in state['rows']:
            item = by_code.setdefault(row['code'], {'code': row['code'], 'periods': {}})
            item['periods'][period] = row
    return [by_code[code] for code in sorted(by_code)]


def capture(output, execution, *, transport=request_raw, clock=now, monotonic=time.monotonic, sleep=time.sleep):
    root = Path(output)
    require(not root.exists() and not root.is_symlink() and not any(p.is_symlink() for p in root.parents), 'OUTPUT_CREATE_ONLY')
    started = clock(); p = plan(execution, started); states = _states()
    root.mkdir(parents=True, exist_ok=False)
    (root / 'plan.json').write_bytes(encoded(p))
    records, stop = [], 'COMPLETE'
    begin = monotonic(); previous = common.clock(started)
    for period in PERIODS:
        for page in range(1, MAX_REQUESTS + 1):
            elapsed = round((monotonic() - begin) * 1000)
            require(elapsed >= 0, 'MONOTONIC_REVERSED')
            if len(records) >= MAX_REQUESTS or elapsed >= MAX_SECONDS * 1000:
                stop = 'REQUEST_BUDGET' if len(records) >= MAX_REQUESTS else 'TIME_BUDGET'; break
            spec = request_spec(period, page)
            record = {'request': spec, 'elapsed_ms': elapsed, 'requested_at': clock(),
                'received_at': None, 'http_status': None, 'status': 'SOURCE_ERROR',
                'body_file': None, 'bytes': None, 'sha256': None, 'error_type': None}
            require(previous <= common.clock(record['requested_at']), 'CAPTURE_CLOCK_REVERSED')
            done = False
            try:
                raw = transport(spec); record['received_at'] = clock(); record['http_status'] = 200
                require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY, 'BODY_BUDGET')
                _check_safe_json(common.decode(raw))
                filename = f'{period}-{page}.json'
                with (root / filename).open('xb') as stream:
                    stream.write(raw)
                record.update(body_file=filename, bytes=len(raw), sha256=sha256(raw).hexdigest(), status='BODY_RETAINED')
                done = _consume(states[period], raw, spec, filename)
            except ERRORS as exc:
                record.update(received_at=clock(), error_type=type(exc).__name__)
                status = getattr(exc, 'http_status', None)
                if type(status) is int and 100 <= status <= 599:
                    record['http_status'] = status
                record['status'] = 'BODY_REJECTED' if record['body_file'] else 'SOURCE_ERROR'
                stop = record['status']
            require(previous <= common.clock(record['requested_at']) <= common.clock(record['received_at']), 'CAPTURE_CLOCK_REVERSED')
            previous = common.clock(record['received_at']); records.append(record)
            if stop != 'COMPLETE' or done:
                break
            sleep(0.25)
        if stop != 'COMPLETE':
            break
    finished = clock(); require(previous <= common.clock(finished), 'CAPTURE_CLOCK_REVERSED')
    saved = {'version': VERSION, 'plan_hash': canonical_hash(p), 'execution': p['execution'],
        'started_at': started, 'finished_at': finished, 'elapsed_ms': round((monotonic() - begin) * 1000),
        'records': records, 'stop_reason': stop, 'retry_count': 0, **AUTHORITY}
    saved['capture_hash'] = canonical_hash(saved)
    (root / 'capture.json').write_bytes(encoded(saved))
    result = replay(read_files(root), expected_execution=p['execution'])
    (root / 'observation.json').write_bytes(encoded(result))
    (root / 'summary.md').write_text(render(result), encoding='utf-8')
    return result


def replay(files, *, expected_execution):
    require(isinstance(files, dict) and {'plan.json', 'capture.json'} <= set(files)
        and len(files) <= MAX_REQUESTS + 4 and all(isinstance(b, bytes) and 0 < len(b) <= 4 * MAX_BODY for b in files.values())
        and sum(map(len, files.values())) <= (MAX_REQUESTS + 8) * MAX_BODY, 'FILE_BUDGET')
    p, saved = common.decode(files['plan.json']), common.decode(files['capture.json'])
    require(saved['execution'] == execution_identity(expected_execution)
        and canonical_json(p) == canonical_json(plan(expected_execution, saved['started_at']))
        and saved['version'] == VERSION and saved['plan_hash'] == canonical_hash(p)
        and saved['capture_hash'] == canonical_hash({k: v for k, v in saved.items() if k != 'capture_hash'})
        and type(saved['retry_count']) is int and saved['retry_count'] == 0
        and canonical_json({k: saved.get(k) for k in AUTHORITY}) == canonical_json(AUTHORITY), 'CAPTURE_IDENTITY')
    start, end = common.clock(saved['started_at']), common.clock(saved['finished_at'])
    require(start <= end and type(saved['elapsed_ms']) is int and saved['elapsed_ms'] >= 0, 'CAPTURE_CLOCKS')
    records = saved['records']; require(isinstance(records, list) and len(records) <= MAX_REQUESTS, 'REQUEST_COUNT')
    states, names, cursor, previous, elapsed, terminal = _states(), {'plan.json', 'capture.json'}, 0, start, 0, None
    periods = list(PERIODS)
    for i, record in enumerate(records):
        require(cursor < len(periods) and terminal is None, 'REQUEST_AFTER_STOP')
        period = periods[cursor]; state = states[period]
        spec = request_spec(period, state['pages'] + 1)
        require(record['request'] == spec and type(record['elapsed_ms']) is int
            and elapsed <= record['elapsed_ms'] < MAX_SECONDS * 1000, 'REQUEST_OR_BUDGET_DIFFERS')
        require(previous <= common.clock(record['requested_at']) <= common.clock(record['received_at']) <= end, 'REQUEST_CLOCKS')
        previous, elapsed = common.clock(record['received_at']), record['elapsed_ms']
        require(record['http_status'] is None or (type(record['http_status']) is int and 100 <= record['http_status'] <= 599), 'HTTP_STATUS')
        filename = record['body_file']
        if filename is None:
            require(record['status'] == 'SOURCE_ERROR' and record['bytes'] is None and record['sha256'] is None
                and isinstance(record['error_type'], str) and record['error_type'].isidentifier(), 'FAILURE_RECORD')
            terminal = 'SOURCE_ERROR'; continue
        require(filename == f'{period}-{spec["page"]}.json' and filename in files and record['http_status'] == 200
            and type(record['bytes']) is int and len(files[filename]) == record['bytes']
            and sha256(files[filename]).hexdigest() == record['sha256'], 'RAW_IDENTITY')
        names.add(filename)
        try:
            done = _consume(state, files[filename], spec, filename)
        except ERRORS as exc:
            require(record['status'] == 'BODY_REJECTED' and record['error_type'] == type(exc).__name__, 'PARSE_FAILURE_DIFFERS')
            terminal = 'BODY_REJECTED'
        else:
            require(record['status'] == 'BODY_RETAINED' and record['error_type'] is None, 'BODY_STATUS')
            if done:
                cursor += 1
    require(saved['elapsed_ms'] >= elapsed, 'ELAPSED_CLOCKS')
    if terminal is None:
        terminal = ('COMPLETE' if cursor == len(periods) else 'REQUEST_BUDGET' if len(records) == MAX_REQUESTS
                    else 'TIME_BUDGET' if saved['elapsed_ms'] >= MAX_SECONDS * 1000 else None)
    require(terminal is not None and saved['stop_reason'] == terminal, 'UNEXPLAINED_STOP')
    coverage = {period: {'returned_rows': len(s['rows']), 'upstream_total_claim': s['total'],
        'returned_pages': s['pages'], 'matched_reported_catalog': s['complete'],
        'missing_or_invalid_values': sum(len(r['field_gaps']) for r in s['rows'])} for period, s in states.items()}
    result = common.seal({'version': VERSION, 'execution': p['execution'], 'upstream_commit': UPSTREAM,
        'capture_hash': saved['capture_hash'], 'started_at': saved['started_at'], 'finished_at': saved['finished_at'],
        'attempted_requests': len(records), 'stop_reason': terminal, 'coverage': coverage,
        'status': 'MATCHED_REPORTED_CATALOGS' if all(s['complete'] for s in states.values()) else 'PARTIAL_OR_UNAVAILABLE',
        'observations': _summary(states), 'kind': 'MARKET_EXPRESSION', 'qualification': 'CONTEXT_ONLY',
        'taxonomy': 'EASTMONEY_CONCEPT_BK_NOT_HITHINK_TI', 'source_trade_date': None,
        'source_freshness': 'NOT_ESTABLISHED_BY_RETRIEVAL_TIME',
        'period_basis': 'SOURCE_REPORTED_ROLLING_WINDOWS_NOT_DAILY_PATH_OR_PERSISTENCE',
        'coverage_basis': 'MATCH_TO_REPORTED_TOTAL_NOT_INDEPENDENT_UNIVERSE_OR_ATOMIC_SNAPSHOT',
        'field_basis': 'PINNED_VIBE_MAPPING_NOT_INDEPENDENT_ECONOMIC_VERIFICATION',
        'source_calls_during_replay': 0, **AUTHORITY})
    if 'observation.json' in files:
        require(files['observation.json'] == encoded(result), 'DERIVED_OBSERVATION_DIFFERS'); names.add('observation.json')
    if 'summary.md' in files:
        require(files['summary.md'] == render(result).encode(), 'DERIVED_SUMMARY_DIFFERS'); names.add('summary.md')
    require(names == set(files), 'UNBOUND_FILES')
    return result


def render(result):
    p = result['projection']
    require(result['projection_hash'] == canonical_hash(p), 'OBSERVATION_HASH')
    def text(v):
        value = escape(str('UNKNOWN' if v is None else v)).replace('\n', ' ').replace('\r', ' ')
        return re.sub(r'[\\`*_{}\[\]()#+.!|]', lambda m: '&#' + str(ord(m[0])) + ';', value)
    lines = ['# 概念市场横截面', '', '状态：' + text(p['status']), '',
        '东方财富BK口径；不与同花顺TI历史拼接。获取时间不是交易/发布时间。',
        '5/10日是来源报告的累计窗口，不证明每日持续上涨，不是5/20/60日完整历史。',
        '总数匹配只检验已返回目录；分时分页不是原子快照，也不认证全市场独立穷尽。',
        '资金字段是来源定义，不是公司现金流；不生成候选、评分、Research或投资权限。', '',
        '获取区间：' + text(p['started_at']) + ' → ' + text(p['finished_at']),
        '实际请求：' + str(p['attempted_requests']) + '；停止：' + text(p['stop_reason']), '',
        '| 窗口 | 已返回 | 来源宣称总数 | 总数匹配 | 缺失/无效值 |', '|---|---:|---:|---|---:|']
    for period, c in p['coverage'].items():
        lines.append('| ' + ' | '.join(text(v) for v in (period, c['returned_rows'], c['upstream_total_claim'], c['matched_reported_catalog'], c['missing_or_invalid_values'])) + ' |')
    lines += ['', '下表保留全部取得对象，按代码排序；未取得不等于无变化。名称按各窗口原值保留在JSON。', '',
              '| 代码 | 名称 | 当日% | 5日% | 10日% |', '|---|---|---:|---:|---:|']
    for item in p['observations']:
        periods = item['periods']; name = next(iter(periods.values()))['name']
        lines.append('| ' + ' | '.join(text(v) for v in (item['code'], name, *[periods.get(k, {}).get('change_percent') for k in PERIODS])) + ' |')
    return '\n'.join(lines + ['', '[全部资金原值、字段缺口与逐行来源](observation.json)', ''])


def read_files(root):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink() and not any(p.is_symlink() for p in root.parents), 'READ_DIRECTORY_INVALID')
    paths = list(root.iterdir())
    require(len(paths) <= MAX_REQUESTS + 4 and all(p.is_file() and not p.is_symlink()
        and 0 < p.stat().st_size <= 4 * MAX_BODY for p in paths)
        and sum(p.stat().st_size for p in paths) <= (MAX_REQUESTS + 8) * MAX_BODY, 'READ_FILE_BUDGET')
    return {p.name: p.read_bytes() for p in paths}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('capture', 'replay'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv); env = os.environ
    execution = {'repository': env['GITHUB_REPOSITORY'], 'workflow': WORKFLOW, 'ref': env['GITHUB_REF'],
        'event': env['GITHUB_EVENT_NAME'], 'code_commit': env['GITHUB_SHA'],
        'run_id': int(env['GITHUB_RUN_ID']), 'attempt': int(env['GITHUB_RUN_ATTEMPT'])}
    if args.operation == 'capture':
        result = capture(args.output, execution)
    else:
        files = read_files(args.output)
        result = replay(files, expected_execution=execution)
    print('CONCEPT_CONTEXT_STATUS=' + result['projection']['status'])
    print('CONCEPT_CONTEXT_HASH=' + result['projection_hash'])
    return 0  # A retained, explicitly failed source attempt is not successful data.


if __name__ == '__main__':
    raise SystemExit(main())
