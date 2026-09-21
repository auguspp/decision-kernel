"""Synthetic source-only I/O, real PDF parsing and native-Git contracts; no live sources."""
import base64
from copy import deepcopy
import io
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
import requests
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from decision_kernel.runtime import woton_report_custody as c
from decision_kernel.runtime import stock_research_reading as reader
from test_pdf_text import _pdf_with_text_pages

CODE = 'a' * 40
AT = '2026-09-21T00:40:00Z'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError('Tests must not access a network')
    monkeypatch.setattr(socket.socket, 'connect', fail)
    monkeypatch.setattr(socket, 'create_connection', fail)


def synthetic_pdf(pages=133, title='000920 2026 ABCDE', blank=False):
    # Reuse the original tiny-PDF builder; a ToUnicode map supplies printed CJK
    # without installing a font, report generator or additional dependency.
    raw = _pdf_with_text_pages(title, *['' if blank else 'synthetic page' for _ in range(pages - 1)])
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(raw)))
    cmap = DecodedStreamObject()
    cmap.set_data(b'''/CIDInit /ProcSet findresource begin
12 dict begin begincmap /CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def
/CMapName /SyntheticUnicode def /CMapType 2 def
1 begincodespacerange <00> <FF> endcodespacerange
5 beginbfchar <41> <534A> <42> <5E74> <43> <5EA6> <44> <62A5> <45> <544A> endbfchar
endcmap CMapName currentdict /CMap defineresource pop end end''')
    writer.pages[0]['/Resources']['/Font']['/F1'][NameObject('/ToUnicode')] = writer._add_object(cmap)
    # >1MiB, to exercise Git Contents encoding=none and native raw-blob readback.
    padding = DecodedStreamObject(); padding.set_data(b'SYNTHETIC padding only ' * 60000)
    writer._add_object(padding)
    stream = io.BytesIO(); writer.write(stream)
    return stream.getvalue()


@pytest.fixture(scope='module')
def pdf():
    return synthetic_pdf()


def use_synthetic(monkeypatch, pdf):
    monkeypatch.setattr(c, 'PDF_BYTES', len(pdf))
    monkeypatch.setattr(c, 'PDF_SHA', c.once.sha(pdf))
    monkeypatch.setattr(c, 'PREFIX', 'research_runs/sources/public-reports/' + c.PDF_SHA + '/')
    monkeypatch.setattr(c, 'SCOPE', {**c.SCOPE, 'expected_bytes': len(pdf), 'expected_sha256': c.PDF_SHA})


