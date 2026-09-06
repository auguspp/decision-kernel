from pathlib import Path

import pytest

from decision_kernel.runtime import radar_feed_intake as intake
from test_radar_feed_intake import capture, offline


@pytest.mark.parametrize('length', [str(intake.MAX_BODY+1), 'unknown'])
def test_declared_size_refusal_is_visible_without_reading_body(tmp_path, monkeypatch, length):
    class Response:
        status = 200
        headers = {'content-length':length, 'content-type':'text/xml', 'Set-Cookie':'DO_NOT_RETAIN'}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): pytest.fail('declared over-budget body must not be read')
    class Opener:
        def open(self, *args, **kwargs): return Response()
    monkeypatch.setattr(intake,'build_opener',lambda *args:Opener())
    root=tmp_path/'capture'
    report,_=capture(root,[],transport=intake.fetch_feed)
    entry=report['requests'][0]
    assert report['status']=='INCOMPLETE_FEED_INTAKE'
    assert entry['status']==200 and entry['headers']['content-length']==length
    assert entry['rejection_reason']=='DECLARED_BODY_BYTE_BUDGET_EXCEEDED'
    assert entry['body_file'] is None and report['files']=={}
    assert 'DO_NOT_RETAIN' not in (root/'capture.json').read_text()
    assert any(frame['function']=='fetch_feed' for frame in entry['failure_origin'])
    assert intake.verify_capture(root)['status']=='RETAINED_BYTES_ONLY_INCOMPLETE_INTAKE'


def test_unexpected_pre_response_exception_records_only_code_location(tmp_path,monkeypatch):
    secret='MUST_NOT_ARCHIVE_EXCEPTION_MESSAGE_OR_LOCALS'
    class Opener:
        def open(self,*args,**kwargs):
            sensitive_local=secret
            raise ValueError(sensitive_local)
    monkeypatch.setattr(intake,'build_opener',lambda *args:Opener())
    root=tmp_path/'capture'
    report,_=capture(root,[],transport=intake.fetch_feed)
    entry=report['requests'][0]
    assert entry['status'] is None and entry['error_type']=='ValueError'
    assert entry['failure_origin'][-1]['function']=='open'
    assert 1<=len(entry['failure_origin'])<=4
    assert all(Path(f['file']).name==f['file'] and type(f['line']) is int for f in entry['failure_origin'])
    assert secret not in (root/'capture.json').read_text()
    assert not (root/'registry.json').exists()
