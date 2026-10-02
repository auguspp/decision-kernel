"""Two approved C1 report-directory queries, not PDF/model qualification.

Reuse the existing Relay client and receipt validation. No URL is fetched here.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from decision_kernel.runtime import current_state as saved
from decision_kernel.runtime import global_market_context as common
from decision_kernel.runtime import tushare_relay as relay
from decision_kernel.runtime.research_commit_only import _safe_path

PILOT = 'c1-accelink-two-reports-20261002'
WORKFLOW = '.github/workflows/c1-report-locators.yml'
TARGETS = {'20260430': '数通业务驱动高增 毛利率持续提升',
           '20260910': '传输与海外双轮驱动 Q2业绩延续高增'}
FIELDS = ('trade_date', 'abstr', 'title', 'report_type', 'author', 'name',
          'ts_code', 'inst_csname', 'ind_name', 'url')
AUTHORITY = {'research_authority': 'NONE', 'investment_authority': 'NONE',
             'pdf_acquired': False, 'full_model_qualified': False}


def plan():
    return [{'api': 'research_report', 'params': {
        'trade_date': day, 'ts_code': '002281.SZ', 'inst_csname': '长江证券',
        'report_type': '个股研报', 'fields': ','.join(FIELDS), 'limit': '1000'}}
        for day in TARGETS]


def identity(env):
    out = {k: env.get(k) for k in ('GITHUB_REPOSITORY', 'GITHUB_SHA', 'GITHUB_RUN_ID',
           'GITHUB_RUN_ATTEMPT', 'GITHUB_REF', 'GITHUB_EVENT_NAME')}
    saved.check(out['GITHUB_REPOSITORY'] == saved.REPOSITORY
                and out['GITHUB_REF'] == 'refs/heads/main'
                and out['GITHUB_EVENT_NAME'] == 'workflow_dispatch'
                and out['GITHUB_RUN_ATTEMPT'] == '1'
                and re.fullmatch(r'[0-9a-f]{40}', out['GITHUB_SHA'] or '')
                and re.fullmatch(r'[1-9][0-9]*', out['GITHUB_RUN_ID'] or ''),
                'C1 execution identity differs')
    return out


def inspect(raw, spec):
    body = relay.decode(raw)
    saved.check(type(body.get('code')) is int and body['code'] == 0
                and body.get('ok', True) is True and body.get('error') in (None, ''),
                'C1 business response not qualified')
    saved.check(body.get('api_name') in (None, 'research_report'), 'C1 response API differs')
    fields = body.get('data', {}).get('fields')
    saved.check(isinstance(fields, list) and len(fields) == len(set(fields))
                and set(FIELDS) <= set(fields), 'C1 directory fields incomplete')
    rows = relay.rows(body)
    saved.check(len(rows) < 1000 and (body.get('count') is None
                or type(body['count']) is int and body['count'] == len(rows)),
                'C1 directory may be truncated')
    targets = []
    expected_day = spec['params']['trade_date']
    normalize = lambda text: re.sub(r'[\s，,：:。()（）-]', '', text)
    for index, row in enumerate(rows):
        day = row['trade_date']
        saved.check(isinstance(day, str) and day in
                    (expected_day, expected_day[:4]+'-'+expected_day[4:6]+'-'+expected_day[6:]),
                    'C1 response date differs')
        saved.check(row['ts_code'] == '002281.SZ'
                    and row['inst_csname'] in ('长江证券', '长江证券股份有限公司')
                    and row['report_type'] == '个股研报', 'C1 response scope differs')
        saved.check(isinstance(row['title'], str) and bool(row['title'].strip()), 'C1 title missing')
        if normalize(TARGETS[expected_day]) not in normalize(row['title']):
            continue
        url = row['url']
        valid = isinstance(url, str) and 0 < len(url) <= 8192 and not any(ord(c) < 33 for c in url)
        if valid:
            try:
                part = urlsplit(url)
                valid = (part.scheme == 'https' and bool(part.hostname) and not part.username
                         and not part.password and part.port in (None, 443) and not part.fragment)
            except ValueError:
                valid = False
        targets.append({'row_index': index, 'title': row['title'], 'author': row['author'],
                        'url': url, 'url_status': 'LOCATOR_ONLY_NOT_FETCHED' if valid else 'URL_UNQUALIFIED'})
    status = ('TARGET_NOT_IN_RETURNED_PAGE' if not targets else
              'TARGET_AMBIGUOUS' if len(targets) != 1 else targets[0]['url_status'])
    return {'trade_date': expected_day, 'rows_received': len(rows), 'status': status,
            'targets': targets, 'original_report_identity': 'NOT_ESTABLISHED_BY_DIRECTORY'}


def write(path, raw):
    _safe_path(path)
    with path.open('xb') as stream:
        stream.write(raw)
    saved.check(path.read_bytes() == raw, 'C1 saved bytes differ')


def rebuild(root, expected):
    root = Path(root); _safe_path(root)
    files = {p.name: p for p in root.iterdir()}
    saved.check(len(files) <= 6 and all(p.is_file() and not p.is_symlink() for p in files.values())
                and sum(p.stat().st_size for p in files.values()) <= 20 * 1024 * 1024,
                'C1 retained inventory differs')
    manifest = relay.decode((root/'capture.json').read_bytes())
    saved.check(manifest['capture_hash'] == common.digest(manifest), 'C1 capture hash differs')
    saved.check(manifest['pilot'] == PILOT and manifest['workflow'] == WORKFLOW
                and manifest['identity'] == identity(expected) and manifest['plan'] == plan()
                and manifest['authority'] == AUTHORITY and len(manifest['records']) == 2,
                'C1 capture binding differs')
    first, finish = map(saved.clock, (manifest['started_at'], manifest['finished_at']))
    saved.check(first <= finish, 'C1 capture clock reversed')
    seen = {'capture.json'}; previous = first; stopped = False; outcomes = []
    for i, (spec, record) in enumerate(zip(plan(), manifest['records'], strict=True)):
        saved.check(record['spec'] == spec and len(record['attempts']) <= 2, 'C1 plan differs')
        attempts = record['attempts']
        saved.check(not stopped or not attempts and record['status'] == 'NOT_ATTEMPTED_STOP', 'C1 stop ignored')
        outcome = {'trade_date': spec['params']['trade_date'], 'status': record['status']}
        if not attempts:
            saved.check(record['status'] in ('NOT_ATTEMPTED_STOP', 'REQUEST_RECEIPT_UNAVAILABLE',
                        'CREDENTIAL_UNAVAILABLE'), 'C1 missing receipt state differs')
            stopped = True
        for k, attempt in enumerate(attempts, 1):
            name = attempt['body']
            saved.check(name is None or name == f'raw-{i}-{k}.json', 'C1 body name differs')
            raw = None if name is None else (root/name).read_bytes()
            if name: seen.add(name)
            common.validate_attempt(attempt, raw, first, finish)
            requested, received = map(saved.clock, (attempt['requested_at'], attempt['received_at']))
            saved.check(previous <= requested <= received and attempt['attempt'] == k, 'C1 receipt order differs')
            if k == 2:
                saved.check(attempts[0]['classification'] == 'TEMPORARY_QUEUE'
                            and (requested-previous).total_seconds() >= relay.RETRY_WAIT_SECONDS,
                            'C1 retry differs')
            previous = received
        if attempts:
            saved.check(record['status'] == attempts[-1]['classification'], 'C1 status differs')
            if record['status'] == 'SUCCESS':
                try:
                    outcome = inspect(raw, spec)
                except (ValueError, KeyError, TypeError):
                    outcome['status'] = 'DIRECTORY_UNQUALIFIED'
                    stopped = True
            else:
                stopped = True
        outcomes.append(outcome)
    saved.check(set(files) <= seen | {'summary.json'}, 'C1 unexpected retained file')
    return {'pilot': PILOT, 'identity': manifest['identity'], 'outcomes': outcomes,
            'logical_queries_attempted': sum(r['status'] not in ('NOT_ATTEMPTED_STOP', 'CREDENTIAL_UNAVAILABLE')
                                             for r in manifest['records']),
            'http_receipts': sum(len(r['attempts']) for r in manifest['records']),
            'source_capture_hash': manifest['capture_hash'], **AUTHORITY}


def capture(root, env, *, request=relay.request, now=relay.now):
    who = identity(env); root = Path(root); _safe_path(root)
    root.mkdir(parents=False, exist_ok=False)
    start = now(); records = []; stopped = False
    for i, spec in enumerate(plan()):
        record = {'spec': spec, 'status': 'NOT_ATTEMPTED_STOP', 'attempts': []}
        records.append(record)
        if stopped: continue
        if not os.environ.get(relay.SECRET_ENV):
            record['status'] = 'CREDENTIAL_UNAVAILABLE'; stopped = True; continue
        record['status'] = 'REQUEST_RECEIPT_UNAVAILABLE'
        try:
            response = request(spec['api'], spec['params'], clock=now)
        except Exception:
            stopped = True; continue  # Never echo exceptions which may contain credentials.
        for k, source in enumerate(response['attempts'], 1):
            item = dict(source); raw = item.pop('raw')
            name = None if raw is None else f'raw-{i}-{k}.json'
            if name: write(root/name, raw)
            item.update(body=name, bytes=None if raw is None else len(raw),
                        sha256=None if raw is None else saved.sha256(raw))
            record['attempts'].append(item)
        record['status'] = response['status']
        stopped = response['status'] != 'SUCCESS'
        if not stopped:
            try:
                inspect(raw, spec)
            except (ValueError, KeyError, TypeError):
                stopped = True
    manifest = {'pilot': PILOT, 'workflow': WORKFLOW, 'identity': who, 'plan': plan(),
                'started_at': start, 'finished_at': now(), 'records': records, 'authority': AUTHORITY}
    manifest['capture_hash'] = common.digest(manifest)
    write(root/'capture.json', common.encoded(manifest))
    result = rebuild(root, who)
    write(root/'summary.json', common.encoded(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('capture', 'verify'))
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    root = Path(args.root)
    if args.mode == 'capture':
        result = capture(root, os.environ)
    else:
        result = rebuild(root, os.environ)
        saved.check(common.encoded(result) == (root/'summary.json').read_bytes(), 'C1 replay differs')
    # Do not expose potentially signed download URLs in public job logs.
    print(common.encoded({'pilot': PILOT, 'outcomes': [x['status'] for x in result['outcomes']],
                          'http_receipts': result['http_receipts'], **AUTHORITY}).decode())
