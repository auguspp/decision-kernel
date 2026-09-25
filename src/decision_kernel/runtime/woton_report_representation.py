"""Historical identity bindings for the completed Woton representation repair.

The repair writer is retired. These immutable bindings remain only because the
current reader must validate the already-retained repair lineage exactly.
"""
from __future__ import annotations

from . import woton_report_custody as c

SOURCE_LABEL = 'woton-h1-source-ready'
REPAIR_LABEL = 'woton-h1-representation-ready'
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

def original_failure(api):
    def read(spec):
        return c.identity._json(c.identity._checked_source(spec, lambda s: api.file(s['path'], s['ref'])))
    failure, prepare = read(FAILURE_SOURCE), read(PREPARE_SOURCE)
    c.once.require(prepare['scope'] == c.SCOPE and prepare['code_commit'] == FAILED_CODE
        and prepare['run_id'] == FAILED_RUN and prepare['trigger_event'] == 'issues'
        and prepare['trigger_issue'] == '297' and prepare['trigger_label'] == SOURCE_LABEL
        and failure['code_commit'] == FAILED_CODE and failure['status'] == 'SOURCE_CUSTODY_FAILED'
        and failure['phase'] == 'FULL_PDF_REPRESENTATION' and failure['error_code'] == 'REPORT_PRINTED_IDENTITY'
        and failure['http_status'] == 200 and type(failure['source_requests']) is int
        and failure['source_requests'] == 1 and failure['formal_research_started'] is False
        and failure['model_calls'] == failure['market_requests'] == 0
        and all(failure.get(k) == v for k, v in c.model.AUTHORITY.items()), 'REPORT_REPAIR_PREDECESSOR')
    return failure

