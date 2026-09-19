"""Synthetic transport -> original source/host failure retention, never live Research."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import socket

import pytest
import requests

from decision_kernel.runtime import cninfo_http as cninfo
from decision_kernel.runtime import hithink_dump_trial as transport
from decision_kernel.runtime import stock_research_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_research_sources as sources
from test_cninfo_pdf_transport_reuse import Response, Session, URL, install
from test_stock_research_sources import setup_capture
from test_stock_research_host import setup_host


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError('test attempted external network')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


def diagnostic(response, monkeypatch):
    calls = install(monkeypatch, response)
    with pytest.raises(cninfo.CninfoRuntimeError) as caught:
        cninfo.fetch_cninfo_pdf_bytes(source_locator=URL, max_bytes=1024, timeout_seconds=45)
    assert len(calls) == 1
    assert calls[0][1] == {'headers': {'Accept': 'application/pdf', 'Accept-Encoding': 'identity'},
                          'timeout': (10, 45), 'stream': True, 'allow_redirects': False}
    return cninfo.pdf_failure_diagnostic(caught.value)


@pytest.mark.parametrize('status', [301, 403, 404, 429, 500, 503])
def test_original_response_guard_retains_http_status_without_body_or_retry(monkeypatch, status):
    class UnreadableBody(Response):
        def iter_content(self, **_kwargs):
            raise AssertionError('rejected response body must not be read')
    response = UnreadableBody(b'SECRET_RESPONSE', status=status,
                              headers={'Set-Cookie': 'SECRET_COOKIE', 'Location': 'SECRET_REDIRECT'})
    assert diagnostic(response, monkeypatch) == {'reason_code': 'HTTP_REJECTED', 'http_status': status}


@pytest.mark.parametrize('status', [None, True, '403', 0, 99, 600, 403.0])
def test_original_response_guard_keeps_invalid_status_unknown(monkeypatch, status):
    assert diagnostic(Response(b'not read', status=status), monkeypatch) == {
        'reason_code': 'HTTP_REJECTED', 'http_status': None}


@pytest.mark.parametrize('headers,code', [
    ({'Content-Encoding': 'gzip'}, 'UNEXPECTED_CONTENT_ENCODING'),
    ({'Content-Encoding': 'br'}, 'UNEXPECTED_CONTENT_ENCODING'),
    ({'Content-Length': 'bad'}, 'INVALID_CONTENT_LENGTH'),
    ({'Content-Length': '0'}, 'INVALID_CONTENT_LENGTH'),
    ({'Content-Length': '-3'}, 'INVALID_CONTENT_LENGTH'),
    ({'Content-Length': '99'}, 'RESPONSE_LENGTH_MISMATCH'),
])
def test_original_response_guard_and_stream_distinguish_qualification_failures(monkeypatch, headers, code):
    assert diagnostic(Response(b'%PDF-1.7\nbody', headers=headers), monkeypatch) == {
        'reason_code': code, 'http_status': 200}


@pytest.mark.parametrize('kind,code', [
    (requests.Timeout, 'REQUEST_TIMEOUT'),
    (requests.exceptions.ConnectTimeout, 'REQUEST_TIMEOUT'),
    (requests.exceptions.ReadTimeout, 'REQUEST_TIMEOUT'),
    (requests.ConnectionError, 'CONNECTION_FAILED'),
    (requests.RequestException, 'REQUEST_FAILED'),
])
@pytest.mark.parametrize('after_headers', [False, True])
def test_request_failure_categories_do_not_echo_remote_details(monkeypatch, kind, code, after_headers):
    calls = []
    class BrokenBody(Response):
        def iter_content(self, **_kwargs):
            raise kind('SECRET_URL_USER_PASSWORD', request='SECRET_REQUEST', response='SECRET_RESPONSE')
    class BrokenSession(Session):
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            if not after_headers:
                raise kind('SECRET_URL_USER_PASSWORD', request='SECRET_REQUEST', response='SECRET_RESPONSE')
            return BrokenBody(b'%PDF-synthetic')
    monkeypatch.setattr(transport, '_session', lambda: BrokenSession(None, calls))
    with pytest.raises(cninfo.CninfoPdfTransportError) as caught:
        cninfo.fetch_cninfo_pdf_bytes(source_locator=URL, max_bytes=1024)
    assert len(calls) == 1
    result = cninfo.pdf_failure_diagnostic(caught.value)
    assert result == {'reason_code': code, 'http_status': 200 if after_headers else None}
    assert 'SECRET' not in json.dumps(result)


@pytest.mark.parametrize('kind,code', [
    (cninfo.CninfoPdfSourceError, 'PDF_SOURCE_REJECTED'),
    (cninfo.CninfoPdfHttpError, 'HTTP_REJECTED'),
    (cninfo.CninfoPdfTransportError, 'PDF_TRANSPORT_FAILED'),
    (cninfo.CninfoPdfByteLimitError, 'PDF_BYTE_LIMIT_EXCEEDED'),
    (cninfo.CninfoPdfContainerError, 'PDF_CONTAINER_REJECTED'),
])
def test_legacy_exceptions_remain_compatible_and_do_not_invent_status(kind, code):
    exc = kind('SECRET_LEGACY')
    exc.__cause__ = RuntimeError('SECRET_CAUSE')
    exc.response = 'SECRET_RESPONSE'
    assert cninfo.pdf_failure_diagnostic(exc) == {'reason_code': code, 'http_status': None}


@pytest.mark.parametrize('value', [True, '429', 0, 600, 200, 429.0])
def test_inconsistent_http_exception_metadata_cannot_enter_a_receipt(value):
    assert cninfo.pdf_failure_diagnostic(cninfo.CninfoPdfHttpError('SECRET', http_status=value)) == {
        'reason_code': 'HTTP_REJECTED', 'http_status': None}


@pytest.mark.parametrize('code', ['SECRET_ARBITRARY_CODE', ['SECRET'], None, 1])
def test_non_finite_transport_metadata_is_quarantined(code):
    assert cninfo.pdf_failure_diagnostic(cninfo.CninfoPdfTransportError(
        'SECRET', reason_code=code, http_status=429)) == {
        'reason_code': 'PDF_TRANSPORT_FAILED', 'http_status': None}


def test_unknown_exception_and_subclass_are_not_inspected():
    class Foreign(cninfo.CninfoPdfHttpError):
        @property
        def http_status(self):
            raise AssertionError('do not inspect foreign exception')
    error = Foreign.__new__(Foreign)
    RuntimeError.__init__(error, 'SECRET')
    assert cninfo.pdf_failure_diagnostic(error) is None
    unknown = RuntimeError('SECRET')
    unknown.__cause__ = cninfo.CninfoPdfHttpError('SECRET', http_status=429)
    assert cninfo.pdf_failure_diagnostic(unknown) is None


@pytest.mark.parametrize('preparation_only', [False, True])
def test_source_journal_preserves_failed_body_identity_clock_and_finite_reason(tmp_path, monkeypatch, preparation_only):
    args, query_calls, _ = setup_capture(tmp_path, monkeypatch)
    clock_count = [0]
    def clock():
        clock_count[0] += 1
        return (datetime(2026, 9, 13, 4, tzinfo=timezone.utc) + timedelta(seconds=clock_count[0])).isoformat()
    args.update(fetch_pdf=cninfo.fetch_cninfo_pdf_bytes, preparation_only=preparation_only, clock=clock)
    calls = install(monkeypatch, Response(b'SECRET_BODY', status=429))
    with pytest.raises(cninfo.CninfoPdfHttpError):
        sources.capture(**args)
    assert len(calls) == 1 and len(query_calls) == 2
    journal = json.loads((args['output'] / 'source-journal.json').read_bytes())
    assert journal['captured_pdf_bytes'] == 0 and journal['completed_reads'] == []
    assert len(journal['body_events']) == 1
    event = journal['body_events'][0]
    assert event['announcement_id'] == 'report' and event['status'] == 'INCOMPLETE'
    assert event['source_locator'].endswith('/report.PDF')
    assert datetime.fromisoformat(event['started_at']) < datetime.fromisoformat(event['finished_at'])
    assert event['pdf_diagnostic'] == {'reason_code': 'HTTP_REJECTED', 'http_status': 429}
    assert not list(args['output'].glob('*.pdf'))
    if preparation_only:
        preparation = json.loads((args['output'] / 'source-preparation.json').read_bytes())
        assert preparation['pdf_diagnostic'] == event['pdf_diagnostic']
        assert preparation['unattempted_ids'] == ['risk']
        assert not preparation['all_planned_bodies_inspected'] and not preparation['research_execution_allowed']
    assert all('SECRET' not in p.read_text() for p in args['output'].glob('*.json'))


def test_source_success_keeps_original_journal_contract(tmp_path, monkeypatch):
    args, _, _ = setup_capture(tmp_path, monkeypatch)
    sources.capture(**args)
    journal = json.loads((args['output'] / 'source-journal.json').read_bytes())
    assert len(journal['body_events']) == 2
    assert all(e['status'] == 'FORMAT_AND_IDENTITY_CHECKED_NOT_TRUTH' and 'pdf_diagnostic' not in e
               for e in journal['body_events'])


def test_unknown_capture_error_keeps_clock_without_adopting_arbitrary_reason(tmp_path, monkeypatch):
    args, _, _ = setup_capture(tmp_path, monkeypatch)
    def unknown(**_kwargs):
        exc = RuntimeError('SECRET')
        exc.reason_code = 'SECRET_REASON'
        exc.http_status = 429
        raise exc
    args['fetch_pdf'] = unknown
    with pytest.raises(RuntimeError):
        sources.capture(**args)
    event = json.loads((args['output'] / 'source-journal.json').read_bytes())['body_events'][0]
    assert 'finished_at' in event and 'pdf_diagnostic' not in event


def test_original_host_saves_source_failure_and_existing_root_prevents_second_capture(tmp_path, monkeypatch):
    args, api, model_calls, _, mutations = setup_host(tmp_path, monkeypatch)
    source_args, _, _ = setup_capture(tmp_path, monkeypatch)
    def capture(**kwargs):
        return sources.capture(**{**source_args, **kwargs, 'fetch_pdf': cninfo.fetch_cninfo_pdf_bytes})
    args['capture'] = capture
    calls = install(monkeypatch, Response(b'SECRET_BODY', status=403))
    result = host.run_item(**args)
    expected = {'reason_code': 'HTTP_REJECTED', 'http_status': 403}
    assert result['pdf_diagnostic'] == expected
    assert result['status'] == 'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE'
    assert not result['formal_research_started'] and model_calls == [] and len(calls) == 1
    retained = api.files[api.heads[intake.WORK_REF]]
    prefix = args['item']['prefix']
    failure = json.loads(retained[prefix + 'failure.json'])
    receipt = json.loads(retained[prefix + 'host-receipt.json'])
    assert failure['pdf_diagnostic'] == receipt['pdf_diagnostic'] == expected
    assert failure['research_execution'] == 'NOT_EXECUTED' and failure['funnel_status'] == 'NOT_REACHED'
    assert failure['automatic_retry'] is False and failure['investment_authority'] == 'NONE'
    assert not (args['output'] / 'funnel.json').exists()
    assert all('SECRET' not in raw.decode() for raw in retained.values())
    before = deepcopy(retained); mutation_count = len(mutations)
    args['output'] = tmp_path / 'repeat'
    repeat = host.run_item(**args)
    assert repeat['status'] == 'EXISTING_BASELINE_REUSED_NO_EXECUTION'
    assert before == api.files[api.heads[intake.WORK_REF]] and len(mutations) == mutation_count
    assert model_calls == [] and len(calls) == 1
