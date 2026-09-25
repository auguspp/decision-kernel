"""Historical Woton representation lineage remains readable after writer retirement."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from decision_kernel.runtime import woton_report_custody as c
from decision_kernel.runtime import woton_report_representation as r
from test_woton_report_custody import API, CODE, no_network

FIXTURE = Path(__file__).parent / 'fixtures/woton_original'
AT = '2026-09-21T01:40:00Z'

def api():
    value = API()
    files = {c.PREFIX + name: (FIXTURE/name).read_bytes() for name in ('source.pdf','prepare.json','failure.json')}
    files['old-research/failure.json'] = b'ORIGINAL_RESEARCH_FAILURE'
    for ref in (r.FAILED_COMMIT, r.PDF_SOURCE['ref'], r.PREPARE_SOURCE['ref']):
        value.versions[ref] = deepcopy(files)
    value.head = r.FAILED_COMMIT
    for data in files.values(): value.blobs[c.once.blob(data)] = data
    return value

@pytest.fixture(scope='module')
def completed_snapshot():
    value = api(); pdf = (FIXTURE/'source.pdf').read_bytes(); parsed = c.parse_original(pdf); extraction = c.once.raw(parsed)
    text_ref, marker_ref, source_ref = 'c' * 40, 'd' * 40, 'e' * 40
    text_path = c.PREFIX + 'extraction.json'; value.versions[text_ref] = {text_path: extraction}; value.blobs[c.once.blob(extraction)] = extraction
    text_source = {**c.once.source_ref(text_path, text_ref, extraction, 'PUBLIC_REPORT_SOURCE_ONLY'), 'bytes': len(extraction)}
    marker = {'code_commit': CODE, 'original_failure': r.FAILURE_SOURCE, 'original_prepare': r.PREPARE_SOURCE,
        'original_pdf': r.PDF_SOURCE, 'source_requests': 0, 'operation': 'REBUILD_RETAINED_PDF_ONLY',
        'started_at': AT, 'run_id': '35560000000', 'trigger_label': r.REPAIR_LABEL, **c.model.AUTHORITY}
    marker_raw = c.once.raw(marker); marker_path = c.PREFIX + r.MARKER
    value.versions[marker_ref] = {marker_path: marker_raw}
    marker_source = c.once.source_ref(marker_path, marker_ref, marker_raw, 'PUBLIC_REPORT_SOURCE_ONLY')
    failure = r.original_failure(value)
    manifest = {'scope': c.SCOPE, 'status': c.COMPLETE, 'code_commit': CODE,
        'source_requests': failure['source_requests'], 'http_status': failure['http_status'],
        'requested_at': failure['requested_at'], 'received_at': failure['received_at'], 'finished_at': AT,
        'files': {'source.pdf': r.PDF_SOURCE, 'extraction.json': text_source},
        'representation_repair': {'original_failure': r.FAILURE_SOURCE, 'reservation': marker_source,
            'source_requests': 0, 'original_run_preserved_as_failure': True},
        'provenance': 'ISSUER_REPORT_VIA_SINA_MIRROR_NOT_CNINFO_BYTE_EQUIVALENCE', **c.model.AUTHORITY}
    manifest['custody_hash'] = c.canonical_hash(manifest); raw = c.once.raw(manifest); path = c.PREFIX + 'source.json'
    value.versions[source_ref] = {path: raw}
    return value, c.once.source_ref(path, source_ref, raw, 'WOTON_PUBLIC_REPORT_CUSTODY'), parsed

def test_representation_writer_is_retired_but_historical_bindings_remain():
    assert not hasattr(r, 'run') and r.FAILED_RUN == '35550930725'
    assert r.PDF_SOURCE['sha256'] == c.PDF_SHA and r.MARKER == 'representation-repair.json'

def test_original_downloaded_pdf_hash_and_actual_company_identity_layout(completed_snapshot):
    pdf = (FIXTURE/'source.pdf').read_bytes()
    assert len(pdf) == c.PDF_BYTES == 1262185 and c.once.sha(pdf) == c.PDF_SHA
    assert c.once.blob(pdf) == r.PDF_SOURCE['git_blob']
    _, _, parsed = completed_snapshot
    assert len(parsed['pages']) == parsed['page_count'] == 133
    assert '000920' not in parsed['pages'][0]['text'] and '沃顿科技股份有限公司' in parsed['pages'][0]['text']
    assert '000920' in parsed['pages'][5]['text'] and '股票代码' in parsed['pages'][5]['text']

def test_completed_repair_lineage_still_recovers_exact_original(completed_snapshot):
    value, source, _ = deepcopy(completed_snapshot); pdf, text, manifest = c.recover(value, source)
    assert pdf == (FIXTURE/'source.pdf').read_bytes() and len(text['pages']) == 133
    assert manifest['representation_repair']['source_requests'] == 0
    assert manifest['representation_repair']['original_failure'] == r.FAILURE_SOURCE and value.writes == []

@pytest.mark.parametrize('case', ['no-code','late-code','no-year','no-report-title'])
def test_printed_identity_remains_bounded_and_rejects_missing_fields(monkeypatch, case):
    pdf = (FIXTURE/'source.pdf').read_bytes()
    pages = [SimpleNamespace(page_number=i+1, text='readable page content') for i in range(133)]
    pages[0].text = '2026 半年度报告'; pages[5].text = '公司简介 股票代码 000920'
    if case == 'no-code': pages[5].text = '公司简介 股票代码 999999'
    if case == 'late-code': pages[6].text, pages[5].text = pages[5].text, 'other code'
    if case == 'no-year': pages[0].text = '半年度报告'
    if case == 'no-report-title': pages[0].text = '2026 annual report'
    monkeypatch.setattr(c, 'extract_pdf_text', lambda *a, **k: SimpleNamespace(page_count=133, pages=pages))
    with pytest.raises(ValueError, match='REPORT_PRINTED_IDENTITY'): c.parse_original(pdf)

@pytest.mark.parametrize('kind', ['original-failure','clock','source-count','pdf-ref','marker-path','marker-prepare','marker-authority','marker-operation'])
def test_rehashed_repair_claims_cannot_change_original_source_or_authority(completed_snapshot, kind):
    value, source, _ = deepcopy(completed_snapshot); manifest = json.loads(value.file(source['path'], source['ref'])); repair = manifest['representation_repair']
    if kind == 'original-failure': repair['original_failure']['sha256'] = '0' * 64
    elif kind == 'clock': manifest['requested_at'] = '2026-09-21T01:28:00Z'
    elif kind == 'source-count': repair['source_requests'] = 1
    elif kind == 'pdf-ref': manifest['files']['source.pdf']['ref'] = 'b' * 40
    elif kind == 'marker-path': repair['reservation']['path'] = c.PREFIX + 'prepare.json'
    else:
        spec = repair['reservation']; marker = json.loads(value.file(spec['path'], spec['ref']))
        if kind == 'marker-prepare': marker['original_prepare']['sha256'] = '0' * 64
        if kind == 'marker-authority': marker['research_authority'] = 'EXECUTE'
        if kind == 'marker-operation': marker['operation'] = 'REACQUIRE_SOURCE'
        raw = c.once.raw(marker); value.versions[spec['ref']][spec['path']] = raw
        repair['reservation'] = c.once.source_ref(spec['path'], spec['ref'], raw, 'repair')
    manifest['custody_hash'] = c.canonical_hash({k:v for k,v in manifest.items() if k != 'custody_hash'})
    raw = c.once.raw(manifest); value.versions[source['ref']][source['path']] = raw
    source = c.once.source_ref(source['path'], source['ref'], raw, 'source.json')
    with pytest.raises((ValueError,RuntimeError,KeyError)): c.recover(value, source)
