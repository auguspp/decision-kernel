"""Full PDF consumption through existing daily gates, not another source provider."""
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
import socket

import pytest
from pypdf import PdfReader, PdfWriter

from decision_kernel.adapters.pdf_text import extract_pdf_text
from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_question_host as host
from test_stock_daily_question import setup_daily, refresh, rebuild_archive, assert_unspent


REF = "4" * 40
PATH = "research_runs/retained-test/source.pdf"
NOW = "2026-09-20T10:00:00+00:00"
SAVED = "2026-09-20T09:42:00+00:00"


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("retained PDF tests must not access networking")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def reference(raw):
    return once.source_ref(PATH, REF, raw, "RETAINED_PUBLIC_ISSUER_PDF")


class TreeAPI:
    def __init__(self, raw):
        self.calls = []
        self.tree = {"truncated": False, "tree": [{"path": PATH, "type": "blob",
            "mode": "100644", "size": len(raw), "sha": once.blob(raw)}]}
        self.commit = {"sha": REF, "committer": {"date": SAVED}}

    def get(self, endpoint):
        self.calls.append(endpoint)
        if endpoint == "git/trees/" + REF + "?recursive=1":
            return deepcopy(self.tree)
        if endpoint == "git/commits/" + REF:
            return deepcopy(self.commit)
        raise AssertionError(endpoint)

    def file(self, *args):
        raise AssertionError("large PDF must not use the inline Contents body")


@pytest.fixture
def raw_large():
    # Byte-identity fixture only; real PDF parsing is exercised by the host tests.
    return b"%PDF-1.4\n" + b"x" * (1024 * 1024 + 1) + b"\n%%EOF\n"


def test_large_artifact_pdf_uses_exact_git_binding_without_second_body_read(raw_large):
    api = TreeAPI(raw_large)
    actual, saved = daily._retained_pdf(api, reference(raw_large), raw_large, len(raw_large), lambda: NOW)
    assert actual is raw_large and saved == SAVED
    assert api.calls == ["git/trees/" + REF + "?recursive=1", "git/commits/" + REF]


@pytest.mark.parametrize("damage,code", [
    ("missing", "DAILY_PDF_GIT_BINDING_DIFFERS"),
    ("duplicate", "DAILY_PDF_GIT_BINDING_DIFFERS"),
    ("symlink", "DAILY_PDF_GIT_BINDING_DIFFERS"),
    ("executable", "DAILY_PDF_GIT_BINDING_DIFFERS"),
    ("submodule", "DAILY_PDF_GIT_BINDING_DIFFERS"),
    ("size", "DAILY_PDF_GIT_BINDING_DIFFERS"),
    ("blob", "DAILY_PDF_GIT_BINDING_DIFFERS"),
    ("truncated", "DAILY_PDF_TREE_INCOMPLETE"),
    ("oversized-tree", "DAILY_PDF_TREE_INCOMPLETE"),
    ("bad-row", "DAILY_PDF_TREE_INCOMPLETE"),
    ("future-commit", "DAILY_SOURCE_COMMIT_CLOCK"),
    ("wrong-commit", "DAILY_SOURCE_COMMIT_CLOCK"),
])
def test_large_pdf_rejects_unbound_or_unreadable_git_history(raw_large, damage, code):
    api = TreeAPI(raw_large)
    row = api.tree["tree"][0]
    if damage == "missing": api.tree["tree"] = []
    elif damage == "duplicate": api.tree["tree"].append(deepcopy(row))
    elif damage == "symlink": row["mode"] = "120000"
    elif damage == "executable": row["mode"] = "100755"
    elif damage == "submodule": row.update(mode="160000", type="commit")
    elif damage == "size": row["size"] += 1
    elif damage == "blob": row["sha"] = "a" * 40
    elif damage == "truncated": api.tree["truncated"] = True
    elif damage == "oversized-tree": api.tree["tree"] = [row] * 5001
    elif damage == "bad-row": api.tree["tree"].append(None)
    elif damage == "future-commit": api.commit["committer"]["date"] = "2026-09-21T00:00:00Z"
    else: api.commit["sha"] = "a" * 40
    with pytest.raises(once.TrialError) as err:
        daily._retained_pdf(api, reference(raw_large), raw_large, len(raw_large), lambda: NOW)
    assert err.value.code == code


