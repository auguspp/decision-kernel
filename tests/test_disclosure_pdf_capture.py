"""Original packet/CLI with synthetic transport; never a real Research execution."""
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from pypdf import PdfWriter

from decision_kernel import cli
from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.adapters.pdf_text import extract_pdf_text
from decision_kernel.research import ResearchSnapshot
from decision_kernel.runtime import cninfo_http
from decision_kernel.runtime.disclosure_assessment import (
    parse_disclosure_assessment_packet, prepare_disclosure_assessment_packet,
    serialize_disclosure_assessment_packet,
)
from decision_kernel.runtime.disclosure_pdf_capture import DisclosurePdfCapture
from decision_kernel.runtime.disclosure_radar import DisclosureBatch

AT = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)
URL = "https://static.cninfo.com.cn/finalpage/2026-09-08/synthetic.PDF"


def pdf():
    writer = PdfWriter(); writer.add_blank_page(width=72, height=72)
    output = io.BytesIO(); writer.write(output)
    return output.getvalue()


def snapshot():
    return ResearchSnapshot(id=UUID(int=1), ticker="603986", company_name="Synthetic",
        exchange="SSE", currency="CNY", created_at="2026-09-01T00:00:00Z",
        as_of_datetime="2026-09-01T00:00:00Z", valuation_horizon_date="2027-09-01",
        version=1, core_thesis="Synthetic monitoring question", created_by="test")


def announcement():
    return CninfoAnnouncement(announcement_id="synthetic", stock_code="603986", org_id="test",
        title="Synthetic announcement", announcement_type=None,
        published_at=datetime(2026, 9, 8, tzinfo=timezone.utc), source_locator=URL)


def batch():
    a = announcement()
    return DisclosureBatch(stock_code=a.stock_code, publication_date=a.published_at.date(),
        first_published_at=a.published_at, last_published_at=a.published_at, announcements=(a,))


