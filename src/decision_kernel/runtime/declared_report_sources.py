"""Explicit report preparation through existing discovery, HTTP, PDF and Git owners.

A source-only composition in the original workflow, not another provider or
Research executor. Mirrors keep their identity; no returned text grants authority.
"""
from __future__ import annotations

import argparse
import base64
from datetime import date
import os
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

from bs4 import BeautifulSoup
import requests

from ..adapters.pdf_text import extract_pdf_text
from . import current_state as reading, external_research_identity as identity
from . import saved_research_once as once, stock_research_sources as sources
from .current_state_delivery import GitHubAPI, GitHubReadError
from .stock_research_host import authorize, head
from .stock_research_intake import WORK_REF, security

REQUEST = 'research_runs/declared-report-source-request.json'
MODE = 'DECLARED_PUBLIC_REPORT_SOURCES_ONLY'
LABEL = 'declared-report-sources-ready'
ROOT = 'research_runs/sources/declared-reports/'
MAX_PDF = once.MAX_SOURCE_BYTES
MAX_HTML = 2 * 1024 * 1024


def check_request(value, clock):
    once.require(set(value) == {'schema_version', 'enabled', 'mode', 'permission', 'batch_id',
        'subject', 'issuer_name', 'question_id', 'execute_before', 'reports'}, 'REPORT_PLAN_SHAPE')
    once.require(value['schema_version'] == 1 and value['enabled'] is True and value['mode'] == MODE
        and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', value['batch_id'])
        and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,127}', value['question_id'])
        and isinstance(value['issuer_name'], str) and 1 <= len(value['issuer_name']) <= 90,
        'REPORT_PLAN_IDENTITY')
    security(value['subject'])
    now = reading.clock(clock())
    once.require(reading.clock(value['permission']['created_at']) <= now
        < reading.clock(value['execute_before']), 'REPORT_PLAN_EXPIRED')
    reports = value['reports']
    once.require(isinstance(reports, list) and 0 < len(reports) <= 2, 'REPORT_PLAN_CAPACITY')
    periods = []
    for row in reports:
        once.require(set(row) == {'period', 'announcement_date', 'cninfo_locator', 'sina_id'}
            and re.fullmatch(r'20[0-9]{2}(?:FY|H1)', row['period'])
            and re.fullmatch(r'[0-9]{1,20}', row['sina_id']), 'REPORT_PLAN_REPORT')
        day = date.fromisoformat(row['announcement_date'])
        end = date(int(row['period'][:4]), 6, 30) if row['period'].endswith('H1') else date(int(row['period'][:4]), 12, 31)
        once.require(end <= day <= now.date() and day.isoformat() == row['announcement_date'], 'REPORT_PLAN_DATE')
        if row['cninfo_locator'] is not None:
            once.require(re.fullmatch(r'https://static\.cninfo\.com\.cn/finalpage/'
                + re.escape(day.isoformat()) + r'/[0-9]+\.[Pp][Dd][Ff]', row['cninfo_locator']), 'REPORT_PLAN_LOCATOR')
        periods.append(row['period'])
    once.require(len(periods) == len(set(periods)), 'REPORT_PLAN_DUPLICATE')
    return value


class ScopeChanged(once.TrialError):
    pass


class SourceFetchError(once.TrialError):
    def __init__(self, body, status):
        super().__init__('REPORT_HTTP_INCOMPLETE')
        self.body, self.status = bytes(body), status


def public_get(url, limit):
    """Reuse requests' credential-free streaming/no-redirect transport, no retry."""
    raw, status = bytearray(), None
    try:
        with requests.Session() as session:
            session.trust_env = False
            with session.get(url, timeout=(15, 60), stream=True, allow_redirects=False,
                             headers={'Accept-Encoding': 'identity'}) as response:
                status = response.status_code
                once.require(response.url == url and response.headers.get('Content-Encoding', 'identity') == 'identity',
                             'REPORT_HTTP_REPRESENTATION')
                for chunk in response.iter_content(64 * 1024):
                    once.require(len(raw) + len(chunk) <= limit, 'REPORT_HTTP_SIZE')
                    raw.extend(chunk)
                length = response.headers.get('Content-Length')
                once.require(length is None or length.isdigit() and int(length) == len(raw), 'REPORT_HTTP_LENGTH')
                return status, bytes(raw)
    except (requests.RequestException, once.TrialError) as exc:
        raise SourceFetchError(raw, status) from exc


