"""Historical Woton reader + reusable offline Git/PDF test helpers; no live sources."""
import base64
from copy import deepcopy
import io
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from decision_kernel.runtime import woton_report_custody as c
from decision_kernel.runtime.current_state_delivery import GitHubReadError
from decision_kernel.runtime.stock_research_intake import WORK_REF
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
    def __init__(self, *, request_path=None, scope=None, permission=None, prefix=None):
        self.head = 'b' * 40
        self.versions = {self.head: {'old-research/failure.json': b'ORIGINAL_FAILURE'}}
        self.blobs = {}
        self.reads = []; self.writes = []; self.auths = 0
        self.request_path = request_path
        self.scope = deepcopy(c.SCOPE if scope is None else scope)
        self.permission = c.PERMISSION if permission is None else permission
        self.prefix = c.PREFIX if prefix is None else prefix
        self.comment = {'id': self.permission['comment_id'], 'created_at': self.permission['created_at'],
            'issue_url': 'https://api.github.com/repos/' + c.once.REPO + '/issues/297', 'body': ''}
        self.fail_name = None; self.fail_after_write = False

    def file(self, path, ref):
        self.reads.append(('file', path, ref))
        if self.request_path is not None and ref == CODE and path == self.request_path:
            return c.once.raw(self.scope)
        return self.versions[ref][path]

    def _call(self, method, endpoint):
        assert method == 'GET'
        self.reads.append(endpoint)
        if endpoint == 'git/ref/heads/main':
            return SimpleNamespace(json=lambda: {'object': {'type': 'commit', 'sha': CODE}})
        if endpoint == 'git/ref/heads/' + WORK_REF:
            return SimpleNamespace(json=lambda: {'object': {'type': 'commit', 'sha': self.head}})
        if endpoint == 'issues/comments/' + str(self.permission['comment_id']):
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
            raise GitHubReadError('GitHub HTTP 404')
        if endpoint.startswith('git/blobs/'):
            sha = endpoint.split('/')[-1]; raw = self.blobs[sha]
            return {'sha': sha, 'size': len(raw), 'encoding': 'base64',
                    'content': base64.encodebytes(raw).decode()}
        raise AssertionError(endpoint)

    def native(self, method, endpoint, body):
        assert method == 'PUT' and endpoint.startswith('contents/' + self.prefix)
        assert body['branch'] == WORK_REF and 'sha' not in body
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



def _reader_snapshot(monkeypatch, pdf):
    use_synthetic(monkeypatch, pdf)
    api = API()
    extraction = c.once.raw(c.parse_original(pdf))
    pdf_ref, text_ref, manifest_ref = 'c' * 40, 'd' * 40, 'e' * 40
    pdf_path, text_path = c.PREFIX + 'source.pdf', c.PREFIX + 'extraction.json'
    def stored(path, ref, raw):
        api.versions[ref] = {path: raw}; api.blobs[c.once.blob(raw)] = raw
        return {**c.once.source_ref(path, ref, raw, 'PUBLIC_REPORT_SOURCE_ONLY'), 'bytes': len(raw)}
    pdf_source, text_source = stored(pdf_path, pdf_ref, pdf), stored(text_path, text_ref, extraction)
    manifest = {'scope': c.SCOPE, 'status': c.COMPLETE, 'code_commit': CODE,
        'source_requests': 1, 'http_status': 200, 'requested_at': '2026-09-21T00:40:01Z',
        'received_at': '2026-09-21T00:40:02Z', 'finished_at': '2026-09-21T00:40:03Z',
        'files': {'source.pdf': pdf_source, 'extraction.json': text_source},
        'provenance': 'ISSUER_REPORT_VIA_SINA_MIRROR_NOT_CNINFO_BYTE_EQUIVALENCE', **c.model.AUTHORITY}
    manifest['custody_hash'] = c.canonical_hash(manifest)
    raw = c.once.raw(manifest); source_path = c.PREFIX + 'source.json'
    api.versions[manifest_ref] = {source_path: raw}; api.blobs[c.once.blob(raw)] = raw
    return api, c.once.source_ref(source_path, manifest_ref, raw, 'WOTON_PUBLIC_REPORT_CUSTODY'), pdf


def test_writer_surface_is_retired_but_reader_identity_remains():
    assert c.SCOPE['execute_before'] == '2026-09-23T00:00:00Z'
    assert c.PDF_BYTES == 1262185 and c.SCOPE['page_count'] == 133
    assert c.SCOPE['related_question_id'] == c.QUESTION_ID
    assert not any(hasattr(c, name) for name in ('run', 'main', 'acquire', 'check_environment'))


def test_reader_roundtrip_uses_exact_retained_bytes(monkeypatch, pdf):
    api, source, expected = _reader_snapshot(monkeypatch, pdf)
    got, parsed, manifest = c.recover(api, source)
    assert got == expected and parsed['page_count'] == 133 and '半年度报告' in parsed['pages'][0]['text']
    assert manifest['status'] == c.COMPLETE and api.writes == []


@pytest.mark.parametrize('kind', ['hash', 'pages', 'issuer', 'blank'])
def test_actual_parser_rejects_wrong_original_or_incomplete_representation(monkeypatch, pdf, kind):
    raw = pdf if kind == 'hash' else synthetic_pdf(pages=132 if kind == 'pages' else 133,
        title='999999 2026 ABCDE' if kind == 'issuer' else '000920 2026 ABCDE', blank=kind == 'blank')
    use_synthetic(monkeypatch, raw)
    if kind == 'hash': raw += b'x'
    with pytest.raises(ValueError): c.parse_original(raw)


@pytest.mark.parametrize('kind', ['body', 'size', 'blob', 'path', 'envelope', 'manifest-authority'])
def test_reader_rejects_rehashed_or_mismatched_custody(monkeypatch, pdf, kind):
    api, source, _ = _reader_snapshot(monkeypatch, pdf)
    import json
    manifest = json.loads(api.file(source['path'], source['ref']))
    if kind == 'manifest-authority':
        manifest['investment_authority'] = 'BUY'
        manifest['custody_hash'] = c.canonical_hash({k:v for k,v in manifest.items() if k != 'custody_hash'})
        raw = c.once.raw(manifest); api.versions[source['ref']][source['path']] = raw
        source = c.once.source_ref(source['path'], source['ref'], raw, 'WOTON_PUBLIC_REPORT_CUSTODY')
    else:
        original = api.get; pdf_spec = manifest['files']['source.pdf']
        def changed(endpoint):
            result = original(endpoint)
            if endpoint.startswith('git/blobs/') and endpoint.endswith(pdf_spec['git_blob']):
                if kind == 'body': result['content'] = base64.b64encode(pdf[:-1] + b'X').decode()
                elif kind == 'size': result['size'] += 1
                elif kind == 'blob': result['sha'] = '0' * 40
                elif kind == 'envelope': result['content'] = '%%%badbase64%%'
            elif kind == 'path' and endpoint.startswith('contents/') and 'source.pdf?' in endpoint:
                result['path'] = 'elsewhere.pdf'
            return result
        api.get = changed
    with pytest.raises((ValueError, RuntimeError)):
        c.recover(api, source)