@pytest.mark.parametrize("field,value", [
    ("repository", "other/repository"), ("ref", "main"), ("ref", None),
    ("git_blob", "bad"), ("sha256", None), ("purpose", "MODEL_CONTEXT"),
    ("path", "docs/source.pdf"), ("path", "research_runs/source.json"),
])
def test_large_pdf_is_not_a_generic_large_source_escape(raw_large, field, value):
    api = TreeAPI(raw_large)
    spec = reference(raw_large); spec[field] = value
    with pytest.raises(once.TrialError) as err:
        daily._retained_pdf(api, spec, raw_large, len(raw_large), lambda: NOW)
    assert err.value.code == "DAILY_PDF_SOURCE_REFERENCE" and not api.calls


def test_large_pdf_checks_sha256_not_only_git_blob(raw_large):
    api = TreeAPI(raw_large); spec = reference(raw_large); spec["sha256"] = "0" * 64
    with pytest.raises(once.TrialError) as err:
        daily._retained_pdf(api, spec, raw_large, len(raw_large), lambda: NOW)
    assert err.value.code == "DAILY_PDF_GIT_BINDING_DIFFERS"


@pytest.mark.parametrize("declared", [True, 0, -1, 32 * 1024 * 1024 + 1])
def test_invalid_pdf_size_fails_before_metadata_reads(raw_large, declared):
    api = TreeAPI(raw_large)
    with pytest.raises(once.TrialError) as err:
        daily._retained_pdf(api, reference(raw_large), raw_large, declared, lambda: NOW)
    assert err.value.code == "DAILY_RETAINED_PDF_IDENTITY_OR_SIZE" and not api.calls


def test_actual_pdf_byte_budget_boundary():
    size = daily.POLICY["max_pdf_bytes"]
    raw = b"x" * size; api = TreeAPI(raw)
    assert daily._retained_pdf(api, reference(raw), raw, size, lambda: NOW)[0] is raw
    oversized = raw + b"x"; api = TreeAPI(oversized)
    with pytest.raises(once.TrialError) as err:
        daily._retained_pdf(api, reference(oversized), oversized, len(oversized), lambda: NOW)
    assert err.value.code == "DAILY_RETAINED_PDF_IDENTITY_OR_SIZE" and not api.calls


def test_small_pdf_keeps_original_reader_and_metadata_stays_bounded(monkeypatch):
    called = []; raw = b"small saved PDF fixture"
    def source(api, spec, purpose, clock):
        called.append((spec, purpose)); return raw, SAVED
    monkeypatch.setattr(daily, "_source", source)
    spec = reference(raw)
    assert daily._retained_pdf(None, spec, raw, len(raw), lambda: NOW) == (raw, SAVED)
    assert called == [(spec, "RETAINED_PUBLIC_ISSUER_PDF")]
    assert identity.MAX_BYTES == daily.POLICY["retained_source_file_bytes"] == 512 * 1024
    with pytest.raises(identity.ExecutionIdentityError):
        identity._json(b" " * (identity.MAX_BYTES + 1))