def test_same_bytes_and_packet_identity_with_or_without_capture(tmp_path):
    raw = pdf(); calls = []
    def fetch(**kwargs):
        calls.append(kwargs); return raw
    capture = DisclosurePdfCapture(tmp_path / "raw", fetch_pdf=fetch)
    kwargs = dict(research_snapshot=snapshot(), batch=batch(), prepared_at=AT)
    original = prepare_disclosure_assessment_packet(**kwargs, fetch_pdf=fetch)
    retained = prepare_disclosure_assessment_packet(**kwargs, fetch_pdf=capture.fetch)
    assert serialize_disclosure_assessment_packet(original) == serialize_disclosure_assessment_packet(retained)
    assert len(calls) == 2  # One per invocation; capture adds no source request.
    stored = parse_disclosure_assessment_packet(serialize_disclosure_assessment_packet(retained))
    assert stored.evidence[0].text_status.value == "NO_TEXT"
    assert stored.evidence[0].evidence_artifact.retention_mode == original.evidence[0].evidence_artifact.retention_mode
    assert stored.evidence[0].evidence_artifact.raw_storage_ref == original.evidence[0].evidence_artifact.raw_storage_ref
    capture.complete()
    rows = [json.loads(s) for s in (capture.root / "manifest.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["source_locator"] == URL
    assert rows[0]["pdf_sha256"] == hashlib.sha256(raw).hexdigest()
    assert (capture.root / rows[0]["path"]).read_bytes() == raw
    summary = json.loads((capture.root / "capture-summary.json").read_text())
    assert summary["returned_pdf_reads"] == 1 and summary["unique_pdf_objects"] == 1
    assert summary["investment_authority"] == "NONE"
    assert summary["manifest_sha256"] == hashlib.sha256((capture.root/"manifest.jsonl").read_bytes()).hexdigest()


def test_extraction_failure_preserves_original_without_completion(tmp_path):
    raw = pdf()
    capture = DisclosurePdfCapture(tmp_path/"raw", fetch_pdf=lambda **kw: raw)
    def fail(_raw):
        assert _raw is raw
        raise ValueError("synthetic extraction failure")
    with pytest.raises(ValueError, match="extraction failure"):
        prepare_disclosure_assessment_packet(research_snapshot=snapshot(), batch=batch(), prepared_at=AT,
                                            fetch_pdf=capture.fetch, extract_pdf=fail)
    assert next((capture.root/"objects").iterdir()).read_bytes() == raw
    assert not (capture.root/"capture-summary.json").exists()


def test_second_fetch_failure_keeps_first_without_retry(tmp_path):
    raw = pdf(); calls = []
    def fetch(**kw):
        calls.append(kw)
        if len(calls) == 2: raise cninfo_http.CninfoRuntimeError("synthetic HTTP 429")
        return raw
    capture = DisclosurePdfCapture(tmp_path/"raw", fetch_pdf=fetch)
    capture.fetch(source_locator=URL)
    with pytest.raises(cninfo_http.CninfoRuntimeError, match="429"):
        capture.fetch(source_locator=URL)
    assert len(calls) == 2 and capture.reads == 1
    assert len((capture.root/"manifest.jsonl").read_text().splitlines()) == 1
    assert not (capture.root/"capture-summary.json").exists()


def test_repeated_body_reuses_local_object_but_preserves_each_return(tmp_path):
    raw = pdf(); capture = DisclosurePdfCapture(tmp_path/"raw", fetch_pdf=lambda **kw: raw)
    for suffix in ("one", "two"):
        assert capture.fetch(source_locator=URL+suffix) is raw
    assert len(list((capture.root/"objects").iterdir())) == 1
    rows = [json.loads(s) for s in (capture.root/"manifest.jsonl").read_text().splitlines()]
    assert [r["sequence"] for r in rows] == [1, 2]
    assert rows[0]["source_locator"] != rows[1]["source_locator"]


def test_existing_directory_is_never_overwritten(tmp_path):
    root = tmp_path/"raw"; root.mkdir(); marker = root/"existing"; marker.write_text("preserve")
    with pytest.raises(FileExistsError): DisclosurePdfCapture(root)
    assert marker.read_text() == "preserve"


@pytest.mark.parametrize("payload", [b"not a pdf", "not bytes", b"%PDF-" + b"x"*16])
def test_original_byte_limits_and_header_not_relaxed(tmp_path, monkeypatch, payload):
    from decision_kernel.runtime import disclosure_pdf_capture as module
    monkeypatch.setattr(module, "MAX_PDF_BYTES", 16)
    capture = DisclosurePdfCapture(tmp_path/"raw", fetch_pdf=lambda **kw: payload)
    with pytest.raises(ValueError, match="bounded PDF bytes"): capture.fetch(source_locator=URL)
    assert capture.reads == 0


def test_existing_corrupt_or_linked_object_is_not_followed(tmp_path):
    raw = pdf(); capture = DisclosurePdfCapture(tmp_path/"raw", fetch_pdf=lambda **kw: raw)
    target = capture.root/"objects"/(hashlib.sha256(raw).hexdigest()+".pdf")
    target.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="bytes changed"): capture.fetch(source_locator=URL)
    target.unlink(); outside = tmp_path/"outside"; outside.write_bytes(b"keep")
    target.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"): capture.fetch(source_locator=URL)
    assert outside.read_bytes() == b"keep"


def test_completed_capture_cannot_append_or_finish_again(tmp_path):
    capture = DisclosurePdfCapture(tmp_path/"raw", fetch_pdf=lambda **kw: pdf())
    capture.complete()
    with pytest.raises(ValueError, match="completed"): capture.complete()
    with pytest.raises(ValueError, match="completed"): capture.fetch(source_locator=URL)


def run_cli(tmp_path, monkeypatch, extra, *, fail_extract=False):
    package = tmp_path/"input.json"; package.write_text("{}")
    monkeypatch.setattr(cli, "_research_snapshot_from_raw_package", lambda raw: snapshot())
    a = announcement()
    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", lambda **kw:
        cninfo_http.CninfoDisclosureBatch(stock_code="603986", org_id="test", start_date=AT.date(),
                                        end_date=AT.date(), announcements=(a,)))
    calls = []
    raw = pdf()
    def fetch(**kw): calls.append(kw); return raw
    monkeypatch.setattr(cninfo_http, "fetch_cninfo_pdf_bytes", fetch)
    original = cli.prepare_disclosure_assessment_packet
    def prepare(**kw):
        def fail(_): raise ValueError("synthetic extraction failure")
        kw.setdefault("fetch_pdf", fetch)
        return original(**kw, extract_pdf=fail if fail_extract else extract_pdf_text)
    monkeypatch.setattr(cli, "prepare_disclosure_assessment_packet", prepare)
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["scan-disclosures", str(package), "--through", "2026-09-09", *extra], stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue(), calls


