"""Offline regressions for exchange-official source probe; all network denied."""
import copy
import importlib.util
import json
from pathlib import Path
import socket

import pytest
import requests

MODULE = Path(__file__).resolve().parents[1] / "eval" / "exchange_official_pdf_source_probe.py"
spec = importlib.util.spec_from_file_location("exchange_pdf_probe", MODULE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

PDFS = {
    "000920": b"%PDF-1.7\nSZ TARGET SYNTHETIC\n",
    "300711": b"%PDF-1.7\nSZ CONTROL SYNTHETIC\n",
    "603268": b"%PDF-1.7\nSH TARGET SYNTHETIC\n",
    "603353": b"%PDF-1.7\nSH CONTROL SYNTHETIC\n",
}


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected external networking")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    samples = [dict(item) for item in p.SAMPLES]
    for sample in samples:
        if sample["code"] in {"300711", "603353"}:
            sample["retained_cninfo_sha256"] = p._sha(PDFS[sample["code"]])
    monkeypatch.setattr(p, "SAMPLES", tuple(samples))


class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body
        self.status_code = status
        self.headers = {"Content-Length": str(len(body))} if headers is None else headers
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, **kwargs):
        self.reads += 1
        if self.status_code != 200 or self.headers.get("Content-Encoding") == "gzip":
            raise AssertionError("rejected response body must not be read")
        yield self.body


def szse_row(sample, *, ann_id=None, title=None, attach_path=None):
    return {
        "annId": int(ann_id or sample["cninfo_announcement_id"]),
        "title": title or f"{sample['short_name']}：{sample['title']}",
        "publishTime": sample["date"] + " 00:00:00",
        "attachPath": attach_path or (
            f"/disc/disk03/finalpage/{sample['date']}/"
            f"{sample['cninfo_announcement_id']}-synthetic.PDF"
        ),
        "attachFormat": "PDF",
        "attachSize": 123,
        "secCode": [sample["code"]],
        "secName": [sample["short_name"]],
    }


def sse_row(sample, *, title=None, url=None, code=None, date=None):
    return {
        "SECURITY_CODE": code or sample["code"],
        "TITLE": title or f"{sample['short_name']}：{sample['title']}",
        "SSEDATE": date or sample["date"],
        "URL": url or (
            f"/disclosure/listedinfo/announcement/c/new/{sample['date']}/"
            f"{sample['code']}_{sample['date'].replace('-', '')}_TEST.pdf"
        ),
    }


class FakeSession:
    def __init__(self, behavior=None):
        self.behavior = behavior or {}
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        payload = json.loads(kwargs["data"])
        code = payload["stock"][0]
        key = ("SZSE_QUERY", code)
        action = self.behavior.get(key)
        if isinstance(action, type) and issubclass(action, Exception):
            raise action("SECRET_REMOTE_TEXT")
        if isinstance(action, Response):
            return action
        sample = next(s for s in p.SAMPLES if s["code"] == code)
        row = szse_row(sample)
        if callable(action):
            row = action(sample, row)
        return Response(json.dumps({"announceCount": 1, "data": [row]},
                                   ensure_ascii=False).encode())

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if url == p.SSE_QUERY:
            code = kwargs["params"]["productId"]
            key = ("SSE_QUERY", code)
            action = self.behavior.get(key)
            if isinstance(action, type) and issubclass(action, Exception):
                raise action("SECRET_REMOTE_TEXT")
            if isinstance(action, Response):
                return action
            sample = next(s for s in p.SAMPLES if s["code"] == code)
            row = sse_row(sample)
            if callable(action):
                row = action(sample, row)
            return Response(json.dumps({"result": [row]}, ensure_ascii=False).encode())
        # PDF route: resolve the code from URL.
        code = next((c for c in PDFS if c in url), None)
        if code is None:
            # SZSE synthetic path contains CNINFO id, not code.
            for sample in p.SAMPLES:
                if sample["cninfo_announcement_id"] in url:
                    code = sample["code"]
                    break
        action = self.behavior.get(("PDF", code))
        if isinstance(action, type) and issubclass(action, Exception):
            raise action("SECRET_REMOTE_TEXT")
        if isinstance(action, Response):
            return action
        body = PDFS[code]
        if callable(action):
            body = action(body)
        return Response(body)


def factory(behavior=None):
    sessions = []
    def build():
        session = FakeSession(behavior)
        sessions.append(session)
        return session
    return build, sessions


def all_calls(sessions):
    return [call for session in sessions for call in session.calls]


def test_four_fixed_exchange_sources_retain_pdfs_and_control_identity(tmp_path):
    build, sessions = factory()
    out = tmp_path / "capture"
    result = p.run_probe(out, {"mode": "SYNTHETIC"}, session_factory=build)
    calls = all_calls(sessions)
    assert result["attempted_requests"] == len(calls) == 8
    assert [r["query_status"] for r in result["records"]] == ["MATCHED"] * 4
    assert [r["pdf_status"] for r in result["records"]] == [
        "OFFICIAL_PDF_RETAINED_NOT_PRODUCTION_QUALIFIED"
    ] * 4
    assert result["records"][0]["same_bytes_as_retained_cninfo"] is None
    assert result["records"][1]["same_bytes_as_retained_cninfo"] is True
    assert result["records"][2]["same_bytes_as_retained_cninfo"] is None
    assert result["records"][3]["same_bytes_as_retained_cninfo"] is True
    assert p.verify(out) == "RETAINED_EXCHANGE_SOURCE_PROBE_INTEGRITY_CHECKED_NOT_SOURCE_TRUTH"
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["remote_failure_cause"] == "UNKNOWN"


