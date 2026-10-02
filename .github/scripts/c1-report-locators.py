"""Offline reader for retired C1 report-locator captures.

No acquisition entry remains. Historical request plans and source limitations
are retained for verification, not execution or PDF/model qualification.
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
NATIVE_PILOT = 'c1-accelink-native-schema-20261002'
PREDECESSOR = {'run_id': 36968934918, 'artifact_id': 11210703148,
               'sha256': 'e2f951b99cdd529acd3feba3fb8d736259f2bf654d84dc1e1c88efbd3031d764'}
WORKFLOW = '.github/workflows/c1-report-locators.yml'
TARGETS = {'20260430': '数通业务驱动高增 毛利率持续提升',
           '20260910': '传输与海外双轮驱动 Q2业绩延续高增'}
FIELDS = ('trade_date', 'abstr', 'title', 'report_type', 'author', 'name',
          'ts_code', 'inst_csname', 'ind_name', 'url')
AUTHORITY = {'research_authority': 'NONE', 'investment_authority': 'NONE',
             'pdf_acquired': False, 'full_model_qualified': False}


def plan(*, native=False):
    specs = [{'api': 'research_report', 'params': {
        'trade_date': day, 'ts_code': '002281.SZ', 'inst_csname': '长江证券',
        'report_type': '个股研报', 'fields': ','.join(FIELDS), 'limit': '1000'}}
        for day in TARGETS]
    if native:
        specs = specs[:1]
        del specs[0]['params']['fields']
    return specs


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
    saved.check(isinstance(fields, list) and fields
                and all(isinstance(f, str) and f for f in fields)
                and len(fields) == len(set(fields)), 'C1 directory fields incomplete')
    native = 'fields' not in spec['params']
    saved.check(native or set(FIELDS) <= set(fields), 'C1 directory fields incomplete')
    rows = relay.rows(body)
    saved.check(len(rows) < 1000 and (body.get('count') is None
                or type(body['count']) is int and body['count'] == len(rows)),
                'C1 directory may be truncated')
    if native:
        return {'trade_date': spec['params']['trade_date'], 'rows_received': len(rows),
                'status': 'NATIVE_SCHEMA_RETAINED_NOT_REPORT_QUALIFIED',
                'fields': fields, 'request_filter_qualification': 'NOT_CHECKED',
                'original_report_identity': 'NOT_ESTABLISHED_BY_DIRECTORY'}
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


def rebuild(root, expected):
    root = Path(root); _safe_path(root)
    files = {p.name: p for p in root.iterdir()}
    saved.check(len(files) <= 6 and all(p.is_file() and not p.is_symlink() for p in files.values())
                and sum(p.stat().st_size for p in files.values()) <= 20 * 1024 * 1024,
                'C1 retained inventory differs')
    manifest = relay.decode((root/'capture.json').read_bytes())
    saved.check(manifest['capture_hash'] == common.digest(manifest), 'C1 capture hash differs')
    native = manifest['pilot'] == NATIVE_PILOT
    saved.check(manifest['pilot'] in (PILOT, NATIVE_PILOT) and manifest['workflow'] == WORKFLOW
                and manifest['identity'] == identity(expected) and manifest['plan'] == plan(native=native)
                and manifest['authority'] == AUTHORITY
                and len(manifest['records']) == len(plan(native=native)), 'C1 capture binding differs')
    saved.check(manifest.get('predecessor') == (PREDECESSOR if native else None),
                'C1 predecessor differs')
    first, finish = map(saved.clock, (manifest['started_at'], manifest['finished_at']))
    saved.check(first <= finish, 'C1 capture clock reversed')
    seen = {'capture.json'}; previous = first; stopped = False; outcomes = []
    for i, (spec, record) in enumerate(zip(plan(native=native), manifest['records'], strict=True)):
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
    return {'pilot': manifest['pilot'], 'identity': manifest['identity'], 'outcomes': outcomes,
            'logical_queries_attempted': sum(r['status'] not in ('NOT_ATTEMPTED_STOP', 'CREDENTIAL_UNAVAILABLE')
                                             for r in manifest['records']),
            'http_receipts': sum(len(r['attempts']) for r in manifest['records']),
            'source_capture_hash': manifest['capture_hash'], **AUTHORITY}



def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('verify',))
    parser.add_argument('--root', required=True)
    args = parser.parse_args(argv)
    root = Path(args.root)
    result = rebuild(root, os.environ)
    saved.check(common.encoded(result) == (root/'summary.json').read_bytes(), 'C1 replay differs')
    # Do not expose potentially signed historical URLs in public logs.
    print(common.encoded({'pilot': result['pilot'], 'outcomes': [x['status'] for x in result['outcomes']],
                         'http_receipts': result['http_receipts'], **AUTHORITY}).decode())


if __name__ == '__main__':
    main()
