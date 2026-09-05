from __future__ import annotations

import json

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_source_capture as capture
from test_economic_source_capture import SOURCES, execute, rehash_file, response


@pytest.mark.parametrize("mode", ["match", "truncated", "declared_oversized"])
def test_lowest_transport_is_bounded_and_credential_free(monkeypatch, mode):
    source = SOURCES[0]
    body = response(source).body
    requests, reads, handlers = [], [], []

    class Reply:
        status = 200
        headers = {"Content-Type": "text/html; charset=utf-8",
                   "Content-Length": str(len(body) if mode == "match" else len(body) + 10),
                   "Set-Cookie": "not-retained"}
        if mode == "declared_oversized":
            headers["Content-Length"] = str(capture.MAX_BODY_BYTES + 1)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def geturl(self):
            return source["source_url"]
        def read(self, size):
            reads.append(size)
            return body

    class Opener:
        def open(self, request, timeout):
            requests.append((request, timeout))
            return Reply()

    def opener(*values):
        handlers.extend(values)
        return Opener()

    monkeypatch.setattr(capture, "build_opener", opener)
    if mode == "match":
        result = capture.fetch_public_page(source["source_url"])
        assert result.body == body
        assert result.headers == {"content-type": "text/html; charset=utf-8", "content-length": str(len(body))}
    else:
        with pytest.raises(capture.EconomicCaptureError):
            capture.fetch_public_page(source["source_url"])
    assert len(requests) == 1
    request, timeout = requests[0]
    assert timeout == 20 and request.get_method() == "GET"
    headers = {key.lower(): value for key, value in request.header_items()}
    assert set(headers) == {"user-agent", "accept", "accept-encoding"}
    assert headers["accept-encoding"] == "identity"
    assert any(isinstance(item, capture._NoRedirect) for item in handlers)
    assert next(item for item in handlers if isinstance(item, capture.ProxyHandler)).proxies == {}
    assert reads == ([] if mode == "declared_oversized" else [capture.MAX_BODY_BYTES + 1])


def test_rehashed_false_rejection_does_not_pass_verification(tmp_path):
    root = tmp_path / "capture"
    execute(root, [SOURCES[0]])
    manifest = json.loads((root / "manifest.json").read_text())
    for name in ("page.txt", "binding.json", "observation.json"):
        (root / "0000" / name).unlink()
        manifest["files"].pop("0000/" + name)
    manifest["records"][0].update(status="REJECTED_BINDING", error_type="EconomicCaptureError", error_reason="invented failure")
    manifest["status"] = "INCOMPLETE"
    manifest.pop("capture_hash")
    manifest["capture_hash"] = canonical_hash(manifest)
    (root / "manifest.json").write_text(canonical_json(manifest))
    with pytest.raises(capture.EconomicCaptureError, match="now accepts"):
        capture.verify_capture(root)


def test_rehashed_extra_response_header_is_rejected(tmp_path):
    root = tmp_path / "capture"
    execute(root, [SOURCES[0]])
    metadata = json.loads((root / "0000/response.json").read_text())
    metadata["headers"]["set-cookie"] = "not allowed"
    rehash_file(root, "0000/response.json", (canonical_json(metadata) + "\n").encode())
    with pytest.raises(capture.EconomicCaptureError, match="metadata"):
        capture.verify_capture(root)


def test_synthetic_mode_cannot_accidentally_use_live_transport(tmp_path, monkeypatch):
    monkeypatch.setattr(capture, "fetch_public_page", lambda url: pytest.fail("synthetic mode contacted public server"))
    with pytest.raises(capture.EconomicCaptureError, match="injected transport"):
        capture.capture_reviewed_sources(SOURCES, tmp_path / "capture", provenance=capture.SYNTHETIC)
    assert not (tmp_path / "capture").exists()