def test_szse_request_contract_and_exact_annid(tmp_path):
    build, sessions = factory()
    p.run_probe(tmp_path / "capture", {}, session_factory=build)
    calls = all_calls(sessions)
    method, url, kwargs = calls[0]
    assert method == "POST" and url == p.SZSE_QUERY
    assert json.loads(kwargs["data"]) == {
        "seDate": ["2026-08-21", "2026-08-21"],
        "stock": ["000920"],
        "channelCode": ["listedNotice_disc"],
        "pageSize": 50,
        "pageNum": 1,
    }
    assert kwargs["allow_redirects"] is False and kwargs["stream"] is True
    first = json.loads((tmp_path / "capture" / "result.json").read_text())["records"][0]
    assert first["matched_metadata"]["exchange_announcement_id"] == "1225486756"
    assert first["matched_metadata"]["official_pdf_url"].startswith(
        "https://disc.static.szse.cn/download/disc/"
    )


def test_sse_request_contract_and_safe_official_url(tmp_path):
    build, sessions = factory()
    p.run_probe(tmp_path / "capture", {}, session_factory=build)
    calls = all_calls(sessions)
    sse_query = next(call for call in calls if call[1] == p.SSE_QUERY)
    assert sse_query[2]["params"] == {
        "isPagination": "false",
        "productId": "603268",
        "keyWord": "",
        "securityType": "0101",
        "reportType2": "LSGG",
        "reportType": "ALL",
        "beginDate": "2026-08-25",
        "endDate": "2026-08-25",
    }
    records = json.loads((tmp_path / "capture" / "result.json").read_text())["records"]
    sh = records[2]
    assert sh["matched_metadata"]["official_pdf_url"].startswith(
        "https://static.sse.com.cn/disclosure/listedinfo/announcement/"
    )


def test_szse_wrong_annid_does_not_download_that_sample(tmp_path):
    def wrong(sample, row):
        row["annId"] = 999
        return row
    build, sessions = factory({("SZSE_QUERY", "000920"): wrong})
    result = p.run_probe(tmp_path / "capture", {}, session_factory=build)
    first = result["records"][0]
    assert first["query_status"] == "NO_EXACT_MATCH"
    assert first["query_reason"] == "NO_EXACT_MATCH"
    assert first["pdf_status"] == "NOT_ATTEMPTED_NO_EXACT_MATCH"
    assert result["attempted_requests"] == 7


def test_szse_unsafe_attach_path_never_becomes_request(tmp_path):
    def unsafe(sample, row):
        row["attachPath"] = "/disc/../secret.PDF"
        return row
    build, sessions = factory({("SZSE_QUERY", "000920"): unsafe})
    result = p.run_probe(tmp_path / "capture", {}, session_factory=build)
    assert result["records"][0]["query_reason"] == "UNSAFE_ATTACH_PATH"
    assert all("secret.PDF" not in call[1] for call in all_calls(sessions))


def test_sse_wrong_title_does_not_download_that_sample(tmp_path):
    def wrong(sample, row):
        row["TITLE"] = "不同公告"
        return row
    build, _ = factory({("SSE_QUERY", "603268"): wrong})
    result = p.run_probe(tmp_path / "capture", {}, session_factory=build)
    sh = result["records"][2]
    assert sh["query_status"] == "NO_EXACT_MATCH"
    assert sh["pdf_status"] == "NOT_ATTEMPTED_NO_EXACT_MATCH"


def test_sse_unsafe_url_path_never_becomes_request(tmp_path):
    def unsafe(sample, row):
        row["URL"] = "https://evil.test/a.pdf"
        return row
    build, sessions = factory({("SSE_QUERY", "603268"): unsafe})
    result = p.run_probe(tmp_path / "capture", {}, session_factory=build)
    assert result["records"][2]["query_reason"] == "UNSAFE_URL_PATH"
    assert all("evil.test" not in call[1] for call in all_calls(sessions))


@pytest.mark.parametrize("exchange_key,code", [("SZSE_QUERY", "000920"), ("SSE_QUERY", "603268")])
def test_query_403_retains_status_without_body_and_other_exchange_continues(
    tmp_path, exchange_key, code
):
    response = Response(b"SECRET", status=403)
    build, _ = factory({(exchange_key, code): response})
    result = p.run_probe(tmp_path / "capture", {}, session_factory=build)
    row = next(r for r in result["records"] if r["code"] == code)
    assert row["query_status"] == "REJECTED"
    assert row["query_http_status"] == 403
    assert row["query_reason"] == "HTTP_REJECTED"
    assert response.reads == 0
    assert any(r["pdf_status"] == "OFFICIAL_PDF_RETAINED_NOT_PRODUCTION_QUALIFIED"
               for r in result["records"] if r["exchange"] != row["exchange"])


