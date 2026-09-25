"""Bounded issuer activity/report context; not a screener or research authority.

Protocol reuse: Vibe-Research@7f3a08b85451b54c762898789e2dcaa5d7d2ec98
(eastmoney_reports) and AKShare@0191689d57c667b7c7a198fd0cf97316837ef311
(stock_jgdy_detail_em). MIT notices and scope: docs/institutional-context.md.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import os
from pathlib import Path
import re

import requests

from ..identity import canonical_hash, canonical_json
from . import easy_stock_context as common
from .hithink_dump_trial import _session

VERSION = 'institutional-context-v1'
WORKFLOW = '.github/workflows/institutional-context.yml'
FAMILIES = ('activity', 'reports')
MAX_BODY = 512 * 1024
LIMIT = 50
AUTHORITY = common.AUTHORITY
require = common.require


def encoded(value):
    return (canonical_json(value) + '\n').encode('utf-8')


def identity(value):
    require(isinstance(value, dict) and set(value) == {
        'repository', 'workflow', 'ref', 'event', 'code_commit', 'run_id', 'attempt'}, 'EXECUTION_FIELDS')
    require(value['repository'] == 'auguspp/decision-kernel' and value['workflow'] == WORKFLOW
        and value['ref'] == 'refs/heads/main' and value['event'] == 'workflow_dispatch'
        and type(value['attempt']) is int and value['attempt'] == 1
        and type(value['run_id']) is int and value['run_id'] > 0
        and isinstance(value['code_commit'], str) and re.fullmatch(r'[a-f0-9]{40}', value['code_commit']),
        'EXECUTION_IDENTITY')
    return dict(value)


def scope(ticker, begin, end):
    require(isinstance(ticker, str) and re.fullmatch(r'(?:6[0-9]{5}\.SH|[03][0-9]{5}\.SZ)', ticker), 'TICKER')
    first, last = common.day(begin), common.day(end)
    require(0 <= (last - first).days <= 92, 'WINDOW')
    return {'ticker': ticker, 'begin': begin, 'end': end, 'basis': 'PROVIDER_PUBLICATION_DATE'}


def specs(selected):
    require(selected == scope(selected['ticker'], selected['begin'], selected['end']), 'SCOPE')
    ticker, begin, end = (selected[k] for k in ('ticker', 'begin', 'end'))
    return [
        {'family': 'activity', 'url': 'https://datacenter-web.eastmoney.com/api/data/v1/get', 'params': {
            'reportName': 'RPT_ORG_SURVEY',
            'columns': 'SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,NOTICE_DATE,RECEIVE_START_DATE,RECEIVE_OBJECT,RECEIVE_PLACE,RECEIVE_WAY_EXPLAIN,INVESTIGATORS,RECEPTIONIST,ORG_TYPE',
            'sortColumns': 'NOTICE_DATE,RECEIVE_START_DATE,SECURITY_CODE,NUMBERNEW',
            'sortTypes': '-1,-1,1,-1', 'pageSize': str(LIMIT), 'pageNumber': '1',
            'source': 'WEB', 'client': 'WEB',
            'filter': f'(IS_SOURCE="1")(SECUCODE="{ticker}")(NOTICE_DATE>=\'{begin}\')(NOTICE_DATE<=\'{end}\')'}},
        {'family': 'reports', 'url': 'https://reportapi.eastmoney.com/report/list', 'params': {
            'industryCode': '*', 'pageSize': str(LIMIT), 'industry': '*', 'rating': '*', 'ratingChange': '*',
            'beginTime': begin, 'endTime': end, 'pageNo': '1', 'fields': '', 'qType': '0',
            'orgCode': '', 'code': ticker[:6], 'rcode': '', 'p': '1', 'pageNum': '1', 'pageNumber': '1'}}]


def request_raw(spec, selected):
    require(spec in specs(selected), 'UNREVIEWED_REQUEST')
    with _session() as session:
        with session.get(spec['url'], params=spec['params'], stream=True, allow_redirects=False,
                timeout=(10, 20), headers={'Accept-Encoding': 'identity',
                    'User-Agent': 'Mozilla/5.0 DecisionKernel-issuer-context',
                    'Referer': 'https://data.eastmoney.com/'}) as response:
            expected = requests.Request('GET', spec['url'], params=spec['params']).prepare().url
            require(response.url == expected and response.headers.get('Content-Encoding', 'identity').lower()
                    in {'', 'identity'}, 'DESTINATION_OR_ENCODING')
            length = response.headers.get('Content-Length')
            require(length is None or length.isdigit() and int(length) <= MAX_BODY, 'HTTP_SIZE')
            chunks, size = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                size += len(chunk); require(size <= MAX_BODY, 'HTTP_SIZE'); chunks.append(chunk)
            require(length is None or size == int(length), 'HTTP_LENGTH')
            return response.status_code, b''.join(chunks)


def publication(value):
    # Preserve the original string separately. An unzoned vendor timestamp is
    # only a publication-date claim, never a historical available_at clock.
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)?', value), 'PUBLICATION_DATE')
    datetime.fromisoformat(value)
    return common.day(value[:10])


def normalize(raw, record, selected):
    family = record['request']['family']; obj = common.decode(raw)
    require(isinstance(obj, dict), 'ENVELOPE')
    if family == 'activity':
        require(obj.get('success') is True and isinstance(obj.get('result'), dict), 'ACTIVITY_UNAVAILABLE')
        data = obj['result']; rows, total, pages = data.get('data'), data.get('count'), data.get('pages')
    else:
        rows, total, pages = obj.get('data'), obj.get('hits'), obj.get('TotalPage')
    require(isinstance(rows, list) and len(rows) <= LIMIT, 'ROWS')
    require(total is None or type(total) is int and len(rows) <= total, 'TOTAL')
    require(pages is None or type(pages) is int and pages >= 0, 'PAGES')
    unique = {}
    for index, row in enumerate(rows):
        require(isinstance(row, dict), 'ROW')
        key = 'SECURITY_CODE' if family == 'activity' else 'stockCode'
        require(row.get(key) == selected['ticker'][:6], 'ISSUER_MISMATCH')
        if family == 'activity':
            require(row.get('SECUCODE') == selected['ticker'], 'EXCHANGE_MISMATCH')
        published_raw = row.get('NOTICE_DATE' if family == 'activity' else 'publishDate')
        published = publication(published_raw)
        require(common.day(selected['begin']) <= published <= common.day(selected['end'])
            and published <= common.clock(record['received_at']).astimezone(common.ZONE).date(), 'PUBLICATION_WINDOW')
        fingerprint = canonical_hash(row)
        location = {'body_file': record['body_file'], 'sha256': record['sha256'], 'row_index': index}
        if fingerprint in unique:
            unique[fingerprint]['source_locations'].append(location)
            continue
        item = {'record_hash': fingerprint, 'provider_fields': row, 'source_locations': [location],
            'publication_date': str(published), 'publication_time_raw': published_raw,
            'publication_timezone': 'UNKNOWN', 'available_at': record['received_at'],
            'historical_available_at': 'NOT_ESTABLISHED'}
        if family == 'activity':
            event = row.get('RECEIVE_START_DATE')
            event_day = publication(event) if event is not None else None
            require(event_day is None or event_day <= published, 'EVENT_AFTER_DISCLOSURE')
            item.update(event_date=None if event_day is None else str(event_day),
                institution_text=row.get('RECEIVE_OBJECT'), participants_text=row.get('INVESTIGATORS'),
                event_identity='NOT_ESTABLISHED_BY_DATE_OR_PARTICIPANT_ROW',
                counts={'events': None, 'distinct_institutions': None, 'participants': None})
        else:
            report_id = row.get('infoCode')
            require(isinstance(report_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', report_id), 'REPORT_ID')
            slots = {k: row.get(k) for k in ('predictThisYearEps', 'predictNextYearEps', 'predictNextTwoYearEps')}
            item.update(report_id=report_id, institution=row.get('orgCode'), institution_name=row.get('orgSName'),
                forecast_slots=slots, target_period='NOT_ESTABLISHED', currency='NOT_ESTABLISHED',
                share_basis='NOT_ESTABLISHED', forecast_revision='NOT_COMPARABLE',
                comparison_blockers=['TARGET_PERIOD', 'CURRENCY', 'SHARE_BASIS'])
        unique[fingerprint] = item
    complete = total is not None and total == len(rows) and pages in {0, 1}
    return {'status': 'CONTEXT_READY' if rows else 'EMPTY_RETURN_NOT_PROOF_OF_NO_ACTIVITY',
        'returned_rows': len(rows), 'unique_record_versions': len(unique), 'duplicates_collapsed': len(rows)-len(unique),
        'provider_total': total, 'provider_pages': pages, 'matched_reported_scope': complete,
        'coverage': 'MATCHED_PROVIDER_RETURN_NOT_ALL_DISCLOSURES' if complete else 'BOUNDED_FIRST_PAGE_NOT_COMPLETE',
        'records': list(unique.values())}


def project(saved, files, expected_execution):
    require(saved['version'] == VERSION and saved['execution'] == identity(expected_execution)
        and saved['capture_hash'] == canonical_hash({k: v for k, v in saved.items() if k != 'capture_hash'})
        and saved['authority'] == AUTHORITY, 'CAPTURE_IDENTITY')
    selected = saved['scope']; expected = specs(selected)
    require(len(saved['records']) == len(expected), 'RECORD_COUNT')
    start, finish = common.clock(saved['started_at']), common.clock(saved['finished_at'])
    require(start <= finish and common.day(selected['end']) <= start.astimezone(common.ZONE).date(), 'CLOCKS')
    names, families, previous, stopped, attempts = {'capture.json'}, {}, start, False, 0
    for spec, record in zip(expected, saved['records']):
        require(record['request'] == spec, 'REQUEST_IDENTITY')
        name = spec['family']; families[name] = {'status': record['status'], 'records': []}
        if stopped:
            require(record['status'] == 'NOT_ATTEMPTED_POLICY_STOP' and all(record[k] is None for k in
                ('requested_at','received_at','http_status','body_file','sha256','bytes','error_type')), 'POLICY_STOP')
            continue
        require(previous <= common.clock(record['requested_at']) <= common.clock(record['received_at']) <= finish, 'CLOCKS')
        previous = common.clock(record['received_at']); attempts += 1
        status = record['http_status']
        require(status is None or type(status) is int and 100 <= status <= 599, 'HTTP_STATUS')
        if record['body_file'] is None:
            require(record['status'] == 'TRANSPORT_UNAVAILABLE' and status is None and record['sha256'] is None
                and record['bytes'] is None and isinstance(record['error_type'], str)
                and record['error_type'].isidentifier(), 'TRANSPORT_RECORD')
            continue
        filename = name + '.body'; require(record['body_file'] == filename, 'RAW_PATH')
        raw = files[filename]; names.add(filename)
        require(isinstance(raw, bytes) and len(raw) <= MAX_BODY and type(record['bytes']) is int
            and len(raw) == record['bytes'] and sha256(raw).hexdigest() == record['sha256']
            and record['status'] == 'HTTP_BODY_RETAINED' and record['error_type'] is None, 'RAW_IDENTITY')
        if status != 200:
            families[name].update(status='HTTP_UNAVAILABLE', http_status=status)
            stopped = status in {401, 403, 429}
            continue
        try:
            families[name] = normalize(raw, record, selected)
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as exc:
            families[name].update(status='RETAINED_BODY_NOT_QUALIFIED', error_type=type(exc).__name__)
        families[name]['source_request'] = spec
    require(names == set(files), 'UNBOUND_FILES')
    payload = {'version': VERSION, 'execution': saved['execution'], 'scope': selected,
        'capture_hash': saved['capture_hash'], 'families': families, 'attempted_requests': attempts,
        'source_calls_during_replay': 0, 'qualification': 'SECONDARY_CONTEXT_NOT_EVIDENCE',
        'forecast_comparison': 'NOT_ESTABLISHED_WITHOUT_COMPATIBLE_PERIOD_CURRENCY_SHARE_BASIS', **AUTHORITY}
    return common.seal(payload)


def read_files(root):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink() and not any(p.is_symlink() for p in root.parents), 'UNSAFE_DIRECTORY')
    paths = list(root.iterdir())
    require(len(paths) <= 5 and all(p.is_file() and not p.is_symlink() and p.stat().st_size <= 4*MAX_BODY for p in paths), 'FILE_BUDGET')
    return {p.name: p.read_bytes() for p in paths}


def replay(root, execution):
    files = read_files(root); derived = {k: files.pop(k) for k in ('context.json','summary.md') if k in files}
    result = project(common.decode(files['capture.json']), files, execution)
    if 'context.json' in derived:
        require(derived['context.json'] == encoded(result), 'DERIVED_CONTEXT_DIFFERS')
    if 'summary.md' in derived:
        require(derived['summary.md'] == render(result).encode(), 'DERIVED_SUMMARY_DIFFERS')
    return result


def render(result):
    p = result['projection']; s = p['scope']
    def text(value):
        return escape(str(value)).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')
    lines = ['# 机构活动 / 研报版本观察', '', f"{text(s['ticker'])} · 披露日期 {s['begin']} 至 {s['end']}",
        '', '有界来源资料，不是投资信号。空返回不证明无活动；未取得不等于零。',
        '调研行数不等于事件数、独立机构数或人数。EPS槽位未确认目标期/货币/股本口径，不计算上修下修。', '']
    for name, family in p['families'].items():
        lines += [f"## {name}: {text(family['status'])}",
            f"返回 {family.get('returned_rows', 'UNKNOWN')} 行；去重版本 {family.get('unique_record_versions', 'UNKNOWN')}；来源总数 {family.get('provider_total', 'UNKNOWN')}。",
            f"覆盖：{text(family.get('coverage', 'UNAVAILABLE'))}", '']
        for item in family['records'][:12]:
            row = item['provider_fields']; label = row.get('RECEIVE_OBJECT') if name == 'activity' else row.get('title')
            lines.append(f"- {item['publication_date']} | {text(label)} | {item['record_hash'][:12]}")
        if len(family['records']) > 12:
            lines.append('此处仅展示前12条；全部已取得原行见 context.json 与 .body 原件。')
    return '\n'.join(lines) + '\n'


def capture(root, selected, execution, *, transport=request_raw, clock=lambda: datetime.now(timezone.utc).isoformat()):
    root = Path(root); identity(execution); expected = specs(selected); started = clock()
    require(common.day(selected['end']) <= common.clock(started).astimezone(common.ZONE).date(), 'FUTURE_WINDOW')
    require(not root.exists() and not root.is_symlink() and not any(p.is_symlink() for p in root.parents), 'OUTPUT_CREATE_ONLY')
    root.mkdir(parents=True)
    def save(name, raw):
        with (root/name).open('xb') as stream: stream.write(raw)
    records, stopped = [], False
    for spec in expected:
        record = {'request': spec, 'status': 'NOT_ATTEMPTED_POLICY_STOP', **{k: None for k in
            ('requested_at','received_at','http_status','body_file','sha256','bytes','error_type')}}
        if not stopped:
            record.update(requested_at=clock(), status='TRANSPORT_UNAVAILABLE')
            try:
                status, raw = transport(spec, selected)
                require(type(status) is int and 100 <= status <= 599 and isinstance(raw, bytes) and len(raw) <= MAX_BODY, 'TRANSPORT_RESULT')
                filename = spec['family'] + '.body'; save(filename, raw)
                record.update(status='HTTP_BODY_RETAINED', http_status=status, body_file=filename,
                    sha256=sha256(raw).hexdigest(), bytes=len(raw))
                stopped = status in {401, 403, 429}
            except (ValueError, OSError, requests.RequestException) as exc:
                record['error_type'] = type(exc).__name__
            record['received_at'] = clock()
        records.append(record)
    saved = {'version': VERSION, 'execution': identity(execution), 'scope': selected,
        'started_at': started, 'finished_at': clock(), 'records': records, 'authority': AUTHORITY}
    saved['capture_hash'] = canonical_hash(saved); save('capture.json', encoded(saved))
    result = replay(root, execution); save('context.json', encoded(result)); save('summary.md', render(result).encode())
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['capture','replay'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ticker', default='002436.SZ')
    parser.add_argument('--begin', default='2026-08-11')
    parser.add_argument('--end', default='2026-09-24')
    args = parser.parse_args(argv); env = os.environ
    execution = {'repository': env['GITHUB_REPOSITORY'], 'workflow': WORKFLOW, 'ref': env['GITHUB_REF'],
        'event': env['GITHUB_EVENT_NAME'], 'code_commit': env['GITHUB_SHA'],
        'run_id': int(env['GITHUB_RUN_ID']), 'attempt': int(env['GITHUB_RUN_ATTEMPT'])}
    result = capture(args.output, scope(args.ticker,args.begin,args.end), execution) if args.operation == 'capture' else replay(args.output, execution)
    print('INSTITUTIONAL_CONTEXT_HASH=' + result['projection_hash'])
    # Completion means observations/failures were retained, not source success.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
