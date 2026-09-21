"""One known public report into native Git custody; never Research or a downloader service.

Reuse #297/5753902322's scope, the original PDF parser, permission check and
create-only Retainer. The old financial question and all failed attempts survive.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import quote

import requests

from ..adapters.pdf_text import extract_pdf_text
from ..identity import canonical_hash
from . import current_state as model
from . import external_research_identity as identity
from . import saved_research_once as once
from .current_state_delivery import GitHubAPI, GitHubReadError
from .stock_research_host import authorize, head
from .stock_research_intake import WORK_REF

MODE = 'WOTON_H1_PUBLIC_REPORT_CUSTODY_ONLY'
REQUEST = 'research_runs/woton-report-custody-request.json'
SOURCE_URL = 'https://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2026/2026-8/2026-08-21/12512184.PDF'
PDF_SHA = '27c74e31c8aaf5a38d27b688f0841d81797816420b591647bfb6763e485b7728'
PDF_BYTES = 1262185
PREFIX = 'research_runs/sources/public-reports/' + PDF_SHA + '/'
QUESTION_ID = 'stock-business-66446c4257a92cd4576ee87ff1bd4ead51ca61a4292befc55cbde3d514b5542c'
PERMISSION = {'comment_id': 5753902322, 'body_sha256': 'a6fedda75600bcde32ec78e26e9ee2bbaa467f769fe4f2d936908acfac474f3f',
              'created_at': '2026-09-21T00:33:28Z'}
SCOPE = {'schema_version': 1, 'enabled': True, 'mode': MODE, 'permission': PERMISSION,
         'source_url': SOURCE_URL, 'expected_sha256': PDF_SHA, 'expected_bytes': PDF_BYTES,
         'subject': '000920.SZ', 'report_period': '2026H1', 'page_count': 133,
         'related_question_id': QUESTION_ID, 'execute_before': '2026-09-23T00:00:00Z'}
COMPLETE = 'SOURCE_CUSTODY_COMPLETE_NOT_RESEARCH'
REUSED = 'EXISTING_SOURCE_ATTEMPT_NO_ACQUISITION'
READY_LABEL = 'woton-h1-source-ready'
OTHER_FLAGS = ('reviewed-question', 'daily-reviewed-question', 'reviewed-question-continuation',
               'deepseek-compat', 'recover-sources', 'prepare-sources', 'source-successor',
               'source-successor-continuation')


def check_environment(env, code):
    once.require(model.SHA.fullmatch(code or '') is not None
                 and env.get('GITHUB_SHA') == code and env.get('EXPECTED_CODE_SHA') == code
                 and env.get('GITHUB_REPOSITORY') == once.REPO
                 and env.get('GITHUB_REF') == 'refs/heads/main'
                 and env.get('GITHUB_WORKFLOW') == 'stock-business-research'
                 and env.get('GITHUB_EVENT_NAME') in {'workflow_dispatch', 'issues'}
                 and env.get('GITHUB_RUN_ATTEMPT') == '1'
                 and str(env.get('GITHUB_RUN_ID', '')).isdigit()
                 and int(env['GITHUB_RUN_ID']) > 0, 'REPORT_WORKFLOW_IDENTITY')
    inputs = json.loads(env.get('REPORT_INPUTS', '{}'))
    if env['GITHUB_EVENT_NAME'] == 'issues':
        once.require(inputs in ({}, None, '') and env.get('REPORT_EVENT_ACTION') == 'labeled'
                     and env.get('REPORT_ISSUE_NUMBER') == '297'
                     and env.get('REPORT_LABEL') == READY_LABEL
                     and env.get('REPORT_SENDER') == 'auguspp'
                     and env.get('REPORT_IS_PULL_REQUEST') == 'false',
                     'REPORT_LABEL_TRANSPORT_SCOPE')
        return
    once.require(set(inputs) == {*OTHER_FLAGS, 'retain-report-source', 'source-stock-run-id', 'code-sha'}
                 and inputs['retain-report-source'] is True and inputs['code-sha'] == code
                 and inputs['source-stock-run-id'] == ''
                 and all(inputs[k] is False for k in OTHER_FLAGS), 'REPORT_EXCLUSIVE_SOURCE_MODE')


def _read_blob(api, spec, limit):
    """Native Git metadata + raw blob; no widening of ResearchInputSourceRef."""
    once.require(spec['repository'] == once.REPO and model.SHA.fullmatch(spec['ref'])
                 and spec['path'] in {PREFIX + 'source.pdf', PREFIX + 'extraction.json'}
                 and type(spec['bytes']) is int and 0 < spec['bytes'] <= limit,
                 'REPORT_SOURCE_REFERENCE')
    data = api.get('contents/' + quote(spec['path'], safe='/') + '?ref=' + spec['ref'])
    once.require(data['type'] == 'file' and data['path'] == spec['path']
                 and data['sha'] == spec['git_blob'] and data['size'] == spec['bytes'],
                 'REPORT_COMMIT_FILE_BINDING')
    stored = api.get('git/blobs/' + spec['git_blob'])
    once.require(stored['encoding'] == 'base64' and stored['sha'] == spec['git_blob']
                 and stored['size'] == spec['bytes']
                 and len(stored['content']) <= 2 * limit, 'REPORT_BLOB_ENVELOPE')
    raw = base64.b64decode(''.join(stored['content'].split()), validate=True)
    once.require(len(raw) == spec['bytes'] and once.sha(raw) == spec['sha256']
                 and once.blob(raw) == spec['git_blob'], 'REPORT_BLOB_BYTES')
    return raw


def _save_data(retain, name, data):
    limit = once.MAX_SOURCE_BYTES if name == 'source.pdf' else identity.MAX_BYTES
    once.require(name in {'source.pdf', 'extraction.json'} and len(data) <= limit,
                 'REPORT_SOURCE_WRITE_SCOPE')
    path = PREFIX + name
    result = retain.native('PUT', 'contents/' + path,
        {'branch': WORK_REF, 'message': 'Retain original public report: ' + name,
         'content': base64.b64encode(data).decode('ascii')})
    retain.uncertain = True
    spec = {**once.source_ref(path, result['commit']['sha'], data, 'PUBLIC_REPORT_SOURCE_ONLY'),
            'bytes': len(data)}
    once.require(result['content']['sha'] == spec['git_blob']
                 and _read_blob(retain.api, spec, limit) == data, 'REPORT_SOURCE_READBACK')
    retain.uncertain = False
    retain.writes.append(spec)
    return spec


def acquire(output, receipt, clock):
    """One ordinary credential-free GET; bounded partial bytes survive failures."""
    receipt.update(phase='PUBLIC_PDF_GET', requested_at=clock(), source_requests=1)
    with requests.Session() as session:
        session.trust_env = False  # No repository token, .netrc or proxy credentials.
        with session.get(SOURCE_URL, timeout=(15, 60), stream=True, allow_redirects=False) as response:
            receipt['http_status'] = response.status_code
            once.require(response.status_code == 200, 'REPORT_HTTP_UNAVAILABLE')
            count = 0
            with (output / 'source.pdf').open('xb') as saved:
                for part in response.iter_content(64 * 1024):
                    count += len(part)
                    once.require(count <= once.MAX_SOURCE_BYTES, 'REPORT_DOWNLOAD_SIZE')
                    saved.write(part)
    receipt['received_at'] = clock()
    return (output / 'source.pdf').read_bytes()


def parse_original(pdf):
    once.require(len(pdf) == PDF_BYTES and once.sha(pdf) == PDF_SHA, 'REPORT_ORIGINAL_BYTES_DIFFER')
    parsed = extract_pdf_text(pdf, max_pdf_bytes=once.MAX_SOURCE_BYTES,
                              max_pages=200, max_extracted_chars=1_000_000)
    once.require(parsed.page_count == 133 and all(t in parsed.pages[0].text
                 for t in ('000920', '2026', '半年度报告')),
                 'REPORT_PRINTED_IDENTITY')
    from .disclosure_source_reading import text_ok
    once.require(all(text_ok(p.text) for p in parsed.pages), 'REPORT_UNREADABLE_PAGE')
    value = {'pdf_sha256': parsed.pdf_sha256, 'text_sha256': parsed.text_sha256,
             'page_count': parsed.page_count,
             'pages': [{'page_number': p.page_number, 'text': p.text} for p in parsed.pages],
             'reading_method': 'ORIGINAL_PYPDF', 'source_url': SOURCE_URL,
             'meaning': 'FULL_SOURCE_TEXT_NOT_FULL_RESEARCH_OR_TABLE_TRUTH_CERTIFICATION'}
    once.require(len(once.raw(value)) <= identity.MAX_BYTES, 'REPORT_EXTRACTION_SIZE')
    return value


def recover(api, source):
    """Read exact source custody and reparse bytes; no source HTTP, egress or writes."""
    once.require(source['path'] == PREFIX + 'source.json', 'REPORT_MANIFEST_SCOPE')
    saved = identity._json(identity._checked_source(source, lambda s: api.file(s['path'], s['ref'])))
    once.require(saved['scope'] == SCOPE and saved['status'] == COMPLETE
                 and type(saved['source_requests']) is int and saved['source_requests'] == 1
                 and saved['http_status'] == 200 and model.SHA.fullmatch(saved['code_commit'])
                 and set(saved['files']) == {'source.pdf', 'extraction.json'}
                 and all(saved['files'][name]['path'] == PREFIX + name for name in saved['files'])
                 and saved['provenance'] == 'ISSUER_REPORT_VIA_SINA_MIRROR_NOT_CNINFO_BYTE_EQUIVALENCE'
                 and saved['custody_hash'] == canonical_hash({k:v for k,v in saved.items() if k != 'custody_hash'})
                 and all(saved.get(k) == v for k,v in model.AUTHORITY.items())
                 and model.clock(PERMISSION['created_at']) <= model.clock(saved['requested_at'])
                 <= model.clock(saved['received_at']) <= model.clock(saved['finished_at'])
                 < model.clock(SCOPE['execute_before']), 'REPORT_MANIFEST_IDENTITY')
    pdf = _read_blob(api, saved['files']['source.pdf'], once.MAX_SOURCE_BYTES)
    pages = _read_blob(api, saved['files']['extraction.json'], identity.MAX_BYTES)
    once.require(once.raw(parse_original(pdf)) == pages, 'REPORT_EXTRACTION_REPLAY_DIFFERS')
    return pdf, json.loads(pages), saved


def run(*, api, code, output, clock=once.now, download=acquire, retainer_factory=once.Retainer):
    once.require(not output.exists() and not output.is_symlink()
                 and not any(p.is_symlink() for p in output.parents), 'REPORT_CREATE_ONLY_OUTPUT')
    output.mkdir(parents=True)
    receipt = {'mode': MODE, 'code_commit': code, 'started_at': clock(),
        'status': 'SOURCE_CUSTODY_FAILED', 'phase': 'AUTHORIZATION', 'source_requests': 0,
        'formal_research_started': False, 'model_calls': 0, 'market_requests': 0,
        'automatic_retry': False, 'research_root_reset': False, **model.AUTHORITY}
    retain = None
    reserved = False
    try:
        request = identity._json(api.file(REQUEST, code))
        once.require(request == SCOPE and model.clock(PERMISSION['created_at']) <= model.clock(clock())
                     < model.clock(SCOPE['execute_before']), 'REPORT_REQUEST_SCOPE')
        authorize(api, code, request, request_path=REQUEST, mode=MODE)
        work = head(api, WORK_REF)
        try:
            existing = api.get('contents/' + PREFIX.rstrip('/') + '?ref=' + work)
        except GitHubReadError as exc:
            if str(exc) != 'GitHub HTTP 404':
                raise
            existing = []
        once.require(isinstance(existing, list), 'REPORT_SOURCE_DIRECTORY')
        if existing:
            receipt.update(status=REUSED, work_commit=work,
                           meaning='SAVED_OR_PARTIAL_ATTEMPT_NOT_PROOF_OF_COMPLETE_SOURCE_CUSTODY')
            return receipt
        retain = retainer_factory(api, {'prefix': PREFIX, 'id': 'report-source-' + PDF_SHA,
                                  'work_ref': WORK_REF}, code, output)
        retain.save('prepare.json', {'scope': SCOPE, 'code_commit': code,
            'started_at': clock(), 'run_id': os.environ.get('GITHUB_RUN_ID'),
            'operation': 'SOURCE_ONLY_NOT_RESEARCH_LAUNCH',
            'trigger_event': os.environ.get('GITHUB_EVENT_NAME'),
            'trigger_issue': os.environ.get('REPORT_ISSUE_NUMBER'),
            'trigger_label': os.environ.get('REPORT_LABEL'), **model.AUTHORITY})
        reserved = True
        authorize(api, code, request, request_path=REQUEST, mode=MODE)
        once.require(model.clock(clock()) < model.clock(SCOPE['execute_before']), 'REPORT_SCOPE_EXPIRED')
        pdf = download(output, receipt, clock)
        once.require(len(pdf) == PDF_BYTES and once.sha(pdf) == PDF_SHA, 'REPORT_ORIGINAL_BYTES_DIFFER')
        receipt['phase'] = 'ORIGINAL_GIT_RETENTION'
        pdf_source = _save_data(retain, 'source.pdf', pdf)
        receipt['phase'] = 'FULL_PDF_REPRESENTATION'
        extraction = once.raw(parse_original(pdf))
        (output / 'extraction.json').write_bytes(extraction)
        text_source = _save_data(retain, 'extraction.json', extraction)
        manifest = {'scope': SCOPE, 'status': COMPLETE, 'code_commit': code,
            'source_requests': receipt['source_requests'], 'http_status': receipt['http_status'],
            'requested_at': receipt['requested_at'], 'received_at': receipt['received_at'],
            'finished_at': clock(), 'files': {'source.pdf': pdf_source, 'extraction.json': text_source},
            'provenance': 'ISSUER_REPORT_VIA_SINA_MIRROR_NOT_CNINFO_BYTE_EQUIVALENCE', **model.AUTHORITY}
        manifest['custody_hash'] = canonical_hash(manifest)
        manifest_source = retain.save('source.json', manifest)
        actual_pdf, actual_text, _ = recover(api, manifest_source)
        once.require(actual_pdf == pdf and once.raw(actual_text) == extraction, 'REPORT_CUSTODY_READBACK')
        receipt.update(status=COMPLETE, phase='COMPLETE', source=manifest_source,
                       custody_hash=manifest['custody_hash'], page_count=133)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError,
            requests.RequestException, subprocess.SubprocessError) as exc:
        receipt.update(error_type=type(exc).__name__,
                       error_code=exc.code if isinstance(exc, once.TrialError) else 'REPORT_OPERATION_UNAVAILABLE',
                       failure_meaning='SOURCE_OPERATION_FAILED_NOT_NO_REPORT_OR_BUSINESS_WAIT')
        if reserved and retain is not None and not retain.uncertain:
            try:
                retain.save('failure.json', receipt)
            except (ValueError, RuntimeError, OSError, KeyError, subprocess.SubprocessError):
                receipt['failure_retention_uncertain'] = True
    finally:
        receipt.update(finished_at=clock(), remote_writes=[] if retain is None else retain.writes,
                       mutation_uncertain=False if retain is None else retain.uncertain)
        (output / 'host-receipt.json').write_bytes(once.raw(receipt))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=MODE)
    parser.add_argument('--code-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    check_environment(os.environ, args.code_commit)
    once.require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
                 == args.code_commit, 'REPORT_CHECKOUT_IDENTITY')
    result = run(api=GitHubAPI(os.environ['GH_TOKEN'], max_calls=48), code=args.code_commit, output=args.output)
    print(result['status'])
    return 0 if result['status'] in {COMPLETE, REUSED} else 2


if __name__ == '__main__':
    raise SystemExit(main())
