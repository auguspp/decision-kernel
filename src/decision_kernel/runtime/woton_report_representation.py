"""Finish one exact retained-PDF representation failure; no source acquisition.

The original run/prepare/failure/PDF stay immutable. This is an explicit local
interpretation repair under the original source scope, never a producer retry.
"""
from __future__ import annotations

import os
import subprocess

import requests

from . import woton_report_custody as c

FAILED_CODE = 'aedf5160c344204b3595687c152c750af9cba0a3'
FAILED_COMMIT = '75f3b7e88037d1eb8c2558b9a981ccb25d4dd17a'
FAILED_RUN = '35550930725'
PDF_SOURCE = {'repository': c.once.REPO, 'ref': '7ec7eee11ac61aecdf05940904631a47cc07436a',
    'path': c.PREFIX + 'source.pdf', 'bytes': 1262185,
    'git_blob': '87b56650d5ec01935e94e97d9e60ad986cb378d1', 'sha256': c.PDF_SHA,
    'purpose': 'PUBLIC_REPORT_SOURCE_ONLY'}
FAILURE_SOURCE = {'repository': c.once.REPO, 'ref': FAILED_COMMIT,
    'path': c.PREFIX + 'failure.json', 'git_blob': 'f45c0d6d004cc67145218df27dc43de11169c4b0',
    'sha256': '2e29dfe9c00f591dec9231197b07fac204ad9fa4fab188d8ed605fb3fa01ebff',
    'purpose': 'ORIGINAL_SOURCE_REPRESENTATION_FAILURE'}
PREPARE_SOURCE = {'repository': c.once.REPO, 'ref': '14d2efc0fd2f741bf6496721823a42028b40eae2',
    'path': c.PREFIX + 'prepare.json', 'git_blob': '1ff1968388e4393cbb4c2a5f6591376533105780',
    'sha256': '890156d755d07bea8e8c75f465b7c0d76f9263a953bc795001f9ab63947adca4',
    'purpose': 'ORIGINAL_SOURCE_RESERVATION'}
MARKER = 'representation-repair.json'


def _save_metadata(retain, name, value):
    c.once.require(name in {MARKER, 'representation-failure.json'}, 'REPORT_REPAIR_WRITE_SCOPE')
    data = c.once.raw(value)
    retain.local(name, data)
    return c._save_data(retain, name, data)


def original_failure(api):
    def read(spec):
        return c.identity._json(c.identity._checked_source(spec, lambda s: api.file(s['path'], s['ref'])))
    failure, prepare = read(FAILURE_SOURCE), read(PREPARE_SOURCE)
    c.once.require(prepare['scope'] == c.SCOPE and prepare['code_commit'] == FAILED_CODE
        and prepare['run_id'] == FAILED_RUN and prepare['trigger_event'] == 'issues'
        and prepare['trigger_issue'] == '297' and prepare['trigger_label'] == c.READY_LABEL
        and failure['code_commit'] == FAILED_CODE and failure['status'] == 'SOURCE_CUSTODY_FAILED'
        and failure['phase'] == 'FULL_PDF_REPRESENTATION' and failure['error_code'] == 'REPORT_PRINTED_IDENTITY'
        and failure['http_status'] == 200 and type(failure['source_requests']) is int
        and failure['source_requests'] == 1 and failure['formal_research_started'] is False
        and failure['model_calls'] == failure['market_requests'] == 0
        and all(failure.get(k) == v for k, v in c.model.AUTHORITY.items()), 'REPORT_REPAIR_PREDECESSOR')
    return failure


