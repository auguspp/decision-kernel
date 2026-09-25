"""Pure read contracts. Synthetic runs are never production acceptance evidence."""
from __future__ import annotations

import copy
import io
import json
import zipfile
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime.attention_inbox import ResearchAttentionHandoff, serialize_research_attention_handoff
from test_attention_inbox_research import _deepen

SHA = "a" * 40
AT = "2026-09-08T10:40:00+00:00"


def run(number=10, *, lane="sector", status="completed", conclusion="success", event="schedule", day=8):
    return {"id": number, "path": read.WORKFLOWS[lane], "head_sha": SHA, "head_branch": "main",
            "repository": {"full_name": read.REPOSITORY}, "head_repository": {"full_name": read.REPOSITORY},
            "status": status, "conclusion": conclusion, "event": event, "run_attempt": 1,
            "created_at": f"2026-09-{day:02}T10:13:00Z"}


def test_production_selection_does_not_use_a_successful_test_on_same_sha():
    good = run()
    ci = dict(run(20), path=".github/workflows/ci.yml", event="push")
    latest, chosen = read.select_runs([ci, good], "sector")
    assert latest == chosen == good
    read.run_identity(chosen, "sector", success=True)


@pytest.mark.parametrize("field,value", [
    ("event", "pull_request"), ("head_branch", "other"), ("run_attempt", 2),
    ("head_sha", "latest"), ("repository", {"full_name": "foreign/repo"}),
    ("head_repository", {"full_name": "foreign/repo"}),
    ("status", "in_progress"), ("conclusion", "failure"),
])
def test_run_binding_rejects_wrong_identity_or_incomplete_production(field, value):
    with pytest.raises(ValueError):
        read.run_identity(dict(run(), **{field: value}), "sector", success=True)


def test_latest_failure_does_not_hide_behind_prior_qualified_success():
    old = {"market_session": "2026-09-07", "source_checked_at": "2026-09-07T12:00:00Z"}
    latest, success = read.select_runs([run(9, day=7), run(10, conclusion="failure")], "sector")
    lane = read.lane_reading(latest=latest, qualified=old, failure=None, checked_at=AT, query_complete=True)
    assert success["id"] == 9
    assert lane["health"] == "LATEST_ATTEMPT_FAILED"
    assert lane["last_qualified_result"]["market_session"] == "2026-09-07"
    assert not lane["restore_authority"]
    assert lane["market_freshness"] == "LATEST_COMPLETED_SESSION_NOT_REQUALIFIED_BY_THIS_READER"


@pytest.mark.parametrize("state", [None, "in_progress", "queued", "waiting"])
def test_unrun_or_running_is_never_quiet(state):
    latest = None if state is None else run(status=state, conclusion=None)
    lane = read.lane_reading(latest=latest, qualified=None, failure=None, checked_at=AT, query_complete=True)
    assert lane["health"] not in {"LATEST_ATTEMPT_SUCCEEDED", "QUIET"}
    assert lane["gaps"]


def test_rejected_latest_input_keeps_only_labelled_previous_read_copy():
    previous = {"last_qualified_result": {"market_session": "2026-09-07", "source_checked_at": "2026-09-07T12:00:00Z"}}
    before = copy.deepcopy(previous)
    lane = read.lane_reading(latest=run(), qualified=None, failure="LATEST_ARTIFACT_EXPIRED", checked_at=AT,
                            query_complete=False, previous=previous)
    assert lane["health"] == "CHECK_INCOMPLETE"
    assert "LATEST_ARTIFACT_EXPIRED" in lane["gaps"]
    assert lane["reading_copy_kind"] == "PREVIOUSLY_VERIFIED_READ_COPY_NOT_RESTORE_INPUT"
    assert previous == before
    assert lane["last_qualified_result"]["source_checked_at"] == "2026-09-07T12:00:00Z"


