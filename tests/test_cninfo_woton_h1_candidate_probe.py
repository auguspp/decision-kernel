"""Bounded source-only regressions; real parser, synthetic PDFs, no networking."""
from io import BytesIO
import json
from pathlib import Path
import re
import socket

import pytest
import requests
from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject

from eval import cninfo_woton_h1_candidate_probe as p


def report_pdf(*, issuer="沃顿科技股份有限公司", year="2026", ticker="000920", statement_year="2026"):
    """Small Unicode PDF exercises the original parser without a font dependency."""
    writer = PdfWriter()
    for text in (f"{issuer} {year}年半年度报告全文 合成测试材料",
                 f"证券代码：{ticker} 合并利润表 单位：元 项目 {statement_year}年半年度 2025年半年度"):
        page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type0"), NameObject("/BaseFont"): NameObject("/Synthetic"),
            NameObject("/Encoding"): NameObject("/Identity-H"), NameObject("/DescendantFonts"): ArrayObject()})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        content = DecodedStreamObject()
        content.set_data(("BT /F1 12 Tf 10 700 Td <" + text.encode("utf-16-be").hex() + "> Tj ET").encode())
        page[NameObject("/Contents")] = content
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


BODY = report_pdf()


def announcement(number="101", title="沃顿科技：2026年半年度报告", **changes):
    return {"secCode": "000920", "secName": "沃顿科技", "announcementId": number,
            "announcementTitle": title, "announcementTime": "2026-08-21",
            "adjunctUrl": f"finalpage/2026-08-21/{number}.PDF", **changes}


class Response:
    def __init__(self, body=BODY, *, status=200, headers=None):
        self.body, self.status_code, self.reads = body, status, 0
        self.headers = {"Content-Length": str(len(body))} if headers is None else headers

    def __enter__(self): return self
    def __exit__(self, *args): return False

    def iter_content(self, *, chunk_size):
        self.reads += 1
        assert self.status_code == 200, "rejected HTTP body was read"
        for offset in range(0, len(self.body), chunk_size):
            yield self.body[offset:offset + chunk_size]


def directory(rows, *, more=False, total=None):
    return Response(p._raw({"announcements": rows, "hasMore": more,
                            "totalAnnouncement": len(rows or []) if total is None else total}))


def session_factory(responses):
    calls, pending = [], iter(responses)

    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): return False

        def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            response = next(pending)
            if isinstance(response, Exception):
                raise response
            return response

        def post(self, url, **kwargs): return self.request("POST", url, **kwargs)
        def get(self, url, **kwargs): return self.request("GET", url, **kwargs)

    return Session, calls


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("source-probe test attempted live networking")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


def run_case(tmp_path, responses, **kwargs):
    factory, calls = session_factory(responses)
    output = tmp_path / "capture"
    result = p.run_probe(output, {"test_only": "SYNTHETIC_NOT_A_NATIVE_RUN"}, session_factory=factory, **kwargs)
    p.verify(output)
    return output, result, calls


def test_two_pages_three_pdfs_keep_revisions_and_unattempted_version(tmp_path):
    first = directory([announcement(), announcement("102", "沃顿科技：2026年半年度报告（更正后）")], more=True, total=4)
    second = directory([announcement("103", "2026年半年度报告（补充修订版）"), announcement("104")])
    output, result, calls = run_case(tmp_path, [first, second, Response(), Response(), Response()])
    assert [method for method, _, _ in calls] == ["POST", "POST", "GET", "GET", "GET"]
    assert result["attempted_requests"] == 5
    assert [call[2]["data"] for call in calls[:2]] == [p.build_query(1), p.build_query(2)]
    assert all("topSearch" not in url and call["allow_redirects"] is False for _, url, call in calls)
    assert all(call["headers"]["Accept-Encoding"] == "identity" for _, _, call in calls)
    assert all(doc["status"] == "PDF_PARSED_IDENTITY_CHECKED_NOT_RESEARCH" for doc in result["documents"])
    assert len(result["unattempted_candidates"]) == 1
    assert result["unattempted_candidates"][0]["announcement_id"] == "104"
    assert sum(item["revision_label_present"] for item in result["catalog"]["candidates"]) == 2
    assert result["catalog"]["version_selection"] == "MULTIPLE_CANDIDATES_NO_CANONICAL_VERSION_SELECTED"
    assert result["received_response_bytes"] == len(first.body) + len(second.body) + 3 * len(BODY)
    assert all(result[key] == 0 for key in ("model_calls", "research_work_writes", "market_state_writes"))
    assert (output / "response-3.pdf").read_bytes() == BODY
    assert json.loads((output / "extraction-3.json").read_bytes())["page_count"] == 2