def sina_locator(raw, row, subject, issuer_name):
    """Use the actual page link, never fabricate a PDF path or CNINFO identity."""
    soup = BeautifulSoup(raw, 'html.parser')
    text = soup.get_text(' ', strip=True)
    title = row['period'][:4] + ('年半年度报告' if row['period'].endswith('H1') else '年年度报告')
    once.require(all(t in text for t in (subject[:6], issuer_name, title, row['announcement_date']))
        and '\ufffd' not in text, 'REPORT_SINA_PAGE_IDENTITY')
    suffix = 'CNSESH_STOCK' if subject.endswith('.SH') else 'CNSESZ_STOCK'
    day = date.fromisoformat(row['announcement_date'])
    expected_path = f'/211.154.219.97:9494/MRGG/{suffix}/{day.year}/{day.year}-{day.month}/{day.isoformat()}/{row["sina_id"]}.PDF'
    links = set()
    for tag in soup.find_all('a', href=True):
        url = tag['href']
        parts = urlsplit(url)
        if (parts.scheme == 'https' and parts.netloc == 'file.finance.sina.com.cn'
            and unquote(parts.path) == expected_path and not parts.query and not parts.fragment):
            links.add(url)
    once.require(len(links) == 1, 'REPORT_SINA_PDF_LINK_MISSING_OR_AMBIGUOUS')
    return links.pop()


def _store(retain, name, raw):
    """Reuse original create-only native Git mutation, with exact blob readback."""
    once.require(re.fullmatch(r'(?:20[0-9]{2}(?:FY|H1))-(?:cninfo|sina)-(?:source\.pdf|extraction\.json)', name)
                 and 0 < len(raw) <= MAX_PDF, 'REPORT_RETAINED_FILE_SCOPE')
    path = retain.request['prefix'] + name
    result = retain.native('PUT', 'contents/' + path, {'branch': WORK_REF,
        'message': 'Retain declared public report source: ' + name, 'content': base64.b64encode(raw).decode('ascii')})
    retain.uncertain = True
    spec = {**once.source_ref(path, result['commit']['sha'], raw, 'DECLARED_REPORT_SOURCE_NOT_ADMISSION'), 'bytes': len(raw)}
    meta = retain.api.get('contents/' + quote(path, safe='/') + '?ref=' + spec['ref'])
    stored = retain.api.get('git/blobs/' + spec['git_blob'])
    once.require(result['content']['sha'] == meta['sha'] == stored['sha'] == spec['git_blob']
        and meta['type'] == 'file' and meta['path'] == path
        and meta['size'] == stored['size'] == len(raw) and stored['encoding'] == 'base64'
        and base64.b64decode(''.join(stored['content'].split()), validate=True) == raw, 'REPORT_GIT_READBACK')
    retain.uncertain = False
    retain.writes.append(spec)
    return spec