class API:
    """Only GitHub HTTP/native-write boundaries are fake; parser/retainer are real."""
    def __init__(self):
        self.head = 'b' * 40
        self.versions = {self.head: {'old-research/failure.json': b'ORIGINAL_FAILURE'}}
        self.blobs = {}
        self.reads = []; self.writes = []; self.auths = 0
        self.comment = {'id': c.PERMISSION['comment_id'], 'created_at': c.PERMISSION['created_at'],
            'issue_url': 'https://api.github.com/repos/' + c.once.REPO + '/issues/297',
            'body': Path('tests/fixtures/woton_report_custody_permission.txt').read_text()}
        self.scope = deepcopy(c.SCOPE)
        self.fail_name = None; self.fail_after_write = False

    def file(self, path, ref):
        self.reads.append(('file', path, ref))
        if ref == CODE and path == c.REQUEST:
            return c.once.raw(self.scope)
        return self.versions[ref][path]

    def _call(self, method, endpoint):
        assert method == 'GET'
        self.reads.append(endpoint)
        if endpoint == 'git/ref/heads/main':
            return SimpleNamespace(json=lambda: {'object': {'type': 'commit', 'sha': CODE}})
        if endpoint == 'git/ref/heads/' + c.WORK_REF:
            return SimpleNamespace(json=lambda: {'object': {'type': 'commit', 'sha': self.head}})
        if endpoint == 'issues/comments/' + str(c.PERMISSION['comment_id']):
            self.auths += 1
            return SimpleNamespace(json=lambda: deepcopy(self.comment))
        raise AssertionError(endpoint)

    def get(self, endpoint):
        self.reads.append(endpoint)
        if endpoint.startswith('contents/'):
            path, ref = endpoint[9:].split('?ref=')
            files = self.versions[ref]
            if path in files:
                raw = files[path]
                return {'type': 'file', 'path': path, 'size': len(raw), 'sha': c.once.blob(raw),
                        'encoding': 'none' if len(raw) > 1024 * 1024 else 'base64', 'content': ''}
            found = [{'name': p.rsplit('/', 1)[-1]} for p in files if p.startswith(path + '/')]
            if found: return found
            raise c.GitHubReadError('GitHub HTTP 404')
        if endpoint.startswith('git/blobs/'):
            sha = endpoint.split('/')[-1]; raw = self.blobs[sha]
            return {'sha': sha, 'size': len(raw), 'encoding': 'base64',
                    'content': base64.encodebytes(raw).decode()}
        raise AssertionError(endpoint)

    def native(self, method, endpoint, body):
        assert method == 'PUT' and endpoint.startswith('contents/' + c.PREFIX)
        assert body['branch'] == c.WORK_REF and 'sha' not in body
        path = endpoint[9:]; old = self.versions[self.head]
        assert path not in old, 'No overwrite permitted'
        if self.fail_name == Path(path).name and not self.fail_after_write:
            raise RuntimeError('synthetic uncertain write')
        raw = base64.b64decode(body['content']); sha = c.once.blob(raw)
        self.head = c.once.blob((self.head + path + sha).encode())
        self.versions[self.head] = {**old, path: raw}; self.blobs[sha] = raw
        self.writes.append(path)
        if self.fail_name == Path(path).name:
            raise RuntimeError('synthetic lost write response')
        return {'content': {'sha': sha}, 'commit': {'sha': self.head}}


class Retainer(c.once.Retainer):
    def native(self, *args):
        assert not self.uncertain
        self.uncertain = True
        result = self.api.native(*args)
        self.uncertain = False
        return result


def execute(tmp_path, monkeypatch, pdf, *, api=None, download=None):
    use_synthetic(monkeypatch, pdf)
    monkeypatch.setattr(c.once, 'now', lambda: AT)
    api = API() if api is None else api
    if download is None:
        def download(out, receipt, clock):
            assert c.PREFIX + 'prepare.json' in api.versions[api.head]
            assert api.auths == 2
            receipt.update(phase='PUBLIC_PDF_GET', source_requests=1, http_status=200,
                           requested_at=clock(), received_at=clock())
            (out / 'source.pdf').write_bytes(pdf)
            return pdf
    result = c.run(api=api, code=CODE, output=tmp_path/'out', clock=lambda: AT,
                   download=download, retainer_factory=Retainer)
    return result, api


def env():
    return {'GITHUB_SHA': CODE, 'EXPECTED_CODE_SHA': CODE, 'GITHUB_REPOSITORY': c.once.REPO,
        'GITHUB_REF': 'refs/heads/main', 'GITHUB_WORKFLOW': 'stock-business-research',
        'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_RUN_ID': '42',
        'REPORT_INPUTS': json.dumps({**dict.fromkeys(c.OTHER_FLAGS, False),
            'retain-report-source': True, 'source-stock-run-id': '', 'code-sha': CODE})}


def test_permission_and_request_are_exact_main_scope():
    raw = Path('tests/fixtures/woton_report_custody_permission.txt').read_bytes()
    assert c.once.sha(raw) == c.PERMISSION['body_sha256']
    assert json.loads(Path(c.REQUEST).read_text()) == c.SCOPE
    assert c.PDF_BYTES == 1262185 and c.SCOPE['page_count'] == 133
    assert c.SCOPE['related_question_id'] == c.QUESTION_ID
    c.check_environment(env(), CODE)