def run(*, api, code, output, clock=c.once.now, retainer_factory=c.once.Retainer):
    c.once.require(not output.exists() and not output.is_symlink()
        and not any(p.is_symlink() for p in output.parents), 'REPORT_CREATE_ONLY_OUTPUT')
    output.mkdir(parents=True)
    receipt = {'mode': 'RETAINED_REPORT_REPRESENTATION_ONLY', 'code_commit': code,
        'started_at': clock(), 'status': 'SOURCE_REPRESENTATION_REPAIR_FAILED', 'phase': 'AUTHORIZATION',
        'source_requests': 0, 'model_calls': 0, 'market_requests': 0,
        'formal_research_started': False, 'automatic_retry': False,
        'research_root_reset': False, 'original_failed_run': FAILED_RUN, **c.model.AUTHORITY}
    retain = None; reserved = False
    try:
        c.authorize(api, code, c.SCOPE, request_path=c.REQUEST, mode=c.MODE)
        c.once.require(c.model.clock(c.PERMISSION['created_at']) <= c.model.clock(clock())
            < c.model.clock(c.SCOPE['execute_before']), 'REPORT_SCOPE_EXPIRED')
        work = c.head(api, c.WORK_REF)
        rows = api.get('contents/' + c.PREFIX.rstrip('/') + '?ref=' + work)
        c.once.require(isinstance(rows, list) and len(rows) <= 7, 'REPORT_REPAIR_DIRECTORY')
        names = {r['name'] for r in rows}
        c.once.require(len(names) == len(rows), 'REPORT_REPAIR_DIRECTORY')
        if MARKER in names:
            receipt.update(status=c.REUSED, work_commit=work,
                meaning='REPAIR_ALREADY_ATTEMPTED_NOT_PROOF_OF_COMPLETE_REPRESENTATION')
            return receipt
        c.once.require(names == {'prepare.json', 'failure.json', 'source.pdf'}, 'REPORT_REPAIR_EXPECTED_FILES')
        failure = original_failure(api)
        # Current directory must still contain the exact pinned failed originals.
        for spec in (PREPARE_SOURCE, FAILURE_SOURCE):
            c.identity._checked_source({**spec, 'ref': work}, lambda s: api.file(s['path'], s['ref']))
        pdf = c._read_blob(api, {**PDF_SOURCE, 'ref': work}, c.once.MAX_SOURCE_BYTES)
        c.once.require(pdf == c._read_blob(api, PDF_SOURCE, c.once.MAX_SOURCE_BYTES), 'REPORT_REPAIR_SOURCE_CHANGED')
        (output / 'source.pdf').write_bytes(pdf)
        retain = retainer_factory(api, {'prefix': c.PREFIX, 'id': 'report-representation-' + c.PDF_SHA,
            'work_ref': c.WORK_REF}, code, output)
        marker = _save_metadata(retain, MARKER, {'code_commit': code, 'original_failure': FAILURE_SOURCE,
            'original_prepare': PREPARE_SOURCE, 'original_pdf': PDF_SOURCE, 'source_requests': 0,
            'operation': 'REBUILD_RETAINED_PDF_ONLY', 'started_at': clock(),
            'run_id': os.environ.get('GITHUB_RUN_ID'), 'trigger_label': c.REPRESENTATION_LABEL,
            **c.model.AUTHORITY})
        reserved = True
        c.authorize(api, code, c.SCOPE, request_path=c.REQUEST, mode=c.MODE)
        receipt['phase'] = 'FULL_PDF_REPRESENTATION'
        extraction = c.once.raw(c.parse_original(pdf))
        (output / 'extraction.json').write_bytes(extraction)
        text_source = c._save_data(retain, 'extraction.json', extraction)
        manifest = {'scope': c.SCOPE, 'status': c.COMPLETE, 'code_commit': code,
            'source_requests': failure['source_requests'], 'http_status': failure['http_status'],
            'requested_at': failure['requested_at'], 'received_at': failure['received_at'],
            'finished_at': clock(), 'files': {'source.pdf': PDF_SOURCE, 'extraction.json': text_source},
            'representation_repair': {'original_failure': FAILURE_SOURCE, 'reservation': marker,
                'source_requests': 0, 'original_run_preserved_as_failure': True},
            'provenance': 'ISSUER_REPORT_VIA_SINA_MIRROR_NOT_CNINFO_BYTE_EQUIVALENCE', **c.model.AUTHORITY}
        manifest['custody_hash'] = c.canonical_hash(manifest)
        source = retain.save('source.json', manifest)
        actual_pdf, actual_text, _ = c.recover(api, source)
        c.once.require(actual_pdf == pdf and c.once.raw(actual_text) == extraction, 'REPORT_CUSTODY_READBACK')
        receipt.update(status=c.COMPLETE, phase='COMPLETE', source=source,
            custody_hash=manifest['custody_hash'], page_count=133,
            meaning='ORIGINAL_SOURCE_RETAINED_REPRESENTATION_FINISHED_NOT_ORIGINAL_RUN_SUCCESS')
    except (ValueError, KeyError, TypeError, OSError, RuntimeError,
            requests.RequestException, subprocess.SubprocessError) as exc:
        receipt.update(error_type=type(exc).__name__,
            error_code=exc.code if isinstance(exc, c.once.TrialError) else 'REPORT_REPAIR_OPERATION_UNAVAILABLE')
        if reserved and retain is not None and not retain.uncertain:
            try:
                _save_metadata(retain, 'representation-failure.json', receipt)
            except (ValueError, RuntimeError, OSError, KeyError, subprocess.SubprocessError):
                receipt['failure_retention_uncertain'] = True
    finally:
        receipt.update(finished_at=clock(), remote_writes=[] if retain is None else retain.writes,
            mutation_uncertain=False if retain is None else retain.uncertain)
        (output / 'host-receipt.json').write_bytes(c.once.raw(receipt))
    return receipt