def test_partial_stock_denominator_and_unknown_inputs_are_not_complete():
    saved = {"market_session": "2026-09-07", "coverage": {
        "planned_issuers": 4, "evaluated_issuers": 3, "unavailable_issuers": 1, "scope_complete": False},
        "unreviewed_member_count": 32, "surfaced_codes": ["605296.SH"]}
    lane = read.lane_reading(latest=run(lane="stock"), qualified=saved, failure=None, checked_at=AT, query_complete=True)
    assert lane["last_qualified_result"] == saved
    assert "PARTIAL_STOCK_COVERAGE_NOT_COMPLETE_OR_QUIET" in lane["gaps"]


def archive_fixture(name="summary.md", content=b"saved content"):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(name, content)
    raw = stream.getvalue()
    metadata = {"id": 100, "name": "example", "expired": False, "size_in_bytes": len(raw),
                "digest": "sha256:" + read.sha256(raw), "workflow_run": {"id": 10, "head_sha": SHA}}
    return raw, metadata


def test_archive_digest_identity_inventory_and_no_implicit_extraction(tmp_path):
    raw, metadata = archive_fixture()
    assert read.unpack_archive(raw, metadata, run()) == {"summary.md": b"saved content"}
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("field,value", [
    ("expired", True), ("digest", "sha256:" + "0" * 64), ("size_in_bytes", 1),
    ("workflow_run", {"id": 11, "head_sha": SHA}),
    ("workflow_run", {"id": 10, "head_sha": "b" * 40}),
])
def test_bad_archive_input_is_rejected_not_renamed_or_replaced(field, value):
    raw, metadata = archive_fixture()
    with pytest.raises(ValueError):
        read.unpack_archive(raw, dict(metadata, **{field: value}), run())


@pytest.mark.parametrize("name", ["../outside", "/absolute", "a/../b", "a\\b", "./a"])
def test_unsafe_archive_path_is_rejected(name):
    raw, metadata = archive_fixture(name)
    with pytest.raises(ValueError):
        read.unpack_archive(raw, metadata, run())


def test_selected_missing_or_expired_artifact_never_chooses_older_similar_name():
    with pytest.raises(ValueError, match="missing"):
        read.select_artifact([{"name": "old-state-bundle", "expired": False}], "sector-radar-state-bundle")
    with pytest.raises(ValueError, match="expired"):
        read.select_artifact([{"name": "sector-radar-state-bundle", "expired": True}], "sector-radar-state-bundle")


def handoff(discovery_id="first", lane="SOURCE_A"):
    return serialize_research_attention_handoff(ResearchAttentionHandoff(
        _deepen(ticker="000001", discovery_id=discovery_id, lane=lane), "Synthetic issuer")).encode()


def loader(values):
    def load(spec):
        raw = values[spec["path"]]
        return raw, {"path": spec["path"], "ref": SHA, "sha256": read.sha256(raw)}
    return load


def test_valid_quick_request_is_independent_of_market_or_odds_failure(monkeypatch, tmp_path):
    raw = handoff()
    registry = {"references": [], "historical_handoffs": [], "additional_registered_handoffs": [
        {"source": {"path": "valid.json"}, "registered_current": True}]}
    collector = delivery.Collector(None, SHA, tmp_path, now=lambda: AT)
    def source(spec):
        if spec["path"] != "valid.json":
            raise ValueError("independent production configuration unavailable")
        return loader({"valid.json": raw})(spec)
    monkeypatch.setattr(collector, "source", source)
    # Never call the CLI or live package runner even for a valid handoff.
    from decision_kernel.runtime import attention_inbox
    def forbidden(*args, **kwargs):
        pytest.fail("reader attempted live production")
    monkeypatch.setattr(attention_inbox, "_run_research_package", forbidden)
    monkeypatch.setattr(attention_inbox, "main", forbidden)
    result = collector.research(registry)
    assert result["gaps"][0]["status"] == "PRODUCTION_REGISTRATION_UNAVAILABLE"
    assert len(result["handoffs"]["active"]) == 1
    assert result["handoffs"]["active"][0]["terminal_state"] == "DEEPEN_REQUIRED"