def test_directory_filters_wrong_scope_summary_and_unsafe_locator_before_get(tmp_path):
    rows = [announcement(secCode="600519"), announcement(title="2025年半年度报告"),
            announcement(title="2026年年度报告"), announcement(title="2026年半年度报告摘要"),
            announcement(title="关于2026年半年度报告的更正公告"),
            announcement(announcementTime="2026-09-21"),
            announcement(adjunctUrl="https://evil.example/101.PDF"),
            announcement(adjunctUrl="https://static.cninfo.com.cn@evil.example/101.PDF"),
            announcement(adjunctUrl="http://static.cninfo.com.cn/finalpage/2026-08-21/101.PDF"),
            announcement(adjunctUrl="finalpage/2026-08-21/999.PDF")]
    _, result, calls = run_case(tmp_path, [directory(rows)])
    assert len(calls) == 1 and result["catalog"]["candidates"] == []
    assert len(result["catalog"]["decisions"]) == len(rows)
    assert result["catalog"]["match_status"] == "NO_MATCH_IN_RETURNED_ROWS"


@pytest.mark.parametrize("changed", [
    {"issuer": "另一家股份有限公司"}, {"year": "2025"}, {"ticker": "000921"}, {"statement_year": "2025"},
])
def test_wrong_document_identity_remains_saved_without_qualification(tmp_path, changed):
    body = report_pdf(**changed)
    output, result, _ = run_case(tmp_path, [directory([announcement()]), Response(body)])
    assert result["documents"][0]["status"] == "PDF_RETAINED_DOCUMENT_IDENTITY_MISMATCH"
    assert (output / "response-2.pdf").read_bytes() == body


@pytest.mark.parametrize("payload,expected", [
    ({"announcements": None, "totalAnnouncement": 0}, "NO_MATCH_IN_RETURNED_ROWS"),
    ({"announcements": []}, "NO_MATCH_IN_RETURNED_ROWS"),
    ({"announcements": None}, "UNKNOWN"), ({}, "UNKNOWN"),
    ({"announcements": [], "hasMore": "false"}, "UNKNOWN"),
])
def test_empty_directory_and_invalid_envelope_are_distinguished(tmp_path, payload, expected):
    _, result, calls = run_case(tmp_path, [Response(p._raw(payload))])
    assert len(calls) == 1 and result["documents"] == []
    assert result["catalog"]["match_status"] == expected


def test_second_page_failure_keeps_first_page_candidate_unattempted(tmp_path):
    rejected = Response(b"secret remote error", status=403)
    output, result, calls = run_case(tmp_path, [directory([announcement()], more=True, total=31), rejected])
    assert len(calls) == 2 and rejected.reads == 0
    assert result["catalog"]["status"] == "DIRECTORY_FAILED"
    assert result["unattempted_candidates"][0]["announcement_id"] == "101"
    assert (output / "response-1.bin").is_file()
    assert "secret remote error" not in (output / "result.json").read_text()


@pytest.mark.parametrize("body", [b"<html>200 is not a PDF</html>", b"%PDF-1.7\ninvalid page tree"])
def test_200_non_pdf_or_broken_pdf_retains_original_failure_bytes(tmp_path, body):
    output, result, _ = run_case(tmp_path, [directory([announcement()]), Response(body)])
    doc = result["documents"][0]
    assert doc["status"] == "BODY_RETAINED_PDF_PARSE_FAILED"
    assert (output / result["records"][1]["body_file"]).read_bytes() == body
    assert doc["extraction_file"] is None


def test_unknown_parser_error_does_not_lose_pdf_or_journal(tmp_path, monkeypatch):
    def broken_parser(raw):
        assert (tmp_path / "capture/response-2.pdf").read_bytes() == raw
        raise OSError("private parser details")
    monkeypatch.setattr(p, "_extract", broken_parser)
    output, result, _ = run_case(tmp_path, [directory([announcement()]), Response()])
    assert result["documents"][0]["parse_error_type"] == "OSError"
    assert (output / "journal.json").is_file() and result["internal_failure"] is None
    assert "private parser details" not in (output / "result.json").read_text()