def test_429_stops_only_that_exchange(tmp_path):
    response = Response(b"SECRET", status=429)
    build, sessions = factory({("SZSE_QUERY", "000920"): response})
    result = p.run_probe(tmp_path / "capture", {}, session_factory=build)
    assert result["records"][0]["query_http_status"] == 429
    assert result["records"][1]["query_status"] == "SKIPPED_EXCHANGE_STOP"
    assert result["exchange_stop"]["SZSE"] == "HTTP_429_STOP"
    assert result["records"][2]["pdf_status"] == "OFFICIAL_PDF_RETAINED_NOT_PRODUCTION_QUALIFIED"
    assert result["attempted_requests"] == 5


@pytest.mark.parametrize("error,reason", [
    (requests.ConnectionError, "CONNECTION_FAILED"),
    (requests.Timeout, "REQUEST_TIMEOUT"),
])
def test_transport_failure_stops_same_exchange_but_not_other(tmp_path, error, reason):
    build, _ = factory({("SZSE_QUERY", "000920"): error})
    out = tmp_path / "capture"
    result = p.run_probe(out, {}, session_factory=build)
    assert result["records"][0]["query_reason"] == reason
    assert result["records"][1]["query_status"] == "SKIPPED_EXCHANGE_STOP"
    assert result["records"][2]["pdf_status"] == "OFFICIAL_PDF_RETAINED_NOT_PRODUCTION_QUALIFIED"
    assert "SECRET_REMOTE_TEXT" not in (out / "result.json").read_text()


def test_pdf_403_is_finite_and_does_not_read_body(tmp_path):
    response = Response(b"SECRET", status=403)
    build, _ = factory({("PDF", "000920"): response})
    result = p.run_probe(tmp_path / "capture", {}, session_factory=build)
    row = result["records"][0]
    assert row["query_status"] == "MATCHED"
    assert row["pdf_status"] == "REJECTED"
    assert row["pdf_http_status"] == 403
    assert row["pdf_reason"] == "HTTP_REJECTED"
    assert response.reads == 0


def test_non_pdf_200_fails_closed(tmp_path):
    build, _ = factory({("PDF", "000920"): lambda _: b"<html>not pdf</html>"})
    result = p.run_probe(tmp_path / "capture", {}, session_factory=build)
    assert result["records"][0]["pdf_status"] == "REJECTED"
    assert result["records"][0]["pdf_reason"] == "PDF_MAGIC_MISSING"


def test_control_hash_difference_is_recorded_not_silently_identical(tmp_path, monkeypatch):
    samples = [dict(s) for s in p.SAMPLES]
    samples[1]["retained_cninfo_sha256"] = "0" * 64
    monkeypatch.setattr(p, "SAMPLES", tuple(samples))
    build, _ = factory()
    result = p.run_probe(tmp_path / "capture", {}, session_factory=build)
    control = result["records"][1]
    assert control["pdf_status"] == "OFFICIAL_PDF_RETAINED_NOT_PRODUCTION_QUALIFIED"
    assert control["same_bytes_as_retained_cninfo"] is False


def test_query_raw_and_pdf_corruption_fail_verifier(tmp_path):
    build, _ = factory()
    out = tmp_path / "capture"
    p.run_probe(out, {}, session_factory=build)
    first_raw = next(out.glob("*-query.json"))
    original = first_raw.read_bytes()
    first_raw.write_bytes(b"{}")
    with pytest.raises(ValueError, match="QUERY_RAW_IDENTITY_MISMATCH"):
        p.verify(out)
    first_raw.write_bytes(original)
    first_pdf = next(out.glob("*.pdf"))
    first_pdf.write_bytes(b"changed")
    with pytest.raises(ValueError, match="OFFICIAL_PDF_IDENTITY_MISMATCH"):
        p.verify(out)


def test_native_identity_exact_main_first_attempt(monkeypatch):
    env = {
        "GITHUB_REPOSITORY": "auguspp/decision-kernel",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_SHA": "a" * 40,
        "EXPECTED_CODE_SHA": "a" * 40,
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "789",
    }
    monkeypatch.setattr(p, "version", lambda _: "2.34.2")
    assert p.native_identity(env)["GITHUB_RUN_ID"] == "789"
    for patch in (
        {"GITHUB_RUN_ATTEMPT": "2"},
        {"EXPECTED_CODE_SHA": "b" * 40},
        {"GITHUB_REF": "refs/heads/other"},
        {"GITHUB_EVENT_NAME": "push"},
        {"GITHUB_RUN_ID": ""},
    ):
        with pytest.raises(ValueError):
            p.native_identity({**env, **patch})


def test_existing_kernel_session_has_no_env_proxy_cookie_or_retry():
    with p._session() as session:
        assert session.trust_env is False
        assert session.auth is None
        assert len(session.cookies) == 0
        assert session.get_adapter("https://www.szse.cn/").max_retries.total == 0
        assert session.get_adapter("https://query.sse.com.cn/").max_retries.total == 0
