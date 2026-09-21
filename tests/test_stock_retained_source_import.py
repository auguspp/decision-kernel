"""Historical source import through native daily gates; no live source/model I/O."""
from copy import deepcopy
import json
import socket

import pytest

from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_retained_source_import as imported
from test_stock_daily_question import setup_daily, rebuild_archive, refresh, assert_unspent


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("source import tests are offline")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def setup_import(tmp_path, monkeypatch, route="WAIT_FOR_TRIGGER"):
    case = setup_daily(tmp_path, monkeypatch, route=route)
    doc = case.context["issuer_documents"][0]
    prefix = case.q["case_id"] + "/sources/"
    pdf = case.archive_files[prefix + doc["pdf_sha256"] + ".pdf"]
    extraction = json.loads(case.archive_files[prefix + doc["pdf_sha256"] + "-extraction.json"])
    case.source_run.update(path=".github/workflows/fixture-source-capture.yml",
                          event="push", head_branch="fixture-capture")
    row = case.inventory["announcements"][0]
    def entry(name, raw):
        return {"path": name, "bytes": len(raw), "sha256": once.sha(raw)}
    raw_files = {"source.pdf": pdf, "inventory.json": once.raw(case.inventory),
                 "extraction.json": once.raw(extraction), "query-1.json": b"[]"}
    receipt = {"target": {"ticker": case.q["ticker"], "announcement_id": doc["announcement_id"],
        "title": doc["title"], "code_commit": case.args["code"]},
        "run_id": str(case.source_run["id"]), "workflow_commit": case.source_run["head_sha"],
        "status": "EXACT_REPORT_RETAINED_NOT_RESEARCH_ADMITTED", "research_execution": "NOT_EXECUTED",
        "model_calls": 0, "automatic_retry": False, "investment_authority": "NONE",
        "started_at": case.source_run["run_started_at"], "pdf_started_at": case.source_run["run_started_at"],
        "pdf_finished_at": doc["retrieved_at"], "finished_at": "2026-09-20T09:46:00+00:00",
        "selected": row, "pdf": entry("source.pdf", pdf), "page_count": doc["page_count"],
        "inventory": entry("inventory.json", raw_files["inventory.json"]),
        "extraction": entry("extraction.json", raw_files["extraction.json"]),
        "query_events": [{"source": entry("query-1.json", b"[]")} ]}
    raw_files["receipt.json"] = once.raw(receipt)
    saved = {n: {**once.source_ref("research_runs/import-fixture/" + n, "7" * 40, raw,
        "RETAINED_PUBLIC_ISSUER_PDF" if n.endswith(".pdf") else "RETAINED_CAPTURE_DATA"),
        "bytes": len(raw)} for n, raw in raw_files.items()}
    case.api.files["7" * 40] = {saved[n]["path"]: b for n, b in raw_files.items()}
    case.commits["7" * 40] = {"sha": "7" * 40, "committer": {"date": "2026-09-20T09:50:00+00:00"}}
    case.custody["documents"][0]["pdf_source"] = {k: v for k, v in saved["source.pdf"].items() if k != "bytes"}
    case.custody["source_import"] = "fixture-import"
    profile = {"enabled": True, "format": imported.FORMAT, "case_id": case.q["case_id"],
        "announcement_id": doc["announcement_id"], "capture_code": case.args["code"],
        "run": {k: case.source_run[k] for k in ("id", "path", "head_branch", "head_sha", "event")},
        "files": saved}
    case.journal = json.loads(imported.project(profile, raw_files)[prefix + "source-journal.json"])
    case.archive_files = raw_files
    rebuild_archive(case)
    profile["artifact"] = deepcopy(case.custody["source_artifact"])
    case.profile = profile
    case.imports = {"schema_version": 1, "imports": {"fixture-import": profile}}
    case.api.files[case.args["code"]][imported.IMPORTS_PATH] = once.raw(case.imports)
    refresh(case)
    return case


def test_projection_preserves_original_bytes_and_acquisition_time(tmp_path, monkeypatch):
    case = setup_import(tmp_path, monkeypatch)
    original = deepcopy(case.archive_files)
    result = imported.project(case.profile, case.archive_files)
    prefix = case.q["case_id"] + "/sources/"
    pdf_hash = case.context["issuer_documents"][0]["pdf_sha256"]
    assert result[prefix + pdf_hash + ".pdf"] is case.archive_files["source.pdf"]
    journal = json.loads(result[prefix + "source-journal.json"])
    assert journal["provenance"] == imported.PROVENANCE and journal["new_source_requests"] == 0
    assert journal["original_source_run"]["event"] == "push"
    assert journal["body_events"][0]["captured_at"] == case.source_run["run_started_at"]
    assert case.archive_files == original and not case.calls and not case.writes