def test_real_cli_retains_source_without_changing_packet_count(tmp_path, monkeypatch):
    raw, packets = tmp_path/"raw", tmp_path/"packets"
    code, out, err, calls = run_cli(tmp_path, monkeypatch,
        ["--packet-dir", str(packets), "--raw-pdf-dir", str(raw)])
    assert code == 0 and not err and len(calls) == 1
    assert "ASSESSMENT PACKETS: 1 prepared" in out
    assert len(list(packets.glob("*.json"))) == 1
    assert (raw/"capture-summary.json").exists()


def test_cli_failure_leaves_raw_but_never_claims_quiet_or_complete(tmp_path, monkeypatch):
    raw, packets = tmp_path/"raw", tmp_path/"packets"
    code, out, err, calls = run_cli(tmp_path, monkeypatch,
        ["--packet-dir", str(packets), "--raw-pdf-dir", str(raw)], fail_extract=True)
    assert code != 0 and "extraction failure" in err and len(calls) == 1
    assert "QUIET" not in out and "ASSESSMENT PACKETS:" not in out
    assert not (raw/"capture-summary.json").exists()
    assert list((raw/"objects").glob("*.pdf"))
    assert not packets.exists()


@pytest.mark.parametrize("kind", ["no-packets", "same", "nested-raw", "nested-packets", "existing"])
def test_bad_capture_paths_fail_before_source_calls(tmp_path, monkeypatch, kind):
    raw, packets = tmp_path/"raw", tmp_path/"packets"
    if kind == "same": raw = packets
    if kind == "nested-raw": raw = packets/"raw"
    if kind == "nested-packets": packets = raw/"packets"
    if kind == "existing": raw.mkdir()
    extra = ["--raw-pdf-dir", str(raw)]
    if kind != "no-packets": extra += ["--packet-dir", str(packets)]
    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", lambda **kw: pytest.fail("unexpected scan"))
    source = tmp_path/"unused.json"; source.write_text("{}")
    out, err = io.StringIO(), io.StringIO()
    assert cli.main(["scan-disclosures",str(source),"--through","2026-09-09",*extra],stdout=out,stderr=err) != 0
    assert "ERROR" in err.getvalue().upper()


def test_legacy_cli_without_capture_keeps_old_path(tmp_path, monkeypatch):
    code, out, err, calls = run_cli(tmp_path, monkeypatch, ["--packet-dir",str(tmp_path/"packets")])
    assert code == 0 and len(calls) == 1 and not (tmp_path/"raw").exists()


def test_workflow_keeps_original_artifact_separate_and_preserves_partial_bodies():
    source = Path(".github/workflows/decision-inbox.yml").read_text()
    assert source.count("--raw-pdf-dir disclosure-primary-bodies") == 1
    original = source.split("- name: Upload disclosure scan and assessment handoffs", 1)[1].split("- name: Upload already-fetched", 1)[0]
    assert "if: success()" in original and "name: official-disclosure-scan" in original
    assert "disclosure-primary-bodies" not in original
    capture = source.split("- name: Upload already-fetched disclosure PDF bodies", 1)[1]
    assert "if: always()" in capture and "name: official-disclosure-primary-bodies" in capture
    assert "retention-days: 14" in capture and "continue-on-error" not in capture
    assert "overwrite:" not in capture and "secrets." not in capture
    assert 'cron: "20 8 * * 1-5"' in source