@pytest.mark.parametrize("kind,with_length", [("DIRECTORY", True), ("DIRECTORY", False), ("PDF", True), ("PDF", False)])
def test_response_byte_bounds_apply_to_declared_and_streamed_bodies(tmp_path, kind, with_length):
    cap = p.LIMITS["directory_bytes" if kind == "DIRECTORY" else "pdf_bytes"]
    response = Response(b"x" * (cap + 1), headers=None if with_length else {})
    inputs = [response] if kind == "DIRECTORY" else [directory([announcement()]), response]
    _, result, _ = run_case(tmp_path, inputs)
    record = result["records"][-1]
    assert record["reason"] == "RESPONSE_BYTE_LIMIT" and record["body_file"] is None
    assert response.reads == (0 if with_length else 1)


def test_total_budget_includes_directory_bytes_and_stops_before_next_body(tmp_path, monkeypatch):
    query = directory([announcement(str(i)) for i in (101, 102, 103)])
    monkeypatch.setattr(p, "LIMITS", {**p.LIMITS,
        "total_response_bytes": len(query.body) + 2 * len(BODY) - 1})
    rejected = Response()
    _, result, calls = run_case(tmp_path, [query, Response(), rejected])
    assert len(calls) == 3 and rejected.reads == 0
    assert result["received_response_bytes"] == len(query.body) + len(BODY)
    assert result["stop_reason"] == "TOTAL_RESPONSE_BYTE_LIMIT"
    assert result["unattempted_candidates"][0]["announcement_id"] == "103"


@pytest.mark.parametrize("response,reason", [
    (Response(status=302, headers={"Location": "https://evil.example/redirect"}), "HTTP_REJECTED"),
    (Response(status=429), "HTTP_REJECTED"),
    (requests.ConnectionError("SECRET_REMOTE_TRACE"), "CONNECTION_FAILED"),
])
def test_no_redirect_retry_or_exception_text_egress(tmp_path, response, reason):
    output, result, calls = run_case(tmp_path, [directory([announcement()]), response])
    assert len(calls) == 2 and result["records"][-1]["reason"] == reason
    assert all(call["allow_redirects"] is False for _, _, call in calls)
    assert "SECRET_REMOTE_TRACE" not in (output / "result.json").read_text()


def test_acquisition_clock_stops_during_stream(tmp_path):
    times = iter((0, 0, 181))
    _, result, calls = run_case(tmp_path, [directory([announcement()])], monotonic=lambda: next(times, 181))
    assert len(calls) == 1 and result["stop_reason"] == "ELAPSED_BUDGET"
    assert result["records"][0]["body_file"] is None


def reseal(output, result):
    result.pop("result_sha256", None)
    result["result_sha256"] = p._sha(p._raw(result))
    (output / "result.json").write_bytes(p._raw(result))
    (output / "journal.json").write_bytes(p._raw(result["records"]))


def test_pdf_hash_and_reparsed_text_cannot_be_replaced_by_self_hashes(tmp_path):
    output, result, _ = run_case(tmp_path, [directory([announcement()]), Response()])
    body_path = output / "response-2.pdf"
    body_path.write_bytes(report_pdf(issuer="另一家股份有限公司"))
    with pytest.raises(ValueError, match="BODY_HASH"):
        p.verify(output)
    row = result["records"][1]
    row.update(body_sha256=p._sha(body_path.read_bytes()), received_bytes=body_path.stat().st_size)
    result["received_response_bytes"] = sum(row["received_bytes"] for row in result["records"])
    reseal(output, result)
    with pytest.raises(ValueError, match="EXTRACTION_DIFFERS"):
        p.verify(output)


def test_sina_same_bytes_requires_actual_digest_equality(tmp_path, monkeypatch):
    monkeypatch.setattr(p, "SINA_SHA256", p._sha(BODY))  # synthetic comparison, never a company receipt
    _, result, _ = run_case(tmp_path, [directory([announcement()]), Response()])
    assert result["documents"][0]["sina_comparison"] == "SAME_BYTES"


def test_verify_only_never_checks_live_identity_or_makes_request(tmp_path, monkeypatch):
    output, _, _ = run_case(tmp_path, [directory([announcement()]), Response()])
    def forbidden(*args, **kwargs):
        raise AssertionError("verify-only crossed a live boundary")
    monkeypatch.setattr(p, "native_identity", forbidden)
    monkeypatch.setattr(p, "run_probe", forbidden)
    assert p.main(["--output", str(output), "--verify-only"]) == 0