@pytest.mark.parametrize('key', ['GITHUB_SHA', 'EXPECTED_CODE_SHA', 'GITHUB_REPOSITORY',
    'GITHUB_REF', 'GITHUB_WORKFLOW', 'GITHUB_EVENT_NAME', 'GITHUB_RUN_ATTEMPT', 'GITHUB_RUN_ID'])
def test_environment_mismatch_rejects_before_io(key):
    e = env(); e[key] = 'wrong'
    with pytest.raises(ValueError): c.check_environment(e, CODE)


@pytest.mark.parametrize('key', [*c.OTHER_FLAGS, 'source-stock-run-id', 'code-sha', 'retain-report-source', 'extra'])
def test_source_mode_cannot_mix_with_other_operations(key):
    e = env(); inputs = json.loads(e['REPORT_INPUTS']); inputs[key] = 'true' if key == 'retain-report-source' else True
    e['REPORT_INPUTS'] = json.dumps(inputs)
    with pytest.raises(ValueError): c.check_environment(e, CODE)


def test_real_parser_large_source_roundtrip_and_second_run_does_not_acquire(tmp_path, monkeypatch, pdf):
    result, api = execute(tmp_path, monkeypatch, pdf)
    assert result['status'] == c.COMPLETE, result
    assert result['model_calls'] == result['market_requests'] == 0
    assert not result['formal_research_started'] and not result['mutation_uncertain']
    assert [Path(p).name for p in api.writes] == ['prepare.json', 'source.pdf', 'extraction.json', 'source.json']
    assert api.versions[api.head]['old-research/failure.json'] == b'ORIGINAL_FAILURE'
    original_writes = api.writes.copy()
    got, parsed, manifest = c.recover(api, result['source'])
    assert got == pdf and parsed['page_count'] == 133 and '半年度报告' in parsed['pages'][0]['text']
    assert len(got) > 1024 * 1024 and api.writes == original_writes
    def forbidden(*args): raise AssertionError('existing source attempt must not acquire')
    second = c.run(api=api, code=CODE, output=tmp_path/'again', clock=lambda: AT,
                   download=forbidden, retainer_factory=Retainer)
    assert second['status'] == c.REUSED and second['source_requests'] == 0
    assert api.writes == original_writes


@pytest.mark.parametrize('kind', ['permission', 'scope', 'expired', 'prepare-lost', 'pdf-lost', 'bad-hash', 'parse'])
def test_failures_retain_history_without_retry(tmp_path, monkeypatch, pdf, kind):
    use_synthetic(monkeypatch, pdf); api = API(); downloads = []
    if kind == 'permission': api.comment['body'] += ' changed'
    if kind == 'scope': api.scope['subject'] = '601952.SH'
    if kind == 'expired': monkeypatch.setattr(c, 'SCOPE', {**c.SCOPE, 'execute_before': AT}); api.scope = deepcopy(c.SCOPE)
    if kind in {'prepare-lost', 'pdf-lost'}:
        api.fail_name = 'prepare.json' if kind == 'prepare-lost' else 'source.pdf'; api.fail_after_write = True
    if kind == 'parse':
        def broken(*args): raise c.once.TrialError('REPORT_UNREADABLE_PAGE')
        monkeypatch.setattr(c, 'parse_original', broken)
    def download(out, receipt, clock):
        downloads.append(1); receipt.update(source_requests=1, http_status=200, requested_at=AT, received_at=AT)
        raw = pdf + b'x' if kind == 'bad-hash' else pdf
        (out/'source.pdf').write_bytes(raw); return raw
    # Do not reset a deliberately changed expiry scope in the execute helper.
    monkeypatch.setattr(c.once, 'now', lambda: AT)
    result = c.run(api=api, code=CODE, output=tmp_path/'out', clock=lambda: AT,
                   download=download, retainer_factory=Retainer)
    assert result['status'] == 'SOURCE_CUSTODY_FAILED'
    assert len(downloads) == (0 if kind in {'permission', 'scope', 'expired', 'prepare-lost'} else 1)
    assert api.versions[api.head]['old-research/failure.json'] == b'ORIGINAL_FAILURE'
    if kind.endswith('lost'):
        assert result['mutation_uncertain'] and not any(p.endswith('failure.json') for p in api.writes)
    if kind == 'parse':
        assert api.versions[api.head][c.PREFIX+'source.pdf'] == pdf
        assert c.PREFIX+'failure.json' in api.versions[api.head]