def acquire_reports(plan, output, check, *, fetch=public_get, discover=sources.prepare_report_discovery,
                    clock=once.now, save=None):
    """At most one declared official route and one independent mirror per report."""
    result = {'status': 'SOURCE_GAPS', 'reports': [], 'requests': [], 'model_calls': 0,
              'research_executions': 0, 'automatic_retry': False, **reading.AUTHORITY}
    def get(url, name, limit):
        check()
        item = {'url': url, 'requested_at': clock(), 'status': 'TRANSPORT_UNAVAILABLE', 'body': None}
        result['requests'].append(item)
        try:
            status, body = fetch(url, limit)
            once.require(type(status) is int and isinstance(body, bytes) and len(body) <= limit, 'REPORT_HTTP_CONTRACT')
            (output / name).write_bytes(body)
            item.update(status='HTTP_BODY_RETAINED', http_status=status, received_at=clock(),
                        body=name, bytes=len(body), sha256=once.sha(body))
            once.require(status == 200, 'REPORT_HTTP_UNAVAILABLE')
            return body
        except Exception as exc:
            item['error_type'] = type(exc).__name__
            if isinstance(exc, SourceFetchError) and exc.body:
                partial = name + '.partial'
                (output / partial).write_bytes(exc.body)
                item.update(status='PARTIAL_HTTP_BODY_NOT_COMPLETE', http_status=exc.status,
                            body=partial, bytes=len(exc.body), sha256=once.sha(exc.body))
            raise
        finally:
            item['finished_at'] = clock()
    for row in plan['reports']:
        record = {'period': row['period'], 'publication_date': row['announcement_date'],
            'publication_precision': 'DAY_NOT_AVAILABILITY_TIMESTAMP', 'routes': [], 'selected_source': None}
        result['reports'].append(record)
        for provider in ('cninfo', 'sina'):
            check()
            route = {'provider': provider, 'status': 'SOURCE_UNAVAILABLE'}
            record['routes'].append(route)
            prefix = row['period'] + '-' + provider
            try:
                if provider == 'cninfo':
                    locator = row['cninfo_locator']
                    if locator is None:
                        lead = discover(ticker=plan['subject'][:6], announcement_date=date.fromisoformat(row['announcement_date']),
                            period=row['period'], issuer_name=plan['issuer_name'], output=output / (prefix + '-discovery'), clock=clock)
                        route['discovery'] = lead
                        once.require(lead['status'] == 'OFFICIAL_REPORT_LOCATED_NOT_ACQUIRED', 'REPORT_OFFICIAL_DISCOVERY_UNAVAILABLE')
                        official = lead['official_report']
                        once.require(official['stock_code'] == plan['subject'][:6], 'REPORT_OFFICIAL_ISSUER_DIFFERS')
                        locator = official['source_locator']
                    once.require(re.fullmatch(r'https://static\.cninfo\.com\.cn/finalpage/'
                        + re.escape(row['announcement_date']) + r'/[0-9]+\.[Pp][Dd][Ff]', locator), 'REPORT_OFFICIAL_LOCATOR')
                else:
                    page = f'https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id={row["sina_id"]}&stockid={plan["subject"][:6]}'
                    html = get(page, prefix + '-page.html', MAX_HTML)
                    locator = sina_locator(html, row, plan['subject'], plan['issuer_name'])
                    route['page_url'] = page
                route['locator'] = locator
                raw = get(locator, prefix + '-source.pdf', MAX_PDF)
                route.update(status='ORIGINAL_BYTES_RETAINED_NOT_YET_PARSED', bytes=len(raw), pdf_sha256=once.sha(raw))
                if save is not None:
                    route['pdf_source'] = save(prefix + '-source.pdf', raw)
                parsed = extract_pdf_text(raw, max_pdf_bytes=MAX_PDF, max_pages=500, max_extracted_chars=1_000_000)
                front = '\n'.join(p.text for p in parsed.pages[:10])
                title = '半年度报告' if row['period'].endswith('H1') else '年度报告'
                compact = re.sub(r'\s+', '', front)
                match = re.search(re.escape(row['period'][:4]) + r'年?(半年度报告|年度报告)', compact)
                once.require(plan['subject'][:6] in front and match is not None and match[1] == title
                    and not re.search(re.escape(row['period'][:4]) + r'年?(?:半年度报告|年度报告)摘要',
                                      re.sub(r'\s+', '', parsed.pages[0].text)), 'REPORT_PRINTED_IDENTITY')
                extraction = {'pdf_sha256': parsed.pdf_sha256, 'text_sha256': parsed.text_sha256,
                    'page_count': parsed.page_count, 'pages': [{'page_number': p.page_number, 'text': p.text} for p in parsed.pages],
                    'locator': locator, 'representation': 'ORIGINAL_PYPDF_NOT_TABLE_TRUTH',
                    'empty_pages': [p.page_number for p in parsed.pages if not p.text.strip()]}
                data = once.raw(extraction)
                (output / (prefix + '-extraction.json')).write_bytes(data)
                if save is not None:
                    route['extraction_source'] = save(prefix + '-extraction.json', data)
                route.update(status='REPORT_PARSED_NOT_ADMITTED', page_count=parsed.page_count,
                    provenance='CNINFO_ISSUER_REPORT' if provider == 'cninfo' else 'ISSUER_REPORT_VIA_SINA_NOT_CNINFO_BYTE_EQUIVALENCE',
                    empty_pages=extraction['empty_pages'], replacement_characters=sum(p.text.count('\ufffd') for p in parsed.pages))
                record['selected_source'] = provider
                break
            except Exception as exc:
                # An uncertain Git write stops the whole batch, not a new source route.
                if isinstance(exc, ScopeChanged) or save is not None and getattr(save, 'uncertain', lambda: False)():
                    raise
                route.update(error_type=type(exc).__name__, error_code=getattr(exc, 'code', None))
    if all(r['selected_source'] is not None for r in result['reports']):
        result['status'] = 'DECLARED_REPORTS_RETAINED_NOT_RESEARCH'
    return result


