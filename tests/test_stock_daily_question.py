"""Daily host round trips with real gates, PDF extraction and create-only retention.

GitHub replies and model responses are synthetic. The permission body is the
recorded public policy, not new Human permission or a live Research acceptance.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import socket
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5
import zipfile

import pytest

from decision_kernel.adapters.pdf_text import extract_pdf_text
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as reading
from decision_kernel.runtime import reviewed_question_reading as reader
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_question_continuation as deepseek
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_research_intake as intake
from test_pdf_text import _pdf_with_text_pages
from test_reviewed_question_reading import collector, report
from test_saved_research_once import pre, quick
from test_stock_question_host import setup_question
import test_stock_research_host as original_fixture


ROOT = Path(__file__).parents[1]
FIXED_NOW = datetime(2026, 9, 20, 10, tzinfo=timezone.utc)
PDF_ID = "1234567890"
PDF_TEXT = "600184 Synthetic retained public issuer funding body. Approval is not expenditure."


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("daily question tests must not access networking")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def _put(case, key, body):
    previous = case.request[key]
    raw = once.raw(body)
    source = once.source_ref(previous["path"], previous["ref"], raw, previous["purpose"])
    case.request[key] = source
    case.api.files[source["ref"]][source["path"]] = raw
    return source


def refresh(case):
    """Save changed synthetic evidence and all dependent exact-byte references."""
    context_source = _put(case, "context_source", case.context)
    execution_id = host.question_execution(case.q["security_id"], case.q["question_id"])[0]
    case.pf["seed_publications"] = [{
        "evidence_id": str(uuid5(NAMESPACE_URL, execution_id + ":" + context_source["sha256"])),
        "kind": "GIT_COMMIT", "source": context_source,
    }]
    question_source = _put(case, "question_source", case.q)
    _put(case, "preflight_source", case.pf)
    case.review.update(reading_source=case.q["reading_source"], question_source=question_source)
    _put(case, "batch_review_source", case.review)
    for key, value in (("inventory_source", case.inventory), ("journal_source", case.journal)):
        previous = case.custody[key]
        raw = once.raw(value)
        case.custody[key] = once.source_ref(previous["path"], previous["ref"], raw, previous["purpose"])
        case.api.files[previous["ref"]][previous["path"]] = raw
    case.custody["context"] = context_source
    _put(case, "source_custody_source", case.custody)
    case.api.files[case.args["code"]][daily.REQUEST] = once.raw(case.request)


def rebuild_archive(case):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as out:
        for path, raw in sorted(case.archive_files.items()):
            out.writestr(zipfile.ZipInfo(path, date_time=(2026, 9, 20, 9, 46, 0)), raw)
    case.archive_bytes = archive.getvalue()
    case.artifact.update(size_in_bytes=len(case.archive_bytes), digest="sha256:" + once.sha(case.archive_bytes))
    case.custody["source_artifact"] = {key: case.artifact[key] for key in ("id", "name", "size_in_bytes", "digest")}
    case.custody["source_artifact"]["head_sha"] = case.source_run["head_sha"]


def setup_daily(tmp_path, monkeypatch, *, route="WAIT_FOR_TRIGGER", at=FIXED_NOW):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return at.astimezone(tz) if tz else at.replace(tzinfo=None)

    monkeypatch.setattr(original_fixture, "datetime", FixedDatetime)
    args, api, request, q, context, pf, calls, writes, prefix = setup_question(tmp_path, monkeypatch)
    args["daily"] = True
    stamp = reading.clock(args["clock"]())
    earlier = lambda minutes: (stamp - timedelta(minutes=minutes)).isoformat()
    permission_body = (ROOT / "tests/fixtures/stock_daily_question_permission.txt").read_text().removesuffix("\n")
    assert once.sha(permission_body.encode()) == daily.PERMISSION["body_sha256"]
    api.comment.update(id=daily.PERMISSION["comment_id"], body=permission_body,
                       created_at=daily.PERMISSION["created_at"])
    request.update(mode=daily.MODE, permission=deepcopy(daily.PERMISSION), approved_egress_hash=None)
    api.files[args["code"]][daily.POLICY_PATH] = once.raw(daily.POLICY)

    run = {
        "id": 101, "repository": {"full_name": once.REPO}, "head_repository": {"full_name": once.REPO},
        "path": reading.WORKFLOWS["stock"], "head_branch": "main", "head_sha": "9" * 40,
        "event": "schedule", "run_attempt": 1, "status": "completed", "conclusion": "success",
        "created_at": "2026-09-18T10:00:00Z", "run_started_at": "2026-09-18T10:00:01Z",
        "updated_at": "2026-09-18T10:05:00Z", "html_url": "https://github.com/auguspp/decision-kernel/actions/runs/101",
    }
    rows = [
        {"thscode": "600184.SH", "company_name": "Synthetic selected issuer",
         "status": "CONTRACT_CHECKED_RAW_READING", "input_failure": None,
         "eligible_for_shadow_reading": True, "excluded_reasons": []},
        {"thscode": "600127.SH", "company_name": "Synthetic unavailable issuer", "status": "UNAVAILABLE",
         "input_failure": {"reason_code": "CURRENT_QUOTE_HISTORY_MISMATCH"},
         "eligible_for_shadow_reading": False, "excluded_reasons": ["DATA_UNAVAILABLE"]},
        {"thscode": "000019.SZ", "company_name": "Synthetic price disposition", "status": "CONDITIONS_NOT_MET",
         "input_failure": None, "eligible_for_shadow_reading": False, "excluded_reasons": ["PRICE_CONDITION"]},
    ]
    projection = {"market_session": "2026-09-18", "all_stock_observations": deepcopy(rows)}
    detail = once.raw({"projection": projection, "projection_hash": canonical_hash(projection)})
    read_ref = q["reading_source"]["ref"]
    detail_path = "details/stock/reading/stock-reading.json"
    api.files[read_ref][detail_path] = detail
    stock = {"market_session": "2026-09-18", "observed_at": "2026-09-18T10:04:00Z",
        "validation": "EXISTING_PURE_READING_VALIDATOR_AND_CAPTURE_INVENTORY_NOT_NEW_LIVE_RUN",
        "coverage": {"planned_issuers": 3, "qualified_issuers": 1}, "dispositions": rows,
        "projection_hash": canonical_hash(projection), "archive": {"origin_run": reading.concise_run(run)},
        "details": {"reading/stock-reading.json": {"read_path": detail_path, "bytes": len(detail),
            "sha256": once.sha(detail), "git_blob": once.blob(detail),
            "read_ref_rule": "USE_THE_SAME_PINNED_READING_COMMIT"}}}
    state = reading.assemble(code_commit=args["code"], checked_at=earlier(30), check_started_at=earlier(31),
        lanes={"stock": {"health": "LATEST_ATTEMPT_SUCCEEDED", "gaps": [], "last_qualified_result": stock}},
        research={"handoffs": {"active": []}, "stock_business_work": {"status": "READ_OK", "items": []}},
        capabilities=[], refresh_identity={})
    api.files[read_ref]["current-state.json"] = once.raw(state)
    q["reading_source"] = once.source_ref("current-state.json", read_ref, once.raw(state), "SAVED_QUESTION_READING")
    q["origins"][0].update(source=once.source_ref(detail_path, read_ref, detail, "SAVED_STOCK_BATCH_ORIGIN"),
                           observed_at=stock["observed_at"])

    pdf = _pdf_with_text_pages(PDF_TEXT)
    parsed = extract_pdf_text(pdf)
    doc = context["issuer_documents"][0]
    doc.update(announcement_id=PDF_ID, source_locator=f"https://static.cninfo.com.cn/finalpage/2026-09-18/{PDF_ID}.PDF",
               pdf_sha256=once.sha(pdf), page_count=parsed.page_count,
               pages=[{"page_number": p.page_number, "text": p.text} for p in parsed.pages])
    pf["reads"][0].update(identity="600184:" + PDF_ID, locator=doc["source_locator"], body_sha256=doc["pdf_sha256"])
    pdf_source = once.source_ref("research_runs/daily-test/source.pdf", "4" * 40, pdf, "RETAINED_PUBLIC_ISSUER_PDF")
    api.files[pdf_source["ref"]] = {pdf_source["path"]: pdf}
    review = {"reading_source": q["reading_source"], "question_source": request["question_source"],
        "batch_id": reader.stock_review_scope(state)["batch_id"], "reviewed_at": earlier(8),
        "items": [{"thscode": row["thscode"], "disposition": disposition, "reason": reason}
            for row, disposition, reason in zip(rows, (
                "SELECTED_NEW_DISTINCT_QUESTION", "DATA_UNAVAILABLE", "ORIGINAL_PRICE_DISPOSITION_ONLY"), (
                "Synthetic distinct funding question; baseline does not answer it.",
                "Saved quote/history mismatch remains unavailable.", "Saved price condition remains unmet."), strict=True)]}
    inventory = {"stock_code": q["ticker"], "org_id": "synthetic-org", "announcements": [{
        "announcement_id": PDF_ID, "stock_code": q["ticker"], "org_id": "synthetic-org",
        "title": doc["title"], "source_locator": doc["source_locator"], "published_at": doc["published_at"]}]}
    journal = {"completed_reads": deepcopy(pf["reads"]), "body_events": [{"announcement_id": PDF_ID, "source_locator": doc["source_locator"],
        "status": "FORMAT_AND_IDENTITY_CHECKED_NOT_TRUTH", "pdf_sha256": doc["pdf_sha256"],
        "bytes": len(pdf), "captured_at": earlier(16), "finished_at": earlier(14)}]}
    inventory_source = once.source_ref("research_runs/daily-test/inventory.json", "5" * 40,
        once.raw(inventory), "RETAINED_CNINFO_ISSUER_INVENTORY")
    journal_source = once.source_ref("research_runs/daily-test/journal.json", "6" * 40,
        once.raw(journal), "RETAINED_CNINFO_SOURCE_JOURNAL")
    for source, value in ((inventory_source, inventory), (journal_source, journal)):
        api.files[source["ref"]] = {source["path"]: once.raw(value)}
    custody = {"context": request["context_source"], "checked_at": earlier(7), "ticker": q["ticker"],
        "source_run_id": 102,
        "inventory_source": inventory_source, "journal_source": journal_source, "documents": [{
        "announcement_id": PDF_ID, "pdf_source": pdf_source, "bytes": len(pdf),
        "pdf_sha256": once.sha(pdf), "page_count": parsed.page_count}]}
    for key, ref, body in (("batch_review_source", "2" * 40, review), ("source_custody_source", "3" * 40, custody)):
        path = "research_runs/daily-test/" + key + ".json"
        request[key] = once.source_ref(path, ref, once.raw(body), daily.EXTRA_SOURCES[key])
        api.files[ref] = {path: once.raw(body)}
    commits = {ref: {"sha": ref, "committer": {"date": earlier(minutes)}}
               for ref, minutes in (("2" * 40, 6), ("3" * 40, 6), ("4" * 40, 18),
                                    ("5" * 40, 14), ("6" * 40, 14))}
    source_run = {**deepcopy(run), "id": 102, "path": ".github/workflows/stock-business-research.yml",
        "event": "workflow_dispatch", "head_sha": "8" * 40,
        "created_at": earlier(17), "run_started_at": earlier(16), "updated_at": earlier(13)}
    artifact = {"id": 1020, "name": "stock-source-preparation-102-1", "expired": False,
        "workflow_run": {"id": 102, "head_sha": source_run["head_sha"]}}
    artifacts = [artifact]
    source_prefix = q["case_id"] + "/sources/"
    archive_files = {source_prefix + "inventory.json": once.raw(inventory),
        source_prefix + "source-journal.json": once.raw(journal),
        source_prefix + doc["pdf_sha256"] + ".pdf": pdf,
        source_prefix + doc["pdf_sha256"] + "-extraction.json": once.raw({
            "pdf_sha256": doc["pdf_sha256"], "source_locator": doc["source_locator"],
            "text_sha256": parsed.text_sha256, "page_count": parsed.page_count, "pages": doc["pages"]})}
    original_get = api.get
    def get(path):
        if path == "actions/runs/101":
            return deepcopy(run)
        if path == "actions/runs/102":
            return deepcopy(source_run)
        if path == "actions/runs/102/artifacts?per_page=100":
            return {"total_count": len(artifacts), "artifacts": deepcopy(artifacts)}
        if path.startswith("git/commits/") and path.removeprefix("git/commits/") in commits:
            return deepcopy(commits[path.removeprefix("git/commits/")])
        return original_get(path)
    api.get = get

    def call(stage, prompt, model, output, usage):
        calls.append(stage)
        return pre(prompt, route) if stage == "pre" else quick(prompt)
    args["call"] = call
    case = SimpleNamespace(args=args, api=api, request=request, q=q, context=context, pf=pf,
        calls=calls, writes=writes, prefix=prefix, state=state, stock=stock, projection=projection,
        review=review, custody=custody, run=run, pdf=pdf, commits=commits, inventory=inventory, journal=journal,
        source_run=source_run, artifact=artifact, artifacts=artifacts, archive_files=archive_files, archive_calls=[])
    def archive(requested):
        case.archive_calls.append(requested["id"])
        return case.archive_bytes
    api.archive = archive
    rebuild_archive(case)
    refresh(case)
    return case


@pytest.mark.parametrize("route,stages", [
    ("WAIT_FOR_TRIGGER", ["pre"]), ("STOP", ["pre"]), ("CONTINUE_TO_QUICK", ["pre", "quick"]),
])
def test_daily_native_gates_preserve_original_routes_and_before_egress_reservations(tmp_path, monkeypatch, route, stages):
    case = setup_daily(tmp_path, monkeypatch, route=route)
    original_call = case.args["call"]
    def call(*args):
        saved = case.api.files[case.api.heads[intake.WORK_REF]]
        assert daily.PREFIX + "slots/01/prepare.json" in saved
        assert daily.PREFIX + "days/2026-09-18/prepare.json" in saved
        assert case.prefix + "prepare.json" in saved and case.prefix + "launch.json" in saved
        return original_call(*args)
    case.args["call"] = call
    result = host.run_question(**case.args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert case.calls == stages
    assert result["formal_research_started"] and not result["mutation_uncertain"]
    assert result["investment_authority"] == "NONE" and not result["registered_current_handoff"]
    saved = case.api.files[case.api.heads[intake.WORK_REF]]
    launch = json.loads(saved[case.prefix + "launch.json"])
    assert launch["provider"] == daily.POLICY["provider"] and launch["permission"] == daily.PERMISSION
    assert len(launch["daily_reservations"]) == 2
    assert launch["daily_scope"]["reviewed_items"] == case.review["items"]
    assert len(launch["approved_egress_hash"]) == 64
    assert json.loads(saved[case.prefix + "admission.json"])["research_execution_allowed"] is True
    packet = json.loads(saved[case.prefix + "input.json"])
    assert case.custody["documents"][0]["pdf_source"] in packet["source_refs"]
    assert case.request["batch_review_source"] in packet["source_refs"]
    assert case.request["source_custody_source"] in packet["source_refs"]
    assert case.archive_calls == [1020]


def test_daily_checked_main_policy_and_disabled_request_match_recorded_scope():
    from decision_kernel.runtime import industry_daily_question as industry
    assert json.loads((ROOT / daily.POLICY_PATH).read_bytes()) == daily.POLICY
    request = json.loads((ROOT / daily.REQUEST).read_bytes())
    # Deployment can select either existing approved family, without freezing
    # yesterday's ticker/path as permanent policy. Configuration is not a run.
    assert request["enabled"] is True and request["mode"] == daily.MODE
    review_purpose = request["batch_review_source"]["purpose"]
    permissions = {daily.EXTRA_SOURCES["batch_review_source"]: daily.PERMISSION,
                   industry.PURPOSE: industry.PERMISSION}
    assert request["permission"] == permissions[review_purpose] and request["approved_egress_hash"] is None
    assert daily.base_request(request)["mode"] == host.QUESTION_MODE
    for key in ("question_source", "context_source", "preflight_source", *daily.EXTRA_SOURCES):
        spec = request[key]
        assert set(spec) == {"repository", "ref", "path", "git_blob", "sha256", "purpose"}
        assert spec["repository"] == once.REPO and reading.SHA.fullmatch(spec["ref"])
        assert reading.SHA.fullmatch(spec["git_blob"]) and len(spec["sha256"]) == 64
        assert spec["path"].startswith("research_runs/") and reading.safe_path(spec["path"]) == spec["path"]
    assert request["question_source"]["purpose"] == "REVIEWED_RADAR_QUESTION"
    assert request["context_source"]["purpose"] == "MODEL_CONTEXT"
    assert request["preflight_source"]["purpose"] == "PRE_EXECUTION_SOURCE_PREFLIGHT"
    purposes = {**daily.EXTRA_SOURCES, "batch_review_source": review_purpose}
    assert all(request[key]["purpose"] == purpose for key, purpose in purposes.items())
    assert daily.POLICY["provider"] == {"name": "DEEPSEEK_OFFICIAL", "base_url": "https://api.deepseek.com",
        "model": "deepseek-flash", "credential_binding": "DEEPSEEK_API_KEY", "reasoning": {"effort": "none"}}


def test_daily_result_returns_through_native_reader_without_model_or_new_writes(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    assert host.run_question(**case.args)["status"] == "VALIDATED_FUNNEL_RESULT"
    c, baseline = collector(case.args, tmp_path, stock=False)
    before = deepcopy(case.api.files[case.api.heads[intake.WORK_REF]])
    calls, writes = list(case.calls), len(case.writes)
    result = reader.attach(c, baseline)
    work = report(c, result)["question_work"]
    assert work["status"] == "READ_OK", work
    assert len(work["items"]) == 1
    row = work["items"][0]
    assert row["status"] == "VALIDATED_FUNNEL_RESULT" and row["terminal_state"] == "WAIT_FOR_TRIGGER"
    assert row["host_receipt_present"] and not row["quick_present"]
    assert row["semantic_acceptance"] == "NOT_ESTABLISHED_BY_READER"
    assert case.calls == calls and len(case.writes) == writes
    assert case.api.files[case.api.heads[intake.WORK_REF]] == before
    reading.validate_read_package(result)


def test_daily_model_boundary_uses_fixed_official_deepseek_wire(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    case.args.pop("call")
    requests, previews = [], []
    def model_call(stage, prompt, output_type, output, usage, **wire):
        requests.append(wire)
        body, schema, output_format, parameters = deepseek._deepseek_request(prompt, output_type)
        previews.append((body, output_format, parameters))
        return pre(prompt, "WAIT_FOR_TRIGGER")
    monkeypatch.setattr(once, "model_call", model_call)
    result = host.run_question(**case.args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert requests == [{"max_prompt_bytes": 512 * 1024, "base_url": "https://api.deepseek.com",
        "model": "deepseek-flash", "api_key_env": "DEEPSEEK_API_KEY", "provider": "DEEPSEEK_OFFICIAL",
        "extra_parameters": {"reasoning": {"effort": "none"}}}]
    body, output_format, parameters = previews[0]
    assert set(output_format) == {"type", "name", "schema"}
    assert parameters["model"] == "deepseek-flash"
    assert parameters["reasoning"] == {"effort": "none"}
    assert parameters["max_output_tokens"] == 6000
    assert parameters.get("tools", []) == []
    assert PDF_TEXT in body and "source-journal.json" not in body


def assert_unspent(case, result):
    assert result["status"] == "NOT_EXECUTED" and not result["formal_research_started"], result
    assert not case.calls and not case.writes
    assert not (case.args["output"] / "launch.json").exists()


@pytest.mark.parametrize("damage", [
    "disabled", "policy-changed", "permission-revoked", "different-permission",
    "dynamic-question", "update-static-downgrade", "missing-required-body", "missing-required-class",
    "no-full-review", "two-selected-questions", "review-clock", "future-source-commit",
    "private-context", "private-doc-field", "bound-page-representation", "forged-pdf-text",
    "foreign-pdf-locator", "locator-identity", "missing-pdf", "pdf-bytes-changed",
    "foreign-issuer-inventory", "missing-completed-read", "shell-completed-read",
    "missing-artifact", "expired-artifact", "corrupt-archive", "different-archived-copy", "different-archived-pages",
    "stock-run-failed", "stock-run-rerun", "stock-run-foreign", "stock-origin-mismatch",
    "source-run-unfinished", "source-run-rerun", "source-run-foreign", "origin-observed-clock",
])
def test_daily_unqualified_inputs_never_reserve_or_call(tmp_path, monkeypatch, damage):
    case = setup_daily(tmp_path, monkeypatch)
    doc = case.context["issuer_documents"][0]
    source_prefix = case.q["case_id"] + "/sources/"
    rearchive = False
    if damage == "disabled":
        case.request["enabled"] = False
    elif damage == "policy-changed":
        policy = deepcopy(daily.POLICY)
        policy["max_market_days"] += 1
        case.api.files[case.args["code"]][daily.POLICY_PATH] = once.raw(policy)
    elif damage == "permission-revoked":
        case.api.comment["body"] += " Revoked."
    elif damage == "different-permission":
        case.api.comment.update(id=1, body="Synthetic unrelated permission, not the daily policy.")
        case.request["permission"] = {"comment_id": 1, "created_at": case.api.comment["created_at"],
                                      "body_sha256": once.sha(case.api.comment["body"].encode())}
    elif damage == "dynamic-question":
        case.q["required_classes"][0].update(mode="LATEST_INVENTORY", planned_queries=["Bounded subsequent updates"])
    elif damage == "update-static-downgrade":
        case.q["required_classes"][0]["id"] = "LATEST_UPDATE_CHECK"
        case.pf["required_classes"][0]["id"] = "LATEST_UPDATE_CHECK"
    elif damage == "missing-required-body":
        case.pf["required_classes"][0]["body_ids"] = []
    elif damage == "missing-required-class":
        case.pf["required_classes"] = []
    elif damage == "no-full-review":
        case.review["items"].pop()
    elif damage == "two-selected-questions":
        case.review["items"][1]["disposition"] = "SELECTED_NEW_DISTINCT_QUESTION"
    elif damage == "review-clock":
        case.review["reviewed_at"] = case.args["clock"]()
    elif damage == "future-source-commit":
        case.commits["2" * 40]["committer"]["date"] = "2026-09-21T00:00:00Z"
    elif damage == "private-context":
        case.context["private_notes"] = "SYNTHETIC_PRIVATE_CONTENT_MUST_NOT_EGRESS"
    elif damage == "private-doc-field":
        doc["private_notes"] = "SYNTHETIC_PRIVATE_CONTENT_MUST_NOT_EGRESS"
    elif damage == "bound-page-representation":
        doc.update(reading_method="BOUND_SAME_PDF_READING", page_reading={"synthetic": "untrusted reading"})
    elif damage == "forged-pdf-text":
        doc["pages"][0]["text"] += " SYNTHETIC_PRIVATE_CONTENT_MUST_NOT_EGRESS"
    elif damage in {"foreign-pdf-locator", "locator-identity"}:
        doc["source_locator"] = ("https://private.invalid/source.PDF" if damage == "foreign-pdf-locator"
                                  else "https://static.cninfo.com.cn/finalpage/2026-09-18/9876543210.PDF")
        case.pf["reads"][0]["locator"] = doc["source_locator"]
    elif damage in {"missing-pdf", "pdf-bytes-changed"}:
        source = case.custody["documents"][0]["pdf_source"]
        if damage == "missing-pdf":
            del case.api.files[source["ref"]][source["path"]]
        else:
            case.api.files[source["ref"]][source["path"]] += b"changed"
    elif damage == "foreign-issuer-inventory":
        case.inventory["stock_code"] = "000920"
        case.archive_files[source_prefix + "inventory.json"] = once.raw(case.inventory)
        rearchive = True
    elif damage in {"missing-completed-read", "shell-completed-read"}:
        if damage == "missing-completed-read":
            case.journal["completed_reads"] = []
        else:
            case.journal["completed_reads"][0]["kind"] = "SHELL"
        case.archive_files[source_prefix + "source-journal.json"] = once.raw(case.journal)
        rearchive = True
    elif damage == "missing-artifact":
        case.artifacts.clear()
    elif damage == "expired-artifact":
        case.artifact["expired"] = True
    elif damage == "corrupt-archive":
        case.archive_bytes += b"changed"
    elif damage == "different-archived-copy":
        case.archive_files[source_prefix + "inventory.json"] += b" "
        rearchive = True
    elif damage == "different-archived-pages":
        path = source_prefix + doc["pdf_sha256"] + "-extraction.json"
        extraction = json.loads(case.archive_files[path])
        extraction["pages"][0]["text"] += " changed"
        case.archive_files[path] = once.raw(extraction)
        rearchive = True
    elif damage == "stock-run-failed":
        case.run["conclusion"] = "failure"
    elif damage == "stock-run-rerun":
        case.run["run_attempt"] = 2
    elif damage == "stock-run-foreign":
        case.run["head_repository"]["full_name"] = "other/decision-kernel"
    elif damage == "stock-origin-mismatch":
        case.run["id"] = 999
    elif damage == "source-run-unfinished":
        case.source_run["status"] = "in_progress"
    elif damage == "source-run-rerun":
        case.source_run["run_attempt"] = 2
    elif damage == "source-run-foreign":
        case.source_run["head_repository"]["full_name"] = "other/decision-kernel"
    else:
        case.q["origins"][0]["observed_at"] = "2026-09-18T10:04:01Z"
    if rearchive:
        rebuild_archive(case)
    refresh(case)
    result = host.run_question(**case.args)
    assert_unspent(case, result)


@pytest.mark.parametrize("at", ["2026-09-20T09:00:29Z", "2026-10-20T00:00:00Z", "2026-10-21T00:00:00Z"])
def test_daily_policy_has_finite_execution_clock(tmp_path, monkeypatch, at):
    case = setup_daily(tmp_path, monkeypatch)
    case.args["clock"] = lambda: at
    result = host.run_question(**case.args)
    assert_unspent(case, result)
    assert result["error_code"] == "DAILY_POLICY_EXPIRED_OR_NOT_STARTED"


@pytest.mark.parametrize("damage", ["omitted-disposition", "changed-disposition", "wrong-coverage"])
def test_daily_full_batch_review_cannot_hide_saved_stock_rows(tmp_path, monkeypatch, damage):
    case = setup_daily(tmp_path, monkeypatch)
    if damage == "omitted-disposition":
        case.stock["dispositions"].pop()
    elif damage == "changed-disposition":
        case.stock["dispositions"][0]["eligible_for_shadow_reading"] = False
    else:
        case.stock["coverage"]["planned_issuers"] = 2
    case.state["reading_hash"] = canonical_hash({key: value for key, value in case.state.items() if key != "reading_hash"})
    source = case.q["reading_source"]
    raw = once.raw(case.state)
    case.api.files[source["ref"]][source["path"]] = raw
    case.q["reading_source"] = once.source_ref(source["path"], source["ref"], raw, source["purpose"])
    case.review["batch_id"] = reader.stock_review_scope(case.state)["batch_id"]
    refresh(case)
    result = host.run_question(**case.args)
    assert_unspent(case, result)
    assert result["error_code"] == "DAILY_STOCK_FULL_SCOPE_DIFFERS"


@pytest.mark.parametrize("existing", ["prepare.json", "source.json", "input.json", "failure.json"])
def test_daily_existing_question_root_cannot_be_reopened_with_a_fresh_run(tmp_path, monkeypatch, existing):
    case = setup_daily(tmp_path, monkeypatch)
    case.api.heads[intake.WORK_REF] = case.args["code"]
    case.api.files[case.args["code"]][case.prefix + existing] = b"{}"
    result = host.run_question(**case.args)
    assert result["status"] == "EXISTING_QUESTION_REUSED_NO_EXECUTION", result
    assert not result["formal_research_started"] and not case.calls and not case.writes


def saved_marker(case, market_session, execution_id):
    if not execution_id.startswith("stock-question-"):
        execution_id = host.question_execution(case.q["security_id"], execution_id)[0]
    return {"policy": deepcopy(daily.POLICY), "market_session": market_session, "execution_id": execution_id}


@pytest.mark.parametrize("history,expected", [
    ("slot-gap", "DAILY_RESERVATION_HISTORY_INCOMPLETE"),
    ("orphan-day", "DAILY_RESERVATION_HISTORY_INCOMPLETE"),
    ("duplicate-day", "DAILY_RESERVATION_HISTORY_INCOMPLETE"),
    ("foreign-policy", "DAILY_RESERVATION_INVALID"),
])
def test_daily_incomplete_reservation_history_blocks_spending(tmp_path, monkeypatch, history, expected):
    case = setup_daily(tmp_path, monkeypatch)
    case.api.heads[intake.WORK_REF] = case.args["code"]
    files = case.api.files[case.args["code"]]
    marker = saved_marker(case, "2026-09-18", "synthetic-other-question")
    if history == "slot-gap":
        files[daily.PREFIX + "slots/02/prepare.json"] = once.raw(marker)
    elif history == "orphan-day":
        files[daily.PREFIX + "days/2026-09-18/prepare.json"] = once.raw(marker)
    else:
        if history == "foreign-policy":
            marker["policy"]["max_market_days"] += 1
        files[daily.PREFIX + "slots/01/prepare.json"] = once.raw(marker)
        if history == "duplicate-day":
            files[daily.PREFIX + "slots/02/prepare.json"] = once.raw(saved_marker(case, "2026-09-18", "duplicate-day"))
    result = host.run_question(**case.args)
    assert_unspent(case, result)
    assert result["error_code"] == expected


@pytest.mark.parametrize("point", ["slot", "day", "question"])
def test_daily_uncertain_reservation_stops_writes_and_never_retries(tmp_path, monkeypatch, point):
    case = setup_daily(tmp_path, monkeypatch)
    original = once.Retainer.native
    endpoint = "contents/" + {
        "slot": daily.PREFIX + "slots/01/prepare.json",
        "day": daily.PREFIX + "days/2026-09-18/prepare.json",
        "question": case.prefix + "prepare.json",
    }[point]
    attempted = []
    def uncertain(self, method, path, body):
        attempted.append(path)
        result = original(self, method, path, body)
        if path == endpoint:
            # Git accepted this create, but the caller never received its reply.
            self.uncertain = True
            raise RuntimeError("SYNTHETIC_UNCERTAIN_REPLY_MUST_NOT_LEAK")
        return result
    monkeypatch.setattr(once.Retainer, "native", uncertain)
    result = host.run_question(**case.args)
    assert result["status"] == "NOT_EXECUTED" and result["mutation_uncertain"], result
    assert not result["formal_research_started"] and not case.calls
    assert attempted[-1] == endpoint and attempted.count(endpoint) == 1
    assert not (case.args["output"] / "launch.json").exists()
    before = deepcopy(case.api.files[case.api.heads[intake.WORK_REF]])
    count = len(case.writes)
    case.args["output"] = tmp_path / "again"
    repeat = host.run_question(**case.args)
    assert repeat["status"] in {"NOT_EXECUTED", "EXISTING_QUESTION_REUSED_NO_EXECUTION"}, repeat
    assert not case.calls and len(case.writes) == count
    assert case.api.files[case.api.heads[intake.WORK_REF]] == before
    assert all(b"SYNTHETIC_UNCERTAIN_REPLY" not in raw for raw in before.values())


def test_daily_competing_slot_create_cannot_spend(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    original = once.Retainer.native
    slot = daily.PREFIX + "slots/01/prepare.json"
    def compete(self, method, endpoint, body):
        if endpoint == "contents/" + slot:
            files = case.api.files[case.api.heads[intake.WORK_REF]]
            files[slot] = once.raw(saved_marker(case, "2026-09-18", "synthetic-competing-question"))
        return original(self, method, endpoint, body)
    monkeypatch.setattr(once.Retainer, "native", compete)
    result = host.run_question(**case.args)
    assert result["status"] == "NOT_EXECUTED" and result["mutation_uncertain"], result
    assert not case.calls and not result["formal_research_started"]
    assert [path for method, path, body in case.writes].count("contents/" + slot) == 1
    assert not any(path == "contents/" + case.prefix + "launch.json" for method, path, body in case.writes)


@pytest.mark.parametrize("failure,expected_calls", [("pre", ["pre"]), ("quick", ["pre", "quick"]),
                                                  ("revoke-after-pre", ["pre"])])
def test_daily_provider_failure_or_revocation_is_retained_without_retry_or_business_wait(tmp_path, monkeypatch, failure, expected_calls):
    case = setup_daily(tmp_path, monkeypatch, route="CONTINUE_TO_QUICK")
    def call(stage, prompt, model, output, usage):
        case.calls.append(stage)
        if stage == failure:
            raise RuntimeError("SYNTHETIC_PROVIDER_SECRET_MUST_NOT_LEAK")
        if failure == "revoke-after-pre":
            case.api.comment["body"] += " revoked"
        return pre(prompt, "CONTINUE_TO_QUICK") if stage == "pre" else quick(prompt)
    case.args["call"] = call
    result = host.run_question(**case.args)
    assert result["status"] == "EXECUTION_GAP", result
    assert case.calls == expected_calls and result["formal_research_started"]
    assert not (case.args["output"] / "funnel.json").exists()
    saved = case.api.files[case.api.heads[intake.WORK_REF]]
    assert daily.PREFIX + "slots/01/prepare.json" in saved
    assert daily.PREFIX + "days/2026-09-18/prepare.json" in saved
    assert all(b"SYNTHETIC_PROVIDER_SECRET" not in raw for raw in saved.values())
    before, count = deepcopy(saved), len(case.writes)
    case.args["output"] = tmp_path / "again"
    repeated = host.run_question(**case.args)
    assert repeated["status"] in {"NOT_EXECUTED", "EXISTING_QUESTION_REUSED_NO_EXECUTION"}
    assert case.calls == expected_calls and len(case.writes) == count
    assert case.api.files[case.api.heads[intake.WORK_REF]] == before