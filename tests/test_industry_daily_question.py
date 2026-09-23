"""Industry-to-original-host integration; only Git I/O and model replies are fake."""
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import socket
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as reading, saved_research_once as once
from decision_kernel.runtime import industry_breadth as breadth, industry_breadth_reading as br
from decision_kernel.runtime import industry_daily_question as industry, stock_daily_question as daily
from decision_kernel.runtime import stock_question_host as host, stock_research_intake as intake
from test_stock_daily_question import setup_daily, refresh

ROOT = Path(__file__).parents[1]
NOW = datetime(2026, 9, 22, 15, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Industry integration is offline")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


def seal_case(c):
    c.report["projection_hash"] = canonical_hash(c.report["projection"])
    raw = once.raw(c.report)
    rs = c.q["reading_source"]
    spec = {"read_path": br.REPORT, "bytes": len(raw), "git_blob": once.blob(raw),
            "sha256": once.sha(raw), "read_ref_rule": "USE_THE_SAME_PINNED_READING_COMMIT"}
    c.state["research"]["industry_breadth"] = {"details": {"json": spec}}
    c.state = reading.assemble(code_commit=c.args["code"], checked_at=c.state["generated_at"],
        check_started_at=c.state["checks"]["started_at"], lanes=c.state["lanes"], research=c.state["research"],
        capabilities=c.state["capability_gaps"], refresh_identity=c.state["refresh"])
    state_raw = once.raw(c.state)
    c.api.files[rs["ref"]].update({"current-state.json": state_raw, br.REPORT: raw})
    c.q["reading_source"] = once.source_ref("current-state.json", rs["ref"], state_raw, rs["purpose"])
    c.q["origins"] = [{"kind": "INDUSTRY_VARIABLE_OBSERVATION",
        "source": once.source_ref(br.REPORT, rs["ref"], raw, "SAVED_INDUSTRY_BATCH_ORIGIN"),
        "observed_at": c.section["capture"]["receipt"]["received_at"],
        "qualification": "QUALIFIED_FOR_DECLARED_SCOPE", "qualification_reason": "Saved dated context for this synthetic economic question only."}]
    c.review["batch_id"] = industry.batch_id(c.q["reading_source"], c.section)
    refresh(c)
    c.review["economic_exposure"]["context_source"] = c.request["context_source"]
    refresh(c)


def setup_industry(tmp_path, monkeypatch, route="WAIT_FOR_TRIGGER"):
    c = setup_daily(tmp_path, monkeypatch, route=route, at=NOW)
    permission = (ROOT / "tests/fixtures/industry_daily_question_permission.txt").read_text().removesuffix("\n")
    assert once.sha(permission.encode()) == industry.PERMISSION["body_sha256"]
    c.api.comment.update(id=industry.PERMISSION["comment_id"], body=permission,
                         created_at=industry.PERMISSION["created_at"])
    c.request["permission"] = deepcopy(industry.PERMISSION)
    c.request["batch_review_source"]["purpose"] = industry.PURPOSE
    c.api.files[c.args["code"]][industry.EXTENSION_PATH] = once.raw(industry.EXTENSION)
    # No Stock candidate or successful Stock product is supplied to this route.
    c.state["lanes"]["stock"]["last_qualified_result"] = None
    c.sector_run = {**deepcopy(c.run), "id": 103, "path": reading.WORKFLOWS["sector"]}
    c.state["lanes"]["sector"] = {"health": "LATEST_ATTEMPT_SUCCEEDED", "gaps": [],
        "last_qualified_result": {"market_session": "2026-09-18",
            "archive": {"origin_run": reading.concise_run(c.sector_run)}}}
    c.industry_run = {**deepcopy(c.run), "id": 104, "event": "workflow_dispatch", "path": breadth.WORKFLOW,
        "created_at": "2026-09-18T10:05:00Z", "run_started_at": "2026-09-18T10:05:01Z",
        "updated_at": "2026-09-18T10:08:00Z"}
    row = {"thscode": "CUZL.SHF", "ticker": "cu9999", "spot_indicator_id": "test", "reference_site": "Synthetic",
           "spot_publish_date": "2026-09-18", "spot_price": 100, "converted_spot_price": 100,
           "close_price": 99, "settle_price": 99, "close_basis": 1, "settle_basis": 1,
           "close_basis_rate": 1, "settle_basis_rate": 1}
    body = once.raw({"code": 0, "data": {"timestamp": 1789725900000,
        "item": [row, {**row, "thscode": "RBZL.SHF", "ticker": "rb9999"}]}})
    times = iter(["2026-09-18T10:06:00Z", "2026-09-18T10:06:01Z", "2026-09-18T10:06:02Z"])
    path = tmp_path / "native-capture"
    capture = breadth.capture(path, {"repository": once.REPO, "workflow": breadth.WORKFLOW,
        "ref": "refs/heads/main", "event": "workflow_dispatch", "code_commit": c.industry_run["head_sha"],
        "run_id": 104, "attempt": 1, "trigger_run_id": None}, credential="synthetic-key",
        request=lambda _: body, clock=lambda: next(times))
    assert capture["error_type"] is None, capture
    c.industry_files = {p.name: p.read_bytes() for p in path.iterdir()}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as out:
        for name, raw in c.industry_files.items(): out.writestr(name, raw)
    c.industry_bytes = buf.getvalue()
    c.industry_artifact = {"id": 1040, "name": "industry-breadth-104-1", "expired": False,
        "size_in_bytes": len(c.industry_bytes), "digest": "sha256:" + once.sha(c.industry_bytes),
        "workflow_run": {"id": 104, "head_sha": c.industry_run["head_sha"]}}
    c.section = {**breadth.replay(c.industry_files, c.industry_run, cutoff=c.args["clock"]()),
        "latest_attempt": reading.concise_run(c.industry_run), "archive": {
            "artifact_id": 1040, "artifact_name": c.industry_artifact["name"], "bytes": len(c.industry_bytes),
            "sha256": once.sha(c.industry_bytes), "origin_run": reading.concise_run(c.industry_run)}}
    c.report = {"projection": {"sections": {"native": c.section}, "generated_at": c.state["generated_at"]}}
    c.review = {"reading_source": c.q["reading_source"], "question_source": c.request["question_source"],
        "batch_id": "pending", "reviewed_at": c.review["reviewed_at"], "market_session": "2026-09-18",
        "items": [{**industry.row_binding(r), "disposition": "SELECTED_FOR_QUESTION" if i == 0 else "NOT_SELECTED",
                   "reason": "Synthetic selection for retained company exposure; not a price gate."}
                  for i, r in enumerate(c.section["snapshot"]["projection"]["observations"])],
        "economic_exposure": {"case_id": c.q["case_id"], "security_id": c.q["security_id"],
            "context_source": c.request["context_source"], "mechanism": "Synthetic documented exposure",
            "materiality_basis": "Underlying company body must establish relevance, not the copper price.",
            "counterevidence": "Pass-through can offset nominal price effects.",
            "falsification_test": c.q["falsification_test"], "use": "QUESTION_FORMATION_NOT_QUANTIFIED_BENEFIT"}}
    get, archive = c.api.get, c.api.archive
    def get_(path):
        if path == "actions/runs/103": return deepcopy(c.sector_run)
        if path == "actions/runs/104": return deepcopy(c.industry_run)
        if path == "actions/runs/104/artifacts?per_page=100":
            return {"total_count": 1, "artifacts": [deepcopy(c.industry_artifact)]}
        return get(path)
    def archive_(a):
        if a["id"] == 1040:
            c.archive_calls.append(1040)
            return c.industry_bytes
        return archive(a)
    c.api.get, c.api.archive = get_, archive_
    seal_case(c)
    return c


@pytest.mark.parametrize("route,stages", [("WAIT_FOR_TRIGGER", ["pre"]), ("STOP", ["pre"]),
                                         ("CONTINUE_TO_QUICK", ["pre", "quick"])])
def test_industry_outside_stock_uses_original_host_custody_and_funnel(tmp_path, monkeypatch, route, stages):
    c = setup_industry(tmp_path, monkeypatch, route)
    assert c.state["lanes"]["stock"]["last_qualified_result"] is None
    result = host.run_question(**c.args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert c.calls == stages and c.archive_calls == [1040, 1020]
    scope = result["daily_scope"]
    assert scope["origin_kind"] == "INDUSTRY_VARIABLE_OBSERVATION"
    assert scope["extension_permission"] == industry.PERMISSION and scope["economic_exposure"] == c.review["economic_exposure"]
    assert result["investment_authority"] == "NONE" and not result["automatic_retry"]
    saved = c.api.files[c.api.heads[intake.WORK_REF]]
    marker = json.loads(saved[daily.PREFIX + "slots/01/prepare.json"])
    assert marker["policy"] == daily.POLICY and marker["origin_kind"] == scope["origin_kind"]
    assert daily.PREFIX + "days/2026-09-18/prepare.json" in saved
    assert json.loads(saved[c.prefix + "launch.json"])["permission"] == industry.PERMISSION
    assert json.loads(saved[c.prefix + "admission.json"])["research_execution_allowed"] is True


@pytest.mark.parametrize("damage", ["missing_row", "reordered_rows", "duplicate_row", "no_selection", "bad_row_hash",
    "no_mechanism", "no_materiality", "wrong_company", "fake_evidence", "wrong_context", "wrong_day",
    "native_failed", "changed_replay", "foreign_run", "expired_artifact", "damaged_zip", "no_sector",
    "changed_policy", "old_permission", "missing_pdf", "changed_pdf_text", "wrong_origin_clock"])
def test_invalid_industry_inputs_never_reserve_or_call_model(tmp_path, monkeypatch, damage):
    c = setup_industry(tmp_path, monkeypatch)
    if damage == "missing_row": c.review["items"].pop()
    elif damage == "reordered_rows": c.review["items"].reverse()
    elif damage == "duplicate_row": c.review["items"][1] = deepcopy(c.review["items"][0])
    elif damage == "no_selection": c.review["items"][0]["disposition"] = "CONTEXT_ONLY"
    elif damage == "bad_row_hash": c.review["items"][0]["raw_sha256"] = "0" * 64
    elif damage == "no_mechanism": c.review["economic_exposure"]["mechanism"] = ""
    elif damage == "no_materiality": c.review["economic_exposure"]["materiality_basis"] = ""
    elif damage == "wrong_company": c.review["economic_exposure"]["case_id"] = "600362.SH"
    elif damage == "fake_evidence": c.review["economic_exposure"]["use"] = "COMPANY_EVIDENCE"
    elif damage == "wrong_context": c.review["economic_exposure"]["context_source"] = c.request["question_source"]
    elif damage == "wrong_day": c.review["market_session"] = "2026-09-21"
    elif damage == "native_failed": c.section["status"] = "SOURCE_UNAVAILABLE"
    elif damage == "changed_replay": c.section["snapshot"]["projection"]["observations"][0]["raw"]["close_price"] = 1000
    elif damage == "foreign_run": c.industry_run["repository"]["full_name"] = "foreign/repo"
    elif damage == "expired_artifact": c.industry_artifact["expired"] = True
    elif damage == "damaged_zip": c.industry_bytes += b"changed"
    elif damage == "no_sector": c.state["lanes"].pop("sector")
    elif damage == "changed_policy": c.api.files[c.args["code"]][industry.EXTENSION_PATH] = once.raw({})
    elif damage == "old_permission": c.request["permission"] = daily.PERMISSION
    elif damage == "missing_pdf": c.api.files[c.custody["documents"][0]["pdf_source"]["ref"]] = {}
    elif damage == "changed_pdf_text": c.context["issuer_documents"][0]["pages"][0]["text"] = "fake full source 600184"
    seal_case(c)
    # Keep deliberately bad declaration fields after resealing dependent sources.
    if damage == "wrong_context": c.review["economic_exposure"]["context_source"] = c.request["question_source"]
    if damage == "wrong_origin_clock": c.q["origins"][0]["observed_at"] = "2026-09-18T10:06:00Z"
    refresh(c)
    result = host.run_question(**c.args)
    assert result["status"] == "NOT_EXECUTED", result
    assert not result["formal_research_started"] and c.calls == [] and c.writes == []


def test_shared_stock_day_consumption_cannot_be_reset_by_industry(tmp_path, monkeypatch):
    c = setup_industry(tmp_path, monkeypatch)
    # "e" * 40 already stores MODEL_CONTEXT in setup_question. Use a distinct
    # immutable history identity so this test reaches the shared-day gate.
    ref = once.sha(b"synthetic-existing-stock-consumption")[:40]
    assert ref not in c.api.files
    c.api.heads[intake.WORK_REF] = ref
    marker = {"policy": daily.POLICY, "market_session": "2026-09-18", "execution_id": "stock-question-" + "a" * 64}
    c.api.files[ref] = {daily.PREFIX + "slots/01/prepare.json": once.raw(marker),
                       daily.PREFIX + "days/2026-09-18/prepare.json": once.raw(marker)}
    before = deepcopy(c.api.files)
    result = host.run_question(**c.args)
    assert result["status"] == "NOT_EXECUTED", result
    assert result["error_code"] == "DAILY_MARKET_DAY_ALREADY_CONSUMED", result
    assert not result["formal_research_started"] and c.calls == [] and c.writes == []
    assert c.api.files == before


def test_policy_is_additive_and_original_request_not_activated_for_industry():
    assert json.loads((ROOT / industry.EXTENSION_PATH).read_bytes()) == industry.EXTENSION
    from test_quick_checkpoint_activation import checked_daily_configuration
    request = checked_daily_configuration(ROOT)
    # Deployment may now select either explicitly approved family. The extension
    # still shares the unchanged Stock consumption policy; a request is not a run.
    assert json.loads((ROOT / daily.POLICY_PATH).read_bytes()) == daily.POLICY
    purpose = request["batch_review_source"]["purpose"]
    permissions = {daily.EXTRA_SOURCES["batch_review_source"]: daily.PERMISSION,
                   industry.PURPOSE: industry.PERMISSION}
    assert request["permission"] == permissions[purpose]
    assert industry.EXTENSION["shared_consumption_prefix"] == daily.PREFIX
    assert industry.EXTENSION["model_cost_policy"] == "HUMAN_MANAGED_ACCOUNT_NO_ADDITIONAL_PROJECT_MONETARY_CEILING"