@pytest.mark.parametrize("route,stages", [("STOP", ["pre"]), ("WAIT_FOR_TRIGGER", ["pre"]),
                                         ("CONTINUE_TO_QUICK", ["pre", "quick"])])
def test_import_reaches_original_host_routes(tmp_path, monkeypatch, route, stages):
    case = setup_import(tmp_path, monkeypatch, route)
    result = host.run_question(**case.args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert case.calls == stages and case.archive_calls == [1020]
    packet = json.loads((case.args["output"] / "input.json").read_bytes())
    assert any(s["path"] == imported.IMPORTS_PATH for s in packet["source_refs"])
    assert result["daily_scope"]["source_custody_source"] == case.request["source_custody_source"]


@pytest.mark.parametrize("damage,error", [
    ("unlisted", "DAILY_IMPORT_NOT_REVIEWED"), ("disabled", "DAILY_IMPORT_PROFILE_BINDING"),
    ("wrong-run", "DAILY_IMPORT_RUN_IDENTITY"), ("foreign-repository", "DAILY_IMPORT_RUN_IDENTITY"),
    ("rerun", "DAILY_IMPORT_RUN_IDENTITY"), ("expired", "DAILY_IMPORT_ARTIFACT_IDENTITY"),
    ("artifact-digest", "DAILY_IMPORT_ARTIFACT_IDENTITY"), ("altered-source", "DAILY_IMPORT_FILE_BYTES"),
    ("altered-git-copy", "EXECUTION_SOURCE_BLOB_MISMATCH"),
    ("changed-journal", "DAILY_SOURCE_ARTIFACT_COPIES_DIFFER"), ("late-run", "DAILY_IMPORT_RUN_CLOCK")])
def test_bad_import_never_reserves_or_calls(tmp_path, monkeypatch, damage, error):
    case = setup_import(tmp_path, monkeypatch)
    if damage == "unlisted": case.custody["source_import"] = "not-reviewed"
    elif damage == "disabled": case.profile["enabled"] = False
    elif damage == "wrong-run": case.source_run["path"] = ".github/workflows/unreviewed.yml"
    elif damage == "foreign-repository": case.source_run["head_repository"]["full_name"] = "other/repo"
    elif damage == "rerun": case.source_run["run_attempt"] = 2
    elif damage == "expired": case.artifact["expired"] = True
    elif damage == "artifact-digest": case.artifact["digest"] = "sha256:" + "a" * 64
    elif damage == "altered-source":
        case.archive_files["source.pdf"] += b"changed"
        rebuild_archive(case)
        case.profile["artifact"] = deepcopy(case.custody["source_artifact"])
    elif damage == "altered-git-copy":
        path = case.profile["files"]["receipt.json"]["path"]
        case.api.files["7" * 40][path] += b" "
    elif damage == "changed-journal": case.journal["body_events"][0]["captured_at"] = "2026-09-20T09:45:00Z"
    else: case.source_run["updated_at"] = "2026-09-21T09:46:00Z"
    case.api.files[case.args["code"]][imported.IMPORTS_PATH] = once.raw(case.imports)
    refresh(case)
    result = host.run_question(**case.args)
    assert_unspent(case, result)
    assert result.get("error_code") == error, result


def label_env():
    return {"GITHUB_EVENT_NAME": "issues", "GITHUB_WORKFLOW": "stock-business-research",
            "DAILY_EVENT_ACTION": "labeled", "DAILY_ISSUE_NUMBER": "297",
            "DAILY_LABEL": daily.READY_LABEL, "DAILY_SENDER": "auguspp",
            "DAILY_IS_PULL_REQUEST": "false"}


def test_explicit_daily_label_transport_is_not_permission():
    assert daily.label_transport(label_env()) is True
    assert daily.PERMISSION["comment_id"] == 5748820065


@pytest.mark.parametrize("field", list(label_env()))
def test_other_issue_event_cannot_enter_daily_transport(field):
    env = label_env(); env[field] = "wrong"
    assert daily.label_transport(env) is False


def test_unbound_import_profile_is_rejected(tmp_path, monkeypatch):
    case = setup_import(tmp_path, monkeypatch)
    del case.profile["run"]["path"]
    case.api.files[case.args["code"]][imported.IMPORTS_PATH] = once.raw(case.imports)
    result = host.run_question(**case.args)
    assert_unspent(case, result)
    assert result["error_code"] == "DAILY_IMPORT_RUN_PROFILE"
