from __future__ import annotations

import copy
import io
import json
from urllib.error import HTTPError, URLError

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_source_capture as capture
from test_economic_source_capture import NOW, SOURCES, execute, rehash_file, response


class UnreadBody(io.BytesIO):
    def read(self, *args, **kwargs):
        pytest.fail("HTTP error body must not be read")


def http_error(code):
    body = UnreadBody(b"private-error-body-marker")
    error = HTTPError(
        "https://untrusted.invalid/?token=private-url-marker", code,
        "private-reason-marker", {"Set-Cookie": "private-cookie-marker"}, body,
    )
    return error, body


def mutate_manifest(root, edit):
    value = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    edit(value)
    value.pop("capture_hash")
    value["capture_hash"] = canonical_hash(value)
    (root / "manifest.json").write_text(canonical_json(value) + "\n", encoding="utf-8")


@pytest.mark.parametrize("code", [401, 403, 404, 429, 500, 503])
def test_numeric_http_failure_is_preserved_closed_and_never_retried(tmp_path, monkeypatch, code):
    error, body = http_error(code)
    calls = []

    def transport(url):
        calls.append(url)
        raise error

    root = tmp_path / "capture"
    original = copy.deepcopy(SOURCES[0])
    manifest = execute(root, [original], transport=transport)
    assert original == SOURCES[0]
    assert calls == [original["source_url"]]
    assert body.closed
    assert manifest["schema_version"] == capture.CAPTURE_SCHEMA_VERSION == 2
    assert manifest["status"] == "INCOMPLETE"
    record = manifest["records"][0]
    assert record["http_status"] == code
    assert record["error_type"] == "HTTPError"
    assert record["error_reason"] == capture._http_error_reason(code)
    assert record["status"] == "SOURCE_UNAVAILABLE"
    assert set(path.name for path in (root / "0000").iterdir()) == {"source.json"}
    data = b"\n".join(path.read_bytes() for path in root.rglob("*") if path.is_file())
    for marker in (b"private-url-marker", b"private-reason-marker", b"private-cookie-marker", b"private-error-body-marker"):
        assert marker not in data
    assert f"HTTP={code}" in (root / "summary.md").read_text(encoding="utf-8")
    monkeypatch.setattr(capture, "fetch_public_page", lambda url: pytest.fail("verifier called network"))
    report = capture.verify_capture(root)
    assert report["archive_integrity"] == "VERIFIED"
    assert report["status"] == "INCOMPLETE"
    assert report["network_calls"] == report["production_state_writes"] == 0
    assert capture.main(["verify", str(root)]) == 2


@pytest.mark.parametrize("code", [None, "403", True, 200, 299, 600])
def test_malformed_http_error_status_remains_unknown_not_coerced(tmp_path, code):
    error, body = http_error(code)

    def fail(url):
        raise error

    root = tmp_path / "capture"
    result = execute(root, [SOURCES[0]], transport=fail)
    assert body.closed
    assert result["records"][0]["http_status"] is None
    assert "valid numeric status unavailable" in result["records"][0]["error_reason"]
    assert "HTTP=UNKNOWN" in (root / "summary.md").read_text(encoding="utf-8")
    assert capture.verify_capture(root)["status"] == "INCOMPLETE"


def test_lowest_http_opener_error_is_caught_by_capture_without_credentials(tmp_path, monkeypatch):
    error, body = http_error(403)
    calls = []

    class Opener:
        def open(self, request, timeout):
            calls.append((request.full_url, request.header_items(), timeout))
            raise error

    monkeypatch.setattr(capture, "build_opener", lambda *args: Opener())
    root = tmp_path / "capture"
    # Exercise the actual lowest transport, but retain explicit synthetic provenance.
    result = execute(root, [SOURCES[0]], transport=capture.fetch_public_page)
    assert len(calls) == 1 and calls[0][0] == SOURCES[0]["source_url"]
    assert calls[0][2] == 20 and body.closed
    assert {name.lower() for name, _ in calls[0][1]} == {"user-agent", "accept", "accept-encoding"}
    assert result["provenance"] == capture.SYNTHETIC
    assert result["records"][0]["http_status"] == 403
    assert capture.verify_capture(root)["matched_excerpts"] == 0


