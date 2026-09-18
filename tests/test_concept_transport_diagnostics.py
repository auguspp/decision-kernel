"""Synthetic HTTP responses at the real request_raw seam, not live market data."""
from copy import deepcopy
from datetime import timedelta
import json

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import concept_radar_capture as capture
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError
from tests.test_concept_radar import AT, DAY, SHA, WF, Fixture, no_network, raw

SECRET = 'SYNTHETIC-DO-NOT-RETAIN-KEY'


class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body
        self.status_code = status
        self.headers = headers if headers is not None else {'Content-Length': str(len(body))}
        self.body_reads = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def iter_content(self, chunk_size):
        self.body_reads += 1
        yield self.body


def attempt(tmp_path, monkeypatch, *, status=200, headers=None, failed=True):
    f, responses, calls, pauses = Fixture(), [], [], []

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, *, params, headers, timeout, stream, allow_redirects):
            assert headers['X-api-key'] == SECRET
            assert headers['Accept-Encoding'] == 'identity'
            assert timeout == (10, 20) and stream and not allow_redirects
            assert url.startswith(capture.HITHINK_BASE_URL + '/')
            path = url.removeprefix(capture.HITHINK_BASE_URL)
            calls.append((path, params))
            if failed and len(calls) == 3:
                r = Response(SECRET.encode(), status, failure_headers)
            else:
                r = Response(raw(f.body(path, params)))
            responses.append(r)
            return r

    failure_headers = headers
    monkeypatch.setattr(capture, '_session', Session)
    stamp = AT

    def now():
        nonlocal stamp
        stamp += timedelta(seconds=1)
        return stamp

    out = tmp_path/'capture'
    receipt = capture.capture(out, market_session=DAY, workflow=WF, expected_code=SHA,
        transport=lambda path, params: capture.request_raw(path, params, credential=SECRET),
        now=now, pause=pauses.append, credential=SECRET)
    return out, receipt, calls, responses, pauses


@pytest.mark.parametrize('status,headers,reason', [
    (429, {}, 'HTTP_REJECTED'),
    (403, {}, 'HTTP_REJECTED'),
    (503, {}, 'HTTP_REJECTED'),
    (302, {'Location': 'https://untrusted.invalid/' + SECRET}, 'HTTP_REJECTED'),
    (200, {'Content-Encoding': 'gzip'}, 'UNEXPECTED_CONTENT_ENCODING'),
    (200, {'Content-Length': 'invalid-' + SECRET}, 'INVALID_CONTENT_LENGTH'),
    (200, {'Content-Length': '0'}, 'INVALID_CONTENT_LENGTH'),
])
def test_real_guard_failure_survives_capture_without_secret_or_retry(tmp_path, monkeypatch, status, headers, reason):
    out, r, calls, responses, pauses = attempt(tmp_path, monkeypatch, status=status, headers=headers)
    assert r['status'] == capture.FAILED and r['failed_stage'] == 'TRANSPORT'
    assert r['failure_type'] == 'DumpTrialError' and r['reason_code'] == reason
    last = r['requests'][-1]
    assert last['params'] == {'tag': 'industry'} and last['http_status'] == status
    assert last['received_at'] >= last['requested_at'] and last['response_file'] is None
    assert len(calls) == 3 and pauses == [20, 20]
    assert [p.name for p in sorted(out.glob('response-*.json'))] == ['response-1.json', 'response-2.json']
    assert not (out/'observation.json').exists()
    assert responses[-1].body_reads == 0 and all(r.closed for r in responses)
    assert all(SECRET.encode() not in p.read_bytes() for p in out.iterdir())
    assert capture.verify(out)['status'] == 'RETAINED_FAILED_CONCEPT_CAPTURE_REMOTE_CAUSE_NOT_REPROVEN'
    assert capture.verify(out)['network_calls'] == 0


@pytest.mark.parametrize('status', [True, '429', 0, 600])
def test_invalid_status_not_coerced_into_http_fact(tmp_path, monkeypatch, status):
    out, r, calls, _, _ = attempt(tmp_path, monkeypatch, status=status)
    assert r['reason_code'] == 'HTTP_REJECTED' and len(calls) == 3
    assert r['requests'][-1]['http_status'] is None
    assert r['requests'][-1]['received_at'] is None
    assert capture.verify(out)['network_calls'] == 0


@pytest.mark.parametrize('code,status', [(SECRET, 429), (['HTTP_REJECTED'], 503),
    ('HTTP_REJECTED', 200), ('UNEXPECTED_CONTENT_ENCODING', 503)])
def test_unknown_or_inconsistent_exception_is_not_quoted_or_certified(tmp_path, code, status):
    out = tmp_path/'unknown'
    def transport(*args):
        raise DumpTrialError(code, http_status=status)
    r = capture.capture(out, market_session=DAY, workflow=WF, expected_code=SHA,
        transport=transport, now=lambda: AT, pause=lambda _: None, credential=SECRET)
    assert r['reason_code'] == 'SOURCE_PREPARATION_REJECTED'
    assert r['requests'][-1]['http_status'] is None
    assert all(SECRET.encode() not in p.read_bytes() for p in out.iterdir())
    assert capture.verify(out)['network_calls'] == 0


@pytest.mark.parametrize('field,value', [('http_status', 200), ('http_status', '429'),
    ('http_status', True), ('http_status', 600), ('received_at', None)])
def test_inconsistent_failed_http_metadata_rejected_even_after_rehash(tmp_path, monkeypatch, field, value):
    out, receipt, _, _, _ = attempt(tmp_path, monkeypatch, status=429)
    changed = deepcopy(receipt)
    changed['requests'][-1][field] = value
    changed['capture_hash'] = canonical_hash({k: v for k, v in changed.items() if k != 'capture_hash'})
    (out/'capture.json').write_bytes(raw(changed))
    with pytest.raises(ValueError, match='FAILED_HTTP_DIAGNOSTIC_REJECTED'):
        capture.verify(out)


def test_header_rejection_cannot_claim_non_200_or_body(tmp_path, monkeypatch):
    out, r, _, _, _ = attempt(tmp_path, monkeypatch, headers={'Content-Encoding': 'gzip'})
    r['requests'][-1]['http_status'] = 429
    r['capture_hash'] = canonical_hash({k: v for k, v in r.items() if k != 'capture_hash'})
    (out/'capture.json').write_bytes(raw(r))
    with pytest.raises(ValueError, match='FAILED_HTTP_DIAGNOSTIC_REJECTED'):
        capture.verify(out)


def test_successful_http_path_and_raw_bytes_remain_unchanged(tmp_path, monkeypatch):
    out, r, calls, responses, pauses = attempt(tmp_path, monkeypatch, failed=False)
    assert r['status'] == capture.COMPLETE and len(calls) == 11
    assert r['reason_code'] is None and pauses == [20]*10
    for i, response in enumerate(responses, 1):
        assert (out/f'response-{i}.json').read_bytes() == response.body
        assert response.body_reads == 1 and response.closed
    verified = capture.verify(out)
    assert verified['network_calls'] == 0 and verified['catalog_count'] == 4
    assert verified['company_count'] == 4