def test_same_ticker_preserves_different_problem_and_content_identities():
    values = {"a.json": handoff("first", "SOURCE_A"), "b.json": handoff("second", "SOURCE_B")}
    entries = [{"source": {"path": p}, "registered_current": True} for p in values]
    result = read.project_handoffs(entries, loader(values))
    assert len(result["active"]) == 2
    assert len({i["ticker"] for i in result["active"]}) == 1
    assert len({i["request_id"] for i in result["active"]}) == 2
    assert read.project_handoffs(entries, loader(values)) == result


def test_resolved_request_keeps_history_without_restoring_current_attention():
    raw = handoff()
    entry = {"source": {"path": "a.json"}, "registered_current": True,
             "resolved_handoff_sha256": read.sha256(raw), "resolution": {"path": "resolved.md"}}
    result = read.project_handoffs([entry], loader({"a.json": raw, "resolved.md": b"explicit resolved record"}))
    assert result["active"] == [] and len(result["resolved_history"]) == 1


def test_bad_resolution_cannot_silently_close_current_valid_request():
    raw = handoff()
    entry = {"source": {"path": "a.json"}, "registered_current": True,
             "resolved_handoff_sha256": "0" * 64, "resolution": {"path": "resolved.md"}}
    result = read.project_handoffs([entry], loader({"a.json": raw, "resolved.md": b"wrong version"}))
    assert len(result["active"]) == 1 and result["resolved_history"] == []
    assert result["gaps"][0]["status"] == "RESOLUTION_UNVERIFIED"


def test_no_handoff_is_not_an_all_market_research_claim():
    result = read.project_handoffs([], loader({}))
    assert result["active"] == []
    assert result["registration_scope"] == "EXPLICIT_INPUTS_ONLY_NOT_ALL_RESEARCH_OR_ALL_MARKET"


def test_historical_handoff_file_presence_does_not_create_pending():
    result = read.project_handoffs([{"source": {"path": "a.json"}, "registered_current": False}],
                                   loader({"a.json": handoff()}))
    assert not result["active"] and len(result["background"]) == 1


def test_tinavi_real_frozen_handoff_is_retained_as_resolved_not_daily_pending():
    registry = json.loads(Path(delivery.REGISTRY_PATH).read_text())
    def load(spec):
        raw = Path(spec["path"]).read_bytes()
        assert read.blob_sha(raw) == spec["git_blob"]
        assert all(s in raw.decode() for s in spec.get("contains", []))
        return loader({spec["path"]: raw})(spec)
    result = read.project_handoffs(registry["historical_handoffs"], load)
    assert not result["gaps"] and not result["active"]
    assert len(result["resolved_history"]) == 1
    assert result["resolved_history"][0]["terminal_state"] == "DEEPEN_REQUIRED"


def test_production_purposes_are_separate_from_method_and_human_records():
    registry = json.loads(Path(delivery.REGISTRY_PATH).read_text())
    production = read.configured_paths(Path(read.WORKFLOWS["inbox"]).read_text(), "decision_packages")
    # R5 retires automatic legacy Odds, not stored research or Human history.
    assert production == []
    assert "dogfood/300750-catl.json" not in production
    for case in ("603986.SH", "002050.SZ"):
        uses = {r["use"] for r in registry["references"] if r["case"] == case}
        assert {"METHOD_SUPPLEMENT", "HUMAN_DECISION_CHECKPOINT", "HISTORICAL_CALCULATION_BASELINE"} <= uses
    assert any(r["use"] == "EXPLICIT_QUALIFICATION_EXIT_REFERENCE" for r in registry["references"])


@pytest.mark.parametrize("item", ["dogfood/*.json", "$(echo bad).json", "../other.json"])
def test_production_array_is_parsed_as_data_not_executed(item):
    with pytest.raises(ValueError):
        read.configured_paths("decision_packages=(\n " + item + "\n)\n", "decision_packages")


