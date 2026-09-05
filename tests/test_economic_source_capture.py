from __future__ import annotations

import copy
import hashlib
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import URLError

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_source_capture as capture


SOURCES = json.loads(Path("radar_inputs/economic-node-study-2026-09-05.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 9, 5, 6, tzinfo=timezone.utc)


def response(source, *, body=None, headers=None):
    if body is None:
        lines = source["excerpt"].splitlines()
        body = ("<!doctype html><html><head><meta charset='utf-8'>"
                "<script>document.cookie='ignored';</script></head><body>"
                + "".join("<p>" + html.escape(line) + "</p>" for line in lines)
                + "</body></html>").encode("utf-8")
    return capture.PublicResponse(source["source_url"], 200,
        headers or {"Content-Type": "text/html; charset=utf-8", "Set-Cookie": "must-not-be-retained"}, body)


def execute(root, sources=None, transport=None, clock=NOW):
    selected = copy.deepcopy(sources if sources is not None else SOURCES)
    by_url = {source["source_url"]: source for source in selected}
    return capture.capture_reviewed_sources(selected, root,
        transport=transport or (lambda url: response(by_url[url])),
        provenance=capture.SYNTHETIC, now=lambda: clock)


def rehash_file(root, name, data):
    (root / name).write_bytes(data)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    manifest.pop("capture_hash")
    manifest["capture_hash"] = canonical_hash(manifest)
    (root / "manifest.json").write_text(canonical_json(manifest) + "\n", encoding="utf-8")


@pytest.mark.parametrize("index", range(4))
def test_reviewed_source_binds_to_exact_synthetic_html_with_new_capture_time(tmp_path, monkeypatch, index):
    source = copy.deepcopy(SOURCES[index])
    original = copy.deepcopy(source)
    root = tmp_path / "capture"
    manifest = execute(root, [source])
    assert manifest["status"] == "COMPLETE"
    assert manifest["provenance"] == capture.SYNTHETIC
    assert source == original
    assert (root / "0000/response.bin").read_bytes() == response(source).body
    metadata = json.loads((root / "0000/response.json").read_text())
    assert "Set-Cookie" not in metadata["headers"] and "set-cookie" not in metadata["headers"]
    observation = json.loads((root / "0000/observation.json").read_text())
    assert observation["system_pit_eligible_from"] == "2026-09-05T06:00:00Z"
    assert observation["source_record"]["captured_at"] != original["captured_at"]
    assert observation["source_record"]["capture_method"] == capture.SYNTHETIC
    assert observation["historical_first_vintage_proven"] is False
    assert all(observation[key] == "NONE" for key in capture.AUTHORITY)
    monkeypatch.setattr(capture, "fetch_public_page", lambda url: pytest.fail("offline verify contacted network"))
    report = capture.verify_capture(root)
    assert report["matched_excerpts"] == report["attempted_sources"] == 1
    assert report["network_calls"] == report["production_state_writes"] == 0


def test_revised_fact_is_retained_but_does_not_silently_replace_reviewed_value(tmp_path):
    def transport(url):
        source = next(item for item in SOURCES if item["source_url"] == url)
        value = response(source)
        if source == SOURCES[1]:
            value = capture.PublicResponse(url, 200, value.headers, value.body.replace(b"11.55", b"10.55"))
        return value
    root = tmp_path / "capture"
    result = execute(root, transport=transport)
    assert result["status"] == "INCOMPLETE"
    assert [item["status"] for item in result["records"]] == [capture.MATCHED, "REJECTED_BINDING", capture.MATCHED, capture.MATCHED]
    assert b"10.55" in (root / "0001/response.bin").read_bytes()
    assert not (root / "0001/observation.json").exists()
    assert capture.verify_capture(root)["matched_excerpts"] == 3


def test_transport_error_does_not_leak_exception_payload_or_retry(tmp_path):
    calls = []
    def fail(url):
        calls.append(url)
        raise URLError("sensitive transport message not for persistence")
    root = tmp_path / "capture"
    result = execute(root, [SOURCES[0]], transport=fail)
    assert calls == [SOURCES[0]["source_url"]]
    assert result["status"] == "INCOMPLETE"
    assert result["records"][0]["error_type"] == "URLError"
    assert all(b"sensitive transport" not in path.read_bytes() for path in root.rglob("*") if path.is_file())
    assert not (root / "0000/response.bin").exists()
    assert capture.verify_capture(root)["status"] == "INCOMPLETE"


@pytest.mark.parametrize("mutation", ["bad_url", "duplicate", "empty", "too_many"])
def test_source_preflight_fails_without_network_or_directory(tmp_path, mutation):
    selected = copy.deepcopy(SOURCES[:1])
    if mutation == "bad_url":
        selected[0]["source_url"] = "https://127.0.0.1/private"
    elif mutation == "duplicate":
        selected *= 2
    elif mutation == "empty":
        selected = []
    else:
        selected = SOURCES + SOURCES[:1]
    with pytest.raises(ValueError):
        execute(tmp_path / "capture", selected, transport=lambda url: pytest.fail("unexpected network"))
    assert not (tmp_path / "capture").exists()


def test_injected_transport_cannot_claim_public_http_capture(tmp_path):
    with pytest.raises(capture.EconomicCaptureError, match="synthetic"):
        capture.capture_reviewed_sources(SOURCES, tmp_path / "capture", transport=lambda url: None)
    assert not (tmp_path / "capture").exists()


@pytest.mark.parametrize("url", [
    "http://xmsyj.moa.gov.cn/jcyj/202609/t20260901_6487189.htm",
    "https://xmsyj.moa.gov.cn.evil.invalid/jcyj/202609/t20260901_6487189.htm",
    "https://www.spb.gov.cn/gjyzj/c100015/c100016/202608/b38ba608fef440bb89db1e7c3a9fddbf.shtml?token=x",
    "https://user:pass@www.spb.gov.cn/anything", "file:///etc/passwd",
])
def test_lowest_transport_rejects_unapproved_urls_before_request(monkeypatch, url):
    monkeypatch.setattr(capture, "build_opener", lambda *args: pytest.fail("opener called for bad URL"))
    with pytest.raises(capture.EconomicCaptureError, match="allowlist"):
        capture.fetch_public_page(url)


def test_redirect_is_not_followed():
    with pytest.raises(capture.EconomicCaptureError, match="redirect"):
        capture._NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://elsewhere.invalid")


@pytest.mark.parametrize("case", ["json", "conflicting_charset", "bad_bytes", "oversized"])
def test_unqualified_response_never_produces_an_observation(tmp_path, case):
    source = SOURCES[0]
    value = response(source)
    if case == "json":
        value = response(source, headers={"content-type": "application/json"})
    elif case == "conflicting_charset":
        value = response(source, headers={"content-type": "text/html; charset=gbk"})
    elif case == "bad_bytes":
        value = response(source, body=b"\xff", headers={"content-type": "text/html; charset=utf-8"})
    else:
        value = response(source, body=b"a" * (capture.MAX_BODY_BYTES + 1))
    root = tmp_path / "capture"
    result = execute(root, [source], transport=lambda url: value)
    assert result["status"] == "INCOMPLETE"
    assert not (root / "0000/observation.json").exists()
    assert capture.verify_capture(root)["matched_excerpts"] == 0


def test_script_only_price_does_not_satisfy_reviewed_evidence(tmp_path):
    source = SOURCES[0]
    value = response(source)
    phrase = html.escape(source["excerpt"].splitlines()[3]).encode("utf-8")
    body = value.body.replace(b"<p>" + phrase + b"</p>", b"<script>" + phrase + b"</script>")
    result = execute(tmp_path / "capture", [source], transport=lambda url: response(source, body=body))
    assert result["records"][0]["status"] == "REJECTED_BINDING"


def test_rehashed_forged_metric_fails_raw_reconstruction(tmp_path):
    root = tmp_path / "capture"
    execute(root, [SOURCES[0]])
    value = json.loads((root / "0000/observation.json").read_text())
    value["metrics"][0]["value"] = "999"
    value.pop("observation_hash")
    value["observation_hash"] = canonical_hash(value)
    rehash_file(root, "0000/observation.json", (canonical_json(value) + "\n").encode())
    with pytest.raises(capture.EconomicCaptureError, match="reconstruct"):
        capture.verify_capture(root)


@pytest.mark.parametrize("mutation", ["body", "extra", "symlink", "incomplete"])
def test_archive_integrity_rejects_tampering(tmp_path, mutation):
    root = tmp_path / "capture"
    execute(root, [SOURCES[0]])
    if mutation == "body":
        (root / "0000/response.bin").write_bytes(b"changed")
    elif mutation == "extra":
        (root / "extra.txt").write_text("unexpected")
    elif mutation == "symlink":
        (root / "linked").symlink_to(tmp_path)
    else:
        value = json.loads((root / "manifest.json").read_text())
        value["status"] = "RECORDING"
        value.pop("capture_hash")
        value["capture_hash"] = canonical_hash(value)
        (root / "manifest.json").write_text(canonical_json(value))
    with pytest.raises(capture.EconomicCaptureError):
        capture.verify_capture(root)


def test_new_captures_preserve_original_archive_and_do_not_backdate_knowledge(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    execute(first, [SOURCES[0]])
    before = {str(path.relative_to(first)): path.read_bytes() for path in first.rglob("*") if path.is_file()}
    execute(second, [SOURCES[0]], clock=NOW + timedelta(days=1))
    assert (first / "0000/response.bin").read_bytes() == (second / "0000/response.bin").read_bytes()
    assert (first / "0000/observation.json").read_bytes() != (second / "0000/observation.json").read_bytes()
    with pytest.raises(capture.EconomicCaptureError, match="new directory"):
        execute(first, [SOURCES[0]])
    assert before == {str(path.relative_to(first)): path.read_bytes() for path in first.rglob("*") if path.is_file()}
    with pytest.raises(capture.EconomicCaptureError, match="market-state"):
        execute(tmp_path / "decision-state/new", [SOURCES[0]])
