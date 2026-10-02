"""Offline source doubles and synthetic PDFs only; never a real IMA capture."""
from copy import deepcopy
from hashlib import sha256
import io
import json
from pathlib import Path
from urllib.parse import quote

import pytest
from pypdf import PdfWriter
from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject

from decision_kernel.runtime import ima_private_probe as p
from decision_kernel.runtime import ima_document_check as d

ROW = {"media_id": "synthetic-private-id", "title": "SampleCo broker report.pdf", "highlight_content": "private snippet"}
ACCESS = {"url": "https://bucket.cos.ap-guangzhou.myqcloud.com/report.pdf?sign=synthetic", "headers": {"Authorization": "scoped-file-token"}}
NOW = "2026-10-02T12:00:00+00:00"


def raw(data, code=0):
    return json.dumps({"code": code, "data": data}, ensure_ascii=False).encode()


def run_check(data=None, *, rows=None, terms="SampleCo", code=0, status=200, downloader=None, inspector=None):
    data = {"media_type": 1, "url_info": deepcopy(ACCESS)} if data is None else data
    calls, gets = [], []
    def send(spec):
        calls.append(spec)
        return status, raw(data, code)
    def download(access):
        gets.append(access)
        return b"%PDF-synthetic-not-a-real-file" if downloader is None else downloader(access)
    result = d.check_one_document([ROW] if rows is None else rows, terms, send=send, clock=lambda: NOW,
                                  download=download, inspect=inspector or (lambda _: {"status": "PDF_MACHINE_READABLE"}))
    return result, calls, gets


def test_one_candidate_and_public_projection():
    result, calls, gets = run_check(rows=[ROW, {**ROW, "media_id": "second"}])
    assert result["candidate_matches"] == 2 and len(calls) == len(gets) == 1
    assert calls[0] == d.media_spec(ROW["media_id"])
    assert result["status"] == "PDF_MACHINE_READABLE" and result["pdf_downloads"] == 1
    assert result["file_response"]["sha256"] == sha256(b"%PDF-synthetic-not-a-real-file").hexdigest()
    for value in (ROW["title"], ROW["media_id"], ROW["highlight_content"], ACCESS["url"], "scoped-file-token"):
        assert value not in json.dumps(result)


@pytest.mark.parametrize("access", [None, {}, {"url": ""}])
def test_missing_url_is_unavailable_without_get(access):
    result, calls, gets = run_check({"media_type": 1, "url_info": access})
    assert result["status"] == "BODY_UNAVAILABLE_NO_URL" and len(calls) == 1 and not gets


@pytest.mark.parametrize("kind", [2, 6, 11, 99])
def test_non_pdf_never_downloads_or_follows_notes(kind):
    result, _, gets = run_check({"media_type": kind, "url_info": ACCESS})
    assert result["status"] == "NOT_PDF_NO_DOWNLOAD" and not gets


@pytest.mark.parametrize("kind", [None, True, "1"])
def test_invalid_media_type_remains_failure(kind):
    result, _, gets = run_check({"media_type": kind, "url_info": ACCESS})
    assert result["status"] == "CHECK_FAILED" and result["failure_code"] == "MEDIA_TYPE" and not gets


def test_no_matching_candidate_does_not_call_source():
    result, calls, gets = run_check(terms="OtherCompany")
    assert result["status"] == "NOT_SELECTED" and not calls and not gets


def test_same_id_conflict_fails_before_source():
    result, calls, _ = run_check(rows=[ROW, {**ROW, "title": "SampleCo changed"}])
    assert result["failure_code"] == "CANDIDATE_ID_CONFLICT" and not calls


@pytest.mark.parametrize("status,code", [(403,0), (429,0), (302,0), (200,220030)])
def test_rejection_is_not_empty_or_success(status, code):
    result, calls, gets = run_check(status=status, code=code)
    assert result["status"] == "CHECK_FAILED" and len(calls) == 1 and not gets
    if code:
        assert result["business_code"] == code
    else:
        assert result["http_status"] == status


@pytest.mark.parametrize("url", [
    "http://bucket.cos.ap-guangzhou.myqcloud.com/r", "https://example.com/r",
    "https://bucket.myqcloud.com.evil.test/r", "https://user:pass@ima.qq.com/r",
    "https://127.0.0.1/r", "https://ima.qq.com:444/r", "https://ima.qq.com/r#fragment",
    "https://ima.qq.com\\@evil.test/r", "https://ima.qq.com/r\r\nx: a",
])
def test_reject_download_destination_before_get(url):
    result, _, gets = run_check({"media_type": 1, "url_info": {"url": url}})
    assert result["status"] == "CHECK_FAILED" and result["file_get_attempts"] == 0 and not gets


@pytest.mark.parametrize("headers", [{"Host": "evil"}, {"Cookie": "session"}, {"Authorization": "x\ny"},
                                      {"ima-openapi-apikey": "secret"}, {"authorization": "x", "Authorization": "y"}])
def test_header_egress_is_limited(headers):
    with pytest.raises(p.ProbeError):
        d.download_target({**ACCESS, "headers": headers})


def test_long_term_secret_never_goes_to_download(monkeypatch):
    token = "test-apikey/with+escapes"
    monkeypatch.setenv("IMA_OPENAPI_APIKEY", token)
    with pytest.raises(p.ProbeError, match="FILE_CREDENTIAL_REFLECTION"):
        d.download_target({**ACCESS, "url": ACCESS["url"] + quote(quote(token, safe=""), safe="")})