def test_mixed_results_keep_http_success_separate_from_extraction_success(tmp_path):
    selected = SOURCES[:3]
    by_url = {source["source_url"]: source for source in selected}
    calls = []

    def transport(url):
        calls.append(url)
        if url == selected[0]["source_url"]:
            raise http_error(404)[0]
        value = response(by_url[url])
        if url == selected[1]["source_url"]:
            return capture.PublicResponse(url, 200, value.headers, value.body.replace(b"11.55", b"10.55"))
        return value

    root = tmp_path / "capture"
    result = execute(root, selected, transport=transport)
    assert calls == [source["source_url"] for source in selected]
    assert [row["http_status"] for row in result["records"]] == [404, 200, 200]
    assert [row["status"] for row in result["records"]] == ["SOURCE_UNAVAILABLE", "REJECTED_BINDING", capture.MATCHED]
    assert capture.verify_capture(root)["matched_excerpts"] == 1
    assert result["status"] == "INCOMPLETE"


def test_non_http_transport_failure_never_infers_http_status_from_message(tmp_path):
    def fail(url):
        raise URLError("403 token=private-marker")

    root = tmp_path / "capture"
    result = execute(root, [SOURCES[0]], transport=fail)
    assert result["records"][0]["http_status"] is None
    assert result["records"][0]["error_type"] == "URLError"
    assert "private-marker" not in (root / "manifest.json").read_text(encoding="utf-8")
    assert capture.verify_capture(root)["status"] == "INCOMPLETE"


def test_redirect_is_not_followed_or_saved_but_its_numeric_code_is_known(tmp_path):
    body = UnreadBody(b"private-body")

    def redirect(url):
        capture._NoRedirect().redirect_request(
            None, body, 302, "private-reason", {"Set-Cookie": "private-cookie"},
            "https://other.invalid/?token=private-target",
        )

    root = tmp_path / "capture"
    result = execute(root, [SOURCES[0]], transport=redirect)
    assert body.closed
    record = result["records"][0]
    assert record["http_status"] == 302 and record["error_type"] == "EconomicRedirectError"
    assert record["status"] == "SOURCE_UNAVAILABLE"
    assert "private-target" not in (root / "manifest.json").read_text(encoding="utf-8")
    assert capture.verify_capture(root)["status"] == "INCOMPLETE"


@pytest.mark.parametrize("value", [True, "200", 200.0, 99, 600, None, 403])
def test_rehashed_http_status_must_match_retained_response_metadata(tmp_path, value):
    root = tmp_path / "capture"
    execute(root, [SOURCES[0]])
    mutate_manifest(root, lambda payload: payload["records"][0].update(http_status=value))
    with pytest.raises(capture.EconomicCaptureError, match="HTTP status"):
        capture.verify_capture(root)


def test_error_code_cannot_change_without_a_consistent_safe_diagnostic(tmp_path):
    def fail(url):
        raise http_error(403)[0]

    root = tmp_path / "capture"
    execute(root, [SOURCES[0]], transport=fail)
    mutate_manifest(root, lambda payload: payload["records"][0].update(http_status=404))
    with pytest.raises(capture.EconomicCaptureError, match="diagnostic"):
        capture.verify_capture(root)


def test_rehashed_summary_cannot_hide_failures(tmp_path):
    root = tmp_path / "capture"
    execute(root, [SOURCES[0]])
    rehash_file(root, "summary.md", b"invented all-clear summary\n")
    with pytest.raises(capture.EconomicCaptureError, match="summary"):
        capture.verify_capture(root)


def test_older_schema_is_not_silently_upgraded_or_backfilled(tmp_path):
    root = tmp_path / "capture"
    execute(root, [SOURCES[0]])
    mutate_manifest(root, lambda payload: payload.update(schema_version=1))
    before = {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    with pytest.raises(capture.EconomicCaptureError, match="recorded implementation"):
        capture.verify_capture(root)
    assert before == {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}