def test_capture_cli_logs_only_verified_bounded_observations_once(tmp_path, monkeypatch, capsys):
    private = "BODY_ONLY_DO_NOT_LOG_" + "x" * 100_000
    rows = [announcement(internal_note=private), announcement("102", "2026年半年度报告（修订版）")]
    factory, calls = session_factory([directory(rows), Response(headers={"Set-Cookie": private}),
                                     Response(b"<html>BODY_ONLY_DO_NOT_LOG</html>")])
    native = {"GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "123"}
    capture = p.run_probe
    monkeypatch.setattr(p, "native_identity", lambda: native)
    monkeypatch.setattr(p, "run_probe", lambda output, identity: capture(output, identity, session_factory=factory))
    output = tmp_path / "capture"
    assert p.main(["--output", str(output)]) == 0
    logged = capsys.readouterr().out
    lines = [line for line in logged.splitlines() if line.startswith("SOURCE_PROBE_OBSERVATIONS=")]
    assert len(lines) == 1 and len(lines[0]) < 6000
    observed = json.loads(lines[0].split("=", 1)[1])
    saved = json.loads((output / "result.json").read_bytes())
    assert observed["identity"] == {"code_commit": "a" * 40, "run_id": "123"}
    assert observed["directory"]["candidate_count"] == 2
    assert observed["directory"]["status"] == saved["catalog"]["status"]
    assert observed["attempted_requests"] == len(calls) == 3
    for actual, record in zip(observed["requests"], saved["records"]):
        assert set(actual) == {"sequence", "kind", "url", "http_status", "received_bytes",
                               "body_sha256", "reason", "started_at", "finished_at"}
        assert actual == {key: record[key] for key in actual}
    document = observed["documents"][0]
    parsed = json.loads((output / "extraction-2.json").read_bytes())
    assert document["page_count"] == parsed["page_count"] == 2
    assert document["text_sha256"] == parsed["text_sha256"]
    assert document["identity"] == saved["documents"][0]["identity"]
    assert observed["documents"][1]["page_count"] is None
    assert observed["documents"][1]["text_sha256"] is None
    assert observed["model_calls"] == observed["research_work_writes"] == 0
    assert all(text not in logged for text in ("BODY_ONLY_DO_NOT_LOG", "沃顿科技", "半年度报告", "Set-Cookie"))
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    assert p.main(["--output", str(output), "--verify-only"]) == 0
    assert "SOURCE_PROBE_OBSERVATIONS=" not in capsys.readouterr().out
    assert len(calls) == 3 and before == {path.name: path.read_bytes() for path in output.iterdir()}


def test_existing_output_is_never_reused(tmp_path):
    output, _, _ = run_case(tmp_path, [directory([])])
    factory, calls = session_factory([])
    with pytest.raises(FileExistsError):
        p.run_probe(output, {}, session_factory=factory)
    assert calls == []


def test_new_workflow_mode_has_only_its_fixed_capture_and_offline_verify():
    path = Path(__file__).resolve().parents[1] / ".github/workflows/cninfo-announcement-source-probe.yml"
    text = path.read_text()
    steps = re.split(r"\n      - ", text)
    mode = "inputs.probe-kind == 'woton-h1-cninfo-candidate'"
    capture = [step for step in steps if "-m eval.cninfo_woton_h1_candidate_probe" in step]
    assert len(capture) == 2 and all(f"if: {mode}\n" in step for step in capture)
    command = "python -m eval.cninfo_woton_h1_candidate_probe --output cninfo-woton-h1-candidate-probe"
    assert [re.search(r"^\s*run: (.+)$", step, re.M).group(1) for step in capture] == [command, command + " --verify-only"]
    install = [step for step in steps if ".[documents]" in step]
    assert len(install) == 1 and f"if: {mode}\n" in install[0]
    artifact = next(step for step in steps if "upload-artifact@" in step)
    assert "if: always()" in artifact
    artifact_inputs = artifact.split("\n        with:", 1)[1]
    for field in ("name", "path"):
        assert "woton-h1-cninfo-candidate" in re.search(rf"^\s*{field}: (.+)$", artifact_inputs, re.M).group(1)
    assert "permissions:\n  contents: read\n" in text
    assert "secrets." not in text