def test_public_ip_pinning_and_no_credentials_or_proxies(monkeypatch):
    seen = {}
    class Response:
        status = 200
        def getheader(self, key, default=None):
            return {"Content-Length": "9"}.get(key, default)
        def read(self, n):
            if seen.get("read"):
                return b""
            seen["read"] = True
            return b"%PDF-test"
    class Connection:
        def __init__(self, host, address): seen.update(host=host, address=address)
        def request(self, method, path, headers): seen.update(method=method, path=path, headers=headers)
        def getresponse(self): return Response()
        def close(self): seen["closed"] = True
    monkeypatch.setattr(d.socket, "getaddrinfo", lambda *a, **kw: [(None,None,None,None,("8.8.8.8",443))])
    monkeypatch.setattr(d, "_PinnedHTTPS", Connection)
    assert d.download_pdf(ACCESS) == b"%PDF-test"
    assert seen["address"] == "8.8.8.8" and seen["host"].endswith(".myqcloud.com")
    assert seen["headers"]["Host"] == seen["host"] and seen["method"] == "GET" and seen["closed"]


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1"])
def test_private_dns_is_rejected_before_connection(monkeypatch, ip):
    monkeypatch.setattr(d.socket, "getaddrinfo", lambda *a, **kw: [(None,None,None,None,(ip,443))])
    monkeypatch.setattr(d, "_PinnedHTTPS", lambda *a: pytest.fail("connection must not occur"))
    with pytest.raises(p.ProbeError, match="FILE_DNS_NOT_PUBLIC"):
        d.download_pdf(ACCESS)


def test_get_failure_retains_attempt_not_pdf_or_source_text():
    def fail(_): raise OSError("secret signed URL")
    result, _, gets = run_check(downloader=fail)
    assert result["status"] == "CHECK_FAILED" and result["file_get_attempts"] == 1 and result["pdf_downloads"] == 0
    assert len(gets) == 1 and "secret signed" not in json.dumps(result)


@pytest.mark.parametrize("body", [b"<html>login</html>", b"%PDF-" + b"x" * d.MAX_PDF], ids=["not-pdf", "oversize-pdf"])
def test_non_pdf_or_oversize_never_reaches_parser(body):
    result, _, _ = run_check(downloader=lambda _:body, inspector=lambda _:pytest.fail("must not parse"))
    assert result["status"] == "CHECK_FAILED" and result["pdf_downloads"] == 0


def synthetic_pdf(with_text=True):
    writer = PdfWriter()
    page = writer.add_blank_page(300, 300)
    if with_text:
        font = DictionaryObject({NameObject("/Type"):NameObject("/Font"), NameObject("/Subtype"):NameObject("/Type1"),
                                 NameObject("/BaseFont"):NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):DictionaryObject({NameObject("/F1"):font})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 200 Td (Synthetic text only) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.parametrize("with_text", [True, False])
def test_real_synthetic_parser_and_renderer_in_isolated_process(with_text, capfd):
    result = d.inspect_pdf(synthetic_pdf(with_text))
    assert result["status"] == ("PDF_MACHINE_READABLE" if with_text else "PDF_RENDERABLE_TEXT_UNAVAILABLE")
    assert result["pdf_pages"] == result["text_pages_checked"] == 1 and result["first_page_rendered"]
    assert result["semantic_reading"] == "NOT_PERFORMED"
    assert "Synthetic text" not in json.dumps(result) + "".join(capfd.readouterr())


def test_malformed_pdf_diagnostics_not_leaked(capfd):
    result = d.inspect_pdf(b"%PDF-secret-invalid-content")
    assert result["status"] == "PDF_PARSE_FAILED"
    assert "secret-invalid" not in "".join(capfd.readouterr())


def test_probe_three_api_calls_without_url_and_safe_output(tmp_path):
    calls = []
    def send(spec):
        calls.append(spec)
        if spec["endpoint"] == "search_knowledge_base":
            return 200, raw({"info_list":[{"id":"private-base","name":"TestBase"}],"is_end":True,"next_cursor":""})
        if spec["endpoint"] == "search_knowledge":
            return 200, raw({"info_list":[ROW]})
        return 200, raw({"media_type":1})
    result = p.probe("TestBase", "SampleCo", send=send, clock=lambda:NOW, report_title_terms="SampleCo")
    assert len(calls) == result["source_calls"] == 3
    assert result["body_check"]["status"] == "BODY_UNAVAILABLE_NO_URL" and result["pdf_downloads"] == 0
    p.write_result(tmp_path/"out", result)
    assert set(x.name for x in (tmp_path/"out").iterdir()) == {"receipt.json","summary.md"}
    assert "BODY_UNAVAILABLE_NO_URL" in (tmp_path/"out"/"summary.md").read_text()
    text=(tmp_path/"out"/"receipt.json").read_text()
    assert "synthetic-private-id" not in text and "SampleCo" not in text and "private-base" not in text


def test_workflow_explicit_opt_in_existing_document_packages_no_extra_egress():
    root=Path(__file__).resolve().parents[1]
    text=(root/".github/workflows/ima-private-probe.yml").read_text()
    assert "report-title-terms:" in text and "IMA_REPORT_TITLE_TERMS: ${{ inputs.report-title-terms }}" in text
    assert ".[feeds,documents]" in text and "schedule:" not in text
    assert "github.actor == 'auguspp'" in text and "persist-credentials: false" in text