def run(*, api, code, output, clock=once.now, fetch=public_get, discover=sources.prepare_report_discovery,
        retainer_factory=once.Retainer):
    once.require(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in output.parents), 'REPORT_OUTPUT_EXISTS_OR_UNSAFE')
    output.mkdir(parents=True)
    result = {'status': 'NOT_STARTED', 'code_commit': code, 'started_at': clock(), **reading.AUTHORITY}
    retain = None
    try:
        plan = check_request(identity._json(api.file(REQUEST, code)), clock)
        def check():
            try:
                check_request(plan, clock)
                authorize(api, code, plan, request_path=REQUEST, mode=MODE)
            except Exception as exc:
                raise ScopeChanged('REPORT_SOURCE_SCOPE_CHANGED') from exc
        check()
        prefix = ROOT + plan['batch_id'] + '/'
        work = head(api, WORK_REF)
        try:
            existing = api.get('contents/' + prefix.rstrip('/') + '?ref=' + work)
        except GitHubReadError as exc:
            if str(exc) != 'GitHub HTTP 404': raise
            existing = []
        once.require(isinstance(existing, list), 'REPORT_SOURCE_HISTORY')
        if existing:
            result['status'] = 'EXISTING_SOURCE_ATTEMPT_NOT_REACQUIRED'
            return result
        (output / 'git').mkdir()
        retain = retainer_factory(api, {'prefix': prefix, 'id': plan['batch_id'], 'work_ref': WORK_REF}, code, output / 'git')
        retain.save('prepare.json', {'plan': plan, 'code_commit': code, 'started_at': clock(),
            'run_id': os.environ.get('GITHUB_RUN_ID'), 'event': os.environ.get('GITHUB_EVENT_NAME'), **reading.AUTHORITY})
        def save(name, raw):
            check()
            return _store(retain, name, raw)
        save.uncertain = lambda: retain.uncertain
        result.update(acquire_reports(plan, output, check, fetch=fetch, discover=discover, clock=clock, save=save))
        result.update(plan=plan, acquisition_finished_at=clock())
        check()
        result['source_manifest'] = retain.save('source.json', result)
    except Exception as exc:
        result.update(status='SOURCE_PREPARATION_INCOMPLETE', error_type=type(exc).__name__, error_code=getattr(exc, 'code', None))
    finally:
        result.update(finished_at=clock(), mutation_uncertain=bool(retain and retain.uncertain))
        (output / 'source-receipt.json').write_bytes(once.raw(result))
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--code-commit', required=True)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args(argv)
    env = os.environ
    once.require(env.get('GITHUB_REPOSITORY') == once.REPO and env.get('GITHUB_REF') == 'refs/heads/main'
        and env.get('GITHUB_SHA') == args.code_commit and reading.SHA.fullmatch(args.code_commit)
        and env.get('GITHUB_WORKFLOW') == 'stock-business-research' and env.get('GITHUB_RUN_ATTEMPT') == '1'
        and env.get('GITHUB_RUN_ID', '').isdigit() and int(env['GITHUB_RUN_ID']) > 0
        and env.get('GITHUB_EVENT_NAME') == 'issues' and env.get('SOURCE_ACTION') == 'labeled'
        and env.get('SOURCE_ISSUE') == '297' and env.get('SOURCE_LABEL') == LABEL
        and env.get('SOURCE_SENDER') == 'auguspp' and env.get('SOURCE_IS_PR') == 'false', 'REPORT_NATIVE_SOURCE_IDENTITY')
    api = GitHubAPI(env['GH_TOKEN'], max_calls=256)
    runs = api.get('actions/runs?head_sha=' + args.code_commit + '&event=push&per_page=30')['workflow_runs']
    tests = [r for r in runs if r['path'] == '.github/workflows/ci.yml' and r['head_sha'] == args.code_commit
             and r['head_branch'] == 'main' and r['event'] == 'push']
    latest = max(tests, key=lambda r: r['id']) if tests else {}
    once.require(latest.get('status') == 'completed' and latest.get('conclusion') == 'success'
                 and latest.get('run_attempt') == 1, 'REPORT_INDEPENDENT_MAIN_CI_REQUIRED')
    result = run(api=api, code=args.code_commit, output=args.output)
    print(result['status'])
    return 0 if result['status'] in {'DECLARED_REPORTS_RETAINED_NOT_RESEARCH', 'EXISTING_SOURCE_ATTEMPT_NOT_REACQUIRED'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