@pytest.mark.parametrize('kind', ['hash', 'pages', 'issuer', 'blank'])
def test_actual_parser_rejects_wrong_original_or_incomplete_representation(monkeypatch, pdf, kind):
    raw = pdf if kind == 'hash' else synthetic_pdf(pages=132 if kind == 'pages' else 133,
        title='999999 2026 ABCDE' if kind == 'issuer' else '000920 2026 ABCDE', blank=kind == 'blank')
    use_synthetic(monkeypatch, raw)
    if kind == 'hash': raw += b'x'
    with pytest.raises(ValueError): c.parse_original(raw)


@pytest.mark.parametrize('kind', ['body', 'size', 'blob', 'path', 'envelope', 'text-rehashed', 'manifest-role', 'manifest-authority'])
def test_readback_rejects_tampering(tmp_path, monkeypatch, pdf, kind):
    result, api = execute(tmp_path, monkeypatch, pdf)
    source = result['source']; manifest = json.loads(api.file(source['path'], source['ref']))
    if kind in {'manifest-role', 'manifest-authority'}:
        if kind == 'manifest-role': manifest['files']['source.pdf'], manifest['files']['extraction.json'] = manifest['files']['extraction.json'], manifest['files']['source.pdf']
        else: manifest['investment_authority'] = 'BUY'
        manifest['custody_hash'] = c.canonical_hash({k:v for k,v in manifest.items() if k != 'custody_hash'})
        raw = c.once.raw(manifest); api.versions[source['ref']][source['path']] = raw
        source = c.once.source_ref(source['path'], source['ref'], raw, 'source.json')
    elif kind == 'text-rehashed':
        spec = manifest['files']['extraction.json']; value = json.loads(api.versions[spec['ref']][spec['path']])
        value['pages'][0]['text'] = 'FORGED'; raw = c.once.raw(value); spec.update(bytes=len(raw), sha256=c.once.sha(raw), git_blob=c.once.blob(raw))
        api.versions[spec['ref']][spec['path']] = raw; api.blobs[spec['git_blob']] = raw
        manifest['custody_hash'] = c.canonical_hash({k:v for k,v in manifest.items() if k != 'custody_hash'})
        raw = c.once.raw(manifest); api.versions[source['ref']][source['path']] = raw
        source = c.once.source_ref(source['path'], source['ref'], raw, 'source.json')
    else:
        original = api.get
        def changed(endpoint):
            result = original(endpoint)
            if endpoint.startswith('git/blobs/') and endpoint.endswith(manifest['files']['source.pdf']['git_blob']):
                if kind == 'body': result['content'] = base64.b64encode(pdf[:-1]+b'X').decode()
                elif kind == 'size': result['size'] += 1
                elif kind == 'blob': result['sha'] = '0'*40
                elif kind == 'envelope': result['content'] = '%%%badbase64%%'
            elif kind == 'path' and endpoint.startswith('contents/') and 'source.pdf?' in endpoint:
                result['path'] = 'elsewhere.pdf'
            return result
        api.get = changed
    with pytest.raises((ValueError, RuntimeError)): c.recover(api, source)