def test_fixed_package_is_deterministic_and_source_text_cannot_expand_authority():
    lanes = {"sector": read.lane_reading(latest=None, qualified=None,
        failure='<script>dispatch()</script>', checked_at=AT, query_complete=False)}
    kwargs = dict(code_commit=SHA, checked_at=AT, check_started_at=AT, lanes=lanes,
                  research={"handoffs": {"active": []}}, capabilities=[], refresh_identity={})
    payload = read.assemble(**kwargs)
    assert payload == read.assemble(**kwargs)
    assert "<script>" not in read.render_summary(payload)
    assert "&lt;script&gt;" in read.render_summary(payload)
    payload["research_authority"] = "EXECUTE"
    payload["reading_hash"] = canonical_hash({k: v for k, v in payload.items() if k != "reading_hash"})
    with pytest.raises(ValueError, match="authority"):
        read.validate_read_package(payload)


def test_root_index_keeps_exact_utf8_byte_limit_including_final_newline():
    kwargs = dict(code_commit=SHA, checked_at=AT, check_started_at=AT, lanes={},
                  research={"handoffs": {"active": []}, "note": ""}, capabilities=[], refresh_identity={})
    remaining = 192 * 1024 - len(read.read_package_bytes(read.assemble(**kwargs)))
    kwargs["research"]["note"] = "中" * (remaining // 3) + "x" * (remaining % 3)
    payload = read.assemble(**kwargs)
    raw = read.read_package_bytes(payload)
    assert len(raw) == 192 * 1024 and raw.endswith(b"\n")
    assert len(raw.decode("utf-8")) < len(raw) < len(read.json_bytes(payload))
    read.validate_read_package(json.loads(raw))
    kwargs["research"]["note"] += "x"
    with pytest.raises(ValueError, match="bounded index size"):
        read.assemble(**kwargs)
    # A later mutation cannot make an actual emitter exceed the same byte bound.
    with pytest.raises(ValueError, match="bounded index size"):
        read.read_package_bytes(payload)


@pytest.mark.parametrize("terminal", ["WAIT_FOR_TRIGGER", "DROP_FOR_NOW"])
def test_wait_or_drop_never_becomes_active_research(terminal):
    from test_attention_inbox_research import _wait
    from decision_kernel.research_workflow_v1 import ResearchFunnelResult
    value = _wait(ticker="000001", discovery_id="waiting", lane="BACKGROUND").model_dump(mode="json")
    if terminal == "DROP_FOR_NOW":
        # Same existing models own this disposition; no reader-side route creation.
        from decision_kernel.research_funnel import PreResearchRoute
        value["pre_research"]["route"] = PreResearchRoute.STOP.value
        value["terminal_state"] = terminal
    frozen = ResearchFunnelResult.model_validate(value)
    raw = serialize_research_attention_handoff(ResearchAttentionHandoff(frozen)).encode()
    result = read.project_handoffs([{"source": {"path": "wait.json"}, "registered_current": True}], loader({"wait.json": raw}))
    assert not result["active"] and result["background"][0]["terminal_state"] == terminal


def test_malformed_handoff_does_not_suppress_independent_valid_request():
    entries = [{"source": {"path": p}, "registered_current": True} for p in ("bad.json", "good.json")]
    result = read.project_handoffs(entries, loader({"bad.json": b"{}", "good.json": handoff()}))
    assert len(result["active"]) == 1 and len(result["gaps"]) == 1


def test_sector_question_without_ticker_is_not_assigned_a_leader():
    from decision_kernel.research_workflow_v1 import ResearchFunnelResult
    value = _deepen(ticker="000001", discovery_id="industry-only", lane="SECTOR").model_dump(mode="json")
    value["discovery"]["ticker"] = None
    value["discovery"]["security_id"] = "SECTOR:SYNTHETIC-INDUSTRY"
    frozen = ResearchFunnelResult.model_validate(value)
    raw = serialize_research_attention_handoff(ResearchAttentionHandoff(frozen)).encode()
    result = read.project_handoffs([{"source": {"path": "sector.json"}, "registered_current": True}], loader({"sector.json": raw}))
    assert not result["gaps"]
    assert result["active"][0]["ticker"] is None
    assert result["active"][0]["security_id"] == "SECTOR:SYNTHETIC-INDUSTRY"
    assert result["active"][0]["source_lane"] == "SECTOR"
