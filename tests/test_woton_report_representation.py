"""Actual retained source corpus + offline-only, create-only representation repair."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import woton_report_custody as c
from decision_kernel.runtime import woton_report_representation as r
from test_woton_report_custody import API, Retainer, CODE, no_network
from test_woton_report_label_transport import label_env

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


def test_original_downloaded_pdf_hash_and_actual_company_identity_layout():
    pdf = (FIXTURE/'source.pdf').read_bytes()
    assert len(pdf) == c.PDF_BYTES == 1262185
    assert c.once.sha(pdf) == c.PDF_SHA
    assert c.once.blob(pdf) == r.PDF_SOURCE['git_blob']
    parsed = c.parse_original(pdf)
    assert len(parsed['pages']) == parsed['page_count'] == 133
    assert '000920' not in parsed['pages'][0]['text']  # Actual rejected cover, not synthetic assumption.
    assert '沃顿科技股份有限公司' in parsed['pages'][0]['text']
    assert '000920' in parsed['pages'][5]['text'] and '股票代码' in parsed['pages'][5]['text']
    assert all(p['text'].strip() for p in parsed['pages'])


def test_actual_original_retainer_repair_keeps_source_and_failure_and_has_no_get(tmp_path, monkeypatch):
    value = api(); original = deepcopy(value.versions[value.head])
    monkeypatch.setattr(c.once, 'now', lambda: AT)
    def forbidden(*args, **kwargs): raise AssertionError('No source GET or reacquisition')
    monkeypatch.setattr(c, 'acquire', forbidden)
    monkeypatch.setattr(c.requests.Session, 'get', forbidden)
    result = r.run(api=value, code=CODE, output=tmp_path/'repair', clock=lambda: AT, retainer_factory=Retainer)
    assert result['status'] == c.COMPLETE, result
    assert result['source_requests'] == result['model_calls'] == result['market_requests'] == 0
    assert not result['formal_research_started'] and not result['mutation_uncertain']
    assert value.writes == [c.PREFIX + n for n in (r.MARKER, 'extraction.json', 'source.json')]
    assert all(value.versions[value.head][p] == data for p,data in original.items())
    pdf, text, manifest = c.recover(value, result['source'])
    assert pdf == (FIXTURE/'source.pdf').read_bytes() and len(text['pages']) == 133
    assert manifest['source_requests'] == 1  # The ORIGINAL attempt; current repair is zero.
    assert manifest['representation_repair']['source_requests'] == 0
    assert manifest['representation_repair']['original_failure'] == r.FAILURE_SOURCE
    writes = value.writes.copy()
    second = r.run(api=value, code=CODE, output=tmp_path/'again', clock=lambda: AT, retainer_factory=Retainer)
    assert second['status'] == c.REUSED and value.writes == writes
    # The initial acquisition path must also stay consumed, not restart the GET.
    third = c.run(api=value, code=CODE, output=tmp_path/'initial-again', clock=lambda: AT,
        download=forbidden, retainer_factory=Retainer)
    assert third['status'] == c.REUSED and value.writes == writes


@pytest.mark.parametrize('kind', ['missing-failure','changed-failure','changed-prepare','changed-pdf',
    'extra-file','permission','expiry','marker-lost','extraction-lost'])
def test_repair_failures_never_rewrite_originals_or_invoke_acquisition(tmp_path, monkeypatch, kind):
    value = api(); monkeypatch.setattr(c.once, 'now', lambda: AT)
    if kind == 'missing-failure': del value.versions[value.head][c.PREFIX+'failure.json']
    if kind == 'changed-failure': value.versions[value.head][c.PREFIX+'failure.json'] += b' '
    if kind == 'changed-prepare': value.versions[value.head][c.PREFIX+'prepare.json'] += b' '
    if kind == 'changed-pdf': value.versions[value.head][c.PREFIX+'source.pdf'] += b' '
    if kind == 'extra-file': value.versions[value.head][c.PREFIX+'arbitrary.json'] = b'{}'
    if kind == 'permission': value.comment['body'] += ' changed'
    if kind.endswith('-lost'):
        value.fail_name = r.MARKER if kind == 'marker-lost' else 'extraction.json'
        value.fail_after_write = True
    before = deepcopy(value.versions[value.head])
    now = '2026-09-23T00:00:00Z' if kind == 'expiry' else AT
    def forbidden(*args, **kwargs): raise AssertionError('No source GET')
    monkeypatch.setattr(c, 'acquire', forbidden)
    result = r.run(api=value, code=CODE, output=tmp_path/'repair', clock=lambda: now, retainer_factory=Retainer)
    assert result['status'] == 'SOURCE_REPRESENTATION_REPAIR_FAILED'
    assert result['source_requests'] == 0
    assert all(value.versions[value.head][path] == data for path,data in before.items())
    assert not any(path.endswith('/failure.json') or path.endswith('/source.pdf') for path in value.writes)
    if kind.endswith('-lost'):
        assert result['mutation_uncertain']
        assert c.PREFIX+'representation-failure.json' not in value.writes
    else: assert not value.writes


@pytest.mark.parametrize('case', ['no-code','late-code','no-year','no-report-title'])
def test_printed_identity_remains_bounded_and_rejects_missing_fields(monkeypatch, case):
    pdf = (FIXTURE/'source.pdf').read_bytes()
    pages = [SimpleNamespace(page_number=i+1, text='readable page content') for i in range(133)]
    pages[0].text = '2026 半年度报告'
    pages[5].text = '公司简介 股票代码 000920'
    if case == 'no-code': pages[5].text = '公司简介 股票代码 999999'
    if case == 'late-code': pages[6].text, pages[5].text = pages[5].text, 'other code'
    if case == 'no-year': pages[0].text = '半年度报告'
    if case == 'no-report-title': pages[0].text = '2026 annual report'
    monkeypatch.setattr(c, 'extract_pdf_text', lambda *a, **k: SimpleNamespace(page_count=133, pages=pages))
    with pytest.raises(ValueError, match='REPORT_PRINTED_IDENTITY'): c.parse_original(pdf)


def test_cli_exact_representation_label_never_selects_acquisition(tmp_path, monkeypatch):
    for key,value in {**label_env(), 'REPORT_LABEL':c.REPRESENTATION_LABEL}.items(): monkeypatch.setenv(key,value)
    monkeypatch.setattr(c.subprocess, 'check_output', lambda *a, **k: CODE+'\n')
    monkeypatch.setattr(c, 'GitHubAPI', lambda *a, **k: 'fake-github-api')
    monkeypatch.setenv('GH_TOKEN','synthetic-test-only')
    def forbidden(*args, **kwargs): raise AssertionError('Initial capture path not permitted')
    monkeypatch.setattr(c, 'run', forbidden)
    calls=[]
    def repair(**kw): calls.append(kw); return {'status':c.REUSED}
    monkeypatch.setattr(r,'run',repair)
    assert c.main(['--code-commit',CODE,'--output',str(tmp_path/'out')]) == 0
    assert calls == [{'api':'fake-github-api','code':CODE,'output':tmp_path/'out'}]


def test_workflow_keeps_exact_repair_label_in_only_original_isolated_source_job():
    text=Path('.github/workflows/stock-business-research.yml').read_text()
    source=text.split('  retain-public-report-source:\n',1)[1].split('  prepare-stock-sources:',1)[0]
    assert text.count("github.event.label.name == 'woton-h1-representation-ready'") == 1
    assert "github.event.label.name == 'woton-h1-representation-ready'" in source
    assert 'secrets.' not in source and 'research-api' not in source
    assert c.SCOPE['permission']['comment_id'] == 5753902322


@pytest.fixture(scope='module')
def completed_snapshot(tmp_path_factory):
    # Cache only immutable upstream setup. Each assertion below re-runs the
    # actual recover validator on a fresh mutable API copy; no result is cached.
    value=api()
    result=r.run(api=value, code=CODE, output=tmp_path_factory.mktemp('repair')/'out',
        clock=lambda:AT, retainer_factory=Retainer)
    assert result['status']==c.COMPLETE
    return value,result['source']


@pytest.mark.parametrize('kind', ['original-failure','clock','source-count','pdf-ref',
    'marker-path','marker-prepare','marker-authority','marker-operation'])
def test_rehashed_repair_claims_cannot_change_original_source_or_authority(completed_snapshot,kind):
    value,source=deepcopy(completed_snapshot)
    manifest=json.loads(value.file(source['path'],source['ref']))
    repair=manifest['representation_repair']
    if kind=='original-failure': repair['original_failure']['sha256']='0'*64
    elif kind=='clock': manifest['requested_at']='2026-09-21T01:28:00Z'
    elif kind=='source-count': repair['source_requests']=1
    elif kind=='pdf-ref': manifest['files']['source.pdf']['ref']='b'*40
    elif kind=='marker-path': repair['reservation']['path']=c.PREFIX+'prepare.json'
    else:
        spec=repair['reservation'];marker=json.loads(value.file(spec['path'],spec['ref']))
        if kind=='marker-prepare': marker['original_prepare']['sha256']='0'*64
        if kind=='marker-authority': marker['research_authority']='EXECUTE'
        if kind=='marker-operation': marker['operation']='REACQUIRE_SOURCE'
        raw=c.once.raw(marker);value.versions[spec['ref']][spec['path']]=raw
        repair['reservation']=c.once.source_ref(spec['path'],spec['ref'],raw,'repair')
    manifest['custody_hash']=c.canonical_hash({k:v for k,v in manifest.items() if k!='custody_hash'})
    raw=c.once.raw(manifest);value.versions[source['ref']][source['path']]=raw
    source=c.once.source_ref(source['path'],source['ref'],raw,'source.json')
    with pytest.raises((ValueError,RuntimeError,KeyError)):c.recover(value,source)