@pytest.mark.parametrize('kind', ['success', 'http403', 'redirect', 'partial', 'oversize'])
def test_actual_http_boundary_is_one_credential_free_get(tmp_path, monkeypatch, kind):
    calls = []; closed = []; response = SimpleNamespace(status_code=200)
    def chunks(size):
        assert size == 64*1024
        yield b'%PDF'
        if kind == 'partial': raise requests.Timeout('sensitive diagnostic must not be reported')
        yield b'12345'
    response.iter_content = chunks
    if kind == 'http403': response.status_code = 403
    if kind == 'redirect': response.status_code = 302
    class Response:
        def __enter__(self): return response
        def __exit__(self, *args): closed.append('response')
    class Session:
        trust_env = True
        def __enter__(self): return self
        def __exit__(self, *args): closed.append('session')
        def get(self, url, **kwargs):
            assert self.trust_env is False
            calls.append((url, kwargs)); return Response()
    monkeypatch.setattr(c.requests, 'Session', Session)
    if kind == 'oversize': monkeypatch.setattr(c.once, 'MAX_SOURCE_BYTES', 5)
    receipt = {}
    if kind == 'success': assert c.acquire(tmp_path, receipt, lambda: AT) == b'%PDF12345'
    else:
        with pytest.raises((ValueError, requests.Timeout)): c.acquire(tmp_path, receipt, lambda: AT)
    assert calls == [(c.SOURCE_URL, {'timeout': (15,60), 'stream': True, 'allow_redirects': False})]
    assert closed == ['response', 'session'] and receipt['source_requests'] == 1
    if kind in {'partial', 'oversize'}: assert (tmp_path/'source.pdf').read_bytes() == b'%PDF'


def test_workflow_source_job_is_isolated_and_original_modes_are_guarded():
    text = Path('.github/workflows/stock-business-research.yml').read_text()
    source = text.split('\n  retain-public-report-source:\n')[1]
    assert text.count('!inputs.retain-report-source &&') == 3
    assert 'research-api' not in source and 'secrets.' not in source
    assert "pip install -e '.[documents,feeds]'" in source and 'if: always()' in source
    assert 'persist-credentials: false' in source and 'ref: ${{ github.sha }}' in source
    for key in c.OTHER_FLAGS: assert '!inputs.' + key in source
    assert 'workflows:' not in source and 'schedule:' not in text


@pytest.mark.parametrize('active,expected', [
    ('research-stock-business','latest_execution_attempt'),
    ('prepare-stock-sources','latest_source_preparation_attempt'),
    ('deepseek-compatibility','latest_compatibility_attempt'),
    ('retain-public-report-source','latest_report_source_attempt'),
    ('BOTH',None)])
def test_source_attempt_is_not_research_or_generic_preparation(active, expected):
    run = {'id': 42, 'event':'workflow_dispatch', 'path':'.github/workflows/stock-business-research.yml',
        'head_branch':'main', 'run_attempt':1, 'head_sha':CODE,
        'head_repository':{'full_name':c.once.REPO}, 'created_at':AT, 'updated_at':AT,
        'status':'completed', 'conclusion':'success'}
    jobs = [{'run_id':42,'name':name,'conclusion':'success' if name==active or active=='BOTH' else 'skipped'}
        for name in ('research-stock-business','prepare-stock-sources','deepseek-compatibility','retain-public-report-source')]
    def get(endpoint):
        if 'workflows/' in endpoint: return {'workflow_runs':[run],'total_count':1}
        return {'jobs':jobs,'total_count':len(jobs)}
    result = reader.attempts(SimpleNamespace(api=SimpleNamespace(get=get,calls=0,max_calls=252),files={}))
    if expected:
        assert result[expected]['id'] == 42 and result['unclassified_invocations'] == []
        assert all(result[k] is None for k in ('latest_execution_attempt','latest_source_preparation_attempt',
            'latest_compatibility_attempt','latest_report_source_attempt') if k != expected)
    else: assert result['attempt_classification_status'] == 'PARTIAL_OR_UNAVAILABLE'
