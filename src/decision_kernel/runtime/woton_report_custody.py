"""Read the exact retained Woton H1 report and historical repair metadata.

The bounded source/representation writers are retired. Git history keeps their
execution evidence; current code only verifies exact retained bytes and identity.
"""
from __future__ import annotations

import base64
import json
from urllib.parse import quote


from ..adapters.pdf_text import extract_pdf_text
from ..identity import canonical_hash
from . import current_state as model
from . import external_research_identity as identity
from . import saved_research_once as once

MODE = 'WOTON_H1_PUBLIC_REPORT_CUSTODY_ONLY'
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
DATA_FILES = {'source.pdf', 'extraction.json', 'representation-repair.json', 'representation-failure.json'}


def _read_blob(api, spec, limit):
    """Native Git metadata + raw blob; no widening of ResearchInputSourceRef."""
    once.require(spec['repository'] == once.REPO and model.SHA.fullmatch(spec['ref'])
                 and spec['path'] in {PREFIX + name for name in DATA_FILES}
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




def parse_original(pdf):
    once.require(len(pdf) == PDF_BYTES and once.sha(pdf) == PDF_SHA, 'REPORT_ORIGINAL_BYTES_DIFFER')
    parsed = extract_pdf_text(pdf, max_pdf_bytes=once.MAX_SOURCE_BYTES,
                              max_pages=200, max_extracted_chars=1_000_000)
    once.require(parsed.page_count == 133 and all(t in parsed.pages[0].text
                 for t in ('2026', '半年度报告'))
                 and '000920' in '\n'.join(p.text for p in parsed.pages[:6]),
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
    if 'representation_repair' in saved:
        from .woton_report_representation import FAILURE_SOURCE, MARKER, PDF_SOURCE, PREPARE_SOURCE, original_failure
        repair = saved['representation_repair']
        failure = original_failure(api)
        reservation = identity._json(identity._checked_source(repair['reservation'],
            lambda s: api.file(s['path'], s['ref'])))
        once.require(repair['original_failure'] == FAILURE_SOURCE and repair['source_requests'] == 0
            and repair['original_run_preserved_as_failure'] is True
            and saved['files']['source.pdf'] == PDF_SOURCE
            and all(saved[k] == failure[k] for k in ('requested_at', 'received_at', 'http_status', 'source_requests'))
            and repair['reservation']['path'] == PREFIX + MARKER
            and reservation['original_failure'] == FAILURE_SOURCE
            and reservation['original_pdf'] == PDF_SOURCE and reservation['original_prepare'] == PREPARE_SOURCE
            and reservation['source_requests'] == 0 and reservation['operation'] == 'REBUILD_RETAINED_PDF_ONLY'
            and all(reservation.get(k) == v for k, v in model.AUTHORITY.items())
            and reservation['code_commit'] == saved['code_commit'], 'REPORT_REPAIR_MANIFEST_IDENTITY')
    pdf = _read_blob(api, saved['files']['source.pdf'], once.MAX_SOURCE_BYTES)
    pages = _read_blob(api, saved['files']['extraction.json'], identity.MAX_BYTES)
    once.require(once.raw(parse_original(pdf)) == pages, 'REPORT_EXTRACTION_REPLAY_DIFFERS')
    return pdf, json.loads(pages), saved



