from datetime import timedelta

import pytest

from decision_kernel.runtime import radar_feed_intake as intake
from decision_kernel.runtime.economic_source_capture import PublicResponse
from test_radar_feed_intake import AT, capture, item, offline, xml


@pytest.mark.parametrize('headers,reason', [
    ({'content-type': 'text/html'}, 'UNSUPPORTED_FEED_MEDIA_TYPE'),
    ({'content-type': 'application/octet-stream'}, 'UNSUPPORTED_FEED_MEDIA_TYPE'),
    ({'content-type': 'text/xml', 'content-encoding': 'gzip'}, 'UNSUPPORTED_CONTENT_ENCODING'),
])
def test_actual_public_transport_returns_metadata_to_capture_before_media_refusal(tmp_path, monkeypatch, headers, reason):
    body = xml([item()])
    opened = []
    class Response:
        status = 200
        def __init__(self, url):
            self.url = url
            self.headers = {**headers, 'content-length': str(len(body)), 'Set-Cookie': 'never-retain-cookie'}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def geturl(self): return self.url
        def read(self, limit):
            assert limit == intake.MAX_BODY + 1
            return body
    class Opener:
        def open(self, request, timeout):
            assert timeout == 20
            opened.append(request.full_url)
            return Response(request.full_url)
    monkeypatch.setattr(intake, 'build_opener', lambda *args: Opener())
    root = tmp_path / 'rejected'
    report, _ = capture(root, [], transport=intake.fetch_feed)
    assert len(opened) == 1 and report['status'] == 'INCOMPLETE_FEED_INTAKE'
    entry = report['requests'][0]
    assert entry['status'] == 200 and entry['rejection_reason'] == reason
    assert entry['headers']['content-type'] == headers['content-type']
    assert entry['received_body'] == intake.digest(body)
    assert entry['body_file'] is None and report['files'] == {}
    assert not (root/'registry.json').exists() and not (root/'index.html').exists()
    assert 'never-retain-cookie' not in (root/'capture.json').read_text()
    assert intake.verify_capture(root)['status'] == 'RETAINED_BYTES_ONLY_INCOMPLETE_INTAKE'


def test_response_url_and_http_status_refusal_are_separate():
    raw = xml([])
    with pytest.raises(intake.FeedResponseRejected, match='HTTP_STATUS_NOT_200'):
        intake.check_response(PublicResponse(intake.FEEDS['nbs-releases'], 201, {'content-type':'text/xml'}, raw), 'nbs-releases')
    with pytest.raises(intake.FeedResponseRejected, match='RESPONSE_URL_MISMATCH'):
        intake.check_response(PublicResponse('https://example.test/rss', 200, {'content-type':'text/xml'}, raw), 'nbs-releases')


def test_success_still_requires_exact_raw_reconstruction(tmp_path):
    root = tmp_path/'complete'
    report, _ = capture(root, [item()])
    assert report['status'] == 'COMPLETE_FEED_INTAKE'
    assert all(r['received_body'] == report['files'][r['body_file']] for r in report['requests'])
    assert intake.verify_capture(root)['status'] == 'ORIGINAL_FEEDS_REGISTRY_AND_PAGE_REBUILT'