def large_case(tmp_path, monkeypatch, *, route="WAIT_FOR_TRIGGER"):
    case = setup_daily(tmp_path, monkeypatch, route=route)
    record = case.custody["documents"][0]; source = record["pdf_source"]
    original = case.api.files[source["ref"]][source["path"]]
    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(original)).pages: writer.add_page(page)
    writer.add_metadata({"/SyntheticPadding": "x" * (1200 * 1024)})
    out = io.BytesIO(); writer.write(out); pdf = out.getvalue()
    assert 1024 * 1024 < len(pdf) < 2 * 1024 * 1024
    parsed = extract_pdf_text(pdf, max_pdf_bytes=daily.POLICY["max_pdf_bytes"])
    doc = case.context["issuer_documents"][0]; old_hash = doc["pdf_sha256"]
    pages = [{"page_number": p.page_number, "text": p.text} for p in parsed.pages]
    doc.update(pdf_sha256=once.sha(pdf), page_count=parsed.page_count, pages=pages)
    record.update(bytes=len(pdf), pdf_sha256=once.sha(pdf), page_count=parsed.page_count,
        pdf_source=once.source_ref(source["path"], source["ref"], pdf, source["purpose"]))
    case.api.files[source["ref"]][source["path"]] = pdf
    case.pf["reads"][0]["body_sha256"] = once.sha(pdf)
    case.journal["completed_reads"][0]["body_sha256"] = once.sha(pdf)
    case.journal["body_events"][0].update(pdf_sha256=once.sha(pdf), bytes=len(pdf))
    prefix = case.q["case_id"] + "/sources/"
    del case.archive_files[prefix + old_hash + ".pdf"]
    del case.archive_files[prefix + old_hash + "-extraction.json"]
    case.archive_files[prefix + once.sha(pdf) + ".pdf"] = pdf
    case.archive_files[prefix + once.sha(pdf) + "-extraction.json"] = once.raw({
        "pdf_sha256": once.sha(pdf), "source_locator": doc["source_locator"],
        "text_sha256": parsed.text_sha256, "page_count": parsed.page_count, "pages": pages})
    case.archive_files[prefix + "source-journal.json"] = once.raw(case.journal)
    rebuild_archive(case); refresh(case)
    original_file = case.api.file
    def file(path, ref):
        assert path != source["path"], "PDF body must come from the verified source archive"
        return original_file(path, ref)
    monkeypatch.setattr(case.api, "file", file)
    return case


@pytest.mark.parametrize("route,stages", [("STOP", ["pre"]),
    ("WAIT_FOR_TRIGGER", ["pre"]), ("CONTINUE_TO_QUICK", ["pre", "quick"])])
def test_large_pdf_reaches_original_daily_host_routes_without_inline_blob_read(tmp_path, monkeypatch, route, stages):
    case = large_case(tmp_path, monkeypatch, route=route)
    result = host.run_question(**case.args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert case.calls == stages and case.archive_calls == [1020]
    assert result["daily_scope"]["pdf_bytes"] > 1024 * 1024
    assert not result["automatic_retry"] and result["investment_authority"] == "NONE"
    saved = json.loads((case.args["output"] / "input.json").read_bytes())
    assert case.custody["documents"][0]["pdf_source"] in saved["source_refs"]


@pytest.mark.parametrize("damage", ["missing", "changed", "truncated", "probe-run"])
def test_large_pdf_cannot_spend_with_invalid_original_custody(tmp_path, monkeypatch, damage):
    case = large_case(tmp_path, monkeypatch)
    source = case.custody["documents"][0]["pdf_source"]
    if damage == "missing": del case.api.files[source["ref"]][source["path"]]
    elif damage == "changed": case.api.files[source["ref"]][source["path"]] += b"changed"
    elif damage == "probe-run": case.source_run["path"] = ".github/workflows/isolated-probe.yml"
    else:
        original_get = case.api.get
        def get(path):
            value = original_get(path)
            if path == "git/trees/" + source["ref"] + "?recursive=1": value["truncated"] = True
            return value
        monkeypatch.setattr(case.api, "get", get)
    result = host.run_question(**case.args); assert_unspent(case, result)
    expected = ("DAILY_SOURCE_RUN_IDENTITY" if damage == "probe-run" else
                "DAILY_PDF_TREE_INCOMPLETE" if damage == "truncated" else "DAILY_PDF_GIT_BINDING_DIFFERS")
    assert result["error_code"] == expected
